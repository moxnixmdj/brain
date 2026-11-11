import unittest
import canonical.runtime.universal_escape_obstruction_reduction_v2 as reduction

class UniversalEscapeObstructionReductionV2Tests(unittest.TestCase):
    def test_current_exact_sources_reduce_to_single_unsplittable_conflict_root(self):
        out=reduction.verify_reduction(repo_root="/home/sprite")
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["only_live_universal_obstruction"],
            "TARGET_SUPPORTED_REACHABLE_UNSPLITTABLE_POLICY_CONFLICT_CLASS")
        self.assertFalse(out["serial_db_region_enumeration_required"])
        self.assertFalse(out["complete_discriminator_library_required_for_positive_cover"])
        self.assertFalse(out["exact_true_world_enumeration_required_for_positive_cover"])
        self.assertEqual(out["current_constructive_witness_family"],"GDPVAL_HIDDEN_EVALUATOR_RELATION")
        self.assertFalse(out["u_empty_authorized"])
        self.assertFalse(out["terminal_authority"])

    def test_forged_source_hash_fails_closed(self):
        original=reduction.SOURCES["frontier"]
        reduction.SOURCES["frontier"]=(original[0],"0"*40)
        try:
            out=reduction.verify_reduction(repo_root="/home/sprite")
        finally:
            reduction.SOURCES["frontier"]=original
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"],"SOURCE_BINDING_INVALID")
        self.assertFalse(out["u_empty_authorized"])

if __name__=="__main__":
    unittest.main()
