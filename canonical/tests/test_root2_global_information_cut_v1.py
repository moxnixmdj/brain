import unittest

from canonical.runtime.root2_global_information_cut_v1 import Action, solve


class GlobalCutTests(unittest.TestCase):
    def test_shared_action_beats_two_single_actions(self):
        preds = ["A", "B", "C"]
        actions = [
            Action("a", frozenset({"A"}), 5, 0, 1, ()),
            Action("b", frozenset({"B"}), 5, 0, 1, ()),
            Action("ab", frozenset({"A", "B"}), 4, 0, 1, ()),
            Action("c", frozenset({"C"}), 3, 0, 1, ()),
        ]
        out = solve(preds, actions)
        self.assertEqual(out["unresolved_predicate_count"], 0)
        self.assertEqual(out["selected_root_actions"], ["ab", "c"])

    def test_dependency_is_counted(self):
        preds = ["A"]
        actions = [
            Action("preflight", frozenset({"IGNORED"}), 2, 0, 1, ()),
            Action("measure", frozenset({"A"}), 3, 1, 1, ("preflight",)),
        ]
        out = solve(preds, actions)
        self.assertEqual(out["selected_with_dependencies"], ["measure", "preflight"])
        self.assertEqual(out["objective"]["action_count"], 2)
        self.assertEqual(out["objective"]["reality_units"], 1)

    def test_partial_cut_reports_unresolved(self):
        out = solve(
            ["A", "B"],
            [Action("a", frozenset({"A"}), 1, 0, 1, ())],
        )
        self.assertEqual(out["covered_predicates"], ["A"])
        self.assertEqual(out["unresolved_predicates"], ["B"])


if __name__ == "__main__":
    unittest.main()
