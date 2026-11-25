"""Mechanism sketches: honest tests.

These tests hold the four mechanisms to their contracts:
slotting (a list is one hole, not five), candidates (read from the observation,
never from imagination), render (AST substitution, never string splicing), and
bind-and-verify (the goal decides; a rendering that cannot be bound is refused).
"""
from __future__ import annotations

import unittest

from canonical.runtime import mechanism_sketch_v1 as sketch


class ParameterizeTests(unittest.TestCase):
    def test_a_list_literal_is_one_hole(self):
        out = sketch.parameterize("statistics.median([3, 1, 4, 1, 5])")
        self.assertEqual(out["status"], "PASS__SLOTTED")
        self.assertEqual(out["template"], "statistics.median(S0)")
        self.assertEqual(len(out["slots"]), 1)
        self.assertEqual(out["slots"][0]["kind"], "sequence")

    def test_scalar_constants_get_their_own_holes(self):
        out = sketch.parameterize("round(3.14159, 2)")
        self.assertEqual(out["template"], "round(S0, S1)")
        self.assertEqual([s["kind"] for s in out["slots"]], ["scalar:number", "scalar:number"])

    def test_boolean_and_none_are_mechanism_not_data(self):
        out = sketch.parameterize("bool(True)")
        self.assertEqual(out["template"], "bool(True)")
        self.assertEqual(out["slots"], [])

    def test_statement_is_refused_not_guessed(self):
        out = sketch.parameterize("x = 1")
        self.assertEqual(out["status"], "REFUSED__NOT_AN_EXPRESSION")

    def test_slot_start_keeps_names_unique_across_steps(self):
        first = sketch.parameterize("f([1, 2], 3)", slot_start=0)
        second = sketch.parameterize("g([4, 5], 6)", slot_start=len(first["slots"]))
        ids = [s["id"] for s in first["slots"]] + [s["id"] for s in second["slots"]]
        self.assertEqual(ids, ["S0", "S1", "S2", "S3"])

    def test_more_than_eight_slots_refused(self):
        out = sketch.parameterize("f(1, 2, 3, 4, 5, 6, 7, 8, 9)")
        self.assertEqual(out["status"], "REFUSED__MORE_THAN_8_SLOTS")

    def test_nested_constant_structure_is_one_hole(self):
        out = sketch.parameterize("matrix_rank([[1, 0], [0, 1]])")
        # the whole constant structure is data, so it is ONE hole -- the
        # template keeps working for a matrix of any shape
        self.assertEqual(out["status"], "PASS__SLOTTED")
        self.assertEqual(out["template"], "matrix_rank(S0)")
        self.assertEqual([s["kind"] for s in out["slots"]], ["sequence"])


class CandidateTests(unittest.TestCase):
    def test_sequences_and_numbers_come_from_the_observation(self):
        cand = sketch.candidate_values(("input", (3, 1, 4, 1, 5)))
        self.assertIn((3, 1, 4, 1, 5), cand["sequence"])
        self.assertIn(3, cand["number"])
        self.assertIn(4, cand["number"])
        self.assertEqual(cand["string"], ["input"])

    def test_nested_mapping_is_walked(self):
        cand = sketch.candidate_values({"task": "sort", "data": [10, 20, 30]})
        self.assertIn((10, 20, 30), cand["sequence"])
        self.assertIn("sort", cand["string"])


class RenderTests(unittest.TestCase):
    def test_render_substitutes_by_ast_not_splicing(self):
        out = sketch.render("statistics.median(S0)", {"S0": (1, 2, 3, 4, 5)})
        self.assertEqual(out, "statistics.median((1, 2, 3, 4, 5))")

    def test_render_round_trips_through_the_parser(self):
        import ast
        ast.parse(sketch.render("round(S0, S1)", {"S0": 3.14159, "S1": 2}), mode="eval")


class BindAndVerifyTests(unittest.TestCase):
    def _steps(self):
        return [{"template": "statistics.median(S0)",
                 "slots": [{"id": "S0", "kind": "sequence"}]}]

    def test_binding_that_reaches_goal_wins(self):
        ran = []

        def execute(stmt):
            ran.append(stmt)

        def is_goal():
            return bool(ran) and "(1, 2, 3, 4, 5)" in ran[-1]

        out = sketch.bind_plan_and_verify(
            self._steps(),
            {"sequence": [(9, 9, 9), (1, 2, 3, 4, 5)], "number": [], "string": []},
            execute, is_goal)
        self.assertEqual(out["status"], "PASS__BOUND_AND_GOAL_OBSERVED")
        self.assertEqual(out["tried"], 2)
        self.assertIn("(1, 2, 3, 4, 5)", out["rendered"][0])

    def test_no_candidates_is_a_refusal(self):
        out = sketch.bind_plan_and_verify(
            self._steps(), {"sequence": [], "number": [], "string": []},
            lambda s: None, lambda: False)
        self.assertEqual(out["status"], "REFUSED__NO_CANDIDATE_FOR_SLOT")

    def test_no_binding_reaching_goal_is_refused_with_count(self):
        out = sketch.bind_plan_and_verify(
            self._steps(),
            {"sequence": [(1, 2)], "number": [], "string": []},
            lambda s: None, lambda: False)
        self.assertEqual(out["status"], "REFUSED__NO_BINDING_REACHED_GOAL")
        self.assertEqual(out["tried"], 1)

    def test_bind_limit_is_a_refusal_not_a_truncation(self):
        out = sketch.bind_plan_and_verify(
            [{"template": "f(S0, S1)",
              "slots": [{"id": "S0", "kind": "scalar:number"}, {"id": "S1", "kind": "scalar:number"}]}],
            {"number": [1, 2, 3, 4], "sequence": [], "string": []},
            lambda s: None, lambda: False, limit=3)
        self.assertEqual(out["status"], "REFUSED__BIND_LIMIT_REACHED")
        self.assertEqual(out["tried"], 3)


if __name__ == "__main__":
    unittest.main()
