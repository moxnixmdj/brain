"""Brain-owned local text planner for the OSWorld 2.1 action DSL.

The operative language model is the exact Brain-controlled Qwen3.5-9B-M GGUF
mirror. No remote model/provider fallback exists. Output is parsed into the
strict OSWorld adapter DSL and receives zero authority merely for being emitted.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_OSWORLD_V21_QWEN35_PLANNER_V1"
MODEL_BYTES = 5_060_174_144
MODEL_SHA256 = "f41c0a0c0e43bf721fb2da29374cd1a97271bac0bab08a9dc42964525e82350c"
LLAMA_CPP_REVISION = "bec4772f6a2527d371557b5d2032641e5ff7619c"
MAX_BROWSER_PAGES = 8
MAX_ELEMENTS_PER_PAGE = 80
MAX_HISTORY = 10

_verified_model: Path | None = None


class PlannerError(RuntimeError):
    pass


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _local_file(env: str) -> Path:
    value = os.environ.get(env, "").strip()
    if not value:
        raise PlannerError(env + "_REQUIRED")
    path = Path(value).resolve()
    if not path.is_file():
        raise PlannerError(env + "_MISSING")
    return path


def _model() -> Path:
    global _verified_model
    model = _local_file("PROJECT_BRAIN_QWEN35_MODEL")
    if _verified_model == model:
        return model
    if model.stat().st_size != MODEL_BYTES:
        raise PlannerError("MODEL_BYTE_COUNT_MISMATCH")
    if _sha256_file(model) != MODEL_SHA256:
        raise PlannerError("MODEL_SHA256_MISMATCH")
    _verified_model = model
    return model


def _compact_browser_state(value: Any) -> Any:
    if not isinstance(value, Mapping):
        return value
    pages_out = []
    pages = value.get("pages")
    if isinstance(pages, list):
        for page in pages[:MAX_BROWSER_PAGES]:
            if not isinstance(page, Mapping):
                continue
            elements = page.get("elements")
            compact_elements = []
            if isinstance(elements, list):
                for e in elements[:MAX_ELEMENTS_PER_PAGE]:
                    if not isinstance(e, Mapping):
                        continue
                    compact_elements.append({
                        k: e.get(k)
                        for k in (
                            "i", "tag", "role", "type", "text", "aria",
                            "placeholder", "name", "value", "href",
                            "checked", "disabled",
                        )
                        if e.get(k) not in (None, "", False)
                    })
            pages_out.append({
                "page_index": page.get("page_index"),
                "url": page.get("url"),
                "title": page.get("title"),
                "elements": compact_elements,
            })
    return {
        "status": value.get("status"),
        "page_count": value.get("page_count"),
        "pages": pages_out,
    }


def _prompt(state: Mapping[str, Any]) -> str:
    goal = str(state.get("instruction") or "").strip()
    if not goal:
        raise PlannerError("INSTRUCTION_REQUIRED")
    browser_state = _compact_browser_state(state.get("browser_state"))
    history = state.get("history")
    if not isinstance(history, list):
        history = []

    contract = {
        "goal": goal,
        "browser_state": browser_state,
        "a11y_tree": (
            str(state.get("a11y_tree"))[:12000]
            if state.get("a11y_tree") is not None else None
        ),
        "history": history[-MAX_HISTORY:],
    }
    return """You are the deterministic planning component of Project Brain's OSWorld agent.
Return EXACTLY one JSON object and no markdown or commentary.

Allowed output shape:
{"response":"short rationale","actions":[ACTION]}

Choose exactly one ACTION per turn.

Preferred browser action:
{"type":"BROWSER_OP","op":{"type":"NAVIGATE|CLICK_SELECTOR|CLICK_TEXT|FILL|PRESS|SELECT|CHECK|NEW_TAB|CLOSE_TAB", ...}}
Use only selectors/text/URLs justified by the supplied live browser state or user goal.
Do not invent hidden task IDs, evaluator details, expected answers, or benchmark source paths.

Other allowed actions when browser control cannot do the job:
{"type":"CLICK","x":0..1919,"y":0..1079}
{"type":"DOUBLE_CLICK","x":...,"y":...}
{"type":"RIGHT_CLICK","x":...,"y":...}
{"type":"MOVE","x":...,"y":...}
{"type":"DRAG_TO","x":...,"y":...,"duration_ms":50..5000}
{"type":"TYPE","text":"...","interval_ms":0..500}
{"type":"PRESS","key":"...","presses":1}
{"type":"HOTKEY","keys":["ctrl","s"]}
{"type":"SCROLL","clicks":nonzero integer}
{"type":"STATE_OPS","ops":[bounded declarative file/application operations]}
{"type":"WAIT"}
{"type":"DONE"}
{"type":"FAIL"}

Prefer direct browser/state operations over coordinate guessing.
Never emit raw shell, Python, JavaScript, or evaluator/task-source access.
Use DONE only when the requested end state is already satisfied.
Use WAIT after an operation when fresh state is needed.
Fail closed rather than fabricating an unsupported operation.

LIVE_STATE:
""" + json.dumps(contract, ensure_ascii=False, separators=(",", ":"))


def _extract_object(text: str) -> Mapping[str, Any]:
    decoder = json.JSONDecoder()
    for i, ch in enumerate(text):
        if ch != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(text[i:])
        except json.JSONDecodeError:
            continue
        if isinstance(obj, Mapping) and isinstance(obj.get("actions"), list):
            return obj
    raise PlannerError("PLANNER_JSON_OBJECT_NOT_FOUND")


class Qwen35OSWorldPlanner:
    def __init__(self) -> None:
        self.cli = _local_file("PROJECT_BRAIN_LLAMA_CLI")
        self.model = _model()

    def __call__(self, state: Mapping[str, Any]) -> Mapping[str, Any]:
        prompt = _prompt(state)
        timeout = float(os.environ.get("PROJECT_BRAIN_QWEN35_TIMEOUT_S", "240"))
        threads = max(1, min(int(os.environ.get("PROJECT_BRAIN_QWEN35_THREADS", "4")), 16))
        cmd = [
            str(self.cli),
            "-m", str(self.model),
            "-p", prompt,
            "-n", "640",
            "-c", "8192",
            "-t", str(threads),
            "--temp", "0",
            "--no-display-prompt",
        ]
        env = {
            k: os.environ[k]
            for k in ("PATH", "HOME", "TMPDIR", "TEMP", "TMP", "LD_LIBRARY_PATH")
            if k in os.environ
        }
        env["PROJECT_BRAIN_OFFLINE"] = "1"
        proc = subprocess.run(
            cmd,
            text=True,
            capture_output=True,
            timeout=timeout,
            env=env,
            check=False,
        )
        if proc.returncode != 0:
            raise PlannerError(
                "LOCAL_PLANNER_EXECUTION_FAILED:" + proc.stderr[-1600:].replace("\n", " ")
            )
        out = _extract_object(proc.stdout)
        return dict(out)
