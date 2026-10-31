# PROJECT_BRAIN
"""Pins for python.repo.diff_apply_full_testgate.v1 — the pre-merge
apply+full-suite gate.  Every pin declares its world; every failure mode
is exercised by a paired world that makes the old behavior visible.

Run: python -m pytest canonical/tests/test_python_repo_diff_apply_full_testgate_v1.py -q
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.bound_capabilities import (
    python_repo_diff_apply_full_testgate as gate,
)

PY = sys.executable

ANCHOR_CORE = """def helper(x: int) -> int:
    return x + 1
"""

ANCHOR_UTIL = """from pkg.core import helper


def twice(a: int) -> int:
    return helper(a) * 2
"""

ANCHOR_TEST = """import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from pkg.util import twice


def test_twice():
    assert twice(2) == 6


def test_twice_zero():
    assert twice(0) == 2
"""

# rename helper -> compute, tests updated accordingly (a green refactor)
GREEN_DIFF = """--- a/pkg/core.py
+++ b/pkg/core.py
@@ -1,2 +1,2 @@
-def helper(x: int) -> int:
+def compute(x: int) -> int:
     return x + 1
--- a/pkg/util.py
+++ b/pkg/util.py
@@ -1,5 +1,5 @@
-from pkg.core import helper
+from pkg.core import compute
 
 
 def twice(a: int) -> int:
-    return helper(a) * 2
+    return compute(a) * 2
"""

# same rename but util.py NOT updated -> import breaks the whole suite
RED_DIFF = """--- a/pkg/core.py
+++ b/pkg/core.py
@@ -1,2 +1,2 @@
-def helper(x: int) -> int:
+def compute(x: int) -> int:
     return x + 1
--- a/tests/test_core.py
+++ b/tests/test_core.py
@@ -10,2 +10,4 @@
 def test_twice_zero():
     assert twice(0) == 2
+
+    assert False, "planted runtime break invisible to static triage"
"""


def _build_anchor(root: Path, with_tests: bool = True) -> Path:
    anchor = root / "anchor"
    (anchor / "pkg").mkdir(parents=True)
    (anchor / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (anchor / "pkg" / "core.py").write_text(ANCHOR_CORE, encoding="utf-8")
    (anchor / "pkg" / "util.py").write_text(ANCHOR_UTIL, encoding="utf-8")
    if with_tests:
        (anchor / "tests").mkdir(parents=True)
        (anchor / "tests" / "test_core.py").write_text(ANCHOR_TEST, encoding="utf-8")
    return anchor


def _tree_manifest(path: Path) -> str:
    rows = []
    for f in sorted(path.rglob("*")):
        if f.is_file() and "__pycache__" not in f.parts:
            rows.append(str(f.relative_to(path)) + ":" +
                        hashlib.sha256(f.read_bytes()).hexdigest())
    return hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest()


def _run(root: Path, diff_rel: str, anchor_rel: str = "anchor",
         out_rel: str = "_out/gate.json", py: str = PY):
    return gate.run({
        "anchor_path": anchor_rel,
        "diff_path": diff_rel,
        "output_path": out_rel,
        "python_executable": py,
        "timeout_s": 120,
    }, root)


class TestDiffApplyFullTestgate(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="applygate_"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def _fixture(self, diff: str, with_tests: bool = True) -> Path:
        root = self.tmp
        _build_anchor(root, with_tests=with_tests)
        (root / "d.diff").write_text(diff, encoding="utf-8")
        return root

    def test_green_refactor_gate_pass(self):
        root = self._fixture(GREEN_DIFF)
        res = _run(root, "d.diff")
        self.assertEqual(res["gate"], "UNRESOLVED__UNAUTHENTICATED_EVIDENCE")
        self.assertEqual(res["local_gate"], "PASS")
        self.assertFalse(res["verified"])
        self.assertEqual(res["tests_discovered"], 1)
        self.assertEqual(res["tests_failed"], 0)

    def test_runtime_break_fails_gate_with_named_test(self):
        root = self._fixture(RED_DIFF)
        res = _run(root, "d.diff")
        self.assertEqual(res["gate"], "FAIL")
        self.assertFalse(res["verified"])
        art = json.loads((root / "_out/gate.json").read_text())
        # collection ERROR row (helper import broken) or FAILED row: either
        # names the test module as evidence
        self.assertTrue(any("test_core" in t for t in art["failing_tests"]))

    def test_artifact_byte_identical_on_rerun(self):
        root = self._fixture(GREEN_DIFF)
        _run(root, "d.diff", out_rel="_out/g1.json")
        _run(root, "d.diff", out_rel="_out/g2.json")
        self.assertEqual((root / "_out/g1.json").read_bytes(),
                         (root / "_out/g2.json").read_bytes())

    def test_anchor_tree_never_mutated(self):
        root = self._fixture(RED_DIFF)
        before = _tree_manifest(root / "anchor")
        _run(root, "d.diff")
        self.assertEqual(before, _tree_manifest(root / "anchor"))

    def test_empty_diff_refuses(self):
        root = self._fixture(GREEN_DIFF)
        (root / "empty.diff").write_text("", encoding="utf-8")
        with self.assertRaises(SystemExit) as ctx:
            _run(root, "empty.diff")
        self.assertIn("DIFF_EMPTY", str(ctx.exception))

    def test_no_tests_discovered_refuses(self):
        root = self._fixture(GREEN_DIFF, with_tests=False)
        with self.assertRaises(SystemExit) as ctx:
            _run(root, "d.diff")
        self.assertIn("NO_TESTS_DISCOVERED", str(ctx.exception))

    def test_bogus_diff_refuses_apply(self):
        root = self._fixture(GREEN_DIFF)
        (root / "bad.diff").write_text(
            "--- a/pkg/core.py\n+++ b/pkg/core.py\n@@ -99,2 +99,2 @@\n-def nosuch():\n+def other():\n     pass\n",
            encoding="utf-8")
        with self.assertRaises(SystemExit) as ctx:
            _run(root, "bad.diff")
        self.assertIn("DIFF_DOES_NOT_APPLY", str(ctx.exception))
        # the refusal happened before any suite run: no gate artifact
        self.assertFalse((root / "_out/gate.json").exists())

    def test_path_escape_refuses(self):
        root = self._fixture(GREEN_DIFF)
        with self.assertRaises(SystemExit) as ctx:
            _run(root, "../outside.diff")
        self.assertIn("PATH_ESCAPE", str(ctx.exception))

    def test_missing_anchor_refuses(self):
        root = self._fixture(GREEN_DIFF)
        with self.assertRaises(SystemExit) as ctx:
            _run(root, "d.diff", anchor_rel="not_there")
        self.assertIn("PATH_MISSING", str(ctx.exception))

    def test_scratch_tree_removed_after_run(self):
        root = self._fixture(GREEN_DIFF)
        _run(root, "d.diff")
        leftovers = [p for p in (root / "_out").iterdir() if p.name.startswith("_gate_tree_")]
        self.assertEqual(leftovers, [])

    def test_git_absent_refuses_loudly(self):
        root = self._fixture(GREEN_DIFF)
        real_run = gate.subprocess.run
        def fake_run(cmd, **kw):
            if cmd[:2] == ["git", "--version"]:
                class R: returncode, stdout = 127, ""
                return R()
            return real_run(cmd, **kw)
        gate.subprocess.run = fake_run
        try:
            with self.assertRaises(SystemExit) as ctx:
                _run(root, "d.diff")
            self.assertIn("GIT_UNAVAILABLE", str(ctx.exception))
        finally:
            gate.subprocess.run = real_run

    def test_gate_pass_only_when_both_stages_green(self):
        # triage-visible static cleanliness does NOT imply the integration
        # gate: RED_DIFF is syntactically clean everywhere yet fails.
        root = self._fixture(RED_DIFF)
        res = _run(root, "d.diff")
        art = json.loads((root / "_out/gate.json").read_text())
        self.assertEqual(art["gate"], "FAIL")
        self.assertEqual(art["tests_discovered"], 1)
        # and the same world with the fix lands on PASS:
        root2 = root / "w2"
        root2.mkdir()
        _build_anchor(root2)
        (root2 / "d.diff").write_text(GREEN_DIFF, encoding="utf-8")
        res2 = _run(root2, "d.diff")
        self.assertEqual(res2["gate"], "UNRESOLVED__UNAUTHENTICATED_EVIDENCE")
        self.assertEqual(res2["local_gate"], "PASS")

    def test_artifact_schema_and_diff_sha(self):
        root = self._fixture(GREEN_DIFF)
        _run(root, "d.diff")
        art = json.loads((root / "_out/gate.json").read_text())
        for key in ("schema", "anchor_path", "diff_sha256", "tests_discovered",
                    "test_files", "failing_tests", "gate", "gate_law", "complete"):
            self.assertIn(key, art)
        expect = hashlib.sha256(GREEN_DIFF.encode("utf-8")).hexdigest()
        self.assertEqual(art["diff_sha256"], expect)


if __name__ == "__main__":
    unittest.main()
