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
# verified emitted artifacts
# --------------------------------------------------------------------------- #
# WHY THIS TABLE EXISTS
#
# 85 of the 96 effect tokens the registry provides are consumed by nothing, and
# 25 capabilities "provide" their own name (`archive.tar_gz.create_from_manifest`
# provides `archive.tar_gz.create_from_manifest`).  A name is not a type: no
# consumer can ever unify with it, so the edge does not exist and the planner
# cannot chain two capabilities that really do fit together.
#
# `archive.tar_gz.create_from_manifest` writes a tar.gz and the registry's own
# verification record says so: it names `archive.verify.tar_gz.gnu` as its
# independent verifier, that verifier requires `archive.tar_gz.available`, and
# the pair carries a mission receipt with the observed member count and archive
# hash.  So the fact is already proven and paid for -- only the token the
# consumer needs was never declared, and the graph could not see a composition
# its own evidence certifies.
#
# WHAT MAY GO IN A ROW
#
# Only what an execution proved.  A row states the token a capability really
# emits, the oracle that re-read the emitted bytes independently of the adapter,
# and the consumer that accepts them.  A row whose token no consumer requires,
# or whose capability is not in the registry, contributes NOTHING (see
# `verified_emits_report`), because a declaration no one can use is decoration
# and an unproven declaration is the exact defect this table exists to remove.
#
# Nothing here calls a model and nothing is asserted from a name: every row is
# re-proven on demand by canonical/tests/test_verified_emitted_artifacts_v1.py,
# which runs the producer and re-reads the bytes with the stdlib.
VERIFIED_EMITS_V1: dict[str, dict[str, Any]] = {
    "archive.tar_gz.create_from_manifest": {
        "tokens": ["archive.tar_gz.available"],
        "consumer": "archive.verify.tar_gz.gnu",
        "evidence": {
            "proven_by": "EXECUTION",
            "oracle": (
                "stdlib tarfile reopens the emitted bytes, requires the gzip "
                "magic, and byte-compares every member against the manifest's "
                "verification_paths; the archive is then handed to "
                "archive.verify.tar_gz.gnu, which must report verified=true"
            ),
            "registry_record": (
                "archive.tar_gz.create_from_manifest.verification."
                "independently_verified_by = archive.verify.tar_gz.gnu"
            ),
            "receipt": (
                "canonical/astra_runtime/evidence/"
                "ASTRA-VERIFY-MANIFEST-ARCHIVE-001__RECEIPT.json"
            ),
            "mission_id": "ASTRA-VERIFY-MANIFEST-ARCHIVE-001",
        },
    },
}


def verified_emits_report(
    reg: Mapping[str, Any] | None = None,
    table: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Which rows are usable, and why the others are not.

    Fail-closed: a row is admitted only when its capability exists, every token
    it claims is required by some other capability, and the row names the
    oracle and the consumer that prove it.  Everything else is reported as
    refused with a reason instead of being quietly trusted.
    """
    reg = reg if reg is not None else load_registry()
    table = table if table is not None else VERIFIED_EMITS_V1
    required = {t for entry in reg.values() for t in (entry.get("requires") or [])}
    admitted: dict[str, list[str]] = {}
    refused: list[dict[str, Any]] = []
    for cid, row in table.items():
        tokens = [str(t) for t in (row.get("tokens") or [])]
        evidence = row.get("evidence") or {}
        if cid not in reg:
            refused.append({"capability_id": cid, "reason": "CAPABILITY_NOT_IN_REGISTRY"})
            continue
        if not tokens:
            refused.append({"capability_id": cid, "reason": "NO_TOKENS_CLAIMED"})
            continue
        unused = [t for t in tokens if t not in required]
        if unused:
            refused.append({"capability_id": cid, "reason": "TOKEN_NO_CONSUMER",
                            "tokens": unused})
            continue
        if not evidence.get("oracle") or not row.get("consumer"):
            refused.append({"capability_id": cid, "reason": "NO_EXECUTION_EVIDENCE"})
            continue
        if str(row.get("consumer")) not in reg:
            refused.append({"capability_id": cid, "reason": "CONSUMER_NOT_IN_REGISTRY",
                            "consumer": str(row.get("consumer"))})
            continue
        admitted[cid] = tokens
    return {"schema": SCHEMA + "_VERIFIED_EMITS", "admitted": admitted,
            "refused": refused, "rows": len(table)}


# --------------------------------------------------------------------------- #
# graph
# --------------------------------------------------------------------------- #
def load_registry(path: str | Path | None = None) -> dict[str, Any]:
    p = Path(path) if path else REGISTRY
    snap = p.with_name("BOUND_CAPABILITY_REGISTRY_SNAPSHOT_V1.json")
    txt = p.read_text(encoding="utf-8") if p.is_file() else ""
    if path is None and not txt.lstrip().startswith("{") and snap.is_file():
        txt = snap.read_text(encoding="utf-8")
    caps = dict(json.loads(txt)["capabilities"])
    if path is None and snap.is_file():
        caps.update(json.loads(snap.read_text(encoding="utf-8")).get("capabilities") or {})
    return caps


def graph(registry: Mapping[str, Any] | None = None,
          verified: Mapping[str, Mapping[str, Any]] | None = None,
          use_verified: bool = True) -> dict[str, dict[str, list[str]]]:
    """cid -> {"requires": [...], "provides": [...]}

    The declared graph is the registry's own `requires`/`provides`.  A token a
    capability really emits but never declared (see VERIFIED_EMITS_V1) is added
    here, so a chain its evidence already certifies becomes visible to `plan`
    and `forward_closure`.  `use_verified=False` reproduces the declared graph
    exactly, which is how the negative controls prove the added edge is what
    changed the answer.
    """
    reg = registry if registry is not None else load_registry()
    additions: dict[str, list[str]] = {}
    if use_verified:
        table = verified if verified is not None else VERIFIED_EMITS_V1
        additions = verified_emits_report(reg, table)["admitted"]
    out: dict[str, dict[str, list[str]]] = {}
    for cid, entry in reg.items():
        provides = list(entry.get("provides") or [])
        for token in additions.get(cid, []):
            if token not in provides:
                provides.append(token)
        out[cid] = {
            "requires": list(entry.get("requires") or []),
            "provides": provides,
        }
    return out


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
