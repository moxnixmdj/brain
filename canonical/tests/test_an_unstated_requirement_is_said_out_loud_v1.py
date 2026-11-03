"""An unstated requirement must be said out loud, named, and never guessed.

`goal_gap_statement_v1` consumes the structured refusal the goal compiler already
emits (`GoalCompilationFailure.detail` = `<capability>:<slot>:<reason>`) and turns
it into one actionable statement. These tests pin the four behaviours that make
that honest rather than decorative:

  1. a missing slot is NAMED, with the capability and the compiler's own reason;
  2. a value is never invented for it -- there is no field that could hold one;
  3. a refusal that reports no detail says the REPORT is the gap, not the goal;
  4. a goal that compiles is not thereby endorsed. This module does not vouch for a
     selection -- and it does not claim to know which selections are wrong either.
     The "3 times in 12" figure that originally justified this bullet was measured at
     the compiler alone; at the full door, which runs route_admission after compiling,
     2 of those 3 are refused and the third asks to "write the result out", so a
     writer is not clearly wrong. Non-endorsement does not depend on that figure and
     survives its withdrawal.

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
# The counterexample that retracted the confidence rule: scores 37 and matches 3
# of its 4 goal tokens on `provides`, yet its row's precondition is
# `structured.json.available`, so matched_requires is empty.
STRONG_MATCH = "Create a DOCX document report."


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

    def test_a_strong_match_is_not_accused_of_being_a_guess(self) -> None:
        """REGRESSION TEST FOR A RETRACTED RULE.

        A rule merged on 2026-11-02 called any selection whose row declares
        `requires` that the goal did not match a LOW_CONFIDENCE_SELECTION, and told
        the reader that acting on it would be acting on a guess. On this goal it
        fired. docx.document.create_from_json_record scores 37 -- above every one of
        the 4 correct cases in the n=7 sample that produced the rule -- and matches
        create, document and docx, 3 of the 4 goal tokens, on what the row PROVIDES.
        Its matched_requires is empty only because the row's precondition is
        `structured.json.available`: a fact about the world, not a word a sentence
        would contain.

        The rule was measuring vocabulary coincidence. Across all 149 bound rows,
        182 of 182 `requires` tokens are dotted world-precondition identifiers, so
        matched_requires is non-empty only when a goal happens to share a sub-token
        with one -- "Create the archive from the manifest" matched
        `manifest.json.available` on the word "manifest" alone, which is why the n=7
        separation looked clean.
        """
        got = state_the_gap(STRONG_MATCH)
        self.assertEqual(got["outcome"], "COMPILED")
        self.assertIs(got["selection_endorsed"], False)
        ev = got["match_evidence"]
        self.assertGreaterEqual(len(ev["matched_provides"]), 2)
        self.assertEqual(ev["matched_requires"], [])
        low = got["statement"].lower()
        for phrase in ("guess", "not forced", "did not force", "low confidence"):
            self.assertNotIn(phrase, low)

    def test_no_verdict_separates_a_strong_match_from_a_weak_one(self) -> None:
        """Both compile, both get the same outcome, and neither is judged.

        Telling this strong match apart from a JSON query bound to a cross-file
        repair writer is a semantic question about what the sentence asks for and
        what the capability does. The two overlap on every lexical field the compiler
        emits, so no deterministic function of score, matched_provides or
        matched_requires separates them -- and answering it anyway would mean putting
        model cognition in the producer path, which
        GENERAL_COGNITION_SUBSTRATE_AND_CAPABILITY_OWNERSHIP_LAW_V4 forbids.
        """
        strong = state_the_gap(STRONG_MATCH)
        weak = state_the_gap(COMPILES_ONTO_A_WRITER)
        self.assertEqual(strong["outcome"], weak["outcome"])
        self.assertEqual(strong["outcome"], "COMPILED")
        self.assertIs(strong["selection_endorsed"], False)
        self.assertIs(weak["selection_endorsed"], False)
        self.assertNotIn("LOW_CONFIDENCE_SELECTION", OUTCOMES)

    def test_the_evidence_is_reported_uninterpreted(self) -> None:
        """Only the verdict was withdrawn; the evidence stays auditable.

        A consumer can still read score and coverage. It is simply no longer told
        what they mean, because what they meant turned out to be nothing.
        """
        for goal in (STRONG_MATCH, COMPILES_CLEANLY, COMPILES_ONTO_A_WRITER):
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
                     COMPILES_CLEANLY, STRONG_MATCH, ""):
            self.assertIn(state_the_gap(goal)["outcome"], OUTCOMES)

    def test_ranking_puts_the_actionable_statement_first(self) -> None:
        rows = state_the_gaps([NO_DETAIL, UNSTATED_EXPRESSION, COMPILES_ONTO_A_WRITER,
                               COMPILES_CLEANLY])
        self.assertEqual(len(rows), 4)
        # A named missing slot is the only actionable statement, so it comes first.
        # No position in this ordering expresses confidence in a selection.
        self.assertEqual(rows[0]["outcome"], "SLOT_UNSTATED")
        self.assertEqual(rows[1]["outcome"], "COMPILED")
        self.assertEqual(rows[2]["outcome"], "COMPILED")
        self.assertEqual(rows[-1]["outcome"], "NO_CANDIDATE_REPORTED")

    def test_nothing_is_claimed_beyond_the_statement(self) -> None:
        for goal in (UNSTATED_EXPRESSION, NO_DETAIL, COMPILES_ONTO_A_WRITER,
                     COMPILES_CLEANLY, STRONG_MATCH):
            got = state_the_gap(goal)
            self.assertEqual(got["authority"], "NONE")


if __name__ == "__main__":
    unittest.main()
