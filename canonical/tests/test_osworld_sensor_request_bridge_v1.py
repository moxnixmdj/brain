"""A computed sensor request is admitted into a real OSWorld-compatible guest program."""
from __future__ import annotations

import json
import pathlib
import sys
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import osworld_sensor_request_bridge_v1 as B  # noqa: E402
from canonical.runtime.osworld_v21_brain_agent_adapter_v1 import BrainOSWorldAgent  # noqa: E402


def test_fresh_store_is_admitted_and_guest_assertion_executes(tmp_path: pathlib.Path) -> None:
    target = tmp_path / "made_by_the_guest"
    target.mkdir()
    result = B.run_with_real_controller(
        {"ops": [{"type": "ASSERT_SENSOR_REQUEST", "path": str(target)}]}, tmp_path)
    assert result["ok"] is True
    assert "SENSOR_REQUEST:PASS:" in result["output"]
    assert result["admission"]["field"] == "st_mode"
    assert result["admission"]["source"] == "fresh_measurement"


def test_ordinary_state_ops_still_delegate_and_sensor_assertion_follows(tmp_path: pathlib.Path) -> None:
    text = tmp_path / "note.txt"
    directory = tmp_path / "directory"
    directory.mkdir()
    result = B.run_with_real_controller({"ops": [
        {"type": "WRITE_TEXT", "path": str(text), "text": "admitted\n"},
        {"type": "ASSERT_SENSOR_REQUEST", "path": str(directory)},
    ]}, tmp_path)
    assert text.read_text() == "admitted\n"
    assert "WRITE_TEXT:PASS:" in result["output"]
    assert "SENSOR_REQUEST:PASS:" in result["output"]


def test_stale_store_fails_closed(tmp_path: pathlib.Path) -> None:
    store = tmp_path / "stale.json"
    data = json.loads(B.DEFAULT_STORE.read_text(encoding="utf-8"))
    data["learned_relation"]["value"] = 1
    store.write_text(json.dumps(data), encoding="utf-8")
    target = tmp_path / "directory"
    target.mkdir()
    try:
        B.run_with_real_controller(
            {"ops": [{"type": "ASSERT_SENSOR_REQUEST", "path": str(target)}]},
            tmp_path, store=store)
    except B.AdmissionError as exc:
        assert "STORED_REQUEST_DISAGREES_WITH_FRESH_EXECUTION" in str(exc)
    else:
        raise AssertionError("stale store was admitted")


def test_wrong_path_kind_fails_in_real_guest(tmp_path: pathlib.Path) -> None:
    wrong = tmp_path / "regular.txt"
    wrong.write_text("not a directory\n", encoding="utf-8")
    try:
        B.run_with_real_controller(
            {"ops": [{"type": "ASSERT_SENSOR_REQUEST", "path": str(wrong)}]}, tmp_path)
    except Exception as exc:
        assert "SENSOR_VALUE_MISMATCH" in str(exc)
    else:
        raise AssertionError("regular file passed a directory-field assertion")


def test_policy_cannot_supply_its_own_field_or_value(tmp_path: pathlib.Path) -> None:
    target = tmp_path / "directory"
    target.mkdir()
    try:
        B.run_with_real_controller({"ops": [{
            "type": "ASSERT_SENSOR_REQUEST", "path": str(target),
            "field": "st_mode", "value": 0,
        }]}, tmp_path)
    except Exception as exc:
        assert "SENSOR_OP_FIELD_NOT_ALLOWED" in str(exc)
    else:
        raise AssertionError("policy supplied its own field/value")


def test_agent_accepts_the_bridge_through_its_existing_injection_point(tmp_path: pathlib.Path) -> None:
    target = tmp_path / "directory"
    target.mkdir()

    class Browser:
        def bind_environment(self, _environment: Any) -> None:
            return None

    bridge = B.AdmittedSensorGuestOps()
    agent = BrainOSWorldAgent(
        lambda _state: {"response": "verify", "actions": [
            {"type": "STATE_OPS", "ops": [
                {"type": "ASSERT_SENSOR_REQUEST", "path": str(target)}]}]},
        policy_id="sensor-admission",
        browser_controller=Browser(),
        guest_controller=bridge,
    )
    agent.bind_environment(type("Env", (), {"controller": _ControllerFor(tmp_path)})())
    response, actions = agent.predict("verify the directory", {"screenshot": b"image"})
    assert response == "verify"
    assert actions == ["WAIT"]
    assert "SENSOR_REQUEST:PASS:" in agent.history[-1]["guest_result"]["output"]


class _ControllerFor:
    def __init__(self, root: pathlib.Path) -> None:
        self.root = root

    def execute_python_command(self, program: str) -> dict[str, Any]:
        import subprocess
        import sys

        done = subprocess.run([sys.executable, "-c", program], cwd=str(self.root),
                              capture_output=True, text=True, timeout=120)
        return {"status": "success" if done.returncode == 0 else "error",
                "output": done.stdout, "error": done.stderr or None}
