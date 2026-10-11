#!/usr/bin/env python3
"""Bounded coupled multi-edit Python patch search V1.

Explores a finite breadth-first prefix of AST edit sequences over repository-local
Python source candidates. Unlike the sequential repair loop, intermediate states
do not need to pass any witness; this can solve coupled defects that require two
or more edits before the supplied tests pass.

Candidate-only. Sources are always restored. No model/network/package install.
"""
from __future__ import annotations

import ast
import difflib
import hashlib
import json
import os
import pathlib
import sys
from typing import Any, Mapping

from canonical.runtime.bound_capabilities import python_failure_localizer_v1 as floc
from canonical.runtime.bound_capabilities import python_test_guided_patch_search_v1 as ptg

SCHEMA="PROJECT_BRAIN_PYTHON_COUPLED_PATCH_SEARCH_V1"

class CoupledPatchSearchError(RuntimeError):
    pass

def _safe(repo:pathlib.Path, raw:Any)->pathlib.Path:
    p=(repo/str(raw or "")).resolve()
    if p==repo or repo not in p.parents or not p.is_file() or p.is_symlink() or p.suffix!=".py":
        raise CoupledPatchSearchError("PATH_INVALID:"+str(raw))
    return p

def _sha(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()

def _apply(state:Mapping[pathlib.Path,str])->None:
    for path,text in state.items():
        path.write_text(text,encoding="utf-8")
        ptg._purge_source_bytecode(path)

def _evaluate(repo:pathlib.Path, tests:list[pathlib.Path], timeout_s:int)->dict[str,Any]:
    failures=0
    timed_out=False
    rows=[]
    for test in tests:
        r=ptg._run_tests(repo,[sys.executable,str(test.relative_to(repo))],timeout_s)
        ok=r["returncode"]==0 and not r["timed_out"]
        failures += 0 if ok else 1
        timed_out = timed_out or bool(r["timed_out"])
        rows.append({
            "test_path":str(test.relative_to(repo)).replace("\\","/"),
            "pass":ok,
            "returncode":r["returncode"],
            "timed_out":r["timed_out"],
        })
    return {"pass":failures==0 and not timed_out,"failure_count":failures,"timed_out":timed_out,"tests":rows}

def _state_key(sources:list[pathlib.Path],state:Mapping[pathlib.Path,str])->tuple[str,...]:
    return tuple(_sha(state[p].encode("utf-8")) for p in sources)

def _successors(
    state:Mapping[pathlib.Path,str],
    sources:list[pathlib.Path],
    tests:list[pathlib.Path],
    max_mutations_per_source:int,
):
    nums,strings=ptg._test_literals(tests)
    for source in sources:
        text=state[source]
        tree=ast.parse(text,filename=str(source))
        emitted=0
        for key,desc,replacer in ptg._candidate_specs(tree,nums,strings):
            if emitted>=max_mutations_per_source:
                break
            candidate=ptg._render_candidate(text,key,replacer)
            if candidate is None or candidate==text:
                continue
            emitted+=1
            nxt=dict(state); nxt[source]=candidate
            yield source,desc,nxt

def _diff(rel:str,before:str,after:str)->str:
    return "".join(difflib.unified_diff(
        before.splitlines(True),after.splitlines(True),
        fromfile="a/"+rel,tofile="b/"+rel
    ))

def run(args:Mapping[str,Any], root:str|os.PathLike[str])->dict[str,Any]:
    repo=pathlib.Path(root).resolve()
    if not isinstance(args,Mapping):
        raise CoupledPatchSearchError("ARGS_NOT_OBJECT")
    raw_tests=args.get("test_paths") or []
    if not isinstance(raw_tests,list) or not raw_tests:
        raise CoupledPatchSearchError("TEST_PATHS_REQUIRED")
    tests=[_safe(repo,x) for x in raw_tests]
    timeout_s=max(1,min(int(args.get("timeout_s",20)),120))
    max_depth=max(1,min(int(args.get("max_depth",2)),4))
    beam_width=max(1,min(int(args.get("beam_width",40)),500))
    max_states=max(1,min(int(args.get("max_states",1500)),20000))
    max_mut=max(1,min(int(args.get("max_mutations_per_source",80)),1000))
    output=(repo/str(args.get("output_path") or "")).resolve()
    if output==repo or repo not in output.parents:
        raise CoupledPatchSearchError("OUTPUT_PATH_OUTSIDE_REPOSITORY")

    baseline=_evaluate(repo,tests,timeout_s)
    if baseline["pass"]:
        raise CoupledPatchSearchError("BASELINE_ALREADY_PASSES")
    if baseline["timed_out"]:
        raise CoupledPatchSearchError("BASELINE_TIMEOUT")

    explicit=args.get("source_paths")
    if explicit is not None and not isinstance(explicit,list):
        raise CoupledPatchSearchError("SOURCE_PATHS_NOT_LIST")
    sources=[]
    if explicit:
        for raw in explicit:
            p=_safe(repo,raw)
            if p not in tests and p not in sources:
                sources.append(p)
    else:
        loc=floc.localize({"test_paths":[str(p.relative_to(repo)) for p in tests],"timeout_s":timeout_s},repo)
        for row in loc.get("candidates",[]):
            p=_safe(repo,row["source_path"])
            if p not in tests and p not in sources:
                sources.append(p)
    if not sources:
        raise CoupledPatchSearchError("NO_LOCALIZED_SOURCE_FILES")

    originals={p:p.read_bytes() for p in sources}
    base={p:raw.decode("utf-8") for p,raw in originals.items()}
    winner=None
    tested_states=0
    replay=[]
    seen={_state_key(sources,base)}
    frontier=[(base,[])]
    try:
        _apply(base)

        for depth in range(1,max_depth+1):
            candidates=[]
            for state,history in frontier:
                for source,desc,nxt in _successors(state,sources,tests,max_mut):
                    key=_state_key(sources,nxt)
                    if key in seen:
                        continue
                    seen.add(key)
                    _apply(nxt)
                    ev=_evaluate(repo,tests,timeout_s)
                    tested_states+=1
                    step=history+[{
                        "depth":depth,
                        "source_path":str(source.relative_to(repo)).replace("\\","/"),
                        "mutation":desc,
                    }]
                    if ev["pass"]:
                        winner=(nxt,step,ev)
                        break
                    candidates.append((ev["failure_count"],key,nxt,step))
                    if tested_states>=max_states:
                        break
                if winner or tested_states>=max_states:
                    break
            if winner or tested_states>=max_states:
                break
            candidates.sort(key=lambda x:(x[0],x[1]))
            frontier=[(state,history) for _,_,state,history in candidates[:beam_width]]
            if not frontier:
                break

        if winner:
            state,history,final_eval=winner
            _apply(state)
            ok=True
            for _ in range(2):
                ev=_evaluate(repo,tests,timeout_s)
                replay.append({"pass":ev["pass"],"failure_count":ev["failure_count"]})
                ok=ok and ev["pass"]
            if not ok:
                winner=None

        patches=[]
        final_history=[]
        winning_depth=None
        if winner:
            state,final_history,_=winner
            winning_depth=len(final_history)
            for path in sources:
                before=originals[path].decode("utf-8")
                after=state[path]
                if before!=after:
                    rel=str(path.relative_to(repo)).replace("\\","/")
                    patches.append({
                        "source_path":rel,
                        "candidate_sha256":_sha(after.encode("utf-8")),
                        "unified_diff":_diff(rel,before,after),
                    })
    finally:
        for path,raw in originals.items():
            path.write_bytes(raw)
            ptg._purge_source_bytecode(path)

    result={
        "schema":SCHEMA,
        "status":"PASS__VERIFIED_COUPLED_PATCH_FOUND" if winner else "OPEN__NO_VERIFIED_PATCH_IN_BOUNDED_SEARCH",
        "pass":winner is not None,
        "localized_source_paths":[str(p.relative_to(repo)).replace("\\","/") for p in sources],
        "max_depth":max_depth,
        "beam_width":beam_width,
        "max_states":max_states,
        "tested_state_count":tested_states,
        "winning_depth":winning_depth,
        "repair_history":final_history,
        "verification_replays":replay,
        "patches":patches if winner else [],
        "source_restored":all(p.read_bytes()==raw for p,raw in originals.items()),
        "model_dependency_count":0,
        "external_capability_provider_count":0,
        "incremental_spend_usd":0,
        "hard_nonclaims":[
            "NO_SEARCH_COMPLETENESS_BEYOND_DECLARED_DEPTH_BEAM_AND_STATE_BOUNDS",
            "NO_CAUSAL_CLAIM_FROM_LOCALIZATION_ALONE",
            "NO_NON_PYTHON_SUPPORT",
            "NO_SEMANTIC_CORRECTNESS_BEYOND_SUPPLIED_TESTS",
            "NO_SOURCE_WRITE_OR_PROMOTION_AUTHORITY",
            "NO_FRONTIERCODE_SCORE_CREDIT"
        ],
    }
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    result["output_path"]=str(output.relative_to(repo)).replace("\\","/")
    result["output_sha256"]=_sha(output.read_bytes())
    result["output_verified"]=True
    return result
