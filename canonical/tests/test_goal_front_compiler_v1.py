"""The one mouth: every bound capability reachable from a sentence, and the pinned compiler's
measured defects corrected in front of it (goal_front_compiler_v1 F1-F9)."""
from __future__ import annotations

import json
import pytest
import os
import random
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


def _skip_if_the_machine_lacks_the_dependency(res):
    """A DAG step that cannot import its dependency is not a broken DAG result.

    Measured on this box: the four multi-step tests stop at
    ``ModuleNotFoundError: No module named 'et_xmlfile'`` -- openpyxl's own
    dependency.  The admission result now says so
    (``BLOCKED__CAPABILITY_DAG_ENVIRONMENT_BLOCKER``, ``failure_kind:
    ENVIRONMENT_BLOCKER``, ``blocked_by: et_xmlfile``) instead of calling the run an
    invalid result, and a test that asserts ``pass is True`` would be asserting that
    this box has a library it does not have.  The repo already treats an
    environment-blocked capability as "not a pass and not a defect" -- the end-to-end
    harness counts these families under ``environment_blocked_here`` -- so the test
    skips, naming the dependency, rather than pretending the chain is broken.
    """
    if res.get("failure_kind") == "ENVIRONMENT_BLOCKER":
        pytest.skip("ENVIRONMENT_BLOCKER:" + str(res.get("blocked_by") or res.get("reason")))
    return res


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


def test_an_unstated_key_value_mapping_defaults_to_the_empty_mapping():
    """No binding was stated for a key/value input, so the only non-guessed value is the
    empty mapping. The capability that owns the semantics still fails closed on any symbol
    it cannot resolve, so this must not turn an unanswerable goal into a pass."""
    assert front.bind_typed_key("evaluate the expression 2**10 + 3*4", "variables", ROOT) == {}
    # a real binding still wins
    assert front.bind_typed_key(
        'expression "2*x+1" with variables x=2, y=3', "variables", ROOT
    ) == {"x": 2, "y": 3}


def test_f14_an_unbound_symbol_still_fails_closed_at_execution():
    """F14: the {} default must not let a goal with free variables through. The sympy
    adapter inspects the AST and raises NUMERIC_EXPRESSION_VARIABLE_UNBOUND, so the
    default only admits expressions that genuinely need no bindings."""
    closed = adm.solve({"task_id": "F14_SYMBOLIC", "goal": 'Evaluate the expression "x**2 + 2*x + 1".'})
    assert closed["pass"] is False
    assert "NUMERIC_EXPRESSION_VARIABLE_UNBOUND" in str(closed["reason"])
    numeric = adm.solve({"task_id": "F14_NOVARS", "goal": "Evaluate the expression 2**10 + 3*4."})
    assert numeric["pass"] is True
    assert numeric["status"].startswith("PASS")


def test_inputs_are_never_guessed():
    (WORK / "data2.json").write_text("{}", encoding="utf-8")
    try:
        front.bind_typed_key(f"Query {REL}/data2.json with jq", "jq_filter", ROOT)
    except gc.GoalCompilationFailure as exc:
        assert exc.code == "GOAL_INPUT_BINDING_REQUIRED"
    else:
        raise AssertionError("a missing input must fail closed")


def test_every_capability_is_reachable_from_one_sentence_by_prose_or_by_name():
    report = reachability(WORK / "reach")
    counts = report["counts"]
    assert counts.get("NOT_REACHABLE", 0) == 0, [r for r in report["rows"] if r["state"] == "NOT_REACHABLE"]
    assert counts.get("ROUTED_ELSEWHERE", 0) == 0, [r for r in report["rows"] if r["state"] == "ROUTED_ELSEWHERE"]
    # prose binding reaches the input-bearing capabilities (F1..F13); explicit naming (F15)
    # reaches the input-free ones. No capability is structurally unreachable any more.
    assert counts.get("BLOCKED_ZERO_INPUT", 0) == 0
    assert counts["REACHED_AND_BOUND"] + counts.get("REACHED_BY_EXPLICIT_NAME", 0) == report["capabilities_total"]
    assert counts["REACHED_AND_BOUND"] >= 63


