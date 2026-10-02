import copy,json
from pathlib import Path
from canonical.runtime.opus55_prebeacon_acceptance_authority_reconciliation_v1 import evaluate

FILES={
 "protocols":"canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json",
 "registry":"canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json",
 "policy":"canonical/governance/TERMINAL_FAMILY_ADJUDICATION_POLICY_V1.json",
 "pre":"canonical/verification/TERMINAL_FAMILY_ADJUDICATION_V1_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json",
 "dom":"canonical/governance/GLOBAL_TERMINAL_SURFACE_DOMINANCE_INPUT_V6.json",
 "domr":"canonical/verification/GLOBAL_TERMINAL_SURFACE_DOMINANCE_V6_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json",
 "post":"canonical/verification/TERMINAL_V3_POSTWAVE_CONTRACT_AND_FAMILY_REDUCTION_20261002_V1.json",
 "global":"canonical/verification/GLOBAL_OWNERSHIP_POSTCONDITIONS_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json",
}
def load():
    return {k:json.loads(Path(p).read_text()) for k,p in FILES.items()}
def run(d):
    return evaluate(d["protocols"],d["registry"],d["policy"],d["pre"],d["dom"],d["domr"],d["post"],d["global"])

def test_live_exact_evidence_closes_effective_acceptance():
    out=run(load())
    assert out["pass"] is True,out
    assert out["effective_acceptance_closed_count"]==19
    assert out["effective_acceptance_open_count"]==0
    assert out["score_inheritance"] is False
    assert out["terminal_replay_required"] is False

def test_postresult_dominance_is_not_accepted():
    d=load()
    d["pre"]["terminal_results_observed"]=1
    out=run(d)
    assert out["pass"] is False
    assert any("PREBEACON" in x or "ZERO_RESULT" in x for x in out["errors"])

def test_uncovered_replacement_fails_closed():
    d=load()
    target="TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001"
    for r in d["dom"]["routes"]:
        if target in r.get("covers",[]) and r.get("zero_cost") is True and r.get("executable") is True:
            r["blocked"]=True
    out=run(d)
    assert out["pass"] is False
    assert any(x.startswith("DOMINANCE_REPLACEMENT_UNCOVERED:") for x in out["errors"])

def test_missing_terminal_contract_pass_fails_family():
    d=load()
    bid=d["post"]["contract_verdict"]["passed_contracts"][0]
    d["post"]["contract_verdict"]["passed_contracts"].remove(bid)
    d["post"]["contract_verdict"]["contract_pass_count"]=11
    out=run(d)
    assert out["pass"] is False
    assert "POSTWAVE_CONTRACT_VERDICT_NOT_12_OF_12" in out["errors"]

def test_global_postconditions_must_remain_closed():
    d=load()
    d["global"]["result"]["counters"]["donor_dependent_required_behaviors"]=1
    out=run(d)
    assert out["pass"] is False
    assert "GLOBAL_POSTCONDITION_COUNTERS_NOT_ZERO" in out["errors"]
