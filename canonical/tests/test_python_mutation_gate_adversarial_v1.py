"""Adversarial controls for the Python diff mutation gate.

All projects and patches are temporary; the independent oracle is real pytest
against the localized mutation, not the gate's own verdict.
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time
import unittest

from canonical.runtime.bound_capabilities import python_review_diff_mutation_gate as gate


class MutationGateAdversarialTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.temp.name)
        self.anchor = self.root / "anchor"
        self.anchor.mkdir()
        (self.anchor / "tests").mkdir()
        self.addCleanup(self.temp.cleanup)

    def write(self, relative: str, content: str) -> None:
        path = self.anchor / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def run_gate(self, diff: str, **overrides):
        (self.root / "change.diff").write_text(diff, encoding="utf-8")
        args = {"anchor_path": "anchor", "diff_path": "change.diff",
                "output_path": "out/result.json", "run_tests": ["tests/test_value.py"],
                "python_executable": sys.executable, "timeout_s": 10}
        args.update(overrides)
        result = gate.run(args, self.root)
        artifact = json.loads((self.root / "out/result.json").read_text(encoding="utf-8"))
        return result, artifact

    def single_file_fixture(self, tests: str) -> str:
        self.write("mod.py", "VALUE = 1\n# a\n# b\n# c\ndef untouched():\n    return 5\n")
        self.write("tests/test_value.py", tests)
        return ("--- a/mod.py\n+++ b/mod.py\n@@ -1,4 +1,4 @@\n"
                "-VALUE = 1\n+VALUE = 2\n # a\n # b\n # c\n")

    def test_numeric_mutation_does_not_delete_untouched_functions(self):
        diff = self.single_file_fixture(
            "from mod import untouched\ndef test_untouched():\n    assert untouched() == 5\n")
        result, artifact = self.run_gate(diff)
        # Prove the intended localized mutation is unobserved independently.
        (self.anchor / "mod.py").write_text(
            "VALUE = 3\n# a\n# b\n# c\ndef untouched():\n    return 5\n", encoding="utf-8")
        env = dict(os.environ, PYTHONPATH=str(self.anchor), PYTHONDONTWRITEBYTECODE="1")
        independent = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                                      "tests/test_value.py"], cwd=self.anchor, env=env,
                                     capture_output=True, text=True, timeout=10)
        self.assertEqual(independent.returncode, 0, independent.stdout + independent.stderr)
        self.assertEqual(result["gate"], "FAIL")
        self.assertFalse(result["verified"])
        self.assertGreaterEqual(artifact["mutants_survived"], 1)
        self.assertIn("numeric_bump", {row["operator"] for row in artifact["survivors"]})

    def test_zero_and_one_receive_numeric_mutants(self):
        for value in (0, 1):
            with self.subTest(value=value):
                text = f"VALUE = {value}\n"
                sites = gate._mutants_for_text("mod.py", text, {1}, 100)
                numeric = [site for site in sites if site.kind == "numeric_bump"]
                self.assertEqual(len(numeric), 1)
                self.assertEqual(gate._apply_splice(text, "mod.py", numeric[0]),
                                 f"VALUE = {value + 1}\n")

    def test_utf8_and_multiline_splices_preserve_all_other_bytes(self):
        source = "# café 🧠\ndef value():\n    return (\n        2 + 4\n    )\n\ndef untouched():\n    return 9\n"
        sites = gate._mutants_for_text("mod.py", source, {2, 3, 4, 5}, 100)
        self.assertGreater(len(sites), 0)
        for site in sites:
            with self.subTest(kind=site.kind, line=site.line, col=site.col):
                edited = gate._apply_splice(source, "mod.py", site)
                original_bytes = source.encode("utf-8")
                offset = sum(len(line) for line in original_bytes.splitlines(keepends=True)[:site.line - 1]) + site.col
                expected = original_bytes[:offset] + site.replacement + original_bytes[offset + site.span:]
                self.assertEqual(edited.encode("utf-8"), expected)
                self.assertIn("def untouched():\n    return 9\n", edited)
                compile(edited, "mod.py", "exec")

    def test_operator_tokens_ignore_comments_and_use_utf8_byte_columns(self):
        cases = [
            ("def f(a, b):\n    return (a  # + is a comment\n            + b)\n", "arith_swap", "-"),
            ("def f(café, b):\n    return (café  # < is a comment\n            < b)\n", "compare_swap", ">="),
        ]
        for source, kind, replacement in cases:
            with self.subTest(kind=kind):
                sites = [site for site in gate._mutants_for_text("mod.py", source, {3}, 100)
                         if site.kind == kind]
                self.assertEqual(len(sites), 1)
                mutated = gate._apply_splice(source, "mod.py", sites[0])
                self.assertEqual(mutated, source.replace("            " + ("+" if kind == "arith_swap" else "<") + " b)",
                                                         "            " + replacement + " b)"))
                self.assertEqual(sites[0].row("mod.py")["span_bytes"], 1)
                compile(mutated, "mod.py", "exec")

    def test_untested_new_production_file_is_a_mutation_target(self):
        diff = self.single_file_fixture(
            "from mod import VALUE\ndef test_value():\n    assert VALUE == 2\n")
        diff += ("diff --git a/new.py b/new.py\nnew file mode 100644\n"
                 "--- /dev/null\n+++ b/new.py\n@@ -0,0 +1,2 @@\n"
                 "+UNTESTED = 2\n+\n")
        result, artifact = self.run_gate(diff)
        self.assertEqual(result["gate"], "FAIL")
        self.assertFalse(result["verified"])
        self.assertTrue(any(row["file"] == "new.py" for row in artifact["survivors"]))
        self.assertIn(1, artifact["changed_lines_targeted"]["new.py"])

    def test_truncated_mutation_frontier_is_not_a_full_pass(self):
        self.write("mod.py", "FIRST = 1\nSECOND = 1\n# c\n# d\n")
        self.write("tests/test_value.py",
                   "from mod import FIRST, SECOND\ndef test_values():\n    assert FIRST == 2\n    assert SECOND == 3\n")
        diff = ("--- a/mod.py\n+++ b/mod.py\n@@ -1,4 +1,4 @@\n"
                "-FIRST = 1\n-SECOND = 1\n+FIRST = 2\n+SECOND = 3\n # c\n # d\n")
        result, artifact = self.run_gate(diff, max_mutants=1)
        self.assertNotEqual(result["gate"], "PASS")
        self.assertFalse(result["verified"])
        self.assertTrue(artifact["mutation_frontier_truncated"])

    def test_absolute_anchor_test_path_is_rebased_into_each_trial(self):
        diff = self.single_file_fixture(
            "from pathlib import Path\nfrom mod import VALUE\n"
            "def test_value():\n    Path(__file__).resolve().parents[1].joinpath('marker').write_text('x')\n"
            "    assert VALUE == 2\n")
        result, _ = self.run_gate(diff, run_tests=[str(self.anchor / "tests/test_value.py")])
        self.assertEqual(result["gate"], "PASS")
        self.assertFalse((self.anchor / "marker").exists())

    def test_explicit_test_path_outside_anchor_is_rejected(self):
        diff = self.single_file_fixture("from mod import VALUE\ndef test_value(): assert VALUE == 2\n")
        outside = self.root / "outside.py"
        outside.write_text("def test_wrong(): assert False\n", encoding="utf-8")
        with self.assertRaises(SystemExit) as raised:
            self.run_gate(diff, run_tests=[str(outside)])
        self.assertIn("TEST_PATH_OUTSIDE_ANCHOR", str(raised.exception))

    def test_baseline_created_state_cannot_turn_a_survivor_into_a_kill(self):
        diff = self.single_file_fixture(
            "from pathlib import Path\nfrom mod import untouched\n"
            "def test_untouched():\n    marker = Path('run.marker')\n"
            "    assert not marker.exists()\n    marker.write_text('created by this test run')\n"
            "    assert untouched() == 5\n")
        result, artifact = self.run_gate(diff)
        self.assertEqual(result["gate"], "FAIL", artifact)
        self.assertFalse(result["verified"])
        self.assertTrue(any(row["operator"] == "numeric_bump" for row in artifact["survivors"]))
        self.assertFalse((self.anchor / "run.marker").exists())

    def test_global_wall_budget_makes_slow_mutants_inconclusive(self):
        diff = self.single_file_fixture(
            "import time\nfrom mod import VALUE\ndef test_value():\n"
            "    if VALUE == 3: time.sleep(3)\n    assert VALUE == 2\n")
        started = time.monotonic()
        result, artifact = self.run_gate(diff, timeout_s=10, max_wall_time_s=1)
        self.assertLess(time.monotonic() - started, 2.5)
        self.assertEqual(result["gate"], "INCONCLUSIVE")
        self.assertTrue(artifact["wall_time_budget_exhausted"])
        self.assertGreater(artifact["mutants_inconclusive"], 0)

    def test_timeout_is_inconclusive_not_an_automatic_kill(self):
        diff = self.single_file_fixture(
            "import time\nfrom mod import VALUE\ndef test_value():\n"
            "    if VALUE == 3:\n        time.sleep(3)\n    assert VALUE == 2\n")
        result, artifact = self.run_gate(diff, timeout_s=1)
        self.assertNotEqual(result["gate"], "PASS")
        self.assertFalse(result["verified"])
        self.assertGreaterEqual(artifact["mutants_inconclusive"], 1)
        self.assertEqual(artifact["mutants_killed"], 0)

    def test_skipped_only_baseline_cannot_certify_a_gate(self):
        diff = self.single_file_fixture(
            "import pytest\n@pytest.mark.skip(reason='no observation')\n"
            "def test_value():\n    raise AssertionError('not executed')\n")
        try:
            result, _ = self.run_gate(diff)
        except SystemExit as exc:
            self.assertIn("BASE_WORLD", str(exc))
        else:
            self.assertNotEqual(result["gate"], "PASS")
            self.assertFalse(result["verified"])


if __name__ == "__main__":
    unittest.main()