def test_every_capability_is_reachable_BY_PROSE_alone():
    """A plain sentence reaches EVERY capability - the id is never needed.

    Measured before this rule: the metric asked the easy question for the 296 capabilities
    that take no input ("can the caller spell the internal id?") and reported them as
    REACHED_BY_EXPLICIT_NAME, so 296 capabilities looked unreachable by a sentence when the
    machine in fact reached them by prose.  The metric now asks the PROSE question first, and
    the honest answer is that prose alone reaches all of them.
    """
    report = reachability(WORK / "reach_prose")
    counts = report["counts"]
    assert counts.get("NOT_REACHABLE", 0) == 0, [r for r in report["rows"] if r["state"] == "NOT_REACHABLE"]
    assert counts.get("ROUTED_ELSEWHERE", 0) == 0, [r for r in report["rows"] if r["state"] == "ROUTED_ELSEWHERE"]
    assert counts.get("REACHED_BY_EXPLICIT_NAME", 0) == 0, [
        r for r in report["rows"] if r["state"] == "REACHED_BY_EXPLICIT_NAME"][:10]
    assert counts["REACHED_AND_BOUND"] == report["capabilities_total"], counts


# ------------------------------------------- F27/F28: the request's own words decide


def test_f27_a_request_that_states_a_version_excludes_the_other_versions():
    """F27: "audit v2" is not a request for v1.

    Measured: the version token is diluted - it appears in 88% of the corpus, so its IDF is
    nearly zero and it moved the score by hundredths (46.18 against 46.14) - so a near-tied
    sibling of a DIFFERENT version shrank the margin of a request that had already excluded
    it, and the request failed closed on a capability it had named exactly.
    """
    from canonical.runtime import capability_selection_retrieval_v1 as sel
    reg = _registry()
    goal = "Run the composition cross step no bypass audit v2."
    compiled = front.compile_goal(goal, reg, ROOT)
    assert compiled.get("selected_capability") == "canonical/runtime/composition_cross_step_no_bypass_audit_v2.py.auto.v1"

    # the request's version excludes the other version from the contest
    proposals = [{"capability_id": "canonical/runtime/composition_cross_step_no_bypass_audit_v1.py.auto.v1",
                  "lexical_relevance_score": 46.18},
                 {"capability_id": "canonical/runtime/composition_cross_step_no_bypass_audit_v2.py.auto.v1",
                  "lexical_relevance_score": 46.14}]
    kept, excluded = sel.request_excluded_proposals(goal, proposals)
    assert [p["capability_id"] for p in kept] == [
        "canonical/runtime/composition_cross_step_no_bypass_audit_v2.py.auto.v1"]
    assert excluded and excluded[0]["excluded_by"] == "F27_REQUESTED_VERSION_EXCLUDES_OTHER_VERSION"


def test_f28_a_candidate_that_adds_an_unstated_word_is_not_the_one_asked_for():
    """F28: the request never said "hblind", so the hblind variant is not what it asked for.

    Measured: "Run the bytes active query task generator." was contested by
    `bytes_hblind_active_query_task_generator_v1`, whose extra word appears nowhere in the
    request.  The general capability is the one that was asked for.
    """
    from canonical.runtime import capability_selection_retrieval_v1 as sel
    goal = "Run the bytes active query task generator."
    proposals = [{"capability_id": "canonical/runtime/bytes_active_query_task_generator_v1.py.auto.v1",
                  "lexical_relevance_score": 34.14},
                 {"capability_id": "canonical/runtime/bytes_hblind_active_query_task_generator_v1.py.auto.v1",
                  "lexical_relevance_score": 33.57}]
    kept, excluded = sel.request_excluded_proposals(goal, proposals)
    assert [p["capability_id"] for p in kept] == [
        "canonical/runtime/bytes_active_query_task_generator_v1.py.auto.v1"]
    assert excluded and excluded[0]["excluded_by"] == "F28_UNSTATED_DISTINGUISHING_WORD"


