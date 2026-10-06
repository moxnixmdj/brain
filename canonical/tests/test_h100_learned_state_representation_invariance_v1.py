import unittest
from canonical.runtime import h100_learned_state_representation_invariance_v1 as r

class T(unittest.TestCase):
    def test_capability_preserved_after_embedding(self):
        w={"bias":-0.75,"slope":1.625}
        a=r.naive_filetype_accounting(w)
        self.assertTrue(a["same_capability"])
        self.assertGreater(a["weights_file_learned_bytes"],0)
        self.assertEqual(a["compiled_source_naively_counted_learned_bytes"],0)
    def test_provenance_accounting_counts_embedded_constants(self):
        w={"bias":1.0,"slope":2.0}
        a=r.provenance_accounting(w)
        self.assertTrue(a["must_count_as_learned_derived"])
        self.assertGreater(a["persistent_training_derived_capability_bytes_lower_bound"],0)
    def test_nonfinite_rejected(self):
        with self.assertRaises(r.RepresentationAccountingError):
            r.compile_weights_into_program_literals({"bias":0.0,"slope":float("nan")})
if __name__=="__main__": unittest.main(verbosity=2)
