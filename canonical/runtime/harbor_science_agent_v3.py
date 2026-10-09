"""Science Agent V3: run-wide typed-action memory over verified V1 control."""
from __future__ import annotations

import asyncio
import json
from typing import Any

from canonical.runtime import harbor_science_agent_v1 as _v1
from canonical.runtime import harbor_science_agent_v2 as _v2
from canonical.runtime import harbor_science_planner_v2 as _planner_v2
from canonical.runtime.science_action_contract_v2 import (
    action_fingerprint,
    prompt_observation_state,
    required_schema_keys,
)

SCHEMA = "PROJECT_BRAIN_HARBOR_SCIENCE_AGENT_TRACE_V3"
_LOCK = asyncio.Lock()


class _PlannerProxy:
    failed_fingerprints: set[str] = set()
    observed_schema_keys: set[str] = set()

    @classmethod
    def reset(cls) -> None:
        cls.failed_fingerprints = set()
        cls.observed_schema_keys = set()

    @staticmethod
    def extract_json_object(text: Any) -> dict[str, Any]:
        return _planner_v2.extract_json_object(text)

    @staticmethod
    def normalize_proposal_object(obj: dict[str, Any]) -> dict[str, Any]:
        return _planner_v2.normalize_proposal_object(obj)

    @classmethod
    def plan(cls, prompt: str, *, timeout_s: int = 180) -> dict[str, Any]:
        result = _planner_v2.plan(prompt, timeout_s=timeout_s)
        proposal = _planner_v2.normalize_proposal_object(
            _planner_v2.extract_json_object(result.get("text", ""))
        )
        candidates = proposal.get("candidates")
        if not isinstance(candidates, list):
            return result

        observed, failed = prompt_observation_state(prompt)
        cls.observed_schema_keys.update(observed)
        cls.failed_fingerprints.update(failed)

        kept: list[dict[str, Any]] = []
        seen: set[str] = set()
        for row in candidates:
            fp = action_fingerprint(
                row.get("command_language"), row.get("command")
            )
            if fp in cls.failed_fingerprints or fp in seen:
                continue
            needed = required_schema_keys(
                row.get("command_language"), row.get("command")
            )
            if set(needed) - cls.observed_schema_keys:
                continue
            seen.add(fp)
            kept.append(row)

        allowed = {str(x.get("action_id") or "") for x in kept}
        kept = [
            x for x in kept
            if all(str(dep) in allowed for dep in (x.get("depends_on") or []))
        ]
        proposal = dict(proposal)
        if kept:
            proposal["candidates"] = kept
        else:
            proposal.pop("candidates", None)

        out = dict(result)
        out["text"] = json.dumps(
            proposal, sort_keys=True, separators=(",", ":")
        )
        return out


async def run_science_goal(
    goal: str,
    environment: Any,
    *,
    max_cycles: int = 8,
) -> dict[str, Any]:
    async with _LOCK:
        prior_planner = _v1.science_planner
        prior_rows = _v1._candidate_rows
        prior_deliverables = _v1._brain_mandated_deliverables
        _PlannerProxy.reset()
        _v1.science_planner = _PlannerProxy
        _v1._candidate_rows = _v2._candidate_rows
        _v1._brain_mandated_deliverables = _v2._brain_mandated_deliverables
        try:
            result = await _v1.run_science_goal(
                goal, environment, max_cycles=max_cycles
            )
        finally:
            _v1.science_planner = prior_planner
            _v1._candidate_rows = prior_rows
            _v1._brain_mandated_deliverables = prior_deliverables

    out = dict(result)
    out["schema"] = SCHEMA
    out["typed_action_contract_v2"] = True
    out["run_wide_failed_action_fingerprint_memory_v3"] = True
    out["run_wide_external_schema_grounding_v3"] = True
    out["passive_deliverable_binding_v2"] = True
    return out


class HarborScienceAgent(_v2.HarborScienceAgent):
    def version(self) -> str:
        return "3.0.0"

    async def run(self, instruction: str, environment: Any, context: Any) -> None:
        result = await run_science_goal(instruction, environment)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        (self.logs_dir / "project_brain_science_trace.json").write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        if hasattr(context, "cost_usd"):
            context.cost_usd = 0.0
