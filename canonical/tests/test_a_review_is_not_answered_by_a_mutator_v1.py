"""A REVIEW asks for a verdict about a file; a MUTATOR answers by editing it.

Measured 2026-10-31 in ``execution_guard/swe_capability_matrix_v1.py``, case
``security_review``: the sentence

    "Review <...>/security_review/cov/calc.py for security issues."

was answered by ``software.repair.choreograph.crossfile.v1`` -- a mutator -- which ran its
``dead_code_and_import_pruning`` mode over the reviewed project, EDITED a file the sentence had
only asked about (``bench_calc.py`` was damaged), and returned ``pass=True`` with no security
verdict anywhere in the artifact.  Two separate escape hatches let it through:

* ``review`` is not one of the read-only openers in ``_READ_ONLY_REQUEST_RE``, so the sentence was
  not even recognised as a question; and
* the choreographer lists read-sounding words among what it provides ("call graph", "crossfile"),
  so ``_READ_SURFACE_RE`` excused it from the read-only rule *while its own row declares that it
  edits source*, which is exactly the authority it then used.

The fix is drawn from the row's own declaration (``capability_edits_source``), not from a list of
verboten capability names, so the day a review gate is bound that really reads, it is admitted by
the same rule.  This module pins both halves: the review sentence cannot reach a writer, and a
sentence that really promises a change still can.
"""

import pathlib
import shutil
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import (  # noqa: E402
    goal_front_compiler_v1 as front,
    live_brain_route_admission_v1 as door,
)

SCRATCH = ROOT / "canonical/astra_runtime/tmp/review_is_not_a_mutator"
CHOREOGRAPHER = "software.repair.choreograph.crossfile.v1"
CALC = "def add(a, b):\n    return a + b\n"


def _rel(path: pathlib.Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _fresh(case: str) -> pathlib.Path:
    base = SCRATCH / case
    if base.exists():
        shutil.rmtree(base)
    (base / "cov").mkdir(parents=True)
    (base / "cov/calc.py").write_text(CALC, encoding="utf-8")
    return base


class AReviewIsAQuestion(unittest.TestCase):
    def test_review_is_recognised_as_a_read_only_request(self):
        for sentence in ("Review %s for security issues.",
                         "Please review the file %s.",
                         "Audit %s for vulnerabilities.",
                         "Run a security review of %s."):
            with self.subTest(sentence=sentence):
                self.assertTrue(door._REVIEW_REQUEST_RE.search(sentence % "x/calc.py")
                                or door._REVIEW_REQUEST_RE.search(sentence))

    def test_a_review_promises_no_change(self):
        self.assertFalse(door._sentence_promises_a_change(
            "Review canonical/runtime/x.py for security issues."))

    def test_but_review_and_fix_does_promise_a_change(self):
        """The rule is scoped by the sentence's promise, so this one keeps its writers."""
        self.assertTrue(door._sentence_promises_a_change(
            "Review and fix the security issues in canonical/runtime/x.py."))


class AMutatorCannotAnswerAReview(unittest.TestCase):
    def test_the_choreographer_declares_that_it_edits_source(self):
        entry = door.load_verified_registry()[CHOREOGRAPHER]
        self.assertTrue(front.capability_edits_source(entry),
                        "the rule below is drawn from this declaration; if it changes, so must the rule")

    def test_the_review_sentence_refuses_the_choreographer(self):
        entry = door.load_verified_registry()[CHOREOGRAPHER]
        goal = "Review %s for security issues." % _rel(_fresh("refuse") / "cov/calc.py")
        errors = door.stated_answer_errors(goal, entry, CHOREOGRAPHER)
        self.assertIn("STATED_READ_ONLY_QUESTION_ANSWERED_BY_A_WRITER:" + CHOREOGRAPHER, errors)

    def test_the_caller_question_is_still_refused_too(self):
        """The shape rule this belongs to already refused a mutator for a caller map; it must stay."""
        entry = door.load_verified_registry()[CHOREOGRAPHER]
        goal = "Find every caller of the function add in %s." % _rel(_fresh("callers") / "cov/calc.py")
        errors = door.stated_answer_errors(goal, entry, CHOREOGRAPHER)
        self.assertIn("STATED_READ_ONLY_QUESTION_ANSWERED_BY_A_WRITER:" + CHOREOGRAPHER, errors)

    def test_every_row_whose_provides_are_a_read_surface_keeps_the_escape(self):
        """The escape this change narrows must still hold where nothing declares a write.

        Scoped exactly as the rule is: ``_READ_SURFACE_RE`` over ``provides`` plus no declaration of
        source editing.  A row can still be refused by the OTHER predicate (``_MUTATION_PROVIDES_RE``
        over the same words) -- that is the rule as it stood before today and this change neither
        widens nor narrows it.
        """
        registry = door.load_verified_registry()
        goal = "Review %s for security issues." % _rel(_fresh("readers") / "cov/calc.py")
        offender = "STATED_READ_ONLY_QUESTION_ANSWERED_BY_A_WRITER:"
        checked = 0
        for cid, entry in registry.items():
            provides = " ".join(str(x) for x in (entry.get("provides") or []))
            if front.capability_edits_source(entry) or not door._READ_SURFACE_RE.search(provides):
                continue
            checked += 1
            errors = door.stated_answer_errors(goal, entry, cid)
            if any(e.startswith(offender) for e in errors):
                self.fail("%s reads for a living but was refused as a writer" % cid)
        self.assertGreater(checked, 0, "the escape must have at least one row to protect")


class TheDoorNeverLetsAWriterAnswerAReview(unittest.TestCase):
    def test_end_to_end_the_answer_is_not_a_mutator(self):
        base = _fresh("end_to_end")
        goal = "Review %s for security issues." % _rel(base / "cov/calc.py")
        result = door.solve({"task_id": "TEST_REVIEW_NOT_A_MUTATOR", "goal": goal}) or {}
        selected = str(result.get("compiled_capability_id") or "")
        registry = door.load_verified_registry()
        if selected:
            self.assertFalse(front.capability_edits_source(registry.get(selected) or {}),
                             "a review sentence was answered by a source editor: %s" % selected)
        # Whatever happened, the reviewed file is not the agent's to rewrite.
        self.assertEqual((base / "cov/calc.py").read_text(encoding="utf-8"), CALC)


if __name__ == "__main__":
    unittest.main()
