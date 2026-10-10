from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest

from canonical.runtime import one_shot_reality_closure_v2 as one_shot
from canonical.runtime import professional_quality_r10_proof_slot_verifier_v1 as slots

ROOT = Path(__file__).resolve().parents[2]
CONSTITUTION = ROOT / "canonical/governance/PROFESSIONAL_QUALITY_R10_DECISION_CONSTITUTION_20261010_V1.json"


def closure():
    return {
        "schema": "PROJECT_BRAIN_ONE_SHOT_VERIFIED_CLOSURE_V1",
        "status": "OPEN",
        "pass": False,
        "fixed_point": True,
        "closure_class": "R10_PROOF_SLOT_TEST",
        "initial_frontier_digest": "i",
        "final_frontier_digest": "f",
        "final_state_sha256": "a" * 64,
        "irreducible_external_information_proved": False,
        "residual": {
            "internal_blockers": [],
            "evidence_blockers": ["MISSING_FACT"],
            "irreducible_external_information_proved": False,
        },
    }


def clean_context():
    return {
        "target": {
            "target_spec_sha256": "1" * 64,
            "hard_constraints_sha256": "2" * 64,
            "freeze_receipt_sha256": "3" * 64,
        },
        "uncertainty_claims": [
            {
                "id": "u1",
                "type": "MODEL_UNCERTAINTY",
                "source_type": "MODEL_UNCERTAINTY",
            }
        ],
        "decision_policy": {
            "aggregation_mode": "PARETO_ONLY",
            "risk_threshold_required": False,
            "precommit_receipt_sha256": "4" * 64,
        },
        "veto_constraints": [
            {
                "id": "hard-no-fabrication",
                "noncompensatory": True,
                "satisfied": True,
            }
        ],
        "analysis_models": [
            {"id": "m1", "decision": "candidate-a"},
            {"id": "m2", "decision": "candidate-a"},
        ],
        "evidence_packet": {
            "declared_evidence_ids": ["e1", "e2"],
            "included_evidence_ids": ["e1", "e2"],
            "omissions": [],
            "packet_sha256": "5" * 64,
            "declared_basis_sha256": "6" * 64,
        },
        "stopping_rule": {
            "rule_sha256": "7" * 64,
            "precommit_receipt_sha256": "8" * 64,
            "frozen_before_outcome_reveal": True,
        },
        "quality_claim": {
            "claim_level": "RELATIVE_OR_SCOPED",
        },
    }


class R10ProofSlotVerifierV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.constitution = json.loads(CONSTITUTION.read_text())

    def contracts(self):
        gap = one_shot.compile_gap_contract(closure())
        decision = one_shot.compile_decision_sufficient_contract(gap)
        minimum = one_shot.compile_minimum_information_contract(gap, decision)
        return decision, minimum

    def evaluate(self, context=None, constitution=None):
        decision, minimum = self.contracts()
        return slots.evaluate(
            claim_id=slots.CLAIM_ID,
            constitution=constitution or self.constitution,
            decision_contract=decision,
            minimum_information_contract=minimum,
            case_context=context or clean_context(),
        )

    def test_clean_conservative_case_satisfies_all_nine_structural_slots(self):
        out = self.evaluate()
        self.assertTrue(out["pass"], out)
        self.assertEqual(set(out["slot_results"]), set(slots.REQUIRED_SLOTS))
        self.assertTrue(all(out["slot_results"].values()))
        self.assertFalse(out["underlying_fact_truth_authority"])
        self.assertFalse(out["whole_leaf_property_truth_proved"])

    def test_custom_aggregation_without_authority_is_open(self):
        c = clean_context()
        c["decision_policy"]["aggregation_mode"] = "WEIGHTED_SUM"
        out = self.evaluate(c)
        self.assertIn("aggregation_and_risk_policy_precommitted", out["missing_slots"])

    def test_custom_aggregation_with_authority_receipt_is_structurally_admissible(self):
        c = clean_context()
        c["decision_policy"]["aggregation_mode"] = "AUTHORIZED_WEIGHTED_SUM"
        c["decision_policy"]["aggregation_authority_receipt_sha256"] = "9" * 64
        out = self.evaluate(c)
        self.assertTrue(out["pass"], out)

    def test_required_risk_threshold_without_authority_is_open(self):
        c = clean_context()
        c["decision_policy"]["risk_threshold_required"] = True
        out = self.evaluate(c)
        self.assertIn("aggregation_and_risk_policy_precommitted", out["missing_slots"])

    def test_uncertainty_cross_type_laundering_requires_adapter(self):
        c = clean_context()
        c["uncertainty_claims"][0]["source_type"] = "POSTERIOR_PROBABILITY"
        out = self.evaluate(c)
        self.assertIn("uncertainty_semantics_typed", out["missing_slots"])

    def test_compensatory_or_failed_veto_is_open(self):
        for field, value in (("noncompensatory", False), ("satisfied", False)):
            with self.subTest(field=field):
                c = clean_context()
                c["veto_constraints"][0][field] = value
                out = self.evaluate(c)
                self.assertIn("veto_constraints_preserved", out["missing_slots"])

    def test_decision_sensitive_model_multiplicity_requires_escalation(self):
        c = clean_context()
        c["analysis_models"][1]["decision"] = "candidate-b"
        out = self.evaluate(c)
        self.assertIn(
            "model_or_analysis_multiplicity_resolved_or_escalated",
            out["missing_slots"],
        )
        c["multiplicity_escalation_receipt_sha256"] = "a" * 64
        out2 = self.evaluate(c)
        self.assertTrue(out2["pass"], out2)

    def test_selective_evidence_packet_requires_certified_omission(self):
        c = clean_context()
        c["evidence_packet"]["included_evidence_ids"] = ["e1"]
        out = self.evaluate(c)
        self.assertIn("evidence_packet_complete", out["missing_slots"])
        c["evidence_packet"]["omissions"] = [
            {"evidence_id": "e2", "omission_certificate_sha256": "b" * 64}
        ]
        out2 = self.evaluate(c)
        self.assertTrue(out2["pass"], out2)

    def test_post_outcome_stopping_rule_is_open(self):
        c = clean_context()
        c["stopping_rule"]["frozen_before_outcome_reveal"] = False
        out = self.evaluate(c)
        self.assertIn("stopping_rule_precommitted", out["missing_slots"])

    def test_absolute_excellence_needs_absolute_floor_evidence(self):
        c = clean_context()
        c["quality_claim"]["claim_level"] = "ABSOLUTE_PROFESSIONAL_EXCELLENCE"
        out = self.evaluate(c)
        self.assertIn(
            "absolute_floor_not_inferred_from_weak_baseline",
            out["missing_slots"],
        )
        c["quality_claim"]["absolute_floor_definition_sha256"] = "c" * 64
        c["quality_claim"]["absolute_floor_evidence_sha256"] = "d" * 64
        out2 = self.evaluate(c)
        self.assertTrue(out2["pass"], out2)

    def test_target_freeze_receipt_required(self):
        c = clean_context()
        c["target"]["freeze_receipt_sha256"] = None
        out = self.evaluate(c)
        self.assertIn("target_and_hard_constraints_frozen", out["missing_slots"])

    def test_constitution_cannot_invent_user_utility(self):
        cst = deepcopy(self.constitution)
        cst["authority_boundary"]["policy_file_can_invent_user_utility"] = True
        out = self.evaluate(constitution=cst)
        self.assertEqual(
            out["reason"],
            "CONSTITUTION_AUTHORITY_OVERCLAIM:policy_file_can_invent_user_utility",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
