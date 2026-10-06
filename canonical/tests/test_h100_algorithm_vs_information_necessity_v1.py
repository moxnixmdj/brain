import unittest
from canonical.runtime import h100_algorithm_vs_information_necessity_v1 as n

class T(unittest.TestCase):
    def test_complete_computable(self):
        c=n.deterministic_function_certificate(runtime_information_complete=True,function_computable=True)
        self.assertTrue(c["zero_world_dependent_learned_bits_information_theoretically_sufficient"])
        self.assertFalse(c["positive_learned_bits_information_theoretically_necessary"])
    def test_incomplete(self):
        c=n.deterministic_function_certificate(runtime_information_complete=False,function_computable=True)
        self.assertFalse(c["zero_world_dependent_learned_bits_information_theoretically_sufficient"])
        self.assertIsNone(c["positive_learned_bits_information_theoretically_necessary"])
    def test_lookup(self):
        f=n.finite_lookup_program([(1,"a"),(2,"b")])
        self.assertEqual(f(2),"b")
    def test_nonfunctional(self):
        with self.assertRaises(n.NecessityError): n.finite_lookup_program([(1,"a"),(1,"b")])
    def test_out_of_domain(self):
        f=n.finite_lookup_program([(1,"a")])
        with self.assertRaises(n.NecessityError): f(2)
    def test_description_nonzero(self):
        self.assertGreater(n.finite_solver_description_bytes([(1,"a")]),0)
    def test_role(self):
        self.assertEqual(n.learned_state_role(carries_instance_specific_missing_information=False,carries_algorithm_or_prior=True,carries_world_knowledge=False),"ALGORITHM_OR_PRIOR")
    def test_certificate(self):
        self.assertIn("PROGRAM_DESCRIPTION_LENGTH",n.certificate()["core"]["remaining_possible_barriers"])
if __name__=="__main__": unittest.main(verbosity=2)
