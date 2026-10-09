import json
import tempfile
import unittest
from pathlib import Path

import canonical.runtime.p3_robust_policy_adequacy_cegar_v1 as v1
import canonical.runtime.p3_robust_policy_adequacy_cegar_v2 as v2
import canonical.runtime.p3_bound_relevance_cegar_loop_v1 as loop


class P3RobustPolicyAdequacyCegarV2Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "canonical/governance").mkdir(parents=True)
        (self.root / "canonical/verification").mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def _binding(self, policy_id, condition):
        gov = self.root / "canonical/governance" / f"{policy_id}.json"
        ver = self.root / "canonical/verification" / f"{policy_id}.json"
        gov.write_text(
            json.dumps({
                "schema": v1.ADEQUACY_SCHEMA,
                "policy_id": policy_id,
                "policy_condition_sha256": v1._condition_sha256(condition),
                "adequacy_proved": True,
                "brain_owned": True,
                "load_bearing_constraints_preserved": True,
            }, sort_keys=True),
            encoding="utf-8",
        )
        gov_blob = v1._git_blob_sha(gov)
        ver.write_text(
            json.dumps({
                "schema": v1.VERIFY_SCHEMA,
                "policy_id": policy_id,
                "subject_git_blob_sha": gov_blob,
                "pass": True,
            }, sort_keys=True),
            encoding="utf-8",
        )
        return {
            "adequacy_certificate_path": f"canonical/governance/{policy_id}.json",
            "adequacy_certificate_blob_sha": gov_blob,
            "independent_verification_path": f"canonical/verification/{policy_id}.json",
            "independent_verification_blob_sha": v1._git_blob_sha(ver),
        }

    def test_v2_preserves_common_policy_solver_semantics(self):
        x = {"op": "ATOM", "id": "x"}
        problem = {
            "decision_basis": ["x"],
            "formal_source_constraints": [x],
            "proposed_refinements": [x],
            "policy_conditions": {"p": x},
            "policy_adequacy_bindings": {"p": self._binding("p", x)},
        }
        out = v2.run(problem, root=self.root)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["status"], "COMMON_POLICY_CERTIFIED_ACROSS_ALL_SURVIVING_MODELS")
        self.assertEqual(out["selected_policy_id"], "p")
        self.assertEqual(out["conditioned_registry_successor"], "V2")
        self.assertFalse(out["terminal_authority"])

    def test_bound_relevance_loop_imports_v2_solver(self):
        self.assertEqual(
            loop.solve_cegar.__module__,
            "canonical.runtime.p3_robust_policy_adequacy_cegar_v2",
        )


if __name__ == "__main__":
    unittest.main()
