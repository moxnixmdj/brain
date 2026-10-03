"""Complete-interface dynamic tool discovery candidate V4.

This policy preserves the frozen TOOL_ROUTE_DISCOVERY_AND_SELECTION_001 target while
making unknown tool identity discovery explicit. A finite discovery epoch is usable
only when a proof-carrying registry declares the authoritative discovery-source set
complete. Every current source is exhausted before capability probing/selection.

The policy never treats metadata as hidden capability evidence. Current-epoch safe
probe receipts are the only capability evidence, and tool/source epoch changes
invalidate stale receipts.
"""
from __future__ import annotations
import hashlib
import json
from typing import Any, Mapping

from canonical.runtime import tool_discovery_information_safe_candidate as legacy

CMP = {"eq","neq","in","not_in","lt","le","gt","ge","contains","exists"}


class ToolDiscoveryV4Error(ValueError):
    pass


def _canon(v: Any) -> str:
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha(v: Any) -> str:
    return hashlib.sha256(_canon(v).encode("utf-8")).hexdigest()


def _get(obj: Mapping[str, Any], path: str) -> Any:
    cur: Any = obj
    for part in str(path).split("."):
        if not isinstance(cur, Mapping) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _pred(expr: Any, tool: Mapping[str, Any]) -> bool:
    if expr in (None, {}, []):
        return True
    if not isinstance(expr, Mapping):
        return False
    op = str(expr.get("op") or "")
    if op == "and":
        xs = expr.get("args")
        return isinstance(xs, list) and all(_pred(x, tool) for x in xs)
    if op == "or":
        xs = expr.get("args")
        return isinstance(xs, list) and bool(xs) and any(_pred(x, tool) for x in xs)
    if op == "not":
        return not _pred(expr.get("arg"), tool)
    if op not in CMP:
        return False
    value = _get(tool, str(expr.get("path") or ""))
    target = expr.get("value")
    if op == "exists":
        return (value is not None) is bool(target)
    if op == "eq":
        return value == target
    if op == "neq":
        return value != target
    if op == "in":
        return isinstance(target, list) and value in target
    if op == "not_in":
        return isinstance(target, list) and value not in target
    if op == "contains":
        return isinstance(value, (str, list, tuple, set)) and target in value
    if isinstance(value, bool) or isinstance(target, bool):
        return False
    if not isinstance(value, (int, float)) or not isinstance(target, (int, float)):
        return False
    if op == "lt":
        return value < target
    if op == "le":
        return value <= target
    if op == "gt":
        return value > target
    if op == "ge":
        return value >= target
    return False


def _registry(public: Mapping[str, Any]) -> dict[str, Any]:
    reg = public.get("discovery_registry")
    if not isinstance(reg, Mapping):
        raise ToolDiscoveryV4Error("DISCOVERY_REGISTRY_MISSING")
    if reg.get("kind") != "COMPLETE_DISCOVERY_REGISTRY":
        raise ToolDiscoveryV4Error("DISCOVERY_REGISTRY_KIND_INVALID")
    # `complete` is an interface assertion consumed fail-closed here. Whether that
    # assertion is trustworthy is proved by the separately content-addressed scope
    # certificate; an input boolean never self-certifies the theorem.
    if reg.get("complete") is not True:
        raise ToolDiscoveryV4Error("DISCOVERY_REGISTRY_COMPLETENESS_NOT_DECLARED")
    epoch = reg.get("epoch")
    if not isinstance(epoch, int) or isinstance(epoch, bool) or epoch < 0:
        raise ToolDiscoveryV4Error("DISCOVERY_REGISTRY_EPOCH_INVALID")
    rows = reg.get("sources")
    if not isinstance(rows, list):
        raise ToolDiscoveryV4Error("DISCOVERY_REGISTRY_SOURCES_INVALID")
    out = []
    ids = set()
    for raw in rows:
        if not isinstance(raw, Mapping):
            raise ToolDiscoveryV4Error("DISCOVERY_SOURCE_NOT_OBJECT")
        sid = raw.get("source_id")
        sep = raw.get("epoch")
        cost = raw.get("cost")
        if not isinstance(sid, str) or not sid or sid in ids:
            raise ToolDiscoveryV4Error("DISCOVERY_SOURCE_ID_INVALID_OR_DUPLICATE")
        if not isinstance(sep, int) or isinstance(sep, bool) or sep < 0:
            raise ToolDiscoveryV4Error("DISCOVERY_SOURCE_EPOCH_INVALID:" + sid)
        if not isinstance(cost, (int, float)) or isinstance(cost, bool) or float(cost) < 0:
            raise ToolDiscoveryV4Error("DISCOVERY_SOURCE_COST_INVALID:" + sid)
        authorized = raw.get("authorized") is True
        ids.add(sid)
        out.append({
            "source_id": sid,
            "epoch": sep,
            "cost": float(cost),
            "available": raw.get("available") is True,
            "authorized": authorized,
        })
    declared = reg.get("source_manifest_sha256")
    expected = _sha(sorted(
        [{"source_id": x["source_id"], "epoch": x["epoch"], "cost": x["cost"],
          "available": x["available"], "authorized": x["authorized"]}
         for x in out],
        key=lambda x: x["source_id"],
    ))
    if declared != expected:
        raise ToolDiscoveryV4Error("DISCOVERY_REGISTRY_MANIFEST_MISMATCH")
    return {"epoch": epoch, "sources": sorted(out, key=lambda x: (x["cost"], x["source_id"]))}


