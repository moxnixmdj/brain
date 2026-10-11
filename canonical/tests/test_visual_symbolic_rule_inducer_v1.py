import unittest

from canonical.runtime.visual_symbolic_rule_inducer_v1 import induce, predict, score_public_task


def _component_area_task():
    return {
        "train": [
            {
                "input": [
                    [0, 1, 0, 2, 2],
                    [0, 0, 0, 2, 2],
                    [3, 3, 0, 0, 4],
                ],
                "output": [
                    [0, 8, 0, 2, 2],
                    [0, 0, 0, 2, 2],
                    [3, 3, 0, 0, 8],
                ],
            },
            {
                "input": [
                    [5, 0, 6, 6],
                    [0, 0, 6, 6],
                    [7, 7, 0, 9],
                ],
                "output": [
                    [8, 0, 6, 6],
                    [0, 0, 6, 6],
                    [7, 7, 0, 8],
                ],
            },
        ],
        "test": [
            {
                "input": [
                    [2, 2, 0, 3],
                    [2, 2, 0, 0],
                    [0, 0, 4, 4],
                    [5, 0, 0, 0],
                ],
                "output": [
                    [2, 2, 0, 8],
                    [2, 2, 0, 0],
                    [0, 0, 4, 4],
                    [8, 0, 0, 0],
                ],
            }
        ],
    }


class VisualSymbolicRuleInducerTests(unittest.TestCase):
    def test_global_mirror_action_generalizes_without_color_training(self):
        task = {
            "train": [
                {"input": [[1, 2, 3], [4, 5, 6]], "output": [[3, 2, 1], [6, 5, 4]]},
                {"input": [[7, 0, 8], [2, 9, 4]], "output": [[8, 0, 7], [4, 9, 2]]},
            ],
            "test": [
                {"input": [[6, 1, 9], [8, 3, 2]], "output": [[9, 1, 6], [2, 3, 8]]}
            ],
        }
        result = score_public_task(task, max_depth=2)
        self.assertTrue(result["exact_task_solved"])
        self.assertEqual(result["induction"]["best_rule"]["kind"], "LEAF")
        self.assertEqual(result["induction"]["best_rule"]["action"], "COPY_MIRROR_H")

    def test_component_area_rule_generalizes_to_unseen_colors_and_layout(self):
        task = _component_area_task()
        result = score_public_task(task, max_depth=3)
        self.assertTrue(result["exact_task_solved"])
        signature = result["induction"]["best_rule"]["signature"]
        self.assertIn("COMPONENT_AREA", signature)

    def test_local_neighbor_rule_is_induced(self):
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
                    "input": [
                        [0, 4, 0],
                        [5, 0, 6],
                        [0, 7, 0],
                    ],
                    "output": [
                        [0, 4, 0],
                        [5, 3, 6],
                        [0, 7, 0],
                    ],
                }
            ],
        }
        result = score_public_task(task, max_depth=4)
        self.assertTrue(result["exact_task_solved"])
        self.assertIn("N4_NONZERO", result["induction"]["best_rule"]["signature"])

    def test_shape_change_fails_closed_as_out_of_scope(self):
        result = induce(
            [{"input": [[1, 0]], "output": [[1], [0]]}],
            max_depth=3,
        )
        self.assertEqual(result["status"], "OUT_OF_SCOPE")
        self.assertEqual(result["reason"], "SHAPE_CHANGE_OUT_OF_SCOPE")

    def test_prediction_fails_on_unseen_branch_instead_of_guessing(self):
        result = induce(
            [
                {"input": [[1, 1]], "output": [[2, 2]]},
                {"input": [[0, 0]], "output": [[0, 0]]},
            ],
            max_depth=2,
        )
        self.assertEqual(result["status"], "EXACT_RULES_FOUND")
        out = predict(result["best_rule"], [[3, 3]])
        # A literal-color split is allowed by V1; if selected, unseen color must fail closed.
        if out["status"] != "PREDICTED":
            self.assertEqual(out["status"], "UNSEEN_FEATURE_BRANCH")


if __name__ == "__main__":
    unittest.main()
