from __future__ import annotations

import hashlib
import pathlib
import tempfile
import zipfile

from canonical.runtime.content_addressed_artifact_measurement_v1 import measure
from canonical.runtime.measured_typed_acceptance_program_v1 import verify
from canonical.runtime.typed_acceptance_program_v1 import PROGRAM_SCHEMA


def _write_zip(path: pathlib.Path, members: dict[str, str]):
    with zipfile.ZipFile(path, "w") as zf:
        for name, text in members.items():
            zf.writestr(name, text)


def test_file_identity_measurements_are_content_addressed():
    with tempfile.TemporaryDirectory() as td:
        root=pathlib.Path(td)
        p=root/"sample.txt"
        p.write_text("abc",encoding="utf-8")
        out=measure("sample.txt",[
            {"id":"basename","kind":"FILE_BASENAME"},
            {"id":"suffix","kind":"FILE_SUFFIX"},
            {"id":"size","kind":"FILE_SIZE_BYTES"},
        ],root=root)
        assert out["status"]=="MEASURED",out
        assert out["values"]=={"basename":"sample.txt","suffix":".txt","size":3}
        assert out["artifact_sha256"]==hashlib.sha256(b"abc").hexdigest()
        assert out["proposal_supplied_measurement_values"] is False


def test_xlsx_sheet_structure_measurements():
    xml='<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheets><sheet name="Summary"/><sheet name="Data"/></sheets></workbook>'
    with tempfile.TemporaryDirectory() as td:
        root=pathlib.Path(td)
        p=root/"book.xlsx"
        _write_zip(p,{"xl/workbook.xml":xml})
        out=measure("book.xlsx",[
            {"id":"has_summary","kind":"XLSX_SHEET_EXISTS","sheet_name":"summary","case_sensitive":False},
            {"id":"sheet_count","kind":"XLSX_SHEET_COUNT"},
        ],root=root)
        assert out["status"]=="MEASURED",out
        assert out["values"]=={"has_summary":True,"sheet_count":2}


def test_docx_text_and_structure_measurements():
    xml='''<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Quarterly Review</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>42</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:body></w:document>'''
    with tempfile.TemporaryDirectory() as td:
        root=pathlib.Path(td)
        p=root/"report.docx"
        _write_zip(p,{"word/document.xml":xml})
        out=measure("report.docx",[
            {"id":"has_title","kind":"DOCX_TEXT_CONTAINS","text":"quarterly review","case_sensitive":False},
            {"id":"paragraphs","kind":"DOCX_PARAGRAPH_COUNT"},
            {"id":"tables","kind":"DOCX_TABLE_COUNT"},
        ],root=root)
        assert out["status"]=="MEASURED",out
        assert out["values"]=={"has_title":True,"paragraphs":1,"tables":1}


def test_pptx_slide_and_text_measurements():
    s1='<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><p:cSld><a:t>Executive Summary</a:t></p:cSld></p:sld>'
    s2='<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><p:cSld><a:t>Appendix</a:t></p:cSld></p:sld>'
    with tempfile.TemporaryDirectory() as td:
        root=pathlib.Path(td)
        p=root/"deck.pptx"
        _write_zip(p,{"ppt/slides/slide1.xml":s1,"ppt/slides/slide2.xml":s2})
        out=measure("deck.pptx",[
            {"id":"slides","kind":"PPTX_SLIDE_COUNT"},
            {"id":"has_summary","kind":"PPTX_TEXT_CONTAINS","text":"Executive Summary"},
        ],root=root)
        assert out["status"]=="MEASURED",out
        assert out["values"]=={"slides":2,"has_summary":True}


def test_path_escape_fails_closed():
    with tempfile.TemporaryDirectory() as td:
        out=measure("../outside.txt",[{"id":"size","kind":"FILE_SIZE_BYTES"}],root=td)
        assert out["status"]=="FAIL_CLOSED"


def test_measured_typed_acceptance_uses_artifact_derived_values_only():
    xml='<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheets><sheet name="Summary"/></sheets></workbook>'
    with tempfile.TemporaryDirectory() as td:
        root=pathlib.Path(td)
        p=root/"book.xlsx"
        _write_zip(p,{"xl/workbook.xml":xml})
        program={
            "schema":PROGRAM_SCHEMA,
            "fields":[
                {"id":"has_summary","type":"boolean","dimension":"dimensionless","source":"candidate"},
                {"id":"sheet_count","type":"integer","dimension":"count","source":"candidate"},
            ],
            "accept_when":{"op":"and","args":[
                {"op":"ref","id":"has_summary"},
                {"op":"ge","left":{"op":"ref","id":"sheet_count"},"right":{"op":"const","type":"integer","dimension":"count","value":1}},
            ]},
        }
        out=verify(program,artifact_path="book.xlsx",measurements=[
            {"id":"has_summary","kind":"XLSX_SHEET_EXISTS","sheet_name":"Summary"},
            {"id":"sheet_count","kind":"XLSX_SHEET_COUNT"},
        ],trusted_values={},root=str(root))
        assert out["pass"] is True,out
        assert out["proposal_supplied_candidate_values"] is False
        assert out["measurement_receipt"]["values"]["has_summary"] is True


def test_measured_typed_acceptance_falsifies_actual_artifact_failure():
    xml='<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheets><sheet name="Data"/></sheets></workbook>'
    with tempfile.TemporaryDirectory() as td:
        root=pathlib.Path(td)
        p=root/"book.xlsx"
        _write_zip(p,{"xl/workbook.xml":xml})
        program={
            "schema":PROGRAM_SCHEMA,
            "fields":[{"id":"has_summary","type":"boolean","dimension":"dimensionless","source":"candidate"}],
            "accept_when":{"op":"ref","id":"has_summary"},
        }
        out=verify(program,artifact_path="book.xlsx",measurements=[
            {"id":"has_summary","kind":"XLSX_SHEET_EXISTS","sheet_name":"Summary"},
        ],trusted_values={},root=str(root))
        assert out["pass"] is False
        assert out["status"]=="FALSIFIED__MEASURED_TYPED_ACCEPTANCE"


def test_measurement_type_mismatch_fails_closed():
    with tempfile.TemporaryDirectory() as td:
        root=pathlib.Path(td)
        p=root/"x.txt"
        p.write_text("abc",encoding="utf-8")
        program={
            "schema":PROGRAM_SCHEMA,
            "fields":[{"id":"size","type":"number","dimension":"bytes","source":"candidate"}],
            "accept_when":{"op":"ge","left":{"op":"ref","id":"size"},"right":{"op":"const","type":"number","dimension":"bytes","value":1.0}},
        }
        out=verify(program,artifact_path="x.txt",measurements=[
            {"id":"size","kind":"FILE_SIZE_BYTES"},
        ],trusted_values={},root=str(root))
        assert out["status"]=="FAIL_CLOSED"
        assert out["reason"]=="PROGRAM_MEASUREMENT_TYPE_MISMATCH"
