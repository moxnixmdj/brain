"""Atomic bounded Python repair -> candidate realization -> measured acceptance V8.

This controller composes only Brain-owned verified mechanisms:
1. provenance-guided bounded Python repair produces candidate diffs and restores source;
2. diffs are realized in an isolated copied workspace and candidate hashes are checked;
3. the realized candidate repository is measured by content-addressed execution;
4. the raw-task objective acceptance gate consumes only that measurement receipt.

No semantic residual is converted into success. No patch is written to the source tree.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import pathlib
import re
import shutil
import sys
import tempfile
from typing import Any, Mapping

from canonical.runtime import acceptance_clause_v1 as acceptance_clause
from canonical.runtime.swe_task_artifacts_v1 import fresh_output, publish_report

SCHEMA="PROJECT_BRAIN_PYTHON_REPAIR_MEASURED_ACCEPTANCE_CONTROLLER_V1"
CAPABILITY_ID="python.software.repair.measured_acceptance.v1"
MODEL_DEPENDENCY_COUNT=0
EXTERNAL_MODEL_RUNTIME_CALLS=0

class RepairAcceptanceError(RuntimeError):
    pass

def _load(path:pathlib.Path,name:str):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None:
        raise RepairAcceptanceError("MODULE_LOAD_FAILED:"+str(path))
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    return module

_HERE=pathlib.Path(__file__).resolve()
_REPAIR=_load(_HERE.with_name("python_provenance_guided_coupled_repair_v1.py"),"_brain_v8_repair")
_MEASURE=_load(_HERE.with_name("python_repository_acceptance_measurement_v1.py"),"_brain_v8_measure")
_ACCEPT=_load(_HERE.parent.parent/"python_measured_objective_acceptance_v1.py","_brain_v8_accept")

def _sha(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()

def _rel(root:pathlib.Path,p:pathlib.Path)->str:
    return str(p.relative_to(root)).replace("\\","/")

def _safe_dir(repo:pathlib.Path,raw:Any)->pathlib.Path:
    p=(repo/str(raw or ".")).resolve()
    if p!=repo and repo not in p.parents:
        raise RepairAcceptanceError("SOURCE_ROOT_OUTSIDE_REPOSITORY")
    if not p.is_dir() or p.is_symlink():
        raise RepairAcceptanceError("SOURCE_ROOT_INVALID")
    return p

def _safe_file(repo:pathlib.Path,raw:Any)->pathlib.Path:
    p=(repo/str(raw or "")).resolve()
    if p==repo or repo not in p.parents or not p.is_file() or p.is_symlink():
        raise RepairAcceptanceError("TEST_PATH_INVALID:"+str(raw))
    return p

def _safe_output(repo:pathlib.Path,raw:Any)->pathlib.Path:
    p=(repo/str(raw or "")).resolve()
    if p==repo or repo not in p.parents:
        raise RepairAcceptanceError("OUTPUT_PATH_OUTSIDE_REPOSITORY")
    return p

_HUNK=re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")

def _apply_unified_diff(original:str,diff_text:str)->str:
    lines=diff_text.splitlines(keepends=True)
    i=0
    while i<len(lines) and not lines[i].startswith("@@ "):
        i+=1
    if i>=len(lines):
        raise RepairAcceptanceError("PATCH_HUNK_MISSING")
    src=original.splitlines(keepends=True)
    out=[]
    cursor=0
    while i<len(lines):
        header=lines[i].rstrip("\r\n")
        m=_HUNK.match(header)
        if not m:
            raise RepairAcceptanceError("PATCH_HUNK_HEADER_INVALID")
        old_start=int(m.group(1));old_count=int(m.group(2) or "1")
        start_index=old_start-1
        if start_index<cursor or start_index>len(src):
            raise RepairAcceptanceError("PATCH_HUNK_RANGE_INVALID")
        out.extend(src[cursor:start_index])
        cursor=start_index
        consumed=0
        i+=1
        while i<len(lines) and not lines[i].startswith("@@ "):
            row=lines[i]
            if row.startswith("\\ No newline at end of file"):
                i+=1
                continue
            if not row:
                raise RepairAcceptanceError("PATCH_ROW_EMPTY")
            prefix=row[0]
            body=row[1:]
            if prefix==" ":
                if cursor>=len(src) or src[cursor]!=body:
                    raise RepairAcceptanceError("PATCH_CONTEXT_MISMATCH")
                out.append(src[cursor]);cursor+=1;consumed+=1
            elif prefix=="-":
                if cursor>=len(src) or src[cursor]!=body:
                    raise RepairAcceptanceError("PATCH_DELETE_MISMATCH")
                cursor+=1;consumed+=1
            elif prefix=="+":
                out.append(body)
            else:
                raise RepairAcceptanceError("PATCH_ROW_PREFIX_INVALID")
            i+=1
        if consumed!=old_count:
            raise RepairAcceptanceError("PATCH_OLD_COUNT_MISMATCH")
    out.extend(src[cursor:])
    return "".join(out)

def _candidate_test_layout(
    repo:pathlib.Path,source_root:pathlib.Path,test_paths:list[pathlib.Path],argv:list[str]
)->tuple[list[str],list[str]]:
    rel_tests=[]
    for p in test_paths:
        try:
            rel_tests.append(_rel(source_root,p))
        except ValueError as exc:
            raise RepairAcceptanceError("TEST_OUTSIDE_SOURCE_ROOT:"+_rel(repo,p)) from exc
    rewritten=[]
    for token in argv:
        if token==argv[0]:
            rewritten.append(token)
            continue
        raw=pathlib.Path(token)
        candidate=None
        on_disk=False
        try:
            if not raw.is_absolute():
                candidate=(repo/raw).resolve()
            elif raw.is_absolute():
                candidate=raw.resolve()
            on_disk=candidate.is_file() or candidate.is_dir()
        except OSError:
            # A test argv token is a command argument, not necessarily a path.
            # ``python3 -c '<harness program>'`` carries a whole test runner in
            # ONE token, and stat() on that name fails with ENAMETOOLONG, which
            # Path.is_file()/is_dir() re-raise instead of answering False.  Such a token
            # is not a file inside the source root, so it must pass through
            # verbatim -- exactly as every other non-file token does -- rather
            # than abort the measurement.
            on_disk=False
        if on_disk and (candidate==source_root or source_root in candidate.parents):
            rewritten.append(_rel(source_root,candidate))
        else:
            rewritten.append(token)
    return rel_tests,rewritten

def _realize_candidate(
    repo:pathlib.Path,source_root:pathlib.Path,patches:list[Mapping[str,Any]],candidate_root:pathlib.Path
)->list[dict[str,Any]]:
    shutil.copytree(
        source_root,candidate_root,
        ignore=shutil.ignore_patterns(".git","__pycache__","*.pyc",".pytest_cache"),
    )
    realized=[]
    for index,row in enumerate(patches):
        if not isinstance(row,Mapping):
            raise RepairAcceptanceError("PATCH_ROW_NOT_OBJECT:"+str(index))
        source_path=str(row.get("source_path") or "")
        original_sha=str(row.get("original_sha256") or "")
        candidate_sha=str(row.get("candidate_sha256") or "")
        diff_text=str(row.get("unified_diff") or "")
        original_path=(repo/source_path).resolve()
        if original_path==repo or repo not in original_path.parents or not original_path.is_file():
            raise RepairAcceptanceError("PATCH_SOURCE_PATH_INVALID:"+source_path)
        try:
            relative=original_path.relative_to(source_root)
        except ValueError as exc:
            raise RepairAcceptanceError("PATCH_SOURCE_OUTSIDE_SOURCE_ROOT:"+source_path) from exc
        target=(candidate_root/relative).resolve()
        if candidate_root not in target.parents or not target.is_file():
            raise RepairAcceptanceError("CANDIDATE_TARGET_INVALID:"+source_path)
        raw=target.read_bytes()
        if _sha(raw)!=original_sha:
            raise RepairAcceptanceError("PATCH_ORIGINAL_SHA_MISMATCH:"+source_path)
        try:
            before=raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise RepairAcceptanceError("PATCH_SOURCE_NOT_UTF8:"+source_path) from exc
        after=_apply_unified_diff(before,diff_text)
        after_raw=after.encode("utf-8")
        if _sha(after_raw)!=candidate_sha:
            raise RepairAcceptanceError("PATCH_CANDIDATE_SHA_MISMATCH:"+source_path)
        target.write_bytes(after_raw)
        realized.append({
            "source_path":source_path,
            "candidate_relative_path":str(relative).replace("\\","/"),
            "original_sha256":original_sha,
            "candidate_sha256":candidate_sha,
        })
    return realized

def _validate_contract_checks(checks, source_root):
    """Reject malformed requests before spending time on repair search."""
    from canonical.runtime.bound_capabilities import evidence_oracle_hypothesis_v1 as oracle
    if not isinstance(checks, list) or not checks or len(checks) > 16:
        raise RepairAcceptanceError("CONTRACT_CHECKS_INVALID")
    validated = []
    allowed = {"source_path", "timeout_s", "max_examples", "min_value", "max_value"}
    for check in checks:
        if not isinstance(check, Mapping) or set(check) - allowed:
            raise RepairAcceptanceError("CONTRACT_CHECK_INVALID")
        path = (source_root / str(check.get("source_path") or "")).resolve()
        if source_root not in path.parents or not path.is_file() or path.suffix != ".py":
            raise RepairAcceptanceError("CONTRACT_SOURCE_INVALID")
        limits = {
            "timeout_s": oracle._integer(check, "timeout_s", 10, 1, 120),
            "max_examples": oracle._integer(check, "max_examples", 50, 1, 5000),
            "min_value": oracle._integer(check, "min_value", -100, -(2**63), 2**63 - 1),
            "max_value": oracle._integer(check, "max_value", 100, -(2**63), 2**63 - 1),
        }
        if limits["min_value"] > limits["max_value"]:
            raise RepairAcceptanceError("CONTRACT_INTEGER_RANGE_INVALID")
        validated.append({"source_path": str(path.relative_to(source_root)), **limits})
    return validated


def _check_candidate_contracts(checks, candidate_root, temp_root):
    """Check the realized candidate, never the original source or a demo.

    These two input enumerators share a contract evaluator. This is additional
    concrete/property evidence, not a claim of independent semantic oracles.
    """
    from concurrent.futures import ThreadPoolExecutor
    from canonical.runtime.bound_capabilities import evidence_oracle_concrete_v1 as concrete
    from canonical.runtime.bound_capabilities import evidence_oracle_hypothesis_v1 as hypothesis

    if not isinstance(checks, list) or not checks or len(checks) > 16:
        raise RepairAcceptanceError("CONTRACT_CHECKS_INVALID")
    records = []
    with ThreadPoolExecutor(max_workers=2) as workers:
        for index, check in enumerate(checks):
            if not isinstance(check, Mapping):
                raise RepairAcceptanceError("CONTRACT_CHECK_INVALID")
            path = (candidate_root / str(check.get("source_path") or "")).resolve()
            if candidate_root not in path.parents or not path.is_file() or path.suffix != ".py":
                raise RepairAcceptanceError("CONTRACT_SOURCE_INVALID")
            source_sha = _sha(path.read_bytes())
            common = {"source_path": _rel(temp_root, path),
                      "timeout_s": check.get("timeout_s", 10)}
            cargs = {**common, "output_path": f"contracts/{index}_concrete.json"}
            hargs = {**common, "output_path": f"contracts/{index}_hypothesis.json"}
            for key in ("max_examples", "min_value", "max_value"):
                if key in check:
                    hargs[key] = check[key]
            cf = workers.submit(concrete.run, cargs, temp_root)
            hf = workers.submit(hypothesis.run, hargs, temp_root)
            c, h = cf.result(), hf.result()
            unchanged = source_sha == _sha(path.read_bytes())
            passed = unchanged and all(
                r.get("check_completed") is True and r.get("verified") is True
                and r.get("checked", 0) > 0 and not r.get("violations")
                and r.get("source_sha256") == source_sha for r in (c, h)
            )
            records.append({"source_path": str(path.relative_to(candidate_root)),
                            "source_sha256": source_sha, "source_unchanged": unchanged,
                            "pass": passed,
                            "concrete": {k: v for k, v in c.items() if k != "output_path"},
                            "hypothesis": {k: v for k, v in h.items() if k != "output_path"}})
    return records


def _run_search(args, repair_args, repo, source_root, scratch):
    """Coordinate existing engines; exhaustion is not an execution failure.

    No catches convert crashes/replay failures into another search attempt.
    All branch results must restore the same source and explicit test inputs.
    """
    strategy = args.get("repair_strategy", "guided")
    if strategy not in ("guided", "iterative_then_guided"):
        raise RepairAcceptanceError("REPAIR_STRATEGY_UNSUPPORTED")
    attempts = []
    if strategy == "iterative_then_guided":
        from canonical.runtime.canonical_tree_attestation_v1 import tree_manifest
        # Ignore only this owned path, not every directory sharing its basename.
        owned_prefix = (scratch.relative_to(source_root).as_posix() + "/"
                        if scratch.is_relative_to(source_root) else None)

        def source_manifest():
            manifest = tree_manifest(source_root)
            return manifest, [row for row in manifest["files"]
                              if owned_prefix is None or not row["path"].startswith(owned_prefix)]

        before, before_files = source_manifest()
        if before["pass"] is not True:
            raise RepairAcceptanceError("PORTFOLIO_SOURCE_TREE_INVALID")
        tests = {path: _sha((repo / path).read_bytes()) for path in repair_args["test_paths"]}

        def check_restored(result):
            after, after_files = source_manifest()
            if (result.get("source_restored") is not True or after["pass"] is not True
                    or after_files != before_files
                    or any(_sha((repo / path).read_bytes()) != sha for path, sha in tests.items())):
                raise RepairAcceptanceError("PORTFOLIO_INPUT_DRIFT")

        iterative_args = {key: repair_args[key] for key in
                          ("source_root", "test_paths", "test_argv", "timeout_s")}
        iterative_args.update({"output_path": _rel(repo, scratch / "iterative.json"),
                              "max_rounds": args.get("iterative_max_rounds", 6),
                              "max_files": args.get("max_guided_files", 4),
                              "max_candidates_per_file": args.get("iterative_candidates_per_file", 24),
                              "max_total_candidates": args.get("iterative_max_candidates", 128)})
        iterative = _REPAIR._STRICT.run(iterative_args, repo)
        check_restored(iterative)
        attempts.append({"engine": "iterative", "status": iterative["status"],
                         "pass": iterative["pass"], "tested_candidate_count": iterative["tested_candidate_count"]})
        if iterative.get("pass") is True:
            if (iterative["status"] != "PASS__BOUNDED_MULTI_ROUND_REPAIR_FOUND"
                    or len(iterative.get("final_verification_replays", [])) != 2
                    or any(r.get("returncode") != 0 or r.get("timed_out") is not False
                           for r in iterative["final_verification_replays"])):
                raise RepairAcceptanceError("ITERATIVE_REPLAY_NOT_VERIFIED")
            return {**iterative, "winner_mode": "ITERATIVE_STRICT_PROGRESS",
                    "verification_replays": iterative["final_verification_replays"],
                    "search_attempts": attempts}
        if iterative["status"] not in ("OPEN__NO_STRICTLY_IMPROVING_CANDIDATE",
                                       "OPEN__NO_COMPLETE_REPAIR_IN_BOUNDED_SEARCH"):
            raise RepairAcceptanceError("ITERATIVE_SEARCH_DID_NOT_EXHAUST_NORMALLY")

    guided = _REPAIR.run(repair_args, repo)
    if strategy == "iterative_then_guided":
        check_restored(guided)
    attempts.append({"engine": "guided", "status": guided["status"], "pass": guided["pass"],
                     "single_candidates_tested": guided["single_candidates_tested"],
                     "pair_candidates_tested": guided["pair_candidates_tested"]})
    return {**guided, "search_attempts": attempts}


def run(args:Mapping[str,Any],root:str|os.PathLike[str])->dict[str,Any]:
    if not isinstance(args,Mapping):
        raise RepairAcceptanceError("ARGS_NOT_OBJECT")
    strategy = args.get("repair_strategy", "guided")
    if strategy not in ("guided", "iterative_then_guided"):
        raise RepairAcceptanceError("REPAIR_STRATEGY_UNSUPPORTED")
    for key, maximum in (("iterative_max_rounds", 20), ("iterative_candidates_per_file", 5000),
                         ("iterative_max_candidates", 50000)):
        if key in args and (type(args[key]) is not int or not 1 <= args[key] <= maximum):
            raise RepairAcceptanceError("ITERATIVE_LIMIT_INVALID:" + key)
    repo=pathlib.Path(root).resolve()
    source_root=_safe_dir(repo,args.get("source_root","."))
    contract_checks = (_validate_contract_checks(args["contract_checks"], source_root)
                       if "contract_checks" in args else None)
    test_paths=[_safe_file(repo,x) for x in (args.get("test_paths") or []) if str(x).strip()]
    if not test_paths:
        from canonical.runtime.bound_capabilities.python_test_corpus_discovery_v1 import discover_test_files
        try:
            test_paths=discover_test_files(source_root)
        except FileNotFoundError:
            raise RepairAcceptanceError("NO_TEST_FILES_UNDER_SOURCE_ROOT")
    if not test_paths:
        raise RepairAcceptanceError("TEST_PATHS_REQUIRED")
    argv=_REPAIR._PATCH.argv_or_derived(args.get("test_argv"),sys.executable,*test_paths)
    task_text=str(args.get("task_text") or "").strip()
    if not task_text:
        raise RepairAcceptanceError("TASK_TEXT_REQUIRED")
    # The front door binds the whole goal here.  An explicitly delimited
    # ``where`` clause is the acceptance contract; the preceding sentence is
    # routing metadata only when every one of its words is declared.  Any other
    # shape returns the original lossless text and keeps blocking residuals.
    clause=acceptance_clause.extract(task_text,args)
    task_text=str(clause.get("acceptance_task_text") or task_text).strip()
    if not task_text:
        raise RepairAcceptanceError("TASK_TEXT_REQUIRED")
    output=_safe_output(repo,args.get("output_path"))
    try:
        fresh_output(repo, args.get("output_path"), "")
    except ValueError as exc:
        raise RepairAcceptanceError(str(exc)) from exc
    timeout=max(1,min(int(args.get("timeout_s",20)),120))
    output.parent.mkdir(parents=True, exist_ok=True)
    repair_args={
        "source_root":_rel(repo,source_root) if source_root!=repo else ".",
        "test_paths":[_rel(repo,p) for p in test_paths],
        "test_argv":argv,

        "timeout_s":timeout,
        "max_guided_files":args.get("max_guided_files",4),
        "max_guided_symbols_per_file":args.get("max_guided_symbols_per_file",6),
        "mutations_per_file":args.get("mutations_per_file",24),
        "max_pair_candidates":args.get("max_pair_candidates",1000),
        "max_control_files":args.get("max_control_files",12),
        "max_control_symbols_per_file":args.get("max_control_symbols_per_file",12),
    }
    with tempfile.TemporaryDirectory(prefix=".repair-search-", dir=output.parent) as temporary:
        scratch = pathlib.Path(temporary)
        repair_args["output_path"] = _rel(repo, scratch / "guided.json")
        repair = _run_search(args, repair_args, repo, source_root, scratch)
    if repair.get("source_restored") is not True:
        raise RepairAcceptanceError("REPAIR_SOURCE_RESTORATION_NOT_PROVED")
    if repair.get("pass") is not True:
        result={
            "schema":SCHEMA,"capability_id":CAPABILITY_ID,
            "status":"OPEN__NO_VERIFIED_REPAIR_IN_BOUNDED_SEARCH","pass":False,
            "repair_pass":False,"acceptance_stop_authorized":False,
            "repair_status":repair.get("status"),"repair_summary":repair,
            "model_dependency_count":0,"external_general_purpose_model_runtime_dependency_count":0,
            "incremental_spend_usd":0,"source_restored":True,"terminal_authority":False,
            "hard_nonclaims":["NO_REPAIR_FOUND_MEANS_ONLY_BOUNDED_SEARCH_EXHAUSTED","NO_FRONTIERCODE_SCORE_OR_TERMINAL_CREDIT"],
        }
    else:
        patches=repair.get("patches") or []
        if not isinstance(patches,list) or not patches:
            raise RepairAcceptanceError("REPAIR_PATCHES_MISSING")
        rel_tests,candidate_argv=_candidate_test_layout(repo,source_root,test_paths,argv)
        with tempfile.TemporaryDirectory(prefix="brain-v8-") as td:
            temp_root=pathlib.Path(td)
            candidate_root=temp_root/"candidate"
            realized=_realize_candidate(repo,source_root,patches,candidate_root)
            contract_results = (_check_candidate_contracts(contract_checks, candidate_root, temp_root)
                                if contract_checks is not None else [])
            contracts_pass = (bool(contract_results) and all(r["pass"] for r in contract_results)
                              if contract_checks is not None else True)
            measurement=_MEASURE.run({
                "source_root":"candidate",
                "test_paths":rel_tests,
                "test_argv":candidate_argv,
                "output_path":"measurement.json",
                "timeout_s":timeout,
            },temp_root)
            acceptance=_ACCEPT.evaluate_from_receipt(
                task_text,
                measurement_receipt_path="measurement.json",
                root=temp_root,
                response_text=(str(args["response_text"]) if args.get("response_text") is not None else None),
            )
            accepted=acceptance.get("acceptance_stop_authorized") is True and contracts_pass
            result={
                "schema":SCHEMA,"capability_id":CAPABILITY_ID,
                "status":("PASS__REPAIR_REALIZED_MEASURED_AND_ACCEPTED" if accepted else
                          "OPEN__REPAIR_FOUND_BUT_CONTRACT_CHECKS_NOT_CLEARED" if not contracts_pass else
                          "OPEN__REPAIR_FOUND_BUT_MEASURED_ACCEPTANCE_NOT_CLEARED"),
                "pass":accepted,"repair_pass":True,
                "acceptance_stop_authorized":accepted,
                "repair_status":repair.get("status"),
                "winner_mode":repair.get("winner_mode"),
                "repair_search":{key:repair.get(key) for key in (
                    "single_candidates_tested", "pair_candidates_tested", "verification_replays",
                    "provenance_hypothesis_count", "crossed_nonmonotonic_valley", "guidance",
                    "rounds", "accepted_edit_count", "tested_candidate_count", "search_attempts")},
                "realized_patches":realized,
                "patches":patches if accepted else [],
                "contract_checks":contract_results,
                "contract_checks_pass":contracts_pass if contract_checks is not None else None,
                "contract_checks_executed":bool(contract_results),
                "independent_semantic_oracle_credit":False,
                "candidate_subject_snapshot_sha256":(measurement.get("subject") or {}).get("snapshot_sha256"),
                "measurement_receipt_payload_sha256":measurement.get("receipt_payload_sha256"),
                "measurement_program_sha256":measurement.get("measurement_program_sha256"),
                "measurement_spec_sha256":measurement.get("measurement_spec_sha256"),
                "measured_fields":measurement.get("measurements"),
                "acceptance_status":acceptance.get("status"),
                "semantic_residual_obligation_ids":((acceptance.get("objective_result") or {}).get("semantic_residual_obligation_ids") or []),
                "source_restored":repair.get("source_restored") is True,
                "model_dependency_count":0,
                "external_general_purpose_model_runtime_dependency_count":0,
                "incremental_spend_usd":0,
                "terminal_authority":False,
                "hard_nonclaims":[
                    "NO_GENERAL_NATURAL_LANGUAGE_SEMANTIC_COMPLETENESS",
                    "NO_ARBITRARY_PATCH_SEARCH_COMPLETENESS",
                    "NO_NON_PYTHON_SUPPORT",
                    "NO_TEST_PASS_EQUALS_GENERAL_MERGEABILITY",
                    "NO_FRONTIERCODE_SCORE_OR_TERMINAL_CREDIT",
                ],
            }
    result["repair_strategy"] = strategy
    result["requested_contract_checks"] = contract_checks
    result["contract_check_spec_sha256"] = (
        _sha(json.dumps(contract_checks, sort_keys=True, separators=(",", ":")).encode())
        if contract_checks is not None else None)
    try:
        published = publish_report(repo, output, result)
    except FileExistsError as exc:
        raise RepairAcceptanceError("OUTPUT_ALREADY_EXISTS") from exc
    # This controller's legacy field describes the artifact, not task success.
    # Preserve it without marking an intact failed-search report as accepted.
    return {**published, "output_verified": published["artifact_integrity_verified"]}
