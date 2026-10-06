import hashlib
import pathlib
import tempfile
from canonical.runtime import continuous_obs_runtime
from canonical.runtime.matched_agency_stateful_case_v1 import child_code,run_case,install_synthetic_continuous_obs

def test_synthetic_obs_context_passes_current_admission_validator():
    with tempfile.TemporaryDirectory() as td:
        root=pathlib.Path(td)
        context=install_synthetic_continuous_obs(root)
        out=continuous_obs_runtime.validate_context(context,root=root)
        assert out["pass"] is True,out

def test_stateful_agency_case_passes():
    token="STATEFUL-AGENCY-TEST-TOKEN"
    out=run_case(token,0)
    assert out["pass"] is True,out
    assert out["planner_plan"]==["browser","tool","delegation"]
    assert len(set(out["action_types"]))==3
    assert all(out["component_results"][k]["pass"] for k in ("browser","tool","delegation"))
    assert all(out["checks"].values())

def test_objective_trace_proves_three_target_semantics():
    token="STATEFUL-AGENCY-TRACE"
    out=run_case(token,1)
    events=out["objective_trace"]["events"]
    plan=next(x for x in events if x["type"]=="PLAN")
    actions=[x for x in events if x["type"]=="ACTION"]
    write=next(x for x in events if x["type"]=="FACT_WRITE")
    read=next(x for x in events if x["type"]=="FACT_READ")
    guidance=[x for x in events if x["type"]=="GUIDANCE"]
    assert len(set(plan["action_types"]))>=3
    assert set(plan["action_types"]) <= {x["action_type"] for x in actions}
    assert read["seq"]-write["seq"]>=5
    assert read["value"]==write["value"]==hashlib.sha256(token.encode()).hexdigest()
    first_action=min(x["seq"] for x in actions)
    assert not any(x["seq"]>first_action for x in guidance)
    assert events[-1]["type"]=="TERMINAL" and events[-1]["success"] is True

def test_case_token_is_not_embedded_in_child_program():
    token="DO-NOT-SMUGGLE-THIS-TOKEN"
    code_a=child_code("/tmp/a","/tmp/b","/tmp/c","/tmp/d",True,0)
    code_b=child_code("/tmp/a","/tmp/b","/tmp/c","/tmp/d",False,0)
    assert token not in code_a
    assert token not in code_b
