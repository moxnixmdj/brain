import json, pathlib, tempfile
from canonical.runtime.effect_broker_receipt_resolver_v2 import git_blob_id
from canonical.runtime.finite_abstraction_cover_lift_v1 import verify

SCOPE="scope://lift/unit-v1"

def spec():
    return {
      "schema":"PROJECT_BRAIN_FINITE_ABSTRACTION_COVER_SPEC_V1",
      "scope_id":SCOPE,
      "concrete_variables":["x","y"],
      "concrete_scope_cnf":[],
      "abstract_predicates":[
        {"name":"X","definition_cnf":[["x"]]},
        {"name":"Y","definition_cnf":[["y"]]}
      ],
      "routes":[
        {"route_id":"x_true","admission_cnf":[["X"]],"adequacy_cnf":[["X"]]},
        {"route_id":"x_false","admission_cnf":[["!X"]],"adequacy_cnf":[["!X"]]}
      ]
    }

def run(v, expected_scope=SCOPE, stale=False):
    with tempfile.TemporaryDirectory() as td:
        root=pathlib.Path(td)
        p=root/"spec.json"
        raw=json.dumps(v,sort_keys=True,separators=(",",":")).encode()
        p.write_bytes(raw)
        sha=git_blob_id(raw,object_format="sha1")
        if stale: sha="0"*40
        return verify({"path":"spec.json","git_blob_sha":sha},
                      repo_root=root,expected_scope_id=expected_scope)

def test_total_cover_passes():
    out=run(spec())
    assert out["pass"] is True
    assert out["scoped_concrete_valuations_checked"]==4
    assert out["abstraction_total_over_declared_scope"] is True
    assert out["u_empty_authorized"] is False

def test_uncovered_returns_concrete_witness():
    p=spec(); p["routes"]=p["routes"][:1]
    out=run(p)
    assert out["reason"]=="UNCOVERED_CONCRETE_VALUATION"
    assert out["failing_concrete_valuation"]["x"] is False
    assert out["derived_abstract_valuation"]["X"] is False

def test_admitted_but_inadequate_returns_witness():
    p=spec(); p["routes"][1]["adequacy_cnf"]=[["X"]]
    out=run(p)
    assert out["reason"]=="ADMITTED_BUT_NO_ADEQUATE_ROUTE"
    assert out["failing_concrete_valuation"]["x"] is False

def test_overlap_with_one_adequate_route_is_ok():
    p=spec()
    p["routes"].insert(0,{"route_id":"bad_overlap","admission_cnf":[],"adequacy_cnf":[["X"]]})
    assert run(p)["pass"] is True

def test_scope_restriction_is_respected():
    p=spec(); p["concrete_scope_cnf"]=[["x"]]; p["routes"]=p["routes"][:1]
    out=run(p)
    assert out["pass"] is True
    assert out["scoped_concrete_valuations_checked"]==2

def test_empty_scope_fails():
    p=spec(); p["concrete_scope_cnf"]=[[]]
    assert run(p)["reason"]=="EMPTY_DECLARED_SCOPE_NOT_CREDITABLE"

def test_unknown_field_fails():
    p=spec(); p["magic"]=True
    assert run(p)["reason"]=="SPEC_FIELDS_INVALID"

def test_unknown_abstract_literal_fails():
    p=spec(); p["routes"][0]["admission_cnf"]=[["Z"]]
    assert run(p)["reason"]=="SPEC_BINDING_OR_REPLAY_INVALID"

def test_stale_blob_fails():
    assert run(spec(),stale=True)["reason"]=="SPEC_BINDING_OR_REPLAY_INVALID"

def test_scope_swap_fails():
    assert run(spec(),expected_scope="scope://other")["reason"]=="SPEC_SCOPE_MISMATCH"

def test_global_claim_field_fails_closed():
    p=spec(); p["u_empty_authorized"]=True
    assert run(p)["reason"]=="SPEC_FIELDS_INVALID"

def test_policy_changing_discriminator_example():
    p=spec()
    # Without X split, a single route claiming adequacy only on X cannot cover !X.
    p["routes"]=[{"route_id":"common","admission_cnf":[],"adequacy_cnf":[["X"]]}]
    out=run(p)
    assert out["reason"]=="ADMITTED_BUT_NO_ADEQUATE_ROUTE"
    assert out["derived_abstract_valuation"]["X"] is False
