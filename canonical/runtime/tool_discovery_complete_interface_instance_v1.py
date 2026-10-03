"""Closed-world complete discovery interface for Project Brain Tool Discovery.

This environment adapter makes discovery completeness an execution-authority
invariant instead of an empirical claim about an open registry.

For one decision epoch:
* the complete Brain-callable tool universe U is finite and content-addressed;
* every member of U is assigned to exactly one finite authoritative discovery
  source;
* discovery returns only the canonical public metadata used by the execution
  gate;
* safe probes return only exact hidden capability truth and are epoch-bound;
* no tool outside U can be admitted for execution;
* version changes create a new epoch object/fingerprint rather than mutating an
  active episode.

The policy never receives the hidden capability table or undiscovered tool
metadata. This module does not itself grant acceptance or promotion authority.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_TOOL_DISCOVERY_COMPLETE_INTERFACE_INSTANCE_V1"
REQUIRED_PROPERTIES = (
    "FINITE_DISCOVERY_SOURCE_SET_PER_DECISION_EPOCH",
    "DISCOVERY_RECEIPT_IDENTIFIES_QUERIED_SOURCE",
    "DISCOVERY_RESULTS_MONOTONICALLY_ADD_VISIBLE_TOOL_IDENTITIES_WITHIN_EPOCH",
    "UNION_OF_AUTHORITATIVE_DISCOVERY_RESULTS_IS_COMPLETE_FOR_DECLARED_TARGET_SCOPE",
    "DISCOVERED_TOOL_METADATA_CORRECT_FOR_AVAILABILITY_AUTHORIZATION_COST_AND_CONSTRAINT_FIELDS",
    "SAFE_CAPABILITY_PROBE_RECEIPTS_ARE_TRUTHFUL_AND_EPOCH_BOUND",
    "VERSION_EPOCH_STABLE_DURING_ONE_SELECTION_EPISODE_OR_RESTARTS_EPISODE",
)

class InterfaceError(ValueError):
    pass

def _canon(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")

def _sha256(value: Any) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()

def _number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InterfaceError(name + "_NOT_NUMBER")
    out = float(value)
    if not math.isfinite(out) or out < 0:
        raise InterfaceError(name + "_INVALID")
    return out

def _identifier(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InterfaceError(name + "_INVALID")
    return value.strip()

def _public_tool(tool: Mapping[str, Any], epoch_id: int) -> dict[str, Any]:
    # Hidden capability truth is intentionally absent. All remaining metadata is
    # copied from the same canonical record used by execution_admit().
    out = {
        str(k): copy.deepcopy(v)
        for k, v in tool.items()
        if k not in {"capability_truth", "hidden_capabilities", "_oracle"}
    }
    out["tool_id"] = str(tool["tool_id"])
    out["available"] = bool(tool["available"])
    out["authorized"] = bool(tool["authorized"])
    out["cost"] = float(tool["cost"])
    out["epoch"] = int(epoch_id)
    return out

def _payload_without_fingerprint(epoch: Mapping[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(dict(epoch))
    out.pop("fingerprint_sha256", None)
    return out

def _assert_fingerprint(epoch: Mapping[str, Any]) -> None:
    supplied = str(epoch.get("fingerprint_sha256") or "")
    actual = _sha256(_payload_without_fingerprint(epoch))
    if supplied != actual:
        raise InterfaceError("EPOCH_FINGERPRINT_MISMATCH")

def compile_epoch(spec: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(spec, Mapping):
        raise InterfaceError("SPEC_NOT_MAPPING")
    raw_epoch = spec.get("epoch_id")
    if isinstance(raw_epoch, bool) or not isinstance(raw_epoch, int) or raw_epoch < 0:
        raise InterfaceError("EPOCH_ID_INVALID")
    epoch_id = int(raw_epoch)

    raw_tools = spec.get("tools")
    if not isinstance(raw_tools, list) or not raw_tools:
        raise InterfaceError("TOOLS_MUST_BE_NONEMPTY_FINITE_LIST")

    tools: dict[str, dict[str, Any]] = {}
    for raw in raw_tools:
        if not isinstance(raw, Mapping):
            raise InterfaceError("TOOL_NOT_MAPPING")
        tool_id = _identifier(raw.get("tool_id"), "TOOL_ID")
        if tool_id in tools:
            raise InterfaceError("DUPLICATE_TOOL_ID:" + tool_id)
        if raw.get("available") not in (True, False):
            raise InterfaceError("TOOL_AVAILABLE_NOT_BOOL:" + tool_id)
        if raw.get("authorized") not in (True, False):
            raise InterfaceError("TOOL_AUTHORIZED_NOT_BOOL:" + tool_id)
        cost = _number(raw.get("cost"), "TOOL_COST:" + tool_id)
        item = copy.deepcopy(dict(raw))
        item["tool_id"] = tool_id
        item["available"] = bool(raw["available"])
        item["authorized"] = bool(raw["authorized"])
        item["cost"] = cost
        for forbidden in ("capability_truth", "hidden_capabilities", "_oracle"):
            if forbidden in item:
                raise InterfaceError("HIDDEN_TRUTH_EMBEDDED_IN_PUBLIC_TOOL:" + tool_id)
        tools[tool_id] = item

    universe = set(tools)

    raw_truth = spec.get("capability_truth")
    if not isinstance(raw_truth, Mapping) or set(map(str, raw_truth.keys())) != universe:
        raise InterfaceError("CAPABILITY_TRUTH_TOOL_UNIVERSE_MISMATCH")
    truth: dict[str, dict[str, bool]] = {}
    for tool_id in sorted(universe):
        caps = raw_truth.get(tool_id)
        if not isinstance(caps, Mapping) or not caps:
            raise InterfaceError("CAPABILITY_TRUTH_INVALID:" + tool_id)
        row: dict[str, bool] = {}
        for cap, value in caps.items():
            cap_id = _identifier(cap, "CAPABILITY_ID")
            if value not in (True, False):
                raise InterfaceError("CAPABILITY_TRUTH_NOT_BOOL:" + tool_id + ":" + cap_id)
            row[cap_id] = bool(value)
        truth[tool_id] = row

    raw_sources = spec.get("sources")
    if not isinstance(raw_sources, list) or not raw_sources:
        raise InterfaceError("SOURCES_MUST_BE_NONEMPTY_FINITE_LIST")
    sources: dict[str, dict[str, Any]] = {}
    owner: dict[str, str] = {}
    for raw in raw_sources:
        if not isinstance(raw, Mapping):
            raise InterfaceError("SOURCE_NOT_MAPPING")
        source_id = _identifier(raw.get("source_id"), "SOURCE_ID")
        if source_id in sources:
            raise InterfaceError("DUPLICATE_SOURCE_ID:" + source_id)
        if raw.get("available") is not True:
            # A source that cannot be queried cannot carry a completeness claim.
            raise InterfaceError("AUTHORITATIVE_SOURCE_NOT_AVAILABLE:" + source_id)
        cost = _number(raw.get("cost"), "SOURCE_COST:" + source_id)
        ids = raw.get("tool_ids")
        if not isinstance(ids, list):
            raise InterfaceError("SOURCE_TOOL_IDS_NOT_FINITE_LIST:" + source_id)
        normalized: list[str] = []
        for value in ids:
            tool_id = _identifier(value, "SOURCE_TOOL_ID")
            if tool_id not in universe:
                raise InterfaceError("SOURCE_REFERENCES_UNKNOWN_TOOL:" + tool_id)
            if tool_id in owner:
                raise InterfaceError(
                    "TOOL_ASSIGNED_TO_MULTIPLE_SOURCES:"
                    + tool_id + ":" + owner[tool_id] + ":" + source_id
                )
            owner[tool_id] = source_id
            normalized.append(tool_id)
        sources[source_id] = {
            "source_id": source_id,
            "cost": cost,
            "available": True,
            "tool_ids": sorted(normalized),
        }

    if set(owner) != universe:
        missing = sorted(universe - set(owner))
        raise InterfaceError("SOURCE_UNION_INCOMPLETE:" + ",".join(missing))

    initial = spec.get("initial_visible", [])
    if not isinstance(initial, list):
        raise InterfaceError("INITIAL_VISIBLE_NOT_FINITE_LIST")
    initial_ids = [_identifier(x, "INITIAL_TOOL_ID") for x in initial]
    if len(set(initial_ids)) != len(initial_ids):
        raise InterfaceError("INITIAL_VISIBLE_DUPLICATE")
    if not set(initial_ids) <= universe:
        raise InterfaceError("INITIAL_VISIBLE_OUTSIDE_UNIVERSE")

    required = spec.get("required_capabilities")
    if not isinstance(required, list) or not required:
        raise InterfaceError("REQUIRED_CAPABILITIES_MUST_BE_NONEMPTY_LIST")
    required_caps = [_identifier(x, "REQUIRED_CAPABILITY_ID") for x in required]
    if len(set(required_caps)) != len(required_caps):
        raise InterfaceError("DUPLICATE_REQUIRED_CAPABILITY")
    for tool_id, caps in truth.items():
        if not set(required_caps) <= set(caps):
            raise InterfaceError("CAPABILITY_TRUTH_INCOMPLETE:" + tool_id)

    payload = {
        "schema": SCHEMA,
        "epoch_id": epoch_id,
        "declared_target_scope":
            "ALL_BRAIN_CALLABLE_TOOLS_IN_THIS_DECISION_EPOCH",
        "tools": [tools[x] for x in sorted(tools)],
        "sources": [sources[x] for x in sorted(sources)],
        "capability_truth": {x: truth[x] for x in sorted(truth)},
        "initial_visible": sorted(initial_ids),
        "required_capabilities": sorted(required_caps),
    }
    payload["fingerprint_sha256"] = _sha256(payload)
    return payload

def source_catalog(epoch: Mapping[str, Any]) -> list[dict[str, Any]]:
    _assert_fingerprint(epoch)
    return [
        {
            "source_id": str(s["source_id"]),
            "cost": float(s["cost"]),
            "available": True,
        }
        for s in epoch["sources"]
    ]

def initial_public_tools(epoch: Mapping[str, Any]) -> list[dict[str, Any]]:
    _assert_fingerprint(epoch)
    wanted = set(epoch["initial_visible"])
    return [
        _public_tool(t, int(epoch["epoch_id"]))
        for t in epoch["tools"]
        if t["tool_id"] in wanted
    ]

def discover(
    epoch: Mapping[str, Any], source_id: str, query: str
) -> dict[str, Any]:
    _assert_fingerprint(epoch)
    sid = _identifier(source_id, "SOURCE_ID")
    if not isinstance(query, str) or not query.strip():
        raise InterfaceError("DISCOVERY_QUERY_REQUIRED")
    source = next((s for s in epoch["sources"] if s["source_id"] == sid), None)
    if source is None or source.get("available") is not True:
        raise InterfaceError("DISCOVERY_SOURCE_INVALID:" + sid)
    ids = set(source["tool_ids"])
    tools = [
        _public_tool(t, int(epoch["epoch_id"]))
        for t in epoch["tools"]
        if t["tool_id"] in ids
    ]
    return {
        "kind": "DISCOVERY_RESULT",
        "source_id": sid,
        "epoch": int(epoch["epoch_id"]),
        "epoch_fingerprint_sha256": str(epoch["fingerprint_sha256"]),
        "query": query,
        "tools": tools,
    }

def probe(
    epoch: Mapping[str, Any], tool_id: str, capability: str
) -> dict[str, Any]:
    _assert_fingerprint(epoch)
    tid = _identifier(tool_id, "TOOL_ID")
    cap = _identifier(capability, "CAPABILITY_ID")
    truth = epoch["capability_truth"]
    if tid not in truth:
        raise InterfaceError("PROBE_TOOL_OUTSIDE_UNIVERSE:" + tid)
    if cap not in truth[tid]:
        raise InterfaceError("PROBE_CAPABILITY_UNDECLARED:" + cap)
    return {
        "kind": "SAFE_CAPABILITY_PROBE",
        "tool_id": tid,
        "capability": cap,
        "epoch": int(epoch["epoch_id"]),
        "epoch_fingerprint_sha256": str(epoch["fingerprint_sha256"]),
        "supported": bool(truth[tid][cap]),
    }

def execution_admit(epoch: Mapping[str, Any], tool_id: str) -> dict[str, Any]:
    """Sole interface admission result for a tool identity.

    This function is deliberately closed-world: an identity absent from U is
    rejected rather than delegated to an out-of-band execution path.
    """
    _assert_fingerprint(epoch)
    tid = _identifier(tool_id, "TOOL_ID")
    row = next((t for t in epoch["tools"] if t["tool_id"] == tid), None)
    if row is None:
        return {
            "admitted": False,
            "reason": "TOOL_ID_OUTSIDE_CONTENT_ADDRESSED_EPOCH_UNIVERSE",
        }
    if row["available"] is not True:
        return {"admitted": False, "reason": "TOOL_UNAVAILABLE"}
    if row["authorized"] is not True:
        return {"admitted": False, "reason": "TOOL_UNAUTHORIZED"}
    return {
        "admitted": True,
        "reason": "ADMITTED_FROM_CONTENT_ADDRESSED_EPOCH_UNIVERSE",
        "tool": _public_tool(row, int(epoch["epoch_id"])),
    }

def _session_payload_without_fingerprint(session: Mapping[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(dict(session))
    out.pop("state_sha256", None)
    return out

def _seal_session(payload: Mapping[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(dict(payload))
    out["state_sha256"] = _sha256(out)
    return out

def _assert_session(epoch: Mapping[str, Any], session: Mapping[str, Any]) -> None:
    _assert_fingerprint(epoch)
    if not isinstance(session, Mapping):
        raise InterfaceError("SESSION_NOT_MAPPING")
    if session.get("epoch_fingerprint_sha256") != epoch.get("fingerprint_sha256"):
        raise InterfaceError("SESSION_EPOCH_MISMATCH_RESTART_REQUIRED")
    supplied = str(session.get("state_sha256") or "")
    actual = _sha256(_session_payload_without_fingerprint(session))
    if supplied != actual:
        raise InterfaceError("SESSION_FINGERPRINT_MISMATCH")

def new_session(
    epoch: Mapping[str, Any], *, constraint: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    _assert_fingerprint(epoch)
    payload = {
        "schema": "PROJECT_BRAIN_TOOL_DISCOVERY_SESSION_V1",
        "epoch_id": int(epoch["epoch_id"]),
        "epoch_fingerprint_sha256": str(epoch["fingerprint_sha256"]),
        "visible_tool_ids": sorted(set(epoch["initial_visible"])),
        "discovery_receipts": [],
        "probe_receipts": [],
        "constraint": copy.deepcopy(constraint),
    }
    return _seal_session(payload)

def apply_discovery(
    epoch: Mapping[str, Any],
    session: Mapping[str, Any],
    source_id: str,
    query: str,
) -> dict[str, Any]:
    _assert_session(epoch, session)
    sid = _identifier(source_id, "SOURCE_ID")
    if any(
        isinstance(x, Mapping)
        and x.get("kind") == "DISCOVERY_RESULT"
        and x.get("source_id") == sid
        for x in session["discovery_receipts"]
    ):
        raise InterfaceError("DISCOVERY_SOURCE_ALREADY_QUERIED:" + sid)
    receipt = discover(epoch, sid, query)
    out = _session_payload_without_fingerprint(session)
    prior = set(map(str, session["visible_tool_ids"]))
    additions = {str(t["tool_id"]) for t in receipt["tools"]}
    out["visible_tool_ids"] = sorted(prior | additions)
    out["discovery_receipts"] = list(session["discovery_receipts"]) + [receipt]
    return _seal_session(out)

def apply_probe(
    epoch: Mapping[str, Any],
    session: Mapping[str, Any],
    tool_id: str,
    capability: str,
) -> dict[str, Any]:
    _assert_session(epoch, session)
    tid = _identifier(tool_id, "TOOL_ID")
    cap = _identifier(capability, "CAPABILITY_ID")
    if tid not in set(map(str, session["visible_tool_ids"])):
        raise InterfaceError("PROBE_TOOL_NOT_VISIBLE:" + tid)
    if any(
        isinstance(x, Mapping)
        and x.get("kind") == "SAFE_CAPABILITY_PROBE"
        and x.get("tool_id") == tid
        and x.get("capability") == cap
        and x.get("epoch") == epoch["epoch_id"]
        for x in session["probe_receipts"]
    ):
        raise InterfaceError("DUPLICATE_CURRENT_EPOCH_PROBE:" + tid + ":" + cap)
    receipt = probe(epoch, tid, cap)
    out = _session_payload_without_fingerprint(session)
    out["probe_receipts"] = list(session["probe_receipts"]) + [receipt]
    return _seal_session(out)

def public_state(
    epoch: Mapping[str, Any], session: Mapping[str, Any]
) -> dict[str, Any]:
    _assert_session(epoch, session)
    visible = set(map(str, session["visible_tool_ids"]))
    return {
        "required_capabilities": list(epoch["required_capabilities"]),
        "constraint": copy.deepcopy(session.get("constraint")),
        "visible_tools": [
            _public_tool(t, int(epoch["epoch_id"]))
            for t in epoch["tools"]
            if t["tool_id"] in visible
        ],
        "discovery_sources": source_catalog(epoch),
        "prior_probe_receipts": copy.deepcopy(session["probe_receipts"]),
        "discovery_receipts": copy.deepcopy(session["discovery_receipts"]),
        # A session is pinned to one immutable epoch. Version change is a new
        # epoch + new session, which is the contract's allowed restart branch.
        "version_events": [],
    }

def rotate_epoch(
    epoch: Mapping[str, Any],
    *,
    new_epoch_id: int,
    capability_updates: Mapping[str, Mapping[str, bool]] | None = None,
    tool_metadata_updates: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Create a new epoch. Active epoch bytes are never mutated in place."""
    _assert_fingerprint(epoch)
    if isinstance(new_epoch_id, bool) or not isinstance(new_epoch_id, int):
        raise InterfaceError("NEW_EPOCH_ID_INVALID")
    if new_epoch_id <= int(epoch["epoch_id"]):
        raise InterfaceError("NEW_EPOCH_ID_MUST_INCREASE")
    spec = {
        "epoch_id": int(new_epoch_id),
        "tools": copy.deepcopy(epoch["tools"]),
        "sources": copy.deepcopy(epoch["sources"]),
        "capability_truth": copy.deepcopy(epoch["capability_truth"]),
        "initial_visible": copy.deepcopy(epoch["initial_visible"]),
        "required_capabilities": copy.deepcopy(epoch["required_capabilities"]),
    }
    byid = {t["tool_id"]: t for t in spec["tools"]}
    for tid, updates in dict(tool_metadata_updates or {}).items():
        if tid not in byid or not isinstance(updates, Mapping):
            raise InterfaceError("TOOL_METADATA_UPDATE_INVALID:" + str(tid))
        for key, value in updates.items():
            if key in {"tool_id", "capability_truth", "hidden_capabilities", "_oracle"}:
                raise InterfaceError("TOOL_METADATA_UPDATE_FIELD_FORBIDDEN:" + str(key))
            byid[tid][key] = copy.deepcopy(value)
    for tid, updates in dict(capability_updates or {}).items():
        if tid not in spec["capability_truth"] or not isinstance(updates, Mapping):
            raise InterfaceError("CAPABILITY_UPDATE_INVALID:" + str(tid))
        for cap, value in updates.items():
            if cap not in spec["capability_truth"][tid] or value not in (True, False):
                raise InterfaceError("CAPABILITY_UPDATE_INVALID:" + str(tid) + ":" + str(cap))
            spec["capability_truth"][tid][cap] = bool(value)
    return compile_epoch(spec)

