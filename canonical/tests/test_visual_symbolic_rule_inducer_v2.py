import unittest

from canonical.runtime.visual_symbolic_rule_inducer_v2 import induce, score_public_task


class VisualSymbolicRuleInducerV2Tests(unittest.TestCase):
    def test_global_mirror_is_single_symbolic_action(self):
        task = {
            "train": [
                {"input": [[1, 2, 3], [4, 5, 6]], "output": [[3, 2, 1], [6, 5, 4]]},
                {"input": [[7, 0, 8], [2, 9, 4]], "output": [[8, 0, 7], [4, 9, 2]]},
            ],
            "test": [
                {"input": [[6, 1, 9], [8, 3, 2]], "output": [[9, 1, 6], [2, 3, 8]]}
            ],
        }
        out = score_public_task(task)
        self.assertTrue(out["exact_task_solved"])
        self.assertEqual(out["induction"]["best_rule"]["kind"], "LEAF")
        self.assertEqual(out["induction"]["best_rule"]["action"], "COPY_MIRROR_H")

    def test_binary_else_route_handles_unseen_input_color(self):
        task = {
            "train": [
                {"input": [[0, 1, 0, 2]], "output": [[0, 8, 0, 8]]},
                {"input": [[3, 0, 4, 0]], "output": [[8, 0, 8, 0]]},
            ],
            "test": [
                {"input": [[0, 9, 5, 0]], "output": [[0, 8, 8, 0]]}
            ],
        }
        out = score_public_task(task, max_depth=3)
        self.assertTrue(out["exact_task_solved"])
        self.assertIn("IS_ZERO", out["induction"]["best_rule"]["signature"])

    def test_component_area_predicate_generalizes_to_unseen_larger_size(self):
        task = {
            "train": [
                {
                    "input": [
                        [1, 0, 2, 2],
                        [0, 0, 2, 2],
                        [3, 3, 0, 4],
                    ],
                    "output": [
                        [8, 0, 2, 2],
                        [0, 0, 2, 2],
                        [3, 3, 0, 8],
                    ],
                },
                {
                    "input": [
                        [5, 0, 6, 6, 0],
                        [0, 0, 0, 0, 7],
                        [9, 9, 9, 0, 0],
                    ],
                    "output": [
                        [8, 0, 6, 6, 0],
                        [0, 0, 0, 0, 8],
                        [9, 9, 9, 0, 0],
                    ],
                },
            ],
            "test": [
                {
                    "input": [
                        [2, 2, 2, 0, 4],
                        [0, 0, 0, 0, 0],
                        [6, 6, 0, 7, 0],
                    ],
                    "output": [
                        [2, 2, 2, 0, 8],
                        [0, 0, 0, 0, 0],
                        [6, 6, 0, 8, 0],
                    ],
                }
            ],
        }
        out = score_public_task(task, max_depth=4)
        self.assertTrue(out["exact_task_solved"])
        self.assertIn("COMPONENT_AREA", out["induction"]["best_rule"]["signature"])

    def test_color_invariant_neighborhood_diversity_rule(self):
        task = {
            "train": [
                {
                    "input": [
                        [0, 1, 0, 0, 0],
                        [1, 0, 1, 0, 0],
                        [0, 1, 0, 2, 0],
                        [0, 0, 2, 0, 2],
                        [0, 0, 0, 2, 0],
                    ],
                    "output": [
                        [0, 1, 0, 0, 0],
                        [1, 3, 1, 0, 0],
                        [0, 1, 0, 2, 0],
                        [0, 0, 2, 3, 2],
                        [0, 0, 0, 2, 0],
                    ],
                }
            ],
            "test": [
                {
                    "input": [[0, 7, 0], [7, 0, 7], [0, 7, 0]],
                    "output": [[0, 7, 0], [7, 3, 7], [0, 7, 0]],
                }
            ],
        }
        out = score_public_task(task, max_depth=4)
        self.assertTrue(out["exact_task_solved"])
        sig = out["induction"]["best_rule"]["signature"]
        self.assertTrue("N4_COLOR_COUNT" in sig or "N4_NONZERO" in sig)

    def test_shape_change_is_explicitly_out_of_scope(self):
        out = induce([{"input": [[1, 0]], "output": [[1], [0]]}])
        self.assertEqual(out["status"], "OUT_OF_SCOPE")
        self.assertEqual(out["reason"], "SHAPE_CHANGE_OUT_OF_SCOPE")


if __name__ == "__main__":
    unittest.main()
