from pathlib import Path
import tempfile
import zipfile

from canonical.runtime import professional_artifact_hard_defect_preflight_v1 as m


CONTENT_TYPES = b'''<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"></Types>'''

def write_zip(path: Path, members: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        for name, data in members.items():
            z.writestr(name, data)

def docx(path: Path, text: str = "Hello") -> None:
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:body><w:p><w:r><w:t>' + text + '</w:t></w:r></w:p></w:body></w:document>'
    ).encode()
    write_zip(path, {"word/document.xml": body})

def xlsx(path: Path, *, error=False, zero_width=False) -> None:
    wb = b'''<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheets><sheet name="Model" sheetId="1"/></sheets>
</workbook>'''
    cols = '<cols><col min="2" max="2" width="0"/></cols>' if zero_width else ''
    cell = '<c r="A1" t="e"><v>#REF!</v></c>' if error else '<c r="A1"><v>42</v></c>'
    ws = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        + cols + '<sheetData><row r="1">' + cell + '</row></sheetData></worksheet>'
    ).encode()
    write_zip(path, {"xl/workbook.xml": wb, "xl/worksheets/sheet1.xml": ws})

def pptx(path: Path, *, outside=False, blank=False) -> None:
    pres = b'''<?xml version="1.0" encoding="UTF-8"?>
<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:sldSz cx="1000" cy="1000"/>
</p:presentation>'''
    if blank:
        child = ''
    else:
        x = 900 if outside else 100
        child = f'''
        <p:sp>
          <p:spPr><a:xfrm><a:off x="{x}" y="100"/><a:ext cx="200" cy="200"/></a:xfrm></p:spPr>
          <p:txBody><a:p><a:r><a:t>Title</a:t></a:r></a:p></p:txBody>
        </p:sp>'''
    slide = f'''<?xml version="1.0" encoding="UTF-8"?>
<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
       xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
  <p:cSld><p:spTree><p:nvGrpSpPr/><p:grpSpPr/>{child}</p:spTree></p:cSld>
</p:sld>'''.encode()
    write_zip(path, {"ppt/presentation.xml": pres, "ppt/slides/slide1.xml": slide})

def test_clean_docx_is_only_required_check_clean():
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/"a.docx"; docx(p)
        out=m.verify({
            "artifact_paths":[str(p)],
            "required_checks":["DOCX_NONEMPTY_CONTENT"],
        })
        assert out["pass"] is True, out
        assert out["hard_defect_count"] == 0
        assert out["quality_authority"] is False
        assert out["style_adequacy_proved"] is False
        assert out["acceptance_credit_delta"] == 0

def test_blank_docx_blocks_only_when_check_is_required():
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/"a.docx"; docx(p, "")
        out=m.verify({
            "artifact_paths":[str(p)],
            "required_checks":["DOCX_NONEMPTY_CONTENT"],
        })
        assert out["pass"] is False
        assert any(x["id"]=="DOCX_NONEMPTY_CONTENT" for x in out["hard_defects"])

def test_xlsx_error_cell_blocks_when_source_or_policy_requires_check():
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/"a.xlsx"; xlsx(p,error=True)
        out=m.verify({
            "artifact_paths":[str(p)],
            "required_checks":["XLSX_NO_ERROR_CELLS"],
        })
        assert out["pass"] is False
        assert any(x["id"]=="XLSX_NO_ERROR_CELLS" for x in out["hard_defects"])

def test_xlsx_zero_width_column_blocks_when_required():
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/"a.xlsx"; xlsx(p,zero_width=True)
        out=m.verify({
            "artifact_paths":[str(p)],
            "required_checks":["XLSX_NO_ZERO_WIDTH_COLUMNS"],
        })
        assert out["pass"] is False
        assert any(x["id"]=="XLSX_NO_ZERO_WIDTH_COLUMNS" for x in out["hard_defects"])

def test_observed_unrequired_condition_does_not_become_authority():
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/"a.xlsx"; xlsx(p,error=True)
        out=m.verify({
            "artifact_paths":[str(p)],
            "required_checks":["XLSX_HAS_VISIBLE_WORKSHEET"],
        })
        assert out["pass"] is True, out
        assert out["hard_defect_count"] == 0
        assert any(x["id"]=="XLSX_NO_ERROR_CELLS" for x in out["observed_nonrequired_conditions"])
        assert out["source_or_policy_authority_required_for_check_selection"] is True

def test_pptx_text_object_outside_slide_bounds_blocks_when_required():
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/"a.pptx"; pptx(p,outside=True)
        out=m.verify({
            "artifact_paths":[str(p)],
            "required_checks":["PPTX_NO_TEXT_OBJECT_OUTSIDE_SLIDE_BOUNDS"],
        })
        assert out["pass"] is False, out
        assert any(x["id"]=="PPTX_NO_TEXT_OBJECT_OUTSIDE_SLIDE_BOUNDS" for x in out["hard_defects"])

def test_blank_slide_is_not_universally_declared_a_defect():
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/"a.pptx"; pptx(p,blank=True)
        out=m.verify({
            "artifact_paths":[str(p)],
            "required_checks":["PPTX_HAS_SLIDES"],
        })
        assert out["pass"] is True, out
        assert out["style_adequacy_proved"] is False

def test_explicit_file_count_and_format_constraints_fail_closed():
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/"a.docx"; docx(p)
        out=m.verify({
            "artifact_paths":[str(p)],
            "required_checks":["DOCX_NONEMPTY_CONTENT"],
            "constraints":{"exact_file_count":2,"allowed_suffixes":[".xlsx"]},
        })
        ids={x["id"] for x in out["hard_defects"]}
        assert out["pass"] is False
        assert "EXPLICIT_FILE_COUNT_MISMATCH" in ids
        assert "EXPLICIT_FORMAT_MISMATCH" in ids

def test_corrupt_package_is_inspection_failure_not_style_judgment():
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/"a.docx"; p.write_bytes(b"not-a-zip")
        out=m.verify({
            "artifact_paths":[str(p)],
            "required_checks":["DOCX_NONEMPTY_CONTENT"],
        })
        assert out["pass"] is False
        assert out["hard_defect_count"] == 0
        assert any("OOXML_PACKAGE_INVALID" in e for e in out["checked_artifacts"][0]["errors"])

def test_missing_required_check_authority_fails_closed():
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/"a.docx"; docx(p)
        out=m.verify({"artifact_paths":[str(p)]})
        assert out["pass"] is False
        assert "REQUIRED_CHECKS_INVALID_OR_EMPTY" in out["errors"]
