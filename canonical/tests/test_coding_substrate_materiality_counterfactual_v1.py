import unittest
from canonical.runtime.coding_substrate_materiality_counterfactual_v1 import (
    FINISH,bare_terminal_decision,configured_terminal_decision,evaluate_counterfactual
)

class Tests(unittest.TestCase):
    def test_counterfactual_passes(self):
        out=evaluate_counterfactual()
        self.assertTrue(out["pass"],out)
        self.assertTrue(out["configuration_material_control_proven"])
        self.assertFalse(out["benchmark_case_content_consumed"])

    def test_bare_accepts_premature_finish(self):
        self.assertTrue(bare_terminal_decision(FINISH)["accepted"])

    def test_configured_blocks_known_failure(self):
        sid="s"
        auth={
          "schema":"BRAIN_SESSION_TERMINAL_AUTHORIZATION_V1",
          "session_id":sid,
          "submission_authorized":True,
          "known_relevant_failures":["x"],
          "acceptance_criteria":[{"criterion":"tests","status":"PASS","evidence":"e"}],
          "verification_commands":[{"command":"pytest","exit_code":0}],
        }
        out=configured_terminal_decision(FINISH,auth,session_id=sid)
        self.assertFalse(out["accepted"])
        self.assertIn("KNOWN_RELEVANT_FAILURES_REMAIN",out["errors"])

    def test_configured_blocks_failed_verification(self):
        sid="s"
        auth={
          "schema":"BRAIN_SESSION_TERMINAL_AUTHORIZATION_V1",
          "session_id":sid,
          "submission_authorized":True,
          "known_relevant_failures":[],
          "acceptance_criteria":[{"criterion":"tests","status":"PASS","evidence":"e"}],
          "verification_commands":[{"command":"pytest","exit_code":1}],
        }
        out=configured_terminal_decision(FINISH,auth,session_id=sid)
        self.assertFalse(out["accepted"])
        self.assertIn("VERIFICATION_COMMANDS_NOT_ALL_PASS",out["errors"])

    def test_configured_accepts_after_all_evidence_passes(self):
        sid="s"
        auth={
          "schema":"BRAIN_SESSION_TERMINAL_AUTHORIZATION_V1",
          "session_id":sid,
          "submission_authorized":True,
          "known_relevant_failures":[],
          "acceptance_criteria":[{"criterion":"tests","status":"PASS","evidence":"e"}],
          "verification_commands":[{"command":"pytest","exit_code":0}],
        }
        self.assertTrue(configured_terminal_decision(FINISH,auth,session_id=sid)["accepted"])

if __name__=="__main__": unittest.main()
