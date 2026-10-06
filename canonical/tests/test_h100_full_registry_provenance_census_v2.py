import unittest
from canonical.runtime import h100_full_registry_provenance_census_v2 as c

class CensusV2Tests(unittest.TestCase):
    def test_counts_close_to_21_with_zero_unresolved(self):
        out=c.run()
        self.assertEqual(out["record_count"],21)
        self.assertEqual(out["category_counts"],{
          c.STRICT:9,c.POST:4,c.PRE:3,c.EXT:5,"PROVENANCE_UNRESOLVED":0
        })

    def test_known_representation_ceiling(self):
        x=c.run()["known_outcome_dependent_representation_ceiling"]
        self.assertEqual(x["strict_selection_index_bits"],54)
        self.assertEqual(x["postoutcome_implementation_source_bytes"],15196)
        self.assertEqual(x["aggregate_bits"],121622)
        self.assertEqual(x["ceil_bytes"],15203)

    def test_chronology_partition(self):
        out=c.run()
        self.assertEqual(set(out["postoutcome_v1_entries"]),{
          "CAP_LINEAR_TREND_SINUSOID_V1","CAP_EXP_ABS_V1","CAP_THRESHOLD_STEP_V1",
          "CAP_LEXICAL_SOURCE_FALLBACK_V1",
        })
        self.assertEqual(set(out["preoutcome_fixed_v1_entries"]),{
          "CAP_OEWN_REAL_LEXICAL_V1","CAP_COMPOSITIONAL_LANGUAGE_V1","CAP_TOOL_TRACE_NORMALIZER_V1",
        })

    def test_not_minimum_state_claim(self):
        txt=" ".join(c.run()["interpretation"])
        self.assertIn("NOT_MINIMUM_NECESSARY_PERSISTENT_STATE",txt)

if __name__=="__main__":
    unittest.main(verbosity=2)