def test_a_version_token_is_a_name_fragment_and_not_a_stated_value():
    """A bare "v1" names a capability; it is not a value the caller supplied.

    Measured: "Run the p3 binary decision grounded expression v1." bound the `expression`
    input to the string "v1", so the request for a capability NAMED
    `p3_binary_decision_grounded_expression_v1` was served by `math.numeric_expression.sympy`
    with the expression "v1" - a number, not an expression.  A QUOTED value is still a value.
    """
    reg = _registry()
    goal = "Run the p3 binary decision grounded expression v1."
    compiled = front.compile_goal(goal, reg, ROOT)
    assert compiled.get("selected_capability") == "canonical/runtime/p3_binary_decision_grounded_expression_v1.py.auto.v1"
    assert compiled.get("inputs", {}).get("expression") != "v1"


def test_the_compiler_does_not_crash_when_the_repository_root_is_a_string():
    """A compiler that crashes is not a compiler that fails closed.

    Measured: `repair_output_collisions` declared `root: pathlib.Path` but the retrieval path
    passes whatever the caller gave it; a request naming "p3 binary decision grounded
    expression v1" died on `root / value` with `unsupported operand type(s) for /: 'str' and
    'str'`.  The type is settled inside the function rather than at each call site.
    """
    reg = _registry()
    goal = "Run the p3 binary decision grounded expression v1."
    compiled = front.compile_goal(goal, reg, str(ROOT))
    assert compiled.get("selected_capability") == "canonical/runtime/p3_binary_decision_grounded_expression_v1.py.auto.v1"


def test_a_plain_sentence_executes_a_receipt_backed_capability_and_matches_the_CI_oracle():
    """The one entry reaches a receipt-backed capability by NAME, runs it, and the result
    reproduces the hash GitHub Actions minted for it.

    The expected value is computed by a DIFFERENT identity, on different hardware, and this
    machine never produced it.  That is what makes it an oracle rather than a self-report.
    """
    from execution_guard.live_solver_families_v7 import gen_receipt_prose_execution
    rng = random.Random(20261019)
    case = gen_receipt_prose_execution(rng, WORK / "v7", 0)
    assert case.family == "RECEIPT_PROSE_EXECUTION"
    assert not case.goal.startswith("run "), case.goal
    task_id = "TEST_V7_PROSE_%d" % os.getpid()
    try:
        result = adm.solve({"task_id": task_id, "goal": case.goal})
        good, why = case.oracle(result)
        assert good, f"{case.goal} -> {why}"
    finally:
        _cleanup(task_id)


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

        _skip_if_the_machine_lacks_the_dependency(res)
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

        _skip_if_the_machine_lacks_the_dependency(res)
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

        _skip_if_the_machine_lacks_the_dependency(res)
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

        _skip_if_the_machine_lacks_the_dependency(res)
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




def test_f13_intermediate_spool_assigned_when_the_sentence_names_no_artifact():
    """F13: a producer and its consumer agree on an intermediate the sentence never names.

    The pinned behaviour failed closed with ``json_path:0_type_compatible_existing_files_named``
    because the step-1 artifact did not exist yet and step 2 named no file of its own.  The DAG
    planner now assigns a deterministic spool path, so the data flows without being invented.
    """
    yaml_in = WORK / "f13_source.yaml"
    yaml_in.write_text("items:\n  - item: Alpha\n    count: 10\n    score: 95\n", encoding="utf-8")
    # NOTE: the intermediate JSON is deliberately absent from the sentence.
    goal = (
        f"Convert the yaml file {REL}/f13_source.yaml to json. "
        f"Then create an excel spreadsheet from json records with columns item, count, score."
    )
    for stale in WORK.glob("spool_*"):
        if stale.is_file():
            stale.unlink()

    compiled = front.compile_goal(goal, _registry(), ROOT)
    assert compiled["compiler_mode"] == "FRONT_CAPABILITY_DAG_PLANNED"
    assert "F13_INTERMEDIATE_SPOOL_ASSIGNED" in compiled["front_compiler"]["rules_applied"]
    producer = compiled["compiled_parts"][0]["inputs"]["output_path"]
    consumer = compiled["compiled_parts"][1]["inputs"]["json_path"]
    # the consumer reads exactly the artifact the producer writes, and it is a spool
    assert producer == consumer
    assert producer.startswith("canonical/astra_runtime/tmp/spool_")
    assert producer.endswith(".json")

    # ... and the whole thing really executes with zero spend
    task_id = "TEST_F13_SPOOL_%d" % os.getpid()
    try:
        res = adm.solve({"task_id": task_id, "goal": goal})
    finally:
        _cleanup(task_id)
    assert res["pass"] is True, res.get("status")
    assert res["compiler_mode"] == "FRONT_CAPABILITY_DAG_PLANNED"
    assert (ROOT / producer).is_file()


