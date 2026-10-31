"""Pins for python.review.diff_mutation_gate.v1.

A mutation gate is only honest if every answer is the truth the
measurement produced (kill/survive lists come from subprocess exit
codes, not from heuristics) and every escape hatch is a named refusal.
Fifteen tests: happy-path kills, stitching witness, layout handling,
base-red refusal, determinism, diff-application failures, and every
pre-action refuse row.

The suite fixture is deliberately small so mutation runs are fast
(~0.1 s per mutant) without touching wall-clock flakiness: helper
matches the fixture's behaviour exactly, a shadowing lambda survives,
and the test kills every mutant the operator set can generate.
"""
from __future__ import annotations

import json
import os
import pathlib
import shutil
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from canonical.runtime.bound_capabilities import (
    python_review_diff_mutation_gate as mg,
)

CORE = '''"""Fixture used by the mutation-gate pins."""


def helper(n: int) -> int:
    """The one-parameter function under the microscope.

    Behaviour contract: == branch, arithmetic, bool, numeric literal.
    A suite that pins all four behaviours kills every mutant.
    """
    if n < 2:
        return n + 1
    if n == 3 and True:
        return n * 2
    return n - 0
'''

DIFF = '''\
diff --git a/pkg/core.py b/pkg/core.py
index 1000000..2000000 100644
--- a/pkg/core.py
+++ b/pkg/core.py
@@ -9,5 +9,5 @@
     """
-    if n < 2:
-        return n + 1
+    if n <= 1:
+        return n + 2
     if n == 3 and True:
         return n * 2
'''

# The honest-observer suite: fails whenever any one mutation lands.
TEST_KILLER = '''import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from pkg.core import helper


def test_arithmetic_is_pinned():
    assert helper(0) == 2   # n + 2 on the n==0 branch


def test_compare_is_pinned():
    assert helper(3) == 6   # n * 2 on the n==3 branch


def test_boundary_is_pinned():
    assert helper(1) == 3   # n + 2 below the branch
    assert helper(2) == 2   # fall-through
'''

TEST_BLIND = '''import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from pkg.core import helper


def test_only_one_branch_observed():
    assert helper(3) == 6
    # the <= branch (helper(0)/helper(1)) is never asserted:
    # arith-swap and numeric-bump mutants on `return n + 2` survive
'''

TEST_RED = '''import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from pkg.core import helper


def test_red_from_baseline():
    assert helper(0) == 999   # deliberately wrong: base world is red
'''


def _build(tree: pathlib.Path, extra: dict[str, str] | None = None,
           anchor_py: str = "pkg/core.py", anchor_tests: bool = True) -> pathlib.Path:
    """Anchor holds the OLD world + (in-world) tests; diff fixes it.

    extra keys are paths relative to the ANCHOR world (e.g. tests discovered
    by the gate live under the anchor, not under the tmp root).
    """
    (tree / "pkg").mkdir(parents=True, exist_ok=True)
    (tree / "pkg/__init__.py").write_text("", encoding="utf-8")
    (tree / "pkg/core.py").write_text(CORE, encoding="utf-8")
    anchor = tree / "_anchor/world"
    anchor.mkdir(parents=True, exist_ok=True)
    pkg_dir = anchor / pathlib.Path(anchor_py).parent
    pkg_dir.mkdir(parents=True, exist_ok=True)
    (pkg_dir / "__init__.py").write_text("", encoding="utf-8")
    (anchor / anchor_py).write_text(CORE, encoding="utf-8")
    for rel, text in (extra or {}).items():
        p = anchor / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    (tree / "_seeds").mkdir(exist_ok=True)
    diff = DIFF if anchor_py == "pkg/core.py" else DIFF.replace("pkg/core.py", anchor_py)
    (tree / "_seeds/seed.diff").write_text(diff, encoding="utf-8")
    return tree


def _run(tree: pathlib.Path, **overrides):
    args = {
        "anchor_path": "_anchor/world",
        "diff_path": "_seeds/seed.diff",
        "output_path": "_out/mutation.json",
        "python_executable": sys.executable,
        "timeout_s": 30,
    }
    args.update(overrides)
    res = mg.run(args, tree)
    art = json.loads((tree / "_out/mutation.json").read_text(encoding="utf-8"))
    return res, art


