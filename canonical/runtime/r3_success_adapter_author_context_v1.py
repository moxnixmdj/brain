"""Redacted structural context for R3 success-adapter patch authors.

This module exposes only bounded protocol shape from a retained success proof and
replay capsule. It never exposes raw goal text, arbitrary request values,
checkpoint paths, acceptance payloads, model valuations, verifier source, or
secret-like strings.
"""
from __future__ import annotations

from hashlib import sha256
import json
import re
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_R3_SUCCESS_ADAPTER_AUTHOR_CONTEXT_V1"
_SAFE_SYMBOL = re.compile(r"^[A-Za-z0-9_.:/=-]{1,160}$")
_ALLOWED_REQUEST_KEYS = (
    "task_id",
    "goal",
    "initial_facts",
    "target_effects",
    "allowed_capability_ids",
    "capability_inputs",
    "decision_payload",
    "execution_problem",
    "policy_execution_binding",
    "goal_satisfaction_binding",
    "episode_id",
    "scope_id",
)
_ALLOWED_MATERIAL_KEYS = (
    "source_schema",
    "source_status",
    "task_id",
    "selected_plan",
    "verified_target_effects",
    "controller_checkpoint",
    "execution",
    "cognition_dependency_class",
    "model_dependency_count",
    "semantic_acceptance_complete",
    "raw_goal_sha256",
    "raw_task_contract_sha256",
    "raw_acceptance_obligation_count",
    "accepted_raw_obligation_ids",
    "compiled_capability_id",
    "raw_goal_acceptance",
)


def _canon(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _digest(value: Any) -> str:
    return "sha256:" + sha256(_canon(value).encode("utf-8")).hexdigest()


def context_sha256(value: Mapping[str, Any]) -> str:
    base = dict(value)
    base.pop("context_sha256", None)
    return _digest(base)


def _symbol(value: Any) -> str | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    if _SAFE_SYMBOL.fullmatch(raw):
        return raw
    return "sha256:" + sha256(raw.encode("utf-8")).hexdigest()


def _shape(value: Any) -> dict[str, Any]:
    if value is None:
        return {"type": "null"}
    if isinstance(value, bool):
        return {"type": "bool"}
    if isinstance(value, int) and not isinstance(value, bool):
        return {"type": "int"}
    if isinstance(value, float):
        return {"type": "float"}
    if isinstance(value, str):
        return {"type": "string"}
    if isinstance(value, Mapping):
        return {"type": "object", "size": len(value)}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return {"type": "array", "size": len(value)}
    return {"type": type(value).__name__}


def compile_context(
    proof_context: Mapping[str, Any],
    replay_context: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(proof_context, Mapping) or not isinstance(replay_context, Mapping):
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "reason": "PROOF_AND_REPLAY_CONTEXT_REQUIRED",
            "candidate_generation_authority": False,
        }

    material = proof_context.get("material")
    context = replay_context.get("context")
    if not isinstance(material, Mapping) or not isinstance(context, Mapping):
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "reason": "PROOF_OR_REPLAY_CONTEXT_SHAPE_INVALID",
            "candidate_generation_authority": False,
        }

    raw_request = context.get("request")
    request = raw_request if isinstance(raw_request, Mapping) else {}
    selected = material.get("selected_plan")
    execution = material.get("execution")
    accepted_ids = material.get("accepted_raw_obligation_ids")

    selected_symbols = []
    if isinstance(selected, Sequence) and not isinstance(selected, (str, bytes, bytearray)):
        selected_symbols = [
            x for x in (_symbol(v) for v in selected) if isinstance(x, str)
        ]

    execution_rows = []
    if isinstance(execution, Sequence) and not isinstance(execution, (str, bytes, bytearray)):
        for row in execution:
            if not isinstance(row, Mapping):
                continue
            execution_rows.append({
                "capability_id": _symbol(row.get("capability_id")),
                "pass": row.get("pass") is True,
                "status": _symbol(row.get("status")),
                "composition_digest_present": bool(
                    str(row.get("composition_capsule_head_hash") or "").strip()
                ),
            })

    request_keys = [key for key in _ALLOWED_REQUEST_KEYS if key in request]
    request_shape = {key: _shape(request.get(key)) for key in request_keys}
    material_keys = [key for key in _ALLOWED_MATERIAL_KEYS if key in material]

    out = {
        "schema": SCHEMA,
        "status": "PASS__REDACTED_ADAPTER_AUTHOR_CONTEXT_READY",
        "pass": True,
        "replay": {
            "mode": _symbol(context.get("mode")),
            "request_keys": request_keys,
            "request_shape": request_shape,
        },
        "proof": {
            "material_keys": material_keys,
            "source_schema": _symbol(material.get("source_schema")),
            "source_status": _symbol(material.get("source_status")),
            "selected_plan": selected_symbols,
            "selected_plan_count": len(selected_symbols),
            "verified_target_effect_count": (
                len(material.get("verified_target_effects"))
                if isinstance(material.get("verified_target_effects"), Sequence)
                and not isinstance(material.get("verified_target_effects"), (str, bytes, bytearray))
                else 0
            ),
            "controller_checkpoint_present": isinstance(
                material.get("controller_checkpoint"), Mapping
            ),
            "execution_rows": execution_rows,
            "execution_count": len(execution_rows),
            "cognition_dependency_class": _symbol(
                material.get("cognition_dependency_class")
            ),
            "model_dependency_count": (
                material.get("model_dependency_count")
                if isinstance(material.get("model_dependency_count"), int)
                and not isinstance(material.get("model_dependency_count"), bool)
                else None
            ),
            "semantic_acceptance_complete": (
                material.get("semantic_acceptance_complete") is True
            ),
            "raw_goal_digest_present": bool(
                str(material.get("raw_goal_sha256") or "").strip()
            ),
            "raw_task_contract_digest_present": bool(
                str(material.get("raw_task_contract_sha256") or "").strip()
            ),
            "raw_acceptance_obligation_count": (
                material.get("raw_acceptance_obligation_count")
                if isinstance(material.get("raw_acceptance_obligation_count"), int)
                and not isinstance(material.get("raw_acceptance_obligation_count"), bool)
                else None
            ),
            "accepted_raw_obligation_id_count": (
                len(accepted_ids)
                if isinstance(accepted_ids, Sequence)
                and not isinstance(accepted_ids, (str, bytes, bytearray))
                else 0
            ),
            "compiled_capability_id": _symbol(
                material.get("compiled_capability_id")
            ),
            "raw_goal_acceptance_present": isinstance(
                material.get("raw_goal_acceptance"), Mapping
            ),
        },
        "bindings": {
            "proof_capsule_sha256": _symbol(
                proof_context.get("proof_capsule_sha256")
            ),
            "replay_capsule_sha256": _symbol(
                replay_context.get("replay_capsule_sha256")
            ),
        },
        "redaction_policy": {
            "raw_request_values_exposed": False,
            "raw_goal_text_exposed": False,
            "checkpoint_path_exposed": False,
            "acceptance_payload_exposed": False,
            "model_valuations_exposed": False,
            "verifier_source_exposed": False,
            "only_fixed_protocol_keys_and_sanitized_symbols_exposed": True,
        },
        "candidate_generation_authority": True,
        "source_write_authority": False,
        "verification_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
    }
    out["context_sha256"] = context_sha256(out)
    return out
