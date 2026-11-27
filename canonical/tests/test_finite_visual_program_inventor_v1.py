import unittest

from canonical.runtime.finite_visual_program_inventor_v1 import (
    PrimitiveSpec,
    invent,
    solve,
)
from canonical.runtime.arc_visual_program_invention_adapter_v1 import score_public_task


def _p(name, fn, cost=1.0):
    return PrimitiveSpec(
        primitive_id=name,
        input_type="GRID",
        output_type="GRID",
        cost=cost,
        source={"test": name},
        apply=fn,
    )


def _flip_h(g):
    return tuple(tuple(reversed(row)) for row in g)


def _trim_zero_left(g):
    if not all(row[0] == 0 for row in g):
        return None
    return tuple(tuple(row[1:]) for row in g)


def _double(g):
    return tuple(tuple(v * 2 for v in row) for row in g)


class FiniteVisualProgramInventorTests(unittest.TestCase):
    def test_depth_two_program_is_invented(self):
        examples = [
            {"input": [[0, 1, 2], [0, 3, 4]], "output": [[2, 1], [4, 3]]},
            {"input": [[0, 5, 6], [0, 7, 8]], "output": [[6, 5], [8, 7]]},
        ]
        out = invent(
            examples,
            [_p("TRIM_ZERO_LEFT", _trim_zero_left), _p("FLIP_HORIZONTAL", _flip_h)],
            max_depth=2,
        )
        self.assertEqual(out["status"], "EXACT_PROGRAMS_FOUND")
        self.assertGreaterEqual(out["exact_program_count"], 1)
        self.assertEqual(
            out["programs"][0]["primitive_ids"],
            ["TRIM_ZERO_LEFT", "FLIP_HORIZONTAL"],
        )
        self.assertEqual(out["programs"][0]["depth"], 2)
        self.assertIsNotNone(out["candidate_macro"])

    def test_training_equivalent_programs_preserve_unseen_ambiguity(self):
        examples = [{"input": [[1, 2, 1]], "output": [[1, 2, 1]]}]
        out = solve(
            examples,
            [[[1, 2, 3]]],
            [_p("FLIP_HORIZONTAL", _flip_h)],
            max_depth=1,
            attempts=2,
        )
        self.assertEqual(out["status"], "SOLVED_CANDIDATES")
        self.assertEqual(len(out["attempts"]), 2)
        predictions = [row["predictions"][0] for row in out["attempts"]]
        self.assertIn([[1, 2, 3]], predictions)
        self.assertIn([[3, 2, 1]], predictions)
        self.assertTrue(out["ambiguity_preserved"])

    def test_semantic_duplicate_keeps_lower_cost_representative(self):
        examples = [{"input": [[1, 2]], "output": [[2, 4]]}]
        out = invent(
            examples,
            [_p("DOUBLE_EXPENSIVE", _double, 2.0), _p("DOUBLE_CHEAP", _double, 1.0)],
            max_depth=1,
            max_equivalent_programs_per_semantics=1,
        )
        self.assertEqual(out["status"], "EXACT_PROGRAMS_FOUND")
        self.assertEqual(out["programs"][0]["primitive_ids"], ["DOUBLE_CHEAP"])

    def test_grammar_exhaustion_requests_representation_expansion(self):
        examples = [{"input": [[1, 0], [0, 0]], "output": [[2, 0], [0, 0]]}]
        out = invent(examples, [_p("FLIP_HORIZONTAL", _flip_h)], max_depth=2)
        self.assertEqual(out["status"], "GRAMMAR_EXHAUSTED__REPRESENTATION_EXPANSION_REQUIRED")
        self.assertEqual(
            out["next_action"],
            "SYNTHESIZE_SMALLEST_MISSING_REPRESENTATION_OR_PRIMITIVE_CLASS",
        )
        self.assertEqual(out["residual_summary"]["shape_relations"], {"SAME_SHAPE": 1})


    def test_arc_two_attempt_scoring_is_per_test_input(self):
        task = {
            "train": [
                {"input": [[1, 2, 1]], "output": [[1, 2, 1]]},
            ],
            "test": [
                {"input": [[1, 2, 3]], "output": [[1, 2, 3]]},
                {"input": [[4, 5, 6]], "output": [[6, 5, 4]]},
            ],
        }
        out = score_public_task(task, max_depth=1)
        self.assertTrue(out["exact_task_solved"])

    def test_arc_adapter_discovers_composed_program_on_fresh_synthetic_case(self):
        task = {
            "train": [
                {
                    "input": [
                        [0, 0, 0, 0],
                        [0, 1, 2, 0],
                        [0, 3, 4, 0],
                        [0, 0, 0, 0],
                    ],
                    "output": [[3, 1], [4, 2]],
                },
                {
                    "input": [
                        [0, 0, 0, 0],
                        [0, 5, 6, 0],
                        [0, 7, 8, 0],
                        [0, 0, 0, 0],
                    ],
                    "output": [[7, 5], [8, 6]],
                },
            ],
            "test": [
                {
                    "input": [
                        [0, 0, 0, 0],
                        [0, 2, 9, 0],
                        [0, 4, 7, 0],
                        [0, 0, 0, 0],
                    ],
                    "output": [[4, 2], [7, 9]],
                }
            ],
        }
        out = score_public_task(task, max_depth=2)
        self.assertTrue(out["exact_task_solved"])
        programs = out["program_invention"]["invention"]["programs"]
        self.assertTrue(any(p["depth"] == 2 for p in programs))


if __name__ == "__main__":
    unittest.main()
