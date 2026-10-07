"""Structural common-policy decision-region gate.

This module proves only a set-containment fact:
all surviving interpretation IDs are contained in at least one declared policy
adequacy region. It does NOT prove that the declared regions are semantically
sound. Region soundness must come from a separate Brain-owned adequacy
certificate. Therefore this module has no terminal authority by itself.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

SCHEMA = "BRAIN_COMMON_POLICY_DECISION_REGION_GATE_V1"


def common_policy_region(
    surviving_interpretations: Sequence[str],
    policy_regions: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    errors: list[str] = []
    if (
        not isinstance(surviving_interpretations, Sequence)
        or isinstance(surviving_interpretations, (str, bytes))
        or not surviving_interpretations
        or any(not isinstance(x, str) or not x for x in surviving_interpretations)
    ):
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": ["SURVIVING_INTERPRETATIONS_INVALID_OR_EMPTY"],
            "terminal_authority": False,
        }

    survivors = set(surviving_interpretations)
    if len(survivors) != len(surviving_interpretations):
        errors.append("SURVIVING_INTERPRETATION_DUPLICATE")

    if not isinstance(policy_regions, Mapping) or not policy_regions:
        errors.append("POLICY_REGIONS_INVALID_OR_EMPTY")

    normalized: dict[str, dict[str, Any]] = {}
    for pid, row in policy_regions.items() if isinstance(policy_regions, Mapping) else []:
        if not isinstance(pid, str) or not pid:
            errors.append("POLICY_ID_INVALID")
            continue
        if not isinstance(row, Mapping):
            errors.append(f"POLICY_REGION_NOT_OBJECT:{pid}")
            continue
        ids = row.get("interpretation_ids")
        certificate_id = row.get("adequacy_certificate_id")
        if (
            not isinstance(ids, Sequence)
            or isinstance(ids, (str, bytes))
            or any(not isinstance(x, str) or not x for x in ids)
        ):
            errors.append(f"POLICY_REGION_INTERPRETATIONS_INVALID:{pid}")
            continue
        if not isinstance(certificate_id, str) or not certificate_id:
            errors.append(f"POLICY_REGION_CERTIFICATE_ID_MISSING:{pid}")
            continue
        normalized[pid] = {
            "interpretation_ids": sorted(set(ids)),
            "adequacy_certificate_id": certificate_id,
        }

    if errors:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": sorted(set(errors)),
            "terminal_authority": False,
        }

    common = []
    for pid, row in normalized.items():
        region = set(row["interpretation_ids"])
        if survivors.issubset(region):
            common.append({
                "policy_id": pid,
                "adequacy_certificate_id": row["adequacy_certificate_id"],
            })

    common.sort(key=lambda x: (x["policy_id"], x["adequacy_certificate_id"]))
    return {
        "schema": SCHEMA,
        "status": "COMMON_POLICY_REGION" if common else "DISCRIMINATOR_REQUIRED",
        "surviving_interpretations": sorted(survivors),
        "common_policy_regions": common,
        "unique_interpretation_required": False,
        "terminal_authority": False,
        "soundness_boundary": (
            "THIS_GATE_PROVES_ONLY_REGION_SET_CONTAINMENT;"
            "THE REFERENCED ADEQUACY CERTIFICATE MUST INDEPENDENTLY PROVE REGION SOUNDNESS"
        ),
    }
