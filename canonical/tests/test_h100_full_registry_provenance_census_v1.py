import unittest
from canonical.runtime import h100_full_registry_provenance_census_v1 as c

class H100FullRegistryProvenanceCensusTests(unittest.TestCase):
    def test_full_count_and_categories(self):
        out=c.run()
        self.assertEqual(out["entry_count"],21)
        self.assertEqual(out["unique_stable_capability_id_count"],20)
        self.assertEqual(out["category_counts"],{
            c.STRICT:9,
            c.DEV_FIXED:3,
            c.EXTERNAL_FIXED:5,
            c.UNRESOLVED:4,
        })

    def test_cross_generation_tanh_id_collision_is_explicit(self):
        out=c.run()
        self.assertEqual(set(out["stable_id_collisions"]),{"CAP_AFFINE_TANH_V1"})
        rows=out["stable_id_collisions"]["CAP_AFFINE_TANH_V1"]
        self.assertEqual(sorted(x["registry_generation"] for x in rows),[3,6])
        self.assertEqual({x["category"] for x in rows},{c.STRICT,c.EXTERNAL_FIXED})
        self.assertEqual(out["census_identity_rule"],"REGISTRY_GENERATION_PLUS_CAPABILITY_ID")

    def test_strict_compact_selection_code_is_54_bits(self):
        out=c.run()
        self.assertEqual(out["strict_outcome_selected_compact_code"]["aggregate_fixed_length_bits"],54)
        self.assertEqual(out["strict_outcome_selected_compact_code"]["ceil_bytes"],7)

    def test_v3_support_code_is_bound_not_per_entry_fiction(self):
        out=c.run()
        row=next(x for x in out["strict_selection_codes"] if x["id"]=="V3_SUPPORT")
        self.assertEqual(row["support_set_count"],15)
        self.assertEqual(row["support_set_bits"],4)
        self.assertEqual(row["power_exponent_count"],5)
        self.assertEqual(row["power_exponent_bits"],3)
        self.assertEqual(row["aggregate_fixed_length_bits"],7)

    def test_rational_and_depth4_codes(self):
        out=c.run()
        v4=next(x for x in out["strict_selection_codes"] if x["id"]=="RATIONAL_V4")
        v8=next(x for x in out["strict_selection_codes"] if x["id"]=="DEPTH4_V8")
        self.assertEqual(v4["candidate_count"],2822)
        self.assertEqual(v4["fixed_length_bits"],12)
        self.assertEqual(v8["candidate_count_per_task"],1554)
        self.assertEqual(v8["fixed_length_bits_per_task"],11)
        self.assertEqual(v8["aggregate_fixed_length_bits"],33)

    def test_external_definitions_not_called_strict_learned(self):
        out=c.run()
        ids={x["capability_id"] for x in out["rows"] if x["category"]==c.EXTERNAL_FIXED}
        self.assertEqual(ids,{
            "CAP_AFFINE_ERF_V1","CAP_AFFINE_ATAN_V1","CAP_AFFINE_TANH_V1",
            "CAP_AFFINE_ASYM_CLAMP_V1","CAP_AFFINE_TRIANGLE_V1",
        })

    def test_unresolved_direct_v1_remains_unresolved(self):
        out=c.run()
        ids={x["capability_id"] for x in out["rows"] if x["category"]==c.UNRESOLVED}
        self.assertEqual(ids,{
            "CAP_OEWN_REAL_LEXICAL_V1","CAP_LEXICAL_SOURCE_FALLBACK_V1",
            "CAP_COMPOSITIONAL_LANGUAGE_V1","CAP_TOOL_TRACE_NORMALIZER_V1",
        })

    def test_dual_ledger_truth(self):
        out=c.run()
        self.assertTrue(out["ledger_summary"]["syntactic_v0_zero_learned_claim_for_registry"])
        self.assertFalse(out["ledger_summary"]["provenance_v1_zero_learned_claim_for_registry"])
        self.assertIsNone(out["ledger_summary"]["exact_total_provenance_v1_learned_bits"])
        self.assertEqual(out["h100_terminal_credit_delta"],0)

if __name__=="__main__":
    unittest.main(verbosity=2)
