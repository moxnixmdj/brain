from __future__ import annotations

import inspect
import tempfile
from pathlib import Path
import unittest
import zipfile

from canonical.runtime import native_artifact_cross_format_proof as proof
from canonical.runtime import native_artifact_unique_text_edit as candidate


class NativeArtifactCrossFormatTests(unittest.TestCase):
    def test_cross_format_grid(self):
        out = proof.run_grid(8)
        self.assertTrue(out["all_pass"], out)
        self.assertEqual(set(out["by_format"]), set(proof.FORMATS))
        for row in out["by_format"].values():
            self.assertEqual(row["pass"], row["total"])

    def test_candidate_does_not_depend_on_proof_or_hidden_oracle(self):
        src = inspect.getsource(candidate)
        self.assertNotIn("native_artifact_cross_format_proof", src)
        self.assertNotIn("_oracle", src)

    def test_ooxml_duplicate_visible_target_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "in.docx"
            dst = Path(td) / "out.docx"
            main = proof._make_ooxml(src, "docx", "DUP")
            with zipfile.ZipFile(src, "a") as z:
                payload = z.read(main).replace(b"KEEP", b"DUP")
                z.writestr(main, payload)
            out = candidate.apply_unique_text_edit(src, dst, old="DUP", new="NEW")
            self.assertEqual(out["status"], "FAIL_CLOSED", out)
            self.assertEqual(out["reason"], "VISIBLE_TEXT_TARGET_NOT_UNIQUE")
            self.assertFalse(dst.exists())

    def test_xlsx_shared_string_indirection_is_out_of_scope(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "in.xlsx"
            dst = Path(td) / "out.xlsx"
            main = "xl/sharedStrings.xml"
            with zipfile.ZipFile(src, "w") as z:
                z.writestr("[Content_Types].xml", proof._content_types(main))
                z.writestr("_rels/.rels", proof._root_rels(main))
                z.writestr(main, b'<sst xmlns="urn:x"><si><t>TARGET</t></si></sst>')
            out = candidate.apply_unique_text_edit(src, dst, old="TARGET", new="NEW")
            self.assertEqual(out["status"], "FAIL_CLOSED", out)
            self.assertEqual(out["reason"], "VISIBLE_TEXT_TARGET_NOT_UNIQUE")

    def test_pdf_duplicate_visible_target_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            from pypdf import PdfWriter
            from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
            src = Path(td) / "in.pdf"
            dst = Path(td) / "out.pdf"
            w = PdfWriter()
            page = w.add_blank_page(width=200, height=200)
            font = DictionaryObject({
                NameObject("/Type"):NameObject("/Font"),
                NameObject("/Subtype"):NameObject("/Type1"),
                NameObject("/BaseFont"):NameObject("/Helvetica"),
            })
            ref = w._add_object(font)
            page[NameObject("/Resources")] = DictionaryObject({
                NameObject("/Font"):DictionaryObject({NameObject("/F1"):ref})
            })
            stream = DecodedStreamObject()
            stream.set_data(b"BT /F1 12 Tf 20 100 Td (DUP) Tj 0 -20 Td (DUP) Tj ET")
            page[NameObject("/Contents")] = w._add_object(stream)
            with src.open("wb") as f:
                w.write(f)
            out = candidate.apply_unique_text_edit(src, dst, old="DUP", new="NEW")
            self.assertEqual(out["status"], "FAIL_CLOSED", out)
            self.assertEqual(out["reason"], "PDF_VISIBLE_TEXT_TARGET_NOT_UNIQUE")
            self.assertFalse(dst.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
