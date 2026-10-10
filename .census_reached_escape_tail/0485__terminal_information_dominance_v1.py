"""Exact zero-credit information-dominance optimizer for terminal certificates.

This sits above the terminal certificate cut. It does not claim that satisfying a
certificate proves any acceptance predicate. Instead it reasons only about the
scheduler's declared coverage and required verified propositions.

It adds three things the basic certificate cut intentionally does not:
1. exact detection of dominated single certificates,
2. exact full-frontier structural compression over all certificate subsets,
3. bounded conjunctive synergy analysis over small certificate bundles.

"Requirement count" is a structural cardinality, not an estimate of difficulty,
time, probability, or proof cost. Unknown proof effort remains unknown.
"""
from __future__ import annotations

from itertools import combinations
import json
from math import isfinite
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_TERMINAL_INFORMATION_DOMINANCE_V1"
MAX_EXACT_CERTIFICATES = 20
DEFAULT_MAX_SYNERGY_ORDER = 3


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "errors": sorted(set(errors)),
        "dominated_certificate_ids": [],
        "nondominated_certificate_ids": [],
        "best_full_frontier_bundle": None,
        "synergy_bundles": [],
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def _dominates(a: Mapping[str, Any], b: Mapping[str, Any]) -> bool:
    return (
        a["targets"] >= b["targets"]
        and a["requires"] <= b["requires"]
        and a["reality"] <= b["reality"]
        and (
            a["targets"] > b["targets"]
            or a["requires"] < b["requires"]
            or a["reality"] < b["reality"]
        )
    )


def evaluate(
    doc: Mapping[str, Any],
    *,
    max_synergy_order: int = DEFAULT_MAX_SYNERGY_ORDER,
) -> dict[str, Any]:
    if not isinstance(doc, Mapping):
        return _fail("INPUT_NOT_OBJECT")

    unresolved = doc.get("unresolved_predicates")
    certificates = doc.get("certificates")
    if (
        not isinstance(unresolved, list)
        or not unresolved
        or any(not isinstance(x, str) or not x for x in unresolved)
        or len(set(unresolved)) != len(unresolved)
    ):
        return _fail("UNRESOLVED_PREDICATES_INVALID")
    if not isinstance(certificates, list) or not certificates:
        return _fail("CERTIFICATES_INVALID")
    if (
        isinstance(max_synergy_order, bool)
        or not isinstance(max_synergy_order, int)
        or max_synergy_order < 1
    ):
        return _fail("MAX_SYNERGY_ORDER_INVALID")

    unresolved_set = set(unresolved)
    parsed: list[dict[str, Any]] = []
    ids: set[str] = set()

    for i, row in enumerate(certificates):
        if not isinstance(row, Mapping):
            return _fail(f"CERTIFICATE_{i}_INVALID")
        cid = row.get("id")
        targets = row.get("target_predicates")
        requires = row.get("requires", [])
        raw_reality = row.get("new_reality_units", 0)

        if not isinstance(cid, str) or not cid or cid in ids:
            return _fail("CERTIFICATE_ID_INVALID_OR_DUPLICATE")
        ids.add(cid)
        if (
            not isinstance(targets, list)
            or not targets
            or len(set(targets)) != len(targets)
            or any(not isinstance(x, str) or x not in unresolved_set for x in targets)
        ):
            return _fail(f"CERTIFICATE_TARGETS_INVALID:{cid}")
        if (
            not isinstance(requires, list)
            or not requires
            or len(set(requires)) != len(requires)
            or any(not isinstance(x, str) or not x for x in requires)
        ):
            return _fail(f"CERTIFICATE_REQUIRES_INVALID:{cid}")
        if (
            isinstance(raw_reality, bool)
            or not isinstance(raw_reality, (int, float))
            or not isfinite(float(raw_reality))
            or float(raw_reality) < 0
        ):
            return _fail(f"CERTIFICATE_REALITY_COST_INVALID:{cid}")

        parsed.append(
            {
                "id": cid,
                "targets": frozenset(targets),
                "requires": frozenset(requires),
                "reality": float(raw_reality),
                "certificate_class": row.get("certificate_class"),
            }
        )

    if len(parsed) > MAX_EXACT_CERTIFICATES:
        return {
            **_fail(f"CERTIFICATE_COUNT_EXCEEDS_{MAX_EXACT_CERTIFICATES}"),
            "status": "EXACT_SEARCH_LIMIT",
            "certificate_count": len(parsed),
        }

    dominated_by: dict[str, list[str]] = {}
    for b in parsed:
        dominators = sorted(a["id"] for a in parsed if a["id"] != b["id"] and _dominates(a, b))
        if dominators:
            dominated_by[b["id"]] = dominators

    nondominated = sorted(c["id"] for c in parsed if c["id"] not in dominated_by)

    structural_front = []
    for c in parsed:
        structural_front.append(
            {
                "certificate_id": c["id"],
                "covered_predicate_count": len(c["targets"]),
                "requirement_count": len(c["requires"]),
                "new_reality_units": c["reality"],
                "covered_predicates": sorted(c["targets"]),
                "required_propositions": sorted(c["requires"]),
                "dominated": c["id"] in dominated_by,
                "dominated_by": dominated_by.get(c["id"], []),
            }
        )
    structural_front.sort(
        key=lambda x: (
            x["dominated"],
            -x["covered_predicate_count"],
            x["requirement_count"],
            x["new_reality_units"],
            x["certificate_id"],
        )
    )

    best_full = None
    n = len(parsed)
    for size in range(1, n + 1):
        for combo in combinations(range(n), size):
            covered: set[str] = set()
            requirements: set[str] = set()
            reality = 0.0
            cids = []
            for idx in combo:
                cert = parsed[idx]
                covered.update(cert["targets"])
                requirements.update(cert["requires"])
                reality += cert["reality"]
                cids.append(cert["id"])
            if covered != unresolved_set:
                continue
            cids_t = tuple(sorted(cids))
            key = (reality, len(requirements), len(cids_t), cids_t)
            if best_full is None or key < best_full[0]:
                best_full = (key, cids_t, requirements, reality)

    best_full_out = None
    if best_full is not None:
        best_full_out = {
            "certificate_ids": list(best_full[1]),
            "covered_predicate_count": len(unresolved_set),
            "unique_requirement_count": len(best_full[2]),
            "required_propositions": sorted(best_full[2]),
            "new_reality_units": best_full[3],
        }

    synergy_rows = []
    limit = min(max_synergy_order, n)
    for size in range(2, limit + 1):
        for combo in combinations(parsed, size):
            covered: set[str] = set()
            requirements: set[str] = set()
            reality = 0.0
            sum_requirement_count = 0
            for cert in combo:
                covered.update(cert["targets"])
                requirements.update(cert["requires"])
                reality += cert["reality"]
                sum_requirement_count += len(cert["requires"])
            shared_requirement_savings = sum_requirement_count - len(requirements)
            max_member_coverage = max(len(cert["targets"]) for cert in combo)
            coverage_gain_over_best_member = len(covered) - max_member_coverage
            if shared_requirement_savings <= 0 and coverage_gain_over_best_member <= 0:
                continue
            synergy_rows.append(
                {
                    "certificate_ids": sorted(cert["id"] for cert in combo),
                    "bundle_size": size,
                    "covered_predicate_count": len(covered),
                    "unique_requirement_count": len(requirements),
                    "shared_requirement_savings": shared_requirement_savings,
                    "coverage_gain_over_best_member": coverage_gain_over_best_member,
                    "new_reality_units": reality,
                }
            )

    synergy_rows.sort(
        key=lambda x: (
            -x["shared_requirement_savings"],
            -x["coverage_gain_over_best_member"],
            -x["covered_predicate_count"],
            x["unique_requirement_count"],
            x["certificate_ids"],
        )
    )

    reality_values = {c["reality"] for c in parsed}
    max_direct_coverage = max(len(c["targets"]) for c in parsed)
    highest_direct = sorted(c["id"] for c in parsed if len(c["targets"]) == max_direct_coverage)

    return {
        "schema": SCHEMA,
        "status": "EXACT_INFORMATION_DOMINANCE_COMPUTED",
        "errors": [],
        "unresolved_predicate_count": len(unresolved_set),
        "certificate_count": len(parsed),
        "all_reality_costs_equal": len(reality_values) == 1,
        "reality_cost_degenerate_for_ordering": len(reality_values) == 1,
        "highest_direct_coverage_count": max_direct_coverage,
        "highest_direct_coverage_certificate_ids": highest_direct,
        "dominated_certificate_ids": sorted(dominated_by),
        "dominated_by": dominated_by,
        "nondominated_certificate_ids": nondominated,
        "single_certificate_structural_front": structural_front,
        "best_full_frontier_bundle": best_full_out,
        "synergy_order_evaluated": limit,
        "synergy_bundles": synergy_rows,
        "rule": (
            "CERTIFICATE_COVERAGE_IS_SCHEDULING_COVERAGE_NOT_ACCEPTANCE_PROOF__"
            "DOMINANCE_REQUIRES_TARGET_SUPERSET_REQUIREMENT_SUBSET_AND_NO_GREATER_REALITY__"
            "REQUIREMENT_COUNT_IS_STRUCTURAL_CARDINALITY_NOT_PROOF_DIFFICULTY__"
            "NO_UNKNOWN_PROOF_COST_MAY_BE_INVENTED"
        ),
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    frontier = root / "canonical/governance/TERMINAL_CERTIFICATE_FRONTIER_V3.json"
    doc = json.loads(frontier.read_text(encoding="utf-8"))
    out = evaluate(doc)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["status"] == "EXACT_INFORMATION_DOMINANCE_COMPUTED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
