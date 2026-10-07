import json
import tempfile
from pathlib import Path

import canonical.runtime.proof_carrying_semantic_refinement_v3 as adequacy_auth
from canonical.runtime.proof_carrying_semantic_refinement_v4 import resolve_from_source_proof
from canonical.runtime.source_aligned_semantic_proof_v3 import typed_context_sha256
from canonical.runtime.source_aligned_semantic_proof_v4 import verify_proof


def test_v4_authenticated_policy_adequacy_can_certify():
    text = "Apply Rule A unless exception_holds is true."
    context = {
        "schema_id": "FINANCE_TYPED_CONTEXT_V1",
        "fields": {"exception_holds": {"type": "BOOL", "value": True}},
    }
    digest = typed_context_sha256(context)
    claim = {
        "claim_id": "cond",
        "kind": "CERTIFIED_TYPED_UNLESS_CONDITION",
        "condition_holds": True,
    }
    checked = verify_proof(
        text, source_id="s", claims=[claim],
        typed_context=context, expected_typed_context_sha256=digest,
    )
    atom_id = checked["accepted_claims"][0]["condition_atom_id"]
    condition = {"op": "ATOM", "id": atom_id}

    old_root = adequacy_auth.ROOT
    try:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            adequacy_auth.ROOT = root
            gov = root / "canonical/governance"
            ver = root / "canonical/verification"
            gov.mkdir(parents=True)
            ver.mkdir(parents=True)

            adequacy_path = gov / "p.json"
            adequacy_path.write_text(json.dumps({
                "schema": adequacy_auth.ADEQUACY_SCHEMA,
                "policy_id": "exception_policy",
                "policy_condition_sha256": adequacy_auth._condition_sha256(condition),
                "adequacy_proved": True,
                "brain_owned": True,
                "load_bearing_constraints_preserved": True,
            }, sort_keys=True), encoding="utf-8")
            adequacy_blob = adequacy_auth._git_blob_sha(adequacy_path)

            verify_path = ver / "p_verify.json"
            verify_path.write_text(json.dumps({
                "schema": adequacy_auth.VERIFY_SCHEMA,
                "policy_id": "exception_policy",
                "subject_git_blob_sha": adequacy_blob,
                "pass": True,
            }, sort_keys=True), encoding="utf-8")
            verify_blob = adequacy_auth._git_blob_sha(verify_path)

            out = resolve_from_source_proof(
                text,
                source_id="s",
                claims=[claim],
                decision_basis=[atom_id],
                policy_conditions={"exception_policy": condition},
                typed_context=context,
                expected_typed_context_sha256=digest,
                policy_adequacy_bindings={
                    "exception_policy": {
                        "adequacy_certificate_path": "canonical/governance/p.json",
                        "adequacy_certificate_blob_sha": adequacy_blob,
                        "independent_verification_path": "canonical/verification/p_verify.json",
                        "independent_verification_blob_sha": verify_blob,
                    }
                },
            )
            assert out["status"] == "COMMON_POLICY_CERTIFIED"
            assert out["certified_common_policies"] == ["exception_policy"]
    finally:
        adequacy_auth.ROOT = old_root
