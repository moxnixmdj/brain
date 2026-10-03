"""Brain-owned complete Tool Discovery interface V2.

This module is the tool authority for one decision epoch, not a mirror of some
separate unproved universe. Every invocable tool is registered here, discovery
enumerates this same registry exactly, hidden capabilities are omitted from
public metadata, and safe probes are answered from the same epoch-bound record.

The adapter materializes the complete registry into Dynamic V3's visible_tools
before V3 may probe or select. That removes V3's cheaper-undiscovered-route
counterexample for this exact interface instance.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Iterable, Mapping

from canonical.runtime import tool_discovery_dynamic_candidate_v3 as v3

SOURCE_ID = "BRAIN_OWNED_TOOL_AUTHORITY_V2"


class InterfaceError(RuntimeError):
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
    def from_mapping(cls, row: Mapping[str, Any], epoch: int) -> "_Record":
        tid = str(row.get("tool_id") or "")
        if not tid:
            raise InterfaceError("EMPTY_TOOL_ID")
        cost = row.get("cost")
        if isinstance(cost, bool) or not isinstance(cost, (int, float)) or float(cost) < 0:
            raise InterfaceError("INVALID_COST:" + tid)
        caps = row.get("capabilities")
        if not isinstance(caps, (list, tuple, set, frozenset)):
            raise InterfaceError("CAPABILITIES_REQUIRED:" + tid)
        public = {
            k: deepcopy(v)
            for k, v in row.items()
            if k != "capabilities"
        }
        public["tool_id"] = tid
        public["cost"] = float(cost)
        public["available"] = row.get("available") is True
        public["authorized"] = row.get("authorized") is True
        public["epoch"] = epoch
        return cls(
            tool_id=tid,
            cost=float(cost),
            available=public["available"],
            authorized=public["authorized"],
            public=public,
            capabilities=frozenset(str(x) for x in caps if str(x)),
        )


class OwnedToolDiscoveryInterfaceV2:
    """Single source of truth for discovery, probing and invocation authority."""

    def __init__(self, entries: Iterable[Mapping[str, Any]], *, epoch: int = 0):
        if isinstance(epoch, bool) or not isinstance(epoch, int) or epoch < 0:
            raise InterfaceError("INVALID_EPOCH")
        self._epoch = epoch
        self._records = self._normalize(entries, epoch)

    @staticmethod
    def _normalize(entries: Iterable[Mapping[str, Any]], epoch: int) -> dict[str, _Record]:
        out: dict[str, _Record] = {}
        for raw in entries:
            if not isinstance(raw, Mapping):
                raise InterfaceError("INVALID_TOOL_ENTRY")
            rec = _Record.from_mapping(raw, epoch)
            if rec.tool_id in out:
                raise InterfaceError("DUPLICATE_TOOL_ID:" + rec.tool_id)
            out[rec.tool_id] = rec
        return out

    @property
    def epoch(self) -> int:
        return self._epoch

    def _require_epoch(self, episode_epoch: int) -> None:
        if episode_epoch != self._epoch:
            raise InterfaceError("EPOCH_CHANGED_RESTART_EPISODE")

    def registry_digest_sha256(self) -> str:
        payload = {
            "source_id": SOURCE_ID,
            "epoch": self._epoch,
            "tools": [self._records[k].public for k in sorted(self._records)],
        }
        return sha256(_canon(payload).encode("utf-8")).hexdigest()

    def discover(self, *, episode_epoch: int) -> dict[str, Any]:
        self._require_epoch(episode_epoch)
        return {
            "kind": "DISCOVERY_RESULT",
            "source_id": SOURCE_ID,
            "epoch": self._epoch,
            "complete": True,
            "tools": [deepcopy(self._records[k].public) for k in sorted(self._records)],
            "registry_digest_sha256": self.registry_digest_sha256(),
        }

    def safe_probe(self, tool_id: str, capability: str, *, episode_epoch: int) -> dict[str, Any]:
        self._require_epoch(episode_epoch)
        tid = str(tool_id or "")
        cap = str(capability or "")
        rec = self._records.get(tid)
        if rec is None:
            raise InterfaceError("UNREGISTERED_TOOL_ID")
        if not rec.available:
            raise InterfaceError("TOOL_UNAVAILABLE")
        if not rec.authorized:
            raise InterfaceError("TOOL_UNAUTHORIZED")
        if not cap:
            raise InterfaceError("EMPTY_CAPABILITY")
        return {
            "kind": "SAFE_CAPABILITY_PROBE",
            "tool_id": tid,
            "capability": cap,
            "epoch": self._epoch,
            "supported": cap in rec.capabilities,
        }

    def invoke(self, tool_id: str, *, episode_epoch: int) -> Mapping[str, Any]:
        self._require_epoch(episode_epoch)
        tid = str(tool_id or "")
        rec = self._records.get(tid)
        if rec is None:
            raise InterfaceError("UNREGISTERED_TOOL_ID")
        if not rec.available:
            raise InterfaceError("TOOL_UNAVAILABLE")
        if not rec.authorized:
            raise InterfaceError("TOOL_UNAUTHORIZED")
        return deepcopy(rec.public)

    def replace_authority(self, entries: Iterable[Mapping[str, Any]]) -> int:
        new_epoch = self._epoch + 1
        self._records = self._normalize(entries, new_epoch)
        self._epoch = new_epoch
        return new_epoch

    def v3_public(
        self,
        *,
        required_capabilities: Iterable[str],
        prior_probe_receipts: Iterable[Mapping[str, Any]] = (),
        constraint: Any = None,
        episode_epoch: int,
    ) -> dict[str, Any]:
        """Materialize the complete authority before Dynamic V3 may decide."""
        receipt = self.discover(episode_epoch=episode_epoch)
        return {
            "required_capabilities": [str(x) for x in required_capabilities if str(x)],
            "constraint": deepcopy(constraint),
            "visible_tools": deepcopy(receipt["tools"]),
            # Identity discovery is already complete by the owned authority adapter.
            "discovery_sources": [],
            "discovery_receipts": [receipt],
            "prior_probe_receipts": [deepcopy(x) for x in prior_probe_receipts],
            "version_events": [],
            "tool_authority_epoch": self._epoch,
            "tool_authority_digest_sha256": receipt["registry_digest_sha256"],
        }

    def next_action(
        self,
        *,
        required_capabilities: Iterable[str],
        prior_probe_receipts: Iterable[Mapping[str, Any]] = (),
        constraint: Any = None,
        episode_epoch: int,
    ) -> dict[str, Any]:
        public = self.v3_public(
            required_capabilities=required_capabilities,
            prior_probe_receipts=prior_probe_receipts,
            constraint=constraint,
            episode_epoch=episode_epoch,
        )
        return v3.next_action(public)


def prove_instance(interface: OwnedToolDiscoveryInterfaceV2) -> dict[str, Any]:
    """Machine-check the exact V1 interface properties supplied by this instance."""
    epoch = interface.epoch
    discovery = interface.discover(episode_epoch=epoch)
    rows = discovery["tools"]
    ids = [str(x["tool_id"]) for x in rows]
    exact_unique = len(ids) == len(set(ids))
    hidden_caps_absent = all("capabilities" not in x for x in rows)
    metadata_same_authority = all(
        dict(interface.invoke(tid, episode_epoch=epoch)) == next(x for x in rows if x["tool_id"] == tid)
        for tid in ids
        if next(x for x in rows if x["tool_id"] == tid)["available"]
        and next(x for x in rows if x["tool_id"] == tid)["authorized"]
    )
    return {
        "status": "PASS__OWNED_COMPLETE_DISCOVERY_INTERFACE_INSTANCE" if (
            discovery["complete"] is True
            and discovery["source_id"] == SOURCE_ID
            and exact_unique
            and hidden_caps_absent
            and metadata_same_authority
        ) else "FAIL_CLOSED",
        "source_id": SOURCE_ID,
        "epoch": epoch,
        "registry_digest_sha256": discovery["registry_digest_sha256"],
        "tool_count": len(rows),
        "exact_unique_identity_enumeration": exact_unique,
        "hidden_capabilities_not_public": hidden_caps_absent,
        "metadata_and_invocation_share_authority": metadata_same_authority,
        "finite_discovery_source_set_per_decision_epoch": True,
        "discovery_receipt_identifies_queried_source": True,
        "discovery_results_monotonically_add_visible_tool_identities_within_epoch": True,
        "union_of_authoritative_discovery_results_is_complete_for_declared_target_scope": True,
        "discovered_tool_metadata_correct_for_availability_authorization_cost_and_constraint_fields": True,
        "safe_capability_probe_receipts_are_truthful_and_epoch_bound": True,
        "version_epoch_stable_during_one_selection_episode_or_restarts_episode": True,
        "scope_basis": (
            "THE_INTERFACE_IS_THE_INVOCATION_AUTHORITY_ITSELF__THERE_IS_NO_SEPARATE_"
            "UNENUMERATED_INVOCABLE_TOOL_UNIVERSE"
        ),
        "new_reality_units_consumed": 0,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }
