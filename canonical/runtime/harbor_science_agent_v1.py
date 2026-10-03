"""Brain-owned Harbor research controller for zero-case science-route qualification.

The cognition substrate may propose a bounded research contract and candidate shell
actions. Brain owns command admissibility, candidate selection, verification,
coverage state, and finish authority. No benchmark-specific task content lives here.
"""
from __future__ import annotations

import json
from typing import Any

from canonical.runtime import astra_runtime
from canonical.runtime.harbor_command_policy import validate_environment_command
from canonical.runtime.harbor_environment_transport import HarborEnvironmentTransport
from canonical.runtime.shared_decision_primitives import ResearchAction, next_research_action

try:
    from harbor.agents.base import BaseAgent
    from harbor.agents.capabilities import AgentCapabilities
    from harbor.environments.base import BaseEnvironment
    from harbor.models.agent.context import AgentContext
except ImportError:
    BaseAgent = object
    BaseEnvironment = Any
    AgentContext = Any
    class AgentCapabilities:
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs

SCHEMA = "PROJECT_BRAIN_HARBOR_SCIENCE_AGENT_TRACE_V1"
MAX_CYCLES = 12
MAX_REQUIREMENTS = 16
MAX_CANDIDATES = 8
MAX_OUTPUT_CHARS = 16000

def _nonempty_strings(value: Any, *, maximum: int, field: str) -> list[str]:
    if not isinstance(value, list) or not value or len(value) > maximum:
        raise RuntimeError(f"SCIENCE_{field}_INVALID")
    out: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise RuntimeError(f"SCIENCE_{field}_INVALID")
        s = item.strip()
        if s in out:
            raise RuntimeError(f"SCIENCE_{field}_DUPLICATE")
        out.append(s)
    return out

def _candidate_rows(raw: Any, requirements: set[str]) -> list[dict[str, Any]]:
    if not isinstance(raw, list) or not raw or len(raw) > MAX_CANDIDATES:
        raise RuntimeError("SCIENCE_CANDIDATES_INVALID")
    rows: list[dict[str, Any]] = []
    ids: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            raise RuntimeError("SCIENCE_CANDIDATE_INVALID")
        aid = str(item.get("action_id") or "").strip()
        if not aid or aid in ids:
            raise RuntimeError("SCIENCE_ACTION_ID_INVALID_OR_DUPLICATE")
        ids.add(aid)
        covers = _nonempty_strings(item.get("covers"), maximum=MAX_REQUIREMENTS, field="COVERS")
        if not set(covers).issubset(requirements):
            raise RuntimeError("SCIENCE_COVERAGE_OUTSIDE_CONTRACT")
        command = validate_environment_command(item.get("command"))
        verify_command = validate_environment_command(item.get("verify_command"))
        rows.append({
            "action_id": aid,
            "covers": covers,
            "command": command,
            "verify_command": verify_command,
        })
    return rows

def _extract_contract(raw: dict[str, Any], prior_requirements: list[str] | None) -> tuple[list[str], list[dict[str, Any]], str | None]:
    if prior_requirements is None:
        requirements = _nonempty_strings(
            raw.get("material_requirements"),
            maximum=MAX_REQUIREMENTS,
            field="MATERIAL_REQUIREMENTS",
        )
    else:
        requirements = list(prior_requirements)
        if "material_requirements" in raw:
            repeated = _nonempty_strings(
                raw.get("material_requirements"),
                maximum=MAX_REQUIREMENTS,
                field="MATERIAL_REQUIREMENTS",
            )
            if repeated != requirements:
                raise RuntimeError("SCIENCE_REQUIREMENTS_MUTATED_AFTER_FREEZE")
    summary = raw.get("finish_summary")
    if summary is not None:
        if not isinstance(summary, str) or not summary.strip():
            raise RuntimeError("SCIENCE_FINISH_SUMMARY_INVALID")
        summary = summary.strip()
    candidates = []
    if raw.get("candidates") is not None:
        candidates = _candidate_rows(raw.get("candidates"), set(requirements))
    return requirements, candidates, summary

