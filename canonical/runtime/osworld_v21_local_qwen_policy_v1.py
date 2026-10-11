"""Local-Qwen OSWorld policy using Brain's verified loopback llama.cpp tool-call route.

Operative cognition is the pinned Brain-controlled Qwen3.5-9B substrate. The
model proposes exactly one generic action. The OSWorld adapter independently
validates/executes it; no task IDs, reference trajectories, benchmark source, or
hidden evaluator data are provided to the planner.
"""
from __future__ import annotations

import json
import time
import urllib.request
from typing import Any, Mapping

from canonical.runtime.harbor_science_planner_v1 import (
    ENDPOINT,
    TOKEN_COUNT_ENDPOINT,
    MODEL,
    MAX_RESPONSE_BYTES,
    MAX_TOOL_COMPLETION_TOKENS,
    count_input_tokens,
    effective_timeout_s,
)

TOOL_NAME = "submit_osworld_action"
MAX_PROMPT_CHARS = 30000
MAX_ACTION_JSON_CHARS = 12000
MAX_RESPONSE_CHARS = 1000

TOOL = {
    "type": "function",
    "function": {
        "name": TOOL_NAME,
        "description": (
            "Submit exactly one next generic OSWorld action. Brain validates it "
            "against a strict action/state-operation boundary before execution."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "response": {"type": "string"},
                "action_json": {
                    "type": "string",
                    "description": (
                        "A JSON object encoding one next action. Allowed top-level "
                        "types: BROWSER_OP, STATE_OPS, CLICK, DOUBLE_CLICK, "
                        "RIGHT_CLICK, MOVE, DRAG_TO, TYPE, PRESS, HOTKEY, SCROLL, "
                        "WAIT, DONE, FAIL."
                    ),
                },
            },
            "required": ["action_json"],
            "additionalProperties": False,
        },
    },
}


class OSWorldPolicyError(RuntimeError):
    pass


def _trim(value: Any, limit: int) -> Any:
    if value is None:
        return None
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, sort_keys=True)
    if len(text) <= limit:
        return text
    return text[:limit] + "\n...[TRUNCATED]"


def state_prompt(state: Mapping[str, Any]) -> str:
    if not isinstance(state, Mapping):
        raise OSWorldPolicyError("STATE_NOT_OBJECT")
    instruction = str(state.get("instruction") or "").strip()
    if not instruction:
        raise OSWorldPolicyError("INSTRUCTION_REQUIRED")

    ocr = state.get("ocr")
    ocr_items = []
    if isinstance(ocr, Mapping):
        for item in list(ocr.get("text_items") or [])[:160]:
            if not isinstance(item, Mapping):
                continue
            ocr_items.append({
                "text": str(item.get("text") or "")[:300],
                "box": item.get("box"),
                "confidence": item.get("confidence", item.get("confidence_mean")),
            })

    history = []
    for row in list(state.get("history") or [])[-12:]:
        if not isinstance(row, Mapping):
            continue
        history.append({
            "actions": row.get("actions"),
            "response": _trim(row.get("response"), 500),
            "browser_result": _trim(row.get("browser_result"), 6000),
            "guest_result": _trim(row.get("guest_result"), 6000),
            "operation_error": _trim(row.get("operation_error"), 3000),
            "screenshot_sha256": row.get("screenshot_sha256"),
        })

    payload = {
        "instruction": instruction,
        "task_current_date": state.get("task_current_date"),
        "screen": state.get("screen"),
        "screenshot_sha256": state.get("screenshot_sha256"),
        "positioned_ocr": ocr_items,
        "accessibility_tree": _trim(state.get("a11y_tree"), 10000),
        "recent_history": history,
    }
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    if len(text) > MAX_PROMPT_CHARS:
        text = text[:MAX_PROMPT_CHARS] + "\n...[STATE_TRUNCATED]"
    return text


SYSTEM = """You are the general action planner inside Project Brain's OSWorld agent.
Choose exactly ONE next action that advances the user's instruction from the current state.

Use generic state tools before pixel clicking when they are sufficient:
- Browser observation/action:
  {"type":"BROWSER_OP","op":{"type":"OBSERVE"}}
  {"type":"BROWSER_OP","op":{"type":"NAVIGATE","url":"https://..."}}
  {"type":"BROWSER_OP","op":{"type":"CLICK_TEXT","text":"...","exact":true}}
  {"type":"BROWSER_OP","op":{"type":"CLICK_ROLE","role":"button","name":"...","exact":true}}
  {"type":"BROWSER_OP","op":{"type":"FILL_LABEL","label":"...","value":"...","exact":true}}
  {"type":"BROWSER_OP","op":{"type":"FILL_PLACEHOLDER","placeholder":"...","value":"...","exact":true}}
  {"type":"BROWSER_OP","op":{"type":"PRESS","key":"Enter"}}
  {"type":"BROWSER_OP","op":{"type":"CLICK_SELECTOR","selector":"..."}}
  {"type":"BROWSER_OP","op":{"type":"FILL_SELECTOR","selector":"...","value":"..."}}
  {"type":"BROWSER_OP","op":{"type":"PRESS_SELECTOR","selector":"...","key":"Enter"}}
  {"type":"BROWSER_OP","op":{"type":"SELECT_SELECTOR","selector":"...","value":"..."}}
  {"type":"BROWSER_OP","op":{"type":"CHECK_SELECTOR","selector":"..."}}
  {"type":"BROWSER_OP","op":{"type":"UNCHECK_SELECTOR","selector":"..."}}
  {"type":"BROWSER_OP","op":{"type":"EXTRACT_TEXT","selector":"..."}}  # selector optional
  {"type":"BROWSER_OP","op":{"type":"BACK"}} / FORWARD / RELOAD
- Declarative guest end-state operations:
  {"type":"STATE_OPS","ops":[...]} where each op is MKDIR, WRITE_TEXT, COPY, MOVE,
  DELETE, JSON_SET, READ_TEXT, ASSERT_PATH_EXISTS, ASSERT_TEXT_EQUALS, SHA256_FILE,
  or RUN_CLI using only the adapter's allowlisted app CLIs.
  Prefer an explicit verification op before DONE when the task changes files.
- GUI fallback:
  CLICK/DOUBLE_CLICK/RIGHT_CLICK/MOVE/DRAG_TO/TYPE/PRESS/HOTKEY/SCROLL.
- Use WAIT only when a state change needs time.
- Use DONE only when current observations support task completion.
- If recent history already contains a passing ASSERT_PATH_EXISTS or ASSERT_TEXT_EQUALS
  receipt that directly verifies the requested file/state outcome, return DONE instead
  of repeating the mutation.
- If a post-mutation browser OBSERVE receipt visibly shows the requested goal state,
  return DONE instead of repeating the prior click/fill/navigation.
- Use FAIL only when the task is genuinely impossible from available tools/state.

Never reference task IDs, benchmark source files, evaluator internals, hidden answers,
or reference trajectories. Never assume an action succeeded without observing the
receipt or resulting state on a later cycle. Treat operation_error as a recoverable
mismatch: change selector/strategy instead of repeating the identical failed action.
If browser state is relevant but unknown, OBSERVE first. After any browser mutation,
OBSERVE again before DONE so completion is based on post-action state. OBSERVE receipts
include visible text plus generic semantic controls; prefer those labels/roles/selectors
over guessed pixel coordinates. For guest file/state changes, run an ASSERT_* verification
operation before DONE.
Return no prose outside the required tool call."""


def _request_payload(prompt: str) -> dict[str, Any]:
    return {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt},
        ],
        "tools": [TOOL],
        "tool_choice": "required",
        "parallel_tool_calls": False,
        "temperature": 0,
        "max_tokens": MAX_TOOL_COMPLETION_TOKENS,
        "stream": False,
    }


