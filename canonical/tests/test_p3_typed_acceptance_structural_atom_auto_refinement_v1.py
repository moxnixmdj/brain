from canonical.runtime import p3_robust_policy_adequacy_cegar_v1 as p3

POLICY = "BRAIN_INDEPENDENT_ACCEPTANCE_MODEL_TYPED_PLAN_V1"
AUTO = "SPEC_ACCEPT_SUPPORTED_TRANSFORM_KINDS_ONLY_V1"
EXTERNAL = [
    "SPEC_ACCEPT_TYPED_SEMANTICS_BOUND_V1",
    "SPEC_ACCEPT_FAILURE_MODE_COMPLETENESS_V1",
    "SPEC_ACCEPT_DEPENDENCY_PROVENANCE_TRUTH_V1",
    "SPEC_ACCEPT_NO_HIDDEN_VERIFIER_ACCESS_V1",
]

NO_HIDDEN = "SPEC_ACCEPT_NO_HIDDEN_VERIFIER_ACCESS_V1"
PREWAVE = {
    "path": "canonical/governance/SPECIFICATION_INDEPENDENT_ACCEPTANCE_PREWAVE_BINDING_V1.json",
    "git_blob_sha": "65c2ea78a548b4f4cd12ca6275cbad7ad2e08900",
}
THREE = [
    "SPEC_ACCEPT_TYPED_SEMANTICS_BOUND_V1",
    "SPEC_ACCEPT_FAILURE_MODE_COMPLETENESS_V1",
    "SPEC_ACCEPT_DEPENDENCY_PROVENANCE_TRUTH_V1",
]


def atom(x):
    return {"op": "ATOM", "id": x}


def typed_model(kind="artifact"):
    return {
        "requirements": [{
            "id": "R",
            "critical": True,
            "transform_kinds": [kind],
            "builder_dependencies": ["raw:source"],
        }],
        "checks": [],
    }


def problem(*, include_model=True, kind="artifact"):
    out = {
        "decision_basis": list(EXTERNAL),
        "formal_source_constraints": [atom(x) for x in EXTERNAL],
        "proposed_refinements": [atom(x) for x in EXTERNAL],
    }
    if include_model:
        out["typed_acceptance_model"] = typed_model(kind)
    return out


def test_structural_model_auto_proves_fifth_atom_and_selects_specialist():
    out = p3.solve(problem())
    assert out["pass"] is True, out
    assert out["selected_policy_id"] == POLICY
    reg = out["conditioned_policy_adequacy_registry"]
    assert POLICY in reg["injected_policy_ids"]
    assert AUTO in reg["structurally_proved_atom_ids"]
    assert out["semantic_state"]["accepted_refinements"] == [atom(x) for x in EXTERNAL] + [atom(AUTO)]


def test_without_exact_typed_model_no_structural_atom_is_created():
    out = p3.solve(problem(include_model=False))
    assert out["pass"] is False
    reg = out["conditioned_policy_adequacy_registry"]
    assert POLICY not in reg["injected_policy_ids"]
    assert reg["structurally_proved_atom_ids"] == []


def test_unknown_transform_does_not_create_structural_atom_or_inject_policy():
    out = p3.solve(problem(kind="UNKNOWN_TRANSFORM"))
    assert out["pass"] is False
    reg = out["conditioned_policy_adequacy_registry"]
    assert POLICY not in reg["injected_policy_ids"]
    assert reg["structurally_proved_atom_ids"] == []
    proof = reg["structural_atom_proofs"][0]
    assert proof["pass"] is False
    assert proof["unknown_transform_kinds"] == ["UNKNOWN_TRANSFORM"]


def test_structural_proof_does_not_create_any_of_the_other_four_atoms():
    p = {
        "decision_basis": [EXTERNAL[0]],
        "formal_source_constraints": [atom(EXTERNAL[0])],
        "proposed_refinements": [atom(EXTERNAL[0])],
        "typed_acceptance_model": typed_model(),
    }
    out = p3.solve(p)
    assert out["pass"] is False
    reg = out["conditioned_policy_adequacy_registry"]
    assert reg["structurally_proved_atom_ids"] == [AUTO]
    assert POLICY not in reg["injected_policy_ids"]


def test_existing_supported_atom_is_not_duplicated():
    p = problem()
    p["decision_basis"].append(AUTO)
    p["formal_source_constraints"].append(atom(AUTO))
    p["proposed_refinements"].append(atom(AUTO))
    out = p3.solve(p)
    assert out["pass"] is True, out
    assert out["decision_basis"].count(AUTO) == 1
    assert out["semantic_state"]["accepted_refinements"].count(atom(AUTO)) == 1


def prewave_problem(*, binding=PREWAVE):
    return {
        "decision_basis": list(THREE),
        "formal_source_constraints": [atom(x) for x in THREE],
        "proposed_refinements": [atom(x) for x in THREE],
        "typed_acceptance_model": typed_model(),
        "typed_acceptance_information_boundary_binding": dict(binding),
    }


def test_exact_prewave_boundary_plus_structural_model_reduces_external_burden_to_three():
    out = p3.solve(prewave_problem())
    assert out["pass"] is True, out
    assert out["selected_policy_id"] == POLICY
    reg = out["conditioned_policy_adequacy_registry"]
    assert reg["structurally_proved_atom_ids"] == [AUTO]
    assert reg["source_bound_proved_atom_ids"] == [NO_HIDDEN]
    assert POLICY in reg["injected_policy_ids"]
    accepted = out["semantic_state"]["accepted_refinements"]
    assert set(tuple(sorted(x.items())) for x in accepted) == set(
        tuple(sorted(atom(x).items())) for x in THREE + [AUTO, NO_HIDDEN]
    )


def test_without_exact_prewave_boundary_three_external_atoms_are_not_enough():
    p = prewave_problem()
    p.pop("typed_acceptance_information_boundary_binding")
    out = p3.solve(p)
    assert out["pass"] is False
    reg = out["conditioned_policy_adequacy_registry"]
    assert reg["structurally_proved_atom_ids"] == [AUTO]
    assert reg["source_bound_proved_atom_ids"] == []
    assert POLICY not in reg["injected_policy_ids"]


def test_forged_prewave_binding_fails_closed_instead_of_self_certifying():
    bad = dict(PREWAVE)
    bad["git_blob_sha"] = "0" * 40
    out = p3.solve(prewave_problem(binding=bad))
    assert out["pass"] is False
    assert out["reason"] == "CONDITIONED_POLICY_ADEQUACY_REGISTRY_FAIL_CLOSED"
    inner = out["detail"]["conditioned_policy_adequacy_registry"]
    assert inner["reason"] == "SOURCE_BOUND_ATOM_PROOF_FAILED"
    proof = inner["detail"]["proof"]
    assert proof["atom_truth_authorized"] is False
    assert proof["reason"] == "BINDING_REFERENCE_SHA_MISMATCH"


def test_malformed_refinement_collection_fails_closed_when_auto_proof_would_write():
    p = problem()
    p["formal_source_constraints"] = "not-a-list"
    out = p3.solve(p)
    assert out["pass"] is False
    assert out["reason"] == "CONDITIONED_POLICY_ADEQUACY_REGISTRY_FAIL_CLOSED"
    inner = out["detail"]["conditioned_policy_adequacy_registry"]
    assert inner["reason"] == "STRUCTURAL_ATOM_REFINEMENT_TARGET_NOT_LIST"