def test_f13_spooling_never_overrides_an_artifact_the_sentence_names():
    """A named artifact still wins; spooling only fills a silence, never a stated intent."""
    (WORK / "named_f13.json").write_text(json.dumps({"a": {"b": 3}}), encoding="utf-8")
    goal = (
        f'Run the jq query with jq filter ".a.b" on {REL}/named_f13.json '
        f"and save the output to {REL}/named_out_f13.json."
    )
    compiled = front.compile_goal(goal, _registry(), ROOT)
    assert compiled["inputs"]["output_path"] == REL + "/named_out_f13.json"
    assert "F13_INTERMEDIATE_SPOOL_ASSIGNED" not in compiled["front_compiler"]["rules_applied"]


def test_f13_ambiguity_still_fails_closed():
    """Two candidate artifacts are still an ambiguity, not a spooling opportunity."""
    (WORK / "amb_f13.json").write_text(json.dumps({"a": 1}), encoding="utf-8")
    inputs = {"json_path": REL + "/amb_f13.json", "output_path": REL + "/amb_f13.json"}
    goal = (
        f'Run the jq query with jq filter ".a" on {REL}/amb_f13.json '
        f"and save the output to {REL}/one_f13.json or {REL}/two_f13.json."
    )
    with pytest.raises(gc.GoalCompilationFailure):
        front.repair_output_collisions(goal, inputs, ROOT, cycle=0, spool=set())


def _zero_input_cid() -> str:
    return next(c for c, e in sorted(_registry().items()) if not front.is_plain_goal_routable(e))


def _path_shaped_zero_input_cid() -> str:
    """For the F16 demonstration, deliberately a PATH-shaped id.

    The defect shown below is the pinned compiler binding an id token as `output_path`, which
    it only does for a token that looks like a path; with a bare-token id it refuses for a
    different reason and the demonstration would be measuring the wrong thing.  Sorted-first
    is not a shape, so the shape is asked for explicitly.
    """
    return next(c for c, e in sorted(_registry().items())
                if not front.is_plain_goal_routable(e) and c.endswith(".py.auto.v1"))


def _input_bearing_cid() -> str:
    return next(c for c, e in sorted(_registry().items()) if front.is_plain_goal_routable(e))


def test_f15_a_goal_that_names_a_capability_selects_that_capability_and_not_a_catch_all():
    """F15: an id in the sentence is the caller choosing, and defect 8 strips paths, so the
    pinned compiler cannot see the choice - it answered with a generic candidate instead."""
    reg = _registry()
    cid = _zero_input_cid()
    compiled = front.compile_goal(f"run {cid}", reg, ROOT)
    assert compiled["selected_capability"] == cid
    assert compiled["inputs"] == {}
    assert compiled["target_effects"] == list(reg[cid]["provides"])
    assert "F15_EXPLICIT_CAPABILITY_ID_NAMED" in compiled["front_compiler"]["rules_applied"]
    # what the creature would execute is the named capability, with its own frozen argv
    action = gc._render_template(reg[cid]["action_template"], dict(compiled["inputs"]))
    assert action["type"] == "invoke_capability"
    assert action["args"]["capability_id"] == cid
    # the defect being corrected: without F15 the id selects something else, never itself
    try:
        pinned = gc.compile_goal(f"run {cid}", front.routable_registry(reg), ROOT)
    except gc.GoalCompilationFailure:
        pinned = None
    assert (pinned or {}).get("selected_capability") != cid


