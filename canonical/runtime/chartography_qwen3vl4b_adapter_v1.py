"""Fail-closed local Chartography image+prompt adapter for the pinned Qwen3-VL subject.

This module is transport only. It binds the exact model/projector subject already
proved to fit the zero-cost public runner and produces a content-addressed
execution receipt. It never sees a golden answer and grants no benchmark,
acceptance, capability, ownership, promotion, or terminal credit.
"""
from __future__ import annotations

import hashlib
import subprocess
import time
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_CHARTOGRAPHY_QWEN3VL4B_ADAPTER_V1"

MODEL_SHA256 = "66358cb18bb6b3b1b6675aa412c7a88ef01d228f481184d13668e5201c730a0a"
PROJECTOR_SHA256 = "30ba2c7dd3127a4561b6cba9d13d0f711c91bdb38742e2f56d73c8cb596bd06d"
LLAMA_CPP_COMMIT = "a7fb71fab83b474a0892b9a05aaa3a8ddca2729b"

_ALLOWED_SAMPLE_KEYS = {"task_id", "prompt", "chart_path"}


class ChartographyAdapterError(ValueError):
    pass


def _sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def validate_sample(sample: Mapping[str, Any]) -> dict[str, str]:
    if not isinstance(sample, Mapping):
        raise ChartographyAdapterError("SAMPLE_MAPPING_REQUIRED")
    extra = set(sample) - _ALLOWED_SAMPLE_KEYS
    if extra:
        raise ChartographyAdapterError(
            "UNMODELED_OR_LEAKY_SAMPLE_FIELDS:" + ",".join(sorted(extra))
        )
    out: dict[str, str] = {}
    for key in ("task_id", "prompt", "chart_path"):
        value = sample.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ChartographyAdapterError("SAMPLE_FIELD_INVALID:" + key)
        out[key] = value.strip()
    return out


def build_command(
    sample: Mapping[str, Any],
    *,
    llama_cli_path: str | Path,
    model_path: str | Path,
    projector_path: str | Path,
    threads: int = 4,
    max_tokens: int = 192,
) -> list[str]:
    clean = validate_sample(sample)
    if not isinstance(threads, int) or threads < 1:
        raise ChartographyAdapterError("THREADS_INVALID")
    if not isinstance(max_tokens, int) or max_tokens < 1:
        raise ChartographyAdapterError("MAX_TOKENS_INVALID")
    return [
        str(llama_cli_path),
        "-m",
        str(model_path),
        "--mmproj",
        str(projector_path),
        "--no-mmproj-offload",
        "--image",
        clean["chart_path"],
        "-p",
        clean["prompt"],
        "-n",
        str(max_tokens),
        "-t",
        str(threads),
    ]


def run_sample(
    sample: Mapping[str, Any],
    *,
    llama_cli_path: str | Path,
    model_path: str | Path,
    projector_path: str | Path,
    threads: int = 4,
    max_tokens: int = 192,
    timeout_seconds: int = 300,
) -> dict[str, Any]:
    clean = validate_sample(sample)
    llama = Path(llama_cli_path)
    model = Path(model_path)
    projector = Path(projector_path)
    image = Path(clean["chart_path"])
    for label, path in (
        ("LLAMA_CLI", llama),
        ("MODEL", model),
        ("PROJECTOR", projector),
        ("IMAGE", image),
    ):
        if not path.is_file():
            raise ChartographyAdapterError(label + "_MISSING")

    model_sha = _sha256_file(model)
    projector_sha = _sha256_file(projector)
    if model_sha != MODEL_SHA256:
        raise ChartographyAdapterError("MODEL_SHA256_MISMATCH")
    if projector_sha != PROJECTOR_SHA256:
        raise ChartographyAdapterError("PROJECTOR_SHA256_MISMATCH")

    command = build_command(
        clean,
        llama_cli_path=llama,
        model_path=model,
        projector_path=projector,
        threads=threads,
        max_tokens=max_tokens,
    )
    started = time.monotonic()
    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ChartographyAdapterError("INFERENCE_TIMEOUT") from exc
    wall = round(time.monotonic() - started, 6)

    if proc.returncode != 0:
        raise ChartographyAdapterError(
            "INFERENCE_NONZERO_EXIT:" + str(proc.returncode)
        )
    completion = proc.stdout.strip()
    if not completion:
        raise ChartographyAdapterError("EMPTY_COMPLETION")

    return {
        "schema": SCHEMA,
        "status": "PASS__PINNED_SUBJECT_IMAGE_PROMPT_EXECUTION",
        "task_id": clean["task_id"],
        "subject": {
            "model_sha256": model_sha,
            "projector_sha256": projector_sha,
            "llama_cpp_commit": LLAMA_CPP_COMMIT,
        },
        "input": {
            "prompt_sha256": _sha256_text(clean["prompt"]),
            "image_sha256": _sha256_file(image),
        },
        "output": {
            "completion": completion,
            "completion_sha256": _sha256_text(completion),
            "stderr_sha256": _sha256_text(proc.stderr),
            "returncode": proc.returncode,
            "wall_seconds": wall,
        },
        "terminal_cases_consumed": 0,
        "incremental_spend_usd": 0,
        "score_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "hard_nonclaim": (
            "TRANSPORT_EXECUTION_ONLY__DOES_NOT_PROVE_CHARTOGRAPHY_GE_89"
        ),
    }
