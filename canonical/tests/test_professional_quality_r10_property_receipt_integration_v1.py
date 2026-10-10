from __future__ import annotations

import json
from pathlib import Path
import unittest

from canonical.runtime import professional_quality_r10_execution_guard_v1 as guard
from canonical.runtime import professional_quality_r10_proof_slot_verifier_v1 as slots
from canonical.runtime import professional_quality_r10_property_receipt_gate_v1 as property_gate


ROOT=Path(__file__).resolve().parents[2]
CONSTITUTION=ROOT/"canonical/governance/PROFESSIONAL_QUALITY_R10_DECISION_CONSTITUTION_20261010_V1.json"
PROFILE=ROOT/"canonical/governance/PROFESSIONAL_QUALITY_P1_EXECUTION_PROFILE_20261010_V3.json"
CATALOG=ROOT/"canonical/governance/PROFESSIONAL_QUALITY_DOMAIN_DEFEATER_CATALOG_20261009_V2.json"


def clean_inputs():
    constitution=json.loads(CONSTITUTION.read_text(encoding="utf-8"))
    profile=json.loads(PROFILE.read_text(encoding="utf-8"))
    catalog=json.loads(CATALOG.read_text(encoding="utf-8"))
    decision={
        "schema":"PROJECT_BRAIN_DECISION_SUFFICIENT_GAP_CONTRACT_V1",
        "pass":True,
        "reduction_mode":"LOSSLESS_IDENTITY__NO_UNVERIFIED_OMISSION",
        "omitted_evidence":[],
        "source_contract_sha256":"1"*64,
        "representation_sha256":"2"*64,
    }
    minimum={
        "schema":"PROJECT_BRAIN_MINIMUM_POLICY_CHANGING_INFORMATION_CONTRACT_V1",
        "requests":[],
    }
    context={
        "target":{
            "target_spec_sha256":"3"*64,
            "hard_constraints_sha256":"4"*64,
            "freeze_receipt_sha256":"5"*64,
        },
        "uncertainty_claims":[
            {"id":"u1","type":"MODEL_UNCERTAINTY","source_type":"MODEL_UNCERTAINTY"}
        ],
        "decision_policy":{
            "aggregation_mode":"PARETO_ONLY",
            "risk_threshold_required":False,
            "precommit_receipt_sha256":"6"*64,
        },
        "veto_constraints":[
            {"id":"hard-no-fabrication","noncompensatory":True,"satisfied":True}
        ],
        "analysis_models":[
            {"id":"m1","decision":"candidate-a"},
            {"id":"m2","decision":"candidate-a"},
        ],
        "evidence_packet":{
            "declared_evidence_ids":["e1","e2"],
            "included_evidence_ids":["e1","e2"],
            "omissions":[],
            "packet_sha256":"7"*64,
            "declared_basis_sha256":"8"*64,
        },
        "stopping_rule":{
            "rule_sha256":"9"*64,
            "precommit_receipt_sha256":"a"*64,
            "frozen_before_outcome_reveal":True,
        },
        "quality_claim":{"claim_level":"RELATIVE_OR_SCOPED"},
    }
    return constitution,profile,catalog,decision,minimum,context


class R10PropertyReceiptIntegrationV1Tests(unittest.TestCase):
    def test_structural_and_guard_pass_do_not_self_certify_property_truth(self):
        constitution,profile,catalog,decision,minimum,context=clean_inputs()
        structural=slots.evaluate(
            claim_id=slots.CLAIM_ID,
            constitution=constitution,
            decision_contract=decision,
            minimum_information_contract=minimum,
            case_context=context,
        )
        self.assertTrue(structural["pass"],structural)
        self.assertFalse(structural["underlying_fact_truth_authority"])
        self.assertFalse(structural["whole_leaf_property_truth_proved"])

        guarded=guard.evaluate(
            claim_id=guard.CLAIM_ID,
            decision_contract=decision,
            minimum_information_contract=minimum,
            execution_profile=profile,
            defeater_catalog=catalog,
            constitution=constitution,
            case_context=context,
        )
        self.assertTrue(guarded["pass"],guarded)
        self.assertFalse(guarded["whole_leaf_property_truth_proved"])

        property_out=property_gate.evaluate(
            repo_root=ROOT,
            claim_id=property_gate.CLAIM_ID,
            structural_verdict=structural,
            property_slots={},
            detection_completeness_slot=None,
        )
        self.assertFalse(property_out["pass"])
        self.assertEqual(
            set(property_out["missing_property_receipt_slots"]),
            set(property_gate.REQUIRED_SLOTS),
        )
        self.assertFalse(property_out["detection_completeness_proved"])
        self.assertFalse(property_out["whole_leaf_property_truth_proved"])

        blocked=guard.evaluate(
            claim_id=guard.CLAIM_ID,
            decision_contract=decision,
            minimum_information_contract=minimum,
            execution_profile=profile,
            defeater_catalog=catalog,
            detected_defeater_ids=["C48_ANALYSIS_CHERRY_PICK"],
            constitution=constitution,
            case_context=context,
        )
        self.assertFalse(blocked["pass"])
        self.assertEqual(
            blocked["status"],
            "ABSTAIN_OR_ESCALATE__KNOWN_R10_DEFEATER_ACTIVE",
        )


if __name__=="__main__":
    unittest.main(verbosity=2)
