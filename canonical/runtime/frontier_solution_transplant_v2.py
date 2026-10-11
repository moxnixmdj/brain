"""Source-locked reuse-first frontier transplanter V2."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

SCHEMA = "PROJECT_BRAIN_FRONTIER_SOLUTION_TRANSPLANT_V2"


def _sha(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _valid_sha(v: Any) -> bool:
    return isinstance(v, str) and len(v) == 64 and all(c in "0123456789abcdef" for c in v)

@dataclass(frozen=True)
class Donor:
    donor_id: str
    invariants: frozenset[str]
    strength: int
    source_id: str
    source_sha256: str


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {"schema": SCHEMA, "pass": False, "status": "FAIL_CLOSED", "reason": reason,
            "new_mechanism_invention_authority": False, "promotion_authority": False,
            "terminal_authority": False, "terminal_credit_delta": 0, "incremental_spend_usd": 0, **extra}


def compile_plan(frontiers: Iterable[Mapping[str, Any]], donors: Iterable[Mapping[str, Any]],
                 source_lock: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    ds = []
    seen = set()
    for row in donors:
        if not isinstance(row, Mapping) or not isinstance(row.get("donor_id"), str) or not row["donor_id"]:
            return _fail("DONOR_INVALID")
        if row["donor_id"] in seen:
            return _fail("DUPLICATE_DONOR_ID", donor_id=row["donor_id"])
        seen.add(row["donor_id"])
        inv = row.get("invariants")
        sid = row.get("source_id")
        ssha = row.get("source_sha256")
        if not isinstance(inv, list) or not inv or not all(isinstance(x, str) and x for x in inv):
            return _fail("DONOR_INVARIANTS_INVALID", donor_id=row["donor_id"])
        if not isinstance(sid, str) or sid not in source_lock or not _valid_sha(ssha):
            return _fail("DONOR_SOURCE_LOCK_MISSING", donor_id=row["donor_id"])
        locked = source_lock[sid]
        if locked.get("sha256") != ssha or locked.get("available_exact_bytes") is not True:
            return _fail("DONOR_SOURCE_NOT_EXACTLY_AVAILABLE", donor_id=row["donor_id"], source_id=sid)
        ds.append(Donor(row["donor_id"], frozenset(inv), int(row.get("strength", 0)), sid, ssha))
    if not ds:
        return _fail("NO_DONORS")

    compiled = []
    for f in frontiers:
        if not isinstance(f, Mapping) or not isinstance(f.get("frontier_id"), str) or not f["frontier_id"]:
            return _fail("FRONTIER_INVALID")
        required = {x for x in (f.get("required_invariants") or []) if isinstance(x, str) and x}
        external = {x for x in (f.get("external_invariants") or []) if isinstance(x, str) and x}
        if not required:
            return _fail("FRONTIER_REQUIRED_INVARIANTS_EMPTY", frontier_id=f["frontier_id"])
        uncovered = set(required)
        chosen = []
        available = list(ds)
        while uncovered:
            ranked = sorted(((len(d.invariants & uncovered), d.strength, d.donor_id, d) for d in available),
                            key=lambda x: (x[0], x[1], x[2]), reverse=True)
            if not ranked or ranked[0][0] == 0:
                break
            d = ranked[0][3]
            chosen.append(d)
            uncovered -= set(d.invariants)
            available = [x for x in available if x.donor_id != d.donor_id]
        internal = uncovered - external
        compiled.append({
            "frontier_id": f["frontier_id"],
            "selected_donors": [{"donor_id": d.donor_id, "source_id": d.source_id, "source_sha256": d.source_sha256} for d in chosen],
            "required_invariants": sorted(required), "covered_invariants": sorted(required-uncovered),
            "external_residual_invariants": sorted(uncovered & external), "internal_uncovered_invariants": sorted(internal),
            "new_mechanism_invention_required": bool(internal), "fine_tune_only": not bool(internal),
            "apply_delta": list(f.get("apply_delta") or []), "acceptance": list(f.get("acceptance") or []),
        })
    unresolved = [x for x in compiled if x["internal_uncovered_invariants"]]
    ext_only = [x for x in compiled if x["external_residual_invariants"] and not x["internal_uncovered_invariants"]]
    core = {"frontiers": compiled,
            "frontiers_requiring_new_internal_mechanism": [x["frontier_id"] for x in unresolved],
            "frontiers_with_external_residual_only": [x["frontier_id"] for x in ext_only]}
    return {"schema": SCHEMA, "pass": not unresolved,
            "status": "PASS__ALL_ENUMERATED_INTERNAL_FRONTIER_INVARIANTS_SOURCE_LOCKED_TO_EXISTING_IMPLEMENTATIONS__FINE_TUNE_ONLY" if not unresolved else "FAIL_CLOSED__GENUINELY_UNCOVERED_INTERNAL_INVARIANT",
            "reason": None if not unresolved else "UNRESOLVED_INTERNAL_INVARIANTS",
            **core, "plan_sha256": _sha(core), "new_mechanism_invention_authority": bool(unresolved),
            "promotion_authority": False, "terminal_authority": False, "terminal_credit_delta": 0,
            "incremental_spend_usd": 0}
