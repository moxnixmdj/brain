"""Generated postwave acceptance state for Project Brain.

The current postwave frontier is derived from the frozen atomic registry, the
content-addressed evidence ledger, the action hypergraph, and non-authoritative
reconciliation candidates. It intentionally does not consume the older manually
maintained behavioral residual live input as acceptance authority.

This is a read model only. No execution, promotion, capability, or family credit.
"""
from __future__ import annotations

from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_GENERATED_POSTWAVE_ACCEPTANCE_STATE_V1"


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "errors": sorted(set(errors)),
        "execution_authority": False,
        "promotion_authority": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }


def evaluate(
    policy: Mapping[str, Any],
    registry: Mapping[str, Any],
    evidence: Mapping[str, Any],
    hypergraph: Mapping[str, Any],
    reconciliation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    if policy.get("schema") != "PROJECT_BRAIN_POSTWAVE_ACCEPTANCE_STATE_POLICY_V1":
        return _fail("POLICY_SCHEMA_INVALID")

    rows = registry.get("predicates")
    claims = evidence.get("claims")
    actions = hypergraph.get("actions")
    if not isinstance(rows, list):
        errors.append("PREDICATES_NOT_LIST")
        rows = []
    if not isinstance(claims, list):
        errors.append("CLAIMS_NOT_LIST")
        claims = []
    if not isinstance(actions, list):
        errors.append("ACTIONS_NOT_LIST")
        actions = []

    by_id: dict[str, Mapping[str, Any]] = {}
    family_ids: dict[str, list[str]] = {}
    for i, row in enumerate(rows):
        if not isinstance(row, Mapping):
            errors.append(f"PREDICATE_NOT_OBJECT:{i}")
            continue
        pid = row.get("id")
        family = row.get("family")
        if not isinstance(pid, str) or not pid or not isinstance(family, str) or not family:
            errors.append(f"PREDICATE_FIELDS_INVALID:{i}")
            continue
        if pid in by_id:
            errors.append("DUPLICATE_PREDICATE:" + pid)
            continue
        by_id[pid] = row
        family_ids.setdefault(family, []).append(pid)

    claim_by_id: dict[str, Mapping[str, Any]] = {}
    for i, claim in enumerate(claims):
        if not isinstance(claim, Mapping):
            errors.append(f"CLAIM_NOT_OBJECT:{i}")
            continue
        pid = claim.get("predicate_id")
        state = claim.get("state")
        if not isinstance(pid, str) or pid not in by_id:
            errors.append("UNKNOWN_CLAIM_PREDICATE:" + str(pid))
            continue
        if pid in claim_by_id:
            errors.append("DUPLICATE_CLAIM:" + pid)
            continue
        if state not in {"PROVED", "EXTERNAL_BLOCKED", "REFUTED"}:
            errors.append("CLAIM_STATE_INVALID:" + pid)
            continue
        if state == "PROVED":
            if claim.get("independent_or_objective") is not True:
                errors.append("PROVED_NOT_INDEPENDENT_OR_OBJECTIVE:" + pid)
            if claim.get("scope_complete") is not True:
                errors.append("PROVED_NOT_SCOPE_COMPLETE:" + pid)
        claim_by_id[pid] = claim

    action_cover: dict[str, list[str]] = {pid: [] for pid in by_id}
    for i, action in enumerate(actions):
        if not isinstance(action, Mapping) or not isinstance(action.get("id"), str):
            errors.append(f"ACTION_INVALID:{i}")
            continue
        aid = action["id"]
        targets = action.get("target_predicates")
        if not isinstance(targets, list):
            errors.append("ACTION_TARGETS_INVALID:" + aid)
            continue
        for pid in targets:
            if pid not in by_id:
                errors.append("ACTION_UNKNOWN_TARGET:" + aid + ":" + str(pid))
            else:
                action_cover[pid].append(aid)

    proof_candidates: dict[str, list[dict[str, Any]]] = {}
    scope_evidence: dict[str, list[dict[str, Any]]] = {}
    if reconciliation is not None:
        if reconciliation.get("status") != "PASS":
            errors.append("RECONCILIATION_NOT_PASS")
        for c in reconciliation.get("candidate_predicate_witnesses") or []:
            if isinstance(c, Mapping) and isinstance(c.get("predicate_id"), str):
                proof_candidates.setdefault(c["predicate_id"], []).append(dict(c))
        for c in reconciliation.get("scope_valid_terminal_evidence") or []:
            if isinstance(c, Mapping) and isinstance(c.get("predicate_id"), str):
                scope_evidence.setdefault(c["predicate_id"], []).append(dict(c))

    predicates: list[dict[str, Any]] = []
    proved = blocked = refuted = open_count = 0
    for pid, row in sorted(by_id.items()):
        claim = claim_by_id.get(pid)
        if claim is None:
            state = "OPEN"
            open_count += 1
        else:
            state = str(claim.get("state"))
            if state == "PROVED":
                proved += 1
            elif state == "EXTERNAL_BLOCKED":
                blocked += 1
            elif state == "REFUTED":
                refuted += 1
        live_targets = sorted(action_cover.get(pid) or [])
        if state != "PROVED" and not live_targets:
            errors.append("UNRESOLVED_WITHOUT_DISCHARGE_ACTION:" + pid)
        if state == "PROVED" and live_targets:
            errors.append("PROVED_STILL_TARGETED:" + pid)
        predicates.append({
            "predicate_id": pid,
            "family": row.get("family"),
            "kind": row.get("kind"),
            "state": state,
            "discharge_actions": live_targets,
            "candidate_witnesses": proof_candidates.get(pid, []),
            "scope_valid_terminal_evidence": scope_evidence.get(pid, []),
        })

    residual_families: list[dict[str, Any]] = []
    closed_residual = 0
    for family, ids in sorted(family_ids.items()):
        states = {p["predicate_id"]: p["state"] for p in predicates if p["predicate_id"] in ids}
        complete = bool(ids) and all(states.get(pid) == "PROVED" for pid in ids)
        if complete:
            closed_residual += 1
        residual_families.append({
            "family": family,
            "predicate_count": len(ids),
            "proved_predicate_count": sum(states.get(pid) == "PROVED" for pid in ids),
            "closed": complete,
            "open_predicates": sorted(pid for pid in ids if states.get(pid) != "PROVED"),
        })

    base_owned = policy.get("base_owned_families")
    if not isinstance(base_owned, list) or any(not isinstance(x, str) or not x for x in base_owned):
        errors.append("BASE_OWNED_FAMILIES_INVALID")
        base_owned = []

    total_family_count = int(policy.get("terminal_family_count", 0) or 0)
    if total_family_count != len(base_owned) + len(residual_families):
        errors.append("TERMINAL_FAMILY_COUNT_MISMATCH")

    total_closed = len(base_owned) + closed_residual
    return {
        "schema": SCHEMA,
        "status": "PASS" if not errors else "FAIL_CLOSED",
        "pass": not errors,
        "errors": sorted(set(errors)),
        "phase": "POSTWAVE_ACCEPTANCE",
        "predicate_count": len(by_id),
        "proved_predicate_count": proved,
        "external_blocked_predicate_count": blocked,
        "refuted_predicate_count": refuted,
        "open_predicate_count": open_count,
        "unresolved_predicate_count": len(by_id) - proved,
        "predicates": predicates,
        "base_owned_families": sorted(base_owned),
        "residual_families": residual_families,
        "closed_residual_family_count": closed_residual,
        "strict_closed_family_count": total_closed,
        "terminal_family_count": total_family_count,
        "global_terminal_promotion": total_closed == total_family_count and not errors,
        "legacy_behavioral_global_residual_live_input_authoritative": False,
        "rule": "POSTWAVE_ACCEPTANCE_TRUTH_IS_GENERATED_FROM_ATOMIC_REGISTRY_PLUS_CONTENT_ADDRESSED_EVIDENCE__RECONCILIATION_CANDIDATES_ARE_VISIBLE_BUT_NEVER_SELF_PROMOTE__OLDER_BEHAVIORAL_RESIDUAL_LIVE_INPUT_IS_NONAUTHORITATIVE_FOR_POSTWAVE_ACCEPTANCE",
        "execution_authority": False,
        "promotion_authority": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }
