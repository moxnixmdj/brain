#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TB4 Hetero 11-file — heterogeneous edits, hardest Pro shape.

Why next bottleneck: tb4_proxy_composer proved 11-file scale but uniform bug (all `is None→not`, family collapsed to 1 snippet). Real TB4 avg 261 lines heterogeneous, SWE-Pro 4.1 files heterogeneous (-20pt frontier gap). Missing is proving causal cut + content-aware family handles 11 *different* fixes with same mechanism, no new primitive.

Reuse: extract_minimal_cut, attribute_and_induce with pre/post (different requires_content per file), gui caps.

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
SCHEMA="PROJECT_BRAIN_TB4_HETERO_COMPOSER_V1"

HETERO_SPECS=[
    ("src/auth.py",   "def authenticate(token):\n    if token is None:\n        return False\n    return token == 'secret'\n", "def authenticate(token):\n    if not token:\n        return False\n    return token == 'secret'\n"),
    ("src/db.py",     "def query(sql):\n    if sql is None:\n        return []\n    return execute(sql)\n", "def query(sql):\n    if not sql:\n        return []\n    return execute(sql)\n"),
    ("src/api.py",    "def handle(req):\n    if req is None:\n        return 500\n    return 200\n", "def handle(req):\n    if not req:\n        return 500\n    return 200\n"),
    ("src/ui.py",     "def render(x):\n    if x is None:\n        return ''\n    return str(x)\n", "def render(x):\n    if not x:\n        return ''\n    return str(x)\n"),
    ("src/cache.py",  "CACHE={}\ndef get(k):\n    if k not in CACHE:\n        return None\n    return CACHE[k]\n", "CACHE={}\ndef get(k):\n    return CACHE.get(k)\n"),
    ("src/util.py",   "def normalize(s):\n    if s == '':\n        return None\n    return s.strip()\n", "def normalize(s):\n    if not s:\n        return None\n    return s.strip()\n"),
    ("src/conf.py",   "PORT=8080\ndef load():\n    if PORT is None:\n        return 8000\n    return PORT\n", "PORT=8080\ndef load():\n    return PORT or 8000\n"),
    ("src/log.py",    "import logging\ndef emit(msg):\n    if msg is None:\n        return\n    logging.info(msg)\n", "import logging\ndef emit(msg):\n    if not msg:\n        return\n    logging.info(msg)\n"),
    ("src/net.py",    "def fetch(url):\n    if url is None:\n        raise ValueError()\n    return request(url)\n", "def fetch(url):\n    if not url:\n        raise ValueError()\n    return request(url)\n"),
    ("src/store.py",  "DATA=[]\ndef push(v):\n    if v is None:\n        return\n    DATA.append(v)\n", "DATA=[]\ndef push(v):\n    if v is not None:\n        DATA.append(v)\n"),
    ("src/cli.py",    "def main(args):\n    if args is None:\n        args=[]\n    run(args)\n", "def main(args):\n    args=args or []\n    run(args)\n"),
]

def _make_hetero_task(tmp: Path) -> dict[str, Any]:
    files={}
    for path, buggy, _ in HETERO_SPECS:
        files[path]=buggy
    files["gui_state.json"]=json.dumps({"elements":[{"role":"button","name":"Ship","text":"Ship Fix","aria":"Ship fix"},{"role":"textbox","name":"Changelog","placeholder":"Describe"},{"role":"button","name":"Cancel","text":"Cancel"}],"actions":[]})
    for rel,c in files.items():
        (tmp/rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp/rel).write_text(c, encoding="utf-8")
    trace=[]; causal=[]; noise=[]
    for idx,(path,_,fixed) in enumerate(HETERO_SPECS):
        if idx==3:
            trace.append({"layer":"cli_exec","argv":["ls","src"],"note":"noise"})
            noise.append(len(trace)-1)
        if idx==7:
            trace.append({"layer":"cli_exec","argv":["echo","noise"],"note":"noise"})
            noise.append(len(trace)-1)
        trace.append({"layer":"python_file_op","op":"write_text","path":path,"content":fixed})
        causal.append(len(trace)-1)
    trace.append({"layer":"semantic_dom","op":"FILL_SEMANTIC","selector":{"role":"textbox","name":"Changelog"},"value":"hetero 11-file fix"})
    causal.append(len(trace)-1)
    trace.append({"layer":"semantic_dom","op":"CLICK_SEMANTIC","selector":{"role":"button","name":"Ship"}})
    causal.append(len(trace)-1)
    goal="Fix 11 heterogeneous files (null/empty/PORT/missing-key) and ship via GUI Ship"
    return {"tmp":tmp,"files":files,"trace":trace,"goal":goal,"causal_indices":causal,"noise_indices":noise}

def _oracle_hetero(trace: Sequence[Mapping[str,Any]]) -> bool:
    required={p for p,_,_ in HETERO_SPECS}
    # check each file has been overwritten with fixed content (must contain fixed snippet)
    needed={p: fixed for p,_,fixed in HETERO_SPECS}
    for p,fixed in needed.items():
        hits=[s for s in trace if str(s.get("layer"))=="python_file_op" and s.get("path")==p]
        if not hits:
            return False
        # content must match fixed (or contain its distinguishing line)
        last=str(hits[-1].get("content") or "")
        if last.strip()!=fixed.strip():
            return False
    has_fill=any(str(s.get("layer"))=="semantic_dom" and "FILL" in str(s.get("op")) for s in trace)
    has_click=any(str(s.get("layer"))=="semantic_dom" and "CLICK" in str(s.get("op")) and "Ship" in str(s.get("selector",{}).get("name","")) for s in trace)
    return has_fill and has_click

