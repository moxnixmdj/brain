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

def xlsx(path: Path, *, error=False, zero_width=False, hidden=False) -> None:
    wb = b'''<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheets><sheet name="Model" sheetId="1"/></sheets>
</workbook>'''
    attrs=[]
    if zero_width: attrs.append('width="0"')
    if hidden: attrs.append('hidden="1"')
    cols = '<cols><col min="2" max="2" ' + ' '.join(attrs) + '/></cols>' if attrs else ''
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

def verify(profile, path):
    return m.verify({"artifact_paths":[str(path)],"profile_id":profile})

def test_brain_sanity_clean_docx_passes_without_quality_credit():
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/"a.docx"; docx(p)
        out=verify("BRAIN_PROFESSIONAL_OOXML_SANITY_V1",p)
        assert out["pass"] is True, out
        assert out["quality_authority"] is False
        assert out["style_adequacy_proved"] is False
        assert out["acceptance_credit_delta"] == 0

def test_brain_sanity_blank_docx_blocks():
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/"a.docx"; docx(p,"")
        out=verify("BRAIN_PROFESSIONAL_OOXML_SANITY_V1",p)
        assert out["pass"] is False
        assert any(x["id"]=="DOCX_NONEMPTY_CONTENT" for x in out["hard_defects"])

def test_public_xlsx_subgate_blocks_error_cells():
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/"a.xlsx"; xlsx(p,error=True)
        out=verify("AA_BRIEFCASE_LITE_W1_T2_XLSX_HARD_SUBGATE_V1",p)
        assert out["pass"] is False
        assert out["public_target_example_only"] is True
        assert out["source_check_id"]=="W1-T2-P-01"
        assert any(x["id"]=="XLSX_NO_ERROR_CELLS" for x in out["hard_defects"])

def test_public_xlsx_subgate_blocks_zero_width_not_merely_hidden_column():
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/"zero.xlsx"; xlsx(p,zero_width=True)
        bad=verify("AA_BRIEFCASE_LITE_W1_T2_XLSX_HARD_SUBGATE_V1",p)
        assert bad["pass"] is False
        assert any(x["id"]=="XLSX_NO_ZERO_WIDTH_COLUMNS" for x in bad["hard_defects"])

        q=Path(td)/"hidden.xlsx"; xlsx(q,hidden=True)
        good=verify("AA_BRIEFCASE_LITE_W1_T2_XLSX_HARD_SUBGATE_V1",q)
        assert good["pass"] is True, good

def test_public_pptx_subgate_blocks_text_outside_slide_bounds():
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/"a.pptx"; pptx(p,outside=True)
        out=verify("AA_BRIEFCASE_LITE_W1_T3_PPTX_HARD_SUBGATE_V1",p)
        assert out["pass"] is False, out
        assert out["source_check_id"]=="W1-T3-P-01"
        assert any(x["id"]=="PPTX_NO_TEXT_OBJECT_OUTSIDE_SLIDE_BOUNDS" for x in out["hard_defects"])

def test_blank_slide_not_invented_as_public_pptx_hard_failure():
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/"a.pptx"; pptx(p,blank=True)
        out=verify("AA_BRIEFCASE_LITE_W1_T3_PPTX_HARD_SUBGATE_V1",p)
        assert out["pass"] is True, out
        assert out["style_adequacy_proved"] is False

def test_public_profile_enforces_exact_artifact_format():
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/"a.docx"; docx(p)
        out=verify("AA_BRIEFCASE_LITE_W1_T2_XLSX_HARD_SUBGATE_V1",p)
        assert out["pass"] is False
        assert any(x["id"]=="EXPLICIT_FORMAT_MISMATCH" for x in out["hard_defects"])

def test_corrupt_package_is_inspection_failure_not_style_judgment():
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/"a.docx"; p.write_bytes(b"not-a-zip")
        out=verify("BRAIN_PROFESSIONAL_OOXML_SANITY_V1",p)
        assert out["pass"] is False
        assert out["hard_defect_count"] == 0
        assert any("OOXML_PACKAGE_INVALID" in e for e in out["checked_artifacts"][0]["errors"])

def test_unknown_profile_fails_closed():
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/"a.docx"; docx(p)
        out=verify("USER_CHOSE_EASY_CHECKS",p)
        assert out["pass"] is False
        assert "PROFILE_ID_UNKNOWN_OR_MISSING" in out["errors"]

def test_caller_cannot_inject_custom_check_selection():
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/"a.docx"; docx(p)
        out=m.verify({
            "artifact_paths":[str(p)],
            "profile_id":"BRAIN_PROFESSIONAL_OOXML_SANITY_V1",
            "required_checks":["DOCX_NONEMPTY_CONTENT"],
        })
        assert out["pass"] is False
        assert "UNSUPPORTED_CALLER_FIELDS" in out["errors"]
