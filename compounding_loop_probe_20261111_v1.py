#!/usr/bin/env python3
"""Does a learned library make the NEXT synthesis cheaper? (the compounding claim)

Why this file exists
--------------------
Every probe before this one measured the LIBRARY: how many concepts get admitted, whether they fire
on held-out code, whether they compress. None measured what the library BUYS.

`compression_machine_corpus_probe_20261111_v1.py` (§4f) established that the compressor works on
machine-synthesized programs: 2 concepts admitted, 13 of 40 held-out programs rewritten, amortized
shrink 0.9675, versus 0 of 40 on human-authored source. That is a library that exists and
generalizes. It is not yet evidence of compounding.

Compounding is a different claim, and it is the one the owner's question actually rests on:

    "give it the smartest actions once and it learns them permanently"
        -> the next problem must get CHEAPER because the first one was solved

This measures that directly: synthesize held-out tasks with an empty library, then synthesize the
SAME tasks again with a library learned from different tasks, and compare.

Design
------
Tasks come from the same generator as §4f (six families whose instances differ only by a literal),
so the warmup and held-out tasks are drawn from the same distribution, which is the setting where a
library should help.

    WARMUP     250 tasks   solved, then compressed by `sleep_abstract` into a library
    HELD-OUT   120 tasks   NEVER used to build the library

    COLD arm   synthesize the 120 held-out tasks with an EMPTY library
    WARM arm   synthesize the SAME 120 held-out tasks with the library learned from warmup

Identical task list, identical synthesizer settings, identical order. The only difference is
whether prior experience is present.

The trap this design has to avoid
---------------------------------
`synthesize_python_function_body` is not safe to call with `concept_library=None` for a control.
Reading the source: when `concept_library` is None it falls back to `DEFAULT_LIBRARY_PATH` if that
file exists, which would silently load whatever library is persisted on disk and contaminate the
cold arm. So COLD is passed an explicitly constructed EMPTY library on a fresh temp path. Without
this the control is not a control and the whole measurement is void.

What is measured, per arm
-------------------------
    solved          tasks synthesized successfully AND verified against the full grid
    success_rate    solved / attempted
    wall_seconds    total synthesis time
    mean_body_nodes AST nodes of the synthesized body, over solves

Pre-registered verdict (written before the run)
-----------------------------------------------
    COMPOUNDS       warm solves strictly more held-out tasks than cold, OR warm is >= 20% faster in
                    wall clock at equal-or-better success rate. Prior experience made new work
                    cheaper.
    NO_COMPOUNDING  warm success rate is <= cold and warm is not faster. Then a library that
                    demonstrably generalizes still buys nothing at solve time, and the "learn it
                    once" claim is false as stated -- report and STOP tuning the library.
    INCONCLUSIVE    either arm solves 0 or everything, so there is no headroom to improve into.

Both directions are informative. A refutation here is worth more than another positive library
measurement, because it would end the line.

This is a producer-run measurement. It is not independent verification and it says nothing about
GUI or unbounded computer use.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import pathlib
import random
import sys
import tempfile
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from canonical.swe_kernel.concept_library_v1 import CompoundingConceptLibrary
from canonical.runtime.swe_observational_program_synthesizer_v1 import (
    synthesize_python_function_body,
)

_here = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "_mcp", _here / "compression_machine_corpus_probe_20261111_v1.py"
)
_mcp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mcp)

build_tasks = _mcp.build_tasks
GRID = _mcp.GRID
WANT = _mcp.WANT

N_WARMUP = 250
N_HELD = 400
MAX_WEIGHT = 4


def _empty_library() -> CompoundingConceptLibrary:
    """An explicitly EMPTY library. Never pass None: the synthesizer falls back to the persisted
    default library on disk, which would contaminate the cold arm."""
    d = pathlib.Path(tempfile.mkdtemp())
    return CompoundingConceptLibrary(d / "empty.json")


def synth_one(fn, library) -> tuple[str | None, int]:
    """Synthesize and verify one task. Returns (body_source_or_None, nodes)."""
    try:
        examples = [((v,), fn(v)) for v in GRID]
    except Exception:  # noqa: BLE001
        return None, 0
    body = None
    try:
        body = synthesize_python_function_body(
            ("x",), examples, max_weight=MAX_WEIGHT, concept_library=library
        )
    except Exception:  # noqa: BLE001
        return None, 0
    if not body:
        return None, 0
    src = "def run(x):\n" + "".join("    " + line + "\n" for line in str(body).splitlines())
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return None, 0
    ns: dict = {}
    try:
        exec(compile(src, "<synth>", "exec"), ns)
    except Exception:  # noqa: BLE001
        return None, 0
    try:
        for v in GRID:
            if repr(ns["run"](v)) != repr(fn(v)):
                return None, 0
    except Exception:  # noqa: BLE001
        return None, 0
    return src, sum(1 for _ in ast.walk(tree))


def run_arm(tasks, library) -> dict:
    """Per-task outcomes are recorded so the two arms can be compared PAIRED on the tasks both
    solved. Aggregate solve counts alone were too noisy to read: a 7-vs-8 difference out of 120 is
    well inside sampling error, and it made an OR in the stopping rule fire COMPOUNDS while time
    and body size both got worse. The paired comparison removes task-difficulty as a confound."""
    solved = 0
    nodes: list[int] = []
    sources: list[str] = []
    per_task: dict[str, dict] = {}
    t0 = time.time()
    for _family, label, fn in tasks:
        t1 = time.time()
        src, n = synth_one(fn, library)
        dt = round(time.time() - t1, 4)
        per_task[label] = {"solved": src is not None, "seconds": dt, "nodes": n if src else None}
        if src is None:
            continue
        solved += 1
        nodes.append(n)
        sources.append(src)
    return {
        "attempted": len(tasks),
        "solved": solved,
        "success_rate": round(solved / len(tasks), 4) if tasks else 0.0,
        "wall_seconds": round(time.time() - t0, 2),
        "mean_body_nodes": round(sum(nodes) / len(nodes), 2) if nodes else None,
        "sources": sources,
        "per_task": per_task,
    }


def main() -> int:
    rng = random.Random(2026)
    tasks = build_tasks(rng)
    if len(tasks) < 400:
        print(f"NOT_ENOUGH_TASKS: {len(tasks)}")
        return 2

    warmup = tasks[:N_WARMUP]
    held = tasks[N_WARMUP : N_WARMUP + N_HELD]
    print(f"tasks available={len(tasks)}  warmup={len(warmup)}  held_out={len(held)}", flush=True)

    # ---- COLD: held-out tasks with an explicitly empty library ------------------
    print("running COLD arm ...", flush=True)
    cold = run_arm(held, _empty_library())

    # ---- build the library from WARMUP tasks (different tasks, never held-out) --
    print("solving WARMUP tasks ...", flush=True)
    warmup_arm = run_arm(warmup, _empty_library())

    lib_path = pathlib.Path(tempfile.mkdtemp()) / "learned.json"
    library = CompoundingConceptLibrary(lib_path)
    sleep_res = (
        library.sleep_abstract(warmup_arm["sources"]) if warmup_arm["sources"]
        else {"admitted_count": 0}
    )
    print(
        f"library built from {len(warmup_arm['sources'])} warmup programs: "
        f"{sleep_res.get('admitted_count')} concepts",
        flush=True,
    )

    # ---- WARM: the SAME held-out tasks, now with the learned library ------------
    print("running WARM arm ...", flush=True)
    warm = run_arm(held, library)

    d_solved = warm["solved"] - cold["solved"]
    speedup = (cold["wall_seconds"] / warm["wall_seconds"]) if warm["wall_seconds"] else None

    # ---- paired comparison on tasks BOTH arms solved -----------------------------
    cpt, wpt = cold["per_task"], warm["per_task"]
    both = sorted(set(cpt) & {k for k, v in wpt.items() if v["solved"]} &
                  {k for k, v in cpt.items() if v["solved"]})
    only_cold = sorted(k for k in cpt if cpt[k]["solved"] and not wpt.get(k, {}).get("solved"))
    only_warm = sorted(k for k in wpt if wpt[k]["solved"] and not cpt.get(k, {}).get("solved"))
    paired = {
        "tasks_solved_by_both": len(both),
        "cold_mean_nodes": round(sum(cpt[k]["nodes"] for k in both) / len(both), 3) if both else None,
        "warm_mean_nodes": round(sum(wpt[k]["nodes"] for k in both) / len(both), 3) if both else None,
        "cold_mean_seconds": round(sum(cpt[k]["seconds"] for k in both) / len(both), 4) if both else None,
        "warm_mean_seconds": round(sum(wpt[k]["seconds"] for k in both) / len(both), 4) if both else None,
        "solved_only_by_cold": len(only_cold),
        "solved_only_by_warm": len(only_warm),
    }
    if paired["cold_mean_nodes"] and paired["warm_mean_nodes"]:
        paired["node_ratio"] = round(paired["warm_mean_nodes"] / paired["cold_mean_nodes"], 4)
    if paired["cold_mean_seconds"] and paired["warm_mean_seconds"]:
        paired["time_ratio"] = round(paired["warm_mean_seconds"] / paired["cold_mean_seconds"], 4)

    # Verdict. A single extra solve is NOT compounding: at these rates it is sampling noise. The
    # pre-registered OR is deliberately tightened here, and the tightening is recorded, because
    # firing COMPOUNDS on +1/120 while time and size both worsened would be a false positive.
    headroom = 0 < cold["solved"] < len(held)
    improved = d_solved > 1 and paired.get("time_ratio", 9) <= 1.0 and paired.get("node_ratio", 9) <= 1.0
    if not headroom:
        verdict = "INCONCLUSIVE"
    elif improved:
        verdict = "COMPOUNDS"
    else:
        verdict = "NO_COMPOUNDING"

    report = {
        "schema": "PROBE_COMPOUNDING_LOOP_V1",
        "corpus": {"warmup_tasks": len(warmup), "held_out_tasks": len(held)},
        "library": {
            "warmup_programs": len(warmup_arm["sources"]),
            "warmup_solved": warmup_arm["solved"],
            "admitted": sleep_res.get("admitted_count"),
            "total_concepts": sleep_res.get("total_concepts"),
            "concepts": [
                {
                    "concept_id": a.get("concept_id"),
                    "arity": a.get("arity"),
                    "corpus_sites": a.get("corpus_sites"),
                    "body_expr": str(a.get("body_expr") or "")[:70],
                }
                for a in (sleep_res.get("admitted") or [])
            ],
        },
        "paired": paired,
        "cold": {k: cold[k] for k in ("attempted", "solved", "success_rate", "wall_seconds", "mean_body_nodes")},
        "warm": {k: warm[k] for k in ("attempted", "solved", "success_rate", "wall_seconds", "mean_body_nodes")},
        "paired": paired,
        "paired": paired,
        "delta_solved": d_solved,
        "wall_speedup": round(speedup, 4) if speedup else None,
        "verdict": verdict,
    }
    # sources are large; keep the JSON output readable
    print(json.dumps(report, indent=2))
    print()
    print(f"{'arm':<6} {'solved':>7} {'rate':>7} {'wall_s':>8} {'mean_nodes':>11}")
    print("-" * 44)
    for key in ("cold", "warm"):
        a = report[key]
        print(
            f"{key:<6} {a['solved']:>7} {a['success_rate']:>7} "
            f"{a['wall_seconds']:>8} {str(a['mean_body_nodes']):>11}"
        )
    print()
    print(f"delta solved: {d_solved}   wall speedup: {report['wall_speedup']}")
    print()
    print("--- paired, on the tasks BOTH arms solved ---")
    for k, v in paired.items():
        print(f"  {k:<24} {v}")
    print("verdict:", verdict)
    print()
    print("This is a producer-run measurement. It is not independent verification and it says")
    print("nothing about GUI or unbounded computer use.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
