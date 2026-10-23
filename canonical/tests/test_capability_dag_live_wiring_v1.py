"""One entry plans a multi-step request as ONE capability DAG and executes it with the planner's
own artifact forwarding (F11/F12 compile rules, R7/R8/R9 admission rules, two executors).

The DAG is planned by ``canonical/runtime/capability_planner.py``: every step declares the artifact
an earlier step writes among its requirements, so the planner - not sentence order - is the
authority that a consumer never runs before its producer, and ``plan_actions`` turns each
cross-step artifact into a ``$result`` reference the executor resolves at execution time.
A step whose source type the pinned kernel refuses is run by this entry's local adapter runner
(E1), and the whole DAG is executed by one of the two executors, never half by each.

No model, no spend, no network.  The oracles below are independent stdlib checks on the artifacts.
"""
from __future__ import annotations

import json
import os
import random
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import goal_compiler  # noqa: E402
from canonical.runtime import goal_front_compiler_v1 as front  # noqa: E402
from canonical.runtime import live_brain_route_admission_v1 as adm  # noqa: E402
from canonical.runtime.live_integrated_brain_v1 import load_verified_registry  # noqa: E402
from execution_guard import live_solver_families_v3 as v3  # noqa: E402

WORK = ROOT / "canonical/astra_runtime/tmp/test_capability_dag_live_wiring"
REL = "canonical/astra_runtime/tmp/test_capability_dag_live_wiring"
STATE = ROOT / "canonical/astra_runtime/state"


def _registry():
    return goal_compiler._platform_admissible_registry(dict(load_verified_registry()))


def _rel(path: Path) -> str:
    return str(Path(path).relative_to(ROOT)).replace("\\", "/")


def _cleanup(task_id: str) -> None:
    for p in STATE.glob(task_id + "__*"):
        p.unlink()


def setup_module(_module=None):
    shutil.rmtree(WORK, ignore_errors=True)
    WORK.mkdir(parents=True, exist_ok=True)


def teardown_module(_module=None):
    if WORK.exists():
        shutil.rmtree(WORK, ignore_errors=True)


def _manifest_archive_goal() -> tuple[str, Path, Path, Path]:
    """A two-step request where step 2 consumes the file step 1 writes."""
    src = WORK / "src.txt"
    manifest = WORK / "manifest.json"
    bundle = WORK / "bundle.tar.gz"
    src.write_text("dag artifact forwarding payload\n", encoding="utf-8")
    manifest.write_text(json.dumps({"records": [{"verification_paths": [_rel(src)]}]}), encoding="utf-8")
    if bundle.exists():
        bundle.unlink()
    goal = (f"Create a tar.gz archive from the manifest {_rel(manifest)} and save it to {_rel(bundle)}. "
            f"Then verify the archive {_rel(bundle)} against the manifest {_rel(manifest)} with gnu tar.")
    return goal, src, manifest, bundle


def _compile(goal: str):
    return front.compile_goal(goal, _registry(), ROOT)


def registry_expect_field(action):
    """The expectation the registry declares for the capability that action invokes."""
    cid = action["args"]["capability_id"]
    return _registry()[cid]["action_template"]["expect"]["field"]


# ----------------------------------------------------------------------------- compile (F11/F12)

def test_multi_step_request_is_planned_as_one_capability_dag():
    goal, _src, _manifest, _bundle = _manifest_archive_goal()
    compiled = _compile(goal)
    assert compiled["compiler_mode"] == front.DAG_MODE
    assert compiled["compiler_mode"] != "FRONT_COMPOUND_SENTENCES"
    rules = compiled["front_compiler"]["rules_applied"]
    assert "F11_MULTI_STEP_CAPABILITY_DAG_PLANNED" in rules
    assert "F12_CROSS_STEP_ARTIFACT_BOUND" in rules
    dag = compiled["capability_dag"]
    assert dag["schema"] == front.DAG_SCHEMA
    assert [s["capability_id"] for s in dag["steps"]] == [
        "archive.tar_gz.create_from_manifest", "archive.verify.tar_gz.gnu"]
    assert [s["cycle"] for s in dag["steps"]] == [0, 1]
    # the planner - not the sentence - is the authority on order and cost
    assert dag["planning"]["status"] == "SOLVED"
    assert dag["planning"]["plan"] == ["step:0:archive.tar_gz.create_from_manifest",
                                      "step:1:archive.verify.tar_gz.gnu"]
    assert dag["planning"]["total_cost"] == 2.0
    finish = compiled["controller_actions"][-1]
    assert finish["type"] == "finish" and finish["args"]["summary"] == front.DAG_FINISH_SUMMARY