def _current_tool_epochs(public: Mapping[str, Any], tools: Mapping[str, Mapping[str, Any]]) -> dict[str, int]:
    out = {tid: int(row["epoch"]) for tid, row in tools.items()}
    events = list(public.get("version_events", []) or []) + list(public.get("tool_version_events", []) or [])
    for ev in events:
        if not isinstance(ev, Mapping) or ev.get("kind") != "TOOL_VERSION_CHANGED":
            continue
        tid = str(ev.get("tool_id") or "")
        ep = ev.get("new_epoch")
        if tid in out and isinstance(ep, int) and not isinstance(ep, bool) and ep >= out[tid]:
            out[tid] = ep
    return out


def _materialize(public: Mapping[str, Any], reg: Mapping[str, Any]) -> tuple[dict[str, dict[str, Any]], set[str]]:
    rows_by_id = {x["source_id"]: x for x in reg["sources"]}
    receipts: dict[str, Mapping[str, Any]] = {}
    for raw in public.get("discovery_receipts", []):
        if not isinstance(raw, Mapping) or raw.get("kind") != "DISCOVERY_RESULT":
            continue
        sid = str(raw.get("source_id") or "")
        src = rows_by_id.get(sid)
        if src is None:
            raise ToolDiscoveryV4Error("DISCOVERY_RECEIPT_UNKNOWN_SOURCE:" + sid)
        if raw.get("registry_epoch") != reg["epoch"] or raw.get("source_epoch") != src["epoch"]:
            continue
        if raw.get("complete") is not True:
            raise ToolDiscoveryV4Error("DISCOVERY_RECEIPT_NOT_COMPLETE:" + sid)
        if sid in receipts:
            raise ToolDiscoveryV4Error("DUPLICATE_DISCOVERY_RECEIPT:" + sid)
        receipts[sid] = raw

    tools: dict[str, dict[str, Any]] = {}

    def ingest(raw: Mapping[str, Any]) -> None:
        tid = raw.get("tool_id")
        epoch = raw.get("epoch", 0)
        cost = raw.get("cost")
        if not isinstance(tid, str) or not tid:
            raise ToolDiscoveryV4Error("DISCOVERED_TOOL_ID_INVALID")
        if not isinstance(epoch, int) or isinstance(epoch, bool) or epoch < 0:
            raise ToolDiscoveryV4Error("DISCOVERED_TOOL_EPOCH_INVALID:" + tid)
        if not isinstance(cost, (int, float)) or isinstance(cost, bool) or float(cost) < 0:
            raise ToolDiscoveryV4Error("DISCOVERED_TOOL_COST_INVALID:" + tid)
        row = dict(raw)
        row["epoch"] = epoch
        row["cost"] = float(cost)
        # Newly discovered identities may be probed only when the interface
        # explicitly grants bounded safe-probe authority. Absence fails closed.
        row["safe_probe_allowed"] = raw.get("safe_probe_allowed") is True
        prior = tools.get(tid)
        if prior is not None and _canon(prior) != _canon(row):
            raise ToolDiscoveryV4Error("DISCOVERED_TOOL_ID_CONFLICT:" + tid)
        tools[tid] = row

    # A complete interface may start with already-visible tools and then discover
    # arbitrary additional identities. This is a conservative extension, not a
    # requirement to forget tools already exposed by the frozen interface.
    base_tools = public.get("tools", [])
    if not isinstance(base_tools, list):
        raise ToolDiscoveryV4Error("VISIBLE_TOOLS_INVALID")
    for raw in base_tools:
        if not isinstance(raw, Mapping):
            raise ToolDiscoveryV4Error("VISIBLE_TOOL_NOT_OBJECT")
        ingest(raw)

    for sid, rec in sorted(receipts.items()):
        rows = rec.get("tools")
        if not isinstance(rows, list):
            raise ToolDiscoveryV4Error("DISCOVERY_TOOLS_INVALID:" + sid)
        for raw in rows:
            if not isinstance(raw, Mapping):
                raise ToolDiscoveryV4Error("DISCOVERED_TOOL_NOT_OBJECT")
            ingest(raw)
    return tools, set(receipts)


