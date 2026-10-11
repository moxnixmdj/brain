import unittest

from canonical.runtime.arc_conservative_combined_solver_v1 import score_public_task


class ArcConservativeCombinedSolverTests(unittest.TestCase):
    def test_program_inventor_fills_missing_incumbent_slot(self):
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
        out = score_public_task(task)
        self.assertTrue(out["exact_task_solved"])
        self.assertTrue(out["inventor_used"])
        self.assertTrue(any(x["source"] == "PROGRAM_INVENTOR" for x in out["attempts"]))

    def test_two_distinct_incumbent_bundles_are_not_evicted(self):
        task = {
            "train": [
                {"input": [[1, 1], [1, 1]], "output": [[1, 1], [1, 1]]},
            ],
            "test": [
                {"input": [[1, 2], [3, 4]], "output": [[1, 2], [3, 4]]},
            ],
        }
        out = score_public_task(task, max_depth=1)
        self.assertTrue(out["exact_task_solved"])
        self.assertGreaterEqual(out["direct_unique_bundle_count"], 2)
        self.assertFalse(out["inventor_used"])
        self.assertEqual([x["source"] for x in out["attempts"]], ["ARC_V16_DIRECT", "ARC_V16_DIRECT"])


if __name__ == "__main__":
    unittest.main()
