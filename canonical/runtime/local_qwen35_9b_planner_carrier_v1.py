from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess
import time
import urllib.request
from typing import Any, Mapping

MODEL_LABEL = "Qwen3.5-9B-M-Q4_K_M-local"
BACKEND = "LOCAL_LLAMA_SERVER"
MODEL_FILE = "Qwen3.5-9B-M-TS-Q4_K_M.gguf"
MODEL_BYTES = 5_060_174_144
MODEL_SHA256 = "f41c0a0c0e43bf721fb2da29374cd1a97271bac0bab08a9dc42964525e82350c"
LLAMA_CPP_COMMIT = "bec4772f6a2527d371557b5d2032641e5ff7619c"

REQUEST_SCHEMA = "PROJECT_BRAIN_EXTERNAL_TOOL_REQUEST_V1"
RESPONSE_SCHEMA = "PROJECT_BRAIN_EXTERNAL_TOOL_RESPONSE_V1"


class LocalPlannerCarrierError(RuntimeError):
    pass


def _sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(8 * 1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _git_head(repo: pathlib.Path) -> str:
    cp = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        text=True,
        capture_output=True,
        check=False,
    )
    if cp.returncode != 0:
        raise LocalPlannerCarrierError("LLAMA_CPP_GIT_HEAD_UNAVAILABLE")
    return cp.stdout.strip()


def verify_assets(
    *,
    model_path: str | pathlib.Path,
    llama_repo: str | pathlib.Path,
    server_binary: str | pathlib.Path | None = None,
) -> dict[str, Any]:
    model = pathlib.Path(model_path).resolve(strict=True)
    repo = pathlib.Path(llama_repo).resolve(strict=True)
    server = (
        pathlib.Path(server_binary).resolve(strict=True)
        if server_binary is not None
        else (repo / "build" / "bin" / "llama-server").resolve(strict=True)
    )
    if model.name != MODEL_FILE:
        raise LocalPlannerCarrierError("MODEL_FILENAME_MISMATCH")
    if model.stat().st_size != MODEL_BYTES:
        raise LocalPlannerCarrierError("MODEL_BYTE_COUNT_MISMATCH")
    observed_sha = _sha256_file(model)
    if observed_sha != MODEL_SHA256:
        raise LocalPlannerCarrierError("MODEL_SHA256_MISMATCH")
    observed_commit = _git_head(repo)
    if observed_commit != LLAMA_CPP_COMMIT:
        raise LocalPlannerCarrierError("LLAMA_CPP_COMMIT_MISMATCH")
    if repo != server and repo not in server.parents:
        raise LocalPlannerCarrierError("LLAMA_SERVER_BINARY_OUTSIDE_PINNED_REPO")
    if not server.is_file():
        raise LocalPlannerCarrierError("LLAMA_SERVER_BINARY_MISSING")
    return {
        "model_path": str(model),
        "model_file": MODEL_FILE,
        "model_bytes": MODEL_BYTES,
        "model_sha256": observed_sha,
        "llama_cpp_repo": str(repo),
        "llama_cpp_commit": observed_commit,
        "llama_server_binary": str(server),
    }


def launch_server(
    assets: Mapping[str, Any],
    *,
    host: str = "127.0.0.1",
    port: int = 8080,
    context_tokens: int = 8192,
    threads: int = 4,
) -> subprocess.Popen:
    if host != "127.0.0.1":
        raise LocalPlannerCarrierError("NON_LOOPBACK_SERVER_HOST_FORBIDDEN")
    args = [
        str(assets["llama_server_binary"]),
        "-m",
        str(assets["model_path"]),
        "--host",
        host,
        "--port",
        str(int(port)),
        "-c",
        str(int(context_tokens)),
        "-t",
        str(int(threads)),
        "--parallel",
        "1",
        "--no-webui",
    ]
    return subprocess.Popen(
        args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=False,
    )


def wait_ready(*, host: str = "127.0.0.1", port: int = 8080, timeout_s: float = 120.0) -> None:
    if host != "127.0.0.1":
        raise LocalPlannerCarrierError("NON_LOOPBACK_SERVER_HOST_FORBIDDEN")
    deadline = time.monotonic() + float(timeout_s)
    last = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(
                f"http://{host}:{int(port)}/health",
                timeout=2,
            ) as r:
                if 200 <= int(r.status) < 300:
                    return
        except Exception as exc:
            last = type(exc).__name__
        time.sleep(0.1)
    raise LocalPlannerCarrierError("LLAMA_SERVER_NOT_READY:" + str(last or "UNKNOWN"))


