from canonical.runtime.c_acceptance_ledger_transport_gate_v1 import verify_claims

def direct(pid):
    return {"predicate_id":pid,"state":"PROVED","proof_kind":"UNIVERSAL","scope_complete":True,"independent_or_objective":True}

def cert(ok=True):
    return {
      "implementation_content_addressed":True,
      "load_bearing_state_quotient_complete":True,
      "target_evaluator_pullbacks_complete":ok,
      "hard_constraint_preimages_complete":True,
      "independent_or_objective_verified":True,
    }

def test_direct_current_style_claim_passes_without_transport_cert():
    out=verify_claims([direct("A")])
    assert out["pass"] is True
    assert out["direct_count"]==1 and out["transported_count"]==0

def test_unknown_new_proof_kind_fails_closed():
    row=direct("B"); row["proof_kind"]="MAGIC_NEW_KIND"
    out=verify_claims([row])
    assert out["pass"] is False
    assert any("UNKNOWN_PROOF_KIND" in e for e in out["errors"])

def test_transport_requires_explicit_parent_and_complete_c_cert():
    a=direct("A")
    b={"predicate_id":"B","state":"PROVED","proof_kind":"TRANSFER_FROM_A","scope_complete":True,"independent_or_objective":True,"c_route_kind":"TRANSPORT","c_parent_predicate_id":"A","c_transform_certificate":cert(False)}
    assert verify_claims([a,b])["pass"] is False
    b["c_transform_certificate"]=cert(True)
    out=verify_claims([a,b])
    assert out["pass"] is True
    assert out["transported_count"]==1

def test_transport_parent_must_already_be_proved_in_same_ledger():
    b={"predicate_id":"B","state":"PROVED","proof_kind":"TRANSFER_FROM_A","scope_complete":True,"independent_or_objective":True,"c_route_kind":"TRANSPORT","c_parent_predicate_id":"A","c_transform_certificate":cert(True)}
    assert verify_claims([b])["pass"] is False
