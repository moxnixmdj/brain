"""Agent V12: task-authoritative artifact binding over verified Agent V11.

The only new authority is a prestart-produced, context-bound artifact list.
V12 validates the task digest and exact instruction hash, then feeds those safe
absolute paths into V11's existing mandatory-deliverable finish gate.

No artifact path is task-specific in this module. No benchmark, acceptance, or
terminal credit is granted by the binding itself.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
from typing import Any

from canonical.runtime import harbor_science_agent_v11 as v11

SCHEMA = "PROJECT_BRAIN_HARBOR_SCIENCE_AGENT_TRACE_V12"
BINDING_SCHEMA = "PROJECT_BRAIN_SCIENCE_TASK_ARTIFACT_RUNTIME_BINDING_V1"
ENV_KEY = "BRAIN_TASK_ARTIFACT_BINDING_JSON"

_V11_DELIVERABLES = v11._brain_mandated_deliverables


def _runtime_binding(goal: str) -> dict[str, Any] | None:
    raw = str(os.environ.get(ENV_KEY) or "").strip()
    if not raw:
        return None
    try:
        value = json.loads(raw)
    except Exception as exc:
        raise RuntimeError("SCIENCE_TASK_ARTIFACT_BINDING_JSON_INVALID") from exc
    if not isinstance(value, dict) or value.get("schema") != BINDING_SCHEMA:
        raise RuntimeError("SCIENCE_TASK_ARTIFACT_BINDING_SCHEMA_INVALID")

    expected_digest = str(os.environ.get("BRAIN_TASK_DIGEST") or "").strip()
    if value.get("task_digest") != expected_digest:
        raise RuntimeError("SCIENCE_TASK_ARTIFACT_BINDING_DIGEST_MISMATCH")
    goal_sha = hashlib.sha256(goal.encode("utf-8")).hexdigest()
    if value.get("instruction_sha256") != goal_sha:
        raise RuntimeError("SCIENCE_TASK_ARTIFACT_BINDING_INSTRUCTION_MISMATCH")

    paths = value.get("paths")
    if not isinstance(paths, list) or len(paths) > v11.MAX_BRAIN_DELIVERABLES:
        raise RuntimeError("SCIENCE_TASK_ARTIFACT_BINDING_PATHS_INVALID")
    normalized: list[str] = []
    for path in paths:
        if not isinstance(path, str) or not v11._valid_mandated_output_path(path):
            raise RuntimeError("SCIENCE_TASK_ARTIFACT_BINDING_PATH_INVALID")
        if path not in normalized:
            normalized.append(path)
    if normalized != paths:
        raise RuntimeError("SCIENCE_TASK_ARTIFACT_BINDING_NONCANONICAL_PATHS")

    return {
        "schema": BINDING_SCHEMA,
        "task_digest": expected_digest,
        "instruction_sha256": goal_sha,
        "paths": normalized,
        "source": value.get("source"),
        "task_authority_used": bool(value.get("task_authority_used")),
    }


def _deliverables_with_binding(goal: str) -> dict[str, str]:
    binding = _runtime_binding(goal)
    if binding is None:
        return _V11_DELIVERABLES(goal)

    paths: list[str] = list(binding["paths"])
    # Retain safe instruction-derived outputs as a fallback supplement, while
    # task-authoritative paths remain first and therefore cannot be displaced.
    for path in _V11_DELIVERABLES(goal).values():
        if path not in paths and len(paths) < v11.MAX_BRAIN_DELIVERABLES:
            paths.append(path)
    return {f"BD{i + 1:02d}": path for i, path in enumerate(paths)}


async def run_science_goal(
    goal: str,
    environment: Any,
    *,
    max_cycles: int = v11.MAX_CYCLES,
    journal_session: Any = None,
) -> dict[str, Any]:
    binding = _runtime_binding(goal)
    old = v11._brain_mandated_deliverables
    v11._brain_mandated_deliverables = _deliverables_with_binding
    try:
        result = await v11.run_science_goal(
            goal,
            environment,
            max_cycles=max_cycles,
            journal_session=journal_session,
        )
    finally:
        v11._brain_mandated_deliverables = old

    result = dict(result)
    result["schema"] = SCHEMA
    result["task_artifact_runtime_binding"] = binding
    result["task_artifact_binding_present"] = binding is not None
    result["task_artifact_binding_is_acceptance"] = False
    return result


class HarborScienceAgent(v11.HarborScienceAgent):
    @staticmethod
    def name() -> str:
        return "project-brain-science"

    def version(self) -> str:
        return "1.12.0"

    async def run(self, instruction: str, environment: Any, context: Any) -> None:
        logical_attempt_id = v11.logical_attempt_id_for_goal(instruction)
        await v11.start_barrier.await_start_commit(logical_attempt_id)
        journal_dir = os.environ.get("BRAIN_CAUSAL_JOURNAL_DIR")
        if not isinstance(journal_dir, str) or not journal_dir.strip():
            raise RuntimeError("BRAIN_CAUSAL_JOURNAL_DIR_REQUIRED")
        journal_session = v11.causal_bridge.JournalSession(
            journal_dir, logical_attempt_id
        )
        try:
            result = await run_science_goal(
                instruction, environment, journal_session=journal_session
            )
        except Exception as exc:
            result = {
                "schema": SCHEMA,
                "status": "BLOCKED_INTERNAL_CONTROLLER_OR_TRANSPORT_EXCEPTION",
                "internal_unsolved": True,
                "task_completion_claimed": False,
                "model_has_terminal_authority": False,
                "exception_type": type(exc).__name__,
                "exception_sha256": hashlib.sha256(
                    str(exc).encode("utf-8", "replace")
                ).hexdigest(),
            }
            try:
                await asyncio.to_thread(
                    journal_session.append,
                    "FAULT",
                    {
                        "cycle": -1,
                        "action_id": "CONTROLLER",
                        "stage": "CONTROLLER_EXCEPTION",
                        "error_type": type(exc).__name__,
                        "error_sha256": result["exception_sha256"],
                        "effect_replayed": False,
                        "verification_replayed": False,
                    },
                )
            except Exception:
                pass

        try:
            self.logs_dir.mkdir(parents=True, exist_ok=True)
            (self.logs_dir / "project_brain_science_trace.json").write_text(
                json.dumps(result, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        except Exception:
            pass
        if hasattr(context, "cost_usd"):
            try:
                context.cost_usd = 0.0
            except Exception:
                pass
