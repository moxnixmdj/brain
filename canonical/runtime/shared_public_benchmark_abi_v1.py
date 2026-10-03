"""Fail-closed OpenAI-compatible chat-completions ABI for shared benchmark routes.

This is adapter infrastructure only. It does not bind or verify a Brain model,
execute a benchmark, provide a score, grant execution authority, or confer
acceptance credit. A caller must explicitly inject a backend and explicitly
enable the local execution switch; that switch is not a substitute for the
project's separate governance gate. Request bodies and credentials are never
written to logs.
"""
from __future__ import annotations

import hmac
import http.client
import json
import math
import re
import time
import uuid
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable, Mapping, Protocol
from urllib.parse import urlsplit


DEFAULT_MAX_REQUEST_BYTES = 2 * 1024 * 1024
_MAX_MESSAGES = 512
_MAX_TOOLS = 128
_MODEL_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
_FINISH_REASONS = frozenset({"stop", "length", "tool_calls", "content_filter"})
_ALLOWED_REQUEST_FIELDS = frozenset(
    {
        "model",
        "messages",
        "temperature",
        "top_p",
        "max_tokens",
        "max_completion_tokens",
        "stop",
        "presence_penalty",
        "frequency_penalty",
        "seed",
        "tools",
        "tool_choice",
        "parallel_tool_calls",
        "response_format",
        "user",
        "stream",
        "n",
    }
)
_ALLOWED_MESSAGE_FIELDS = frozenset(
    {"role", "content", "name", "tool_call_id", "tool_calls"}
)
_ALLOWED_OUTPUT_MESSAGE_FIELDS = frozenset(
    {"role", "content", "tool_calls", "refusal", "audio", "annotations"}
)


