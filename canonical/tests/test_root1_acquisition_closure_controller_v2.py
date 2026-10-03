from __future__ import annotations

import unittest
from canonical.runtime import root1_acquisition_closure_controller_v2 as r1

def transfer_mapping():
    return {
        "source_primitive": "old:p",
        "target_primitive": "new:q",
        "relation": "EXACT",
        "mapping_basis": "CAUSAL_ISOMORPHISM",
        "verification_receipt": {
            "receipt_id": "map",
            "independent_verified": True,
            "exact_byte_bound": True,
            "conclusion": "success",
            "source_primitive": "old:p",
            "target_primitive": "new:q",
            "relation": "EXACT",
            "mapping_basis": "CAUSAL_ISOMORPHISM",
        },
        "provenance_chain": ["canonical:x"],
    }

def owned(pid, rid):
    return {
        "primitive_id": pid,
        "route_id": rid,
        "route_status": "VERIFIED_OWNED",
        "independent_verified": True,
        "exact_byte_bound": True,
        "content_addressed": True,
        "target_brain_owned_configuration": True,
        "future_use_requires_capability_rediscovery": False,
        "incremental_spend_usd": 0,
    }

def acquisition(pid, rid):
    out = owned(pid, rid)
    out.update({
        "route_status": "VERIFIED_ACQUISITION_ROUTE",
        "internalizable": True,
        "executable": True,
        "source_admission_verified": True,
    })
    return out

class Tests(unittest.TestCase):
    def test_root1_is_zero_action_without_constructive_gap(self):
        out = r1.acquisition_transaction(
            gap_evidence=None,
            required_primitives={"x"},
            verified_primitives=set(),
            actions=[{"id":"tempting","safe":True,"source_class":"code","p_close":1,"closure_mass":99,"time":1,"risk":0,"incremental_spend_usd":0}],
        )
        self.assertEqual(out["status"], "NO_ACTION_ROOT1_INACTIVE")
        self.assertEqual(out["selected_actions"], [])

    def test_unknown_is_not_missing(self):
        out = r1.classify_root1({"positive_operational_gap":True,"required_behavior":"x"})
        self.assertFalse(out["root1_active"])
        self.assertEqual(out["reason"], "UNKNOWN_OR_UNPROVED_IS_NOT_MISSING")

    def test_constructive_gap_reopens_root1(self):
        e = {
            "positive_operational_gap": True,
            "required_behavior": "x",
            "constructive_witness_verified": True,
            "constructive_witness_content_addressed": True,
            "operative_failure_demonstrated": True,
            "acquisition_routes_accounted": True,
            "unresolved_after_available_acquisition": True,
        }
        self.assertTrue(r1.classify_root1(e)["root1_active"])

    def test_verified_structural_transfer_reduces_delta(self):
        out = r1.minimum_capability_delta(
            required_primitives={"new:q","new:r"},
            verified_primitives={"old:p"},
            transfer_mappings=[transfer_mapping()],
        )
        self.assertEqual(out["missing_primitives"], ["new:r"])

    def test_frozen_envelope_seals_only_with_complete_receipt_and_routes(self):
        required = {"a","b"}
        receipt = {
            "independent_verified": True,
            "exact_byte_bound": True,
            "conclusion": "success",
            "capability_set_complete": True,
            "envelope_id": "opus55-frozen",
            "primitive_set_sha256": r1._digest(required),
        }
        out = r1.compile_frozen_envelope(
            envelope_id="opus55-frozen",
            required_primitives=required,
            coverage_records=[owned("a","ra"), acquisition("b","rb")],
            envelope_receipt=receipt,
        )
        self.assertTrue(out["root1_sealed_for_frozen_envelope"])
        self.assertEqual(out["status"], "ROOT1_CLOSED_FOR_FROZEN_ENVELOPE")
        self.assertFalse(out["universal_semantic_learning_success_claimed"])

    def test_envelope_does_not_seal_with_unverified_or_paid_route(self):
        required = {"a","b"}
        receipt = {
            "independent_verified": True,
            "exact_byte_bound": True,
            "conclusion": "success",
            "capability_set_complete": True,
            "envelope_id": "e",
            "primitive_set_sha256": r1._digest(required),
        }
        bad = acquisition("b","rb")
        bad["incremental_spend_usd"] = 1
        out = r1.compile_frozen_envelope(
            envelope_id="e",
            required_primitives=required,
            coverage_records=[owned("a","ra"), bad],
            envelope_receipt=receipt,
        )
        self.assertFalse(out["root1_sealed_for_frozen_envelope"])
        self.assertEqual(out["uncovered_primitives"], ["b"])

    def test_false_envelope_receipt_is_rejected(self):
        with self.assertRaises(r1.Root1ClosureError):
            r1.compile_frozen_envelope(
                envelope_id="e",
                required_primitives={"a"},
                coverage_records=[owned("a","ra")],
                envelope_receipt={"independent_verified":True},
            )

    def test_action_ranking_removes_paid_and_orthogonalizes_sources_and_clusters(self):
        actions = [
            {"id":"code1","safe":True,"source_class":"code","dependency_cluster":"same","p_close":"1/2","closure_mass":4,"information_gain":1,"time":1,"risk":0,"incremental_spend_usd":0},
            {"id":"code2","safe":True,"source_class":"code","dependency_cluster":"other","p_close":1,"closure_mass":10,"information_gain":1,"time":1,"risk":0,"incremental_spend_usd":0},
            {"id":"paper","safe":True,"source_class":"paper","dependency_cluster":"same","p_close":1,"closure_mass":8,"information_gain":1,"time":1,"risk":0,"incremental_spend_usd":0},
            {"id":"paid","safe":True,"source_class":"social","dependency_cluster":"paid","p_close":1,"closure_mass":999,"information_gain":999,"time":1,"risk":0,"incremental_spend_usd":1},
        ]
        out = r1.select_orthogonal_portfolio(actions, max_actions=3)
        ids = [x["id"] for x in out]
        self.assertNotIn("paid", ids)
        self.assertEqual(len({x["source_class"] for x in out}), len(out))
        self.assertEqual(len({x["dependency_cluster"] for x in out}), len(out))

    def test_search_does_not_stop_on_consensus_without_scope_proof(self):
        out = r1.search_stop_decision(
            selected_route_id="r",
            required_source_classes={"brain","code","papers","official","social"},
            searched_source_classes={"brain","code"},
        )
        self.assertFalse(out["decision_complete"])
        remaining = out["remaining_source_classes"]
        receipt = {
            "independent_verified": True,
            "exact_byte_bound": True,
            "conclusion": "success",
            "all_remaining_sources_action_invariant": True,
            "selected_route_id": "r",
            "remaining_source_classes_sha256": r1._digest(remaining),
        }
        closed = r1.search_stop_decision(
            selected_route_id="r",
            required_source_classes={"brain","code","papers","official","social"},
            searched_source_classes={"brain","code"},
            invariance_receipt=receipt,
        )
        self.assertTrue(closed["decision_complete"])

    def test_mechanism_graph_uses_source_native_edges(self):
        out = r1.mechanism_graph_frontier([{
            "id":"x",
            "dependencies":["d"],
            "official_docs":["doc"],
            "papers":["p"],
            "issues":["i"],
            "community_discussions":["c"],
        }])
        self.assertEqual(len(out), 5)

if __name__ == "__main__":
    unittest.main(verbosity=2)
