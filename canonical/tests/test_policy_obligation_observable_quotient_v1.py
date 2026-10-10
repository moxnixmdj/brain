from canonical.runtime.policy_obligation_observable_quotient_v1 import evaluate, _sha


def atom(name):
    return {"op": "ATOM", "id": name}


def neg(x):
    return {"op": "NOT", "arg": x}


def true():
    return {"op": "TRUE"}


def policy(scope, basis, pid, condition):
    return {
        "policy_id": pid,
        "condition": condition,
        "adequacy_receipt": {
            "independent_verified": True,
            "exact_byte_bound": True,
            "conclusion": "success",
            "scope_id": scope,
            "policy_id": pid,
            "condition_sha256": _sha(condition),
            "decision_basis_sha256": _sha(basis),
            "policy_adequate_whenever_condition_true": True,
            "brain_owned": True,
            "deployed_exact": True,
            "resource_bound_proved": True,
        },
    }


def observation(scope, basis, oid, formula, cost=1):
    return {
        "observation_id": oid,
        "formula": formula,
        "cost_units": cost,
        "truth_safety_receipt": {
            "independent_verified": True,
            "exact_byte_bound": True,
            "conclusion": "success",
            "scope_id": scope,
            "observation_id": oid,
            "formula_sha256": _sha(formula),
            "decision_basis_sha256": _sha(basis),
            "truth_preserving_on_scope": True,
            "safe_on_scope": True,
            "resource_bound_proved": True,
        },
    }


def test_common_policy_needs_zero_observations():
    scope = "S"
    basis = ["x"]
    out = evaluate({
        "scope_id": scope,
        "decision_basis": basis,
        "policies": [policy(scope, basis, "common", true())],
        "observations": [],
    })
    assert out["pass"] is True
    assert out["positive_quotient_closed"] is True
    assert out["selected_observation_ids"] == []
    assert out["common_policy_without_observation"] is True


def test_one_observable_atom_closes_disjoint_policy_regions():
    scope = "S"
    basis = ["x"]
    out = evaluate({
        "scope_id": scope,
        "decision_basis": basis,
        "policies": [
            policy(scope, basis, "p0", neg(atom("x"))),
            policy(scope, basis, "p1", atom("x")),
        ],
        "observations": [observation(scope, basis, "observe_x", atom("x"))],
    })
    assert out["pass"] is True
    assert out["selected_observation_ids"] == ["observe_x"]
    assert len(out["quotient_classes"]) == 2
    assert all(row["common_policy_ids"] for row in out["quotient_classes"])


def test_irrelevant_observation_is_deleted():
    scope = "S"
    basis = ["x", "y"]
    out = evaluate({
        "scope_id": scope,
        "decision_basis": basis,
        "policies": [
            policy(scope, basis, "p0", neg(atom("x"))),
            policy(scope, basis, "p1", atom("x")),
        ],
        "observations": [
            observation(scope, basis, "observe_y", atom("y"), cost=0),
            observation(scope, basis, "observe_x", atom("x"), cost=2),
        ],
    })
    assert out["pass"] is True
    assert out["selected_observation_ids"] == ["observe_x"]
    assert out["selected_observation_count"] == 1


def test_uncovered_abstract_model_is_exact_positive_cover_witness():
    scope = "S"
    basis = ["x"]
    out = evaluate({
        "scope_id": scope,
        "decision_basis": basis,
        "policies": [policy(scope, basis, "p1", atom("x"))],
        "observations": [],
    })
    assert out["pass"] is False
    assert out["status"] == "UNRESOLVED__POSITIVE_POLICY_COVER_GAP"
    assert len(out["uncovered_abstract_models"]) == 1
    assert out["uncovered_is_capability_failure"] is False


