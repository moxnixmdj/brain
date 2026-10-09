from __future__ import annotations

import json
from pathlib import Path

from canonical.runtime import r2_finance_task_role_raw_fact_unless_direct_adequacy_v1 as d
from canonical.runtime import finance_task_role_raw_fact_unless_verify_v1 as verifier


POLICY_DECIMAL = (
    "Total exposure means exposure_amount. "
    "Apply Rule A unless Total exposure is at least 125.50."
)
POLICY_BOOL = (
    "Exception status means breach. "
    "Apply Rule A unless Exception status is true."
)


def _goal(
    inp="canonical/tmp/crossdoc_case.json",
    out="canonical/tmp/crossdoc_result.json",
):
    return (
        "Using the task-role cross-document finance UNLESS case at "
        f"{inp}, select and independently verify the applicable branch and save it "
        f"to {out}."
    )


def _bundle(
    root: Path,
    *,
    value: str = "130.00",
    policy: str = POLICY_DECIMAL,
    fact_field: str = "exposure_amount",
    fact_type: str = "DECIMAL_STRING",
    raw_fact: str | None = None,
):
    policy_rel = "canonical/tmp/policy.txt"
    fact_rel = "canonical/tmp/facts.json"
    case_rel = "canonical/tmp/crossdoc_case.json"

    pp = root / policy_rel
    fp = root / fact_rel
    cp = root / case_rel
    pp.parent.mkdir(parents=True, exist_ok=True)
    pp.write_text(policy, encoding="utf-8")

    if raw_fact is None:
        fact_value = value
        if fact_type == "BOOL":
            fact_value = value.lower() == "true"
        raw_fact = json.dumps(
            {
                "schema_id": "FINANCE_TYPED_CONTEXT_V1",
                "fields": {
                    fact_field: {"type": fact_type, "value": fact_value},
                },
            },
            separators=(",", ":"),
        )
    fp.write_text(raw_fact, encoding="utf-8")

    case = {
        "schema": "PROJECT_BRAIN_FINANCE_TASK_ROLE_RAW_FACT_UNLESS_CASE_V1",
        "task_record": {
            "task_id": "finance-crossdoc-task",
            "shared_files": [policy_rel, fact_rel],
            "week_files": [],
            "source_roles": {
                "policy_source_path": policy_rel,
                "fact_source_path": fact_rel,
            },
        },
    }
    cp.write_text(json.dumps(case), encoding="utf-8")
    return case, cp, pp, fp


def test_decimal_above_threshold_selects_exception(tmp_path: Path):
    _bundle(tmp_path, value="130.00")
    out = d.run({"task_id": "x1", "goal": _goal()}, repo_root=tmp_path)
    assert out["pass"] is True, out
    assert out["selected_branch"] == "EXCEPTION_BRANCH"
    assert out["condition_holds"] is True
    assert out["field_name"] == "exposure_amount"
    assert out["acceptance_receipt"]["producer_independent"] is True


def test_decimal_below_threshold_selects_ordinary(tmp_path: Path):
    _bundle(tmp_path, value="100.00")
    out = d.run({"task_id": "x2", "goal": _goal()}, repo_root=tmp_path)
    assert out["pass"] is True, out
    assert out["selected_branch"] == "ORDINARY_BRANCH"
    assert out["condition_holds"] is False
    result = json.loads(
        (tmp_path / "canonical/tmp/crossdoc_result.json").read_text()
    )
    assert result["selected_text"] == "Apply Rule A"


def test_boolean_fact_source_is_supported(tmp_path: Path):
    _bundle(
        tmp_path,
        value="true",
        policy=POLICY_BOOL,
        fact_field="breach",
        fact_type="BOOL",
    )
    out = d.run({"task_id": "x3", "goal": _goal()}, repo_root=tmp_path)
    assert out["pass"] is True, out
    assert out["operator"] == "BOOL_EQ"
    assert out["selected_branch"] == "EXCEPTION_BRANCH"


def test_fact_role_must_be_declared_in_bounded_source_set(tmp_path: Path):
    case, cp, _, _ = _bundle(tmp_path)
    case["task_record"]["shared_files"] = ["canonical/tmp/policy.txt"]
    cp.write_text(json.dumps(case), encoding="utf-8")
    out = d.preflight({"task_id": "x4", "goal": _goal()}, repo_root=tmp_path)
    assert out["matched"] is True
    assert out["status"] == "FAIL_CLOSED"
    assert "FACT_SOURCE_ROLE_NOT_IN_DECLARED_SOURCE_SET" in out["reason"]


def test_policy_and_fact_roles_must_be_distinct(tmp_path: Path):
    case, cp, _, _ = _bundle(tmp_path)
    case["task_record"]["source_roles"]["fact_source_path"] = (
        case["task_record"]["source_roles"]["policy_source_path"]
    )
    cp.write_text(json.dumps(case), encoding="utf-8")
    out = d.preflight({"task_id": "x5", "goal": _goal()}, repo_root=tmp_path)
    assert out["matched"] is True
    assert out["status"] == "FAIL_CLOSED"
    assert "POLICY_AND_FACT_SOURCE_MUST_BE_DISTINCT" in out["reason"]


