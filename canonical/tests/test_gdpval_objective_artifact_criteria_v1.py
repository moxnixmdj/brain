import tempfile
import wave
import zipfile
from pathlib import Path

from canonical.runtime import gdpval_objective_artifact_criteria_v1 as m


def test_exact_workbook_filename_requires_native_validity():
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

        p.write_bytes(b"not-an-xlsx")
        assert m.verify_compiled(c, d)["pass"] is False


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
    assert m.compile_criterion(
        "Both .pptx files open without error and are not password-protected."
    )["status"] == "UNRESOLVED"
    assert m.compile_criterion(
        "The Excel schedule preserves the rotation order from the source PDF."
    )["status"] == "UNRESOLVED"


def test_semantic_role_labeled_file_count_refused():
    assert m.compile_criterion(
        "Exactly one checklist file is provided in PDF format."
    )["status"] == "UNRESOLVED"
    assert m.compile_criterion(
        "Exactly one action-items document is provided in Word (.docx) format."
    )["status"] == "UNRESOLVED"


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


def test_exact_audio_filename_requires_valid_wav():
    c = m.compile_criterion(
        'An audio file named exactly "State of Affairs_FULL_EDIT_MIX.wav" is delivered.'
    )
    assert c["status"] == "COMPILED_OBJECTIVE_CHECK"
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "State of Affairs_FULL_EDIT_MIX.wav"
        p.write_bytes(b"fake")
        assert m.verify_compiled(c, d)["pass"] is False

        with wave.open(str(p), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(48000)
            w.writeframes(b"\x00\x00" * 4)
        assert m.verify_compiled(c, d)["pass"] is True


def test_simple_docx_format_and_corruption():
    c = m.compile_criterion(
        "Deliverable is provided as a Microsoft Word document (.docx)."
    )
    assert c["status"] == "COMPILED_OBJECTIVE_CHECK"
    with tempfile.TemporaryDirectory() as d:
        from docx import Document

        p = Path(d) / "x.docx"
        doc = Document()
        doc.add_paragraph("x")
        doc.save(p)
        assert m.verify_compiled(c, d)["pass"] is True

        p.write_bytes(b"not-a-docx")
        assert m.verify_compiled(c, d)["pass"] is False


def test_professional_quality_refused():
    assert m.compile_criterion(
        "The memo is clear and professional."
    )["status"] == "UNRESOLVED"


def test_single_zip_rejects_extra_top_level_file():
    c = m.compile_criterion(
        "Exactly one top-level ZIP archive is submitted as the final deliverable "
        "(one and only one .zip file)."
    )
    assert c["status"] == "COMPILED_OBJECTIVE_CHECK"
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "bundle.zip"
        with zipfile.ZipFile(p, "w") as z:
            z.writestr("x.txt", "x")
        (Path(d) / "extra.txt").write_text("x")
        assert m.verify_compiled(c, d)["pass"] is False
