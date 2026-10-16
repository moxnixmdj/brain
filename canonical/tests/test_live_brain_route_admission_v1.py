"""Fail-closed route admission in front of the live Brain.

Measured on 2026-10-15 (canonical/capabilities/true/LIVE_SOLVER_END_TO_END_MEASUREMENT_20261015_V1.json):
through ``run_raw_goal`` 100 of 100 fresh out-of-scope goals ("translate ...", "prove ...",
"summarize ...") came back PASS because a repository path token such as ``runtime`` matched a
keyword of a zero-input tool.  ``solve`` must refuse those before anything executes, and must
not refuse the goals the compiler really serves.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import goal_compiler  # noqa: E402
from canonical.runtime import live_brain_route_admission_v1 as adm  # noqa: E402
from canonical.runtime.live_integrated_brain_v1 import load_verified_registry  # noqa: E402

WORK = ROOT / "canonical/astra_runtime/tmp/test_live_brain_route_admission"
STATE = ROOT / "canonical/astra_runtime/state"


def _registry():
    return goal_compiler._platform_admissible_registry(dict(load_verified_registry()))


def _compile(goal: str):
    return goal_compiler.compile_goal(goal, _registry(), ROOT)


def _cleanup(task_id: str) -> None:
    for p in STATE.glob(task_id + "__*"):
        p.unlink()


def setup_module(_module=None):
    WORK.mkdir(parents=True, exist_ok=True)


def teardown_module(_module=None):
    if WORK.exists():
        shutil.rmtree(WORK)


# ----------------------------------------------------------------------------- pure rules

def test_path_token_only_match_is_rejected_before_execution():
    goal = "Translate the sentence 'good morning' into French and save it to canonical/astra_runtime/tmp/test_live_brain_route_admission/fr.txt."
    compiled = _compile(goal)
    assert compiled.get("selected_capability") == "terminal.kstar.root.assess.stdlib"  # the measured fail-open route
    verdict = adm.route_admission(goal, compiled, _registry())
    assert verdict["admitted"] is False
    assert verdict["rule"] == "R1_PATH_TOKENS_ONLY"
    assert verdict["semantic_matched_tokens"] == []
    assert "runtime" in verdict["matched_from_paths_only"]


def test_future_artifact_with_tool_that_cannot_write_is_rejected():
    goal = "Prove that the square root of 2 is irrational and save the proof to canonical/astra_runtime/tmp/test_live_brain_route_admission/proof.md."
    compiled = _compile(goal)
    verdict = adm.route_admission(goal, compiled, _registry())
    assert verdict["admitted"] is False
    assert verdict["rule"] == "R2_OUTPUT_ARTIFACT_UNSERVED"
    assert verdict["capability_output_keys"] == []
    assert verdict["goal_future_artifacts"]


def test_single_word_evidence_is_rejected():
    goal = "Write a Python tutorial for beginners and save it to canonical/astra_runtime/tmp/test_live_brain_route_admission/tut.md."
    compiled = _compile(goal)
    verdict = adm.route_admission(goal, compiled, _registry())
    assert verdict["admitted"] is False
    assert verdict["rule"] == "R3_WEAK_EVIDENCE"
    assert verdict["semantic_matched_tokens"] == ["python"]


def test_real_archive_goal_is_admitted_even_though_its_paths_share_tokens():
    manifest = WORK / "manifest.json"
    src = WORK / "src.txt"
    src.write_text("admitted", encoding="utf-8")
    manifest.write_text(json.dumps({"records": [{"verification_paths": ["canonical/astra_runtime/tmp/test_live_brain_route_admission/src.txt"]}]}), encoding="utf-8")
    goal = ("Create a tar.gz archive from the manifest canonical/astra_runtime/tmp/test_live_brain_route_admission/manifest.json "
            "and save it to canonical/astra_runtime/tmp/test_live_brain_route_admission/out.tar.gz.")
    compiled = _compile(goal)
    assert compiled.get("selected_capability") == "archive.tar_gz.create_from_manifest"
    verdict = adm.route_admission(goal, compiled, _registry())
    assert verdict["admitted"] is True, verdict
    assert {"archive", "tar", "gz"} <= set(verdict["semantic_matched_tokens"])


def test_controller_plans_without_a_selected_capability_are_not_judged_by_token_overlap():
    compiled = _compile('Respond with exactly "orientation 42".')
    verdict = adm.route_admission('Respond with exactly "orientation 42".', compiled, _registry())
    assert verdict["admitted"] is True
    assert verdict["selected_capability"] is None


def test_tool_truth_rule_catches_pass_false_and_non_success_status():
    result = {"execution": [{"capability_id": "x", "result": {"pass": False, "output_verified": True}}]}
    assert adm.tool_truth_errors(result) == ["TOOL_REPORTED_PASS_FALSE:x"]
    result = {"execution": [{"capability_id": "y", "result": {"status": "OPEN__SEMANTIC_RESIDUALS", "output_verified": True}}]}
    assert adm.tool_truth_errors(result) == ["TOOL_REPORTED_NON_SUCCESS_STATUS:y:OPEN__SEMANTIC_RESIDUALS"]
    result = {"execution": [{"capability_id": "z", "result": {"status": "UNRESOLVED", "outcome": "UNRESOLVED"}}]}
    assert adm.tool_truth_errors(result)[0].startswith("TOOL_REPORTED_NON_SUCCESS_STATUS:z:UNRESOLVED")
    assert adm.tool_truth_errors({"execution": [{"capability_id": "ok", "result": {"status": "PASS", "pass": True}}]}) == []


# ----------------------------------------------------------------------------- end to end

def test_solve_fails_closed_on_out_of_scope_goal_and_writes_nothing():
    out = WORK / "summary.txt"
    src = WORK / "notes.txt"
    src.write_text("alpha\nbeta\n", encoding="utf-8")
    task_id = "TEST_ROUTE_ADMISSION_OOS_%d" % os.getpid()
    try:
        result = adm.solve({"task_id": task_id, "goal": f"Summarize the file canonical/astra_runtime/tmp/test_live_brain_route_admission/notes.txt into three sentences and save the summary to canonical/astra_runtime/tmp/test_live_brain_route_admission/summary.txt."})
    finally:
        _cleanup(task_id)
    assert result["pass"] is False
    # with zero-input tools blocked from plain goals (F4) nothing can match; before F4 the same
    # goal reached admission and was rejected there - both are fail-closed with nothing written
    assert result["status"] == "FAIL__RAW_GOAL_COMPILATION_GAP"
    assert result["compiler_code"] == "GOAL_COMPILATION_NO_VERIFIED_CAPABILITY_MATCH"
    assert result["executed"] is False
    assert result["incremental_spend_usd"] == 0
    assert not out.exists()


def test_compiler_fallback_to_a_zero_input_tool_is_refused():
    """When the right tool cannot bind its inputs (manifest file not named *manifest*), the
    compiler silently falls through to the next scored candidate - here the zero-input
    catch-all - instead of failing closed.  The guard must refuse that route."""
    manifest = WORK / "m9.json"
    src = WORK / "s9.txt"
    src.write_bytes(b"fallback")
    manifest.write_text(json.dumps({"records": [{"verification_paths": ["canonical/astra_runtime/tmp/test_live_brain_route_admission/s9.txt"]}]}), encoding="utf-8")
    goal = ("Create a tar.gz archive from the manifest canonical/astra_runtime/tmp/test_live_brain_route_admission/m9.json, "
            "including all its verification_paths files, and save it to canonical/astra_runtime/tmp/test_live_brain_route_admission/bundle9.tar.gz.")
    compiled = _compile(goal)
    assert compiled.get("selected_capability") == "terminal.kstar.root.assess.stdlib"
    verdict = adm.route_admission(goal, compiled, _registry())
    assert verdict["admitted"] is False
    assert verdict["rule"] in {"R1_PATH_TOKENS_ONLY", "R2_OUTPUT_ARTIFACT_UNSERVED"}


def test_solve_still_executes_a_real_goal():
    manifest = WORK / "manifest2.json"
    src = WORK / "s2.txt"
    out = WORK / "bundle2.tar.gz"
    src.write_bytes(b"solve executes real goals\n")
    manifest.write_text(json.dumps({"records": [{"verification_paths": ["canonical/astra_runtime/tmp/test_live_brain_route_admission/s2.txt"]}]}), encoding="utf-8")
    if out.exists():
        out.unlink()
    task_id = "TEST_ROUTE_ADMISSION_ARCHIVE_%d" % os.getpid()
    try:
        result = adm.solve({"task_id": task_id, "goal": (
            "Create a tar.gz archive from the manifest canonical/astra_runtime/tmp/test_live_brain_route_admission/manifest2.json, "
            "including all its verification_paths files, and save it to canonical/astra_runtime/tmp/test_live_brain_route_admission/bundle2.tar.gz.")})
    finally:
        _cleanup(task_id)
    assert result["pass"] is True, result.get("status")
    assert result["route_admission"]["admitted"] is True
    assert result["model_dependency_count"] == 0
    with tarfile.open(out, "r:gz") as tf:
        names = [m.name for m in tf.getmembers() if m.isfile()]
        assert any(n.endswith("s2.txt") for n in names)
        member = next(m for m in tf.getmembers() if m.name.endswith("s2.txt"))
        assert tf.extractfile(member).read() == b"solve executes real goals\n"


def test_solve_compilation_gap_is_reported_as_before():
    task_id = "TEST_ROUTE_ADMISSION_GAP_%d" % os.getpid()
    try:
        result = adm.solve({"task_id": task_id, "goal": "Calibrate the neutrino interferometer phase drift."})
    finally:
        _cleanup(task_id)
    assert result["pass"] is False
    assert result["failure_class"] == "RAW_GOAL_TO_EXECUTABLE_CONTRACT_GAP"


def _a_receipt_backed_capability_id() -> str:
    return next(c for c, e in sorted(load_verified_registry().items())
                if e.get("capability_source") == "receipt_projection")


def test_an_explicitly_named_capability_is_admitted_and_executed():
    """The other half of this file's contract: never refuse a goal the compiler really serves.

    Measured before: all 294 receipt-backed capabilities were selected by the front layer and
    then refused here with R1_PATH_TOKENS_ONLY, and the R6 gate then demanded the capability
    write a file named after itself.  None of the 294 could pass through this entry."""
    cid = _a_receipt_backed_capability_id()
    task_id = "TEST_NAMED_CAPABILITY_%d" % os.getpid()
    try:
        result = adm.solve({"task_id": task_id, "goal": f"run {cid}"})
    finally:
        _cleanup(task_id)
    assert result["status"] == (
        "PASS__RAW_GOAL_COMPILED_FRONT_LOCAL_ADAPTER_EXECUTED_AND_VERIFIED"
        "__RAW_ACCEPTANCE_RECEIPTS_STILL_REQUIRED"
    ), result.get("status")
    assert result["pass"] is True, result.get("status")
    assert result["compiled_capability_id"] == cid
    assert result["route_admission"]["admission_basis"] == "EXPLICIT_CAPABILITY_ID_IN_GOAL"
    # the R6 gate reports only what is missing; the capability's own id is not a promised file
    assert "promised_artifact_errors" not in result
    assert result["routing_success_authority"] is False
    assert result["model_dependency_count"] == 0


def test_a_capability_identity_is_never_a_promised_artifact():
    """F16's rule at the R6 gate: the id is an identity, and the artifact check still works."""
    cid = _a_receipt_backed_capability_id()
    assert adm._future_artifacts(f"run {cid}") == []
    assert adm._future_artifacts("save it to canonical/astra_runtime/tmp/real_future_artifact.md")


def test_a_ghost_capability_id_is_refused_before_anything_executes():
    cid = _a_receipt_backed_capability_id()
    ghost = cid.rsplit(".py.auto.v1", 1)[0] + "_renamed.py.auto.v1"
    result = adm.solve({"task_id": "TEST_GHOST_ID", "goal": f"run {ghost}"})
    assert result["status"] == "FAIL__RAW_GOAL_COMPILATION_GAP"
    assert result["compiler_code"] == "GOAL_NAMES_UNKNOWN_CAPABILITY"
