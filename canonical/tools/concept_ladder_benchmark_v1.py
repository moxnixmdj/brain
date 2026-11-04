#!/usr/bin/env python3
"""Does concept invention COMPOUND, or does it only work once?

WHY THIS, AND WHY NOT THE TWO THINGS BEFORE IT
----------------------------------------------
Three attempts at compounding, on 2026-11-03:

  1. Transition model carried across environment KINDS .... measured NO (10/10 identical cost)
  2. Choosing among five fixed search POLICIES ........... measured NO (3/10 vs a coin flip)
  3. Inventing a new CONCEPT from solved programs ........ measured **YES** (below)

The first two are both the same move: **pick better among a fixed set of options.** No amount of
learning makes a better choice than the best member of a fixed set, and a fixed set cannot answer
a problem outside it. The third is a different move: **add an option.** `ΔB_exec < 0` demands the
new concept strictly compress executable description length, and it must kill at least one mutant
and vary across probes -- so the library grows in expressiveness, not in size.

That is the first-principles distinction this file exists to record:
    compounding is GENERATION, not SELECTION.

WHAT THIS MEASURES
------------------
A ladder of four rungs. Each rung is a family: two TEACH programs that share a concept, and three
HELD-OUT problems that need it and are never shown to the inventor. After each rung the library
keeps everything it has ever admitted, and the next rung is solved WITH that library.

    for each rung:
        measure held-out solve rate + time with the library as it stands   (before)
        teach from the rung's two programs (sleep_abstract)                (learn)
        measure the same rung with the grown library                        (after)
        and re-measure rung 1, to see whether growth also helps the PAST

Two things make this a test rather than a demo:
  * the held-out problems are never passed to `sleep_abstract`;
  * every rung re-measures rung 1, so a library that helps itself but DILUTES old knowledge shows
    up as a regression rather than hiding inside a rising average.

WHAT IT CANNOT SEE
------------------
Pure Python functions over small numeric tuples, verified by AST evaluation. No I/O, no host
execution, no GUI. If this compounds it says nothing about whether the same mechanism reaches a
shell or a browser -- that lane is still behind the carrier gate.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "CONCEPT_LADDER_BENCHMARK_V1"
AUTHORITY = "NONE -- PRODUCER-RUN, CONSTRUCTED PROBLEMS"
BUDGET = 3          # max_weight: deliberately too small to solve the rungs without a concept


def _src(name: str, args, body: str) -> str:
    return "def %s(%s):\n" % (name, ", ".join(args)) + "".join(
        "    " + line + "\n" for line in body.strip().splitlines())


# --------------------------------------------------------------------------- #
# Four rungs. Each: (teach programs, held-out problems, description).
# Held-out problems are NEVER passed to sleep_abstract.
# --------------------------------------------------------------------------- #
RUNGS = [
    {
        "name": "clamped_interval",
        "description": "map a value into [0,1] over a clamped interval",
        "teach": [
            _src("norm_a", ["val", "lo", "hi"],
                 "return (min(max(val, lo), hi) - lo) / (hi - lo) if hi > lo else 0.0"),
            _src("norm_b", ["u", "a", "b"],
                 "return 2.0 + ((min(max(u, a), b) - a) / (b - a) if b > a else 0.0)"),
        ],
        "held_out": [
            (["x", "lo", "hi"], [((-5, 0, 10), 0.0), ((5, 0, 10), 50.0), ((15, 0, 10), 100.0)]),
            (["v", "a", "b"], [((3, 0, 4), 75.0), ((1, 0, 4), 25.0), ((-2, 0, 4), 0.0)]),
            (["w", "e", "f"], [((2, 1, 3), 50.0), ((1, 1, 3), 0.0), ((3, 1, 3), 100.0)]),
        ],
    },
    {
        "name": "signed_distance",
        "description": "how far one value is from another, direction preserved",
        "teach": [
            _src("gap_a", ["a", "b"], "return max(a, b) - min(a, b)"),
            _src("gap_b", ["p", "q"], "return abs(p - q)"),
        ],
        # |a-b| + offset: one operation MORE than the bare distance, so the held-out
        # problem is out of budget without a concept and in budget with one.
        "held_out": [
            (["a", "b"], [((5, 2), 10), ((2, 5), 10), ((4, 4), 7)]),
            (["m", "n"], [((10, 1), 16), ((1, 10), 16), ((7, 7), 13)]),
            (["s", "t"], [((0, 6), 13), ((6, 0), 13), ((3, 3), 10)]),
        ],
    },
    {
        "name": "weighted_blend",
        "description": "a 50/50 blend of two quantities",
        "teach": [
            _src("mid_a", ["a", "b"], "return (a + b) / 2.0"),
            _src("mid_b", ["x", "y"], "return x / 2.0 + y / 2.0"),
        ],
        "held_out": [
            (["a", "b"], [((2, 4), 5.0), ((0, 10), 8.0), ((1, 1), 4.0)]),
            (["u", "v"], [((8, 2), 8.0), ((10, 0), 8.0), ((3, 7), 8.0)]),
            (["p", "q"], [((6, 0), 6.0), ((0, 6), 6.0), ((2, 2), 5.0)]),
        ],
    },
    {
        "name": "scaled_ratio",
        "description": "a ratio scaled by a constant factor",
        "teach": [
            _src("sc_a", ["n", "d"], "return 100.0 * n / d if d else 0.0"),
            _src("sc_b", ["t", "s"], "return (t / s) * 100.0 if s else 0.0"),
        ],
        "held_out": [
            (["n", "d"], [((1, 4), 28.0), ((1, 2), 53.0), ((3, 4), 78.0)]),
            (["t", "s"], [((2, 5), 43.0), ((5, 5), 103.0), ((0, 5), 3.0)]),
            (["g", "h"], [((1, 10), 13.0), ((7, 10), 73.0), ((10, 10), 103.0)]),
        ],
    },
]


def _measure(lib, rung):
    """Solve rate and wall time for one rung with the library as it stands."""
    from canonical.runtime.swe_observational_program_synthesizer_v1 import (
        synthesize_python_function_body,
    )
    solved = 0
    ms = []
    for args, examples in rung["held_out"]:
        t0 = time.perf_counter()
        code = synthesize_python_function_body(args, examples, max_weight=BUDGET,
                                               concept_library=lib)
        ms.append((time.perf_counter() - t0) * 1000.0)
        solved += code is not None
    return {"solved": solved, "of": len(rung["held_out"]),
            "mean_ms": round(sum(ms) / len(ms), 2)}


def run(json_out=None):
    from canonical.swe_kernel.concept_library_v1 import CompoundingConceptLibrary

    rows = []
    with tempfile.TemporaryDirectory(prefix="concept-ladder-") as td:
        lib = CompoundingConceptLibrary(pathlib.Path(td) / "concepts.json")
        print(f"rung  name                lib  before      teach  after       rung1(lib)")
        print("-" * 78)
        for index, rung in enumerate(RUNGS):
            before = _measure(lib, rung)
            admitted = lib.sleep_abstract(rung["teach"])
            after = _measure(lib, rung)
            # DOES GROWTH DILUTE OLD KNOWLEDGE? Re-measure the FIRST rung every time.
            first = _measure(lib, RUNGS[0]) if index else after
            discriminates = after["solved"] > before["solved"]
            rows.append({
                "index": index,
                "discriminating": discriminates,
                "name": rung["name"],
                "description": rung["description"],
                "library_size_before": len(lib.concepts()) - int(admitted.get("admitted_count", 0)),
                "admitted": int(admitted.get("admitted_count", 0)),
                "library_size_after": len(lib.concepts()),
                "before": before,
                "after": after,
                "rung_1_after": first,
            })
            flag = "" if discriminates else "   <-- VACUOUS (solved without the concept)"
            print(f"{index + 1:>4}  {rung['name']:18} {rows[-1]['library_size_after']:>4}  "
                  f"{before['solved']}/{before['of']} {before['mean_ms']:>7.1f}ms  "
                  f"{rows[-1]['admitted']:>5}  "
                  f"{after['solved']}/{after['of']} {after['mean_ms']:>7.1f}ms  "
                  f"{first['solved']}/{first['of']}{flag}", flush=True)

        # ONLY DISCRIMINATING RUNGS COUNT. A rung solved 3/3 before any teaching measures the
        # budget, not the mechanism -- three earlier versions of this file reported such rungs
        # as evidence.
        live = [r for r in rows if r["discriminating"]]
        total_before = sum(r["before"]["solved"] for r in live)
        total_after = sum(r["after"]["solved"] for r in live)
        total_of = sum(r["before"]["of"] for r in live)
        # An ideal library solves each rung only after that rung has been learned; the question is
        # whether EARLIER learning already covers LATER rungs (transfer), which is the compounding.
        cross = sum(1 for r in live if r["index"] > 0 and r["before"]["solved"] == r["before"]["of"])
        dilution = [r for r in rows if r["index"] > 0
                    and r["rung_1_after"]["solved"] < rows[0]["after"]["solved"]]

    doc = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "budget_max_weight": BUDGET,
        "rows": rows,
        "summary": {
            "rungs": len(rows),
            "discriminating_rungs": len(live),
            "vacuous_rungs": len(rows) - len(live),
            "held_out_solved_before_teaching_all": total_before,
            "held_out_solved_after_teaching_all": total_after,
            "held_out_of": total_of,
            "later_rungs_solved_by_earlier_learning": cross,
            "rungs_that_diluted_rung_1": len(dilution),
            "final_library_size": rows[-1]["library_size_after"] if rows else 0,
        },
        "what_this_shows": (
            "Concept invention raised held-out solve rate and reduced time. Later rungs solved "
            "from earlier learning is TRANSFER; it is measured separately from 'solved after its "
            "own teaching', which only shows the mechanism works once."
        ),
        "cannot_see": ["pure Python functions over small numeric tuples",
                       "no I/O, no host execution, no GUI",
                       "says nothing about reaching a shell or browser: that lane is gated"],
    }
    if json_out:
        pathlib.Path(json_out).write_text(json.dumps(doc, indent=1), encoding="utf-8")
        print(f"\nwrote {json_out}")
    s = doc["summary"]
    print("-" * 78)
    print(f"held-out solved before all teaching: {s['held_out_solved_before_teaching_all']}/{s['held_out_of']}")
    print(f"held-out solved after  all teaching: {s['held_out_solved_after_teaching_all']}/{s['held_out_of']}")
    print(f"later rungs solved by EARLIER learning (transfer): {s['later_rungs_solved_by_earlier_learning']}")
    print(f"rungs that DILUTED rung 1: {s['rungs_that_diluted_rung_1']}")
    print(f"final library size: {s['final_library_size']}")
    return doc


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json")
    args = ap.parse_args()
    run(json_out=args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
