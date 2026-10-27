#!/usr/bin/env python3
"""Orchestration — verified bridge enumeration, insanely fast only-right-way.

Hidden kernel: canonical/runtime/bridge_enumeration_v1.py (457 lines, enumerate
producers×artifacts, execute each, keep EMITS_VERIFIED survivors, classify rest).

Why this is max: literal token matching has 11 edges on 73 caps (89→93 now 17).
The missing bridges are execution facts — run the producer, check bytes with
independent stdlib parser, publish table. No guessing, no model, $0, fail-closed.
"""
from __future__ import annotations
import hashlib
import json
import pathlib
from typing import Any

SCHEMA = "PROJECT_BRAIN_ORCHESTRATION_BRIDGE_ENUMERATION_V1"
CAPABILITY_ID = "orchestration.verify.bridge_enumeration.v1"
PROVIDES = ["orchestration.bridge_table.verified", "orchestration.emits.verified"]
REQUIRES: list[str] = []

REPO = pathlib.Path(__file__).resolve().parents[3]

def _safe_output(root: pathlib.Path, raw: str | None) -> pathlib.Path:
    p = (root / str(raw or "canonical/tmp_bridge_enumeration.json")).resolve()
    if p == root or root not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

def _load_bridge():
    import canonical.runtime.bridge_enumeration_v1 as mod
    return mod

def run(args: dict[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    repo = pathlib.Path(root).resolve()
    output = _safe_output(repo, args.get("output_path"))
    bridge_mod = _load_bridge()
    registry = args.get("registry") or "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
    report = bridge_mod.enumerate_bridges(registry)
    # Keep only execution-verified rows; rest is already classified in report
    artifact = {
        "schema": SCHEMA,
        "capability_id": CAPABILITY_ID,
        "registry": registry,
        "counts": report["counts"],
        "emits_verified": report["emits_verified"],
        "bridge_verified": report["bridge_verified"],
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
        "verified": len(report["emits_verified"]) >= 1,
    }
    raw = json.dumps(artifact, sort_keys=True, separators=(",", ":")).encode()
    output.write_bytes(raw)
    return {
        "adapter": "orchestration_bridge_enumeration_v1",
        "output_path": str(output.relative_to(repo)),
        "output_sha256": hashlib.sha256(raw).hexdigest(),
        "output_verified": artifact["verified"],
        "emits_verified": len(report["emits_verified"]),
        "bridge_verified": len(report["bridge_verified"]),
        "counts": report["counts"],
        "verified": artifact["verified"],
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }
