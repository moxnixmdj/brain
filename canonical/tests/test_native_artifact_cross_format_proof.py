from __future__ import annotations

import inspect
import shutil
import unittest

from canonical.runtime import native_artifact_cross_format_candidate as candidate
from canonical.runtime import native_artifact_cross_format_proof as proof


class NativeArtifactCrossFormatTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        deps = proof._deps()
        if isinstance(deps, Exception):
            raise unittest.SkipTest("cross-format dependencies unavailable: " + type(deps).__name__)
        if not shutil.which("pdftotext") or not shutil.which("pdfinfo"):
            raise unittest.SkipTest("Poppler unavailable")

    def test_candidate_does_not_import_proof_or_format_readers(self):
        src = inspect.getsource(candidate)
        self.assertNotIn("native_artifact_cross_format_proof", src)
        self.assertNotIn("openpyxl", src)
        self.assertNotIn("python-docx", src)
        self.assertNotIn("pptx", src)

    def test_four_format_roundtrip_and_preservation(self):
        out = proof.run_cross_format_preflight(candidate.apply_explicit_native_edit)
        self.assertTrue(out["all_pass"], out)
        self.assertEqual(out["format_count"], 4)
        self.assertEqual(out["passed"], 4)

    def test_unknown_format_fails_closed(self):
        out = candidate.apply_explicit_native_edit(
            "nope.bin", "out.bin", {"format": "unknown", "old": "A", "new": "B"}
        )
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "FORMAT_UNSUPPORTED")

    def test_noop_edit_fails_closed(self):
        out = candidate.apply_explicit_native_edit(
            "nope.docx", "out.docx", {"format": "docx", "old": "A", "new": "A"}
        )
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "TEXT_EDIT_INVALID")


if __name__ == "__main__":
    unittest.main(verbosity=2)
