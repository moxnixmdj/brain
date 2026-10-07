from canonical.runtime.certified_defined_term_typed_condition_v1 import evaluate_defined_unless_condition
from canonical.runtime.source_aligned_semantic_proof_v3 import typed_context_sha256
from canonical.runtime.monotone_semantic_constraint_kernel_v1 import resolve_common_policy


def ctx(**fields):
    c = {"schema_id": "FINANCE_TYPED_CONTEXT_V1", "fields": fields}
    return c, typed_context_sha256(c)


def test_explicit_definition_binds_human_term_to_typed_numeric_field():
    text = (
        "Total exposure means exposure_amount. "
        "Apply Rule A unless Total exposure is at least 125.50."
    )
    c, digest = ctx(exposure_amount={"type": "DECIMAL_STRING", "value": "130.00"})
    out = evaluate_defined_unless_condition(
        text, source_id="s", typed_context=c, expected_typed_context_sha256=digest
    )
    assert out["status"] == "PROVED_TRUE", out
    assert out["defined_term"] == "Total exposure"
    assert out["field_name"] == "exposure_amount"
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
    assert resolved["certified_common_policies"] == ["exception_policy"]


def test_explicit_definition_binds_human_term_to_bool_field():
    text = (
        "Material exception means exception_holds. "
        "Apply Rule A unless Material exception is true."
    )
    c, digest = ctx(exception_holds={"type": "BOOL", "value": False})
    out = evaluate_defined_unless_condition(
        text, source_id="s", typed_context=c, expected_typed_context_sha256=digest
    )
    assert out["status"] == "PROVED_FALSE", out
    assert out["field_name"] == "exception_holds"


def test_undefined_human_term_remains_unresolved():
    text = "Apply Rule A unless Total exposure is at least 125.50."
    c, digest = ctx(exposure_amount={"type": "DECIMAL_STRING", "value": "130.00"})
    out = evaluate_defined_unless_condition(
        text, source_id="s", typed_context=c, expected_typed_context_sha256=digest
    )
    assert out["status"] == "UNRESOLVED"
    assert out["reason"] == "NO_EXPLICIT_DEFINED_TERM_BINDS_EXCEPTION_CONDITION_TO_TYPED_FIELD"


def test_definition_to_missing_field_remains_unresolved():
    text = (
        "Total exposure means exposure_amount. "
        "Apply Rule A unless Total exposure is at least 125.50."
    )
    c, digest = ctx(other={"type": "DECIMAL_STRING", "value": "130.00"})
    out = evaluate_defined_unless_condition(
        text, source_id="s", typed_context=c, expected_typed_context_sha256=digest
    )
    assert out["status"] == "UNRESOLVED"
    assert out["reason"] == "DEFINED_FIELD_NOT_PRESENT_IN_TYPED_CONTEXT"


def test_conflicting_explicit_definitions_fail_closed():
    text = (
        "Total exposure means exposure_amount. "
        "Total exposure means other_amount. "
        "Apply Rule A unless Total exposure is at least 125.50."
    )
    c, digest = ctx(
        exposure_amount={"type": "DECIMAL_STRING", "value": "130.00"},
        other_amount={"type": "DECIMAL_STRING", "value": "0.00"},
    )
    out = evaluate_defined_unless_condition(
        text, source_id="s", typed_context=c, expected_typed_context_sha256=digest
    )
    assert out["status"] == "FAIL_CLOSED"
    assert "EXPLICIT_DEFINITION_GRAPH_FAIL_CLOSED" in out["errors"]


def test_paraphrase_not_licensed_by_explicit_definition():
    text = (
        "Total exposure means exposure_amount. "
        "Apply Rule A unless Aggregate exposure is at least 125.50."
    )
    c, digest = ctx(exposure_amount={"type": "DECIMAL_STRING", "value": "130.00"})
    out = evaluate_defined_unless_condition(
        text, source_id="s", typed_context=c, expected_typed_context_sha256=digest
    )
    assert out["status"] == "UNRESOLVED"


def test_wrong_typed_context_digest_fails_closed():
    text = (
        "Material exception means exception_holds. "
        "Apply Rule A unless Material exception is true."
    )
    c, _ = ctx(exception_holds={"type": "BOOL", "value": True})
    out = evaluate_defined_unless_condition(
        text, source_id="s", typed_context=c, expected_typed_context_sha256="0" * 64
    )
    assert out["status"] == "FAIL_CLOSED"
    assert "TYPED_CONTEXT_CONTENT_ADDRESS_MISMATCH" in out["errors"]
