"""Four sentences a DEFINITION COUNTER was allowed to answer with PASS.

Measured 2026-10-31 on ``75ea4ec``.  The five magnet rows were removed from the registry in
memory (435 rows) to see what the machine would do when they were not in the way. Served went
from 2 of 49 to 6 of 49 -- and four of the six were wrong. Every one of them was
``python.source.definition_count.v1``:

    "Profile <f> and tell me which function is the hot spot."          PASS
    "Optimise the function total in <f>; it is too slow on large inputs."  PASS
    "Make the function total in <f> release the GIL while summing."    PASS
    "Fuzz the function add in <f> for integer overflow."               PASS

A count of definitions answered a request for a measurement over time, a change, a statement
about concurrent execution, and execution under generated inputs. Nothing was profiled,
nothing was optimised, no thread existed, and no input was generated.

That experiment is also why the magnet rows are NOT deleted first: a wrong row that fails is
better than a wrong row that passes. The answer gate already decides this class from the
sentence and the capability's own declaration (``_STATED_EFFECTS``), so the fix is four rows in
that table, and 0 of the 435 rows declare any of the four surfaces -- which is why the honest
outcome today is a refusal that names the effect, not a count wearing the word "profile".

Pinned here, because a refusal is only worth having if it can be told apart from a break.
"""
from __future__ import annotations

import pathlib
import shutil
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import live_brain_route_admission_v1 as door  # noqa: E402

WORK = ROOT / "canonical/astra_runtime/tmp/test_definition_count"
REL = WORK.relative_to(ROOT).as_posix()


def _fresh() -> pathlib.Path:
    if WORK.exists():
        shutil.rmtree(WORK)
    (WORK / "pkg").mkdir(parents=True)
    (WORK / "pkg/calc.py").write_text(
        "def add(a, b):\n    return a + b\n\n\ndef total(xs):\n"
        "    out = 0\n    for x in xs:\n        out += x\n    return out\n", encoding="utf-8")
    (WORK / "pkg/test_calc.py").write_text(
        "import unittest\nfrom pkg.calc import add\n\n\nclass T(unittest.TestCase):\n"
        "    def test_add(self):\n        self.assertEqual(add(1, 2), 3)\n", encoding="utf-8")
    return WORK


class ACountIsNotAMeasurementOrAChange(unittest.TestCase):
    def setUp(self):
        _fresh()

    def tearDown(self):
        shutil.rmtree(WORK, ignore_errors=True)

    # ---------------------------------------------------------------- the defects
    def _refused_with(self, goal: str, code: str) -> None:
        """The count may not answer it, and the request may not PASS.

        Two assertions, deliberately separate.  The count is judged DIRECTLY, because with the
        magnet rows present a different wrong row is selected and refused earlier by admission
        (``FAIL_CLOSED__ROUTE_ADMISSION_REJECTED``) -- the request is still refused, but the
        named effect never gets to speak, and a test that only looked at the end-to-end status
        would pass while the gate underneath was broken.  Measured 2026-10-31: two of these
        four sentences are refused by admission and two by this gate.
        """
        count = door.load_verified_registry().get("python.source.definition_count.v1") or {}
        self.assertTrue(count, "the definition counter must exist")
        errors = door.stated_answer_errors(goal, count, "python.source.definition_count.v1")
        self.assertTrue(any(code in e for e in errors), errors)
        result = door.solve({"task_id": "TEST_DEFINITION_COUNT", "goal": goal})
        self.assertFalse(result.get("pass"), result.get("status"))

    def test_a_definition_count_is_not_a_profile(self):
        self._refused_with(
            "Profile %s/pkg/calc.py and tell me which function is the hot spot." % REL,
            "STATED_PROFILE_NOT_TAKEN_BY_CAPABILITY")

    def test_a_definition_count_is_not_an_optimisation(self):
        self._refused_with(
            "Optimise the function total in %s/pkg/calc.py; it is too slow on large inputs." % REL,
            "STATED_OPTIMISATION_NOT_PERFORMED_BY_CAPABILITY")

    def test_a_definition_count_releases_no_gil(self):
        self._refused_with(
            "Make the function total in %s/pkg/calc.py release the GIL while summing." % REL,
            "STATED_CONCURRENCY_NOT_ADDRESSED_BY_CAPABILITY")

    def test_a_definition_count_fuzzes_nothing(self):
        self._refused_with(
            "Fuzz the function add in %s/pkg/calc.py for integer overflow." % REL,
            "STATED_FUZZ_OR_PROPERTY_RUN_NOT_PERFORMED_BY_CAPABILITY")

    # ------------------------------------------------- the neighbours the gate must not touch
    def test_a_performance_review_is_still_the_perf_gate(self):
        """The matrix case that must stay REAL: a DESCRIPTION of performance is not a change."""
        registry = door.load_verified_registry()
        gate = registry.get("python.review.diff_perf_gate.v1") or {}
        self.assertTrue(gate, "the perf gate must exist")
        self.assertEqual(door.stated_answer_errors(
            "Run a performance review of %s/cov_calc.py." % REL, gate), [])

    def test_measuring_mutation_strength_is_still_a_measurement(self):
        registry = door.load_verified_registry()
        score = registry.get("python.tests.mutation_score.v1") or {}
        self.assertTrue(score)
        self.assertEqual(door.stated_answer_errors(
            "Measure the mutation score of %s/pkg/calc.py." % REL, score), [])

    def test_the_ordinary_neighbours_are_untouched(self):
        registry = door.load_verified_registry()
        dead = registry.get("python.source.dead_code.v1") or {}
        self.assertTrue(dead)
        self.assertEqual(door.stated_answer_errors(
            "Which function in %s/pkg is never called?" % REL, dead), [])
        self.assertEqual(door.stated_answer_errors(
            "How many functions are defined in %s/pkg/calc.py?" % REL, dead), [])

    # --------------------------------------- and a capability that really does it is admitted
    def test_a_real_profiler_would_be_admitted_by_its_declaration(self):
        profiler = {"capability_id": "python.source.profile.cprofile.v1",
                    "provides": ["python.source.profile.hotspot"],
                    "keywords": ["profile", "cprofile", "hotspot"]}
        self.assertEqual(door.stated_answer_errors(
            "Profile %s/pkg/calc.py and tell me which function is the hot spot." % REL, profiler), [])

    def test_a_real_threading_change_would_be_admitted_by_its_declaration(self):
        threading = {"capability_id": "python.source.concurrency.thread_pool.v1",
                     "provides": ["python.source.concurrency.threaded"],
                     "keywords": ["thread pool", "parallel", "concurrency"]}
        self.assertEqual(door.stated_answer_errors(
            "Make the function total in %s/pkg/calc.py release the GIL while summing." % REL,
            threading), [])

    def test_a_real_fuzzer_would_be_admitted_by_its_declaration(self):
        fuzzer = {"capability_id": "python.tests.fuzz.hypothesis.v1",
                  "provides": ["python.tests.fuzz.executed"],
                  "keywords": ["fuzz", "property-based", "hypothesis"]}
        self.assertEqual(door.stated_answer_errors(
            "Fuzz the function add in %s/pkg/calc.py for integer overflow." % REL, fuzzer), [])


if __name__ == "__main__":
    unittest.main()
