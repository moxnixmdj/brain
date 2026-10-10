"""End-to-end structured task route through the Universal Verified Adaptive Solver.

This is a parameterized vertical slice, not a benchmark-specific mechanism.

Input:
- controlled source requirements;
- declared typed candidate field schema;
- explicit finite domains;
- optional bounded registered filesystem effect.

Flow:
source requirements -> source-aligned acceptance program -> finite complete search ->
independent solver re-verification -> optional verified effect execution/readback ->
append-only state lineage -> verified episode candidate.

No general cognition substrate is needed when the finite search class is sufficient.
Unsupported normative language, incomplete finite domains, or unsupported effects
remain unresolved/fail closed.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime.source_aligned_acceptance_program_v1 import compile_program
from canonical.runtime.universal_verified_adaptive_solver_v1 import run
from canonical.runtime.universal_verified_skill_ratchet_v1 import episode_candidate_from_solver

SCHEMA = "PROJECT_BRAIN_UNIVERSAL_STRUCTURED_TASK_ROUTE_V1"
ALLOWED_EFFECT_TOOLS = {"JSON_RECEIPT_WRITER_V1", "JSONL_LEDGER_APPEND_V1"}


def solve(
    task: Mapping[str, Any],
    *,
    effect_root: str | Path | None = None,
) -> dict[str, Any]:
    try:
        if not isinstance(task, Mapping):
            raise ValueError("TASK_NOT_OBJECT")
        source_text = task.get("source_text")
        source_id = task.get("source_id")
        field_schema = task.get("field_schema")
        candidate_domains = task.get("candidate_domains")
        target_effect = task.get("target_effect")
        if not isinstance(source_text, str) or not source_text.strip():
            raise ValueError("SOURCE_TEXT_REQUIRED")
        if not isinstance(source_id, str) or not source_id.strip():
            raise ValueError("SOURCE_ID_REQUIRED")
        if not isinstance(field_schema, Mapping) or not field_schema:
            raise ValueError("FIELD_SCHEMA_REQUIRED")
        if not isinstance(candidate_domains, Mapping) or not candidate_domains:
            raise ValueError("CANDIDATE_DOMAINS_REQUIRED")
        if not isinstance(target_effect, str) or not target_effect.strip():
            raise ValueError("TARGET_EFFECT_REQUIRED")

        compiled = compile_program(
            source_text,
            source_id=source_id,
            field_schema=field_schema,
        )
        if compiled.get("status") != "COMPILED":
            return {
                "schema": SCHEMA,
                "status": "UNRESOLVED__ACCEPTANCE_PROGRAM_NOT_COMPILED",
                "pass": False,
                "acceptance_compilation": compiled,
                "terminal_authority": False,
            }

        action: dict[str, Any] = {
            "type": "verified_policy",
            "verifier_id": "TYPED_ACCEPTANCE_PROGRAM_V1",
            "verifier_payload": {
                "program": compiled["acceptance_program"],
                "trusted_values": {},
            },
            "proposal_generator_id": "TYPED_ACCEPTANCE_FINITE_SEARCH_V1",
            "proposal_generator_payload": {
                "candidate_domains": dict(candidate_domains),
                "max_candidates": int(task.get("max_candidates", 100000)),
            },
        }

        effect = task.get("effect")
        if effect is not None:
            if not isinstance(effect, Mapping):
                raise ValueError("EFFECT_INVALID")
            tool_id = effect.get("tool_id")
            sandbox_rel = effect.get("sandbox_rel")
            if tool_id not in ALLOWED_EFFECT_TOOLS:
                raise ValueError("EFFECT_TOOL_NOT_ALLOWED")
            if not isinstance(sandbox_rel, str) or not sandbox_rel:
                raise ValueError("EFFECT_SANDBOX_REL_REQUIRED")
            action = {
                "type": "verified_effect_tool",
                "pre_verifier_id": "TYPED_ACCEPTANCE_PROGRAM_V1",
                "pre_verifier_payload": {
                    "program": compiled["acceptance_program"],
                    "trusted_values": {},
                },
                "proposal_generator_id": "TYPED_ACCEPTANCE_FINITE_SEARCH_V1",
                "proposal_generator_payload": {
                    "candidate_domains": dict(candidate_domains),
                    "max_candidates": int(task.get("max_candidates", 100000)),
                },
                "executor_id": "H100_VERIFIED_EFFECT_TOOL_REGISTRY_V1",
                "executor_payload": {
                    "tool_id": tool_id,
                    "sandbox_rel": sandbox_rel,
                },
            }

        problem = {
            "initial_facts": [],
            "target_effects": [target_effect],
            "max_solver_cycles": 8,
            "capabilities": [{
                "id": "structured-task-solve",
                "requires": [],
                "provides": [target_effect],
                "cost": 1,
                "result_fields": [],
                "action": action,
            }],
        }
        result = run(
            problem,
            proposal_packets={},
            effect_root=str(effect_root) if effect_root is not None else None,
        )
        out = {
            "schema": SCHEMA,
            "status": result.get("status"),
            "pass": result.get("pass") is True,
            "acceptance_compilation": compiled,
            "solver_result": result,
            "terminal_authority": False,
        }
        if result.get("pass") is True:
            episode = episode_candidate_from_solver(
                result,
                episode_id="structured:" + str(result.get("state_capsule_head_hash") or "")[:24],
                scope_id="SOURCE_ALIGNED_FINITE_STRUCTURED_TASK_V1",
                postconditions=[target_effect],
            )
            out["episode_candidate"] = episode
            out["episode_reuse_authorized"] = False
        return out
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "errors": [type(exc).__name__ + ":" + str(exc)],
            "terminal_authority": False,
        }
