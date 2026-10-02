from __future__ import annotations
import inspect, tempfile, unittest
from pathlib import Path

from canonical.runtime import remaining_behavior_brain_candidate as candidate
from canonical.runtime import remaining_behavior_proof_suites as suite


class RemainingBehaviorBrainCandidateTests(unittest.TestCase):
    def test_candidate_does_not_import_evaluator(self):
        source=inspect.getsource(candidate)
        self.assertNotIn("remaining_behavior_proof_suites",source)
        self.assertNotIn("_oracle",source)
        self.assertNotIn("delegation_contract_proof_suite",source)

    def test_all_six_existing_brain_routes_on_fresh_generated_cases(self):
        for contract in suite.CONTRACTS:
            for difficulty in range(1,6):
                for seed in (31,211,1597):
                    case=suite.generate_case(contract,seed,difficulty)
                    public=suite.public_task(case)
                    with tempfile.TemporaryDirectory() as td:
                        got=candidate.solve(public,workdir=td)
                        artifact_bytes=None
                        if contract=="NATIVE_ARTIFACT_STRUCTURED_EDIT_PRESERVATION_001":
                            artifact_bytes=(Path(got["output_path"])).read_bytes()
                        verdict=suite.score_case(case,got,artifact_bytes=artifact_bytes)
                    self.assertTrue(verdict["pass"],(contract,difficulty,seed,verdict,got))


if __name__=="__main__":
    unittest.main()
