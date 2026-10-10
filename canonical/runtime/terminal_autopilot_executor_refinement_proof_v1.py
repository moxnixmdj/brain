"""Bounded semantic refinement proof for terminal_autopilot_executor_v1.

The checker proves the executor's authority-critical control layer against the
versioned abstract spec. same_identity_supervisor.run_once remains an explicit
content-bound downstream dependency whose effect semantics are not re-proved.
"""
from __future__ import annotations

import ast
from copy import deepcopy
from hashlib import sha1, sha256
import json
from pathlib import Path
import tempfile
from typing import Any, Mapping

from canonical.runtime import terminal_autopilot_executor_v1 as executor

SCHEMA = "PROJECT_BRAIN_TERMINAL_AUTOPILOT_EXECUTOR_REFINEMENT_RECEIPT_V1"
ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = Path(
    "canonical/governance/TERMINAL_AUTOPILOT_EXECUTOR_ABSTRACT_SPEC_20261010_V1.json"
)
RUNTIME_PATH = Path("canonical/runtime/terminal_autopilot_executor_v1.py")
RUNNER_PATH = Path("canonical/runtime/same_identity_supervisor.py")


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "pass": False,
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "refinement_verified": False,
        "semantic_truth_authority": False,
        "execution_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON_OBJECT_REQUIRED:" + str(path))
    return value


def _task(
    task_id: str,
    agent_id: str,
    action_id: str,
    obligation: str,
    *,
    phase: str = "EXECUTE",
    execution_class: str = "REVERSIBLE_ZERO_REALITY",
    irreversible: bool = False,
    promotion_authority: Mapping[str, Any] | None = None,
    spend: float = 0.0,
) -> dict[str, Any]:
    raw = {
        "schema": executor.TASK_SCHEMA,
        "task_id": task_id,
        "agent_id": agent_id,
        "incremental_spend_usd": spend,
        "mission_path": "canonical/missions/fake.json",
        "mission_sha256": "0" * 64,
        "terminal_autopilot": {
            "enabled": True,
            "phase": phase,
            "execution_class": execution_class,
            "action_id": action_id,
            "obligation_ids": [obligation],
            "irreversible_benchmark": irreversible,
        },
    }
    if promotion_authority is not None:
        raw["terminal_autopilot"]["promotion_authority"] = dict(promotion_authority)
    return raw


def _repo() -> tuple[tempfile.TemporaryDirectory[str], Path]:
    td = tempfile.TemporaryDirectory()
    root = Path(td.name)
    (root / executor.TASKS_DIR).mkdir(parents=True)
    (root / executor.STATE_DIR).mkdir(parents=True)
    (root / executor.EVIDENCE_DIR).mkdir(parents=True)
    return td, root


def _expect_gate_error(root: Path, task: dict[str, Any], expected: str) -> bool:
    try:
        executor._task_gate(root, task)
    except executor.AutopilotExecutionError as exc:
        return str(exc) == expected
    return False


