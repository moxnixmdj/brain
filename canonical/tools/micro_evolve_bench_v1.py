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


def make_family(n: int, seed: int, points: int):
    rng = random.Random(seed)
    tasks = []
    for i in range(n):
        g = GEN[i % len(GEN)]
        a, b = rng.randint(1, 4), rng.randint(1, 3)
        expr = g(a, b)
        f = eval(f"lambda x: {expr}", {"abs": abs}, {})  # noqa: S307
        pts = rng.sample(range(-6, 7), points)
        tasks.append({"expr": expr, "f": f, "pts": pts})
    return tasks


def run_task(task, steps: int) -> tuple[bool, float]:
    from canonical.runtime import brain_unified_model_v1 as bum
    from canonical.runtime import model_v1, solve_v1

    bound = model_v1.bind(bum.SOVEREIGN_ZERO_LLM_MODEL_SPEC)
    f = task["f"]
    with tempfile.TemporaryDirectory(prefix="micro-evolve-") as td:
        ws = pathlib.Path(td)
        (ws / "impl.py").write_text("def f(x):\n    return 0\n", encoding="utf-8")
        asserts = "".join(
            f"        self.assertEqual(f({p}), {f(p)})\n" for p in task["pts"]
        )
        (ws / "test_f.py").write_text(
            "import unittest\nfrom impl import f\nclass T(unittest.TestCase):\n"
            "    def test_pts(self):\n" + asserts,
            encoding="utf-8",
        )
        t0 = time.perf_counter()
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
            )
            ok = r.returncode == 0
        return ok, ms


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="micro_evolve_bench_v1")
    ap.add_argument("--tasks", type=int, default=10)
    ap.add_argument("--seed", type=int, default=65)
    ap.add_argument("--steps", type=int, default=6)
    ap.add_argument("--points", type=int, default=6)
    ns = ap.parse_args(argv)

    family = make_family(ns.tasks, ns.seed, ns.points)
    rows = []
    for t in family:
        ok, ms = run_task(t, ns.steps)
        rows.append({"expr": t["expr"], "ok": ok, "ms": round(ms)})
        print(f"{'HIT ' if ok else 'miss'} {ms:6.0f} ms  f(x) = {t['expr']}", flush=True)
    solved = sum(r["ok"] for r in rows)
    mean_ms = sum(r["ms"] for r in rows) / max(1, len(rows))
    print(json.dumps({
        "schema": "MICRO_EVOLVE_BENCH_V1", "tasks": ns.tasks, "seed": ns.seed,
        "steps": ns.steps, "points": ns.points,
        "solved": solved, "mean_ms": round(mean_ms), "llm_samples": 0, "tokens": 0,
        "rows": rows,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
