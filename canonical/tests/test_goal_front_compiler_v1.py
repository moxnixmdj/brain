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
    assert "terminal.kstar.root.assess.stdlib" in blocked
    assert not any(cid in front.routable_registry(registry) for cid in blocked)
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
    assert counts["REACHED_AND_BOUND"] + counts["BLOCKED_ZERO_INPUT"] == report["capabilities_total"]
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


def test_f11_multi_step_capability_dag_planned_and_executed():
    """Autonomous cross-format multi-step capability chaining:
    Step 1: yaml.to_json.yq converts YAML to JSON.
    Step 2: xlsx.table.create_from_json_records consumes JSON from Step 1 and builds an Excel workbook.
    Step 3: xlsx.table.verify_against_json_records verifies the workbook against Step 1's JSON.
    """
    yaml_in = WORK / "dag_data.yaml"
    json_out = WORK / "dag_intermediate.json"
    xlsx_out = WORK / "dag_metrics.xlsx"
    for p in (json_out, xlsx_out):
        if p.exists():
            p.unlink()

    yaml_in.write_text("items:\n  - item: Alpha\n    count: 10\n    score: 95\n  - item: Beta\n    count: 20\n    score: 88\n", encoding="utf-8")
    goal = (
        f"Convert the yaml file {REL}/dag_data.yaml to json and save to {REL}/dag_intermediate.json. "
        f"Then create an excel spreadsheet at {REL}/dag_metrics.xlsx from json records at {REL}/dag_intermediate.json with columns item, count, score. "
        f"Then verify the excel spreadsheet at {REL}/dag_metrics.xlsx against json records at {REL}/dag_intermediate.json with columns item, count, score."
    )
    task_id = "TEST_DAG_CHAIN_%d" % os.getpid()
    try:
        res = adm.solve({"task_id": task_id, "goal": goal})
    finally:
        _cleanup(task_id)

    assert res["pass"] is True, res.get("status")
    assert res["compiler_mode"] == "FRONT_CAPABILITY_DAG_PLANNED"
    assert res["status"] == "PASS__CAPABILITY_DAG_EXECUTED_AND_VERIFIED__RAW_ACCEPTANCE_RECEIPTS_STILL_REQUIRED"
    assert json_out.is_file()
    assert xlsx_out.is_file()
    assert xlsx_out.read_bytes().startswith(b"PK\x03\x04")


def test_f11_multi_step_capability_dag_with_bm25_ranking():
    """Autonomous multi-step pipeline linking Python AST source auditing and BM25 lexical ranking."""
    src_dir = WORK / "dag_py_src"
    src_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "calc.py").write_text("def solve_problem(x):\n    return x ** 2\n", encoding="utf-8")
    audit_out = WORK / "dag_audit.json"

    docs_in = WORK / "dag_docs.json"
    docs_in.write_text(json.dumps({
        "objective": "caching mechanisms",
        "candidates": [
            {"title": "Cache Doc", "snippet": "caching mechanisms and in-memory caches"},
            {"title": "Other Doc", "snippet": "unrelated hardware storage protocols"}
        ]
    }), encoding="utf-8")
    rank_out = WORK / "dag_ranked.json"

    for p in (audit_out, rank_out):
        if p.exists():
            p.unlink()

    goal = (
        f"Audit the python sources in {REL}/dag_py_src with ast and save the report to {REL}/dag_audit.json. "
        f"Then rank candidate sources in {REL}/dag_docs.json for objective relevance with BM25 and save to {REL}/dag_ranked.json."
    )
    task_id = "TEST_DAG_BM25_%d" % os.getpid()
    try:
        res = adm.solve({"task_id": task_id, "goal": goal})
    finally:
        _cleanup(task_id)

    assert res["pass"] is True, res.get("status")
    assert res["compiler_mode"] == "FRONT_CAPABILITY_DAG_PLANNED"
    assert audit_out.is_file()
    assert rank_out.is_file()
    audit_data = json.loads(audit_out.read_text(encoding="utf-8"))
    assert audit_data["totals"]["functions"] == 1
    rank_data = json.loads(rank_out.read_text(encoding="utf-8"))
    assert rank_data["status"] == "LEXICAL_RELEVANCE_RANKED"


