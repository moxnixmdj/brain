#!/usr/bin/env python3
from __future__ import annotations
import copy, importlib.util, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SUBJECT=ROOT/"canonical/runtime/composition_closed_world_tcb_reducer_v1.py"
spec=importlib.util.spec_from_file_location("cw",SUBJECT)
if spec is None or spec.loader is None: raise RuntimeError("SUBJECT_LOAD_FAILED")
cw=importlib.util.module_from_spec(spec); spec.loader.exec_module(cw)

def comp():
    return {"composition_ready":True,"verified_initial_facts":["ext.ready"],"required_external_initials":["ext.ready"],
      "problem":{"restrict_inherited_bound_capabilities":True,"capabilities":[
        {"id":"a","clause_index":0,"requires":["ext.ready"],"provides":["e1","slot.e1"],"result_fields":["x"],"inputs":{},"action":{"type":"tool_a","args":{}}},
        {"id":"b","clause_index":1,"requires":["slot.e1"],"provides":["e2"],"result_fields":["y"],
         "inputs":{"src":{"$effect_result":{"effect":"slot.e1","field":"x"}}},"action":{"type":"tool_b","args":{}}}
      ]}}
def ledger():
    d={k:True for k in cw.LEDGER_TRUE}
    d.update({"certificate_id":"ledger-v1","implementation_path":"canonical/runtime/ledger.py","implementation_git_blob_sha":"a"*40,
              "verifier_path":"canonical/runtime/verify_ledger.py","verifier_git_blob_sha":"b"*40})
    return d
def cert(t):
    d={k:True for k in cw.ACTION_TRUE}
    d.update({"certificate_id":"cert-"+t,"action_type":t,"implementation_path":"canonical/runtime/"+t+".py","implementation_git_blob_sha":"c"*40,
              "verifier_path":"canonical/runtime/verify_"+t+".py","verifier_git_blob_sha":"d"*40})
    return d
def req(name,ok,out):
    if not ok: raise AssertionError(name+":"+json.dumps(out,sort_keys=True))

def main():
    tests=[]
    c=comp()
    out=cw.evaluate(c,ledger(),[cert("tool_a"),cert("tool_b")])
    req("GOOD",out["pass"] is True,out); tests.append("GOOD")

    x=copy.deepcopy(c); x["verified_initial_facts"]=[]
    out=cw.evaluate(x,ledger(),[cert("tool_a"),cert("tool_b")])
    req("UNVERIFIED_INITIAL",not out["pass"] and "UNVERIFIED_EXTERNAL_INITIAL_PRESENT" in out["errors"],out); tests.append("UNVERIFIED_INITIAL")

    l=ledger(); l["rollback_restores_exact_prior_state_root"]=False
    out=cw.evaluate(c,l,[cert("tool_a"),cert("tool_b")])
    req("ROLLBACK_HOLE",not out["pass"] and any(e.startswith("LEDGER_CERTIFICATE_NOT_CLOSED_WORLD:") for e in out["errors"]),out); tests.append("ROLLBACK_HOLE")

    b=cert("tool_b"); b["ambient_reads_forbidden"]=False
    out=cw.evaluate(c,ledger(),[cert("tool_a"),b])
    req("AMBIENT_READ_HOLE",not out["pass"] and any(e.startswith("ACTION_CERTIFICATE_NOT_CLOSED_WORLD:tool_b:") for e in out["errors"]),out); tests.append("AMBIENT_READ_HOLE")

    x=copy.deepcopy(c); x["problem"]["capabilities"][1]["inputs"]["src"]["$effect_result"]["field"]="missing"
    out=cw.evaluate(x,ledger(),[cert("tool_a"),cert("tool_b")])
    req("FIELD_HOLE",not out["pass"] and any(e.startswith("EFFECT_RESULT_FIELD_UNDECLARED_ON_SOME_ALTERNATIVE:") for e in out["errors"]),out); tests.append("FIELD_HOLE")

    x=copy.deepcopy(c); x["problem"]["capabilities"].insert(1,
      {"id":"a_alt","clause_index":0,"requires":["ext.ready"],"provides":["e1","slot.e1"],"result_fields":["x"],"inputs":{},"action":{"type":"tool_a","args":{"variant":2}}})
    out=cw.evaluate(x,ledger(),[cert("tool_a"),cert("tool_b")])
    req("SAME_CLAUSE_ALT",out["pass"] is True,out); tests.append("SAME_CLAUSE_ALT")

    x["problem"]["capabilities"][1]["clause_index"]=2
    out=cw.evaluate(x,ledger(),[cert("tool_a"),cert("tool_b")])
    req("CROSS_CLAUSE_AMBIGUITY",not out["pass"] and any(e.startswith("EFFECT_RESULT_PROVIDER_AMBIGUOUS_ACROSS_CLAUSES:") for e in out["errors"]),out); tests.append("CROSS_CLAUSE_AMBIGUITY")

    out=cw.evaluate(c,ledger(),[cert("tool_a")])
    req("MISSING_CERT",not out["pass"] and "ACTION_TYPE_CERTIFICATE_MISSING:tool_b" in out["errors"],out); tests.append("MISSING_CERT")

    return {"schema":"PROJECT_BRAIN_COMPOSITION_CLOSED_WORLD_TCB_REDUCER_SELFTEST_V1","status":"PASS","pass":True,
            "test_count":len(tests),"tests":tests,"independent":False,
            "reason_independent_false":"SAME_WORKER_SELFTEST_REQUIRES_SEPARATE_RUNNER_FOR_INDEPENDENT_CREDIT",
            "execution_authority":False,"promotion_authority":False,"capability_credit_delta":0,"family_credit_delta":0}
if __name__=="__main__": print(json.dumps(main(),indent=2,sort_keys=True))
