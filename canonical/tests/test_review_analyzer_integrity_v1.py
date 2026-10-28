"""Analyzer failures must not be converted into passing review gates."""
from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from canonical.runtime.bound_capabilities import (
    python_review_diff_security_gate as security,
    python_review_diff_static_triage as lint,
    python_review_diff_type_gate as types,
)

DIFF = """--- a/m.py
+++ b/m.py
@@ -1,2 +1,2 @@
 def f():
-    return 0
+    return 1
"""


class ReviewAnalyzerIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="brain-review-analyzer-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "tree").mkdir()
        (self.root / "tree/m.py").write_text("def f():\n    return 1\n")
        (self.root / "diff").write_text(DIFF)
        self.args = {"worktree_path": "tree", "diff_path": "diff", "output_path": "report.json"}

    @staticmethod
    def process(code, stdout="", stderr=""):
        return subprocess.CompletedProcess([], code, stdout, stderr)

    def test_ruff_invocation_failure_is_not_clean(self):
        responses = [self.process(0, "ruff 0.1\n"), self.process(2, "", "internal failure")]
        with mock.patch.object(lint.subprocess, "run", side_effect=responses):
            with self.assertRaisesRegex(SystemExit, "RUFF_INVOCATION_FAILED"):
                lint.run(self.args, self.root)

    def test_mypy_error_without_json_diagnostics_is_not_clean(self):
        responses = [self.process(0, "mypy 1.2\n"), self.process(1, "internal error\n")]
        with mock.patch.object(types.subprocess, "run", side_effect=responses):
            with self.assertRaisesRegex(SystemExit, "MYPY_OUTPUT"):
                types.run(self.args, self.root)

    def test_bandit_scan_errors_are_not_clean(self):
        data = json.dumps({"results": [], "errors": [{"filename": "m.py", "reason": "cannot scan"}]})
        responses = [self.process(0, "bandit 1.0\n"), self.process(1, data)]
        with mock.patch.object(security.subprocess, "run", side_effect=responses):
            with self.assertRaisesRegex(SystemExit, "BANDIT_SCAN"):
                security.run(self.args, self.root)

    def test_output_never_replaces_diff_or_changed_source(self):
        for module in (lint, types, security):
            for output in ("diff", "tree/m.py"):
                with self.subTest(module=module.__name__, output=output):
                    before = (self.root / output).read_bytes()
                    with self.assertRaisesRegex(SystemExit, "OUTPUT_"):
                        module.run({**self.args, "output_path": output}, self.root)
                    self.assertEqual((self.root / output).read_bytes(), before)

    def test_diff_target_cannot_escape_worktree(self):
        (self.root / "outside.py").write_text("value = 1\n")
        (self.root / "diff").write_text("--- a/../outside.py\n+++ b/../outside.py\n@@ -1 +1 @@\n-value = 0\n+value = 1\n")
        for module in (lint, types, security):
            with self.subTest(module=module.__name__):
                with self.assertRaisesRegex(SystemExit, "TOUCHED_PATH_ESCAPE"):
                    module.run(self.args, self.root)

    def test_non_python_diff_cannot_verify_python_analyzers(self):
        (self.root / "diff").write_text("--- a/readme.txt\n+++ b/readme.txt\n@@ -1 +1 @@\n-old\n+new\n")
        for module, name in ((lint, "ruff"), (types, "mypy"), (security, "bandit")):
            with self.subTest(name=name):
                with mock.patch.object(module.subprocess, "run", return_value=self.process(0, name + " 1.0\n")):
                    result = module.run(self.args, self.root)
                self.assertFalse(result["verified"], result)
                self.assertNotEqual(result["gate"], "PASS")


if __name__ == "__main__":
    unittest.main()
