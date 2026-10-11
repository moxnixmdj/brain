#!/usr/bin/env python3
"""Deterministic bounded multi-file, multi-edit test-guided Python repair loop.

This is a candidate constructor, not mergeability or semantic-completeness authority.
It composes the verified single-edit patch search basis into a bounded beam search:
baseline failure -> source inference/localization -> one-edit trials -> best partial
repairs -> second-edit trials -> independent replay -> multi-file unified diff.

No model calls, network calls, package installation, or persistent source mutation.
"""
from __future__ import annotations

import ast
import difflib
import hashlib
import importlib.util
import json
import os
import pathlib
import re
import subprocess
import sys
import time
from typing import Any, Iterable, Mapping

SCHEMA="PROJECT_BRAIN_PYTHON_TEST_GUIDED_REPAIR_LOOP_V1"

class RepairLoopError(RuntimeError):
    pass

def _load_patch_basis():
    path=pathlib.Path(__file__).resolve().with_name("python_test_guided_patch_search_v1.py")
    if not path.is_file():
        raise RepairLoopError("PATCH_BASIS_MISSING")
    spec=importlib.util.spec_from_file_location("project_brain_patch_basis_v1",path)
    if spec is None or spec.loader is None:
        raise RepairLoopError("PATCH_BASIS_LOAD_FAILED")
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def _safe_file(root:pathlib.Path,raw:Any,*,suffix:str|None=None)->pathlib.Path:
    p=(root/str(raw or "")).resolve()
    if p==root or root not in p.parents or not p.is_file() or p.is_symlink():
        raise RepairLoopError("PATH_INVALID:"+str(raw))
    if suffix and p.suffix!=suffix:
        raise RepairLoopError("PATH_SUFFIX_INVALID:"+str(raw))
    return p

