from __future__ import annotations
import unittest
from canonical.runtime import root1_capability_acquisition_controller_v1 as r1

def mapping():
    return {
        "source_primitive":"old:checkpoint",
        "target_primitive":"new:checkpoint",
        "relation":"EXACT",
        "mapping_basis":"CAUSAL_ISOMORPHISM",
        "verification_receipt":{
            "receipt_id":"m1",
            "independent_verified":True,
            "exact_byte_bound":True,
            "conclusion":"success",
            "source_primitive":"old:checkpoint",
            "target_primitive":"new:checkpoint",
            "relation":"EXACT",
            "mapping_basis":"CAUSAL_ISOMORPHISM",
        },
        "provenance_chain":["canonical:x"],
    }

class Tests(unittest.TestCase):
    def test_root1_dormant_without_positive_gap(self):
        out=r1.classify_root1({})
        self.assertFalse(out["root1_active"])
        self.assertEqual(out["status"],"ROOT1_INACTIVE_NO_ACTION")

    def test_unknown_does_not_reopen_root1(self):
        out=r1.classify_root1({"positive_operational_gap":True,"required_behavior":"x"})
        self.assertFalse(out["root1_active"])
        self.assertEqual(out["reason"],"UNKNOWN_OR_UNPROVED_IS_NOT_MISSING")

    def test_constructive_gap_reopens(self):
        out=r1.classify_root1({
            "positive_operational_gap":True,
            "required_behavior":"restore state",
            "constructive_witness_verified":True,
            "constructive_witness_content_addressed":True,
            "operative_failure_demonstrated":True,
            "acquisition_routes_accounted":True,
            "unresolved_after_available_acquisition":True,
        })
        self.assertTrue(out["root1_active"])

    def test_proven_transfer_shrinks_delta(self):
        out=r1.minimum_capability_delta(
            required_primitives={"new:checkpoint","new:novel"},
            verified_primitives={"old:checkpoint"},
            transfer_mappings=[mapping()],
        )
        self.assertEqual(out["missing_primitives"],["new:novel"])

    def test_paid_actions_are_removed_and_source_classes_orthogonalized(self):
        actions=[
            {"id":"web1","safe":True,"source_class":"web","p_close":"1/2","terminal_leverage":4,"information_gain":1,"transfer_gain":0,"proof_gain":0,"time":1,"risk":0,"incremental_spend_usd":0},
            {"id":"web2","safe":True,"source_class":"web","p_close":"4/5","terminal_leverage":4,"information_gain":1,"transfer_gain":0,"proof_gain":0,"time":2,"risk":0,"incremental_spend_usd":0},
            {"id":"code","safe":True,"source_class":"code","p_close":"1/2","terminal_leverage":4,"information_gain":1,"transfer_gain":0,"proof_gain":0,"time":1,"risk":0,"incremental_spend_usd":0},
            {"id":"paid","safe":True,"source_class":"paper","p_close":1,"terminal_leverage":99,"information_gain":99,"transfer_gain":99,"proof_gain":99,"time":1,"risk":0,"incremental_spend_usd":1},
        ]
        out=r1.select_orthogonal_portfolio(actions,max_actions=3,max_same_source_class=1)
        self.assertEqual({x["source_class"] for x in out},{"web","code"})
        self.assertNotIn("paid",[x["id"] for x in out])

    def test_correlation_penalizes_duplicate_information(self):
        actions=[
            {"id":"a","safe":True,"source_class":"web","p_close":"1/2","terminal_leverage":2,"information_gain":1,"transfer_gain":0,"proof_gain":0,"time":1,"risk":0,"correlation_with_selected":1,"incremental_spend_usd":0},
            {"id":"b","safe":True,"source_class":"code","p_close":"1/2","terminal_leverage":2,"information_gain":1,"transfer_gain":0,"proof_gain":0,"time":1,"risk":0,"correlation_with_selected":0,"incremental_spend_usd":0},
        ]
        out=r1.rank_acquisition_actions(actions)
        self.assertEqual(out[0]["id"],"b")

    def test_experiment_fallback_maximizes_information_density(self):
        out=r1.choose_experiment([
            {"id":"slow","safe":True,"expected_information_gain":4,"time":4,"risk":0,"incremental_spend_usd":0},
            {"id":"fast","safe":True,"expected_information_gain":3,"time":1,"risk":0,"incremental_spend_usd":0},
        ])
        self.assertEqual(out["id"],"fast")

    def test_graph_expansion(self):
        out=r1.mechanism_graph_frontier([{"id":"r","dependencies":["d"],"papers":["p"],"issues":["i"]}])
        self.assertEqual(len(out),3)

    def test_abstraction_requires_independent_exact_receipt(self):
        with self.assertRaises(r1.Root1ControllerError):
            r1.structural_abstraction(concrete_mechanism="x",abstract_pattern="y",verification_receipts=[{"receipt_id":"bad","independent_verified":False}])
        out=r1.structural_abstraction(
            concrete_mechanism="checkpoint retry",
            abstract_pattern="recoverable state machine",
            verification_receipts=[{"receipt_id":"ok","independent_verified":True,"exact_byte_bound":True,"conclusion":"success"}],
        )
        self.assertFalse(out["promotion_authorized"])

    def test_transaction_is_zero_action_while_root1_inactive(self):
        out=r1.acquisition_transaction(
            gap_evidence=None,
            required_primitives={"x"},
            verified_primitives=set(),
            actions=[{"id":"search","safe":True,"source_class":"web","p_close":1,"terminal_leverage":1,"information_gain":1,"time":1,"risk":0,"incremental_spend_usd":0}],
        )
        self.assertEqual(out["status"],"NO_ACTION_ROOT1_INACTIVE")
        self.assertEqual(out["selected_actions"],[])

if __name__=="__main__":
    unittest.main(verbosity=2)
