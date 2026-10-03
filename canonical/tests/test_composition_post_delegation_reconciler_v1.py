from __future__ import annotations
import copy, json, unittest
from canonical.runtime import composition_post_delegation_reconciler_v1 as rec

class Tests(unittest.TestCase):
    def test_current_exact_sources_reconcile_to_two_components(self):
        out=rec.evaluate()
        self.assertTrue(out["status"].startswith("PASS"),out)
        self.assertEqual(out["source_blob_drift"],[])
        self.assertTrue(out["stale_v3_zero_of_12_invalidated_by_current_delegation_closure"])
        self.assertTrue(out["tool_discovery_remains_quarantined"])
        self.assertEqual(out["current_admissible_scoped_proved"],2)
        self.assertEqual(out["current_open_or_quarantined"],10)
        self.assertEqual(out["scoped_proved_components"],["delegation","memory"])
        self.assertFalse(out["parent_composition_predicate_closed"])

    def test_delegation_reopens_only_if_current_scope_complete_claim_is_proved(self):
        a=json.loads((rec.ROOT/rec.FILES["acceptance"][0]).read_text(encoding="utf-8"))
        a=copy.deepcopy(a)
        row=next(x for x in a["claims"] if x["predicate_id"]=="DELEGATION_TERMINAL_SUCCESS_NONINFERIOR")
        row["state"]="EXTERNAL_BLOCKED"
        out=rec.evaluate(acceptance_override=a)
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("CURRENT_DELEGATION_SCOPE_COMPLETE_ACCEPTANCE_NOT_PROVED",out["errors"])

    def test_tool_discovery_cannot_sneak_back_in(self):
        a=json.loads((rec.ROOT/rec.FILES["acceptance"][0]).read_text(encoding="utf-8"))
        a=copy.deepcopy(a)
        row=next(x for x in a["claims"] if x["predicate_id"]=="TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR")
        row["state"]="PROVED"
        out=rec.evaluate(acceptance_override=a)
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("TOOL_DISCOVERY_MUST_REMAIN_QUARANTINED",out["errors"])

    def test_memory_scope_must_remain_owned_and_closed(self):
        m=json.loads((rec.ROOT/rec.FILES["memory_package"][0]).read_text(encoding="utf-8"))
        m=copy.deepcopy(m)
        m["decision"]["parent_family_closed_for_claim_scope"]=False
        out=rec.evaluate(memory_package_override=m)
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("MEMORY_PARENT_FAMILY_NOT_CLOSED_FOR_CLAIM_SCOPE",out["errors"])

    def test_zero_credit_and_zero_reality(self):
        out=rec.evaluate()
        self.assertEqual(out["new_reality_units_consumed"],0)
        self.assertEqual(out["terminal_results_replayed"],0)
        self.assertEqual(out["incremental_spend_usd"],0)
        self.assertEqual(out["capability_credit_delta"],0)
        self.assertEqual(out["family_credit_delta"],0)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])

if __name__=="__main__":
    unittest.main(verbosity=2)
