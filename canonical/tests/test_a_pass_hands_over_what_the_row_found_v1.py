# PROJECT_BRAIN
"""A PASS hands over what the row found.

Measured 2026-11-01 on ``34124aa``, by re-running the repository's own 49-sentence advanced census
and its 54-case capability matrix and recording the field the census does not record --
``answer``:

    census    SERVED 34 / 49   ... of which delivered an answer:  1
    matrix    REAL   42 / 54   ... of which delivered an answer:  5

Seventy of the 77 passing executions wrote a report to ``output_path`` that held the answer, and
the door read none of them.  ``asked()`` recognises thirteen nouns; everything else fell through
``shape is None`` to ``return []``.  The work was done, the row named its findings, the caller was
told nothing.  This is the ``observed_effect`` defect of PR #6504 one level up: the projection was
reading the sentence's grammar instead of the result it was handed.

Four laws, all narrowings and all measured against a real row result:

1. THE SURFACE IS WHAT THE ROW RETURNED.  Nothing is invented: a field is delivered only if the
   row produced it, and the bookkeeping every row fills in (``schema``, ``adapter``, ``gate``,
   ``verified``, ``output_path``…) is not part of the answer.
2. THE SENTENCE PICKS THE FIELD WHEN IT CAN.  ``hot spot`` → ``hot_spot_function``;
   ``root cause`` → ``root_causes``; ``migration`` → ``migration_steps``.
3. WHEN NO FIELD NAME MATCHES, THE WHOLE SURFACE IS THE ANSWER.  A question answered deserves
   the answer even when the row named it something the sentence did not anticipate; losing it
   would be the same defect with better manners.
4. A ROW THAT NAMED ITS ANSWER HAS ANSWERED.  ``{"answer": "apply_discount"}`` is delivered
   untouched -- the pinned law ``test_the_gate_stays_out_of_the_way_for_a_named_answer``.
"""

from __future__ import annotations

import unittest

from canonical.runtime import answer_shape_v1 as shape


def _row(**fields):
    """A result whose single execution is a row that produced ``fields``."""
    base = {"schema": "SOME_ROW_SCHEMA", "adapter": "some_adapter", "capability_id": "c.v1",
            "dependency": "local", "verified": True, "gate": "PASS",
            "output_path": "canonical/tmp/report_abc.json", "output_sha256": "0" * 64,
            "output_verified": True}
    base.update(fields)
    return {"pass": True, "status": "PASS__MEASURED",
            "execution": [{"capability_id": "c.v1", "result": base}]}


class TheSentencePicksTheField(unittest.TestCase):
    def test_a_hot_spot_question_is_answered_by_the_hot_spot(self) -> None:
        result = _row(operation="profile_hotspot", function_profiles=[{"name": "total"}],
                      hot_spot_function="total", hot_spot_elapsed_ns=42)
        self.assertEqual(shape.deliver("Profile pkg/util.py and tell me which function is the "
                                       "hot spot.", result), [])
        self.assertEqual(result["answer"]["field"], "hot_spot_function")
        self.assertEqual(result["answer"]["value"], "total")

    def test_a_root_cause_question_is_answered_by_the_root_cause(self) -> None:
        result = _row(operation="diagnose_test_suite", failed_tests=["test_add"],
                      cause="ZeroDivisionError", root_causes=[{"test": "test_add"}])
        shape.deliver("The test in tests/test_calc.py fails; find the root cause.", result)
        self.assertEqual(result["answer"]["field"], "root_causes")

    def test_an_adr_request_is_answered_by_the_adr(self) -> None:
        result = _row(operation="design_api", api_types=["RateLimiter"],
                      adr_markdown="# ADR: Rate limiter\n\nToken bucket.")
        shape.deliver("Design the API for a rate limiter and write an ADR.", result)
        self.assertEqual(result["answer"]["field"], "adr_markdown")
        self.assertIn("Rate limiter", result["answer"]["value"])

    def test_a_migration_plan_is_answered_by_its_steps(self) -> None:
        result = _row(operation="migration_plan", module_count=4,
                      migration_steps=[{"file": "a.py", "steps": ["upgrade"]}])
        shape.deliver("Plan the migration of the package in pkg from Python 3.9 to 3.12.", result)
        self.assertEqual(result["answer"]["field"], "migration_steps")

    def test_a_vulnerability_audit_is_answered_by_its_findings(self) -> None:
        result = _row(operation="audit_dependencies", dependency_count=2,
                      vulnerabilities=[{"package": "x", "advisory": "CVE-1"}],
                      unpinned_dependencies=["y"])
        shape.deliver("Audit the dependency list in pyproject.toml for known vulnerabilities.",
                      result)
        self.assertEqual(result["answer"]["field"], "vulnerabilities")