def test_f15_composition_is_never_stolen_by_a_named_capability():
    """F15 is naming, not routing: a sentence that keeps asking for more still fails closed."""
    cid = _zero_input_cid()
    try:
        compiled = front.compile_goal(f"run {cid} and then summarize the outcome", _registry(), ROOT)
    except gc.GoalCompilationFailure:
        return  # the normal machinery decided - F15 did not claim the request
    assert "F15_EXPLICIT_CAPABILITY_ID_NAMED" not in compiled["front_compiler"]["rules_applied"]


def test_f15_two_named_capabilities_are_not_a_single_naming():
    """Two ids are a composition, not a choice; the decision stays with the normal machinery."""
    zero = [c for c, e in sorted(_registry().items()) if not front.is_plain_goal_routable(e)]
    assert len(zero) >= 2
    try:
        compiled = front.compile_goal(f"run {zero[0]} and run {zero[1]}", _registry(), ROOT)
    except gc.GoalCompilationFailure:
        return
    assert "F15_EXPLICIT_CAPABILITY_ID_NAMED" not in compiled["front_compiler"]["rules_applied"]


def test_f15_a_named_capability_that_needs_inputs_still_fails_closed():
    """Naming never fabricates inputs: the missing binding is reported, not guessed."""
    cid = _input_bearing_cid()
    with pytest.raises(gc.GoalCompilationFailure) as excinfo:
        front.compile_goal(f"run {cid}", _registry(), ROOT)
    assert excinfo.value.code == "GOAL_INPUT_BINDING_REQUIRED"


def test_f15_identifier_boundaries_and_a_sentence_final_period():
    """A longer identifier is a different identifier; a sentence-final period is not."""
    reg = _registry()
    cid = _zero_input_cid()
    assert front.explicitly_named_capabilities(f"run {cid}", reg) == [cid]
    assert front.explicitly_named_capabilities(f"run {cid}.", reg) == [cid]
    assert front.explicitly_named_capabilities(f"run {cid}x", reg) == []
    assert front.explicitly_named_capabilities("run something else entirely", reg) == []


def test_f16_an_id_shaped_path_that_no_capability_answers_to_fails_closed():
    """F16: an id-shaped token is an identity, not an artifact.

    The defect, shown first: the pinned compiler binds the named path as `output_path` for a
    generic candidate, which then reports `output_verified: true` by writing a file at the
    capability's own id path - so asking for a capability that does not exist produced a
    success and a fabricated artifact.  Measured on the real registry: 224 of 294 goals that
    named a real capability "succeeded" that way."""
    reg = _registry()
    cid = _path_shaped_zero_input_cid()
    ghost = cid.rsplit(".py.auto.v1", 1)[0] + "_renamed.py.auto.v1"
    goal = f"run {ghost}"
    pinned = gc.compile_goal(goal, front.routable_registry(reg), ROOT)
    assert pinned["inputs"]["output_path"] == ghost
    assert pinned["selected_capability"] != ghost
    with pytest.raises(gc.GoalCompilationFailure) as excinfo:
        front.compile_goal(goal, reg, ROOT)
    assert excinfo.value.code == "GOAL_NAMES_UNKNOWN_CAPABILITY"


def test_f16_a_registered_capability_inside_a_longer_request_is_not_an_artifact():
    """A registered id inside a longer sentence is a composition this layer does not claim;
    it fails closed instead of being handed to another capability as an output artifact."""
    cid = _zero_input_cid()
    with pytest.raises(gc.GoalCompilationFailure) as excinfo:
        front.compile_goal(f"run {cid} and then report the outcome to me", _registry(), ROOT)
    assert excinfo.value.code == "GOAL_NAMES_CAPABILITY_IN_COMPOUND_REQUEST"


# ------------------------------------------------------------------------------- F23: role-anchored inputs