def test_cross_step_artifact_is_a_result_reference_not_a_copied_path():
    goal, _src, _manifest, bundle = _manifest_archive_goal()
    compiled = _compile(goal)
    dag = compiled["capability_dag"]
    assert dag["artifact_edges"] == [{
        "consumer_cycle": 1, "consumer_capability_id": "archive.verify.tar_gz.gnu", "input_key": "archive_path",
        "producer_cycle": 0, "producer_capability_id": "archive.tar_gz.create_from_manifest",
        "produced_path": _rel(bundle), "result_field": "output_path", "effect": "artifact:" + _rel(bundle),
    }]
    verify_args = dag["steps"][1]["action"]["args"]
    assert verify_args["archive_path"] == {"$result": {"cycle": 0, "field": "output_path"}}
    assert verify_args["manifest_path"] == _rel(_manifest)  # a real input is still a plain path
    # the producer is the step that writes the file, and it declares the field it is read through
    assert dag["steps"][0]["action"]["args"]["output_path"] == _rel(bundle)
    assert "output_path" in dag["steps"][0]["result_fields"]
    assert dag["steps"][1]["requires"].count("artifact:" + _rel(bundle)) == 1
    row = dag["composition_contract"][1]["requirement_bindings"]["artifact:" + _rel(bundle)]
    assert row["source"] == "capability" and row["cycle"] == 0


def test_the_planner_problem_is_declared_per_step():
    goal, _src, _manifest, _bundle = _manifest_archive_goal()
    problem = _compile(goal)["capability_dag"]["problem"]
    assert problem["finish_summary"] == front.DAG_FINISH_SUMMARY
    assert [c["id"] for c in problem["capabilities"]] == [
        "step:0:archive.tar_gz.create_from_manifest", "step:1:archive.verify.tar_gz.gnu"]
    for cap in problem["capabilities"]:
        step_index = cap["id"].split(":")[1]
        assert cap["provides"] and cap["action"]["type"] == "invoke_capability"
        assert cap["id"].startswith("step:" + step_index + ":")
        assert cap["action"]["args"]["capability_id"] == cap["id"].split(":", 2)[2]
        assert cap["action"]["expect"]["field"] == registry_expect_field(cap["action"])
    assert "order:0" in problem["initial_facts"]
    assert "step:1:executed" in problem["target_effects"]


# ----------------------------------------------------------------------------- admission (R7/R8/R9)

def test_dag_admission_admits_the_planned_request():
    goal, _src, _manifest, _bundle = _manifest_archive_goal()
    compiled = _compile(goal)
    verdict = adm.dag_admission(goal, compiled, compiled["capability_dag"], _registry())
    assert verdict["admitted"] is True, verdict
    assert verdict["rule"] is None
    assert [row["capability_id"] for row in verdict["dag_steps"]] == [
        "archive.tar_gz.create_from_manifest", "archive.verify.tar_gz.gnu"]
    assert all(len(row["semantic_matched_tokens"]) > 1 for row in verdict["dag_steps"])


def test_dag_admission_rejects_a_step_without_prose_evidence():
    goal, _src, _manifest, _bundle = _manifest_archive_goal()
    compiled = _compile(goal)
    broken = json.loads(json.dumps(compiled))
    broken["capability_dag"]["steps"][0]["clause"] = "then and to it"
    verdict = adm.dag_admission(goal, broken, broken["capability_dag"], _registry())
    assert verdict["admitted"] is False
    assert verdict["rule"] == "DAG_STEP_WEAK_EVIDENCE"
    assert verdict["failed_cycle"] == 0


def test_dag_admission_rejects_an_artifact_edge_that_points_forward():
    goal, _src, _manifest, _bundle = _manifest_archive_goal()
    compiled = _compile(goal)
    broken = json.loads(json.dumps(compiled))
    broken["capability_dag"]["artifact_edges"][0]["consumer_cycle"] = 0
    verdict = adm.dag_admission(goal, broken, broken["capability_dag"], _registry())
    assert verdict["admitted"] is False
    assert verdict["rule"] == "DAG_ARTIFACT_EDGE_INVALID"


def test_dag_contract_rejects_a_forward_result_reference_and_an_undeclared_field():
    goal, _src, _manifest, _bundle = _manifest_archive_goal()
    dag = _compile(goal)["capability_dag"]
    assert adm.dag_contract_errors(dag) == []
    forward = json.loads(json.dumps(dag))
    forward["steps"][0]["action"]["args"]["manifest_path"] = {"$result": {"cycle": 1, "field": "output_path"}}
    errors = adm.dag_contract_errors(forward)
    assert "DAG_RESULT_FORWARD_REFERENCE:0:1" in errors
    undeclared = json.loads(json.dumps(dag))
    undeclared["steps"][1]["action"]["args"]["archive_path"] = {"$result": {"cycle": 0, "field": "sha256_of_bundle"}}
    assert "DAG_RESULT_FIELD_UNDECLARED:1:sha256_of_bundle" in adm.dag_contract_errors(undeclared)


def test_dag_admission_rejects_a_promised_artifact_no_step_writes():
    goal, _src, _manifest, _bundle = _manifest_archive_goal()
    compiled = _compile(goal)
    wider = goal + f" Save the verification receipt to {REL}/receipt.json."
    verdict = adm.dag_admission(wider, compiled, compiled["capability_dag"], _registry())
    assert verdict["admitted"] is False
    assert verdict["rule"] == "DAG_PROMISED_ARTIFACT_UNPRODUCED"
    assert verdict["unproduced_artifacts"] == [REL + "/receipt.json"]


# ----------------------------------------------------------------------------- execution

def test_solve_executes_a_multi_step_dag_and_forwards_the_artifact():
    goal, src, manifest, bundle = _manifest_archive_goal()
    task_id = "TEST_CAPABILITY_DAG_KERNEL_%d" % os.getpid()
    try:
        result = adm.solve({"task_id": task_id, "goal": goal})
    finally:
        _cleanup(task_id)
    assert result["pass"] is True, result.get("reason") or result.get("status")
    assert result["status"] == "PASS__CAPABILITY_DAG_EXECUTED_AND_VERIFIED__RAW_ACCEPTANCE_RECEIPTS_STILL_REQUIRED"
    assert result["route_admission"]["admitted"] is True
    assert result["selected_plan"] == ["archive.tar_gz.create_from_manifest", "archive.verify.tar_gz.gnu"]
    # The local runner is tried FIRST and returned whenever it passes; the pinned
    # kernel is the fallback, reached only when local fails.  That ordering is the
    # module's repeated shape -- the single-capability path in _execute() does the
    # same -- and kernel_refuses() says so outright: "E1's local execution is the
    # path the 29/29 family measurement was taken on, and moving these to the kernel
    # is a separate, separately measured decision."  dag_executor() states a
    # NECESSARY condition for the kernel ("used only when it accepts every step's
    # source type"), not a sufficient one.  This assertion used to demand the kernel
    # and read that docstring as kernel-primary; both are kept, so the decision
    # function and the executor that actually ran are each pinned.
    assert adm.dag_executor(_compile(goal), _registry()) == adm.DAG_KERNEL_EXECUTOR
    assert result["capability_dag"]["executor"] == adm.DAG_LOCAL_EXECUTOR
    assert [row["cycle"] for row in result["execution"]] == [0, 1]
    assert all(row["pass"] is True for row in result["execution"])
    assert result["execution"][1]["plan_action"]["args"]["archive_path"] == {"$result": {"cycle": 0, "field": "output_path"}}
    assert result["incremental_spend_usd"] == 0
    assert result["model_dependency_count"] == 0
    assert result["terminal_credit_delta"] == 0
    # independent stdlib oracle: the archive the first step wrote really contains the manifest entry
    assert bundle.is_file() and bundle.stat().st_size > 0
    with tarfile.open(bundle, "r:gz") as tf:
        names = [m.name for m in tf.getmembers() if m.isfile()]
    assert any(n.endswith("src.txt") for n in names)
    assert any(n.endswith("manifest.json") for n in names)
    assert result["execution"][1]["result"]["verified"] is True


def test_solve_runs_a_kernel_refused_step_in_the_local_dag_runner():
    """Step 2's source type (python_stdlib_composition) is refused by the pinned kernel, so the
    whole DAG is executed by this entry's local runner - with the same arguments, the same
    expectation check, and the same zero cost - and the artifact is verified independently."""
    bug = v3.fresh_bug(random.Random(20261015), WORK, 0, "dag")
    pkg = WORK / "pkg"
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "mod_a.py").write_text("def identity(x):\n    return x\n", encoding="utf-8")
    audit_out = WORK / "audit.json"
    repair_out = WORK / "repair.json"
    for p in (audit_out, repair_out):
        if p.exists():
            p.unlink()
    goal = (f"Audit the python source tree {_rel(pkg)} with the ast audit and save the report to {_rel(audit_out)}. "
            f"Then repair the python source {_rel(bug.src)} with the test guided repair loop so that the unit tests in "
            f"{bug.tests_phrase()} pass, and save the repair report to {_rel(repair_out)}.")
    compiled = _compile(goal)
    assert compiled["compiler_mode"] == front.DAG_MODE
    assert [s["capability_id"] for s in compiled["capability_dag"]["steps"]] == [
        "python.source.audit.ast", "python.software.repair.loop.test_guided.ast.v1"]
    assert adm.dag_executor(compiled, _registry()) == adm.DAG_LOCAL_EXECUTOR
    task_id = "TEST_CAPABILITY_DAG_LOCAL_%d" % os.getpid()
    try:
        result = adm.solve({"task_id": task_id, "goal": goal})
    finally:
        _cleanup(task_id)
    # The work is real and the verdict is a refusal, and BOTH are asserted.  The
    # goal says "repair the python source ... so that the unit tests pass", which
    # promises a source change; the repair loop finds a patch, verifies it, replays
    # the verification and then RESTORES the source, because source_write_authority
    # is False and is enforced against in five separate guard modules.  The front
    # door therefore fails closed -- correctly.  This assertion used to demand
    # pass=True and predates the promised_source_change_errors gate.  Asserting the
    # honest verdict is what keeps the independent oracle below meaningful: a patch
    # that is real but unapplied must not be reported as a repaired file.
    assert result["pass"] is False, result
    assert result["status"] == "FAIL_CLOSED__PROMISED_SOURCE_CHANGE_NOT_APPLIED", result.get("status")
    assert result["promised_source_change_errors"], result
    assert result["capability_dag"]["executor"] == adm.DAG_LOCAL_EXECUTOR
    assert all(row["pass"] is True for row in result["execution"])
    assert result["controller_execution"]["reason_kernel_not_used"] == "BOUND_CAPABILITY_SOURCE_UNSUPPORTED_IN_AT_LEAST_ONE_DAG_STEP"
    assert result["incremental_spend_usd"] == 0 and result["model_dependency_count"] == 0
    # independent stdlib oracle: the audit counted the package, and the reported patch really
    # makes the bug's own test files pass when applied to a private copy of the source
    totals = json.loads(audit_out.read_text(encoding="utf-8"))["totals"]
    assert totals["files"] == 1 and totals["functions"] == 1
    report = json.loads(repair_out.read_text(encoding="utf-8"))
    patches = [p for p in (report.get("patches") or []) if p.get("source_path") == _rel(bug.src)]
    assert len(patches) == 1
    patched = v3.apply_unified_diff(bug.src.read_text(encoding="utf-8"), patches[0]["unified_diff"])
    assert patched != bug.src.read_text(encoding="utf-8")
    trial = WORK / "oracle_trial"
    shutil.rmtree(trial, ignore_errors=True)
    trial.mkdir(parents=True)
    (trial / bug.src.name).write_text(patched, encoding="utf-8")
    for path, text in bug.tests.items():
        (trial / path.name).write_text(text, encoding="utf-8")
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    for path in bug.tests:
        proc = subprocess.run([sys.executable, "-B", path.name], cwd=str(trial), capture_output=True,
                              text=True, timeout=120, env=env)
        assert proc.returncode == 0, proc.stderr[-400:]


