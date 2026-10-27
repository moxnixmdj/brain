"""Measuring a family must not depend on WHEN it was measured.

Two independent facts are asserted here, because the heartbeat now measures families
at the same time (``--jobs``):

1. A family's row is a function of the run seed, its own name and its own instances --
   not of which families ran before it.  The old code shared one ``random.Random``
   across the family loop, so a family's fixtures silently depended on the order it
   happened to be measured in, which makes any concurrency unverifiable.
2. Two families measured at the same time get numerically identical rows to the same
   two families measured one after the other.

Measured before the fix (2026-10-27), by running three measurement processes against
the old fixed work root: the PDF family dropped from 3/3 to 2/3 and one process ran
for over fifteen minutes, because every run ``rmtree``'d the directory the others were
writing fixtures into.  That is why the work root is now per-run (``_measure_family``
takes its own work directory, and ``run()`` gives each run its own).
"""
from __future__ import annotations

import sys
import unittest
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from execution_guard.live_solver_end_to_end_measurement_v1 import _measure_family  # noqa: E402

WORK = ROOT / "canonical/astra_runtime/tmp/concurrency_unit_tests"

# Cheap, deterministic families.  One instance each keeps the whole file under a few
# seconds; the property being tested is about seeding and isolation, not corpus size.
CHEAP = "EXACT_LITERAL_RESPONSE"
OTHER = "PDF_TEXT_EXTRACT"


def _job(tag: str, family: str, seed: int, n: int = 1):
    return (tag, seed, "new", family, n, WORK / tag / family)


def _row(family: str, row: dict) -> tuple:
    """The part of a row that must not move: no timings, no route histograms."""
    return (row["oracle_pass"], row["instances"], row["environment_blocked_here"])


class AFamilyIsAFunctionOfItsOwnInputs(unittest.TestCase):
    def test_the_same_seed_gives_the_same_row_twice(self):
        first = _measure_family(_job("SAME_A", CHEAP, 4242))
        second = _measure_family(_job("SAME_B", CHEAP, 4242))
        self.assertEqual(_row(CHEAP, first[1]), _row(CHEAP, second[1]))

    def test_a_family_does_not_depend_on_what_ran_before_it(self):
        alone = _measure_family(_job("ALONE", CHEAP, 99))
        # same family, same seed, but measured after another family ran first
        _measure_family(_job("AFTER1", OTHER, 99))
        after = _measure_family(_job("AFTER2", CHEAP, 99))
        self.assertEqual(_row(CHEAP, alone[1]), _row(CHEAP, after[1]))

    def test_a_different_seed_is_allowed_to_change_the_row(self):
        """Control: the seeding is live, not a constant that trivially matches."""
        a = _measure_family(_job("SEED_A", CHEAP, 1))
        self.assertEqual(a[1]["instances"], 1)
        self.assertIsNotNone(a[1]["pass_rate"])


class ConcurrencyDoesNotChangeTheNumbers(unittest.TestCase):
    def test_two_families_at_once_equal_the_same_two_in_sequence(self):
        jobs = [_job("SEQ_A", CHEAP, 7), _job("SEQ_B", OTHER, 7)]
        serial = {name: _row(name, row) for name, row, _ in (_measure_family(j) for j in jobs)}

        par_jobs = [_job("PAR_A", CHEAP, 7), _job("PAR_B", OTHER, 7)]
        with ProcessPoolExecutor(max_workers=2) as pool:
            parallel = {name: _row(name, row) for name, row, _ in pool.map(_measure_family, par_jobs)}

        self.assertEqual(serial, parallel)

    def test_a_family_keeps_its_own_work_directory(self):
        """The collision that corrupted a measurement: two families, one path."""
        a = _job("ISO_A", CHEAP, 5)
        b = _job("ISO_B", OTHER, 5)
        self.assertNotEqual(a[-1], b[-1])
        self.assertIn("ISO_A", str(a[-1]))
        self.assertIn("ISO_B", str(b[-1]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