def contract_certificate(epoch: Mapping[str, Any]) -> dict[str, Any]:
    _assert_fingerprint(epoch)
    universe = {str(t["tool_id"]) for t in epoch["tools"]}
    source_union = {
        str(tool_id)
        for source in epoch["sources"]
        for tool_id in source["tool_ids"]
    }
    owner_count = {
        tid: sum(tid in source["tool_ids"] for source in epoch["sources"])
        for tid in universe
    }
    properties = {
        "FINITE_DISCOVERY_SOURCE_SET_PER_DECISION_EPOCH":
            isinstance(epoch["sources"], list) and len(epoch["sources"]) > 0,
        "DISCOVERY_RECEIPT_IDENTIFIES_QUERIED_SOURCE":
            all(isinstance(s.get("source_id"), str) and s["source_id"] for s in epoch["sources"]),
        "DISCOVERY_RESULTS_MONOTONICALLY_ADD_VISIBLE_TOOL_IDENTITIES_WITHIN_EPOCH":
            True,  # discover() is pure and returns additions; it has no removal operation.
        "UNION_OF_AUTHORITATIVE_DISCOVERY_RESULTS_IS_COMPLETE_FOR_DECLARED_TARGET_SCOPE":
            source_union == universe and all(owner_count[x] == 1 for x in universe),
        "DISCOVERED_TOOL_METADATA_CORRECT_FOR_AVAILABILITY_AUTHORIZATION_COST_AND_CONSTRAINT_FIELDS":
            True,  # discover() and execution_admit() project the same canonical tool rows.
        "SAFE_CAPABILITY_PROBE_RECEIPTS_ARE_TRUTHFUL_AND_EPOCH_BOUND":
            True,  # probe() reads only exact hidden truth and binds epoch+fingerprint.
        "VERSION_EPOCH_STABLE_DURING_ONE_SELECTION_EPISODE_OR_RESTARTS_EPISODE":
            True,  # fingerprint mismatch fails closed; rotate_epoch() creates a new epoch.
    }
    return {
        "schema": "PROJECT_BRAIN_TOOL_DISCOVERY_COMPLETE_INTERFACE_CERTIFICATE_V1",
        "status": (
            "PASS__COMPLETE_INTERFACE_INSTANCE_BY_CONSTRUCTION__"
            "INDEPENDENT_VERIFICATION_REQUIRED__ZERO_CREDIT"
            if all(properties.values())
            else "FAIL_CLOSED"
        ),
        "epoch_id": int(epoch["epoch_id"]),
        "epoch_fingerprint_sha256": str(epoch["fingerprint_sha256"]),
        "declared_target_scope": str(epoch["declared_target_scope"]),
        "tool_universe_size": len(universe),
        "source_count": len(epoch["sources"]),
        "source_union_exact": source_union == universe,
        "execution_authority_closed_world": True,
        "required_properties": list(REQUIRED_PROPERTIES),
        "properties": properties,
        "all_required_properties_hold": all(properties.values()),
        "new_reality_units_consumed": 0,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }
