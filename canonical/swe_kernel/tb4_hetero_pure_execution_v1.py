#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TB4 Hetero Pure Execution — 11 files behaviorally distinguishable, no test_contents.

Why this was the single bottleneck: 19 used test_contents (source text via pytest) to make
each file observable. Pure SWE-Pro execution is behavioral — pytest checks output, not file
text. For 7 of 11 files, `is None` → `not` is behaviorally identical for tested inputs
(e.g. auth '' both False), so omission not detected without content check. This redesigns
HETERO_SPECS so every fix changes behavior for some input, and TEST_SUITE checks only
behavior (no file read). This proves causal cut + family handle true SWE-Pro semantics,
where string-match would still succeed but execution fails for 0/''/False.

Reuse: extract_minimal_cut, attribute_and_induce, gui caps, same 13-step trace shape.

Authority: NONE. Zero model calls.
"""
from __future__ import annotations
import json, tempfile, time, subprocess, textwrap
from pathlib import Path
from typing import Any, Mapping, Sequence
import pathlib, sys
_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

SCHEMA="PROJECT_BRAIN_TB4_HETERO_PURE_EXECUTION_V1"

PURE_SPECS=[
    ("src/auth.py",  "def authenticate(token):\n    if token is None:\n        return False\n    return True\n", "def authenticate(token):\n    if not token:\n        return False\n    return token == 'secret'\n"),
    ("src/db.py",    "def query(sql):\n    if sql is None:\n        return []\n    return execute(sql)\n", "def query(sql):\n    if not sql:\n        return []\n    return execute(sql)\n"),
    ("src/api.py",   "def handle(req):\n    if req is None:\n        return 500\n    return 200\n", "def handle(req):\n    if not req:\n        return 500\n    return 200\n"),
    ("src/ui.py",    "def render(x):\n    if x is None:\n        return ''\n    return str(x)\n", "def render(x):\n    if not x:\n        return ''\n    return str(x)\n"),
    ("src/cache.py", "CACHE={'a': 1}\ndef get(k):\n    return CACHE[k]\n", "CACHE={'a': 1}\ndef get(k):\n    return CACHE.get(k)\n"),
    ("src/util.py",  "def normalize(s):\n    if s == '':\n        return None\n    return s.strip()\n", "def normalize(s):\n    if not s:\n        return None\n    return s.strip()\n"),
    ("src/conf.py",  "PORT=8080\ndef load():\n    if PORT is None:\n        return 8000\n    return PORT\n", "PORT=8080\ndef load():\n    return PORT or 8000\n"),
    ("src/log.py",   "import logging\nLOGGED=[]\ndef emit(msg):\n    if msg is None:\n        return\n    LOGGED.append(msg)\n", "import logging\nLOGGED=[]\ndef emit(msg):\n    if not msg:\n        return\n    LOGGED.append(msg)\n"),
    ("src/net.py",   "def fetch(url):\n    if url is None:\n        raise ValueError()\n    return request(url)\n", "def fetch(url):\n    if not url:\n        raise ValueError()\n    return request(url)\n"),
    ("src/store.py", "DATA=[]\ndef push(v):\n    if v is None:\n        return\n    DATA.append(v)\n", "DATA=[]\ndef push(v):\n    if not v:\n        return\n    DATA.append(v)\n"),
    ("src/cli.py",   "def main(args):\n    if args is None:\n        args=[]\n    run(args)\n", "def main(args):\n    args=args or []\n    run(args)\n"),
]

PURE_TESTS=textwrap.dedent("""
import sys
sys.path.insert(0, 'src')
def test_auth():
    from auth import authenticate
    assert authenticate(None)==False
    assert authenticate('secret')==True
    assert authenticate('wrong')==False  # buggy True, fixed False
    assert authenticate('')==False
def test_db():
    from db import query
    assert query(None)==[]
    assert query('')==[]  # buggy executes '' -> 'executed:', fixed []
    assert query('SELECT 1')=='executed:SELECT 1'
def test_api():
    from api import handle
    assert handle(None)==500
    assert handle('')==500  # buggy 200, fixed 500
    assert handle('req')==200
def test_ui():
    from ui import render
    assert render(None)==''
    assert render(0)==''  # buggy '0', fixed ''
    assert render('hi')=='hi'
def test_cache():
    import cache
    assert cache.get('a')==1
    assert cache.get('missing') is None  # buggy KeyError, fixed None
    assert cache.get('a')==1
def test_util():
    from util import normalize
    assert normalize(None) is None  # buggy AttributeError None.strip(), fixed None
    assert normalize('') is None
    assert normalize('  hi ')=='hi'
def test_conf():
    import conf, importlib
    importlib.reload(conf)
    assert conf.load()==8080
    conf.PORT=0
    assert conf.load()==8000  # buggy 0, fixed 8000
    conf.PORT=8080
