"""A mutation score is measured, not asserted -- and not required to be a diff gate.

The capability matrix's oracle for ``mutation_score`` used to accept only
``PROJECT_BRAIN_DIFF_MUTATION_GATE_V1`` with ``gate: PASS``, so the sentence

    "Measure the mutation score of <...>/cov/calc.py."

was scored FALSE even when ``python.tests.mutation_score.v1`` had really run every mutant: measured
2026-10-31 that run produced two mutants, both killed, ``mutation_score: 1.0`` -- a correct answer
graded wrong because it arrived in the shape of the row that answers the sentence.

The oracle now accepts both shapes, but never a self-report: the score row must have enumerated its
mutants and the arithmetic must close.  This module pins that, in both directions.
"""

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import importlib.util  # noqa: E402

_SPEC = importlib.util.spec_from_file_location(
    "swe_capability_matrix_v1", ROOT / "execution_guard/swe_capability_matrix_v1.py")
matrix = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(matrix)

SCORE_SCHEMA = "PROJECT_BRAIN_PYTHON_TESTS_MUTATION_SCORE_V1"


def _doc(*, total=2, killed=2, survived=0, score=1.0, mutants=None):
    if mutants is None:
        mutants = ([{"function": "add", "operator": "AOR", "status": "killed"}] * killed
                   + [{"function": "mul", "operator": "AOR", "status": "survived"}] * survived)
    return {"schema": SCORE_SCHEMA, "total_mutants": total, "mutation_score": score,
            "killed_count": killed, "survived_count": survived, "mutants": mutants}


class _WithArtifact:
    """Run the oracle against a document written where the matrix would look for it."""

    def __init__(self, doc):
        self.doc = doc

    def __enter__(self):
        self.base = ROOT / "canonical/astra_runtime/tmp/mutation_oracle"
        self.base.mkdir(parents=True, exist_ok=True)
        self.path = self.base / "artifact.json"
        import json
        self.path.write_text(json.dumps(self.doc), encoding="utf-8")
        self.result = {"execution": [{"result": {"output_path": self.path.relative_to(ROOT).as_posix()}}]}
        return self.result

    def __exit__(self, *exc):
        return False


class TheScoreRowIsAccepted(unittest.TestCase):
    def test_every_mutant_killed_and_the_arithmetic_closes(self):
        with _WithArtifact(_doc()) as result:
            self.assertTrue(matrix._mutation_score_measured(ROOT, result))

    def test_a_partial_score_is_still_a_real_measurement(self):
        with _WithArtifact(_doc(total=2, killed=1, survived=1, score=0.5)) as result:
            self.assertTrue(matrix._mutation_score_measured(ROOT, result))


class ASelfReportIsNot(unittest.TestCase):
    def test_a_score_that_does_not_match_its_mutants_is_refused(self):
        with _WithArtifact(_doc(total=2, killed=1, survived=1, score=1.0)) as result:
            self.assertFalse(matrix._mutation_score_measured(ROOT, result))

    def test_a_score_with_no_mutants_enumerated_is_refused(self):
        with _WithArtifact(_doc(total=2, killed=0, survived=0, score=0.0, mutants=[])) as result:
            self.assertFalse(matrix._mutation_score_measured(ROOT, result))

    def test_an_unknown_status_is_refused(self):
        mutants = [{"function": "add", "operator": "AOR", "status": "killed"},
                   {"function": "mul", "operator": "AOR", "status": "timeout"}]
        with _WithArtifact(_doc(total=2, killed=1, survived=0, score=0.5, mutants=mutants)) as result:
            self.assertFalse(matrix._mutation_score_measured(ROOT, result))


if __name__ == "__main__":
    unittest.main()