class ABIRequestError(ValueError):
    """Safe-to-return request validation error; never contains request content."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class ABIBackendError(ValueError):
    """Backend result failed the public ABI contract."""


@dataclass(frozen=True)
class CompletionResult:
    """One non-streaming assistant completion returned by a configured backend."""

    message: Mapping[str, Any]
    finish_reason: str = "stop"
    usage: Mapping[str, int] | None = None


class ChatCompletionBackend(Protocol):
    def __call__(self, request: Mapping[str, Any]) -> CompletionResult:
        """Generate exactly one completion for a validated request."""
        ...


@dataclass(frozen=True)
class RouteConfig:
    """Explicit route configuration; the local execution switch defaults off.

    ``execution_enabled`` is not governance authorization. The embedding runner
    remains responsible for validating any separate execution gate.
    """

    model_id: str
    api_key: str
    backend: Callable[[Mapping[str, Any]], CompletionResult]
    execution_enabled: bool = False
    max_request_bytes: int = DEFAULT_MAX_REQUEST_BYTES

    def __post_init__(self) -> None:
        if not isinstance(self.model_id, str) or not _MODEL_ID_RE.fullmatch(self.model_id):
            raise ValueError("model_id must be a nonempty route-safe identifier")
        if not isinstance(self.api_key, str) or len(self.api_key) < 16:
            raise ValueError("api_key must contain at least 16 characters")
        if not callable(self.backend):
            raise TypeError("backend must be callable")
        if not isinstance(self.execution_enabled, bool):
            raise TypeError("execution_enabled must be bool")
        if (
            isinstance(self.max_request_bytes, bool)
            or not isinstance(self.max_request_bytes, int)
            or not 1 <= self.max_request_bytes <= 16 * 1024 * 1024
        ):
            raise ValueError("max_request_bytes must be between 1 and 16777216")


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def _reject_nonfinite_json_constant(_constant: str) -> None:
    raise ValueError("non-finite JSON number")


def _finite_number(value: Any, *, minimum: float, maximum: float) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return math.isfinite(float(value)) and minimum <= float(value) <= maximum


def _validate_tool_calls(value: Any) -> bool:
    if not isinstance(value, list) or not value:
        return False
    for call in value:
        if not isinstance(call, Mapping) or call.get("type") != "function":
            return False
        if not isinstance(call.get("id"), str) or not call["id"]:
            return False
        function = call.get("function")
        if not isinstance(function, Mapping):
            return False
        if not isinstance(function.get("name"), str) or not function["name"]:
            return False
        if not isinstance(function.get("arguments"), str):
            return False
    return True


def _validate_message(message: Any) -> bool:
    if not isinstance(message, Mapping):
        return False
    if set(message) - _ALLOWED_MESSAGE_FIELDS:
        return False
    role = message.get("role")
    if not isinstance(role, str) or role not in {
        "system", "developer", "user", "assistant", "tool"
    }:
        return False
    if "name" in message and (not isinstance(message["name"], str) or not message["name"]):
        return False
    if role == "tool":
        if not isinstance(message.get("tool_call_id"), str) or not message["tool_call_id"]:
            return False
    elif "tool_call_id" in message:
        return False
    if "content" not in message:
        return False
    content = message["content"]
    if content is None:
        if role != "assistant" or not _validate_tool_calls(message.get("tool_calls")):
            return False
    elif isinstance(content, str):
        pass
    elif isinstance(content, list):
        # Keep text and multimodal content opaque. The ABI validates the outer
        # JSON shape but never decodes, logs, or otherwise inspects payload data.
        for part in content:
            if isinstance(part, str):
                continue
            if not isinstance(part, Mapping):
                return False
            if not isinstance(part.get("type"), str) or not part["type"]:
                return False
    else:
        return False
    if "tool_calls" in message:
        if role != "assistant" or not _validate_tool_calls(message["tool_calls"]):
            return False
    return True


def _validate_tool_definitions(value: Any) -> bool:
    if not isinstance(value, list) or len(value) > _MAX_TOOLS:
        return False
    for tool in value:
        if not isinstance(tool, Mapping) or tool.get("type") != "function":
            return False
        function = tool.get("function")
        if not isinstance(function, Mapping):
            return False
        if not isinstance(function.get("name"), str) or not function["name"]:
            return False
        if "parameters" in function and not isinstance(function["parameters"], Mapping):
            return False
    return True


def validate_chat_request(payload: Any, *, model_id: str) -> dict[str, Any]:
    """Validate the supported, non-streaming Chat Completions request subset.

    The request is returned without rewriting message content. Unsupported
    options fail closed instead of being silently dropped or misrepresented.
    """
    if not isinstance(payload, Mapping):
        raise ABIRequestError("INVALID_JSON_OBJECT")
    if set(payload) - _ALLOWED_REQUEST_FIELDS:
        raise ABIRequestError("UNSUPPORTED_REQUEST_FIELD")
    if payload.get("model") != model_id:
        raise ABIRequestError("MODEL_ID_MISMATCH")
    messages = payload.get("messages")
    if (
        not isinstance(messages, list)
        or not messages
        or len(messages) > _MAX_MESSAGES
        or any(not _validate_message(message) for message in messages)
    ):
        raise ABIRequestError("INVALID_MESSAGES")
    if payload.get("stream", False) is not False:
        raise ABIRequestError("STREAMING_UNSUPPORTED")
    choice_count = payload.get("n", 1)
    if isinstance(choice_count, bool) or not isinstance(choice_count, int) or choice_count != 1:
        raise ABIRequestError("MULTIPLE_CHOICES_UNSUPPORTED")
    if "max_tokens" in payload and "max_completion_tokens" in payload:
        raise ABIRequestError("AMBIGUOUS_TOKEN_LIMIT")
    for field in ("max_tokens", "max_completion_tokens"):
        if field in payload:
            value = payload[field]
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ABIRequestError("INVALID_TOKEN_LIMIT")
    if "temperature" in payload and not _finite_number(
        payload["temperature"], minimum=0.0, maximum=2.0
    ):
        raise ABIRequestError("INVALID_TEMPERATURE")
    if "top_p" in payload and not _finite_number(
        payload["top_p"], minimum=0.0, maximum=1.0
    ):
        raise ABIRequestError("INVALID_TOP_P")
    for field in ("presence_penalty", "frequency_penalty"):
        if field in payload and not _finite_number(
            payload[field], minimum=-2.0, maximum=2.0
        ):
            raise ABIRequestError("INVALID_PENALTY")
    if "seed" in payload and (
        isinstance(payload["seed"], bool) or not isinstance(payload["seed"], int)
    ):
        raise ABIRequestError("INVALID_SEED")
    if "stop" in payload:
        stop = payload["stop"]
        if not (
            isinstance(stop, str)
            or (
                isinstance(stop, list)
                and len(stop) <= 4
                and all(isinstance(item, str) for item in stop)
            )
        ):
            raise ABIRequestError("INVALID_STOP")
    if "tools" in payload and not _validate_tool_definitions(payload["tools"]):
        raise ABIRequestError("INVALID_TOOLS")
    if "tool_choice" in payload:
        choice = payload["tool_choice"]
        if isinstance(choice, str):
            if choice not in {"none", "auto", "required"}:
                raise ABIRequestError("INVALID_TOOL_CHOICE")
        elif (
            not isinstance(choice, Mapping)
            or choice.get("type") != "function"
            or not isinstance(choice.get("function"), Mapping)
            or not isinstance(choice["function"].get("name"), str)
        ):
            raise ABIRequestError("INVALID_TOOL_CHOICE")
    if "parallel_tool_calls" in payload and not isinstance(
        payload["parallel_tool_calls"], bool
    ):
        raise ABIRequestError("INVALID_PARALLEL_TOOL_CALLS")
    if "response_format" in payload:
        response_format = payload["response_format"]
        response_format_type = (
            response_format.get("type") if isinstance(response_format, Mapping) else None
        )
        if not isinstance(response_format_type, str) or response_format_type not in {
            "text",
            "json_object",
            "json_schema",
        }:
            raise ABIRequestError("INVALID_RESPONSE_FORMAT")
    if "user" in payload and not isinstance(payload["user"], str):
        raise ABIRequestError("INVALID_USER_FIELD")
    return dict(payload)


def _validated_completion(result: Any) -> tuple[dict[str, Any], str, dict[str, int] | None]:
    if not isinstance(result, CompletionResult):
        raise ABIBackendError("backend must return CompletionResult")
    if result.finish_reason not in _FINISH_REASONS:
        raise ABIBackendError("invalid finish reason")
    if not isinstance(result.message, Mapping):
        raise ABIBackendError("message must be an object")
    message = dict(result.message)
    if set(message) - _ALLOWED_OUTPUT_MESSAGE_FIELDS:
        raise ABIBackendError("unsupported message field")
    if message.get("role") != "assistant":
        raise ABIBackendError("assistant role required")
    if "content" in message and message["content"] is not None and not isinstance(
        message["content"], str
    ):
        raise ABIBackendError("assistant content must be text or null")
    if "tool_calls" in message and not _validate_tool_calls(message["tool_calls"]):
        raise ABIBackendError("invalid tool calls")
    if "refusal" in message and not isinstance(message["refusal"], str):
        raise ABIBackendError("invalid refusal field")
    if result.finish_reason == "tool_calls" and not message.get("tool_calls"):
        raise ABIBackendError("tool_calls finish reason requires tool calls")
    usage: dict[str, int] | None = None
    if result.usage is not None:
        if not isinstance(result.usage, Mapping):
            raise ABIBackendError("usage must be an object")
        required_usage_fields = {"prompt_tokens", "completion_tokens", "total_tokens"}
        if set(result.usage) != required_usage_fields:
            raise ABIBackendError("usage fields must be complete")
        if any(
            isinstance(result.usage[field], bool)
            or not isinstance(result.usage[field], int)
            or result.usage[field] < 0
            for field in required_usage_fields
        ):
            raise ABIBackendError("usage counts must be nonnegative integers")
        if result.usage["total_tokens"] != (
            result.usage["prompt_tokens"] + result.usage["completion_tokens"]
        ):
            raise ABIBackendError("usage total must equal prompt plus completion")
        usage = {field: result.usage[field] for field in sorted(required_usage_fields)}
    return message, result.finish_reason, usage


def _strict_json_bytes(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")


class LoopbackOpenAIChatBackend:
    """Call one explicitly configured loopback OpenAI-compatible model endpoint.

    This adapter is useful when a Brain runtime already exposes Chat Completions
    locally. It deliberately rejects non-loopback URLs, performs one request with
    no retry or fallback, bounds response bytes, and validates the returned model
    identity. It does not establish that the selected endpoint is an authoritative
    Brain configuration; that binding must be supplied and verified separately.
    """

    def __init__(
        self,
        *,
        endpoint: str,
        upstream_model_id: str,
        api_key: str | None = None,
        timeout_seconds: float = 120.0,
        max_response_bytes: int = 4 * 1024 * 1024,
    ) -> None:
        if not isinstance(endpoint, str):
            raise TypeError("endpoint must be str")
        parsed = urlsplit(endpoint)
        if (
            parsed.scheme != "http"
            or parsed.hostname != "127.0.0.1"
            or parsed.port is None
            or parsed.path != "/v1/chat/completions"
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("endpoint must be a loopback Chat Completions URL")
        if not isinstance(upstream_model_id, str) or not _MODEL_ID_RE.fullmatch(
            upstream_model_id
        ):
            raise ValueError("upstream_model_id must be a route-safe identifier")
        if api_key is not None and (not isinstance(api_key, str) or len(api_key) < 16):
            raise ValueError("api_key must be None or contain at least 16 characters")
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or not math.isfinite(float(timeout_seconds))
            or not 0 < float(timeout_seconds) <= 600
        ):
            raise ValueError("timeout_seconds must be greater than 0 and at most 600")
        if (
            isinstance(max_response_bytes, bool)
            or not isinstance(max_response_bytes, int)
            or not 1 <= max_response_bytes <= 16 * 1024 * 1024
        ):
            raise ValueError("max_response_bytes must be between 1 and 16777216")
        self._host = parsed.hostname
        self._port = parsed.port
        self._path = parsed.path
        self._model_id = upstream_model_id
        self._api_key = api_key
        self._timeout_seconds = float(timeout_seconds)
        self._max_response_bytes = max_response_bytes

    def __call__(self, request: Mapping[str, Any]) -> CompletionResult:
        if not isinstance(request, Mapping):
            raise ABIBackendError("request must be an object")
        upstream_request = dict(request)
        upstream_request["model"] = self._model_id
        body = _strict_json_bytes(upstream_request)
        if len(body) > DEFAULT_MAX_REQUEST_BYTES:
            raise ABIBackendError("upstream request exceeds byte limit")
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Connection": "close",
        }
        if self._api_key is not None:
            headers["Authorization"] = f"Bearer {self._api_key}"
        connection = http.client.HTTPConnection(
            self._host, self._port, timeout=self._timeout_seconds
        )
        try:
            connection.request("POST", self._path, body=body, headers=headers)
            response = connection.getresponse()
            if response.status != 200:
                raise ABIBackendError("loopback backend returned non-success status")
            length_header = response.getheader("Content-Length")
            if length_header is not None:
                try:
                    response_length = int(length_header)
                except ValueError as exc:
                    raise ABIBackendError("invalid backend response length") from exc
                if response_length < 0 or response_length > self._max_response_bytes:
                    raise ABIBackendError("backend response exceeds byte limit")
            raw = response.read(self._max_response_bytes + 1)
            if len(raw) > self._max_response_bytes:
                raise ABIBackendError("backend response exceeds byte limit")
            if length_header is not None and len(raw) != response_length:
                raise ABIBackendError("incomplete backend response")
        except ABIBackendError:
            raise
        except Exception as exc:
            raise ABIBackendError("loopback backend unavailable") from exc
        finally:
            connection.close()
        try:
            payload = json.loads(
                raw.decode("utf-8"),
                object_pairs_hook=_reject_duplicate_json_keys,
                parse_constant=_reject_nonfinite_json_constant,
            )
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
            raise ABIBackendError("invalid loopback backend JSON") from exc
        if not isinstance(payload, Mapping) or payload.get("model") != self._model_id:
            raise ABIBackendError("loopback backend model identity mismatch")
        choices = payload.get("choices")
        if not isinstance(choices, list) or len(choices) != 1 or not isinstance(
            choices[0], Mapping
        ):
            raise ABIBackendError("loopback backend must return exactly one choice")
        choice = choices[0]
        message = choice.get("message")
        finish_reason = choice.get("finish_reason")
        usage_value = payload.get("usage")
        usage: Mapping[str, int] | None = None
        if usage_value is not None:
            if not isinstance(usage_value, Mapping):
                raise ABIBackendError("invalid loopback backend usage")
            required = {"prompt_tokens", "completion_tokens", "total_tokens"}
            if not required.issubset(usage_value):
                raise ABIBackendError("incomplete loopback backend usage")
            usage = {field: usage_value[field] for field in required}
        return CompletionResult(
            message=message,
            finish_reason=finish_reason,
            usage=usage,
        )


def _handler_for(config: RouteConfig) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "BrainSharedBenchmarkABI/1"
        sys_version = ""

        def log_message(self, _format: str, *args: Any) -> None:
            # The stdlib default includes the request line; prompts and query
            # strings must not enter server logs.
            return

        def setup(self) -> None:
            super().setup()
            self.connection.settimeout(30.0)

        def _send_json(self, status: int, payload: Mapping[str, Any]) -> None:
            try:
                body = _strict_json_bytes(payload)
            except (TypeError, ValueError):
                status = 500
                body = b'{"error":{"type":"server_error","code":"SERIALIZATION_FAILURE","message":"response unavailable"}}'
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def _send_error(self, status: int, code: str, error_type: str) -> None:
            self._send_json(
                status,
                {
                    "error": {
                        "type": error_type,
                        "code": code,
                        "message": "request rejected",
                    }
                },
            )

        def _authorized(self) -> bool:
            values = self.headers.get_all("Authorization", [])
            if len(values) != 1 or not values[0].startswith("Bearer "):
                return False
            supplied = values[0][len("Bearer ") :]
            if not supplied:
                return False
            return hmac.compare_digest(supplied.encode("utf-8"), config.api_key.encode("utf-8"))

        def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            if self.path == "/healthz":
                self._send_json(200, {"status": "ok"})
                return
            if self.path != "/v1/models":
                self._send_error(404, "NOT_FOUND", "invalid_request_error")
                return
            if not self._authorized():
                self.close_connection = True
                self._send_error(401, "UNAUTHORIZED", "authentication_error")
                return
            self._send_json(
                200,
                {
                    "object": "list",
                    "data": [
                        {
                            "id": config.model_id,
                            "object": "model",
                            "created": 0,
                            "owned_by": "brain",
                        }
                    ],
                },
            )

        def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            if self.path != "/v1/chat/completions":
                self.close_connection = True
                self._send_error(404, "NOT_FOUND", "invalid_request_error")
                return
            if not self._authorized():
                self.close_connection = True
                self._send_error(401, "UNAUTHORIZED", "authentication_error")
                return
            if not config.execution_enabled:
                self.close_connection = True
                self._send_error(503, "EXECUTION_DISABLED", "server_error")
                return
            if self.headers.get("Transfer-Encoding") is not None or self.headers.get(
                "Content-Encoding"
            ) is not None:
                self.close_connection = True
                self._send_error(400, "UNSUPPORTED_TRANSFER_ENCODING", "invalid_request_error")
                return
            content_types = self.headers.get_all("Content-Type", [])
            if len(content_types) != 1 or content_types[0].split(";", 1)[0].strip().lower() != "application/json":
                self.close_connection = True
                self._send_error(415, "JSON_REQUIRED", "invalid_request_error")
                return
            lengths = self.headers.get_all("Content-Length", [])
            if len(lengths) != 1:
                self.close_connection = True
                self._send_error(411, "CONTENT_LENGTH_REQUIRED", "invalid_request_error")
                return
            try:
                body_length = int(lengths[0])
            except (TypeError, ValueError):
                self.close_connection = True
                self._send_error(400, "INVALID_CONTENT_LENGTH", "invalid_request_error")
                return
            if body_length < 1:
                self.close_connection = True
                self._send_error(400, "EMPTY_BODY", "invalid_request_error")
                return
            if body_length > config.max_request_bytes:
                self.close_connection = True
                self._send_error(413, "REQUEST_TOO_LARGE", "invalid_request_error")
                return
            raw = self.rfile.read(body_length)
            if len(raw) != body_length:
                self.close_connection = True
                self._send_error(400, "INCOMPLETE_BODY", "invalid_request_error")
                return
            try:
                payload = json.loads(
                    raw.decode("utf-8"),
                    object_pairs_hook=_reject_duplicate_json_keys,
                    parse_constant=_reject_nonfinite_json_constant,
                )
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError):
                self._send_error(400, "INVALID_JSON", "invalid_request_error")
                return
            try:
                request = validate_chat_request(payload, model_id=config.model_id)
            except ABIRequestError as exc:
                self._send_error(400, exc.code, "invalid_request_error")
                return
            except Exception:
                # Malformed adversarial JSON must not trigger a traceback that
                # could expose route internals or leave the client unanswered.
                self._send_error(400, "INVALID_REQUEST", "invalid_request_error")
                return
            try:
                # Exactly one backend invocation; this adapter does not retry or
                # silently switch models/routes.
                result = config.backend(request)
                message, finish_reason, usage = _validated_completion(result)
                response: dict[str, Any] = {
                    "id": f"chatcmpl-{uuid.uuid4().hex}",
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": config.model_id,
                    "choices": [
                        {
                            "index": 0,
                            "message": message,
                            "finish_reason": finish_reason,
                        }
                    ],
                }
                if usage is not None:
                    response["usage"] = usage
                # Validate serialization before writing headers so a malformed
                # backend result fails as a bounded 502 rather than a partial reply.
                _strict_json_bytes(response)
            except Exception:
                self._send_error(502, "BACKEND_UNAVAILABLE", "server_error")
                return
            self._send_json(200, response)

        def do_PUT(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            self.close_connection = True
            self._send_error(405, "METHOD_NOT_ALLOWED", "invalid_request_error")

        def do_DELETE(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            self.close_connection = True
            self._send_error(405, "METHOD_NOT_ALLOWED", "invalid_request_error")

        def do_PATCH(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            self.close_connection = True
            self._send_error(405, "METHOD_NOT_ALLOWED", "invalid_request_error")

        def do_OPTIONS(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            self.close_connection = True
            self._send_error(405, "METHOD_NOT_ALLOWED", "invalid_request_error")

    return Handler


def create_server(
    config: RouteConfig,
    *,
    host: str = "0.0.0.0",
    port: int = 8000,
) -> ThreadingHTTPServer:
    """Create, but do not start, an authenticated HTTP ABI server.

    The returned server has no model backend of its own. Inference is possible
    only when a caller supplies a backend and sets ``execution_enabled=True``.
    """
    if not isinstance(config, RouteConfig):
        raise TypeError("config must be RouteConfig")
    if not isinstance(host, str) or not host:
        raise ValueError("host must be nonempty")
    if isinstance(port, bool) or not isinstance(port, int) or not 0 <= port <= 65535:
        raise ValueError("port must be between 0 and 65535")
    server = ThreadingHTTPServer((host, port), _handler_for(config))
    server.daemon_threads = True
    server.allow_reuse_address = True
    return server