def _static_proof(source: str) -> dict[str, Any]:
    tree = ast.parse(source)
    assignments: dict[str, Any] = {}
    terminal_credit_true = 0
    runner_direct_calls = 0
    runner_submit_calls = 0
    required_error_literals = {
        "TASK_SCHEMA_INVALID",
        "NONZERO_INCREMENTAL_SPEND",
        "AUTOPILOT_NOT_EXPLICITLY_ENABLED",
        "AUTOPILOT_PHASE_INVALID",
        "AUTOPILOT_EXECUTION_CLASS_NOT_AUTHORIZED",
        "IRREVERSIBLE_BENCHMARK_AUTOEXECUTION_FORBIDDEN",
        "AUTOPILOT_ACTION_ID_REQUIRED",
        "AUTOPILOT_OBLIGATION_IDS_INVALID",
        "PROMOTION_AUTHORITY_REQUIRED",
        "PROMOTION_AUTHORITY_BINDING_INVALID",
        "PROMOTION_AUTHORITY_BYTE_MISMATCH",
    }
    seen_strings: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(
            node.targets[0], ast.Name
        ):
            name = node.targets[0].id
            if name in {"SAFE_CLASSES", "PHASE_RANK"}:
                try:
                    assignments[name] = ast.literal_eval(node.value)
                except Exception:
                    assignments[name] = None

        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            seen_strings.add(node.value)

        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if (
                    isinstance(key, ast.Constant)
                    and key.value == "terminal_credit"
                    and isinstance(value, ast.Constant)
                    and value.value is True
                ):
                    terminal_credit_true += 1

        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "runner":
                runner_direct_calls += 1
            if (
                isinstance(node.func, ast.Attribute)
                and node.func.attr == "submit"
                and node.args
                and isinstance(node.args[0], ast.Name)
                and node.args[0].id == "runner"
            ):
                runner_submit_calls += 1

    expected_safe = {
        "EXECUTE": {"REVERSIBLE_ZERO_REALITY"},
        "VERIFY": {"INDEPENDENT_ZERO_SPEND_VERIFY"},
        "PROMOTE": {"CONTENT_BOUND_PROMOTION"},
    }
    expected_rank = {"EXECUTE": 1, "VERIFY": 2, "PROMOTE": 3}
    return {
        "pass": (
            assignments.get("SAFE_CLASSES") == expected_safe
            and assignments.get("PHASE_RANK") == expected_rank
            and terminal_credit_true == 0
            and runner_direct_calls == 0
            and runner_submit_calls == 1
            and required_error_literals.issubset(seen_strings)
        ),
        "safe_classes_exact": assignments.get("SAFE_CLASSES") == expected_safe,
        "phase_rank_exact": assignments.get("PHASE_RANK") == expected_rank,
        "terminal_credit_true_literal_count": terminal_credit_true,
        "runner_direct_call_count": runner_direct_calls,
        "runner_submit_call_count": runner_submit_calls,
        "missing_gate_error_literals": sorted(required_error_literals - seen_strings),
    }


