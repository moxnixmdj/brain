from copy import deepcopy
from canonical.runtime import synthesis_scope_certificate_activation_verifier_v1 as v

def test_current_activation_passes():
    out=v.evaluate()
    assert out["pass"] is True,out
    assert out["after_root_class"]=="ROOT2_ONLY"
    assert out["after_root3_involved_count"]==10
    assert out["root2_involved_count"]==19
    assert out["unresolved_total"]==26
    assert out["acceptance_credit_delta"]==0
    assert out["fresh_reality_authority"] is False

def test_scope_certificate_failure_blocks_activation(monkeypatch):
    monkeypatch.setattr(v,"eval_scope",lambda cert:{"scope_complete":False,"basis":"LOSSLESS_DECOMPOSITION"})
    out=v.evaluate()
    assert out["pass"] is False
    assert "GENERIC_SCOPE_COMPILER_REJECTED" in out["errors"]

def test_wrong_current_partition_blocks_activation(monkeypatch):
    orig=v.load
    def fake(p):
        x=deepcopy(orig(p))
        if p==v.ROOTS:
            x["current_residual_root_partition"]["root2_and_root3"].remove(v.PID)
        return x
    monkeypatch.setattr(v,"load",fake)
    out=v.evaluate()
    assert out["pass"] is False
    assert "SYNTHESIS_NOT_CURRENTLY_MIXED" in out["errors"]

def test_acceptance_credit_overclaim_blocks_activation(monkeypatch):
    orig=v.load
    def fake(p):
        x=deepcopy(orig(p))
        if p==v.ACT:
            x["acceptance_credit_delta"]=1
        return x
    monkeypatch.setattr(v,"load",fake)
    out=v.evaluate()
    assert out["pass"] is False
    assert "ACCEPTANCE_CREDIT_OVERCLAIM" in out["errors"]
