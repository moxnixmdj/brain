"""Information-safe P3 v4 candidate.

Extends v3 with fail-closed required-claim handling and provenance/unit-preserving
selection receipts. No evaluator imports or hidden support/relevance labels.
"""
from __future__ import annotations
from typing import Any, Mapping

CONTRACT = "EVIDENCE_TO_AUDIENCE_SYNTHESIS_001"
AUDIENCE_PRIORITY = {
    "executive": ("risk", "trend"),
    "engineer": ("mechanism", "risk"),
    "auditor": ("control", "risk"),
}

def _satisfies(claim: Mapping[str, Any], value: float) -> bool:
    t = float(claim["threshold"])
    if claim["relation"] == "at_least":
        return value >= t
    if claim["relation"] == "at_most":
        return value <= t
    raise ValueError("RELATION")

def solve(public: Mapping[str, Any]) -> dict[str, Any]:
    if public.get("contract") != CONTRACT or not isinstance(public.get("task"), Mapping):
        raise ValueError("TASK")
    t = public["task"]
    audience = str(t.get("audience") or "")
    required = [str(x) for x in t.get("required_claims", [])]
    required_set = set(required)
    claims = [x for x in t.get("claims", []) if isinstance(x, Mapping)]
    evidence = [x for x in t.get("evidence", []) if isinstance(x, Mapping)]

    by_metric: dict[str, list[dict[str, Any]]] = {}
    for e in evidence:
        metric = str(e.get("metric") or "")
        record = {
            "evidence_id": str(e.get("evidence_id") or ""),
            "value": float(e["value"]),
            "unit": str(e.get("unit") or ""),
            "provenance": list(e.get("provenance") or []),
        }
        by_metric.setdefault(metric, []).append(record)

    ranked: list[tuple[int, str]] = []
    uncertainty: list[str] = []
    unresolved_required: dict[str, str] = {}
    support_receipts: dict[str, list[dict[str, Any]]] = {}
    prefs = set(AUDIENCE_PRIORITY.get(audience, ()))

    for c in claims:
        cid = str(c.get("claim_id") or "")
        rows = by_metric.get(str(c.get("metric") or ""), [])
        if not rows:
            if cid in required_set:
                unresolved_required[cid] = "NO_MATCHING_EVIDENCE"
            continue

        units = {row["unit"] for row in rows}
        explicit_unit = str(c.get("unit") or "")
        if explicit_unit:
            compatible = [row for row in rows if row["unit"] == explicit_unit]
            if len(compatible) != len(rows):
                if cid in required_set:
                    unresolved_required[cid] = "UNIT_MISMATCH"
                continue
            rows = compatible
        elif len(units) > 1:
            if cid in required_set:
                unresolved_required[cid] = "MIXED_UNITS"
            continue

        votes = [_satisfies(c, row["value"]) for row in rows]
        positive = sum(votes)
        negative = len(votes) - positive
        supported = positive > 0 and positive >= negative
        relevant = cid in required_set or str(c.get("kind") or "") in prefs

        if supported and relevant:
            ranked.append((0 if cid in required_set else 1, cid))
            support_receipts[cid] = rows
        elif cid in required_set:
            unresolved_required[cid] = "INSUFFICIENT_SUPPORT"

        if any(votes) and not all(votes):
            uncertainty.append(cid)

    ranked.sort()
    max_claims = int(t.get("max_claims") or 0)
    selected = [cid for _, cid in ranked[:max_claims]]
    selected_set = set(selected)

    for cid in required:
        if cid not in selected_set and cid not in unresolved_required:
            unresolved_required[cid] = "OUTPUT_BUDGET_EXCLUDES_REQUIRED_CLAIM"

    return {
        "selected_claims": selected,
        "uncertainty_claims": sorted(set(uncertainty) & selected_set),
        "unresolved_required_claims": [
            {"claim_id": cid, "reason": unresolved_required[cid]}
            for cid in required
            if cid in unresolved_required
        ],
        "claim_evidence": {
            cid: support_receipts[cid]
            for cid in selected
            if cid in support_receipts
        },
        "terminal_authority": False,
    }
