import unittest
from canonical.runtime import professional_quality_p1_router_v2 as r

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

class T(unittest.TestCase):
    def test_empty_abstains(self):
        out=r.route({})
        self.assertEqual(out["status"],"ABSTAIN__P1_INCOMPLETE")
        self.assertEqual(out["blocking_steps"],STEPS)

    def test_clean_routes_p1(self):
        out=r.route({"step_results":done()})
        self.assertEqual(out["route"],"P1")
        self.assertFalse(out["terminal_authority"])

    def test_known_trigger_escalates(self):
        out=r.route({"step_results":done(),"detected_triggers":["UNSUPPORTED_OR_LOSSY_OBSERVATION_CHANNEL"]})
        self.assertEqual(out["route"],"ESCALATE")

    def test_unknown_trigger_fails_closed(self):
        out=r.route({"step_results":done(),"detected_triggers":["UNKNOWN_X"]})
        self.assertEqual(out["status"],"FAIL_CLOSED")

    def test_new_root_candidate_has_no_authority(self):
        out=r.route({"step_results":done(),"unmapped_material_false_certification_path":True,"unmapped_path_representation":"UNREPRESENTABLE"})
        self.assertEqual(out["route"],"ARCHITECTURE_REVIEW")
        self.assertTrue(out["new_root_candidate"])
        self.assertFalse(out["new_root_authority"])
