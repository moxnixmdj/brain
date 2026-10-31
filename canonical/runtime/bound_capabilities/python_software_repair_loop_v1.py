#!/usr/bin/env python3
"""Bounded donor-free multi-edit Python repair loop V1."""
from __future__ import annotations
import ast, hashlib, json, os, pathlib, sys
from typing import Any, Mapping
from canonical.runtime.bound_capabilities import python_test_guided_patch_search_v1 as ptg

SCHEMA="PROJECT_BRAIN_PYTHON_SOFTWARE_REPAIR_LOOP_V1"
class RepairLoopError(RuntimeError): pass

def _sha(b: bytes)->str: return hashlib.sha256(b).hexdigest()

def _safe(repo:pathlib.Path, raw:Any)->pathlib.Path:
    p=(repo/str(raw or "")).resolve()
    if p==repo or repo not in p.parents or not p.is_file() or p.is_symlink() or p.suffix!=".py":
        raise RepairLoopError("PATH_INVALID:"+str(raw))
    return p

def _imports(repo:pathlib.Path, test:pathlib.Path)->list[pathlib.Path]:
    # A file under source_root may be third-party and use syntax this interpreter cannot parse
    # (PEP 695 type aliases need 3.12). Such a file cannot be a repair candidate or a
    # localization target, so it contributes nothing - it must not abort the whole search,
    # which is the defect python_test_audit documents for timeouts one layer down.
    try:
        tree=ast.parse(test.read_text(encoding="utf-8"),filename=str(test))
    except (SyntaxError,ValueError,UnicodeDecodeError):
        return []
    names=[]
    for n in ast.walk(tree):
        if isinstance(n,ast.Import): names += [a.name for a in n.names]
        elif isinstance(n,ast.ImportFrom) and n.module: names.append(n.module)
    out=[]
    for name in names:
        rel=pathlib.Path(*name.split("."))
        for p in (repo/rel.with_suffix(".py"), repo/rel/"__init__.py"):
            p=p.resolve()
            if p.is_file() and repo in p.parents and p!=test and p not in out: out.append(p)
    return out

def _test(repo:pathlib.Path, test:pathlib.Path, timeout:int)->dict[str,Any]:
    return ptg._run_tests(repo,ptg.suite_argv(sys.executable,test),timeout,ptg._source_env(test))

def _materialize(source:pathlib.Path, tests:list[pathlib.Path], wanted:Mapping[str,Any])->str|None:
    text=source.read_text(encoding="utf-8")
    nums,strings=ptg._test_literals(tests)
    try:
        tree=ast.parse(text,filename=str(source))
    except (SyntaxError,ValueError):
        return None
    for key,desc,replacer in ptg._candidate_specs(tree,nums,strings):
        if desc==wanted:
            return ptg._render_candidate(text,key,replacer)
    return None