def compose_and_verify_hetero(root: Path|None=None) -> dict[str,Any]:
    t0=time.perf_counter_ns()
    from canonical.swe_kernel.causal_cut_attribution_v1 import extract_minimal_cut, attribute_and_induce
    tmp=Path(tempfile.mkdtemp(prefix="brain-hetero-")) if root is None else Path(root)
    try:
        hard=_make_hetero_task(tmp)
        trace,goal,exp_causal,exp_noise=hard["trace"],hard["goal"],set(hard["causal_indices"]),set(hard["noise_indices"])
        cut_res=extract_minimal_cut(trace, _oracle_hetero, max_ablation_cost=100)
        if cut_res["status"] not in ("CUT_DONE__CAUSAL_CUT_EXTRACTED","CUT_MINIMAL__NECESSARY_AND_SUFFICIENT"):
            return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED__CUT_FAILED","cut_res":cut_res}
        kept=set(cut_res["kept_indices"]); pruned=set(cut_res["pruned_indices"])
        attribution_correct=(kept==exp_causal and pruned==exp_noise)
        pre_state={k:v.encode() for k,v in hard["files"].items() if k!="gui_state.json"}
        post_state=dict(pre_state)
        for s in trace:
            if str(s.get("layer"))=="python_file_op" and s.get("path"):
                post_state[str(s["path"])]=str(s["content"]).encode()
        induced=attribute_and_induce(trace, _oracle_hetero, goal=goal, pre_state=pre_state, post_state=post_state)
        family_ok=induced.get("pass") and induced.get("family_predicate",{}).get("postcondition",{}).get("kind")!="unknown"
        # requires_content should be heterogeneous (multiple distinct snippets)
        requires_content=(induced.get("family_predicate",{}).get("precondition",{}).get("requires_content") if family_ok else {})
        hetero_ok=len(requires_content or {})>=3  # at least 3 distinct buggy snippets
        from canonical.runtime.gui_computer_use_registry_v1 import invoke as gui_invoke
        gui_state=str(tmp/"gui_state.json")
        g1=gui_invoke("CAP_GUI_GROUND_V1",{"target_label":"Ship","state_path":gui_state},str(tmp))
        ground_ok=g1["status"]=="VERIFIED_CAPABILITY_INVOKED" and g1["receipt"].get("decisive")
        g2=gui_invoke("CAP_GUI_ACT_V1",{"selector":g1["receipt"]["selector"],"action":"CLICK_SEMANTIC","state_path":gui_state},str(tmp)) if ground_ok else {"status":"FAIL"}
        act_ok=g2.get("status")=="VERIFIED_CAPABILITY_INVOKED" if isinstance(g2,dict) else False
        g3=gui_invoke("CAP_GUI_VERIFY_V1",{"target_name":"Ship","state_path":gui_state},str(tmp)) if act_ok else {"status":"FAIL"}
        verify_ok=g3.get("status")=="VERIFIED_CAPABILITY_INVOKED" if isinstance(g3,dict) else False
        elapsed=(time.perf_counter_ns()-t0)/1e6
        passed=attribution_correct and family_ok and hetero_ok and ground_ok and act_ok and verify_ok
        return {"schema":SCHEMA,"pass":passed,"status":"PASS__TB4_HETERO_VERIFIED" if passed else "FAIL__TB4_HETERO_FAILED","goal":goal,"trace_len":len(trace),"kept_indices":sorted(kept),"pruned_indices":sorted(pruned),"expected_kept":sorted(exp_causal),"attribution_correct":attribution_correct,"family_ok":family_ok,"family_id":induced.get("family_predicate",{}).get("family_id") if family_ok else None,"requires_content_count":len(requires_content or {}),"requires_content_keys":sorted((requires_content or {}).keys())[:6],"hetero_ok":hetero_ok,"ground_ok":ground_ok,"act_ok":act_ok,"verify_ok":verify_ok,"oracle_calls":cut_res.get("oracle_calls"),"elapsed_ms":round(elapsed,2),"model_calls":0,"network_calls":0}
    finally:
        if root is None:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)

def main(argv: Sequence[str]|None=None) -> int:
    import argparse, json
    p=argparse.ArgumentParser(description="TB4 hetero 11-file proxy")
    p.add_argument("--json", dest="json_path", default=None)
    ns=p.parse_args(argv)
    res=compose_and_verify_hetero()
    print(json.dumps(res, indent=2, sort_keys=True))
    if ns.json_path:
        Path(ns.json_path).parent.mkdir(parents=True, exist_ok=True)
        Path(ns.json_path).write_text(json.dumps(res,indent=2,sort_keys=True)+"\n")
    return 0 if res.get("pass") else 1
if __name__=="__main__":
    raise SystemExit(main())
