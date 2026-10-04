#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse
import urllib.request

from canonical.runtime import root1_contrastive_semantic_gate_v1 as gate

SCHEMA = "PROJECT_BRAIN_ROOT1_CONTRASTIVE_SEMANTIC_CANDIDATE_RUNNER_V1"


class CandidateRunnerError(RuntimeError):
    pass


def verify_subject(path: str | Path, *, expected_sha256: str, expected_bytes: int) -> dict:
    model = Path(path)
    if not model.is_file():
        raise CandidateRunnerError("MODEL_FILE_REQUIRED")
    size = model.stat().st_size
    if size != int(expected_bytes):
        raise CandidateRunnerError("MODEL_SIZE_MISMATCH")
    h = hashlib.sha256()
    with model.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    digest = h.hexdigest()
    if digest.lower() != str(expected_sha256).lower():
        raise CandidateRunnerError("MODEL_SHA256_MISMATCH")
    return {"path": str(model), "bytes": size, "sha256": digest}


def _local_endpoint(url: str) -> str:
    parsed = urlparse(str(url))
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"}:
        raise CandidateRunnerError("LOCALHOST_HTTP_ENDPOINT_REQUIRED")
    return str(url)


def _prompt(probe: gate.Probe) -> str:
    if probe.source:
        return f"{probe.prompt}\n\nSource:\n{probe.source}"
    return probe.prompt


def chat(
    endpoint: str,
    *,
    model_alias: str,
    prompt: str,
    seed: int,
    temperature: float = 0.0,
    max_tokens: int = 256,
) -> str:
    endpoint = _local_endpoint(endpoint)
    payload = {
        "model": model_alias,
        "messages": [
            {
                "role": "system",
                "content": "Follow the transformation request exactly. Return only the requested final text.",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": float(temperature),
        "seed": int(seed),
        "max_tokens": int(max_tokens),
        "stream": False,
    }
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=300) as response:
        if response.status != 200:
            raise CandidateRunnerError(f"MODEL_HTTP_STATUS_{response.status}")
        data = json.loads(response.read().decode("utf-8", "replace"))
    choices = data.get("choices")
    if not isinstance(choices, list) or len(choices) != 1:
        raise CandidateRunnerError("MODEL_RESPONSE_CHOICES_INVALID")
    message = choices[0].get("message") or {}
    output = str(message.get("content") or "").strip()
    if not output:
        raise CandidateRunnerError("MODEL_RESPONSE_EMPTY")
    return output


def run_candidate(
    *,
    model_path: str | Path,
    expected_sha256: str,
    expected_bytes: int,
    model_alias: str,
    endpoint: str = "http://127.0.0.1:8080/v1/chat/completions",
    seed_base: int = 424200,
    temperature: float = 0.0,
    max_tokens: int = 256,
) -> dict:
    subject = verify_subject(
        model_path,
        expected_sha256=expected_sha256,
        expected_bytes=expected_bytes,
    )
    _local_endpoint(endpoint)
    outputs: dict[str, str] = {}
    for index, probe in enumerate(gate.frozen_probes()):
        outputs[probe.probe_id] = chat(
            endpoint,
            model_alias=model_alias,
            prompt=_prompt(probe),
            seed=seed_base + index,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    verdict = gate.evaluate_suite(outputs)
    return {
        "schema": SCHEMA,
        "status": verdict["status"],
        "subject": subject,
        "model_alias": model_alias,
        "endpoint_scope": "LOCALHOST_ONLY",
        "generation": {
            "attempts_per_probe": 1,
            "seed_base": seed_base,
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
        "outputs": outputs,
        "gate_verdict": verdict,
        "terminal_case_exposure": 0,
        "incremental_spend_usd": 0,
        "acceptance_credit": 0,
        "capability_credit": 0,
        "hard_nonclaim": "PASS_QUALIFIES_ONLY_THE_FROZEN_BOUNDED_NONTERMINAL_SEMANTIC_GATE; IT_DOES_NOT_PROVE_OPUS_PARITY_OR_LIVEBENCH_TERMINAL_SUCCESS",
    }


def run(args: dict | None = None, root=None) -> dict:
    values = args or {}
    return run_candidate(
        model_path=values["model_path"],
        expected_sha256=values["expected_sha256"],
        expected_bytes=int(values["expected_bytes"]),
        model_alias=str(values["model_alias"]),
        endpoint=str(
            values.get("endpoint")
            or "http://127.0.0.1:8080/v1/chat/completions"
        ),
        seed_base=int(values.get("seed_base", 424200)),
        temperature=float(values.get("temperature", 0.0)),
        max_tokens=int(values.get("max_tokens", 256)),
    )
