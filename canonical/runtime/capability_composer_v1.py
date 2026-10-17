#!/usr/bin/env python3
"""PROJECT_BRAIN_CAPABILITY_COMPOSER_V1 -- connect the 67 bound capabilities.

The registry already declares the wiring: every capability lists what it
`requires` and what it `provides`.  Nothing ever chained over it.  This module
is that chain.

Two layers, kept deliberately separate:

  * the GRAPH   (`requires` / `provides`) decides what may follow what;
  * the SURFACE (`capability_type_surface_v1`) decides how to call it, and
    type-checks the arguments before anything runs.

Given what the world supplies, `forward_closure` fires everything whose
requirements are met, repeatedly, until nothing new can fire.  Given a goal
token, `plan` returns the capability sequence that produces it.

Fail-closed: an unknown capability, an unsatisfiable goal, or a type error is
returned as data.  Nothing is raised and nothing is papered over.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

try:  # package import
    from . import capability_type_surface_v1 as SURFACE
except ImportError:  # pragma: no cover - direct execution
    import capability_type_surface_v1 as SURFACE  # type: ignore

SCHEMA = "PROJECT_BRAIN_CAPABILITY_COMPOSER_V1"
REGISTRY = Path(__file__).resolve().parents[0] / "BOUND_CAPABILITY_REGISTRY_V1.json"


# --------------------------------------------------------------------------- #
# graph
# --------------------------------------------------------------------------- #
def load_registry(path: str | Path | None = None) -> dict[str, Any]:
    p = Path(path) if path else REGISTRY
    return json.loads(p.read_text(encoding="utf-8"))["capabilities"]


def graph(registry: Mapping[str, Any] | None = None) -> dict[str, dict[str, list[str]]]:
    """cid -> {"requires": [...], "provides": [...]}"""
    reg = registry if registry is not None else load_registry()
    return {
        cid: {
            "requires": list(entry.get("requires") or []),
            "provides": list(entry.get("provides") or []),
        }
        for cid, entry in reg.items()
    }


def producers(token: str, g: Mapping[str, Any] | None = None) -> list[str]:
    """Capabilities that emit `token`."""
    g = g if g is not None else graph()
    return sorted(cid for cid, spec in g.items() if token in spec["provides"])


def consumers(token: str, g: Mapping[str, Any] | None = None) -> list[str]:
    """Capabilities that need `token`."""
    g = g if g is not None else graph()
    return sorted(cid for cid, spec in g.items() if token in spec["requires"])


def external_tokens(g: Mapping[str, Any] | None = None) -> list[str]:
    """Required by something, produced by nothing: only the world can supply these."""
    g = g if g is not None else graph()
    provided = {t for spec in g.values() for t in spec["provides"]}
    required = {t for spec in g.values() for t in spec["requires"]}
    return sorted(required - provided)


def missing(cid: str, available, g: Mapping[str, Any] | None = None) -> list[str]:
    """Requirements of `cid` that `available` does not yet satisfy."""
    g = g if g is not None else graph()
    return [r for r in g[cid]["requires"] if r not in set(available)]


# --------------------------------------------------------------------------- #
# forward chaining
# --------------------------------------------------------------------------- #
def forward_closure(
    seed: Sequence[str], g: Mapping[str, Any] | None = None
) -> tuple[list[str], set[str]]:
    """Fire every capability whose requirements are met, until nothing new fires.

    Returns (firing order, all tokens available at the end).  The order is a
    valid topological order: every capability appears after every capability
    that produces something it requires.
    """
    g = g if g is not None else graph()
    have: set[str] = set(seed)
    order: list[str] = []
    progressed = True
    while progressed:
        progressed = False
        for cid in sorted(g):
            if cid in order:
                continue
            if not missing(cid, have, g):
                order.append(cid)
                have |= set(g[cid]["provides"])
                progressed = True
    return order, have


def unreachable(seed: Sequence[str], g: Mapping[str, Any] | None = None) -> list[str]:
    """Capabilities that can never fire from `seed`."""
    g = g if g is not None else graph()
    order, _ = forward_closure(seed, g)
    return sorted(set(g) - set(order))


# --------------------------------------------------------------------------- #
# backward planning
# --------------------------------------------------------------------------- #
def plan(
    seed: Sequence[str], goal: str, g: Mapping[str, Any] | None = None
) -> list[str] | None:
    """Capabilities, in firing order, that produce `goal` from `seed`.

    None when the goal is unreachable.  Cheapest producers are preferred, so
    the chain stays short; the result is always a valid firing order.
    """
    g = g if g is not None else graph()
    have: set[str] = set(seed)
    order: list[str] = []
    visiting: set[str] = set()

    def solve(token: str) -> bool:
        nonlocal have
        if token in have:
            return True
        if token in visiting:  # cycle -- refuse, do not loop forever
            return False
        visiting.add(token)
        # cheapest first: fewest requirements, then stable name order
        for cid in sorted(producers(token, g), key=lambda c: (len(g[c]["requires"]), c)):
            if cid in order:  # already scheduled; its outputs are in `have`
                return True
            if all(solve(req) for req in g[cid]["requires"]):
                order.append(cid)
                have |= set(g[cid]["provides"])
                visiting.discard(token)
                return True
        visiting.discard(token)
        return False

    return list(order) if solve(goal) else None


def blockers(seed: Sequence[str], goal: str, g: Mapping[str, Any] | None = None) -> list[str]:
    """External tokens missing to reach `goal`.  Empty when the goal is reachable."""
    g = g if g is not None else graph()
    ext = set(external_tokens(g))
    if plan(seed, goal, g) is not None:
        return []
    have = set(seed)
    order, have = forward_closure(seed, g)
    needed: set[str] = set()

    def walk(token: str, seen: set[str]) -> None:
        if token in have or token in seen:
            return
        seen.add(token)
        for cid in producers(token, g):
            for req in g[cid]["requires"]:
                if req in ext:
                    needed.add(req)
                walk(req, seen)

    walk(goal, set())
    return sorted(needed - have)


# --------------------------------------------------------------------------- #
# typed call surface
# --------------------------------------------------------------------------- #
def signature(cid: str, registry: Mapping[str, Any] | None = None) -> dict[str, str]:
    reg = registry if registry is not None else load_registry()
    return SURFACE.signature(reg[cid])


def call_errors(cid: str, args: Mapping[str, Any], registry=None) -> list[str]:
    """Type errors in `args` for `cid`.  Empty means the call is well-typed."""
    return SURFACE.check(signature(cid, registry), args)


# --------------------------------------------------------------------------- #
# report
# --------------------------------------------------------------------------- #
def report(seed: Sequence[str], g: Mapping[str, Any] | None = None) -> dict[str, Any]:
    g = g if g is not None else graph()
    order, have = forward_closure(seed, g)
    return {
        "schema": SCHEMA,
        "seed": sorted(set(seed)),
        "capabilities_total": len(g),
        "capabilities_fired": len(order),
        "capabilities_unreachable": len(unreachable(seed, g)),
        "firing_order": order,
        "tokens_produced": sorted(have),
        "external_prerequisites": external_tokens(g),
    }


def main() -> None:  # pragma: no cover
    g = graph()
    ext = external_tokens(g)
    print(f"{SCHEMA}")
    print(f"  capabilities          : {len(g)}")
    print(f"  external prerequisites: {len(ext)}")
    print(f"  fire with nothing     : {len(forward_closure([], g)[0])}")
    print()
    print("Full closure (world supplies everything):")
    order, have = forward_closure(ext, g)
    print(f"  fired {len(order)}/{len(g)}   tokens produced: {len(have)}")
    orphans = sorted(set(g) - set(order))
    print(f"  never fires even then: {orphans if orphans else 'none'}")
    print()
    for goal in ("docx.document.verified", "pdf.extract.text", "structured.json.available"):
        chain = plan(ext, goal, g)
        print(f"plan -> {goal}")
        print(f"   {chain if chain else 'UNREACHABLE; blockers=' + str(blockers(ext, goal, g))}")


if __name__ == "__main__":  # pragma: no cover
    main()