def planner(
    *,
    server: str,
    prompt: str,
    assets: Mapping[str, Any],
    timeout_s: float,
) -> dict[str, Any]:
    if not server.startswith("http://127.0.0.1:"):
        raise LocalPlannerCarrierError("PLANNER_SERVER_NOT_LOOPBACK")
    body = json.dumps(
        {
            "model": "local",
            "messages": [{"role": "user", "content": str(prompt)}],
            "temperature": 0.1,
            "max_tokens": 1024,
            "stream": False,
        },
        separators=(",", ":"),
    ).encode("utf-8")
    req = urllib.request.Request(
        server.rstrip("/") + "/v1/chat/completions",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t = time.monotonic()
    with urllib.request.urlopen(req, timeout=float(timeout_s)) as r:
        obj = json.loads(r.read(4_000_000).decode("utf-8"))
    msg = ((obj.get("choices") or [{}])[0].get("message") or {})
    text = msg.get("content")
    if not isinstance(text, str) or not text.strip():
        text = msg.get("reasoning_content")
    if not isinstance(text, str) or not text.strip():
        raise LocalPlannerCarrierError("LOCAL_PLANNER_EMPTY")
    return {
        "text": text,
        "model": MODEL_LABEL,
        "backend": BACKEND,
        "model_sha256": assets["model_sha256"],
        "model_bytes": assets["model_bytes"],
        "llama_cpp_commit": assets["llama_cpp_commit"],
        "duration_s": round(time.monotonic() - t, 3),
        "errors": [],
    }


def _canonical_request_hash(request: Mapping[str, Any]) -> str:
    base = {k: v for k, v in request.items() if k != "request_sha256"}
    raw = json.dumps(
        base,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _atomic_json(path: pathlib.Path, value: Mapping[str, Any]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def serve_bridge(
    *,
    bridge_dir: str | pathlib.Path,
    task_id: str,
    server: str,
    assets: Mapping[str, Any],
    idle_sleep_s: float = 0.02,
) -> None:
    bridge = pathlib.Path(bridge_dir).resolve()
    if bridge.name != task_id or bridge.is_symlink():
        raise LocalPlannerCarrierError("BRIDGE_TASK_DIRECTORY_IDENTITY_MISMATCH")
    bridge.mkdir(parents=True, exist_ok=True)
    log = bridge / "LOCAL_QWEN35_9B_PLANNER_CARRIER_LOG.jsonl"
    while True:
        for request_path in sorted(bridge.glob("*.request.json")):
            sha = request_path.name.split(".", 1)[0]
            response_path = bridge / (sha + ".response.json")
            if response_path.exists():
                continue
            req: dict[str, Any] = {}
            try:
                req = json.loads(request_path.read_text(encoding="utf-8"))
                if req.get("schema") != REQUEST_SCHEMA:
                    raise LocalPlannerCarrierError("REQUEST_SCHEMA_INVALID")
                if req.get("task_id") != task_id:
                    raise LocalPlannerCarrierError("REQUEST_TASK_ID_MISMATCH")
                if req.get("kind") != "planner":
                    raise LocalPlannerCarrierError("KIND_NOT_ALLOWED:" + str(req.get("kind")))
                calc = _canonical_request_hash(req)
                if calc != sha or req.get("request_sha256") != sha:
                    raise LocalPlannerCarrierError("REQUEST_HASH_MISMATCH")
                payload = req.get("payload")
                if not isinstance(payload, Mapping):
                    raise LocalPlannerCarrierError("PLANNER_PAYLOAD_INVALID")
                result = planner(
                    server=server,
                    prompt=str(payload.get("prompt") or ""),
                    assets=assets,
                    timeout_s=float(payload.get("timeout_s") or 20),
                )
                response = {
                    "schema": RESPONSE_SCHEMA,
                    "request_sha256": sha,
                    "kind": "planner",
                    "agent_id": req.get("agent_id"),
                    "task_id": task_id,
                    "status": "ok",
                    "result": result,
                }
                record = {
                    "request_sha256": sha,
                    "kind": "planner",
                    "status": "ok",
                    "planner_model": result["model"],
                    "planner_backend": result["backend"],
                    "model_sha256": result["model_sha256"],
                    "llama_cpp_commit": result["llama_cpp_commit"],
                }
            except Exception as exc:
                response = {
                    "schema": RESPONSE_SCHEMA,
                    "request_sha256": sha,
                    "kind": req.get("kind"),
                    "agent_id": req.get("agent_id"),
                    "task_id": req.get("task_id"),
                    "status": "error",
                    "result": {"error": type(exc).__name__ + ":" + str(exc)},
                }
                record = {
                    "request_sha256": sha,
                    "kind": req.get("kind"),
                    "status": "error",
                    "error": type(exc).__name__ + ":" + str(exc),
                }
            _atomic_json(response_path, response)
            with log.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, sort_keys=True) + "\n")
        time.sleep(float(idle_sleep_s))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--llama-repo", required=True)
    ap.add_argument("--server-binary")
    ap.add_argument("--bridge-dir", required=True)
    ap.add_argument("--task-id", required=True)
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--context", type=int, default=8192)
    args = ap.parse_args()

    assets = verify_assets(
        model_path=args.model,
        llama_repo=args.llama_repo,
        server_binary=args.server_binary,
    )
    proc = launch_server(
        assets,
        port=args.port,
        context_tokens=args.context,
        threads=args.threads,
    )
    try:
        wait_ready(port=args.port)
        serve_bridge(
            bridge_dir=args.bridge_dir,
            task_id=args.task_id,
            server=f"http://127.0.0.1:{args.port}",
            assets=assets,
        )
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    main()
