from canonical.runtime.adequacy_basis_structural_completeness_gate_v1 import (
    MANIFEST_SCHEMA,
    compile_contract_basis,
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


def _manifest():
    a = _atoms()
    policy_fields = {
        "allowed_information",
        "required_output_or_action",
        "success_condition",
        "failure_condition",
        "dependency_boundary",
    }
    policy_atoms = [a[x] for x in sorted(policy_fields)]
    return {
        "schema": MANIFEST_SCHEMA,
        "behavior_id": "TEST_BEHAVIOR",
        "candidate_policy_set_complete_certificate_id": "CERT_POLICY_SET",
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


def test_complete_manifest_passes_without_interpreting_contract_prose():
    out = verify_policy_manifest(CONTRACT, SCHEMA, _manifest())
    assert out["pass"] is True, out
    assert out["structural_field_omission_closed"] is True
    assert out["semantic_truth_self_verified"] is False
    assert out["candidate_policy_set_completeness_self_verified"] is False


def test_missing_success_condition_from_policy_basis_fails_closed():
    a = _atoms()
    m = _manifest()
    m["policies"][0]["basis_atom_ids"].remove(a["success_condition"])
    out = verify_policy_manifest(CONTRACT, SCHEMA, m)
    assert out["pass"] is False
    assert any("POLICY_REQUIRED_OBLIGATION_NOT_IN_BASIS:P:" in x for x in out["errors"])


def test_missing_scope_from_admission_fails_closed():
    a = _atoms()
    m = _manifest()
    m["admission_atom_ids"].remove(a["scope"])
    out = verify_policy_manifest(CONTRACT, SCHEMA, m)
    assert out["pass"] is False
    assert "MEMBERSHIP_OBLIGATION_UNBOUND:" + a["scope"] in out["errors"]


def test_independent_unconditional_discharge_can_replace_contingent_basis_atom():
    a = _atoms()
    m = _manifest()
    m["policies"][0]["basis_atom_ids"].remove(a["success_condition"])
    m["policies"][0]["policy_condition_atom_ids"].remove(a["success_condition"])
    m["policies"][0]["unconditional_discharges"] = [{
        "atom_id": a["success_condition"],
        "certificate_id": "CERT_SUCCESS_TOP_LAW",
    }]
    out = verify_policy_manifest(CONTRACT, SCHEMA, m)
    assert out["pass"] is True, out


def test_discharge_without_certificate_fails_closed():
    a = _atoms()
    m = _manifest()
    m["policies"][0]["basis_atom_ids"].remove(a["failure_condition"])
    m["policies"][0]["policy_condition_atom_ids"].remove(a["failure_condition"])
    m["policies"][0]["unconditional_discharges"] = [{
        "atom_id": a["failure_condition"],
        "certificate_id": "",
    }]
    out = verify_policy_manifest(CONTRACT, SCHEMA, m)
    assert out["pass"] is False
    assert "POLICY_DISCHARGE_CERTIFICATE_MISSING:P:" + a["failure_condition"] in out["errors"]


def test_missing_candidate_policy_set_completeness_reference_fails_closed():
    m = _manifest()
    m["candidate_policy_set_complete_certificate_id"] = ""
    out = verify_policy_manifest(CONTRACT, SCHEMA, m)
    assert out["pass"] is False
    assert "CANDIDATE_POLICY_SET_COMPLETENESS_CERTIFICATE_MISSING" in out["errors"]


def test_required_contract_field_cannot_silently_disappear():
    bad = dict(CONTRACT)
    del bad["dependency_boundary"]
    out = compile_contract_basis(bad, SCHEMA)
    assert out["pass"] is False
    assert "REQUIRED_CONTRACT_FIELD_MISSING:dependency_boundary" in out["errors"]


def test_unknown_policy_atom_is_rejected():
    m = _manifest()
    m["policies"][0]["basis_atom_ids"].append("CONTRACT::FAKE")
    out = verify_policy_manifest(CONTRACT, SCHEMA, m)
    assert out["pass"] is False
    assert "POLICY_BASIS_UNKNOWN_ATOM:P:CONTRACT::FAKE" in out["errors"]


def test_policy_condition_atom_cannot_live_outside_declared_basis():
    a = _atoms()
    m = _manifest()
    m["policies"][0]["basis_atom_ids"].remove(a["allowed_information"])
    out = verify_policy_manifest(CONTRACT, SCHEMA, m)
    assert out["pass"] is False
    assert (
        "POLICY_CONDITION_ATOM_OUTSIDE_BASIS:P:" + a["allowed_information"]
        in out["errors"]
    )


def test_all_canonical_registry_contracts_compile_required_base_fields():
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    schema = json.loads(
        (root / "canonical/governance/BEHAVIORAL_CONTRACT_SCHEMA_V1.json").read_text()
    )
    registry = json.loads(
        (root / "canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V2.json").read_text()
    )
    rows = registry["active_contracted_residuals"]
    assert len(rows) == 13
    for row in rows:
        out = compile_contract_basis(row, schema)
        assert out["pass"] is True, (row["behavior_id"], out)
        assert len(out["obligations"]) == len(schema["required_behavior_fields"])
