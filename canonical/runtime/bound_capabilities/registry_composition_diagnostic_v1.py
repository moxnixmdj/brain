"""Shared fail-closed diagnostic for registry-only composition wrappers.

Registry membership is useful for discovery but is not execution evidence.
This helper records availability without crediting any project effect.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
from typing import Any, Mapping, Sequence


def run_diagnostic(args: Mapping[str, Any], root: str | pathlib.Path, *, schema: str,
                   capability_id: str, required: Sequence[str], producers: Sequence[str],
                   default_output: str, adapter: str) -> dict[str, Any]:
    if not isinstance(args, Mapping):
        raise ValueError("ARGS_NOT_OBJECT")
    repo = pathlib.Path(root).resolve()
    registry = (repo / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json").resolve()
    output = (repo / str(args.get("output_path") or default_output)).resolve()
    if output == repo or repo not in output.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    if (output == registry or (output.exists() and registry.exists() and output.samefile(registry))
            or (output.is_file() and output.suffix == ".py")):
        raise RuntimeError("OUTPUT_OVERLAPS_INPUT")
    data = json.loads(registry.read_text(encoding="utf-8"))
    capabilities = data.get("capabilities")
    if not isinstance(capabilities, dict):
        raise ValueError("REGISTRY_CAPABILITIES_INVALID")
    provided = {p for metadata in capabilities.values() if isinstance(metadata, dict)
                for p in metadata.get("provides", [])}
    found = {token: token in provided for token in required}
    producer_found = {capability: capability in capabilities for capability in producers}
    artifact = {"schema": schema, "capability_id": capability_id,
                "required_tokens": list(required), "found": found, "producers": producer_found,
                "registry_components_present": all(found.values()) and all(producer_found.values()),
                "status": "OPEN__NO_TASK_BOUND_COMPOSITION_EXECUTED", "verified": False,
                "model_dependency_count": 0, "incremental_spend_usd": 0}
    raw = json.dumps(artifact, sort_keys=True, separators=(",", ":")).encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(raw)
    return {"adapter": adapter, "output_path": str(output.relative_to(repo)),
            "output_sha256": hashlib.sha256(raw).hexdigest(), "output_verified": output.read_bytes() == raw,
            "status": artifact["status"], "verified": False, "found": found,
            "registry_components_present": artifact["registry_components_present"],
            "model_dependency_count": 0, "incremental_spend_usd": 0}
