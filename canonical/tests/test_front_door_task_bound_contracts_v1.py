"""Real public-entry repair execution, request binding, and artifact tampering."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import pathlib
import tempfile
import time
import uuid

import pytest

from canonical.runtime import live_brain_route_admission_v1 as door
from canonical.runtime import live_integrated_brain_v1 as live
from canonical.runtime import swe_typed_plan_v1 as typed

ROOT = pathlib.Path(__file__).resolve().parents[2]


@pytest.fixture
def task():
    parent = ROOT / "canonical/astra_runtime/tmp"
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="front-contract-", dir=parent) as raw:
        path = pathlib.Path(raw)
        (path / "m.py").write_text(
            'def f(x):\n    """post: _ == (x <= 3)"""\n    return x < 3\n')
        (path / "trace_fail.py").write_text("from m import f\nassert f(3)\n")
        (path / "trace_pass.py").write_text("from m import f\nassert f(2)\n")
        (path / "test_all.py").write_text(
            "from m import f\nassert f(3)\nassert f(2)\nassert not f(4)\n")
        rel = str(path.relative_to(ROOT))
        goal = (
            f"Write a measured acceptance repair report to {rel}/report.json "
            f"for the source root {rel} using the test path {rel}/test_all.py "
            "where `tests_pass` must be true and `python_parse_ok` must be true"
        )
        request = {"task_id": "FRONT_CONTRACT_" + uuid.uuid4().hex, "goal": goal,
                   "contract_checks": [{"source_path": "m.py", "max_examples": 20}]}
        yield path, request


def test_normal_public_request_executes_real_repair_and_requested_checks(task):
    path, request = task
    original = {p.name: p.read_bytes() for p in path.glob("*.py")}
    started = time.perf_counter_ns()
    result = door.solve(request)
    wall = time.perf_counter_ns() - started
    assert 0.9 * wall <= result["elapsed_ns"] <= wall
    assert result["pass"] is True, result
    assert result["compiled_capability_id"] == "python.software.repair.measured_acceptance.v1"
    assert result["structured_contract_acceptance_complete"] is True
    assert result["typed_swe_selection"]["primary_capability"] == "python.repository.acceptance.measure.v1"
    assert result["typed_swe_selection"]["basis"] == "DECISIVE_TYPED_SELECTION_BEFORE_EXECUTION"
    report = json.loads((path / "report.json").read_text())
    assert result["contract_check_spec_sha256"] == report["contract_check_spec_sha256"]
    checks = report["contract_checks"]
    assert checks[0]["concrete"]["checked"] == 13
    assert checks[0]["hypothesis"]["checked"] > 0
    assert checks[0]["hypothesis"]["input_bounds"]["max_examples"] == 20
    assert original == {p.name: p.read_bytes() for p in path.glob("*.py")}
    # Independently apply the emitted patch and check 401 expected behaviors.
    patch = report["patches"][0]
    fixed = door._acceptance._apply_unified_diff(original["m.py"].decode(), patch["unified_diff"])
    namespace = {}
    exec(compile(fixed, "<front-door-candidate>", "exec"), namespace)
    assert all(namespace["f"](x) == (x <= 3) for x in range(-200, 201))
    assert checks[0]["source_sha256"] == hashlib.sha256(fixed.encode()).hexdigest()


def test_failed_property_cannot_be_dropped_by_router_or_retry(task):
    path, request = task
    source = (path / "m.py").read_text().replace("_ == (x <= 3)", "_ is False")
    (path / "m.py").write_text(source)
    result = door.solve(request)
    assert result["pass"] is False
    assert result["executed"] is True
    assert result["structured_contract_acceptance_complete"] is False
    assert "typed_swe_retry" not in result
    report = json.loads((path / "report.json").read_text())
    assert report["measured_fields"]["tests_pass"] is True
    assert report["contract_checks_pass"] is False
    assert report["pass"] is False
    assert report["patches"] == []
    assert (path / "m.py").read_text() == source


@pytest.mark.parametrize("checks", [None, [], {}, [None], [{}],
                                    [{"source_path": "../outside.py"}],
                                    [{"source_path": "m.py", "max_examples": 0}],
                                    [{"source_path": "m.py", "extra": "not allowed"}]])
def test_invalid_public_contracts_fail_before_any_tool_execution(checks, task):
    path, request = task
    request["contract_checks"] = checks
    before = {p.name: p.read_bytes() for p in path.iterdir()}
    result = door.solve(request)
    assert result["pass"] is False
    assert result["executed"] is False
    assert result["failure_class"] == "CONTRACT_CHECKS_UNBOUND"
    assert before == {p.name: p.read_bytes() for p in path.iterdir()}


def test_unrelated_write_cannot_silently_discard_contracts(task):
    path, request = task
    target = str((path / "unrelated.txt").relative_to(ROOT))
    request["goal"] = f"Write the text 'hello' to the file {target}"
    result = door.solve(request)
    assert result["pass"] is False
    assert result["executed"] is False
    assert not (path / "unrelated.txt").exists()
    assert not (path / "report.json").exists()


def test_existing_report_is_preserved_before_execution(task):
    path, request = task
    report = path / "report.json"
    report.write_bytes(b"pre-existing user work")
    result = door.solve(request)
    assert result["pass"] is False
    assert result.get("executed", False) is False
    assert report.read_bytes() == b"pre-existing user work"


def test_binding_does_not_mutate_registry_or_request(task):
    _, request = task
    context = live.compile_against_live_registry(request["goal"], ROOT)
    plan = typed.build_plan(request["goal"], ROOT, compiled_context=context)
    assert plan is not None
    before_registry = deepcopy(plan[1])
    before_request = deepcopy(request)
    updated, spec = door._bind_requested_contract_checks(request["contract_checks"], plan[2], plan[1])
    assert plan[1] == before_registry
    assert request == before_request
    cid = "python.software.repair.measured_acceptance.v1"
    assert updated[cid]["action_template"]["args"]["contract_checks"] == spec["checks"]
    assert "contract_checks" not in plan[1][cid]["action_template"]["args"]
    # Corrected plan metadata must not claim the measurement-only tool's effects.
    assert plan[2]["target_effects"] == plan[0][cid]["provides"]
    assert plan[2]["capabilities"] == [cid]


@pytest.mark.parametrize("mutation", ["digest", "omitted", "different_bounds",
                                        "missing_source_hashes", "zero_checks", "boolean_checks"])
def test_reinspection_rejects_tampered_real_report(mutation, task):
    path, request = task
    result = door.solve(request)
    assert result["pass"] is True
    report_path = path / "report.json"
    report = json.loads(report_path.read_text())
    spec = {"checks": report["requested_contract_checks"],
            "sha256": result["contract_check_spec_sha256"],
            "output_path": str(report_path.relative_to(ROOT))}
    if mutation == "digest":
        report["contract_check_spec_sha256"] = "0" * 64
    elif mutation == "omitted":
        report["contract_checks"] = []
    elif mutation == "different_bounds":
        report["contract_checks"][0]["hypothesis"]["input_bounds"]["min_value"] = 999
    elif mutation == "missing_source_hashes":
        observed = report["contract_checks"][0]
        for row in (observed, observed["concrete"], observed["hypothesis"]):
            row.pop("source_sha256", None)
    else:
        report["contract_checks"][0]["hypothesis"]["checked"] = (0 if mutation == "zero_checks" else True)
    raw = json.dumps(report).encode()
    report_path.write_bytes(raw)
    # Even if artifact integrity is recomputed, the task requirement must hold.
    result["execution"][0]["result"]["output_sha256"] = hashlib.sha256(raw).hexdigest()
    closed = door._close_requested_contract_checks(result, spec)
    assert closed["pass"] is False
    assert closed["structured_contract_acceptance_complete"] is False
    assert closed["semantic_acceptance_complete"] is False
    assert closed["failure_class"] == "REQUESTED_CONTRACT_CHECKS_NOT_VERIFIED"


def test_unknown_requirement_in_goal_is_not_removed_by_structured_checks(task):
    path, request = task
    request["goal"] = request["goal"].replace("using the test path", "preserve every secret file using the test path")
    result = door.solve(request)
    assert result["pass"] is False
    assert result["structured_contract_acceptance_complete"] is False
    # This sentence selects the semantic controller, which does not implement
    # the requested optional property configuration. Refuse BEFORE running it,
    # rather than silently discard the structured part of the user's request.
    assert result["executed"] is False
    assert result["failure_class"] == "CONTRACT_CHECKS_UNBOUND"
    assert not (path / "report.json").exists()


@pytest.mark.parametrize("payload", [None, {}, {"task_id": "missing-goal"}, {"goal": "fix the bug"}])
def test_invalid_requests_do_not_enter_execution(payload):
    result = door.solve(payload)
    assert result["pass"] is False
    assert result["executed"] is False
    assert result["failure_class"] == "REQUEST_INVALID"
