from __future__ import annotations
import math
from pathlib import Path
import tempfile
import wave
import zipfile

from canonical.runtime.gdpval_structural_rubric_sufficient_v1 import (
    compile_criterion,
    verify_compiled,
)

def test_exact_pdf_format_compiles_but_subjective_style_does_not():
    x=compile_criterion("The deliverable is a single file in PDF format")
    assert x["status"]=="COMPILED_SUFFICIENT_CONDITION"
    assert [p["kind"] for p in x["predicates"]]==["OUTPUT_FILE_COUNT_EQ","FILE_FORMAT_EQ"]
    y=compile_criterion("Overall formatting and style of the deliverable")
    assert y["status"]=="UNRESOLVED"

def test_sentence_range_is_exactly_bounded():
    c=compile_criterion("The paragraph contains between 5 and 7 sentences inclusive.")
    assert c["status"]=="COMPILED_SUFFICIENT_CONDITION"
    out=verify_compiled(c,text_response="One. Two. Three. Four. Five. Six.")
    assert out["satisfied"] is True
    bad=verify_compiled(c,text_response="One. Two. Three. Four.")
    assert bad["satisfied"] is False

def test_pptx_count_uses_actual_slide_members():
    c=compile_criterion("The deck contains between 8 and 10 slides inclusive (counting all slides)")
    assert c["status"]=="COMPILED_SUFFICIENT_CONDITION"
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/"x.pptx"
        with zipfile.ZipFile(p,"w") as z:
            z.writestr("[Content_Types].xml","<Types/>")
            z.writestr("ppt/presentation.xml","<p:presentation xmlns:p='x'/>")
            for i in range(1,9):
                z.writestr(f"ppt/slides/slide{i}.xml","<p:sld xmlns:p='x'/>")
        out=verify_compiled(c,output_paths=[str(p)])
        assert out["satisfied"] is True

def test_wav_metadata_and_peak_are_measured_from_bytes():
    criteria=[
        "The delivered file is a WAV file and not a compressed format (e.g., MP3/AAC).",
        "Sample rate of the delivered file is 48kHz.",
        "Bit depth of the delivered file is 24-bit PCM.",
        "The delivered file is in stereo (Left/Right channels).",
        "Recommended headroom practice: sample peaks do not exceed -0.1 dBFS.",
    ]
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/"x.wav"
        with wave.open(str(p),"wb") as w:
            w.setnchannels(2); w.setsampwidth(3); w.setframerate(48000)
            sample=int((1<<23)*0.5)
            b=sample.to_bytes(3,"little",signed=True)
            w.writeframes((b+b)*100)
        for text in criteria:
            c=compile_criterion(text)
            assert c["status"]=="COMPILED_SUFFICIENT_CONDITION", text
            out=verify_compiled(c,output_paths=[str(p)])
            assert out["satisfied"] is True, (text,out)

def test_nearby_unproved_language_fails_closed():
    for text in [
        "The PDF looks professional.",
        "The document is easy to read.",
        "The deck contains appropriate visual hierarchy.",
        "The WAV sounds natural and polished.",
        "The document is a Word file.",
    ]:
        assert compile_criterion(text)["status"]=="UNRESOLVED"


def test_generic_structural_forms_are_bounded_and_not_role_inference():
    samples={
        "The final deliverable is provided as an Excel workbook in .xlsx format.":"SINGLE_XLSX_FORMAT",
        "A single PDF file is delivered.":"SINGLE_PDF_FORMAT",
        "Submission is a single-page PDF":"EXACT_SINGLE_PAGE_PDF",
        "The workbook contains a worksheet named exactly 'Sample Size Calculation' (case-insensitive, ignoring surrounding spaces).":"EXACT_XLSX_SHEET_NAME",
        "The zip archive contains a top-level file named README.md.":"EXACT_ZIP_TOP_LEVEL_FILE",
        "Deliverable includes a Terraform file named main.tf":"EXACT_DELIVERABLE_FILE_EXISTS",
    }
    for text,rule in samples.items():
        out=compile_criterion(text)
        assert out["status"]=="COMPILED_SUFFICIENT_CONDITION",(text,out)
        assert out["rule"]==rule,(text,out)
    for text in [
        "A memo file in PDF format ('.pdf') is submitted.",
        "The checklist PDF is no more than five pages in total, including any appendices.",
        "The PDF looks polished and client-ready.",
    ]:
        assert compile_criterion(text)["status"]=="UNRESOLVED"

def test_xlsx_sheet_and_zip_top_level_verifiers_are_byte_structural():
    with tempfile.TemporaryDirectory() as td:
        td=Path(td)
        x=td/"book.xlsx"
        with zipfile.ZipFile(x,"w") as z:
            z.writestr("[Content_Types].xml","<Types/>")
            z.writestr("xl/workbook.xml","""<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheets><sheet name="Sample Size Calculation" sheetId="1"/></sheets></workbook>""")
        c=compile_criterion("The workbook contains a worksheet named exactly 'Sample Size Calculation' (case-insensitive, ignoring surrounding spaces).")
        assert verify_compiled(c,output_paths=[str(x)])["satisfied"] is True

        zpath=td/"submission.zip"
        with zipfile.ZipFile(zpath,"w") as z:
            z.writestr("README.md","ok")
            z.writestr("nested/README.md","not-top-level")
        c=compile_criterion("The zip archive contains a top-level file named README.md.")
        assert verify_compiled(c,output_paths=[str(zpath)])["satisfied"] is True

def test_filename_capture_does_not_swallow_sentence_period():
    c=compile_criterion("The zip archive contains a top-level file named README.md.")
    assert c["predicates"][0]["basename"]=="README.md"
