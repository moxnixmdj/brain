from canonical.runtime.symbolic_positive_admission_route_router_v1 import (
    PredicateRoute, PredicateRouterError, context_sha256, select
)

def pred(pid,cell,key,value):
    def f(ctx):
        return {
            "admitted":ctx.get(key)==value,
            "cell_id":cell,
            "admission_predicate_id":pid,
            "context_sha256":context_sha256(ctx),
        }
    return f

def route(cell,rid,pid,ch,key,value):
    return PredicateRoute(
        cell_id=cell,route_id=rid,admission_predicate_id=pid,
        admission_predicate_blob_sha=ch*40,
        route_blob_sha=("b" if ch!="b" else "c")*40,
        adequacy_certificate_blob_sha=("d" if ch!="d" else "e")*40,
        admission_soundness_receipt_blob_sha=("f" if ch!="f" else "a")*40,
        admission_soundness_verified=True,
        predicate=pred(pid,cell,key,value),
    )

def test_symbolic_region_matches_many_contexts_without_digest_enumeration():
    r=route("pdf-cell","pdf-route","is-pdf","1","kind","pdf")
    a=select({"kind":"pdf","task":"A"},[r])
    b=select({"kind":"pdf","task":"B"},[r])
    assert a["pass"] is True and b["pass"] is True
    assert a["context_sha256"]!=b["context_sha256"]
    assert a["selected_route"]["route_id"]=="pdf-route"
    assert b["selected_route"]["route_id"]=="pdf-route"

def test_uncovered_context_becomes_explicit_residual_escape():
    r=route("pdf-cell","pdf-route","is-pdf","1","kind","pdf")
    out=select({"kind":"docx"},[r])
    assert out["pass"] is False
    assert out["residual_escape"] is True
    assert out["status"]=="RESIDUAL_ESCAPE__NO_SOUND_ADMISSION_PREDICATE_MATCHED"

def test_overlap_is_safe_and_deterministic():
    a=route("any-doc","r2","p2","2","kind","pdf")
    b=route("pdf","r1","p1","1","kind","pdf")
    x=select({"kind":"pdf"},[a,b])
    y=select({"kind":"pdf"},[b,a])
    assert x["selected_route"]==y["selected_route"]

def test_predicate_cannot_attest_wrong_context_digest():
    def bad(ctx):
        return {"admitted":True,"cell_id":"c","admission_predicate_id":"p","context_sha256":"sha256:bad"}
    r=PredicateRoute("c","r","p","1"*40,"2"*40,"3"*40,"4"*40,True,bad)
    try:
        select({"x":1},[r])
        assert False
    except PredicateRouterError as exc:
        assert str(exc)=="PREDICATE_CONTEXT_DIGEST_MISMATCH:r"

def test_unverified_admission_soundness_is_rejected():
    r=PredicateRoute("c","r","p","1"*40,"2"*40,"3"*40,"4"*40,False,pred("p","c","x",1))
    try:
        select({"x":1},[r])
        assert False
    except PredicateRouterError as exc:
        assert str(exc)=="ADMISSION_SOUNDNESS_NOT_VERIFIED:r"
