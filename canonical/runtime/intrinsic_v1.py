#!/usr/bin/env python3
"""A reason to keep a thought that is not yet right.

Log 19 ended on a wall, and the wall is not the hypothesis language. Every search this system has
ever run -- logs 16, 18 and 19 -- ranks a candidate by how much it agrees with the answer *right
now*. Parity is unreachable under that rule for a mechanical reason: the exact three-way rule
separates `xor3` at 1.000, every proper part of it sits at chance (0.575, 0.517), and a search that
only keeps what already helps therefore deletes the only path to it. More depth and more budget
cannot repair a ranking that is wrong about what a step is for.

Two things are changed here, and they are different in kind.

1. **Constants are derived, not typed.** The algebra had no constants at all, so no rule centred on
   a threshold was even spellable. Rather than hand the creature 0.5, it now computes each signal's
   median from the data it was given and treats that as a column. For a uniform signal the median
   lands near the threshold the world actually uses, and nothing in this file contains the number.

2. **The ranking is an intrinsic one.** `policy="novelty"` keeps the candidates that are least like
   anything the search already holds -- valued for being new, not for being right. That is the only
   kind of signal that can survive a plateau, because it does not go to zero when the answer does
   not improve. `policy="adaptive"` starts objective-guided and switches to novelty when its own
   measured progress stalls, so the creature chooses how to think from evidence about itself rather
   than from a choice I made.

Honest about what is still mine: the idea of novelty, the per-level survivor count, the median as
the constant, and the size budget. What is no longer mine is the requirement that a thought pay
immediately -- and that requirement is what made parity impossible.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import program_v1 as program     # noqa: E402
from canonical.runtime import vocabulary_v1 as vocab    # noqa: E402

SCHEMA = "PROJECT_BRAIN_INTRINSIC_V1"
MAX_SIZE = 11                 # the parity rule's size; unreachable at log 19's MAX_SIZE of 5
PER_LEVEL = 20                # survivors kept at each size -- the search's working memory
BUDGET = 2000                 # distinct columns kept in the archive
STALL_LEVELS = 2              # adaptive: how many sizes without objective progress count as a stall
ARCHETYPES = 40               # how many archive members novelty is measured against


# ------------------------------------------------------------------ constants, derived from data
def median(values: list[float]) -> float:
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2.0


def derived_constants(examples: list[dict]) -> dict[str, float]:
    """Each signal's own median, computed from the data. Not a number a person supplied.

    Measured 2026-11-05: the parity rule needs a centre, and `vocabulary_v1` has no constants, so
    the creature could not spell `a - k` at all. The median is the least committal centre available
    -- it is a property of the world in front of it, so two different worlds get two different
    constants, and nothing here knows what a threshold is.
    """
    names = sorted({key for ex in examples for key in ex["signals"]})
    return {f"med_{name}": median([float(ex["signals"][name]) for ex in examples])
            for name in names}


def with_derived_constants(examples: list[dict]) -> tuple[list[dict], dict[str, float]]:
    constants = derived_constants(examples)
    rows = []
    for ex in examples:
        signals = dict(ex["signals"])
        signals.update(constants)
        rows.append({**ex, "signals": signals})
    return rows, constants


# ------------------------------------------------------------------------- the two rankings
def _signature(values: list[float | None]) -> tuple:
    return tuple(None if value is None else round(float(value), 9) for value in values)


def _summary(values: list[float | None]) -> tuple[float, ...]:
    """A cheap shape of a column: eight quantiles. Used only to measure how unlike it is."""
    usable = sorted(float(value) for value in values if value is not None)
    if not usable:
        return (0.0,) * 8
    pick = lambda fraction: usable[min(len(usable) - 1, int(fraction * len(usable)))]  # noqa: E731
    return tuple(pick(step / 8.0) for step in range(8))


def _distance(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    return sum((a - b) ** 2 for a, b in zip(left, right)) ** 0.5


def _gain(values: list[float | None], verdicts: list[str]) -> float:
    parent = vocab._entropy({v: verdicts.count(v) for v in set(verdicts)})
    found = vocab._best_threshold(values, verdicts)
    return (parent - found[0]) if found else 0.0


def _stable_key(expr: tuple) -> float:
    """A deterministic stand-in for "picked at random" -- the null arm, reproducible."""
    text = repr(expr)
    return (sum((index + 1) * ord(char) for index, char in enumerate(text)) % 100003) / 100003.0


# --------------------------------------------------------------------------- the search itself
def search(examples: list[dict], policy: str = "objective", per_level: int = PER_LEVEL,
           max_size: int = MAX_SIZE, budget: int = BUDGET,
           stall_levels: int = STALL_LEVELS) -> dict:
    """Grow expressions to `max_size`, keeping what the policy says is worth keeping.

    The archive is every distinct column ever produced -- that is what "spellable" means here. The
    survivors per level are the working memory the next level is built from, and they are what the
    policy actually decides. Both are reported, because a wide archive with a narrow memory is a
    search that looked and did not think.
    """
    verdicts = [ex["verdict"] for ex in examples]
    bases = sorted({key for ex in examples for key in ex["signals"]})
    cache: dict[tuple, list[float | None]] = {}

    def values_of(expr: tuple) -> list[float | None]:
        if expr not in cache:
            cache[expr] = [vocab.evaluate(expr, ex["signals"]) for ex in examples]
        return cache[expr]

    level: dict[int, list[tuple]] = {1: [("base", name) for name in bases]}
    memory: dict[int, list[tuple[float, str]]] = {}
    archive: dict[tuple, tuple] = {}
    for name in bases:
        archive[_signature(values_of(("base", name)))] = ("base", name)

    archetypes: list[tuple[float, ...]] = [_summary(values_of(("base", name))) for name in bases]
    best_by_size: dict[int, float] = {}
    chosen_by_size: dict[int, str] = {}
    stalled = 0
    previous_best = -1.0

    for size in range(2, max_size + 1):
        generated: list[tuple] = []
        for left_size in range(1, size - 1):
            right_size = size - 1 - left_size
            if right_size < 1 or left_size > right_size:
                continue          # mirrored pairs are deduped by signature, not re-enumerated
            for left in level.get(left_size, []):
                for right in level.get(right_size, []):
                    for op in program.BINARY_OPS:
                        expr = ("bin", op, left, right)
                        signature = _signature(values_of(expr))
                        if signature in archive or signature[0] is None:
                            continue
                        archive[signature] = expr
                        generated.append(expr)
                        if len(archive) >= budget:
                            break
                    if len(archive) >= budget:
                        break
                if len(archive) >= budget:
                    break
            if len(archive) >= budget:
                break
        for left in level.get(size - 1, []):
            for op in program.UNARY_OPS:
                expr = ("un", op, left)
                signature = _signature(values_of(expr))
                if signature in archive:
                    continue
                archive[signature] = expr
                generated.append(expr)

        gains = [(expr, _gain(values_of(expr), verdicts)) for expr in generated]
        best_now = max((gain for _, gain in gains), default=0.0)
        best_by_size[size] = round(best_now, 4)

        # The policy decides the working memory for the next size. Nothing else changes.
        effective = policy
        if policy == "adaptive":
            stalled = stalled + 1 if best_now <= previous_best + 1e-9 else 0
            effective = "novelty" if stalled >= stall_levels else "objective"
        chosen_by_size[size] = effective
        previous_best = max(previous_best, best_now)

        if effective == "mixed":
            # Half by agreement, half by novelty. Measured 2026-11-05 as an attempt to hold a chain
            # whose every prefix is at chance: a purely objective pool deletes the prefix, and a
            # purely novel pool keeps it by accident. Whether this actually holds it is measured,
            # not asserted.
            by_gain = sorted(gains, key=lambda row: -row[1])
            novelty = sorted(((min((_distance(_summary(values_of(expr)), archetype)
                                   for archetype in archetypes[:ARCHETYPES]), default=0.0), expr)
                              for expr in generated), key=lambda row: -row[0])
            half = per_level // 2
            level[size] = ([expr for expr, _ in by_gain[:half]]
                           + [expr for _, expr in novelty[:per_level - half]])
            for expr in level[size]:
                archetypes.append(_summary(values_of(expr)))
            memory[size] = [(round(_gain(values_of(expr), verdicts), 6), repr(expr))
                            for expr in level[size]]
            if len(archive) >= budget:
                break
            continue
        if effective == "novelty":
            scored = [(min((_distance(_summary(values_of(expr)), archetype)
                           for archetype in archetypes[:ARCHETYPES]), default=0.0), expr)
                      for expr in generated]
        elif effective == "random":
            scored = [(_stable_key(expr), expr) for expr in generated]
        else:
            scored = [(gain, expr) for expr, gain in gains]
        scored.sort(key=lambda row: -row[0])
        level[size] = [expr for _, expr in scored[:per_level]]
        for expr in level[size]:
            archetypes.append(_summary(values_of(expr)))
        memory[size] = [(round(_gain(values_of(expr), verdicts), 6), repr(expr))
                        for expr in level[size]]
        if len(archive) >= budget:
            break

    spelled = {}
    for signature, expr in archive.items():
        if None in signature:
            continue
        spelled[signature] = expr
    return {
        "schema": SCHEMA,
        "policy": policy,
        "archive": len(archive),
        "spellable": len(spelled),
        "best_by_size": best_by_size,
        "policy_by_size": chosen_by_size,
        "constants_used": sorted(name for name in bases if name.startswith("med_")),
        "memory": {size: kept for size, kept in memory.items()},
        "expressions": archive,
    }


def best_column(found: dict, examples: list[dict]) -> tuple[tuple | None, float]:
    """The column in the archive that separates the verdicts best, and how well."""
    best, best_sep = None, 0.0
    for expr in found["expressions"].values():
        separation = program.separability(examples, expr)
        if separation > best_sep:
            best_sep = separation
            best = expr
    return best, round(best_sep, 4)
