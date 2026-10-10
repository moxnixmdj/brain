from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest

from canonical.runtime import one_shot_reality_closure_v2 as one_shot
from canonical.runtime import professional_quality_r10_execution_guard_v1 as guard

ROOT = Path(__file__).resolve().parents[2]
PROFILE_PATH = ROOT / "canonical/governance/PROFESSIONAL_QUALITY_P1_EXECUTION_PROFILE_20261010_V3.json"
CATALOG_PATH = ROOT / "canonical/governance/PROFESSIONAL_QUALITY_DOMAIN_DEFEATER_CATALOG_20261009_V2.json"


def closure(*, evidence=("MISSING_FACT",), internal=()):
    return {
        "schema": "PROJECT_BRAIN_ONE_SHOT_VERIFIED_CLOSURE_V1",
        "status": "OPEN",
        "pass": False,
        "fixed_point": True,
        "closure_class": "R10_PROPERTY_CHALLENGE",
        "initial_frontier_digest": "i",
        "final_frontier_digest": "f",
        "final_state_sha256": "a" * 64,
        "irreducible_external_information_proved": False,
        "residual": {
            "internal_blockers": list(internal),
            "evidence_blockers": list(evidence),
            "irreducible_external_information_proved": False,
        },
    }


def proof_slots():
    return {slot: True for slot in guard.REQUIRED_PROOF_SLOTS}


