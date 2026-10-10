from __future__ import annotations
import unittest

from canonical.runtime import professional_quality_p1_router_v1 as router

STEPS=[
"COMPILE_TARGET_SPEC_AND_HARD_CONSTRAINTS",
"GENERATE_DIVERSE_CANDIDATE_BRANCHES_WITH_INCUMBENT_PRESERVATION",
"RUN_DETERMINISTIC_FACT_STRUCTURE_FORMAT_AND_GROUNDING_CHECKS",
"RENDER_EXACT_AUDIENCE_VIEW_AND_BIND_OBSERVATION_CHANNELS",
"RUN_CRITERION_SPECIFIC_PLUS_HOLISTIC_COMPARATIVE_EVALUATION",
"ATTACK_FINALISTS_WITH_RELEVANT_INVARIANCE_DEFEATER_HIDDEN_CHANNEL_AND_COUNTEREXAMPLE_PROBES",
"FREEZE_WINNER_AND_USE_FRESH_OR_SELECTION_AWARE_TERMINAL_EVIDENCE",
"ISSUE_SCOPED_CERTIFICATE_OR_ABSTAIN_WITH_MINIMUM_BLOCKING_CUT",
]

def done():
    return {s:"PASS" for s in STEPS}

class TestProfessionalQualityP1RouterV1(unittest.TestCase):
    def test_clean_ordinary_case_routes_p1_without_authority(self):
        out=router.route({"step_results":done()})
        self.assertEqual(out["route"],"P1")
        self.assertEqual(out["status"],"ROUTE__P1_ORDINARY")
        self.assertFalse(out["terminal_authority"])
        self.assertFalse(out["quality_judgment_authority"])

    def test_known_trigger_escalates_only_existing_roots(self):
        out=router.route({
            "step_results":done(),
            "detected_triggers":["UNSUPPORTED_OR_LOSSY_OBSERVATION_CHANNEL"],
        })
        self.assertEqual(out["route"],"ESCALATE")
        self.assertEqual(
            out["escalation_root_ids"],
            ["R12_META_COMPOSITION_CLOSURE","R3_REALIZATION_OBSERVATION"],
        )
        self.assertFalse(out["new_root_candidate"])
        self.assertFalse(out["terminal_authority"])

    def test_unknown_trigger_fails_closed(self):
        out=router.route({
            "step_results":done(),
            "detected_triggers":["TOTALLY_NEW_MAGIC_TRIGGER"],
        })
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertEqual(out["reason"],"UNKNOWN_ESCALATION_TRIGGER")

    def test_incomplete_p1_abstains(self):
        results=done()
        results[STEPS[4]]="OPEN"
        out=router.route({"step_results":results})
        self.assertEqual(out["status"],"ABSTAIN__P1_INCOMPLETE")
        self.assertEqual(out["blocking_steps"],[STEPS[4]])
        self.assertFalse(out["terminal_authority"])

    def test_failed_p1_step_abstains(self):
        results=done()
        results[STEPS[2]]="FAIL"
        out=router.route({"step_results":results})
        self.assertEqual(out["status"],"ABSTAIN__P1_HARD_FAILURE")
        self.assertEqual(out["blocking_steps"],[STEPS[2]])

    def test_unmapped_path_unknown_representation_abstains(self):
        out=router.route({
            "step_results":done(),
            "unmapped_material_false_certification_path":True,
            "unmapped_path_representation":"UNKNOWN",
        })
        self.assertEqual(
            out["status"],
            "ABSTAIN__UNMAPPED_PATH_REPRESENTATION_UNKNOWN",
        )
        self.assertFalse(out["new_root_authority"])

    def test_unrepresentable_path_only_creates_candidate(self):
        out=router.route({
            "step_results":done(),
            "unmapped_material_false_certification_path":True,
            "unmapped_path_representation":"UNREPRESENTABLE",
        })
        self.assertEqual(out["route"],"ARCHITECTURE_REVIEW")
        self.assertTrue(out["new_root_candidate"])
        self.assertFalse(out["new_root_authority"])
        self.assertFalse(out["terminal_authority"])

    def test_profile_contract_drift_is_not_silently_accepted(self):
        original=router.TRIGGER_ROOTS.copy()
        try:
            router.TRIGGER_ROOTS.pop("NEAR_DECISION_BOUNDARY")
            out=router.route({"step_results":done()})
            self.assertEqual(out["status"],"FAIL_CLOSED")
            self.assertEqual(out["reason"],"PROFILE_ROUTER_CONTRACT_DRIFT")
        finally:
            router.TRIGGER_ROOTS.clear()
            router.TRIGGER_ROOTS.update(original)

if __name__=="__main__":
    unittest.main()
