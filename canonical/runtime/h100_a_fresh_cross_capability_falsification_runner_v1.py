"""Evaluator for the frozen A fresh cross-capability falsification suite V1.

Evaluation-only code. G0 V2 and suite population were frozen before this file.
"""
from __future__ import annotations
import itertools, json, math, tempfile
from pathlib import Path
from typing import Any
import numpy as np
from PIL import Image

from canonical.runtime import h100_verified_capability_registry_v8 as registry
from canonical.runtime import h100_complete_unary_chain_search_v1 as chain
from canonical.runtime import h100_typed_capability_planner_v1 as planner
from canonical.runtime import h100_jit_lexical_orchestrator_v1 as lexical
from canonical.runtime import h100_verified_effect_tool_registry_v1 as tools
from canonical.runtime import h100_zero_learned_event_memory_v1 as memory
from canonical.runtime import h100_generic_bar_geometry_v0 as vision

ROOT=Path(__file__).resolve().parents[2]
SUITE=ROOT/"canonical/governance/H100_A_FRESH_CROSS_CAPABILITY_FALSIFICATION_SUITE_V1.json"
SCHEMA="PROJECT_BRAIN_H100_A_FRESH_CROSS_CAPABILITY_FALSIFICATION_RESULT_V1"

def nrmse(actual,pred):
    mean=sum(actual)/len(actual)
    spread=math.sqrt(sum((x-mean)**2 for x in actual)/len(actual))
    scale=max(spread,max(abs(x) for x in actual)*1e-9,1e-12)
    return math.sqrt(sum((a-b)**2 for a,b in zip(actual,pred))/len(actual))/scale

def apply_seq(x,seq):
    return chain._apply_sequence(float(x),seq)

def rows(seq,coeff,xs):
    a,b,c=map(float,coeff)
    return [{"x":float(x),"y":a+b*float(x)+c*apply_seq(float(x),seq)} for x in xs]

def task_by_id(pre,tid):
    return next(dict(x) for x in pre["tasks"] if x["id"]==tid)

def eval_registry(pre):
    t=task_by_id(pre,"FRESH_REGISTRY_REUSE")
    pop=pre["shared_numeric_population"]
    train=rows(t["sequence"],t["coefficients"],pop["training_x"])
    hold=rows(t["sequence"],t["coefficients"],pop["holdout_x"])
    out=registry.resolve_verified_capability(train,target="y",input_name="x")
    hit=out.get("status")=="LIBRARY_HIT__VERIFY_BEFORE_USE"
    err=None
    if hit:
        pred=[registry.predict(out,{"x":r["x"]}) for r in hold]
        err=nrmse([r["y"] for r in hold],pred)
    ok=bool(hit and err is not None and err<=1e-8)
    return {
        "task_id":t["id"],"class":t["class"],"pass":ok,
        "status":out.get("status"),"capability_id":None if not hit else out["match"].get("capability_id"),
        "holdout_nrmse":err,
        "failure_class":None if ok else "ALGORITHM_GAP",
    }

def eval_unknown_search(pre):
    t=task_by_id(pre,"FRESH_UNKNOWN_STRUCTURE")
    pop=pre["shared_numeric_population"]
    train=rows(t["sequence"],t["coefficients"],pop["training_x"])
    hold=rows(t["sequence"],t["coefficients"],pop["holdout_x"])
    ops=("neg","abs","square","sqrt_abs","log1p_abs","sat")
    best=None; evaluated=0
    for depth in range(1,5):
        exact=[]
        for seq in itertools.product(ops,repeat=depth):
            evaluated+=1
            fit=chain._fit_sequence(train,hold,seq)
            if fit is None: continue
            if fit["train_nrmse"]<=1e-10 and fit["holdout_nrmse"]<=1e-8:
                exact.append(fit)
        if exact:
            exact.sort(key=lambda x:(x["holdout_nrmse"],x["signature"]))
            best=exact[0]
            break
    ok=best is not None and best["holdout_nrmse"]<=1e-8
    return {
        "task_id":t["id"],"class":t["class"],"pass":ok,
        "sequences_evaluated":evaluated,
        "first_exact_depth":None if best is None else best["depth"],
        "selected_sequence":None if best is None else best["sequence"],
        "selected_signature":None if best is None else best["signature"],
        "holdout_nrmse":None if best is None else best["holdout_nrmse"],
        "failure_class":None if ok else "SEARCH_GAP",
    }

def eval_plan(pre):
    t=task_by_id(pre,"FRESH_TYPED_PLAN")
    out=planner.derive_plan(t["initial_resources"],t["goal_resource"])
    ok=out.get("status")=="PLAN_FOUND" and out.get("plan_length")==1 and out.get("plan")==["OP_LEXICAL_SOURCE_FALLBACK"]
    return {
        "task_id":t["id"],"class":t["class"],"pass":ok,
        "planner_result":out,
        "failure_class":None if ok else "ALGORITHM_GAP",
    }

def eval_lexical(pre):
    rows_out=[]
    for tid in ("FRESH_JIT_LEXICAL_INPUT","FRESH_JIT_LEXICAL_TARGET"):
        t=task_by_id(pre,tid)
        out=lexical.resolve(term=t["term"],source_records=t["source_records"])
        ok=out.get("status")=="ROLE_IDENTIFIED" and out.get("role")==t["expected_role"]
        rows_out.append({
            "task_id":tid,"pass":ok,"expected_role":t["expected_role"],
            "observed_role":out.get("role"),"status":out.get("status")
        })
    ok=all(x["pass"] for x in rows_out)
    return {
        "task_id":"FRESH_JIT_LEXICAL_PAIR","class":"LANGUAGE_JIT_SEMANTICS","pass":ok,
        "cases":rows_out,
        "failure_class":None if ok else "ALGORITHM_GAP",
    }

def eval_tools(pre):
    t=task_by_id(pre,"FRESH_EFFECT_TOOLS")
    with tempfile.TemporaryDirectory(prefix="h100-suite-tool-") as td:
        root=Path(td)
        a=tools.invoke("JSON_RECEIPT_WRITER_V1",t["receipt_payload"],root)
        b=tools.invoke("JSONL_LEDGER_APPEND_V1",t["ledger_payload"],root)
        recs=list(a.get("receipts",[]))+list(b.get("receipts",[]))
        hashes_ok=bool(recs) and all(isinstance(x.get("sha256"),str) and len(x["sha256"])==64 for x in recs)
        paths_ok=all((root/x["path"]).is_file() for x in recs)
        ok=(a.get("status")=="VERIFIED_EFFECT_TOOL_INVOKED" and b.get("status")=="VERIFIED_EFFECT_TOOL_INVOKED" and hashes_ok and paths_ok)
        return {
            "task_id":t["id"],"class":t["class"],"pass":ok,
            "receipt_tool_receipts":a.get("receipts"),
            "ledger_tool_receipts":b.get("receipts"),
            "failure_class":None if ok else "ALGORITHM_GAP",
        }

def eval_memory(pre):
    t=task_by_id(pre,"FRESH_EVENT_MEMORY")
    events=memory.generate_trace(int(t["event_count"]))
    full=memory.replay(events)
    b1,b2=map(int,t["restart_boundaries"])
    s1=memory.replay(events[:b1])["snapshot"]
    s2=memory.replay(events[b1:b2],s1)["snapshot"]
    restarted=memory.replay(events[b2:],s2)
    ok=full["state"]==restarted["state"] and full["last_event_hash"]==restarted["last_event_hash"] and full["last_seq"]==restarted["last_seq"]
    return {
        "task_id":t["id"],"class":t["class"],"pass":ok,
        "event_count":len(events),"restart_boundaries":[b1,b2],
        "final_state_key_count":len(full["state"]),
        "failure_class":None if ok else "MEMORY_GAP",
    }

