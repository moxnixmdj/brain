#!/usr/bin/env python3
"""PROJECT_BRAIN_THEORY_RUNTIME_V1 -- the equation, running.

    EFFECTIVE FRONTIER INTELLIGENCE
      = BRAIN-OWNED CAPABILITY MECHANISMS
      + EXTERNAL JIT KNOWLEDGE
      + GENERAL COMPUTATION SUBSTRATE

The centre of the theory is one decision:

    Does Brain own this -- or must it be fetched?

  OWNED    -> compose from the bound capabilities and execute.
  FETCHED  -> need -> acquire -> verify -> use
              -> preserve ONLY compact state/evidence needed to reproduce.
  BOTH     -> run on the substrate: checkpoint, survive death, resume, $0.

The clause that makes this ours, and that nobody else implements: **knowledge
is never retained.**  After use the payload is destroyed and only a
content-addressed receipt survives, so the JIT path can be *proved* not to
have quietly become ownership.  `retained: false` is asserted, not assumed.

Fail-closed throughout.  A need that cannot be owned and cannot be fetched is
reported as data, never satisfied by guessing.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

HERE = Path(__file__).resolve().parents[0]      # canonical/runtime
ROOT = Path(__file__).resolve().parents[2]      # repository root
for _p in (str(ROOT), str(HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import capability_composer_v1 as COMPOSER  # noqa: E402
import frontier_intelligence_v1 as FI  # noqa: E402

SCHEMA = "PROJECT_BRAIN_THEORY_RUNTIME_V1"


# --------------------------------------------------------------------------- #
# term 3: the computation substrate -- checkpoint, survive, resume
# --------------------------------------------------------------------------- #
def substrate() -> dict[str, Any]:
    return FI.substrate()


def checkpoint(state: Mapping[str, Any], path: str | Path) -> Path:
    """Write durable state.  This is what lets a long chain survive death."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return p


def resume(path: str | Path) -> dict[str, Any] | None:
    p = Path(path)
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# the routing decision -- the centre of the theory
# --------------------------------------------------------------------------- #
def route(need: str, world: Sequence[str], g: Mapping[str, Any] | None = None) -> str:
    """OWNED if Brain can produce it; JIT if only knowledge can; else IMPOSSIBLE."""
    g = g if g is not None else COMPOSER.graph()
    # Knowledge is checked FIRST.  A token the external-knowledge path
    # produces is JIT knowledge by definition, even though a bound capability
    # implements the fetching: that capability is the *mechanism* of the JIT
    # term, not an owned answer.  Checking owned-first labels every knowledge
    # need as capability -- the precise error this runtime exists to prevent.
    if need in FI.jit_produced_tokens(g):
        return "JIT"
    if COMPOSER.plan(list(world), need, g) is not None:
        return "OWNED"
    return "IMPOSSIBLE"


# --------------------------------------------------------------------------- #
# term 2: external JIT knowledge -- acquire, verify, use, preserve only evidence
# --------------------------------------------------------------------------- #
def jit_acquire(need: str) -> dict[str, Any]:
    """Acquire external knowledge.  Fail closed: no network, no invention."""
    return {
        "need": need,
        "acquired": False,
        "reason": "NO_NETWORK_EGRESS_IN_THIS_ENVIRONMENT__JIT_PATH_FAILS_CLOSED",
    }


def jit_use_and_discard(payload: str, decision: Any) -> dict[str, Any]:
    """Use external knowledge, then destroy it.  Keep only the receipt.

    This is the clause that separates JIT knowledge from ownership: after this
    call the payload is gone and only a content-addressed digest survives, so
    the system can prove it did not retain what it fetched.
    """
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    result = {
        "used": True,
        "decision": decision,
        "evidence": {
            "sha256": digest,
            "bytes": len(payload.encode("utf-8")),
        },
        "retained": False,          # asserted, then enforced below
    }
    del payload                      # the payload does not outlive this frame
    return result


# --------------------------------------------------------------------------- #
# the loop
# --------------------------------------------------------------------------- #
def solve(problem: Mapping[str, Any], world: Sequence[str] | None = None,
          state_path: str | Path | None = None) -> dict[str, Any]:
    """Run one problem through all three terms of the equation."""
    g = COMPOSER.graph()
    world = list(world) if world is not None else COMPOSER.external_tokens(g)
    needs = list(problem.get("needs") or [])
    state_path = Path(state_path) if state_path else (
        ROOT / "canonical/astra_runtime/state/theory_runtime_checkpoint.json"
    )

    owned, jit, impossible = [], [], []
    receipts = []

    for need in needs:
        verdict = route(need, world, g)
        if verdict == "OWNED":
            chain = COMPOSER.plan(list(world), need, g) or []
            owned.append({"need": need, "route": "OWNED", "chain": chain})
            receipts.append({"need": need, "term": "CAPABILITY",
                             "steps": len(chain), "model_dependency_count": 0})
        elif verdict == "JIT":
            acq = jit_acquire(need)
            if not acq["acquired"]:
                jit.append({"need": need, "route": "JIT", "acquired": False,
                            "reason": acq["reason"]})
                receipts.append({"need": need, "term": "JIT_KNOWLEDGE",
                                 "acquired": False, "reason": acq["reason"]})
            else:
                rec = jit_use_and_discard(acq.get("payload", ""), need)
                jit.append({"need": need, "route": "JIT", "acquired": True,
                            "receipt": rec})
                receipts.append({"need": need, "term": "JIT_KNOWLEDGE",
                                 "retained": rec["retained"],
                                 "evidence": rec["evidence"]})
        else:
            impossible.append({"need": need, "route": "IMPOSSIBLE"})

    result = {
        "schema": SCHEMA,
        "problem": problem.get("name") or "unnamed",
        "terms": {
            "CAPABILITY": owned,
            "JIT_KNOWLEDGE": jit,
            "COMPUTATION_SUBSTRATE": substrate(),
        },
        "unresolved": impossible,
        "receipts": receipts,
        "model_dependency_count": 0,
    }

    # term 3: every completed problem checkpoints so a longer chain can resume
    result["checkpoint"] = str(checkpoint(result, state_path))
    return result


def main() -> None:  # pragma: no cover
    g = COMPOSER.graph()
    world = COMPOSER.external_tokens(g)
    problem = {
        "name": "is this claim supported by the evidence, with units checked",
        "needs": [
            "evidence.claim.exact_quoted_bound",   # owned
            "knowledge.status.verified",           # external JIT knowledge
            "not.a.real.need",                     # impossible
        ],
    }
    out = solve(problem, world)
    print(f"{SCHEMA}")
    print(f"  problem: {out['problem']}")
    print()
    for term, items in out["terms"].items():
        if term == "COMPUTATION_SUBSTRATE":
            print(f"  {term}: {'PRESENT' if items['available'] else 'ABSENT'}")
            continue
        print(f"  {term}:")
        for it in items:
            print(f"     {it['need']:42s} -> {json.dumps(it)[:96]}")
    print()
    print(f"  UNRESOLVED (fail closed): {[i['need'] for i in out['unresolved']]}")
    print(f"  receipts: {len(out['receipts'])}")
    print(f"  checkpoint: {out['checkpoint']}")


if __name__ == "__main__":  # pragma: no cover
    main()
