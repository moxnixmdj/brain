from canonical.runtime.terminal_root_decision_gate_v1 import evaluate

B = {"path": "canonical/verification/PROOF.json", "git_blob_sha": "0" * 40}
SCOPE = "scope://opus55/observable-trace"

def receipt(kind):
    return {
        "proof_kind": kind,
        "independent_verified": True,
        "exact_byte_bound": True,
        "conclusion": "success",
        "proof_artifact": B,
        "verifier_receipt_artifact": B,
        "scope_id": SCOPE,
    }

def test_full_scope_db_cover_closes_abc_only():
    r = receipt("FULL_SCOPE_DB_COVER")
    r["s_trace_subset_db"] = True
    out = evaluate({"closure_receipt": r})
    assert out["pass"] is True
    assert out["x"] is False
    assert out["u_empty"] is True
    assert out["abc_closed"] is True
    assert out["d_finality_required"] is True
    assert out["terminal"] is False

def test_target_escape_nonoccupancy_closes_abc_only():
    r = receipt("TARGET_ESCAPE_NONOCCUPANCY")
    r["u_intersection_escape_empty"] = True
    out = evaluate({"closure_receipt": r})
    assert out["pass"] is True
    assert out["proof_rule"] == "DIRECT_TARGET_ESCAPE_NONOCCUPANCY"

def test_generator_closure_requires_all_load_bearing_premises():
    r = receipt("GENERATOR_CLOSURE_SCOPE_COMPLETE")
    r.update({
        "generator_basis_complete": True,
        "all_generators_covered": True,
        "all_transforms_abc_preserving": True,
        "all_useful_contexts_reachable": True,
    })
    assert evaluate({"closure_receipt": r})["pass"] is True
    r["all_transforms_abc_preserving"] = False
    out = evaluate({"closure_receipt": r})
    assert out["pass"] is False
    assert out["reason"] == "GENERATOR_CLOSURE_PREMISES_UNPROVED"

def test_selected_cover_requires_sound_union_and_unsat_complement():
    r = receipt("SELECTED_COVER_COMPLEMENT_UNSAT")
    r["every_admission_sound"] = True
    r["residual_complement_unsat"] = True
    assert evaluate({"closure_receipt": r})["pass"] is True
    r["residual_complement_unsat"] = False
    out = evaluate({"closure_receipt": r})
    assert out["pass"] is False
    assert out["reason"] == "SELECTED_COVER_COMPLEMENT_PREMISES_UNPROVED"

def test_self_certified_or_unbound_receipt_is_rejected():
    r = receipt("FULL_SCOPE_DB_COVER")
    r["s_trace_subset_db"] = True
    r["independent_verified"] = False
    assert evaluate({"closure_receipt": r})["reason"] == "INDEPENDENT_VERIFICATION_REQUIRED"
    r["independent_verified"] = True
    r["proof_artifact"] = {"path": "x", "git_blob_sha": "bad"}
    assert evaluate({"closure_receipt": r})["reason"] == "CONTENT_ADDRESSED_PROOF_AND_VERIFIER_REQUIRED"