def _dynamic_proof() -> dict[str, Any]:
    checks: dict[str, bool] = {}

    td, root = _repo()
    try:
        base = _task("e", "A", "execute::O", "O")
        gate = executor._task_gate(root, deepcopy(base))
        checks["valid_execute_admitted"] = (
            gate["phase"] == "EXECUTE"
            and gate["execution_class"] == "REVERSIBLE_ZERO_REALITY"
            and gate["obligation_ids"] == ["O"]
        )

        bad = deepcopy(base)
        bad["incremental_spend_usd"] = 1
        checks["nonzero_spend_rejected"] = _expect_gate_error(
            root, bad, "NONZERO_INCREMENTAL_SPEND"
        )

        bad = deepcopy(base)
        bad["terminal_autopilot"]["irreversible_benchmark"] = True
        checks["irreversible_benchmark_rejected"] = _expect_gate_error(
            root, bad, "IRREVERSIBLE_BENCHMARK_AUTOEXECUTION_FORBIDDEN"
        )

        bad = deepcopy(base)
        bad["terminal_autopilot"]["execution_class"] = "CONTENT_BOUND_PROMOTION"
        checks["phase_class_mismatch_rejected"] = _expect_gate_error(
            root, bad, "AUTOPILOT_EXECUTION_CLASS_NOT_AUTHORIZED"
        )

        promote = _task(
            "p",
            "P",
            "promote::O",
            "O",
            phase="PROMOTE",
            execution_class="CONTENT_BOUND_PROMOTION",
        )
        checks["promotion_without_authority_rejected"] = _expect_gate_error(
            root, promote, "PROMOTION_AUTHORITY_REQUIRED"
        )

        auth = root / "canonical/governance/PROMOTE_O.json"
        auth.parent.mkdir(parents=True)
        auth.write_text('{"authorized":true}\n', encoding="utf-8")
        binding = {
            "path": "canonical/governance/PROMOTE_O.json",
            "git_blob_sha": executor._git_blob_sha(auth.read_bytes()),
        }
        promote = _task(
            "p",
            "P",
            "promote::O",
            "O",
            phase="PROMOTE",
            execution_class="CONTENT_BOUND_PROMOTION",
            promotion_authority=binding,
        )
        checks["promotion_exact_authority_admitted"] = (
            executor._task_gate(root, promote)["phase"] == "PROMOTE"
        )
        auth.write_text('{"authorized":false}\n', encoding="utf-8")
        checks["promotion_authority_drift_rejected"] = _expect_gate_error(
            root, promote, "PROMOTION_AUTHORITY_BYTE_MISMATCH"
        )
    finally:
        td.cleanup()

    td, root = _repo()
    try:
        tasks = root / executor.TASKS_DIR
        states = root / executor.STATE_DIR
        a = _task("a", "WORKER-A", "execute::A", "A")
        b = _task("b", "WORKER-A", "execute::B", "B")
        tasks.joinpath("a.json").write_text(json.dumps(a), encoding="utf-8")
        tasks.joinpath("b.json").write_text(json.dumps(b), encoding="utf-8")
        plan = {
            "pass": True,
            "dispatch": [
                {"action_id": "execute::A", "obligation_ids": ["A"]},
                {"action_id": "execute::B", "obligation_ids": ["B"]},
            ],
            "verify": [],
            "promote": [],
        }
        selected = executor.select_runnable_tasks(root, plan)
        checks["one_task_per_worker_identity"] = len(selected) == 1

        mismatch_plan = {
            "pass": True,
            "dispatch": [{"action_id": "execute::A", "obligation_ids": ["OTHER"]}],
            "verify": [],
            "promote": [],
        }
        checks["plan_obligation_mismatch_not_selected"] = (
            executor.select_runnable_tasks(root, mismatch_plan) == []
        )

        states.joinpath("a.json").write_text(
            json.dumps({"status": "RUNNING"}), encoding="utf-8"
        )
        checks["running_task_not_redispatched"] = all(
            x["meta"]["task_id"] != "a"
            for x in executor.select_runnable_tasks(root, plan)
        )
    finally:
        td.cleanup()

    td, root = _repo()
    try:
        tasks = root / executor.TASKS_DIR
        states = root / executor.STATE_DIR

        route = _task(
            "route",
            "R",
            "route::SCOPE_COMPLETE_UNIVERSAL_COVER",
            "O1",
        )
        ordinary = _task("exec", "E", "execute::O2", "O2")
        verify = _task(
            "verify",
            "V",
            "verify::O3",
            "O3",
            phase="VERIFY",
            execution_class="INDEPENDENT_ZERO_SPEND_VERIFY",
        )

        auth = root / "canonical/governance/PROMOTE_O4.json"
        auth.parent.mkdir(parents=True)
        auth.write_text('{"authorized":true}\n', encoding="utf-8")
        promote = _task(
            "promote",
            "P",
            "promote::O4",
            "O4",
            phase="PROMOTE",
            execution_class="CONTENT_BOUND_PROMOTION",
            promotion_authority={
                "path": "canonical/governance/PROMOTE_O4.json",
                "git_blob_sha": executor._git_blob_sha(auth.read_bytes()),
            },
        )

        for name, raw in (
            ("route", route),
            ("exec", ordinary),
            ("verify", verify),
            ("promote", promote),
        ):
            tasks.joinpath(name + ".json").write_text(
                json.dumps(raw), encoding="utf-8"
            )
            states.joinpath(name + ".json").write_text(
                json.dumps({"status": "COMPLETE"}), encoding="utf-8"
            )

        manifest = {
            "obligations": [
                {"id": "O1", "status": "OPEN"},
                {"id": "O2", "status": "OPEN"},
                {"id": "O3", "status": "RESULT_PRESENT"},
                {"id": "O4", "status": "VERIFIED"},
            ]
        }
        out = executor.overlay_worker_progress(manifest, root)
        status = {row["id"]: row["status"] for row in out["obligations"]}
        checks["route_complete_does_not_fabricate_result"] = status["O1"] == "OPEN"
        checks["ordinary_execute_projects_result_present_only"] = (
            status["O2"] == "RESULT_PRESENT"
        )
        checks["verify_projects_verified_only"] = status["O3"] == "VERIFIED"
        checks["promote_complete_does_not_self_mint_promoted"] = (
            status["O4"] == "VERIFIED"
        )
    finally:
        td.cleanup()

    td, root = _repo()
    try:
        tasks = root / executor.TASKS_DIR
        a = _task("a", "WORKER-A", "execute::A", "A")
        tasks.joinpath("a.json").write_text(json.dumps(a), encoding="utf-8")
        plan = {
            "pass": True,
            "dispatch": [{"action_id": "execute::A", "obligation_ids": ["A"]}],
            "verify": [],
            "promote": [],
        }
        calls: list[dict[str, Any]] = []

        def fake_runner(**kwargs: Any) -> tuple[int, dict[str, Any]]:
            calls.append(dict(kwargs))
            return 0, {"status": "PASS"}

        wave = executor.execute_wave(
            root, plan, max_concurrency=1, runner=fake_runner
        )
        checks["runner_called_once_for_selected_task"] = (
            len(calls) == 1
            and Path(calls[0]["task_path"]).name == "a.json"
            and wave["selected"] == ["a"]
        )
        checks["wave_never_grants_terminal_credit"] = (
            wave.get("terminal_credit") is False
        )
    finally:
        td.cleanup()

    return {
        "pass": all(checks.values()),
        "checks": checks,
        "check_count": len(checks),
        "failed_checks": sorted(k for k, v in checks.items() if not v),
    }


