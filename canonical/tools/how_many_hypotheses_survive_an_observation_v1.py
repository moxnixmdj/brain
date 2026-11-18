"""How many programs survive one observation?

The thesis under test: give the agent an action, let it experience it once, and it is learned
permanently. "Learned" can only mean: the set of hypotheses consistent with what was observed has
collapsed to one. So the thing to measure is not whether a fix is found -- the enumerator finds fixes
-- but **how many candidates remain consistent after k observations, and whether the correct one is
the smallest of them.**

This is the identifiability mechanism, measured where the project lives. For a bug's fix site, take
the candidates the site's own material can build, run each candidate on the first k corpus cases, and
count how many produce the expected output on all k. k = 1 is the promise the thesis rests on. If a
hundred candidates survive one observation, one observation did not identify anything; it eliminated
some hypotheses and left the choice to a prior. If two survive all of them, the corpus itself does not
identify the fix, and no amount of permanence fixes that.

Reported per k: survivors (consistent candidates), whether the survivors agree with each other on
unseen inputs (a false consensus is still a consensus), and whether the smallest survivor is correct
beyond the corpus. The last number is the one that has been missing from this tree's own accounting:
correct on inputs the corpus never saw.
"""

from __future__ import annotations

import argparse
import json
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
from expressions_from_a_site_v1 import _size  # noqa: E402

SCHEMA = "BRAIN_HOW_MANY_HYPOTHESES_SURVIVE_AN_OBSERVATION_V1"
UPSTREAM = "https://github.com/jkoppel/QuixBugs"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"

FIXES = {
    "lis": ("length + 1", 14),
    "mergesort": ("len(arr) == 0", 17),
    "kth": ("kth(above, k)", 9),
    "get_factors": ("int(n ** 0.5) + 1", 6),
    "next_permutation": ("perm[j] < perm[i]", 6),
    "possible_change": ("total < 0", 8),
}


def candidates_for(root: pathlib.Path, name: str, site_text: str, lineno: int, *,
                   budget: int = 400) -> tuple[str, list[dict[str, Any]]]:
    source = (root / "python_programs" / f"{name}.py").read_text(encoding="utf-8")
    _adapted, sites = forced.instrumented_source(source, name)
    site = next((s for s in sites if s["text"] == site_text and s["lineno"] == lineno), None) \
        or next((s for s in sites if s["text"] == site_text), None)
    if site is None:
        return source, []
    cases = gen.examples_of(root, name)
    failing = []
    for args, expected in cases:
        ran, produced = forced.run_case(source, name, args, forced=None)
        if not (ran and forced.case_passes(produced, expected, None, args)):
            failing.append((args, expected))
    if not failing:
        return source, []
    state = forced.context_at(source, name, failing[0][0], site["lineno"])[0]
    offered = forced.expressions_at(site_text, state, source, name, budget=budget)
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for text, _value in offered:
        if text == site_text or text in seen:
            continue
        seen.add(text)
        patched = _patched(source, name, site, text)
        if patched is None:
            continue
        out.append({"expression": text, "size": _size(text), "site": site, "source": patched})
    out.sort(key=lambda item: (item["size"], len(item["expression"])))
    return source, out


def _patched(source: str, name: str, site: dict[str, Any], expression: str) -> str | None:
    import ast
    tree = ast.parse(source)
    function = next((node for node in tree.body if isinstance(node, ast.FunctionDef)), None)
    if function is None:
        return None
    path = forced._site_path(function, site["lineno"], site["text"])  # noqa: SLF001
    if path is None:
        return None
    try:
        replacement = ast.parse(expression, mode="eval").body
    except SyntaxError:
        return None
    patched = gen.replace_at(function, path, replacement)
    tree.body = [patched if node is function else node for node in tree.body]
    return ast.unparse(tree) + "\n"


def perturbed(args: Sequence[Any], rng: random.Random) -> list[Any] | None:
    """A genuinely new input, derived from a corpus argument.

    The first version of this tool drew its "unseen" probes from the corpus itself, so a candidate
    that satisfies the corpus scored 12/12 "unseen" -- the corpus grading itself, which is the exact
    self-deception this tree keeps having to retract. Inputs are perturbed instead, and the reference
    program is the oracle.
    """
    out: list[Any] = []
    for value in args:
        if isinstance(value, bool):
            out.append(value)
        elif isinstance(value, int):
            out.append(value + rng.choice([-2, -1, 1, 2]))
        elif isinstance(value, list) and all(isinstance(x, int) for x in value) and value:
            style = rng.choice(["shuffle", "sample", "reverse", "scale"])
            if style == "shuffle":
                copy = list(value)
                rng.shuffle(copy)
                out.append(copy)
            elif style == "sample":
                take = rng.randint(1, len(value))
                out.append(rng.sample(value, take))
            elif style == "reverse":
                out.append(list(reversed(value)))
            else:
                out.append([x * rng.choice([1, 2]) for x in value])
        elif isinstance(value, str):
            out.append(value[::-1] if rng.random() < 0.5 else value)
        else:
            return None
    return out


