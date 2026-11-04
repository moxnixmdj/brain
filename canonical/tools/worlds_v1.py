#!/usr/bin/env python3
"""One world generator, in one place, because five copies cost four wrong numbers.

Twice in two logs a measurement was taken on a world that was not the world named. Once because a
dict literal evaluated an `rng.choice` for a branch that was not selected, so the RNG advanced and
every `a, b` after it differed. Once because a probe imported another probe's generator, which had
no branch for the world being measured and silently fell through to noise -- `circles` was measured
as 0.476 and reported as a method failure when it had never been measured at all.

The lesson is not "check the fixture". It is that a fixture duplicated five times will be wrong in
one of them and nobody will notice, because the wrong one still returns a number. So there is now
exactly one.

`describe(kind)` states the rule in words so a human can check the world against its name, and
`check()` asserts the label actually depends on the rule (a world whose labels are constant is not
a world).
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

RULES = {
    "and": "BOTH if a > 0.5 and b > 0.5 else NOT",
    "or": "ANY if a > 0.5 or b > 0.5 else NEITHER",
    "xor": "DIFF if exactly one of a, b > 0.5 else SAME",
    "circles": "OUT if (a-0.5)^2 + (b-0.5)^2 > 0.09 else IN",
    "product": "HIGH if a * b > 0.25 else LOW",
    "sum": "HI if a + b > 1 else LO",
    "stripe": "LEFT if b > 0.35 else RIGHT",
    "noise": "a label independent of every signal",
}


def describe(kind: str) -> str:
    if kind not in RULES:
        raise KeyError(f"no such world: {kind!r}; known: {sorted(RULES)}")
    return RULES[kind]


def world(kind: str, n: int, seed: int) -> list[dict]:
    if kind not in RULES:
        raise KeyError(f"no such world: {kind!r}; known: {sorted(RULES)}")
    rng = random.Random(seed)
    rows = []
    for index in range(n):
        a, b = rng.random(), rng.random()
        if kind == "and":
            verdict = "BOTH" if (a > 0.5 and b > 0.5) else "NOT"
        elif kind == "or":
            verdict = "ANY" if (a > 0.5 or b > 0.5) else "NEITHER"
        elif kind == "xor":
            verdict = "DIFF" if (a > 0.5) != (b > 0.5) else "SAME"
        elif kind == "circles":
            verdict = "OUT" if (a - 0.5) ** 2 + (b - 0.5) ** 2 > 0.09 else "IN"
        elif kind == "product":
            verdict = "HIGH" if a * b > 0.25 else "LOW"
        elif kind == "sum":
            verdict = "HI" if a + b > 1 else "LO"
        elif kind == "stripe":
            verdict = "LEFT" if b > 0.35 else "RIGHT"
        else:
            verdict = rng.choice(["X", "Y"])
        rows.append({"group": f"g{index}", "signals": {"a": a, "b": b}, "verdict": verdict})
    return rows


def check() -> dict:
    """Every named world must actually differ from its own name's opposite.

    A world whose labels do not depend on the rule is indistinguishable from noise, and that is
    exactly how `circles` was silently measured as noise for a whole run.
    """
    report = {}
    for kind in RULES:
        rows = world(kind, 60, 1)
        counts = {}
        for row in rows:
            counts[row["verdict"]] = counts.get(row["verdict"], 0) + 1
        report[kind] = {"labels": sorted(counts), "majority_share": round(max(counts.values()) / 60, 3),
                        "rule": RULES[kind]}
        if kind != "noise":
            assert len(counts) == 2, f"{kind} produced {len(counts)} classes"
            assert max(counts.values()) / 60 < 0.95, f"{kind} is almost constant"
    return report


if __name__ == "__main__":
    for name, info in check().items():
        print(f"{name:9s} {info['majority_share']:.3f}  {info['rule']}")
