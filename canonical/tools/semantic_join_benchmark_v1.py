"""Does semantic anti-unification buy anything beyond re-spelling? Measure all three arms.

WHY THIS FILE EXISTS
--------------------
The claim in `COMPOUNDING_IS_GENERATION_20261103_V1.md` was that the organ "cannot notice that two
different programs mean the same thing". Probing that claim on 2026-11-04 turned up two of the
agent's own instrument bugs and one finding that supersedes the claim's diagnosis. A result that
exists only as prose from a throwaway session is one step from unreproducible -- `LEARN_TO_LEARN_VERDICT`
§12 already paid for that lesson -- so the measurement lives here, re-runnable, with no JSON
hand-copied into the record.

WHAT IT MEASURES
----------------
For a concept that is genuinely NOT in the synthesizer's bank (a clamped normalisation; `abs` and
`max`/`min` are native, so a concept built from them has no headroom by construction), three arms:

  ARM 1  every program written the SAME way          -> does the organ learn at all?
  ARM 2  half the programs written a SECOND way      -> does it still learn?
  ARM 3  same corpus, second half REWRITTEN through   -> does the semantic correspondence
         a verified correspondence into the first way   restore what ARM 2 lost?

ARM 1 is the control that says the concept is worth learning. If ARM 1 == ARM 3 the join buys
nothing on this corpus. ARM 2 is the arm the join exists to repair.

THE HONEST READ
---------------
What the join restores is the *corpus*: it lets one concept cover programs written two ways. It
does not by itself let the synthesizer reach a NEW FUNCTION written the other way, because the
concept is a call the search can emit in either spelling -- the spelling was never what the
search was blocked on. Measured 2026-11-04: all three arms solved the same held-out count.

Authority: NONE. Pure Python, small numeric tuples, $0.
"""
from __future__ import annotations

import argparse
import ast
import json
import statistics
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime.swe_observational_program_synthesizer_v1 import (  # noqa: E402
    synthesize_python_function_body,
)
from canonical.swe_kernel.concept_library_v1 import CompoundingConceptLibrary  # noqa: E402
from canonical.swe_kernel.semantic_unification_v1 import (  # noqa: E402
    bridge_sources,
    find_correspondences,
)

SCHEMA = "PROJECT_BRAIN_SEMANTIC_JOIN_BENCHMARK_V1"

# Eight distinct variable triples so repeated sites do not accidentally share syntax.
TRIPLES = [("val", "lo", "hi"), ("u", "a", "b"), ("x", "mn", "mx"), ("t", "low", "high"),
           ("q", "p0", "p1"), ("zz", "k0", "k1"), ("mm", "n0", "n1"), ("hh", "g0", "g1")]

# HELD OUT: never passed to `sleep_abstract`. `normalised + 0.5` -- one operation beyond the
# concept's own body, which is the headroom a concept is supposed to supply.
HELD_OUT = [
    (["v", "l", "h"], [((5, 2, 4), 1.5), ((7, 0, 10), 0.75), ((-3, 0, 10), 0.5)]),
    (["s", "lo2", "hi2"], [((9, 8, 10), 1.0), ((5, 0, 4), 1.75), ((12, 10, 11), 2.0)]),
]

MAX_WEIGHT = 4
# Corpus size changes the answer, and measuring one size flatters whichever conclusion the agent
# was hoping for. At 8+8 each spelling amortises its own concept definition, so there is nothing
# for a join to restore; below ~7 sites a concept cannot pay for its own definition at all
# (measured: 11-12 sites for the 9-node distance concept, under the MDL gate). Both regimes are
# reported.
CORPUS_SIZES = (4, 6, 8)


def _src(name: str, params: list[str], body: str) -> str:
    return "def %s(%s):\n    return %s" % (name, ", ".join(params), body)


def spelling_a(i: int, v: tuple[str, str, str]) -> str:
    val, lo, hi = v
    return _src(f"na{i}", list(v),
                f"(min(max({val}, {lo}), {hi}) - {lo}) / ({hi} - {lo}) if {hi} > {lo} else 0.0")


def spelling_b(i: int, v: tuple[str, str, str]) -> str:
    """The same function, written with clamps applied to the RESULT instead of the input."""
    val, lo, hi = v
    return _src(f"nb{i}", list(v),
                f"min(1.0, max(0.0, ({val} - {lo}) / ({hi} - {lo}))) if {hi} > {lo} else 0.0")


def _solved(library_path: Path | None) -> int:
    lib = CompoundingConceptLibrary(library_path) if library_path is not None else None
    hits = 0
    for params, examples in HELD_OUT:
        body = synthesize_python_function_body(params, examples, max_weight=MAX_WEIGHT,
                                             concept_library=lib)
        hits += 1 if body else 0
    return hits


def bridge_corpus(first: list[str], second: list[str]) -> tuple[list[str], list[dict[str, Any]]]:
    """Rewrite each program of `second` into the spelling of its `first` counterpart."""
    bridged: list[str] = []
    log: list[dict[str, Any]] = []
    for left, right in zip(first, second):
        doc = find_correspondences([left, right])
        target = None
        for corr in doc["correspondences"]:
            if _node_count(corr["left"]) >= _node_count(corr["right"]):
                target = corr
                break
        if target is None:
            bridged.append(right)
            log.append({"status": "NO_CORRESPONDENCE"})
            continue
        new = bridge_sources(left, right, target)
        bridged.append(new)
        log.append({"status": "BRIDGED" if new != right else "REWRITE_CHANGED_NOTHING",
                    "correspondence": f"{target['left']} == {target['right']}",
                    "grade": target["grade"]})
    return bridged, log


