"""Exact observability partition for Tool Discovery.

This module does not grant Tool Discovery acceptance. It compiles the
information-theoretic lower bound into a finite decision rule after identity
scope is complete:

- if every route that can still change the least-cost decision is already
  decided or safely decidable, universal program-side proof remains eligible;
- if an unresolved route can change the least-cost decision and at least one
  required capability is neither evidenced nor safely probeable, a universal
  valid+least-cost guarantee is impossible from the admitted observation and
  matched comparator evidence is required for that partition.

The input is deliberately abstract. It is a post-filter capability-observation
state, so deterministic schema/authorization/constraint filtering happens
before this classifier.
"""
from __future__ import annotations

import json
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_TOOL_DISCOVERY_OBSERVABILITY_PARTITION_V1"

TRUE = "SUPPORTED"
FALSE = "UNSUPPORTED"
UNKNOWN = "UNKNOWN"
VALID_STATES = {TRUE, FALSE, UNKNOWN}


def _fail(reason: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED__INVALID_PARTITION_INPUT",
        "reason": reason,
        "universal_proof_eligible": False,
        "matched_comparator_required": True,
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
        if isinstance(cost, bool) or not isinstance(cost, (int, float)) or float(cost) < 0:
            return _fail("TOOL_COST_INVALID:" + tid)

        evidence = raw.get("capability_evidence", {})
        if not isinstance(evidence, Mapping):
            return _fail("CAPABILITY_EVIDENCE_NOT_OBJECT:" + tid)
        safe = raw.get("safe_probe_capabilities", [])
        if not isinstance(safe, list):
            return _fail("SAFE_PROBE_CAPABILITIES_NOT_LIST:" + tid)
        safe_set = {str(x) for x in safe}

        states: dict[str, str] = {}
        for cap in required:
            value = str(evidence.get(cap, UNKNOWN))
            if value not in VALID_STATES:
                return _fail("CAPABILITY_EVIDENCE_STATE_INVALID:" + tid + ":" + cap)
            states[cap] = value

        tools.append({
            "tool_id": tid,
            "cost": float(cost),
            "states": states,
            "safe": safe_set,
        })

    tools.sort(key=lambda row: (row["cost"], row["tool_id"]))

    verified = [
        row for row in tools
        if all(row["states"][cap] == TRUE for cap in required)
    ]
    best_verified = min((row["cost"] for row in verified), default=None)

    ambiguous: list[dict[str, Any]] = []
    resolvable: list[dict[str, Any]] = []
    ruled_out: list[str] = []
    for row in tools:
        states = row["states"]
        if any(states[cap] == FALSE for cap in required):
            ruled_out.append(row["tool_id"])
            continue

        unknown = [cap for cap in required if states[cap] == UNKNOWN]
        if not unknown:
            continue

        unobservable = [cap for cap in unknown if cap not in row["safe"]]
        can_change_decision = (
            best_verified is None or row["cost"] <= best_verified
        )

        if can_change_decision and unobservable:
            ambiguous.append({
                "tool_id": row["tool_id"],
                "cost": row["cost"],
                "unknown_capabilities": unknown,
                "unobservable_capabilities": unobservable,
                "decision_relevance": (
                    "NO_VERIFIED_SUFFICIENT_ROUTE_EXISTS"
                    if best_verified is None
                    else "COST_NOT_GREATER_THAN_BEST_VERIFIED_ROUTE"
                ),
            })
        else:
            resolvable.append({
                "tool_id": row["tool_id"],
                "cost": row["cost"],
                "unknown_capabilities": unknown,
                "all_decision_relevant_unknowns_safe_probe_decidable": not unobservable,
                "cannot_improve_current_best_verified_cost": (
                    best_verified is not None and row["cost"] > best_verified
                ),
            })

    matched_required = bool(ambiguous)
    return {
        "schema": SCHEMA,
        "status": (
            "MATCHED_COMPARATOR_REQUIRED__UNOBSERVABLE_DECISION_RELEVANT_FACT"
            if matched_required
            else "UNIVERSAL_PROGRAM_SIDE_PROOF_ELIGIBLE__OBSERVABILITY_COMPLETE_FOR_DECISION"
        ),
        "identity_scope_complete": True,
        "required_capabilities": required,
        "best_verified_sufficient_cost": best_verified,
        "verified_sufficient_tool_ids": [row["tool_id"] for row in verified],
        "ruled_out_tool_ids": ruled_out,
        "resolvable_unknown_routes": resolvable,
        "ambiguous_decision_relevant_routes": ambiguous,
        "universal_proof_eligible": not matched_required,
        "matched_comparator_required": matched_required,
        "proof_rule": (
            "A universal valid-and-global-least-cost proof is inadmissible iff an "
            "admissible route can still change the least-cost decision while at "
            "least one decision-relevant required capability is neither currently "
            "evidenced nor safely probe-decidable."
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
    example = {
        "identity_scope_complete": True,
        "required_capabilities": ["CAP_A"],
        "admissible_tools": [
            {
                "tool_id": "CHEAP",
                "cost": 1,
                "capability_evidence": {"CAP_A": "UNKNOWN"},
                "safe_probe_capabilities": [],
            },
            {
                "tool_id": "EXPENSIVE",
                "cost": 2,
                "capability_evidence": {"CAP_A": "SUPPORTED"},
                "safe_probe_capabilities": ["CAP_A"],
            },
        ],
    }
    print(json.dumps(classify(example), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
