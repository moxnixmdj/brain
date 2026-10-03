"""Recompute exact structural information dominance on the current 27-predicate world.

This V2 wrapper is intentionally bound to the current Recovery-promoted scheduler
and the mandatory Tool Discovery V2 retrieval-authority gate. It never mutates
acceptance state and grants no execution, promotion, family, or capability credit.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.current_terminal_scheduling_world_v1 import evaluate as compile_world
from canonical.runtime.terminal_information_dominance_v1 import evaluate as information_dominance
from canonical.runtime import tool_discovery_retrieval_authority_gate_v1 as retrieval_gate_module

SCHEMA = "PROJECT_BRAIN_CURRENT_TERMINAL_INFORMATION_DOMINANCE_V2"
TOOL_TARGET = "TOOL_LEARNING_SUCCESS_ROUTE_NONINFERIOR"
RECOVERY_PROVED = {
    "RECOVERY_TERMINAL_NONINFERIOR",
    "RECOVERY_CAUSAL_LOCALIZATION_NONINFERIOR",
    "RECOVERY_ZERO_CRITICAL_FAIL_CLOSED_MISSES",
}
DELEGATION_PROVED = "DELEGATION_TERMINAL_SUCCESS_NONINFERIOR"


def _fail(*errors: str, **extra: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "errors": sorted(set(errors)),
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "new_reality_units_consumed": 0,
        "incremental_spend_usd": 0,
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
) -> dict[str, Any]:
    errors: list[str] = []

    if retrieval_gate.get("schema") != retrieval_gate_module.SCHEMA or retrieval_gate.get("pass") is not True:
        errors.append("MANDATORY_TOOL_DISCOVERY_RETRIEVAL_GATE_NOT_PASS")

    if current_scheduling_authority.get("schema") != "PROJECT_BRAIN_TERMINAL_SCHEDULING_CURRENT_AUTHORITY_V1":
        errors.append("CURRENT_SCHEDULING_AUTHORITY_SCHEMA_INVALID")
    if not str(current_scheduling_authority.get("status") or "").startswith("ACTIVE_INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("CURRENT_SCHEDULING_AUTHORITY_NOT_ACTIVE_INDEPENDENT_PASS")

    sched_world = current_scheduling_authority.get("live_world")
    if not isinstance(sched_world, Mapping):
        errors.append("CURRENT_SCHEDULING_LIVE_WORLD_MISSING")
        sched_world = {}
    if (
        sched_world.get("registry_predicates"),
        sched_world.get("proved_predicates"),
        sched_world.get("unresolved_predicates"),
        sched_world.get("opus55_acceptance"),
    ) != (38, 11, 27, "4/19_PASS__15/19_OPEN"):
        errors.append("CURRENT_SCHEDULING_WORLD_NOT_38_11_27_4_OF_19")

    mandatory = current_scheduling_authority.get("mandatory_tool_discovery_retrieval")
    if not isinstance(mandatory, Mapping):
        errors.append("CURRENT_SCHEDULING_MANDATORY_RETRIEVAL_BLOCK_MISSING")
        mandatory = {}
    if mandatory.get("mandatory") is not True:
        errors.append("CURRENT_SCHEDULING_RETRIEVAL_NOT_MANDATORY")
    if mandatory.get("direct_bypass_allowed") is not False:
        errors.append("CURRENT_SCHEDULING_DIRECT_BYPASS_NOT_DISABLED")
    if mandatory.get("consumed_source_epoch_replay_allowed") is not False:
        errors.append("CURRENT_SCHEDULING_EPOCH_REPLAY_NOT_DISABLED")
    if mandatory.get("no_result_means_nonexistence") is not False:
        errors.append("CURRENT_SCHEDULING_NO_RESULT_FIREWALL_MISSING")

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

    counts = (
        live.get("registry_predicate_count"),
        live.get("proved_predicate_count"),
        live.get("unresolved_predicate_count"),
    )
    if counts != (38, 11, 27):
        errors.append(f"LIVE_WORLD_COUNT_MISMATCH:{counts}")

    unresolved = set(live.get("unresolved_predicates") or [])
    if TOOL_TARGET not in unresolved:
        errors.append("TOOL_DISCOVERY_TARGET_NOT_OPEN")
    leaked_recovery = sorted(RECOVERY_PROVED & unresolved)
    if leaked_recovery:
        errors.append("RECOVERY_PROVED_TARGETS_STILL_LIVE:" + ",".join(leaked_recovery))
    if DELEGATION_PROVED in unresolved:
        errors.append("DELEGATION_PROVED_TARGET_STILL_LIVE")

    if live.get("tool_discovery_retrieval_authority_gate_required") is not True:
        errors.append("LIVE_WORLD_TOOL_RETRIEVAL_GATE_NOT_REQUIRED")
    if live.get("tool_discovery_retrieval_authority_gate_pass") is not True:
        errors.append("LIVE_WORLD_TOOL_RETRIEVAL_GATE_NOT_PASS")

    if errors:
        return _fail(*errors, live_world=live)

    doc = {
        "unresolved_predicates": live["unresolved_predicates"],
        "certificates": live["live_certificates"],
    }
    dominance = information_dominance(doc)
    if dominance.get("status") != "EXACT_INFORMATION_DOMINANCE_COMPUTED":
        return _fail("DOMINANCE_NOT_COMPUTED", live_world=live, dominance=dominance)

    if dominance.get("unresolved_predicate_count") != 27:
        errors.append("DOMINANCE_UNRESOLVED_COUNT_NOT_27")
    bundle = dominance.get("best_full_frontier_bundle")
    if not isinstance(bundle, Mapping) or bundle.get("covered_predicate_count") != 27:
        errors.append("DOMINANCE_FULL_FRONTIER_BUNDLE_NOT_27")

    cert_ids = {
        str(row.get("certificate_id"))
        for row in dominance.get("single_certificate_structural_front") or []
        if isinstance(row, Mapping)
    }
    if "DELEGATION_PROTOCOL_SCOPE_COMPLETENESS_CERTIFICATE" in cert_ids:
        errors.append("DELEGATION_CLOSED_CERTIFICATE_STILL_LIVE")

    if errors:
        return _fail(*errors, live_world=live, dominance=dominance)

    return {
        "schema": SCHEMA,
        "status": "PASS__EXACT_LIVE_27_INFORMATION_DOMINANCE__MANDATORY_TOOL_DISCOVERY_V2_GATE__ZERO_REALITY__ZERO_CREDIT",
        "pass": True,
        "errors": [],
        "live_world_summary": {
            "frozen_predicates": 38,
            "proved_predicates": 11,
            "unresolved_predicates": 27,
            "live_certificate_count": live["live_certificate_count"],
            "live_action_count": live["live_action_count"],
            "live_action_coverage_count": live["live_action_coverage_count"],
            "tool_discovery_retrieval_gate_required": True,
            "tool_discovery_retrieval_gate_pass": True,
        },
        "removed_terminal_predicates": sorted(RECOVERY_PROVED | {DELEGATION_PROVED}),
        "tool_discovery_target_open": True,
        "dominance": dominance,
        "nondominated_zero_reality_certificate_ids": dominance.get("nondominated_certificate_ids") or [],
        "dominated_zero_reality_certificate_ids": dominance.get("dominated_certificate_ids") or [],
        "next_rule": (
            "COMPILE_THE_LIVE_27_ACTION_FRONTIER_FROM_ONLY_CURRENT_UNRESOLVED_TARGETS__"
            "WORK_BOUNDED_NONDOMINATED_ZERO_REALITY_ACTIONS_FIRST__"
            "TOOL_DISCOVERY_RETRIEVAL_MUST_PASS_EXACT_VERIFIED_V2_GATE__"
            "RUN_FIXED_POINT_AFTER_EACH_VERIFIED_CLOSURE__"
            "FRESH_REALITY_ONLY_AFTER_ZERO_REALITY_FRONTIER_IS_EXPLICITLY_SATURATED"
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
    )
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out.get("pass") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
