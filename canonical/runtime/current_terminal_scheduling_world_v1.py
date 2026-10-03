"""Compile the live terminal scheduling world from frozen predicates and current receipts.

This is a scheduling-only, zero-credit compiler. It refuses to inherit a stale
frontier count from historical activation files. The live unresolved predicate
set is derived as:

    frozen registry - {PROVED, REFUTED current evidence claims}

Historical certificate/action documents may be reused only after terminal
targets are removed and exact current coverage is rechecked.
"""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_CURRENT_TERMINAL_SCHEDULING_WORLD_V1"
TERMINAL_STATES = {"PROVED", "REFUTED"}


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "errors": sorted(set(errors)),
        "execution_authority": False,
        "promotion_authority": False,
        "fresh_reality_authority": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }


def _ids_from_registry(registry: Mapping[str, Any]) -> tuple[list[str], dict[str, Mapping[str, Any]], list[str]]:
    errors: list[str] = []
    rows = registry.get("predicates")
    if not isinstance(rows, list):
        return [], {}, ["PREDICATE_REGISTRY_NOT_LIST"]
    ids: list[str] = []
    by_id: dict[str, Mapping[str, Any]] = {}
    for i, row in enumerate(rows):
        if not isinstance(row, Mapping):
            errors.append(f"INVALID_PREDICATE_ROW:{i}")
            continue
        pid = row.get("id")
        if not isinstance(pid, str) or not pid:
            errors.append(f"INVALID_PREDICATE_ID:{i}")
            continue
        if pid in by_id:
            errors.append(f"DUPLICATE_PREDICATE:{pid}")
            continue
        ids.append(pid)
        by_id[pid] = row
    return ids, by_id, errors


