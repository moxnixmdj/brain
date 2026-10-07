import copy

import pytest

from canonical.runtime.monotone_proof_carrying_semantic_kernel_v1 import (
    PROOF_SCHEMA,
    SemanticKernel,
    make_exact_typed_boolean_fact_proof,
)


def test_omitted_semantic_fact_cannot_create_false_policy_entailment():
    k = SemanticKernel(["rule_applicable", "material_exception"])
    source = {"rule_applicable": True}
    proof = make_exact_typed_boolean_fact_proof(source, "rule_applicable")

    out = k.admit_exact_typed_boolean_fact(source, proof)
    assert out["pass"] is True
    assert k.possible_values("material_exception") == frozenset({False, True})
    assert k.entails([
        {"atom": "rule_applicable", "value": True},
        {"atom": "material_exception", "value": True},
    ]) is False
    assert k.select_certified_policy({
        "APPLY": [
            {"atom": "rule_applicable", "value": True},
            {"atom": "material_exception", "value": False},
        ]
    })["status"] == "UNKNOWN_FAIL_CLOSED"


def test_proved_missing_fact_can_finish_policy_entailment():
    k = SemanticKernel(["rule_applicable", "material_exception"])
    source = {"rule_applicable": True, "material_exception": False}

    first = make_exact_typed_boolean_fact_proof(source, "rule_applicable")
    second = make_exact_typed_boolean_fact_proof(source, "material_exception")
    assert k.admit_exact_typed_boolean_fact(source, first)["pass"] is True
    assert k.entails([
        {"atom": "rule_applicable", "value": True},
        {"atom": "material_exception", "value": False},
    ]) is False

    assert k.admit_exact_typed_boolean_fact(source, second)["pass"] is True
    assert k.entails([
        {"atom": "rule_applicable", "value": True},
        {"atom": "material_exception", "value": False},
    ]) is True


def test_unproved_constraint_injection_is_rejected_without_state_change():
    k = SemanticKernel(["rule_applicable"])
    source = {"rule_applicable": True}
    bad = {
        "schema": PROOF_SCHEMA,
        "atom": "rule_applicable",
        "field": "rule_applicable",
        "value": True,
        "source_sha256": "0" * 64,
    }
    before = k.model_count
    out = k.admit_exact_typed_boolean_fact(source, bad)
    assert out["pass"] is False
    assert "SOURCE_HASH_MISMATCH" in out["errors"]
    assert k.model_count == before
    assert k.possible_values("rule_applicable") == frozenset({False, True})


def test_same_name_semantic_identity_is_required():
    k = SemanticKernel(["rule_applicable"])
    source = {"other_field": True}
    proof = make_exact_typed_boolean_fact_proof(source, "other_field")
    proof = dict(proof, atom="rule_applicable", field="other_field")

    out = k.admit_exact_typed_boolean_fact(source, proof)
    assert out["pass"] is False
    assert "FIELD_ATOM_IDENTITY_REQUIRED" in out["errors"]


def test_refinement_is_monotone_and_never_adds_models():
    k = SemanticKernel(["a", "b", "c"])
    counts = [k.model_count]
    source = {"a": True, "b": False, "c": True}
    for atom in ["a", "b", "c"]:
        out = k.admit_exact_typed_boolean_fact(
            source, make_exact_typed_boolean_fact_proof(source, atom)
        )
        assert out["pass"] is True
        counts.append(k.model_count)

    assert counts == sorted(counts, reverse=True)
    assert counts == [8, 4, 2, 1]


def test_false_boolean_fact_is_preserved_exactly_not_treated_as_missing():
    k = SemanticKernel(["exception_present"])
    source = {"exception_present": False}
    proof = make_exact_typed_boolean_fact_proof(source, "exception_present")
    assert k.admit_exact_typed_boolean_fact(source, proof)["pass"] is True
    assert k.possible_values("exception_present") == frozenset({False})
    assert k.entails([{"atom": "exception_present", "value": False}]) is True
    assert k.entails([{"atom": "exception_present", "value": True}]) is False


def test_non_boolean_semantic_value_fails_closed():
    k = SemanticKernel(["material_exception"])
    source = {"material_exception": "maybe"}
    proof = make_exact_typed_boolean_fact_proof(source, "material_exception")
    before = k.model_count
    out = k.admit_exact_typed_boolean_fact(source, proof)
    assert out["pass"] is False
    assert "FIELD_VALUE_NOT_BOOLEAN" in out["errors"]
    assert "CLAIMED_VALUE_NOT_BOOLEAN" in out["errors"]
    assert k.model_count == before


def test_tampered_source_after_proof_is_rejected():
    k = SemanticKernel(["rule_applicable"])
    source = {"rule_applicable": True}
    proof = make_exact_typed_boolean_fact_proof(source, "rule_applicable")
    tampered = copy.deepcopy(source)
    tampered["rule_applicable"] = False

    out = k.admit_exact_typed_boolean_fact(tampered, proof)
    assert out["pass"] is False
    assert "SOURCE_HASH_MISMATCH" in out["errors"]
    assert "CLAIMED_VALUE_MISMATCH" in out["errors"]


def test_invalid_policy_requirement_is_never_silently_ignored():
    k = SemanticKernel(["a"])
    with pytest.raises(ValueError):
        k.entails([{"atom": "unknown", "value": True}])
    with pytest.raises(ValueError):
        k.entails([{"atom": "a", "value": "true"}])
