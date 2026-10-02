"""Brain-owned OpenAI-compatible control gateway for AutomationBench.

The model is an untrusted GENERAL_COGNITION_SUBSTRATE. Brain owns the operative
automation configuration: one-action semantics, exact tool allowlisting,
argument-schema validation, fail-closed refusal, provenance, and response
normalization.

No benchmark case is executed by this module unless the caller sends one.
"""
from __future__ import annotations

import argparse
import json
import os
import time
import uuid
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable, Mapping

SCHEMA = "PROJECT_BRAIN_AUTOMATIONBENCH_CONTROL_GATEWAY_V1"
MAX_BODY_BYTES = 2_000_000
MAX_TOOLS = 256
MAX_MESSAGES = 256

class GatewayBlocked(RuntimeError):
    pass

def _json_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise GatewayBlocked(f"{label}_MUST_BE_OBJECT")
    return dict(value)

def _tool_map(tools: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(tools, list) or not tools:
        raise GatewayBlocked("TOOLS_REQUIRED")
    if len(tools) > MAX_TOOLS:
        raise GatewayBlocked("TOOL_LIMIT_EXCEEDED")
    out: dict[str, dict[str, Any]] = {}
    for i, raw in enumerate(tools):
        tool = _json_object(raw, f"TOOL_{i}")
        if tool.get("type") != "function":
            raise GatewayBlocked("ONLY_FUNCTION_TOOLS_ALLOWED")
        fn = _json_object(tool.get("function"), f"TOOL_{i}_FUNCTION")
        name = fn.get("name")
        if not isinstance(name, str) or not name or name in out:
            raise GatewayBlocked("TOOL_NAME_INVALID_OR_DUPLICATE")
        params = fn.get("parameters") or {"type": "object", "properties": {}}
        if not isinstance(params, dict) or params.get("type", "object") != "object":
            raise GatewayBlocked(f"TOOL_SCHEMA_NOT_OBJECT:{name}")
        out[name] = {"name": name, "description": fn.get("description", ""), "parameters": params}
    return out

def _validate_scalar(value: Any, typ: str, path: str) -> None:
    ok = {
        "string": isinstance(value, str),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "null": value is None,
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
    }.get(typ)
    if ok is False:
        raise GatewayBlocked(f"ARG_TYPE_MISMATCH:{path}:{typ}")

def _validate_schema(value: Any, schema: Mapping[str, Any], path: str = "arguments") -> None:
    typ = schema.get("type")
    if isinstance(typ, str):
        _validate_scalar(value, typ, path)
    if isinstance(schema.get("enum"), list) and value not in schema["enum"]:
        raise GatewayBlocked(f"ARG_ENUM_MISMATCH:{path}")
    if isinstance(value, dict):
        props = schema.get("properties") or {}
        if not isinstance(props, dict):
            raise GatewayBlocked(f"SCHEMA_PROPERTIES_INVALID:{path}")
        required = schema.get("required") or []
        if not isinstance(required, list):
            raise GatewayBlocked(f"SCHEMA_REQUIRED_INVALID:{path}")
        missing = [x for x in required if x not in value]
        if missing:
            raise GatewayBlocked("ARG_REQUIRED_MISSING:" + path + ":" + ",".join(map(str, missing)))
        additional = schema.get("additionalProperties", True)
        if additional is False:
            extras = sorted(set(value) - set(props))
            if extras:
                raise GatewayBlocked("ARG_EXTRA_KEYS:" + path + ":" + ",".join(extras))
        for key, item in value.items():
            sub = props.get(key)
            if isinstance(sub, dict):
                _validate_schema(item, sub, f"{path}.{key}")
    if isinstance(value, list) and isinstance(schema.get("items"), dict):
        for i, item in enumerate(value):
            _validate_schema(item, schema["items"], f"{path}[{i}]")

def _compact_messages(messages: Any) -> list[dict[str, Any]]:
    if not isinstance(messages, list) or not messages:
        raise GatewayBlocked("MESSAGES_REQUIRED")
    if len(messages) > MAX_MESSAGES:
        raise GatewayBlocked("MESSAGE_LIMIT_EXCEEDED")
    out = []
    for i, raw in enumerate(messages):
        msg = _json_object(raw, f"MESSAGE_{i}")
        role = msg.get("role")
        if role not in {"system", "user", "assistant", "tool"}:
            raise GatewayBlocked(f"MESSAGE_ROLE_INVALID:{i}")
        keep = {"role": role}
        if "content" in msg:
            keep["content"] = msg["content"]
        if "tool_calls" in msg:
            keep["tool_calls"] = msg["tool_calls"]
        if "tool_call_id" in msg:
            keep["tool_call_id"] = msg["tool_call_id"]
        out.append(keep)
    return out

def build_planner_prompt(messages: list[dict[str, Any]], tools: dict[str, dict[str, Any]]) -> str:
    contract = {
        "instruction": (
            "Return exactly one JSON object. Choose either "
            "{\"type\":\"tool\",\"name\":<allowed tool name>,\"arguments\":<object>} "
            "or {\"type\":\"finish\",\"content\":<string>}. "
            "The proposal is untrusted and will be independently validated."
        ),
        "allowed_tools": list(tools.values()),
        "conversation": messages,
    }
    return json.dumps(contract, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def _parse_proposal(text: str) -> dict[str, Any]:
    raw = str(text).strip()
    try:
        value = json.loads(raw)
    except Exception:
        a, b = raw.find("{"), raw.rfind("}")
        if a < 0 or b < a:
            raise GatewayBlocked("PLANNER_NO_JSON")
        try:
            value = json.loads(raw[a:b+1])
        except Exception as exc:
            raise GatewayBlocked("PLANNER_INVALID_JSON") from exc
    return _json_object(value, "PROPOSAL")

def decide(payload: Mapping[str, Any], planner: Callable[[str], Any]) -> dict[str, Any]:
    messages = _compact_messages(payload.get("messages"))
    tools = _tool_map(payload.get("tools"))
    prompt = build_planner_prompt(messages, tools)
    proposed = planner(prompt)
    if isinstance(proposed, Mapping):
        text = proposed.get("text", "")
        substrate = str(proposed.get("model") or "declared-general-substrate")
        transport = str(proposed.get("transport") or "")
    else:
        text, substrate, transport = str(proposed), "declared-general-substrate", ""
    p = _parse_proposal(text)
    typ = p.get("type")
    if typ == "finish":
        content = p.get("content")
        if not isinstance(content, str) or not content.strip():
            raise GatewayBlocked("FINISH_CONTENT_REQUIRED")
        return {"kind": "finish", "content": content, "substrate": substrate, "transport": transport}
    if typ != "tool":
        raise GatewayBlocked("PROPOSAL_TYPE_REJECTED")
    name = p.get("name")
    if not isinstance(name, str) or name not in tools:
        raise GatewayBlocked("UNKNOWN_TOOL_REJECTED")
    args = p.get("arguments")
    if not isinstance(args, dict):
        raise GatewayBlocked("TOOL_ARGUMENTS_MUST_BE_OBJECT")
    _validate_schema(args, tools[name]["parameters"])
    return {
        "kind": "tool",
        "name": name,
        "arguments": args,
        "substrate": substrate,
        "transport": transport,
    }

def openai_response(payload: Mapping[str, Any], planner: Callable[[str], Any]) -> dict[str, Any]:
    result = decide(payload, planner)
    rid = "chatcmpl-brain-" + uuid.uuid4().hex
    message: dict[str, Any] = {"role": "assistant", "content": None}
    finish_reason = "stop"
    if result["kind"] == "tool":
        call_id = "call_" + uuid.uuid4().hex
        message["tool_calls"] = [{
            "id": call_id,
            "type": "function",
            "function": {
                "name": result["name"],
                "arguments": json.dumps(result["arguments"], sort_keys=True, separators=(",", ":")),
            },
        }]
        finish_reason = "tool_calls"
    else:
        message["content"] = result["content"]
    return {
        "id": rid,
        "object": "chat.completion",
        "created": int(time.time()),
        "model": str(payload.get("model") or "brain-automation-v1"),
        "choices": [{"index": 0, "message": message, "finish_reason": finish_reason}],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        "brain_control": {
            "schema": SCHEMA,
            "configuration": "BRAIN_OWNED_TOOL_ALLOWLIST_SCHEMA_AND_ONE_ACTION_GATE",
            "substrate": result["substrate"],
            "transport": result["transport"],
        },
    }

def default_planner(prompt: str) -> Mapping[str, Any]:
    """Zero-incremental proposal transport; output remains untrusted."""
    endpoint = os.environ.get("BRAIN_AUTOMATION_PLANNER_URL", "https://text.pollinations.ai/").strip()
    timeout_s = int(os.environ.get("BRAIN_AUTOMATION_PLANNER_TIMEOUT_S", "60"))
    models = tuple(
        x.strip() for x in os.environ.get(
            "BRAIN_AUTOMATION_PLANNER_MODELS", "openai-fast,openai,mistral"
        ).split(",") if x.strip()
    )
    if not endpoint or not models:
        raise GatewayBlocked("PLANNER_TRANSPORT_CONFIGURATION_INVALID")
    errors: list[str] = []
    for model in models:
        body = json.dumps({
            "messages": [{"role": "user", "content": prompt}],
            "model": model,
            "jsonMode": True,
        }).encode("utf-8")
        req = urllib.request.Request(
            endpoint,
            data=body,
            headers={"Content-Type": "application/json", "User-Agent": "ProjectBrain-Automation/1.0"},
            method="POST",
        )
        t = time.monotonic()
        try:
            with urllib.request.urlopen(req, timeout=timeout_s) as response:
                raw = response.read(30000).decode("utf-8", "replace")
            return {
                "text": raw,
                "model": model,
                "duration_s": round(time.monotonic() - t, 3),
                "transport": "ZERO_INCREMENTAL_PUBLIC_PROPOSAL_ENDPOINT",
            }
        except Exception as exc:
            errors.append(f"{model}:{type(exc).__name__}:{str(exc)[:200]}")
    raise GatewayBlocked("PLANNER_ALL_ROUTES_FAILED:" + "|".join(errors))

class Handler(BaseHTTPRequestHandler):
    planner = staticmethod(default_planner)
    def log_message(self, fmt: str, *args: Any) -> None:
        return
    def _write(self, code: int, payload: Mapping[str, Any]) -> None:
        raw = json.dumps(payload, sort_keys=True).encode()
        self.send_response(code)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)
    def do_GET(self) -> None:
        if self.path == "/health":
            self._write(200, {"status": "ok", "schema": SCHEMA})
        else:
            self._write(404, {"error": "not_found"})
    def do_POST(self) -> None:
        if self.path.rstrip("/") != "/v1/chat/completions":
            self._write(404, {"error": "not_found"}); return
        try:
            n = int(self.headers.get("content-length", "0"))
            if n <= 0 or n > MAX_BODY_BYTES:
                raise GatewayBlocked("BODY_SIZE_INVALID")
            payload = json.loads(self.rfile.read(n))
            if not isinstance(payload, dict):
                raise GatewayBlocked("REQUEST_MUST_BE_OBJECT")
            self._write(200, openai_response(payload, self.planner))
        except GatewayBlocked as exc:
            self._write(422, {"error": {"type": "brain_control_rejection", "message": str(exc)}})
        except Exception as exc:
            self._write(503, {"error": {"type": "brain_gateway_failure", "message": type(exc).__name__}})

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8787)
    args = ap.parse_args()
    ThreadingHTTPServer((args.host, args.port), Handler).serve_forever()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
