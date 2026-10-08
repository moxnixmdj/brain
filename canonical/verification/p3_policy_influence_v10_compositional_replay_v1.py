"""Controlled predecessor-interface replay for the V10 routing delta.

V9 itself has separate exact-byte verification. This replay isolates the new V10
composition logic while keeping the real policy-influence kernel live.
"""
import importlib.util
import pathlib
import sys
import tempfile
import types

ROOT=pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

stub=types.ModuleType("canonical.runtime.p3_real_context_v3_admission_v9")
state={"mode":"capacity"}

def eval_v9(payload, repo_root=None):
    mode=state["mode"]
    if mode=="pass":
        return {"pass":True,"route":"V9_PASS","terminal_authority":False,"terminal_credit_delta":0}
    if mode=="weights_fail":
        return {"pass":False,"reason":"OBJECTIVE_WEIGHTS_UNSATISFIED","terminal_authority":False,"terminal_credit_delta":0}
    if mode=="conflict":
        return {"pass":False,"nonbinding_capacity_reason":"CONFLICT_REQUIRES_UNCERTAINTY_SEMANTICS","terminal_authority":False,"terminal_credit_delta":0}
    return {"pass":False,"nonbinding_capacity_reason":"CAPACITY_BINDING_REQUIRES_RELEVANCE_POLICY","terminal_authority":False,"terminal_credit_delta":0}

stub.evaluate=eval_v9
sys.modules["canonical.runtime.p3_real_context_v3_admission_v9"]=stub

path=ROOT/"canonical"/"runtime"/"p3_real_context_v3_admission_v10.py"
spec=importlib.util.spec_from_file_location("canonical.runtime.p3_real_context_v3_admission_v10",path)
m=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=m
spec.loader.exec_module(m)

from canonical.tests.test_p3_policy_influence_relevance_cell_v1 import make_payload, public_case

passed=0
total=0

def check(name,fn):
    global passed,total
    total+=1
    try:
        fn()
        passed+=1
        print("PASS",name)
    except Exception as exc:
        print("FAIL",name,repr(exc))

def t1():
    state["mode"]="pass"
    out=m.evaluate({"context_id":"ctx","v3_input":public_case(3)})
    assert out["pass"] is True and out["v9_preserved_positive_route"] is True and out["route"]=="V9_PASS"

def t2():
    state["mode"]="capacity"
    with tempfile.TemporaryDirectory() as td:
        out=m.evaluate(make_payload(pathlib.Path(td),2),repo_root=td)
        assert out["pass"] is True and out["route"]=="POLICY_INFLUENCE_NONINTERFERENCE_RELEVANCE_CELL_V1"
        assert out["selected_claim_ids"]==["A","B"]
        assert out["relevance_bits"]=={"D":"RELEVANT","E":"IRRELEVANT"}

def t3():
    state["mode"]="capacity"
    out=m.evaluate({"context_id":"ctx","v3_input":public_case(2)})
    assert out["pass"] is False and out["policy_influence_fast_path_pass"] is False

def t4():
    state["mode"]="weights_fail"
    with tempfile.TemporaryDirectory() as td:
        p=make_payload(pathlib.Path(td),2)
        p["objective_weights"]={"A":1}
        out=m.evaluate(p,repo_root=td)
        assert out["pass"] is False and out["reason"]=="OBJECTIVE_WEIGHTS_UNSATISFIED"
        assert out["policy_influence_fast_path_pass"] is False

def t5():
    state["mode"]="conflict"
    with tempfile.TemporaryDirectory() as td:
        p=make_payload(pathlib.Path(td),2)
        out=m.evaluate(p,repo_root=td)
        assert out["pass"] is False
        assert out["policy_influence_not_applicable_reason"]=="V9_DID_NOT_REACH_CAPACITY_BINDING_RELEVANCE_FRONTIER"

def t6():
    state["mode"]="capacity"
    with tempfile.TemporaryDirectory() as td:
        p=make_payload(pathlib.Path(td),2)
        p["policy_influence_contract"]["current_discriminator_values"]["E"]="X0"
        out=m.evaluate(p,repo_root=td)
        assert out["pass"] is False and out["reason"]=="POLICY_INFLUENCE_CONTRACT_UNSATISFIED"

def t7():
    state["mode"]="capacity"
    with tempfile.TemporaryDirectory() as td:
        out=m.evaluate(make_payload(pathlib.Path(td),2),repo_root=td)
        assert out["pass"] is True and out["top_law_eligible"] is False
        for k in ("source_authorization_verified","policy_adequacy_authority","db_admission_authority","u_subtraction_authority","terminal_authority"):
            assert out[k] is False
        assert out["terminal_credit_delta"]==0

for i,f in enumerate((t1,t2,t3,t4,t5,t6,t7),1):
    check("v10_delta_"+str(i),f)
print("RESULT",passed,"/",total)
raise SystemExit(0 if passed==total else 1)
