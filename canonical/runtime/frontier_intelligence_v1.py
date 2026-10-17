#!/usr/bin/env python3
"""PROJECT_BRAIN_FRONTIER_INTELLIGENCE_V1 -- the whole equation, running.

    EFFECTIVE FRONTIER INTELLIGENCE
      = BRAIN-OWNED CAPABILITY MECHANISMS
      + EXTERNAL JIT KNOWLEDGE
      + GENERAL COMPUTATION SUBSTRATE

Connecting the 67 capabilities to each other is one term of that sum.  This
module is all three, and -- more importantly -- the seam between them.

  * CAPABILITY -- what Brain owns and can still run with every outside model
    deleted.  Planned mechanically by `capability_composer_v1`.

  * JIT KNOWLEDGE -- knowledge stays external.  The law in canonical/README.md:
    ``need knowledge -> acquire strongest relevant current knowledge -> verify
    -> use -> preserve only compact state/evidence needed for reproducibility``.
    Brain does not hoard a frontier model's knowledge warehouse and call it
    ownership; it fetches, verifies, uses, and keeps the receipt.

  * COMPUTATION SUBSTRATE -- the same-identity superworker: provider-neutral,
    checkpoint/relaunch, $0.  It is not one of the 67; it is what they run on.

The seam is the whole point.  When an owned capability needs a token it cannot
produce, this module first asks whether the JIT knowledge path can supply it,
and only then declares the goal unreachable.  What survives that is a genuine
gap, and it is reported as data -- never hidden, never raised.

`solve` therefore answers three questions at once: what we owned, what we had
to fetch, and what is still missing.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

HERE = Path(__file__).resolve().parents[0]   # canonical/runtime
ROOT = Path(__file__).resolve().parents[2]   # repository root
# the substrate imports `canonical.runtime.*`, so the repo root must resolve
for _p in (str(ROOT), str(HERE)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import capability_composer_v1 as COMPOSER  # noqa: E402

SCHEMA = "PROJECT_BRAIN_FRONTIER_INTELLIGENCE_V1"

# Knowledge stays external/JIT: these capabilities acquire, verify, and
# compact external knowledge.  They are the "EXTERNAL JIT KNOWLEDGE" term,
# not Brain-owned capability mechanisms.
JIT_PREFIXES = ("knowledge.",)

# The substrate is not a capability; it is the body the capabilities run on.
SUBSTRATE_MODULE = "same_identity_supervisor"


# --------------------------------------------------------------------------- #
# the three terms
# --------------------------------------------------------------------------- #
def is_jit(cid: str) -> bool:
    return cid.startswith(JIT_PREFIXES)


def terms(g: Mapping[str, Any] | None = None) -> dict[str, list[str]]:
    """Split the bound capabilities into the two in-registry terms."""
    g = g if g is not None else COMPOSER.graph()
    return {
        "CAPABILITY": sorted(c for c in g if not is_jit(c)),
        "JIT_KNOWLEDGE": sorted(c for c in g if is_jit(c)),
    }


def jit_produced_tokens(g: Mapping[str, Any] | None = None) -> set[str]:
    """Tokens the external-knowledge path can supply."""
    g = g if g is not None else COMPOSER.graph()
    return {t for c in g if is_jit(c) for t in g[c]["provides"]}


def substrate() -> dict[str, Any]:
    """Is the body present and loadable?  Reported, never assumed."""
    try:
        module = importlib.import_module(SUBSTRATE_MODULE)
    except Exception as exc:  # fail closed, name the reason
        return {
            "module": SUBSTRATE_MODULE,
            "available": False,
            "reason": f"{type(exc).__name__}: {exc}",
        }
    return {
        "module": SUBSTRATE_MODULE,
        "available": True,
        "path": getattr(module, "__file__", None),
        "has_supervise": any(
            hasattr(module, n) for n in ("main", "supervise", "run", "Supervisor")
        ),
    }


# --------------------------------------------------------------------------- #
# the seam
# --------------------------------------------------------------------------- #
def jit_path_for(
    token: str, world: Sequence[str], g: Mapping[str, Any] | None = None
) -> list[str] | None:
    """Can the external-knowledge path produce `token`?  Returns the chain."""
    g = g if g is not None else COMPOSER.graph()
    if token not in jit_produced_tokens(g):
        return None
    return COMPOSER.plan(list(world), token, g)


def _result(
    goal: str, chain: Sequence[str] | None, jit_extra: Sequence[str], gaps: Sequence[str]
) -> dict[str, Any]:
    """Split a planned chain into the two in-registry terms of the equation.

    A single planned chain can cross the seam: owned mechanisms and the JIT
    knowledge path can both appear in it.  Ownership is what the law scores,
    so the two are never merged in the report.
    """
    chain = list(chain or [])
    seen: set[str] = set()
    jit: list[str] = []
    for cid in list(jit_extra) + [c for c in chain if is_jit(c)]:
        if cid not in seen:
            seen.add(cid)
            jit.append(cid)
    return {
        "schema": SCHEMA,
        "goal": goal,
        "owned_capability": [c for c in chain if not is_jit(c)],
        "jit_knowledge": jit,
        "unresolved_gaps": list(gaps),
        "substrate": substrate(),
    }


def solve(
    goal: str, world: Sequence[str], g: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    """Run the whole equation toward `goal`.

    Owned capability first; the JIT knowledge path only where ownership runs
    out; whatever still cannot be produced is reported as a real gap.
    """
    g = g if g is not None else COMPOSER.graph()
    have: set[str] = set(world)

    # 1. try it with what we own
    chain = COMPOSER.plan(have, goal, g)
    if chain is not None:
        return _result(goal, chain, [], [])

    # 2. what is missing?
    gaps = COMPOSER.blockers(list(world), goal, g)

    # 3. can external JIT knowledge supply any of it?
    jit: list[str] = []
    resolved: set[str] = set()
    for gap in gaps:
        fetched = jit_path_for(gap, sorted(have), g)
        if fetched:
            for cid in fetched:
                if cid not in jit:
                    jit.append(cid)
                have |= set(g[cid]["provides"])
            resolved.add(gap)

    # 4. re-plan now that knowledge has landed
    chain = COMPOSER.plan(have, goal, g) if resolved else None
    return _result(goal, chain, jit, sorted(set(gaps) - resolved))


# --------------------------------------------------------------------------- #
# what is still missing -- the point of building it
# --------------------------------------------------------------------------- #
def gap_report(goals: Sequence[str], world: Sequence[str]) -> dict[str, Any]:
    """Across every goal the graph can name: owned, borrowed, or impossible.

    Three buckets, because they cost different things.  `owned` still runs
    with every outside model deleted.  `borrowed` needs the external JIT
    knowledge path, so it stops working the moment the network does.
    `blocked` is what we genuinely still have to build.
    """
    g = COMPOSER.graph()
    ext = set(COMPOSER.external_tokens(g))
    supplied = set(world) | ext
    owned: list[str] = []
    borrowed: list[str] = []
    blocked: dict[str, list[str]] = {}
    for goal in sorted({p for spec in g.values() for p in spec["provides"]}):
        out = solve(goal, sorted(supplied), g)
        if not (out["owned_capability"] or out["jit_knowledge"]):
            blocked[goal] = out["unresolved_gaps"]
        elif out["jit_knowledge"]:
            borrowed.append(goal)
        else:
            owned.append(goal)
    return {
        "schema": SCHEMA,
        "world_supplies": sorted(supplied),
        "owned_goals": owned,
        "borrowed_goals": borrowed,
        "blocked": blocked,
        "counts": {
            "owned": len(owned),
            "borrowed": len(borrowed),
            "blocked": len(blocked),
        },
        "substrate": substrate(),
    }


def main() -> None:  # pragma: no cover
    g = COMPOSER.graph()
    t = terms(g)
    print(f"{SCHEMA}")
    print(f"  CAPABILITY (owned)   : {len(t['CAPABILITY'])}")
    print(f"  JIT_KNOWLEDGE        : {len(t['JIT_KNOWLEDGE'])} -> {t['JIT_KNOWLEDGE']}")
    sub = substrate()
    print(f"  COMPUTATION SUBSTRATE: {'PRESENT' if sub['available'] else 'ABSENT'} ({sub['module']})")
    print()
    world = COMPOSER.external_tokens(g)
    for goal in (
        "evidence.claim.exact_quoted_bound",
        "knowledge.status.verified",
        "decision.synthesis.verified",
        "pdf.extract.text",
    ):
        out = solve(goal, world, g)
        print(f"goal: {goal}")
        print(f"   owned   : {out['owned_capability']}")
        print(f"   jit     : {out['jit_knowledge']}")
        print(f"   missing : {out['unresolved_gaps'] or 'nothing'}")
        print()


if __name__ == "__main__":  # pragma: no cover
    main()
