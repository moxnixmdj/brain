"""Fail-closed OOXML/OPC package integrity validation.

This validates package mechanics after an exact low-level transaction. It does not infer
high-level edit intent and does not claim visual or semantic correctness.

Checks:
- ZIP/package readability and duplicate/path-traversal member names
- [Content_Types].xml coverage and duplicate definitions
- XML well-formedness for XML/relationship parts
- relationship-id uniqueness
- internal relationship target resolution and existence
- external relationships are explicit and excluded from local-target existence checks
"""
from __future__ import annotations

from pathlib import Path
from posixpath import dirname, join, normpath
import xml.etree.ElementTree as ET
import zipfile

CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
REL_CONTENT_TYPE = "application/vnd.openxmlformats-package.relationships+xml"


def _fail(reason: str, **extra):
    return {"status": "FAIL_CLOSED", "reason": reason, **extra}


def _source_part_for_rels(rels_part: str) -> str | None:
    if rels_part == "_rels/.rels":
        return ""
    marker = "/_rels/"
    if marker not in rels_part or not rels_part.endswith(".rels"):
        return None
    prefix, tail = rels_part.split(marker, 1)
    if not tail.endswith(".rels"):
        return None
    source_name = tail[:-5]
    if not source_name:
        return None
    return f"{prefix}/{source_name}" if prefix else source_name


def _resolve_internal_target(source_part: str, target: str) -> str | None:
    if not isinstance(target, str) or not target or target.startswith("/") or "://" in target:
        return None
    base = dirname(source_part) if source_part else ""
    resolved = normpath(join(base, target))
    if resolved in ("", ".", "..") or resolved.startswith("../"):
        return None
    return resolved


def validate_ooxml_package(path: str | Path) -> dict:
    src = Path(path)
    if not src.is_file():
        return _fail("INPUT_MISSING")

    try:
        with zipfile.ZipFile(src, "r") as zf:
            infos = zf.infolist()
            names = [i.filename for i in infos if not i.is_dir()]
            if len(names) != len(set(names)):
                return _fail("DUPLICATE_ZIP_MEMBER")
            for name in names:
                if name.startswith("/") or name in ("", ".", "..") or normpath(name).startswith("../"):
                    return _fail("INVALID_MEMBER_PATH", member=name)
            members = {name: zf.read(name) for name in names}
    except Exception as exc:
        return _fail("INVALID_ZIP_PACKAGE", error=type(exc).__name__)

    if "[Content_Types].xml" not in members:
        return _fail("CONTENT_TYPES_MISSING")

    try:
        ct_root = ET.fromstring(members["[Content_Types].xml"])
    except Exception as exc:
        return _fail("CONTENT_TYPES_XML_INVALID", error=type(exc).__name__)

    defaults: dict[str, str] = {}
    overrides: dict[str, str] = {}
    for node in ct_root:
        tag = node.tag.rsplit("}", 1)[-1]
        if tag == "Default":
            ext = (node.get("Extension") or "").lower()
            ctype = node.get("ContentType") or ""
            if not ext or not ctype:
                return _fail("CONTENT_TYPE_DEFAULT_INVALID")
            if ext in defaults and defaults[ext] != ctype:
                return _fail("CONTENT_TYPE_DEFAULT_CONFLICT", extension=ext)
            defaults[ext] = ctype
        elif tag == "Override":
            part = node.get("PartName") or ""
            ctype = node.get("ContentType") or ""
            if not part.startswith("/") or len(part) == 1 or not ctype:
                return _fail("CONTENT_TYPE_OVERRIDE_INVALID")
            normalized = part[1:]
            if normalized in overrides and overrides[normalized] != ctype:
                return _fail("CONTENT_TYPE_OVERRIDE_CONFLICT", part=normalized)
            overrides[normalized] = ctype

    missing_content_types = []
    xml_parts_checked = 0
    relationship_parts_checked = 0
    internal_relationships_checked = 0
    external_relationships_seen = 0

    for name, payload in members.items():
        if name == "[Content_Types].xml":
            continue
        ext = name.rsplit(".", 1)[-1].lower() if "." in name.rsplit("/", 1)[-1] else ""
        ctype = overrides.get(name) or defaults.get(ext)
        if not ctype:
            missing_content_types.append(name)

        is_xml = ext in {"xml", "rels"}
        if is_xml:
            try:
                root = ET.fromstring(payload)
            except Exception as exc:
                return _fail("XML_PART_INVALID", part=name, error=type(exc).__name__)
            xml_parts_checked += 1

        if name.endswith(".rels"):
            relationship_parts_checked += 1
            source_part = _source_part_for_rels(name)
            if source_part is None:
                return _fail("RELATIONSHIP_PART_PATH_INVALID", part=name)

            rel_ids: set[str] = set()
            for rel in root.findall(f"{{{REL_NS}}}Relationship"):
                rid = rel.get("Id") or ""
                target = rel.get("Target") or ""
                if not rid or rid in rel_ids:
                    return _fail("RELATIONSHIP_ID_MISSING_OR_DUPLICATE", part=name, relationship_id=rid)
                rel_ids.add(rid)

                if rel.get("TargetMode") == "External":
                    external_relationships_seen += 1
                    continue

                resolved = _resolve_internal_target(source_part, target)
                if resolved is None:
                    return _fail("RELATIONSHIP_TARGET_INVALID", part=name, relationship_id=rid, target=target)
                if resolved not in members:
                    return _fail(
                        "RELATIONSHIP_TARGET_MISSING",
                        part=name,
                        relationship_id=rid,
                        target=resolved,
                    )
                internal_relationships_checked += 1

    if missing_content_types:
        return _fail("CONTENT_TYPE_COVERAGE_MISSING", parts=sorted(missing_content_types))

    return {
        "status": "PASS",
        "member_count": len(members),
        "xml_parts_checked": xml_parts_checked,
        "relationship_parts_checked": relationship_parts_checked,
        "internal_relationships_checked": internal_relationships_checked,
        "external_relationships_seen": external_relationships_seen,
        "content_type_defaults": len(defaults),
        "content_type_overrides": len(overrides),
        "terminal_authority": False,
        "scope": "OOXML_OPC_PACKAGE_MECHANICAL_INTEGRITY_ONLY",
    }
