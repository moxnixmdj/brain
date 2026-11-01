"""Apply a bounded, test-verified Python repair to the source tree.

Every other repair capability in the Brain deliberately stops short of writing:
`python.software.repair.measured_acceptance.v1` states in its own docstring that
"no patch is written to the source tree", and the test-guided loop carries the
hard non-claim `NO_SOURCE_WRITE_OR_PROMOTION_AUTHORITY`.  That division is
correct -- finding a patch and landing a patch are different authorities -- but
it left the sequence with no last step, so a repair that had been found and
verified was always thrown away and the source on disk never changed.

This capability is that last step, and it writes only behind four gates, each of
which fails closed:

1. both the stated command and the maintained runner for the declared test
   corpus must agree that the original project fails (or already passes);
2. a scoped retained proposal or the existing bounded search/fallback must
   produce a candidate; retained memory never bypasses application gates;
3. the realized bytes must match the patch's hashes and may not rewrite tests;
4. both the stated command and the declared corpus must pass IN PLACE after
   application, with the planned source bytes and declared tests unchanged;
5. optional generated regression tests are checked before any project commit.

Observed post-apply verification failures restore planned source and protected
selected-test bytes. This is not a crash-atomic filesystem transaction or an OS
sandbox. Trusted project tests and explicit applicability context are required.
A passing declared suite is not proof of complete request semantics.

With explicit retained_learning configuration, single-target successful repairs
may be taught to the existing scoped store using actual copied-project evidence.
Unavailable/corrupt memory falls back to the same solver without erasing state.

Zero external-model producer cognition.  Zero incremental spend.
"""
from __future__ import annotations

import ast
import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile
from typing import Any, Mapping

from canonical.runtime.bound_capabilities.python_test_corpus_discovery_v1 import is_test_file_name

SCHEMA="PROJECT_BRAIN_PYTHON_REPAIR_APPLY_VERIFIED_V1"
CAPABILITY_ID="python.software.repair.apply.verified.v1"
MODEL_DEPENDENCY_COUNT=0
EXTERNAL_MODEL_RUNTIME_CALLS=0

_HERE=pathlib.Path(__file__).resolve()

def _load(path:pathlib.Path,name:str):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None:
        raise RepairApplyError("MODULE_LOAD_FAILED:"+str(path))
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module

# Reuse the verified mechanisms rather than restating them: the same path
# guards, the same diff applier, the same candidate-layout rewrite and the same
# bounded repair engine the acceptance controller already composes.
_CTRL=_load(_HERE.with_name("python_repair_measured_acceptance_controller_v1.py"),"_brain_apply_ctrl")
_REPAIR=_CTRL._REPAIR

RepairApplyError=_CTRL.RepairAcceptanceError
_safe_dir=_CTRL._safe_dir
_safe_file=_CTRL._safe_file
_safe_output=_CTRL._safe_output
_rel=_CTRL._rel
_sha=_CTRL._sha
_apply_unified_diff=_CTRL._apply_unified_diff
_candidate_test_layout=_CTRL._candidate_test_layout

MAX_TIMEOUT_S=600


def _run_test(argv:list[str],cwd:pathlib.Path,timeout:int,env_paths:tuple=())->tuple[int|None,bytes]:
    """Run the stated test command verbatim.  No shell, so nothing is invented.

    The command line is the caller's; the IMPORT PATH is the tree's.  Measured
    2026-10-29: without the shared ``_source_env`` the gate that matters most --
    "the stated test passes IN PLACE, against the real source tree, after the
    write" -- could not run at all in a package layout.  The patch was found, the
    bytes were written, and the in-place verification then failed with the same
    ModuleNotFoundError the pre-apply gate had seen, so ``from pkg.calc import
    add`` was reported as FAIL_CLOSED__IN_PLACE_VERIFICATION_FAILED_AFTER_APPLY
    even though the candidate was correct.  One environment, one definition,
    shared with every other member of the repair family.
    """
    try:
        # A same-size edit within one filesystem timestamp tick must not read
        # the old source's bytecode cache during the final acceptance run.
        with tempfile.TemporaryDirectory(prefix="brain-apply-pycache-") as cache:
            proc=subprocess.run(
                argv,cwd=str(cwd),capture_output=True,timeout=timeout,check=False,
                env={**os.environ,**_REPAIR._PATCH._source_env(*(env_paths or (cwd,))),
                     "PYTHONPYCACHEPREFIX":cache},
            )
    except subprocess.TimeoutExpired:
        return None,b"TIMEOUT"
    except OSError as exc:
        return None,str(exc).encode("utf-8")[:4096]
    tail=(proc.stdout or b"")[-2048:]+(proc.stderr or b"")[-2048:]
    return proc.returncode,tail


def _corpus_test(test_paths, cwd, timeout, env_paths, completed=None):
    """Run the named corpus, not just a command that mentions its filenames.

    The maintained runner rejects empty/all-skipped suites and supports explicit
    assertion scripts. Counts can be unknown for that legacy script form; never
    invent a positive count or promote it to a typed TEST_SUITE receipt.
    """
    from canonical.runtime.bound_capabilities.python_repository_acceptance_measurement_v1 import _test_count
    argv=_REPAIR._PATCH.suite_argv(sys.executable,*test_paths)
    if completed is not None and completed[0]==argv:
        # The exact maintained runner/target argv has already executed. Reuse
        # that observation, never merely an arbitrary command's zero exit code.
        _,rc,tail=completed
    else:
        rc,tail=_run_test(argv,cwd,timeout,env_paths)
    return rc,tail,_test_count(tail.decode("utf-8","replace")) or None


def _restore_changed_tests(originals):
    changed=False
    for path,raw in originals.items():
        if not path.is_file() or path.read_bytes()!=raw:
            path.write_bytes(raw)
            changed=True
    return changed


def _base(args:Mapping[str,Any],repo:pathlib.Path)->dict[str,Any]:
    return {
        "schema":SCHEMA,
        "capability_id":CAPABILITY_ID,
        "pass":False,
        "applied":False,
        "source_restored":True,
        "files_written":[],
        "unified_diffs":[],
        "repair_search_invocations":0,
        "retained_learning":{"enabled":False},
        "pre_apply_test_returncode":None,
        "post_apply_test_returncode":None,
        "output_verified":False,
        "model_dependency_count":MODEL_DEPENDENCY_COUNT,
        "external_general_purpose_model_runtime_dependency_count":EXTERNAL_MODEL_RUNTIME_CALLS,
        "incremental_spend_usd":0,
        "terminal_authority":False,
        "hard_nonclaims":[
            "NO_GENERAL_PATCH_COMPLETENESS_ONLY_THE_BOUNDED_VERIFIED_SEARCH_FAMILIES",
            "A_PASSING_STATED_TEST_IS_NOT_PROOF_THE_WIDER_PROGRAM_IS_CORRECT",
            "NO_FRONTIERCODE_SCORE_OR_TERMINAL_CREDIT",
        ],
    }


def _atomic_write(target:pathlib.Path,data:bytes)->None:
    import time as _time
    old_st=target.stat()
    fd,name=tempfile.mkstemp(prefix=target.name+".brain_apply_",dir=target.parent)
    tmp=pathlib.Path(name)
    try:
        with os.fdopen(fd,"wb") as handle:
            handle.write(data)
            os.fchmod(handle.fileno(),old_st.st_mode & 0o777)
        distinct_s=min(int(old_st.st_mtime),int(_time.time()))-2
        os.utime(tmp,(distinct_s,distinct_s))
        os.replace(tmp,target)
        pyc_dir=target.parent/"__pycache__"
        if pyc_dir.is_dir():
            for pyc in pyc_dir.glob(f"{target.stem}.*.pyc"):
                pyc.unlink(missing_ok=True)
    finally:
        tmp.unlink(missing_ok=True)


def _try_live_trace_synth_patches(
    repo:pathlib.Path,
    source_root:pathlib.Path,
    exec_root:pathlib.Path,
    test_paths:list[pathlib.Path],
    run_argv:list[str],
    timeout:int,
    env_paths:tuple,
)->list[dict[str,Any]]:
    """Fallback pass: harvest live runtime assertion/call-frame I/O and synthesize verified diff."""
    import difflib
    try:
        from canonical.swe_kernel.whitebox_introspector_and_trace_synthesizer_v1 import (
            synthesize_candidates_for_file,
        )
    except Exception:
        return []
    test_set={p.resolve() for p in test_paths}
    py_files=[
        p for p in sorted(source_root.rglob("*.py"))
        if "__pycache__" not in p.parts
        and p.resolve() not in test_set
        and not p.name.startswith("test_")
        and not p.name.endswith("_test.py")
    ][:12]
    for src_f in py_files:
        orig_bytes=src_f.read_bytes()
        orig_txt=orig_bytes.decode("utf-8",errors="replace")
        try:
            cands=synthesize_candidates_for_file(src_f,exec_root,test_paths)
        except Exception:
            cands=[]
        for cand_txt in cands:
            cand_bytes=cand_txt.encode("utf-8")
            try:
                _atomic_write(src_f,cand_bytes)
                rc,_=_run_test(run_argv,exec_root,min(timeout,15),env_paths)
            finally:
                _atomic_write(src_f,orig_bytes)
            if rc==0:
                rel=_rel(repo,src_f)
                diff="".join(
                    difflib.unified_diff(
                        orig_txt.splitlines(keepends=True),
                        cand_txt.splitlines(keepends=True),
                        fromfile="a/"+rel,
                        tofile="b/"+rel,
                    )
                )
                return [{
                    "source_path":rel,
                    "unified_diff":diff,
                    "original_sha256":_sha(orig_bytes),
                    "candidate_sha256":_sha(cand_bytes),
                    "operator":"live_trace_observational_synthesis",
                }]
    return []


def _try_multistep_closed_loop_patches(
    repo:pathlib.Path,
    source_root:pathlib.Path,
    exec_root:pathlib.Path,
    test_paths:list[pathlib.Path],
    run_argv:list[str],
    timeout:int,
    env_paths:tuple,
    goal:str="",
)->tuple[list[dict[str,Any]],int]:
    """Multi-step closed-loop beam-search fallback for >=2-step, src-layout, or cross-module bugs."""
    import difflib
    if source_root==repo and (repo/"canonical"/"governance"/"REPO_INTEGRITY_POLICY_V1.json").is_file():
        return [],0
    try:
        from canonical.swe_kernel.multistep_repo_closed_loop_solver_v1 import (
            solve_repository_closed_loop,
        )
    except Exception:
        return [],0
    rel_tfiles=[
        p.relative_to(source_root).as_posix()
        for p in test_paths
        if source_root in p.parents
    ]
    res=solve_repository_closed_loop(
        source_root,
        goal=goal,
        test_files=rel_tfiles or None,
        apply_to_source=False,
        timeout_s=min(float(timeout),35.0),
    )
    if not res.get("ok") or not res.get("verified"):
        return [],0
    patched_map=res.get("patched_sources") or {}
    if not isinstance(patched_map,Mapping) or not patched_map:
        return [],0
    rows:list[dict[str,Any]]=[]
    backup:dict[pathlib.Path,bytes]={}
    try:
        for rel_sub,cand_txt in sorted(patched_map.items()):
            src_f=(source_root/str(rel_sub)).resolve()
            if not src_f.is_file() or repo not in src_f.parents:
                return [],0
            orig_bytes=src_f.read_bytes()
            cand_bytes=str(cand_txt).encode("utf-8")
            backup[src_f]=orig_bytes
            _atomic_write(src_f,cand_bytes)
            repo_rel=_rel(repo,src_f)
            diff="".join(
                difflib.unified_diff(
                    orig_bytes.decode("utf-8",errors="replace").splitlines(keepends=True),
                    str(cand_txt).splitlines(keepends=True),
                    fromfile="a/"+repo_rel,
                    tofile="b/"+repo_rel,
                )
            )
            rows.append({
                "source_path":repo_rel,
                "unified_diff":diff,
                "original_sha256":_sha(orig_bytes),
                "candidate_sha256":_sha(cand_bytes),
                "operator":"multistep_closed_loop_beam_search",
            })
        rc,_=_run_test(run_argv,exec_root,min(timeout,20),env_paths)
    finally:
        for fpath,ob in backup.items():
            _atomic_write(fpath,ob)
    if rc!=0:
        return [],0
    return rows,int(res.get("steps_taken") or len(rows))


def run(args:Mapping[str,Any],root:str|os.PathLike[str])->dict[str,Any]:
    if not isinstance(args,Mapping):
        raise RepairApplyError("ARGS_NOT_OBJECT")
    repo=pathlib.Path(root).resolve()
    source_root=_safe_dir(repo,args.get("source_root","."))
    if "test_paths" not in args or args.get("test_paths") is None:
        raise RepairApplyError("TEST_PATHS_REQUIRED")
    _stated_tests=[x for x in (args.get("test_paths") or []) if str(x).strip()]
    if _stated_tests:
        test_paths=[_safe_file(repo,x) for x in _stated_tests]
        test_paths_source="stated"
    else:
        # "Fix the failing test in the python source root D" names no file, and
        # which files are tests is a fact about the tree.  The command on the
        # next line was already derived when unstated; only this list was
        # missing.  This is the same fallback python_coupled_software_repair_loop
        # already had, reading the same shared module -- one rule, one place,
        # eleven consumers.  A tree with no tests raises rather than reporting a
        # green empty suite: test_count 0 with returncode 0 would be a pass for a
        # suite that was never found.
        from canonical.runtime.bound_capabilities.python_test_corpus_discovery_v1 import discover_test_files
        try:
            test_paths=discover_test_files(source_root)
            test_paths_source="discovered_under_source_root"
        except FileNotFoundError:
            sib_tests=source_root.parent/"tests" if source_root!=repo else None
            if sib_tests is not None and sib_tests.is_dir() and (sib_tests==repo or repo in sib_tests.parents):
                try:
                    test_paths=discover_test_files(sib_tests)
                    test_paths_source="discovered_under_source_root"
                except FileNotFoundError:
                    raise RepairApplyError("NO_TEST_FILES_UNDER_SOURCE_ROOT")
            else:
                raise RepairApplyError("NO_TEST_FILES_UNDER_SOURCE_ROOT")
    if not test_paths:
        raise RepairApplyError("TEST_PATHS_REQUIRED")
    if test_paths_source=="discovered_under_source_root":
        # A command line bound at COMPILE time cannot name a corpus that was only
        # found at RUN time.  Measured on 96015b9, with a fixture whose add(1,2)
        # returned -1 and whose test genuinely failed:
        #
        #   pre_apply_test_returncode  0
        #   applied                    false
        #   status                     PASS__STATED_TEST_ALREADY_PASSES_NOTHING_TO_REPAIR
        #
        # A LIE.  The bound argv was the collecting runner built for whatever
        # targets existed when the binder ran -- none -- so it collected zero
        # tests and returned 0, and gate 1 read that as "the test already
        # passes" and declined to repair a file that was broken.  Zero tests
        # passing is not a passing suite.  Derive the command from the tests
        # this run actually found; that is still the adapter's own suite_argv,
        # which is what the pinned binding requires, never an invented command.
        argv=[str(x) for x in _REPAIR._PATCH.suite_argv(sys.executable,*test_paths)]
    else:
        argv=_REPAIR._PATCH.argv_or_derived(args.get("test_argv") or [],sys.executable,*test_paths)
    if not argv:
        raise RepairApplyError("TEST_ARGV_EMPTY")
    output=_safe_output(repo,args.get("output_path"))
    timeout=max(1,min(int(args.get("timeout_s",60)),MAX_TIMEOUT_S))

    out=_base(args,repo)
    out["test_paths_source"]=test_paths_source
    exec_root=pathlib.Path(os.path.commonpath([str(source_root),*(str(p) for p in test_paths)])).resolve()
    if exec_root!=repo and repo not in exec_root.parents:
        raise RepairApplyError("EXEC_ROOT_OUTSIDE_REPOSITORY")
    rel_tests,run_argv=_candidate_test_layout(repo,exec_root,test_paths,argv)
    if not rel_tests:
        raise RepairApplyError("TEST_PATHS_OUTSIDE_SOURCE_ROOT")

    # GATE 1 -- the stated test must fail on the source as it stands.
    src_sub=source_root/"src"
    has_src_layout=src_sub.is_dir() and not (src_sub/"__init__.py").exists()
    env_paths=((src_sub,) if has_src_layout else ())+(source_root,*test_paths)
    protected_tests={p:p.read_bytes() for p in test_paths}
    before_rc,before_tail=_run_test(run_argv,exec_root,timeout,env_paths)
    out["pre_apply_test_returncode"]=before_rc
    corpus_rc,corpus_tail,corpus_count=_corpus_test(rel_tests,exec_root,timeout,env_paths,
                                                  (run_argv,before_rc,before_tail))
    out["pre_apply_corpus"]={"returncode":corpus_rc,"observed_test_count":corpus_count,
                              "shared_runner_enforces_nonempty":True}
    if _restore_changed_tests(protected_tests):
        out["status"]="FAIL_CLOSED__DECLARED_TESTS_CHANGED_DURING_BASELINE"
        _emit(output,out)
        return out
    if before_rc is None or corpus_rc is None:
        out["status"]="FAIL_CLOSED__BASELINE_VERIFICATION_INCOMPLETE"
        _emit(output,out)
        return out
    if (before_rc==0)!=(corpus_rc==0):
        out["status"]="FAIL_CLOSED__STATED_COMMAND_AND_DECLARED_CORPUS_DISAGREE"
        _emit(output,out)
        return out
    if before_rc==0:
        # The sentence asked for the stated test to pass.  It already does, and
        # that was measured rather than assumed, so the outcome the sentence
        # asked for holds and nothing needs writing.  Reporting this as a
        # failure told the caller the machine had crashed when it had in fact
        # checked and correctly declined to change a file that was not broken;
        # `applied` stays False and `files_written` stays empty so the pass
        # cannot be read as "I changed something".
        out["pass"]=True
        out["output_verified"]=True
        # SAY THE FACT IN THE VOCABULARY THE DOOR ALREADY HONOURS.  ``already_satisfied`` is how
        # every repair loop in this repository reports a green baseline (the door maps
        # ``BASELINE_ALREADY_PASSES`` onto it), and a request whose post-state already holds owes no
        # byte change.  This adapter measured exactly that -- ``applied`` false, ``files_written``
        # empty, ``pre_apply_test_returncode`` 0 -- and stated it only in ``status``, so the door's
        # source-change gate read the unchanged file as a promise it had failed to keep: measured
        # 2026-10-31, the idempotent sentence "Repair <src> so that the unit tests in <t> pass" on an
        # already-green tree came back FAIL_CLOSED__PROMISED_SOURCE_CHANGE_NOT_APPLIED.
        out["already_satisfied"]=True
        out["edited"]=False
        out["status"]="PASS__STATED_TEST_ALREADY_PASSES_NOTHING_TO_REPAIR"
        out["detail"]=(
            "The stated test passes on the current source, measured before any write, "
            "so the outcome the sentence asked for already holds and no file was changed."
        )
        _emit(output,out)
        return out
    out["pre_apply_test_tail"]=before_tail.decode("utf-8","replace")[-1024:]

    # GATE 2 -- a bounded repair must actually be found and verified.  The
    # engine restores the source itself; only its verified patches are used.
    goal_str=str(args.get("goal") or "")
    session=None
    config=args.get("retained_learning")
    if config is not None and (not isinstance(config,Mapping) or type(config.get("enabled")) is not bool):
        raise RepairApplyError("INVALID_RETAINED_LEARNING_CONFIG")
    if config is not None and config["enabled"]:
        from canonical.swe_kernel.retained_repair_session_v1 import RetainedRepairSession
        session=RetainedRepairSession(config,repo,source_root,exec_root,test_paths,timeout)
        out["retained_learning"]=session.metadata
    patches=session.propose() if session else []
    if patches:
        out["repair_status"]="PASS__SCOPED_RETAINED_PROPOSAL_PENDING_APPLICATION"
        out["repair_mode"]="scoped_retained_repair"
    elif has_src_layout:
        out["repair_search_invocations"]+=1
        patches,loop_steps=_try_multistep_closed_loop_patches(
            repo,source_root,exec_root,test_paths,run_argv,timeout,env_paths,goal=goal_str
        )
        if patches:
            out["repair_status"]="PASS__MULTISTEP_CLOSED_LOOP_BEAM_SEARCH"
            out["repair_mode"]="multistep_closed_loop_beam_search"
            out["closed_loop_steps_taken"]=loop_steps
    else:
        intermediate=output.parent/(".apply_repair_"+output.name)
        out["repair_search_invocations"]+=1
        repair=_REPAIR.run({
            "source_root":_rel(repo,exec_root) if exec_root!=repo else ".",
            "test_paths":[_rel(repo,p) for p in test_paths],
            "test_argv":argv,
            "output_path":_rel(repo,intermediate),
            "timeout_s":timeout,
            "max_guided_files":args.get("max_guided_files",4),
            "max_guided_symbols_per_file":args.get("max_guided_symbols_per_file",6),
            "mutations_per_file":args.get("mutations_per_file",24),
            "max_pair_candidates":args.get("max_pair_candidates",1000),
            "max_control_files":args.get("max_control_files",12),
            "max_control_symbols_per_file":args.get("max_control_symbols_per_file",12),
        },repo)
        patches=repair.get("patches") or []
        out["repair_status"]=repair.get("status")
    if (not isinstance(patches,list) or not patches) and not has_src_layout:
        patches=_try_live_trace_synth_patches(
            repo,source_root,exec_root,test_paths,run_argv,timeout,env_paths
        )
        if patches:
            out["repair_status"]="PASS__LIVE_TRACE_OBSERVATIONAL_SYNTHESIS"
            out["repair_mode"]="live_trace_observational_synthesis"
    if (not isinstance(patches,list) or not patches) and not has_src_layout:
        patches,loop_steps=_try_multistep_closed_loop_patches(
            repo,source_root,exec_root,test_paths,run_argv,timeout,env_paths,goal=goal_str
        )
        if patches:
            out["repair_status"]="PASS__MULTISTEP_CLOSED_LOOP_BEAM_SEARCH"
            out["repair_mode"]="multistep_closed_loop_beam_search"
            out["closed_loop_steps_taken"]=loop_steps
    if _restore_changed_tests(protected_tests):
        out["status"]="FAIL_CLOSED__DECLARED_TESTS_CHANGED_DURING_SEARCH"
        _emit(output,out)
        return out
    if not isinstance(patches,list) or not patches:
        out["status"]="OPEN__NO_VERIFIED_REPAIR_IN_BOUNDED_SEARCH"
        out["detail"]="Bounded search exhausted; the source was not modified."
        _emit(output,out)
        return out

    # GATE 3 -- realize the bytes and check them against the patch's own hash
    # before anything touches the tree.
    planned=[]
    originals={}
    for index,row in enumerate(patches):
        if not isinstance(row,Mapping):
            raise RepairApplyError("PATCH_ROW_NOT_OBJECT:"+str(index))
        rel=str(row.get("source_path") or "")
        diff_text=str(row.get("unified_diff") or "")
        original_sha=str(row.get("original_sha256") or "")
        candidate_sha=str(row.get("candidate_sha256") or "")
        target=(repo/rel).resolve()
        if target==repo or repo not in target.parents:
            raise RepairApplyError("PATCH_SOURCE_PATH_INVALID:"+rel)
        try:
            # The repair engine reports repo-relative paths; only a file that is
            # genuinely inside the stated source root may ever be written.
            target.relative_to(source_root)
        except ValueError as exc:
            raise RepairApplyError("PATCH_SOURCE_OUTSIDE_SOURCE_ROOT:"+rel) from exc
        if target in protected_tests or target.name=="conftest.py" or is_test_file_name(target.name):
            raise RepairApplyError("PATCH_MUST_NOT_REWRITE_TESTS:"+rel)
        if target in originals:
            raise RepairApplyError("DUPLICATE_PATCH_TARGET:"+rel)
        if not target.is_file():
            raise RepairApplyError("PATCH_TARGET_MISSING:"+rel)
        before_bytes=target.read_bytes()
        if _sha(before_bytes)!=original_sha:
            raise RepairApplyError("PATCH_ORIGINAL_SHA_MISMATCH:"+rel)
        after=_apply_unified_diff(before_bytes.decode("utf-8"),diff_text).encode("utf-8")
        if _sha(after)!=candidate_sha:
            raise RepairApplyError("PATCH_CANDIDATE_SHA_MISMATCH:"+rel)
        if after==before_bytes:
            raise RepairApplyError("PATCH_HAS_NO_SOURCE_EFFECT:"+rel)
        originals[target]=before_bytes
        planned.append((target,after,rel,diff_text))

    if bool(args.get("synthesize_regression_test")):
        # The shared generator uses a deterministic destination. Refuse an
        # existing file before any source write instead of overwriting a test.
        for target,after,_,_ in planned:
            old={n.name:ast.unparse(n) for n in ast.parse(originals[target]).body if isinstance(n,ast.FunctionDef)}
            for fn in ast.parse(after).body:
                if isinstance(fn,ast.FunctionDef) and old.get(fn.name)!=ast.unparse(fn):
                    destination=test_paths[0].parent/f"test_regression_{target.stem}_{fn.name}.py"
                    if destination.exists() or destination.is_symlink():
                        raise RepairApplyError("REGRESSION_TEST_DESTINATION_ALREADY_EXISTS")

    # Write.  Every original byte is held so any later gate can put it back.
    written=[]
    try:
        for target,after,rel,_diff in planned:
            _atomic_write(target,after)
            written.append(rel)
        out["files_written"]=written
        out["unified_diffs"]=[row[3] for row in planned]

        # GATE 4 -- the stated test must pass IN PLACE, on the real tree.
        after_rc,after_tail=_run_test(run_argv,exec_root,timeout,env_paths)
        out["post_apply_test_returncode"]=after_rc
        out["post_apply_test_tail"]=after_tail.decode("utf-8","replace")[-1024:]
        final_corpus_rc,_,final_count=_corpus_test(rel_tests,exec_root,timeout,env_paths,
                                                (run_argv,after_rc,after_tail))
        out["post_apply_corpus"]={"returncode":final_corpus_rc,"observed_test_count":final_count,
                                   "shared_runner_enforces_nonempty":True}
        tests_changed=_restore_changed_tests(protected_tests)
        source_changed=any(target.read_bytes()!=after for target,after,_,_ in planned)
        if after_rc!=0 or final_corpus_rc!=0 or tests_changed or source_changed:
            for target,original in originals.items():
                target.write_bytes(original)
            out["files_written"]=[]
            out["status"]="FAIL_CLOSED__IN_PLACE_VERIFICATION_FAILED_AFTER_APPLY"
            if tests_changed or source_changed:
                out["status"]="FAIL_CLOSED__SOURCE_OR_TESTS_CHANGED_DURING_VERIFICATION"
            out["source_restored"]=True
            out["detail"]="The applied patch did not make the stated test pass in place; every original byte was restored."
            _emit(output,out)
            return out
    except BaseException:
        _restore_changed_tests(protected_tests)
        for target,original in originals.items():
            target.write_bytes(original)
        out["files_written"]=[]
        out["source_restored"]=True
        raise

    out["applied"]=True
    out["source_restored"]=False
    reg_file=None
    try:
        if bool(args.get("synthesize_regression_test")) and planned and test_paths:
            from canonical.runtime.bound_capabilities.software_repair_crossfile_choreograph_v1 import (
                _synthesize_differential_regression_test,
            )
            edited_targets=[t for t,_,_,_ in planned]
            reg_file=_synthesize_differential_regression_test(
                exec_root,test_paths[0].parent,edited_targets,originals
            )
            import time as _time
            _back_s=int(_time.time())-2
            for _et in edited_targets:
                os.utime(_et,(_back_s,_back_s))
                _pc=_et.parent/"__pycache__"
                if _pc.is_dir():
                    for _pyc in _pc.glob(f"{_et.stem}.*.pyc"):
                        _pyc.unlink(missing_ok=True)
            if reg_file is not None and reg_file.is_file():
                reg_rel=_rel(repo,reg_file)
                out["regression_test_written"]=reg_rel
                out["files_written"]=list(out.get("files_written") or [])+[reg_rel]
                extra_rel=reg_file.relative_to(exec_root).as_posix()
                rc,_,count=_corpus_test([*rel_tests,extra_rel],exec_root,timeout,env_paths)
                changed=_restore_changed_tests(protected_tests)
                if rc!=0 or changed or any(t.read_bytes()!=raw for t,raw,_,_ in planned):
                    for t,raw in originals.items():
                        t.write_bytes(raw)
                    reg_file.unlink(missing_ok=True)
                    out.update({"pass":False,"applied":False,"source_restored":True,"files_written":[],
                                "status":"FAIL_CLOSED__GENERATED_REGRESSION_VERIFICATION_FAILED"})
                    _emit(output,out)
                    return out
                out["generated_regression_verification"]={"returncode":rc,"observed_test_count":count}
                if (exec_root/".git").is_dir() and exec_root!=repo:
                    rel_to_proj=[p.relative_to(exec_root).as_posix() for p in [*edited_targets,reg_file]]
                    subprocess.run(["git","add","--",*rel_to_proj],cwd=str(exec_root),capture_output=True,timeout=10)
                    subprocess.run(
                        ["git","-c","user.name=brain","-c","user.email=brain@local","commit","-q","-m","fix and regression test"],
                        cwd=str(exec_root),capture_output=True,timeout=10,
                    )
    except BaseException:
        _restore_changed_tests(protected_tests)
        for target,original in originals.items():
            _atomic_write(target,original)
        if reg_file is not None:
            reg_file.unlink(missing_ok=True)
        raise
    if session is not None:
        session.learn(originals)
    out["applied_source_sha256"]={rel:_sha(t.read_bytes()) for t,_,rel,_ in planned}
    out["declared_test_sha256"]={_rel(repo,p):_sha(raw) for p,raw in protected_tests.items()}
    out["pass"]=True
    out["output_verified"]=True
    out["status"]="PASS__VERIFIED_REPAIR_APPLIED_AND_VERIFIED_IN_PLACE"
    out["detail"]=(
        "The stated test failed before, the bounded verified repair was applied to the "
        "source tree, and the same stated test passes in place afterwards."
    )
    _emit(output,out)
    return out


def _emit(output:pathlib.Path,payload:Mapping[str,Any])->None:
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_bytes(json.dumps(payload,indent=1,sort_keys=True,ensure_ascii=True).encode("utf-8"))
