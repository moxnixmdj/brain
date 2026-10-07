from canonical.runtime.symbolic_admission_predicate_registry_v1 import evaluate, _sha256

B = "0" * 40

def route(pid="A1", atom="A"):
    ast = {"op": "ATOM", "id": atom}
    return {
        "cell_id": "c-" + pid,
        "route_id": "r-" + pid,
        "admission_predicate_id": pid,
        "admission_predicate_blob_sha": B,
        "adequacy_certificate_blob_sha": B,
        "admission_soundness_receipt_blob_sha": B,
        "admission_predicate_ast": ast,
        "admission_predicate_ast_sha256": _sha256(ast),
        "admission_soundness_receipt": {
            "independent_verified": True,
            "exact_byte_bound": True,
            "conclusion": "success",
            "admission_implies_route_adequacy": True,
        },
    }

def payload():
    return {
        "scope_id": "scope://opus55/observable-trace",
        "scope_predicate": {"op": "TRUE"},
        "routes": [route("A1", "A"), route("A2", "B")],
    }

def test_builds_exact_symbolic_residual_without_false_closure():
    out = evaluate(payload())
    assert out["pass"] is True
    assert out["symbolic_successor_deployed"] is True
    assert out["residual_definition"] == "S_TRACE_AND_NOT_ANY_SOUND_ADMISSION_PREDICATE"
    assert out["selected_cover_complete"] is False
    assert out["u_empty"] is False
    assert out["terminal"] is False

def test_ast_digest_mismatch_fails_closed():
    p = payload()
    p["routes"][0]["admission_predicate_ast_sha256"] = "sha256:" + "0" * 64
    out = evaluate(p)
    assert out["pass"] is False
    assert out["reason"] == "ADMISSION_PREDICATE_AST_DIGEST_MISMATCH"

def test_unsound_admission_fails_closed():
    p = payload()
    p["routes"][1]["admission_soundness_receipt"]["independent_verified"] = False
    out = evaluate(p)
    assert out["pass"] is False
    assert out["reason"] == "ADMISSION_SOUNDNESS_UNPROVED"

def test_duplicate_predicate_identity_fails_closed():
    p = payload()
    p["routes"][1]["admission_predicate_id"] = "A1"
    out = evaluate(p)
    assert out["pass"] is False
    assert out["reason"] == "ROUTE_IDENTITY_INVALID"