def test_f23_two_same_type_inputs_bind_by_the_roles_the_sentence_states():
    """F23: two JSON files, two roles, one binding each - and no name ever spells a key.

    The defect, shown here: the pinned binder and the type fallback BOTH refuse this
    sentence, because two named files share the type of ``metadata_path`` and neither file
    is called *metadata*::

        GOAL_INPUT_BINDING_REQUIRED:pypi.provenance.audit_live_artifact:
        metadata_path:2_type_compatible_existing_files_named

    The request states the roles in words ("... on <file> with selection <file>"), so the
    compiler reads that statement: the selection role names its file, and the one file
    left for the one key left is a forced assignment, not a guess.
    """
    (WORK / "meta23.json").write_text(json.dumps({"info": {"name": "x"}}), encoding="utf-8")
    (WORK / "sel23.json").write_text(json.dumps({"id": "cap.x", "record": {}}), encoding="utf-8")
    goal = (f"Audit the pypi wheel artifact provenance and sha256 download hash on {REL}/meta23.json "
            f"with selection {REL}/sel23.json and save the report to {REL}/rep23.json")
    # the pinned compiler alone cannot bind this sentence: it falls through to a capability
    # that has nothing to do with the request (the F1 defect) instead of the pypi audit
    pinned = gc.compile_goal(goal, front.routable_registry(_registry()), ROOT)
    assert pinned.get("selected_capability") != "pypi.provenance.audit_live_artifact"
    compiled = front.compile_goal(goal, _registry(), ROOT)
    assert compiled["selected_capability"] == "pypi.provenance.audit_live_artifact"
    assert compiled["inputs"]["metadata_path"] == REL + "/meta23.json"
    assert compiled["inputs"]["selection_path"] == REL + "/sel23.json"
    assert compiled["inputs"]["report_path"] == REL + "/rep23.json"
    # the fail-closed admission layer accepts the plan: nothing was invented
    assert adm.route_admission(goal, compiled, _registry())["admitted"] is True


def test_f23_a_role_in_front_of_a_conjunction_stays_open():
    """A role word in front of a CONJUNCTION governs every member of the group.

    "the manifest a.json and b.json" does not say which file is the manifest, so the
    compiler keeps the request open instead of taking the first one it sees.
    """
    (WORK / "a23.json").write_text("{}", encoding="utf-8")
    (WORK / "b23.json").write_text("{}", encoding="utf-8")
    goal = (f"Create a tar.gz archive from the manifest {REL}/a23.json and {REL}/b23.json "
            f"and save it to {REL}/bundle23.tar.gz.")
    with pytest.raises(gc.GoalCompilationFailure) as excinfo:
        front.compile_goal(goal, _registry(), ROOT)
    assert excinfo.value.code == "GOAL_INPUT_BINDING_REQUIRED"
    assert "manifest_path" in str(excinfo.value.detail)


def test_f23_a_sentence_without_roles_does_not_get_a_mapping_invented():
    """Two files, two keys, no role: the mapping is ambiguous, so it fails closed.

    The F23 binder disposes of what the SENTENCE states.  It never completes a mapping the
    sentence leaves open - a capability that needs two documents cannot be told which is
    which by the order they happen to appear in.
    """
    (WORK / "meta24.json").write_text(json.dumps({"info": {"name": "x"}}), encoding="utf-8")
    (WORK / "sel24.json").write_text(json.dumps({"id": "cap.x", "record": {}}), encoding="utf-8")
    goal = (f"Audit the pypi wheel artifact provenance and sha256 download hash on {REL}/meta24.json "
            f"and {REL}/sel24.json and save the report to {REL}/rep24.json")
    with pytest.raises(gc.GoalCompilationFailure) as excinfo:
        front.compile_goal(goal, _registry(), ROOT)
    assert excinfo.value.code == "GOAL_INPUT_BINDING_REQUIRED"


# ------------------------------------------------------------------- F24: the route must be executable


