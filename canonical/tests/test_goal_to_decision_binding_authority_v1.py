from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from canonical.runtime import general_adequate_decision_controller_v1 as legacy
from canonical.runtime import goal_to_decision_binding_authority_v1 as kernel


def write_binding(root: Path, goal: str, payload: dict) -> dict:
    gov = root / "canonical/governance"
    ver = root / "canonical/verification"
    gov.mkdir(parents=True)
    ver.mkdir(parents=True)
    receipt = {
        "schema": kernel.GOAL_BINDING_SCHEMA,
        "goal_sha256": sha256(goal.encode("utf-8")).hexdigest(),
        "decision_payload_sha256": kernel.digest(payload),
        "binding_proved": True,
        "load_bearing_constraints_preserved": True,
        "decision_context_semantically_sufficient": True,
        "producer_id": "producer",
    }
    rp = gov / "binding.json"
    rp.write_text(json.dumps(receipt, sort_keys=True), encoding="utf-8")
    rb = kernel.git_blob_sha(rp)
    verify = {
        "schema": kernel.GOAL_BINDING_VERIFY_SCHEMA,
        "subject_git_blob_sha": rb,
        "goal_sha256": receipt["goal_sha256"],
        "decision_payload_sha256": receipt["decision_payload_sha256"],
        "pass": True,
        "independent_verified": True,
        "semantic_preservation_verified": True,
        "independent_verifier_id": "verifier",
    }
    vp = ver / "binding_verify.json"
    vp.write_text(json.dumps(verify, sort_keys=True), encoding="utf-8")
    return {
        "receipt": {
            "path": "canonical/governance/binding.json",
            "git_blob_sha": rb,
        },
        "verification": {
            "path": "canonical/verification/binding_verify.json",
            "git_blob_sha": kernel.git_blob_sha(vp),
        },
    }


class GoalToDecisionBindingAuthorityV1Tests(unittest.TestCase):
    def assert_equivalent(self, binding, goal, payload, root):
        new = kernel.authenticate_goal_binding(
            binding, goal=goal, decision_payload=payload, repo_root=root
        )
        old = legacy._authenticate_goal_binding(
            binding, goal=goal, decision_payload=payload, repo_root=root
        )
        self.assertEqual(new, old)
        return new

    def test_digest_is_exactly_legacy_digest(self):
        value = {"z": [3, 2, 1], "a": {"x": True}}
        self.assertEqual(kernel.digest(value), legacy._digest(value))

    def test_valid_binding_matches_legacy_exactly(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            goal = "Build the requested artifact."
            payload = {"context_id": "x", "target": {"a": 1}}
            binding = write_binding(root, goal, payload)
            out = self.assert_equivalent(binding, goal, payload, root)
            self.assertTrue(out["pass"])
            self.assertEqual(
                out["status"], "PASS__GOAL_TO_DECISION_CONTEXT_AUTHENTICATED"
            )

    def test_goal_tamper_matches_legacy_fail_closed(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            goal = "Original"
            payload = {"context_id": "x"}
            binding = write_binding(root, goal, payload)
            out = self.assert_equivalent(binding, "Tampered", payload, root)
            self.assertFalse(out["pass"])
            self.assertEqual(
                out["status"], "FAIL_CLOSED__GOAL_TO_DECISION_BINDING_INVALID"
            )

    def test_payload_tamper_matches_legacy_fail_closed(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            goal = "Original"
            payload = {"context_id": "x"}
            binding = write_binding(root, goal, payload)
            out = self.assert_equivalent(
                binding, goal, {"context_id": "changed"}, root
            )
            self.assertFalse(out["pass"])

    def test_verification_blob_drift_matches_legacy_fail_closed(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            goal = "Original"
            payload = {"context_id": "x"}
            binding = write_binding(root, goal, payload)
            binding["verification"]["git_blob_sha"] = "0" * 40
            out = self.assert_equivalent(binding, goal, payload, root)
            self.assertFalse(out["pass"])

    def test_missing_binding_matches_legacy_open_state(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            out = self.assert_equivalent(None, "Original", {"x": 1}, root)
            self.assertEqual(
                out["status"], "OPEN__GOAL_TO_DECISION_BINDING_REQUIRED"
            )

    def test_path_escape_fails_closed(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            binding = {
                "receipt": {"path": "../outside.json", "git_blob_sha": "0" * 40},
                "verification": {
                    "path": "canonical/verification/v.json",
                    "git_blob_sha": "0" * 40,
                },
            }
            out = self.assert_equivalent(binding, "g", {"x": 1}, root)
            self.assertFalse(out["pass"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
