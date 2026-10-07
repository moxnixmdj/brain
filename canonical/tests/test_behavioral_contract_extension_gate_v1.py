import json
from pathlib import Path

from canonical.runtime.behavioral_contract_extension_gate_v1 import (
    compile_extensions, verify_abc_extension_admission
)

ROOT=Path(__file__).resolve().parents[2]
REG=ROOT/"canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V2.json"

def contracts():
    return json.loads(REG.read_text())["active_contracted_residuals"]

def by_id(bid):
    return next(x for x in contracts() if x["behavior_id"]==bid)

def test_all_current_registry_extensions_classify():
    outs=[compile_extensions(x) for x in contracts()]
    assert all(x["pass"] for x in outs), outs

def test_unknown_future_extension_fails_closed():
    x=dict(contracts()[0])
    x["mystery_extension"]={"x":1}
    out=compile_extensions(x)
    assert out["pass"] is False
    assert any(e=="UNCLASSIFIED_EXTENSION_FIELD:mystery_extension" for e in out["errors"])

def test_saccr_remaining_scope_is_abc_membership_boundary():
    out=compile_extensions(by_id("SA_CCR_CREDIT_EFFECTIVE_NOTIONAL_AND_ADDON_001"))
    rows={x["field"]:x for x in out["extensions"]}
    assert rows["remaining_scope"]["role"]=="ABC_MEMBERSHIP_BOUNDARY"
    assert rows["remaining_scope"]["abc_load_bearing"] is True
    for f in ("mechanism_state","mechanism_artifact","mechanism_evidence"):
        assert rows[f]["abc_load_bearing"] is False

def test_saccr_remaining_scope_must_be_admitted():
    c=by_id("SA_CCR_CREDIT_EFFECTIVE_NOTIONAL_AND_ADDON_001")
    compiled=compile_extensions(c)
    out=verify_abc_extension_admission(c,[])
    assert out["pass"] is False
    assert out["errors"]
    out2=verify_abc_extension_admission(c,compiled["abc_extension_atom_ids"])
    assert out2["pass"] is True

def test_delegation_terminal_acceptance_is_promotion_metadata_not_abc():
    out=compile_extensions(by_id("TASK_TO_DELEGATION_GRAPH_001"))
    rows={x["field"]:x for x in out["extensions"]}
    assert rows["terminal_acceptance"]["role"]=="PROMOTION_EVIDENCE_AUTHORITY"
    assert rows["terminal_acceptance"]["abc_load_bearing"] is False
