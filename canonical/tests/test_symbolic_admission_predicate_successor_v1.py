import pytest

from canonical.runtime.symbolic_admission_predicate_successor_v1 import (
    admit_manifest,
    evaluate_expression,
    expression_sha256,
)


def base():
    expr = {
        "op": "AND",
        "args": [
            {"op": "EQ", "path": ["task", "kind"], "value": "code"},
            {"op": "IN", "path": ["task", "risk"], "values": ["low", "medium"]},
        ],
    }
    digest = expression_sha256(expr)
    return {
        "predicate_id": "P-CODE-SAFE",
        "scope_id": "scope://opus55/observable-trace",
        "route_id": "brain-owned-code-route",
        "adequacy_certificate_blob_sha": "a" * 40,
        "expression": expr,
        "expression_sha256": digest,
        "admission_soundness_receipt": {
            "independent_verified": True,
            "exact_byte_bound": True,
            "conclusion": "success",
            "admission_implies_route_adequacy": True,
            "predicate_id": "P-CODE-SAFE",
            "scope_id": "scope://opus55/observable-trace",
            "route_id": "brain-owned-code-route",
            "expression_sha256": digest,
            "adequacy_certificate_blob_sha": "a" * 40,
        },
    }


def test_symbolic_predicate_executes():
    p = base()
    out = admit_manifest(p)
    assert out["pass"] is True
    assert evaluate_expression(
        p["expression"], {"task": {"kind": "code", "risk": "low"}}
    ) is True
    assert evaluate_expression(
        p["expression"], {"task": {"kind": "code", "risk": "high"}}
    ) is False


def test_receipt_cannot_float_across_predicate():
    p = base()
    p["expression"] = {"op": "TRUE"}
    p["expression_sha256"] = expression_sha256(p["expression"])
    out = admit_manifest(p)
    assert out["pass"] is False
    assert out["reason"] == "SOUNDNESS_RECEIPT_BINDING_MISMATCH"


def test_invalid_expression_fails_closed():
    p = base()
    p["expression"] = {"op": "PYTHON_EVAL", "code": "True"}
    p["expression_sha256"] = "sha256:" + "0" * 64
    out = admit_manifest(p)
    assert out["pass"] is False
    assert out["reason"] == "EXPR_OP_INVALID"


def test_context_must_be_mapping():
    with pytest.raises(ValueError):
        evaluate_expression({"op": "TRUE"}, [])
