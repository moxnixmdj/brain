"""Fail-closed DOCX relationship-bound image replacement.

Scope
-----
Replace exactly one existing image/media payload referenced by an explicit
relationship Id from a chosen Word XML part. The XML part, relationship part,
content types, dimensions, drawing anchors, styles, tables, fields, and every
other ZIP member remain byte-identical.

This is a structural native edit, not semantic image selection. The caller must
provide the exact source part and relationship Id. Unknown/ambiguous paths fail
closed.
"""
from __future__ import annotations

from pathlib import Path
from posixpath import normpath, dirname, join
import hashlib
import xml.etree.ElementTree as ET
import zipfile

REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
OFFICE_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
IMAGE_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _rels_name(source_part: str) -> str:
    d = dirname(source_part)
    b = source_part.rsplit("/", 1)[-1]
    return f"{d}/_rels/{b}.rels" if d else f"_rels/{b}.rels"


def _resolve_target(source_part: str, target: str) -> str | None:
    if not target or target.startswith("/") or "://" in target:
        return None
    base = dirname(source_part)
    resolved = normpath(join(base, target))
    if resolved.startswith("../") or resolved == "..":
        return None
    return resolved


def replace_image_by_relationship(
    input_path: str | Path,
    output_path: str | Path,
    *,
    source_part: str,
    relationship_id: str,
    replacement_image: bytes,
) -> dict:
    src = Path(input_path)
    dst = Path(output_path)

    if not src.is_file():
        return {"status": "FAIL_CLOSED", "reason": "INPUT_MISSING"}
    if not isinstance(source_part, str) or not source_part.startswith("word/") or not source_part.endswith(".xml"):
        return {"status": "FAIL_CLOSED", "reason": "SOURCE_PART_INVALID"}
    if not isinstance(relationship_id, str) or not relationship_id:
        return {"status": "FAIL_CLOSED", "reason": "RELATIONSHIP_ID_INVALID"}
    if not isinstance(replacement_image, (bytes, bytearray)) or not replacement_image:
        return {"status": "FAIL_CLOSED", "reason": "REPLACEMENT_IMAGE_INVALID"}

    try:
        with zipfile.ZipFile(src, "r") as zin:
            infos = zin.infolist()
            original = {i.filename: zin.read(i.filename) for i in infos}
    except Exception as exc:
        return {"status": "FAIL_CLOSED", "reason": "INVALID_ZIP_PACKAGE", "error": type(exc).__name__}

    if source_part not in original:
        return {"status": "FAIL_CLOSED", "reason": "SOURCE_PART_MISSING"}

    rels_part = _rels_name(source_part)
    if rels_part not in original:
        return {"status": "FAIL_CLOSED", "reason": "RELATIONSHIP_PART_MISSING"}

    try:
        root = ET.fromstring(original[rels_part])
    except Exception as exc:
        return {"status": "FAIL_CLOSED", "reason": "RELATIONSHIP_XML_INVALID", "error": type(exc).__name__}

    matches = []
    for rel in root.findall(f"{{{REL_NS}}}Relationship"):
        if rel.get("Id") == relationship_id:
            matches.append(rel)
    if len(matches) != 1:
        return {
            "status": "FAIL_CLOSED",
            "reason": "RELATIONSHIP_ID_NOT_UNIQUE",
            "match_count": len(matches),
        }

    try:
        source_root = ET.fromstring(original[source_part])
    except Exception as exc:
        return {"status": "FAIL_CLOSED", "reason": "SOURCE_PART_XML_INVALID", "error": type(exc).__name__}
    reference_count = 0
    for node in source_root.iter():
        for key, value in node.attrib.items():
            if key.startswith("{%s}" % OFFICE_REL_NS) and value == relationship_id:
                reference_count += 1
    if reference_count == 0:
        return {"status": "FAIL_CLOSED", "reason": "RELATIONSHIP_ID_NOT_REFERENCED_BY_SOURCE_PART"}

    rel = matches[0]
    if rel.get("Type") != IMAGE_REL:
        return {"status": "FAIL_CLOSED", "reason": "RELATIONSHIP_NOT_IMAGE"}
    if rel.get("TargetMode") == "External":
        return {"status": "FAIL_CLOSED", "reason": "EXTERNAL_IMAGE_RELATIONSHIP_FORBIDDEN"}

    target = _resolve_target(source_part, rel.get("Target") or "")
    if target is None:
        return {"status": "FAIL_CLOSED", "reason": "RELATIONSHIP_TARGET_INVALID"}
    if not target.startswith("word/media/"):
        return {"status": "FAIL_CLOSED", "reason": "IMAGE_TARGET_OUTSIDE_WORD_MEDIA", "target": target}
    if target not in original:
        return {"status": "FAIL_CLOSED", "reason": "IMAGE_TARGET_MISSING", "target": target}

    # Preserve extension/content-type contract. We do not silently change media
    # type because [Content_Types].xml and downstream consumers may depend on it.
    ext = "." + target.rsplit(".", 1)[-1].lower() if "." in target.rsplit("/", 1)[-1] else ""
    known = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff"}
    if ext not in known:
        return {"status": "FAIL_CLOSED", "reason": "UNSUPPORTED_IMAGE_EXTENSION", "extension": ext}

    replacement = bytes(replacement_image)
    signatures = {
        ".png": lambda b: b.startswith(b"\x89PNG\r\n\x1a\n"),
        ".jpg": lambda b: b.startswith(b"\xff\xd8\xff"),
        ".jpeg": lambda b: b.startswith(b"\xff\xd8\xff"),
        ".gif": lambda b: b.startswith((b"GIF87a", b"GIF89a")),
        ".bmp": lambda b: b.startswith(b"BM"),
        ".tif": lambda b: b.startswith((b"II*\x00", b"MM\x00*")),
        ".tiff": lambda b: b.startswith((b"II*\x00", b"MM\x00*")),
    }
    if not signatures[ext](replacement):
        return {"status": "FAIL_CLOSED", "reason": "REPLACEMENT_IMAGE_SIGNATURE_MISMATCH", "extension": ext}
    if replacement == original[target]:
        return {"status": "FAIL_CLOSED", "reason": "REPLACEMENT_IDENTICAL_TO_ORIGINAL"}

    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(src, "r") as zin, zipfile.ZipFile(dst, "w") as zout:
            for info in zin.infolist():
                data = replacement if info.filename == target else zin.read(info.filename)
                zout.writestr(info, data)
    except Exception as exc:
        dst.unlink(missing_ok=True)
        return {"status": "FAIL_CLOSED", "reason": "WRITE_FAILED", "error": type(exc).__name__}

    try:
        with zipfile.ZipFile(dst, "r") as zout:
            after = {i.filename: zout.read(i.filename) for i in zout.infolist()}
    except Exception as exc:
        dst.unlink(missing_ok=True)
        return {"status": "FAIL_CLOSED", "reason": "OUTPUT_PACKAGE_INVALID", "error": type(exc).__name__}

    if set(after) != set(original):
        dst.unlink(missing_ok=True)
        return {"status": "FAIL_CLOSED", "reason": "PACKAGE_MEMBER_SET_CHANGED"}

    changed = [n for n in sorted(original) if _sha(original[n]) != _sha(after[n])]
    if changed != [target]:
        dst.unlink(missing_ok=True)
        return {"status": "FAIL_CLOSED", "reason": "UNRELATED_PACKAGE_MEMBER_MUTATED", "changed_members": changed}

    # Re-parse untouched structural parts to prove package structure remains readable.
    try:
        ET.fromstring(after[source_part])
        ET.fromstring(after[rels_part])
        if "[Content_Types].xml" in after:
            ET.fromstring(after["[Content_Types].xml"])
    except Exception as exc:
        dst.unlink(missing_ok=True)
        return {"status": "FAIL_CLOSED", "reason": "ROUNDTRIP_STRUCTURAL_XML_INVALID", "error": type(exc).__name__}

    return {
        "status": "PASS",
        "output_path": str(dst),
        "source_part": source_part,
        "relationship_id": relationship_id,
        "relationship_reference_count": reference_count,
        "media_part": target,
        "changed_members": changed,
        "preserved_member_count": len(original) - 1,
        "layout_xml_preserved_byte_identical": True,
        "relationship_xml_preserved_byte_identical": True,
        "content_types_preserved_byte_identical": "[Content_Types].xml" in original,
        "scope": "EXACT_EXISTING_DOCX_IMAGE_PAYLOAD_REPLACEMENT_BY_EXPLICIT_WORD_RELATIONSHIP_ID",
        "semantic_authority": False,
        "terminal_authority": False,
    }
