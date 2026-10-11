"""Executable receipt-chain gate for the Brain improvement loop.

It turns UNDERSTAND->PLAN->COMPOSE->ACT->VERIFY->LEARN->GENERALIZE->COMPRESS->REUSE
from a slogan into a promotion precondition.  It does not invent skills itself;
it proves that a proposed learned route is the output of one complete verified
loop and has survived neighboring replay before it may enter live-manifest
promotion.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_VERIFIED_IMPROVEMENT_LOOP_V1"
PHASES = ("understand", "plan", "compose", "act", "verify", "learn", "generalize", "compress", "reuse")


def _sha(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _valid_sha(v: Any) -> bool:
    return isinstance(v, str) and len(v) == 64 and all(c in "0123456789abcdef" for c in v)


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {"schema": SCHEMA, "pass": False, "status": "FAIL_CLOSED", "reason": reason,
            "promotion_candidate": False, "promotion_authority": False, "terminal_authority": False,
            "terminal_credit_delta": 0, "incremental_spend_usd": 0, **extra}


def verify_loop(episode: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(episode, Mapping) or not isinstance(episode.get("episode_id"), str) or not episode["episode_id"]:
        return _fail("EPISODE_INVALID")
    receipts = episode.get("phase_receipts")
    if not isinstance(receipts, Mapping):
        return _fail("PHASE_RECEIPTS_MISSING")
    previous = None
    bound = {}
    for phase in PHASES:
        r = receipts.get(phase)
        if not isinstance(r, Mapping) or not _valid_sha(r.get("sha256")) or r.get("pass") is not True:
            return _fail("PHASE_RECEIPT_INVALID", phase=phase)
        if phase != "understand" and r.get("previous_phase_sha256") != previous:
            return _fail("PHASE_CHAIN_BROKEN", phase=phase)
        if phase == "verify" and r.get("independently_verified") is not True:
            return _fail("VERIFY_NOT_INDEPENDENT")
        previous = r["sha256"]
        bound[phase] = previous

    route = episode.get("learned_route")
    if not isinstance(route, Mapping) or not isinstance(route.get("route_id"), str) or not route["route_id"]:
        return _fail("LEARNED_ROUTE_MISSING")
    if not _valid_sha(route.get("behavior_sha256")) or not _valid_sha(route.get("scope_relation_sha256")):
        return _fail("LEARNED_ROUTE_BINDING_INVALID")
    if route.get("behavior_preservation_verified") is not True:
        return _fail("BEHAVIOR_PRESERVATION_UNPROVED")

    neighbors = episode.get("neighbor_replays")
    if not isinstance(neighbors, list) or len(neighbors) < 2:
        return _fail("NEIGHBOR_REPLAY_INSUFFICIENT")
    for row in neighbors:
        if not isinstance(row, Mapping) or row.get("pass") is not True or row.get("independently_verified") is not True or not _valid_sha(row.get("sha256")):
            return _fail("NEIGHBOR_REPLAY_INVALID")
        if row.get("route_id") != route["route_id"]:
            return _fail("NEIGHBOR_REPLAY_ROUTE_MISMATCH")

    compression = episode.get("compression")
    if not isinstance(compression, Mapping) or compression.get("quality_preserved") is not True or not _valid_sha(compression.get("receipt_sha256")):
        return _fail("COMPRESSION_PROOF_INVALID")
    before = compression.get("resource_before")
    after = compression.get("resource_after")
    if not isinstance(before, (int, float)) or not isinstance(after, (int, float)) or after > before:
        return _fail("COMPRESSION_NOT_NONWORSENING")

    core = {"episode_id": episode["episode_id"], "route_id": route["route_id"], "phase_receipts": bound,
            "behavior_sha256": route["behavior_sha256"], "scope_relation_sha256": route["scope_relation_sha256"],
            "neighbor_receipt_sha256": sorted(x["sha256"] for x in neighbors),
            "compression_receipt_sha256": compression["receipt_sha256"]}
    return {"schema": SCHEMA, "pass": True,
            "status": "PASS__COMPLETE_VERIFIED_IMPROVEMENT_LOOP__ROUTE_ELIGIBLE_FOR_ATOMIC_LIVE_MANIFEST_PROMOTION",
            "reason": None, **core, "improvement_receipt_sha256": _sha(core), "promotion_candidate": True,
            "promotion_authority": False, "terminal_authority": False, "terminal_credit_delta": 0,
            "incremental_spend_usd": 0}
