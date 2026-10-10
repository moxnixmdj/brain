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
            defects.append({"id": "PPTX_NO_SLIDES", "severity": "HARD", "evidence": {}})

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
            "pass": not defects,
            "errors": [],
            "hard_defects": defects,
            "measurements": measurements,
        }
    except (OSError, ValueError) as exc:
        return {
            "path": str(p),
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

    required_checks = bundle.get("required_checks")
    if (
        not isinstance(required_checks, Sequence)
        or isinstance(required_checks, (str, bytes))
        or not required_checks
        or any(not isinstance(x, str) or x not in CHECK_IDS for x in required_checks)
        or len(set(required_checks)) != len(required_checks)
    ):
        return _fail("REQUIRED_CHECKS_INVALID_OR_EMPTY")
    required_check_set = set(required_checks)

    constraints = bundle.get("constraints", {})
    if not isinstance(constraints, Mapping):
        return _fail("CONSTRAINTS_NOT_OBJECT")
    allowed_constraint_keys = {"exact_file_count", "allowed_suffixes"}
    extra = set(constraints) - allowed_constraint_keys
    if extra:
        return _fail("UNKNOWN_CONSTRAINT:" + ",".join(sorted(extra)))

    normalized = [str(Path(x)) for x in paths]
    if len(set(normalized)) != len(normalized):
        return _fail("ARTIFACT_PATH_DUPLICATE")
    rows = [inspect_artifact(x) for x in normalized]

    observed_conditions = [
        {"path": row["path"], **d}
        for row in rows
        for d in row.get("hard_defects", [])
    ]
    hard_defects = [
        row for row in observed_conditions if row.get("id") in required_check_set
    ]
    errors = [
        err
        for row in rows
        for err in row.get("errors", [])
    ]

    exact_count = constraints.get("exact_file_count")
    if exact_count is not None:
        if not isinstance(exact_count, int) or isinstance(exact_count, bool) or exact_count < 1:
            errors.append("EXACT_FILE_COUNT_INVALID")
        elif len(rows) != exact_count:
            hard_defects.append({
                "path": None,
                "id": "EXPLICIT_FILE_COUNT_MISMATCH",
                "severity": "HARD",
                "evidence": {"observed": len(rows), "expected": exact_count},
            })

    allowed = constraints.get("allowed_suffixes")
    if allowed is not None:
        if (
            not isinstance(allowed, Sequence)
            or isinstance(allowed, (str, bytes))
            or not allowed
            or any(not isinstance(x, str) or not x.startswith(".") for x in allowed)
        ):
            errors.append("ALLOWED_SUFFIXES_INVALID")
        else:
            aset = {x.lower() for x in allowed}
            for row in rows:
                if row.get("suffix") not in aset:
                    hard_defects.append({
                        "path": row["path"],
                        "id": "EXPLICIT_FORMAT_MISMATCH",
                        "severity": "HARD",
                        "evidence": {"observed": row.get("suffix"), "allowed": sorted(aset)},
                    })

    passed = not errors and not hard_defects and all(row.get("pass") is True for row in rows)
    return {
        "schema": SCHEMA,
        "status": (
            "PASS__NO_CHECKED_HARD_DEFECT_FOUND"
            if passed
            else "FAIL_CLOSED__HARD_DEFECT_OR_INSPECTION_FAILURE"
        ),
        "pass": passed,
        "checked_artifacts": rows,
        "errors": sorted(set(errors)),
        "hard_defect_count": len(hard_defects),
        "hard_defects": hard_defects,
        "required_checks": sorted(required_check_set),
        "observed_nonrequired_conditions": [
            row for row in observed_conditions if row.get("id") not in required_check_set
        ],
        "checked_scope": sorted(CHECK_IDS),
        "quality_authority": False,
        "target_preference_authority": False,
        "style_adequacy_proved": False,
        "source_or_policy_authority_required_for_check_selection": True,
        "acceptance_credit_delta": 0,
        "terminal_credit_delta": 0,
    }
