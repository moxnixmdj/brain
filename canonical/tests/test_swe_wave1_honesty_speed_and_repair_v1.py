#!/usr/bin/env python3
"""Wave 1 SWE regression pins: honesty gates, stdlib subprocess isolation, repair+regression synthesis, and bounded execution."""
from __future__ import annotations

import io
import json
import pathlib
import shutil
import unittest
from contextlib import redirect_stdout

ROOT = pathlib.Path(__file__).resolve().parents[2]


class Wave1SweHonestySpeedRepairTests(unittest.TestCase):
    def setUp(self) -> None:
        self.scratch = ROOT / "canonical/astra_runtime/tmp/test_wave1_swe"
        shutil.rmtree(self.scratch, ignore_errors=True)
        self.scratch.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.scratch, ignore_errors=True)

    def test_untracked_git_diff_refuses_instead_of_empty_pass(self) -> None:
        from canonical.runtime.bound_capabilities import git_repository_operate

        untracked = self.scratch / "untracked_calc.py"
        untracked.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
        out_json = self.scratch / "diff_out.json"
        with self.assertRaises(Exception) as ctx:
            git_repository_operate.run(
                {
                    "op": "diff",
                    "target": untracked.relative_to(ROOT).as_posix(),
                    "output_path": out_json.relative_to(ROOT).as_posix(),
                },
                ROOT,
            )
        self.assertIn("DIFF_TARGET_NOT_TRACKED_IN_GIT", str(ctx.exception))

    def test_unsupported_git_rewrite_verbs_do_not_bind_read_ops(self) -> None:
        from canonical.runtime import declared_input_derivation_v1 as der

        self.assertEqual(der.stated_git_operations("Cherry-pick the last commit onto a new branch."), ())
        self.assertEqual(der.stated_git_operations("Write the changelog entry for the last three commits."), ())
        self.assertEqual(der.stated_git_operations("Revert the last commit on the branch."), ())

    def test_answer_shape_gates_reject_counter_and_non_duplication_adapters(self) -> None:
        from canonical.runtime.live_brain_route_admission_v1 import load_verified_registry, stated_answer_errors

        reg = load_verified_registry()
        errs_def = stated_answer_errors(
            "Show me the definition of run_raw_goal in canonical/runtime/live_integrated_brain_v1.py",
            reg["python.source.definition_count.v1"],
            "python.source.definition_count.v1",
        )
        self.assertTrue(any("STATED_EXTRACTION_ANSWERED_BY_A_COUNTER" in e for e in errs_def))

        errs_dup = stated_answer_errors(
            "Find duplicated code across canonical/runtime/bound_capabilities",
            reg["code.index.tree_sitter.incremental.v1"],
            "code.index.tree_sitter.incremental.v1",
        )
        self.assertTrue(any("STATED_DUPLICATION_ANALYSIS_NOT_PROVIDED_BY_CAPABILITY" in e for e in errs_dup))

    def test_stdlib_shadow_and_cli_parse_args_do_not_break_add_parameter_or_repair(self) -> None:
        from canonical.runtime.bound_capabilities import python_source_add_parameter

        pkg = self.scratch / "pkg"
        pkg.mkdir(parents=True, exist_ok=True)
        (pkg / "http.py").write_text("import urllib.request\n\ndef fetch():\n    return urllib.request\n", encoding="utf-8")
        (pkg / "cli.py").write_text("import argparse\np = argparse.ArgumentParser()\np.add_argument('name')\np.parse_args()\n", encoding="utf-8")
        (pkg / "util.py").write_text("def total(price, qty):\n    return price * qty\n", encoding="utf-8")
        out_path = self.scratch / "add_param_report.json"

        res = python_source_add_parameter.run(
            {
                "source_root": pkg.relative_to(ROOT).as_posix(),
                "module": (pkg / "util.py").relative_to(ROOT).as_posix(),
                "qualname": "total",
                "param_name": "strict",
                "output_path": out_path.relative_to(ROOT).as_posix(),
            },
            ROOT,
        )
        self.assertTrue(res.get("verified"))
        self.assertIn("strict=None", (pkg / "util.py").read_text(encoding="utf-8"))

    def test_rename_symbol_emits_no_stdout_json_and_test_audit_bounds_large_corpus(self) -> None:
        from canonical.runtime.bound_capabilities import python_refactor_rename_symbol, python_test_audit

        pkg = self.scratch / "ren"
        pkg.mkdir(parents=True, exist_ok=True)
        (pkg / "mod.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
        (pkg / "caller.py").write_text("from mod import add\nx = add(1, 2)\n", encoding="utf-8")
        buf = io.StringIO()
        with redirect_stdout(buf):
            res = python_refactor_rename_symbol.run(
                {
                    "source_root": pkg.relative_to(ROOT).as_posix(),
                    "module": "mod.py",
                    "qualname": "add",
                    "new_symbol": "plus",
                    "output_path": (self.scratch / "ren_out.json").relative_to(ROOT).as_posix(),
                },
                ROOT,
            )
        self.assertEqual(buf.getvalue(), "")
        self.assertIn("def plus(", (pkg / "mod.py").read_text(encoding="utf-8"))
        self.assertIn("plus(1, 2)", (pkg / "caller.py").read_text(encoding="utf-8"))

        big = self.scratch / "big_tests"
        big.mkdir(parents=True, exist_ok=True)
        for i in range(66):
            (big / f"test_{i:03d}.py").write_text("import unittest\n", encoding="utf-8")
        with self.assertRaises(Exception) as ctx:
            python_test_audit.run(
                {
                    "source_root": big.relative_to(ROOT).as_posix(),
                    "output_path": (self.scratch / "audit_out.json").relative_to(ROOT).as_posix(),
                },
                ROOT,
            )
        self.assertIn("REFUSING_UNBOUNDED_TEST_AUDIT_CORPUS", str(ctx.exception))

    def test_verified_repair_synthesizes_differential_regression_test(self) -> None:
        from canonical.runtime.bound_capabilities import python_repair_apply_verified_v1

        proj = self.scratch / "proj"
        (proj / "app").mkdir(parents=True)
        (proj / "tests").mkdir(parents=True)
        (proj / "app/__init__.py").write_text("", encoding="utf-8")
        (proj / "app/calc.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
        (proj / "tests/__init__.py").write_text("", encoding="utf-8")
        (proj / "tests/test_calc.py").write_text(
            "import unittest\nfrom app.calc import add\nclass T(unittest.TestCase):\n    def test_add(self):\n        self.assertEqual(add(1, 2), 3)\n",
            encoding="utf-8",
        )
        res = python_repair_apply_verified_v1.run(
            {
                "source_root": (proj / "app").relative_to(ROOT).as_posix(),
                "test_paths": [(proj / "tests/test_calc.py").relative_to(ROOT).as_posix()],
                "synthesize_regression_test": True,
                "output_path": (self.scratch / "rep_out.json").relative_to(ROOT).as_posix(),
            },
            ROOT,
        )
        self.assertTrue(res.get("pass"))
        self.assertTrue(res.get("regression_test_written"))
        self.assertTrue((ROOT / res["regression_test_written"]).is_file())


if __name__ == "__main__":
    unittest.main()
