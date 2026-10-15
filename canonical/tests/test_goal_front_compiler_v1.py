"""The one mouth: every bound capability reachable from a sentence, and the pinned compiler's
measured defects corrected in front of it (goal_front_compiler_v1 F1-F9)."""
from __future__ import annotations

import json
import pytest
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import goal_compiler as gc  # noqa: E402
from canonical.runtime import goal_front_compiler_v1 as front  # noqa: E402
from canonical.runtime import live_brain_route_admission_v1 as adm  # noqa: E402
from canonical.runtime.live_integrated_brain_v1 import load_verified_registry  # noqa: E402
from execution_guard.live_solver_end_to_end_measurement_v1 import reachability  # noqa: E402

WORK = ROOT / "canonical/astra_runtime/tmp/test_goal_front_compiler"
REL = "canonical/astra_runtime/tmp/test_goal_front_compiler"
STATE = ROOT / "canonical/astra_runtime/state"


def _registry():
    return gc._platform_admissible_registry(dict(load_verified_registry()))


def setup_module(_module=None):
    WORK.mkdir(parents=True, exist_ok=True)


def teardown_module(_module=None):
    if WORK.exists():
        shutil.rmtree(WORK)


def _cleanup(task_id: str) -> None:
    for p in STATE.glob(task_id + "__*"):
        p.unlink()


def test_f2_sentence_final_period_no_longer_corrupts_the_last_literal_value():
    goal = f"Create {REL}/rec.json containing exactly one record with fields id and value: alpha 1."
    compiled = front.compile_goal(goal, _registry(), ROOT)
    records = compiled["controller_actions"][0]["args"]["records"]
    assert records == [{"id": "alpha", "value": 1}]
    assert "F2_SENTENCE_FINAL_PERIOD_REMOVED" in compiled["front_compiler"]["rules_applied"]
    # the pinned compiler alone keeps the period in the value - that is the defect being corrected
    pinned = gc.compile_goal(goal, _registry(), ROOT)
    assert pinned["controller_actions"][0]["args"]["records"] == [{"id": "alpha", "value": "1."}]


def test_f5_compound_sentences_are_compiled_separately():
    goal = (f"Create {REL}/a.json containing exactly one record with fields id and value: alpha 7. "
            f"Then create {REL}/b.json containing exactly one record with fields id and value: beta 9.")
    compiled = front.compile_goal(goal, _registry(), ROOT)
    actions = [a for a in compiled["controller_actions"] if a["type"] != "finish"]
    assert [a["args"]["records"] for a in actions] == [[{"id": "alpha", "value": 7}], [{"id": "beta", "value": 9}]]
    assert compiled["compiler_mode"] == "FRONT_COMPOUND_SENTENCES"
    pinned = gc.compile_goal(goal, _registry(), ROOT)
    assert len([a for a in pinned["controller_actions"] if a["type"] != "finish"]) == 1  # the swallowed clause


def test_f3_build_and_write_routes_to_the_archive_creator_not_the_verifier():
    (WORK / "src.txt").write_text("x", encoding="utf-8")
    (WORK / "manifest.json").write_text(json.dumps({"records": [{"verification_paths": [REL + "/src.txt"]}]}), encoding="utf-8")
    goal = f"Build a tar.gz archive from the manifest {REL}/manifest.json and write it to {REL}/built.tar.gz."
    compiled = front.compile_goal(goal, _registry(), ROOT)
    assert compiled["selected_capability"] == "archive.tar_gz.create_from_manifest"
    assert compiled["inputs"]["output_path"] == REL + "/built.tar.gz"
    assert "F3_ARTIFACT_WRITERS_PREFERRED" in compiled["front_compiler"]["rules_applied"]


def test_f1_best_candidate_that_cannot_bind_fails_closed_instead_of_falling_through():
    (WORK / "s9.txt").write_text("x", encoding="utf-8")
    (WORK / "m9.json").write_text(json.dumps({"records": [{"verification_paths": [REL + "/s9.txt"]}]}), encoding="utf-8")
    # the manifest file is not named *manifest*; also an unrelated existing .json makes type binding ambiguous
    (WORK / "other.json").write_text("{}", encoding="utf-8")
    goal = f"Create a tar.gz archive from the manifest {REL}/m9.json and {REL}/other.json and save it to {REL}/bundle9.tar.gz."
    try:
        front.compile_goal(goal, _registry(), ROOT)
    except gc.GoalCompilationFailure as exc:
        assert exc.code == "GOAL_INPUT_BINDING_REQUIRED"
        assert str(exc.detail).startswith("archive.tar_gz.create_from_manifest:manifest_path")
    else:
        raise AssertionError("expected fail-closed binding failure")


