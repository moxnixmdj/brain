from canonical.runtime.adequacy_basis_structural_completeness_gate_v1 import (
    compile_contract_basis,
)
from canonical.runtime.adequacy_basis_structural_completeness_gate_v2 import (
    MINIMUM,
    NEGATIVE,
    POSITIVE,
    verify_policy_manifest,
)

SCHEMA = {
    "required_behavior_fields": [
        "behavior_id",
        "inputs",
        "environment_state",
        "allowed_information",
        "required_output_or_action",
        "success_condition",
        "failure_condition",
        "terminal_consequence",
        "verification_route",
        "dependency_boundary",
        "scope",
    ]
}

CONTRACT = {
    "behavior_id": "TEST_BEHAVIOR",
    "inputs": "visible task input",
    "environment_state": "declared environment",
    "allowed_information": "visible information only",
    "required_output_or_action": "return correct action",
    "success_condition": "required result is correct",
    "failure_condition": "wrong or unsupported result",
    "terminal_consequence": "load-bearing test behavior",
    "verification_route": "independent verifier",
    "dependency_boundary": "Brain-owned route only",
    "scope": "frozen test scope",
}


def _atoms():
    out = compile_contract_basis(CONTRACT, SCHEMA)
    assert out["pass"] is True
    return {row["field"]: row["atom_id"] for row in out["obligations"]}


def _manifest(mode, *, include_set_certificate=False):
    a = _atoms()
    policy_fields = {
        "allowed_information",
        "required_output_or_action",
        "success_condition",
        "failure_condition",
        "dependency_boundary",
    }
    policy_atoms = [a[x] for x in sorted(policy_fields)]
    out = {
        "schema": "PROJECT_BRAIN_POLICY_ADEQUACY_BASIS_MANIFEST_V1",
        "behavior_id": "TEST_BEHAVIOR",
        "claim_mode": mode,
        "admission_atom_ids": [a["inputs"], a["environment_state"], a["scope"]],
        "promotion_atom_ids": [a["verification_route"]],
        "terminal_accounting_atom_ids": [a["terminal_consequence"]],
        "policies": [{
            "policy_id": "P",
            "basis_atom_ids": list(policy_atoms),
            "policy_condition_atom_ids": list(policy_atoms),
            "unconditional_discharges": [],
        }],
    }
    if include_set_certificate:
        out["candidate_policy_set_complete_certificate_id"] = "CERT_POLICY_SET"
    return out


def test_positive_cover_does_not_require_candidate_policy_set_completeness():
    out = verify_policy_manifest(CONTRACT, SCHEMA, _manifest(POSITIVE))
    assert out["pass"] is True, out
    assert out["candidate_policy_set_completeness_required"] is False


def test_positive_cover_with_optional_completeness_reference_still_passes():
    out = verify_policy_manifest(
        CONTRACT, SCHEMA, _manifest(POSITIVE, include_set_certificate=True)
    )
    assert out["pass"] is True, out


def test_negative_exhaustive_claim_still_requires_completeness():
    out = verify_policy_manifest(CONTRACT, SCHEMA, _manifest(NEGATIVE))
    assert out["pass"] is False
    assert "CANDIDATE_POLICY_SET_COMPLETENESS_CERTIFICATE_MISSING" in out["errors"]


def test_minimum_information_optimality_still_requires_completeness():
    out = verify_policy_manifest(CONTRACT, SCHEMA, _manifest(MINIMUM))
    assert out["pass"] is False
    assert "CANDIDATE_POLICY_SET_COMPLETENESS_CERTIFICATE_MISSING" in out["errors"]


def test_positive_cover_does_not_hide_other_structural_omissions():
    m = _manifest(POSITIVE)
    a = _atoms()
    m["policies"][0]["basis_atom_ids"].remove(a["success_condition"])
    out = verify_policy_manifest(CONTRACT, SCHEMA, m)
    assert out["pass"] is False
    assert any("POLICY_REQUIRED_OBLIGATION_NOT_IN_BASIS" in x for x in out["errors"])


def test_unknown_claim_mode_fails_closed():
    out = verify_policy_manifest(CONTRACT, SCHEMA, _manifest("WHATEVER"))
    assert out["pass"] is False
    assert out["errors"] == ["CLAIM_MODE_INVALID_OR_MISSING"]
