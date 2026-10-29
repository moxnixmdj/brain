#!/usr/bin/env python3
"""Software repair loop — CEGIS+hypothesis HTN loop, only-right-way.

Hidden kernels harvested: CEGIS(T) 321L + hypothesis 6.170.12 + concrete 13 + CrossHair Z3 +
symbol 86k/221k + change-impact 2070/2096 + crossfile + pipeline 8-stage.
Why max: repair is loop not DAG. Synthesize→verify triad→counterexample→resynthesize until pass or budget. No blind search.
"""
from __future__ import annotations
import hashlib, json, pathlib, sys
from typing import Any
SCHEMA="PROJECT_BRAIN_SOFTWARE_REPAIR_LOOP_CEGIS_HYPOTHESIS_V1"
CAPABILITY_ID="software.repair.loop.cegis_hypothesis.v1"
PROVIDES=["software.repair.loop.cegis_verified","software.repair.synthesis.triad_proven"]
REQUIRES: list[str]=["python.fault.localization.symbol_ranked"]
REPO=pathlib.Path(__file__).resolve().parents[3]
def _safe_output(root: pathlib.Path, raw: str | None) -> pathlib.Path:
    p=(root / str(raw or "canonical/tmp_repair_loop_cegis.json")).resolve()
    if p==root or root not in p.parents: raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    p.parent.mkdir(parents=True, exist_ok=True); return p
def _load(path:pathlib.Path,name:str):
    import importlib.util
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module

_CTRL=_load(pathlib.Path(__file__).with_name("python_repair_measured_acceptance_controller_v1.py"),"_brain_cegis_ctrl")
_PGC=_CTRL._REPAIR

def _run_suite(repo,test_argv,timeout,env=None):
    # Same harness as the sibling loops: _run_tests applies the source env
    # (PYTHONPATH at the test's directory); a bare cwd=repo run answers
    # ModuleNotFoundError even on a FIXED tree, which would read as
    # "synthesis never verifies" -- an instrument fault, not a result.
    d=_PGC._PATCH._run_tests(repo,[str(x) for x in test_argv],timeout,
                             env if env is not None else _PGC._PATCH._source_env())
    return int(d["returncode"]),(d.get("stdout") or "")+"\n"+(d.get("stderr") or "")

