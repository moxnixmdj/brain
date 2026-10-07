"""Compile a lossless raw task into a Universal Solver V6 mission.

The raw task and the routing problem are deliberately separated.

Routing:
- candidate capabilities may use coarse effects and untrusted proposal sources;
- the adapter makes no claim that routing effects fully express the task meaning.

Success:
- every non-whitespace raw task segment is preserved by
  lossless_raw_task_contract_v1 as an acceptance obligation;
- the final mission target RAW_TASK_ACCEPTED can be minted only by
  RAW_TASK_ACCEPTANCE_V1;
- that verifier receives the exact candidate SHA-256 through a trusted
  $effect_result value reference;
- every raw obligation needs a candidate-bound acceptance receipt plus separate
  independent verification.

Thus semantic incompleteness in routing may make the mission hard or unresolved,
but cannot silently redefine success.
"""
from __future__ import annotations

from hashlib import sha256
from typing import Any, Mapping, Sequence

from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract
from canonical.runtime.universal_verified_adaptive_solver_v2 import SUCCESS_CONDITIONS

SCHEMA = "PROJECT_BRAIN_LOSSLESS_RAW_TASK_UNIVERSAL_MISSION_V1"
FINAL_CAPABILITY_ID = "RAW_TASK_FINAL_ACCEPTANCE"
FINAL_EFFECT = "RAW_TASK_ACCEPTED"


class RawTaskMissionError(ValueError):
    pass


def _token(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RawTaskMissionError(label + "_INVALID")
    return value.strip()


def compile_mission(
    task_text: str,
    *,
    source_id: str,
    candidate_capabilities: Sequence[Mapping[str, Any]],
    candidate_effect: str,
    candidate_sha256_field: str,
    repo_root: str,
    task_id: str | None = None,
) -> dict[str, Any]:
    try:
        if not isinstance(task_text, str) or not task_text.strip():
            raise RawTaskMissionError("TASK_TEXT_REQUIRED")
        source_id = _token(source_id, "SOURCE_ID")
        candidate_effect = _token(candidate_effect, "CANDIDATE_EFFECT")
        candidate_sha256_field = _token(candidate_sha256_field, "CANDIDATE_SHA256_FIELD")
        repo_root = _token(repo_root, "REPO_ROOT")

        if not isinstance(candidate_capabilities, Sequence) or isinstance(
            candidate_capabilities, (str, bytes, bytearray)
        ):
            raise RawTaskMissionError("CANDIDATE_CAPABILITIES_INVALID")
        caps = []
        ids = set()
        providers = []
        for i, row in enumerate(candidate_capabilities):
            if not isinstance(row, Mapping):
                raise RawTaskMissionError("CANDIDATE_CAPABILITY_NOT_OBJECT:" + str(i))
            cid = _token(row.get("id"), "CAPABILITY_ID")
            if cid in ids or cid == FINAL_CAPABILITY_ID:
                raise RawTaskMissionError("CAPABILITY_ID_DUPLICATE_OR_RESERVED:" + cid)
            ids.add(cid)
            provides = row.get("provides")
            result_fields = row.get("result_fields")
            if not isinstance(provides, list) or not isinstance(result_fields, list):
                raise RawTaskMissionError("CAPABILITY_EFFECT_OR_RESULT_FIELDS_INVALID:" + cid)
            if candidate_effect in provides:
                providers.append(cid)
                if candidate_sha256_field not in result_fields:
                    raise RawTaskMissionError(
                        "CANDIDATE_SHA256_FIELD_NOT_DECLARED_BY_PROVIDER:" + cid
                    )
            caps.append(dict(row))
        if not providers:
            raise RawTaskMissionError("NO_CAPABILITY_PROVIDES_CANDIDATE_EFFECT")

        contract = compile_contract(
            task_text,
            source_id=source_id,
            routing_target_effects=[candidate_effect],
            semantic_goal_contract=None,
        )
        if contract.get("pass") is not True:
            raise RawTaskMissionError(
                "LOSSLESS_RAW_TASK_CONTRACT_FAILED:"
                + ";".join(contract.get("errors") or [])
            )

        final_cap = {
            "id": FINAL_CAPABILITY_ID,
            "requires": [candidate_effect],
            "provides": [FINAL_EFFECT],
            "cost": 0,
            "result_fields": [
                "candidate_sha256",
                "accepted_obligation_count",
                "required_obligation_count",
            ],
            "action": {
                "type": "verified_policy",
                "verifier_id": "RAW_TASK_ACCEPTANCE_V1",
                "verifier_payload": {
                    "task_contract": contract,
                    "candidate_sha256": {
                        "$effect_result": {
                            "effect": candidate_effect,
                            "field": candidate_sha256_field,
                        }
                    },
                    "repo_root": repo_root,
                },
                "effect_contract": {
                    "effects": [FINAL_EFFECT],
                    "verifier_success_condition": SUCCESS_CONDITIONS[
                        "RAW_TASK_ACCEPTANCE_V1"
                    ],
                },
            },
        }
        caps.append(final_cap)
        resolved_task_id = (
            _token(task_id, "TASK_ID")
            if task_id is not None
            else "RAW_TASK:" + sha256(task_text.encode("utf-8")).hexdigest()[:24]
        )
        problem = {
            "task_id": resolved_task_id,
            "initial_facts": [],
            "target_effects": [FINAL_EFFECT],
            "capabilities": caps,
            "raw_task_contract_sha256": contract["task_contract_sha256"],
            "raw_task_sha256": contract["task_sha256"],
            "raw_task_acceptance_obligation_count": len(
                contract["acceptance_contract"]["required_obligation_ids"]
            ),
        }
        return {
            "schema": SCHEMA,
            "status": "PASS__LOSSLESS_RAW_TASK_UNIVERSAL_MISSION_COMPILED",
            "pass": True,
            "problem": problem,
            "raw_task_contract": contract,
            "candidate_effect": candidate_effect,
            "candidate_sha256_field": candidate_sha256_field,
            "candidate_provider_capability_ids": sorted(providers),
            "final_acceptance_capability_id": FINAL_CAPABILITY_ID,
            "final_target_effect": FINAL_EFFECT,
            "routing_success_authority": False,
            "raw_task_acceptance_is_final_success_authority": True,
            "semantic_completeness_required_at_routing_time": False,
            "terminal_authority": False,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "errors": [type(exc).__name__ + ":" + str(exc)],
            "terminal_authority": False,
        }
