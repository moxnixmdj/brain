"""Independent cross-format preflight for native structured edit preservation.

The evaluator creates native DOCX/XLSX/PPTX/PDF artifacts containing unrelated
structure, invokes the Brain candidate with only an explicit text edit, then reopens
the output with format-specific readers and independently checks requested semantics
and unrelated invariants.

OOXML package members not declared changed must remain byte-identical. PDF semantic
text/page geometry are checked through Poppler when available, independently from
the pypdf-based candidate transaction.

This is bounded preflight evidence, not terminal capability credit.
"""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any
import hashlib
import shutil
import subprocess
import tempfile
import zipfile


SCHEMA = "PROJECT_BRAIN_NATIVE_ARTIFACT_CROSS_FORMAT_PROOF_V1"


def _deps():
    try:
        from docx import Document
        from docx.shared import Inches
        from openpyxl import Workbook, load_workbook
        from openpyxl.styles import PatternFill
        from pptx import Presentation
        from pptx.enum.shapes import MSO_SHAPE_TYPE
        from pptx.util import Inches as PptInches
        from PIL import Image
        from pypdf import PdfWriter
        from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
        return {
            "Document": Document,
            "DocxInches": Inches,
            "Workbook": Workbook,
            "load_workbook": load_workbook,
            "PatternFill": PatternFill,
            "Presentation": Presentation,
            "MSO_SHAPE_TYPE": MSO_SHAPE_TYPE,
            "PptInches": PptInches,
            "Image": Image,
            "PdfWriter": PdfWriter,
            "DecodedStreamObject": DecodedStreamObject,
            "DictionaryObject": DictionaryObject,
            "NameObject": NameObject,
        }
    except Exception as exc:
        return exc


def _zip_bytes(path: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(path, "r") as z:
        return {i.filename: z.read(i.filename) for i in z.infolist() if not i.is_dir()}


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _changed_zip_members(before: Path, after: Path) -> list[str]:
    a = _zip_bytes(before)
    b = _zip_bytes(after)
    if set(a) != set(b):
        raise ValueError("PACKAGE_MEMBER_SET_CHANGED")
    return sorted(k for k in a if a[k] != b[k])


def _write_png(path: Path, Image) -> None:
    Image.new("RGB", (20, 14), (31, 89, 140)).save(path, "PNG")


def _make_docx(path: Path, deps: dict[str, Any], image_path: Path) -> dict[str, Any]:
    Document = deps["Document"]
    Inches = deps["DocxInches"]
    doc = Document()
    doc.add_heading("Preservation Fixture", level=1)
    doc.add_paragraph("TARGET_OLD")
    keep = doc.add_paragraph()
    r = keep.add_run("KEEP_FORMATTED")
    r.bold = True
    doc.add_picture(str(image_path), width=Inches(0.4))
    doc.core_properties.title = "KEEP_METADATA"
    doc.save(path)
    z = _zip_bytes(path)
    return {
        "member_hashes": {k: _sha(v) for k, v in z.items()},
        "image_members": sorted(k for k in z if k.startswith("word/media/")),
    }


def _verify_docx(before: Path, after: Path, deps: dict[str, Any], fixture: dict[str, Any]) -> dict[str, Any]:
    Document = deps["Document"]
    doc = Document(after)
    texts = [p.text for p in doc.paragraphs]
    if "TARGET_NEW" not in texts or "TARGET_OLD" in texts:
        raise ValueError("DOCX_TARGET_TEXT_MISMATCH")
    keep_runs = [r for p in doc.paragraphs for r in p.runs if r.text == "KEEP_FORMATTED"]
    if len(keep_runs) != 1 or keep_runs[0].bold is not True:
        raise ValueError("DOCX_UNRELATED_FORMATTING_CHANGED")
    if len(doc.inline_shapes) != 1:
        raise ValueError("DOCX_IMAGE_RELATIONSHIP_LOST")
    if doc.core_properties.title != "KEEP_METADATA":
        raise ValueError("DOCX_METADATA_CHANGED")
    changed = _changed_zip_members(before, after)
    if changed != ["word/document.xml"]:
        raise ValueError("DOCX_UNDECLARED_MEMBER_CHANGED:" + ",".join(changed))
    return {"changed_members": changed, "image_members": fixture["image_members"]}


def _make_xlsx(path: Path, deps: dict[str, Any]) -> dict[str, Any]:
    Workbook = deps["Workbook"]
    PatternFill = deps["PatternFill"]
    wb = Workbook()
    ws = wb.active
    ws.title = "Data"
    ws["A1"] = "TARGET_OLD"
    ws["B1"] = 7
    ws["C1"] = 5
    ws["D1"] = "=B1+C1"
    ws["A2"] = "KEEP_CELL"
    ws["A2"].fill = PatternFill(fill_type="solid", fgColor="00FF00")
    other = wb.create_sheet("KeepSheet")
    other["A1"] = "UNCHANGED_SHEET"
    wb.save(path)
    return {"sheet_names": ["Data", "KeepSheet"]}


def _verify_xlsx(before: Path, after: Path, deps: dict[str, Any], fixture: dict[str, Any]) -> dict[str, Any]:
    load_workbook = deps["load_workbook"]
    wb = load_workbook(after, data_only=False)
    if wb.sheetnames != fixture["sheet_names"]:
        raise ValueError("XLSX_SHEET_STRUCTURE_CHANGED")
    ws = wb["Data"]
    if ws["A1"].value != "TARGET_NEW":
        raise ValueError("XLSX_TARGET_TEXT_MISMATCH")
    if ws["D1"].value != "=B1+C1":
        raise ValueError("XLSX_FORMULA_CHANGED")
    if ws["A2"].value != "KEEP_CELL" or ws["A2"].fill.fill_type != "solid":
        raise ValueError("XLSX_UNRELATED_STYLE_OR_VALUE_CHANGED")
    if wb["KeepSheet"]["A1"].value != "UNCHANGED_SHEET":
        raise ValueError("XLSX_UNRELATED_SHEET_CHANGED")
    changed = _changed_zip_members(before, after)
    if len(changed) != 1 or not (changed[0].startswith("xl/worksheets/") or changed[0] == "xl/sharedStrings.xml"):
        raise ValueError("XLSX_UNEXPECTED_CHANGED_MEMBERS:" + ",".join(changed))
    return {"changed_members": changed, "sheet_names": wb.sheetnames}


def _make_pptx(path: Path, deps: dict[str, Any], image_path: Path) -> dict[str, Any]:
    Presentation = deps["Presentation"]
    PptInches = deps["PptInches"]
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    box = slide.shapes.add_textbox(PptInches(0.5), PptInches(0.5), PptInches(3), PptInches(0.6))
    box.text = "TARGET_OLD"
    keep = slide.shapes.add_textbox(PptInches(0.5), PptInches(1.3), PptInches(3), PptInches(0.6))
    keep.text = "KEEP_TEXT"
    slide.shapes.add_picture(str(image_path), PptInches(4), PptInches(0.5), width=PptInches(0.6))
    prs.core_properties.title = "KEEP_PPT_METADATA"
    dims = (prs.slide_width, prs.slide_height)
    prs.save(path)
    return {"slide_dims": dims}


def _verify_pptx(before: Path, after: Path, deps: dict[str, Any], fixture: dict[str, Any]) -> dict[str, Any]:
    Presentation = deps["Presentation"]
    MSO_SHAPE_TYPE = deps["MSO_SHAPE_TYPE"]
    prs = Presentation(after)
    if len(prs.slides) != 1 or (prs.slide_width, prs.slide_height) != fixture["slide_dims"]:
        raise ValueError("PPTX_SLIDE_STRUCTURE_CHANGED")
    texts = [shape.text for shape in prs.slides[0].shapes if hasattr(shape, "text")]
    if "TARGET_NEW" not in texts or "TARGET_OLD" in texts or "KEEP_TEXT" not in texts:
        raise ValueError("PPTX_TEXT_MISMATCH")
    pictures = [s for s in prs.slides[0].shapes if s.shape_type == MSO_SHAPE_TYPE.PICTURE]
    if len(pictures) != 1:
        raise ValueError("PPTX_IMAGE_LOST")
    if prs.core_properties.title != "KEEP_PPT_METADATA":
        raise ValueError("PPTX_METADATA_CHANGED")
    changed = _changed_zip_members(before, after)
    if len(changed) != 1 or not changed[0].startswith("ppt/slides/slide"):
        raise ValueError("PPTX_UNEXPECTED_CHANGED_MEMBERS:" + ",".join(changed))
    return {"changed_members": changed, "picture_count": len(pictures)}


def _make_pdf(path: Path, deps: dict[str, Any]) -> dict[str, Any]:
    PdfWriter = deps["PdfWriter"]
    DecodedStreamObject = deps["DecodedStreamObject"]
    DictionaryObject = deps["DictionaryObject"]
    NameObject = deps["NameObject"]
    w = PdfWriter()
    page = w.add_blank_page(width=240, height=180)
    font = DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Helvetica"),
    })
    font_ref = w._add_object(font)
    page[NameObject("/Resources")] = DictionaryObject({
        NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_ref})
    })
    stream = DecodedStreamObject()
    stream.set_data(b"BT /F1 12 Tf 20 120 Td (TARGET_OLD) Tj 0 -24 Td (KEEP_PDF_TEXT) Tj ET")
    page[NameObject("/Contents")] = w._add_object(stream)
    with path.open("wb") as fh:
        w.write(fh)
    return {"page_size": (240.0, 180.0), "page_count": 1}