def test_f4_zero_input_tools_are_never_routable_from_a_sentence():
    registry = _registry()
    blocked = front.blocked_zero_input_capabilities(registry)
    # The current registry gives the terminal assessor an explicit sentence-bound
    # assessment_scope; no evolving capability is hidden as a zero-input tool.
    assert blocked == []
    assert "terminal.kstar.root.assess.stdlib" in front.routable_registry(registry)
    goal = f"Translate the sentence 'good morning' into French and save it to {REL}/fr.txt."
    try:
        compiled = front.compile_goal(goal, registry, ROOT)
    except gc.GoalCompilationFailure as exc:
        assert exc.code in {"GOAL_COMPILATION_NO_VERIFIED_CAPABILITY_MATCH", "GOAL_INPUT_BINDING_REQUIRED", "GOAL_OUTPUT_ARTIFACT_UNSERVED"}
    else:
        # a weak keyword match may still compile; admission must then refuse it before execution
        assert compiled["selected_capability"] != "terminal.kstar.root.assess.stdlib"
        assert adm.route_admission(goal, compiled, registry)["admitted"] is False


def test_f6_input_path_binds_by_type_when_the_name_lacks_the_stem():
    (WORK / "bundle.tar.gz").write_bytes(b"\x1f\x8b")
    (WORK / "manifest6.json").write_text("{}", encoding="utf-8")
    goal = f"Verify the tar.gz archive {REL}/bundle.tar.gz against the manifest {REL}/manifest6.json with gnu tar."
    compiled = front.compile_goal(goal, _registry(), ROOT)
    assert compiled["selected_capability"] == "archive.verify.tar_gz.gnu"
    assert compiled["inputs"]["archive_path"] == REL + "/bundle.tar.gz"
    assert compiled["inputs"]["manifest_path"] == REL + "/manifest6.json"


def test_typed_grammar_binds_jq_filter_and_numbers_and_lists():
    (WORK / "data.json").write_text(json.dumps({"a": {"b": 3}}), encoding="utf-8")
    goal = f'Run the jq query with jq filter ".a.b" on {REL}/data.json and save the output to {REL}/q.json.'
    compiled = front.compile_goal(goal, _registry(), ROOT)
    assert compiled["selected_capability"] == "json.query.jq"
    assert compiled["inputs"] == {"jq_filter": ".a.b", "json_path": REL + "/data.json", "output_path": REL + "/q.json"}
    assert front.bind_typed_key("evaluate at x value 3.5 for label \"Curve A\"", "x_value", ROOT) == 3.5
    assert front.bind_typed_key("evaluate at x value 3.5 for label \"Curve A\"", "label", ROOT) == "Curve A"
    assert front.bind_typed_key("with x ticks [0, 1, 2]", "x_ticks", ROOT) == [0, 1, 2]
    assert front.bind_typed_key("expression \"2*x+1\" with variables x=2, y=3", "variables", ROOT) == {"x": 2, "y": 3}
    assert front.bind_typed_key('run test argv "python3 -m unittest -q"', "test_argv", ROOT) == ["python3", "-m", "unittest", "-q"]


def test_inputs_are_never_guessed():
    (WORK / "data2.json").write_text("{}", encoding="utf-8")
    try:
        front.bind_typed_key(f"Query {REL}/data2.json with jq", "jq_filter", ROOT)
    except gc.GoalCompilationFailure as exc:
        assert exc.code == "GOAL_INPUT_BINDING_REQUIRED"
    else:
        raise AssertionError("a missing input must fail closed")


def test_every_routable_capability_is_reachable_and_bound_from_one_sentence():
    report = reachability(WORK / "reach")
    counts = report["counts"]
    assert counts.get("NOT_REACHABLE", 0) == 0, [r for r in report["rows"] if r["state"] == "NOT_REACHABLE"]
    assert counts.get("ROUTED_ELSEWHERE", 0) == 0, [r for r in report["rows"] if r["state"] == "ROUTED_ELSEWHERE"]
    assert counts.get("REACHED_AND_BOUND", 0) + counts.get("BLOCKED_ZERO_INPUT", 0) == report["capabilities_total"]
    assert counts["REACHED_AND_BOUND"] >= 63


