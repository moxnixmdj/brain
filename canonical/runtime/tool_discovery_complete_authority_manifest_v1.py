"""Complete content-addressed tool-authority manifest interface V1.

This module is an environment-side adapter, not a capability oracle.

It makes one scope fact mechanically checkable:
the initial visible tool set plus every declared discovery source is an exact,
metadata-preserving partition of one finite authoritative public tool universe
for a decision epoch.

Hidden capability support is intentionally absent from the manifest. It remains
available only through safe probe receipts.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_TOOL_DISCOVERY_COMPLETE_AUTHORITY_MANIFEST_V1"
RECEIPT_SCHEMA = "PROJECT_BRAIN_TOOL_DISCOVERY_COMPLETE_SOURCE_RECEIPT_V1"
PUBLIC_TOOL_KEYS = frozenset(
    {"tool_id", "cost", "available", "authorized", "epoch", "meta"}
)


class ManifestError(ValueError):
    pass


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()


def _normalize_tool(raw: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise ManifestError("TOOL_NOT_MAPPING")
    unknown = set(raw) - PUBLIC_TOOL_KEYS
    if unknown:
        raise ManifestError("TOOL_NONPUBLIC_FIELDS:" + ",".join(sorted(unknown)))
    tid = str(raw.get("tool_id") or "")
    if not tid:
        raise ManifestError("TOOL_ID_REQUIRED")
    cost = raw.get("cost")
    if isinstance(cost, bool) or not isinstance(cost, (int, float)):
        raise ManifestError("TOOL_COST_INVALID:" + tid)
    if float(cost) < 0:
        raise ManifestError("TOOL_COST_NEGATIVE:" + tid)
    if not isinstance(raw.get("available"), bool):
        raise ManifestError("TOOL_AVAILABLE_INVALID:" + tid)
    if not isinstance(raw.get("authorized"), bool):
        raise ManifestError("TOOL_AUTHORIZED_INVALID:" + tid)
    epoch = raw.get("epoch")
    if isinstance(epoch, bool) or not isinstance(epoch, int) or epoch < 0:
        raise ManifestError("TOOL_EPOCH_INVALID:" + tid)
    meta = raw.get("meta", {})
    if not isinstance(meta, Mapping):
        raise ManifestError("TOOL_META_INVALID:" + tid)
    return {
        "tool_id": tid,
        "cost": float(cost),
        "available": bool(raw["available"]),
        "authorized": bool(raw["authorized"]),
        "epoch": int(epoch),
        "meta": dict(meta),
    }


def authority_rows(instance: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = [_normalize_tool(x) for x in instance.get("authority_tools", [])]
    rows.sort(key=lambda x: x["tool_id"])
    return rows


def validate_instance(instance: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(instance, Mapping):
        raise ManifestError("INSTANCE_NOT_MAPPING")
    if instance.get("schema") != SCHEMA:
        raise ManifestError("SCHEMA_MISMATCH")

    epoch_id = str(instance.get("epoch_id") or "")
    if not epoch_id:
        raise ManifestError("EPOCH_ID_REQUIRED")

    rows = authority_rows(instance)
    ids = [x["tool_id"] for x in rows]
    if not ids:
        raise ManifestError("AUTHORITY_EMPTY")
    if len(ids) != len(set(ids)):
        raise ManifestError("AUTHORITY_DUPLICATE_TOOL_ID")

    claimed_root = str(instance.get("authority_sha256") or "").lower()
    actual_root = _sha256(rows)
    if claimed_root != actual_root:
        raise ManifestError("AUTHORITY_HASH_MISMATCH")

    initial = [str(x) for x in instance.get("initial_visible_tool_ids", [])]
    if len(initial) != len(set(initial)):
        raise ManifestError("INITIAL_DUPLICATE_TOOL_ID")

    source_ids: set[str] = set()
    partition_members: list[str] = list(initial)
    normalized_sources: list[dict[str, Any]] = []
    source_hashes: dict[str, str] = {}
    for raw in instance.get("discovery_sources", []):
        if not isinstance(raw, Mapping):
            raise ManifestError("SOURCE_NOT_MAPPING")
        sid = str(raw.get("source_id") or "")
        if not sid or sid in source_ids:
            raise ManifestError("SOURCE_ID_INVALID_OR_DUPLICATE:" + sid)
        source_ids.add(sid)
        if raw.get("available") is not True:
            # A source that owns authority members must be discoverable in the
            # same epoch; otherwise exact-cover completeness is false.
            raise ManifestError("SOURCE_NOT_AVAILABLE:" + sid)
        cost = raw.get("cost", 0.0)
        if isinstance(cost, bool) or not isinstance(cost, (int, float)) or float(cost) < 0:
            raise ManifestError("SOURCE_COST_INVALID:" + sid)
        members = [str(x) for x in raw.get("tool_ids", [])]
        if not members:
            raise ManifestError("SOURCE_EMPTY:" + sid)
        if len(members) != len(set(members)):
            raise ManifestError("SOURCE_DUPLICATE_TOOL_ID:" + sid)
        partition_members.extend(members)
        normalized = {
            "source_id": sid,
            "cost": float(cost),
            "available": True,
            "tool_ids": sorted(members),
        }
        normalized_sources.append(normalized)
        source_hashes[sid] = _sha256(normalized)

    if len(partition_members) != len(set(partition_members)):
        raise ManifestError("PARTITION_OVERLAP")
    if set(partition_members) != set(ids):
        missing = sorted(set(ids) - set(partition_members))
        extra = sorted(set(partition_members) - set(ids))
        raise ManifestError(
            "PARTITION_NOT_EXACT:missing=" + ",".join(missing)
            + ";extra=" + ",".join(extra)
        )

    normalized_sources.sort(key=lambda x: x["source_id"])
    normalized_initial = sorted(initial)
    partition_commitment = _sha256(
        {
            "epoch_id": epoch_id,
            "authority_sha256": actual_root,
            "initial_visible_tool_ids": normalized_initial,
            "discovery_sources": normalized_sources,
        }
    )
    claimed_partition = str(instance.get("partition_sha256") or "").lower()
    if claimed_partition != partition_commitment:
        raise ManifestError("PARTITION_HASH_MISMATCH")

    return {
        "schema": SCHEMA,
        "epoch_id": epoch_id,
        "authority_tool_count": len(rows),
        "authority_sha256": actual_root,
        "partition_sha256": partition_commitment,
        "initial_visible_tool_ids": normalized_initial,
        "discovery_source_count": len(normalized_sources),
        "source_hashes": source_hashes,
        "complete_exact_partition": True,
    }


def build_instance(
    *,
    epoch_id: str,
    authority_tools: list[Mapping[str, Any]],
    initial_visible_tool_ids: list[str],
    discovery_sources: list[Mapping[str, Any]],
) -> dict[str, Any]:
    rows = [_normalize_tool(x) for x in authority_tools]
    rows.sort(key=lambda x: x["tool_id"])
    normalized_sources = []
    for raw in discovery_sources:
        normalized_sources.append(
            {
                "source_id": str(raw.get("source_id") or ""),
                "cost": float(raw.get("cost", 0.0)),
                "available": bool(raw.get("available")),
                "tool_ids": sorted(str(x) for x in raw.get("tool_ids", [])),
            }
        )
    normalized_sources.sort(key=lambda x: x["source_id"])
    initial = sorted(str(x) for x in initial_visible_tool_ids)
    authority_root = _sha256(rows)
    out = {
        "schema": SCHEMA,
        "epoch_id": str(epoch_id),
        "authority_tools": rows,
        "authority_sha256": authority_root,
        "initial_visible_tool_ids": initial,
        "discovery_sources": normalized_sources,
    }
    out["partition_sha256"] = _sha256(
        {
            "epoch_id": out["epoch_id"],
            "authority_sha256": authority_root,
            "initial_visible_tool_ids": initial,
            "discovery_sources": normalized_sources,
        }
    )
    validate_instance(out)
    return out


def initial_public(
    instance: Mapping[str, Any],
    *,
    required_capabilities: list[str],
    constraint: Any = None,
    prior_probe_receipts: list[Mapping[str, Any]] | None = None,
    version_events: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    state = validate_instance(instance)
    by_id = {x["tool_id"]: x for x in authority_rows(instance)}
    initial = [by_id[x] for x in state["initial_visible_tool_ids"]]
    # Candidate receives source identities/cost/availability only, never the
    # private authority membership lists or hidden capability support.
    sources = [
        {
            "source_id": str(x["source_id"]),
            "cost": float(x["cost"]),
            "available": True,
        }
        for x in instance["discovery_sources"]
    ]
    sources.sort(key=lambda x: (x["cost"], x["source_id"]))
    return {
        "required_capabilities": list(required_capabilities),
        "constraint": constraint,
        "visible_tools": initial,
        "discovery_sources": sources,
        "discovery_receipts": [],
        "prior_probe_receipts": [dict(x) for x in (prior_probe_receipts or [])],
        "version_events": [dict(x) for x in (version_events or [])],
        "_interface_epoch_id": state["epoch_id"],
        "_interface_authority_sha256": state["authority_sha256"],
        "_interface_partition_sha256": state["partition_sha256"],
    }


def discover(instance: Mapping[str, Any], source_id: str) -> dict[str, Any]:
    state = validate_instance(instance)
    source = next(
        (x for x in instance["discovery_sources"] if str(x["source_id"]) == str(source_id)),
        None,
    )
    if source is None:
        raise ManifestError("SOURCE_UNKNOWN:" + str(source_id))
    by_id = {x["tool_id"]: x for x in authority_rows(instance)}
    rows = [by_id[str(tid)] for tid in source["tool_ids"]]
    rows.sort(key=lambda x: x["tool_id"])
    return {
        "kind": "DISCOVERY_RESULT",
        "schema": RECEIPT_SCHEMA,
        "source_id": str(source["source_id"]),
        "epoch_id": state["epoch_id"],
        "authority_sha256": state["authority_sha256"],
        "partition_sha256": state["partition_sha256"],
        "source_sha256": state["source_hashes"][str(source["source_id"])],
        "tools": rows,
    }


def apply_discovery(public: Mapping[str, Any], receipt: Mapping[str, Any]) -> dict[str, Any]:
    if receipt.get("kind") != "DISCOVERY_RESULT" or receipt.get("schema") != RECEIPT_SCHEMA:
        raise ManifestError("RECEIPT_INVALID")
    if receipt.get("epoch_id") != public.get("_interface_epoch_id"):
        raise ManifestError("RECEIPT_EPOCH_MISMATCH")
    if receipt.get("authority_sha256") != public.get("_interface_authority_sha256"):
        raise ManifestError("RECEIPT_AUTHORITY_MISMATCH")
    if receipt.get("partition_sha256") != public.get("_interface_partition_sha256"):
        raise ManifestError("RECEIPT_PARTITION_MISMATCH")

    out = dict(public)
    visible = [dict(x) for x in public.get("visible_tools", [])]
    present = {str(x.get("tool_id") or "") for x in visible}
    for raw in receipt.get("tools", []):
        row = _normalize_tool(raw)
        if row["tool_id"] in present:
            raise ManifestError("DISCOVERY_DUPLICATE_VISIBLE_TOOL:" + row["tool_id"])
        present.add(row["tool_id"])
        visible.append(row)

    receipts = [dict(x) for x in public.get("discovery_receipts", [])]
    if any(str(x.get("source_id") or "") == str(receipt["source_id"]) for x in receipts):
        raise ManifestError("SOURCE_ALREADY_DISCOVERED:" + str(receipt["source_id"]))
    receipts.append(dict(receipt))
    out["visible_tools"] = visible
    out["discovery_receipts"] = receipts
    return out
