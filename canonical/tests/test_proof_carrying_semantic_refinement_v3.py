import json
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.certified_scope_fragment_v1 import parse_scope
from canonical.runtime.source_aligned_semantic_proof_v3 import verify_proof
import canonical.runtime.proof_carrying_semantic_refinement_v3 as bridge


class ProofCarryingSemanticRefinementV3AdequacyAuthTests(unittest.TestCase):
    def _scope_claim(self, p):
        return {
            "claim_id": "scope",
            "kind": "SCOPE_RELATION",
            "scope_id": p["scope_id"],
            "relation": p["relation"],
            "operator_id": p["operator_id"],
            "left_role": p["left_role"],
            "left_span": p["left_span"],
            "right_role": p["right_role"],
            "right_span": p["right_span"],
        }

    def _fixture(self):
        text = "Apply the rule unless the exception holds."
        p = parse_scope(text, source="s")["parse"]
        claim = self._scope_claim(p)
        checked = verify_proof(text, source_id="s", claims=[claim])
        atom_id = checked["proved_constraint_ids"][0]
        return text, claim, atom_id

    def test_source_entailment_without_adequacy_auth_cannot_certify_policy(self):
        text, claim, atom_id = self._fixture()
        out = bridge.resolve_from_source_proof(
            text,
            source_id="s",
            claims=[claim],
            decision_basis=[atom_id],
            policy_conditions={"p": {"op": "ATOM", "id": atom_id}},
        )
        self.assertEqual(out["status"], "POLICY_CONDITION_ENTAILED__ADEQUACY_UNAUTHENTICATED")
        self.assertEqual(out["entailed_policy_conditions"], ["p"])
        self.assertEqual(out["certified_common_policies"], [])

    def test_true_condition_exploit_is_blocked(self):
        text, claim, atom_id = self._fixture()
        out = bridge.resolve_from_source_proof(
            text,
            source_id="s",
            claims=[claim],
            decision_basis=[atom_id],
            policy_conditions={"forged": {"op": "TRUE"}},
        )
        self.assertEqual(out["entailed_policy_conditions"], ["forged"])
        self.assertEqual(out["certified_common_policies"], [])
        self.assertEqual(out["status"], "POLICY_CONDITION_ENTAILED__ADEQUACY_UNAUTHENTICATED")

    def test_self_authored_exact_pair_is_not_an_independent_adequacy_root(self):
        text, claim, atom_id = self._fixture()
        condition = {"op": "ATOM", "id": atom_id}
        old_root = bridge.ROOT
        try:
            with tempfile.TemporaryDirectory() as td:
                root = Path(td)
                bridge.ROOT = root
                gov = root / "canonical/governance"
                ver = root / "canonical/verification"
                gov.mkdir(parents=True)
                ver.mkdir(parents=True)

                adequacy_path = gov / "policy_p.json"
                adequacy = {
                    "schema": bridge.ADEQUACY_SCHEMA,
                    "policy_id": "p",
                    "policy_condition_sha256": bridge._condition_sha256(condition),
                    "adequacy_proved": True,
                    "brain_owned": True,
                    "load_bearing_constraints_preserved": True,
                }
                adequacy_path.write_text(json.dumps(adequacy, sort_keys=True), encoding="utf-8")
                adequacy_blob = bridge._git_blob_sha(adequacy_path)

                verification_path = ver / "policy_p_verify.json"
                verification = {
                    "schema": bridge.VERIFY_SCHEMA,
                    "policy_id": "p",
                    "subject_git_blob_sha": adequacy_blob,
                    "pass": True,
                }
                verification_path.write_text(json.dumps(verification, sort_keys=True), encoding="utf-8")
                verification_blob = bridge._git_blob_sha(verification_path)

                out = bridge.resolve_from_source_proof(
                    text,
                    source_id="s",
                    claims=[claim],
                    decision_basis=[atom_id],
                    policy_conditions={"p": condition},
                    policy_adequacy_bindings={
                        "p": {
                            "adequacy_certificate_path": "canonical/governance/policy_p.json",
                            "adequacy_certificate_blob_sha": adequacy_blob,
                            "independent_verification_path": "canonical/verification/policy_p_verify.json",
                            "independent_verification_blob_sha": verification_blob,
                        }
                    },
                )
                self.assertEqual(out["status"], "POLICY_CONDITION_ENTAILED__ADEQUACY_UNAUTHENTICATED")
                self.assertEqual(out["certified_common_policies"], [])
                self.assertIn(
                    "POLICY_ADEQUACY_ROOT_UNREGISTERED",
                    out["rejected_policy_adequacy_bindings"][0]["reason"],
                )
        finally:
            bridge.ROOT = old_root

    def test_forged_verification_subject_cannot_certify(self):
        text, claim, atom_id = self._fixture()
        condition = {"op": "ATOM", "id": atom_id}
        old_root = bridge.ROOT
        try:
            with tempfile.TemporaryDirectory() as td:
                root = Path(td)
                bridge.ROOT = root
                gov = root / "canonical/governance"
                ver = root / "canonical/verification"
                gov.mkdir(parents=True)
                ver.mkdir(parents=True)

                adequacy_path = gov / "policy_p.json"
                adequacy_path.write_text(json.dumps({
                    "schema": bridge.ADEQUACY_SCHEMA,
                    "policy_id": "p",
                    "policy_condition_sha256": bridge._condition_sha256(condition),
                    "adequacy_proved": True,
                    "brain_owned": True,
                    "load_bearing_constraints_preserved": True,
                }, sort_keys=True), encoding="utf-8")
                adequacy_blob = bridge._git_blob_sha(adequacy_path)

                verification_path = ver / "policy_p_verify.json"
                verification_path.write_text(json.dumps({
                    "schema": bridge.VERIFY_SCHEMA,
                    "policy_id": "p",
                    "subject_git_blob_sha": "0" * 40,
                    "pass": True,
                }, sort_keys=True), encoding="utf-8")
                verification_blob = bridge._git_blob_sha(verification_path)

                out = bridge.resolve_from_source_proof(
                    text,
                    source_id="s",
                    claims=[claim],
                    decision_basis=[atom_id],
                    policy_conditions={"p": condition},
                    policy_adequacy_bindings={
                        "p": {
                            "adequacy_certificate_path": "canonical/governance/policy_p.json",
                            "adequacy_certificate_blob_sha": adequacy_blob,
                            "independent_verification_path": "canonical/verification/policy_p_verify.json",
                            "independent_verification_blob_sha": verification_blob,
                        }
                    },
                )
                self.assertEqual(out["certified_common_policies"], [])
                self.assertEqual(out["status"], "POLICY_CONDITION_ENTAILED__ADEQUACY_UNAUTHENTICATED")
        finally:
            bridge.ROOT = old_root


if __name__ == "__main__":
    unittest.main()
