"""Exact acceptance backpropagation for frozen binary benchmark populations.

This compiler reverses a frozen binary-rate acceptance threshold into the weakest
remaining success mass required after independently verified proof/observation
partitions are applied.

Positive partitions must bind explicit frozen population slot IDs to an independently
verified scope-complete content-addressed receipt. The compiler recomputes the frozen
population commitment, requires every partition to bind that exact commitment, and
rejects overlap so a slot can never be counted twice.

The output is scheduling evidence only. It grants no execution, capability, family,
promotion, acceptance, or terminal authority.
"""
from __future__ import annotations

import hashlib
import json
import re
from decimal import Decimal, ROUND_CEILING
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_ACCEPTANCE_BACKPROP_INPUT_V1"
OUT_SCHEMA = "PROJECT_BRAIN_ACCEPTANCE_BACKPROP_VERDICT_V1"

CREDITING_OUTCOMES = {
    "PROVED_PASS",
    "PROVED_FAIL",
    "OBSERVED_PASS",
    "OBSERVED_FAIL",
}
_HEX_RE = re.compile(r"^[0-9a-fA-F]+$")


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": OUT_SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "errors": sorted(set(errors)),
        "decision": "UNRESOLVED",
        "execution_authority": False,
        "promotion_authority": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "terminal_credit_delta": 0,
        "new_reality_units_consumed": 0,
    }


def _dec(v: Any) -> Decimal | None:
    if isinstance(v, bool) or not isinstance(v, (int, float, str, Decimal)):
        return None
    try:
        d = Decimal(str(v))
    except Exception:
        return None
    return d if d.is_finite() else None


def _ceil_decimal(x: Decimal) -> int:
    return int(x.to_integral_value(rounding=ROUND_CEILING))


def _string_list(v: Any) -> list[str] | None:
    if not isinstance(v, Sequence) or isinstance(v, (str, bytes)):
        return None
    out = list(v)
    if any(not isinstance(x, str) or not x for x in out):
        return None
    if len(out) != len(set(out)):
        return None
    return out


