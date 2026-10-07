import tempfile
from pathlib import Path

from canonical.runtime import gdpval_objective_artifact_criteria_v2 as m


def _xlsx(path: Path, sheets):
    from openpyxl import Workbook
    wb=Workbook()
    wb.active.title=sheets[0]
    for s in sheets[1:]:
        wb.create_sheet(s)
    wb.save(path)
    wb.close()


def _pptx(path: Path, slides: int):
    from pptx import Presentation
    p=Presentation()
    for _ in range(slides):
        p.slides.add_slide(p.slide_layouts[6])
    p.save(path)


def test_case_insensitive_sheet_name_variant():
    c=m.compile_criterion("The workbook contains a worksheet named exactly 'EMR TRANSFER PATIENTS' (case-insensitive).")
    assert c["status"]=="COMPILED_OBJECTIVE_CHECK"
    with tempfile.TemporaryDirectory() as d:
        _xlsx(Path(d)/"x.xlsx",["emr transfer patients"])
        assert m.verify_compiled(c,d)["pass"] is True


def test_exact_sheet_title_variant_is_case_sensitive():
    c=m.compile_criterion('Workbook includes a sheet titled exactly "Topics & Labs"')
    assert c["status"]=="COMPILED_OBJECTIVE_CHECK"
    with tempfile.TemporaryDirectory() as d:
        _xlsx(Path(d)/"x.xlsx",["topics & labs"])
        assert m.verify_compiled(c,d)["pass"] is False
        _xlsx(Path(d)/"x.xlsx",["Topics & Labs"])
        assert m.verify_compiled(c,d)["pass"] is True


def test_single_pdf_requires_exactly_one_top_level_real_pdf():
    c=m.compile_criterion("The deliverable is provided as a single PDF file.")
    assert c["status"]=="COMPILED_OBJECTIVE_CHECK"
    with tempfile.TemporaryDirectory() as d:
        from pypdf import PdfWriter
        w=PdfWriter(); w.add_blank_page(width=100,height=100)
        with open(Path(d)/"a.pdf","wb") as f: w.write(f)
        assert m.verify_compiled(c,d)["pass"] is True
        (Path(d)/"extra.txt").write_text("x")
        assert m.verify_compiled(c,d)["pass"] is False


def test_plain_pdf_does_not_require_uniqueness():
    c=m.compile_criterion("The deliverable is provided as a PDF file.")
    assert c["status"]=="COMPILED_OBJECTIVE_CHECK"
    with tempfile.TemporaryDirectory() as d:
        from pypdf import PdfWriter
        for name in ("a.pdf","b.pdf"):
            w=PdfWriter(); w.add_blank_page(width=100,height=100)
            with open(Path(d)/name,"wb") as f: w.write(f)
        assert m.verify_compiled(c,d)["pass"] is True


def test_single_xlsx_requires_one_file_and_native_validity():
    c=m.compile_criterion("The deliverable is a single Microsoft Excel workbook file (.xlsx).")
    assert c["status"]=="COMPILED_OBJECTIVE_CHECK"
    with tempfile.TemporaryDirectory() as d:
        _xlsx(Path(d)/"x.xlsx",["Sheet1"])
        assert m.verify_compiled(c,d)["pass"] is True
        (Path(d)/"y.txt").write_text("extra")
        assert m.verify_compiled(c,d)["pass"] is False


def test_exact_slide_count():
    c=m.compile_criterion("The presentation contains exactly 9 slides")
    assert c["status"]=="COMPILED_OBJECTIVE_CHECK"
    with tempfile.TemporaryDirectory() as d:
        _pptx(Path(d)/"x.pptx",9)
        assert m.verify_compiled(c,d)["pass"] is True
        _pptx(Path(d)/"x.pptx",8)
        assert m.verify_compiled(c,d)["pass"] is False


def test_mixed_conjunct_is_not_partially_compiled():
    assert m.compile_criterion(
        "The deliverable is provided as a PDF file and clearly explains the strategy."
    )["status"]=="UNRESOLVED"
    assert m.compile_criterion(
        "Workbook includes a sheet titled exactly \"Data\" and the analysis is insightful."
    )["status"]=="UNRESOLVED"


def test_v1_route_remains_delegated():
    c=m.compile_criterion(
        "The submitted deliverable is an Excel workbook file whose basename is 'Sample' (accept .xlsx, .xls, or .xlsm)."
    )
    assert c["status"]=="COMPILED_OBJECTIVE_CHECK"
    assert c["compiler_version"]=="V1_DELEGATED"
