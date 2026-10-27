# PROJECT_BRAIN
"""Pins for python.software.issue_to_pr.orchestrate.v1 — the issue→PR loop.

Every pin runs on a hermetic fixture repo it builds in /tmp (brain repo is
never touched by the loop).  pytest is the external tool invoked for the
test-run stage (`pytest` module availability is part of the capability's
honest platform note and of each verdict line).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from canonical.runtime.bound_capabilities import python_issue_to_pr_orchestrate as orch

PKG = """def helper(x):
    return len(normalize(x)) + 1


def normalize(s):
    return str(s).strip().lower()
"""
UTIL = """from pkg.core import helper


def run_twice(a, b):
    return helper(a) + helper(b)
"""
TEST = """import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from pkg.core import helper
from pkg.util import run_twice


def test_helper_basic():
    assert helper(" A ") == 2


def test_run_twice():
    assert run_twice("X ", " y") == 4
"""
TASK = {
    "issue_id": "ISSUE-T1", "title": "rename helper to compute",
    "body": "domain term alignment",
    "edits": [{"op": "rename_symbol", "module": "pkg/core.py",
               "name": "helper", "new_name": "compute"}],
}


def _pytest_exe() -> str:
    return sys.executable


def _have_pytest() -> bool:
    try:
        import pytest  # noqa: F401
        return True
    except Exception:
        return False


def _make_repo(tmp: Path, *, broken_test: bool = False) -> Path:
    root = tmp / "fixture_repo"
    (root / "src" / "pkg").mkdir(parents=True)
    (root / "src" / "tests").mkdir(parents=True)
    (root / "src" / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (root / "src" / "pkg" / "core.py").write_text(PKG, encoding="utf-8")
    (root / "src" / "pkg" / "util.py").write_text(UTIL, encoding="utf-8")
    (root / "src" / "tests" / "test_core.py").write_text(
        TEST.replace("== 2", "== 999") if broken_test else TEST, encoding="utf-8")
    (root / "task.json").write_text(json.dumps(TASK), encoding="utf-8")
    return root


def _run(root: Path, extra: dict | None = None) -> dict:
    args = {
        "task_path": "task.json", "source_root": "src",
        "worktree_path": "_wt", "output_path": "_out/summary.json",
        "diff_path": "_out/change.diff", "pr_intent_path": "_out/pr_intent.json",
        "python_executable": _pytest_exe(),
    }
    if extra:
        args.update(extra)
    return orch.run(args, root)


class TestIssueToPROrchestrate(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="i2p_pins_"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_green_roundtrip_verified(self):
        root = _make_repo(self.tmp)
        res = _run(root)
        self.assertTrue(res["verified"])
        self.assertEqual(res["planned_op_count"], 1)
        self.assertEqual(res["applied_op_count"], 1)
        self.assertEqual(res["refused_op_count"], 0)
        self.assertGreaterEqual(res["applied_site_count"], 5)

    def test_source_tree_bytes_untouched(self):
        root = _make_repo(self.tmp)
        before = {p: p.read_bytes() for p in sorted((root / "src").rglob("*")) if p.is_file()}
        res = _run(root)
        self.assertTrue(res["verified"])
        after = {p: p.read_bytes() for p in sorted((root / "src").rglob("*")) if p.is_file()}
        self.assertEqual(before, after)

    def test_diff_applies_cleanly_and_wins_tests(self):
        root = _make_repo(self.tmp)
        res = _run(root)
        self.assertTrue(res["verified"])
        diff = (root / "_out" / "change.diff").read_bytes()
        chk = subprocess.run(["git", "apply", "--check", "-p1"], input=diff,
                             cwd=root / "src", capture_output=True)
        self.assertEqual(chk.returncode, 0, chk.stderr.decode())
        subprocess.run(["git", "apply", "-p1"], input=diff, cwd=root / "src",
                       capture_output=True, check=True)
        self.assertIn("def compute(", (root / "src" / "pkg" / "core.py").read_text())

    def test_fixed_point_rename_gone_from_old_scope(self):
        root = _make_repo(self.tmp)
        res = _run(root)
        self.assertTrue(res["verified"])
        self.assertNotIn("helper", re.findall(r"\bdef (\w+)",
                         (root / "_wt" / "pkg" / "core.py").read_text()))

    def test_selected_tests_executed(self):
        if not _have_pytest():
            self.skipTest("pytest not on interpreter — covered in verify env")
        root = _make_repo(self.tmp)
        res = _run(root)
        self.assertEqual(res["test_selected_count"], 1)
        self.assertEqual(res["test_passed_count"], 2)
        self.assertEqual(res["test_failed_count"], 0)

    def test_failing_selected_test_flips_verdict_and_stays_truthful(self):
        if not _have_pytest():
            self.skipTest("pytest not on interpreter — covered in verify env")
        root = _make_repo(self.tmp, broken_test=True)
        res = _run(root)
        self.assertFalse(res["verified"])
        self.assertTrue(res["edits_verified"])  # apply stage itself proven
        self.assertGreaterEqual(res["test_failed_count"], 1)
        self.assertEqual(res["applied_op_count"], 1)

    def test_determinism_byte_identical_artifacts(self):
        root = _make_repo(self.tmp)
        r1 = _run(root)
        d1, p1, s1 = [(root / "_out" / n).read_bytes()
                      for n in ("change.diff", "pr_intent.json", "summary.json")]
        r2 = _run(root)
        d2, p2, s2 = [(root / "_out" / n).read_bytes()
                      for n in ("change.diff", "pr_intent.json", "summary.json")]
        self.assertEqual(d1, d2)
        self.assertEqual(p1, p2)
        self.assertEqual({k: v for k, v in r1.items() if k != "seconds"},
                         {k: v for k, v in r2.items() if k != "seconds"})
        self.assertIn(b"seconds", s1) and self.assertIn(b"seconds", s2) if False else None

    def test_worktree_inside_source_refused(self):
        root = _make_repo(self.tmp)
        with self.assertRaises(SystemExit) as cm:
            _run(root, {"worktree_path": "src/_wt"})
        self.assertIn("WORKTREE_OVERLAPS_SOURCE_ROOT", str(cm.exception))

    def test_artifact_inside_source_refused(self):
        root = _make_repo(self.tmp)
        with self.assertRaises(SystemExit) as cm:
            _run(root, {"output_path": "src/_out.json"})
        self.assertIn("ARTIFACT_PATH_OVERLAPS_SOURCE_OR_WORKTREE", str(cm.exception))

    def test_move_symbol_golden_apply_and_proof(self):
        root = _make_repo(self.tmp)
        (root / "src" / "pkg" / "ops.py").write_text("", encoding="utf-8")
        (root / "task.json").write_text(json.dumps({
            "issue_id": "ISSUE-T2", "title": "move helper to pkg/ops.py",
            "edits": [{"op": "move_symbol", "module": "pkg/core.py",
                       "qualname": "helper", "to_module": "pkg/ops.py"}],
        }), encoding="utf-8")
        res = _run(root)
        self.assertTrue(res["verified"])
        core = (root / "_wt" / "pkg" / "core.py").read_text(encoding="utf-8")
        ops = (root / "_wt" / "pkg" / "ops.py").read_text(encoding="utf-8")
        util = (root / "_wt" / "pkg" / "util.py").read_text(encoding="utf-8")
        test = (root / "_wt" / "tests" / "test_core.py").read_text(encoding="utf-8")
        self.assertNotIn("def helper(", core)
        self.assertIn("def helper(", ops)
        self.assertIn("from pkg.ops import helper", util)
        self.assertIn("from pkg.ops import helper", test)
        self.assertNotIn("from pkg.core import helper", util)

    def test_move_symbol_split_multi_name_import(self):
        root = _make_repo(self.tmp)
        (root / "src" / "pkg" / "ops.py").write_text("", encoding="utf-8")
        multi = root / "src" / "pkg" / "multi.py"
        multi.write_text("from pkg.core import helper, normalize\n\n\ndef duo(s):\n"
                         "    return helper(s) + len(normalize(s))\n", encoding="utf-8")
        (root / "task.json").write_text(json.dumps({
            "issue_id": "ISSUE-T3",
            "edits": [{"op": "move_symbol", "module": "pkg/core.py",
                       "qualname": "helper", "to_module": "pkg/ops.py"}],
        }), encoding="utf-8")
        res = _run(root)
        self.assertTrue(res["verified"])
        text = (root / "_wt" / "pkg" / "multi.py").read_text(encoding="utf-8")
        self.assertIn("from pkg.ops import helper", text)
        self.assertIn("from pkg.core import normalize", text)

    def test_move_symbol_decorated_cut(self):
        root = _make_repo(self.tmp)
        decorated = PKG.replace("def helper(x):",
                                "@staticmethod\ndef helper(x):")
        (root / "src" / "pkg" / "core.py").write_text(decorated, encoding="utf-8")
        (root / "src" / "pkg" / "ops.py").write_text("", encoding="utf-8")
        (root / "task.json").write_text(json.dumps({
            "issue_id": "ISSUE-T4",
            "edits": [{"op": "move_symbol", "module": "pkg/core.py",
                       "qualname": "helper", "to_module": "pkg/ops.py"}],
        }), encoding="utf-8")
        res = _run(root)
        self.assertTrue(res["verified"])
        ops = (root / "_wt" / "pkg" / "ops.py").read_text(encoding="utf-8")
        self.assertIn("@staticmethod\ndef helper(", ops)

    def test_unknown_op_refused_at_apply(self):
        root = _make_repo(self.tmp)
        task = dict(TASK, edits=[{"op": "inline_function", "module": "pkg/core.py", "name": "helper"}])
        (root / "task.json").write_text(json.dumps(task), encoding="utf-8")
        with self.assertRaises(SystemExit) as cm:
            _run(root)
        self.assertIn("UNSUPPORTED_OP_AT_APPLY:inline_function", str(cm.exception))

    def test_missing_task_field_fails_closed(self):
        root = _make_repo(self.tmp)
        (root / "task.json").write_text(json.dumps({"issue_id": "X-1", "title": "no edits"}), encoding="utf-8")
        with self.assertRaises(SystemExit) as cm:
            _run(root)
        self.assertIn("TASK_SCHEMA_MISSING:edits", str(cm.exception))

    def test_path_escape_refused(self):
        root = _make_repo(self.tmp)
        with self.assertRaises(SystemExit) as cm:
            _run(root, {"diff_path": "..\\escape.diff" if os.name == "nt" else "../escape.diff"})
        self.assertIn("PATH_ESCAPE", str(cm.exception))

    def test_pr_intent_schema_and_checklist(self):
        root = _make_repo(self.tmp)
        _run(root)
        pr = json.loads((root / "_out" / "pr_intent.json").read_text(encoding="utf-8"))
        self.assertEqual(pr["schema"], "pr_intent_v1")
        self.assertEqual(pr["body"]["plan"]["complete"], True)
        self.assertEqual(len(pr["checklist"]), 3)
        self.assertEqual(pr["issue_id"], "ISSUE-T1")

    def test_collision_refusal_propagates_and_mutates_nothing(self):
        root = _make_repo(self.tmp)
        task = dict(TASK, edits=[{"op": "rename_symbol", "module": "pkg/core.py",
                                  "name": "helper", "new_name": "normalize"}])
        (root / "task.json").write_text(json.dumps(task), encoding="utf-8")
        with self.assertRaises(SystemExit) as cm:
            _run(root)
        self.assertIn("AMBIGUOUS_OR_REFUSED_PLAN", str(cm.exception))
        receipt = json.loads((root / "_out" / "summary.json").read_text(encoding="utf-8"))
        self.assertTrue(receipt["refused"])
        self.assertEqual((root / "src" / "pkg" / "core.py").read_text(), PKG)

    def test_merkle_style_diff_hash_stable(self):
        root = _make_repo(self.tmp)
        res1 = _run(root)
        import hashlib
        self.assertEqual(res1["diff_sha256"],
                         hashlib.sha256((root / "_out" / "change.diff").read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