def population_commitment_sha256(population_ids: Sequence[str]) -> str:
    ids = _string_list(population_ids)
    if not ids:
        raise ValueError("population_ids must be unique nonempty strings")
    raw = json.dumps(sorted(ids), separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _valid_digest(v: Any) -> bool:
    return (
        isinstance(v, str)
        and len(v) in {40, 64}
        and _HEX_RE.fullmatch(v) is not None
    )


def evaluate(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return _fail("INPUT_NOT_OBJECT")
    if payload.get("schema") != SCHEMA:
        return _fail("SCHEMA_INVALID")
    if payload.get("metric_semantics_frozen") is not True:
        return _fail("METRIC_SEMANTICS_NOT_FROZEN")
    if payload.get("population_frozen") is not True:
        return _fail("POPULATION_NOT_FROZEN")
    if payload.get("scorer_identity_bound") is not True:
        return _fail("SCORER_IDENTITY_NOT_BOUND")
    if payload.get("metric_type") != "BINARY_RATE":
        return _fail("UNSUPPORTED_METRIC_TYPE")

    population_ids = _string_list(payload.get("population_ids"))
    if not population_ids:
        return _fail("POPULATION_IDS_INVALID")
    population = set(population_ids)

    computed_commitment = population_commitment_sha256(population_ids)
    declared_commitment = payload.get("population_commitment_sha256")
    if declared_commitment != computed_commitment:
        return _fail("POPULATION_COMMITMENT_MISMATCH")

    threshold = _dec(payload.get("threshold_percent"))
    if threshold is None or threshold < 0 or threshold > 100:
        return _fail("THRESHOLD_PERCENT_INVALID")

    partitions = payload.get("partitions", [])
    if not isinstance(partitions, list):
        return _fail("PARTITIONS_NOT_LIST")

    errors: list[str] = []
    claimed_slots: dict[str, str] = {}
    normalized: list[dict[str, Any]] = []
    proved_pass_slots: set[str] = set()
    proved_fail_slots: set[str] = set()
    observed_pass_slots: set[str] = set()
    observed_fail_slots: set[str] = set()
    seen_partition_ids: set[str] = set()

    for i, row in enumerate(partitions):
        if not isinstance(row, Mapping):
            errors.append(f"PARTITION_NOT_OBJECT:{i}")
            continue

        pid = row.get("partition_id")
        if not isinstance(pid, str) or not pid:
            errors.append(f"PARTITION_ID_INVALID:{i}")
            continue
        if pid in seen_partition_ids:
            errors.append(f"PARTITION_ID_DUPLICATE:{pid}")
            continue
        seen_partition_ids.add(pid)

        outcome = row.get("outcome")
        if outcome not in CREDITING_OUTCOMES:
            errors.append(f"PARTITION_OUTCOME_INVALID:{pid}")
            continue

        slot_ids = _string_list(row.get("slot_ids"))
        if not slot_ids:
            errors.append(f"PARTITION_SLOT_IDS_INVALID:{pid}")
            continue

        outside = sorted(set(slot_ids) - population)
        if outside:
            errors.append(f"PARTITION_OUTSIDE_POPULATION:{pid}:" + ",".join(outside))
            continue

        if row.get("population_commitment_sha256") != computed_commitment:
            errors.append(f"PARTITION_POPULATION_COMMITMENT_MISMATCH:{pid}")

        receipt_path = row.get("receipt_path")
        receipt_sha = row.get("receipt_sha")
        if not isinstance(receipt_path, str) or not receipt_path:
            errors.append(f"CONTENT_ADDRESSED_RECEIPT_PATH_REQUIRED:{pid}")
        if not _valid_digest(receipt_sha):
            errors.append(f"CONTENT_ADDRESSED_RECEIPT_SHA_REQUIRED:{pid}")
        if row.get("independent_verified") is not True:
            errors.append(f"INDEPENDENT_VERIFICATION_REQUIRED:{pid}")
        if row.get("scope_complete") is not True:
            errors.append(f"SCOPE_COMPLETENESS_REQUIRED:{pid}")

        overlap = [sid for sid in slot_ids if sid in claimed_slots]
        if overlap:
            errors.append(
                f"PARTITION_OVERLAP:{pid}:"
                + ",".join(sorted(overlap))
                + ":WITH:"
                + ",".join(sorted({claimed_slots[sid] for sid in overlap}))
            )
            continue

        for sid in slot_ids:
            claimed_slots[sid] = pid

        dest = (
            proved_pass_slots
            if outcome == "PROVED_PASS"
            else proved_fail_slots
            if outcome == "PROVED_FAIL"
            else observed_pass_slots
            if outcome == "OBSERVED_PASS"
            else observed_fail_slots
        )
        dest.update(slot_ids)

        normalized.append(
            {
                "partition_id": pid,
                "outcome": outcome,
                "slot_count": len(slot_ids),
                "population_commitment_sha256": computed_commitment,
                "receipt_path": receipt_path if isinstance(receipt_path, str) else None,
                "receipt_sha": receipt_sha if isinstance(receipt_sha, str) else None,
            }
        )

    if errors:
        return _fail(*errors)

    total = len(population_ids)
    required = _ceil_decimal((threshold * Decimal(total)) / Decimal(100))

    proved_passes = len(proved_pass_slots)
    proved_failures = len(proved_fail_slots)
    observed_passes = len(observed_pass_slots)
    observed_failures = len(observed_fail_slots)

    credited_passes = proved_passes + observed_passes
    credited_failures = proved_failures + observed_failures
    unknown_slots = sorted(population - set(claimed_slots))
    unknown_count = len(unknown_slots)

    lower_successes = credited_passes
    upper_successes = credited_passes + unknown_count

    if lower_successes >= required:
        decision = "PASS_LOCKED"
    elif upper_successes < required:
        decision = "FAIL_LOCKED"
    else:
        decision = "UNRESOLVED"

    additional_success_mass = max(0, required - lower_successes)
    maximum_tolerable_additional_failures = (
        max(0, unknown_count - additional_success_mass)
        if decision == "UNRESOLVED"
        else 0
    )

    return {
        "schema": OUT_SCHEMA,
        "status": "PASS",
        "pass": True,
        "errors": [],
        "metric_type": "BINARY_RATE",
        "decision": decision,
        "population_size": total,
        "population_commitment_sha256": computed_commitment,
        "threshold_percent": str(threshold),
        "threshold_success_count": required,
        "proved_passes": proved_passes,
        "proved_failures": proved_failures,
        "observed_passes": observed_passes,
        "observed_failures": observed_failures,
        "credited_passes": credited_passes,
        "credited_failures": credited_failures,
        "unknown_count": unknown_count,
        "conservative_success_lower_bound": lower_successes,
        "optimistic_success_upper_bound": upper_successes,
        "minimum_additional_success_mass_required": additional_success_mass,
        "maximum_tolerable_additional_failures_before_fail_lock": maximum_tolerable_additional_failures,
        "unknown_slot_ids": unknown_slots,
        "normalized_partitions": sorted(normalized, key=lambda x: x["partition_id"]),
        "weakest_sufficient_residual": {
            "kind": "ADDITIONAL_SUCCESS_MASS",
            "count": additional_success_mass,
            "domain": "CURRENT_UNKNOWN_FROZEN_POPULATION_SLOTS",
            "note": (
                "May be discharged by stronger formal proof, exact receipt reuse, or fresh observation; "
                "this compiler does not authorize which route."
            ),
        },
        "rule": (
            "EXACT_FROZEN_BINARY_POPULATION_ONLY__POPULATION_COMMITMENT_RECOMPUTED__"
            "PROOF_AND_OBSERVATION_PARTITIONS_REQUIRE_EXACT_COMMITMENT_PLUS_INDEPENDENT_SCOPE_COMPLETE_"
            "CONTENT_ADDRESSED_RECEIPT__NO_DOUBLE_COUNT__NO_SEMANTIC_GUESSING__"
            "NO_EXECUTION_OR_ACCEPTANCE_CREDIT_FROM_COMPILATION_ALONE"
        ),
        "execution_authority": False,
        "promotion_authority": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "terminal_credit_delta": 0,
        "new_reality_units_consumed": 0,
    }
