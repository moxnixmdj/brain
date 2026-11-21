"""Fail-closed tests for the zero-model authorized-answer intake.

Receipt-producing cases execute real guest programs through the project's pinned
state ops and admitted sensor bridge. No PASS receipt is hand-written.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile
from typing import Any, Mapping

import pytest

from canonical.runtime.osworld_sensor_request_bridge_v1 import AdmittedSensorGuestOps
from canonical.runtime.osworld_v21_host_guest_ops_v1 import OSWorldHostGuestOps

from intake import authorized_answer_intake_v1 as A


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


def _state(instruction: str, rows: list[dict[str, Any]] | None = None,
           answers: list[dict[str, Any]] | None = None,
           users: list[str] | None = None) -> dict[str, Any]:
    return {
        "instruction": instruction,
        "history": rows or [],
        "authorized_answers": answers or [],
        "authorized_users": users if users is not None else ["owner"],
    }


def _done(_: Mapping[str, Any]) -> dict[str, Any]:
    return {"response": "finish", "actions": [{"type": "DONE"}]}


def _row(ops: list[dict[str, Any]], result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "screenshot_sha256": "a" * 64,
        "action_fingerprint": "x",
        "actions": ["WAIT"],
        "response": "state ops",
        "submitted_operations": ops,
        "guest_result": dict(result),
    }


def _answer(instruction: str, slot: str, value: Any, author: str = "owner",
            text: str | None = None) -> dict[str, Any]:
    return {
        "slot": slot,
        "value": value,
        "answer_text": text if text is not None else str(value),
        "author": author,
        "instruction_sha256": A.instruction_sha256(instruction),
    }


def test_missing_slot_asks_one_question_and_never_finishes() -> None:
    out = A.decide(_state("Create the folder"), _done)
    assert out["actions"][0]["type"] == "ASK_USER"
    assert out["actions"][0]["slot"] == A.PATH_SLOT
    assert out["_policy_receipt"]["verified"] is False


def test_authorized_natural_language_answer_becomes_a_real_directory_assertion() -> None:
    with tempfile.TemporaryDirectory(prefix="brain-intake-dir-") as tmp:
        root = pathlib.Path(tmp)
        target = root / "reports"
        instruction = "Create the folder"
        answers = [_answer(instruction, A.PATH_SLOT, str(target),
                           text=f"Please use this path: {target}")]
        state = _state(instruction, answers=answers)
        compiled = A.compiled_requirements(state)
        assert compiled["pass"] is True
        assert compiled["requirements"][0]["kind"] == "DIRECTORY_SENSOR"

        ops = [
            {"type": "MKDIR", "path": str(target)},
            {"type": "ASSERT_PATH_EXISTS", "path": str(target)},
            {"type": "ASSERT_SENSOR_REQUEST", "path": str(target)},
        ]
        bridge = AdmittedSensorGuestOps()
        bridge.bind_environment(Environment(root))
        result = bridge.run({"ops": ops})
        assert result["ok"] is True
        assert "SENSOR_REQUEST:PASS:" in result["output"]

        out = A.decide(_state(instruction, [_row(ops, result)], answers), _done)
        assert out["actions"] == [{"type": "DONE"}]
        assert out["_policy_receipt"]["answers_used"][0]["slot"] == A.PATH_SLOT


def test_value_answer_becomes_a_real_text_assertion() -> None:
    with tempfile.TemporaryDirectory(prefix="brain-intake-value-") as tmp:
        root = pathlib.Path(tmp)
        target = root / "answer.txt"
        instruction = f"Write the missing value into {target}"
        state = _state(instruction, answers=[_answer(instruction, A.VALUE_SLOT, "42")])
        compiled = A.compiled_requirements(state)
        assert compiled["pass"] is True
        assert any(
            req.get("kind") == "TEXT_CONTAINS" and req.get("path") == str(target)
            and req.get("text") == "42" for req in compiled["requirements"]
        )

        ops = [
            {"type": "WRITE_TEXT", "path": str(target), "text": "value=42"},
            {"type": "ASSERT_TEXT_CONTAINS", "path": str(target), "text": "42"},
        ]
        guest = OSWorldHostGuestOps()
        guest.bind_environment(Environment(root))
        result = guest.run({"ops": ops})
        assert "ASSERT_TEXT_CONTAINS:PASS:" in result["output"]
        out = A.decide(_state(instruction, [_row(ops, result)], state["authorized_answers"]), _done)
        assert out["actions"] == [{"type": "DONE"}]


def test_untrusted_answer_is_not_a_requirement() -> None:
    instruction = "Create the folder"
    state = _state(instruction, answers=[
        _answer(instruction, A.PATH_SLOT, "/tmp/attacker", author="stranger")
    ])
    compiled = A.compiled_requirements(state)
    assert compiled["requirements"] == []
    assert compiled["refusal"] == "ANSWER_NOT_MACHINE_CHECKABLE"
    out = A.decide(state, _done)
    assert out["actions"][0]["type"] == "ASK_USER"


def test_two_answers_to_one_slot_are_a_conflict_not_a_vote() -> None:
    instruction = "Create the folder"
    state = _state(instruction, answers=[
        _answer(instruction, A.PATH_SLOT, "/tmp/one"),
        _answer(instruction, A.PATH_SLOT, "/tmp/two"),
    ])
    compiled = A.compiled_requirements(state)
    assert compiled["pass"] is False
    assert compiled["refusal"] == "CONFLICTING_AUTHORIZED_ANSWERS"


def test_answer_cannot_override_an_explicit_path() -> None:
    instruction = "Create the folder /tmp/explicit"
    state = _state(instruction, answers=[_answer(instruction, A.PATH_SLOT, "/tmp/other")])
    compiled = A.compiled_requirements(state)
    assert compiled["errors"] == ["ANSWER_CONFLICTS_WITH_EXPLICIT_PATH"]


def test_stale_receipt_after_answer_is_still_not_done() -> None:
    with tempfile.TemporaryDirectory(prefix="brain-intake-stale-") as tmp:
        root = pathlib.Path(tmp)
        target = root / "reports"
        instruction = "Create the folder"
        answers = [_answer(instruction, A.PATH_SLOT, str(target))]
        ops = [
            {"type": "MKDIR", "path": str(target)},
            {"type": "ASSERT_PATH_EXISTS", "path": str(target)},
            {"type": "ASSERT_SENSOR_REQUEST", "path": str(target)},
        ]
        bridge = AdmittedSensorGuestOps()
        bridge.bind_environment(Environment(root))
        passed = bridge.run({"ops": ops})
        mutation = [{"type": "DELETE", "path": str(target)}]
        mutated = bridge.run({"ops": mutation})
        out = A.decide(_state(instruction, [_row(ops, passed), _row(mutation, mutated)], answers), _done)
        assert out["actions"][0]["type"] == "ASK_USER"
        assert out["_policy_receipt"]["verified"] is False


def test_one_experience_persists_externally_and_deletion_unlearns_it(tmp_path: pathlib.Path) -> None:
    instruction = "Create the folder"
    target = "/tmp/brain-intake-persisted"
    state = _state(instruction, answers=[_answer(instruction, A.PATH_SLOT, target)])
    store = tmp_path / "answers.json"
    assert A.persist_answers(state, store)["answers_written"] == 1
    reloaded = _state(instruction, answers=A.load_answers(store))
    assert A.compiled_requirements(reloaded)["requirements"][0]["path"] == target
    store.unlink()
    assert A.load_answers(store) == []
    assert A.decide(_state(instruction, answers=A.load_answers(store)), _done)["actions"][0]["type"] == "ASK_USER"


def test_answer_to_a_different_instruction_is_not_reused() -> None:
    original = "Create the folder"
    other = "Create another folder"
    state = _state(other, answers=[_answer(original, A.PATH_SLOT, "/tmp/other")])
    assert A.compiled_requirements(state)["refusal"] == "NO_AUTHORIZED_ANSWER"


def test_untyped_prose_answer_is_refused_without_guessing() -> None:
    instruction = "Write the missing value into /tmp/x.txt"
    answer = _answer(instruction, A.VALUE_SLOT, "anything")
    answer.pop("value")
    answer["answer_text"] = "the answer is probably seven"
    state = _state(instruction, answers=[answer])
    state["missing_slots"] = [A.VALUE_SLOT]
    compiled = A.compiled_requirements(state)
    assert compiled["refusal"] == "ANSWER_NOT_MACHINE_CHECKABLE"
    assert all(not req.get("authorized_answer") for req in compiled["requirements"])


def test_no_model_client_imported_by_the_intake() -> None:
    source = pathlib.Path(A.__file__).read_text(encoding="utf-8")
    for token in ("openai", "anthropic", "transformers", "torch", "requests.post", "urllib.request"):
        assert token not in source


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
