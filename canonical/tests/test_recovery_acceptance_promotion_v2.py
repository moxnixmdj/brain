from __future__ import annotations
import hashlib, json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]

def load(p):
    return json.loads((ROOT/p).read_text(encoding="utf-8"))

def blob_sha(p):
    b=(ROOT/p).read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

class RecoveryAcceptancePromotionV2Tests(unittest.TestCase):
    def test_hardened_v2_receipt_and_atomic_ledger(self):
        receipt_path="canonical/verification/RECOVERY_OPUS55_ZERO_REALITY_PUBLIC_RUNNER_VERIFICATION_20261003_V2.json"
        receipt=load(receipt_path)
        self.assertEqual(blob_sha(receipt_path),"981c8ac9b66ee7fccf5b531525849e29df9be483")
        self.assertTrue(receipt["verified"]["scope_complete"])
        self.assertFalse(receipt["verified"]["historical_relation_observed_bound_used_as_proof"])
        self.assertEqual(receipt["verified"]["proposed_atomic_acceptance_delta"],3)
        ledger=load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json")
        self.assertEqual(ledger["saturation"]["proved_predicate_count"],11)
        self.assertEqual(ledger["saturation"]["unresolved_predicate_count"],27)
        ids={
            "RECOVERY_CAUSAL_LOCALIZATION_NONINFERIOR",
            "RECOVERY_TERMINAL_NONINFERIOR",
            "RECOVERY_ZERO_CRITICAL_FAIL_CLOSED_MISSES",
        }
        rows={x["predicate_id"]:x for x in ledger["claims"] if x.get("predicate_id") in ids}
        self.assertEqual(set(rows),ids)
        for row in rows.values():
            self.assertEqual(row["state"],"PROVED")
            self.assertTrue(row["scope_complete"])
            self.assertEqual(row["source_path"],receipt_path)
            self.assertEqual(row["source_sha"],"981c8ac9b66ee7fccf5b531525849e29df9be483")

    def test_all_current_projections_agree(self):
        auth=load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json")
        self.assertEqual(auth["truth"]["opus55_acceptance"],"4/19_PASS__15/19_OPEN")
        self.assertEqual(auth["atomic_acceptance_frontier"]["proved"],11)
        self.assertEqual(auth["atomic_acceptance_frontier"]["unresolved"],27)
        self.assertFalse(auth["truth"]["achieved"])
        self.assertIn("RECOMPUTE_LIVE_27_PREDICATE",auth["next"])
        self.assertEqual(sum(str(x).startswith("RECOVERY_THREE_ATOMIC_PREDICATES_") for x in auth["residual"]),1)

        manifest=load("canonical/governance/TERMINAL_CLOSURE_MANIFEST_V1.json")
        self.assertEqual(manifest["behavioral_pass_family_count"],19)
        self.assertEqual(manifest["behavioral_quarantined_family_count"],0)
        self.assertEqual(manifest["opus55_acceptance_summary"]["calibrated_family_count"],4)
        self.assertEqual(manifest["opus55_acceptance_summary"]["pending_family_count"],15)
        self.assertEqual(manifest["opus55_acceptance_summary"]["atomic_predicates"],{"proved":11,"unresolved":27,"total":38})
        rec=[x for x in manifest["families"] if x["id"]=="SELF_VERIFICATION_DEBUGGING_AND_RECOVERY"][0]
        self.assertEqual(rec["opus55_acceptance_state"],"PASS")
        self.assertIn("OWNERSHIP_PROMOTION_SEPARATE",rec["ownership_status"])

        matrix=load("canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json")
        self.assertEqual(matrix["postwave_acceptance_summary"]["calibrated_family_count"],4)
        self.assertEqual(matrix["postwave_acceptance_summary"]["verified_owned_family_count"],2)
        recm=[x for x in matrix["rows"] if x["family"]=="SELF_VERIFICATION_DEBUGGING_AND_RECOVERY"][0]
        self.assertIn("PASS_VIA_SCOPE_COMPLETE_STRONGER_PROOF",recm["postwave_opus55_acceptance_status"])
        self.assertTrue(str(recm["postwave_ownership_credit"]).startswith("ZERO_DIRECT_CREDIT"))

        frontier=load("canonical/capabilities/frontier/OPUS_5_5_USEFUL_CAPABILITY_OWNERSHIP_V1.json")
        self.assertEqual(frontier["acceptance_truth"]["accepted_families"],4)
        self.assertEqual(frontier["acceptance_truth"]["proved_atomic_predicates"],11)
        scoreboard=load("canonical/governance/REAL_OUTPUT_SCOREBOARD_V1.json")
        self.assertEqual(scoreboard["canonical_acceptance_truth"]["accepted_families"],4)
        self.assertEqual(scoreboard["canonical_acceptance_truth"]["proved_atomic_predicates"],11)
        hierarchy=load("canonical/governance/ACTIVE_GOAL_HIERARCHY_V1.json")
        self.assertIn("4_OF_19",hierarchy["probe_state"])
        pointer=load("canonical/CANONICAL_POINTER.json")
        self.assertIn("15_OF_19",pointer["current_frontier"]["critical_blocker"])

    def test_no_fresh_reality_or_ownership_overclaim(self):
        receipt=load("canonical/verification/RECOVERY_OPUS55_ZERO_REALITY_PUBLIC_RUNNER_VERIFICATION_20261003_V2.json")
        self.assertEqual(receipt["new_reality_units_consumed"],0)
        self.assertEqual(receipt["terminal_results_replayed"],0)
        matrix=load("canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json")
        self.assertEqual(len(matrix["summary"]["verified_owned_equal_or_better_capabilities"]),2)
        self.assertIn("SELF_VERIFICATION_DEBUGGING_AND_RECOVERY",matrix["summary"]["owned_components_not_full_family"])

if __name__=="__main__":
    unittest.main(verbosity=2)
