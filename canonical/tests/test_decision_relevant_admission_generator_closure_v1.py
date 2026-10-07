from canonical.runtime.decision_relevant_admission_generator_closure_v1 import evaluate

R = {"path": "canonical/verification/PROOF.json", "git_blob_sha": "0" * 40}

def base_problem():
    return {
        "trace_scope": {"proved": True, "proof_receipts": [R]},
        "generators": [
            {
                "generator_id": "G0",
                "coverage_mode": "POSITIVE_COVER",
                "scope_complete": True,
                "covered": True,
                "proof_receipts": [R],
            },
            {
                "generator_id": "G1",
                "coverage_mode": "COMPLETE_OBJECTIVE",
                "scope_complete": True,
                "covered": True,
                "proof_receipts": [R],
            },
        ],
        "transforms": [
            {
                "transform_id": "T0",
                "admission_preserving": True,
                "load_bearing_order_preserving": True,
                "hard_constraint_preserving": True,
                "resource_safety_preserving": True,
                "authority_preserving": True,
                "proof_receipts": [R],
            }
        ],
        "generator_closure": {
            "complete": True,
            "all_useful_contexts_reachable": True,
            "proof_receipts": [R],
        },
    }

def test_all_premises_close_abc_but_not_d_or_terminal():
    out = evaluate(base_problem())
    assert out["pass"] is True
    assert out["abc_closed"] is True
    assert out["u_empty"] is True
    assert out["d_finality_required"] is True
    assert out["terminal"] is False

def test_generator_completeness_is_load_bearing():
    p = base_problem()
    p["generator_closure"]["complete"] = False
    out = evaluate(p)
    assert out["pass"] is False
    assert out["reason"] == "GENERATOR_COMPLETENESS_UNPROVED"
    assert out["u_empty"] is False

def test_uncovered_generator_blocks_induction():
    p = base_problem()
    p["generators"][0]["covered"] = False
    out = evaluate(p)
    assert out["pass"] is False
    assert out["reason"] == "GENERATOR_COVERAGE_UNPROVED:G0"

def test_nonpreserving_transform_blocks_induction():
    p = base_problem()
    p["transforms"][0]["hard_constraint_preserving"] = False
    out = evaluate(p)
    assert out["pass"] is False
    assert out["reason"] == "TRANSFORM_HARD_CONSTRAINT_PRESERVING_UNPROVED:T0"

def test_scope_superset_requires_content_addressed_receipt():
    p = base_problem()
    p["trace_scope"]["proof_receipts"] = [{"path": "x", "git_blob_sha": "bad"}]
    out = evaluate(p)
    assert out["pass"] is False
    assert out["reason"] == "TRACE_SCOPE_SUPERSET_UNPROVED"

def test_generator_receipt_is_mandatory():
    p = base_problem()
    p["generators"][1]["proof_receipts"] = []
    out = evaluate(p)
    assert out["pass"] is False
    assert out["reason"] == "GENERATOR_PROOF_RECEIPTS_INVALID:G1"
