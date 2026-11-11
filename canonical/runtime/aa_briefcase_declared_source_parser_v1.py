from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import shutil
import subprocess
import tempfile
import zipfile
from email import policy
from email.parser import BytesParser
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Mapping
from xml.etree import ElementTree as ET

SCHEMA = "PROJECT_BRAIN_AA_BRIEFCASE_DECLARED_SOURCE_PARSER_V1"
PARSER_VERSION = "AA_SOURCE_PARSER_V1"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
MAX_SOURCE_BYTES = 64_000_000
MAX_TEXT_CHARS_PER_SOURCE = 8_000_000

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
S_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


class SourceParseError(ValueError):
    pass


def _canon(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _safe_join(root: Path, rel: str) -> Path:
    if not isinstance(rel, str) or not rel:
        raise SourceParseError("SOURCE_PATH_INVALID")
    p = (root / rel).resolve()
    r = root.resolve()
    if p == r or r not in p.parents:
        raise SourceParseError("SOURCE_PATH_ESCAPES_ROOT:" + rel)
    if p.is_symlink():
        raise SourceParseError("SOURCE_SYMLINK_FORBIDDEN:" + rel)
    return p


def _bounded_text(text: str) -> str:
    if len(text) > MAX_TEXT_CHARS_PER_SOURCE:
        raise SourceParseError("PARSED_TEXT_TOO_LARGE")
    return text


class _TextHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.parts.append(data)


def _xml_text_nodes(raw: bytes, namespace: str, local: str) -> list[str]:
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise SourceParseError("OOXML_XML_INVALID") from exc
    tag = "{" + namespace + "}" + local
    return [node.text or "" for node in root.iter(tag) if (node.text or "") != ""]


def _parse_docx(raw: bytes) -> dict[str, Any]:
    try:
        z = zipfile.ZipFile(io.BytesIO(raw))
    except Exception as exc:
        raise SourceParseError("DOCX_ZIP_INVALID") from exc
    names = sorted(
        n for n in z.namelist()
        if n.startswith("word/") and n.endswith(".xml")
        and (
            n == "word/document.xml"
            or n.startswith("word/header")
            or n.startswith("word/footer")
            or n in {"word/footnotes.xml", "word/endnotes.xml", "word/comments.xml"}
        )
    )
    if "word/document.xml" not in names:
        raise SourceParseError("DOCX_DOCUMENT_XML_MISSING")
    parts = []
    total = 0
    for name in names:
        texts = _xml_text_nodes(z.read(name), W_NS, "t")
        text = "\n".join(texts)
        total += len(text)
        parts.append({"part": name, "text": text, "text_sha256": _sha(text.encode("utf-8"))})
    _bounded_text("".join(x["text"] for x in parts))
    return {"format": "docx", "parts": parts, "text_char_count": total}


def _parse_pptx(raw: bytes) -> dict[str, Any]:
    try:
        z = zipfile.ZipFile(io.BytesIO(raw))
    except Exception as exc:
        raise SourceParseError("PPTX_ZIP_INVALID") from exc
    names = sorted(
        n for n in z.namelist()
        if n.endswith(".xml")
        and (n.startswith("ppt/slides/slide") or n.startswith("ppt/notesSlides/notesSlide"))
    )
    if not any(n.startswith("ppt/slides/slide") for n in names):
        raise SourceParseError("PPTX_SLIDES_MISSING")
    parts = []
    total = 0
    for name in names:
        texts = _xml_text_nodes(z.read(name), A_NS, "t")
        text = "\n".join(texts)
        total += len(text)
        parts.append({"part": name, "text": text, "text_sha256": _sha(text.encode("utf-8"))})
    _bounded_text("".join(x["text"] for x in parts))
    return {"format": "pptx", "parts": parts, "text_char_count": total}


def _xlsx_shared_strings(z: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in z.namelist():
        return []
    root = ET.fromstring(z.read("xl/sharedStrings.xml"))
    out = []
    ttag = "{" + S_NS + "}t"
    for si in root:
        out.append("".join((node.text or "") for node in si.iter(ttag)))
    return out


def _xlsx_sheet_map(z: zipfile.ZipFile) -> list[dict[str, str]]:
    if "xl/workbook.xml" not in z.namelist():
        raise SourceParseError("XLSX_WORKBOOK_XML_MISSING")
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rels = {}
    rel_path = "xl/_rels/workbook.xml.rels"
    if rel_path in z.namelist():
        rr = ET.fromstring(z.read(rel_path))
        for rel in rr:
            rid = rel.attrib.get("Id")
            target = rel.attrib.get("Target")
            if rid and target:
                if target.startswith("/"):
                    path = target.lstrip("/")
                elif target.startswith("xl/"):
                    path = target
                else:
                    path = "xl/" + target.lstrip("/")
                rels[rid] = str(Path(path).as_posix())
    stag = "{" + S_NS + "}sheet"
    out = []
    for sheet in wb.iter(stag):
        rid = sheet.attrib.get("{" + R_NS + "}id")
        target = rels.get(rid or "")
        if not target:
            raise SourceParseError("XLSX_SHEET_RELATION_MISSING")
        out.append({
            "name": sheet.attrib.get("name") or "",
            "state": sheet.attrib.get("state") or "visible",
            "path": target,
        })
    if not out:
        raise SourceParseError("XLSX_NO_SHEETS")
    return out


def _parse_xlsx(raw: bytes) -> dict[str, Any]:
    try:
        z = zipfile.ZipFile(io.BytesIO(raw))
    except Exception as exc:
        raise SourceParseError("XLSX_ZIP_INVALID") from exc
    shared = _xlsx_shared_strings(z)
    sheets = []
    total_cells = 0
    ctag = "{" + S_NS + "}c"
    vtag = "{" + S_NS + "}v"
    ftag = "{" + S_NS + "}f"
    ttag = "{" + S_NS + "}t"
    for meta in _xlsx_sheet_map(z):
        if meta["path"] not in z.namelist():
            raise SourceParseError("XLSX_SHEET_XML_MISSING:" + meta["path"])
        root = ET.fromstring(z.read(meta["path"]))
        cells = []
        for c in root.iter(ctag):
            ref = c.attrib.get("r") or ""
            typ = c.attrib.get("t") or ""
            formula_node = c.find(ftag)
            value_node = c.find(vtag)
            value = value_node.text if value_node is not None and value_node.text is not None else ""
            if typ == "s" and value:
                try:
                    value = shared[int(value)]
                except Exception as exc:
                    raise SourceParseError("XLSX_SHARED_STRING_INDEX_INVALID:" + ref) from exc
            elif typ == "inlineStr":
                value = "".join((node.text or "") for node in c.iter(ttag))
            formula = formula_node.text if formula_node is not None else None
            if value != "" or formula:
                cells.append({"cell": ref, "value": value, "formula": formula, "type": typ})
        total_cells += len(cells)
        sheets.append({**meta, "cells": cells})
    payload = {"format": "xlsx", "sheets": sheets, "nonempty_cell_count": total_cells}
    _bounded_text(json.dumps(payload, ensure_ascii=False))
    return payload


def _parse_csv_like(raw: bytes, delimiter: str, fmt: str) -> dict[str, Any]:
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise SourceParseError(fmt.upper() + "_NOT_UTF8") from exc
    rows = [row for row in csv.reader(io.StringIO(text), delimiter=delimiter)]
    payload = {"format": fmt, "rows": rows, "row_count": len(rows)}
    _bounded_text(json.dumps(payload, ensure_ascii=False))
    return payload


def _json_scalar_paths(value: Any, prefix: str = "$") -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if isinstance(value, dict):
        for key in sorted(value):
            out.extend(_json_scalar_paths(value[key], prefix + "." + str(key)))
    elif isinstance(value, list):
        for i, item in enumerate(value):
            out.extend(_json_scalar_paths(item, prefix + f"[{i}]"))
    else:
        out.append({"path": prefix, "value": value})
    return out


def _parse_json(raw: bytes) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8-sig"))
    except Exception as exc:
        raise SourceParseError("JSON_INVALID") from exc
    scalars = _json_scalar_paths(value)
    payload = {"format": "json", "canonical": value, "scalar_paths": scalars, "scalar_count": len(scalars)}
    _bounded_text(json.dumps(payload, ensure_ascii=False))
    return payload


def _parse_email(raw: bytes) -> dict[str, Any]:
    try:
        msg = BytesParser(policy=policy.default).parsebytes(raw)
    except Exception as exc:
        raise SourceParseError("EML_INVALID") from exc
    headers = {k: str(msg.get(k, "")) for k in ("From", "To", "Cc", "Date", "Subject", "Message-ID")}
    bodies = []
    parts = msg.walk() if msg.is_multipart() else [msg]
    for part in parts:
        if part.get_content_maintype() == "multipart":
            continue
        ctype = part.get_content_type()
        if ctype not in {"text/plain", "text/html"}:
            continue
        try:
            content = part.get_content()
        except Exception:
            payload = part.get_payload(decode=True) or b""
            content = payload.decode(part.get_content_charset() or "utf-8", "replace")
        if ctype == "text/html":
            parser = _TextHTMLParser()
            parser.feed(str(content))
            content = "\n".join(parser.parts)
        bodies.append({"content_type": ctype, "text": str(content)})
    _bounded_text("".join(x["text"] for x in bodies))
    return {"format": "eml", "headers": headers, "bodies": bodies}


def _parse_html(raw: bytes) -> dict[str, Any]:
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    parser = _TextHTMLParser()
    parser.feed(text)
    rendered = "\n".join(parser.parts)
    _bounded_text(rendered)
    return {"format": "html", "text": rendered}


def _parse_text(raw: bytes, fmt: str) -> dict[str, Any]:
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise SourceParseError(fmt.upper() + "_NOT_UTF8") from exc
    return {"format": fmt, "text": _bounded_text(text)}


def _parse_pdf(raw: bytes) -> dict[str, Any]:
    try:
        import fitz  # type: ignore
    except Exception:
        fitz = None
    if fitz is not None:
        try:
            doc = fitz.open(stream=raw, filetype="pdf")
            pages = [{"page": i + 1, "text": page.get_text("text")} for i, page in enumerate(doc)]
            doc.close()
        except Exception as exc:
            raise SourceParseError("PDF_PYMUPDF_PARSE_FAILED") from exc
        _bounded_text("".join(x["text"] for x in pages))
        return {"format": "pdf", "backend": "PyMuPDF", "pages": pages, "page_count": len(pages)}

    exe = shutil.which("pdftotext")
    if exe:
        with tempfile.TemporaryDirectory(prefix="aa_pdf_") as td:
            inp = Path(td) / "source.pdf"
            out = Path(td) / "source.txt"
            inp.write_bytes(raw)
            proc = subprocess.run(
                [exe, "-layout", str(inp), str(out)],
                capture_output=True,
                timeout=60,
                check=False,
            )
            if proc.returncode != 0 or not out.exists():
                raise SourceParseError("PDF_PDFTOTEXT_PARSE_FAILED")
            text = out.read_text(encoding="utf-8", errors="replace")
        _bounded_text(text)
        return {"format": "pdf", "backend": "pdftotext", "text": text}

    raise SourceParseError("PDF_PARSER_UNAVAILABLE")


def parse_source_bytes(raw: bytes, *, source_path: str) -> dict[str, Any]:
    if not isinstance(raw, bytes) or not raw:
        raise SourceParseError("SOURCE_BYTES_REQUIRED")
    if len(raw) > MAX_SOURCE_BYTES:
        raise SourceParseError("SOURCE_TOO_LARGE")
    ext = Path(source_path).suffix.lower()
    if ext == ".docx":
        parsed = _parse_docx(raw)
    elif ext == ".pptx":
        parsed = _parse_pptx(raw)
    elif ext == ".xlsx":
        parsed = _parse_xlsx(raw)
    elif ext == ".csv":
        parsed = _parse_csv_like(raw, ",", "csv")
    elif ext == ".tsv":
        parsed = _parse_csv_like(raw, "\t", "tsv")
    elif ext == ".json":
        parsed = _parse_json(raw)
    elif ext in {".eml", ".email"}:
        parsed = _parse_email(raw)
    elif ext in {".html", ".htm"}:
        parsed = _parse_html(raw)
    elif ext in {".txt", ".md", ".srt", ".tex", ".ics"}:
        parsed = _parse_text(raw, ext.lstrip("."))
    elif ext == ".pdf":
        parsed = _parse_pdf(raw)
    else:
        raise SourceParseError("UNSUPPORTED_SOURCE_FORMAT:" + ext)

    rep = {
        "parser_version": PARSER_VERSION,
        "source_path": source_path,
        "source_sha256": _sha(raw),
        "source_size_bytes": len(raw),
        "parsed": parsed,
    }
    return {
        "schema": SCHEMA,
        "status": "PARSED_CONTENT_ADDRESSED",
        **rep,
        "parsed_representation_sha256": _sha(_canon(rep)),
        "hidden_rubric_information_used": False,
        "semantic_completeness_claimed": False,
        "terminal_authority": False,
    }


def parse_all_declared_sources(ingress: Mapping[str, Any], *, source_root: str | Path) -> dict[str, Any]:
    if not isinstance(ingress, Mapping) or ingress.get("schema") != "PROJECT_BRAIN_AA_BRIEFCASE_LOSSLESS_TASK_INGRESS_V1":
        raise SourceParseError("INGRESS_INVALID")
    if ingress.get("all_declared_source_files_preserved_by_path_hash_and_size") is not True:
        raise SourceParseError("INGRESS_SOURCE_PRESERVATION_NOT_PROVED")
    sources = ingress.get("source_files")
    if not isinstance(sources, list) or not sources:
        raise SourceParseError("INGRESS_SOURCES_INVALID")

    root = Path(source_root).resolve()
    if not root.is_dir():
        raise SourceParseError("SOURCE_ROOT_INVALID")

    receipts = []
    seen = set()
    for row in sources:
        if not isinstance(row, Mapping):
            raise SourceParseError("INGRESS_SOURCE_ROW_INVALID")
        rel = str(row.get("path") or "")
        if rel in seen:
            raise SourceParseError("INGRESS_DUPLICATE_SOURCE:" + rel)
        seen.add(rel)
        expected_sha = row.get("sha256")
        expected_size = row.get("size_bytes")
        if not isinstance(expected_sha, str) or not HEX64.fullmatch(expected_sha):
            raise SourceParseError("INGRESS_SOURCE_SHA_INVALID:" + rel)
        if not isinstance(expected_size, int) or isinstance(expected_size, bool) or expected_size < 0:
            raise SourceParseError("INGRESS_SOURCE_SIZE_INVALID:" + rel)
        path = _safe_join(root, rel)
        if not path.is_file():
            raise SourceParseError("DECLARED_SOURCE_MISSING:" + rel)
        raw = path.read_bytes()
        actual_sha = _sha(raw)
        if actual_sha != expected_sha:
            raise SourceParseError("DECLARED_SOURCE_SHA_MISMATCH:" + rel)
        if len(raw) != expected_size:
            raise SourceParseError("DECLARED_SOURCE_SIZE_MISMATCH:" + rel)
        receipt = parse_source_bytes(raw, source_path=rel)
        receipts.append(receipt)

    material = {
        "schema": "PROJECT_BRAIN_AA_BRIEFCASE_ALL_DECLARED_SOURCES_PARSED_V1",
        "status": "PASS__ALL_DECLARED_SOURCES_PARSED",
        "ingress_sha256": ingress.get("ingress_sha256"),
        "source_count": len(receipts),
        "receipt_roots": [
            {
                "source_path": x["source_path"],
                "source_sha256": x["source_sha256"],
                "parsed_representation_sha256": x["parsed_representation_sha256"],
                "format": x["parsed"]["format"],
            }
            for x in receipts
        ],
        "all_declared_sources_parsed": True,
        "unsupported_or_unparsed_source_count": 0,
        "hidden_rubric_information_used": False,
        "semantic_completeness_claimed": False,
        "terminal_authority": False,
    }
    return {
        **material,
        "parse_manifest_sha256": _sha(_canon(material)),
        "receipts": receipts,
    }
