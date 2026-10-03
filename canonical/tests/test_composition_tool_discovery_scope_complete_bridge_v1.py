from __future__ import annotations
import hashlib, json, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CAND = "canonical/governance/COMPOSITION_TOOL_DISCOVERY_SCOPE_COMPLETE_BRIDGE_V1.json"
EXPECTED = {
    "canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json": "62394e5b7d221ec9f69c3458f669e40e253a9d09",
    "canonical/governance/FROZEN_COMPOSITION_COMPONENT_INTERFACE_MANIFEST_V1.json": "9efbf3e81e67fbd15e34be2fcd86fbfc626b246d",
    "canonical/verification/TOOL_DISCOVERY_UNIVERSAL_SCOPE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json": "f44e2378cf00f86a59159cb9d8edb35f0a7c27f4",
    "canonical/verification/TOOL_DISCOVERY_ACCEPTANCE_REDUCTION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json": "913d171b3c855000d322e183b142b3200eeaf0a9",
    "canonical/verification/TOOL_DISCOVERY_ACCEPTANCE_PROMOTION_INTEGRATOR_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json": "bed23f2e69d4bc8937d792b07b5812364cf26a85",
    "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json": "4000854d577f7ab5f0146d21d16e91d017458431",
}

def load(path):
    return json.loads((ROOT/path).read_text(encoding="utf-8"))

def blob(path):
    b=(ROOT/path).read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

class CompositionToolDiscoveryScopeBridgeV1Tests(unittest.TestCase):
    def test_all_bound_source_bytes_are_exact(self):
        self.assertEqual({p: blob(p) for p in EXPECTED}, EXPECTED)

    def test_frozen_manifest_has_exactly_one_tool_discovery_component(self):
        m=load("canonical/governance/FROZEN_COMPOSITION_COMPONENT_INTERFACE_MANIFEST_V1.json")
        rows=[x for x in m["interfaces"] if x.get("component_id")=="tool discovery"]
        self.assertEqual(len(rows),1,rows)
        self.assertEqual(rows[0]["interface_id"],"coding+debugging+tool discovery")
        self.assertEqual(rows[0]["required_properties"],["SCOPED_ACCEPTANCE_PROOF"])

    def test_source_protocol_semantically_covers_tool_discovery_component(self):
        p=load("canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json")
        src=next(x for x in p["protocols"] if x["family"]=="TOOL_DISCOVERY_SELECTION_AND_LEARNING")
        self.assertIn("unknown tool discovery",src["task_dimensions"])
        dst=next(x for x in p["protocols"] if x["family"]=="MULTI_CAPABILITY_COMPOSITION")
        self.assertIn("coding+debugging+tool discovery",dst["task_dimensions"])

    def test_tool_discovery_scope_and_acceptance_are_current_independent_facts(self):
        s=load("canonical/verification/TOOL_DISCOVERY_UNIVERSAL_SCOPE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json")
        self.assertTrue(s["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"))
        self.assertTrue(s["verified"]["universal_scope_proved"])
        self.assertEqual(s["verified"]["basis_kind"],"UNIVERSAL_FORMAL_SCOPE_PROOF")
        self.assertEqual(s["verified"]["target_predicate"],"TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR")
        a=load("canonical/verification/TOOL_DISCOVERY_ACCEPTANCE_REDUCTION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json")
        self.assertTrue(a["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"))
        self.assertTrue(a["verified"]["reduction_pass"])
        self.assertTrue(a["verified"]["scope_complete"])
        self.assertTrue(a["verified"]["objective_ceiling"])
        self.assertEqual(a["verified"]["target_predicate"],"TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR")
        p=load("canonical/verification/TOOL_DISCOVERY_ACCEPTANCE_PROMOTION_INTEGRATOR_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json")
        self.assertTrue(p["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"))
        self.assertEqual(p["verified_result"]["newly_closed_families"],["TOOL_DISCOVERY_SELECTION_AND_LEARNING"])
        self.assertEqual(p["verified_result"]["newly_proved_predicates"],["TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR"])

    def test_current_ledger_preserves_scope_complete_tool_discovery_predicate(self):
        e=load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json")
        row=next(x for x in e["claims"] if x.get("predicate_id")=="TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR")
        self.assertEqual(row["state"],"PROVED")
        self.assertTrue(row["scope_complete"])
        self.assertTrue(row["objective_ceiling"])
        self.assertEqual(row["proof_kind"],"ABSOLUTE_CEILING_WITH_UNIVERSAL_FORMAL_SCOPE_COMPLETENESS")
        self.assertTrue(row["scope_completeness"]["formal_completeness"])
        self.assertTrue(row["scope_completeness"]["all_admissible_target_inputs_proved"])

    def test_candidate_is_new_one_component_receipt_and_cannot_self_promote(self):
        c=load(CAND)
        r=c["candidate_receipt"]
        self.assertEqual(r["receipt_id"],"COMPOSITION_SCOPE_COMPLETE_BRIDGE::TOOL_DISCOVERY_SELECTION_AND_LEARNING::tool_discovery::V1")
        self.assertNotEqual(r["receipt_id"],c["quarantine_relation"]["historical_quarantined_receipt"])
        self.assertFalse(c["quarantine_relation"]["historical_receipt_restored"])
        self.assertEqual(r["component_id"],"tool discovery")
        self.assertEqual(r["interface_id"],"coding+debugging+tool discovery")
        self.assertEqual(r["proved_properties"],["SCOPED_ACCEPTANCE_PROOF"])
        self.assertFalse(r["verified"])
        self.assertFalse(r["independent"])
        self.assertTrue(r["contamination_clean"])
        self.assertTrue(r["acceptance_scoped"])
        self.assertFalse(c["execution_authority"])
        self.assertFalse(c["promotion_authority"])
        excluded=set(c["scope_guard"]["excluded_scope"])
        self.assertTrue({"CODING_COMPONENT","GENERAL_DEBUGGING_COMPONENT","GENERAL_MULTI_CAPABILITY_COMPOSITION_INTERACTION_SUCCESS"}.issubset(excluded))

if __name__=="__main__":
    unittest.main(verbosity=2)
