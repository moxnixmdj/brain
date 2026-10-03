"""Compile the current 27-predicate zero-reality action frontier.

This layer sits above the current scheduler and information-dominance result. It:
- keeps only actions that still target unresolved predicates;
- requires all explicit preconditions to be satisfied;
- refuses actions with unknown/false preconditions or explicit BLOCKED disposition;
- enforces the active Tool Discovery V2 no-repeat/no-spend-without-wake policy;
- ranks zero-reality actions by structural reach only.

It does not estimate proof difficulty, success probability, or semantic sufficiency.
It grants no execution, promotion, family, capability, or acceptance credit.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.current_terminal_scheduling_world_v1 import evaluate as compile_world
from canonical.runtime import tool_discovery_retrieval_authority_gate_v1 as retrieval_gate_module

SCHEMA = "PROJECT_BRAIN_CURRENT_LIVE27_ZERO_REALITY_FRONTIER_V1"

def _fail(*errors: str, **extra: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "errors": sorted(set(errors)),
        "selected_action": None,
        "actions": [],
        "new_reality_units_consumed": 0,
        "incremental_spend_usd": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }
    out.update(extra)
    return out

def evaluate(
    registry: Mapping[str, Any],
    evidence: Mapping[str, Any],
    frontier: Mapping[str, Any],
    hypergraph: Mapping[str, Any],
    legacy_scheduling: Mapping[str, Any],
    authority: Mapping[str, Any],
    retrieval_gate: Mapping[str, Any],
    current_scheduling_authority: Mapping[str, Any],
    retrieval_activation: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []

    if retrieval_gate.get("schema") != retrieval_gate_module.SCHEMA or retrieval_gate.get("pass") is not True:
        errors.append("MANDATORY_TOOL_DISCOVERY_RETRIEVAL_GATE_NOT_PASS")

    if current_scheduling_authority.get("schema") != "PROJECT_BRAIN_TERMINAL_SCHEDULING_CURRENT_AUTHORITY_V1":
        errors.append("CURRENT_SCHEDULING_AUTHORITY_SCHEMA_INVALID")
    if not str(current_scheduling_authority.get("status") or "").startswith("ACTIVE_INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("CURRENT_SCHEDULING_AUTHORITY_NOT_ACTIVE_INDEPENDENT_PASS")

    if retrieval_activation.get("schema") != "PROJECT_BRAIN_TOOL_DISCOVERY_RESIDUAL_WITNESS_RETRIEVAL_FRONTIER_V2_ACTIVATION_V1":
        errors.append("TOOL_DISCOVERY_V2_ACTIVATION_SCHEMA_INVALID")
    if not str(retrieval_activation.get("status") or "").startswith("ACTIVE_INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("TOOL_DISCOVERY_V2_ACTIVATION_NOT_ACTIVE")

    live = compile_world(
        registry,
        evidence,
        frontier,
        hypergraph,
        legacy_scheduling,
        authority,
        retrieval_gate,
    )
    if live.get("pass") is not True:
        return _fail(*(errors + ["LIVE_WORLD_INVALID"]), live_world=live)

    if (live.get("registry_predicate_count"), live.get("proved_predicate_count"), live.get("unresolved_predicate_count")) != (38, 11, 27):
        errors.append("LIVE_WORLD_NOT_38_11_27")
    if live.get("live_action_coverage_count") != 27:
        errors.append("LIVE_ACTION_COVERAGE_NOT_27")
    if live.get("tool_discovery_retrieval_authority_gate_pass") is not True:
        errors.append("LIVE_TOOL_DISCOVERY_GATE_NOT_PASS")

    reg_rows = registry.get("predicates")
    if not isinstance(reg_rows, list):
        errors.append("REGISTRY_PREDICATES_NOT_LIST")
        reg_rows = []
    family_by_predicate = {
        str(row.get("id")): str(row.get("family") or "UNKNOWN")
        for row in reg_rows if isinstance(row, Mapping)
    }

    policy = retrieval_activation.get("operational_policy")
    if not isinstance(policy, Mapping):
        errors.append("TOOL_DISCOVERY_V2_POLICY_MISSING")
        policy = {}
    if policy.get("repeat_v1_source_epoch") is not False:
        errors.append("V1_SOURCE_EPOCH_REPLAY_NOT_DISABLED")
    if policy.get("repeat_v2_github_source_epoch") is not False:
        errors.append("V2_GITHUB_SOURCE_EPOCH_REPLAY_NOT_DISABLED")
    no_wake_directive = str(policy.get("next_action_without_wake") or "")
    if not no_wake_directive.startswith("DO_NOT_SPEND_ADDITIONAL_RETRIEVAL_ACTIONS"):
        errors.append("TOOL_DISCOVERY_NO_WAKE_STOP_RULE_MISSING")

    if errors:
        return _fail(*errors, live_world=live)

    rows: list[dict[str, Any]] = []
    for raw in live.get("live_actions") or []:
        if not isinstance(raw, Mapping):
            return _fail("LIVE_ACTION_NOT_OBJECT")
        aid = str(raw.get("id") or "")
        targets = [str(x) for x in raw.get("target_predicates") or []]
        preconditions = raw.get("preconditions") or []
        if not isinstance(preconditions, list):
            return _fail("ACTION_PRECONDITIONS_NOT_LIST:" + aid)

        unsatisfied = [
            str(p.get("id") or "")
            for p in preconditions
            if isinstance(p, Mapping) and p.get("satisfied") is False
        ]
        unknown = [
            str(p.get("id") or "")
            for p in preconditions
            if isinstance(p, Mapping) and p.get("satisfied") not in (True, False)
        ]
        malformed = [p for p in preconditions if not isinstance(p, Mapping)]
        if malformed:
            return _fail("ACTION_PRECONDITION_NOT_OBJECT:" + aid)

        disposition = str(raw.get("current_disposition") or "")
        disposition_blocked = "BLOCKED" in disposition
        zero_reality = raw.get("new_reality_units", 0) == 0

        tool_wait_for_wake = False
        if aid == retrieval_gate_module.ACTION_ID:
            tool_wait_for_wake = (
                policy.get("current_state") == "UNKNOWN_SCOPE_RELATION__STRICT_ACCEPTANCE_OPEN"
                and no_wake_directive.startswith("DO_NOT_SPEND_ADDITIONAL_RETRIEVAL_ACTIONS")
            )

        executable = (
            zero_reality
            and not unsatisfied
            and not unknown
            and not disposition_blocked
            and not tool_wait_for_wake
        )
        families = sorted({family_by_predicate.get(t, "UNKNOWN") for t in targets})
        rows.append({
            "id": aid,
            "action_class": str(raw.get("action_class") or ""),
            "critical_path": raw.get("critical_path") is True,
            "unresolved_target_predicates": targets,
            "affected_unresolved_count": len(targets),
            "affected_families": families,
            "affected_family_count": len(families),
            "new_reality_units": raw.get("new_reality_units", 0),
            "unsatisfied_preconditions": unsatisfied,
            "unknown_preconditions": unknown,
            "explicitly_blocked": disposition_blocked,
            "tool_discovery_wait_for_material_wake": tool_wait_for_wake,
            "executable_zero_reality": executable,
            "saturation_receipt": raw.get("saturation_receipt"),
        })

    executable = [r for r in rows if r["executable_zero_reality"]]
    executable.sort(key=lambda r: (
        -r["affected_unresolved_count"],
        -r["affected_family_count"],
        0 if r["critical_path"] else 1,
        r["id"],
    ))
    blocked = [r for r in rows if not r["executable_zero_reality"]]
    selected = executable[0] if executable else None

    tool_rows = [r for r in rows if r["id"] == retrieval_gate_module.ACTION_ID]
    if len(tool_rows) != 1:
        return _fail(f"TOOL_DISCOVERY_LIVE_ACTION_COUNT_NE_1:{len(tool_rows)}")
    if tool_rows[0]["tool_discovery_wait_for_material_wake"] is not True:
        return _fail("TOOL_DISCOVERY_NOT_BLOCKED_ON_NO_WAKE_POLICY")
    if tool_rows[0]["executable_zero_reality"] is not False:
        return _fail("TOOL_DISCOVERY_EXECUTABLE_DESPITE_NO_WAKE_POLICY")

    return {
        "schema": SCHEMA,
        "status": "PASS__LIVE27_ZERO_REALITY_FRONTIER_COMPILED__TOOL_DISCOVERY_NO_WAKE_STOP_ENFORCED__ZERO_CREDIT",
        "pass": True,
        "errors": [],
        "live_world": {
            "registry_predicates": 38,
            "proved_predicates": 11,
            "unresolved_predicates": 27,
            "live_actions": len(rows),
            "live_action_coverage": 27,
        },
        "selected_action": selected,
        "executable_zero_reality_action_count": len(executable),
        "blocked_action_count": len(blocked),
        "executable_zero_reality_actions": executable,
        "blocked_actions": blocked,
        "tool_discovery_action": tool_rows[0],
        "selection_rule": (
            "ONLY_EXPLICITLY_EXECUTABLE_ZERO_REALITY_ACTIONS__"
            "RANK_BY_UNRESOLVED_COVERAGE_THEN_FAMILY_COVERAGE_THEN_CRITICAL_PATH__"
            "DO_NOT_INFER_PROOF_DIFFICULTY_OR_SUCCESS_PROBABILITY"
        ),
        "new_reality_units_consumed": 0,
        "incremental_spend_usd": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }

def main() -> int:
    root = Path(__file__).resolve().parents[2]
    def load(rel: str) -> dict[str, Any]:
        return json.loads((root / rel).read_text(encoding="utf-8"))
    out = evaluate(
        load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"),
        load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"),
        load("canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V5.json"),
        load("canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json"),
        load("canonical/governance/TERMINAL_SCHEDULING_ACTIVATION_V6.json"),
        load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json"),
        retrieval_gate_module.evaluate_repository(root),
        load("canonical/governance/TERMINAL_SCHEDULING_CURRENT_AUTHORITY_V1.json"),
        load("canonical/governance/TOOL_DISCOVERY_RESIDUAL_WITNESS_RETRIEVAL_FRONTIER_V2_ACTIVATION_V1.json"),
    )
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out.get("pass") is True else 1

if __name__ == "__main__":
    raise SystemExit(main())