def prove(repo_root: str | Path = ROOT) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    spec_path = root / SPEC_PATH
    runtime_path = root / RUNTIME_PATH
    runner_path = root / RUNNER_PATH

    try:
        spec = _load_json(spec_path)
    except Exception as exc:
        return _fail("ABSTRACT_SPEC_LOAD_FAILED:" + type(exc).__name__ + ":" + str(exc))

    if spec.get("schema") != "PROJECT_BRAIN_TERMINAL_AUTOPILOT_EXECUTOR_ABSTRACT_SPEC_V1":
        return _fail("ABSTRACT_SPEC_SCHEMA_INVALID")
    if spec.get("terminal_credit_delta") != 0:
        return _fail("ABSTRACT_SPEC_NONZERO_TERMINAL_CREDIT")

    expected_runtime = spec.get("bound_runtime")
    expected_runner = spec.get("runner_dependency")
    if not isinstance(expected_runtime, Mapping) or not isinstance(expected_runner, Mapping):
        return _fail("ABSTRACT_BINDINGS_INVALID")
    if (
        expected_runtime.get("path") != str(RUNTIME_PATH)
        or expected_runtime.get("git_blob_sha") != _git_blob_sha(runtime_path)
    ):
        return _fail("EXECUTOR_BLOB_BINDING_MISMATCH")
    if (
        expected_runner.get("path") != str(RUNNER_PATH)
        or expected_runner.get("git_blob_sha") != _git_blob_sha(runner_path)
    ):
        return _fail("RUNNER_BLOB_BINDING_MISMATCH")
    if expected_runner.get("semantics_reproved") is not False:
        return _fail("RUNNER_BOUNDARY_MUST_REMAIN_EXPLICIT")

    static = _static_proof(runtime_path.read_text(encoding="utf-8"))
    if static.get("pass") is not True:
        return _fail("STATIC_AUTHORITY_SPACE_PROOF_FAILED", static_proof=static)

    dynamic = _dynamic_proof()
    if dynamic.get("pass") is not True:
        return _fail("DYNAMIC_AUTHORITY_REFINEMENT_FAILED", dynamic_proof=dynamic)

    invariants = spec.get("invariants")
    if not isinstance(invariants, list) or len(invariants) < 10:
        return _fail("ABSTRACT_INVARIANT_SET_INCOMPLETE")

    receipt_body = {
        "pass": True,
        "schema": SCHEMA,
        "status": "PASS__BOUNDED_EXECUTOR_AUTHORITY_REFINEMENT_VERIFIED",
        "subject_id": str(spec.get("subject_id") or ""),
        "assurance_level": "FINITE_ABSTRACTION_EXECUTOR_AUTHORITY_REFINEMENT",
        "refinement_verified": True,
        "abstract_spec_git_blob_sha": _git_blob_sha(spec_path),
        "concrete_route_git_blob_sha": _git_blob_sha(runtime_path),
        "runner_dependency_git_blob_sha": _git_blob_sha(runner_path),
        "runner_boundary_explicit": True,
        "runner_semantics_reproved": False,
        "static_proof": static,
        "dynamic_proof": dynamic,
        "irreversible_benchmark_autoexecution_excluded": True,
        "promotion_requires_exact_content_bound_authority": True,
        "route_completion_cannot_fabricate_result_present": True,
        "promotion_completion_cannot_self_mint_promoted": True,
        "terminal_credit_nonamplification": True,
        "semantic_truth_authority": False,
        "execution_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    return {
        **receipt_body,
        "receipt_sha256": sha256(_canon(receipt_body)).hexdigest(),
    }


if __name__ == "__main__":
    print(json.dumps(prove(ROOT), indent=2, sort_keys=True))