def test_unobservable_policy_conflict_returns_bad_classes_not_impossibility():
    scope = "S"
    basis = ["x", "y"]
    out = evaluate({
        "scope_id": scope,
        "decision_basis": basis,
        "policies": [
            policy(scope, basis, "p0", neg(atom("x"))),
            policy(scope, basis, "p1", atom("x")),
        ],
        "observations": [observation(scope, basis, "observe_y", atom("y"))],
    })
    assert out["pass"] is False
    assert out["status"] == "UNRESOLVED__UNSPLITTABLE_POLICY_CONFLICT_RELATIVE_TO_DECLARED_OBSERVATIONS"
    assert out["negative_impossibility_authorized"] is False
    assert out["unsplittable_bad_classes"]


def test_missing_policy_receipt_fails_closed():
    scope = "S"
    basis = ["x"]
    row = policy(scope, basis, "p", true())
    row.pop("adequacy_receipt")
    out = evaluate({
        "scope_id": scope,
        "decision_basis": basis,
        "policies": [row],
        "observations": [],
    })
    assert out["pass"] is False
    assert out["reason"] == "POLICY_ADEQUACY_RECEIPT_INVALID"


def test_unsound_observation_receipt_fails_closed():
    scope = "S"
    basis = ["x"]
    obs = observation(scope, basis, "observe_x", atom("x"))
    obs["truth_safety_receipt"]["truth_preserving_on_scope"] = False
    out = evaluate({
        "scope_id": scope,
        "decision_basis": basis,
        "policies": [
            policy(scope, basis, "p0", neg(atom("x"))),
            policy(scope, basis, "p1", atom("x")),
        ],
        "observations": [obs],
    })
    assert out["pass"] is False
    assert out["reason"] == "OBSERVATION_RECEIPT_INVALID"


def test_policy_condition_digest_substitution_fails_closed():
    scope = "S"
    basis = ["x"]
    row = policy(scope, basis, "p", true())
    row["adequacy_receipt"]["condition_sha256"] = "sha256:" + "0" * 64
    out = evaluate({
        "scope_id": scope,
        "decision_basis": basis,
        "policies": [row],
        "observations": [],
    })
    assert out["pass"] is False
    assert out["reason"] == "POLICY_ADEQUACY_RECEIPT_INVALID"


def test_unproved_missing_semantics_stays_broad_and_cannot_false_pass():
    scope = "S"
    basis = ["x"]
    out = evaluate({
        "scope_id": scope,
        "decision_basis": basis,
        "policies": [
            policy(scope, basis, "p0", neg(atom("x"))),
            policy(scope, basis, "p1", atom("x")),
        ],
        "observations": [],
    })
    assert out["pass"] is False
    assert out["status"] == "UNRESOLVED__UNSPLITTABLE_POLICY_CONFLICT_RELATIVE_TO_DECLARED_OBSERVATIONS"


def test_proved_source_constraint_can_remove_the_unneeded_discriminator():
    scope = "S"
    basis = ["x"]
    fact = atom("x")
    out = evaluate({
        "scope_id": scope,
        "decision_basis": basis,
        "formal_source_constraints": [fact],
        "proposed_refinements": [fact],
        "policies": [
            policy(scope, basis, "p0", neg(atom("x"))),
            policy(scope, basis, "p1", atom("x")),
        ],
        "observations": [],
    })
    assert out["pass"] is True
    assert out["abstract_model_count"] == 1
    assert out["selected_observation_ids"] == []
    assert out["quotient_classes"][0]["common_policy_ids"] == ["p1"]


def test_unknown_refinement_is_rejected_by_kernel_and_cannot_narrow_state():
    scope = "S"
    basis = ["x"]
    fact = atom("x")
    out = evaluate({
        "scope_id": scope,
        "decision_basis": basis,
        "formal_source_constraints": [],
        "proposed_refinements": [fact],
        "policies": [
            policy(scope, basis, "p0", neg(atom("x"))),
            policy(scope, basis, "p1", atom("x")),
        ],
        "observations": [],
    })
    assert out["pass"] is False
    assert out["status"] == "UNRESOLVED__UNSPLITTABLE_POLICY_CONFLICT_RELATIVE_TO_DECLARED_OBSERVATIONS"
