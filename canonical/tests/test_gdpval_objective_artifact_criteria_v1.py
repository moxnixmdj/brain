import tempfile
import wave
import zipfile
from pathlib import Path

import gdpval_objective_artifact_criteria_v1 as m


def test_exact_filename():
    c = m.compile_criterion(
        "The submitted workbook file name is exactly Aurisic_Financials_4-25-1.xlsx."
    )
    assert c["status"] == "COMPILED_OBJECTIVE_CHECK"
    with tempfile.TemporaryDirectory() as d:
        from openpyxl import Workbook
        p = Path(d) / "Aurisic_Financials_4-25-1.xlsx"
        wb = Workbook()
        wb.save(p)
        wb.close()
        assert m.verify_compiled(c, d)["pass"] is True


def test_sheet_name_casefold_trim():
    c = m.compile_criterion(
        "The workbook contains a worksheet named exactly 'Sample Size Calculation' "
        "(case-insensitive, ignoring surrounding spaces)."
    )
    assert c["status"] == "COMPILED_OBJECTIVE_CHECK"
    with tempfile.TemporaryDirectory() as d:
        from openpyxl import Workbook
        p = Path(d) / "a.xlsx"
        wb = Workbook()
        wb.active.title = "  sample size calculation "
        wb.save(p)
        wb.close()
        assert m.verify_compiled(c, d)["pass"] is True


def test_mixed_semantics_refused():
    x = m.compile_criterion(
        "Both .pptx files open without error and are not password-protected."
    )
    assert x["status"] == "UNRESOLVED"
    y = m.compile_criterion(
        "The Excel schedule preserves the rotation order from the source PDF."
    )
    assert y["status"] == "UNRESOLVED"


def test_wav_header():
    c = m.compile_criterion(
        "The delivered audio file has a sampling rate of exactly 48,000 Hz."
    )
    assert c["status"] == "COMPILED_OBJECTIVE_CHECK"
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "a.wav"
        with wave.open(str(p), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(3)
            w.setframerate(48000)
            w.writeframes(b"\x00\x00\x00" * 10)
        assert m.verify_compiled(c, d)["pass"] is True


def test_single_docx_validity_required():
    c = m.compile_criterion(
        "Exactly one action-items document is provided in Word (.docx) format."
    )
    assert c["status"] == "COMPILED_OBJECTIVE_CHECK"
    with tempfile.TemporaryDirectory() as d:
        from docx import Document
        p = Path(d) / "x.docx"
        doc = Document()
        doc.add_paragraph("action items")
        doc.save(p)
        assert m.verify_compiled(c, d)["pass"] is True


def test_wrong_extension_or_extra_conjunct_not_accepted():
    assert m.compile_criterion("The memo is clear and professional.")["status"] == "UNRESOLVED"


def test_single_zip_rejects_extra_top_level_file():
    c = m.compile_criterion(
        "Exactly one top-level ZIP archive is submitted as the final deliverable "
        "(one and only one .zip file)."
    )
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "bundle.zip"
        with zipfile.ZipFile(p, "w") as z:
            z.writestr("x.txt", "x")
        (Path(d) / "extra.txt").write_text("x")
        assert m.verify_compiled(c, d)["pass"] is False


def test_checklist_pdf_may_coexist_with_action_items():
    c = m.compile_criterion("Exactly one checklist file is provided in PDF format.")
    with tempfile.TemporaryDirectory() as d:
        from pypdf import PdfWriter
        from docx import Document

        pdf = PdfWriter()
        pdf.add_blank_page(width=72, height=72)
        with open(Path(d) / "checklist.pdf", "wb") as f:
            pdf.write(f)

        p = Path(d) / "actions.docx"
        doc = Document()
        doc.add_paragraph("actions")
        doc.save(p)

        assert m.verify_compiled(c, d)["pass"] is True