def test_f11_five_step_metabolic_dag_executed_and_verified():
    """Autonomous 5-step cross-format closed-loop capability DAG:
    Cycle 0: yaml.to_json.yq converts YAML to JSON.
    Cycle 1: docx.document.create_from_json_record consumes JSON and builds Word document.
    Cycle 2: docx.document.verify.intent_ooxml verifies the Word document against intent sidecar.
    Cycle 3: sqlite.table.create_from_json_records consumes JSON and creates SQLite table.
    Cycle 4: sqlite.table.verify_against_json_records verifies SQLite table against JSON.
    """
    yaml_in = WORK / "pipe5_data.yaml"
    yaml_in.write_text("rec1:\n  capability_id: cap_1\n  author: AutonomousBrain\n  status: ACTIVE\n  score: 100\n", encoding="utf-8")
    json_out = WORK / "pipe5_data.json"
    doc_out = WORK / "pipe5_audit.docx"
    db_out = WORK / "pipe5_audit.sqlite"

    for p in (json_out, doc_out, WORK / "pipe5_audit.docx.intent.json", db_out):
        if p.exists():
            p.unlink()

    goal = (
        f"Convert the yaml file {REL}/pipe5_data.yaml to json and save to {REL}/pipe5_data.json. "
        f"Then create a docx document from the json record in {REL}/pipe5_data.json and save it to {REL}/pipe5_audit.docx "
        f"with title System Audit, a paragraph Overview, and a two-column table with headers Field, Value "
        f"containing one row for each of status, author using their values from the json. "
        f"Then verify the docx document at {REL}/pipe5_audit.docx with intent ooxml independent content exact. "
        f"Then create a sqlite table in {REL}/pipe5_audit.sqlite for table named audit_tbl from the ACTIVE records in {REL}/pipe5_data.json with columns capability_id, author, status, score. "
        f"Then verify the sqlite database {REL}/pipe5_audit.sqlite against the ACTIVE records in {REL}/pipe5_data.json for the table named audit_tbl with sqlite3."
    )
    task_id = "TEST_5STEP_%d" % os.getpid()
    try:
        res = adm.solve({"task_id": task_id, "goal": goal})
    finally:
        _cleanup(task_id)

    assert res["pass"] is True, res.get("status")
    assert res["compiler_mode"] == "FRONT_CAPABILITY_DAG_PLANNED"
    assert res["status"] == "PASS__CAPABILITY_DAG_EXECUTED_AND_VERIFIED__RAW_ACCEPTANCE_RECEIPTS_STILL_REQUIRED"
    assert json_out.is_file()
    assert doc_out.is_file()
    assert db_out.is_file()
    assert len(res["route_admission"]["dag_steps"]) == 5
    assert len(res["route_admission"]["artifact_edges"]) == 5


