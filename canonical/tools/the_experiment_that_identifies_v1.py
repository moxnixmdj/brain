"""You cannot get more out of one experience. You can choose which experience to have.

The previous measurement (one observation identifies one bug in six) invites the wrong conclusion --
that experience is weak. It is not. An observation identifies a hypothesis exactly as far as the
candidates are BEHAVIOURALLY DISTINGUISHABLE on it: for `lis` one corpus case collapsed 399 candidates
to 1 (8.6 bits); for `kth` the case collapsed 400 to 400 (zero bits), because every candidate behaves
identically on that input. The observation was not weak. It was uninformative.

Which makes the design question different from the one this project has been asking. Not "how do we
store what we experienced", but **"which experiment identifies the program fastest"**. The object that
answers it is a behaviour table: candidates x probes -> output. Identification is then set arithmetic
(split on the observed output, keep the class the oracle names), and the optimal experiment is the
probe that splits the surviving set hardest. No parameters, no memory, no training -- a computed
experiment.

Measured here, per bug: the number of CHOSEN queries needed to leave one candidate standing, whether
that candidate is right on the probes never used to choose it, and how many GIVEN corpus cases the
same instrument needed (it needed more than the corpus has, or it never converged).
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import random
import sys
import time
from typing import Any, Sequence

TOOLS = pathlib.Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(REPO))

import force_the_value_and_see_v1 as forced  # noqa: E402
import grammar_closed_repair_v1 as gen  # noqa: E402
import how_many_hypotheses_survive_an_observation_v1 as hypotheses  # noqa: E402

SCHEMA = "BRAIN_THE_EXPERIMENT_THAT_IDENTIFIES_V1"
UPSTREAM = "https://github.com/jkoppel/QuixBugs"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"

CRASH = ("<crash>",)


def oracle_for(root: pathlib.Path, name: str):
    path = root / "correct_python_programs" / f"{name}.py"
    if not path.exists():
        return None
    space: dict[str, Any] = {}
    try:
        exec(compile(path.read_text(encoding="utf-8"), "<ref>", "exec"), space)  # noqa: S102
    except Exception:  # noqa: BLE001
        return None
    return space.get(name)


def probe_pool(root: pathlib.Path, name: str, *, count: int = 30, seed: int = 3) -> list[list[Any]]:
    rng = random.Random(seed)
    pool: list[list[Any]] = []
    for args, _expected in gen.examples_of(root, name):
        pool.append(list(args))
        for _ in range(2):
            now = hypotheses.perturbed(args, rng)
            if now is not None:
                pool.append(list(now))
    seen: set[str] = set()
    unique: list[list[Any]] = []
    for args in pool:
        key = repr(args)
        if key in seen:
            continue
        seen.add(key)
        unique.append(args)
    return unique[:count]


def behaviour_table(candidates: Sequence[dict[str, Any]], probes: Sequence[list[Any]],
                    name: str) -> dict[str, Any]:
    """candidates x probes -> output. One execution each; this is the whole identification object."""
    rows: list[list[Any]] = []
    for item in candidates:
        produced: list[Any] = []
        for args in probes:
            ran, value = forced.run_case(item["source"], name, list(args), forced=None)
            produced.append(value if ran else CRASH)
        rows.append(produced)
    return {"rows": rows}


def identify(name: str, candidates: Sequence[dict[str, Any]], probes: Sequence[list[Any]],
             truth: Sequence[Any], table: dict[str, Any], *, split_depth: int = 200) -> dict[str, Any]:
    """Greedy experiment design: at each step take the probe that splits the survivors hardest."""
    alive = list(range(len(candidates)))
    used: list[int] = []
    steps: list[dict[str, Any]] = []
    while len(alive) > 1 and len(used) < split_depth:
        best = None
        best_score = None
        for index in range(len(probes)):
            if index in used:
                continue
            buckets: dict[str, list[int]] = {}
            for candidate in alive:
                key = repr(table["rows"][candidate][index])
                buckets.setdefault(key, []).append(candidate)
            sizes = sorted((len(v) for v in buckets.values()), reverse=True)
            if len(sizes) < 2:
                continue  # this probe tells nothing about the survivors
            score = (sizes[0], -len(sizes))
            if best_score is None or score < best_score:
                best_score, best = score, index
        if best is None:
            steps.append({"stage": "NO_PROBE_SEPARATES_THE_REMAINING_CANDIDATES",
                          "alive": len(alive)})
            break
        used.append(best)
        want = truth[best]
        kept = []
        for candidate in alive:
            got = table["rows"][candidate][best]
            if got is not CRASH and want is not None and forced._same(got, want):  # noqa: SLF001
                kept.append(candidate)
        steps.append({"probe": best, "args": probes[best], "before": len(alive), "after": len(kept)})
        alive = kept
    held_out = [i for i in range(len(probes)) if i not in used]
    verdict: dict[str, Any] = {
        "chosen_queries": len(used), "survivors": len(alive), "steps": steps,
        "bits_resolved": round(math.log2(max(len(candidates), 1) / max(len(alive), 1)), 2),
    }
    if len(alive) == 1:
        best_candidate = alive[0]
        agree = 0
        checked = 0
        for index in held_out:
            want = truth[index]
            if want is None:
                continue
            got = table["rows"][best_candidate][index]
            checked += 1
            if got is not CRASH and forced._same(got, want):  # noqa: SLF001
                agree += 1
        verdict["survivor_expression"] = candidates[best_candidate]["expression"]
        verdict["survivor_agrees_with_the_reference_on_held_out"] = f"{agree}/{checked}" if checked else "none"
        verdict["stage"] = ("IDENTIFIED_AND_CORRECT" if checked and agree == checked
                            else "IDENTIFIED_BUT_WRONG_ON_HELD_OUT")
    else:
        verdict["stage"] = "NOT_IDENTIFIED"
    return verdict


def measure(root: pathlib.Path, name: str, *, budget: int = 400, probe_count: int = 30,
            seed: int = 3) -> dict[str, Any]:
    started = time.time()
    site_text, lineno = hypotheses.FIXES[name]
    source, candidates = hypotheses.candidates_for(root, name, site_text, lineno, budget=budget)
    if not candidates:
        return {"bug": name, "stage": "NO_CANDIDATES", "seconds": round(time.time() - started, 3)}
    probes = probe_pool(root, name, count=probe_count, seed=seed)
    truth_fn = oracle_for(root, name)
    if truth_fn is None:
        return {"bug": name, "stage": "NO_REFERENCE_PROGRAM", "seconds": round(time.time() - started, 3)}
    truth: list[Any] = []
    kept_probes: list[list[Any]] = []
    for args in probes:
        try:
            value = truth_fn(*json.loads(json.dumps(args)))
        except Exception:  # noqa: BLE001
            continue  # outside the reference's precondition: not a probe
        kept_probes.append(args)
        truth.append(value)
    if not kept_probes:
        return {"bug": name, "stage": "NO_VALID_PROBE", "seconds": round(time.time() - started, 3)}
    table = behaviour_table(candidates, kept_probes, name)
    verdict = identify(name, candidates, kept_probes, truth, table)
    return {"bug": name, "site": site_text, "line": lineno, "candidates": len(candidates),
            "probes": len(kept_probes), "executions": len(candidates) * len(kept_probes),
            **verdict, "seconds": round(time.time() - started, 3)}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quixbugs", type=pathlib.Path, default=pathlib.Path("/tmp/QuixBugs"))
    parser.add_argument("--bugs", nargs="*", default=None)
    parser.add_argument("--budget", type=int, default=400)
    parser.add_argument("--probes", type=int, default=30)
    parser.add_argument("--receipt", type=pathlib.Path, default=None)
    args = parser.parse_args(argv)
    wanted = set(args.bugs) if args.bugs else None
    out = []
    for name in hypotheses.FIXES:
        if wanted and name not in wanted:
            continue
        row = measure(args.quixbugs, name, budget=args.budget, probe_count=args.probes)
        out.append(row)
        print(json.dumps({k: row.get(k) for k in ("bug", "candidates", "probes", "chosen_queries",
                                                  "survivors", "survivor_expression",
                                                  "survivor_agrees_with_the_reference_on_held_out",
                                                  "bits_resolved", "stage", "seconds")}), flush=True)
        for step in row.get("steps", [])[:4]:
            if "probe" in step:
                print("    probe %d %r: %d -> %d" % (step["probe"], step["args"], step["before"],
                                                     step["after"]), flush=True)
    receipt = {"schema": SCHEMA, "authority": AUTHORITY, "upstream": UPSTREAM, "rows": out,
               "date": "2026-11-18"}
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(receipt, indent=2, default=str) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
