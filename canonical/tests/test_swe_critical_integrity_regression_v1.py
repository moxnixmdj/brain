"""Adversarial controls for candidate repair, process cleanup and full-session gates."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

from canonical.runtime.bound_capabilities import python_coupled_software_repair_loop_v1 as coupled
from canonical.runtime.bound_capabilities import python_issue_to_pr_orchestrate as issue
from canonical.runtime.bound_capabilities import python_iterative_software_repair_loop_v1 as iterative
from canonical.runtime.bound_capabilities import python_dynamic_fault_localizer_v1 as localizer
from canonical.runtime.bound_capabilities import python_interprocedural_value_provenance_v1 as provenance
from canonical.runtime.bound_capabilities import python_provenance_guided_coupled_repair_v1 as guided
from canonical.runtime.bound_capabilities import python_repair_apply_verified_v1 as apply
from canonical.runtime.bound_capabilities import python_software_repair_loop_v1 as multi_repair
from canonical.runtime.bound_capabilities import python_test_guided_patch_search_v1 as patch


class RepairIntegrityControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="brain-repair-integrity-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "m.py"
        self.test = self.root / "test_m.py"
        self.source.write_text("def f():\n    return 0\n", encoding="utf-8")
        self.test.write_text("from m import f\ndef test_value():\n    assert f() == 1\n", encoding="utf-8")

    def args(self, output="result.json"):
        return {"source_root": ".", "test_paths": ["test_m.py"],
                "output_path": output, "timeout_s": 5,
                "max_candidates_per_file": 10, "max_total_candidates": 10}

    def test_iterative_and_coupled_reject_source_and_test_outputs(self):
        for engine in (iterative, coupled):
            for name in ("m.py", "test_m.py"):
                with self.subTest(engine=engine.__name__, output=name):
                    before_source, before_test = self.source.read_bytes(), self.test.read_bytes()
                    with self.assertRaisesRegex(Exception, "OUTPUT_OVERLAPS_INPUT"):
                        engine.run(self.args(name), self.root)
                    self.assertEqual(self.source.read_bytes(), before_source)
                    self.assertEqual(self.test.read_bytes(), before_test)

    def test_apply_rejects_source_and_test_outputs_even_on_passing_baseline(self):
        self.source.write_text("def f():\n    return 1\n", encoding="utf-8")
        for name in ("m.py", "test_m.py"):
            with self.subTest(output=name):
                before_source, before_test = self.source.read_bytes(), self.test.read_bytes()
                with self.assertRaisesRegex(Exception, "OUTPUT_OVERLAPS_INPUT"):
                    apply.run(self.args(name), self.root)
                self.assertEqual(self.source.read_bytes(), before_source)
                self.assertEqual(self.test.read_bytes(), before_test)

    def test_iterative_restores_trial_after_runner_infrastructure_error(self):
        test = ("import os\nfrom m import f\ndef test_value():\n"
                "    if f() == 1: os._exit(0)\n    assert f() == 99\n")
        self.test.write_text(test, encoding="utf-8")
        before = self.source.read_bytes()
        with self.assertRaisesRegex(Exception, "COMPLETION_MARKER_MISSING"):
            iterative.run(self.args(), self.root)
        self.assertEqual(self.source.read_bytes(), before)
        self.assertEqual(self.test.read_text(), test)

    def test_iterative_rejects_and_restores_test_modified_by_trial(self):
        test = ("from pathlib import Path\nfrom m import f\ndef test_value():\n"
                "    if f() == 1: Path(__file__).write_text('def test_value(): assert 1 == 1\\n')\n"
                "    assert f() == 1\n")
        self.test.write_text(test, encoding="utf-8")
        before = self.source.read_bytes()
        with self.assertRaisesRegex(Exception, "TEST_OR_SOURCE_MODIFIED"):
            iterative.run(self.args(), self.root)
        self.assertEqual(self.source.read_bytes(), before)
        self.assertEqual(self.test.read_text(), test)

    def test_localizers_reject_output_overwriting_source_or_test(self):
        for engine in (localizer, provenance):
            for output in ("m.py", "test_m.py"):
                with self.subTest(engine=engine.__name__, output=output):
                    before = (self.root / output).read_bytes()
                    with self.assertRaisesRegex(Exception, "OUTPUT_OVERLAPS_INPUT"):
                        engine.run({**self.args(), "output_path": output}, self.root)
                    self.assertEqual((self.root / output).read_bytes(), before)

    def test_localizers_restore_self_modified_test(self):
        test = ("from pathlib import Path\nfrom m import f\n"
                "Path(__file__).write_text('assert 1 == 1\\n')\nassert f() == 1\n")
        for engine in (localizer, provenance):
            with self.subTest(engine=engine.__name__):
                self.test.write_text(test)
                with self.assertRaisesRegex(Exception, "TEST_OR_SOURCE_MODIFIED"):
                    engine.run(self.args(), self.root)
                self.assertEqual(self.test.read_text(), test)

    def test_custom_test_argv_script_is_also_protected(self):
        oracle = self.root / "oracle.py"
        original = ("from pathlib import Path\nfrom m import f\n"
                    "Path(__file__).write_text('assert True\\n')\nassert f() == 1\n")
        for engine in (patch, iterative, coupled, guided, apply):
            with self.subTest(engine=engine.__name__):
                oracle.write_text(original)
                args = {**self.args(), "source_path": "m.py", "test_argv": [sys.executable, "oracle.py"]}
                with self.assertRaisesRegex(Exception, "TEST_OR_SOURCE_MODIFIED"):
                    engine.run(args, self.root)
                self.assertEqual(oracle.read_text(), original)

    def test_atomic_apply_never_overwrites_a_preexisting_temporary_name(self):
        neighbour = self.root / "m.py.brain_apply_tmp"
        neighbour.write_bytes(b"do not replace")
        self.source.chmod(0o755)
        apply._atomic_write(self.source, b"new source\n")
        self.assertEqual(neighbour.read_bytes(), b"do not replace")
        self.assertEqual(self.source.read_bytes(), b"new source\n")
        self.assertEqual(self.source.stat().st_mode & 0o777, 0o755)

    def test_multi_and_apply_restore_test_rewritten_during_baseline(self):
        test = ("from pathlib import Path\nfrom m import f\n"
                "Path(__file__).write_text('assert 1 == 1\\n')\nassert f() == 0\n")
        for engine in (multi_repair, apply):
            with self.subTest(engine=engine.__name__):
                self.test.write_text(test)
                before = self.source.read_bytes()
                with self.assertRaisesRegex(Exception, "TEST_OR_SOURCE_MODIFIED"):
                    engine.run(self.args(), self.root)
                self.assertEqual(self.test.read_text(), test)
                self.assertEqual(self.source.read_bytes(), before)

    def test_unparseable_script_failures_do_not_prove_a_nonmonotonic_valley(self):
        (self.root / "a.py").write_text("def a(x): return x < 3\n")
        (self.root / "b.py").write_text("def b(x): return x > 5\n")
        self.test.write_text("from a import a\nfrom b import b\n"
                             "assert a(3) and b(5)\nassert a(2) and b(6)\n"
                             "assert not a(4)\nassert not b(4)\n")
        result = coupled.run({**self.args(), "test_argv": [sys.executable, "test_m.py"],
                              "mutations_per_file": 12, "max_pair_candidates": 300}, self.root)
        self.assertTrue(result["pass"], result)
        self.assertIsNone(result["baseline_failure_score"])
        self.assertFalse(result["crossed_nonmonotonic_valley"])

    def test_guided_single_candidates_are_not_run_twice_before_replays(self):
        from unittest.mock import patch as mock_patch
        self.source.write_text("def helper(x): return x < 3\ndef f(x): return helper(x)\n")
        (self.root / "trace_fail.py").write_text("from m import f\nassert f(3)\n")
        (self.root / "trace_pass.py").write_text("from m import f\nassert f(2)\n")
        (self.root / "oracle.py").write_text("from m import f\nassert f(3)\nassert f(2)\nassert not f(4)\n")
        args = {"source_root": ".", "test_paths": ["trace_fail.py", "trace_pass.py"],
                "test_argv": [sys.executable, "oracle.py"], "output_path": "guided.json",
                "timeout_s": 4, "max_guided_files": 1, "mutations_per_file": 12}
        with mock_patch.object(guided._COUPLED, "_run_candidate", wraps=guided._COUPLED._run_candidate) as run:
            result = guided.run(args, self.root)
        self.assertTrue(result["pass"], result)
        self.assertEqual(result["winner_mode"], "SINGLE_GUIDED")
        self.assertEqual(run.call_count, result["single_candidates_tested"] + 2)

    def test_repair_families_obey_shared_soft_wall_budget(self):
        test = ("import time, unittest\nfrom m import f\n"
                "class TestSlow(unittest.TestCase):\n"
                "    def test_value(self):\n        time.sleep(0.2)\n        self.assertEqual(f(), 1)\n"
                "if __name__ == '__main__': unittest.main()\n")
        self.test.write_text(test)
        before = self.source.read_bytes()
        for engine in (iterative, coupled, multi_repair):
            with self.subTest(engine=engine.__name__):
                started = time.monotonic()
                try:
                    result = engine.run({**self.args(), "test_argv": [sys.executable, "test_m.py"],
                                         "max_wall_time_s": 0.65}, self.root)
                except Exception as exc:
                    self.assertRegex(str(exc), "TIMEOUT|BUDGET")
                else:
                    self.assertFalse(result["pass"], result)
                    self.assertIn("WALL_TIME_BUDGET", result["status"])
                self.assertLess(time.monotonic() - started, 2.0)
                self.assertEqual(self.source.read_bytes(), before)
                self.assertEqual(self.test.read_text(), test)

    def test_runner_handles_non_utf8_output(self):
        result = patch._run_tests(self.root, [sys.executable, "-c",
                                  "import os;os.write(1,b'\\xff');os.write(2,b'\\xfe')"],
                                  2, dict(os.environ))
        self.assertEqual(result["returncode"], 0)
        self.assertIn("\ufffd", result["stdout"])
        self.assertIn("\ufffd", result["stderr"])

    @unittest.skipUnless(os.name == "posix", "POSIX process-group control")
    def test_timeout_reaps_descendant_before_it_can_write(self):
        sentinel = self.root / "descendant_wrote"
        child = f"import pathlib,time;time.sleep(1.4);pathlib.Path({str(sentinel)!r}).write_text('alive')"
        parent = ("import subprocess,sys,time;"
                  f"subprocess.Popen([sys.executable,'-c',{child!r}],"
                  "stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);time.sleep(10)")
        result = patch._run_tests(self.root, [sys.executable, "-c", parent], 1, dict(os.environ))
        self.assertTrue(result["timed_out"])
        time.sleep(0.7)
        self.assertFalse(sentinel.exists())

    @unittest.skipUnless(os.name == "posix", "POSIX process-group control")
    def test_completed_parent_does_not_leave_background_child(self):
        sentinel = self.root / "post_success_child"
        child = f"import pathlib,time;time.sleep(0.5);pathlib.Path({str(sentinel)!r}).write_text('alive')"
        parent = ("import subprocess,sys;"
                  f"subprocess.Popen([sys.executable,'-c',{child!r}],"
                  "stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)")
        result = patch._run_tests(self.root, [sys.executable, "-c", parent], 2, dict(os.environ))
        self.assertEqual(result["returncode"], 0)
        time.sleep(0.8)
        self.assertFalse(sentinel.exists())


class CombinedSessionControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="brain-combined-session-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def pytest(self, cwd: Path, *targets: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", *targets],
                              cwd=cwd, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
                              capture_output=True, text=True, timeout=20)

    def issue_project(self, *, configured_interaction=False):
        src = self.root / "src"
        (src / "pkg").mkdir(parents=True)
        (src / "tests").mkdir()
        (src / "other").mkdir()
        (src / "pkg/__init__.py").write_text("")
        (src / "pkg/core.py").write_text("def helper(x):\n    return x + 1\n")
        (src / "conftest.py").write_text("import pytest\n@pytest.fixture(scope='session')\ndef bucket(): return []\n")
        if configured_interaction:
            (src / "pytest.ini").write_text("[pytest]\ntestpaths = other\npython_files = check_*.py\n")
            (src / "other/check_config.py").write_text("def test_config(bucket): bucket.append(1)\n")
            (src / "tests/test_visible.py").write_text(
                "from pkg.core import helper\nimport pkg.core as core\ndef test_visible(bucket):\n"
                "    assert helper(1) == 2\n    assert not bucket or not hasattr(core, 'compute')\n")
            targets = ("other/check_config.py", "tests/test_visible.py")
        else:
            (src / "pytest.ini").write_text("[pytest]\ntestpaths = other\n")
            (src / "other/test_unrelated.py").write_text("def test_unrelated(): assert 2 + 2 == 4\n")
            (src / "tests/test_visible.py").write_text(
                "from pkg.core import helper\nimport pkg.core as core\ndef test_visible(bucket):\n"
                "    assert helper(1) == 2\n    bucket.append(int(hasattr(core, 'compute')))\n")
            (src / "tests/test_dynamic.py").write_text(
                "def test_dynamic(bucket):\n    assert not bucket or bucket == [0]\n")
            targets = ("tests/test_visible.py", "tests/test_dynamic.py")
        (self.root / "task.json").write_text(json.dumps({"issue_id": "session-probe", "title": "Rename helper to compute",
            "edits": [{"op": "rename_symbol", "module": "pkg/core.py", "name": "helper", "new_name": "compute"}]}))
        return src, targets

    def run_issue(self):
        return issue.run({"task_path": "task.json", "source_root": "src", "worktree_path": "worktree",
                          "output_path": "out/result.json", "diff_path": "out/change.diff",
                          "pr_intent_path": "out/pr.json", "python_executable": sys.executable,
                          "timeout_s": 20}, self.root)

    def test_issue_rejects_cross_session_candidate_interaction(self):
        src, targets = self.issue_project()
        self.assertEqual(self.pytest(src, *targets).returncode, 0)
        result = self.run_issue()
        independent = self.pytest(self.root / "worktree", *targets)
        self.assertNotEqual(independent.returncode, 0, independent.stdout + independent.stderr)
        self.assertFalse(result["verified"], result)

    def test_issue_includes_configured_nonstandard_tests_in_combined_session(self):
        src, targets = self.issue_project(configured_interaction=True)
        self.assertEqual(self.pytest(src, *targets).returncode, 0)
        result = self.run_issue()
        independent = self.pytest(self.root / "worktree", *targets)
        self.assertNotEqual(independent.returncode, 0, independent.stdout + independent.stderr)
        self.assertFalse(result["verified"], result)

    def test_issue_refuses_test_rewritten_in_earlier_slice(self):
        src, _ = self.issue_project()
        test = ("from pathlib import Path\ndef test_dynamic():\n"
                "    Path(__file__).write_text('def test_dynamic(): assert 1 == 1\\n')\n"
                "    assert 2 + 2 == 4\n")
        (src / "tests/test_dynamic.py").write_text(test)
        (src / "tests/test_visible.py").write_text(
            "from pkg.core import helper\ndef test_visible(): assert helper(1) == 2\n")
        result = self.run_issue()
        self.assertFalse(result["verified"], result)
        self.assertEqual((src / "tests/test_dynamic.py").read_text(), test)

    @unittest.skipUnless(all(importlib.util.find_spec(n) for n in ("tree_sitter", "tree_sitter_languages")),
                         "tree-sitter substrate required")
    def test_tree_sitter_rejects_cross_session_candidate_interaction(self):
        from canonical.runtime.bound_capabilities import code_tree_sitter_incremental_index_v1 as index
        from canonical.runtime.bound_capabilities import code_tree_sitter_impact_v1 as impact
        from canonical.runtime.bound_capabilities import code_tree_sitter_patch_verify_v1 as verify
        repo = self.root / "repo"
        project = repo / "project"
        (project / "other").mkdir(parents=True)
        source = project / "calc.py"
        source.write_text("def compute(x):\n    return x + 1\n")
        (project / "pytest.ini").write_text("[pytest]\ntestpaths = other\n")
        (project / "other/test_unrelated.py").write_text("def test_unrelated(): assert 2 + 2 == 4\n")
        (project / "conftest.py").write_text("import pytest\n@pytest.fixture(scope='session')\ndef bucket(): return []\n")
        (project / "test_visible.py").write_text("from calc import compute\ndef test_visible(bucket):\n"
                                                  "    assert compute(0) == 1\n    bucket.append(compute(2))\n")
        (project / "test_dynamic.py").write_text("def test_dynamic(bucket):\n    assert not bucket or bucket == [3]\n")
        targets = ("test_visible.py", "test_dynamic.py")
        self.assertEqual(self.pytest(project, *targets).returncode, 0)
        index.run({"source_root": "project", "output_path": "index.json"}, repo)
        impact.run({"index_path": "index.json", "changed_paths": ["project/calc.py"],
                    "output_path": "selection.json"}, repo)
        raw = source.read_bytes()
        start = raw.index(b"x + 1")
        result = verify.run({"index_path": "index.json", "selection_path": "selection.json",
            "edits": [{"path": "project/calc.py", "start_byte": start, "end_byte": start + 5,
                       "expected": "x + 1", "replacement": "x * 2 + 1"}],
            "test_cwd": "project", "output_path": "patch.json", "timeout_s": 20}, repo)
        candidate = repo / "candidate"
        shutil.copytree(project, candidate)
        (candidate / "calc.py").write_text("def compute(x):\n    return x * 2 + 1\n")
        independent = self.pytest(candidate, *targets)
        self.assertNotEqual(independent.returncode, 0, independent.stdout + independent.stderr)
        self.assertFalse(result["verified"], result)

    @unittest.skipUnless(all(importlib.util.find_spec(n) for n in ("tree_sitter", "tree_sitter_languages")),
                         "tree-sitter substrate required")
    def test_tree_sitter_refuses_test_rewritten_before_combined_session(self):
        from canonical.runtime.bound_capabilities import code_tree_sitter_incremental_index_v1 as index
        from canonical.runtime.bound_capabilities import code_tree_sitter_impact_v1 as impact
        from canonical.runtime.bound_capabilities import code_tree_sitter_patch_verify_v1 as verify
        repo = self.root / "repo"
        project = repo / "project"
        (project / "other").mkdir(parents=True)
        source = project / "calc.py"
        source.write_text("def compute(x):\n    return x + 1\n")
        (project / "pytest.ini").write_text("[pytest]\ntestpaths = other\n")
        (project / "other/test_unrelated.py").write_text("def test_unrelated(): assert 2 + 2 == 4\n")
        (project / "test_visible.py").write_text("from calc import compute\ndef test_visible(): assert compute(0) == 1\n")
        test = ("from pathlib import Path\ndef test_dynamic():\n"
                "    Path(__file__).write_text('def test_dynamic(): assert 1 == 1\\n')\n"
                "    assert 2 + 2 == 4\n")
        (project / "test_dynamic.py").write_text(test)
        index.run({"source_root": "project", "output_path": "index.json"}, repo)
        impact.run({"index_path": "index.json", "changed_paths": ["project/calc.py"],
                    "output_path": "selection.json"}, repo)
        start = source.read_bytes().index(b"x + 1")
        result = verify.run({"index_path": "index.json", "selection_path": "selection.json",
            "edits": [{"path": "project/calc.py", "start_byte": start, "end_byte": start + 5,
                       "expected": "x + 1", "replacement": "x * 2 + 1"}],
            "test_cwd": "project", "output_path": "patch.json", "timeout_s": 20}, repo)
        self.assertFalse(result["verified"], result)
        self.assertEqual((project / "test_dynamic.py").read_text(), test)


if __name__ == "__main__":
    unittest.main()