class WhenNoFieldNameMatches(unittest.TestCase):
    def test_the_whole_surface_is_delivered_rather_than_nothing(self) -> None:
        result = _row(operation="review_api_design", public_symbols=["service.py:area"],
                      finding_count=1, findings=[{"issue": "MISSING_MODULE_DOCSTRING"}])
        shape.deliver("Review pkg/service.py for API design problems.", result)
        self.assertEqual(result["answer"]["field"], "result")
        self.assertIn("findings", result["answer"]["value"])

    def test_the_bookkeeping_is_never_the_answer(self) -> None:
        result = _row(operation="whatever", finding_count=0, findings=[])
        shape.deliver("Review pkg/service.py for API design problems.", result)
        for plumbing in ("schema", "adapter", "gate", "verified", "output_path",
                         "output_sha256", "output_verified", "dependency", "capability_id"):
            self.assertNotIn(plumbing, result["answer"]["value"], plumbing)

    def test_a_row_that_produced_only_bookkeeping_is_left_alone(self) -> None:
        result = _row()
        self.assertEqual(shape.deliver("Review pkg/service.py for API design problems.", result), [])
        self.assertIsNone(result.get("answer"))

    def test_a_count_is_delivered_as_a_count(self) -> None:
        result = _row(operation="audit_dependencies", dependency_count=0, vulnerabilities=[])
        shape.deliver("Audit the dependency list in pyproject.toml for known vulnerabilities.",
                      result)
        self.assertEqual(result["answer"]["value"], [])


class ThePinnedNeighboursAreUntouched(unittest.TestCase):
    def test_a_row_that_named_its_answer_has_answered(self) -> None:
        result = {"execution": [{"capability_id": "python.fault.localize.v1",
                                 "result": {"answer": "apply_discount"}}]}
        self.assertEqual(shape.deliver("Which function in a/app is at fault?", result), [])
        self.assertNotIn("answer", {k for k in result if k != "execution"})

    def test_an_enumeration_still_goes_through_the_noun_projection(self) -> None:
        result = {"execution": [{"capability_id": "python.source.symbol_index.v1",
                                 "result": {"callers_of": {"build_plan": ["a"]},
                                            "file_count": 2}}]}
        shape.deliver("Find every caller of build_plan in pkg", result)
        self.assertEqual(result["answer"]["noun"], "caller")
        self.assertEqual(result["answer"]["field"], "callers_of")

    def test_a_refusal_reason_still_wins_over_the_surface(self) -> None:
        """A shape that CANNOT be served stays a refusal; the surface never rescues it."""
        result = {"execution": [{"capability_id": "python.source.audit.ast",
                                 "result": {"function_count": 10, "files": ["a.py"]}}]}
        reasons = shape.deliver("List the functions in pkg/x.py", result)
        self.assertTrue(reasons)
        self.assertNotIn("answer", {k for k in result if k != "execution"})


if __name__ == "__main__":
    unittest.main()


class ARowThatNamedItsOwnAnswerIsStillDelivered(unittest.TestCase):
    """Not re-shaping and not delivering are two different decisions.

    ``python.source.complexity.v1`` and ``python.source.definition_count.v1`` answer with a field
    literally named ``answer``.  The gate must not wrap it (pinned), and the door must not drop
    it -- measured 2026-11-01: both matrix cases PASSed with ``answer: None`` on the result while
    the row held the answer one level down.
    """

    def test_the_named_answer_is_lifted_verbatim(self) -> None:
        result = {"pass": True,
                  "execution": [{"capability_id": "python.source.complexity.v1",
                                 "result": {"answer": 7, "worst_function": "f",
                                            "output_path": "x.json"}}]}
        self.assertTrue(shape.lift_named_answer(result))
        self.assertEqual(result["answer"], 7)

    def test_an_existing_answer_is_never_replaced(self) -> None:
        result = {"answer": {"noun": "caller"}, "execution": [
            {"capability_id": "c", "result": {"answer": "other"}}]}
        self.assertFalse(shape.lift_named_answer(result))
        self.assertEqual(result["answer"], {"noun": "caller"})

    def test_a_row_with_no_named_answer_lifts_nothing(self) -> None:
        result = {"execution": [{"capability_id": "c", "result": {"function_count": 3}}]}
        self.assertFalse(shape.lift_named_answer(result))
        self.assertNotIn("answer", result)
