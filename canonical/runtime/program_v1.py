#!/usr/bin/env python3
"""Let the shape of a thought grow, instead of listing the shapes.

Every composition this system has ever built is a PAIR of senses, one operator deep. Log 16's
generator was a fixed list: every unary application, every pair, and a signal with itself. Nothing
recurses, so `(a * b) * c` -- a three-way interaction -- cannot be constructed at all, no matter how
much data arrives or how many gates approve. The creature could think about two things together and
never about three.

That is not a limit of arithmetic. It is a limit of the shape list, which I wrote.

This module builds expressions bottom-up instead: at each size it combines everything from the sizes
below, evaluates it, and keeps one representative of every distinct VALUE the world produces. Two
programs that agree on every example are one idea, so the search dedupes on the value vector rather
than on the syntax -- which is what stops an enumerative search from drowning in algebraically
identical spellings of the same column.

What is honestly still mine: the operators. `add`, `sub`, `mul`, `div`, `min`, `max`, `abs` are a
person's idea of what can be computed, and this log does not claim to have invented them.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import vocabulary_v1 as vocab  # noqa: E402

SCHEMA = "PROJECT_BRAIN_PROGRAM_V1"
# Size counts every node: `base` is 1, `abs(x)` is 2, `mul(a, b)` is 3, `mul(mul(a, b), c)` is 5.
# Measured 2026-11-04: with MAX_SIZE = 3 the search could not nest a single operation -- 35 distinct
# value vectors on a three-signal world, which is the same shape list as log 16 wearing a new name.
MAX_SIZE = 5
SEARCH_BUDGET = 3000         # distinct value vectors kept
GATE_CANDIDATES = 30         # how many reach the expensive out-of-group gate

UNARY_OPS = ("abs",)
BINARY_OPS = ("add", "sub", "mul", "div", "mindiff", "maxdiff")


def blank() -> dict:
    return {"schema": SCHEMA, "entries": [], "rejected": [], "proposed": 0, "retired": [],
            "searched": 0, "distinct_values": 0}


def _size(expr: tuple) -> int:
    if expr[0] == "base":
        return 1
    if expr[0] == "un":
        return 1 + _size(expr[2])
    return 1 + _size(expr[2]) + _size(expr[3])


def _values(examples: list[dict], expr: tuple) -> list[float | None]:
    return [vocab.evaluate(expr, ex["signals"]) for ex in examples]


def _signature(values: list[float | None]) -> tuple:
    """What the world sees, rounded. Equal signatures mean equal columns, however they are spelled."""
    return tuple(None if value is None else round(float(value), 9) for value in values)


def synthesize(examples: list[dict], max_size: int = MAX_SIZE,
               budget: int = SEARCH_BUDGET) -> dict:
    """Every distinct value vector this world admits, up to `max_size`, within a budget.

    Bottom-up, deduped by what the data sees. The dedupe matters: `add(a, b)` and `add(b, a)` and
    `sub(b, -a)` are one idea with three spellings, and an enumerator that cannot tell them apart
    spends its whole budget on arithmetic's synonyms.
    """
    bases = sorted({key for ex in examples for key in ex["signals"]})
    levels: dict[int, list[tuple]] = {1: [("base", name) for name in bases]}
    seen: dict[tuple, tuple] = {}
    for name in bases:
        seen[_signature(_values(examples, ("base", name)))] = ("base", name)

    for size in range(2, max_size + 1):
        found: list[tuple] = []
        for left_size in range(1, size - 1):
            right_size = size - 1 - left_size
            if right_size < 1:
                continue
            for left in levels.get(left_size, []):
                for right in levels.get(right_size, [])[:400]:
                    for op in BINARY_OPS:
                        expr = ("bin", op, left, right)
                        signature = _signature(_values(examples, expr))
                        if None in signature[:1] or signature in seen:
                            continue
                        seen[signature] = expr
                        found.append(expr)
                        if len(seen) >= budget:
                            break
                    if len(seen) >= budget:
                        break
                if len(seen) >= budget:
                    break
            if len(seen) >= budget:
                break
        for left in levels.get(size - 1, [])[:400]:
            for op in UNARY_OPS:
                expr = ("un", op, left)
                signature = _signature(_values(examples, expr))
                if signature in seen:
                    continue
                seen[signature] = expr
                found.append(expr)
        levels[size] = found
        if len(seen) >= budget:
            break

    return {"size": max_size, "proposed": len(seen), "levels": {size: len(e) for size, e in levels.items()}}


def separability(examples: list[dict], expr: tuple) -> float:
    """How well one computed column, cut once, tells the verdicts apart -- chance is 0.5."""
    values = _values(examples, expr)
    if any(value is None for value in values):
        return 0.0
    found = vocab._best_threshold(values, [ex["verdict"] for ex in examples])
    if not found:
        return 0.0
    low = [ex["verdict"] for ex, value in zip(examples, values) if value <= found[1]]
    high = [ex["verdict"] for ex, value in zip(examples, values) if value > found[1]]
    pick = lambda labels: max(set(labels), key=labels.count) if labels else None    # noqa: E731
    right = sum(1 for label in low if label == pick(low))
    right += sum(1 for label in high if label == pick(high))
    return right / len(examples)


def ranked(examples: list[dict], limit: int = GATE_CANDIDATES, max_size: int = MAX_SIZE,
           budget: int = SEARCH_BUDGET) -> dict:
    """The expressions worth paying for, ordered by how much they could possibly explain."""
    bases = sorted({key for ex in examples for key in ex["signals"]})
    level: dict[int, list[tuple]] = {1: [("base", name) for name in bases]}
    seen: set[tuple] = {_signature(_values(examples, ("base", name))) for name in bases}
    pool: list[tuple] = [("base", name) for name in bases]

    for size in range(2, max_size + 1):
        found: list[tuple] = []
        for left_size in range(1, size - 1):
            right_size = size - 1 - left_size
            for left in level.get(left_size, []):
                for right in level.get(right_size, [])[:200]:
                    for op in BINARY_OPS:
                        expr = ("bin", op, left, right)
                        signature = _signature(_values(examples, expr))
                        if signature in seen or signature[0] is None:
                            continue
                        seen.add(signature)
                        found.append(expr)
                        if len(seen) >= budget:
                            break
                    if len(seen) >= budget:
                        break
                if len(seen) >= budget:
                    break
            if len(seen) >= budget:
                break
        for left in level.get(size - 1, [])[:200]:
            for op in UNARY_OPS:
                expr = ("un", op, left)
                signature = _signature(_values(examples, expr))
                if signature in seen:
                    continue
                seen.add(signature)
                found.append(expr)
        level[size] = found
        pool.extend(found)
        if len(seen) >= budget:
            break

    scored = []
    for expr in pool:
        try:
            scored.append((vocab._cheap_gain(examples, expr), _size(expr), expr))
        except Exception:                                                 # noqa: BLE001
            continue
    scored.sort(key=lambda row: -row[0])
    return {"searched": len(seen), "scored": len(scored),
            "candidates": [expr for gain, _, expr in scored[:limit] if gain > 0],
            "sizes": {expr_size: sum(1 for _, size, _ in scored if size == expr_size)
                      for expr_size in range(1, max_size + 1)}}


def pays_for_itself(examples: list[dict], entries: list[dict]) -> dict:
    """Does a model that can see these computed senses predict better than one that cannot?

    Log 16's doctrine, applied to this layer: a feature that passes its own gate can still make the
    learner worse. Measured 2026-11-04: on a structureless world this module admitted
    `mul(a, maxdiff(a, b))`, and on every world with a real rule the augmented model scored exactly
    the same as the unaugmented one. A program layer that changes nothing is not a capability; it is
    a column of noise with a story attached.
    """
    from canonical.runtime import belief_v1 as belief

    if not entries:
        return {"with": 0.0, "without": 0.0, "pays": False}

    def held(shown: list[dict]) -> float:
        # The folds must be built on the rows this variant actually sees. Measured 2026-11-04, for
        # the third time in this session: folds carry their own data, so reusing folds built before
        # augmentation made "with" and "without" both fit on the unaugmented rows and return
        # identical scores to four decimal places -- a comparison of a thing with itself.
        rows = vocab.augment(examples, {"entries": shown})
        folds = vocab.time_folds(rows, blocks=4)
        if not folds:
            return 0.0
        scores = []
        for train, test in folds:
            model = belief.blank()
            belief.fit(model, train, test)
            scores.append(belief.accuracy(model, test)[0])
        return sum(scores) / len(scores) if scores else 0.0

    with_them = held(entries)
    without = held([])
    return {"with": round(with_them, 4), "without": round(without, 4),
            "pays": with_them > without + vocab.MIN_GAIN}


def discover(examples: list[dict], folds, alt_folds=None, limit: int = 4,
             max_size: int = MAX_SIZE) -> dict:
    """Admit a computed sense only if it survives the same gates every other claim survives.

    The gates are `vocabulary_v1`'s, unchanged: the cut is learned inside each fold, the feature must
    help every fold, and a permutation null guards against coincidence. The only thing that changed
    is where the candidates come from -- a search instead of a list.
    """
    found = ranked(examples, max_size=max_size)
    vocabulary = blank()
    vocabulary["searched"] = found["searched"]
    vocabulary["distinct_values"] = found["searched"]
    # Both keys exist on every return path. Measured 2026-11-04: `set_aside` used to be created only
    # when a program FAILED to pay, so the schema of this dict depended on its own verdict -- and a
    # caller reading `set_aside` crashed on exactly the worlds that worked.
    vocabulary["set_aside"] = []
    vocabulary["pays_for_itself"] = None
    if not examples or not folds:
        return vocabulary
    floor = vocab._base_rate(folds)
    best_base = max((vocab._cv(examples, ("base", name), None, folds)
                     for name in sorted({k for ex in examples for k in ex["signals"]})), default=0.0)
    bar = max(floor, best_base) + vocab.MIN_GAIN

    for expr in found["candidates"]:
        vocabulary["proposed"] += 1
        found_cut = vocab._best_threshold(_values(examples, expr),
                                          [ex["verdict"] for ex in examples])
        if not found_cut:
            continue
        score = vocab._cv(examples, expr, None, folds)
        per_fold = vocab._cv_by_fold(examples, expr, folds)
        if score < bar:
            vocabulary["rejected"].append({"expr": vocab.render(expr), "why": "below_the_bar",
                                           "cv": round(score, 4), "bar": round(bar, 4)})
            continue
        if per_fold and any(value < bar for value in per_fold):
            vocabulary["rejected"].append({"expr": vocab.render(expr),
                                           "why": "helped_on_average_only",
                                           "cv": round(score, 4)})
            continue
        if alt_folds is not None:
            second = vocab._cv(examples, expr, None, alt_folds)
            if second < bar:
                vocabulary["rejected"].append({"expr": vocab.render(expr), "why": "unstable",
                                               "cv": round(score, 4)})
                continue
        p = vocab._permutation_p(examples, expr, None, folds, score)
        if p >= vocab.ALPHA:
            vocabulary["rejected"].append({"expr": vocab.render(expr), "why": "not_beyond_chance",
                                           "cv": round(score, 4), "p": round(p, 4)})
            continue
        entry = {"name": f"v{len(vocabulary['entries']) + 1}", "expr": vocab._jsonable(expr),
                 "renders": vocab.render(expr), "threshold": found_cut[1],
                 "cv": round(score, 4), "base_rate": round(floor, 4),
                 "best_base_feature": round(best_base, 4), "p": round(p, 4),
                 "size": _size(expr)}
        vocabulary["entries"].append(entry)
        if len(vocabulary["entries"]) >= limit:
            break
    vocabulary = vocab.dedupe(vocabulary, examples)
    verdict = pays_for_itself(examples, vocabulary["entries"])
    vocabulary["pays_for_itself"] = verdict
    if not verdict["pays"]:
        vocabulary["set_aside"] = list(vocabulary["entries"])
        vocabulary["entries"] = []
    return vocabulary


def describe(vocabulary: dict) -> dict:
    entries = vocabulary.get("entries") or []
    return {
        "schema": SCHEMA,
        "admitted": [e["renders"] for e in entries],
        "sizes": [e.get("size") for e in entries],
        "deepest": max((e.get("size") or 0 for e in entries), default=0),
        "searched": vocabulary.get("searched", 0),
        "proposed": vocabulary.get("proposed", 0),
        "set_aside": vocabulary.get("set_aside") or [],
        "pays_for_itself": vocabulary.get("pays_for_itself"),
    }