class TestDiffMutationGate(unittest.TestCase):

    maxDiff = None

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ------------------------------------------------- observe & kill

    def test_full_suite_kills_every_mutant_gate_pass(self):
        _build(self.tmp, extra={"tests/test_core.py": TEST_KILLER})
        res, art = _run(self.tmp)
        self.assertEqual(art["gate"], "UNRESOLVED__UNAUTHENTICATED_EVIDENCE")
        self.assertEqual(art["local_gate"], "PASS")
        self.assertEqual(res["gate"], "UNRESOLVED__UNAUTHENTICATED_EVIDENCE")
        self.assertEqual(res["local_gate"], "PASS")
        self.assertGreaterEqual(art["mutants_generated"], 5)
        self.assertEqual(art["mutants_survived"], 0)
        self.assertEqual(art["kill_ratio"], 1.0)
        self.assertTrue(art["complete"])
        self.assertFalse(res["verified"])

    def test_blind_suite_survives_witness_gate_fails(self):
        _build(self.tmp, extra={"tests/test_core.py": TEST_BLIND})
        res, art = _run(self.tmp)
        self.assertEqual(art["gate"], "FAIL")
        self.assertGreaterEqual(art["mutants_survived"], 1)
        self.assertFalse(art["complete"])
        ops = {s["operator"] for s in art["survivors"]}
        self.assertTrue(ops & {"numeric_bump", "compare_swap", "bool_swap",
                               "arith_swap", "aug_swap", "return_none"})
        # survivors must be confined to the diff's new-side changed lines
        target = art["changed_lines_targeted"]["pkg/core.py"]
        self.assertTrue(target, "changed lines list is non-empty")
        for s in art["survivors"]:
            self.assertIn(s["line"], set(target))

    def test_survivors_record_exact_line_and_operator(self):
        _build(self.tmp, extra={"tests/test_core.py": TEST_BLIND})
        res, art = _run(self.tmp)
        self.assertEqual(art["gate"], "FAIL")
        for row in art["survivors"]:
            self.assertEqual(row["file"], "pkg/core.py")
            self.assertIn(row["operator"], {"compare_swap", "arith_swap",
                                            "aug_swap", "bool_swap",
                                            "numeric_bump", "return_none"})
            self.assertIsInstance(row["line"], int)

    def test_mutants_never_leave_hunk_lines(self):
        _build(self.tmp, extra={"tests/test_core.py": TEST_BLIND})
        res, art = _run(self.tmp)
        target = set(art["changed_lines_targeted"]["pkg/core.py"])
        self.assertGreaterEqual(min(target), 9)   # hunk first line
        self.assertLessEqual(max(target), 13)     # hunk last line
        for s in art["survivors"]:
            self.assertIn(s["line"], target)

    def test_src_layout_resolves_pythonpath(self):
        # src-layout: pkg lives under src/, tests live under tests/ at root.
        _build(self.tmp, extra={"tests/test_core.py": TEST_KILLER.replace(
                   "parents[1]", 'parents[1] / "src"')},
               anchor_py="src/pkg/core.py")
        res, art = _run(self.tmp)
        self.assertEqual(art["gate"], "UNRESOLVED__UNAUTHENTICATED_EVIDENCE")
        self.assertEqual(art["local_gate"], "PASS")
        self.assertEqual(art["mutants_survived"], 0)

    # ------------------------------------------------- honesty gates

    def test_no_tests_refuses_loudly(self):
        _build(self.tmp)  # no tests/ directory
        with self.assertRaises(SystemExit) as ctx:
            _run(self.tmp)
        self.assertIn("NO_TESTS_DISCOVERED", str(ctx.exception))

    def test_base_world_red_refuses_without_mutating(self):
        _build(self.tmp, extra={"tests/test_core.py": TEST_RED})
        with self.assertRaises(SystemExit) as ctx:
            _run(self.tmp)
        reason = str(ctx.exception)
        self.assertIn("BASE_WORLD_RED", reason)
        # anchor never mutated
        self.assertEqual((self.tmp / "_anchor/world/pkg/core.py").read_text(), CORE)
        # diff never mutated
        self.assertEqual((self.tmp / "_seeds/seed.diff").read_text(), DIFF)

    def test_diff_does_not_apply_is_named(self):
        _build(self.tmp, extra={"tests/test_core.py": TEST_KILLER})
        # corrupt the hunk context -> git apply --check must reject
        bad = DIFF.replace("    if n == 3 and True:", "    ZZZ_NEVER_EXISTS_ZZZ")
        (self.tmp / "_seeds/seed.diff").write_text(bad, encoding="utf-8")
        with self.assertRaises(SystemExit) as ctx:
            _run(self.tmp)
        self.assertIn("DIFF_DOES_NOT_APPLY", str(ctx.exception))

    def test_artifact_byte_identical_reruns(self):
        w1 = self.tmp / "w1"
        w2 = self.tmp / "w2"
        for root in (w1, w2):
            _build(root, extra={"tests/test_core.py": TEST_KILLER})
            _run(root)
        a = (w1 / "_out/mutation.json").read_bytes()
        b = (w2 / "_out/mutation.json").read_bytes()
        self.assertEqual(a, b)
        # anchor and caller tree survive the whole measurement intact
        self.assertEqual((w2 / "pkg/core.py").read_text(), CORE)
        self.assertEqual((w2 / "_anchor/world/pkg/core.py").read_text(), CORE)
        # scratch lab deleted after the run
        self.assertFalse(list(w2.glob("_out/_mut_tree_*")))

    # ------------------------------------------------- pre-action refusals

    def test_anchor_missing_is_named(self):
        _build(self.tmp)
        shutil.rmtree(self.tmp / "_anchor/world")
        with self.assertRaises(SystemExit) as ctx:
            _run(self.tmp)
        self.assertIn("PATH_MISSING", str(ctx.exception))

    def test_anchor_not_directory_is_named(self):
        _build(self.tmp)
        shutil.rmtree(self.tmp / "_anchor/world")
        (self.tmp / "_anchor/world").parent.mkdir(parents=True, exist_ok=True)
        (self.tmp / "_anchor/world").write_text("not a dir", encoding="utf-8")
        # world must exist as path, then fail is_dir
        with self.assertRaises(SystemExit) as ctx:
            _run(self.tmp)
        self.assertIn("ANCHOR_NOT_DIRECTORY", str(ctx.exception))

    def test_diff_empty_is_named(self):
        _build(self.tmp)
        (self.tmp / "_seeds/seed.diff").write_text(" \n", encoding="utf-8")
        with self.assertRaises(SystemExit) as ctx:
            _run(self.tmp)
        self.assertIn("DIFF_EMPTY", str(ctx.exception))

    def test_path_escape_is_refused(self):
        _build(self.tmp)
        with self.assertRaises(SystemExit) as ctx:
            _run(self.tmp, anchor_path="../escape")
        self.assertIn("PATH_ESCAPE", str(ctx.exception))

    def test_missing_path_argument_is_named(self):
        with self.assertRaises(SystemExit) as ctx:
            mg.run({"anchor_path": "", "diff_path": "d", "output_path": "o"}, self.tmp)
        self.assertIn("MISSING_OR_INVALID_PATH_ARGUMENT", str(ctx.exception))

    def test_syntax_error_in_post_apply_file_refuses(self):
        _build(self.tmp, extra={"tests/test_core.py": TEST_KILLER})
        # diff content applies cleanly but leaves unparseable python behind:
        # pytest collection goes red -> BASE_WORLD_RED  (named, not a crash)
        broke = DIFF.replace("+        return n + 2\n",
                             "+        return n + +\n")
        (self.tmp / "_seeds/seed.diff").write_text(broke, encoding="utf-8")
        with self.assertRaises(SystemExit) as ctx:
            _run(self.tmp)
        self.assertIn("BASE_WORLD_RED", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
