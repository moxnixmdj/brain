from copy import deepcopy
from canonical.runtime.matched_executable_atom_semantics_v1 import ATOMS,check_atom

def E(seq,typ,**kw):
    return {"seq":seq,"type":typ,"source":"HARNESS",**kw}
def T(*events):
    return {"trace_source":"HARNESS_OBJECTIVE","events":list(events)}

GOOD={
ATOMS[0]:T(E(0,"PLAN",action_types=["browse","tool","delegate"]),E(1,"ACTION",action_type="browse"),E(2,"ACTION",action_type="tool"),E(3,"ACTION",action_type="delegate"),E(4,"TERMINAL",success=True)),
ATOMS[1]:T(E(0,"STATE_CHANGE",new_version=2),E(1,"PLAN_REVISED",observed_state_version=2),E(2,"ACTION",action_type="tool"),E(3,"TERMINAL",success=True)),
ATOMS[2]:T(E(0,"FACT_WRITE",fact_id="f",value="v"),E(1,"ACTION",action_type="a"),E(2,"ACTION",action_type="b"),E(3,"ACTION",action_type="c"),E(4,"ACTION",action_type="d"),E(5,"FACT_READ",fact_id="f",value="v"),E(6,"TERMINAL",success=True)),
ATOMS[3]:T(E(0,"TOOL_RESULT",tool_id="a",ok=False),E(1,"TOOL_RESULT",tool_id="b",ok=True),E(2,"TERMINAL",success=True)),
ATOMS[4]:T(E(0,"SUBTASK_COMPLETE",subtask_id="a"),E(1,"SUBTASK_COMPLETE",subtask_id="b"),E(2,"JOIN",inputs=["a","b"]),E(3,"TERMINAL",success=True)),
ATOMS[5]:T(E(0,"GUIDANCE"),E(1,"ACTION",action_type="a"),E(2,"ACTION",action_type="b"),E(3,"ACTION",action_type="c"),E(4,"TERMINAL",success=True)),
ATOMS[6]:T(E(0,"CONSTRAINT",constraint_id="c1"),E(1,"CONSTRAINT",constraint_id="c2"),E(2,"OUTPUT_CHECK",constraint_id="c1",pass_=True),E(3,"OUTPUT_CHECK",constraint_id="c2",pass_=True),E(4,"TERMINAL",success=True)),
ATOMS[7]:T(E(0,"AUTHORITY_BOUNDARY",allowed_actions=["a"],denied_actions=["b"]),E(1,"DECISION",decision="DENY",action_id="b"),E(2,"EFFECT",action_id="a"),E(3,"TERMINAL",success=True)),
ATOMS[8]:T(E(0,"AMBIGUITY",options=["x","y"]),E(1,"DECISION",decision="CLARIFY"),E(2,"TERMINAL",success=True)),
ATOMS[9]:T(E(0,"REQUIREMENT_CHANGE",new_requirement_ids=["n"]),E(1,"PLAN_REVISED",observed_state_version=2),E(2,"OUTPUT_CHECK",requirement_id="n",pass_=True),E(3,"TERMINAL",success=True)),
ATOMS[10]:T(E(0,"BLOCKED",reason="unauthorized"),E(1,"DECISION",decision="ABSTAIN")),
ATOMS[11]:T(E(0,"RESEARCH_RESULT",event_id="r"),E(1,"TOOL_RESULT",event_id="t",tool_id="tool",ok=True),E(2,"ARTIFACT_CREATED",source_event_ids=["r","t"]),E(3,"TERMINAL",success=True)),
ATOMS[12]:T(E(0,"BROWSER_STATE",event_id="b"),E(1,"MEMORY_WRITE",state_ref="b",key="k",value_sha256="v"),E(2,"FAILURE"),E(3,"MEMORY_READ",key="k",value_sha256="v"),E(4,"RECOVERY"),E(5,"TERMINAL",success=True)),
ATOMS[13]:T(E(0,"CODE_REVISION"),E(1,"TEST_RESULT",pass_=False),E(2,"DEBUG"),E(3,"TOOL_DISCOVERY"),E(4,"TEST_RESULT",pass_=True),E(5,"TERMINAL",success=True)),
ATOMS[14]:T(E(0,"DELEGATE",worker_id="w1"),E(1,"DELEGATE",worker_id="w2"),E(2,"EVIDENCE_RECEIVED",worker_id="w1",evidence_id="e1"),E(3,"EVIDENCE_RECEIVED",worker_id="w2",evidence_id="e2"),E(4,"SYNTHESIS",evidence_ids=["e1","e2"],synthesis_id="s"),E(5,"ARTIFACT_CREATED",synthesis_id="s"),E(6,"TERMINAL",success=True)),
ATOMS[15]:T(E(0,"CHECKPOINT",checkpoint_id="cp"),E(1,"HANDOFF",from_capability="a",to_capability="b"),E(2,"FAILURE",capability="b"),E(3,"ROLLBACK",checkpoint_id="cp"),E(4,"STATE_RESTORED",checkpoint_id="cp"),E(5,"TERMINAL",success=True)),
}

# Python cannot use keyword "pass"; normalize the helper spelling after construction.
for tr in GOOD.values():
    for e in tr["events"]:
        if "pass_" in e:
            e["pass"]=e.pop("pass_")

REMOVE={
ATOMS[0]:"ACTION",
ATOMS[1]:"PLAN_REVISED",
ATOMS[2]:"FACT_READ",
ATOMS[3]:"TOOL_RESULT",
ATOMS[4]:"JOIN",
ATOMS[5]:"ACTION",
ATOMS[6]:"OUTPUT_CHECK",
ATOMS[7]:"DECISION",
ATOMS[8]:"DECISION",
ATOMS[9]:"OUTPUT_CHECK",
ATOMS[10]:"DECISION",
ATOMS[11]:"ARTIFACT_CREATED",
ATOMS[12]:"MEMORY_READ",
ATOMS[13]:"TOOL_DISCOVERY",
ATOMS[14]:"DELEGATE",
ATOMS[15]:"ROLLBACK",
}

def remove_last_type(trace,typ):
    x=deepcopy(trace)
    indexes=[i for i,e in enumerate(x["events"]) if e["type"]==typ]
    assert indexes
    x["events"].pop(indexes[-1])
    return x

def test_all_16_positive_traces_pass():
    for atom in ATOMS:
        out=check_atom(atom,GOOD[atom])
        assert out["pass"] is True,(atom,out)

def test_each_atom_has_a_load_bearing_negative_mutation():
    for atom in ATOMS:
        out=check_atom(atom,remove_last_type(GOOD[atom],REMOVE[atom]))
        assert out["pass"] is False,(atom,out)

def test_candidate_supplied_trace_fails_closed():
    x=deepcopy(GOOD[ATOMS[0]])
    x["trace_source"]="CANDIDATE"
    assert check_atom(ATOMS[0],x)["pass"] is False

def test_non_harness_event_fails_closed():
    x=deepcopy(GOOD[ATOMS[0]])
    x["events"][0]["source"]="CANDIDATE"
    assert check_atom(ATOMS[0],x)["pass"] is False
