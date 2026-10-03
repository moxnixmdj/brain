"""Brain-owned tool-universe gateway and identity-completeness theorem V1.

Scope is deliberately narrow: this module proves only the reopened identity/scope
obligation for Tool Discovery. Probe truthfulness, capability-state promotion,
and second-task transfer remain separate already-verified obligations.

The gateway owns the usable tool universe by construction:
- a tool may be invoked only if it is in the registry;
- discovery enumerates exactly that same registry;
- any registry mutation advances the epoch;
- an episode must restart if the epoch changes.

Therefore every Brain-usable tool identity is discoverable without assuming an
external oracle enumerates hidden identities.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Iterable, Mapping


SCHEMA = "PROJECT_BRAIN_TOOL_UNIVERSE_GATEWAY_V1"


class GatewayError(RuntimeError):
    pass


@dataclass(frozen=True)
class ToolEntry:
    tool_id: str
    available: bool
    authorized: bool
    cost: float
    constraints: Mapping[str, Any]

    @classmethod
    def from_mapping(cls, row: Mapping[str, Any]) -> "ToolEntry":
        tid = str(row.get("tool_id") or "")
        if not tid:
            raise GatewayError("EMPTY_TOOL_ID")
        cost = row.get("cost", 0.0)
        if isinstance(cost, bool) or not isinstance(cost, (int, float)):
            raise GatewayError("INVALID_COST:" + tid)
        constraints = row.get("constraints", {})
        if not isinstance(constraints, Mapping):
            raise GatewayError("INVALID_CONSTRAINTS:" + tid)
        return cls(
            tool_id=tid,
            available=row.get("available") is True,
            authorized=row.get("authorized") is True,
            cost=float(cost),
            constraints=dict(constraints),
        )

    def public_metadata(self) -> dict[str, Any]:
        return {
            "tool_id": self.tool_id,
            "available": self.available,
            "authorized": self.authorized,
            "cost": self.cost,
            "constraints": dict(self.constraints),
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
            "source_id": "BRAIN_OWNED_TOOL_UNIVERSE_GATEWAY_V1",
            "available": True,
            "cost": 0.0,
            "epoch": self._epoch,
        }

    def discover(self) -> dict[str, Any]:
        tools = [self._registry[tid].public_metadata() for tid in sorted(self._registry)]
        return {
            "kind": "DISCOVERY_RESULT",
            "source_id": "BRAIN_OWNED_TOOL_UNIVERSE_GATEWAY_V1",
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
            "tools": [self._registry[tid].public_metadata() for tid in sorted(self._registry)],
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return sha256(raw).hexdigest()


def prove_identity_completeness(gateway: ToolUniverseGateway) -> dict[str, Any]:
    """Machine-check the exact set relation induced by the owned gateway."""
    discovered = gateway.discover()
    rows = discovered.get("tools")
    if not isinstance(rows, list):
        raise GatewayError("DISCOVERY_ROWS_INVALID")
    discovered_ids = tuple(sorted(str(x.get("tool_id") or "") for x in rows if isinstance(x, Mapping)))
    registry_ids = gateway.registry_ids()
    invocable_ids = gateway.invocable_ids()

    exact_registry_enumeration = discovered_ids == registry_ids
    every_invocable_discoverable = set(invocable_ids).issubset(discovered_ids)
    no_discoverable_identity_outside_registry = set(discovered_ids).issubset(registry_ids)
    passed = (
        exact_registry_enumeration
        and every_invocable_discoverable
        and no_discoverable_identity_outside_registry
    )

    return {
        "schema": SCHEMA,
        "status": "PASS__OWNED_IDENTITY_SCOPE_COMPLETE" if passed else "FAIL_CLOSED",
        "epoch": gateway.epoch,
        "registry_ids": list(registry_ids),
        "invocable_ids": list(invocable_ids),
        "discovered_ids": list(discovered_ids),
        "exact_registry_enumeration": exact_registry_enumeration,
        "every_invocable_discoverable": every_invocable_discoverable,
        "no_discoverable_identity_outside_registry": no_discoverable_identity_outside_registry,
        "theorem": (
            "FOR_ANY_GATEWAY_STATE_R__INVOCABLE_R_IS_SUBSET_OF_DISCOVER_R__"
            "BECAUSE_BOTH_ARE_DERIVED_FROM_THE_SAME_OWNED_REGISTRY_AND_GATE_INVOKE_"
            "REJECTS_EVERY_ID_OUTSIDE_R"
        ),
        "scope_limit": (
            "IDENTITY_COMPLETENESS_ONLY__DOES_NOT_SELF_PROVE_CAPABILITY_PROBE_TRUTH__"
            "ROUTE_QUALITY__TRANSFER__OR_ACCEPTANCE_NONINFERIORITY"
        ),
        "new_reality_units_consumed": 0,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }
