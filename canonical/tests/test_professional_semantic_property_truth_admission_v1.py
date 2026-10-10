from __future__ import annotations

from copy import deepcopy
from hashlib import sha1
import json
from pathlib import Path
import unittest

from canonical.runtime import professional_semantic_property_truth_admission_v1 as gate

ROOT = Path(__file__).resolve().parents[2]


def blob(path: Path) -> str:
    raw = path.read_bytes()
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def pack():
    return json.loads((ROOT / gate.PACK_PATH).read_text(encoding="utf-8"))


def row_for(leaf_id="PQ::R10_ANALYSIS_DECISION::SEMANTIC"):
    return next(x for x in pack()["claims"] if x["leaf_id"] == leaf_id)


def valid_candidate(leaf_id="PQ::R10_ANALYSIS_DECISION::SEMANTIC"):
    row = row_for(leaf_id)
    return {
        "leaf_id": leaf_id,
        "semantic_totality_claim_id": row["frozen_claim"]["claim_id"],
        "leaf_acceptance": row["target_predicate"]["acceptance"],
        "whole_leaf_scope_complete": True,
        "proof_mode": "CLAIM_SCOPED_COVERAGE_ROOTS",
        "acceptance_atom_proofs": {
            "claim_semantics_grounding_totality_proved": True,
            "scope_uncertainty_resolution_totality_proved": True,
            "root_relevant_defeater_totality_proved": True,
            "typed_evidence_totality_proved": True,
        },
        "claim_scoped_root_proofs": {
            "mission_sufficient_carrier_factorization_proved": True,
            "cc_r1_reality_containment_proved": True,
            "cc_r2_mission_soundness_proved": True,
            "cc_r3_terminal_closure_proved": True,
            "r4_proof_closure": True,
        },
        "terminal_disposition": {
            "justified_abstention_reachable": False,
            "abstention_satisfies_exact_target_predicate": False,
            "abstention_inputs_outside_claim_scope_proved": False,
            "positive_issuance_totality_proved": True,
        },
        "nonvacuity": {
            "independently_verified_positive_witness_count": 1,
        },
        "independent_verification_pass": True,
    }


class ProfessionalSemanticPropertyTruthAdmissionV1Tests(unittest.TestCase):
    def test_exact_current_claim_with_universal_positive_proof_passes(self):
        p = pack()
        c = valid_candidate()
        out = gate.evaluate_candidate(
            p, c, current_mission_blob_sha=blob(ROOT / gate.MISSION_PATH)
        )
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["leaf_property_truth_admissible"])
        self.assertFalse(out["safe_abstention_substituted_for_positive_property"])
        self.assertFalse(out["terminal_authority"])

    def test_legacy_r10_whole_leaf_scope_claim_id_is_rejected(self):
        p = pack()
        c = valid_candidate()
        # The unmerged legacy R10 semantic verifier used the whole-leaf scope
        # claim rather than the current semantic-totality property claim.
        c["semantic_totality_claim_id"] = "34a59e3ce3ae28c14a475f913639d9dbf03c65f191cf416034a48db5ffda57f0"
        out = gate.evaluate_candidate(
            p, c, current_mission_blob_sha=blob(ROOT / gate.MISSION_PATH)
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "SEMANTIC_TOTALITY_CLAIM_ID_MISMATCH")

    def test_declared_defeater_handlers_without_defeater_totality_are_insufficient(self):
        p = pack()
        c = valid_candidate()
        c["acceptance_atom_proofs"]["root_relevant_defeater_totality_proved"] = False
        out = gate.evaluate_candidate(
            p, c, current_mission_blob_sha=blob(ROOT / gate.MISSION_PATH)
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "SEMANTIC_ACCEPTANCE_TOTALITY_NOT_PROVED")
        self.assertIn(
            "root_relevant_defeater_totality_proved",
            out["missing_acceptance_atoms"],
        )

    def test_safe_in_scope_abstention_does_not_equal_universal_positive_truth(self):
        p = pack()
        c = valid_candidate()
        c["terminal_disposition"]["justified_abstention_reachable"] = True
        out = gate.evaluate_candidate(
            p, c, current_mission_blob_sha=blob(ROOT / gate.MISSION_PATH)
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["reason"],
            "SAFE_ABSTENTION_DOES_NOT_IMPLY_UNIVERSAL_POSITIVE_PROPERTY",
        )

    def test_one_positive_witness_does_not_replace_positive_totality(self):
        p = pack()
        c = valid_candidate()
        c["terminal_disposition"]["positive_issuance_totality_proved"] = False
        out = gate.evaluate_candidate(
            p, c, current_mission_blob_sha=blob(ROOT / gate.MISSION_PATH)
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "UNIVERSAL_POSITIVE_ISSUANCE_TOTALITY_REQUIRED")

    def test_direct_universal_proof_is_valid_alternative_to_root_factorization(self):
        p = pack()
        c = valid_candidate()
        c["proof_mode"] = "INDEPENDENT_DIRECT_UNIVERSAL_PROOF"
        c.pop("claim_scoped_root_proofs")
        c["direct_universal_proof"] = {
            "all_admissible_inputs_satisfy_exact_target_predicate": True,
            "independently_verified": True,
            "scope_relation": "EXACT",
        }
        out = gate.evaluate_candidate(
            p, c, current_mission_blob_sha=blob(ROOT / gate.MISSION_PATH)
        )
        self.assertTrue(out["pass"], out)
        self.assertFalse(out["claim_scoped_root_closure_proved"])
        self.assertTrue(out["direct_universal_proof"])

    def test_mission_pointer_drift_invalidates_pack_for_admission(self):
        p = pack()
        c = valid_candidate()
        out = gate.evaluate_candidate(
            p, c, current_mission_blob_sha="0" * 40
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "SEMANTIC_CLAIM_PACK_MISSION_STALE")

    def test_pack_cannot_precredit_property_truth(self):
        p = pack()
        p["property_truth_claim_count"] = 1
        c = valid_candidate()
        out = gate.evaluate_candidate(
            p, c, current_mission_blob_sha=blob(ROOT / gate.MISSION_PATH)
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "SEMANTIC_CLAIM_PACK_INVALID")


if __name__ == "__main__":
    unittest.main(verbosity=2)
