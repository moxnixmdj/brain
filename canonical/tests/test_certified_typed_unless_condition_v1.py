from canonical.runtime.certified_typed_unless_condition_v1 import evaluate_unless_condition
from canonical.runtime.source_aligned_semantic_proof_v3 import typed_context_sha256
from canonical.runtime.monotone_semantic_constraint_kernel_v1 import resolve_common_policy


def context(**fields):
    ctx = {"schema_id": "FINANCE_TYPED_CONTEXT_V1", "fields": fields}
    return ctx, typed_context_sha256(ctx)


def test_bool_exception_true_is_proved_and_selects_exception_policy():
    text = "Apply Rule A unless exception_holds is true."
    ctx, digest = context(exception_holds={"type": "BOOL", "value": True})
    out = evaluate_unless_condition(
        text, source_id="s", typed_context=ctx, expected_typed_context_sha256=digest
    )
    assert out["status"] == "PROVED_TRUE", out
    atom = {"op": "ATOM", "id": out["condition_atom_id"]}
    resolved = resolve_common_policy(
        [out["condition_atom_id"]],
        {
            "exception_policy": atom,
            "ordinary_policy": {"op": "NOT", "arg": atom},
        },
        formal_source_constraints=[out["proved_constraint"]],
        proposed_refinements=[out["proved_constraint"]],
    )
    assert resolved["status"] == "COMMON_POLICY_CERTIFIED"
    assert resolved["certified_common_policies"] == ["exception_policy"]


def test_bool_exception_false_proves_negation_and_selects_ordinary_policy():
    text = "Apply Rule A unless exception_holds is true."
    ctx, digest = context(exception_holds={"type": "BOOL", "value": False})
    out = evaluate_unless_condition(
        text, source_id="s", typed_context=ctx, expected_typed_context_sha256=digest
    )
    assert out["status"] == "PROVED_FALSE", out
    atom = {"op": "ATOM", "id": out["condition_atom_id"]}
    resolved = resolve_common_policy(
        [out["condition_atom_id"]],
        {
            "exception_policy": atom,
            "ordinary_policy": {"op": "NOT", "arg": atom},
        },
        formal_source_constraints=[out["proved_constraint"]],
        proposed_refinements=[out["proved_constraint"]],
    )
    assert resolved["certified_common_policies"] == ["ordinary_policy"]


def test_numeric_minimum_condition_is_exact():
    text = "Apply Rule A unless exposure is at least 125.50."
    ctx, digest = context(exposure={"type": "DECIMAL_STRING", "value": "125.50"})
    out = evaluate_unless_condition(
        text, source_id="s", typed_context=ctx, expected_typed_context_sha256=digest
    )
    assert out["status"] == "PROVED_TRUE"
    assert out["operator"] == "DECIMAL_GE"
    assert out["literal"] == "125.50"


def test_numeric_below_threshold_is_proved_false():
    text = "Apply Rule A unless exposure is at least 125.50."
    ctx, digest = context(exposure={"type": "DECIMAL_STRING", "value": "125.49"})
    out = evaluate_unless_condition(
        text, source_id="s", typed_context=ctx, expected_typed_context_sha256=digest
    )
    assert out["status"] == "PROVED_FALSE"


def test_unknown_field_remains_unresolved():
    text = "Apply Rule A unless exception_holds is true."
    ctx, digest = context(other={"type": "BOOL", "value": True})
    out = evaluate_unless_condition(
        text, source_id="s", typed_context=ctx, expected_typed_context_sha256=digest
    )
    assert out["status"] == "UNRESOLVED"
    assert out["reason"] == "SOURCE_FIELD_NOT_PRESENT_IN_TYPED_CONTEXT"


def test_uncontrolled_language_remains_unresolved():
    text = "Apply Rule A unless the customer qualifies under the material exception."
    ctx, digest = context(exception_holds={"type": "BOOL", "value": True})
    out = evaluate_unless_condition(
        text, source_id="s", typed_context=ctx, expected_typed_context_sha256=digest
    )
    assert out["status"] == "UNRESOLVED"
    assert out["reason"] == "EXCEPTION_BRANCH_OUTSIDE_CERTIFIED_TYPED_CONDITION_GRAMMAR"


def test_wrong_context_digest_fails_closed():
    text = "Apply Rule A unless exception_holds is true."
    ctx, _ = context(exception_holds={"type": "BOOL", "value": True})
    out = evaluate_unless_condition(
        text, source_id="s", typed_context=ctx, expected_typed_context_sha256="0" * 64
    )
    assert out["status"] == "FAIL_CLOSED"
    assert "TYPED_CONTEXT_CONTENT_ADDRESS_MISMATCH" in out["errors"]
