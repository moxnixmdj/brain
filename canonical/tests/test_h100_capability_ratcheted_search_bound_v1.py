import unittest
from canonical.runtime import h100_capability_ratcheted_search_bound_v1 as r

class H100CapabilityRatchetedSearchBoundTests(unittest.TestCase):
    def test_selector_bits_logarithmic(self):
        self.assertEqual(r.ceil_log2_choices(1),0)
        self.assertEqual(r.ceil_log2_choices(2),1)
        self.assertEqual(r.ceil_log2_choices(3),2)
        self.assertEqual(r.ceil_log2_choices(1024),10)
        self.assertEqual(r.ceil_log2_choices(1025),11)

    def test_reference_bits(self):
        self.assertEqual(r.compiled_reference_bits(1024,40),51)

    def test_each_saved_bit_halves_bound(self):
        self.assertEqual(r.raw_dovetail_bound(20,100)//r.raw_dovetail_bound(19,100),2)

    def test_twenty_saved_bits_is_million_scale(self):
        self.assertEqual(r.exact_search_bound_ratio(60,40),1<<20)

    def test_library_doubling_costs_at_most_one_selector_bit(self):
        for n in (1,2,3,17,1000):
            self.assertLessEqual(r.ceil_log2_choices(2*n)-r.ceil_log2_choices(n),1)

    def test_compiled_bound(self):
        bits=r.compiled_reference_bits(256,24)
        self.assertEqual(bits,33)
        self.assertEqual(r.compiled_dovetail_bound(256,24,7),(1<<33)*7)

    def test_worse_reference_can_be_detected(self):
        self.assertLess(r.exact_search_bound_ratio(20,21),1.0)

    def test_certificate_zero_learned_credit(self):
        c=r.certificate(raw_program_bits=80,library_size=1024,parameter_bits_total=40,verifier_steps=100)
        self.assertEqual(c["compiled_reference_bits"],51)
        self.assertEqual(c["description_bit_reduction"],29)
        self.assertEqual(c["search_bound_ratio_raw_over_compiled"],1<<29)
        self.assertEqual(c["persistent_learned_bytes_added"],0)
        self.assertEqual(c["h100_terminal_credit_delta"],0)

if __name__=="__main__":
    unittest.main(verbosity=2)
