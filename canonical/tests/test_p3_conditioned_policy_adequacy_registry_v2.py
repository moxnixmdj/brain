from unittest.mock import patch

from canonical.runtime import p3_conditioned_policy_adequacy_registry_v2 as v2

SEM = "SPEC_ACCEPT_TYPED_SEMANTICS_BOUND_V1"
COMP = "SPEC_ACCEPT_FAILURE_MODE_COMPLETENESS_V1"
DEP = "SPEC_ACCEPT_DEPENDENCY_PROVENANCE_TRUTH_V1"
INFO = "SPEC_ACCEPT_NO_HIDDEN_VERIFIER_ACCESS_V1"
TRANSFORM = "SPEC_ACCEPT_SUPPORTED_TRANSFORM_KINDS_ONLY_V1"
POLICY = "BRAIN_INDEPENDENT_ACCEPTANCE_MODEL_TYPED_PLAN_V1"

def _problem():
    return {
        "decision_basis": [DEP, INFO],
        "formal_source_constraints": [
            {"op": "ATOM", "id": DEP},
            {"op": "ATOM", "id": INFO},
        ],
        "proposed_refinements": [],
        "typed_acceptance_model": {
            "requirements": [{
                "id": "R",
                "critical": True,
                "transform_kinds": ["selection"],
                "builder_dependencies": ["raw:input"],
            }],
            "checks": [],
        },
        "policy_conditions": {},
        "policy_adequacy_bindings": {},
    }

def _proof(atom_id):
    return {
        "pass": True,
        "atom_id": atom_id,
        "atom_truth_authorized": True,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }

def test_missing_new_bindings_prove_nothing_and_policy_stays_ineligible():
    out = v2.augment_problem(_problem())
    assert out["pass"] is True, out
    assert SEM not in out["proved_condition_atom_ids"]
    assert COMP not in out["proved_condition_atom_ids"]
    rows = {
        row["policy_id"]: row
        for row in out["skipped_registered_policies"]
    }
    assert POLICY in rows
    assert SEM in rows[POLICY]["missing_atoms"]
    assert COMP in rows[POLICY]["missing_atoms"]

def test_verified_new_atoms_delegate_to_v1_and_unlock_existing_policy():
    p = _problem()
    p["typed_acceptance_semantics_binding"] = {"receipt": {}, "verification": {}}
    p["typed_acceptance_failure_mode_completeness_binding"] = {
        "receipt": {}, "verification": {}
    }
    with patch.object(v2, "verify_semantics_atom", return_value=_proof(SEM)),          patch.object(v2, "verify_completeness_atom", return_value=_proof(COMP)):
        out = v2.augment_problem(p)
    assert out["pass"] is True, out
    assert {SEM, COMP, TRANSFORM}.issubset(set(out["proved_condition_atom_ids"]))
    assert POLICY in out["injected_policy_ids"]
    basis = set(out["problem"]["decision_basis"])
    assert {SEM, COMP, DEP, INFO, TRANSFORM}.issubset(basis)
    assert out["membership_self_certified"] is False
    assert out["terminal_authority"] is False

def test_invalid_semantics_binding_fails_closed_before_registry():
    p = _problem()
    p["typed_acceptance_semantics_binding"] = {"receipt": {}, "verification": {}}
    bad = {
        "pass": False,
        "atom_id": SEM,
        "atom_truth_authorized": False,
        "status": "FAIL_CLOSED",
    }
    with patch.object(v2, "verify_semantics_atom", return_value=bad):
        out = v2.augment_problem(p)
    assert out["pass"] is False
    assert out["status"] == "FAIL_CLOSED"
    assert out["reason"] == "TYPED_SEMANTICS_ATOM_BINDING_INVALID"

def test_new_binding_without_model_fails_closed():
    p = _problem()
    p.pop("typed_acceptance_model")
    p["typed_acceptance_semantics_binding"] = {"receipt": {}, "verification": {}}
    out = v2.augment_problem(p)
    assert out["pass"] is False
    assert "REQUIRES_TYPED_ACCEPTANCE_MODEL" in out["reason"]
