from __future__ import annotations
import pathlib,tempfile,zipfile
from canonical.runtime.artifact_measurement_xlsx_file_extension_v1 import measure_one

def _xlsx(root,name="Summary",extra=()):
    p=root/"book.xlsx"
    xml=f'<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheets><sheet name="{name}"/></sheets></workbook>'
    with zipfile.ZipFile(p,"w") as z:
        z.writestr("xl/workbook.xml",xml)
        for member in extra:z.writestr(member,b"x")
    return p

def test_file_basename_and_stem_and_suffix_set():
    with tempfile.TemporaryDirectory() as td:
        p=pathlib.Path(td)/"Chief Key Indicators 5 Year.xlsx";p.write_text("x")
        assert measure_one(p,{"kind":"FILE_BASENAME_EQUALS","expected":"chief key indicators 5 year.xlsx","case_sensitive":False})[1] is True
        assert measure_one(p,{"kind":"FILE_STEM_EQUALS","expected":"Chief Key Indicators 5 Year"})[1] is True
        assert measure_one(p,{"kind":"FILE_SUFFIX_IN","allowed_suffixes":[".xlsx",".xlsm"]})[1] is True

def test_first_sheet_and_contains():
    with tempfile.TemporaryDirectory() as td:
        p=_xlsx(pathlib.Path(td),"Table of Contents")
        assert measure_one(p,{"kind":"XLSX_FIRST_SHEET_NAME_EQUALS","expected":"table of contents","case_sensitive":False})[1] is True
        assert measure_one(p,{"kind":"XLSX_SHEET_NAME_CONTAINS","text":"contents","case_sensitive":False})[1] is True

def test_external_link_count():
    with tempfile.TemporaryDirectory() as td:
        p=_xlsx(pathlib.Path(td),extra=["xl/externalLinks/externalLink1.xml","xl/externalLinks/externalLink2.xml"])
        assert measure_one(p,{"kind":"XLSX_EXTERNAL_LINK_COUNT"})[1]==2

def test_macro_presence():
    with tempfile.TemporaryDirectory() as td:
        p=_xlsx(pathlib.Path(td),extra=["xl/vbaProject.bin"])
        assert measure_one(p,{"kind":"XLSX_MACRO_PRESENT"})[1] is True