def run(args:Mapping[str,Any], root:str|os.PathLike[str])->dict[str,Any]:
    repo=pathlib.Path(root).resolve()
    if not isinstance(args,Mapping): raise RepairLoopError("ARGS_NOT_OBJECT")
    raw_tests=[x for x in (args.get("test_paths") or []) if str(x).strip()]
    if not isinstance(raw_tests,list): raise RepairLoopError("TEST_PATHS_REQUIRED")
    if not raw_tests:
        from canonical.runtime.bound_capabilities.python_test_corpus_discovery_v1 import discover_test_paths
        try: raw_tests=discover_test_paths(repo/str(args.get("source_root") or "."))
        except FileNotFoundError: raise RepairLoopError("NO_TEST_FILES_UNDER_SOURCE_ROOT")
    if not raw_tests: raise RepairLoopError("TEST_PATHS_REQUIRED")
    tests=[_safe(repo,x) for x in raw_tests]
    explicit=args.get("source_paths")
    if explicit is not None and not isinstance(explicit,list): raise RepairLoopError("SOURCE_PATHS_NOT_LIST")
    timeout=max(1,min(int(args.get("timeout_s",20)),120))
    max_edits=max(1,min(int(args.get("max_edits",6)),20))
    max_candidates=max(1,min(int(args.get("max_candidates",600)),5000))
    output=(repo/str(args.get("output_path") or "")).resolve()
    if output==repo or repo not in output.parents: raise RepairLoopError("OUTPUT_PATH_OUTSIDE_REPOSITORY")

    sources=[]
    if explicit:
        for x in explicit:
            p=_safe(repo,x)
            if p not in tests and p not in sources: sources.append(p)
    for t in tests:
        for p in _imports(repo,t):
            if p not in sources: sources.append(p)
    if not sources: raise RepairLoopError("NO_LOCALIZED_SOURCE_FILES")

    from canonical.runtime.write_authority_v1 import check_report
    check_report(repo, output, [*sources, *tests])
    originals={p:p.read_bytes() for p in sources}
    baseline=[_test(repo,t,timeout) for t in tests]
    if all(r["returncode"]==0 for r in baseline): raise RepairLoopError("BASELINE_ALREADY_PASSES")
    history=[]; final=False; replays=[]; probes=0
    probe=(output.parent/(".repair_probe_"+output.name)).resolve()
    try:
        for cycle in range(1,max_edits+1):
            failing=[t for t in tests if _test(repo,t,timeout)["returncode"]!=0]
            if not failing:
                final=True; break
            target=failing[0]
            applied=False
            ordered=[]
            for p in _imports(repo,target)+sources:
                if p not in ordered: ordered.append(p)
            for source in ordered:
                try:
                    res=ptg.run({
                        "source_path":str(source.relative_to(repo)),
                        "test_paths":[str(target.relative_to(repo))],
                        "test_argv":ptg.suite_argv(sys.executable,target),
                        "output_path":str(probe.relative_to(repo)),
                        "timeout_s":timeout,
                        "max_candidates":max_candidates,
                    },repo)
                except ptg.PatchSearchError:
                    continue
                finally:
                    if probe.exists(): probe.unlink()
                probes += int(res.get("tested_candidate_count",0))
                if not res.get("pass"): continue
                candidate=_materialize(source,[target],res["winning_mutation"])
                if candidate is None: raise RepairLoopError("WINNER_RECONSTRUCTION_FAILED")
                before=source.read_text(encoding="utf-8")
                source.write_text(candidate,encoding="utf-8"); ptg._purge_source_bytecode(source)
                history.append({
                    "cycle":cycle,
                    "test_path":str(target.relative_to(repo)).replace("\\","/"),
                    "source_path":str(source.relative_to(repo)).replace("\\","/"),
                    "mutation":res["winning_mutation"],
                    "before_sha256":_sha(before.encode()),
                    "after_sha256":_sha(candidate.encode()),
                })
                applied=True; break
            if not applied: break

        final=all(_test(repo,t,timeout)["returncode"]==0 for t in tests)
        if final:
            for _ in range(2):
                ok=all(_test(repo,t,timeout)["returncode"]==0 for t in tests)
                replays.append({"pass":ok})
                final=final and ok
        patches=[]
        if final:
            import difflib
            for p,raw in originals.items():
                before=raw.decode("utf-8"); after=p.read_text(encoding="utf-8")
                if before!=after:
                    rel=str(p.relative_to(repo)).replace("\\","/")
                    patches.append({"source_path":rel,"unified_diff":"".join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile="a/"+rel,tofile="b/"+rel))})
    finally:
        for p,raw in originals.items():
            p.write_bytes(raw); ptg._purge_source_bytecode(p)
        if probe.exists(): probe.unlink()

    result={
        "schema":SCHEMA,
        "status":"PASS__VERIFIED_MULTI_EDIT_PATCH_FOUND" if final else "OPEN__NO_VERIFIED_PATCH_IN_BOUNDED_LOOP",
        "pass":final,
        "localized_source_paths":[str(p.relative_to(repo)).replace("\\","/") for p in sources],
        "edits_applied":len(history),
        "repair_history":history,
        "tested_candidate_count":probes,
        "verification_replays":replays,
        "patches":patches if final else [],
        "source_restored":all(p.read_bytes()==raw for p,raw in originals.items()),
        "model_dependency_count":0,
        "external_capability_provider_count":0,
        "incremental_spend_usd":0,
        "hard_nonclaims":["NO_ARBITRARY_SOFTWARE_REPAIR_COMPLETENESS","NO_NON_PYTHON_SUPPORT","NO_SEMANTIC_CORRECTNESS_BEYOND_BOUND_TEST_WITNESSES","NO_SOURCE_WRITE_OR_PROMOTION_AUTHORITY","NO_FRONTIERCODE_SCORE_CREDIT"],
    }
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    result["output_path"]=str(output.relative_to(repo)).replace("\\","/")
    result["output_sha256"]=_sha(output.read_bytes()); result["output_verified"]=True
    return result