def test_log():
    import log
    log.LOGGED=[]
    log.emit(None)
    assert log.LOGGED==[]
    log.emit('')
    assert log.LOGGED==[]  # buggy [''], fixed []
    log.emit('hi')
    assert log.LOGGED==['hi']
def test_net():
    from net import fetch
    try: fetch(None); assert False
    except ValueError: pass
    try: fetch(''); assert False  # buggy would request '', fixed raises
    except ValueError: pass
    assert fetch('http://x')=='fetched:http://x'
def test_store():
    import store
    store.DATA=[]
    store.push(None)
    assert store.DATA==[]
    store.push(0)
    assert store.DATA==[]  # buggy [0], fixed []
    store.push(5)
    assert store.DATA==[5]
def test_cli():
    import cli
    calls=[]
    cli.run=lambda a: calls.append(a)
    cli.main(None)
    assert calls[-1]==[]
    cli.main(0)
    assert calls[-1]==[]  # buggy 0, fixed []
    cli.main(['a'])
    assert calls[-1]==['a']
""")

def _write_pure_repo(trace: Sequence[Mapping[str,Any]], repo: Path, initial_files: dict[str,str]) -> None:
    for rel, content in initial_files.items():
        if rel=="gui_state.json": continue
        (repo/rel).parent.mkdir(parents=True, exist_ok=True)
        (repo/rel).write_text(content, encoding="utf-8")
    # stubs
    (repo/"src/execute_stub.py").write_text("def execute(sql): return f'executed:{sql}'\n", encoding="utf-8")
    (repo/"src/request_stub.py").write_text("def request(url): return f'fetched:{url}'\n", encoding="utf-8")
    (repo/"src/run_stub.py").write_text("def run(args): pass\n", encoding="utf-8")
    for s in trace:
        if str(s.get("layer"))=="python_file_op" and s.get("path") and s.get("content") is not None:
            path=str(s["path"]); content=str(s["content"])
            if "execute(sql)" in content and "from execute_stub" not in content:
                content="from execute_stub import execute\n"+content
            if "request(url)" in content and "from request_stub" not in content:
                content="from request_stub import request\n"+content
            if "run(args)" in content and "from run_stub" not in content:
                content="from run_stub import run\n"+content
            (repo/path).parent.mkdir(parents=True, exist_ok=True)
            (repo/path).write_text(content, encoding="utf-8")
    # inject stubs into initial files not overwritten
    for rel in initial_files:
        if rel=="gui_state.json": continue
        p=repo/rel
        if not p.exists(): continue
        text=p.read_text(encoding="utf-8")
        patched=False
        if "execute(sql)" in text and "from execute_stub" not in text:
            text="from execute_stub import execute\n"+text; patched=True
        if "request(url)" in text and "from request_stub" not in text:
            text="from request_stub import request\n"+text; patched=True
        if "run(args)" in text and "from run_stub" not in text:
            text="from run_stub import run\n"+text; patched=True
        if patched: p.write_text(text, encoding="utf-8")

def _make_pure_task(tmp: Path) -> dict[str, Any]:
    files={path: buggy for path, buggy, _ in PURE_SPECS}
    files["gui_state.json"]=json.dumps({"elements":[{"role":"button","name":"Ship","text":"Ship Fix"},{"role":"textbox","name":"Changelog","placeholder":"Describe"}],"actions":[]})
    for rel,c in files.items():
        (tmp/rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp/rel).write_text(c, encoding="utf-8")
    trace=[]; causal=[]; noise=[]
    for idx,(path,_,fixed) in enumerate(PURE_SPECS):
        if idx==3:
            trace.append({"layer":"cli_exec","argv":["ls","src"],"note":"noise"})
            noise.append(len(trace)-1)
        if idx==7:
            trace.append({"layer":"cli_exec","argv":["echo","noise"],"note":"noise"})
            noise.append(len(trace)-1)
        trace.append({"layer":"python_file_op","op":"write_text","path":path,"content":fixed})
        causal.append(len(trace)-1)
    trace.append({"layer":"semantic_dom","op":"FILL_SEMANTIC","selector":{"role":"textbox","name":"Changelog"},"value":"pure hetero fix"})
    causal.append(len(trace)-1)
    trace.append({"layer":"semantic_dom","op":"CLICK_SEMANTIC","selector":{"role":"button","name":"Ship"}})
    causal.append(len(trace)-1)
    goal="Fix 11 pure heterogeneous files (truthiness/empty/PORT/KeyError) and ship via GUI Ship — verified by pytest behavioral"
    return {"tmp":tmp,"files":files,"trace":trace,"goal":goal,"causal_indices":causal,"noise_indices":noise}

def _oracle_pure(trace: Sequence[Mapping[str,Any]], initial_files: dict[str,str]) -> bool:
    has_fill=any(str(s.get("layer"))=="semantic_dom" and "FILL" in str(s.get("op")) for s in trace)
    has_click=any(str(s.get("layer"))=="semantic_dom" and "CLICK" in str(s.get("op")) and "Ship" in str(s.get("selector",{}).get("name","")) for s in trace)
    if not (has_fill and has_click):
        return False
    repo=Path(tempfile.mkdtemp(prefix="brain-pure-oracle-"))
    try:
        _write_pure_repo(trace, repo, initial_files)
        (repo/"test_pure.py").write_text(PURE_TESTS, encoding="utf-8")
        (repo/"pytest.ini").write_text("[pytest]\naddopts = -q\n", encoding="utf-8")
        import os
        env=dict(os.environ)
        if Path("/tmp/pytest_pkg").is_dir():
            env["PYTHONPATH"]="/tmp/pytest_pkg"+":"+env.get("PYTHONPATH","")
        result=subprocess.run([sys.executable,"-m","pytest","-q","test_pure.py"], cwd=str(repo), capture_output=True, text=True, timeout=15, env=env)
        if "No module named pytest" in (result.stderr or "")+ (result.stdout or ""):
            fallback=subprocess.run([sys.executable,"-c","import importlib.util; spec=importlib.util.spec_from_file_location('test_pure','test_pure.py'); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); [getattr(m,n)() for n in dir(m) if n.startswith('test_')]"], cwd=str(repo), capture_output=True, text=True, timeout=10)
            return fallback.returncode==0
        return result.returncode==0
    except Exception:
        return False
    finally:
        import shutil
        shutil.rmtree(repo, ignore_errors=True)

def compose_and_verify_pure(root: Path|None=None) -> dict[str,Any]:
    t0=time.perf_counter_ns()
    from canonical.swe_kernel.causal_cut_attribution_v1 import extract_minimal_cut, attribute_and_induce
    tmp=Path(tempfile.mkdtemp(prefix="brain-pure-")) if root is None else Path(root)
    try:
        hard=_make_pure_task(tmp)
        trace,goal,exp_causal,exp_noise=hard["trace"],hard["goal"],set(hard["causal_indices"]),set(hard["noise_indices"])
        initial_files=hard["files"]
        def oracle(sub): return _oracle_pure(sub, initial_files)
        cut_res=extract_minimal_cut(trace, oracle, max_ablation_cost=100)
        if cut_res["status"] not in ("CUT_DONE__CAUSAL_CUT_EXTRACTED","CUT_MINIMAL__NECESSARY_AND_SUFFICIENT"):
            return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED__CUT_FAILED","cut_res":cut_res}
        kept=set(cut_res["kept_indices"]); pruned=set(cut_res["pruned_indices"])
        attribution_correct=(kept==exp_causal and pruned==exp_noise)
        pre_state={k:v.encode() for k,v in hard["files"].items() if k!="gui_state.json"}
        post_state=dict(pre_state)
        for s in trace:
            if str(s.get("layer"))=="python_file_op" and s.get("path"):
                post_state[str(s["path"])]=str(s["content"]).encode()
        induced=attribute_and_induce(trace, oracle, goal=goal, pre_state=pre_state, post_state=post_state)
        family_ok=induced.get("pass") and induced.get("family_predicate",{}).get("postcondition",{}).get("kind")!="unknown"
        requires_content=(induced.get("family_predicate",{}).get("precondition",{}).get("requires_content") if family_ok else {})
        hetero_ok=len(requires_content or {})>=5
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
        return {"schema":SCHEMA,"pass":passed,"status":"PASS__PURE_EXECUTION_VERIFIED" if passed else "FAIL__PURE_EXECUTION_FAILED","goal":goal,"trace_len":len(trace),"kept_indices":sorted(kept),"pruned_indices":sorted(pruned),"expected_kept":sorted(exp_causal),"attribution_correct":attribution_correct,"family_ok":family_ok,"family_id":induced.get("family_predicate",{}).get("family_id") if family_ok else None,"requires_content_count":len(requires_content or {}),"requires_content_keys":sorted((requires_content or {}).keys())[:8],"hetero_ok":hetero_ok,"ground_ok":ground_ok,"act_ok":act_ok,"verify_ok":verify_ok,"oracle_calls":cut_res.get("oracle_calls"),"elapsed_ms":round(elapsed,2),"model_calls":0,"network_calls":0}
    finally:
        if root is None:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)

def main(argv: Sequence[str]|None=None) -> int:
    import argparse, json
    p=argparse.ArgumentParser(description="TB4 pure behavioral execution")
    p.add_argument("--json", dest="json_path", default=None)
    ns=p.parse_args(argv)
    res=compose_and_verify_pure()
    print(json.dumps(res, indent=2, sort_keys=True))
    if ns.json_path:
        Path(ns.json_path).parent.mkdir(parents=True, exist_ok=True)
        Path(ns.json_path).write_text(json.dumps(res,indent=2,sort_keys=True)+"\n")
    return 0 if res.get("pass") else 1
if __name__=="__main__":
    raise SystemExit(main())
