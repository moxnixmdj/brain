from copy import deepcopy
from canonical.runtime import root3_synthesis_scope_reconciliation_verifier_v1 as v

def test_current_reconciliation_passes():
    out=v.evaluate()
    assert out["pass"] is True,out
    assert out["root2_involved_count"]==19
    assert out["root3_involved_count"]==10
    assert out["unresolved_atomic"]==26
    assert out["acceptance_credit_delta"]==0
    assert out["fresh_reality_authority"] is False

def test_synthesis_mixed_regression_fails(monkeypatch):
    orig=v.load
    def fake(p):
        x=deepcopy(orig(p))
        if p=="canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json":
            part=x["current_residual_root_partition"]
            part["root2_only"]=[i for i in part["root2_only"] if i!=v.PID]
            part["root2_and_root3"].append(v.PID)
            part["root2_only_count"]=15
            part["root2_and_root3_count"]=4
        return x
    monkeypatch.setattr(v,"load",fake)
    out=v.evaluate()
    assert out["pass"] is False
    assert "ROOT_COUNTS" in out["errors"] or "SYNTHESIS_CLASS" in out["errors"]

def test_acceptance_truth_regression_fails(monkeypatch):
    orig=v.load
    def fake(p):
        x=deepcopy(orig(p))
        if p=="canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json":
            x["truth"]["opus55_acceptance"]="6/19_PASS__13/19_OPEN"
        return x
    monkeypatch.setattr(v,"load",fake)
    out=v.evaluate()
    assert out["pass"] is False
    assert "TERMINAL_TRUTH_DRIFT" in out["errors"]

def test_stale_frontier_pointer_fails(monkeypatch):
    orig=v.load
    def fake(p):
        x=deepcopy(orig(p))
        if p=="canonical/governance/ROOT2_ROOT3_MINIMUM_EXECUTION_FRONTIER_V1.json":
            x["authority"]["root_state"]["git_blob_sha"]="deadbeef"
        return x
    monkeypatch.setattr(v,"load",fake)
    out=v.evaluate()
    assert out["pass"] is False
    assert "FRONTIER_ROOT_POINTER" in out["errors"]
