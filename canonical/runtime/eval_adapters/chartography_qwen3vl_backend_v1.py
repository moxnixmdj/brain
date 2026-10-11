#!/usr/bin/env python3
"""Offline Brain-owned wrapper for an already-local Qwen3-VL llama.cpp subject.

The program accepts one JSON request on stdin and returns one JSON response on
stdout. It performs no download, provider call, remote image fetch, or fallback.
Model/runtime bytes must already exist locally and are selected only through
explicit environment paths supplied by the verified execution carrier.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

REQUEST_SCHEMA = "PROJECT_BRAIN_CHARTOGRAPHY_MULTIMODAL_REQUEST_V1"
RESPONSE_SCHEMA = "PROJECT_BRAIN_CHARTOGRAPHY_MULTIMODAL_RESPONSE_V1"


def fail(reason: str) -> "NoReturn":
    raise RuntimeError(reason)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def local_file(env_name: str) -> Path:
    raw = os.environ.get(env_name, "").strip()
    if not raw:
        fail(env_name + "_REQUIRED")
    p = Path(raw).resolve()
    if not p.is_file():
        fail(env_name + "_MISSING")
    return p


def image_suffix(data: bytes) -> str:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if data.startswith(b"BM"):
        return ".bmp"
    fail("UNSUPPORTED_IMAGE_BYTES")


def main() -> int:
    raw = sys.stdin.read()
    request = json.loads(raw)
    if not isinstance(request, dict):
        fail("REQUEST_NOT_OBJECT")
    if request.get("schema") != REQUEST_SCHEMA:
        fail("REQUEST_SCHEMA_INVALID")

    backend_id = str(request.get("backend_id") or "").strip()
    question = request.get("question")
    qsha = str(request.get("question_sha256") or "").lower()
    isha = str(request.get("image_sha256") or "").lower()
    image_b64 = request.get("image_bytes_b64")
    if not backend_id:
        fail("BACKEND_ID_REQUIRED")
    if not isinstance(question, str) or not question:
        fail("QUESTION_REQUIRED")
    if not isinstance(image_b64, str) or not image_b64:
        fail("IMAGE_BYTES_REQUIRED")
    if sha256(question.encode("utf-8")) != qsha:
        fail("QUESTION_HASH_MISMATCH")
    try:
        image = base64.b64decode(image_b64, validate=True)
    except Exception as exc:
        raise RuntimeError("IMAGE_BASE64_INVALID") from exc
    if sha256(image) != isha:
        fail("IMAGE_HASH_MISMATCH")

    cli = local_file("PROJECT_BRAIN_LLAMA_MTMD_CLI")
    model = local_file("PROJECT_BRAIN_QWEN_MODEL")
    mmproj = local_file("PROJECT_BRAIN_QWEN_MMPROJ")

    with tempfile.TemporaryDirectory(prefix="brain-chartography-") as td:
        image_path = Path(td) / ("input" + image_suffix(image))
        image_path.write_bytes(image)
        cmd = [
            str(cli),
            "-m", str(model),
            "--mmproj", str(mmproj),
            "--no-mmproj-offload",
            "--image", str(image_path),
            "-c", "4096",
            "--image-min-tokens", "1024",
            "--image-max-tokens", "1024",
            "-p", question,
            "-n", "256",
            "-t", str(max(1, min(int(os.environ.get("PROJECT_BRAIN_QWEN_THREADS", "4")), 8))),
        ]
        env = {}
        for key in ("PATH", "HOME", "TMPDIR", "TEMP", "TMP", "LD_LIBRARY_PATH"):
            if key in os.environ:
                env[key] = os.environ[key]
        env["PROJECT_BRAIN_OFFLINE"] = "1"
        proc = subprocess.run(
            cmd,
            text=True,
            capture_output=True,
            timeout=float(os.environ.get("PROJECT_BRAIN_QWEN_TIMEOUT_S", "180")),
            env=env,
            check=False,
        )
    if proc.returncode != 0:
        fail("LOCAL_MULTIMODAL_EXECUTION_FAILED:" + proc.stderr[-1600:].replace("\n", " "))
    answer = proc.stdout.strip()
    if not answer:
        fail("LOCAL_MULTIMODAL_ANSWER_EMPTY")

    response = {
        "schema": RESPONSE_SCHEMA,
        "backend_id": backend_id,
        "question_sha256": qsha,
        "image_sha256": isha,
        "answer": answer,
        "fallback_used": False,
        "incremental_spend_usd": 0,
        "network_required": False,
        "carrier": "LOCAL_PINNED_LLAMA_CPP_QWEN3VL",
    }
    sys.stdout.write(json.dumps(response, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        sys.stderr.write(type(exc).__name__ + ":" + str(exc) + "\n")
        raise SystemExit(1)
