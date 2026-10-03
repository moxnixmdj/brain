from __future__ import annotations
import hashlib, json, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CAND = "canonical/governance/COMPOSITION_RECOVERY_SCOPE_COMPLETE_BRIDGE_V1.json"
EXPECTED = {
    "canonical/capabilities/opus55/OPUS_5_5_USEFUL_CAPABILITY_ENVELOPE_V1.json": "661a57f839101fbf54c7e4edc76166c65ce9327d",
    "canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json": "62394e5b7d221ec9f69c3458f669e40e253a9d09",
    "canonical/governance/FROZEN_COMPOSITION_COMPONENT_INTERFACE_MANIFEST_V1.json": "9efbf3e81e67fbd15e34be2fcd86fbfc626b246d",
    "canonical/verification/RECOVERY_OPUS55_ZERO_REALITY_PUBLIC_RUNNER_VERIFICATION_20261003_V2.json": "981c8ac9b66ee7fccf5b531525849e29df9be483",
    "canonical/verification/RECOVERY_ACCEPTANCE_INTEGRATOR_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json": "48a865f38f65be212df1cf0ba52d296b71cd003a",
    "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json": "0ed075c1efa053fe6e4eb3519d9903cf63fcf163",
}
RECOVERY_PREDS = {
    "RECOVERY_CAUSAL_LOCALIZATION_NONINFERIOR",
    "RECOVERY_TERMINAL_NONINFERIOR",
    "RECOVERY_ZERO_CRITICAL_FAIL_CLOSED_MISSES",
}

def load(path):
    return json.loads((ROOT/path).read_text(encoding="utf-8"))

def blob(path):
    b=(ROOT/path).read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

class CompositionRecoveryScopeBridgeV1Tests(unittest.TestCase):
    def test_all_bound_source_bytes_are_exact(self):
        self.assertEqual({p: blob(p) for p in EXPECTED}, EXPECTED)

    def test_frozen_manifest_has_exactly_one_recovery_component(self):
        m=load("canonical/governance/FROZEN_COMPOSITION_COMPONENT_INTERFACE_MANIFEST_V1.json")
        rows=[x for x in m["interfaces"] if x.get("component_id")=="recovery"]
        self.assertEqual(len(rows),1,rows)
        self.assertEqual(rows[0]["interface_id"],"browser/computer action+memory+recovery")
        self.assertEqual(rows[0]["required_properties"],["SCOPED_ACCEPTANCE_PROOF"])

    def test_source_protocol_semantically_covers_recovery_component(self):
        p=load("canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json")
        src=next(x for x in p["protocols"] if x["family"]=="SELF_VERIFICATION_DEBUGGING_AND_RECOVERY")
        self.assertIn("recovery after injected failure",src["task_dimensions"])
        self.assertIn("terminal_recovery_rate",src["primary_metrics"])
        dst=next(x for x in p["protocols"] if x["family"]=="MULTI_CAPABILITY_COMPOSITION")
        self.assertIn("browser/computer action+memory+recovery",dst["task_dimensions"])

    def test_recovery_scope_and_acceptance_are_current_independent_facts(self):
        s=load("canonical/verification/RECOVERY_OPUS55_ZERO_REALITY_PUBLIC_RUNNER_VERIFICATION_20261003_V2.json")
        self.assertTrue(s["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"))
        self.assertTrue(s["verified"]["scope_complete"])
        self.assertTrue(s["verified"]["objective_ceiling_or_floor"])
        self.assertEqual(set(s["verified"]["predicates"]),RECOVERY_PREDS)
        a=load("canonical/verification/RECOVERY_ACCEPTANCE_INTEGRATOR_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json")
        self.assertTrue(a["status"].startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"))
        self.assertEqual(a["verified_result"]["newly_closed_families"],["SELF_VERIFICATION_DEBUGGING_AND_RECOVERY"])
        self.assertEqual(set(a["verified_result"]["newly_proved_predicates"]),RECOVERY_PREDS)
        self.assertTrue(a["verified_result"]["recovery_only_delta"])

    def test_current_ledger_preserves_all_three_scope_complete_recovery_predicates(self):
        e=load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json")
        rows={x["predicate_id"]:x for x in e["claims"] if x.get("predicate_id") in RECOVERY_PREDS}
        self.assertEqual(set(rows),RECOVERY_PREDS)
        for row in rows.values():
            self.assertEqual(row["state"],"PROVED")
            self.assertTrue(row["scope_complete"])
            self.assertEqual(row["source_path"],"canonical/verification/RECOVERY_OPUS55_ZERO_REALITY_PUBLIC_RUNNER_VERIFICATION_20261003_V2.json")

    def test_candidate_is_one_component_only_and_cannot_self_promote(self):
        c=load(CAND)
        r=c["candidate_receipt"]
        self.assertEqual(r["component_id"],"recovery")
        self.assertEqual(r["interface_id"],"browser/computer action+memory+recovery")
        self.assertEqual(r["proved_properties"],["SCOPED_ACCEPTANCE_PROOF"])
        self.assertFalse(r["verified"])
        self.assertFalse(r["independent"])
        self.assertTrue(r["contamination_clean"])
        self.assertTrue(r["acceptance_scoped"])
        self.assertFalse(c["execution_authority"])
        self.assertFalse(c["promotion_authority"])
        excluded=set(c["scope_guard"]["excluded_scope"])
        self.assertTrue({"BROWSER_COMPUTER_ACTION_COMPONENT","MEMORY_COMPONENT","GENERAL_DEBUGGING_COMPONENT","GENERAL_MULTI_CAPABILITY_COMPOSITION_INTERACTION_SUCCESS"}.issubset(excluded))

if __name__=="__main__":
    unittest.main(verbosity=2)
