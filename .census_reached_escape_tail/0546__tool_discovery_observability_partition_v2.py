"""Minimum-reality observability partition for Tool Discovery V2.

This classifier is intentionally narrower than a policy. It decides which kind
of evidence is justified next after common tool-identity scope is complete.

Key correction over the earlier two-way partition candidate:
an unresolved route with an unobservable required fact is not yet irreducible
if a safe probe on that same cheapest cost frontier could first eliminate it or
establish another route at that cost. Safe evidence must be exhausted before
matched-comparator spend.

Likewise, an unresolved route tied in cost with an already verified sufficient
route cannot improve the least-cost objective merely by also being sufficient;
ties do not require a particular tool identity unless the frozen contract says
otherwise. The frozen Tool Discovery contract requires least cost, not a
canonical equal-cost identity.

Zero acceptance/family/execution/promotion credit.
"""

from __future__ import annotations

import json
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_TOOL_DISCOVERY_OBSERVABILITY_PARTITION_V2"

SUPPORTED = "SUPPORTED"
UNSUPPORTED = "UNSUPPORTED"
UNKNOWN = "UNKNOWN"
VALID = {SUPPORTED, UNSUPPORTED, UNKNOWN}


def _fail(reason: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED__INVALID_PARTITION_INPUT",
        "reason": reason,
        "minimum_reality_action": "MATCHED_COMPARATOR",
        "universal_proof_eligible": False,
        "safe_progress_available": False,
        "matched_comparator_required_now": True,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def classify(state: Mapping[str, Any]) -> dict[str, Any]:
    if state.get("identity_scope_complete") is not True:
        return _fail("IDENTITY_SCOPE_NOT_COMPLETE")

    required_raw = state.get("required_capabilities")
    if not isinstance(required_raw, list):
        return _fail("REQUIRED_CAPABILITIES_NOT_LIST")
    required = sorted({str(x) for x in required_raw if str(x)})
    if not required:
        return _fail("NO_REQUIRED_CAPABILITIES")

    tools_raw = state.get("admissible_tools")
    if not isinstance(tools_raw, list):
        return _fail("ADMISSIBLE_TOOLS_NOT_LIST")

    tools: list[dict[str, Any]] = []
    ids: set[str] = set()
    for raw in tools_raw:
        if not isinstance(raw, Mapping):
            return _fail("TOOL_NOT_OBJECT")
        tid = str(raw.get("tool_id") or "")
        if not tid or tid in ids:
            return _fail("TOOL_ID_INVALID_OR_DUPLICATE")
        ids.add(tid)

        cost = raw.get("cost")
        if isinstance(cost, bool) or not isinstance(cost, (int, float)):
            return _fail("TOOL_COST_INVALID:" + tid)
        cost = float(cost)
        if cost < 0 or cost != cost or cost in (float("inf"), float("-inf")):
            return _fail("TOOL_COST_INVALID:" + tid)

        evidence = raw.get("capability_evidence", {})
        if not isinstance(evidence, Mapping):
            return _fail("CAPABILITY_EVIDENCE_NOT_OBJECT:" + tid)
        safe = raw.get("safe_probe_capabilities", [])
        if not isinstance(safe, list):
            return _fail("SAFE_PROBE_CAPABILITIES_NOT_LIST:" + tid)
        safe_set = {str(x) for x in safe if str(x)}

        states: dict[str, str] = {}
        for cap in required:
            value = str(evidence.get(cap, UNKNOWN))
            if value not in VALID:
                return _fail("CAPABILITY_EVIDENCE_STATE_INVALID:" + tid + ":" + cap)
            states[cap] = value

        tools.append({
            "tool_id": tid,
            "cost": cost,
            "states": states,
            "safe": safe_set,
        })

    tools.sort(key=lambda row: (row["cost"], row["tool_id"]))

    ruled_out: list[str] = []
    verified: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []

    for row in tools:
        states = row["states"]
        if any(states[cap] == UNSUPPORTED for cap in required):
            ruled_out.append(row["tool_id"])
            continue
        unknown = [cap for cap in required if states[cap] == UNKNOWN]
        if not unknown:
            verified.append(row)
            continue
        unresolved.append({
            **row,
            "unknown": unknown,
            "safe_unknown": [cap for cap in unknown if cap in row["safe"]],
            "unsafe_unknown": [cap for cap in unknown if cap not in row["safe"]],
        })

    best_verified_cost = min((row["cost"] for row in verified), default=None)

    # Only routes strictly cheaper than an already verified route can improve
    # the least-cost objective. Equal-cost alternatives are also least-cost.
    decision_relevant_unresolved = [
        row for row in unresolved
        if best_verified_cost is None or row["cost"] < best_verified_cost
    ]

    if not decision_relevant_unresolved:
        return {
            "schema": SCHEMA,
            "status": "UNIVERSAL_PROOF_ELIGIBLE__DECISION_OBSERVABILITY_CLOSED",
            "minimum_reality_action": "UNIVERSAL_PROOF",
            "identity_scope_complete": True,
            "required_capabilities": required,
            "best_verified_sufficient_cost": best_verified_cost,
            "verified_sufficient_tool_ids": [row["tool_id"] for row in verified],
            "ruled_out_tool_ids": ruled_out,
            "decision_frontier_cost": None,
            "decision_frontier_tool_ids": [],
            "recommended_safe_probe": None,
            "irreducible_routes": [],
            "universal_proof_eligible": True,
            "safe_progress_available": False,
            "matched_comparator_required_now": False,
            "proof_rule": (
                "Every route that could strictly improve the least-cost objective "
                "is already disproved; or a verified sufficient route is already "
                "at the minimum remaining cost. Equal-cost alternatives cannot "
                "make the selected cost non-minimal."
            ),
            "terminal_results_replayed": 0,
            "new_reality_units_consumed": 0,
            "incremental_spend_usd": 0,
            "capability_credit_delta": 0,
            "family_credit_delta": 0,
            "execution_authority": False,
            "promotion_authority": False,
        }

    frontier_cost = min(row["cost"] for row in decision_relevant_unresolved)
    frontier = [
        row for row in decision_relevant_unresolved
        if row["cost"] == frontier_cost
    ]

    # Minimum-reality law: before paying comparator evidence, exhaust a safe
    # observation that can still remove the cheapest unresolved frontier.
    progress = [
        row for row in frontier
        if row["safe_unknown"]
    ]
    if progress:
        progress.sort(key=lambda row: row["tool_id"])
        chosen = progress[0]
        cap = sorted(chosen["safe_unknown"])[0]
        return {
            "schema": SCHEMA,
            "status": "SAFE_PROGRESS_REQUIRED__PROBE_BEFORE_MATCHED_EVIDENCE",
            "minimum_reality_action": "SAFE_PROBE",
            "identity_scope_complete": True,
            "required_capabilities": required,
            "best_verified_sufficient_cost": best_verified_cost,
            "verified_sufficient_tool_ids": [row["tool_id"] for row in verified],
            "ruled_out_tool_ids": ruled_out,
            "decision_frontier_cost": frontier_cost,
            "decision_frontier_tool_ids": [row["tool_id"] for row in frontier],
            "recommended_safe_probe": {
                "tool_id": chosen["tool_id"],
                "capability": cap,
                "reason": (
                    "CHEAPEST_UNRESOLVED_FRONTIER_HAS_SAFE_DECIDABLE_FACT__"
                    "RESULT_CAN_ELIMINATE_OR_ADVANCE_ROUTE_BEFORE_COMPARATOR_SPEND"
                ),
            },
            "irreducible_routes": [
                {
                    "tool_id": row["tool_id"],
                    "cost": row["cost"],
                    "unsafe_unknown_capabilities": sorted(row["unsafe_unknown"]),
                }
                for row in frontier if row["unsafe_unknown"]
            ],
            "universal_proof_eligible": False,
            "safe_progress_available": True,
            "matched_comparator_required_now": False,
            "proof_rule": (
                "Comparator evidence is not irreducible while a safe probe can "
                "still change membership of the cheapest unresolved cost frontier."
            ),
            "terminal_results_replayed": 0,
            "new_reality_units_consumed": 0,
            "incremental_spend_usd": 0,
            "capability_credit_delta": 0,
            "family_credit_delta": 0,
            "execution_authority": False,
            "promotion_authority": False,
        }

    # At the cheapest unresolved frontier, no remaining unknown fact is safely
    # observable. Two hidden worlds can therefore expose the same admitted
    # transcript while requiring different valid/least-cost terminal choices.
    irreducible = [
        {
            "tool_id": row["tool_id"],
            "cost": row["cost"],
            "unsafe_unknown_capabilities": sorted(row["unsafe_unknown"]),
        }
        for row in frontier
    ]
    return {
        "schema": SCHEMA,
        "status": "MATCHED_COMPARATOR_REQUIRED__IRREDUCIBLE_OBSERVABILITY_BOUND",
        "minimum_reality_action": "MATCHED_COMPARATOR",
        "identity_scope_complete": True,
        "required_capabilities": required,
        "best_verified_sufficient_cost": best_verified_cost,
        "verified_sufficient_tool_ids": [row["tool_id"] for row in verified],
        "ruled_out_tool_ids": ruled_out,
        "decision_frontier_cost": frontier_cost,
        "decision_frontier_tool_ids": [row["tool_id"] for row in frontier],
        "recommended_safe_probe": None,
        "irreducible_routes": irreducible,
        "universal_proof_eligible": False,
        "safe_progress_available": False,
        "matched_comparator_required_now": True,
        "proof_rule": (
            "After safe-observation closure at the cheapest unresolved frontier, "
            "at least one required fact remains unobservable. Observationally "
            "identical hidden worlds can require incompatible terminal actions; "
            "universal valid-plus-global-least-cost proof is impossible there."
        ),
        "terminal_results_replayed": 0,
        "new_reality_units_consumed": 0,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def main() -> int:
    demo = {
        "identity_scope_complete": True,
        "required_capabilities": ["A", "B"],
        "admissible_tools": [
            {
                "tool_id": "CHEAP",
                "cost": 1,
                "capability_evidence": {"A": "UNKNOWN", "B": "UNKNOWN"},
                "safe_probe_capabilities": ["B"],
            },
            {
                "tool_id": "KNOWN",
                "cost": 2,
                "capability_evidence": {"A": "SUPPORTED", "B": "SUPPORTED"},
                "safe_probe_capabilities": ["A", "B"],
            },
        ],
    }
    print(json.dumps(classify(demo), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
