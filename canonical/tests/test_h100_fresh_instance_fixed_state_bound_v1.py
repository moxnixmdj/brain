import unittest
from canonical.runtime import h100_fresh_instance_fixed_state_bound_v1 as f

class FreshInstanceFixedStateBoundTests(unittest.TestCase):
    def test_two_opposite_worlds_half_for_any_fixed_state_size(self):
        for bits in (0,1,8,1024,1_000_000):
            self.assertEqual(
                f.deterministic_fixed_state_success_upper_bound([["INPUT","TARGET"]],bits),
                0.5,
            )

    def test_majority_bound_independent_of_state_size(self):
        classes=[["A","A","A","B"],["C","D","D"]]
        want=(3+2)/7
        for bits in (0,4,100,100000):
            self.assertEqual(f.deterministic_fixed_state_success_upper_bound(classes,bits),want)

    def test_randomization_cannot_beat_majority(self):
        classes=[["A","A","A","B"],["C","D","D"]]
        self.assertEqual(
            f.randomized_fixed_state_success_upper_bound(classes,10**6),
            f.deterministic_fixed_state_success_upper_bound(classes,0),
        )

    def test_runtime_evidence_split_can_raise_bound(self):
        coarse=[["INPUT","TARGET"]]
        split=[["INPUT"],["TARGET"]]
        self.assertEqual(f.deterministic_fixed_state_success_upper_bound(coarse,10**6),0.5)
        self.assertEqual(f.deterministic_fixed_state_success_upper_bound(split,0),1.0)

    def test_same_label_worlds_need_no_distinction(self):
        self.assertEqual(f.deterministic_fixed_state_success_upper_bound([["A","A","A"]],0),1.0)

    def test_state_size_sweep_is_flat(self):
        out=f.state_size_sweep([["A","B"]],[0,1,8,1024])
        self.assertFalse(out["state_size_changes_information_bound"])
        self.assertEqual({x["deterministic_upper_bound"] for x in out["rows"]},{0.5})

    def test_certificate(self):
        c=f.fresh_instance_certificate([["A","B","B"]])
        self.assertEqual(c["fixed_state_information_upper_bound"],2/3)
        self.assertFalse(c["fixed_state_size_affects_bound"])
        self.assertEqual(c["h100_terminal_credit_delta"],0)

    def test_invalid_bits_fail_closed(self):
        with self.assertRaises(f.FreshInstanceBoundError):
            f.deterministic_fixed_state_success_upper_bound([["A"]],-1)

if __name__=="__main__":
    unittest.main(verbosity=2)