def evaluate(
    registry: Mapping[str, Any],
    evidence: Mapping[str, Any],
    frontier: Mapping[str, Any],
    hypergraph: Mapping[str, Any],
    scheduling: Mapping[str, Any],
    authority: Mapping[str, Any],
) -> dict[str, Any]:
    registry_ids, registry_by_id, errors = _ids_from_registry(registry)
    registry_set = set(registry_ids)

    claims = evidence.get("claims")
    if not isinstance(claims, list):
        return _fail(*(errors + ["EVIDENCE_CLAIMS_NOT_LIST"]))

    states: dict[str, str] = {}
    allowed_states = {"OPEN", "PROVED", "REFUTED", "EXTERNAL_BLOCKED"}
    for i, claim in enumerate(claims):
        if not isinstance(claim, Mapping):
            errors.append(f"INVALID_EVIDENCE_CLAIM:{i}")
            continue
        pid = claim.get("predicate_id")
        state = claim.get("state")
        if not isinstance(pid, str) or pid not in registry_set:
            errors.append(f"EVIDENCE_UNKNOWN_PREDICATE:{pid}")
            continue
        if pid in states:
            errors.append(f"DUPLICATE_EVIDENCE_CLAIM:{pid}")
            continue
        if state not in allowed_states:
            errors.append(f"INVALID_EVIDENCE_STATE:{pid}:{state}")
            continue
        states[pid] = state

    terminal = {pid for pid, state in states.items() if state in TERMINAL_STATES}
    proved = {pid for pid, state in states.items() if state == "PROVED"}
    refuted = {pid for pid, state in states.items() if state == "REFUTED"}
    unresolved = [pid for pid in registry_ids if pid not in terminal]
    unresolved_set = set(unresolved)

    old_front = frontier.get("unresolved_predicates")
    if not isinstance(old_front, list):
        errors.append("FRONTIER_UNRESOLVED_NOT_LIST")
        old_front = []
    old_front_set = {x for x in old_front if isinstance(x, str)}

    certificates = frontier.get("certificates")
    if not isinstance(certificates, list):
        errors.append("FRONTIER_CERTIFICATES_NOT_LIST")
        certificates = []
    live_certificates: list[dict[str, Any]] = []
    removed_certificate_targets: list[dict[str, str]] = []
    for i, raw in enumerate(certificates):
        if not isinstance(raw, Mapping):
            errors.append(f"INVALID_CERTIFICATE:{i}")
            continue
        row = deepcopy(dict(raw))
        targets = row.get("target_predicates")
        if not isinstance(targets, list):
            errors.append(f"CERTIFICATE_TARGETS_NOT_LIST:{row.get('id')}")
            continue
        keep: list[str] = []
        for pid in targets:
            if pid not in registry_set:
                errors.append(f"CERTIFICATE_UNKNOWN_TARGET:{row.get('id')}:{pid}")
                continue
            if pid in unresolved_set:
                keep.append(pid)
            else:
                removed_certificate_targets.append({
                    "certificate_id": str(row.get("id")),
                    "predicate_id": pid,
                    "state": states.get(pid, "TERMINAL"),
                })
        if keep:
            row["target_predicates"] = keep
            live_certificates.append(row)

    actions = hypergraph.get("actions")
    if not isinstance(actions, list):
        errors.append("HYPERGRAPH_ACTIONS_NOT_LIST")
        actions = []
    live_actions: list[dict[str, Any]] = []
    removed_action_targets: list[dict[str, str]] = []
    for i, raw in enumerate(actions):
        if not isinstance(raw, Mapping):
            errors.append(f"INVALID_ACTION:{i}")
            continue
        row = deepcopy(dict(raw))
        targets = row.get("target_predicates", [])
        if not isinstance(targets, list):
            errors.append(f"ACTION_TARGETS_NOT_LIST:{row.get('id')}")
            continue
        keep: list[str] = []
        for pid in targets:
            if pid not in registry_set:
                errors.append(f"ACTION_UNKNOWN_TARGET:{row.get('id')}:{pid}")
                continue
            if pid in unresolved_set:
                keep.append(pid)
            else:
                removed_action_targets.append({
                    "action_id": str(row.get("id")),
                    "predicate_id": pid,
                    "state": states.get(pid, "TERMINAL"),
                })
        if keep:
            row["target_predicates"] = keep
            live_actions.append(row)

    covered = {
        pid
        for action in live_actions
        for pid in action.get("target_predicates", [])
        if isinstance(pid, str)
    }
    uncovered = sorted(unresolved_set - covered)
    overcovered = sorted(covered - unresolved_set)
    if uncovered:
        errors.append("UNRESOLVED_WITHOUT_ACTION_EDGE:" + ",".join(uncovered))
    if overcovered:
        errors.append("NONLIVE_ACTION_EDGE:" + ",".join(overcovered))

    truth = authority.get("truth")
    if not isinstance(truth, Mapping):
        errors.append("AUTHORITY_TRUTH_NOT_OBJECT")
        truth = {}
    if truth.get("contracts") != "12/12_WHOLE_SCOPE_PASS__P1_SCOPE_RESTORED_BY_INDEPENDENT_ZERO_REALITY_UNIVERSAL_PROOF":
        errors.append("AUTHORITY_CONTRACT_WORLD_NOT_CURRENT")
    if truth.get("behavioral_families") != "19/19_PROVISIONAL_BEHAVIORAL_PASS__P1_SCOPE_QUARANTINE_CLEARED__STRICT_OPUS55_ACCEPTANCE_SEPARATE":
        errors.append("AUTHORITY_BEHAVIORAL_WORLD_NOT_CURRENT")
    if truth.get("opus55_acceptance") != "3/19_PASS__16/19_OPEN":
        errors.append("AUTHORITY_ACCEPTANCE_WORLD_NOT_3_OF_19")

    if len(registry_ids) != 38:
        errors.append(f"REGISTRY_COUNT_NOT_38:{len(registry_ids)}")
    if len(proved) != 8:
        errors.append(f"PROVED_COUNT_NOT_8:{len(proved)}")
    if len(unresolved) != 30:
        errors.append(f"UNRESOLVED_COUNT_NOT_30:{len(unresolved)}")

    scheduled_frontier = scheduling.get("frontier")
    scheduled_hypergraph = scheduling.get("action_hypergraph")
    scheduled_unresolved = scheduled_frontier.get("unresolved_predicates") if isinstance(scheduled_frontier, Mapping) else None
    scheduled_coverage = scheduled_hypergraph.get("current_unresolved_predicate_coverage") if isinstance(scheduled_hypergraph, Mapping) else None

    stale_reasons: list[str] = []
    if old_front_set != unresolved_set:
        stale_reasons.append("FRONTIER_V5_PREDICATE_SET_DIFFERS_FROM_LIVE_RECEIPT_DERIVED_SET")
    if scheduled_unresolved != len(unresolved):
        stale_reasons.append(f"SCHEDULING_V6_UNRESOLVED_COUNT_{scheduled_unresolved}_NE_LIVE_{len(unresolved)}")
    if scheduled_coverage != len(unresolved):
        stale_reasons.append(f"SCHEDULING_V6_ACTION_COVERAGE_{scheduled_coverage}_NE_LIVE_{len(unresolved)}")
    if removed_action_targets:
        stale_reasons.append("HYPERGRAPH_V2_CONTAINS_TERMINAL_TARGETS")
    if removed_certificate_targets:
        stale_reasons.append("FRONTIER_V5_CONTAINS_TERMINAL_TARGETS")

    kind_counts: dict[str, int] = {}
    family_counts: dict[str, int] = {}
    for pid in unresolved:
        row = registry_by_id[pid]
        kind = str(row.get("kind") or "UNKNOWN")
        family = str(row.get("family") or "UNKNOWN")
        kind_counts[kind] = kind_counts.get(kind, 0) + 1
        family_counts[family] = family_counts.get(family, 0) + 1

    if errors:
        return _fail(*errors)

    return {
        "schema": SCHEMA,
        "status": "PASS__LIVE_30_PREDICATE_WORLD_COMPILED__STALE_31_WORLD_REJECTED",
        "pass": True,
        "registry_predicate_count": len(registry_ids),
        "proved_predicate_count": len(proved),
        "refuted_predicate_count": len(refuted),
        "unresolved_predicate_count": len(unresolved),
        "proved_predicates": sorted(proved),
        "unresolved_predicates": unresolved,
        "unresolved_kind_counts": dict(sorted(kind_counts.items())),
        "unresolved_family_counts": dict(sorted(family_counts.items())),
        "live_certificate_count": len(live_certificates),
        "live_certificates": live_certificates,
        "live_action_count": len(live_actions),
        "live_actions": live_actions,
        "live_action_coverage_count": len(covered),
        "uncovered_predicates": uncovered,
        "removed_terminal_certificate_targets": removed_certificate_targets,
        "removed_terminal_action_targets": removed_action_targets,
        "source_scheduling_world_stale": bool(stale_reasons),
        "source_scheduling_world_stale_reasons": sorted(stale_reasons),
        "legacy_authority_next": authority.get("next"),
        "required_next": (
            "INDEPENDENTLY_VERIFY_THIS_RECEIPT_DERIVED_30_PREDICATE_WORLD__"
            "RECOMPUTE_ZERO_REALITY_INFORMATION_DOMINANCE_AND_PROOF_FIRST_FRONTIER__"
            "ONLY_IF_NO_NONDOMINATED_ZERO_REALITY_ACTION_REMAINS_MAY_CURRENT_FRESH_REALITY_AUTHORITY_EXECUTE"
        ),
        "rule": (
            "LIVE_SCHEDULING_STATE_IS_DERIVED_FROM_FROZEN_REGISTRY_MINUS_CURRENT_TERMINAL_RECEIPTS__"
            "HISTORICAL_FRONTIER_COUNTS_NEVER_GRANT_EXECUTION_AUTHORITY"
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
    )
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out.get("pass") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