def test_f11_eight_step_metabolic_dag_executed_and_verified():
    """Autonomous 8-step cross-modal, cross-domain metabolic pipeline:
    Cycle 0: python.source.audit.ast audits source code AST.
    Cycle 1: python.tests.audit.unittest audits unit test suite.
    Cycle 2: source.objective_relevance.rank.bm25 ranks candidates via BM25.
    Cycle 3: decision.synthesis.typed.stdlib synthesizes typed decision logic.
    Cycle 4: docx.document.create_from_json_record creates executive Word document.
    Cycle 5: docx.document.verify.intent_ooxml verifies Word document OpenXML package.
    Cycle 6: sqlite.table.create_from_json_records creates SQLite relational table.
    Cycle 7: sqlite.table.verify_against_json_records verifies relational table against JSON.
    """
    src_dir = WORK / "pipe8_src"
    src_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "engine.py").write_text("def run(): return True\n", encoding="utf-8")

    test_dir = WORK / "pipe8_tests"
    test_dir.mkdir(parents=True, exist_ok=True)
    (test_dir / "test_engine.py").write_text("import unittest\nclass T(unittest.TestCase):\n def test_r(self): self.assertTrue(True)\n", encoding="utf-8")

    docs_file = WORK / "pipe8_candidates.json"
    docs_file.write_text(json.dumps({
        "objective": "high performance caching",
        "candidates": [
            {"title": "In-Memory Cache", "snippet": "high performance caching in memory"},
            {"title": "Tape Backup", "snippet": "cold archive storage tape"}
        ]
    }))

    prob_file = WORK / "pipe8_decision_problem.json"
    prob_file.write_text(json.dumps({
        "schema": "PROJECT_BRAIN_TYPED_DECISION_PROBLEM_V1",
        "decision_id": "D_ARCH_ENG",
        "question": "Which caching solution?",
        "alternatives": [{"id": "in_memory", "label": "In-Memory"}, {"id": "tape", "label": "Tape"}],
        "constraints": [],
        "evidence": [{
            "id": "E1", "alternative": "in_memory", "relation": "SUPPORTS", "confidence": 0.99, "strength": 1.0,
            "independence_group": "bench", "claim": "in-memory meets all latency SLAs", "provenance": [{"source": "doc", "ref": "1"}]
        }],
        "policy": {"minimum_support_ratio": 0.6, "maximum_conflict_ratio": 0.5, "minimum_independent_support_groups": 1, "minimum_net_margin": 0.1}
    }))

    rec_file = WORK / "pipe8_record.json"
    rec_file.write_text(json.dumps({
        "capabilities": {
            "rec1": {
                "capability_id": "audit.report",
                "status": "ACTIVE",
                "domain": "PYTHON"
            }
        }
    }))

    src_rep = WORK / "pipe8_src_rep.json"
    test_rep = WORK / "pipe8_test_rep.json"
    rank_rep = WORK / "pipe8_rank_rep.json"
    dec_rep = WORK / "pipe8_dec_rep.json"
    docx_rep = WORK / "pipe8_audit.docx"
    db_file = WORK / "pipe8_records.db"

    for p in (src_rep, test_rep, rank_rep, dec_rep, docx_rep, WORK / "pipe8_audit.docx.intent.json", db_file):
        if p.exists():
            p.unlink()

    goal = (
        f"Audit the python sources in {REL}/pipe8_src with ast and save the report to {REL}/pipe8_src_rep.json. "
        f"Then audit the python tests in {REL}/pipe8_tests with unittest matching pattern \"test_*.py\" and save the audit report to {REL}/pipe8_test_rep.json. "
        f"Then rank candidate sources in {REL}/pipe8_candidates.json for objective relevance with BM25 and save to {REL}/pipe8_rank_rep.json. "
        f"Then synthesize a typed decision from {REL}/pipe8_decision_problem.json and save the result to {REL}/pipe8_dec_rep.json. "
        f"Then create a docx document from {REL}/pipe8_record.json with title Audit Report, paragraph Decision complete, and a table with headers Field and Value containing one row for each of capability_id and status using their values from the json and save to {REL}/pipe8_audit.docx. "
        f"Then verify the docx document intent and openxml package for {REL}/pipe8_audit.docx. "
        f"Then from ACTIVE records in {REL}/pipe8_record.json create a sqlite table named capabilities in {REL}/pipe8_records.db with columns capability_id and status. "
        f"Then verify sqlite table capabilities in {REL}/pipe8_records.db against ACTIVE records in {REL}/pipe8_record.json."
    )

    task_id = "TEST_8STEP_%d" % os.getpid()
    try:
        res = adm.solve({"task_id": task_id, "goal": goal})
    finally:
        _cleanup(task_id)

    assert res["pass"] is True, res.get("status")
    assert res["compiler_mode"] == "FRONT_CAPABILITY_DAG_PLANNED"
    assert res["status"] == "PASS__CAPABILITY_DAG_EXECUTED_AND_VERIFIED__RAW_ACCEPTANCE_RECEIPTS_STILL_REQUIRED"
    assert src_rep.is_file()
    assert test_rep.is_file()
    assert rank_rep.is_file()
    assert dec_rep.is_file()
    assert docx_rep.is_file()
    assert db_file.is_file()
    assert len(res["route_admission"]["dag_steps"]) == 8


