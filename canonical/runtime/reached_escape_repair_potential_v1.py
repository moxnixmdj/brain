"""Well-founded repair potential for finite reached escape states.

This module turns the finite reached-state escape kernel into a reusable progress
theorem. It does not prove that a repair is always available. It proves that any
valid monotone repair which lowers the canonical potential makes strict
well-founded progress toward the already verified finite-totality certificate.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime import reached_escape_state_kernel_v1 as kernel
from canonical.runtime import reached_escape_finite_totality_certificate_v1 as finite_totality

SCHEMA = "PROJECT_BRAIN_REACHED_ESCAPE_REPAIR_POTENTIAL_V1"


def _common_policy_ids(state: Mapping[str, Any], region_ids: Sequence[str]) -> list[str]:
    wanted = set(region_ids)
    return sorted(
        row["policy_id"]
        for row in state["policies"]
        if wanted.issubset(set(row["adequate_region_ids"]))
    )


def _equivalence_classes(state: Mapping[str, Any]) -> list[dict[str, Any]]:
    discriminators = list(state["discriminators"])
    groups: dict[tuple[str, ...], list[str]] = {}
    for region in state["regions"]:
        rid = region["region_id"]
        signature = tuple(kernel._canon(row["outcomes"][rid]) for row in discriminators)
        groups.setdefault(signature, []).append(rid)

    out: list[dict[str, Any]] = []
    for signature, ids in sorted(groups.items(), key=lambda item: item[0]):
        ids = sorted(ids)
        common = _common_policy_ids(state, ids)
        out.append(
            {
                "region_ids": ids,
                "discriminator_signature": list(signature),
                "common_adequate_policy_ids": common,
                "conflicting": not bool(common),
            }
        )
    return out


def measure(state: Mapping[str, Any]) -> dict[str, Any]:
    try:
        normalized = kernel._normalize(state)
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": "STATE_NORMALIZATION_FAILED:" + type(exc).__name__ + ":" + str(exc),
            "repair_potential_defined": False,
            "terminal_credit_delta": 0,
        }

    region_ids = [row["region_id"] for row in normalized["regions"]]
    policy_sets = {
        rid: sorted(
            row["policy_id"]
            for row in normalized["policies"]
            if rid in row["adequate_region_ids"]
        )
        for rid in region_ids
    }
    uncovered = sorted(rid for rid, policies in policy_sets.items() if not policies)
    classes = _equivalence_classes(normalized)
    conflicts = [row for row in classes if row["conflicting"]]

    conflict_potential = sum(max(0, len(row["region_ids"]) - 1) for row in conflicts)
    n = len(region_ids)
    scalar = len(uncovered) * (n + 1) + conflict_potential

    finite = finite_totality.certify(state)
    zero_equivalence_holds = (scalar == 0) == (finite.get("pass") is True)

    return {
        "schema": SCHEMA,
        "pass": zero_equivalence_holds,
        "status": (
            "PASS__FINITE_WELL_FOUNDED_REPAIR_POTENTIAL"
            if zero_equivalence_holds
            else "FAIL_CLOSED__POTENTIAL_CERTIFICATE_EQUIVALENCE_BROKEN"
        ),
        "state_id": normalized["state_id"],
        "state_sha256": normalized["state_sha256"],
        "region_count": n,
        "uncovered_region_ids": uncovered,
        "uncovered_region_count": len(uncovered),
        "discriminator_equivalence_classes": classes,
        "conflicting_equivalence_classes": conflicts,
        "conflict_partition_potential": conflict_potential,
        "repair_potential": scalar,
        "repair_potential_defined": True,
        "repair_potential_nonnegative_integer": isinstance(scalar, int) and scalar >= 0,
        "repair_potential_zero": scalar == 0,
        "finite_totality_certificate_pass": finite.get("pass") is True,
        "zero_potential_iff_finite_totality_certificate": zero_equivalence_holds,
        "maximum_strict_repairs_before_certificate_if_each_repair_decreases_potential": scalar,
        "global_repair_acquirability_proved": False,
        "global_escape_progress_totality_proved": False,
        "terminal_credit_delta": 0,
    }


def _by_id(rows: Sequence[Mapping[str, Any]], key: str) -> dict[str, Mapping[str, Any]]:
    return {str(row[key]): row for row in rows}


def verify_monotone_repair(before: Mapping[str, Any], after: Mapping[str, Any]) -> dict[str, Any]:
    try:
        b = kernel._normalize(before)
        a = kernel._normalize(after)
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": "STATE_NORMALIZATION_FAILED:" + type(exc).__name__ + ":" + str(exc),
            "strict_progress_proved": False,
            "terminal_credit_delta": 0,
        }

    b_regions = [row["region_id"] for row in b["regions"]]
    a_regions = [row["region_id"] for row in a["regions"]]
    if b_regions != a_regions:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": "REGION_SET_DRIFT",
            "strict_progress_proved": False,
            "terminal_credit_delta": 0,
        }

    bp = _by_id(b["policies"], "policy_id")
    ap = _by_id(a["policies"], "policy_id")
    bd = _by_id(b["discriminators"], "discriminator_id")
    ad = _by_id(a["discriminators"], "discriminator_id")

    for pid, row in bp.items():
        if pid not in ap or dict(ap[pid]) != dict(row):
            return {
                "schema": SCHEMA,
                "pass": False,
                "status": "FAIL_CLOSED",
                "reason": "EXISTING_POLICY_CHANGED_OR_REMOVED:" + pid,
                "strict_progress_proved": False,
                "terminal_credit_delta": 0,
            }
    for did, row in bd.items():
        if did not in ad or dict(ad[did]) != dict(row):
            return {
                "schema": SCHEMA,
                "pass": False,
                "status": "FAIL_CLOSED",
                "reason": "EXISTING_DISCRIMINATOR_CHANGED_OR_REMOVED:" + did,
                "strict_progress_proved": False,
                "terminal_credit_delta": 0,
            }

    new_policy_ids = sorted(set(ap) - set(bp))
    new_discriminator_ids = sorted(set(ad) - set(bd))
    if not new_policy_ids and not new_discriminator_ids:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "NO_PROGRESS",
            "reason": "NO_MONOTONE_EXTENSION",
            "strict_progress_proved": False,
            "terminal_credit_delta": 0,
        }

    mb = measure(before)
    ma = measure(after)
    if mb.get("pass") is not True or ma.get("pass") is not True:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": "POTENTIAL_MEASURE_INVALID",
            "strict_progress_proved": False,
            "before_measure": mb,
            "after_measure": ma,
            "terminal_credit_delta": 0,
        }

    before_p = int(mb["repair_potential"])
    after_p = int(ma["repair_potential"])
    strict = after_p < before_p

    before_uncovered = set(mb["uncovered_region_ids"])
    after_uncovered = set(ma["uncovered_region_ids"])
    newly_covered = sorted(before_uncovered - after_uncovered)

    before_conflicts = [set(row["region_ids"]) for row in mb["conflicting_equivalence_classes"]]
    after_classes = [set(row["region_ids"]) for row in ma["discriminator_equivalence_classes"]]
    split_conflicts = sorted(
        sorted(c)
        for c in before_conflicts
        if any(part and part < c for part in after_classes if part.issubset(c))
    )

    return {
        "schema": SCHEMA,
        "pass": strict,
        "status": (
            "PASS__MONOTONE_REPAIR_STRICTLY_DECREASES_WELL_FOUNDED_POTENTIAL"
            if strict
            else "OPEN__MONOTONE_EXTENSION_WITHOUT_STRICT_PROGRESS"
        ),
        "strict_progress_proved": strict,
        "before_state_sha256": b["state_sha256"],
        "after_state_sha256": a["state_sha256"],
        "region_count": len(b_regions),
        "new_policy_ids": new_policy_ids,
        "new_discriminator_ids": new_discriminator_ids,
        "newly_covered_region_ids": newly_covered,
        "split_prior_conflict_classes": split_conflicts,
        "before_repair_potential": before_p,
        "after_repair_potential": after_p,
        "repair_potential_delta": after_p - before_p,
        "after_finite_totality_certificate_pass": ma["finite_totality_certificate_pass"],
        "global_repair_acquirability_proved": False,
        "global_escape_progress_totality_proved": False,
        "terminal_credit_delta": 0,
    }


def theorem() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "PROVED_REDUCTION_LAW__REPAIR_PROVIDER_TOTALITY_REMAINS_OPEN",
        "potential": "U*(N+1)+SUM_CONFLICT_CLASSES(|C|-1)",
        "where": {
            "U": "NUMBER_OF_REGIONS_WITH_NO_AUTHENTICATED_SAFE_ADEQUATE_POLICY",
            "N": "FIXED_FINITE_REGION_COUNT",
            "C": "DISCRIMINATOR_EQUIVALENCE_CLASS_WITHOUT_ONE_COMMON_AUTHENTICATED_SAFE_ADEQUATE_POLICY",
        },
        "proved": [
            "POTENTIAL_IS_A_NONNEGATIVE_INTEGER",
            "POTENTIAL_ZERO_IFF_THE_EXISTING_FINITE_REACHED_STATE_TOTALITY_CERTIFICATE_PASSES",
            "ANY_ACCEPTED_MONOTONE_REPAIR_MUST_STRICTLY_DECREASE_POTENTIAL",
            "A_SEQUENCE_OF_STRICT_REPAIRS_REACHES_CERTIFICATE_ELIGIBILITY_IN_AT_MOST_INITIAL_POTENTIAL_STEPS",
        ],
        "not_proved": [
            "A_VALID_REPAIR_IS_ALWAYS_ACQUIRABLE",
            "ANY_SPECIFIC_INTERNAL_ROUTE_ACTION_SATISFIES_THE_REPAIR_CONTRACT",
            "GLOBAL_ESCAPE_PROGRESS_TOTALITY",
            "CC_R3",
        ],
        "terminal_credit_delta": 0,
    }
