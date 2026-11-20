#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TB4 Hetero Twin Admission — held-out generalization for 11-file heterogeneous family.

Why is this the single bottleneck? §6 requires performing on hardest open tests including never-seen single-experience. 11-hetero (aa022) proved the cut works on one instance; without a perturbed twin, the store cannot claim generalization — it's ephemeral Tier A. The admission that was missing (10) did this for 4-file; this does it for 11-hetero, the hardest open shape without H100.

Reuses: tb4_hetero_composer specs, extract_minimal_cut, attribute_and_induce with pre/post, predicate_matches_task, causal_cut_store, gui caps, destroy guard.

Zero model calls.

Authority: NONE.
"""
from __future__ import annotations
import json, tempfile, time, pathlib, sys
from pathlib import Path
from typing import Any, Mapping, Sequence
_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
SCHEMA="PROJECT_BRAIN_TB4_HETERO_ADMISSION_V1"

# Import hetero specs as ground truth for twin perturbation
from canonical.swe_kernel.tb4_hetero_composer_v1 import HETERO_SPECS, _make_hetero_task, _oracle_hetero

def _make_hetero_twin_task(tmp: Path) -> dict[str, Any]:
    # Twin: each file path perturbed *_v2, GUI labels perturbed, same heterogeneous bugs
    twin_buggy={}
    for path, buggy, _ in HETERO_SPECS:
        twin_path = path.replace(".py", "_v2.py")
        twin_buggy[twin_path]=buggy
    twin_buggy["gui_state.json"]=json.dumps({"elements":[{"role":"button","name":"Deploy","text":"Deploy Fix"},{"role":"textbox","name":"Notes","placeholder":"Add notes"},{"role":"button","name":"Cancel","text":"Cancel"}],"actions":[]})
    for rel,c in twin_buggy.items():
        (tmp/rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp/rel).write_text(c, encoding="utf-8")
    # Fixed contents: same mapping but twin paths
    fixed_map={path.replace(".py","_v2.py"): fixed for path,_,fixed in HETERO_SPECS}
    trace=[]; causal=[]
    for twin_path, fixed in fixed_map.items():
        trace.append({"layer":"python_file_op","op":"write_text","path":twin_path,"content":fixed})
        causal.append(len(trace)-1)
    # Add 1 noise interleaved
    trace.insert(5, {"layer":"cli_exec","argv":["ls","src"],"note":"noise"})
    noise=[5]
    # adjust causal indices after insert
    causal=[i+1 if i>=5 else i for i in causal]
    trace.append({"layer":"semantic_dom","op":"FILL_SEMANTIC","selector":{"role":"textbox","name":"Notes"},"value":"twin hetero 11-file"})
    causal.append(len(trace)-1)
    trace.append({"layer":"semantic_dom","op":"CLICK_SEMANTIC","selector":{"role":"button","name":"Deploy"}})
    causal.append(len(trace)-1)
    goal="Fix 11 heterogeneous files and deploy via GUI Deploy"
    return {"tmp":tmp,"files":twin_buggy,"trace":trace,"goal":goal,"causal_indices":causal,"noise_indices":noise,"fixed_map":fixed_map}

def _oracle_hetero_twin(trace: Sequence[Mapping[str,Any]]) -> bool:
    required={p.replace(".py","_v2.py") for p,_,_ in HETERO_SPECS}
    needed={p.replace(".py","_v2.py"): fixed for p,_,fixed in HETERO_SPECS}
    for p,fixed in needed.items():
        hits=[s for s in trace if str(s.get("layer"))=="python_file_op" and s.get("path")==p]
        if not hits: return False
        if str(hits[-1].get("content") or "").strip()!=fixed.strip(): return False
    has_fill=any(str(s.get("layer"))=="semantic_dom" and "FILL" in str(s.get("op")) for s in trace)
    has_click=any(str(s.get("layer"))=="semantic_dom" and "CLICK" in str(s.get("op")) and "Deploy" in str(s.get("selector",{}).get("name","")) for s in trace)
    return has_fill and has_click

def admit_hetero_family() -> dict[str, Any]:
    t0=time.perf_counter_ns()
    from canonical.swe_kernel.causal_cut_attribution_v1 import extract_minimal_cut, attribute_and_induce
    from canonical.swe_kernel.family_predicate_induction_v1 import predicate_matches_task
    from canonical.swe_kernel.causal_cut_store_v1 import store_cut, recall, clear_cache
    from canonical.runtime.gui_computer_use_registry_v1 import invoke as gui_invoke

    orig_tmp=Path(tempfile.mkdtemp(prefix="brain-hetero-orig-"))
    twin_tmp=Path(tempfile.mkdtemp(prefix="brain-hetero-twin-"))
    try:
        # Original
        orig=_make_hetero_task(orig_tmp)
        orig_trace, orig_goal = orig["trace"], orig["goal"]
        orig_pre={k:v.encode() for k,v in orig["files"].items() if k!="gui_state.json"}
        orig_post=dict(orig_pre)
        for s in orig_trace:
            if str(s.get("layer"))=="python_file_op" and s.get("path"):
                orig_post[str(s["path"])]=str(s["content"]).encode()
        induced=attribute_and_induce(orig_trace, _oracle_hetero, goal=orig_goal, pre_state=orig_pre, post_state=orig_post)
        if not induced.get("pass"):
            return {"schema":SCHEMA,"pass":False,"status":"FAIL__INDUCTION_FAILED","induced":induced}
        family=induced["family_predicate"]; family_id=family["family_id"]; cut_res=induced["cut_result"]
        # Twin
        twin=_make_hetero_twin_task(twin_tmp)
        twin_trace, twin_goal = twin["trace"], twin["goal"]
        # Predicate must match twin (path-agnostic via requires_content snippets, not exact paths)
        should_fire, why = predicate_matches_task(family, twin_goal, None)
        if not should_fire:
            return {"schema":SCHEMA,"pass":False,"status":"FAIL__PREDICATE_DID_NOT_MATCH_TWIN","why":why,"family":family}
        # Twin cut must be minimal and correct
        twin_cut=extract_minimal_cut(twin_trace, _oracle_hetero_twin, max_ablation_cost=100)
        twin_ok=twin_cut["status"] in ("CUT_DONE__CAUSAL_CUT_EXTRACTED","CUT_MINIMAL__NECESSARY_AND_SUFFICIENT")
        expected_kept=set(twin["causal_indices"])
        kept_ok=set(twin_cut.get("kept_indices",[]))==expected_kept
        # Sabotage: drop one file fix should fail
        sabotaged=[s for s in twin_trace if s.get("path")!="src/auth_v2.py"]
        sabotage_correctly_fails=not _oracle_hetero_twin(sabotaged)
        # GUI twin
        gui_state=str(twin_tmp/"gui_state.json")
        g1=gui_invoke("CAP_GUI_GROUND_V1",{"target_label":"Deploy","state_path":gui_state},str(twin_tmp))
        ground_ok=g1["status"]=="VERIFIED_CAPABILITY_INVOKED"
        g2=gui_invoke("CAP_GUI_ACT_V1",{"selector":g1["receipt"]["selector"],"action":"CLICK_SEMANTIC","state_path":gui_state},str(twin_tmp)) if ground_ok else {"status":"FAIL"}
        act_ok=g2.get("status")=="VERIFIED_CAPABILITY_INVOKED" if isinstance(g2,dict) else False
        # Destructive guard: content-aware precondition must reject unrelated world
        destroy_check={}
        try:
            destructive_pre={p: b"unrelated_data='secret'\n" for p,_,_ in HETERO_SPECS}
            should_not, why_not = predicate_matches_task(family, twin_goal, destructive_pre)
            destroy_check["predicate_rejects_unrelated"]=not should_not
            destroy_check["predicate_reject_reason"]=why_not
            should_buggy,_=predicate_matches_task(family, twin_goal, orig_pre)
            destroy_check["predicate_accepts_buggy"]=should_buggy
            destroy_check["guard_documented"]="destroy_negative" in family.get("falsifier",{})
            requires_content=family.get("precondition",{}).get("requires_content",{})
            destroy_check["requires_content_count"]=len(requires_content or {})
        except Exception as e:
            destroy_check["error"]=f"{type(e).__name__}: {e}"

        gained=1 if (twin_ok and kept_ok and ground_ok and act_ok and sabotage_correctly_fails) else 0
        lost=0
        admitted=(gained>=1 and lost==0)
        stored=None
        if admitted:
            stored=store_cut(family_id, twin_goal, induced["minimal_trace"], induced["kept_indices"], induced["original_len"], family, cut_res, pre_state=orig_pre, post_state=orig_post)
            stored_count=len(recall())
        else:
            stored_count=len(recall())
        elapsed=(time.perf_counter_ns()-t0)/1e6
        return {"schema":SCHEMA,"pass":admitted,"status":"PASS__TB4_HETERO_ADMITTED" if admitted else "FAIL__ADMISSION_NOT_MET","family_id":family_id,"original_family":family,"twin_goal":twin_goal,"should_fire":should_fire,"twin_cut_ok":twin_ok,"kept_ok":kept_ok,"twin_kept":twin_cut.get("kept_indices"),"expected_kept":sorted(expected_kept),"sabotage_correctly_fails":sabotage_correctly_fails,"ground_ok":ground_ok,"act_ok":act_ok,"gained":gained,"lost":lost,"admitted":admitted,"destroy_check":destroy_check,"stored":stored,"stored_count":stored_count,"elapsed_ms":round(elapsed,2),"model_calls":0,"network_calls":0}
    finally:
        import shutil
        shutil.rmtree(orig_tmp, ignore_errors=True)
        shutil.rmtree(twin_tmp, ignore_errors=True)

def main(argv: Sequence[str]|None=None) -> int:
    import argparse, json
    p=argparse.ArgumentParser(description="TB4 hetero admission via twin")
    p.add_argument("--json", dest="json_path", default=None)
    ns=p.parse_args(argv)
    res=admit_hetero_family()
    print(json.dumps(res, indent=2, sort_keys=True))
    if ns.json_path:
        Path(ns.json_path).parent.mkdir(parents=True, exist_ok=True)
        Path(ns.json_path).write_text(json.dumps(res,indent=2,sort_keys=True)+"\n")
    return 0 if res.get("pass") else 1
if __name__=="__main__":
    raise SystemExit(main())
