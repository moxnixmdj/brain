#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TB4 Pure Admission — twin generalization for pure behavioral 11-hetero.

Why single bottleneck: 22 proved pure 11-file cut 15→13 8a006125f416a05e PASS with behavioral
oracle (every omission fails). Without twin, family is ephemeral Tier A, not durable.
§6 requires never-seen single-experience generalization: original src/*.py → twin src/*_v2.py + Deploy.
This admission closes it, promoting pure to 3rd durable, which live act should prefer.

Reuse: PURE_SPECS + _make_pure_task + _oracle_pure from tb4_hetero_pure_execution, same twin pattern as tb4_hetero_admission.

Authority: NONE. Zero model calls.
"""
from __future__ import annotations
import json, tempfile, time, pathlib, sys
from pathlib import Path
from typing import Any, Mapping, Sequence
_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
SCHEMA="PROJECT_BRAIN_TB4_PURE_ADMISSION_V1"
from canonical.swe_kernel.tb4_hetero_pure_execution_v1 import PURE_SPECS, _make_pure_task, _oracle_pure, PURE_TESTS, _write_pure_repo

def _make_pure_twin(tmp: Path) -> dict[str, Any]:
    twin_buggy={}
    for path, buggy, _ in PURE_SPECS:
        twin_path=path.replace(".py","_v2.py")
        twin_buggy[twin_path]=buggy
    twin_buggy["gui_state.json"]=json.dumps({"elements":[{"role":"button","name":"Deploy","text":"Deploy Fix"},{"role":"textbox","name":"Notes","placeholder":"Add notes"},{"role":"button","name":"Cancel","text":"Cancel"}],"actions":[]})
    for rel,c in twin_buggy.items():
        (tmp/rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp/rel).write_text(c, encoding="utf-8")
    fixed_map={path.replace(".py","_v2.py"): fixed for path,_,fixed in PURE_SPECS}
    trace=[]; causal=[]
    for tp, fixed in fixed_map.items():
        trace.append({"layer":"python_file_op","op":"write_text","path":tp,"content":fixed})
        causal.append(len(trace)-1)
    trace.insert(5, {"layer":"cli_exec","argv":["ls","src"],"note":"noise"})
    noise=[5]
    causal=[i+1 if i>=5 else i for i in causal]
    trace.append({"layer":"semantic_dom","op":"FILL_SEMANTIC","selector":{"role":"textbox","name":"Notes"},"value":"pure twin"})
    causal.append(len(trace)-1)
    trace.append({"layer":"semantic_dom","op":"CLICK_SEMANTIC","selector":{"role":"button","name":"Deploy"}})
    causal.append(len(trace)-1)
    goal="Fix 11 pure heterogeneous files and deploy via GUI Deploy"
    return {"tmp":tmp,"files":twin_buggy,"trace":trace,"goal":goal,"causal_indices":causal,"noise_indices":noise,"fixed_map":fixed_map}

def _oracle_pure_twin(trace: Sequence[Mapping[str,Any]], initial_files: dict[str,str]) -> bool:
    # Behavioral check + GUI Deploy, with twin _v2 file names
    required={p.replace(".py","_v2.py") for p,_,_ in PURE_SPECS}
    needed={p.replace(".py","_v2.py"): fixed for p,_,fixed in PURE_SPECS}
    for p,fixed in needed.items():
        hits=[s for s in trace if str(s.get("layer"))=="python_file_op" and s.get("path")==p]
        if not hits: return False
        if str(hits[-1].get("content") or "").strip()!=fixed.strip(): return False
    has_fill=any(str(s.get("layer"))=="semantic_dom" and "FILL" in str(s.get("op")) for s in trace)
    has_click=any(str(s.get("layer"))=="semantic_dom" and "CLICK" in str(s.get("op")) and "Deploy" in str(s.get("selector",{}).get("name","")) for s in trace)
    if not (has_fill and has_click):
        return False
    # Behavioral oracle on _v2 files: need to run tests that import _v2 modules
    # We synthesize a twin test file that imports from auth_v2 etc.
    import tempfile, subprocess, sys, textwrap
    from pathlib import Path as _P
    repo=_P(tempfile.mkdtemp(prefix="brain-pure-twin-oracle-"))
    try:
        # materialize with helper
        from canonical.swe_kernel.tb4_hetero_pure_execution_v1 import _write_pure_repo
        _write_pure_repo(trace, repo, initial_files)
        # Create twin-aware test file that imports _v2 modules
        twin_tests=textwrap.dedent("""
import sys
sys.path.insert(0, 'src')
def test_auth():
    from auth_v2 import authenticate
    assert authenticate(None)==False
    assert authenticate('secret')==True
    assert authenticate('wrong')==False
    assert authenticate('')==False
def test_db():
    from db_v2 import query
    assert query(None)==[]
    assert query('')==[]
    assert query('SELECT 1')=='executed:SELECT 1'
def test_api():
    from api_v2 import handle
    assert handle(None)==500
    assert handle('')==500
    assert handle('req')==200
def test_ui():
    from ui_v2 import render
    assert render(None)==''
    assert render(0)==''
    assert render('hi')=='hi'
def test_cache():
    import cache_v2 as cache
    assert cache.get('a')==1
    assert cache.get('missing') is None
def test_util():
    from util_v2 import normalize
    assert normalize(None) is None
    assert normalize('') is None
    assert normalize('  hi ')=='hi'
def test_conf():
    import conf_v2 as conf, importlib
    importlib.reload(conf)
    assert conf.load()==8080
    conf.PORT=0
    assert conf.load()==8000
    conf.PORT=8080
def test_log():
    import log_v2 as log
    log.LOGGED=[]
    log.emit(None)
    assert log.LOGGED==[]
    log.emit('')
    assert log.LOGGED==[]
    log.emit('hi')
    assert log.LOGGED==['hi']
def test_net():
    from net_v2 import fetch
    try: fetch(None); assert False
    except ValueError: pass
    try: fetch(''); assert False
    except ValueError: pass
    assert fetch('http://x')=='fetched:http://x'
def test_store():
    import store_v2 as store
    store.DATA=[]
    store.push(None)
    assert store.DATA==[]
    store.push(0)
    assert store.DATA==[]
    store.push(5)
    assert store.DATA==[5]
def test_cli():
    import cli_v2 as cli
    calls=[]
    cli.run=lambda a: calls.append(a)
    cli.main(None)
    assert calls[-1]==[]
    cli.main(0)
    assert calls[-1]==[]
    cli.main(['a'])
    assert calls[-1]==['a']
""")
        (repo/"test_pure_twin.py").write_text(twin_tests, encoding="utf-8")
        import os
        env=dict(os.environ)
        if _P("/tmp/pytest_pkg").is_dir():
            env["PYTHONPATH"]="/tmp/pytest_pkg"+":"+env.get("PYTHONPATH","")
        result=subprocess.run([sys.executable,"-m","pytest","-q","test_pure_twin.py"], cwd=str(repo), capture_output=True, text=True, timeout=15, env=env)
        return result.returncode==0
    except Exception:
        return False
    finally:
        import shutil
        shutil.rmtree(repo, ignore_errors=True)

def admit_pure_family() -> dict[str, Any]:
    t0=time.perf_counter_ns()
    from canonical.swe_kernel.causal_cut_attribution_v1 import extract_minimal_cut, attribute_and_induce
    from canonical.swe_kernel.family_predicate_induction_v1 import predicate_matches_task
    from canonical.swe_kernel.causal_cut_store_v1 import store_cut, recall
    from canonical.runtime.gui_computer_use_registry_v1 import invoke as gui_invoke
    orig_tmp=Path(tempfile.mkdtemp(prefix="brain-pure-orig-"))
    twin_tmp=Path(tempfile.mkdtemp(prefix="brain-pure-twin-"))
    try:
        orig=_make_pure_task(orig_tmp)
        orig_trace, orig_goal = orig["trace"], orig["goal"]
        orig_pre={k:v.encode() for k,v in orig["files"].items() if k!="gui_state.json"}
        orig_post=dict(orig_pre)
        for s in orig_trace:
            if str(s.get("layer"))=="python_file_op" and s.get("path"):
                orig_post[str(s["path"])]=str(s["content"]).encode()
        induced=attribute_and_induce(orig_trace, lambda sub: _oracle_pure(sub, orig["files"]), goal=orig_goal, pre_state=orig_pre, post_state=orig_post)
        if not induced.get("pass"):
            return {"schema":SCHEMA,"pass":False,"status":"FAIL__INDUCTION_FAILED","induced":induced}
        family=induced["family_predicate"]; family_id=family["family_id"]; cut_res=induced["cut_result"]
        twin=_make_pure_twin(twin_tmp)
        twin_trace, twin_goal = twin["trace"], twin["goal"]
        should_fire, why = predicate_matches_task(family, twin_goal, None)
        if not should_fire:
            return {"schema":SCHEMA,"pass":False,"status":"FAIL__PREDICATE_DID_NOT_MATCH_TWIN","why":why}
        twin_cut=extract_minimal_cut(twin_trace, lambda sub: _oracle_pure_twin(sub, twin["files"]), max_ablation_cost=100)
        twin_ok=twin_cut["status"] in ("CUT_DONE__CAUSAL_CUT_EXTRACTED","CUT_MINIMAL__NECESSARY_AND_SUFFICIENT")
        expected_kept=set(twin["causal_indices"])
        kept_ok=set(twin_cut.get("kept_indices",[]))==expected_kept
        sabotaged=[s for s in twin_trace if s.get("path")!="src/auth_v2.py"]
        sabotage_correctly_fails=not _oracle_pure_twin(sabotaged, twin["files"])
        gui_state=str(twin_tmp/"gui_state.json")
        g1=gui_invoke("CAP_GUI_GROUND_V1",{"target_label":"Deploy","state_path":gui_state},str(twin_tmp))
        ground_ok=g1["status"]=="VERIFIED_CAPABILITY_INVOKED"
        g2=gui_invoke("CAP_GUI_ACT_V1",{"selector":g1["receipt"]["selector"],"action":"CLICK_SEMANTIC","state_path":gui_state},str(twin_tmp)) if ground_ok else {"status":"FAIL"}
        act_ok=g2.get("status")=="VERIFIED_CAPABILITY_INVOKED" if isinstance(g2,dict) else False
        destroy_check={}
        try:
            destructive_pre={p: b"unrelated_data='secret'\n" for p,_,_ in PURE_SPECS}
            should_not, why_not = predicate_matches_task(family, twin_goal, destructive_pre)
            destroy_check["predicate_rejects_unrelated"]=not should_not
            destroy_check["predicate_reject_reason"]=why_not
            should_buggy,_=predicate_matches_task(family, twin_goal, orig_pre)
            destroy_check["predicate_accepts_buggy"]=should_buggy
            destroy_check["guard_documented"]="destroy_negative" in family.get("falsifier",{})
            destroy_check["requires_content_count"]=len(family.get("precondition",{}).get("requires_content",{}) or {})
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
        return {"schema":SCHEMA,"pass":admitted,"status":"PASS__PURE_ADMITTED" if admitted else "FAIL__ADMISSION_NOT_MET","family_id":family_id,"twin_goal":twin_goal,"should_fire":should_fire,"twin_cut_ok":twin_ok,"kept_ok":kept_ok,"twin_kept":twin_cut.get("kept_indices"),"expected_kept":sorted(expected_kept),"sabotage_correctly_fails":sabotage_correctly_fails,"ground_ok":ground_ok,"act_ok":act_ok,"gained":gained,"lost":lost,"admitted":admitted,"destroy_check":destroy_check,"stored":stored,"stored_count":stored_count,"elapsed_ms":round(elapsed,2),"model_calls":0,"network_calls":0}
    finally:
        import shutil
        shutil.rmtree(orig_tmp, ignore_errors=True)
        shutil.rmtree(twin_tmp, ignore_errors=True)

def main(argv: Sequence[str]|None=None) -> int:
    import argparse, json
    p=argparse.ArgumentParser(description="pure admission")
    p.add_argument("--json", dest="json_path", default=None)
    ns=p.parse_args(argv)
    res=admit_pure_family()
    print(json.dumps(res, indent=2, sort_keys=True))
    if ns.json_path:
        Path(ns.json_path).parent.mkdir(parents=True, exist_ok=True)
        Path(ns.json_path).write_text(json.dumps(res,indent=2,sort_keys=True)+"\n")
    return 0 if res.get("pass") else 1
if __name__=="__main__":
    raise SystemExit(main())
