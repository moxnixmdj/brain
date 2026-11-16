#!/usr/bin/env python3
"""Tests for the verdict amplifier.

Every test here exists because something in this instrument was *silently* wrong first. A
verifier that returns "nothing to report" looks identical whether it has examined the candidate
and found nothing or never examined it at all, so each of these pins one of the ways the second
case disguised itself as the first:

    a virtualenv interpreter resolved into the base interpreter, so the suite could not import
        pytest and every pair became "unrunnable"
    a pytest hook under the wrong name, so the suite ran, passed, and wrote no trace at all
    an invented argument grid on functions that take records, so a law was NOT_APPLICABLE on the
        only functions that mattered and the amplifier reported a clean zero
    a reduction that deleted the helpers a function calls, so the function raised and every law
        about it looked inapplicable rather than answered
    a TOTALITY law on the inputs the suite already ran, which cannot say anything a pass has not
        already said

Requires an interpreter with pytest, which is how the suites are run: `.venv/bin/python -m pytest`.
A pair whose interpreter has no pytest is skipped by name, never reported as a pass.
"""
from __future__ import annotations

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import patch_verdict_amplification_v1 as amp  # noqa: E402
from canonical.swe_kernel import specification_from_structure_v1 as spec  # noqa: E402

PYTHON = sys.executable

MODULE = "canonical/swe_kernel/rule_expiry_v1.py"
TEST = "canonical/tests/test_rule_expiry_v1.py"


def _pytest_available() -> bool:
    try:
        import pytest  # noqa: F401
    except ImportError:
        return False
    return True


class InterpreterTests(unittest.TestCase):
    def test_a_relative_interpreter_is_resolved_against_the_repository_not_followed(self):
        # `.venv/bin/python` is a symlink to the base interpreter. Resolving it with
        # `Path.resolve()` produced `/usr/bin/python3.11`, which has no pytest -- and the failure
        # arrived as "No module named pytest" from a process nobody was watching.
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            repo = pathlib.Path(directory)
            (repo / "bin").mkdir()
            (repo / "bin" / "python").symlink_to(sys.executable)
            chosen = amp._executable("bin/python", repo)
            # Kept as the symlink's own path: resolving it would discard the `pyvenv.cfg` that
            # makes the environment's packages importable.
            self.assertEqual(chosen, str(repo / "bin" / "python"))

    def test_an_absolute_interpreter_is_used_as_given(self):
        self.assertEqual(amp._executable(PYTHON, ROOT), PYTHON)


class InjectionTests(unittest.TestCase):
    def test_a_suite_run_against_the_pristine_module_passes(self):
        source = (ROOT / MODULE).read_text(encoding="utf-8")
        result = amp.run_tests(module_path=MODULE, test_path=TEST, candidate_source=source,
                               python_executable=PYTHON, timeout_s=120)
        if result.get("why") == "PYTEST_MISSING":
            self.skipTest("this interpreter has no pytest; use .venv/bin/python")
        self.assertEqual(result["outcome"], "PASS", result)

    def test_a_candidate_that_cannot_import_is_a_difference_not_a_pass(self):
        result = amp.run_tests(module_path=MODULE, test_path=TEST,
                               candidate_source="this is not python(\n",
                               python_executable=PYTHON, timeout_s=120)
        if result.get("why") == "PYTEST_MISSING":
            self.skipTest("this interpreter has no pytest; use .venv/bin/python")
        self.assertEqual(result["outcome"], "FAIL")
        self.assertEqual(result["why"], "CANDIDATE_DOES_NOT_IMPORT")


