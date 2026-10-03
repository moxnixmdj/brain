"""Owned-authority universal Tool Discovery candidate V5.

Goal: prove the one remaining Tool Discovery predicate without narrowing the
frozen target.  The construction quantifies over an arbitrary finite tool
authority for one stable epoch.

Key invariants
--------------
* The owned registry IS the invocation authority for the episode.
* Every registry identity belongs to exactly one discovery source.
* Discovery starts with identities hidden and exhausts all sources before route
  choice, so unknown identities cannot hide a cheaper sufficient route.
* Capability truth is absent from discovery metadata and is learned only from
  epoch-bound safe probes.
* Active constraints are represented by a public normalized admissibility bit;
  schema parsing / exact constraint filtering is a deterministic upstream
  component in the frozen behavioral contract.
* Missing probe permission for an unresolved cheaper route fails closed.  The
  policy never skips an unknowable cheaper route and falsely claims optimality.
* Registry replacement advances the epoch, invalidating stale evidence.

This module grants no acceptance/family/execution/promotion authority by itself.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Iterable, Mapping


SOURCE_SCHEMA = "PROJECT_BRAIN_TOOL_DISCOVERY_OWNED_AUTHORITY_V5"


class AuthorityError(RuntimeError):
    pass


def _canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


@dataclass(frozen=True)
class _Tool:
    tool_id: str
    source_id: str
    cost: float
    available: bool
    authorized: bool
    admissible: bool
    safe_probe_capabilities: frozenset[str]
    capabilities: frozenset[str]
    public_extra: Mapping[str, Any]

    @classmethod
    def from_mapping(cls, row: Mapping[str, Any]) -> "_Tool":
        tid = str(row.get("tool_id") or "")
        sid = str(row.get("source_id") or "")
        if not tid:
            raise AuthorityError("EMPTY_TOOL_ID")
        if not sid:
            raise AuthorityError("EMPTY_SOURCE_ID:" + tid)
        cost = row.get("cost")
        if isinstance(cost, bool) or not isinstance(cost, (int, float)) or float(cost) < 0:
            raise AuthorityError("INVALID_COST:" + tid)
        caps = row.get("capabilities")
        if not isinstance(caps, (list, tuple, set, frozenset)):
            raise AuthorityError("CAPABILITIES_REQUIRED:" + tid)
        safe = row.get("safe_probe_capabilities")
        if not isinstance(safe, (list, tuple, set, frozenset)):
            raise AuthorityError("SAFE_PROBE_CAPABILITIES_REQUIRED:" + tid)
        reserved = {
            "tool_id", "source_id", "cost", "available", "authorized",
            "admissible", "safe_probe_capabilities", "capabilities", "epoch",
        }
        extra = {k: deepcopy(v) for k, v in row.items() if k not in reserved}
        return cls(
            tool_id=tid,
            source_id=sid,
            cost=float(cost),
            available=row.get("available") is True,
            authorized=row.get("authorized") is True,
            admissible=row.get("admissible") is True,
            safe_probe_capabilities=frozenset(str(x) for x in safe if str(x)),
            capabilities=frozenset(str(x) for x in caps if str(x)),
            public_extra=extra,
        )

    def public(self, epoch: int) -> dict[str, Any]:
        out = deepcopy(dict(self.public_extra))
        out.update({
            "tool_id": self.tool_id,
            "source_id": self.source_id,
            "cost": self.cost,
            "available": self.available,
            "authorized": self.authorized,
            "admissible": self.admissible,
            "safe_probe_capabilities": sorted(self.safe_probe_capabilities),
            "epoch": epoch,
        })
        return out


class OwnedToolAuthorityV5:
    """Complete finite authority for one frozen decision epoch."""

    def __init__(self, entries: Iterable[Mapping[str, Any]], *, epoch: int = 0):
        if isinstance(epoch, bool) or not isinstance(epoch, int) or epoch < 0:
            raise AuthorityError("INVALID_EPOCH")
        self._epoch = epoch
        self._tools = self._normalize(entries)

    @staticmethod
    def _normalize(entries: Iterable[Mapping[str, Any]]) -> dict[str, _Tool]:
        out: dict[str, _Tool] = {}
        for raw in entries:
            if not isinstance(raw, Mapping):
                raise AuthorityError("INVALID_TOOL_ENTRY")
            tool = _Tool.from_mapping(raw)
            if tool.tool_id in out:
                raise AuthorityError("DUPLICATE_TOOL_ID:" + tool.tool_id)
            out[tool.tool_id] = tool
        return out

    @property
    def epoch(self) -> int:
        return self._epoch

    def registry_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._tools))

    def source_ids(self) -> tuple[str, ...]:
        return tuple(sorted({tool.source_id for tool in self._tools.values()}))

    def source_descriptors(self) -> list[dict[str, Any]]:
        return [
            {"source_id": sid, "available": True, "cost": 0.0, "epoch": self._epoch}
            for sid in self.source_ids()
        ]

    def registry_digest_sha256(self) -> str:
        # Candidate-visible digest binds only public authority metadata.
        # Hidden capability truth must never be encoded into a public digest,
        # even indirectly, because a small hidden state space can make hashes
        # distinguishable by enumeration.
        rows = [
            self._tools[tid].public(self._epoch)
            for tid in self.registry_ids()
        ]
        payload = {"epoch": self._epoch, "public_rows": rows}
        return sha256(_canon(payload).encode("utf-8")).hexdigest()

    def initial_public(
        self,
        *,
        required_capabilities: Iterable[str],
        prior_probe_receipts: Iterable[Mapping[str, Any]] = (),
    ) -> dict[str, Any]:
        return {
            "required_capabilities": sorted({str(x) for x in required_capabilities if str(x)}),
            "visible_tools": [],
            "discovery_sources": self.source_descriptors(),
            "discovery_receipts": [],
            "prior_probe_receipts": [deepcopy(x) for x in prior_probe_receipts],
            "authority_epoch": self._epoch,
            "authority_digest_sha256": self.registry_digest_sha256(),
        }

    def _require_epoch(self, episode_epoch: int) -> None:
        if episode_epoch != self._epoch:
            raise AuthorityError("EPOCH_CHANGED_RESTART_EPISODE")

    def discover(self, source_id: str, *, episode_epoch: int) -> dict[str, Any]:
        self._require_epoch(episode_epoch)
        sid = str(source_id or "")
        if sid not in set(self.source_ids()):
            raise AuthorityError("UNKNOWN_DISCOVERY_SOURCE")
        rows = [
            self._tools[tid].public(self._epoch)
            for tid in self.registry_ids()
            if self._tools[tid].source_id == sid
        ]
        return {
            "kind": "DISCOVERY_RESULT",
            "source_id": sid,
            "epoch": self._epoch,
            "tools": rows,
            "authority_digest_sha256": self.registry_digest_sha256(),
        }

    def safe_probe(
        self,
        tool_id: str,
        capability: str,
        *,
        episode_epoch: int,
    ) -> dict[str, Any]:
        self._require_epoch(episode_epoch)
        tid = str(tool_id or "")
        cap = str(capability or "")
        tool = self._tools.get(tid)
        if tool is None:
            raise AuthorityError("UNREGISTERED_TOOL_ID")
        if not tool.available:
            raise AuthorityError("TOOL_UNAVAILABLE")
        if not tool.authorized:
            raise AuthorityError("TOOL_UNAUTHORIZED")
        if not tool.admissible:
            raise AuthorityError("TOOL_CONSTRAINT_INADMISSIBLE")
        if cap not in tool.safe_probe_capabilities:
            raise AuthorityError("SAFE_PROBE_NOT_PERMITTED")
        return {
            "kind": "SAFE_CAPABILITY_PROBE",
            "tool_id": tid,
            "capability": cap,
            "epoch": self._epoch,
            "supported": cap in tool.capabilities,
        }

    def invoke(self, tool_id: str, *, episode_epoch: int) -> Mapping[str, Any]:
        self._require_epoch(episode_epoch)
        tid = str(tool_id or "")
        tool = self._tools.get(tid)
        if tool is None:
            raise AuthorityError("UNREGISTERED_TOOL_ID")
        if not tool.available:
            raise AuthorityError("TOOL_UNAVAILABLE")
        if not tool.authorized:
            raise AuthorityError("TOOL_UNAUTHORIZED")
        if not tool.admissible:
            raise AuthorityError("TOOL_CONSTRAINT_INADMISSIBLE")
        return deepcopy(tool.public(self._epoch))

    def replace_authority(self, entries: Iterable[Mapping[str, Any]]) -> int:
        new_tools = self._normalize(entries)
        self._tools = new_tools
        self._epoch += 1
        return self._epoch


def _queried_sources(public: Mapping[str, Any]) -> set[str]:
    epoch = int(public.get("authority_epoch", -1))
    return {
        str(row.get("source_id") or "")
        for row in public.get("discovery_receipts", [])
        if isinstance(row, Mapping)
        and row.get("kind") == "DISCOVERY_RESULT"
        and int(row.get("epoch", -2)) == epoch
        and str(row.get("source_id") or "")
    }


def _evidence(public: Mapping[str, Any]) -> dict[tuple[str, str], bool]:
    epoch = int(public.get("authority_epoch", -1))
    visible = {
        str(t.get("tool_id") or "")
        for t in public.get("visible_tools", [])
        if isinstance(t, Mapping)
    }
    out: dict[tuple[str, str], bool] = {}
    for rec in public.get("prior_probe_receipts", []):
        if not isinstance(rec, Mapping) or rec.get("kind") != "SAFE_CAPABILITY_PROBE":
            continue
        tid = str(rec.get("tool_id") or "")
        cap = str(rec.get("capability") or "")
        if tid in visible and int(rec.get("epoch", -2)) == epoch and cap:
            out[(tid, cap)] = rec.get("supported") is True
    return out


def next_action(public: Mapping[str, Any]) -> dict[str, Any]:
    """Discovery-closure-first, evidence-backed least-cost policy."""
    required = sorted({str(x) for x in public.get("required_capabilities", []) if str(x)})
    if not required:
        return {"action": "ESCALATE", "reason": "NO_REQUIRED_CAPABILITIES"}

    epoch = int(public.get("authority_epoch", -1))
    queried = _queried_sources(public)
    sources = [
        s for s in public.get("discovery_sources", [])
        if isinstance(s, Mapping)
        and s.get("available") is True
        and int(s.get("epoch", -2)) == epoch
        and str(s.get("source_id") or "")
        and str(s.get("source_id") or "") not in queried
    ]
    sources.sort(key=lambda s: (float(s.get("cost", 0.0)), str(s.get("source_id") or "")))
    if sources:
        return {
            "action": "DISCOVER",
            "source_id": str(sources[0].get("source_id") or ""),
            "query": " ".join(required),
        }

    evidence = _evidence(public)
    tools = [
        t for t in public.get("visible_tools", [])
        if isinstance(t, Mapping)
        and int(t.get("epoch", -2)) == epoch
        and t.get("available") is True
        and t.get("authorized") is True
        and t.get("admissible") is True
    ]
    tools.sort(key=lambda t: (float(t.get("cost", 0.0)), str(t.get("tool_id") or "")))

    for tool in tools:
        tid = str(tool.get("tool_id") or "")
        permissions = {
            str(x) for x in tool.get("safe_probe_capabilities", [])
            if str(x)
        }
        unresolved: list[str] = []
        eliminated = False
        for cap in required:
            value = evidence.get((tid, cap))
            if value is False:
                eliminated = True
                break
            if value is None:
                unresolved.append(cap)
        if eliminated:
            continue
        if unresolved:
            cap = unresolved[0]
            if cap not in permissions:
                return {
                    "action": "ESCALATE",
                    "reason": "SAFE_PROBE_PERMISSION_MISSING_FOR_UNRESOLVED_CHEAPER_ROUTE",
                    "tool_id": tid,
                    "capability": cap,
                }
            return {"action": "PROBE", "tool_id": tid, "capability": cap}
        return {"action": "SELECT", "tool_id": tid}

    return {"action": "ESCALATE", "reason": "NO_VERIFIED_ADMISSIBLE_SUFFICIENT_ROUTE"}


def apply_discovery(public: dict[str, Any], receipt: Mapping[str, Any]) -> None:
    """Deterministically materialize one exact discovery receipt into public state."""
    if receipt.get("kind") != "DISCOVERY_RESULT":
        raise AuthorityError("NOT_DISCOVERY_RESULT")
    epoch = int(public.get("authority_epoch", -1))
    if int(receipt.get("epoch", -2)) != epoch:
        raise AuthorityError("STALE_DISCOVERY_RECEIPT")
    existing = {
        str(row.get("tool_id") or "")
        for row in public.get("visible_tools", [])
        if isinstance(row, Mapping)
    }
    for row in receipt.get("tools", []):
        if not isinstance(row, Mapping):
            raise AuthorityError("INVALID_DISCOVERY_TOOL_ROW")
        tid = str(row.get("tool_id") or "")
        if not tid:
            raise AuthorityError("EMPTY_DISCOVERED_TOOL_ID")
        if tid in existing:
            raise AuthorityError("DUPLICATE_DISCOVERED_TOOL_ID:" + tid)
        public.setdefault("visible_tools", []).append(deepcopy(dict(row)))
        existing.add(tid)
    public.setdefault("discovery_receipts", []).append(deepcopy(dict(receipt)))


def theorem_invariants(authority: OwnedToolAuthorityV5) -> dict[str, Any]:
    """Machine-check construction invariants; universal reasoning is in the bound theorem."""
    epoch = authority.epoch
    all_rows: list[Mapping[str, Any]] = []
    for source in authority.source_descriptors():
        receipt = authority.discover(source["source_id"], episode_epoch=epoch)
        all_rows.extend(receipt["tools"])
    discovered_ids = sorted(str(x["tool_id"]) for x in all_rows)
    registry_ids = list(authority.registry_ids())
    hidden_caps_absent = all("capabilities" not in row for row in all_rows)
    exact_union = discovered_ids == registry_ids and len(discovered_ids) == len(set(discovered_ids))
    return {
        "schema": SOURCE_SCHEMA,
        "status": "PASS__OWNED_COMPLETE_AUTHORITY_INVARIANTS" if exact_union and hidden_caps_absent else "FAIL_CLOSED",
        "epoch": epoch,
        "registry_ids": registry_ids,
        "discovered_ids": discovered_ids,
        "source_union_exact_registry": exact_union,
        "hidden_capabilities_absent_from_discovery": hidden_caps_absent,
        "unregistered_identity_uninvocable_by_construction": True,
        "registry_replacement_advances_epoch": True,
        "new_reality_units_consumed": 0,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }
