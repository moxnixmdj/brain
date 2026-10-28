"""Adversarial review-coverage controls for evidence, scope and scratch safety."""
from __future__ import annotations

import hashlib
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.bound_capabilities import python_review_diff_coverage_gate as gate

DIFF = """--- a/m.py
+++ b/m.py
@@ -1,2 +1,2 @@
 def f():
-    return 0
+    return 1
"""


class ReviewCoverageAdversarialTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="brain-coverage-controls-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.anchor = self.root / "anchor"
        (self.anchor / "tests").mkdir(parents=True)
        (self.anchor / "m.py").write_text("def f():\n    return 0\n")
        (self.root / "patch.diff").write_text(DIFF)
        (self.root / "out").mkdir()

    def invoke(self, **kwargs):
        return gate.run({"anchor_path": "anchor", "diff_path": "patch.diff",
                         "output_path": "out/report.json", "python_executable": sys.executable,
                         "timeout_s": 30, **kwargs}, self.root)

    def test_unimported_changed_module_is_not_full_coverage(self):
        (self.anchor / "tests/test_other.py").write_text("def test_other():\n    assert 1 + 1 == 2\n")
        result = self.invoke()
        self.assertFalse(result["verified"], result)
        self.assertNotEqual(result["gate"], "PASS")

    def test_skipped_only_suite_cannot_certify_coverage(self):
        (self.anchor / "tests/test_other.py").write_text(
            "import pytest\nfrom m import f\n@pytest.mark.skip(reason='not run')\n"
            "def test_skipped():\n    assert f() == 1\n")
        with self.assertRaisesRegex(SystemExit, "EVIDENCE|SUITE"):
            self.invoke()

    def test_configured_and_candidate_tests_run_in_one_coverage_session(self):
        (self.anchor / "pytest.ini").write_text("[pytest]\npython_files = check_*.py\ntestpaths = configured\n")
        (self.anchor / "configured").mkdir()
        (self.anchor / "configured/check_state.py").write_text(
            "import builtins\ndef test_configured():\n    builtins.brain_gate_flag = True\n")
        (self.anchor / "tests/test_other.py").write_text(
            "import builtins\nfrom m import f\ndef test_interaction():\n"
            "    assert f() == (0 if getattr(builtins, 'brain_gate_flag', False) else 1)\n")
        with self.assertRaisesRegex(SystemExit, "SUITE_RED"):
            self.invoke()

    def test_test_file_rewriting_is_rejected(self):
        (self.anchor / "tests/test_other.py").write_text(
            "from pathlib import Path\nfrom m import f\n"
            "def test_rewrite():\n    Path(__file__).write_text('def test_f(): assert True\\n')\n"
            "    assert f() == 1\n")
        with self.assertRaisesRegex(SystemExit, "INPUT_CHANGED|EVIDENCE"):
            self.invoke()

    def test_existing_scratch_name_is_never_deleted(self):
        (self.anchor / "tests/test_other.py").write_text("from m import f\ndef test_f():\n    assert f() == 1\n")
        previous = self.root / "out" / ("_cov_tree_" + hashlib.sha256(DIFF.encode()).hexdigest()[:16])
        previous.mkdir()
        sentinel = previous / "keep"
        sentinel.write_bytes(b"do not remove")
        self.invoke()
        self.assertEqual(sentinel.read_bytes(), b"do not remove")

    def test_output_cannot_replace_input_diff_or_anchor_files(self):
        (self.anchor / "tests/test_other.py").write_text("from m import f\ndef test_f(): assert f() == 1\n")
        for output in ("patch.diff", "anchor/m.py"):
            with self.subTest(output=output):
                before = (self.root / output).read_bytes()
                with self.assertRaisesRegex(SystemExit, "OUTPUT_"):
                    self.invoke(output_path=output)
                self.assertEqual((self.root / output).read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
