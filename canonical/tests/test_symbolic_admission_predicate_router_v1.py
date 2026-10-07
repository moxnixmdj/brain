import importlib.util
from pathlib import Path

P=Path(__file__).resolve().parents[1]/"runtime"/"symbolic_admission_predicate_router_v1.py"
spec=importlib.util.spec_from_file_location("symbolic_router",P)
m=importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(m)

SHA40="a"*40

def _route(predicate):
    digest=m.predicate_sha256(predicate)
    return {
        "route_id":"R1",
        "admission_predicate_id":"A1",
        "scope_id":"S",
        "predicate":predicate,
        "predicate_sha256":digest,
        "adequacy_certificate_blob_sha":SHA40,
        "admission_soundness_receipt_blob_sha":"b"*40,
        "admission_soundness_receipt":{
            "independent_verified":True,
            "exact_byte_bound":True,
            "conclusion":"success",
            "admission_implies_route_adequacy":True,
            "route_id":"R1",
            "scope_id":"S",
            "admission_predicate_id":"A1",
            "predicate_sha256":digest,
            "adequacy_certificate_blob_sha":SHA40,
        },
    }

def test_symbolic_region_matches_nested_context():
    pred={"op":"AND","args":[
        {"op":"EQ","path":"event.kind","value":"ACTION"},
        {"op":"IN","path":"tool","values":["browser","api"]},
    ]}
    out=m.route_context({"scope_id":"S","routes":[_route(pred)]},{"event":{"kind":"ACTION"},"tool":"api"})
    assert out["pass"] is True
    assert out["matched_route_ids"]==["R1"]
    assert out["u_empty_authorized"] is False

def test_unknown_operator_fails_closed():
    r=_route({"op":"TRUE"})
    r["predicate"]={"op":"EXEC","code":"return True"}
    out=m.route_context({"scope_id":"S","routes":[r]}, {})
    assert out["pass"] is False
    assert out["reason"]=="PREDICATE_INVALID"

def test_digest_mismatch_fails_closed():
    r=_route({"op":"TRUE"})
    r["predicate_sha256"]="0"*64
    out=m.route_context({"scope_id":"S","routes":[r]}, {})
    assert out["pass"] is False
    assert out["reason"]=="PREDICATE_DIGEST_MISMATCH"

def test_true_predicate_does_not_self_authorize_global_cover():
    out=m.route_context({"scope_id":"S","routes":[_route({"op":"TRUE"})]}, {})
    assert out["pass"] is True and out["matched"] is True
    assert out["selected_cover_complete"] is False
    assert out["terminal_authority"] is False

def test_missing_path_is_false_not_exception():
    assert m.evaluate_predicate({"op":"EQ","path":"missing.x","value":1},{"x":1}) is False
