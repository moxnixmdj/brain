"""Brain-owned tool-universe gateway V2.

The usable tool universe is owned by construction:
* invocation accepts only identities in one registry;
* discovery enumerates exactly that same registry;
* registry replacement advances a single universe epoch;
* stale episodes cannot invoke after an epoch change.

This module proves identity discoverability only. Capability truth, route quality,
transfer, and terminal acceptance remain separate obligations.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json, math
from typing import Any, Iterable, Mapping


SCHEMA = "PROJECT_BRAIN_TOOL_UNIVERSE_GATEWAY_V2"
SOURCE_ID = "BRAIN_OWNED_TOOL_UNIVERSE_GATEWAY_V2"


class GatewayError(RuntimeError):
    pass


@dataclass(frozen=True)
class ToolEntry:
    tool_id: str
    available: bool
    authorized: bool
    cost: float
    metadata: Mapping[str, Any]

    @classmethod
    def from_mapping(cls, row: Mapping[str, Any]) -> "ToolEntry":
        tid = str(row.get("tool_id") or "")
        if not tid:
            raise GatewayError("EMPTY_TOOL_ID")
        cost = row.get("cost", 0.0)
        if isinstance(cost, bool) or not isinstance(cost, (int, float)):
            raise GatewayError("INVALID_COST:" + tid)
        cost = float(cost)
        if not math.isfinite(cost) or cost < 0:
            raise GatewayError("INVALID_COST:" + tid)
        meta = {
            k: v for k, v in row.items()
            if k not in {"tool_id", "available", "authorized", "cost", "epoch"}
        }
        return cls(
            tool_id=tid,
            available=row.get("available") is True,
            authorized=row.get("authorized") is True,
            cost=cost,
            metadata=meta,
        )

    def public_metadata(self, epoch: int) -> dict[str, Any]:
        return {
            "tool_id": self.tool_id,
            "available": self.available,
            "authorized": self.authorized,
            "cost": self.cost,
            "epoch": epoch,
            **dict(self.metadata),
        }


class ToolUniverseGateway:
    def __init__(self, entries: Iterable[Mapping[str, Any]], *, epoch: int = 0):
        if isinstance(epoch, bool) or not isinstance(epoch, int) or epoch < 0:
            raise GatewayError("INVALID_EPOCH")
        self._epoch = epoch
        self._registry = self._normalize(entries)

    @staticmethod
    def _normalize(entries: Iterable[Mapping[str, Any]]) -> dict[str, ToolEntry]:
        out: dict[str, ToolEntry] = {}
        for raw in entries:
            if not isinstance(raw, Mapping):
                raise GatewayError("INVALID_TOOL_ENTRY")
            item = ToolEntry.from_mapping(raw)
            if item.tool_id in out:
                raise GatewayError("DUPLICATE_TOOL_ID:" + item.tool_id)
            out[item.tool_id] = item
        return out

    @property
    def epoch(self) -> int:
        return self._epoch

    def registry_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._registry))

    def invocable_ids(self) -> tuple[str, ...]:
        return tuple(sorted(
            tid for tid, item in self._registry.items()
            if item.available and item.authorized
        ))

    def discovery_source(self) -> dict[str, Any]:
        return {
            "source_id": SOURCE_ID,
            "available": True,
            "cost": 0.0,
            "epoch": self._epoch,
        }

    def discover(self) -> dict[str, Any]:
        tools = [
            self._registry[tid].public_metadata(self._epoch)
            for tid in sorted(self._registry)
        ]
        return {
            "kind": "DISCOVERY_RESULT",
            "source_id": SOURCE_ID,
            "epoch": self._epoch,
            "tools": tools,
            "registry_digest_sha256": self.registry_digest_sha256(),
        }

    def gate_invoke(self, tool_id: str, *, episode_epoch: int) -> ToolEntry:
        if episode_epoch != self._epoch:
            raise GatewayError("EPOCH_CHANGED_RESTART_EPISODE")
        tid = str(tool_id or "")
        item = self._registry.get(tid)
        if item is None:
            raise GatewayError("UNREGISTERED_TOOL_ID")
        if not item.available:
            raise GatewayError("TOOL_UNAVAILABLE")
        if not item.authorized:
            raise GatewayError("TOOL_UNAUTHORIZED")
        return item

    def replace_registry(self, entries: Iterable[Mapping[str, Any]]) -> int:
        self._registry = self._normalize(entries)
        self._epoch += 1
        return self._epoch

    def registry_digest_sha256(self) -> str:
        payload = {
            "epoch": self._epoch,
            "tools": [
                self._registry[tid].public_metadata(self._epoch)
                for tid in sorted(self._registry)
            ],
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return sha256(raw).hexdigest()


def prove_identity_completeness(gateway: ToolUniverseGateway) -> dict[str, Any]:
    receipt = gateway.discover()
    rows = receipt.get("tools")
    if not isinstance(rows, list):
        raise GatewayError("DISCOVERY_ROWS_INVALID")
    discovered = tuple(sorted(
        str(x.get("tool_id") or "") for x in rows if isinstance(x, Mapping)
    ))
    registry = gateway.registry_ids()
    invocable = gateway.invocable_ids()
    exact = discovered == registry
    covers = set(invocable).issubset(discovered)
    no_extra = set(discovered).issubset(registry)
    epoch_bound = all(
        isinstance(x, Mapping) and x.get("epoch") == gateway.epoch for x in rows
    )
    passed = exact and covers and no_extra and epoch_bound
    return {
        "schema": SCHEMA,
        "status": "PASS__OWNED_IDENTITY_SCOPE_COMPLETE" if passed else "FAIL_CLOSED",
        "registry_ids": list(registry),
        "invocable_ids": list(invocable),
        "discovered_ids": list(discovered),
        "exact_registry_enumeration": exact,
        "every_invocable_discoverable": covers,
        "no_discoverable_identity_outside_registry": no_extra,
        "discovery_epoch_bound": epoch_bound,
        "universal_set_relation": "INVOCABLE(R)_SUBSET_DISCOVER(R)_EQUALS_REGISTRY(R)",
        "new_reality_units_consumed": 0,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }
