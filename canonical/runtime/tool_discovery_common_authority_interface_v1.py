"""Common matched-authority discovery interface for Tool Discovery.

This module is an evaluator/harness primitive, not a capability-credit grant.
It turns one finite frozen common tool authority into:
  * candidate-visible initial tool rows,
  * finite discovery-source identities, and
  * evaluator-held source results whose union is exactly the common authority.

Capability truth stays oracle-only.  The same common authority is intended to
be bound to Brain and Opus by the matched harness; tools outside that authority
are not invocable by either side and therefore cannot be valid matched routes.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

PUBLIC_FIELDS = ("tool_id", "cost", "available", "authorized", "epoch", "meta")
FORBIDDEN_DISCOVERY_FIELDS = ("capabilities", "supports", "required_capabilities", "oracle")


class InterfaceError(ValueError):
    pass


def _normalize_authority(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in rows:
        if not isinstance(raw, Mapping):
            raise InterfaceError("AUTHORITY_ROW_NOT_MAPPING")
        tid = str(raw.get("tool_id") or "")
        if not tid:
            raise InterfaceError("AUTHORITY_TOOL_ID_REQUIRED")
        if tid in seen:
            raise InterfaceError("DUPLICATE_AUTHORITY_TOOL_ID:" + tid)
        seen.add(tid)
        cost = raw.get("cost")
        if isinstance(cost, bool) or not isinstance(cost, (int, float)):
            raise InterfaceError("AUTHORITY_COST_NUMERIC_REQUIRED:" + tid)
        if float(cost) < 0:
            raise InterfaceError("AUTHORITY_COST_NEGATIVE:" + tid)
        if raw.get("available") not in (True, False):
            raise InterfaceError("AUTHORITY_AVAILABILITY_BOOL_REQUIRED:" + tid)
        if raw.get("authorized") not in (True, False):
            raise InterfaceError("AUTHORITY_AUTHORIZATION_BOOL_REQUIRED:" + tid)
        epoch = raw.get("epoch", 0)
        if isinstance(epoch, bool) or not isinstance(epoch, int) or epoch < 0:
            raise InterfaceError("AUTHORITY_EPOCH_NONNEGATIVE_INT_REQUIRED:" + tid)
        capabilities = raw.get("capabilities", {})
        if not isinstance(capabilities, Mapping):
            raise InterfaceError("AUTHORITY_CAPABILITIES_MAPPING_REQUIRED:" + tid)
        caps: dict[str, bool] = {}
        for cap, value in capabilities.items():
            name = str(cap or "")
            if not name or value not in (True, False):
                raise InterfaceError("AUTHORITY_CAPABILITY_BOOL_REQUIRED:" + tid)
            caps[name] = bool(value)
        meta = raw.get("meta", {})
        if not isinstance(meta, Mapping):
            raise InterfaceError("AUTHORITY_META_MAPPING_REQUIRED:" + tid)
        out.append({
            "tool_id": tid,
            "cost": float(cost),
            "available": bool(raw["available"]),
            "authorized": bool(raw["authorized"]),
            "epoch": int(epoch),
            "meta": deepcopy(dict(meta)),
            "capabilities": caps,
        })
    out.sort(key=lambda x: x["tool_id"])
    return out


def public_projection(row: Mapping[str, Any]) -> dict[str, Any]:
    return {field: deepcopy(row[field]) for field in PUBLIC_FIELDS}


def build_complete_interface(
    authority_rows: Sequence[Mapping[str, Any]],
    *,
    source_count: int = 1,
    initially_visible_ids: Sequence[str] = (),
) -> dict[str, Any]:
    """Build a finite complete discovery interface from the common authority.

    Source payloads are evaluator-held; the candidate sees only source ids until
    it issues DISCOVER.  Round-robin partitioning is deterministic and covers
    every authority identity exactly once.
    """
    authority = _normalize_authority(authority_rows)
    if isinstance(source_count, bool) or not isinstance(source_count, int) or source_count < 1:
        raise InterfaceError("SOURCE_COUNT_POSITIVE_INT_REQUIRED")

    authority_by_id = {row["tool_id"]: row for row in authority}
    initial = [str(x) for x in initially_visible_ids]
    if len(set(initial)) != len(initial):
        raise InterfaceError("DUPLICATE_INITIAL_TOOL_ID")
    unknown_initial = sorted(set(initial) - set(authority_by_id))
    if unknown_initial:
        raise InterfaceError("INITIAL_TOOL_OUTSIDE_COMMON_AUTHORITY:" + ",".join(unknown_initial))

    buckets: list[list[dict[str, Any]]] = [[] for _ in range(source_count)]
    for i, row in enumerate(authority):
        buckets[i % source_count].append(public_projection(row))

    sources = [
        {"source_id": f"COMMON_AUTHORITY_SOURCE_{i:03d}", "cost": 0.0, "available": True}
        for i in range(source_count)
    ]
    source_results = {
        sources[i]["source_id"]: deepcopy(buckets[i])
        for i in range(source_count)
    }
    public = {
        "visible_tools": [public_projection(authority_by_id[tid]) for tid in sorted(initial)],
        "discovery_sources": deepcopy(sources),
        "discovery_receipts": [],
        "prior_probe_receipts": [],
        "version_events": [],
    }
    oracle = {
        "common_authority": deepcopy(authority),
        "source_results": source_results,
    }
    return {"public": public, "oracle": oracle}


def validate_complete_interface(interface: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(interface, Mapping):
        return {"valid": False, "errors": ["INTERFACE_NOT_MAPPING"]}
    public = interface.get("public")
    oracle = interface.get("oracle")
    if not isinstance(public, Mapping) or not isinstance(oracle, Mapping):
        return {"valid": False, "errors": ["PUBLIC_OR_ORACLE_MISSING"]}

    errors: list[str] = []
    try:
        authority = _normalize_authority(oracle.get("common_authority", []))
    except Exception as exc:
        return {"valid": False, "errors": [type(exc).__name__ + ":" + str(exc)]}

    by_id = {row["tool_id"]: row for row in authority}
    authority_ids = set(by_id)
    sources = public.get("discovery_sources")
    results = oracle.get("source_results")
    if not isinstance(sources, list) or not isinstance(results, Mapping):
        return {"valid": False, "errors": ["SOURCE_DECLARATIONS_OR_RESULTS_INVALID"]}

    source_ids: list[str] = []
    union_ids: set[str] = set()
    counts: dict[str, int] = {}
    for source in sources:
        if not isinstance(source, Mapping):
            errors.append("SOURCE_NOT_MAPPING")
            continue
        sid = str(source.get("source_id") or "")
        if not sid or sid in source_ids:
            errors.append("SOURCE_ID_MISSING_OR_DUPLICATE:" + sid)
            continue
        source_ids.append(sid)
        if source.get("available") is not True:
            errors.append("COMMON_AUTHORITY_SOURCE_NOT_AVAILABLE:" + sid)
        rows = results.get(sid)
        if not isinstance(rows, list):
            errors.append("SOURCE_RESULT_MISSING:" + sid)
            continue
        for row in rows:
            if not isinstance(row, Mapping):
                errors.append("DISCOVERY_ROW_NOT_MAPPING:" + sid)
                continue
            forbidden = [x for x in FORBIDDEN_DISCOVERY_FIELDS if x in row]
            if forbidden:
                errors.append("DISCOVERY_CAPABILITY_TRUTH_LEAK:" + sid + ":" + ",".join(forbidden))
            tid = str(row.get("tool_id") or "")
            if tid not in by_id:
                errors.append("DISCOVERY_TOOL_OUTSIDE_COMMON_AUTHORITY:" + tid)
                continue
            counts[tid] = counts.get(tid, 0) + 1
            union_ids.add(tid)
            expected = public_projection(by_id[tid])
            if dict(row) != expected:
                errors.append("DISCOVERY_METADATA_MISMATCH:" + tid)

    extra_results = sorted(set(str(x) for x in results) - set(source_ids))
    if extra_results:
        errors.append("UNDECLARED_SOURCE_RESULT:" + ",".join(extra_results))
    if union_ids != authority_ids:
        errors.append(
            "DISCOVERY_UNION_NOT_COMMON_AUTHORITY:"
            + ",".join(sorted(authority_ids - union_ids))
            + "|extra="
            + ",".join(sorted(union_ids - authority_ids))
        )
    duplicates = sorted(tid for tid, n in counts.items() if n != 1)
    if duplicates:
        errors.append("DISCOVERY_IDENTITY_NOT_EXACTLY_ONCE:" + ",".join(duplicates))

    initial = public.get("visible_tools", [])
    if not isinstance(initial, list):
        errors.append("INITIAL_VISIBLE_TOOLS_NOT_LIST")
    else:
        for row in initial:
            if not isinstance(row, Mapping):
                errors.append("INITIAL_VISIBLE_ROW_NOT_MAPPING")
                continue
            tid = str(row.get("tool_id") or "")
            if tid not in by_id:
                errors.append("INITIAL_VISIBLE_TOOL_OUTSIDE_COMMON_AUTHORITY:" + tid)
            elif dict(row) != public_projection(by_id[tid]):
                errors.append("INITIAL_VISIBLE_METADATA_MISMATCH:" + tid)

    return {
        "valid": not errors,
        "errors": errors,
        "common_authority_ids": sorted(authority_ids),
        "discovery_union_ids": sorted(union_ids),
        "source_count": len(source_ids),
        "capability_truth_candidate_visible": False if not any(
            isinstance(row, Mapping) and any(k in row for k in FORBIDDEN_DISCOVERY_FIELDS)
            for sid in source_ids
            for row in (results.get(sid) if isinstance(results.get(sid), list) else [])
        ) else True,
    }


def tool_invocable(tool_id: str, interface: Mapping[str, Any]) -> bool:
    """Matched action authority gate: no identity outside common authority is invocable."""
    oracle = interface.get("oracle") if isinstance(interface, Mapping) else None
    rows = oracle.get("common_authority") if isinstance(oracle, Mapping) else None
    if not isinstance(rows, list):
        return False
    ids = {str(row.get("tool_id") or "") for row in rows if isinstance(row, Mapping)}
    return str(tool_id) in ids
