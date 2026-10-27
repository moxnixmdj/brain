#!/usr/bin/env python3
"""A missing measurement dependency must cost one family, not the whole census.

The defect, reproduced.  ``live_solver_end_to_end_measurement_v1.py`` wrapped the
solve call in ``try/except`` but called ``case.oracle(result)`` -- and the generator
before it -- unguarded.  Three oracles and generators do ``import openpyxl`` or
``import docx``.  On any host without those libraries the exception escaped and
aborted the run:

    File "execution_guard/live_solver_families_v4.py", line 74, in oracle
        import openpyxl
    ModuleNotFoundError: No module named 'openpyxl'

exit status 1, **no receipt written, and not one of the 36 families measured.**
The harness already had the right vocabulary for this -- ``ENVIRONMENT_BLOCKED_HERE``
-- it simply did not apply it to its own dependencies.

Measured after the fix, on a host with neither openpyxl nor python-docx:

    exit 0, full receipt, 36 families measured, 21 all-pass,
    6 correctly recorded as environment-blocked, 9 real failures surfaced

Those 9 real failures were invisible before, because the run died before reaching them.

These tests drive the extracted helpers directly, so they are fast and hold on every
host regardless of which optional libraries happen to be installed.
"""
from __future__ import annotations

import sys
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from execution_guard import live_solver_end_to_end_measurement_v1 as harness


class _FakeCase:
    """Stands in for a generated Case; only .oracle is exercised."""

    def __init__(self, oracle):
        self.oracle = oracle
        self.goal = "fake goal"
        self.artifacts = []


class _FakeGenerator:
    def __init__(self, behaviour):
        self.behaviour = behaviour
        self.calls = 0

    def __call__(self, rng, work, i):
        self.calls += 1
        if isinstance(self.behaviour, BaseException):
            raise self.behaviour
        return _FakeCase(lambda result: (True, ""))


def _missing(name):
    exc = ModuleNotFoundError("No module named " + repr(name))
    exc.name = name
    return exc


class TestOracleOutcome(unittest.TestCase):
    def test_a_missing_oracle_dependency_becomes_a_blocker_not_a_crash(self):
        case = _FakeCase(self._raise_missing)
        good, why, blocker = harness.oracle_outcome(case, {"status": "PASS"}, None)
        self.assertFalse(good)
        self.assertEqual(why, "")
        self.assertEqual(blocker, "ORACLE_DEPENDENCY_MISSING:openpyxl")

    @staticmethod
    def _raise_missing(result):
        raise _missing("openpyxl")

    def test_an_already_known_blocker_is_not_overwritten(self):
        """The adapter's own blocker is more specific; it must win."""
        case = _FakeCase(self._raise_missing)
        _, _, blocker = harness.oracle_outcome(
            case, {"status": "FAIL"}, "BOUND_APT_METADATA_NOT_FOUND"
        )
        self.assertEqual(blocker, "BOUND_APT_METADATA_NOT_FOUND")

    def test_a_passing_oracle_is_returned_unchanged(self):
        case = _FakeCase(lambda result: (True, ""))
        good, why, blocker = harness.oracle_outcome(case, {"status": "PASS"}, None)
        self.assertTrue(good)
        self.assertEqual(why, "")
        self.assertIsNone(blocker)

    def test_a_failing_oracle_still_reports_its_own_reason(self):
        case = _FakeCase(lambda result: (False, "xlsx rows mismatch: [1] != [2]"))
        good, why, blocker = harness.oracle_outcome(case, {"status": "PASS"}, None)
        self.assertFalse(good)
        self.assertIn("rows mismatch", why)
        self.assertIsNone(blocker)

    def test_a_real_oracle_bug_still_raises(self):
        """The narrow catch is the whole point.

        Only ModuleNotFoundError is excused. A TypeError or AssertionError in an
        oracle is a defect in the measurement and must surface, not be silently
        reclassified as an environment problem.
        """
        for exc in (ValueError("oracle logic broke"), AssertionError("bad check"), KeyError("x")):
            with self.subTest(exc=type(exc).__name__):
                case = _FakeCase(lambda result, e=exc: (_ for _ in ()).throw(e))
                with self.assertRaises(type(exc)):
                    harness.oracle_outcome(case, {"status": "PASS"}, None)


class TestGeneratedCase(unittest.TestCase):
    def test_a_generator_needing_a_missing_library_reports_it(self):
        gen = _FakeGenerator(_missing("openpyxl"))
        case, blocker = harness.generated_case(gen, None, None, 0)
        self.assertIsNone(case)
        self.assertEqual(blocker, "ORACLE_DEPENDENCY_MISSING:openpyxl")

    def test_a_working_generator_returns_its_case(self):
        gen = _FakeGenerator(None)
        case, blocker = harness.generated_case(gen, None, None, 0)
        self.assertIsNotNone(case)
        self.assertIsNone(blocker)
        self.assertEqual(gen.calls, 1)


class TestBlockersStillFailInTheVerdict(unittest.TestCase):
    """Prove this classifies failures rather than hiding them."""

    @staticmethod
    def _receipt(blocked, passed):
        # A complete run.  `alive_errors` now requires this explicitly: a receipt
        # that does not say its run finished fails closed (MEASUREMENT_INCOMPLETE),
        # because an interrupted run measures part of the suite and an unstated
        # provenance is treated as a gap.  This fixture asserts the blocker
        # classification, not the completeness contract, so it states the fact.
        return {
            "run_complete": True,
            "measurements": {
                "new": {
                    "families": {
                        "XLSX_CREATE": {
                            "instances": 6, "oracle_pass": 0,
                            "environment_blocked_here": blocked,
                        },
                        "SQLITE_FROM_RECORDS": {
                            "instances": 6, "oracle_pass": passed,
                            "environment_blocked_here": 0,
                        },
                    },
                    "out_of_scope_fail_closed_rate": 1.0,
                }
            }
        }

    def test_a_blocked_family_is_excused_in_a_sandbox(self):
        errors = harness.alive_errors(self._receipt(6, 6), environment_blockers_are_failures=False)
        self.assertEqual(errors, [])

    def test_the_same_blocked_family_is_a_failure_on_the_public_runner(self):
        """On CI every declared dependency is installed, so a blocker is a real failure."""
        errors = harness.alive_errors(self._receipt(6, 6), environment_blockers_are_failures=True)
        self.assertTrue(
            any("XLSX_CREATE" in e for e in errors),
            f"a blocked family silently passed the CI verdict: {errors}",
        )

    def test_a_partially_blocked_family_is_still_a_failure_everywhere(self):
        """Half the instances blocked and half not passing is not an excuse."""
        errors = harness.alive_errors(self._receipt(3, 3), environment_blockers_are_failures=False)
        self.assertTrue(any("XLSX_CREATE" in e for e in errors), errors)


if __name__ == "__main__":
    unittest.main()