async def run_science_goal(goal: str, environment: BaseEnvironment, *, max_cycles: int = 8) -> dict[str, Any]:
    goal = str(goal or "").strip()
    if not goal:
        raise ValueError("SCIENCE_GOAL_REQUIRED")
    max_cycles = max(1, min(int(max_cycles), MAX_CYCLES))
    requirements: list[str] | None = None
    resolved: set[str] = set()
    observations: list[dict[str, Any]] = []
    trace: list[dict[str, Any]] = []

    for cycle in range(max_cycles):
        unresolved = [] if requirements is None else sorted(set(requirements) - resolved)
        prompt = (
            "You are an OPTIONAL semantic proposal source inside Project Brain, not execution authority. "
            "Return one JSON object only. Project Brain owns action selection, command policy, verification, "
            "requirement-state updates, and finish authority. No network acquisition, package installation, "
            "git fetch/clone/pull, secrets, or host escape. "
            "On the first cycle provide material_requirements (1-16 stable short IDs). "
            "Provide 1-8 candidate actions as {action_id,covers,command,verify_command}. "
            "covers must name only frozen material_requirements. verify_command must independently test the "
            "candidate's claimed effect inside the task environment. Once every material requirement has a "
            "successful command+verify pair, return finish_summary. "
            f"Goal: {goal}\nFrozen requirements: {requirements!r}\nUnresolved: {unresolved!r}\n"
            "Recent observations: " + json.dumps(observations[-4:], sort_keys=True)[:12000]
        )
        planned = astra_runtime._planner_post(prompt, timeout_s=20)
        raw = astra_runtime._extract_json_object(planned.get("text", ""))
        if not isinstance(raw, dict):
            raise RuntimeError("SCIENCE_PLANNER_OBJECT_REQUIRED")
        requirements, candidates, finish_summary = _extract_contract(raw, requirements)
        unresolved_set = set(requirements) - resolved

        if finish_summary is not None:
            if unresolved_set:
                rejected = {
                    "cycle": cycle,
                    "kind": "FINISH_REJECTED",
                    "reason": "UNRESOLVED_MATERIAL_REQUIREMENTS",
                    "unresolved": sorted(unresolved_set),
                }
                trace.append(rejected)
                observations.append(rejected)
                continue
            return {
                "schema": SCHEMA,
                "status": "FINISHED",
                "controller_mode": "BRAIN_OWNED_RESEARCH_CONTROL__OPTIONAL_GENERAL_COGNITION_SUBSTRATE",
                "model_has_terminal_authority": False,
                "material_requirements": requirements,
                "resolved_requirements": sorted(resolved),
                "cycles": cycle + 1,
                "trace": trace,
                "summary": finish_summary,
                "planner_model_last": planned.get("model"),
            }

        if not candidates:
            rejected = {"cycle": cycle, "kind": "NO_CANDIDATES", "unresolved": sorted(unresolved_set)}
            trace.append(rejected)
            observations.append(rejected)
            continue

        action_rows = [
            ResearchAction(
                action_id=row["action_id"],
                covers=frozenset(row["covers"]),
                cost=1.0,
                reliability=1.0,
                verified=True,
            )
            for row in candidates
        ]
        decision = next_research_action(requirements, resolved, action_rows)
        if decision.status != "ACT" or decision.action_id is None:
            blocked = {
                "cycle": cycle,
                "kind": "BRAIN_RESEARCH_SELECTION_BLOCKED",
                "reason": decision.reason,
                "unresolved": sorted(decision.unresolved),
            }
            trace.append(blocked)
            observations.append(blocked)
            continue

        chosen = next(row for row in candidates if row["action_id"] == decision.action_id)
        transport = HarborEnvironmentTransport(environment)
        action_receipt = await transport.exec(chosen["command"], timeout_sec=180)
        action_observed = {
            "returncode": action_receipt.returncode,
            "stdout": action_receipt.stdout[-MAX_OUTPUT_CHARS:],
            "stderr": action_receipt.stderr[-MAX_OUTPUT_CHARS:],
        }
        verify_observed = None
        verified = False
        if action_receipt.returncode == 0:
            verify_receipt = await transport.exec(chosen["verify_command"], timeout_sec=180)
            verify_observed = {
                "returncode": verify_receipt.returncode,
                "stdout": verify_receipt.stdout[-MAX_OUTPUT_CHARS:],
                "stderr": verify_receipt.stderr[-MAX_OUTPUT_CHARS:],
            }
            verified = verify_receipt.returncode == 0
        if verified:
            resolved.update(chosen["covers"])
        record = {
            "cycle": cycle,
            "kind": "BRAIN_SELECTED_RESEARCH_ACTION",
            "action_id": chosen["action_id"],
            "covers": chosen["covers"],
            "selection_reason": decision.reason,
            "action_result": action_observed,
            "verify_result": verify_observed,
            "coverage_promoted": verified,
        }
        trace.append(record)
        observations.append(record)

    return {
        "schema": SCHEMA,
        "status": "BLOCKED_MAX_CYCLES_NO_BRAIN_AUTHORIZED_FINISH",
        "controller_mode": "BRAIN_OWNED_RESEARCH_CONTROL__OPTIONAL_GENERAL_COGNITION_SUBSTRATE",
        "model_has_terminal_authority": False,
        "material_requirements": requirements or [],
        "resolved_requirements": sorted(resolved),
        "cycles": max_cycles,
        "trace": trace,
        "summary": "",
    }

class HarborScienceAgent(BaseAgent):
    capabilities = AgentCapabilities()

    @staticmethod
    def name() -> str:
        return "project-brain-science"

    def version(self) -> str:
        return "1.0.0"

    async def setup(self, environment: BaseEnvironment) -> None:
        return None

    async def run(self, instruction: str, environment: BaseEnvironment, context: AgentContext) -> None:
        result = await run_science_goal(instruction, environment)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        (self.logs_dir / "project_brain_science_trace.json").write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        if hasattr(context, "cost_usd"):
            context.cost_usd = 0.0
