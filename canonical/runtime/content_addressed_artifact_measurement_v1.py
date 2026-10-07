from __future__ import annotations

from hashlib import sha256
import json
import pathlib
from typing import Any, Mapping, Sequence
import xml.etree.ElementTree as ET
import zipfile

SCHEMA = "PROJECT_BRAIN_CONTENT_ADDRESSED_ARTIFACT_MEASUREMENT_V1"

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
S = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

SUPPORTED_KINDS = {
    "FILE_BASENAME",
    "FILE_SUFFIX",
    "FILE_SIZE_BYTES",
    "OOXML_MEMBER_EXISTS",
    "XLSX_SHEET_EXISTS",
    "XLSX_SHEET_COUNT",
    "DOCX_TEXT_CONTAINS",
    "DOCX_PARAGRAPH_COUNT",
    "DOCX_TABLE_COUNT",
    "PPTX_SLIDE_COUNT",
    "PPTX_TEXT_CONTAINS",
}


class ArtifactMeasurementError(ValueError):
    pass


def _canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha_bytes(data: bytes) -> str:
    return sha256(data).hexdigest()


def _safe(root: pathlib.Path, raw: str) -> pathlib.Path:
    root = root.resolve()
    if not isinstance(raw, str) or not raw:
        raise ArtifactMeasurementError("ARTIFACT_PATH_REQUIRED")
    path = (root / raw).resolve()
    if path == root or root not in path.parents:
        raise ArtifactMeasurementError("ARTIFACT_PATH_OUTSIDE_ROOT")
    if not path.is_file():
        raise ArtifactMeasurementError("ARTIFACT_FILE_MISSING")
    return path


def _typed(value: Any) -> tuple[str, Any]:
    if isinstance(value, bool):
        return "boolean", value
    if isinstance(value, int):
        return "integer", value
    if isinstance(value, float):
        return "number", value
    if isinstance(value, str):
        return "enum", value
    raise ArtifactMeasurementError("MEASUREMENT_VALUE_TYPE_UNSUPPORTED")


def _zip(path: pathlib.Path) -> zipfile.ZipFile:
    try:
        return zipfile.ZipFile(path)
    except (zipfile.BadZipFile, OSError) as exc:
        raise ArtifactMeasurementError("OOXML_ZIP_INVALID:" + type(exc).__name__) from exc


def _xml(zf: zipfile.ZipFile, name: str) -> ET.Element:
    if name not in set(zf.namelist()):
        raise ArtifactMeasurementError("OOXML_MEMBER_MISSING:" + name)
    try:
        return ET.fromstring(zf.read(name))
    except ET.ParseError as exc:
        raise ArtifactMeasurementError("OOXML_XML_INVALID:" + name) from exc


def _xlsx_sheet_names(path: pathlib.Path) -> list[str]:
    with _zip(path) as zf:
        root = _xml(zf, "xl/workbook.xml")
        names = []
        for node in root.iter(S + "sheet"):
            name = node.attrib.get("name")
            if not isinstance(name, str) or not name:
                raise ArtifactMeasurementError("XLSX_SHEET_NAME_INVALID")
            names.append(name)
        if len(names) != len(set(names)):
            raise ArtifactMeasurementError("XLSX_DUPLICATE_SHEET_NAME")
        return names


def _docx_structure(path: pathlib.Path) -> tuple[str, int, int]:
    with _zip(path) as zf:
        root = _xml(zf, "word/document.xml")
        body = root.find(W + "body")
        if body is None:
            raise ArtifactMeasurementError("DOCX_BODY_MISSING")
        paragraphs = 0
        tables = 0
        text_parts: list[str] = []
        for child in list(body):
            if child.tag == W + "p":
                paragraphs += 1
            elif child.tag == W + "tbl":
                tables += 1
            for t in child.iter(W + "t"):
                if t.text:
                    text_parts.append(t.text)
        return "\n".join(text_parts), paragraphs, tables


def _pptx_structure(path: pathlib.Path) -> tuple[str, int]:
    with _zip(path) as zf:
        names = sorted(
            name
            for name in zf.namelist()
            if name.startswith("ppt/slides/slide")
            and name.endswith(".xml")
            and name[len("ppt/slides/slide"):-4].isdigit()
        )
        text_parts: list[str] = []
        for name in names:
            root = _xml(zf, name)
            for t in root.iter(A + "t"):
                if t.text:
                    text_parts.append(t.text)
        return "\n".join(text_parts), len(names)


def _measure_one(path: pathlib.Path, req: Mapping[str, Any]) -> tuple[str, Any, dict[str, Any]]:
    kind = str(req.get("kind") or "")
    if kind not in SUPPORTED_KINDS:
        raise ArtifactMeasurementError("MEASUREMENT_KIND_UNSUPPORTED:" + kind)

    if kind == "FILE_BASENAME":
        value = path.name
        detail = {}
    elif kind == "FILE_SUFFIX":
        value = path.suffix.lower()
        detail = {}
    elif kind == "FILE_SIZE_BYTES":
        value = int(path.stat().st_size)
        detail = {}
    elif kind == "OOXML_MEMBER_EXISTS":
        member = req.get("member")
        if not isinstance(member, str) or not member or member.startswith("/") or ".." in pathlib.PurePosixPath(member).parts:
            raise ArtifactMeasurementError("OOXML_MEMBER_INVALID")
        with _zip(path) as zf:
            value = member in set(zf.namelist())
        detail = {"member": member}
    elif kind in {"XLSX_SHEET_EXISTS", "XLSX_SHEET_COUNT"}:
        names = _xlsx_sheet_names(path)
        if kind == "XLSX_SHEET_COUNT":
            value = len(names)
            detail = {"sheet_names": names}
        else:
            sheet_name = req.get("sheet_name")
            if not isinstance(sheet_name, str) or not sheet_name:
                raise ArtifactMeasurementError("XLSX_SHEET_NAME_REQUIRED")
            case_sensitive = bool(req.get("case_sensitive", True))
            if case_sensitive:
                value = sheet_name in names
            else:
                target = sheet_name.strip().casefold()
                value = any(x.strip().casefold() == target for x in names)
            detail = {"sheet_name": sheet_name, "case_sensitive": case_sensitive, "observed_sheet_names": names}
    elif kind in {"DOCX_TEXT_CONTAINS", "DOCX_PARAGRAPH_COUNT", "DOCX_TABLE_COUNT"}:
        text, paragraph_count, table_count = _docx_structure(path)
        if kind == "DOCX_PARAGRAPH_COUNT":
            value = paragraph_count
            detail = {}
        elif kind == "DOCX_TABLE_COUNT":
            value = table_count
            detail = {}
        else:
            needle = req.get("text")
            if not isinstance(needle, str) or not needle:
                raise ArtifactMeasurementError("DOCX_TEXT_REQUIRED")
            case_sensitive = bool(req.get("case_sensitive", True))
            value = needle in text if case_sensitive else needle.casefold() in text.casefold()
            detail = {"text_sha256": sha256(needle.encode("utf-8")).hexdigest(), "case_sensitive": case_sensitive}
    else:
        text, slide_count = _pptx_structure(path)
        if kind == "PPTX_SLIDE_COUNT":
            value = slide_count
            detail = {}
        else:
            needle = req.get("text")
            if not isinstance(needle, str) or not needle:
                raise ArtifactMeasurementError("PPTX_TEXT_REQUIRED")
            case_sensitive = bool(req.get("case_sensitive", True))
            value = needle in text if case_sensitive else needle.casefold() in text.casefold()
            detail = {"text_sha256": sha256(needle.encode("utf-8")).hexdigest(), "case_sensitive": case_sensitive}

    value_type, value = _typed(value)
    return value_type, value, detail


def measure(
    artifact_path: str,
    measurements: Sequence[Mapping[str, Any]],
    *,
    root: str | pathlib.Path,
) -> dict[str, Any]:
    try:
        root_path = pathlib.Path(root).resolve()
        path = _safe(root_path, artifact_path)
        if (
            not isinstance(measurements, Sequence)
            or isinstance(measurements, (str, bytes))
            or not measurements
        ):
            raise ArtifactMeasurementError("MEASUREMENTS_REQUIRED")

        raw = path.read_bytes()
        artifact_sha = _sha_bytes(raw)
        rows = []
        values: dict[str, Any] = {}
        types: dict[str, str] = {}
        seen: set[str] = set()

        for index, req in enumerate(measurements):
            if not isinstance(req, Mapping):
                raise ArtifactMeasurementError("MEASUREMENT_NOT_OBJECT:" + str(index))
            mid = req.get("id")
            if not isinstance(mid, str) or not mid or mid in seen:
                raise ArtifactMeasurementError("MEASUREMENT_ID_INVALID_OR_DUPLICATE:" + str(mid))
            seen.add(mid)
            value_type, value, detail = _measure_one(path, req)
            request_digest = sha256(_canon(dict(req)).encode("utf-8")).hexdigest()
            row = {
                "id": mid,
                "kind": str(req.get("kind")),
                "type": value_type,
                "value": value,
                "artifact_sha256": artifact_sha,
                "request_sha256": request_digest,
                "detail": detail,
            }
            rows.append(row)
            values[mid] = value
            types[mid] = value_type

        request_manifest_sha = sha256(
            "\n".join(row["request_sha256"] for row in rows).encode("utf-8")
        ).hexdigest()
        receipt_payload = {
            "artifact_path": str(path.relative_to(root_path)).replace("\\", "/"),
            "artifact_sha256": artifact_sha,
            "artifact_bytes": len(raw),
            "request_manifest_sha256": request_manifest_sha,
            "measurements": rows,
        }
        return {
            "schema": SCHEMA,
            "status": "MEASURED",
            **receipt_payload,
            "values": values,
            "types": types,
            "receipt_sha256": sha256(_canon(receipt_payload).encode("utf-8")).hexdigest(),
            "measurement_source": "BRAIN_OWNED_DETERMINISTIC_ARTIFACT_BYTES",
            "proposal_supplied_measurement_values": False,
            "terminal_authority": False,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": [type(exc).__name__ + ":" + str(exc)],
            "terminal_authority": False,
        }
