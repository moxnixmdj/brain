from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import zipfile

from canonical.runtime import professional_artifact_type_semantic_receipt_v1 as a


def args(path, target):
    return {
      "path":path,
      "task_id":"task-x",
      "task_sha256":"a"*64,
      "target_artifact_type":target,
      "obligation_semantics_sha256":"b"*64,
      "obligation_universe_digest":"c"*64,
      "target_scope_id":"scope://professional-task-fulfillment/"+"d"*64,
    }


class ArtifactTypeSemanticReceiptV1Tests(unittest.TestCase):
    def test_real_pdf_matching_target_passes_and_emits_bridge_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"report.pdf";p.write_bytes(b"%PDF-1.7\nminimal")
            out=a.verify_and_receipt(args("report.pdf","PDF"),td)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["observed_artifact_type"],"PDF")
        self.assertEqual(out["receipt"]["schema"],a.BRIDGE_RECEIPT_SCHEMA)
        self.assertEqual(out["receipt"]["obligation_id"],a.OBLIGATION_ID)
        self.assertTrue(out["receipt"]["semantic_satisfaction_proved"])
        self.assertEqual(out["external_general_purpose_model_runtime_dependency_count"],0)
        self.assertFalse(out["quality_authority"])

    def test_png_renamed_pdf_does_not_pass_as_pdf(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"fake.pdf";p.write_bytes(b"\x89PNG\r\n\x1a\n"+"x".encode())
            out=a.verify_and_receipt(args("fake.pdf","PDF"),td)
        self.assertFalse(out["pass"])
        self.assertEqual(out["observed_artifact_type"],"PNG")
        self.assertFalse(out["suffix_consistent_with_observed_type"])
        self.assertIsNone(out["receipt"])

    def test_target_mismatch_fails_even_with_valid_bytes_and_suffix(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"report.pdf";p.write_bytes(b"%PDF-1.4\n")
            out=a.verify_and_receipt(args("report.pdf","PNG"),td)
        self.assertFalse(out["pass"])
        self.assertEqual(out["observed_artifact_type"],"PDF")
        self.assertTrue(out["suffix_consistent_with_observed_type"])

    def test_minimal_docx_container_is_observed_from_structure(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"doc.docx"
            with zipfile.ZipFile(p,"w") as z:
                z.writestr("word/document.xml","<w:document/>")
            out=a.verify_and_receipt(args("doc.docx","WORD"),td)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["observed_artifact_type"],"DOCX")
        self.assertEqual(out["target_artifact_type"],"DOCX")

    def test_unrecognized_zip_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"thing.docx"
            with zipfile.ZipFile(p,"w") as z:z.writestr("random.txt","x")
            with self.assertRaisesRegex(a.ArtifactTypeSemanticError,"ARTIFACT_TYPE_UNRECOGNIZED"):
                a.verify_and_receipt(args("thing.docx","DOCX"),td)

    def test_ambiguous_ooxml_container_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"thing.docx"
            with zipfile.ZipFile(p,"w") as z:
                z.writestr("word/document.xml","x")
                z.writestr("xl/workbook.xml","x")
            with self.assertRaisesRegex(a.ArtifactTypeSemanticError,"AMBIGUOUS_OOXML_TYPE"):
                a.verify_and_receipt(args("thing.docx","DOCX"),td)

    def test_unknown_target_type_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"report.pdf";p.write_bytes(b"%PDF-1.7\n")
            with self.assertRaisesRegex(a.ArtifactTypeSemanticError,"TARGET_ARTIFACT_TYPE_UNSUPPORTED"):
                a.verify_and_receipt(args("report.pdf","CAD"),td)

    def test_path_escape_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(a.ArtifactTypeSemanticError,"PATH_OUTSIDE_REPOSITORY"):
                a.verify_and_receipt(args("../outside.pdf","PDF"),td)

    def test_unknown_caller_field_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"report.pdf";p.write_bytes(b"%PDF-1.7\n")
            x=args("report.pdf","PDF");x["trust_me"]=True
            with self.assertRaisesRegex(a.ArtifactTypeSemanticError,"ARGS_UNKNOWN"):
                a.verify_and_receipt(x,td)


if __name__=="__main__":
    unittest.main(verbosity=2)