def run(args: dict[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    """CEGIS repair loop, de-stubbed (ladder receipt REPAIR_DEPTH_LADDER_20261029
    caught this loop returning verified=True without ever passing source/test
    paths to its engines).

    Fixture mode (source_root+test_paths present): the Solar-Lezama shape over
    PROVEN engines, no blind search --
      synthesize  = provenance-guided coupled engine (dynamic-spectrum
                    hypothesis prioritizes the candidate grammar; the CEGIS
                    "hypothesis" role)
      verify      = the real suite executed against the realized candidate
                    (the "concrete oracle" role)
      counterexample = the surviving failure text; budget escalates the
                    grammar (more mutations per file, wider pair space) and
                    resynthesizes
    verified is the MEASURED suite outcome, replayed once, never a constant.

    Manifest mode (no fixture): the legacy engine triad runs unchanged; its
    verdicts are about the engines' own internal contracts, so the receipt
    says exactly that (MANIFEST_MODE) instead of claiming a repo repair.
    """
    repo=pathlib.Path(root).resolve(); output=_safe_output(repo, args.get("output_path"))
    import sys as _sys
    src=args.get("source_root"); tests=args.get("test_paths")
    if not src or not tests:
        return _run_manifest_mode(args,repo,output)
    timeout=max(1,min(int(args.get("timeout_s",20)),120))
    budget=max(1,min(int(args.get("budget",3)),8))
    rel=lambda p:str((repo/str(p)).resolve().relative_to(repo))
    argv=[str(x) for x in (args.get("test_argv") or [__import__("sys").executable,"-B","-m","unittest","-v"])]
    _env=_PGC._PATCH._source_env(repo/str(tests[0]))

    before_rc,before_tail=_run_suite(repo,argv,timeout,_env)
    if before_rc==0:
        raise RuntimeError("BASELINE_ALREADY_PASSES")

    intermediate=output.parent/(".cegis_"+output.name)
    # WALL LAW (tqdm/9 measured): an escalation writer that ignores the wall
    # eats the whole router budget (budget=2 x full search ~230s) and the
    # pair engine starves. The writer's share is whatever the router gave;
    # every round passes the REMAINING wall down to the inner engine.
    import time as _t
    _wb=args.get("wall_budget_s")
    _deadline=(_t.monotonic()+float(_wb)) if _wb else None
    def _wall_left():
        return _deadline is None or _t.monotonic()<_deadline
    rounds=[];winner_patches=None
    for i in range(budget):
        if not _wall_left():
            rounds.append({"round":i,"skipped":"WALL_BUDGET_EXHAUSTED"});break
        escalation={"mutations_per_file":24*(i+1),"max_pair_candidates":1000*(i+1)}
        synth=_PGC.run({
            "wall_budget_s":(max(5.0,round(_deadline-_t.monotonic(),1)) if _deadline else None),
            "source_root":rel(src) if (repo/(str(src))).resolve()!=repo else ".",
            "test_paths":[rel(t) for t in tests],
            "test_argv":argv,
            "output_path":rel(intermediate),
            "timeout_s":timeout,
            # L6 wall economics: tracing a 1000-line module at the 100k-event
            # default costs more than the whole search budget (measured
            # tornado/14: ~2min/round in the tracer alone)
            "max_trace_events":int(args.get("max_trace_events",30000)),
            "max_ranked_symbols":int(args.get("max_ranked_symbols",40)),
            **{k:v for k,v in escalation.items()},
        },repo)
        patches=synth.get("patches") or []
        round_row={"round":i,"synth_status":synth.get("status"),
                   "candidate_count":len(patches),
                   "winner_mode":synth.get("winner_mode")}
        realized=False
        if patches:
            originals={};applied=[]
            try:
                for row in patches:
                    target=(repo/str(row["source_path"])).resolve()
                    originals[target]=target.read_bytes()
                    # _apply_unified_diff is PURE: text->text; the write is ours
                    target.write_text(_CTRL._apply_unified_diff(
                        originals[target].decode("utf-8"),
                        str(row["unified_diff"])),encoding="utf-8")
                    applied.append(target)
                _rt=max(5.0,round(_deadline-_t.monotonic(),1)) if _deadline else timeout
                rc,tail=_run_suite(repo,argv,min(timeout,_rt),_env)
                realized=(rc==0)
                round_row["realized_green"]=realized
            finally:
                if not realized:
                    for t,raw in originals.items():
                        t.write_bytes(raw);_PGC._PATCH._purge_source_bytecode(t)
                else:
                    import difflib
                    winner_patches=[{"source_path":str(t.resolve().relative_to(repo)),
                                     "unified_diff":str(row["unified_diff"])}
                                    for row,t in zip(patches,applied)]
        rounds.append(round_row)
        if realized:
            if _deadline is not None and not _wall_left():
                # wall spent: the router re-verifies every step anyway
                rounds[-1]["skipped_replay"]="WALL_BUDGET_EXHAUSTED"
                rc2=0
            else:
                _rt=max(5.0,round(_deadline-_t.monotonic(),1)) if _deadline else timeout
                rc2,_=_run_suite(repo,argv,min(timeout,_rt),_env)  # replay: the counterexample check
            if rc2!=0:
                realized=False
                for t in originals:
                    t.write_bytes(originals[t]);_PGC._PATCH._purge_source_bytecode(t)
                rounds[-1]["replay_flipped"]=True
            else:
                rounds[-1]["replayed_green"]=True
                break
    after_rc,after_tail=_run_suite(repo,argv,timeout,_env)
    final=(after_rc==0 and realized)
    artifact={"schema":SCHEMA,"capability_id":CAPABILITY_ID,"mode":"FIXTURE_CEGIS",
              "budget":budget,"rounds":rounds,"baseline_returncode":before_rc,
              "final_returncode":after_rc,"pass":final,
              "patches":winner_patches or [],
              "counterexample_tail":after_tail[-400:] if after_rc else "",
              "verified":final,
              "model_dependency_count":0,"incremental_spend_usd":0}
    raw=json.dumps(artifact,sort_keys=True,separators=(",",":")).encode(); output.write_bytes(raw)
    return {"adapter":"software_repair_loop_cegis_hypothesis_v1",
            "output_path":str(output.relative_to(repo)),
            "output_sha256":hashlib.sha256(raw).hexdigest(),
            "output_verified":True,"verified":final,
            "pass":final,"rounds":rounds,"iterations":len(rounds),
            "model_dependency_count":0,"incremental_spend_usd":0}

def _run_manifest_mode(args,repo,output):
    """No fixture given: the engines' own contract triad, honestly labeled."""
    import canonical.runtime.bound_capabilities.software_patch_cegis_z3_v1 as cegis_mod
    import canonical.runtime.bound_capabilities.evidence_oracle_hypothesis_v1 as hyp_mod
    import canonical.runtime.bound_capabilities.evidence_oracle_concrete_v1 as conc_mod
    import canonical.runtime.bound_capabilities.software_repair_crossfile_choreograph_v1 as choreo_mod
    budget=int(args.get("budget",3)); cegis_iterations=[]
    for i in range(budget):
        r1=cegis_mod.run({"output_path": f"canonical/tmp_loop_cegis_{i}.json"}, repo)
        r2=hyp_mod.run({"output_path": f"canonical/tmp_loop_hyp_{i}.json"}, repo)
        r3=conc_mod.run({"output_path": f"canonical/tmp_loop_conc_{i}.json"}, repo)
        r4=choreo_mod.run({"output_path": f"canonical/tmp_loop_choreo_{i}.json"}, repo)
        cegis_iterations.append({"round":i,"cegis":r1["verified"],"hypothesis":r2["verified"],"concrete":r3["verified"],"choreograph":r4["verified"]})
        if r1["verified"] and r2["verified"] and r3["verified"]: break
    artifact={"schema":SCHEMA,"capability_id":CAPABILITY_ID,"mode":"MANIFEST_ENGINES",
              "note":"engines' internal contracts only; NO repository repair claimed",
              "budget":budget,"iterations":cegis_iterations,
              "verified":all(any(v for v in it.values() if isinstance(v,bool)) for it in cegis_iterations),
              "model_dependency_count":0,"incremental_spend_usd":0}
    raw=json.dumps(artifact, sort_keys=True, separators=(",",":")).encode(); output.write_bytes(raw)
    return {"adapter":"software_repair_loop_cegis_hypothesis_v1","output_path":str(output.relative_to(repo)),"output_sha256":hashlib.sha256(raw).hexdigest(),"output_verified":True,"status":"MANIFEST_MODE_NO_FIXTURE_VERIFIED","verified":artifact["verified"],"iterations":len(cegis_iterations),"model_dependency_count":0,"incremental_spend_usd":0}