def _decode(data: Mapping[str, Any]) -> tuple[str, dict[str, Any]]:
    choices = data.get("choices")
    if not isinstance(choices, list) or len(choices) != 1:
        raise OSWorldPolicyError("ONE_CHOICE_REQUIRED")
    choice = choices[0]
    if not isinstance(choice, Mapping):
        raise OSWorldPolicyError("CHOICE_OBJECT_REQUIRED")
    if choice.get("finish_reason") == "length":
        raise OSWorldPolicyError("OUTPUT_TRUNCATED")
    message = choice.get("message")
    if not isinstance(message, Mapping):
        raise OSWorldPolicyError("MESSAGE_REQUIRED")
    calls = message.get("tool_calls")
    if not isinstance(calls, list) or len(calls) != 1:
        raise OSWorldPolicyError("EXACTLY_ONE_TOOL_CALL_REQUIRED")
    fn = calls[0].get("function") if isinstance(calls[0], Mapping) else None
    if not isinstance(fn, Mapping) or fn.get("name") != TOOL_NAME:
        raise OSWorldPolicyError("WRONG_TOOL_CALL")
    args = fn.get("arguments")
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except Exception as exc:
            raise OSWorldPolicyError("TOOL_ARGUMENTS_JSON_INVALID") from exc
    if not isinstance(args, Mapping):
        raise OSWorldPolicyError("TOOL_ARGUMENTS_OBJECT_REQUIRED")
    response = str(args.get("response") or "").strip()
    if len(response) > MAX_RESPONSE_CHARS:
        raise OSWorldPolicyError("RESPONSE_TOO_LONG")
    raw_action = args.get("action_json")
    if not isinstance(raw_action, str) or not raw_action.strip():
        raise OSWorldPolicyError("ACTION_JSON_REQUIRED")
    if len(raw_action) > MAX_ACTION_JSON_CHARS:
        raise OSWorldPolicyError("ACTION_JSON_TOO_LONG")
    try:
        action = json.loads(raw_action)
    except Exception as exc:
        raise OSWorldPolicyError("ACTION_JSON_INVALID") from exc
    if not isinstance(action, dict):
        raise OSWorldPolicyError("ACTION_OBJECT_REQUIRED")
    return response, action


def plan_state(state: Mapping[str, Any], *, timeout_s: int = 300) -> dict[str, Any]:
    prompt = state_prompt(state)
    payload = _request_payload(prompt)
    input_tokens = count_input_tokens(payload)
    timeout = effective_timeout_s(input_tokens, timeout_s)
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        ENDPOINT,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            status = int(getattr(response, "status", 200))
            if status != 200:
                raise OSWorldPolicyError(f"LOCAL_POLICY_HTTP_STATUS:{status}")
            raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise OSWorldPolicyError("LOCAL_POLICY_RESPONSE_TOO_LARGE")
        try:
            data = json.loads(raw.decode("utf-8", "replace"))
        except Exception as exc:
            raise OSWorldPolicyError("LOCAL_POLICY_RESPONSE_JSON_INVALID") from exc
        if not isinstance(data, Mapping):
            raise OSWorldPolicyError("LOCAL_POLICY_RESPONSE_OBJECT_REQUIRED")
        response_text, action = _decode(data)
        return {
            "response": response_text,
            "actions": [action],
            "_policy_receipt": {
                "model": str(data.get("model") or MODEL),
                "transport": "PINNED_LOCAL_QWEN_LLAMA_CPP_TOOL_CALL",
                "endpoint": ENDPOINT,
                "input_tokens": input_tokens,
                "effective_timeout_s": timeout,
                "duration_s": round(time.monotonic() - started, 3),
            },
        }
    except OSWorldPolicyError:
        raise
    except Exception as exc:
        raise OSWorldPolicyError(
            "LOCAL_POLICY_ROUTE_FAILED:" + type(exc).__name__ + ":" + str(exc)
        ) from exc
