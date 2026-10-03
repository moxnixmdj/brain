from copy import deepcopy
from canonical.runtime import synthesis_lossless_scope_decomposition_verifier_v1 as v

def test_current_candidate_passes():
    out=v.evaluate()
    assert out["pass"] is True,out
    assert out["scope_relation_eligible"] is True
    assert out["target_dimension_count"]==6
    assert out["bound_dimension_count"]==6
    assert out["acceptance_closed"] is False
    assert out["performance_credit"] is False
    assert out["fresh_reality_authority"] is False

def test_dimension_set_is_exact():
    assert len(v.TARGET)==6
    assert "compression without decision-relevant loss" in v.TARGET

def test_missing_dimension_fails(monkeypatch):
    orig=v.load
    def fake(p):
        x=deepcopy(orig(p))
        if p==v.CAND:
            x["dimension_bindings"]=x["dimension_bindings"][:-1]
        return x
    monkeypatch.setattr(v,"load",fake)
    out=v.evaluate()
    assert out["pass"] is False
    assert "BINDING_COUNT" in out["errors"] or "UNBOUND_DIMENSIONS" in out["errors"]

def test_bad_fragment_fails(monkeypatch):
    orig=v.load
    def fake(p):
        x=deepcopy(orig(p))
        if p==v.CAND:
            x["dimension_bindings"][0]["contract_witnesses"][0]["fragment"]="not present"
        return x
    monkeypatch.setattr(v,"load",fake)
    out=v.evaluate()
    assert out["pass"] is False
    assert any(e.startswith("CONTRACT_FRAGMENT_MISMATCH") for e in out["errors"])

def test_atom_transport_drift_fails(monkeypatch):
    orig=v.load
    def fake(p):
        x=deepcopy(orig(p))
        if p==v.ATOM:
            x["verified"]["transported_proved_atom_count"]=6
        return x
    monkeypatch.setattr(v,"load",fake)
    out=v.evaluate()
    assert out["pass"] is False
    assert "SEVEN_ATOM_RECEIPT_DRIFT" in out["errors"]

def test_no_acceptance_or_performance_credit():
    out=v.evaluate()
    assert out["acceptance_credit_delta"]==0
    assert out["family_credit_delta"]==0
    assert out["capability_credit_delta"]==0
    assert out["ownership_credit_delta"]==0
