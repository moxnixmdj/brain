import unittest
from canonical.runtime import h100_lexical_coverage_bound_v1 as l

class H100LexicalCoverageBoundTests(unittest.TestCase):
    def test_constructive_witness_is_outside_finite_lexicon(self):
        lex=["predictor","response","covariate","regressor"]
        w=l.constructive_outside_term(lex)
        self.assertNotIn(w,lex)
        self.assertGreater(len(w),max(map(len,lex)))

    def test_empty_finite_lexicon_is_also_incomplete(self):
        self.assertFalse(l.finite_lexicon_open_world_complete([]))

    def test_every_finite_example_is_incomplete(self):
        for lex in (["a"],["a","bb"],["feature","target","label"]):
            self.assertFalse(l.finite_lexicon_open_world_complete(lex))

    def test_source_union_is_monotonic(self):
        out=l.monotonic_source_addition([["covariate"]],["regressor","covariate"])
        self.assertTrue(out["nondecreasing"])
        self.assertEqual(out["new_terms"],("regressor",))

    def test_jit_fail_closed_states(self):
        self.assertEqual(l.conditional_jit_certificate(term="x",source_records_present=False,source_query_complete=False,source_relations_conflict=False)["status"],"ABSTAIN_SOURCE_NOT_AVAILABLE")
        self.assertEqual(l.conditional_jit_certificate(term="x",source_records_present=True,source_query_complete=False,source_relations_conflict=False)["status"],"ABSTAIN_SOURCE_QUERY_INCOMPLETE")
        self.assertEqual(l.conditional_jit_certificate(term="x",source_records_present=True,source_query_complete=True,source_relations_conflict=True)["status"],"ABSTAIN_SOURCE_ROLE_CONFLICT")
        self.assertEqual(l.conditional_jit_certificate(term="x",source_records_present=True,source_query_complete=True,source_relations_conflict=False)["status"],"SOURCE_EVIDENCE_ADMISSIBLE_FOR_DETERMINISTIC_ROLE_BRIDGE")

if __name__=="__main__":
    unittest.main(verbosity=2)
