import math
import unittest

from canonical.runtime import h100_information_state_lower_bound_v1 as b


class H100InformationStateLowerBoundTests(unittest.TestCase):
    def test_zero_bits_binary_hidden_world_is_chance(self):
        self.assertEqual(b.exact_identification_success_upper_bound(2, 0), 0.5)

    def test_zero_bits_n_worlds_is_one_over_n(self):
        for n in (1, 2, 3, 10, 257):
            self.assertEqual(b.exact_identification_success_upper_bound(n, 0), 1.0 / n)

    def test_b_bits_cover_at_most_two_to_b_worlds(self):
        self.assertEqual(b.exact_identification_success_upper_bound(16, 2), 0.25)
        self.assertEqual(b.exact_identification_success_upper_bound(16, 4), 1.0)

    def test_minimum_bits_for_perfect_identification(self):
        for n in (1, 2, 3, 4, 5, 8, 9, 1024, 1025):
            want = 0 if n == 1 else math.ceil(math.log2(n))
            self.assertEqual(b.minimum_bits_for_average_success(n, 1.0), want)

    def test_minimum_bits_for_partial_success(self):
        self.assertEqual(b.minimum_bits_for_average_success(100, 0.5), 6)
        self.assertEqual(b.minimum_bits_for_average_success(100, 0.01), 0)

    def test_binary_witness(self):
        w = b.binary_hidden_bit_zero_learned_bound()
        self.assertEqual(w["average_success_upper_bound"], 0.5)
        self.assertEqual(w["worst_case_exact_success_upper_bound"], 0.5)

    def test_certificate_detects_impossible_target(self):
        c = b.certificate(world_count=64, learned_bits=3, target_success=0.5)
        self.assertEqual(c["success_upper_bound"], 0.125)
        self.assertTrue(c["target_ruled_out_by_current_bits"])
        self.assertEqual(c["minimum_bits_required_by_counting_bound"], 5)
        self.assertEqual(c["h100_terminal_credit_delta"], 0)

    def test_invalid_inputs_fail_closed(self):
        with self.assertRaises(b.InformationStateBoundError):
            b.exact_identification_success_upper_bound(0, 0)
        with self.assertRaises(b.InformationStateBoundError):
            b.exact_identification_success_upper_bound(2, -1)
        with self.assertRaises(b.InformationStateBoundError):
            b.minimum_bits_for_average_success(2, 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
