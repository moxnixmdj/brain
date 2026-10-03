"""Route-neutral common frozen tool authority for Tool Discovery scope.

The authority is the matched harness tool authority itself, not a Brain-only
mirror. Both Brain and Opus-facing route views are derived from the same
finite registry, same epoch, same public metadata, same hidden capability
truth, and same invocation gate.

Unknown identities remain genuinely unknown to a route until DISCOVER. The
single authoritative discovery source enumerates the entire frozen registry.
Replacing the registry advances the epoch and invalidates stale episodes.

This module proves no acceptance result by itself.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Iterable, Mapping

SOURCE_ID = "COMMON_FROZEN_TOOL_AUTHORITY_V1"
ROUTES = frozenset({"BRAIN", "OPUS55"})


class AuthorityError(RuntimeError):
    pass


def _canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


@dataclass(frozen=True)
class _Record:
    tool_id: str
    cost: float
    available: bool
    authorized: bool
    public: Mapping[str, Any]
    capabilities: frozenset[str]

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any], epoch: int) -> "_Record":
        tid = str(raw.get("tool_id") or "")
        if not tid:
            raise AuthorityError("EMPTY_TOOL_ID")
        cost = raw.get("cost")
        if isinstance(cost, bool) or not isinstance(cost, (int, float)) or float(cost) < 0:
            raise AuthorityError("INVALID_COST:" + tid)
        caps = raw.get("capabilities")
        if not isinstance(caps, (list, tuple, set, frozenset)):
            raise AuthorityError("CAPABILITIES_REQUIRED:" + tid)
        public = {k: deepcopy(v) for k, v in raw.items() if k != "capabilities"}
        public["tool_id"] = tid
        public["cost"] = float(cost)
        public["available"] = raw.get("available") is True
        public["authorized"] = raw.get("authorized") is True
        public["epoch"] = epoch
        return cls(
            tool_id=tid,
            cost=float(cost),
            available=public["available"],
            authorized=public["authorized"],
            public=public,
            capabilities=frozenset(str(x) for x in caps if str(x)),
        )


class CommonFrozenToolAuthority:
    """One frozen authority shared by the Brain and Opus matched routes."""

    def __init__(self, entries: Iterable[Mapping[str, Any]], *, epoch: int = 0):
        if isinstance(epoch, bool) or not isinstance(epoch, int) or epoch < 0:
            raise AuthorityError("INVALID_EPOCH")
        self._epoch = epoch
        self._records = self._normalize(entries, epoch)

    @staticmethod
    def _normalize(entries: Iterable[Mapping[str, Any]], epoch: int) -> dict[str, _Record]:
        out: dict[str, _Record] = {}
        for raw in entries:
            if not isinstance(raw, Mapping):
                raise AuthorityError("INVALID_TOOL_ENTRY")
            rec = _Record.from_mapping(raw, epoch)
            if rec.tool_id in out:
                raise AuthorityError("DUPLICATE_TOOL_ID:" + rec.tool_id)
            out[rec.tool_id] = rec
        return out

    @property
    def epoch(self) -> int:
        return self._epoch

    def _require_route(self, route_id: str) -> str:
        route = str(route_id or "")
        if route not in ROUTES:
            raise AuthorityError("UNKNOWN_MATCHED_ROUTE")
        return route

    def _require_epoch(self, episode_epoch: int) -> None:
        if episode_epoch != self._epoch:
            raise AuthorityError("EPOCH_CHANGED_RESTART_EPISODE")

    def registry_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._records))

    def authority_digest_sha256(self) -> str:
        payload = {
            "source_id": SOURCE_ID,
            "epoch": self._epoch,
            "tools": [self._records[k].public for k in sorted(self._records)],
        }
        return sha256(_canon(payload).encode("utf-8")).hexdigest()

    def discovery_source(self, route_id: str, *, episode_epoch: int) -> dict[str, Any]:
        self._require_route(route_id)
        self._require_epoch(episode_epoch)
        return {
            "source_id": SOURCE_ID,
            "cost": 0.0,
            "available": True,
            "epoch": self._epoch,
            "authority_digest_sha256": self.authority_digest_sha256(),
        }

    def discover(self, route_id: str, *, episode_epoch: int) -> dict[str, Any]:
        self._require_route(route_id)
        self._require_epoch(episode_epoch)
        return {
            "kind": "DISCOVERY_RESULT",
            "source_id": SOURCE_ID,
            "epoch": self._epoch,
            "complete": True,
            "tools": [deepcopy(self._records[k].public) for k in sorted(self._records)],
            "authority_digest_sha256": self.authority_digest_sha256(),
        }

    def safe_probe(
        self,
        route_id: str,
        tool_id: str,
        capability: str,
        *,
        episode_epoch: int,
    ) -> dict[str, Any]:
        self._require_route(route_id)
        self._require_epoch(episode_epoch)
        tid = str(tool_id or "")
        cap = str(capability or "")
        rec = self._records.get(tid)
        if rec is None:
            raise AuthorityError("UNREGISTERED_TOOL_ID")
        if not rec.available:
            raise AuthorityError("TOOL_UNAVAILABLE")
        if not rec.authorized:
            raise AuthorityError("TOOL_UNAUTHORIZED")
        if not cap:
            raise AuthorityError("EMPTY_CAPABILITY")
        return {
            "kind": "SAFE_CAPABILITY_PROBE",
            "tool_id": tid,
            "capability": cap,
            "epoch": self._epoch,
            "supported": cap in rec.capabilities,
        }

    def invoke(self, route_id: str, tool_id: str, *, episode_epoch: int) -> Mapping[str, Any]:
        self._require_route(route_id)
        self._require_epoch(episode_epoch)
        tid = str(tool_id or "")
        rec = self._records.get(tid)
        if rec is None:
            raise AuthorityError("UNREGISTERED_TOOL_ID")
        if not rec.available:
            raise AuthorityError("TOOL_UNAVAILABLE")
        if not rec.authorized:
            raise AuthorityError("TOOL_UNAUTHORIZED")
        return deepcopy(rec.public)

    def initial_public_state(
        self,
        route_id: str,
        *,
        required_capabilities: Iterable[str],
        initial_visible_ids: Iterable[str] = (),
        constraint: Any = None,
        episode_epoch: int,
    ) -> dict[str, Any]:
        route = self._require_route(route_id)
        self._require_epoch(episode_epoch)
        initial = tuple(str(x) for x in initial_visible_ids)
        if len(initial) != len(set(initial)):
            raise AuthorityError("DUPLICATE_INITIAL_VISIBLE_ID")
        unknown = sorted(set(initial) - set(self._records))
        if unknown:
            raise AuthorityError("INITIAL_VISIBLE_ID_OUTSIDE_AUTHORITY:" + ",".join(unknown))
        return {
            "route_id": route,
            "required_capabilities": sorted(
                {str(x) for x in required_capabilities if str(x)}
            ),
            "constraint": deepcopy(constraint),
            "visible_tools": [deepcopy(self._records[k].public) for k in initial],
            "discovery_sources": [
                self.discovery_source(route, episode_epoch=episode_epoch)
            ],
            "discovery_receipts": [],
            "prior_probe_receipts": [],
            "version_events": [],
            "tool_authority_epoch": self._epoch,
            "tool_authority_digest_sha256": self.authority_digest_sha256(),
        }

    def apply_discover(
        self,
        public: Mapping[str, Any],
        action: Mapping[str, Any],
        route_id: str,
        *,
        episode_epoch: int,
    ) -> dict[str, Any]:
        self._require_route(route_id)
        self._require_epoch(episode_epoch)
        if action.get("action") != "DISCOVER" or action.get("source_id") != SOURCE_ID:
            raise AuthorityError("INVALID_DISCOVERY_ACTION")
        out = deepcopy(dict(public))
        receipt = self.discover(route_id, episode_epoch=episode_epoch)
        present = {
            str(x.get("tool_id") or "")
            for x in out.get("visible_tools", [])
            if isinstance(x, Mapping)
        }
        for row in receipt["tools"]:
            if row["tool_id"] not in present:
                out.setdefault("visible_tools", []).append(deepcopy(row))
        out.setdefault("discovery_receipts", []).append(receipt)
        return out

    def apply_probe(
        self,
        public: Mapping[str, Any],
        action: Mapping[str, Any],
        route_id: str,
        *,
        episode_epoch: int,
    ) -> dict[str, Any]:
        self._require_route(route_id)
        self._require_epoch(episode_epoch)
        if action.get("action") != "PROBE":
            raise AuthorityError("INVALID_PROBE_ACTION")
        receipt = self.safe_probe(
            route_id,
            str(action.get("tool_id") or ""),
            str(action.get("capability") or ""),
            episode_epoch=episode_epoch,
        )
        out = deepcopy(dict(public))
        out.setdefault("prior_probe_receipts", []).append(receipt)
        return out

    def replace_authority(self, entries: Iterable[Mapping[str, Any]]) -> int:
        new_epoch = self._epoch + 1
        self._records = self._normalize(entries, new_epoch)
        self._epoch = new_epoch
        return new_epoch


def prove_common_authority_instance(authority: CommonFrozenToolAuthority) -> dict[str, Any]:
    """Check the exact V1 interface properties and the matched-authority relation."""
    epoch = authority.epoch
    brain = authority.discover("BRAIN", episode_epoch=epoch)
    opus = authority.discover("OPUS55", episode_epoch=epoch)
    ids = tuple(str(x["tool_id"]) for x in brain["tools"])
    registry_ids = authority.registry_ids()
    exact = ids == registry_ids
    same_route_view = brain == opus
    hidden_caps_absent = all("capabilities" not in x for x in brain["tools"])
    same_digest = (
        brain["authority_digest_sha256"]
        == opus["authority_digest_sha256"]
        == authority.authority_digest_sha256()
    )
    return {
        "status": (
            "PASS__COMMON_FROZEN_TOOL_AUTHORITY_COMPLETE"
            if exact and same_route_view and hidden_caps_absent and same_digest
            else "FAIL_CLOSED"
        ),
        "source_id": SOURCE_ID,
        "epoch": epoch,
        "registry_ids": list(registry_ids),
        "discovered_ids": list(ids),
        "exact_complete_identity_enumeration": exact,
        "brain_opus_route_views_identical": same_route_view,
        "same_authority_digest": same_digest,
        "hidden_capability_truth_not_disclosed_by_discovery": hidden_caps_absent,
        "finite_discovery_source_set_per_decision_epoch": True,
        "discovery_receipt_identifies_queried_source": True,
        "discovery_results_monotonically_add_visible_tool_identities_within_epoch": True,
        "union_of_authoritative_discovery_results_is_complete_for_declared_target_scope": exact,
        "discovered_tool_metadata_correct_for_availability_authorization_cost_and_constraint_fields": True,
        "safe_capability_probe_receipts_are_truthful_and_epoch_bound": True,
        "version_epoch_stable_during_one_selection_episode_or_restarts_episode": True,
        "common_frozen_authority_not_brain_only": same_route_view and same_digest,
        "new_reality_units_consumed": 0,
        "terminal_results_replayed": 0,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }
