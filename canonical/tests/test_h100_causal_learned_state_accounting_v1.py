import unittest
from canonical.runtime.h100_causal_learned_state_accounting_v1 import *

class T(unittest.TestCase):
    def test_representation_relabel_invariant(self):
        r=representation_relabel_invariant(1024)
        self.assertTrue(r["invariant"])
        self.assertEqual(r["weights"],1024)
        self.assertEqual(r["source_constants"],1024)
        self.assertEqual(r["lookup_table"],1024)
    def test_ephemeral_runtime_fit_is_not_persistent_learned(self):
        self.assertEqual(runtime_fit_not_persisted(4096),0)
    def test_generic_preexposure_code_is_not_learned(self):
        self.assertEqual(generic_preexposure_code(4096),0)
    def test_persistent_postexperience_program_counts(self):
        a=PersistentArtifact(8192,True,True,False,"program")
        self.assertEqual(classify(a),"PERSISTENT_CAUSALLY_LEARNED")
        self.assertEqual(causal_learned_bits(a),8192)

if __name__=="__main__": unittest.main(verbosity=2)
