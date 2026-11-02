"""An unstated requirement must be said out loud, named, and never guessed.

`goal_gap_statement_v1` consumes the structured refusal the goal compiler already
emits (`GoalCompilationFailure.detail` = `<capability>:<slot>:<reason>`) and turns
it into one actionable statement. These tests pin the four behaviours that make
that honest rather than decorative:

  1. a missing slot is NAMED, with the capability and the compiler's own reason;
  2. a value is never invented for it -- there is no field that could hold one;
  3. a refusal that reports no detail says the REPORT is the gap, not the goal;
  4. a goal that compiles is not thereby endorsed, because under-specified goals
     were measured to compile onto the wrong row 3 times in 12.

Cases are real goals compiled against the live registry. None needs a fixture and
none executes a capability.
"""

from __future__ import annotations

import unittest

from canonical.runtime.goal_gap_statement_v1 import (
    OUTCOMES,
    SCHEMA,
    state_the_gap,
    state_the_gaps,
)

# Measured 2026-11-02 against this tree; each is a real compiler outcome.
UNSTATED_EXPRESSION = "Evaluate the expression."
UNSTATED_STAGES = "Run the pipeline stages."
NO_DETAIL = "Read the text out of the picture."
COMPILES_ONTO_A_WRITER = "Query the data file and write the result out."
COMPILES_CLEANLY = "Create the archive from the manifest."


