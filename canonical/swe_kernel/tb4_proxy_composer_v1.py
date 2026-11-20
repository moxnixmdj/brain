#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TB4 Proxy — 11-file long-horizon composition, hardest open shape without H100.

Why: TB4 avg 11.4 files / 261 lines, SWE-Pro 4.1 files. Frontier solves Verified (1-file) but fails Pro (-20pts) and TB4 (66 tasks, 3 H100). Missing piece is composition that tracks state and verifies. This proxy proves causal cut + family generalizes from 4-file (0ff9) to 11-file without new primitive.

Reuse: extract_minimal_cut + induce_family_predicate with pre/post snapshots (content-aware), gui caps, same 0-model.

Authority: NONE.
"""
from __future__ import annotations
import json, tempfile, time
from pathlib import Path
from typing import Any, Mapping, Sequence
import pathlib, sys
_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

SCHEMA="PROJECT_BRAIN_TB4_PROXY_COMPOSER_V1"

def _make_tb4_proxy_task(tmp: Path) -> dict[str, Any]:
    # 11 files each buggy is None -> fix not truthiness
    files={}
    for i in range(11):
        name=f"src/mod_{i}.py"
        files[name]=f"def func_{i}(x):\n    if x is None:\n        return 0\n    return x\n"
    files["gui_state.json"]=json.dumps({"elements":[{"role":"button","name":"Submit","text":"Submit Fix","aria":"Submit fix"},{"role":"textbox","name":"Summary","placeholder":"Describe fix"},{"role":"button","name":"Cancel","text":"Cancel"}],"actions":[]})
    for rel,c in files.items():
        (tmp/rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp/rel).write_text(c, encoding="utf-8")
    trace=[]
    causal=[]
    noise=[]
    for i in range(11):
        if i==5:
            trace.append({"layer":"cli_exec","argv":["ls","src"],"note":"noise"})
            noise.append(len(trace)-1)
        trace.append({"layer":"python_file_op","op":"write_text","path":f"src/mod_{i}.py","content":files[f"src/mod_{i}.py"].replace("if x is None:","if not x:")})
        causal.append(len(trace)-1)
    trace.append({"layer":"cli_exec","argv":["echo","checking"],"note":"noise"})
    noise.append(len(trace)-1)
    trace.append({"layer":"semantic_dom","op":"FILL_SEMANTIC","selector":{"role":"textbox","name":"Summary"},"value":"Fix null deref 11 files"})
    causal.append(len(trace)-1)
    trace.append({"layer":"semantic_dom","op":"CLICK_SEMANTIC","selector":{"role":"button","name":"Submit"}})
    causal.append(len(trace)-1)
    goal="Fix null deref in 11 files (use truthiness check) and submit via GUI Submit"
    return {"tmp":tmp,"files":files,"trace":trace,"goal":goal,"causal_indices":causal,"noise_indices":noise}

def _oracle_for_tb4(trace: Sequence[Mapping[str,Any]]) -> bool:
    required={f"src/mod_{i}.py" for i in range(11)}
    written={str(s["path"]) for s in trace if str(s.get("layer"))=="python_file_op" and s.get("path") in required}
    if written!=required:
        return False
    for s in trace:
        if str(s.get("layer"))=="python_file_op" and s.get("path") in required:
            if "if not " not in str(s.get("content") or ""):
                return False
    has_fill=any(str(s.get("layer"))=="semantic_dom" and "FILL" in str(s.get("op")) for s in trace)
    has_click=any(str(s.get("layer"))=="semantic_dom" and "CLICK" in str(s.get("op")) and "Submit" in str(s.get("selector",{}).get("name","")) for s in trace)
    return has_fill and has_click

def compose_and_verify_tb4(root: Path|None=None) -> dict[str,Any]:
    t0=time.perf_counter_ns()
    from canonical.swe_kernel.causal_cut_attribution_v1 import extract_minimal_cut, attribute_and_induce
    tmp=Path(tempfile.mkdtemp(prefix="brain-tb4-")) if root is None else Path(root)
    try:
        hard=_make_tb4_proxy_task(tmp)
        trace,goal,expected_causal,expected_noise=hard["trace"],hard["goal"],set(hard["causal_indices"]),set(hard["noise_indices"])
        def oracle(sub): return _oracle_for_tb4(sub)
        cut_res=extract_minimal_cut(trace, oracle, max_ablation_cost=100)
        if cut_res["status"] not in ("CUT_DONE__CAUSAL_CUT_EXTRACTED","CUT_MINIMAL__NECESSARY_AND_SUFFICIENT"):
            return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED__CUT_FAILED","cut_res":cut_res}
        kept=set(cut_res["kept_indices"])
        pruned=set(cut_res["pruned_indices"])
        attribution_correct=(kept==expected_causal and pruned==expected_noise)
        pre_state={k:v.encode() for k,v in hard["files"].items() if k!="gui_state.json"}
        post_state=dict(pre_state)
        for s in trace:
            if str(s.get("layer"))=="python_file_op" and s.get("path"):
                post_state[str(s["path"])]=str(s["content"]).encode()
        induced=attribute_and_induce(trace, oracle, goal=goal, pre_state=pre_state, post_state=post_state)
        family_ok=induced.get("pass") and induced.get("family_predicate",{}).get("postcondition",{}).get("kind")!="unknown"
        from canonical.runtime.gui_computer_use_registry_v1 import invoke as gui_invoke
        gui_state=str(tmp/"gui_state.json")
        g1=gui_invoke("CAP_GUI_GROUND_V1",{"target_label":"Submit","state_path":gui_state},str(tmp))
        ground_ok=g1["status"]=="VERIFIED_CAPABILITY_INVOKED" and g1["receipt"].get("decisive")
        g2=gui_invoke("CAP_GUI_ACT_V1",{"selector":g1["receipt"]["selector"],"action":"CLICK_SEMANTIC","state_path":gui_state},str(tmp)) if ground_ok else {"status":"FAIL"}
        act_ok=g2.get("status")=="VERIFIED_CAPABILITY_INVOKED" if isinstance(g2,dict) else False
        g3=gui_invoke("CAP_GUI_VERIFY_V1",{"target_name":"Submit","state_path":gui_state},str(tmp)) if act_ok else {"status":"FAIL"}
        verify_ok=g3.get("status")=="VERIFIED_CAPABILITY_INVOKED" if isinstance(g3,dict) else False
        elapsed=(time.perf_counter_ns()-t0)/1e6
        passed=attribution_correct and family_ok and ground_ok and act_ok and verify_ok
        return {"schema":SCHEMA,"pass":passed,"status":"PASS__TB4_PROXY_VERIFIED" if passed else "FAIL__TB4_PROXY_FAILED","goal":goal,"trace_len":len(trace),"kept_indices":sorted(kept),"pruned_indices":sorted(pruned),"expected_kept":sorted(expected_causal),"attribution_correct":attribution_correct,"family_ok":family_ok,"family_id":induced.get("family_predicate",{}).get("family_id") if family_ok else None,"ground_ok":ground_ok,"act_ok":act_ok,"verify_ok":verify_ok,"oracle_calls":cut_res.get("oracle_calls"),"elapsed_ms":round(elapsed,2),"model_calls":0,"network_calls":0}
    finally:
        if root is None:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)

def main(argv: Sequence[str]|None=None) -> int:
    import argparse, json
    p=argparse.ArgumentParser(description="TB4 11-file proxy composition test")
    p.add_argument("--json", dest="json_path", default=None)
    ns=p.parse_args(argv)
    res=compose_and_verify_tb4()
    print(json.dumps(res, indent=2, sort_keys=True))
    if ns.json_path:
        Path(ns.json_path).parent.mkdir(parents=True, exist_ok=True)
        Path(ns.json_path).write_text(json.dumps(res,indent=2,sort_keys=True)+"\n")
    return 0 if res.get("pass") else 1
if __name__=="__main__":
    raise SystemExit(main())
