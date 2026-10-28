#!/usr/bin/env python3
# PROJECT_BRAIN
"""
Distributed candidate evaluation worker node.

Runs an HTTP worker that evaluates SWE patch candidates on behalf of the
central repair loop. Each worker exposes:

  GET  /health   -> node identity + capabilities
  POST /eval_candidate -> deserialize args, call _eval_candidate, return result

Workers register themselves in the NodeRegistry so the central loop can
discover them and farm out candidate evaluation for true cross-process /
cross-machine parallelism.

Usage:
    python canonical/runtime/distributed_eval_node_v1.py <node_id> [port]
"""

from __future__ import annotations

import json
import os
import sys
import threading
from pathlib import Path
from typing import Any, Optional

from wsgiref.simple_server import make_server

from canonical.runtime.distributed_queue_v1 import (
    NodeInfo,
    NodeRegistry,
    PRIORITY_NORMAL,
)
from canonical.runtime.distributed_execution_v1 import REGISTRY_PATH

ROOT = Path(__file__).resolve().parents[2]

# Import _eval_candidate from the SWE engine.
import importlib.util

_SWE_MOD = None


def _swe_module():
    global _SWE_MOD
    if _SWE_MOD is None:
        # Import the already-loaded module instead of re-execing it from
        # file. Re-execing would re-run module-level code (including
        # _register_local_node() which starts more workers → cascade).
        import canonical.runtime.bound_capabilities.real_swe_execution_v1 as mod
        _SWE_MOD = mod
    return _SWE_MOD


def _eval_candidate_worker(args: list) -> dict:
    """Evaluate one candidate on this worker node.

    Appends ``_is_distributed_worker=True`` to the args so the callee skips
    the distributed-eval attempt — prevents infinite HTTP recursion
    (worker → worker → worker → deadlock).
    """
    mod = _swe_module()
    args_with_flag = list(args) + [True]  # _is_distributed_worker flag
    return mod._eval_candidate(tuple(args_with_flag))


def _make_node_app(node_id: str, port: int):
    """Build a minimal WSGI app for the eval worker node."""

    def app(environ, start_response):
        path = environ.get("PATH_INFO", "/")
        method = environ.get("REQUEST_METHOD", "GET")

        if method == "GET" and path == "/health":
            body = json.dumps(
                {
                    "schema": "PROJECT_BRAIN_DISTRIBUTED_EVAL_NODE_HEALTH_V1",
                    "node_id": node_id,
                    "status": "ACTIVE",
                    "capabilities": ["software.hardcore.kernel.eval_candidate.v1"],
                    "port": port,
                    "ts": __import__("time").time(),
                }
            ).encode("utf-8")
            start_response("200 OK", [("Content-Type", "application/json")])
            return [body]

        if method == "POST" and path == "/eval_candidate":
            try:
                length = int(environ.get("CONTENT_LENGTH", "0"))
            except ValueError:
                length = 0
            raw = environ["wsgi.input"].read(length) if length else b"{}"
            try:
                payload = json.loads(raw)
            except Exception:
                payload = {}
            args = payload.get("args", [])
            timeout_s = payload.get("timeout_s", 60)
            try:
                result = _eval_candidate_worker(args)
                body = json.dumps(
                    {
                        "schema": "PROJECT_BRAIN_DISTRIBUTED_EVAL_RESULT_V1",
                        "node_id": node_id,
                        "ok": True,
                        "result": result,
                    }
                ).encode("utf-8")
                start_response("200 OK", [("Content-Type", "application/json")])
                return [body]
            except Exception as exc:  # noqa: BLE001
                body = json.dumps(
                    {
                        "schema": "PROJECT_BRAIN_DISTRIBUTED_EVAL_RESULT_V1",
                        "node_id": node_id,
                        "ok": False,
                        "error": f"{type(exc).__name__}:{exc}",
                    }
                ).encode("utf-8")
                start_response("500 Internal Server Error", [("Content-Type", "application/json")])
                return [body]

        if method == "POST" and path == "/eval_candidates_batch":
            try:
                length = int(environ.get("CONTENT_LENGTH", "0"))
            except ValueError:
                length = 0
            raw = environ["wsgi.input"].read(length) if length else b"{}"
            try:
                payload = json.loads(raw)
            except Exception:
                payload = {}
            batches = payload.get("batches", [])
            results = []
            for batch_entry in batches:
                args = batch_entry.get("args", [])
                timeout_s = batch_entry.get("timeout_s", 60)
                try:
                    result = _eval_candidate_worker(args)
                    results.append(result)
                except Exception as exc:  # noqa: BLE001
                    results.append({"returncode": None, "error": str(exc), "timed_out": True})
            body = json.dumps(
                {
                    "schema": "PROJECT_BRAIN_DISTRIBUTED_EVAL_BATCH_RESULT_V1",
                    "node_id": node_id,
                    "ok": True,
                    "results": results,
                }
            ).encode("utf-8")
            start_response("200 OK", [("Content-Type", "application/json")])
            return [body]

        start_response("404 Not Found", [("Content-Type", "text/plain")])
        return [b"not found"]

    return app


def run_node(node_id: str, host: str = "0.0.0.0", port: int = 0) -> int:
    """Run a distributed eval worker node (blocking).

    Returns the actual port the server is listening on.
    """
    from wsgiref.simple_server import make_server

    # port=0 lets the OS pick a free port; we need to discover it.
    server = make_server(host, port, _make_node_app(node_id, port))
    actual_port = server.server_address[1]
    endpoint = f"http://{host}:{actual_port}"
    if host == "0.0.0.0":
        endpoint = f"http://127.0.0.1:{actual_port}"

    # Register in the node registry with a real, reachable endpoint.
    reg = NodeRegistry()
    reg.register(NodeInfo(node_id, endpoint, ["software.hardcore.kernel.eval_candidate.v1"]))

    print(
        f"[distributed_eval_node] node {node_id} listening on {endpoint}",
        flush=True,
    )
    server.serve_forever()
    return actual_port


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python distributed_eval_node_v1.py <node_id> [port]")
        sys.exit(2)
    nid = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    run_node(nid, port=port)
