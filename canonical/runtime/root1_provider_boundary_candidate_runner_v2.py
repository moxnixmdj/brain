#!/usr/bin/env python3
"""Exact-subject paired runner for Root1 provider-boundary ablation V2."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from canonical.runtime import root1_contrastive_semantic_candidate_runner_v1 as base_runner
from canonical.runtime import root1_contrastive_semantic_gate_v1 as semantic_gate
from canonical.runtime import root1_provider_boundary_ablation_v2 as boundary

SCHEMA = "PROJECT_BRAIN_ROOT1_PROVIDER_BOUNDARY_CANDIDATE_RUNNER_V2"


def _semantic_prompt(probe: semantic_gate.Probe) -> str:
    if probe.source:
        return f"{probe.prompt}\n\nSource:\n{probe.source}"
    return probe.prompt


def _direct_prompt(probe: semantic_gate.Probe, overlay: str) -> str:
    return (
        _semantic_prompt(probe)
        + "\n\nAdditional formal requirement:\n"
        + str(overlay)
    )


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
) -> dict[str, Any]:
    subject = base_runner.verify_subject(
        model_path,
        expected_sha256=expected_sha256,
        expected_bytes=expected_bytes,
    )
    base_runner._local_endpoint(endpoint)

    cfg = boundary._governance()
    overlays = dict(cfg["formal_overlays"])
    records: dict[str, dict[str, str]] = {}

    for index, probe in enumerate(semantic_gate.frozen_probes()):
        paired_seed = int(seed_base) + index
        seed_output = base_runner.chat(
            endpoint,
            model_alias=model_alias,
            prompt=_semantic_prompt(probe),
            seed=paired_seed,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        direct_output = base_runner.chat(
            endpoint,
            model_alias=model_alias,
            prompt=_direct_prompt(probe, overlays[probe.probe_id]),
            seed=paired_seed,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        records[probe.probe_id] = {
            "seed": seed_output,
            "direct": direct_output,
        }

    verdict = boundary.evaluate(records)
    return {
        "schema": SCHEMA,
        "status": verdict["status"],
        "subject": subject,
        "model_alias": model_alias,
        "endpoint_scope": "LOCALHOST_ONLY",
        "generation": {
            "attempts_per_probe_per_route": 1,
            "paired_seed_base": int(seed_base),
            "temperature": float(temperature),
            "max_tokens": int(max_tokens),
            "semantic_model_calls": len(records),
            "direct_model_calls": len(records),
            "brain_composition_model_calls": 0,
        },
        "records": records,
        "provider_boundary_verdict": verdict,
        "terminal_case_exposure": 0,
        "incremental_spend_usd": 0,
        "acceptance_credit": 0,
        "capability_credit": 0,
        "ownership_credit": 0,
        "hard_nonclaim": (
            "PASS_IS_ONLY_A_BOUNDED_CAUSAL_PROVIDER_BOUNDARY_SIGNAL_FOR_THE_"
            "EXACT_SUBJECT_AND_FROZEN_PUBLIC_NONTERMINAL_PROBES"
        ),
    }


def run(args: dict[str, Any] | None = None, root=None) -> dict[str, Any]:
    values = args or {}
    return run_candidate(
        model_path=values["model_path"],
        expected_sha256=str(values["expected_sha256"]),
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
