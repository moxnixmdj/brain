import json
from pathlib import Path

from canonical.runtime.proof_carrying_scope_cover_v2 import evaluate

ROOT=Path(__file__).resolve().parents[2]
SCOPE=ROOT/"canonical/governance/CURSORBENCH_4_0_SCOPE_COMPLETENESS_RECEIPT_V2.json"
REL=ROOT/"canonical/governance/CURSORBENCH_4_0_TARGET_TO_TRACE_SCOPE_RELATION_RECEIPT_20261009_V1.json"
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

def base():
    scope=json.loads(SCOPE.read_text(encoding="utf-8"))
    target=scope["scope_id"]
    return {
        "benchmark_id":"CURSORBENCH_4_0",
        "predicate_id":"CODING_CURSORBENCH_GE_57_8",
        "scope_completeness":scope,
        "cover_completeness":receipt(covers_entire_scope=True,scope_id=target),
        "cells":[{
            "cell_id":"TEST_EXACT_TARGET_CELL",
            "scope_relation":"EXACT",
            "target_scope_id":target,
            "cell_scope_id":target,
            "policy_id":"TEST_ONLY_POLICY",
            "brain_owned_policy":True,
            "deployable":True,
            "resource_admissible":True,
            "external_target_capability_provider":False,
            "adequacy_certificate":receipt(adequate_for_entire_cell=True),
        }],
    }

def test_corrected_target_scope_exact_cover_is_structurally_accepted():
    out=evaluate(base())
    assert out["pass"] is True, out
    assert out["scope_id"]=="scope://cursorbench-4.0/actual-score-relevant-scope"

def test_old_superdomain_id_cannot_pose_as_exact_target_cover():
    p=base()
    p["cover_completeness"]["scope_id"]="scope://cursorbench-4.0/observable-trace-superdomain"
    out=evaluate(p)
    assert out["pass"] is False
    assert "COVER_SCOPE_ID_MISMATCH" in out["errors"]

def test_real_trace_relation_can_support_explicit_stronger_cell():
    p=base()
    relation=json.loads(REL.read_text(encoding="utf-8"))
    p["cells"][0].update({
        "cell_id":"TEST_TRACE_STRONGER_CELL",
        "scope_relation":"PROVEN_STRONGER",
        "cell_scope_id":relation["stronger_scope_id"],
        "scope_relation_receipt":relation,
    })
    out=evaluate(p)
    assert out["pass"] is True, out

def test_scope_receipt_does_not_equate_target_and_witness():
    scope=json.loads(SCOPE.read_text(encoding="utf-8"))
    assert scope["target_scope_equals_witness_superdomain"] is False
    assert scope["scope_id"] != scope["scope_witness"]["stronger_scope_id"]

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