def _evidence(public: Mapping[str, Any], epochs: Mapping[str, int]) -> dict[tuple[str, str], bool]:
    out: dict[tuple[str, str], bool] = {}
    for rec in public.get("prior_probe_receipts", []):
        if not isinstance(rec, Mapping) or rec.get("kind") != "SAFE_CAPABILITY_PROBE":
            continue
        tid = str(rec.get("tool_id") or "")
        cap = str(rec.get("capability") or "")
        if tid not in epochs or rec.get("epoch") != epochs[tid] or not cap:
            continue
        value = rec.get("supported")
        if value is not True and value is not False:
            raise ToolDiscoveryV4Error("PROBE_RECEIPT_RESULT_INVALID")
        key = (tid, cap)
        if key in out and out[key] is not value:
            raise ToolDiscoveryV4Error("CONFLICTING_CURRENT_PROBE_RECEIPTS:" + tid + ":" + cap)
        out[key] = bool(value)
    return out


def next_action(public: Mapping[str, Any]) -> dict[str, Any]:
    # Exact conservative projection: frozen historical terminal inputs contain no
    # discovery registry, so their behavior remains byte-for-byte delegated to the
    # already verified legacy candidate. No terminal replay is required to know this.
    if "discovery_registry" not in public:
        return legacy.next_action(public)

    required = sorted({str(x) for x in public.get("required_capabilities", []) if str(x)})
    if not required:
        return {"action": "ESCALATE", "reason": "NO_REQUIRED_CAPABILITIES"}

    try:
        reg = _registry(public)
        tools, queried = _materialize(public, reg)
    except ToolDiscoveryV4Error as exc:
        return {"action": "ESCALATE", "reason": str(exc)}

    # Identity discovery is completed before capability selection. This is what makes
    # least-cost selection global over the certified discovery universe.
    for src in reg["sources"]:
        if src["available"] and src["authorized"] and src["source_id"] not in queried:
            return {
                "action": "DISCOVER",
                "source_id": src["source_id"],
                "registry_epoch": reg["epoch"],
                "source_epoch": src["epoch"],
                "query": " ".join(required),
            }

    constraint = public.get("constraint")
    epochs = _current_tool_epochs(public, tools)
    evidence = _evidence(public, epochs)
    eligible = [
        row for row in tools.values()
        if row.get("available") is True
        and row.get("authorized") is True
        and _pred(constraint, row)
    ]
    eligible.sort(key=lambda x: (float(x["cost"]), str(x["tool_id"])))

    for tool in eligible:
        tid = str(tool["tool_id"])
        impossible = False
        unknown: list[str] = []
        for cap in required:
            value = evidence.get((tid, cap))
            if value is False:
                impossible = True
                break
            if value is None:
                unknown.append(cap)
        if impossible:
            continue
        if unknown:
            if tool.get("safe_probe_allowed") is not True:
                continue
            return {
                "action": "PROBE",
                "tool_id": tid,
                "capability": unknown[0],
                "epoch": epochs[tid],
            }
        return {"action": "SELECT", "tool_id": tid, "epoch": epochs[tid]}

    return {"action": "ESCALATE", "reason": "NO_VERIFIED_ADMISSIBLE_TOOL_AFTER_COMPLETE_DISCOVERY"}