def test_solve_executes_a_compound_literal_goal_end_to_end():
    a, b = WORK / "e1.json", WORK / "e2.json"
    for p in (a, b):
        if p.exists():
            p.unlink()
    task_id = "TEST_FRONT_COMPOUND_%d" % os.getpid()
    try:
        result = adm.solve({"task_id": task_id, "goal": (
            f"Create {REL}/e1.json containing exactly one record with fields id and value: alpha 1. "
            f"Then create {REL}/e2.json containing exactly one record with fields id and value: beta 2.")})
    finally:
        _cleanup(task_id)
    assert result["pass"] is True, result.get("status")
    assert result["controller_action_count"] == 3
    assert result["model_dependency_count"] == 0
    assert json.loads(a.read_text(encoding="utf-8")) == [{"id": "alpha", "value": 1}]
    assert json.loads(b.read_text(encoding="utf-8")) == [{"id": "beta", "value": 2}]


def test_solve_r6_promised_artifact_must_exist(monkeypatch):
    """Even if the controller says PASS, a promised output file that is missing fails closed."""
    calls = {}

    def fake_run_goal(spec, mission):
        calls["spec"] = spec
        return {"returncode": 0, "controller_mode": "MODEL_INDEPENDENT_ACTION_PLAN", "cognition_dependency_class": "MODEL_INDEPENDENT",
                "model_dependency_count": 0, "final_summary": "done", "trace": [{"action": spec["controller_actions"][0], "result": {"verified": True}}],
                "controller_checkpoint": {"plan_sha256": "x"}}

    monkeypatch.setattr(adm.astra_runtime, "run_goal", fake_run_goal)
    result = adm.solve({"task_id": "TEST_FRONT_R6", "goal": f"Create {REL}/never_written.json containing exactly one record with fields id and value: alpha 1."})
    assert result["pass"] is False
    assert result["status"] == "FAIL_CLOSED__PROMISED_ARTIFACT_MISSING"
    assert result["promised_artifact_errors"] == ["PROMISED_ARTIFACT_MISSING:" + REL + "/never_written.json"]


def test_f10_output_path_is_never_the_input_file():
    """The pinned binder resolved jq's output_path to the input JSON, so the tool overwrote its
    input and the promised .txt never appeared (first public-runner heartbeat, 0/50)."""
    (WORK / "doc_f10.json").write_text(json.dumps({"a": {"b": 7}}), encoding="utf-8")
    goal = f'Run the jq query with jq filter ".a.b" on {REL}/doc_f10.json and save the output to {REL}/answer_f10.txt.'
    compiled = front.compile_goal(goal, _registry(), ROOT)
    assert compiled["selected_capability"] == "json.query.jq"
    assert compiled["inputs"]["json_path"] == REL + "/doc_f10.json"
    assert compiled["inputs"]["output_path"] == REL + "/answer_f10.txt"
    assert compiled["inputs"]["jq_filter"] == ".a.b"
    # the repair helper itself: a colliding output is rebound to the one future artifact
    inputs = {"json_path": REL + "/doc_f10.json", "output_path": REL + "/doc_f10.json"}
    assert front.repair_output_collisions(goal, inputs, ROOT) == ["output_path"]
    assert inputs["output_path"] == REL + "/answer_f10.txt"
    # two future artifacts named: no guess, fail closed
    goal2 = f'Run the jq query with jq filter ".a.b" on {REL}/doc_f10.json and save the output to {REL}/one_f10.txt or {REL}/two_f10.txt.'
    inputs2 = {"json_path": REL + "/doc_f10.json", "output_path": REL + "/doc_f10.json"}
    with pytest.raises(gc.GoalCompilationFailure):
        front.repair_output_collisions(goal2, inputs2, ROOT)


def _solve_real_dag(task_id: str, goal: str):
    """Run the public entry; skip only an explicitly reported missing pinned tool environment."""
    try:
        result = adm.solve({"task_id": task_id, "goal": goal})
    finally:
        _cleanup(task_id)
    reason = str(result.get("reason") or "")
    if reason.startswith("Blocker:BOUND_"):
        pytest.skip("dependency-complete heartbeat runner required: " + reason)
    assert result["pass"] is True, result
    assert result["compiler_mode"] == front.DAG_MODE
    assert result["model_dependency_count"] == 0
    return result