def test_f24_a_candidate_the_sentence_never_gave_its_input_is_not_the_route():
    """F24: the lexical score is a hint; the words of the request are the decision.

    "Collect the external knowledge JSON document <url> with json path [] as authoritative
    true and store it in <out>" scores HIGHER for a DOCX creator (the words "json" and
    "document" are in its very name) than for the knowledge fetcher - and the DOCX creator
    needs a JSON FILE that the sentence never states.  Measured before the fix: the request
    failed closed with GOAL_INPUT_BINDING_REQUIRED on the DOCX creator's json_path.
    """
    goal = (f"Collect the external knowledge JSON document https://pypi.org/pypi/six/1.17.0/json "
            f"with json path [] as authoritative true and store it in {REL}/know24.json")
    compiled = front.compile_goal(goal, _registry(), ROOT)
    assert compiled["selected_capability"] == "knowledge.json.fetch.external"
    assert compiled["inputs"]["url"] == "https://pypi.org/pypi/six/1.17.0/json"
    assert compiled["inputs"]["json_path"] == []
    assert compiled["inputs"]["authoritative"] is True
    assert compiled["inputs"]["output_path"] == REL + "/know24.json"


def test_f24_a_runtime_native_capability_is_admitted_on_the_contract_the_sentence_states():
    """The knowledge actions run INSIDE the runtime, not through an adapter entrypoint.

    Typed admission used to refuse them for that reason, so a sentence that stated their
    contract perfectly was rejected R3_WEAK_EVIDENCE while every adapter capability was
    admitted on the strength of the sentence alone.
    """
    record = {
        "schema": "PROJECT_BRAIN_KNOWLEDGE_EVIDENCE_V1",
        "source_url": "https://pypi.org/pypi/six/1.17.0/json",
        "http_status": 200,
        "json_path": [],
        "value": "1.17.0",
        "retrieved_at_utc": "2026-10-19T10:00:00Z",
        "body_sha256": "a" * 64,
        "source_type": "authoritative_external_json",
    }
    (WORK / "ev24a.json").write_text(json.dumps(record), encoding="utf-8")
    (WORK / "ev24b.json").write_text(json.dumps(record), encoding="utf-8")
    goal = (f"Check whether the knowledge in {REL}/ev24a.json and {REL}/ev24b.json is consistent, "
            f"with max age seconds 600, and save the result to {REL}/assessment24.json")
    compiled = front.compile_goal(goal, _registry(), ROOT)
    assert compiled["selected_capability"] == "knowledge.consistency.assess"
    decision = adm.route_admission(goal, compiled, _registry())
    assert decision["admitted"] is True, decision
    assert decision["admission_basis"] == "DECLARED_INPUT_CONTRACT_FULLY_STATED_IN_GOAL"


def test_f24_an_ambiguous_statement_still_keeps_the_request_open():
    """F24 never turns an ambiguous request into a decision.

    The archive creator is the capability the sentence asks for; two named JSON files for
    one manifest slot is a question the machine must not answer on its own.
    """
    (WORK / "a24.json").write_text("{}", encoding="utf-8")
    (WORK / "b24.json").write_text("{}", encoding="utf-8")
    goal = (f"Create a tar.gz archive from the manifest {REL}/a24.json and {REL}/b24.json "
            f"and save it to {REL}/bundle24.tar.gz.")
    with pytest.raises(gc.GoalCompilationFailure) as excinfo:
        front.compile_goal(goal, _registry(), ROOT)
    assert excinfo.value.code == "GOAL_INPUT_BINDING_REQUIRED"
    assert "manifest_path" in str(excinfo.value.detail)


# ------------------------------------------------------- F25: a value's words are not the task's words


def test_f25_a_quoted_literal_is_a_value_not_a_description_of_the_task():
    """F25: the words inside a quoted literal belong to the VALUE, not to the request.

    Measured: ``Apply the jq filter "[.items[].v] | add" to <file> with jq`` scored the SA-CCR
    credit add-on capability above the jq capability - the word "add" lives inside the FILTER.
    And ``with jq filter ".record.tag"`` scored a DOCX creator above jq, because the word
    "record" lives inside the filter too.  Both sentences ask for jq; both were answered by
    something else.  A URL and a path were already removed from the ranking (F8); a quoted
    literal is the same kind of thing.
    """
    work = WORK / "f25"
    work.mkdir(parents=True, exist_ok=True)
    src = work / "doc25.json"
    src.write_text(json.dumps({"a": {"b": 7}, "items": [{"v": 1}, {"v": 2}]}), encoding="utf-8")
    out = work / "q25.json"
    rel = "canonical/astra_runtime/tmp/test_goal_front_compiler/f25"
    goal = f'Apply the jq filter "[.items[].v] | add" to {rel}/doc25.json with jq and write the output to {rel}/q25.json.'
    prose = front.prose_only(goal)
    assert "add" not in prose.lower(), prose
    compiled = front.compile_goal(goal, _registry(), ROOT)
    assert compiled["selected_capability"] == "json.query.jq", compiled.get("selected_capability")
    assert compiled["inputs"]["jq_filter"] == "[.items[].v] | add"