def test_duplicate_json_fact_key_fails_closed(tmp_path: Path):
    duplicate = (
        '{"schema_id":"FINANCE_TYPED_CONTEXT_V1","fields":{'
        '"exposure_amount":{"type":"DECIMAL_STRING","value":"130.00"},'
        '"exposure_amount":{"type":"DECIMAL_STRING","value":"0.00"}}}'
    )
    _bundle(tmp_path, raw_fact=duplicate)
    out = d.preflight({"task_id": "x6", "goal": _goal()}, repo_root=tmp_path)
    assert out["matched"] is True
    assert out["status"] == "FAIL_CLOSED"


def test_duplicate_declared_source_fails_closed(tmp_path: Path):
    case, cp, _, _ = _bundle(tmp_path)
    case["task_record"]["shared_files"].append("canonical/tmp/facts.json")
    cp.write_text(json.dumps(case), encoding="utf-8")
    out = d.preflight({"task_id": "x7", "goal": _goal()}, repo_root=tmp_path)
    assert out["matched"] is True
    assert out["status"] == "FAIL_CLOSED"
    assert "DECLARED_SOURCE_DUPLICATE" in out["reason"]


def test_preflight_is_side_effect_free(tmp_path: Path):
    _bundle(tmp_path)
    out = d.preflight({"task_id": "x8", "goal": _goal()}, repo_root=tmp_path)
    assert out["matched"] is True
    assert out["status"] == "DIRECT_ADEQUACY_ROUTE_MATCHED"
    assert out["preflight_execution_authority"] is False
    assert not (tmp_path / "canonical/tmp/crossdoc_result.json").exists()


def test_independent_verifier_rejects_tampered_selected_branch(tmp_path: Path):
    case, _, _, _ = _bundle(tmp_path)
    from canonical.runtime import finance_task_role_raw_fact_unless_branch_v1 as producer

    result = producer.compute(case, repo_root=tmp_path)
    result["selected_branch"] = "ORDINARY_BRANCH"
    checked = verifier.verify(case, result, repo_root=tmp_path)
    assert checked["verified"] is False
    assert "MISMATCH:selected_branch" in checked["errors"]


def test_verifier_failure_rolls_back_existing_output(monkeypatch, tmp_path: Path):
    _bundle(tmp_path)
    outp = tmp_path / "canonical/tmp/crossdoc_result.json"
    outp.write_text('{"old":true}\n', encoding="utf-8")
    original = outp.read_bytes()

    original_verify = d.verifier.verify
    calls = {"n": 0}

    def fail_after_preflight(case, result, *, repo_root):
        calls["n"] += 1
        if calls["n"] == 1:
            return original_verify(case, result, repo_root=repo_root)
        return {
            "verified": False,
            "producer_independent": True,
            "model_dependency_count": 0,
            "errors": ["forced"],
        }

    monkeypatch.setattr(d.verifier, "verify", fail_after_preflight)
    out = d.run({"task_id": "x9", "goal": _goal()}, repo_root=tmp_path)
    assert out["pass"] is False
    assert out["rollback_complete"] is True
    assert outp.read_bytes() == original


def test_source_mutation_by_producer_is_detected(monkeypatch, tmp_path: Path):
    _bundle(tmp_path)
    fact_path = tmp_path / "canonical/tmp/facts.json"
    original_compute = d.producer.compute
    calls = {"n": 0}

    def mutating_compute(case, *, repo_root):
        calls["n"] += 1
        out = original_compute(case, repo_root=repo_root)
        if calls["n"] == 2:
            fact_path.write_text(
                '{"schema_id":"FINANCE_TYPED_CONTEXT_V1","fields":'
                '{"exposure_amount":{"type":"DECIMAL_STRING","value":"999.00"}}}',
                encoding="utf-8",
            )
        return out

    monkeypatch.setattr(d.producer, "compute", mutating_compute)
    out = d.run({"task_id": "x10", "goal": _goal()}, repo_root=tmp_path)
    assert out["pass"] is False
    assert "SOURCE_MUTATED_BY_PRODUCER" in out["reason"]


def test_nonmatching_goal_claims_no_scope(tmp_path: Path):
    out = d.preflight(
        {"task_id": "x11", "goal": "Analyze these finance sources."},
        repo_root=tmp_path,
    )
    assert out["matched"] is False
    assert out["pass"] is False


def test_fixed_point_front_door_closes_cross_document_route_at_step_zero(tmp_path: Path):
    from canonical.runtime import general_adequate_decision_fixed_point_v2 as fixed

    _bundle(tmp_path)
    out = fixed.run(
        {"task_id": "x12", "goal": _goal()},
        repo_root=tmp_path,
    )
    assert out["pass"] is True, out
    assert out["route_id"] == d.ROUTE_ID
    assert out["r2_fixed_point_status"] == "PASS__R2_DIRECT_END_TO_END_ADEQUACY_CLOSED"
    assert out["r2_fixed_point_steps"] == 0


def test_v4_router_falls_back_exactly_to_v3_for_nonmatching_goal(tmp_path: Path):
    from canonical.runtime import r2_direct_end_to_end_adequacy_v3 as v3
    from canonical.runtime import r2_direct_end_to_end_adequacy_v4 as v4

    request = {"task_id": "fallback", "goal": 'Reply with exactly "HELLO".'}
    assert v4.preflight(request, repo_root=tmp_path) == v3.preflight(
        request, repo_root=tmp_path
    )