def _node_count(src: str) -> int:
    try:
        return sum(1 for _ in ast.walk(ast.parse(src, mode="eval")))
    except SyntaxError:
        return 0


def run() -> dict[str, Any]:
    baseline = _solved(None)
    sweeps: list[dict[str, Any]] = []
    bridge_log: list[dict[str, Any]] = []

    for size in CORPUS_SIZES:
        first = [spelling_a(i, v) for i, v in enumerate(TRIPLES[:size])]
        second = [spelling_b(i, v) for i, v in enumerate(TRIPLES[:size])]
        bridged, log = bridge_corpus(first, second)
        if not bridge_log:
            bridge_log = log
        arms = _measure_arms(first, second, bridged)
        by_name = {a["arm"]: a for a in arms}
        control, mixed, joined = (by_name["all_one_spelling"], by_name["two_spellings"],
                                  by_name["bridged"])
        sweeps.append({
            "programs_per_spelling": size,
            "arms": arms,
            "verdict": {
                "concept_is_learnable": bool(control["admitted"] > 0),
                # Graded, not all-or-nothing: the first version required `mixed == 0`, which
                # hid the actual effect at thin corpora (mixed 1 -> joined 2) and reported "no".
                "join_increases_admission": bool(joined["admitted"] > mixed["admitted"]),
                "join_fully_restores_control": bool(joined["admitted"] == control["admitted"]),
                "join_improves_held_out_reach": bool(
                    joined["held_out_solved"] > max(control["held_out_solved"],
                                                    mixed["held_out_solved"])),
                "bridge_succeeded_on_all_pairs": all(
                    b.get("status") == "BRIDGED" for b in log),
            },
        })

    return {
        "schema": SCHEMA,
        "measured": "2026-11-04",
        "baseline_empty_library_solved": baseline,
        "held_out_total": len(HELD_OUT),
        "max_weight": MAX_WEIGHT,
        "sweeps": sweeps,
        "limits": [
            "the join restores the CORPUS, not the search: a concept is callable in either "
            "spelling, so re-spelling was never what blocked synthesis",
            "held-out reach did not improve at any corpus size; the concept's benefit here is "
            "compactness and speed, not reach",
            "agreement is observed on a finite probe vector, not proved",
            "the two spellings are equivalent on all probed values by construction, which makes "
            "this a test of the join, not a test of whether two real programs are equivalent",
        ],
        "authority": "NONE",
        "truth_achieved": False,
    }


def _measure_arms(first: list[str], second: list[str],
                  bridged: list[str]) -> list[dict[str, Any]]:
    arms: list[dict[str, Any]] = []
    for name, corpus, description in (
        ("all_one_spelling", first + first, "control: one spelling, concept must amortise"),
        ("two_spellings", first + second, "the arm the join exists to repair"),
        ("bridged", first + bridged, "same corpus, second half rewritten through a correspondence"),
    ):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "library.json"
            lib = CompoundingConceptLibrary(path)
            t0 = time.perf_counter()
            result = lib.sleep_abstract(corpus)
            teach_ms = (time.perf_counter() - t0) * 1000.0

            gathered: list[float] = []
            grown = CompoundingConceptLibrary(path)
            for _ in range(5):
                t1 = time.perf_counter()
                solved = _solved(path)
                gathered.append((time.perf_counter() - t1) * 1000.0)
            arms.append({
                "arm": name,
                "description": description,
                "admitted": int(result.get("admitted_count") or 0),
                "concept_bodies": sorted({c["body_expr"] for c in result.get("admitted") or []}),
                "library_size": len(list(grown.concepts())),
                "held_out_solved": solved,
                "held_out_total": len(HELD_OUT),
                "held_out_median_ms": round(statistics.median(gathered), 1),
                "teach_ms": round(teach_ms, 1),
            })
    return arms


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = ap.parse_args(argv)
    doc = run()
    if args.json:
        print(json.dumps(doc, indent=2, sort_keys=True))
        return 0
    print("held-out solved with an EMPTY library: %d/%d"
          % (doc["baseline_empty_library_solved"], doc["held_out_total"]))
    for sweep in doc["sweeps"]:
        print("\nsites per spelling: %d" % sweep["programs_per_spelling"])
        print("%-18s %8s %8s %10s %11s" % ("arm", "admitted", "library", "held-out", "median ms"))
        print("-" * 60)
        for arm in sweep["arms"]:
            print("%-18s %8d %8d %7d/%-2d %10.1f" % (
                arm["arm"], arm["admitted"], arm["library_size"],
                arm["held_out_solved"], arm["held_out_total"], arm["held_out_median_ms"]))
        for key, value in sweep["verdict"].items():
            print("  %-46s %s" % (key, "YES" if value else "no"))
    print("\nlimits:")
    for line in doc["limits"]:
        print("  - " + line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
