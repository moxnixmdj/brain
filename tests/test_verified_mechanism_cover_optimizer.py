import importlib.util
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PATH = ROOT / "canonical" / "runtime" / "verified_mechanism_cover_optimizer.py"
spec = importlib.util.spec_from_file_location("verified_mechanism_cover_optimizer", PATH)
opt = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = opt
spec.loader.exec_module(opt)


class VerifiedMechanismCoverOptimizerTests(unittest.TestCase):
    def test_shared_dependency_counted_once(self):
        s = {
            "required_behaviors": ["A", "B"],
            "mechanisms": [
                {"id": "shared", "bytes": 80, "covers": []},
                {"id": "a", "bytes": 20, "covers": ["A"], "dependencies": ["shared"]},
                {"id": "b", "bytes": 20, "covers": ["B"], "dependencies": ["shared"]},
                {"id": "whole", "bytes": 130, "covers": ["A", "B"]},
            ],
        }
        r = opt.solve(s)
        self.assertEqual(r["status"], "OPTIMAL_OVER_ENUMERATED_LIBRARY")
        self.assertEqual(r["total_unique_bytes"], 120)
        self.assertEqual(r["selected_mechanisms"], ["a", "b", "shared"])

    def test_ineligible_dependency_blocks_choice(self):
        s = {
            "required_behaviors": ["A"],
            "mechanisms": [
                {"id": "base", "bytes": 1, "covers": [], "eligible": False},
                {"id": "adapter", "bytes": 1, "covers": ["A"], "dependencies": ["base"]},
                {"id": "owned", "bytes": 5, "covers": ["A"]},
            ],
        }
        r = opt.solve(s)
        self.assertEqual(r["selected_mechanisms"], ["owned"])
        self.assertEqual(r["total_unique_bytes"], 5)

    def test_missing_behavior_unsat(self):
        s = {"required_behaviors": ["A", "B"], "mechanisms": [{"id": "a", "bytes": 1, "covers": ["A"]}]}
        r = opt.solve(s)
        self.assertEqual(r["status"], "UNSATISFIABLE")
        self.assertEqual(r["missing_behaviors"], ["B"])

    def test_cycle_rejected(self):
        s = {
            "required_behaviors": ["A"],
            "mechanisms": [
                {"id": "a", "bytes": 1, "covers": ["A"], "dependencies": ["b"]},
                {"id": "b", "bytes": 1, "covers": [], "dependencies": ["a"]},
            ],
        }
        with self.assertRaises(opt.SpecError):
            opt.solve(s)

    def test_tie_break_is_deterministic(self):
        s = {
            "required_behaviors": ["A"],
            "mechanisms": [
                {"id": "b", "bytes": 1, "covers": ["A"]},
                {"id": "a", "bytes": 1, "covers": ["A"]},
            ],
        }
        r = opt.solve(s)
        self.assertEqual(r["selected_mechanisms"], ["a"])

    def test_conflicts_can_make_cheapest_pair_invalid(self):
        s = {
            "required_behaviors": ["A", "B"],
            "mechanisms": [
                {"id": "a", "bytes": 1, "covers": ["A"], "conflicts": ["b"]},
                {"id": "b", "bytes": 1, "covers": ["B"], "conflicts": ["a"]},
                {"id": "ab", "bytes": 3, "covers": ["A", "B"]},
            ],
        }
        r = opt.solve(s)
        self.assertEqual(r["selected_mechanisms"], ["ab"])
        self.assertEqual(r["total_unique_bytes"], 3)


if __name__ == "__main__":
    unittest.main()
