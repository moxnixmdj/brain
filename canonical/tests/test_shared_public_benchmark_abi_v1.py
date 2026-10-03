from __future__ import annotations

import http.client
import json
import threading
import unittest
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Callable, Iterator, Mapping

from canonical.runtime.shared_public_benchmark_abi_v1 import (
    CompletionResult,
    LoopbackOpenAIChatBackend,
    RouteConfig,
    create_server,
)


TOKEN = "test-route-token-not-a-secret"
MODEL_ID = "brain-test-route"
BASE_REQUEST = {
    "model": MODEL_ID,
    "messages": [{"role": "user", "content": "synthetic ABI test"}],
}


class SharedPublicBenchmarkABITests(unittest.TestCase):
    @contextmanager
    def running_server(
        self,
        backend: Callable[[Mapping[str, Any]], CompletionResult],
        *,
        enabled: bool = True,
        max_request_bytes: int = 2 * 1024 * 1024,
    ) -> Iterator[tuple[str, int]]:
        config = RouteConfig(
            model_id=MODEL_ID,
            api_key=TOKEN,
            backend=backend,
            execution_enabled=enabled,
            max_request_bytes=max_request_bytes,
        )
        server = create_server(config, host="127.0.0.1", port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            host, port = server.server_address[:2]
            yield host, port
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def post(
        self,
        address: tuple[str, int],
        body: bytes,
        *,
        token: str | None = TOKEN,
        path: str = "/v1/chat/completions",
    ) -> tuple[int, dict[str, Any], dict[str, str]]:
        connection = http.client.HTTPConnection(*address, timeout=3)
        headers = {"Content-Type": "application/json"}
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        try:
            connection.request("POST", path, body=body, headers=headers)
            response = connection.getresponse()
            raw = response.read()
            return response.status, json.loads(raw), dict(response.getheaders())
        finally:
            connection.close()

    def get(
        self,
        address: tuple[str, int],
        path: str,
        *,
        token: str | None = TOKEN,
    ) -> tuple[int, dict[str, Any]]:
        connection = http.client.HTTPConnection(*address, timeout=3)
        headers = {}
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        try:
            connection.request("GET", path, headers=headers)
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally:
            connection.close()

    @staticmethod
    def encode(payload: Mapping[str, Any]) -> bytes:
        return json.dumps(payload, separators=(",", ":")).encode("utf-8")

    def test_execution_is_disabled_by_default_and_backend_is_not_called(self) -> None:
        calls: list[Mapping[str, Any]] = []

        def backend(request: Mapping[str, Any]) -> CompletionResult:
            calls.append(request)
            return CompletionResult({"role": "assistant", "content": "unused"})

        config = RouteConfig(model_id=MODEL_ID, api_key=TOKEN, backend=backend)
        self.assertFalse(config.execution_enabled)
        with self.running_server(backend, enabled=config.execution_enabled) as address:
            status, payload, _ = self.post(address, self.encode(BASE_REQUEST))
        self.assertEqual(status, 503)
        self.assertEqual(payload["error"]["code"], "EXECUTION_DISABLED")
        self.assertEqual(calls, [])

    def test_valid_request_is_forwarded_once_and_formatted_as_chat_completion(self) -> None:
        calls: list[Mapping[str, Any]] = []

        def backend(request: Mapping[str, Any]) -> CompletionResult:
            calls.append(request)
            return CompletionResult(
                message={"role": "assistant", "content": "synthetic response"},
                usage={"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5},
            )

        with self.running_server(backend) as address:
            status, payload, headers = self.post(address, self.encode(BASE_REQUEST))
        self.assertEqual(status, 200)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["model"], MODEL_ID)
        self.assertEqual(calls[0]["messages"], BASE_REQUEST["messages"])
        self.assertEqual(payload["object"], "chat.completion")
        self.assertEqual(payload["model"], MODEL_ID)
        self.assertEqual(payload["choices"][0]["message"]["content"], "synthetic response")
        self.assertEqual(payload["choices"][0]["finish_reason"], "stop")
        self.assertEqual(payload["usage"]["total_tokens"], 5)
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")

    def test_tool_calls_use_standard_chat_completion_shape(self) -> None:
        request = {
            "model": MODEL_ID,
            "messages": [{"role": "user", "content": "synthetic tool-call test"}],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "sample_tool",
                        "parameters": {"type": "object", "properties": {}},
                    },
                }
            ],
            "tool_choice": "auto",
        }
        expected_tool_calls = [
            {
                "id": "call-test-1",
                "type": "function",
                "function": {"name": "sample_tool", "arguments": "{}"},
            }
        ]

        def backend(_request: Mapping[str, Any]) -> CompletionResult:
            return CompletionResult(
                message={"role": "assistant", "content": None, "tool_calls": expected_tool_calls},
                finish_reason="tool_calls",
            )

        with self.running_server(backend) as address:
            status, payload, _ = self.post(address, self.encode(request))
        self.assertEqual(status, 200)
        self.assertEqual(payload["choices"][0]["finish_reason"], "tool_calls")
        self.assertEqual(payload["choices"][0]["message"]["tool_calls"], expected_tool_calls)

    def test_authentication_is_required_before_backend_invocation(self) -> None:
        calls: list[int] = []

        def backend(_request: Mapping[str, Any]) -> CompletionResult:
            calls.append(1)
            return CompletionResult({"role": "assistant", "content": "unused"})

        with self.running_server(backend) as address:
            status, payload, _ = self.post(address, self.encode(BASE_REQUEST), token=None)
        self.assertEqual(status, 401)
        self.assertEqual(payload["error"]["code"], "UNAUTHORIZED")
        self.assertEqual(calls, [])

    def test_invalid_and_unsupported_requests_fail_closed(self) -> None:
        calls: list[int] = []

        def backend(_request: Mapping[str, Any]) -> CompletionResult:
            calls.append(1)
            return CompletionResult({"role": "assistant", "content": "unused"})

        invalid_requests = []
        wrong_model = dict(BASE_REQUEST, model="other-model")
        invalid_requests.append(wrong_model)
        invalid_requests.append(dict(BASE_REQUEST, stream=True))
        invalid_requests.append(dict(BASE_REQUEST, n=2))
        invalid_requests.append(dict(BASE_REQUEST, unrecognized_option=True))
        invalid_requests.append(
            {"model": MODEL_ID, "messages": [{"role": ["user"], "content": "bad role"}]}
        )
        invalid_requests.append(dict(BASE_REQUEST, temperature=float("nan")))

        with self.running_server(backend) as address:
            results = [self.post(address, self.encode(request))[0] for request in invalid_requests]
        self.assertEqual(results, [400] * len(invalid_requests))
        self.assertEqual(calls, [])

    def test_duplicate_json_keys_are_rejected(self) -> None:
        calls: list[int] = []

        def backend(_request: Mapping[str, Any]) -> CompletionResult:
            calls.append(1)
            return CompletionResult({"role": "assistant", "content": "unused"})

        body = (
            b'{"model":"brain-test-route","model":"brain-test-route",'
            b'"messages":[{"role":"user","content":"synthetic"}]}'
        )
        with self.running_server(backend) as address:
            status, payload, _ = self.post(address, body)
        self.assertEqual(status, 400)
        self.assertEqual(payload["error"]["code"], "INVALID_JSON")
        self.assertEqual(calls, [])

    def test_request_size_limit_is_enforced_before_backend_invocation(self) -> None:
        calls: list[int] = []

        def backend(_request: Mapping[str, Any]) -> CompletionResult:
            calls.append(1)
            return CompletionResult({"role": "assistant", "content": "unused"})

        body = self.encode(BASE_REQUEST)
        with self.running_server(backend, max_request_bytes=32) as address:
            status, payload, _ = self.post(address, body)
        self.assertEqual(status, 413)
        self.assertEqual(payload["error"]["code"], "REQUEST_TOO_LARGE")
        self.assertEqual(calls, [])

    def test_backend_exceptions_are_sanitized_and_not_retried(self) -> None:
        calls: list[int] = []

        def backend(_request: Mapping[str, Any]) -> CompletionResult:
            calls.append(1)
            raise RuntimeError("synthetic-secret-backend-error")

        with self.running_server(backend) as address:
            status, payload, _ = self.post(address, self.encode(BASE_REQUEST))
        self.assertEqual(status, 502)
        self.assertEqual(payload["error"]["code"], "BACKEND_UNAVAILABLE")
        self.assertNotIn("synthetic-secret-backend-error", json.dumps(payload))
        self.assertEqual(calls, [1])

    def test_models_and_health_endpoints_do_not_expose_backend_or_secret(self) -> None:
        def backend(_request: Mapping[str, Any]) -> CompletionResult:
            return CompletionResult({"role": "assistant", "content": "unused"})

        with self.running_server(backend, enabled=False) as address:
            health_status, health = self.get(address, "/healthz", token=None)
            models_status, models = self.get(address, "/v1/models")
        self.assertEqual((health_status, health), (200, {"status": "ok"}))
        self.assertEqual(models_status, 200)
        self.assertEqual(models["data"][0]["id"], MODEL_ID)
        self.assertNotIn(TOKEN, json.dumps(models))

    def test_loopback_backend_binds_one_local_model_without_retry_or_fallback(self) -> None:
        received: list[dict[str, Any]] = []
        upstream_model_id = "brain-local-model"

        class UpstreamHandler(BaseHTTPRequestHandler):
            def log_message(self, _format: str, *args: Any) -> None:
                return

            def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
                length = int(self.headers["Content-Length"])
                received.append(json.loads(self.rfile.read(length)))
                response = {
                    "model": upstream_model_id,
                    "choices": [
                        {
                            "index": 0,
                            "message": {"role": "assistant", "content": "synthetic upstream"},
                            "finish_reason": "stop",
                        }
                    ],
                }
                body = json.dumps(response).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        upstream = HTTPServer(("127.0.0.1", 0), UpstreamHandler)
        thread = threading.Thread(target=upstream.serve_forever, daemon=True)
        thread.start()
        try:
            port = upstream.server_address[1]
            backend = LoopbackOpenAIChatBackend(
                endpoint=f"http://127.0.0.1:{port}/v1/chat/completions",
                upstream_model_id=upstream_model_id,
            )
            result = backend(dict(BASE_REQUEST))
        finally:
            upstream.shutdown()
            upstream.server_close()
            thread.join(timeout=2)
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0]["model"], upstream_model_id)
        self.assertEqual(received[0]["messages"], BASE_REQUEST["messages"])
        self.assertEqual(result.message["content"], "synthetic upstream")
        self.assertEqual(result.finish_reason, "stop")

    def test_loopback_backend_rejects_non_loopback_or_unexpected_urls(self) -> None:
        with self.assertRaises(ValueError):
            LoopbackOpenAIChatBackend(
                endpoint="http://example.com/v1/chat/completions",
                upstream_model_id="brain-local-model",
            )
        with self.assertRaises(ValueError):
            LoopbackOpenAIChatBackend(
                endpoint="http://127.0.0.1:8080/v1/models",
                upstream_model_id="brain-local-model",
            )


if __name__ == "__main__":
    unittest.main()