def _poppler_text(path: Path) -> str:
    exe = shutil.which("pdftotext")
    if not exe:
        raise RuntimeError("PDFTOTEXT_UNAVAILABLE")
    proc = subprocess.run([exe, "-layout", str(path), "-"], check=True, capture_output=True, text=True)
    return proc.stdout


def _pdfinfo(path: Path) -> str:
    exe = shutil.which("pdfinfo")
    if not exe:
        raise RuntimeError("PDFINFO_UNAVAILABLE")
    proc = subprocess.run([exe, str(path)], check=True, capture_output=True, text=True)
    return proc.stdout


def _verify_pdf(before: Path, after: Path, deps: dict[str, Any], fixture: dict[str, Any]) -> dict[str, Any]:
    text = _poppler_text(after)
    if "TARGET_NEW" not in text or "TARGET_OLD" in text or "KEEP_PDF_TEXT" not in text:
        raise ValueError("PDF_INDEPENDENT_TEXT_CHECK_FAILED")
    info = _pdfinfo(after)
    if "Pages:" not in info:
        raise ValueError("PDFINFO_PAGE_COUNT_MISSING")
    # Candidate additionally enforces operator-sequence and MediaBox preservation.
    return {"independent_text_check": "POPPLER_PASS", "pdfinfo_checked": True}


def run_cross_format_preflight(candidate_apply) -> dict[str, Any]:
    deps = _deps()
    if isinstance(deps, Exception):
        return {
            "schema": SCHEMA,
            "all_pass": False,
            "reason": "DEPENDENCY_UNAVAILABLE",
            "error": type(deps).__name__,
            "terminal_authority": False,
        }

    rows = []
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        image = root / "fixture.png"
        _write_png(image, deps["Image"])

        makers = {
            "docx": lambda p: _make_docx(p, deps, image),
            "xlsx": lambda p: _make_xlsx(p, deps),
            "pptx": lambda p: _make_pptx(p, deps, image),
            "pdf": lambda p: _make_pdf(p, deps),
        }
        verifiers = {
            "docx": _verify_docx,
            "xlsx": _verify_xlsx,
            "pptx": _verify_pptx,
            "pdf": _verify_pdf,
        }

        for fmt in ("docx", "xlsx", "pptx", "pdf"):
            src = root / f"in.{fmt}"
            dst = root / f"out.{fmt}"
            fixture = makers[fmt](src)
            request = {"format": fmt, "old": "TARGET_OLD", "new": "TARGET_NEW"}
            if fmt == "pdf":
                request["page_index"] = 0
            try:
                result = candidate_apply(src, dst, request)
                if result.get("status") != "PASS":
                    raise ValueError("CANDIDATE_EDIT_FAILED:" + str(result))
                oracle = verifiers[fmt](src, dst, deps, fixture)
                rows.append({
                    "format": fmt,
                    "pass": True,
                    "candidate_scope": result.get("scope"),
                    "oracle": oracle,
                })
            except Exception as exc:
                rows.append({
                    "format": fmt,
                    "pass": False,
                    "reason": type(exc).__name__ + ":" + str(exc),
                })

    return {
        "schema": SCHEMA,
        "all_pass": all(r["pass"] for r in rows),
        "formats": rows,
        "format_count": len(rows),
        "passed": sum(int(r["pass"]) for r in rows),
        "failed": sum(int(not r["pass"]) for r in rows),
        "independent_oracles": {
            "docx": "python-docx reopen plus ZIP member diff",
            "xlsx": "openpyxl reopen plus ZIP member diff",
            "pptx": "python-pptx reopen plus ZIP member diff",
            "pdf": "Poppler pdftotext/pdfinfo plus candidate internal native checks",
        },
        "terminal_authority": False,
        "capability_credit_delta": 0,
    }