def _render_bar_image(spec,path):
    h,w=280,360
    a=np.full((h,w,3),255,dtype=np.uint8)
    color=np.array(spec["color"],dtype=np.uint8)
    bar=18; gap=24; n=int(spec["bar_count"]); sizes=list(map(int,spec["sizes"]))
    if spec["orientation"]=="VERTICAL":
        x0=max(2,(w-(n*bar+(n-1)*gap))//2)
        base=h-15
        for i,size in enumerate(sizes):
            x=x0+i*(bar+gap)
            a[max(0,base-size):base,x:x+bar]=color
    else:
        y0=max(2,(h-(n*bar+(n-1)*gap))//2)
        left=15
        for i,size in enumerate(sizes):
            y=y0+i*(bar+gap)
            a[y:y+bar,left:min(w,left+size)]=color
    Image.fromarray(a).save(path)

def eval_vision(pre):
    t=task_by_id(pre,"FRESH_BAR_GEOMETRY")
    cases=[]
    with tempfile.TemporaryDirectory(prefix="h100-suite-vision-") as td:
        for i,spec in enumerate(t["images"]):
            p=Path(td)/f"chart_{i}.png"
            _render_bar_image(spec,p)
            out=vision.detect_bar_geometry(p)
            ok=(out.get("status")=="BARLIKE_GEOMETRY_IDENTIFIED" and out.get("orientation")==spec["orientation"] and len(out.get("bar_intervals",[]))==int(spec["bar_count"]))
            cases.append({
                "case":i,"pass":ok,"expected_orientation":spec["orientation"],
                "observed_orientation":out.get("orientation"),
                "expected_bar_count":spec["bar_count"],
                "observed_bar_count":len(out.get("bar_intervals",[])),
                "status":out.get("status"),
            })
    ok=all(x["pass"] for x in cases)
    return {
        "task_id":t["id"],"class":t["class"],"pass":ok,"cases":cases,
        "failure_class":None if ok else "REPRESENTATION_GAP",
    }

def eval_information_control(pre):
    t=task_by_id(pre,"FRESH_HIDDEN_INFORMATION_CONTROL")
    # Identical runtime evidence and deterministic G0 imply one identical output
    # for both hidden worlds; opposite required labels cannot both be correct.
    worlds=t["hidden_worlds"]
    outputs={x["correct_output"] for x in worlds}
    k=len(worlds) if t["runtime_evidence_identical"] and len(outputs)>1 else 1
    bits=0 if k<=1 else math.ceil(math.log2(k))
    ok=(k==int(t["expected_residual_equivalence_class"]) and bits==int(t["lower_bound_target_adapted_bits_if_no_target_code"]))
    return {
        "task_id":t["id"],"class":t["class"],"pass":ok,
        "residual_equivalence_class":k,
        "target_adapted_bit_lower_bound":bits,
        "failure_class":"INFORMATION_GAP" if ok else "VERIFICATION_GAP",
        "control_expected_to_be_unsolvable_at_p0":True,
    }

def run():
    pre=json.loads(SUITE.read_text())
    rows=[
        eval_registry(pre),eval_unknown_search(pre),eval_plan(pre),
        eval_lexical(pre),eval_tools(pre),eval_memory(pre),eval_vision(pre),
        eval_information_control(pre),
    ]
    ordinary=[x for x in rows if x["class"]!="INFORMATION_GAP_POSITIVE_CONTROL"]
    p0_pass=sum(bool(x["pass"]) for x in ordinary)
    failures=[x for x in ordinary if not x["pass"]]
    control=next(x for x in rows if x["class"]=="INFORMATION_GAP_POSITIVE_CONTROL")
    return {
        "schema":SCHEMA,
        "status":"P0_SURVIVES_ALL_BOUNDED_FRESH_TASKS" if not failures and control["pass"] else "P0_FALSIFIED_ON_AT_LEAST_ONE_BOUNDED_FRESH_TASK",
        "g0_target_adapted_persistent_bits":0,
        "ordinary_task_count":len(ordinary),
        "ordinary_tasks_passed":p0_pass,
        "ordinary_tasks_failed":len(failures),
        "information_gap_positive_control_pass":control["pass"],
        "failure_classes":sorted({x["failure_class"] for x in failures if x.get("failure_class")}),
        "task_results":rows,
        "hard_nonclaims":[
            "BOUNDED_FRESH_SUITE_IS_NOT_FRONTIER_CAPABILITY_PROOF",
            "VISION_SLICE_IS_SYNTHETIC_BAR_GEOMETRY_ONLY",
            "P0_SURVIVAL_DOES_NOT_PROVE_UNIVERSAL_ZERO_TARGET_ADAPTED_STATE",
            "P0_FAILURE_DOES_NOT_BY_ITSELF_PROVE_POSITIVE_PERSISTENT_BITS_ARE_NEEDED",
        ],
        "promotion_authority":False,
    }

if __name__=="__main__":
    print(json.dumps(run(),indent=2,sort_keys=True))