def test_f25_the_value_itself_still_binds():
    """Removing the literal from the RANKING must not remove it from the REQUEST."""
    work = WORK / "f25b"
    work.mkdir(parents=True, exist_ok=True)
    src = work / "doc25b.json"
    src.write_text(json.dumps({"record": {"tag": "t"}}), encoding="utf-8")
    out = work / "q25b.json"
    rel = "canonical/astra_runtime/tmp/test_goal_front_compiler/f25b"
    goal = f'Apply the jq filter ".record.tag" to the json file {rel}/doc25b.json and save the output to {rel}/q25b.json.'
    compiled = front.compile_goal(goal, _registry(), ROOT)
    assert compiled["selected_capability"] == "json.query.jq", compiled.get("selected_capability")
    assert compiled["inputs"]["jq_filter"] == ".record.tag"
    assert compiled["inputs"]["json_path"] == rel + "/doc25b.json"


# ------------------------------------------- F26: a consumer's input is the producer's artifact


def test_f26_a_multi_step_request_forwards_the_producers_artifact():
    """F26: "fetch it, then audit what you fetched" is ONE graph with an artifact edge.

    Measured before F26: the request was NOT planned as a DAG at all.  The consumer bound
    the selection record instead (it was the only file on disk), the producer's artifact was
    claimed as the consumer's OUTPUT, and the request silently dropped a step.  An output is
    a NEW artifact and never claims an earlier step's; and the earlier step's artifact is
    part of the pool an input may bind from, because that is what the sentence points at.
    """
    work = WORK / "f26"
    work.mkdir(parents=True, exist_ok=True)
    (work / "sel26.json").write_text(json.dumps({"id": "cap.six", "record": {}}), encoding="utf-8")
    (work / "state26.json").write_text(json.dumps({"release_url": "https://pypi.org/pypi/six/1.17.0/json"}), encoding="utf-8")
    rel = "canonical/astra_runtime/tmp/test_goal_front_compiler/f26"
    goal = (f'Fetch the HTTP JSON live metadata from the source json {rel}/state26.json with url key '
            f'"release_url" and save it to {rel}/fetched26.json. Then audit the pypi wheel artifact '
            f'provenance and sha256 download hash on {rel}/fetched26.json with selection '
            f'{rel}/sel26.json and save the report to {rel}/rep26.json.')
    compiled = front.compile_goal(goal, _registry(), ROOT)
    assert compiled.get("compiler_mode") == front.DAG_MODE
    dag = compiled["capability_dag"]
    steps = dag["steps"]
    assert [s["capability_id"] for s in steps] == ["http.json.fetch_from_state", "pypi.provenance.audit_live_artifact"]
    # the first step writes the file the second step reads
    assert steps[0]["action"]["args"]["output_path"] == rel + "/fetched26.json"
    forwarded = steps[1]["action"]["args"]["metadata_path"]
    assert forwarded == {"$result": {"cycle": 0, "field": "output_path"}}, forwarded
    # the consumer's own output is a NEW artifact, not the producer's
    assert steps[1]["action"]["args"]["report_path"] == rel + "/rep26.json"
    assert steps[1]["action"]["args"]["selection_path"] == rel + "/sel26.json"
    edges = dag["artifact_edges"]
    assert len(edges) == 1 and edges[0]["producer_cycle"] == 0 and edges[0]["consumer_cycle"] == 1
    assert edges[0]["input_key"] == "metadata_path"
