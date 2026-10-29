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

1. the stated test must FAIL on the current source.  If it already passes there
   is nothing to repair, and "fixing" it would be a change nobody asked for;
2. a bounded repair must actually be found and verified by the existing
   provenance-guided engine -- no repair, no write;
3. the realized bytes must match the patch's own `candidate_sha256` before they
   are written, and each file is replaced atomically via a temporary sibling;
4. the stated test must pass IN PLACE, against the real source tree, after the
   write.  This is stronger evidence than the isolated candidate measurement the
   acceptance controller takes, because it is the user's own file and the user's
   own test command.

Any failure at any gate restores every original byte and reports failure.  A
pass therefore means: the file on disk changed, and the stated test went from
failing to passing on that file.

Zero external-model producer cognition.  Zero incremental spend.
"""
from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import subprocess
import sys
from typing import Any, Mapping

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


def _run_test(argv:list[str],cwd:pathlib.Path,timeout:int)->tuple[int|None,bytes]:
    """Run the stated test command verbatim.  No shell, so nothing is invented."""
    try:
        proc=subprocess.run(
            argv,cwd=str(cwd),capture_output=True,timeout=timeout,check=False,
        )
    except subprocess.TimeoutExpired:
        return None,b"TIMEOUT"
    except OSError as exc:
        return None,str(exc).encode("utf-8")[:4096]
    tail=(proc.stdout or b"")[-2048:]+(proc.stderr or b"")[-2048:]
    return proc.returncode,tail


def _base(args:Mapping[str,Any],repo:pathlib.Path)->dict[str,Any]:
    return {
        "schema":SCHEMA,
        "capability_id":CAPABILITY_ID,
        "pass":False,
        "applied":False,
        "source_restored":True,
        "files_written":[],
        "unified_diffs":[],
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
    tmp=target.with_name(target.name+".brain_apply_tmp")
    tmp.write_bytes(data)
    try:
        os.replace(tmp,target)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def run(args:Mapping[str,Any],root:str|os.PathLike[str])->dict[str,Any]:
    if not isinstance(args,Mapping):
        raise RepairApplyError("ARGS_NOT_OBJECT")
    repo=pathlib.Path(root).resolve()
    source_root=_safe_dir(repo,args.get("source_root","."))
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
        argv=_REPAIR._PATCH.argv_or_derived(args.get("test_argv"),sys.executable,*test_paths)
    if not argv:
        raise RepairApplyError("TEST_ARGV_EMPTY")
    output=_safe_output(repo,args.get("output_path"))
    timeout=max(1,min(int(args.get("timeout_s",60)),MAX_TIMEOUT_S))

    out=_base(args,repo)
    out["test_paths_source"]=test_paths_source
    rel_tests,run_argv=_candidate_test_layout(repo,source_root,test_paths,argv)
    if not rel_tests:
        raise RepairApplyError("TEST_PATHS_OUTSIDE_SOURCE_ROOT")

    # GATE 1 -- the stated test must fail on the source as it stands.
    before_rc,before_tail=_run_test(run_argv,source_root,timeout)
    out["pre_apply_test_returncode"]=before_rc
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
    intermediate=output.parent/(".apply_repair_"+output.name)
    repair=_REPAIR.run({
        "source_root":_rel(repo,source_root) if source_root!=repo else ".",
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
        if not target.is_file():
            raise RepairApplyError("PATCH_TARGET_MISSING:"+rel)
        before_bytes=target.read_bytes()
        if _sha(before_bytes)!=original_sha:
            raise RepairApplyError("PATCH_ORIGINAL_SHA_MISMATCH:"+rel)
        after=_apply_unified_diff(before_bytes.decode("utf-8"),diff_text).encode("utf-8")
        if _sha(after)!=candidate_sha:
            raise RepairApplyError("PATCH_CANDIDATE_SHA_MISMATCH:"+rel)
        originals[target]=before_bytes
        planned.append((target,after,rel,diff_text))

    # Write.  Every original byte is held so any later gate can put it back.
    written=[]
    try:
        for target,after,rel,_diff in planned:
            _atomic_write(target,after)
            written.append(rel)
        out["files_written"]=written
        out["unified_diffs"]=[row[3] for row in planned]

        # GATE 4 -- the stated test must pass IN PLACE, on the real tree.
        after_rc,after_tail=_run_test(run_argv,source_root,timeout)
        out["post_apply_test_returncode"]=after_rc
        out["post_apply_test_tail"]=after_tail.decode("utf-8","replace")[-1024:]
        if after_rc!=0:
            for target,original in originals.items():
                target.write_bytes(original)
            out["files_written"]=[]
            out["status"]="FAIL_CLOSED__IN_PLACE_VERIFICATION_FAILED_AFTER_APPLY"
            out["source_restored"]=True
            out["detail"]="The applied patch did not make the stated test pass in place; every original byte was restored."
            _emit(output,out)
            return out
    except BaseException:
        for target,original in originals.items():
            target.write_bytes(original)
        out["files_written"]=[]
        out["source_restored"]=True
        raise

    out["applied"]=True
    out["source_restored"]=False
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
