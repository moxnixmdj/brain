import json, unittest
from pathlib import Path

class Tests(unittest.TestCase):
    def test_coding_tb4_frontier_is_consistent(self):
        audit=json.loads(Path("canonical/governance/ACCEPTANCE_PUBLIC_BAR_CAPABILITY_SOURCE_AUDIT_V2.json").read_text())
        ready=json.loads(Path("canonical/governance/OPUS55_PUBLIC_BAR_SCORE_READINESS_MATRIX_V1.json").read_text())
        plan=json.loads(Path("canonical/governance/OPUS55_ACCEPTANCE_RESIDUAL_MINIMUM_PROOF_PLAN_V1.json").read_text())
        adm=json.loads(Path("canonical/governance/CODING_TB4_SOURCE_GATE_V2_ADMISSION_V1.json").read_text())
        receipt=json.loads(Path("canonical/verification/CODING_TB4_SOURCE_GATE_V2_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json").read_text())

        a=next(r for r in audit["routes"] if r["family"]=="ADVANCED_AGENTIC_CODING")
        q=next(r for r in ready["rows"] if r["surface"]=="Terminal-Bench 4.0")

        self.assertTrue(a["clean_case_execution_authority"])
        self.assertEqual(a["model_role"],"GENERAL_COGNITION_SUBSTRATE")
        self.assertTrue(a["general_substrate_test_pass"])
        self.assertFalse(a["external_hidden_target_capability_provider"])
        self.assertTrue(q["score_producing_route_ready"])
        self.assertEqual(plan["current_execution_frontier"]["clean_case_authorized_public_bar_routes"],1)
        self.assertEqual(len(plan["current_execution_frontier"]["authorized_routes"]),1)
        self.assertTrue(receipt["result"]["pass"])
        self.assertTrue(receipt["result"]["clean_case_execution_authority"])
        self.assertEqual(receipt["capability_credit_delta"],0)
        self.assertEqual(receipt["family_credit_delta"],0)
        self.assertEqual(adm["fresh_acceptance_cases_consumed"],0)
        self.assertEqual(audit["fresh_acceptance_cases_consumed"],0)
        self.assertEqual(audit["capability_credit_delta"],0)
        self.assertEqual(audit["family_credit_delta"],0)

if __name__=="__main__": unittest.main()
