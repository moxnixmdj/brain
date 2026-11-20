"""Hard fail-closed tests for the external verified task ledger.

The receipt-producing tests run real guest subprocesses through the pinned state-op
compiler and the admitted sensor bridge; no receipt is hand-written as PASS.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile
from typing import Any, Mapping

import pytest

from canonical.runtime import osworld_verified_task_ledger_v1 as L
from canonical.runtime.osworld_sensor_request_bridge_v1 import AdmittedSensorGuestOps
from canonical.runtime.osworld_v21_host_guest_ops_v1 import OSWorldHostGuestOps


class Controller:
    def __init__(self, root: pathlib.Path) -> None:
        self.root = root

    def execute_python_command(self, program: str) -> dict[str, Any]:
        done = subprocess.run(
            [sys.executable, "-c", program], cwd=str(self.root),
            capture_output=True, text=True, timeout=120,
        )
        return {
            "status": "success" if done.returncode == 0 else "error",
            "output": done.stdout,
            "error": done.stderr or None,
        }


class Environment:
    def __init__(self, root: pathlib.Path) -> None:
        self.controller = Controller(root)


def _state(instruction: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {"instruction": instruction, "history": rows, "screenshot_sha256": "a" * 64}


def _done(_: Mapping[str, Any]) -> dict[str, Any]:
    return {"response": "finish", "actions": [{"type": "DONE"}]}


def _wait(_: Mapping[str, Any]) -> dict[str, Any]:
    return {"response": "working", "actions": [{"type": "WAIT"}]}


def _row(ops: list[dict[str, Any]], result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "screenshot_sha256": "a" * 64,
        "action_fingerprint": "x",
        "actions": ["WAIT"],
        "response": "state ops",
        "submitted_operations": ops,
        "guest_result": dict(result),
    }


def test_explicit_directory_receipt_from_real_guest_allows_done() -> None:
    with tempfile.TemporaryDirectory(prefix="brain-ledger-dir-") as tmp:
        root = pathlib.Path(tmp)
        target = root / "reports"
        instruction = f"Create a directory {target}"
        requirements, errors = L.compile_requirements(instruction)
        assert errors == []
        assert requirements == [{
            "kind": "DIRECTORY_SENSOR", "path": str(target),
            "op": "ASSERT_SENSOR_REQUEST",
        }]

        ops = [
            {"type": "MKDIR", "path": str(target)},
            {"type": "ASSERT_SENSOR_REQUEST", "path": str(target)},
        ]
        bridge = AdmittedSensorGuestOps()
        bridge.bind_environment(Environment(root))
        result = bridge.run({"ops": ops})
        assert result["ok"] is True
        assert "SENSOR_REQUEST:PASS:" in result["output"]
        assert result["admission"]["source"] == "fresh_measurement"

        out = L.decide(_state(instruction, [_row(ops, result)]), _done)
        assert out["actions"] == [{"type": "DONE"}]
        assert out["_policy_receipt"]["verified"] is True


def test_file_text_receipt_from_real_guest_allows_done() -> None:
    with tempfile.TemporaryDirectory(prefix="brain-ledger-file-") as tmp:
        root = pathlib.Path(tmp)
        target = root / "notes.txt"
        instruction = f'Write "Q4" into {target}'
        requirements, errors = L.compile_requirements(instruction)
        assert errors == []
        assert requirements[0]["kind"] == "TEXT_CONTAINS"
        assert requirements[0]["text"] == "Q4"

        ops = [
            {"type": "WRITE_TEXT", "path": str(target), "text": "Q4 report"},
            {"type": "ASSERT_TEXT_CONTAINS", "path": str(target), "text": "Q4"},
        ]
        guest = OSWorldHostGuestOps()
        guest.bind_environment(Environment(root))
        result = guest.run({"ops": ops})
        assert "ASSERT_TEXT_CONTAINS:PASS:" + str(target) in result["output"]

        out = L.decide(_state(instruction, [_row(ops, result)]), _done)
        assert out["actions"] == [{"type": "DONE"}]

        # The same verified ledger lets a stalled base policy finish honestly.
        out_wait = L.decide(_state(instruction, [_row(ops, result)]), _wait)
        assert out_wait["actions"] == [{"type": "DONE"}]


def test_done_is_withheld_until_assertion_receipt_exists() -> None:
    instruction = "/tmp/brain-ledger-unseen-target"
    out = L.decide(_state(instruction, []), _done)
    assert out["actions"] == [{
        "type": "STATE_OPS",
        "ops": [{"type": "ASSERT_PATH_EXISTS", "path": instruction}],
    }]
    assert out["_policy_receipt"]["withheld_reason"] == "FRESH_PASS_REQUIRED"


def test_later_mutation_invalidates_older_pass() -> None:
    with tempfile.TemporaryDirectory(prefix="brain-ledger-stale-") as tmp:
        root = pathlib.Path(tmp)
        target = root / "notes.txt"
        instruction = f'Write "Q4" into {target}'
        ops = [
            {"type": "WRITE_TEXT", "path": str(target), "text": "Q4 report"},
            {"type": "ASSERT_TEXT_CONTAINS", "path": str(target), "text": "Q4"},
        ]
        guest = OSWorldHostGuestOps()
        guest.bind_environment(Environment(root))
        result = guest.run({"ops": ops})
        mutation = {"type": "WRITE_TEXT", "path": str(target), "text": "changed"}
        mutated = guest.run({"ops": [mutation]})
        rows = [_row(ops, result), _row([mutation], mutated)]
        out = L.decide(_state(instruction, rows), _done)
        assert out["actions"][0]["type"] == "STATE_OPS"
        assert out["_policy_receipt"]["verified"] is False
        evidence = L.audit(_state(instruction, rows), L.compile_requirements(instruction)[0])
        assert evidence["evidence"][0]["last_mutation_row_index"] == 1
        assert evidence["evidence"][0]["pass_row_index"] == 0


def test_pass_for_a_different_path_is_not_accepted() -> None:
    instruction = "/tmp/brain-ledger-required-path"
    wrong = "/tmp/brain-ledger-wrong-path"
    ops = [{"type": "ASSERT_PATH_EXISTS", "path": wrong}]
    rows = [_row(ops, {
        "ok": True, "status": "ok",
        "output": "ASSERT_PATH_EXISTS:PASS:" + wrong,
    })]
    out = L.decide(_state(instruction, rows), _done)
    assert out["actions"][0]["type"] == "STATE_OPS"
    assert out["_policy_receipt"]["verified"] is False


def test_sensor_pass_without_fresh_admission_is_rejected() -> None:
    with tempfile.TemporaryDirectory(prefix="brain-ledger-forged-") as tmp:
        target = pathlib.Path(tmp) / "reports"
        instruction = f"Create a directory {target}"
        ops = [{"type": "ASSERT_SENSOR_REQUEST", "path": str(target)}]
        rows = [_row(ops, {
            "ok": True, "status": "ok",
            "output": "SENSOR_REQUEST:PASS:st_mode:16877",
        })]
        out = L.decide(_state(instruction, rows), _done)
        assert out["actions"][0]["type"] == "STATE_OPS"
        assert out["_policy_receipt"]["verified"] is False


def test_ambiguous_quotes_and_multiple_paths_fail_closed() -> None:
    instruction = 'Write "alpha" into /tmp/a and "beta" into /tmp/b'
    requirements, errors = L.compile_requirements(instruction)
    assert "AMBIGUOUS_QUOTED_TARGET" in errors
    out = L.decide(_state(instruction, []), _done)
    assert out["actions"] == [{"type": "WAIT"}]
    assert out["_policy_receipt"]["withheld_reason"] == "UNRESOLVED_REQUIREMENT"


def test_gui_instruction_cannot_borrow_guest_state_evidence() -> None:
    instruction = 'Click "Save" to close the dialog'
    out = L.decide(_state(instruction, []), _done)
    assert out["actions"] == [{"type": "WAIT"}]
    assert "NO_EXPLICIT_STATE_PATH" in out["_policy_receipt"]["errors"]


def test_fail_output_is_never_overridden() -> None:
    fail = {"response": "failed", "actions": [{"type": "FAIL"}]}
    out = L.decide(_state("/tmp/x", []), lambda _: fail)
    assert out == fail


def test_runtime_policy_composition_is_wired_and_model_free() -> None:
    from canonical.runtime import osworld_verified_policy_v1 as P

    state = {
        "instruction": "Click the Save button",
        "screenshot_sha256": "a" * 64,
        "a11y_tree": "<root/>",
        "history": [],
    }
    out = P.decide(state)
    assert isinstance(out, Mapping)
    assert out.get("actions")
    assert str(out["actions"][0].get("type") or "").upper() != "DONE"
    source = pathlib.Path(P.__file__).read_text(encoding="utf-8")
    assert "unified_policy_v17" in source
    assert "osworld_verified_task_ledger_v1" in source


def test_module_has_no_runtime_model_or_network_dependency() -> None:
    source = pathlib.Path(L.__file__).read_text(encoding="utf-8")
    for forbidden in ("openai", "anthropic", "requests", "urllib.request", "torch",
                      "transformers", "http.client"):
        assert forbidden not in source
