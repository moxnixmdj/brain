"""Bounded byte-derived hard-defect preflight for professional OOXML artifacts.

This gate is intentionally narrower than "professional quality". It rejects only
defects that can be established from exact artifact bytes under explicit rules.
A PASS means "no checked hard defect was found"; it does not mean aesthetically
excellent, target-preferred, rubric-complete, or benchmark-adequate.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping, Sequence
import re
import zipfile
import xml.etree.ElementTree as ET

SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_ARTIFACT_HARD_DEFECT_PREFLIGHT_V1"
SUPPORTED_SUFFIXES = {".docx", ".xlsx", ".pptx"}
CHECK_IDS = {
    "DOCX_NONEMPTY_CONTENT",
    "XLSX_HAS_VISIBLE_WORKSHEET",
    "XLSX_NO_ERROR_CELLS",
    "XLSX_NO_ZERO_WIDTH_COLUMNS",
    "XLSX_NONEMPTY_CONTENT",
    "PPTX_HAS_SLIDES",
    "PPTX_NO_TEXT_OBJECT_OUTSIDE_SLIDE_BOUNDS",
}
PROFILES = {
    "BRAIN_PROFESSIONAL_OOXML_SANITY_V1": {
        "authority_class": "BRAIN_OWNED_GENERAL_QA_POLICY",
        "public_target_example_only": False,
        "checks_by_suffix": {
            ".docx": ["DOCX_NONEMPTY_CONTENT"],
            ".xlsx": [
                "XLSX_HAS_VISIBLE_WORKSHEET",
                "XLSX_NO_ERROR_CELLS",
                "XLSX_NO_ZERO_WIDTH_COLUMNS",
                "XLSX_NONEMPTY_CONTENT",
            ],
            ".pptx": [
                "PPTX_HAS_SLIDES",
                "PPTX_NO_TEXT_OBJECT_OUTSIDE_SLIDE_BOUNDS",
            ],
        },
        "constraints": {"allowed_suffixes": [".docx", ".xlsx", ".pptx"]},
    },
    "AA_BRIEFCASE_LITE_W1_T2_XLSX_HARD_SUBGATE_V1": {
        "authority_class": "PINNED_PUBLIC_AA_BRIEFCASE_LITE_EXAMPLE",
        "public_target_example_only": True,
        "source_commit": "313e44ef0fdc91c8462fc2b4a3f18a3e4877d7f7",
        "source_path": "canonical/evidence/AA_BRIEFCASE_LITE_PRESENTATION_PAIRWISE_CONTRACT_MANIFEST_20261007_V1.json",
        "source_git_blob_sha": "42920315a5ecb9a1c8fe96a1a441dfd4a2f3b4e8",
        "source_check_id": "W1-T2-P-01",
        "checks_by_suffix": {
            ".xlsx": [
                "XLSX_NO_ERROR_CELLS",
                "XLSX_NO_ZERO_WIDTH_COLUMNS",
            ],
        },
        "constraints": {"exact_file_count": 1, "allowed_suffixes": [".xlsx"]},
    },
    "AA_BRIEFCASE_LITE_W1_T3_PPTX_HARD_SUBGATE_V1": {
        "authority_class": "PINNED_PUBLIC_AA_BRIEFCASE_LITE_EXAMPLE",
        "public_target_example_only": True,
        "source_commit": "313e44ef0fdc91c8462fc2b4a3f18a3e4877d7f7",
        "source_path": "canonical/evidence/AA_BRIEFCASE_LITE_PRESENTATION_PAIRWISE_CONTRACT_MANIFEST_20261007_V1.json",
        "source_git_blob_sha": "42920315a5ecb9a1c8fe96a1a441dfd4a2f3b4e8",
        "source_check_id": "W1-T3-P-01",
        "checks_by_suffix": {
            ".pptx": [
                "PPTX_NO_TEXT_OBJECT_OUTSIDE_SLIDE_BOUNDS",
            ],
        },
        "constraints": {"exact_file_count": 1, "allowed_suffixes": [".pptx"]},
    },
}

ERROR_TOKEN_RE = re.compile(r"^#(?:REF!|DIV/0!|VALUE!|NAME\?|N/A|NUM!|NULL!|SPILL!|CALC!|GETTING_DATA)$", re.I)

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
}

def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "errors": sorted(set(errors)),
        "checked_artifacts": [],
        "hard_defect_count": 0,
        "hard_defects": [],
        "quality_authority": False,
        "target_preference_authority": False,
        "acceptance_credit_delta": 0,
        "terminal_credit_delta": 0,
    }

def _xml(zf: zipfile.ZipFile, name: str) -> ET.Element:
    try:
        return ET.fromstring(zf.read(name))
    except KeyError as exc:
        raise ValueError("REQUIRED_OOXML_MEMBER_MISSING:" + name) from exc
    except ET.ParseError as exc:
        raise ValueError("OOXML_XML_INVALID:" + name) from exc

def _zip_members(path: Path) -> tuple[zipfile.ZipFile, set[str]]:
    if not path.is_file() or path.stat().st_size <= 0:
        raise ValueError("ARTIFACT_MISSING_OR_EMPTY")
    try:
        zf = zipfile.ZipFile(path, "r")
        bad = zf.testzip()
        if bad is not None:
            zf.close()
            raise ValueError("ZIP_CRC_FAILURE:" + bad)
        names = set(zf.namelist())
        if "[Content_Types].xml" not in names:
            zf.close()
            raise ValueError("OOXML_CONTENT_TYPES_MISSING")
        return zf, names
    except zipfile.BadZipFile as exc:
        raise ValueError("OOXML_PACKAGE_INVALID") from exc

def _docx(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    defects: list[dict[str, Any]] = []
    zf, names = _zip_members(path)
    try:
        root = _xml(zf, "word/document.xml")
        texts = [(x.text or "") for x in root.findall(".//w:t", NS)]
        visible_text = "".join(texts).strip()
        has_drawing = bool(root.findall(".//w:drawing", NS))
        has_pict = bool(root.findall(".//w:pict", NS))
        media = [n for n in names if n.startswith("word/media/") and not n.endswith("/")]
        if not visible_text and not has_drawing and not has_pict and not media:
            defects.append({
                "id": "DOCX_NONEMPTY_CONTENT",
                "severity": "HARD",
                "evidence": {"text_chars": 0, "media_count": 0},
            })
        return defects, {
            "format": "docx",
            "text_char_count": len(visible_text),
            "media_count": len(media),
            "package_member_count": len(names),
        }
    finally:
        zf.close()

def _xlsx(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    defects: list[dict[str, Any]] = []
    zf, names = _zip_members(path)
    try:
        wb = _xml(zf, "xl/workbook.xml")
        sheets = wb.findall(".//s:sheets/s:sheet", NS)
        if not sheets:
            defects.append({"id": "XLSX_HAS_VISIBLE_WORKSHEET", "severity": "HARD", "evidence": {"reason": "NO_WORKSHEETS"}})
        visible = [x for x in sheets if x.attrib.get("state", "visible") == "visible"]
        if sheets and not visible:
            defects.append({
                "id": "XLSX_HAS_VISIBLE_WORKSHEET",
                "severity": "HARD",
                "evidence": {"sheet_count": len(sheets)},
            })

        shared: list[str] = []
        if "xl/sharedStrings.xml" in names:
            ss = _xml(zf, "xl/sharedStrings.xml")
            for si in ss.findall(".//s:si", NS):
                shared.append("".join((t.text or "") for t in si.findall(".//s:t", NS)))

        error_cells = []
        zero_width_cols = []
        nonempty_cells = 0
        worksheet_names = sorted(
            n for n in names
            if n.startswith("xl/worksheets/sheet") and n.endswith(".xml")
        )
        for name in worksheet_names:
            root = _xml(zf, name)
            for col in root.findall(".//s:cols/s:col", NS):
                hidden = col.attrib.get("hidden") == "1"
                width_raw = col.attrib.get("width")
                width_zero = False
                if width_raw is not None:
                    try:
                        width_zero = float(width_raw) <= 0.0
                    except ValueError:
                        width_zero = True
                if width_zero:
                    zero_width_cols.append({
                        "sheet_xml": name,
                        "min": col.attrib.get("min"),
                        "max": col.attrib.get("max"),
                        "hidden": hidden,
                        "width": width_raw,
                    })
            for cell in root.findall(".//s:c", NS):
                ref = cell.attrib.get("r")
                ctype = cell.attrib.get("t")
                v = cell.find("s:v", NS)
                raw = "" if v is None or v.text is None else v.text
                if raw:
                    nonempty_cells += 1
                text = raw
                if ctype == "s" and raw.isdigit():
                    idx = int(raw)
                    if 0 <= idx < len(shared):
                        text = shared[idx]
                elif ctype == "inlineStr":
                    text = "".join((t.text or "") for t in cell.findall(".//s:t", NS))
                    if text:
                        nonempty_cells += 1
                if ctype == "e" or ERROR_TOKEN_RE.fullmatch(text.strip() or ""):
                    error_cells.append({"sheet_xml": name, "cell": ref, "value": text})

        if error_cells:
            defects.append({
                "id": "XLSX_NO_ERROR_CELLS",
                "severity": "HARD",
                "evidence": {"count": len(error_cells), "examples": error_cells[:20]},
            })
        if zero_width_cols:
            defects.append({
                "id": "XLSX_NO_ZERO_WIDTH_COLUMNS",
                "severity": "HARD",
                "evidence": {"count": len(zero_width_cols), "examples": zero_width_cols[:20]},
            })
        if sheets and nonempty_cells == 0:
            defects.append({
                "id": "XLSX_NONEMPTY_CONTENT",
                "severity": "HARD",
                "evidence": {"sheet_count": len(sheets)},
            })
        return defects, {
            "format": "xlsx",
            "sheet_count": len(sheets),
            "visible_sheet_count": len(visible),
            "worksheet_xml_count": len(worksheet_names),
            "nonempty_cell_count": nonempty_cells,
            "error_cell_count": len(error_cells),
            "hidden_or_zero_width_column_count": len(zero_width_cols),
        }
    finally:
        zf.close()

def _pptx(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    defects: list[dict[str, Any]] = []
    zf, names = _zip_members(path)
    try:
        pres = _xml(zf, "ppt/presentation.xml")
        sldsz = pres.find("p:sldSz", NS)
        if sldsz is None:
            raise ValueError("PPTX_SLIDE_SIZE_MISSING")
        try:
            slide_cx = int(sldsz.attrib["cx"])
            slide_cy = int(sldsz.attrib["cy"])
        except Exception as exc:
            raise ValueError("PPTX_SLIDE_SIZE_INVALID") from exc
        slide_names = sorted(
            n for n in names
            if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)
        )
        if not slide_names:
            defects.append({"id": "PPTX_HAS_SLIDES", "severity": "HARD", "evidence": {}})

        out_of_bounds = []
        effectively_blank = []
        for name in slide_names:
            root = _xml(zf, name)
            sp_tree = root.find(".//p:spTree", NS)
            visible_payload = False
            if sp_tree is None:
                effectively_blank.append(name)
                continue
            for child in list(sp_tree):
                tag = child.tag.rsplit("}", 1)[-1]
                if tag in {"nvGrpSpPr", "grpSpPr"}:
                    continue
                texts = [(t.text or "") for t in child.findall(".//a:t", NS)]
                if "".join(texts).strip():
                    visible_payload = True
                if child.findall(".//p:pic", NS) or child.findall(".//a:blip", NS):
                    visible_payload = True

                xfrm = child.find("./p:spPr/a:xfrm", NS)
                if xfrm is None:
                    xfrm = child.find("./p:xfrm", NS)
                if xfrm is None:
                    xfrm = child.find("./a:xfrm", NS)
                if xfrm is None:
                    continue
                off = xfrm.find("a:off", NS)
                ext = xfrm.find("a:ext", NS)
                if off is None or ext is None:
                    continue
                try:
                    x = int(off.attrib.get("x", "0"))
                    y = int(off.attrib.get("y", "0"))
                    cx = int(ext.attrib.get("cx", "0"))
                    cy = int(ext.attrib.get("cy", "0"))
                except ValueError:
                    out_of_bounds.append({"slide_xml": name, "reason": "NONINTEGER_GEOMETRY"})
                    continue
                contains_text = bool("".join(texts).strip())
                if contains_text and (x < 0 or y < 0 or cx < 0 or cy < 0 or x + cx > slide_cx or y + cy > slide_cy):
                    out_of_bounds.append({
                        "slide_xml": name,
                        "shape_tag": tag,
                        "x": x, "y": y, "cx": cx, "cy": cy,
                        "slide_cx": slide_cx, "slide_cy": slide_cy,
                    })
            if not visible_payload:
                effectively_blank.append(name)

        if out_of_bounds:
            defects.append({
                "id": "PPTX_NO_TEXT_OBJECT_OUTSIDE_SLIDE_BOUNDS",
                "severity": "HARD",
                "evidence": {"count": len(out_of_bounds), "examples": out_of_bounds[:20]},
            })
        return defects, {
            "format": "pptx",
            "slide_count": len(slide_names),
            "out_of_bounds_top_level_object_count": len(out_of_bounds),
            "effectively_blank_slide_count": len(effectively_blank),
            "slide_size_emu": [slide_cx, slide_cy],
        }
    finally:
        zf.close()

def inspect_artifact(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        return {
            "path": str(p),
            "pass": False,
            "errors": ["UNSUPPORTED_SUFFIX:" + suffix],
            "hard_defects": [],
        }
    try:
        digest = sha256(p.read_bytes()).hexdigest()
        if suffix == ".docx":
            defects, measurements = _docx(p)
        elif suffix == ".xlsx":
            defects, measurements = _xlsx(p)
        else:
            defects, measurements = _pptx(p)
        return {
            "path": str(p),
            "artifact_sha256": digest,
            "suffix": suffix,
            "pass": True,
            "errors": [],
            "observed_conditions": defects,
            "hard_defects": defects,
            "measurements": measurements,
        }
    except (OSError, ValueError) as exc:
        return {
            "path": str(p),
            "suffix": suffix,
            "pass": False,
            "errors": [type(exc).__name__ + ":" + str(exc)],
            "hard_defects": [],
        }

def verify(bundle: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(bundle, Mapping):
        return _fail("BUNDLE_NOT_OBJECT")
    paths = bundle.get("artifact_paths")
    if (
        not isinstance(paths, Sequence)
        or isinstance(paths, (str, bytes))
        or not paths
        or any(not isinstance(x, str) or not x.strip() for x in paths)
    ):
        return _fail("ARTIFACT_PATHS_INVALID")

    profile_id = bundle.get("profile_id")
    if not isinstance(profile_id, str) or profile_id not in PROFILES:
        return _fail("PROFILE_ID_UNKNOWN_OR_MISSING")
    if set(bundle) - {"artifact_paths", "profile_id"}:
        return _fail("UNSUPPORTED_CALLER_FIELDS")
    profile = PROFILES[profile_id]
    constraints = dict(profile.get("constraints") or {})
    checks_by_suffix = dict(profile.get("checks_by_suffix") or {})

    normalized = [str(Path(x)) for x in paths]
    if len(set(normalized)) != len(normalized):
        return _fail("ARTIFACT_PATH_DUPLICATE")
    rows = [inspect_artifact(x) for x in normalized]

    required_by_path: dict[str, set[str]] = {}
    for row in rows:
        required_by_path[row["path"]] = set(checks_by_suffix.get(row.get("suffix"), []))

    observed_conditions = [
        {"path": row["path"], **d}
        for row in rows
        for d in row.get("hard_defects", [])
    ]
    hard_defects = [
        row for row in observed_conditions
        if row.get("id") in required_by_path.get(row.get("path"), set())
    ]
    errors = [
        err
        for row in rows
        for err in row.get("errors", [])
    ]

    exact_count = constraints.get("exact_file_count")
    if exact_count is not None and len(rows) != int(exact_count):
        hard_defects.append({
            "path": None,
            "id": "EXPLICIT_FILE_COUNT_MISMATCH",
            "severity": "HARD",
            "evidence": {"observed": len(rows), "expected": int(exact_count)},
        })

    allowed = {x.lower() for x in constraints.get("allowed_suffixes", [])}
    if allowed:
        for row in rows:
            if row.get("suffix") not in allowed:
                hard_defects.append({
                    "path": row["path"],
                    "id": "EXPLICIT_FORMAT_MISMATCH",
                    "severity": "HARD",
                    "evidence": {"observed": row.get("suffix"), "allowed": sorted(allowed)},
                })

    passed = not errors and not hard_defects and all(row.get("pass") is True for row in rows)
    required_checks = sorted({
        check for checks in required_by_path.values() for check in checks
    })
    return {
        "schema": SCHEMA,
        "status": (
            "PASS__NO_PROFILE_REQUIRED_HARD_DEFECT_FOUND"
            if passed
            else "FAIL_CLOSED__PROFILE_HARD_DEFECT_OR_INSPECTION_FAILURE"
        ),
        "pass": passed,
        "profile_id": profile_id,
        "profile_authority_class": profile.get("authority_class"),
        "public_target_example_only": bool(profile.get("public_target_example_only")),
        "source_commit": profile.get("source_commit"),
        "source_path": profile.get("source_path"),
        "source_git_blob_sha": profile.get("source_git_blob_sha"),
        "source_check_id": profile.get("source_check_id"),
        "checked_artifacts": rows,
        "errors": sorted(set(errors)),
        "hard_defect_count": len(hard_defects),
        "hard_defects": hard_defects,
        "required_checks": required_checks,
        "observed_nonrequired_conditions": [
            row for row in observed_conditions
            if row.get("id") not in required_by_path.get(row.get("path"), set())
        ],
        "checked_scope": sorted(CHECK_IDS),
        "quality_authority": False,
        "target_preference_authority": False,
        "style_adequacy_proved": False,
        "official_private_aa_briefcase_credit": False,
        "gdpval_owner_elo_credit": False,
        "acceptance_credit_delta": 0,
        "terminal_credit_delta": 0,
    }

