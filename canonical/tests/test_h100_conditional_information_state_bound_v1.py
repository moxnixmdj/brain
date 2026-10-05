import unittest
from canonical.runtime import h100_conditional_information_state_bound_v1 as c

class ConditionalInformationStateBoundTests(unittest.TestCase):
    def test_no_evidence_recovers_unconditional_bound(self):
        self.assertEqual(c.success_upper_bound([16],0),1/16)
        self.assertEqual(c.success_upper_bound([16],2),4/16)

    def test_perfect_runtime_evidence_needs_zero_bits(self):
        self.assertEqual(c.success_upper_bound([1]*20,0),1.0)
        self.assertEqual(c.minimum_bits_for_target([1]*20,1.0),0)

    def test_partial_partition_interpolates(self):
        sizes=[4,4,2]
        self.assertEqual(c.success_upper_bound(sizes,0),3/10)
        self.assertEqual(c.success_upper_bound(sizes,1),6/10)
        self.assertEqual(c.success_upper_bound(sizes,2),1.0)

    def test_zero_bit_bound_is_class_count_over_n(self):
        for sizes in ([5],[2,3],[1,1,8],[1,1,1,1]):
            self.assertEqual(c.zero_bit_upper_bound(sizes),len(sizes)/sum(sizes))

    def test_bits_for_perfect_identification_depends_on_largest_class(self):
        stats=c.residual_ambiguity_stats([1,2,7,3])
        self.assertEqual(stats["bits_for_perfect_identification"],3)

    def test_certificate(self):
        out=c.certificate([8,8,8,8],learned_bits=1,target_success=0.5)
        self.assertEqual(out["success_upper_bound"],0.25)
        self.assertTrue(out["target_ruled_out_by_current_bits"])
        self.assertEqual(out["minimum_bits_for_target"],2)

    def test_more_runtime_separation_never_hurts_zero_bit_bound(self):
        coarse=[10]
        split=[4,6]
        finer=[1,3,2,4]
        self.assertLess(c.zero_bit_upper_bound(coarse),c.zero_bit_upper_bound(split))
        self.assertLess(c.zero_bit_upper_bound(split),c.zero_bit_upper_bound(finer))

    def test_invalid_inputs_fail_closed(self):
        with self.assertRaises(c.ConditionalInformationBoundError):
            c.success_upper_bound([],0)
        with self.assertRaises(c.ConditionalInformationBoundError):
            c.success_upper_bound([1,0],0)
        with self.assertRaises(c.ConditionalInformationBoundError):
            c.success_upper_bound([1],-1)

if __name__=="__main__":
    unittest.main(verbosity=2)
