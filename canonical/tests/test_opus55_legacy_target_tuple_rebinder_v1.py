import json
import pathlib
import unittest
import importlib.util

ROOT=pathlib.Path(__file__).resolve().parents[1]
RUNTIME=ROOT/"runtime"/"opus55_legacy_target_tuple_rebinder_v1.py"
DOC=ROOT/"governance"/"OPUS55_LEGACY_TARGET_TUPLE_REBIND_20261005_V1.json"

EXPECTED={
    "CODING_TB4_GE_66_4":66.4,
    "CHARTOGRAPHY_TOOLS_GE_89":89.0,
    "HLE_TOOLS_GE_67_7":67.7,
    "OSWORLD_2_1_PARTIAL_GE_81_8":81.8,
    "CODING_FRONTIERCODE_GE_54_4":54.4,
    "PROWORK_GDPVAL_GE_1846":1846,
    "PROWORK_AA_BRIEFCASE_GE_1822":1822,
    "ARTIFACT_AA_BRIEFCASE_GE_1822":1822,
    "AUTOMATIONBENCH_GE_40":40.0,
    "TB_SCIENCE_GE_58_7":63.33333333333333,
}

class LegacyTargetTupleRebindTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not RUNTIME.exists():
            raise AssertionError("rebinder runtime missing")
        if not DOC.exists():
            raise AssertionError("rebinder governance missing")
        spec=importlib.util.spec_from_file_location("rebinder",RUNTIME)
        cls.m=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.m)
        cls.doc=json.loads(DOC.read_text())

    def test_exact_ten_legacy_predicates_bound(self):
        out=self.m.validate(self.doc)
        self.assertEqual(set(out["bound_predicates"]),set(EXPECTED))
        self.assertEqual(out["remaining_unbound_legacy"],0)

    def test_frozen_values_preserved_except_prelocked_tb_science_override(self):
        by={x["predicate_id"]:x for x in self.doc["bindings"]}
        for pid,value in EXPECTED.items():
            self.assertEqual(by[pid]["effective_target_value"],value)
        self.assertEqual(by["TB_SCIENCE_GE_58_7"]["predicate_label_target_value"],58.7)
        self.assertEqual(by["TB_SCIENCE_GE_58_7"]["route_id"],"PUBLIC_CURRENT_HARNESS")
        self.assertGreater(by["TB_SCIENCE_GE_58_7"]["consumed_brain_slots"],0)

    def test_shared_aa_briefcase_tuple_reused_without_rating_rebase(self):
        by={x["predicate_id"]:x for x in self.doc["bindings"]}
        a=by["PROWORK_AA_BRIEFCASE_GE_1822"]
        b=by["ARTIFACT_AA_BRIEFCASE_GE_1822"]
        self.assertEqual(a["target_tuple_id"],b["target_tuple_id"])
        self.assertEqual(a["rating_pool_snapshot"],"FROZEN_PUBLICATION_SNAPSHOT_2026_09_22")
        self.assertEqual(a["effective_target_value"],1822)

    def test_all_tuple_fields_are_explicit_and_no_current_live_board_rebase(self):
        required={"benchmark","benchmark_version","model","effort","evaluator","harness","fallback_policy","unit"}
        for row in self.doc["bindings"]:
            self.assertTrue(required.issubset(row["target_tuple"]))
            self.assertTrue(all(row["target_tuple"][k] for k in required))
            self.assertNotEqual(row.get("target_source_role"),"LIVE_BOARD_REBASE")

    def test_zero_credit_and_score_execution_still_blocked(self):
        out=self.m.validate(self.doc)
        self.assertEqual(out["acceptance_credit_delta"],0)
        self.assertFalse(out["score_execution_authority"])
        self.assertFalse(out["promotion_authority"])

if __name__=="__main__":
    unittest.main(verbosity=2)
