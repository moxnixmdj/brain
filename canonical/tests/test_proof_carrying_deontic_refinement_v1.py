import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import canonical.runtime.proof_carrying_deontic_refinement_v1 as bridge
import canonical.runtime.proof_carrying_semantic_refinement_v3 as auth


class ProofCarryingDeonticAdequacyAuthTests(unittest.TestCase):
    def _semantic_stubs(self):
        return (
            patch.object(
                bridge,
                "verify_proof",
                return_value={
                    "status": "PROOF_CHECKED",
                    "proved_constraints": [{"op": "ATOM", "id": "D"}],
                },
            ),
            patch.object(
                bridge,
                "resolve_common_policy",
                return_value={
                    "status": "COMMON_POLICY_CERTIFIED",
                    "certified_common_policies": ["p"],
                },
            ),
        )

    def _call(self, **extra):
        return bridge.resolve_from_source_proof(
            "The operator must archive the record.",
            source_id="s",
            claims=[{"claim_id": "d", "kind": "DEONTIC_RULE"}],
            decision_basis=["D"],
            policy_conditions={"p": {"op": "ATOM", "id": "D"}},
            **extra,
        )

    def test_entailed_deontic_policy_without_adequacy_binding_is_not_certified(self):
        p1, p2 = self._semantic_stubs()
        with p1, p2:
            out = self._call()
        self.assertEqual(
            out["status"],
            "POLICY_CONDITION_ENTAILED__ADEQUACY_UNAUTHENTICATED",
        )
        self.assertEqual(out["entailed_policy_conditions"], ["p"])
        self.assertEqual(out["certified_common_policies"], [])
        self.assertEqual(
            out["rejected_policy_adequacy_bindings"][0]["reason"],
            "ADEQUACY_BINDING_MISSING",
        )

    def test_exact_authenticated_policy_condition_can_be_certified(self):
        condition = {"op": "ATOM", "id": "D"}
        old_root = auth.ROOT
        try:
            with tempfile.TemporaryDirectory() as td:
                root = Path(td)
                auth.ROOT = root
                gov = root / "canonical/governance"
                ver = root / "canonical/verification"
                gov.mkdir(parents=True)
                ver.mkdir(parents=True)

                adequacy_path = gov / "policy_p.json"
                adequacy_path.write_text(
                    json.dumps({
                        "schema": auth.ADEQUACY_SCHEMA,
                        "policy_id": "p",
                        "policy_condition_sha256": auth._condition_sha256(condition),
                        "adequacy_proved": True,
                        "brain_owned": True,
                        "load_bearing_constraints_preserved": True,
                    }, sort_keys=True),
                    encoding="utf-8",
                )
                adequacy_blob = auth._git_blob_sha(adequacy_path)

                verification_path = ver / "policy_p_verify.json"
                verification_path.write_text(
                    json.dumps({
                        "schema": auth.VERIFY_SCHEMA,
                        "policy_id": "p",
                        "subject_git_blob_sha": adequacy_blob,
                        "pass": True,
                    }, sort_keys=True),
                    encoding="utf-8",
                )
                verification_blob = auth._git_blob_sha(verification_path)

                p1, p2 = self._semantic_stubs()
                with p1, p2:
                    out = self._call(
                        policy_adequacy_bindings={
                            "p": {
                                "adequacy_certificate_path": "canonical/governance/policy_p.json",
                                "adequacy_certificate_blob_sha": adequacy_blob,
                                "independent_verification_path": "canonical/verification/policy_p_verify.json",
                                "independent_verification_blob_sha": verification_blob,
                            }
                        }
                    )
                self.assertEqual(out["status"], "COMMON_POLICY_CERTIFIED")
                self.assertEqual(out["certified_common_policies"], ["p"])
                self.assertEqual(len(out["authenticated_policy_adequacy"]), 1)
        finally:
            auth.ROOT = old_root

    def test_forged_independent_verification_subject_cannot_certify(self):
        condition = {"op": "ATOM", "id": "D"}
        old_root = auth.ROOT
        try:
            with tempfile.TemporaryDirectory() as td:
                root = Path(td)
                auth.ROOT = root
                gov = root / "canonical/governance"
                ver = root / "canonical/verification"
                gov.mkdir(parents=True)
                ver.mkdir(parents=True)

                adequacy_path = gov / "policy_p.json"
                adequacy_path.write_text(
                    json.dumps({
                        "schema": auth.ADEQUACY_SCHEMA,
                        "policy_id": "p",
                        "policy_condition_sha256": auth._condition_sha256(condition),
                        "adequacy_proved": True,
                        "brain_owned": True,
                        "load_bearing_constraints_preserved": True,
                    }, sort_keys=True),
                    encoding="utf-8",
                )
                adequacy_blob = auth._git_blob_sha(adequacy_path)

                verification_path = ver / "policy_p_verify.json"
                verification_path.write_text(
                    json.dumps({
                        "schema": auth.VERIFY_SCHEMA,
                        "policy_id": "p",
                        "subject_git_blob_sha": "0" * 40,
                        "pass": True,
                    }, sort_keys=True),
                    encoding="utf-8",
                )
                verification_blob = auth._git_blob_sha(verification_path)

                p1, p2 = self._semantic_stubs()
                with p1, p2:
                    out = self._call(
                        policy_adequacy_bindings={
                            "p": {
                                "adequacy_certificate_path": "canonical/governance/policy_p.json",
                                "adequacy_certificate_blob_sha": adequacy_blob,
                                "independent_verification_path": "canonical/verification/policy_p_verify.json",
                                "independent_verification_blob_sha": verification_blob,
                            }
                        }
                    )
                self.assertEqual(
                    out["status"],
                    "POLICY_CONDITION_ENTAILED__ADEQUACY_UNAUTHENTICATED",
                )
                self.assertEqual(out["certified_common_policies"], [])
        finally:
            auth.ROOT = old_root

    def test_semantic_kernel_fail_closed_propagates(self):
        with patch.object(
            bridge,
            "verify_proof",
            return_value={
                "status": "PROOF_CHECKED",
                "proved_constraints": [{"op": "ATOM", "id": "D"}],
            },
        ), patch.object(
            bridge,
            "resolve_common_policy",
            return_value={"status": "FAIL_CLOSED", "errors": ["X"]},
        ):
            out = self._call()
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(out["reason"], "SEMANTIC_REFINEMENT_FAIL_CLOSED")


if __name__ == "__main__":
    unittest.main()
