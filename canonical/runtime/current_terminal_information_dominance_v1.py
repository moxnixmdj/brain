"""Recompute exact structural information dominance on the current receipt-derived terminal world.

Scheduling only. Zero acceptance/execution/promotion credit.

This wrapper is bound to the single current scheduling authority pointer and the
mandatory verified Tool Discovery V2 retrieval gate. Historical scheduling
artifacts may supply certificate/action structure only after the current live
world compiler filters terminal targets.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.current_terminal_scheduling_world_v1 import evaluate as compile_world
from canonical.runtime.terminal_information_dominance_v1 import evaluate as information_dominance
from canonical.runtime import tool_discovery_retrieval_authority_gate_v1 as tool_retrieval_gate

SCHEMA = "PROJECT_BRAIN_CURRENT_TERMINAL_INFORMATION_DOMINANCE_V1"
SCHEDULING_AUTHORITY_SCHEMA = "PROJECT_BRAIN_TERMINAL_SCHEDULING_CURRENT_AUTHORITY_V1"


def _fail(status: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": False,
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        **extra,
    }


def _validate_current_scheduling_authority(
    current_scheduling_authority: Mapping[str, Any] | None,
) -> list[str]:
    errors: list[str] = []
    if not isinstance(current_scheduling_authority, Mapping):
        return ["CURRENT_SCHEDULING_AUTHORITY_NOT_OBJECT"]
    if current_scheduling_authority.get("schema") != SCHEDULING_AUTHORITY_SCHEMA:
        errors.append("CURRENT_SCHEDULING_AUTHORITY_SCHEMA_MISMATCH")
    status = current_scheduling_authority.get("status")
    if not isinstance(status, str) or not status.startswith(
        "ACTIVE_INDEPENDENT_PUBLIC_RUNNER_PASS__V9_CURRENT"
    ):
        errors.append("CURRENT_SCHEDULING_AUTHORITY_NOT_ACTIVE_VERIFIED_V9")

    live = current_scheduling_authority.get("live_world")
    if not isinstance(live, Mapping):
        errors.append("CURRENT_SCHEDULING_AUTHORITY_LIVE_WORLD_NOT_OBJECT")
    else:
        expected = {
            "registry_predicates": 38,
            "proved_predicates": 11,
            "unresolved_predicates": 27,
            "opus55_acceptance": "4/19_PASS__15/19_OPEN",
            "tool_learning_success_route_noninferior": "OPEN",
        }
        for key, value in expected.items():
            if live.get(key) != value:
                errors.append(
                    f"CURRENT_SCHEDULING_AUTHORITY_{key.upper()}_{live.get(key)}_NE_{value}"
                )

    retrieval = current_scheduling_authority.get("mandatory_tool_discovery_retrieval")
    if not isinstance(retrieval, Mapping):
        errors.append("CURRENT_SCHEDULING_AUTHORITY_RETRIEVAL_NOT_OBJECT")
    else:
        if retrieval.get("mandatory") is not True:
            errors.append("CURRENT_SCHEDULING_AUTHORITY_RETRIEVAL_NOT_MANDATORY")
        if retrieval.get("direct_bypass_allowed") is not False:
            errors.append("CURRENT_SCHEDULING_AUTHORITY_DIRECT_BYPASS_NOT_FORBIDDEN")
        if retrieval.get("stale_authority_allowed") is not False:
            errors.append("CURRENT_SCHEDULING_AUTHORITY_STALE_RETRIEVAL_NOT_FORBIDDEN")
        if retrieval.get("consumed_source_epoch_replay_allowed") is not False:
            errors.append("CURRENT_SCHEDULING_AUTHORITY_CONSUMED_EPOCH_REPLAY_NOT_FORBIDDEN")
        if retrieval.get("no_result_means_nonexistence") is not False:
            errors.append("CURRENT_SCHEDULING_AUTHORITY_NO_RESULT_SEMANTICS_INVALID")

    return errors


def evaluate(
    registry: dict[str, Any],
    evidence: dict[str, Any],
    frontier: dict[str, Any],
    hypergraph: dict[str, Any],
    scheduling_v6: dict[str, Any],
    authority: dict[str, Any],
    current_scheduling_authority: Mapping[str, Any] | None,
    retrieval_authority_gate: Mapping[str, Any] | None,
) -> dict[str, Any]:
    pointer_errors = _validate_current_scheduling_authority(current_scheduling_authority)
    if pointer_errors:
        return _fail(
            "FAIL_CLOSED__CURRENT_SCHEDULING_AUTHORITY_INVALID",
            errors=sorted(set(pointer_errors)),
        )

    live = compile_world(
        registry,
        evidence,
        frontier,
        hypergraph,
        scheduling_v6,
        authority,
        retrieval_authority_gate,
    )
    if live.get("pass") is not True:
        return _fail("FAIL_CLOSED__LIVE_WORLD_INVALID", live_world=live)

    pointer_live = current_scheduling_authority["live_world"]
    cross_checks = {
        "registry_predicates": live["registry_predicate_count"],
        "proved_predicates": live["proved_predicate_count"],
        "unresolved_predicates": live["unresolved_predicate_count"],
    }
    mismatches = [
        f"LIVE_WORLD_{key.upper()}_{value}_NE_POINTER_{pointer_live.get(key)}"
        for key, value in cross_checks.items()
        if pointer_live.get(key) != value
    ]
    if mismatches:
        return _fail(
            "FAIL_CLOSED__LIVE_WORLD_POINTER_MISMATCH",
            errors=mismatches,
            live_world=live,
        )

    doc = {
        "unresolved_predicates": live["unresolved_predicates"],
        "certificates": live["live_certificates"],
    }
    dominance = information_dominance(doc)
    ok = dominance.get("status") == "EXACT_INFORMATION_DOMINANCE_COMPUTED"
    count = live["unresolved_predicate_count"]

    return {
        "schema": SCHEMA,
        "status": (
            f"PASS__EXACT_LIVE_{count}_INFORMATION_DOMINANCE__V9_BOUND__"
            "TOOL_DISCOVERY_V2_RETRIEVAL_GATE_BOUND__ZERO_REALITY__ZERO_CREDIT"
            if ok
            else "FAIL_CLOSED__DOMINANCE_NOT_COMPUTED"
        ),
        "pass": ok,
        "current_scheduling_authority": {
            "status": current_scheduling_authority.get("status"),
            "path": "canonical/governance/TERMINAL_SCHEDULING_CURRENT_AUTHORITY_V1.json",
            "current_authority": current_scheduling_authority.get("current_authority"),
        },
        "live_world_summary": {
            "frozen_predicates": live["registry_predicate_count"],
            "proved_predicates": live["proved_predicate_count"],
            "unresolved_predicates": count,
            "live_certificate_count": live["live_certificate_count"],
            "live_action_coverage_count": live["live_action_coverage_count"],
            "tool_discovery_retrieval_authority_gate_required": live.get(
                "tool_discovery_retrieval_authority_gate_required"
            ),
            "tool_discovery_retrieval_authority_gate_pass": live.get(
                "tool_discovery_retrieval_authority_gate_pass"
            ),
        },
        "dominance": dominance,
        "next_rule": (
            "WORK_ONLY_VERIFIED_NONDOMINATED_ZERO_REALITY_CERTIFICATES__"
            "ALL_TOOL_DISCOVERY_RETRIEVAL_MUST_USE_CURRENT_V2_AUTHORITY__"
            "RUN_FIXED_POINT_AFTER_EACH_VERIFIED_CERTIFICATE__"
            "FRESH_REALITY_ONLY_AFTER_ZERO_REALITY_FRONTIER_SATURATES_AND_SEPARATE_AUTHORITY_PASSES"
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
        load("canonical/governance/TERMINAL_SCHEDULING_CURRENT_AUTHORITY_V1.json"),
        tool_retrieval_gate.evaluate_repository(root),
    )
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
