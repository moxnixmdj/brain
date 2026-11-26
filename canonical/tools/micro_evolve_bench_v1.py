"""micro_evolve_bench_v1 — priced reach of the zero-LLM repair loop (plan v6 §6).

Self-generated family: random 1-var programs -> render a unittest file from the
program -> break the implementation to `return 0` -> run the LIVE loop (model_v1
socket + solve_v1) -> re-verify in a FRESH PROCESS (the loop's own word is not
accepted). Reports solved, ms/task, and LLM tokens (always 0 by construction).

Knobs under test (each adopted only on measured wins, per plan v6):
  --steps N      loop horizon (default 6, the production value)
  --points N     example points per task (default 6, as the smoke run)
  --seed N       task family (fixed 65 = the recorded smoke family; same tasks
                 across variants, so deltas are attributable to the knob alone)

Run:  python3 canonical/tools/micro_evolve_bench_v1.py [--steps 10] [--points 8]
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import random
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

GEN = [
    lambda a, b: f"(x + {b}) * {a} if x >= 0 else (x - {b}) * {a}",
    lambda a, b: f"x * {a} + {b}",
    lambda a, b: f"abs(x) * {a} - {b}",
    lambda a, b: f"x if x > {b} else {a}",
    lambda a, b: f"-(x * {a}) if x < 0 else x * {a} + {b}",
]

# 2-var family (v6 section 10): the loop's home family saturated at 40/40;
# a saturated yardstick measures nothing. These shapes require cross-variable
# composition the single-var 2c completion does not cover.
GEN2 = [
    lambda a, b: f"x * y + {a}",
    lambda a, b: f"(x + {a}) * (y - {b})",
    lambda a, b: f"x if x > y + {a} else y * {b}",
    lambda a, b: f"abs(x - y) * {a}",
    lambda a, b: f"(x * {a} + y) if (x + y) >= {b} else -(x * {a}) - y",
]


# Concept-shaped family (v6 section 14): clamps. `min`/`max` are NOT atoms in
# the hand-written micro grammar at any depth, so this family probes a
# different organ -- the compounding concept library, whose admitted concepts
# ARE template atoms. The point domain is widened so both clamp edges are
# visible (a 6-point sample in -6..6 never reaches 100, which would make the
# upper clamp unobservable and the family measure nothing).
GEN3 = [
    lambda a, b: f"min(max(x * {a}, 0), 100)",
    lambda a, b: f"min(max(x * {a} + {b}, 0), 100)",
    lambda a, b: f"max(min(x * {a}, 2 * {b} * {a} * 3), -{b} * 10)",
]


def make_family(n: int, seed: int, points: int, *, two_var: bool = False,
                family: str | None = None):
    rng = random.Random(seed)
    tasks = []
    for i in range(n):
        gen = {"clamp": GEN3}.get(family or "", GEN2 if two_var else GEN)
        g = gen[i % len(gen)]
        a, b = rng.randint(1, 4), rng.randint(1, 3)
        expr = g(a, b)
        if family == "clamp":
            f = eval(f"lambda x: {expr}", {"abs": abs, "min": min, "max": max}, {})  # noqa: S307
            pts = rng.sample(list(range(-80, 81)), points)
        elif two_var:
            f = eval(f"lambda x, y: {expr}", {"abs": abs}, {})  # noqa: S307
            grid = [(x, y) for x in range(-3, 4) for y in range(-3, 4)]
            pts = rng.sample(grid, points)
        else:
            f = eval(f"lambda x: {expr}", {"abs": abs}, {})  # noqa: S307  # 1-var
            pts = rng.sample(range(-6, 7), points)
        tasks.append({"expr": expr, "f": f, "pts": pts})
    return tasks


def run_task(task, steps: int) -> tuple[bool, float]:
    from canonical.runtime import brain_unified_model_v1 as bum
    from canonical.runtime import model_v1, solve_v1

    bound = model_v1.bind(bum.SOVEREIGN_ZERO_LLM_MODEL_SPEC)
    f = task["f"]
    arity = f.__code__.co_argcount
    sig = "(x)" if arity == 1 else "(x, y)"
    argstr = (lambda p: str(p)) if arity == 1 else (lambda p: f"{p[0]}, {p[1]}")
    with tempfile.TemporaryDirectory(prefix="micro-evolve-") as td:
        ws = pathlib.Path(td)
        (ws / "impl.py").write_text(f"def f{sig}:\n    return 0\n", encoding="utf-8")
        asserts = "".join(
            f"        self.assertEqual(f({argstr(p)}), {f(*p) if arity == 2 else f(p)})\n"
            for p in task["pts"]
        )
        (ws / "test_f.py").write_text(
            "import unittest\nfrom impl import f\nclass T(unittest.TestCase):\n"
            "    def test_pts(self):\n" + asserts,
            encoding="utf-8",
        )
        t0 = time.perf_counter()
        # Read-only memory for the duration of a measured run. `learn=False`
        # already suppresses the loop's own learning, but it does NOT cover the
        # concept library: the observational synthesizer credits `uses` on the
        # ambient policy, so a benchmark run used to persist learning state into
        # a COMMITTED file (git diff showed `uses: 0 -> 2` after one family).
        # A yardstick that mutates the system it measures is not a yardstick --
        # the same lesson as the §9 bytecode-cache verifier lie, one level up.
        from canonical.runtime.memory_policy_v1 import READ_ONLY, memory_policy_scope
        with memory_policy_scope(READ_ONLY):
            out = solve_v1.solve(
                "fix f in impl.py so test_f.py passes", str(ws),
                model=bound, steps=steps, learn=False,
            )
        ms = (time.perf_counter() - t0) * 1000
        ok = out.get("verdict") == "DONE"
        if ok:  # independent re-verification, fresh process
            r = subprocess.run(
                [sys.executable, "-m", "unittest", "discover", "-s", ".",
                 "-p", "test*.py"],
                cwd=ws, capture_output=True, text=True,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            )
            ok = r.returncode == 0
        return ok, ms


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="micro_evolve_bench_v1")
    ap.add_argument("--tasks", type=int, default=10)
    ap.add_argument("--seed", type=int, default=65)
    ap.add_argument("--steps", type=int, default=6)
    ap.add_argument("--points", type=int, default=6)
    ap.add_argument("--two-var", action="store_true",
                    help="2-variable family (hard yardstick; v6 section 10)")
    ap.add_argument("--clamp", action="store_true",
                    help="concept-shaped clamp family (v6 section 14)")
    ns = ap.parse_args(argv)

    family = make_family(ns.tasks, ns.seed, ns.points, two_var=ns.two_var,
                         family="clamp" if ns.clamp else None)
    rows = []
    for t in family:
        ok, ms = run_task(t, ns.steps)
        rows.append({"expr": t["expr"], "ok": ok, "ms": round(ms)})
        print(f"{'HIT ' if ok else 'miss'} {ms:6.0f} ms  f(x) = {t['expr']}", flush=True)
    solved = sum(r["ok"] for r in rows)
    mean_ms = sum(r["ms"] for r in rows) / max(1, len(rows))
    print(json.dumps({
        "schema": "MICRO_EVOLVE_BENCH_V1", "tasks": ns.tasks, "seed": ns.seed,
        "steps": ns.steps, "points": ns.points, "two_var": ns.two_var, "clamp": ns.clamp,
        "solved": solved, "mean_ms": round(mean_ms), "llm_samples": 0, "tokens": 0,
        "rows": rows,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
