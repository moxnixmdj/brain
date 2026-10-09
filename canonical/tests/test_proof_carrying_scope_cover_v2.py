from canonical.runtime.proof_carrying_scope_cover_v1 import evaluate as evaluate_v1
from canonical.runtime.proof_carrying_scope_cover_v2 import evaluate as evaluate_v2

SHA="1"*40

def receipt(**extra):
    out={
        "verified":True,
        "independent":True,
        "source_path":"canonical/verification/test.json",
        "source_sha":SHA,
    }
    out.update(extra)
    return out

def payload(*, scope_id="scope://cursorbench-4.0/target", cover_scope_id=None, relation="EXACT"):
    cover_scope_id=scope_id if cover_scope_id is None else cover_scope_id
    cell={
        "cell_id":"C1",
        "scope_relation":relation,
        "target_scope_id":scope_id,
        "cell_scope_id":scope_id,
        "policy_id":"P1",
        "brain_owned_policy":True,
        "deployable":True,
        "resource_admissible":True,
        "external_target_capability_provider":False,
        "adequacy_certificate":receipt(adequate_for_entire_cell=True),
    }
    return {
        "benchmark_id":"CURSORBENCH_4_0",
        "predicate_id":"CODING_CURSORBENCH_GE_57_8",
        "scope_completeness":receipt(
            basis="UNIVERSAL_FORMAL_SCOPE_PROOF",
            all_admissible_target_inputs_proved=True,
            formal_completeness=True,
            scope_id=scope_id,
        ),
        "cover_completeness":receipt(
            covers_entire_scope=True,
            scope_id=cover_scope_id,
        ),
        "cells":[cell],
    }

def test_v1_accepts_mismatched_cover_scope_counterexample():
    p=payload(cover_scope_id="scope://unrelated")
    out=evaluate_v1(p)
    assert out["pass"] is True, out

def test_v2_rejects_mismatched_cover_scope():
    p=payload(cover_scope_id="scope://unrelated")
    out=evaluate_v2(p)
    assert out["pass"] is False
    assert "COVER_SCOPE_ID_MISMATCH" in out["errors"]

def test_v2_accepts_exact_scope_binding():
    out=evaluate_v2(payload())
    assert out["pass"] is True, out
    assert out["scope_id"]==out["cover_scope_id"]

def test_v2_rejects_exact_cell_bound_to_other_scope():
    p=payload()
    p["cells"][0]["cell_scope_id"]="scope://other"
    out=evaluate_v2(p)
    assert out["pass"] is False
    assert "CELL:C1:EXACT_SCOPE_ID_MISMATCH" in out["errors"]

def test_v2_requires_relation_receipt_for_stronger_cell():
    p=payload(relation="PROVEN_STRONGER")
    p["cells"][0]["cell_scope_id"]="scope://stronger"
    out=evaluate_v2(p)
    assert out["pass"] is False
    assert "CELL:C1:STRONGER_SCOPE_RELATION_RECEIPT_MISSING" in out["errors"]

def test_v2_accepts_independently_proved_stronger_cell():
    p=payload(relation="PROVEN_STRONGER")
    p["cells"][0]["cell_scope_id"]="scope://stronger"
    p["cells"][0]["scope_relation_receipt"]=receipt(
        target_scope_id=p["scope_completeness"]["scope_id"],
        stronger_scope_id="scope://stronger",
        target_subset_of_stronger_scope=True,
    )
    out=evaluate_v2(p)
    assert out["pass"] is True, out

def test_v2_rejects_stronger_receipt_for_wrong_target():
    p=payload(relation="PROVEN_STRONGER")
    p["cells"][0]["cell_scope_id"]="scope://stronger"
    p["cells"][0]["scope_relation_receipt"]=receipt(
        target_scope_id="scope://wrong",
        stronger_scope_id="scope://stronger",
        target_subset_of_stronger_scope=True,
    )
    out=evaluate_v2(p)
    assert out["pass"] is False
    assert "CELL:C1:STRONGER_RELATION_TARGET_SCOPE_MISMATCH" in out["errors"]

if __name__=="__main__":
    tests=[(n,f) for n,f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    failed=[]
    for n,f in tests:
        try:
            f()
            print("PASS",n)
        except Exception as exc:
            failed.append((n,type(exc).__name__,str(exc)))
            print("FAIL",n,type(exc).__name__,str(exc))
    print("TESTS",len(tests),"FAILED",len(failed))
    if failed:
        raise SystemExit(1)
