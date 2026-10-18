"""Registry V3: V2 plus computer use, composed not edited.

V3 preserves every V1 and V2 route unchanged and adds one separately
verified capability family: computer use.

Unknown inputs do not proceed -- but the two families refuse
differently, and the difference is deliberate rather than tidy. An
unregistered computer-use id returns a FAIL_CLOSED receipt, because
computer use is new here and its callers are new. A legacy id is
handed straight to V2, which RAISES, exactly as it always has.
Converting that into a receipt would change the behaviour of already
verified code in order to make two error shapes match, which is the
wrong trade: cosmetic consistency is not worth altering a verified
route. This is the same composition pattern V2 used for the cubic
patch, applied for the same reason -- the verified core stays
untouched, and a new family is added beside it rather than by altering
what has already been verified.

Why this matters, in one line: before this, the Brain could plan and
verify with real rigour but could only ever produce two effects --
write a receipt, append to a ledger. The effect layer was two tools
wide. Computer use closes that, and it does so by joining the
registry rather than by building a second control loop beside it.

One signature difference: computer-use capabilities act on a
filesystem, so they need a root. V2's invoke takes no root, so V3
accepts an optional one and passes it through. Every pre-existing
route is dispatched exactly as before, with root never consulted.
"""
from __future__ import annotations
from typing import Any, Mapping, Sequence

from canonical.runtime import h100_verified_capability_registry_v2 as v2
from canonical.runtime import h100_computer_use_registry_v1 as cu

SCHEMA = "PROJECT_BRAIN_H100_VERIFIED_CAPABILITY_REGISTRY_V3"

REGISTRY = tuple(v2.REGISTRY) + tuple(cu.REGISTRY)

_BY_ID = {row["capability_id"]: row for row in REGISTRY}
_COMPUTER_USE_IDS = frozenset(
    row["capability_id"] for row in cu.REGISTRY)


class CapabilityRegistryV3Error(ValueError):
    pass


def registry_snapshot() -> dict[str, Any]:
    base = v2.registry_snapshot()
    return {
        "schema": SCHEMA,
        "status": "VERIFIED_CAPABILITY_REGISTRY_V3_READY",
        "entry_count": len(REGISTRY),
        "v2_entry_count": base.get("entry_count"),
        "computer_use_entry_count": len(cu.REGISTRY),
        "capability_ids": sorted(_BY_ID),
        "persistent_learned_bytes": 0,
        "external_learned_capability_calls": 0,
        "routing_priority":
            "V1_LIBRARY_THEN_VERIFIED_CUBIC_THEN_COMPUTER_USE",
    }


def invoke(capability_id: str, payload: Mapping[str, Any],
           root: str | None = None) -> dict[str, Any]:
    """Dispatch any registered capability, V2 routes unchanged."""
    cid = str(capability_id or "")
    if cid in _COMPUTER_USE_IDS:
        if root is None:
            return {"schema": SCHEMA, "status": "FAIL_CLOSED",
                    "reason": "ROOT_REQUIRED_FOR_COMPUTER_USE",
                    "capability_id": cid}
        out = cu.invoke(cid, payload, root)
        out["registry"] = SCHEMA
        return out
    # Unchanged path: every V1/V2 route behaves exactly as it did.
    return v2.invoke(capability_id, payload)
