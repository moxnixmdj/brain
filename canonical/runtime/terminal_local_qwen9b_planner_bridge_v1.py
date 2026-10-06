#!/usr/bin/env python3
"""Brain-owned local planner bridge for terminal execution.

The bridge serves planner requests only and talks only to a loopback
OpenAI-compatible llama.cpp server. Model/substrate identity is independently
verified by astra_runtime before every terminal planner call; this process also
records the same identities in its response for cross-checking.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess
import time
import urllib.parse
import urllib.request

MODEL_LABEL = "Qwen3.5-9B-M-Q4_K_M-local"
BACKEND_LABEL = "LOCAL_LLAMA_SERVER"
EXPECTED_MODEL_SHA256 = "f41c0a0c0e43bf721fb2da29374cd1a97271bac0bab08a9dc42964525e82350c"
EXPECTED_MODEL_BYTES = 5060174144
EXPECTED_LLAMA_CPP_COMMIT = "bec4772f6a2527d371557b5d2032641e5ff7619c"


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_substrate(model_path: pathlib.Path, llama_cpp_dir: pathlib.Path) -> dict[str, object]:
    model_path = model_path.resolve()
    llama_cpp_dir = llama_cpp_dir.resolve()
    if not model_path.is_file():
        raise RuntimeError("TERMINAL_LOCAL_MODEL_FILE_MISSING")
    size = model_path.stat().st_size
    if size != EXPECTED_MODEL_BYTES:
        raise RuntimeError("TERMINAL_LOCAL_MODEL_BYTES_MISMATCH")
    digest = sha256_file(model_path)
    if digest != EXPECTED_MODEL_SHA256:
        raise RuntimeError("TERMINAL_LOCAL_MODEL_SHA256_MISMATCH")
    try:
        revision = subprocess.check_output(
            ["git", "-C", str(llama_cpp_dir), "rev-parse", "HEAD"],
            text=True,
            timeout=10,
        ).strip().lower()
    except Exception as exc:
        raise RuntimeError("TERMINAL_LLAMA_CPP_REVISION_UNAVAILABLE") from exc
    if revision != EXPECTED_LLAMA_CPP_COMMIT:
        raise RuntimeError("TERMINAL_LLAMA_CPP_REVISION_MISMATCH")
    return {
        "model": MODEL_LABEL,
        "backend": BACKEND_LABEL,
        "model_sha256": digest,
        "model_bytes": size,
        "llama_cpp_commit": revision,
    }


def atomic_write(path: pathlib.Path, payload: dict[str, object]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def loopback_server_url(raw: str) -> str:
    parsed = urllib.parse.urlsplit(str(raw))
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"}:
        raise RuntimeError("TERMINAL_PLANNER_SERVER_NOT_LOOPBACK")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise RuntimeError("TERMINAL_PLANNER_SERVER_URL_INVALID")
    return urllib.parse.urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", "")
    )


def planner(server: str, payload: dict[str, object], provenance: dict[str, object]) -> dict[str, object]:
    body = json.dumps(
        {
            "model": "local",
            "messages": [{"role": "user", "content": str(payload.get("prompt") or "")}],
            "temperature": 0.1,
            "max_tokens": 1024,
            "stream": False,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        server.rstrip("/") + "/v1/chat/completions",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.monotonic()
    with urllib.request.urlopen(req, timeout=240) as response:
        obj = json.loads(response.read(3_000_000).decode("utf-8"))
    message = ((obj.get("choices") or [{}])[0].get("message") or {})
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        content = message.get("reasoning_content")
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("TERMINAL_LOCAL_PLANNER_EMPTY")
    return {
        "text": content,
        "duration_s": round(time.monotonic() - t0, 3),
        "errors": [],
        "transport": "BRAIN_OWNED_LOOPBACK_PLANNER_BRIDGE_V1",
        **provenance,
    }


def handle(server: str, request: dict[str, object], provenance: dict[str, object]) -> dict[str, object]:
    kind = str(request.get("kind") or "")
    if kind != "planner":
        raise RuntimeError("TERMINAL_LOCAL_BRIDGE_KIND_REJECTED:" + kind)
    payload = request.get("payload")
    if not isinstance(payload, dict):
        raise RuntimeError("TERMINAL_LOCAL_BRIDGE_PAYLOAD_INVALID")
    models = payload.get("models")
    if models != ["local"]:
        raise RuntimeError("TERMINAL_LOCAL_BRIDGE_MODEL_ROUTE_INVALID")
    return planner(server, payload, provenance)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True)
    parser.add_argument("--server", default="http://127.0.0.1:8080")
    parser.add_argument("--model-path", required=True)
    parser.add_argument("--llama-cpp-dir", required=True)
    args = parser.parse_args()

    directory = pathlib.Path(args.dir).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    server = loopback_server_url(args.server)
    provenance = verify_substrate(
        pathlib.Path(args.model_path),
        pathlib.Path(args.llama_cpp_dir),
    )
    log_path = directory / "TERMINAL_LOCAL_PLANNER_BRIDGE_LOG.jsonl"

    while True:
        for request_path in sorted(directory.glob("*.request.json")):
            request_sha = request_path.name.split(".", 1)[0]
            response_path = directory / (request_sha + ".response.json")
            if response_path.exists():
                continue
            request = None
            try:
                request = json.loads(request_path.read_text(encoding="utf-8"))
                base = {k: v for k, v in request.items() if k != "request_sha256"}
                observed_sha = hashlib.sha256(
                    json.dumps(
                        base,
                        sort_keys=True,
                        separators=(",", ":"),
                        ensure_ascii=False,
                    ).encode("utf-8")
                ).hexdigest()
                if observed_sha != request_sha or request.get("request_sha256") != request_sha:
                    raise RuntimeError("TERMINAL_LOCAL_BRIDGE_REQUEST_HASH_MISMATCH")
                result = handle(server, request, provenance)
                response = {
                    "schema": "PROJECT_BRAIN_EXTERNAL_TOOL_RESPONSE_V1",
                    "request_sha256": request_sha,
                    "kind": request.get("kind"),
                    "agent_id": request.get("agent_id"),
                    "task_id": request.get("task_id"),
                    "status": "ok",
                    "result": result,
                }
                record = {
                    "request_sha256": request_sha,
                    "kind": request.get("kind"),
                    "status": "ok",
                    **provenance,
                }
            except Exception as exc:
                response = {
                    "schema": "PROJECT_BRAIN_EXTERNAL_TOOL_RESPONSE_V1",
                    "request_sha256": request_sha,
                    "kind": request.get("kind") if isinstance(request, dict) else None,
                    "agent_id": request.get("agent_id") if isinstance(request, dict) else None,
                    "task_id": request.get("task_id") if isinstance(request, dict) else None,
                    "status": "error",
                    "result": {"error": type(exc).__name__ + ":" + str(exc)},
                }
                record = {
                    "request_sha256": request_sha,
                    "kind": response.get("kind"),
                    "status": "error",
                    "error": type(exc).__name__ + ":" + str(exc),
                }
            atomic_write(response_path, response)
            with log_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, sort_keys=True) + "\n")
        time.sleep(0.02)


if __name__ == "__main__":
    main()
