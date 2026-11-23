#!/usr/bin/env python3
"""A guard, not a scorer: no row may contain its own answer.

WHY THIS IS A GUARD AND NOT ANOTHER RULE
----------------------------------------
I built three measurements of "ground a goal onto the artifact's own vocabulary" and published
two of the numbers before catching that both were mostly tautologies:

    rule                                  headline   after removing rows whose goal shares a
                                                     stem / is a module name with the truth
    test-file name -> doc overlap          8.5%       (all of it was the easy half)
    module name   -> that module's units  43.6%       11.8%
    name+doc overlap                       47.0%        9.7%

The leak is structural: `test_align.py` imports from `rich/align.py`, so a goal of "align" is
answered by matching "align" to "Align". Every such corpus will keep producing 40-70% headlines
that mean nothing. So the next thing built has to be the thing that STOPS that, or the same
error comes back with a fourth name.

`stem_free` is the whole guard, and it is cheap: a goal may not share a 6-character prefix with
any candidate name it might select. It is deliberately blunt, because a clever stemmer is a
fitted component and this must not be one.

WHY 6, MEASURED
---------------
    align  / Align          collide at 5  -> rejected, correctly (the goal IS the name)
    table  / Table          collide at 5  -> rejected
    table  / tabulate       collide at 3  -> KEPT, because they do not actually collide:
                                             "tabl" vs "tabu" differ at the fourth character.
                                             My own docstring asserted the opposite until a
                                             test caught it -- a reminder that prose about a
                                             mechanism is a claim like any other
    print  / pretty_print   collide at 5  -> rejected
    make text line up in columns / Align    no shared stem -> KEPT, and this is the row that
                                             actually measures something

The guard is allowed to throw away good rows. It is not allowed to keep a leaking one.

WHAT IT DOES NOT CLAIM
----------------------
It does not make a corpus good; it makes a corpus honest about being weak. A run that keeps 4 of
90 rows has measured almost nothing, and reporting "100% of kept rows" without saying "4 of 90
were kept" is the same dishonesty in a different coat. So `audit` always reports kept, dropped,
and the drop rate, and `verdict` refuses to call a result meaningful below 20 kept rows.

Schema BRAIN_THE_GOAL_MUST_NOT_SHARE_A_STEM_V1. Authority NONE__PRODUCER_RUN_SANDBOX.
"""
from __future__ import annotations

import json
import pathlib
import sys
from typing import Any, Mapping, Sequence

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import learned_ranking_store_v1 as L  # noqa: E402

SCHEMA = "BRAIN_THE_GOAL_MUST_NOT_SHARE_A_STEM_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"
STEM = 6
MIN_MEANINGFUL = 20


def _stem(word: str) -> str:
    return word.lower()[:STEM]


def stem_free(goal: str, candidates: Sequence[str]) -> bool:
    """False when the goal shares a prefix of `STEM` characters with any candidate.

    `candidates` is every name the rule under test could possibly return -- not just the truth.
    Guarding only the truth would let a leak in through a near-miss candidate that the goal also
    happens to name, which is the same defect one step removed.
    """
    gw = L.words(goal)
    if not gw:
        return False
    for name in candidates:
        nw = L.words(str(name).replace("_", " "))
        for g in gw:
            sg = _stem(g)
            if not sg:
                continue
            for n in nw:
                if sg == _stem(n):
                    return False
    return True


def audit(rows: Sequence[Mapping[str, Any]], candidates_of) -> dict[str, Any]:
    """Split rows into the ones that could have measured something and the ones that could not.

    `candidates_of(row)` returns every name the rule could return for that row. Keeping the
    guard at this boundary means it can be applied to a corpus produced by any rule without
    knowing anything about the rule -- which is the only way an audit stays independent.
    """
    kept: list[dict[str, Any]] = []
    dropped: list[dict[str, Any]] = []
    for r in rows:
        goal = str(r.get("goal") or "")
        cands = list(candidates_of(r))
        rec = dict(r)
        rec["shared_stem"] = not stem_free(goal, cands)
        (dropped if rec["shared_stem"] else kept).append(rec)
    total = len(rows)
    return {
        "rows": total,
        "kept": len(kept),
        "dropped": len(dropped),
        "drop_rate": round(len(dropped) / total, 3) if total else 0.0,
        "kept_rows": kept,
        "dropped_rows": dropped,
    }


def verdict(kept: int, top1: int) -> dict[str, Any]:
    """Refuse to dress a thin measurement as a result."""
    if kept < MIN_MEANINGFUL:
        return {"meaningful": False, "reason": f"only {kept} leak-free rows (need {MIN_MEANINGFUL})",
                "rate": round(top1 / kept, 3) if kept else 0.0, "top1": top1, "kept": kept}
    return {"meaningful": True, "rate": round(top1 / kept, 3), "top1": top1, "kept": kept}


if __name__ == "__main__":
    print(__doc__)
    print(json.dumps({"schema": SCHEMA, "authority": AUTHORITY}, indent=1))