def _sha(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()

def _purge(paths:Iterable[pathlib.Path])->None:
    for source in paths:
        try:
            cache=pathlib.Path(importlib.util.cache_from_source(str(source)))
        except (NotImplementedError,ValueError):
            continue
        try:
            cache.unlink()
        except FileNotFoundError:
            pass

def _run_tests(root:pathlib.Path,argv:list[str],timeout_s:int)->dict[str,Any]:
    if not argv or any(not isinstance(x,str) or not x for x in argv):
        raise RepairLoopError("TEST_ARGV_INVALID")
    exe=pathlib.Path(argv[0]).name.lower()
    if exe not in {pathlib.Path(sys.executable).name.lower(),"python","python3","py"}:
        raise RepairLoopError("TEST_EXECUTABLE_NOT_PYTHON")
    started=time.monotonic()
    try:
        proc=subprocess.run(argv,cwd=root,text=True,capture_output=True,timeout=timeout_s)
        return {
            "returncode":proc.returncode,
            "stdout":proc.stdout or "",
            "stderr":proc.stderr or "",
            "elapsed_s":round(time.monotonic()-started,6),
            "timed_out":False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "returncode":None,
            "stdout":exc.stdout or "",
            "stderr":exc.stderr or "",
            "elapsed_s":round(time.monotonic()-started,6),
            "timed_out":True,
        }

def _failure_metric(result:Mapping[str,Any])->dict[str,Any]:
    if result.get("timed_out"):
        return {"failures":10**6,"errors":10**6,"total":2*10**6,"parsed":False}
    text=str(result.get("stdout") or "")+"\n"+str(result.get("stderr") or "")
    failures=errors=None
    m=re.search(r"FAILED\s*\(([^)]*)\)",text)
    if m:
        failures=0; errors=0
        for key,val in re.findall(r"(failures|errors)=(\d+)",m.group(1)):
            if key=="failures": failures=int(val)
            elif key=="errors": errors=int(val)
    elif int(result.get("returncode") or 0)==0:
        failures=0; errors=0
    if failures is None or errors is None:
        marker_count=len(re.findall(r"(?m)^(?:FAIL|ERROR):",text))
        total=max(1,marker_count)
        return {"failures":None,"errors":None,"total":total,"parsed":False}
    return {"failures":failures,"errors":errors,"total":failures+errors,"parsed":True}

def _module_candidates(root:pathlib.Path,module:str)->list[pathlib.Path]:
    rel=pathlib.Path(*module.split("."))
    return [root/(str(rel)+".py"),root/rel/"__init__.py"]

def _infer_sources(root:pathlib.Path,tests:list[pathlib.Path],baseline:Mapping[str,Any],max_sources:int)->list[pathlib.Path]:
    candidates=[]
    def add(p:pathlib.Path):
        try: rp=p.resolve()
        except Exception: return
        if rp in tests or rp.suffix!=".py" or not rp.is_file() or rp.is_symlink():
            return
        if rp!=root and root not in rp.parents:
            return
        if rp not in candidates:
            candidates.append(rp)
    text=str(baseline.get("stdout") or "")+"\n"+str(baseline.get("stderr") or "")
    for raw in re.findall(r'File "([^"]+\.py)"',text):
        p=pathlib.Path(raw)
        if not p.is_absolute(): p=root/p
        add(p)
    for test in tests:
        tree=ast.parse(test.read_text(encoding="utf-8"),filename=str(test))
        for node in ast.walk(tree):
            names=[]
            if isinstance(node,ast.Import):
                names=[a.name for a in node.names]
            elif isinstance(node,ast.ImportFrom) and node.module:
                names=[node.module]
            for name in names:
                for mod in [name,name.split(".")[0]]:
                    for p in _module_candidates(root,mod):
                        add(p)
    return candidates[:max_sources]

def _restore(originals:dict[pathlib.Path,bytes])->None:
    for path,data in originals.items():
        path.write_bytes(data)
    _purge(originals)

def _apply_state(originals:dict[pathlib.Path,bytes],state:Mapping[pathlib.Path,str])->None:
    for path,data in originals.items():
        path.write_bytes(data)
    for path,text in state.items():
        path.write_text(text,encoding="utf-8")
    _purge(originals)

def _diff_many(root:pathlib.Path,originals:dict[pathlib.Path,bytes],state:Mapping[pathlib.Path,str])->str:
    chunks=[]
    for path in sorted(originals,key=lambda p:str(p.relative_to(root))):
        before=originals[path].decode("utf-8")
        after=state.get(path,before)
        if after==before: continue
        rel=str(path.relative_to(root)).replace("\\","/")
        chunks.append("".join(difflib.unified_diff(
            before.splitlines(True),after.splitlines(True),
            fromfile="a/"+rel,tofile="b/"+rel
        )))
    return "".join(chunks)

def _candidate_edits(basis,source:pathlib.Path,text:str,nums:list[Any],strings:list[str]):
    tree=ast.parse(text,filename=str(source))
    for key,desc,replacer in basis._candidate_specs(tree,nums,strings):
        candidate=basis._render_candidate(text,key,replacer)
        if candidate is None or candidate==text:
            continue
        yield desc,candidate

def _state_sha(root:pathlib.Path,originals:dict[pathlib.Path,bytes],state:Mapping[pathlib.Path,str])->str:
    h=hashlib.sha256()
    for path in sorted(originals,key=lambda p:str(p.relative_to(root))):
        rel=str(path.relative_to(root)).replace("\\","/")
        data=state.get(path,originals[path].decode("utf-8")).encode("utf-8")
        h.update(rel.encode()); h.update(b"\0"); h.update(data); h.update(b"\0")
    return h.hexdigest()

def run(args:Mapping[str,Any],root:str|os.PathLike[str])->dict[str,Any]:
    repo=pathlib.Path(root).resolve()
    if not isinstance(args,Mapping):
        raise RepairLoopError("ARGS_NOT_OBJECT")
    tests_raw=args.get("test_paths") or []
    if not isinstance(tests_raw,list) or not tests_raw:
        raise RepairLoopError("TEST_PATHS_REQUIRED")
    tests=[_safe_file(repo,x,suffix=".py") for x in tests_raw]
    timeout_s=max(1,min(int(args.get("timeout_s",60)),300))
    max_sources=max(1,min(int(args.get("max_sources",12)),64))
    max_candidates=max(1,min(int(args.get("max_candidates",4000)),30000))
    beam_width=max(1,min(int(args.get("beam_width",12)),128))
    max_edits=max(1,min(int(args.get("max_edits",2)),2))
    output=(repo/str(args.get("output_path") or "")).resolve()
    if output==repo or repo not in output.parents:
        raise RepairLoopError("OUTPUT_PATH_OUTSIDE_REPOSITORY")
    argv=args.get("test_argv")
    if argv is None:
        argv=[sys.executable]+[str(p.relative_to(repo)) for p in tests]
    if not isinstance(argv,list):
        raise RepairLoopError("TEST_ARGV_INVALID")
    argv=[str(x) for x in argv]

    baseline=_run_tests(repo,argv,timeout_s)
    if baseline["returncode"]==0:
        raise RepairLoopError("BASELINE_ALREADY_PASSES")
    if baseline["timed_out"]:
        raise RepairLoopError("BASELINE_TIMEOUT")
    baseline_metric=_failure_metric(baseline)

    source_raw=args.get("source_paths")
    if source_raw is None:
        sources=_infer_sources(repo,tests,baseline,max_sources)
        source_selection="INFERRED_FROM_TRACEBACK_AND_TEST_IMPORTS"
    else:
        if not isinstance(source_raw,list) or not source_raw:
            raise RepairLoopError("SOURCE_PATHS_INVALID")
        sources=[_safe_file(repo,x,suffix=".py") for x in source_raw]
        source_selection="EXPLICIT"
    sources=list(dict.fromkeys(sources))[:max_sources]
    if not sources:
        raise RepairLoopError("NO_SOURCE_FILES_LOCALIZED")

    originals={p:p.read_bytes() for p in sources}
    for p,b in originals.items():
        try: b.decode("utf-8")
        except UnicodeDecodeError as exc: raise RepairLoopError("SOURCE_NOT_UTF8:"+str(p.relative_to(repo))) from exc

    basis=_load_patch_basis()
    nums,strings=basis._test_literals(tests)
    attempts=[]
    passing=None
    partial=[]
    tested=0
    seen_states=set()

    try:
        for source in sources:
            base_text=originals[source].decode("utf-8")
            for desc,candidate in _candidate_edits(basis,source,base_text,nums,strings):
                if tested>=max_candidates: break
                state={source:candidate}
                sig=_state_sha(repo,originals,state)
                if sig in seen_states: continue
                seen_states.add(sig)
                tested+=1
                _apply_state(originals,state)
                rr=_run_tests(repo,argv,timeout_s)
                _restore(originals)
                metric=_failure_metric(rr)
                rec={"index":tested,"depth":1,"state_sha256":sig,"source_path":str(source.relative_to(repo)).replace("\\","/"),"mutation":desc,"returncode":rr["returncode"],"timed_out":rr["timed_out"],"metric":metric}
                attempts.append(rec)
                if rr["returncode"]==0 and not rr["timed_out"]:
                    passing=(state,[rec]); break
                partial.append((metric["total"],tested,state,[rec]))
            if passing or tested>=max_candidates: break

        if passing is None and max_edits>=2 and tested<max_candidates:
            partial.sort(key=lambda x:(x[0],x[1]))
            beam=partial[:beam_width]
            for _,_,first_state,chain in beam:
                _apply_state(originals,first_state)
                current={p:(first_state[p] if p in first_state else originals[p].decode("utf-8")) for p in sources}
                _restore(originals)
                for source in sources:
                    for desc,candidate in _candidate_edits(basis,source,current[source],nums,strings):
                        if tested>=max_candidates: break
                        state=dict(first_state)
                        state[source]=candidate
                        if all(state.get(p,originals[p].decode("utf-8"))==first_state.get(p,originals[p].decode("utf-8")) for p in sources):
                            continue
                        sig=_state_sha(repo,originals,state)
                        if sig in seen_states: continue
                        seen_states.add(sig)
                        tested+=1
                        _apply_state(originals,state)
                        rr=_run_tests(repo,argv,timeout_s)
                        _restore(originals)
                        metric=_failure_metric(rr)
                        rec={"index":tested,"depth":2,"state_sha256":sig,"source_path":str(source.relative_to(repo)).replace("\\","/"),"mutation":desc,"returncode":rr["returncode"],"timed_out":rr["timed_out"],"metric":metric}
                        attempts.append(rec)
                        if rr["returncode"]==0 and not rr["timed_out"]:
                            passing=(state,chain+[rec]); break
                    if passing or tested>=max_candidates: break
                if passing or tested>=max_candidates: break

        replay=[]
        replay_ok=False
        if passing:
            state,chain=passing
            replay_ok=True
            for _ in range(2):
                _apply_state(originals,state)
                rr=_run_tests(repo,argv,timeout_s)
                _restore(originals)
                replay.append({"returncode":rr["returncode"],"timed_out":rr["timed_out"],"metric":_failure_metric(rr),"elapsed_s":rr["elapsed_s"]})
                replay_ok=replay_ok and rr["returncode"]==0 and not rr["timed_out"]
            if not replay_ok:
                passing=None
    finally:
        _restore(originals)

    result={
        "schema":SCHEMA,
        "status":"PASS__VERIFIED_MULTI_EDIT_CANDIDATE_FOUND" if passing else "OPEN__NO_VERIFIED_CANDIDATE_IN_BOUNDED_SEARCH",
        "pass":passing is not None,
        "source_selection":source_selection,
        "source_paths":[str(p.relative_to(repo)).replace("\\","/") for p in sources],
        "source_sha256":{str(p.relative_to(repo)).replace("\\","/"):_sha(originals[p]) for p in sources},
        "test_paths":[str(p.relative_to(repo)).replace("\\","/") for p in tests],
        "test_sha256":{str(p.relative_to(repo)).replace("\\","/"):_sha(p.read_bytes()) for p in tests},
        "baseline_returncode":baseline["returncode"],
        "baseline_metric":baseline_metric,
        "tested_candidate_count":tested,
        "max_candidates":max_candidates,
        "beam_width":beam_width,
        "max_edits":max_edits,
        "model_dependency_count":0,
        "external_capability_provider_count":0,
        "incremental_spend_usd":0,
        "source_restored":all(p.read_bytes()==b for p,b in originals.items()),
        "attempts":attempts,
        "hard_nonclaims":[
            "NO_UNIVERSAL_PATCH_SEARCH_COMPLETENESS",
            "NO_MORE_THAN_TWO_EDIT_COMPLETENESS",
            "NO_NON_PYTHON_SUPPORT",
            "NO_GENERAL_NATURAL_LANGUAGE_TASK_SEMANTIC_AUTHORITY",
            "NO_SEMANTIC_CORRECTNESS_BEYOND_BOUND_TEST_ORACLE",
            "NO_MERGEABILITY_OR_FRONTIERCODE_SCORE_AUTHORITY"
        ]
    }
    if passing:
        state,chain=passing
        result.update({
            "winning_chain":chain,
            "winning_edit_count":len(chain),
            "candidate_state_sha256":_state_sha(repo,originals,state),
            "verification_replays":replay,
            "unified_diff":_diff_many(repo,originals,state),
        })
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    raw=output.read_bytes()
    result["output_path"]=str(output.relative_to(repo)).replace("\\","/")
    result["output_sha256"]=_sha(raw)
    result["output_verified"]=True
    return result
