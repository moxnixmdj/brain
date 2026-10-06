import unittest
from canonical.runtime import h100_finite_benchmark_compiler_loophole_v1 as m

class T(unittest.TestCase):
    def test_perfect_finite_memorization(self):
        p=[({"q":"a"},1),({"q":"b"},2),({"q":"c"},3)]
        c=m.certificate(p)
        self.assertEqual(c["benchmark_accuracy"],1.0)
        self.assertEqual(c["persistent_learned_bytes"],0)
        self.assertGreater(c["capability_bearing_deterministic_code_bytes"],0)
    def test_unseen_fails_closed(self):
        t=m.compile_lookup([(1,"x")])
        with self.assertRaises(m.CompilerLoopholeError): m.run_lookup(t,2)
    def test_nonfunctional_rejected(self):
        with self.assertRaises(m.CompilerLoopholeError): m.compile_lookup([(1,"a"),(1,"b")])
    def test_code_size_grows_with_payload(self):
        self.assertGreater(m.canonical_code_bytes([(1,"x"*100)]),m.canonical_code_bytes([(1,"x")]))
if __name__=="__main__": unittest.main(verbosity=2)
