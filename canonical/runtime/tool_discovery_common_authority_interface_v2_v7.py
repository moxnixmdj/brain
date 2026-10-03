"""V7-native common frozen Brain/Opus Tool Discovery interface.

Environment-side proof machinery. It realizes the V7 complete-interface contract
over any finite frozen authority shared by Brain and Opus without pre-enumerating
tool identities in policy code.

Two causal clocks are separated exactly as V7 requires:
- authority/source epochs bind complete catalog discovery receipts;
- tool epochs bind safe capability probe receipts.

Task requirement or decision-epoch changes preserve catalog/probe receipts while
the authority and relevant tool epochs remain unchanged.
"""
from __future__ import annotations

import hashlib
import json
import math
from copy import deepcopy
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_COMMON_AUTHORITY_DISCOVERY_INTERFACE_V2_V7"
SOURCE_ID = "COMMON_FROZEN_BRAIN_OPUS_TOOL_AUTHORITY"
CATALOG_QUERY = "__FULL_COMMON_FROZEN_AUTHORITY_CATALOG__"


class InterfaceError(ValueError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _nonnegative_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InterfaceError(label + ":NOT_NUMBER")
    out = float(value)
    if not math.isfinite(out) or out < 0:
        raise InterfaceError(label + ":NOT_FINITE_NONNEGATIVE")
    return out


def _public_tool(raw: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise InterfaceError("TOOL_NOT_MAPPING")
    tid = str(raw.get("tool_id") or "")
    if not tid:
        raise InterfaceError("TOOL_ID_MISSING")
    if not isinstance(raw.get("available"), bool):
        raise InterfaceError("TOOL_AVAILABLE_NOT_BOOLEAN:" + tid)
    if not isinstance(raw.get("authorized"), bool):
        raise InterfaceError("TOOL_AUTHORIZED_NOT_BOOLEAN:" + tid)
    epoch = raw.get("epoch", 0)
    if isinstance(epoch, bool) or not isinstance(epoch, int) or epoch < 0:
        raise InterfaceError("TOOL_EPOCH_INVALID:" + tid)
    cost = _nonnegative_number(raw.get("cost", 0.0), "TOOL_COST:" + tid)

    forbidden = {
        "hidden_capabilities",
        "capabilities",
        "supported_capabilities",
        "_oracle",
        "support_truth",
    }
    if forbidden & set(raw):
        raise InterfaceError("PUBLIC_METADATA_CONTAINS_HIDDEN_CAPABILITY_FIELD:" + tid)

    safe = raw.get("safe_probe_capabilities")
    if not isinstance(safe, list):
        raise InterfaceError("SAFE_PROBE_CAPABILITIES_NOT_LIST:" + tid)
    normalized_safe = sorted({str(x) for x in safe if str(x)})
    if len(normalized_safe) != len(safe):
        raise InterfaceError("SAFE_PROBE_CAPABILITIES_INVALID_OR_DUPLICATE:" + tid)

    out = deepcopy(dict(raw))
    out["tool_id"] = tid
    out["cost"] = cost
    out["available"] = raw["available"]
    out["authorized"] = raw["authorized"]
    out["epoch"] = epoch
    out["safe_probe_capabilities"] = normalized_safe
    return out


def _tools_digest(tools: Sequence[Mapping[str, Any]]) -> str:
    rows = [dict(x) for x in tools]
    rows.sort(key=lambda row: str(row.get("tool_id") or ""))
    raw = json.dumps(
        rows,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _source_set_digest(
    sources: Sequence[Mapping[str, Any]],
    *,
    authority_epoch: int,
) -> str:
    payload = []
    for source in sources:
        payload.append({
            "source_id": str(source.get("source_id") or ""),
            "cost": float(source.get("cost", 0.0)),
            "available": source.get("available"),
            "authorized": source.get("authorized"),
            "authoritative": source.get("authoritative"),
            "source_epoch": source.get("source_epoch"),
            "source_digest": str(source.get("source_digest") or ""),
            "catalog_query": str(source.get("catalog_query") or ""),
        })
    payload.sort(key=lambda row: row["source_id"])
    raw = json.dumps(
        {"authority_epoch": authority_epoch, "sources": payload},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _normalize_truth(
    tools: Mapping[str, Mapping[str, Any]],
    hidden_truth: Mapping[str, Any],
) -> dict[str, dict[str, list[str]]]:
    if not isinstance(hidden_truth, Mapping):
        raise InterfaceError("HIDDEN_TRUTH_NOT_MAPPING")
    if set(map(str, hidden_truth)) != set(tools):
        raise InterfaceError("HIDDEN_TRUTH_TOOL_SET_MISMATCH")

    out: dict[str, dict[str, list[str]]] = {}
    for tid, tool in tools.items():
        raw_epochs = hidden_truth.get(tid)
        if not isinstance(raw_epochs, Mapping):
            raise InterfaceError("HIDDEN_TRUTH_TOOL_MISSING:" + tid)
        epochs: dict[str, list[str]] = {}
        for raw_epoch, raw_caps in raw_epochs.items():
            if isinstance(raw_epoch, bool):
                raise InterfaceError("HIDDEN_TRUTH_EPOCH_INVALID:" + tid)
            try:
                epoch = int(raw_epoch)
            except (TypeError, ValueError):
                raise InterfaceError("HIDDEN_TRUTH_EPOCH_INVALID:" + tid)
            if epoch < 0 or str(epoch) != str(raw_epoch):
                raise InterfaceError("HIDDEN_TRUTH_EPOCH_INVALID:" + tid)
            if not isinstance(raw_caps, (list, tuple, set)):
                raise InterfaceError("HIDDEN_TRUTH_CAPS_NOT_SEQUENCE:" + tid)
            epochs[str(epoch)] = sorted({str(x) for x in raw_caps if str(x)})
        if str(tool["epoch"]) not in epochs:
            raise InterfaceError("HIDDEN_TRUTH_CURRENT_EPOCH_MISSING:" + tid)
        out[tid] = dict(sorted(epochs.items(), key=lambda pair: int(pair[0])))
    return out


def freeze_instance(
    public_tools: Sequence[Mapping[str, Any]],
    hidden_truth: Mapping[str, Any],
    *,
    authority_epoch: int = 0,
) -> dict[str, Any]:
    if not isinstance(public_tools, (list, tuple)) or not public_tools:
        raise InterfaceError("FINITE_NONEMPTY_TOOL_AUTHORITY_REQUIRED")
    if (
        isinstance(authority_epoch, bool)
        or not isinstance(authority_epoch, int)
        or authority_epoch < 0
    ):
        raise InterfaceError("AUTHORITY_EPOCH_INVALID")

    tools: dict[str, dict[str, Any]] = {}
    for raw in public_tools:
        row = _public_tool(raw)
        tid = row["tool_id"]
        if tid in tools:
            raise InterfaceError("DUPLICATE_TOOL_ID:" + tid)
        tools[tid] = row

    truth = _normalize_truth(tools, hidden_truth)
    public_manifest = [tools[k] for k in sorted(tools)]
    source_digest = _tools_digest(public_manifest)
    source = {
        "source_id": SOURCE_ID,
        "cost": 0.0,
        "available": True,
        "authorized": True,
        "authoritative": True,
        "source_epoch": authority_epoch,
        "source_digest": source_digest,
        "catalog_query": CATALOG_QUERY,
    }
    source_set_digest = _source_set_digest(
        [source],
        authority_epoch=authority_epoch,
    )
    core = {
        "schema": SCHEMA,
        "authority_epoch": authority_epoch,
        "public_tools": public_manifest,
        "hidden_truth": truth,
        "public_authority_sha256": _sha(public_manifest),
        "hidden_oracle_sha256": _sha(truth),
        "source": source,
        "source_set_digest": source_set_digest,
    }
    core["instance_sha256"] = _sha(core)
    return core


def validate_instance(instance: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(instance, Mapping) or instance.get("schema") != SCHEMA:
        raise InterfaceError("INSTANCE_SCHEMA_INVALID")
    rebuilt = freeze_instance(
        list(instance.get("public_tools") or []),
        dict(instance.get("hidden_truth") or {}),
        authority_epoch=instance.get("authority_epoch"),
    )
    for key in (
        "public_authority_sha256",
        "hidden_oracle_sha256",
        "source_set_digest",
        "instance_sha256",
    ):
        if instance.get(key) != rebuilt[key]:
            raise InterfaceError("INSTANCE_DIGEST_MISMATCH:" + key)
    if instance.get("source") != rebuilt["source"]:
        raise InterfaceError("INSTANCE_SOURCE_DESCRIPTOR_MISMATCH")
    return rebuilt


def matched_route_binding(instance: Mapping[str, Any]) -> dict[str, Any]:
    frozen = validate_instance(instance)
    return {
        "kind": "COMMON_MATCHED_TOOL_AUTHORITY_BINDING_V2",
        "brain": {
            "public_authority_sha256": frozen["public_authority_sha256"],
            "interface_instance_sha256": frozen["instance_sha256"],
        },
        "opus": {
            "public_authority_sha256": frozen["public_authority_sha256"],
            "interface_instance_sha256": frozen["instance_sha256"],
        },
        "same_frozen_tool_authority": True,
    }


def begin_task(
    instance: Mapping[str, Any],
    required_capabilities: Sequence[str],
    *,
    decision_epoch: int = 0,
    constraint: Any = None,
) -> dict[str, Any]:
    frozen = validate_instance(instance)
    required = sorted({str(x) for x in required_capabilities if str(x)})
    if not required:
        raise InterfaceError("REQUIRED_CAPABILITIES_EMPTY")
    if isinstance(decision_epoch, bool) or not isinstance(decision_epoch, int) or decision_epoch < 0:
        raise InterfaceError("DECISION_EPOCH_INVALID")
    return {
        "required_capabilities": required,
        "decision_epoch": decision_epoch,
        "authority_epoch": frozen["authority_epoch"],
        "constraint": deepcopy(constraint),
        # Critical provenance rule: there are no selectable pre-visible identities.
        # Every selectable identity enters through the exact common authority receipt.
        "visible_tools": [],
        "discovery_sources": [deepcopy(frozen["source"])],
        "discovery_receipts": [],
        "prior_probe_receipts": [],
        "version_events": [],
        "interface_instance_sha256": frozen["instance_sha256"],
        "public_authority_sha256": frozen["public_authority_sha256"],
    }


def retarget_task(
    instance: Mapping[str, Any],
    episode: Mapping[str, Any],
    required_capabilities: Sequence[str],
    *,
    decision_epoch: int,
    constraint: Any = None,
) -> dict[str, Any]:
    frozen = _assert_episode_current(instance, episode)
    required = sorted({str(x) for x in required_capabilities if str(x)})
    if not required:
        raise InterfaceError("REQUIRED_CAPABILITIES_EMPTY")
    if isinstance(decision_epoch, bool) or not isinstance(decision_epoch, int) or decision_epoch < 0:
        raise InterfaceError("DECISION_EPOCH_INVALID")
    out = deepcopy(dict(episode))
    out["required_capabilities"] = required
    out["decision_epoch"] = decision_epoch
    out["constraint"] = deepcopy(constraint)
    out["authority_epoch"] = frozen["authority_epoch"]
    out["version_events"] = []
    return out


def _assert_episode_current(
    instance: Mapping[str, Any],
    episode: Mapping[str, Any],
) -> dict[str, Any]:
    frozen = validate_instance(instance)
    if episode.get("interface_instance_sha256") != frozen["instance_sha256"]:
        raise InterfaceError("STALE_EPISODE_RESTART_REQUIRED")
    if episode.get("authority_epoch") != frozen["authority_epoch"]:
        raise InterfaceError("STALE_AUTHORITY_EPOCH_RESTART_REQUIRED")
    if episode.get("public_authority_sha256") != frozen["public_authority_sha256"]:
        raise InterfaceError("EPISODE_AUTHORITY_MISMATCH")
    return frozen


def discover(
    instance: Mapping[str, Any],
    episode: Mapping[str, Any],
    source_id: str,
    query: str,
) -> dict[str, Any]:
    frozen = _assert_episode_current(instance, episode)
    source = frozen["source"]
    if source_id != SOURCE_ID:
        raise InterfaceError("DISCOVERY_SOURCE_INVALID")
    if query != CATALOG_QUERY:
        raise InterfaceError("DISCOVERY_QUERY_NOT_CANONICAL_CATALOG")
    return {
        "kind": "DISCOVERY_RESULT",
        "source_id": SOURCE_ID,
        "complete": True,
        "authority_epoch": frozen["authority_epoch"],
        "source_epoch": source["source_epoch"],
        "source_digest": source["source_digest"],
        "source_set_digest": frozen["source_set_digest"],
        "query": CATALOG_QUERY,
        "tools": deepcopy(frozen["public_tools"]),
        "instance_sha256": frozen["instance_sha256"],
    }


def apply_discovery(
    instance: Mapping[str, Any],
    episode: Mapping[str, Any],
    receipt: Mapping[str, Any],
) -> dict[str, Any]:
    frozen = _assert_episode_current(instance, episode)
    expected = discover(instance, episode, SOURCE_ID, CATALOG_QUERY)
    if dict(receipt) != expected:
        raise InterfaceError("DISCOVERY_RECEIPT_NOT_EXACT_AUTHORITY_RESULT")
    prior = list(episode.get("discovery_receipts") or [])
    if prior:
        raise InterfaceError("DISCOVERY_SOURCE_ALREADY_QUERIED")
    out = deepcopy(dict(episode))
    out["discovery_receipts"] = [deepcopy(dict(receipt))]
    return out


def safe_probe(
    instance: Mapping[str, Any],
    episode: Mapping[str, Any],
    tool_id: str,
    capability: str,
) -> dict[str, Any]:
    frozen = _assert_episode_current(instance, episode)
    tid = str(tool_id or "")
    cap = str(capability or "")
    tools = {x["tool_id"]: x for x in frozen["public_tools"]}
    if tid not in tools:
        raise InterfaceError("PROBE_UNKNOWN_TOOL")
    if not cap:
        raise InterfaceError("PROBE_CAPABILITY_EMPTY")
    tool = tools[tid]
    if cap not in set(tool["safe_probe_capabilities"]):
        raise InterfaceError("PROBE_NOT_EXPLICITLY_SAFE")
    epoch = tool["epoch"]
    truth = frozen["hidden_truth"][tid][str(epoch)]
    return {
        "kind": "SAFE_CAPABILITY_PROBE",
        "tool_id": tid,
        "capability": cap,
        "epoch": epoch,
        "supported": cap in truth,
        "instance_sha256": frozen["instance_sha256"],
    }


def apply_probe(
    instance: Mapping[str, Any],
    episode: Mapping[str, Any],
    receipt: Mapping[str, Any],
) -> dict[str, Any]:
    frozen = _assert_episode_current(instance, episode)
    tid = str(receipt.get("tool_id") or "")
    cap = str(receipt.get("capability") or "")
    tools = {x["tool_id"]: x for x in frozen["public_tools"]}
    if tid not in tools or not cap:
        raise InterfaceError("PROBE_RECEIPT_TARGET_INVALID")
    expected = safe_probe(instance, episode, tid, cap)
    if dict(receipt) != expected:
        raise InterfaceError("PROBE_RECEIPT_NOT_EXACT_TRUTH")
    prior = list(episode.get("prior_probe_receipts") or [])
    key = (tid, cap, expected["epoch"])
    if any(
        isinstance(x, Mapping)
        and (x.get("tool_id"), x.get("capability"), x.get("epoch")) == key
        for x in prior
    ):
        raise InterfaceError("DUPLICATE_CURRENT_EPOCH_PROBE")
    out = deepcopy(dict(episode))
    prior.append(deepcopy(dict(receipt)))
    out["prior_probe_receipts"] = prior
    return out


def evolve_tool(
    instance: Mapping[str, Any],
    tool_id: str,
    *,
    new_epoch: int,
    new_capabilities: Sequence[str],
    public_metadata_updates: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    frozen = validate_instance(instance)
    tid = str(tool_id or "")
    rows = {x["tool_id"]: deepcopy(x) for x in frozen["public_tools"]}
    if tid not in rows:
        raise InterfaceError("VERSION_UNKNOWN_TOOL")
    old_epoch = rows[tid]["epoch"]
    if isinstance(new_epoch, bool) or not isinstance(new_epoch, int) or new_epoch <= old_epoch:
        raise InterfaceError("VERSION_EPOCH_MUST_ADVANCE")
    updates = dict(public_metadata_updates or {})
    forbidden = {
        "tool_id",
        "epoch",
        "hidden_capabilities",
        "capabilities",
        "supported_capabilities",
        "_oracle",
        "support_truth",
    }
    if forbidden & set(updates):
        raise InterfaceError("VERSION_PUBLIC_UPDATE_FORBIDDEN_FIELD")
    rows[tid].update(deepcopy(updates))
    rows[tid]["epoch"] = new_epoch

    truth = deepcopy(frozen["hidden_truth"])
    truth[tid][str(new_epoch)] = sorted({str(x) for x in new_capabilities if str(x)})
    return freeze_instance(
        [rows[k] for k in sorted(rows)],
        truth,
        authority_epoch=frozen["authority_epoch"] + 1,
    )