def test_f11_ten_step_metabolic_dag_executed_and_verified():
    """Complete autonomous 10-step metabolic pipeline across six heterogeneous domains:
    Cycle 0: yaml.to_json.yq compiles YAML config to JSON record.
    Cycle 1: python.source.audit.ast audits source code AST.
    Cycle 2: python.tests.audit.unittest audits unit test suite.
    Cycle 3: source.objective_relevance.rank.bm25 ranks candidates via BM25.
    Cycle 4: decision.synthesis.typed.stdlib synthesizes typed architecture decision.
    Cycle 5: decision.synthesis.verify.stdlib independently verifies decision synthesis.
    Cycle 6: docx.document.create_from_json_record creates executive Word document.
    Cycle 7: docx.document.verify.intent_ooxml verifies Word document OpenXML package.
    Cycle 8: sqlite.table.create_from_json_records creates SQLite relational table.
    Cycle 9: sqlite.table.verify_against_json_records verifies relational table against JSON source.
    """
    yaml_in = WORK / "pipe10_data.yaml"
    yaml_in.write_text(
        "capabilities:\n  rec1:\n    capability_id: audit.report\n    status: ACTIVE\n    domain: PYTHON\n",
        encoding="utf-8",
    )
    json_out = WORK / "pipe10_record.json"

    src_dir = WORK / "pipe10_src"
    src_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "engine.py").write_text("def run(): return True\n", encoding="utf-8")

    test_dir = WORK / "pipe10_tests"
    test_dir.mkdir(parents=True, exist_ok=True)
    (test_dir / "test_engine.py").write_text(
        "import unittest\nclass T(unittest.TestCase):\n def test_r(self): self.assertTrue(True)\n",
        encoding="utf-8",
    )

    docs_file = WORK / "pipe10_candidates.json"
    docs_file.write_text(json.dumps({
        "objective": "high performance caching",
        "candidates": [
            {"title": "In-Memory Cache", "snippet": "high performance caching in memory"},
            {"title": "Tape Backup", "snippet": "cold archive storage tape"}
        ]
    }))

    prob_file = WORK / "pipe10_decision_problem.json"
    prob_file.write_text(json.dumps({
        "schema": "PROJECT_BRAIN_TYPED_DECISION_PROBLEM_V1",
        "decision_id": "D_ARCH_ENG",
        "question": "Which caching solution?",
        "alternatives": [{"id": "in_memory", "label": "In-Memory"}, {"id": "tape", "label": "Tape"}],
        "constraints": [],
        "evidence": [{
            "id": "E1", "alternative": "in_memory", "relation": "SUPPORTS", "confidence": 0.99, "strength": 1.0,
            "independence_group": "bench", "claim": "in-memory meets all latency SLAs", "provenance": [{"source": "doc", "ref": "1"}]
        }],
        "policy": {"minimum_support_ratio": 0.6, "maximum_conflict_ratio": 0.5, "minimum_independent_support_groups": 1, "minimum_net_margin": 0.1}
    }))

    src_rep = WORK / "pipe10_src_rep.json"
    test_rep = WORK / "pipe10_test_rep.json"
    rank_rep = WORK / "pipe10_rank_rep.json"
    dec_rep = WORK / "pipe10_dec_rep.json"
    docx_rep = WORK / "pipe10_audit.docx"
    db_file = WORK / "pipe10_records.db"

    for p in (json_out, src_rep, test_rep, rank_rep, dec_rep, docx_rep, WORK / "pipe10_audit.docx.intent.json", db_file):
        if p.exists():
            p.unlink()

    goal = (
        f"Convert the yaml file {REL}/pipe10_data.yaml to json and save to {REL}/pipe10_record.json. "
        f"Then audit the python sources in {REL}/pipe10_src with ast and save the report to {REL}/pipe10_src_rep.json. "
        f"Then audit the python tests in {REL}/pipe10_tests with unittest matching pattern \"test_*.py\" and save the audit report to {REL}/pipe10_test_rep.json. "
        f"Then rank candidate sources in {REL}/pipe10_candidates.json for objective relevance with BM25 and save to {REL}/pipe10_rank_rep.json. "
        f"Then synthesize a typed decision from {REL}/pipe10_decision_problem.json and save the result to {REL}/pipe10_dec_rep.json. "
        f"Then verify the typed decision synthesis for {REL}/pipe10_decision_problem.json against result {REL}/pipe10_dec_rep.json. "
        f"Then create a docx document from {REL}/pipe10_record.json with title Audit Report, paragraph Decision complete, and a table with headers Field and Value containing one row for each of capability_id and status using their values from the json and save to {REL}/pipe10_audit.docx. "
        f"Then verify the docx document intent and openxml package for {REL}/pipe10_audit.docx. "
        f"Then from ACTIVE records in {REL}/pipe10_record.json create a sqlite table named capabilities in {REL}/pipe10_records.db with columns capability_id and status. "
        f"Then verify sqlite table capabilities in {REL}/pipe10_records.db against ACTIVE records in {REL}/pipe10_record.json."
    )

    task_id = "TEST_10STEP_%d" % os.getpid()
    try:
        res = adm.solve({"task_id": task_id, "goal": goal})
    finally:
        _cleanup(task_id)

    assert res["pass"] is True, res.get("status")
    assert res["compiler_mode"] == "FRONT_CAPABILITY_DAG_PLANNED"
    assert res["status"] == "PASS__CAPABILITY_DAG_EXECUTED_AND_VERIFIED__RAW_ACCEPTANCE_RECEIPTS_STILL_REQUIRED"
    assert json_out.is_file()
    assert src_rep.is_file()
    assert test_rep.is_file()
    assert rank_rep.is_file()
    assert dec_rep.is_file()
    assert docx_rep.is_file()
    assert db_file.is_file()
    assert len(res["route_admission"]["dag_steps"]) == 10




