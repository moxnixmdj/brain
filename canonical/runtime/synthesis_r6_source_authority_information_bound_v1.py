"""Fail-closed source-authority gate for synthesis R6.

This module does not infer trust from source names.  It requires an explicit,
evidence-specific authority fact whose provenance binding exactly matches the
evidence unit.  Missing, contradictory, or misbound facts remain unresolved.

Zero acceptance credit.  This is a deterministic pre-support gate.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

ALLOWED_STATES = {"ADMISSIBLE", "INADMISSIBLE"}


def _provenance(value: Any) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()
    out = tuple(str(x) for x in value if str(x))
    return out


def gate_evidence(
    evidence: Sequence[Mapping[str, Any]],
    authority_facts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Classify evidence without guessing source authority.

    Authority facts are intentionally evidence-specific.  Each fact must bind:
    evidence_id, exact provenance sequence, ADMISSIBLE/INADMISSIBLE state, and
    a non-empty basis string identifying why the fact is verified.
    """
    facts_by_id: dict[str, list[Mapping[str, Any]]] = {}
    for fact in authority_facts:
        if not isinstance(fact, Mapping):
            continue
        eid = str(fact.get("evidence_id") or "")
        if eid:
            facts_by_id.setdefault(eid, []).append(fact)

    admitted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for raw in evidence:
        if not isinstance(raw, Mapping):
            unresolved.append({"evidence_id": "", "reason": "INVALID_EVIDENCE_RECORD"})
            continue

        row = dict(raw)
        eid = str(row.get("evidence_id") or "")
        prov = _provenance(row.get("provenance"))

        if not eid:
            unresolved.append({"evidence_id": "", "reason": "MISSING_EVIDENCE_ID"})
            continue
        if eid in seen_ids:
            unresolved.append({"evidence_id": eid, "reason": "DUPLICATE_EVIDENCE_ID"})
            continue
        seen_ids.add(eid)
        if not prov:
            unresolved.append({"evidence_id": eid, "reason": "MISSING_PROVENANCE"})
            continue

        facts = facts_by_id.get(eid, [])
        if not facts:
            unresolved.append({"evidence_id": eid, "reason": "MISSING_AUTHORITY_FACT"})
            continue

        normalized: set[tuple[tuple[str, ...], str, str]] = set()
        for fact in facts:
            state = str(fact.get("state") or "").upper()
            basis = str(fact.get("basis") or "")
            normalized.add((_provenance(fact.get("provenance")), state, basis))

        if len(normalized) != 1:
            unresolved.append({"evidence_id": eid, "reason": "CONTRADICTORY_AUTHORITY_FACTS"})
            continue

        fact_prov, state, basis = next(iter(normalized))
        if fact_prov != prov:
            unresolved.append(
                {"evidence_id": eid, "reason": "AUTHORITY_PROVENANCE_BINDING_MISMATCH"}
            )
            continue
        if state not in ALLOWED_STATES or not basis:
            unresolved.append({"evidence_id": eid, "reason": "INVALID_AUTHORITY_FACT"})
            continue

        receipt = {
            "evidence": row,
            "authority": {
                "state": state,
                "basis": basis,
                "provenance": list(fact_prov),
            },
        }
        if state == "ADMISSIBLE":
            admitted.append(receipt)
        else:
            rejected.append(receipt)

    return {
        "admissible": admitted,
        "inadmissible": rejected,
        "unresolved": unresolved,
        "terminal_authority": False,
    }


def threshold_polarity(
    claim: Mapping[str, Any],
    gated: Mapping[str, Any],
) -> str:
    """Demonstrate the post-gate polarity for the bounded threshold subdomain.

    Any unresolved evidence sharing the claim metric keeps the result unresolved.
    General claim semantics remain outside this module.
    """
    metric = str(claim.get("metric") or "")
    relation = str(claim.get("relation") or "")
    threshold = float(claim["threshold"])

    evidence_ids_for_metric: set[str] = set()
    for bucket in ("admissible", "inadmissible"):
        for receipt in gated.get(bucket, []):
            row = receipt.get("evidence", {})
            if str(row.get("metric") or "") == metric:
                evidence_ids_for_metric.add(str(row.get("evidence_id") or ""))

    unresolved_ids = {
        str(x.get("evidence_id") or "") for x in gated.get("unresolved", [])
    }
    if unresolved_ids & evidence_ids_for_metric:
        return "UNRESOLVED_SOURCE_AUTHORITY"

    vals: list[float] = []
    for receipt in gated.get("admissible", []):
        row = receipt.get("evidence", {})
        if str(row.get("metric") or "") == metric:
            vals.append(float(row["value"]))

    if not vals:
        return "UNRESOLVED_SOURCE_AUTHORITY"

    if relation == "at_least":
        votes = [v >= threshold for v in vals]
    elif relation == "at_most":
        votes = [v <= threshold for v in vals]
    else:
        return "UNRESOLVED_GENERAL_SUPPORT_SEMANTICS"

    if all(votes):
        return "SUPPORTED"
    if not any(votes):
        return "UNSUPPORTED"
    return "CONFLICT"