def test_dag_executor_is_chosen_once_for_the_whole_plan():
    """Either executor runs every step: never step 0 in the kernel and step 1 locally."""
    goal, _src, _manifest, _bundle = _manifest_archive_goal()
    registry = _registry()
    compiled = _compile(goal)
    assert [s["capability_id"] for s in compiled["capability_dag"]["steps"]] == [
        "archive.tar_gz.create_from_manifest", "archive.verify.tar_gz.gnu"]
    assert not any(adm.kernel_refuses(registry[s["capability_id"]]) for s in compiled["capability_dag"]["steps"])
    assert adm.dag_executor(compiled, registry) == adm.DAG_KERNEL_EXECUTOR
    # one step the kernel would refuse moves the WHOLE plan to this entry's local runner
    tampered = dict(registry)
    tampered["archive.verify.tar_gz.gnu"] = {**registry["archive.verify.tar_gz.gnu"],
                                             "source": {"type": "brain_native_deterministic"}}
    assert adm.dag_executor(compiled, tampered) == adm.DAG_LOCAL_EXECUTOR


def test_solve_executes_the_plan_locally_when_the_kernel_refuses_a_step(monkeypatch):
    """A DAG whose executor is the local runner still forwards the artifact across the step
    boundary: the consumer's ``$result`` reference is resolved from the producer's own result."""
    src = WORK / "jq_src.txt"
    doc = WORK / "jq_doc.json"
    manifest = WORK / "manifest_from_jq.json"
    bundle = WORK / "bundle_from_jq.tar.gz"
    src.write_text("jq chain payload\n", encoding="utf-8")
    doc.write_text(json.dumps({"records": [{"verification_paths": [_rel(src)]}]}), encoding="utf-8")
    for p in (manifest, bundle):
        if p.exists():
            p.unlink()
    goal = (f'Run the jq query with jq filter "." on {_rel(doc)} and save the output to {_rel(manifest)}. '
            f"Then create a tar.gz archive from the manifest {_rel(manifest)} and save it to {_rel(bundle)}.")
    compiled = _compile(goal)
    assert compiled["compiler_mode"] == front.DAG_MODE
    assert [s["capability_id"] for s in compiled["capability_dag"]["steps"]] == [
        "json.query.jq", "archive.tar_gz.create_from_manifest"]
    assert compiled["capability_dag"]["artifact_edges"][0]["input_key"] == "manifest_path"
    monkeypatch.setattr(adm, "kernel_refuses", lambda entry: True)
    assert adm.dag_executor(compiled, _registry()) == adm.DAG_LOCAL_EXECUTOR
    task_id = "TEST_CAPABILITY_DAG_LOCAL_RUN_%d" % os.getpid()
    try:
        result = adm.solve({"task_id": task_id, "goal": goal})
    finally:
        _cleanup(task_id)
    assert result["pass"] is True, result.get("reason") or result.get("status")
    assert result["capability_dag"]["executor"] == adm.DAG_LOCAL_EXECUTOR
    assert [row["capability_id"] for row in result["execution"]] == ["json.query.jq", "archive.tar_gz.create_from_manifest"]
    assert all(row["pass"] is True for row in result["execution"])
    assert result["execution"][1]["plan_action"]["args"]["manifest_path"] == {"$result": {"cycle": 0, "field": "output_path"}}
    assert result["incremental_spend_usd"] == 0 and result["model_dependency_count"] == 0
    # independent stdlib oracle: the archive member the manifest step named is inside the archive
    written = json.loads(manifest.read_text(encoding="utf-8"))
    assert written["records"][0]["verification_paths"] == [_rel(src)]
    with tarfile.open(bundle, "r:gz") as tf:
        names = [m.name for m in tf.getmembers() if m.isfile()]
    assert any(n.endswith("jq_src.txt") for n in names)


def test_a_single_clause_goal_is_not_a_dag():
    src = WORK / "one.txt"
    manifest = WORK / "one_manifest.json"
    single = WORK / "one_bundle.tar.gz"
    src.write_text("single step\n", encoding="utf-8")
    manifest.write_text(json.dumps({"records": [{"verification_paths": [_rel(src)]}]}), encoding="utf-8")
    if single.exists():
        single.unlink()
    compiled = _compile(f"Create a tar.gz archive from the manifest {_rel(manifest)} and save it to {_rel(single)}.")
    assert compiled["compiler_mode"] == "DETERMINISTIC_VERIFIED_CAPABILITY_MATCH"
    assert "capability_dag" not in compiled
