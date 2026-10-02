import json
import unittest
from pathlib import Path

from canonical.runtime.terminal_direct_proof_scope_instance_validator import validate


class TerminalDirectProofScopeInstanceValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest=json.loads(Path(
            "canonical/governance/TERMINAL_DIRECT_PROOF_SCOPE_INSTANCES_V1.json"
        ).read_text())

    def test_frozen_manifest_passes(self):
        out=validate(self.manifest)
        self.assertEqual(out["status"],"PASS",out)
        self.assertEqual(len(out["routes"]),4)
        self.assertTrue(all(x["oracle_candidate_pass"] for x in out["routes"]))

    def test_deleted_score_equivalence_guard_is_required(self):
        bad=json.loads(json.dumps(self.manifest))
        bad["anti_weakening"].remove(
            "SCOPE_INSTANCE_PASS_DOES_NOT_CLAIM_REPRODUCTION_OF_A_DELETED_PRIVATE_BENCHMARK_SCORE"
        )
        self.assertEqual(validate(bad)["status"],"FAIL_CLOSED")

    def test_execution_authority_cannot_be_granted_here(self):
        bad=json.loads(json.dumps(self.manifest))
        bad["prewave_state"]["execution_authority"]=True
        out=validate(bad)
        self.assertEqual(out["status"],"FAIL_CLOSED")
        self.assertIn("SCOPE_MANIFEST_WRONGLY_GRANTS_EXECUTION_AUTHORITY",out["errors"])

    def test_route_contract_mismatch_fails_closed(self):
        bad=json.loads(json.dumps(self.manifest))
        bad["route_instances"][0]["contract"]="TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001"
        self.assertEqual(validate(bad)["status"],"FAIL_CLOSED")


if __name__=="__main__":
    unittest.main()
