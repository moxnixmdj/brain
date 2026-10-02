from canonical.runtime.postwave_global_ownership_reducer_v1 import evaluate

def _family(fid, status="PROVISIONAL_TERMINAL_BEHAVIORAL_PASS__GLOBAL_OWNERSHIP_POSTCONDITIONS_PENDING"):
    return {
        "id": fid,
        "closure_state": "PASS",
        "ownership_status": status,
        "unresolved": ["GLOBAL_OWNERSHIP_POSTCONDITIONS_PENDING"] if status != "VERIFIED_OWNED_EQUAL_OR_BETTER" else [],
    }

def test_provisional_behavior_does_not_equal_ownership():
    families = [_family(f"F{i}") for i in range(19)]
    closure = {"families": families}
    matrix = {"rows": [{"family": f"F{i}", "status": "EXTERNAL_CAPABILITY_SPECIMEN_FOUND"} for i in range(19)]}
    out = evaluate(closure, matrix)
    assert out["status"] == "FAIL_CLOSED"
    assert out["counts"]["donor_independence_pending"] == 19

def test_all_owned_still_requires_explicit_global_receipts():
    families = [_family(f"F{i}", "VERIFIED_OWNED_EQUAL_OR_BETTER") for i in range(19)]
    closure = {"families": families}
    matrix = {"rows": [{"family": f"F{i}", "status": "VERIFIED_OWNED_EQUAL_OR_BETTER"} for i in range(19)]}
    out = evaluate(closure, matrix)
    assert out["status"] == "FAIL_CLOSED"
    assert out["counts"]["donor_independence_pending"] == 0
    assert out["counts"]["verifier_mutation_closure_pending"] == 19

def test_full_explicit_receipts_close():
    families = [_family(f"F{i}", "VERIFIED_OWNED_EQUAL_OR_BETTER") for i in range(19)]
    closure = {
        "families": families,
        "global_ownership_postconditions": {
            "verifier_mutation_closure": {"status": "INDEPENDENT_PASS", "evidence": "v"},
            "composition_closure": {"status": "INDEPENDENT_PASS", "evidence": "c"},
            "final_donor_deletion_cleanroom": {"status": "INDEPENDENT_PASS", "evidence": "d"},
            "proof_bundle_freeze": {"status": "INDEPENDENT_PASS", "evidence": "p"},
        },
    }
    matrix = {"rows": [{"family": f"F{i}", "status": "VERIFIED_OWNED_EQUAL_OR_BETTER"} for i in range(19)]}
    out = evaluate(closure, matrix)
    assert out["status"] == "PASS"
    assert out["achieved"] is True
