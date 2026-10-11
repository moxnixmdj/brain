"""Strict OSWorld 2.1 adapter for a Brain-owned state-conditioned policy.

This module closes the harness/interface boundary while preserving OSWorld's
native evaluator. Generic host-side browser and guest-state API operations are
receipted back into the next policy cycle; graphical actions remain the fallback.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime.osworld_v21_host_browser_ops_v1 import (
    BrowserOpsError,
    OSWorldHostBrowser,
)
from canonical.runtime.osworld_v21_host_guest_ops_v1 import (
    GuestOpsError,
    OSWorldHostGuestOps,
)

SCHEMA = "PROJECT_BRAIN_OSWORLD_V21_AGENT_ADAPTER_V1"
WIDTH = 1920
HEIGHT = 1080
MAX_BATCH = 4
MAX_HISTORY = 32
MAX_TEXT = 4000
MAX_ERROR = 2000

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

    if kind.startswith("BROWSER_"):
        return compile_browser_op(raw)

    if kind == "STATE_OPS":
        if set(raw) - {"type", "ops"}:
            raise AdapterError("STATE_OPS_HAS_UNSUPPORTED_FIELDS")
        return compile_state_ops({"ops": raw.get("ops")})

    if kind in {"WAIT", "DONE", "FAIL"}:
        if set(raw) - {"type", "reason"}:
            raise AdapterError(f"{kind}_HAS_UNSUPPORTED_FIELDS")
        return compile_osworld_pyautogui({"type": kind.lower()}, Screen(WIDTH, HEIGHT))

    typed: dict[str, Any]
    if kind == "CLICK":
        typed = {"type": "click", "x": raw.get("x"), "y": raw.get("y"), "button": "left"}
    elif kind == "DOUBLE_CLICK":
        typed = {"type": "double_click", "x": raw.get("x"), "y": raw.get("y")}
    elif kind == "RIGHT_CLICK":
        typed = {"type": "click", "x": raw.get("x"), "y": raw.get("y"), "button": "right"}
    elif kind == "MOVE":
        typed = {"type": "move", "x": raw.get("x"), "y": raw.get("y")}
    elif kind == "DRAG_TO":
        typed = {
            "type": "drag",
            "path": [
                {"x": raw.get("from_x", raw.get("x0", 0)), "y": raw.get("from_y", raw.get("y0", 0))},
                {"x": raw.get("x"), "y": raw.get("y")},
            ],
            "duration_per_segment": float(raw.get("duration_ms", 500)) / 1000.0,
        }
    elif kind == "TYPE":
        typed = {"type": "type", "text": raw.get("text"), "interval": float(raw.get("interval_ms", 10)) / 1000.0}
    elif kind == "PRESS":
        key = raw.get("key")
        presses = raw.get("presses", 1)
        if isinstance(presses, bool) or not isinstance(presses, int) or not 1 <= presses <= 20:
            raise AdapterError("PRESSES_OUT_OF_RANGE")
        if presses == 1:
            typed = {"type": "keypress", "keys": [key]}
        else:
            # Preserve one OSWorld step while avoiding an unbounded action batch.
            compiled = compile_osworld_pyautogui({"type": "keypress", "keys": [key]}, Screen(WIDTH, HEIGHT))
            return "; ".join([compiled] * presses)
    elif kind == "HOTKEY":
        typed = {"type": "keypress", "keys": raw.get("keys")}
    elif kind == "SCROLL":
        clicks = raw.get("clicks")
        typed = {"type": "scroll", "x": WIDTH // 2, "y": HEIGHT // 2, "scroll_x": 0, "scroll_y": clicks}
    else:
        raise AdapterError("ACTION_TYPE_UNSUPPORTED:" + kind)

    try:
        return compile_osworld_pyautogui(typed, Screen(WIDTH, HEIGHT))
    except Exception as exc:
        raise AdapterError(type(exc).__name__ + ":" + str(exc)) from exc

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
        browser_controller: Any | None = None,
        guest_controller: Any | None = None,
        ocr_provider: Any | None = None,
    ) -> None:
        if not callable(policy_provider):
            raise AdapterError("POLICY_PROVIDER_NOT_CALLABLE")
        if not isinstance(policy_id, str) or not policy_id.strip():
            raise AdapterError("POLICY_ID_REQUIRED")
        if (screen_width, screen_height) != (WIDTH, HEIGHT):
            raise AdapterError("MATCHED_PROTOCOL_REQUIRES_1920x1080")
        self.policy_provider = policy_provider
        self.policy_id = policy_id.strip()
        self.browser_controller = browser_controller if browser_controller is not None else OSWorldHostBrowser()
        self.guest_controller = guest_controller if guest_controller is not None else OSWorldHostGuestOps()
        self.ocr_provider = ocr_provider
        self.history: list[dict[str, Any]] = []
        self.runtime_logger = None
        self.task_current_date = None
        self.result_dir: Path | None = None

    def bind_environment(self, environment: Any) -> None:
        for name, controller in (
            ("BROWSER", self.browser_controller),
            ("GUEST", self.guest_controller),
        ):
            binder = getattr(controller, "bind_environment", None)
            if not callable(binder):
                raise AdapterError(name + "_CONTROLLER_BIND_UNAVAILABLE")
            binder(environment)

    def set_result_dir(self, path: str | Path) -> None:
        target = Path(path)
        target.mkdir(parents=True, exist_ok=True)
        self.result_dir = target

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
        ocr = None
        if self.ocr_provider is not None:
            if not callable(self.ocr_provider):
                raise AdapterError("OCR_PROVIDER_NOT_CALLABLE")
            try:
                ocr = self.ocr_provider(screenshot_bytes)
            except Exception as exc:
                ocr = {
                    "status": "UNAVAILABLE",
                    "reason": type(exc).__name__ + ":" + str(exc)[:MAX_ERROR],
                    "source_sha256": hashlib.sha256(screenshot_bytes).hexdigest(),
                    "terminal_semantic_authority": False,
                }
        return {
            "schema": SCHEMA,
            "policy_id": self.policy_id,
            "instruction": instruction,
            "task_current_date": self.task_current_date,
            "screen": {"width": WIDTH, "height": HEIGHT},
            "screenshot_bytes": screenshot_bytes,
            "screenshot_sha256": hashlib.sha256(screenshot_bytes).hexdigest(),
            "ocr": ocr,
            "a11y_tree": obs.get("accessibility_tree") or obs.get("a11y_tree"),
            "user_response": obs.get("user_response"),
            "history": [dict(x) for x in self.history[-MAX_HISTORY:]],
        }

    def _record(
        self,
        state: Mapping[str, Any],
        *,
        response: str,
        actions: list[str],
        policy_receipt: Any = None,
        **extra: Any,
    ) -> None:
        fingerprint_material = "\n".join(actions) + "\n" + repr(sorted(extra.items()))
        receipt = {
            "screenshot_sha256": state["screenshot_sha256"],
            "action_fingerprint": hashlib.sha256(fingerprint_material.encode("utf-8")).hexdigest(),
            "actions": list(actions),
            "response": response,
            **extra,
        }
        if isinstance(policy_receipt, Mapping):
            receipt["policy_receipt"] = dict(policy_receipt)
        self.history.append(receipt)
        if len(self.history) > MAX_HISTORY:
            del self.history[:-MAX_HISTORY]
        if self.result_dir is not None:
            durable = {
                "schema": "PROJECT_BRAIN_OSWORLD_V21_ACTION_RECEIPT_V1",
                "policy_id": self.policy_id,
                **receipt,
            }
            with (self.result_dir / "brain_action_receipts.jsonl").open(
                "a", encoding="utf-8"
            ) as stream:
                stream.write(
                    json.dumps(
                        durable,
                        ensure_ascii=False,
                        sort_keys=True,
                        default=str,
                    )
                    + "\n"
                )

    def _recoverable_error(
        self,
        state: Mapping[str, Any],
        raw: Mapping[str, Any] | None,
        error: Exception,
    ) -> tuple[str, list[str]]:
        response = str((raw or {}).get("response") or "").strip()
        message = type(error).__name__ + ":" + str(error)[:MAX_ERROR]
        self._record(
            state,
            response=response,
            actions=["WAIT"],
            policy_receipt=(raw or {}).get("_policy_receipt"),
            operation_error=message,
        )
        return response, ["WAIT"]

    def predict(self, instruction: str, obs: Mapping[str, Any]) -> tuple[str, list[str]]:
        state = self._observation(instruction, obs)
        raw = self.policy_provider(state)
        if not isinstance(raw, Mapping):
            raise AdapterError("POLICY_OUTPUT_NOT_OBJECT")
        raw_actions = raw.get("actions")
        policy_receipt = raw.get("_policy_receipt")

        if (
            isinstance(raw_actions, list)
            and len(raw_actions) == 1
            and isinstance(raw_actions[0], Mapping)
        ):
            first = raw_actions[0]
            kind = str(first.get("type") or "").strip().upper()

            if kind == "BROWSER_OP":
                if set(first) - {"type", "op"}:
                    return self._recoverable_error(
                        state, raw, AdapterError("BROWSER_OP_HAS_UNSUPPORTED_FIELDS")
                    )
                op = first.get("op")
                if not isinstance(op, Mapping):
                    return self._recoverable_error(
                        state, raw, AdapterError("BROWSER_OP_OBJECT_REQUIRED")
                    )
                try:
                    result = self.browser_controller.run(op)
                except (BrowserOpsError, ValueError, RuntimeError) as exc:
                    return self._recoverable_error(state, raw, exc)
                response = str(raw.get("response") or "").strip()
                actions = ["WAIT"]
                self._record(
                    state,
                    response=response,
                    actions=actions,
                    policy_receipt=policy_receipt,
                    submitted_operation=dict(op),
                    browser_result=dict(result),
                )
                return response, actions

            if kind.startswith("BROWSER_"):
        return compile_browser_op(raw)

    if kind == "STATE_OPS":
                if set(first) - {"type", "ops"}:
                    return self._recoverable_error(
                        state, raw, AdapterError("STATE_OPS_HAS_UNSUPPORTED_FIELDS")
                    )
                raw_ops = first.get("ops")
                if not isinstance(raw_ops, list) or any(not isinstance(x, Mapping) for x in raw_ops):
                    return self._recoverable_error(
                        state, raw, AdapterError("STATE_OPS_LIST_REQUIRED")
                    )
                try:
                    result = self.guest_controller.run({"ops": raw_ops})
                except (GuestOpsError, ValueError, RuntimeError) as exc:
                    return self._recoverable_error(state, raw, exc)
                response = str(raw.get("response") or "").strip()
                actions = ["WAIT"]
                self._record(
                    state,
                    response=response,
                    actions=actions,
                    policy_receipt=policy_receipt,
                    submitted_operations=[dict(x) for x in raw_ops],
                    guest_result=dict(result),
                )
                return response, actions

        try:
            response, actions = compile_actions(raw)
        except AdapterError as exc:
            return self._recoverable_error(state, raw, exc)

        if actions == ["DONE"]:
            if not self.history:
                return self._recoverable_error(
                    state, raw, AdapterError("DONE_WITHOUT_PRIOR_OBSERVED_ACTION")
                )
            prior = self.history[-1]
            if prior.get("operation_error"):
                return self._recoverable_error(
                    state, raw, AdapterError("DONE_AFTER_UNRECOVERED_OPERATION_ERROR")
                )

            guest_verified = False
            guest = prior.get("guest_result")
            if isinstance(guest, Mapping) and guest.get("ok") is True:
                output = str(guest.get("output") or "")
                guest_verified = (
                    "ASSERT_PATH_EXISTS:PASS:" in output
                    or "ASSERT_TEXT_EQUALS:PASS:" in output
                )

            browser_verified = False
            browser = prior.get("browser_result")
            if isinstance(browser, Mapping) and str(browser.get("type") or "").upper() == "OBSERVE":
                browser_verified = any(
                    isinstance(row, Mapping)
                    and isinstance(row.get("browser_result"), Mapping)
                    and str(row["browser_result"].get("type") or "").upper()
                    not in {"", "OBSERVE"}
                    and not row.get("operation_error")
                    for row in self.history[:-1]
                )

            gui_verified = (
                not isinstance(guest, Mapping)
                and not isinstance(browser, Mapping)
                and prior.get("screenshot_sha256") != state.get("screenshot_sha256")
            )

            if not (guest_verified or browser_verified or gui_verified):
                return self._recoverable_error(
                    state, raw, AdapterError("DONE_WITHOUT_VERIFIED_COMPLETION_EVIDENCE")
                )

        self._record(
            state,
            response=response,
            actions=actions,
            policy_receipt=policy_receipt,
        )

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