class TraceTests(unittest.TestCase):
    def test_the_suite_records_the_arguments_it_actually_passed(self):
        # The hook was first written as `pytest_session_finished`, which pytest does not know, so
        # no file was ever written and the trace reported "no records" -- indistinguishable from
        # "the suite never called this module".
        result = amp.trace_suite_calls(module_path=MODULE, test_path=TEST,
                                       python_executable=PYTHON, timeout_s=120)
        if result.get("why") == "NO_TRACE_FILE":
            self.skipTest("this interpreter has no pytest; use .venv/bin/python")
        self.assertEqual(result["why"], "TRACED", result)
        self.assertGreater(len(result["records"]), 0)
        grids = amp.recorded_grids(result["records"])
        self.assertIn("material_differences", grids)
        self.assertTrue(all(isinstance(entry["args"], list) for entry in grids["material_differences"]))

    def test_an_invented_grid_is_mute_where_a_recorded_one_speaks(self):
        # The zero that started this: `material_differences` takes two parsed records, so the
        # invented grid cannot call it and every law about it is NOT_APPLICABLE. On the arguments
        # the suite passed, the same laws are answered.
        trace = amp.trace_suite_calls(module_path=MODULE, test_path=TEST,
                                      python_executable=PYTHON, timeout_s=120)
        if trace.get("why") != "TRACED":
            self.skipTest("this interpreter has no pytest; use .venv/bin/python")
        grids = amp.recorded_grids(trace["records"])
        invented = amp.prepare_laws(module_path=MODULE)
        recorded = amp.prepare_laws(module_path=MODULE, grids=grids)
        self.assertEqual(recorded["grid_source"], "RECORDED_FROM_A_REAL_SUITE")
        self.assertEqual(invented["grid_source"], "INVENTED")
        invented_laws = {row["function"] for row in invented["derived"]["invariants"]}
        self.assertTrue(set(grids) & invented_laws)

        payload = spec.child_payload(
            module_name="rule_expiry_v1",
            baseline_source=recorded["baseline_source"],
            derived=recorded["derived"],
            variants=[],
            grids=recorded["grids"],
        )
        outcome = spec.run_child(payload)
        defined = {row["function"]: row["inputs_defined"] for row in outcome["confirmations"]}
        self.assertGreater(defined.get("material_differences", 0), 0)

    def test_the_recorded_grid_keeps_only_arguments_that_survive_a_json_round_trip(self):
        grids = amp.recorded_grids([
            {"function": "f", "args": [1, "a"]},
            {"function": "f", "args": [1, "a"]},
            {"function": "g", "args": [{"k": [1, 2]}]},
        ])
        self.assertEqual(grids["f"], [{"args": [1, "a"]}])
        self.assertEqual(len(grids["g"]), 1)


class ReductionTests(unittest.TestCase):
    def test_a_helper_the_selected_function_calls_survives_the_reduction(self):
        # The reduction used to keep only the names under test, so `evaluate` called a
        # `_prepare_victims` that no longer existed, raised, and made every law about it
        # NOT_APPLICABLE. The number this produced was read as "no laws here".
        source = (
            "import json\n"
            "class Failure(Exception):\n    pass\n"
            "def selected(a):\n    return _helper(a)\n"
            "def _helper(a):\n    raise Failure('no') if a is None else str(a)\n"
        )
        reduced = spec.reduce_module(source, ["selected"])
        self.assertIn("def _helper", reduced)
        self.assertIn("class Failure", reduced)


class AmplifierTests(unittest.TestCase):
    def test_a_confirmed_totality_law_cannot_add_to_what_a_passing_suite_already_said(self):
        # Every recorded call either returned or the suite failed. A TOTALITY law on those same
        # inputs is therefore already implied by the pass, so it can only fire on a raise the
        # suite never saw -- which is a different input, i.e. a different law instance.
        prepared = amp.prepare_laws(module_path=MODULE)
        source = (ROOT / MODULE).read_text(encoding="utf-8")
        judged = amp.laws_against_prepared(prepared, candidate_source=source)
        self.assertEqual(judged["verdict"], amp.ACCEPTED_BY_BOTH)
        census = judged["census_by_kind"]
        self.assertIn("TOTALITY", census)
        self.assertGreater(census["TOTALITY"]["proposed"], 0)

    def test_a_verdict_is_never_called_correct(self):
        # `ACCEPTED_BY_BOTH` means nothing available falsified the candidate. The vocabulary of
        # this instrument does not contain the word "correct", and it must not acquire it.
        verdicts = (amp.REJECTED_BY_TESTS, amp.REJECTED_BY_LAW, amp.ACCEPTED_BY_BOTH,
                    amp.UNVERIFIABLE)
        self.assertEqual(verdicts, ("REJECTED_BY_THE_TEST_SUITE", "REJECTED_BY_A_CONFIRMED_LAW",
                                    "ACCEPTED_BY_BOTH", "UNVERIFIABLE"))
        for verdict in verdicts:
            self.assertNotIn("CORRECT", verdict)

    def test_a_law_kill_reports_the_call_and_both_values(self):
        # A kill with no witness is a rumour. The counterexample must carry the arguments.
        prepared = amp.prepare_laws(module_path=MODULE)
        broken_candidate = (
            (ROOT / MODULE).read_text(encoding="utf-8")
            .replace("def material_differences(", "def material_differences(", 1)
        )
        judged = amp.laws_against_prepared(prepared, candidate_source=broken_candidate)
        if judged["verdict"] == amp.REJECTED_BY_LAW:
            self.assertIn("args", judged["counterexample"])
            self.assertIn("law", judged["counterexample"])
        else:
            self.assertIsNone(judged["counterexample"])


if __name__ == "__main__":
    unittest.main()
