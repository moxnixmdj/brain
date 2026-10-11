"""Strict OSWorld 2.1 adapter for a Brain-owned state-conditioned policy.

This module closes only the harness/interface boundary:
    reset()
    predict(instruction, obs) -> (response, actions)

It intentionally does not invent a policy. A caller must supply a policy_provider
whose operative cognition is separately content-addressed and admissible.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime.osworld_v21_state_ops_v1 import compile_state_ops

SCHEMA = "PROJECT_BRAIN_OSWORLD_V21_AGENT_ADAPTER_V1"
WIDTH = 1920
HEIGHT = 1080
MAX_BATCH = 4
MAX_HISTORY = 32
MAX_TEXT = 4000

PolicyProvider = Callable[[Mapping[str, Any]], Mapping[str, Any]]


class AdapterError(ValueError):
    pass


@dataclass(frozen=True)
class Receipt:
    screenshot_sha256: str
    action_fingerprint: str
    action_count: int


def _int(value: Any, name: str, lo: int, hi: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise AdapterError(f"{name}_MUST_BE_INT")
    if not lo <= value <= hi:
        raise AdapterError(f"{name}_OUT_OF_RANGE")
    return value


def _text(value: Any, name: str, max_len: int = MAX_TEXT) -> str:
    if not isinstance(value, str):
        raise AdapterError(f"{name}_MUST_BE_STRING")
    if len(value) > max_len:
        raise AdapterError(f"{name}_TOO_LONG")
    return value


def _special(kind: str) -> str | None:
    if kind in {"WAIT", "DONE", "FAIL"}:
        return kind
    return None


def _compile_one(raw: Mapping[str, Any]) -> str:
    kind = str(raw.get("type") or "").strip().upper()
    special = _special(kind)
    if special is not None:
        if set(raw) - {"type", "reason"}:
            raise AdapterError(f"{kind}_HAS_UNSUPPORTED_FIELDS")
        return special

    if kind in {"CLICK", "DOUBLE_CLICK", "RIGHT_CLICK", "MOVE"}:
        x = _int(raw.get("x"), "X", 0, WIDTH - 1)
        y = _int(raw.get("y"), "Y", 0, HEIGHT - 1)
        if kind == "CLICK":
            return f"pyautogui.click({x}, {y})"
        if kind == "DOUBLE_CLICK":
            return f"pyautogui.doubleClick({x}, {y}, interval=0.15)"
        if kind == "RIGHT_CLICK":
            return f"pyautogui.rightClick({x}, {y})"
        return f"pyautogui.moveTo({x}, {y}, duration=0.2)"

    if kind == "DRAG_TO":
        x = _int(raw.get("x"), "X", 0, WIDTH - 1)
        y = _int(raw.get("y"), "Y", 0, HEIGHT - 1)
        duration_ms = _int(raw.get("duration_ms", 500), "DURATION_MS", 50, 5000)
        return f"pyautogui.dragTo({x}, {y}, duration={duration_ms / 1000.0:.3f}, button='left')"

    if kind == "TYPE":
        value = _text(raw.get("text"), "TEXT")
        interval_ms = _int(raw.get("interval_ms", 10), "INTERVAL_MS", 0, 500)
        return f"pyautogui.write({value!r}, interval={interval_ms / 1000.0:.3f})"

    if kind == "PRESS":
        key = _text(raw.get("key"), "KEY", 64).strip().lower()
        if not key or any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789_+-" for ch in key):
            raise AdapterError("KEY_INVALID")
        presses = _int(raw.get("presses", 1), "PRESSES", 1, 20)
        return f"pyautogui.press({key!r}, presses={presses})"

    if kind == "HOTKEY":
        keys = raw.get("keys")
        if not isinstance(keys, Sequence) or isinstance(keys, (str, bytes)):
            raise AdapterError("KEYS_MUST_BE_SEQUENCE")
        if not 1 <= len(keys) <= 5:
            raise AdapterError("HOTKEY_KEY_COUNT_INVALID")
        normalized = []
        for item in keys:
            key = _text(item, "KEY", 64).strip().lower()
            if not key or any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789_+-" for ch in key):
                raise AdapterError("KEY_INVALID")
            normalized.append(key)
        return "pyautogui.hotkey(" + ", ".join(repr(k) for k in normalized) + ")"

    if kind == "STATE_OPS":
        if set(raw) - {"type", "ops"}:
            raise AdapterError("STATE_OPS_HAS_UNSUPPORTED_FIELDS")
        return compile_state_ops({"ops": raw.get("ops")})

    if kind == "SCROLL":
        clicks = _int(raw.get("clicks"), "CLICKS", -100, 100)
        if clicks == 0:
            raise AdapterError("SCROLL_ZERO")
        return f"pyautogui.scroll({clicks})"

    raise AdapterError("ACTION_TYPE_UNSUPPORTED:" + kind)


def compile_actions(policy_output: Mapping[str, Any]) -> tuple[str, list[str]]:
    if not isinstance(policy_output, Mapping):
        raise AdapterError("POLICY_OUTPUT_NOT_OBJECT")
    response = str(policy_output.get("response") or "").strip()
    raw_actions = policy_output.get("actions")
    if not isinstance(raw_actions, list) or not raw_actions:
        raise AdapterError("ACTIONS_REQUIRED")
    if len(raw_actions) > MAX_BATCH:
        raise AdapterError("ACTION_BATCH_TOO_LARGE")
    if any(not isinstance(x, Mapping) for x in raw_actions):
        raise AdapterError("ACTION_NOT_OBJECT")
    actions = [_compile_one(x) for x in raw_actions]
    terminal = [a for a in actions if a in {"WAIT", "DONE", "FAIL"}]
    if terminal and len(actions) != 1:
        raise AdapterError("SPECIAL_ACTION_MUST_BE_SINGLETON")
    return response, actions


class BrainOSWorldAgent:
    """OSWorld-compatible shell around one separately verified Brain policy."""

    def __init__(
        self,
        policy_provider: PolicyProvider,
        *,
        policy_id: str,
        screen_width: int = WIDTH,
        screen_height: int = HEIGHT,
    ) -> None:
        if not callable(policy_provider):
            raise AdapterError("POLICY_PROVIDER_NOT_CALLABLE")
        if not isinstance(policy_id, str) or not policy_id.strip():
            raise AdapterError("POLICY_ID_REQUIRED")
        if (screen_width, screen_height) != (WIDTH, HEIGHT):
            raise AdapterError("MATCHED_PROTOCOL_REQUIRES_1920x1080")
        self.policy_provider = policy_provider
        self.policy_id = policy_id.strip()
        self.history: list[dict[str, Any]] = []
        self.runtime_logger = None
        self.task_current_date = None

    def reset(self, runtime_logger=None, **_: Any) -> None:
        self.history.clear()
        self.runtime_logger = runtime_logger

    def _observation(self, instruction: str, obs: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(instruction, str) or not instruction.strip():
            raise AdapterError("INSTRUCTION_REQUIRED")
        if not isinstance(obs, Mapping):
            raise AdapterError("OBSERVATION_NOT_OBJECT")
        screenshot = obs.get("screenshot")
        if not isinstance(screenshot, (bytes, bytearray)) or not screenshot:
            raise AdapterError("SCREENSHOT_BYTES_REQUIRED")
        screenshot_bytes = bytes(screenshot)
        return {
            "schema": SCHEMA,
            "policy_id": self.policy_id,
            "instruction": instruction,
            "task_current_date": self.task_current_date,
            "screen": {"width": WIDTH, "height": HEIGHT},
            "screenshot_bytes": screenshot_bytes,
            "screenshot_sha256": hashlib.sha256(screenshot_bytes).hexdigest(),
            "a11y_tree": obs.get("accessibility_tree") or obs.get("a11y_tree"),
            "user_response": obs.get("user_response"),
            "history": [dict(x) for x in self.history[-MAX_HISTORY:]],
        }

    def predict(self, instruction: str, obs: Mapping[str, Any]) -> tuple[str, list[str]]:
        state = self._observation(instruction, obs)
        raw = self.policy_provider(state)
        response, actions = compile_actions(raw)
        fingerprint = hashlib.sha256("\n".join(actions).encode("utf-8")).hexdigest()

        receipt = {
            "screenshot_sha256": state["screenshot_sha256"],
            "action_fingerprint": fingerprint,
            "actions": list(actions),
            "response": response,
        }
        self.history.append(receipt)
        if len(self.history) > MAX_HISTORY:
            del self.history[:-MAX_HISTORY]

        if self.runtime_logger is not None:
            try:
                self.runtime_logger.info(
                    "BrainOSWorld policy=%s screenshot=%s actions=%s",
                    self.policy_id,
                    state["screenshot_sha256"],
                    actions,
                )
            except Exception:
                pass
        return response, actions
