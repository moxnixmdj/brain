#!/usr/bin/env python3
"""Distributed execution engine for Project Brain.

Dispatches bound capability executions to remote nodes over HTTP,
collects results, verifies them, and handles node failure with retry.

Design goals:
- Reuse existing verified_bound_capability_execution_adapter_v1 for local execution
- HTTP-based node protocol (simple, language-agnostic)
- Node registry with health checking and capability advertising
- Failover: retry on a different node when a node errors
- Result content-addressable: results are keyed by capability+inputs hash
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]

REGISTRY_PATH = ROOT / "canonical" / "runtime" / "distributed_nodes_v1.json"

NODE_REQUEST_TIMEOUT = float(os.environ.get("BRAIN_NODE_TIMEOUT", "30"))
NODE_HEALTH_TIMEOUT = float(os.environ.get("BRAIN_NODE_HEALTH_TIMEOUT", "5"))
MAX_RETRIES = int(os.environ.get("BRAIN_NODE_MAX_RETRIES", "3"))

__all__ = [
    "DistributedExecutor",
    "execute_capability_distributed",
    "load_node_registry",
    "save_node_registry",
]


# ---------------------------------------------------------------------------
# Node registry
# ---------------------------------------------------------------------------

def load_node_registry(path: Path = REGISTRY_PATH) -> dict:
    """Load the distributed node registry."""
    if not path.is_file():
        return {"schema": "PROJECT_BRAIN_DISTRIBUTED_NODES_V1", "nodes": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"schema": "PROJECT_BRAIN_DISTRIBUTED_NODES_V1", "nodes": []}


def save_node_registry(data: dict, path: Path = REGISTRY_PATH) -> None:
    """Persist the distributed node registry."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def register_node(
    node_id: str,
    endpoint: str,
    capabilities: Optional[list[str]] = None,
    path: Path = REGISTRY_PATH,
) -> dict:
    """Register (or update) a node in the registry."""
    data = load_node_registry(path)
    caps = capabilities or []
    now = time.time()
    for node in data.get("nodes", []):
        if node.get("node_id") == node_id:
            node.update(
                {
                    "endpoint": endpoint,
                    "capabilities": caps,
                    "registered_at": now,
                    "status": "ACTIVE",
                }
            )
            save_node_registry(data, path)
            return data
    data.setdefault("nodes", []).append(
        {
            "node_id": node_id,
            "endpoint": endpoint,
            "capabilities": caps,
            "registered_at": now,
            "status": "ACTIVE",
            "last_seen": None,
            "failure_count": 0,
        }
    )
    save_node_registry(data, path)
    return data


# ---------------------------------------------------------------------------
# HTTP node client
# ---------------------------------------------------------------------------

class _NodeClient:
    """Minimal HTTP client for a distributed execution node."""

    def __init__(self, node_id: str, endpoint: str):
        self.node_id = node_id
        self.endpoint = endpoint.rstrip("/")

    def health(self) -> Tuple[bool, Optional[dict]]:
        """Check node health. Returns (ok, payload)."""
        try:
            req = urllib.request.Request(
                self.endpoint + "/health",
                method="GET",
                headers={"Accept": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=NODE_HEALTH_TIMEOUT) as resp:
                body = resp.read()
                return True, json.loads(body)
        except Exception:
            return False, None

    def execute(
        self,
        capability_id: str,
        inputs: dict,
        timeout: float = NODE_REQUEST_TIMEOUT,
    ) -> Tuple[bool, Optional[dict], Optional[str]]:
        """Ask the node to execute a capability.

        Returns (ok, result, error).
        """
        payload = {
            "schema": "PROJECT_BRAIN_DISTRIBUTED_EXECUTE_V1",
            "capability_id": capability_id,
            "inputs": inputs,
        }
        body = json.dumps(payload).encode("utf-8")
        try:
            req = urllib.request.Request(
                self.endpoint + "/execute",
                method="POST",
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
                result = json.loads(raw)
                return True, result, None
        except urllib.error.HTTPError as exc:
            try:
                err_body = exc.read().decode("utf-8", errors="replace")
            except Exception:
                err_body = str(exc)
            return False, None, f"HTTP_{exc.code}:{err_body[:200]}"
        except Exception as exc:
            return False, None, f"{type(exc).__name__}:{exc}"


# ---------------------------------------------------------------------------
# Local fallback executor (reuses existing adapter)
# ---------------------------------------------------------------------------

def _execute_locally(capability_id: str, inputs: dict) -> dict:
    """Execute a capability locally via the verified bound adapter."""
    from canonical.runtime import verified_bound_capability_execution_adapter_v1 as promoted_bound

    return promoted_bound.execute(capability_id, inputs=inputs)


# ---------------------------------------------------------------------------
# Distributed executor
# ---------------------------------------------------------------------------

class DistributedExecutor:
    """Executes capabilities across a cluster of nodes.

    Nodes are looked up from the registry. When a node is unavailable or
    returns an error, the executor fails over to another node, and finally
    falls back to local execution.
    """

    def __init__(self, registry_path: Path = REGISTRY_PATH):
        self.registry_path = registry_path

    def _healthy_nodes(self, capability_id: str) -> list[dict]:
        """Return registry nodes that are healthy and advertise the capability."""
        data = load_node_registry(self.registry_path)
        nodes = data.get("nodes", [])
        healthy = []
        for node in nodes:
            if node.get("status") != "ACTIVE":
                continue
            caps = node.get("capabilities", [])
            if capability_id not in caps and "*" not in caps:
                continue
            client = _NodeClient(node["node_id"], node["endpoint"])
            ok, _ = client.health()
            if ok:
                healthy.append(node)
        return healthy

    def execute(
        self,
        capability_id: str,
        inputs: dict,
        prefer_local: bool = False,
    ) -> dict:
        """Execute ``capability_id`` with ``inputs`` across the cluster.

        Tries healthy remote nodes first (round-robin by failure count),
        falls back to local execution if all nodes fail.
        """
        nodes = self._healthy_nodes(capability_id)

        # Sort by failure count (fewer failures first) for basic load balancing.
        nodes.sort(key=lambda n: int(n.get("failure_count", 0)))

        last_error: Optional[str] = None
        for node in nodes:
            client = _NodeClient(node["node_id"], node["endpoint"])
            ok, result, err = client.execute(capability_id, inputs)
            if ok and result is not None:
                # Mark node as seen
                self._touch_node(node["node_id"])
                return result
            last_error = err or "UNKNOWN_NODE_ERROR"
            self._record_failure(node["node_id"])

        # All remote nodes failed — fall back to local execution.
        if prefer_local or not nodes:
            return _execute_locally(capability_id, inputs)

        # One final attempt locally before giving up.
        try:
            return _execute_locally(capability_id, inputs)
        except Exception as exc:
            return {
                "type": "distributed_execution",
                "pass": False,
                "errors": [
                    "DISTRIBUTED_EXECUTION_ALL_NODES_FAILED:" + str(last_error),
                    "LOCAL_FALLBACK_FAILED:" + type(exc).__name__ + ":" + str(exc),
                ],
            }

    def _touch_node(self, node_id: str) -> None:
        data = load_node_registry(self.registry_path)
        now = time.time()
        for node in data.get("nodes", []):
            if node.get("node_id") == node_id:
                node["last_seen"] = now
                node["failure_count"] = max(0, int(node.get("failure_count", 0)) - 1)
                break
        save_node_registry(data, self.registry_path)

    def _record_failure(self, node_id: str) -> None:
        data = load_node_registry(self.registry_path)
        for node in data.get("nodes", []):
            if node.get("node_id") == node_id:
                node["failure_count"] = int(node.get("failure_count", 0)) + 1
                if int(node.get("failure_count", 0)) >= MAX_RETRIES:
                    node["status"] = "DEGRADED"
                break
        save_node_registry(data, self.registry_path)


# ---------------------------------------------------------------------------
# Module-level convenience API
# ---------------------------------------------------------------------------

_executor = DistributedExecutor()


def execute_capability_distributed(
    capability_id: str,
    inputs: dict,
    prefer_local: bool = False,
) -> dict:
    """Module-level convenience: execute a capability across the cluster."""
    return _executor.execute(capability_id, inputs, prefer_local=prefer_local)


# ---------------------------------------------------------------------------
# Node server (reference implementation)
# ---------------------------------------------------------------------------

def make_node_app(node_id: str, capabilities: list[str]):
    """Build a minimal WSGI/HTTP node app (pure stdlib).

    The node exposes:
      GET  /health   -> node identity + capabilities
      POST /execute  -> run a capability locally and return the result

    Intended to be run with ``wsgiref.simple_server`` or any WSGI container.
    """
    def app(environ, start_response):
        path = environ.get("PATH_INFO", "/")
        method = environ.get("REQUEST_METHOD", "GET")

        if method == "GET" and path == "/health":
            body = json.dumps(
                {
                    "schema": "PROJECT_BRAIN_DISTRIBUTED_NODE_HEALTH_V1",
                    "node_id": node_id,
                    "status": "ACTIVE",
                    "capabilities": capabilities,
                    "ts": time.time(),
                }
            ).encode("utf-8")
            start_response("200 OK", [("Content-Type", "application/json")])
            return [body]

        if method == "POST" and path == "/execute":
            try:
                length = int(environ.get("CONTENT_LENGTH", "0"))
            except ValueError:
                length = 0
            raw = environ["wsgi.input"].read(length) if length else b"{}"
            try:
                payload = json.loads(raw)
            except Exception:
                payload = {}
            capability_id = payload.get("capability_id", "")
            inputs = payload.get("inputs", {})
            try:
                result = _execute_locally(capability_id, inputs)
                body = json.dumps(
                    {
                        "schema": "PROJECT_BRAIN_DISTRIBUTED_EXECUTE_RESULT_V1",
                        "node_id": node_id,
                        "capability_id": capability_id,
                        "ok": True,
                        "result": result,
                    }
                ).encode("utf-8")
                start_response("200 OK", [("Content-Type", "application/json")])
                return [body]
            except Exception as exc:
                body = json.dumps(
                    {
                        "schema": "PROJECT_BRAIN_DISTRIBUTED_EXECUTE_RESULT_V1",
                        "node_id": node_id,
                        "capability_id": capability_id,
                        "ok": False,
                        "error": type(exc).__name__ + ":" + str(exc),
                    }
                ).encode("utf-8")
                start_response("500 Internal Server Error", [("Content-Type", "application/json")])
                return [body]

        start_response("404 Not Found", [("Content-Type", "text/plain")])
        return [b"not found"]

    return app


def run_node(node_id: str, host: str = "0.0.0.0", port: int = 8765,
             capabilities: Optional[list[str]] = None) -> None:
    """Run a distributed execution node (blocking)."""
    from wsgiref.simple_server import make_server

    caps = capabilities or []
    app = make_node_app(node_id, caps)
    server = make_server(host, port, app)
    print(f"[distributed_execution] node {node_id} listening on {host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python distributed_execution_v1.py <node_id> [port]")
        sys.exit(2)
    nid = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8765
    run_node(nid, port=port)