class GapStatementTest(unittest.TestCase):
    def test_a_missing_slot_is_named_with_its_capability_and_reason(self) -> None:
        got = state_the_gap(UNSTATED_EXPRESSION)
        self.assertEqual(got["schema"], SCHEMA)
        self.assertEqual(got["outcome"], "SLOT_UNSTATED")
        self.assertEqual(got["capability"], "math.numeric_expression.sympy")
        self.assertEqual(got["slot"], "expression")
        self.assertEqual(got["reason"], "value_not_parseable")
        # The statement must carry the slot name, or nothing downstream can act.
        self.assertIn("expression", got["statement"])
        self.assertIn("math.numeric_expression.sympy", got["statement"])

    def test_the_compilers_own_reason_is_carried_not_paraphrased_away(self) -> None:
        got = state_the_gap(UNSTATED_STAGES)
        self.assertEqual(got["outcome"], "SLOT_UNSTATED")
        self.assertEqual(got["slot"], "stages")
        self.assertEqual(got["reason"], "value_not_parseable")
        self.assertEqual(got["capability"], "execution.pipeline.8stage.v1")

    def test_no_value_is_ever_invented_for_a_slot_it_could_not_fill(self) -> None:
        got = state_the_gap(UNSTATED_EXPRESSION)
        # There is no field that could smuggle in a guessed value.
        for forbidden in ("value", "guessed_value", "inferred", "filled", "candidate_value"):
            self.assertNotIn(forbidden, got)
        self.assertIsNone(got.get("slot_value"))
        # And the statement must not read as though one had been supplied.
        self.assertNotIn("using value", got["statement"].lower())

    def test_a_refusal_with_no_detail_blames_the_report_not_the_goal(self) -> None:
        got = state_the_gap(NO_DETAIL)
        self.assertEqual(got["outcome"], "NO_CANDIDATE_REPORTED")
        self.assertIsNone(got["slot"])
        self.assertIsNone(got["capability"])
        low = got["statement"].lower()
        # The whole point: an empty report is a gap in the reporting, and saying
        # "the goal is missing X" here would be inventing an X.
        self.assertIn("no detail", low)
        self.assertIn("gap in the report", low)

    def test_a_goal_that_compiles_is_reported_but_not_endorsed(self) -> None:
        got = state_the_gap(COMPILES_CLEANLY)
        self.assertEqual(got["outcome"], "COMPILED")
        self.assertIsNotNone(got["capability"])
        self.assertIs(got["selection_endorsed"], False)

    def test_a_selection_the_goal_did_not_force_is_said_out_loud(self) -> None:
        """The dangerous case: the door binds a vague goal to a row it never asked
        for and reports success. Measured, this is how a JSON query reached a
        cross-file repair writer."""
        got = state_the_gap(COMPILES_ONTO_A_WRITER)
        self.assertEqual(got["outcome"], "LOW_CONFIDENCE_SELECTION")
        self.assertEqual(got["capability"], "software.repair.choreograph.crossfile.v1")
        self.assertIs(got["selection_endorsed"], False)
        ev = got["match_evidence"]
        # The rule is structural: the row declares requirements, the goal met none.
        self.assertTrue(got["declared_requires"])
        self.assertEqual(ev["matched_requires"], [])
        self.assertLess(ev["goal_token_coverage"], 0.5)
        low = got["statement"].lower()
        self.assertIn("not forced by the goal", low)
        self.assertIn("guess", low)
        # It must name the capability, or nothing downstream can act on it.
        self.assertIn("software.repair.choreograph.crossfile.v1", got["statement"])

    def test_a_forced_selection_is_not_flagged_as_a_guess(self) -> None:
        """The other half of the rule: a goal that does match what the row requires
        must NOT be flagged, or the signal is just noise on every request."""
        got = state_the_gap(COMPILES_CLEANLY)
        self.assertEqual(got["outcome"], "COMPILED")
        self.assertNotEqual(got["outcome"], "LOW_CONFIDENCE_SELECTION")
        self.assertTrue(got["match_evidence"]["matched_requires"])
        self.assertGreaterEqual(got["match_evidence"]["goal_token_coverage"], 0.5)

    def test_the_evidence_is_reported_not_just_the_verdict(self) -> None:
        """Score is carried as auditable evidence but is not the rule: a numeric
        cutoff fitted to 7 measured points would be overfitting."""
        for goal in (COMPILES_CLEANLY, COMPILES_ONTO_A_WRITER):
            ev = state_the_gap(goal)["match_evidence"]
            for field in ("score", "goal_tokens", "matched_provides",
                          "matched_requires", "goal_token_coverage"):
                self.assertIn(field, ev)

    def test_an_empty_goal_is_refused_rather_than_reported_as_a_gap(self) -> None:
        got = state_the_gap("")
        self.assertEqual(got["outcome"], "UNPARSEABLE_REPORT")
        self.assertIn("No goal", got["statement"])

    def test_every_outcome_it_can_return_is_declared(self) -> None:
        for goal in (UNSTATED_EXPRESSION, NO_DETAIL, COMPILES_ONTO_A_WRITER,
                     COMPILES_CLEANLY, ""):
            self.assertIn(state_the_gap(goal)["outcome"], OUTCOMES)

    def test_ranking_puts_the_actionable_statement_first(self) -> None:
        rows = state_the_gaps([NO_DETAIL, UNSTATED_EXPRESSION, COMPILES_ONTO_A_WRITER,
                               COMPILES_CLEANLY])
        self.assertEqual(len(rows), 4)
        # A selection the goal did not force comes first: ignoring it does the wrong
        # thing. A named missing slot merely stops. An empty report is unactionable.
        self.assertEqual(rows[0]["outcome"], "LOW_CONFIDENCE_SELECTION")
        self.assertEqual(rows[1]["outcome"], "SLOT_UNSTATED")
        self.assertEqual(rows[2]["outcome"], "COMPILED")
        self.assertEqual(rows[-1]["outcome"], "NO_CANDIDATE_REPORTED")

    def test_nothing_is_claimed_beyond_the_statement(self) -> None:
        for goal in (UNSTATED_EXPRESSION, NO_DETAIL, COMPILES_ONTO_A_WRITER, COMPILES_CLEANLY):
            got = state_the_gap(goal)
            self.assertEqual(got["authority"], "NONE")


if __name__ == "__main__":
    unittest.main()