def agreement(item: dict[str, Any], root: pathlib.Path, name: str, *, probes: int = 12,
              seed: int = 1) -> str:
    """How often this candidate agrees with the corpus's reference program on NEW inputs."""
    reference_path = root / "correct_python_programs" / f"{name}.py"
    if not reference_path.exists():
        return "unchecked"
    space: dict[str, Any] = {}
    try:
        exec(compile(reference_path.read_text(encoding="utf-8"), "<ref>", "exec"), space)  # noqa: S102
    except Exception:  # noqa: BLE001
        return "reference_does_not_load"
    truth = space.get(name)
    if truth is None:
        return "no_reference"
    rng = random.Random(seed)
    agree = 0
    checked = 0
    for args, _expected in gen.examples_of(root, name):
        candidate_args = perturbed(args, rng)
        if candidate_args is None:
            continue
        try:
            want = truth(*json.loads(json.dumps(candidate_args)))
        except Exception:  # noqa: BLE001
            continue
        ran, got = forced.run_case(item["source"], name, list(candidate_args), forced=None)
        checked += 1
        if ran:
            try:
                if got == want:
                    agree += 1
            except Exception:  # noqa: BLE001
                pass
        if checked >= probes:
            break
    return f"{agree}/{checked}" if checked else "no_probe"


def measure(root: pathlib.Path, name: str, *, budget: int = 400, max_k: int = 5,
            unseen: int = 12, seed: int = 0) -> dict[str, Any]:
    started = time.time()
    site_text, lineno = FIXES[name]
    source, pool = candidates_for(root, name, site_text, lineno, budget=budget)
    if not pool:
        return {"bug": name, "stage": "NO_CANDIDATES", "seconds": round(time.time() - started, 3)}
    cases = gen.examples_of(root, name)
    failing = []
    for args, expected in cases:
        ran, produced = forced.run_case(source, name, args, forced=None)
        if not (ran and forced.case_passes(produced, expected, None, args)):
            failing.append((args, expected))
    order = failing + [c for c in cases if c not in failing]
    random.Random(seed).shuffle(order)
    rng = random.Random(seed + 1)
    probes: list[list[Any]] = []
    for args, _expected in cases:
        for _ in range(2):
            candidate_args = perturbed(args, rng)
            if candidate_args is not None:
                probes.append(list(candidate_args))
    probes = probes[:unseen]

    def passes(item: dict[str, Any], args: Sequence[Any], expected: Any) -> bool:
        ran, produced = forced.run_case(item["source"], name, list(args), forced=None)
        return ran and forced.case_passes(produced, expected, None, args)

    reference = None
    correct_path = root / "correct_python_programs" / f"{name}.py"
    if correct_path.exists():
        reference = correct_path.read_text(encoding="utf-8")

    steps: list[dict[str, Any]] = []
    survivors = list(pool)
    for k in range(1, min(len(order), max_k) + 1):
        args, expected = order[k - 1]
        survivors = [item for item in survivors if passes(item, args, expected)]
        step: dict[str, Any] = {"k": k, "survivors": len(survivors)}
        if survivors:
            best = survivors[0]
            step["smallest"] = best["expression"]
            step["smallest_size"] = best["size"]
            agreements = 0
            checked = 0
            if reference is not None:
                reference_ns: dict[str, Any] = {}
                try:
                    exec(compile(reference, "<ref>", "exec"), reference_ns)  # noqa: S102
                except Exception:  # noqa: BLE001
                    reference_ns = {}
                truth = reference_ns.get(name)
                if truth is not None:
                    for probe_args in probes:
                        checked += 1
                        try:
                            want = truth(*json.loads(json.dumps(probe_args)))
                        except Exception:  # noqa: BLE001
                            continue
                        ran, got = forced.run_case(best["source"], name, list(probe_args), forced=None)
                        if ran:
                            try:
                                if got == want or list(got) == list(want):
                                    agreements += 1
                            except Exception:  # noqa: BLE001
                                pass
            step["smallest_correct_on_unseen"] = f"{agreements}/{checked}" if checked else "unchecked"
        steps.append(step)
        if not survivors:
            break
    return {"bug": name, "site": site_text, "line": lineno, "candidates": len(pool),
            "failing_cases_in_corpus": len(failing), "corpus_cases": len(cases),
            "steps": steps, "seconds": round(time.time() - started, 3)}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quixbugs", type=pathlib.Path, default=pathlib.Path("/tmp/QuixBugs"))
    parser.add_argument("--bugs", nargs="*", default=None)
    parser.add_argument("--budget", type=int, default=400)
    parser.add_argument("--max-k", type=int, default=5)
    parser.add_argument("--receipt", type=pathlib.Path, default=None)
    args = parser.parse_args(argv)
    wanted = set(args.bugs) if args.bugs else None
    rows = []
    for name in FIXES:
        if wanted and name not in wanted:
            continue
        row = measure(args.quixbugs, name, budget=args.budget, max_k=args.max_k)
        rows.append(row)
        print(json.dumps({k: row.get(k) for k in ("bug", "candidates", "corpus_cases",
                                                  "failing_cases_in_corpus", "seconds")}), flush=True)
        for step in row.get("steps", []):
            print("    k=%d survivors=%-4d smallest=%-40r size=%-2s unseen=%s" %
                  (step["k"], step["survivors"], step.get("smallest"), step.get("smallest_size"),
                   step.get("smallest_correct_on_unseen")), flush=True)
    receipt = {"schema": SCHEMA, "authority": AUTHORITY, "upstream": UPSTREAM, "rows": rows,
               "date": "2026-11-18"}
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(receipt, indent=2, default=str) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
