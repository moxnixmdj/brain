import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from canonical.runtime.aa_briefcase_declared_source_parser_v1 import (
    SourceParseError,
    parse_all_declared_sources,
    parse_source_bytes,
)
from canonical.runtime.aa_briefcase_lossless_task_ingress_v1 import compile_ingress


def _xlsx_bytes():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "x.xlsx"
        with zipfile.ZipFile(p, "w") as z:
            z.writestr("[Content_Types].xml", "<Types/>")
            z.writestr(
                "xl/workbook.xml",
                '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Assumptions" sheetId="1" r:id="rId1"/></sheets></workbook>',
            )
            z.writestr(
                "xl/_rels/workbook.xml.rels",
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>',
            )
            z.writestr(
                "xl/worksheets/sheet1.xml",
                '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>NZD/USD</t></is></c><c r="B1"><f>A2*2</f><v>4</v></c></row></sheetData></worksheet>',
            )
        return p.read_bytes()


def _docx_bytes():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "x.docx"
        with zipfile.ZipFile(p, "w") as z:
            z.writestr("[Content_Types].xml", "<Types/>")
            z.writestr(
                "word/document.xml",
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Use latest FX vintage</w:t></w:r></w:p></w:body></w:document>',
            )
            z.writestr(
                "word/header1.xml",
                '<w:hdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:p><w:r><w:t>Halberd standard</w:t></w:r></w:p></w:hdr>',
            )
        return p.read_bytes()


class T(unittest.TestCase):
    def test_xlsx_extracts_cells_and_formula(self):
        out = parse_source_bytes(_xlsx_bytes(), source_path="week/model.xlsx")
        sheet = out["parsed"]["sheets"][0]
        self.assertEqual(sheet["name"], "Assumptions")
        self.assertEqual(sheet["cells"][0]["value"], "NZD/USD")
        self.assertEqual(sheet["cells"][1]["formula"], "A2*2")
        self.assertEqual(sheet["cells"][1]["value"], "4")

    def test_docx_extracts_document_and_header_text(self):
        out = parse_source_bytes(_docx_bytes(), source_path="shared/standards.docx")
        texts = "\n".join(x["text"] for x in out["parsed"]["parts"])
        self.assertIn("Use latest FX vintage", texts)
        self.assertIn("Halberd standard", texts)

    def test_json_preserves_scalar_paths(self):
        raw = json.dumps({"a": {"b": 3}, "x": [True, "z"]}).encode()
        out = parse_source_bytes(raw, source_path="week/chat.json")
        paths = {x["path"] for x in out["parsed"]["scalar_paths"]}
        self.assertEqual(paths, {"$.a.b", "$.x[0]", "$.x[1]"})

    def test_email_extracts_headers_and_body(self):
        raw = b"From: a@example.com\nTo: b@example.com\nSubject: Decision\n\nUse scenario Delta.\n"
        out = parse_source_bytes(raw, source_path="week/note.eml")
        self.assertEqual(out["parsed"]["headers"]["Subject"], "Decision")
        self.assertIn("Use scenario Delta", out["parsed"]["bodies"][0]["text"])

    def test_all_sources_gate_recomputes_hashes_and_parses(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "week").mkdir()
            (root / "shared").mkdir()
            xraw = _xlsx_bytes()
            draw = _docx_bytes()
            (root / "week" / "model.xlsx").write_bytes(xraw)
            (root / "shared" / "standards.docx").write_bytes(draw)
            ingress = compile_ingress({
                "task_id": "w1_t2",
                "task_text": "Create market_model.xlsx.\nUse all declared sources.\n",
                "deliverables": ["market_model.xlsx"],
                "source_files": [
                    {"path": "week/model.xlsx", "sha256": hashlib.sha256(xraw).hexdigest(), "size_bytes": len(xraw)},
                    {"path": "shared/standards.docx", "sha256": hashlib.sha256(draw).hexdigest(), "size_bytes": len(draw)},
                ],
            })
            out = parse_all_declared_sources(ingress, source_root=root)
            self.assertTrue(out["all_declared_sources_parsed"])
            self.assertEqual(out["source_count"], 2)
            self.assertEqual(out["unsupported_or_unparsed_source_count"], 0)

    def test_hash_mismatch_blocks_before_parse(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "week").mkdir()
            raw = b'{"x":1}'
            (root / "week" / "x.json").write_bytes(raw)
            ingress = compile_ingress({
                "task_id": "t",
                "task_text": "Use source.\n",
                "deliverables": ["out.txt"],
                "source_files": [
                    {"path": "week/x.json", "sha256": "0" * 64, "size_bytes": len(raw)}
                ],
            })
            with self.assertRaisesRegex(SourceParseError, "SHA_MISMATCH"):
                parse_all_declared_sources(ingress, source_root=root)

    def test_unsupported_format_fails_closed(self):
        with self.assertRaisesRegex(SourceParseError, "UNSUPPORTED_SOURCE_FORMAT"):
            parse_source_bytes(b"abc", source_path="week/x.bin")

    def test_representation_digest_is_deterministic(self):
        raw = _xlsx_bytes()
        a = parse_source_bytes(raw, source_path="week/model.xlsx")
        b = parse_source_bytes(raw, source_path="week/model.xlsx")
        self.assertEqual(a["parsed_representation_sha256"], b["parsed_representation_sha256"])