def _bm25_metabolic_goal(depth: int):
    """A real registered BM25 -> JSON transformations -> binary-codec pipeline."""
    base = WORK / ("metabolic_real_%d" % depth)
    base.mkdir(parents=True, exist_ok=True)
    source = base / "candidates.json"
    source.write_text(json.dumps({
        "objective": "compare orbital battery endurance evidence",
        "candidates": [
            {"title": "Orbital battery endurance evidence", "snippet": "battery endurance in orbit"},
            {"title": "Garden irrigation", "snippet": "soil and water"},
        ],
    }), encoding="utf-8")
    rel = lambda name: str((base / name).relative_to(ROOT)).replace("\\", "/")
    json_paths = [rel("stage_%02d.json" % i) for i in range(1, 8)]
    clauses = [
        f"Rank source candidates in {rel('candidates.json')} for objective relevance with BM25 and save output to {json_paths[0]}"
    ]
    # Explicit clauses exercise the ordinary router and binder; no action plan is injected.
    for index in range(1, min(depth, 7)):
        clauses.append(f'Run the jq query with jq filter "." on {json_paths[index - 1]} and save output to {json_paths[index]}')
    if depth >= 8:
        clauses.append(f"Encode JSON {json_paths[6]} using msgpack Python and save output to {rel('stage_08.msgpack')}")
    if depth >= 9:
        clauses.append(f"Encode JSON {json_paths[6]} using bson modern Python and save output to {rel('stage_09.bson')}")
    if depth >= 10:
        clauses.append(f"Encode JSON {json_paths[6]} using CBOR npm and save output to {rel('stage_10.cbor')}")
    return ". Then ".join(clauses) + ".", base, json_paths


def _assert_real_metabolic_dag(depth: int):
    goal, base, json_paths = _bm25_metabolic_goal(depth)
    task_id = "TEST_F11_REAL_%d_%d" % (depth, os.getpid())
    result = _solve_real_dag(task_id, goal)
    dag = result["capability_dag"]
    assert len(result["selected_plan"]) == depth
    assert [step["cycle"] for step in dag["steps"]] == list(range(depth))
    assert len(dag["artifact_edges"]) == depth - 1
    for edge in dag["artifact_edges"]:
        assert edge["producer_cycle"] < edge["consumer_cycle"]
        assert edge["produced_path"] in dag["steps"][edge["producer_cycle"]]["artifacts_produced"]
    ranked = json.loads((ROOT / json_paths[0]).read_text(encoding="utf-8"))
    assert ranked["status"] == "LEXICAL_RELEVANCE_RANKED"
    assert ranked["top_candidate_original_index"] == 0
    for path in json_paths[:min(depth, 7)]:
        assert json.loads((ROOT / path).read_text(encoding="utf-8"))["top_candidate_original_index"] == 0
    if depth >= 8:
        assert (base / "stage_08.msgpack").read_bytes()
    if depth >= 9:
        raw = (base / "stage_09.bson").read_bytes()
        assert len(raw) >= 5 and int.from_bytes(raw[:4], "little") == len(raw)
    if depth >= 10:
        assert (base / "stage_10.cbor").read_bytes()
    return result


def test_f11_multi_step_capability_dag_planned_and_executed():
    source = WORK / "f11_archive_source.txt"
    manifest = WORK / "f11_archive_manifest.json"
    archive = WORK / "f11_archive.tar.gz"
    source.write_text("real cross-format artifact\n", encoding="utf-8")
    manifest.write_text(json.dumps({"records": [{"verification_paths": [str(source.relative_to(ROOT))]}]}), encoding="utf-8")
    goal = (f"Build a tar.gz archive from manifest {manifest.relative_to(ROOT)} and write it to {archive.relative_to(ROOT)}. "
            f"Then verify the tar.gz archive {archive.relative_to(ROOT)} against manifest {manifest.relative_to(ROOT)} with gnu tar.")
    result = _solve_real_dag("TEST_F11_ARCHIVE_%d" % os.getpid(), goal)
    assert result["selected_plan"] == ["archive.tar_gz.create_from_manifest", "archive.verify.tar_gz.gnu"]
    assert len(result["capability_dag"]["artifact_edges"]) == 1
    import tarfile
    with tarfile.open(archive, "r:gz") as tf:
        assert str(source.relative_to(ROOT)) in tf.getnames()


def test_f11_multi_step_capability_dag_with_bm25_ranking():
    result = _assert_real_metabolic_dag(3)
    assert result["selected_plan"][0] == "source.objective_relevance.rank.bm25"
    assert result["selected_plan"][1:] == ["json.query.jq", "json.query.jq"]


def test_f11_five_step_metabolic_dag_executed_and_verified():
    _assert_real_metabolic_dag(5)


def test_f11_eight_step_metabolic_dag_executed_and_verified():
    _assert_real_metabolic_dag(8)


def test_f11_ten_step_metabolic_dag_executed_and_verified():
    result = _assert_real_metabolic_dag(10)
    assert result["selected_plan"][-3:] == ["auto.pypi.msgpack", "auto.pypi.bson-modern", "auto.npm.dfinity-cbor"]