class R10ExecutionGuardV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile = json.loads(PROFILE_PATH.read_text())
        cls.catalog = json.loads(CATALOG_PATH.read_text())

    def contracts(self):
        gap = one_shot.compile_gap_contract(closure())
        decision = one_shot.compile_decision_sufficient_contract(gap)
        minimum = one_shot.compile_minimum_information_contract(gap, decision)
        self.assertTrue(decision["pass"])
        self.assertEqual(
            decision["reduction_mode"],
            "LOSSLESS_IDENTITY__NO_UNVERIFIED_OMISSION",
        )
        return decision, minimum

    def evaluate(self, **overrides):
        decision, minimum = self.contracts()
        args = {
            "claim_id": guard.CLAIM_ID,
            "decision_contract": decision,
            "minimum_information_contract": minimum,
            "execution_profile": deepcopy(self.profile),
            "defeater_catalog": deepcopy(self.catalog),
            "detected_defeater_ids": (),
            "near_miss_signals": {},
            "proof_slots": proof_slots(),
            "unmapped_material_false_certification_defeater": False,
        }
        args.update(overrides)
        return guard.evaluate(**args)

    def test_positive_clean_path_is_only_certificate_eligible_not_property_truth(self):
        out = self.evaluate()
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["status"],
            "PASS__R10_EXECUTION_GUARD_ELIGIBLE_FOR_SCOPED_CERTIFICATE_VERIFICATION",
        )
        self.assertTrue(out["ordinary_certificate_path_allowed"])
        self.assertFalse(out["detection_completeness_proved"])
        self.assertFalse(out["whole_leaf_property_truth_proved"])
        self.assertFalse(out["quality_authority"])

    def test_all_17_known_r10_defeaters_block_ordinary_certificate_path(self):
        self.assertEqual(len(guard.KNOWN_R10_DEFEATERS), 17)
        for defeater_id in sorted(guard.KNOWN_R10_DEFEATERS):
            with self.subTest(defeater_id=defeater_id):
                out = self.evaluate(detected_defeater_ids=[defeater_id])
                self.assertFalse(out["pass"], out)
                self.assertEqual(
                    out["status"],
                    "ABSTAIN_OR_ESCALATE__KNOWN_R10_DEFEATER_ACTIVE",
                )
                self.assertFalse(out["ordinary_certificate_path_allowed"])

    def test_near_miss_signals_route_to_declared_profile_escalations(self):
        for signal, trigger in guard.NEAR_MISS_TO_TRIGGER.items():
            with self.subTest(signal=signal):
                out = self.evaluate(near_miss_signals={signal: True})
                self.assertFalse(out["pass"], out)
                self.assertEqual(out["status"], "ESCALATE__R10_NEAR_MISS_TRIGGER")
                self.assertIn(trigger, out["active_escalation_triggers"])
                self.assertFalse(out["ordinary_certificate_path_allowed"])

    def test_unknown_detected_defeater_uses_generic_unmapped_material_escalation(self):
        out = self.evaluate(detected_defeater_ids=["C999_FRESH_DECISION_ATTACK"])
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "ESCALATE__UNMAPPED_DETECTED_DEFEATER")
        self.assertEqual(
            out["required_trigger"],
            "UNMAPPED_MATERIAL_FALSE_CERTIFICATION_DEFEATER",
        )

    def test_unmapped_material_signal_escalates_even_without_catalog_id(self):
        out = self.evaluate(unmapped_material_false_certification_defeater=True)
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "ESCALATE__UNMAPPED_MATERIAL_FALSE_CERTIFICATION_DEFEATER",
        )

    def test_missing_proof_slot_keeps_property_open(self):
        slots = proof_slots()
        slots["stopping_rule_precommitted"] = False
        out = self.evaluate(proof_slots=slots)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "OPEN__R10_EXECUTION_PROOF_SLOT_REQUIRED")
        self.assertEqual(out["missing_proof_slots"], ["stopping_rule_precommitted"])

    def test_lossy_decision_contract_fails_closed(self):
        decision, minimum = self.contracts()
        decision = deepcopy(decision)
        decision["reduction_mode"] = "UNVERIFIED_SUMMARY"
        out = guard.evaluate(
            claim_id=guard.CLAIM_ID,
            decision_contract=decision,
            minimum_information_contract=minimum,
            execution_profile=self.profile,
            defeater_catalog=self.catalog,
            proof_slots=proof_slots(),
        )
        self.assertEqual(out["reason"], "DECISION_CONTRACT_NOT_LOSSLESS")

    def test_omitted_decision_evidence_fails_closed(self):
        decision, minimum = self.contracts()
        decision = deepcopy(decision)
        decision["omitted_evidence"] = ["TAIL_RISK"]
        out = guard.evaluate(
            claim_id=guard.CLAIM_ID,
            decision_contract=decision,
            minimum_information_contract=minimum,
            execution_profile=self.profile,
            defeater_catalog=self.catalog,
            proof_slots=proof_slots(),
        )
        self.assertEqual(out["reason"], "DECISION_CONTRACT_OMITS_EVIDENCE")

    def test_broad_acquisition_weakening_fails_closed(self):
        decision, minimum = self.contracts()
        minimum = deepcopy(minimum)
        self.assertTrue(minimum["requests"])
        minimum["requests"][0][
            "broad_acquisition_forbidden_without_minimality_proof"
        ] = False
        out = guard.evaluate(
            claim_id=guard.CLAIM_ID,
            decision_contract=decision,
            minimum_information_contract=minimum,
            execution_profile=self.profile,
            defeater_catalog=self.catalog,
            proof_slots=proof_slots(),
        )
        self.assertEqual(
            out["reason"],
            "MINIMUM_INFORMATION_BROAD_ACQUISITION_NOT_FORBIDDEN",
        )

    def test_profile_trigger_drift_fails_closed(self):
        profile = deepcopy(self.profile)
        profile["escalation_triggers"].remove(
            "UNMAPPED_MATERIAL_FALSE_CERTIFICATION_DEFEATER"
        )
        out = self.evaluate(execution_profile=profile)
        self.assertEqual(out["reason"], "PROFILE_ESCALATION_TRIGGER_MISSING")

    def test_catalog_drift_fails_closed(self):
        catalog = deepcopy(self.catalog)
        rows = catalog.get("challenges")
        self.assertIsInstance(rows, list)
        target = next(
            row
            for row in rows
            if row.get("id") == "C48_ANALYSIS_CHERRY_PICK"
        )
        field = "root_ids" if isinstance(target.get("root_ids"), list) else "target_root_ids"
        target[field] = [x for x in target[field] if x != guard.ROOT_ID]
        out = self.evaluate(defeater_catalog=catalog)
        self.assertEqual(out["reason"], "R10_DEFEATER_CATALOG_DRIFT")

    def test_claim_substitution_fails_closed(self):
        out = self.evaluate(claim_id="0" * 64)
        self.assertEqual(out["reason"], "CLAIM_ID_MISMATCH")


if __name__ == "__main__":
    unittest.main(verbosity=2)
