"""Is the fix even in the pool? A completeness witness for any claim of insufficiency.

THE CORRECTION THIS EXISTS TO MAKE
----------------------------------
`THE_FAILURE_ALREADY_SAYS_WHAT_TO_WRITE_20261118_V1` reported that `lis`, `next_permutation` and
`possible_change` are "not fixed by any expression the site's own material can build". That sentence
was false, and the published corpus says so plainly:

    lis               longest = length + 1        ->  longest = max(longest, length + 1)
    next_permutation  if perm[j] < perm[i]:       ->  if perm[i] < perm[j]:
    possible_change   if total < 0:               ->  if total < 0 or not coins:

Every one is a single expression over names and operators that are already at the site. The wall was
the enumerator: it admitted only terms whose *text* was <= 3 characters, so a local called `length`
could be tested alone and never combined, and it replaced its pool with each level's output, so an
atom could never be combined with a composite.

THE RULE THIS FILE ESTABLISHES
------------------------------
An insufficiency claim is a claim about the WORLD; a failure to find something is a claim about my
CODE. They are not the same statement, and the earlier receipt published the second as the first.
So from now on, before anything in this tree may say "the site cannot build it", it has to show a
*completeness witness*: the published fix, fed to the same enumerator, appears in what the enumerator
offers. If it does not appear, the honest verdict is UNRESOLVED WITHIN THE CAP, not IMPOSSIBLE.

What it measures per bug:

    rank_of_the_published_fix       where the published expression sits in the offered order
    offered                          whether it is offered at all, under a wall-clock cap
    candidates_offered               how many candidates that took

Nothing here is a repair, nothing runs the corpus's own pytest, and no claim of a solved bug is made.

INTEGRITY: the published fix is read here only to compute the value it would produce, i.e. to measure
reachability. It never enters a repair, never enters a search, and this file claims no solved bug. The
corpus's own pytest is not consulted at all.
"""
from __future__ import annotations

import argparse
import ast
import json
import pathlib
import sys
import time
from typing import Any, Sequence

TOOLS = pathlib.Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
for path in (str(TOOLS), str(REPO)):
    if path not in sys.path:
        sys.path.insert(0, path)

import force_the_value_and_see_v1 as forced  # noqa: E402
import grammar_closed_repair_v1 as gen  # noqa: E402

SCHEMA = "BRAIN_IS_THE_FIX_EVEN_IN_THE_POOL_V1"
UPSTREAM = "https://github.com/jkoppel/QuixBugs"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"
THE_FIX_IS_IN_THE_POOL = "THE_FIX_IS_IN_THE_POOL"
UNRESOLVED = "NOT_OFFERED_WITHIN_THE_CAP__NOT_A_CLAIM_OF_IMPOSSIBILITY"

# site text (as the instrument names it) -> the published fix's expression at that same site
FIXES = {
    "lis": ("length + 1", "max(longest, length + 1)"),
    "next_permutation": ("perm[j] < perm[i]", "perm[i] < perm[j]"),
    "possible_change": ("total < 0", "total < 0 or not coins"),
}


def _sites(source: str, name: str) -> list[dict[str, Any]]:
    return forced.instrumented_source(source, name)[1]


def measure(root: pathlib.Path, name: str, site_text: str, fix_expression: str,
            budget: int, seconds: float) -> dict[str, Any]:
    started = time.time()
    source = (root / "python_programs" / f"{name}.py").read_text()
    cases = gen.examples_of(root, name)
    row: dict[str, Any] = {"task": name, "site": site_text, "published_fix_expression": fix_expression,
                           "cases": len(cases)}
    if not cases:
        row["stage"] = "NO_PUBLISHED_CASES"
        return row
    failing = None
    for args, expected in cases:
        ran, value = forced.run_case(source, name, args, forced=None)
        if not ran or not forced.case_passes(value, expected, None, args):
            failing = (args, expected)
            break
    if failing is None:
        row["stage"] = "NO_FAILING_CASE"
        return row
    args, _expected = failing
    site = next((s for s in _sites(source, name) if s["text"] == site_text), None)
    if site is None:
        row["stage"] = "SITE_NOT_FOUND"
        return row
    contexts = forced.context_at(source, name, args, site["lineno"])
    if not contexts:
        row["stage"] = "SITE_NEVER_RAN"
        return row
    state = contexts[0] if len(contexts) > 4 else contexts[-1]
    row["contexts_observed"] = len(contexts)

    # A value that coincides in ONE observed state is not the goal -- measured here the hard way: a
    # constant matched a demanded value on a site that ran once and failed the corpus. So this file
    # reports a witness (is the expression offered), never a value match.
    offered = forced.expressions_at(site_text, state, source, name, budget=budget,
                                    deadline=time.time() + seconds)
    row["candidates_offered"] = len(offered)
    row["rank_of_the_published_fix"] = next(
        (index for index, (text, _value) in enumerate(offered)
         if _same_expression(text, fix_expression)), None)
    row["seconds_spent"] = round(time.time() - started, 2)
    row["stage"] = (THE_FIX_IS_IN_THE_POOL if row["rank_of_the_published_fix"] is not None
                    else UNRESOLVED)
    return row


def _same_expression(left: str, right: str) -> bool:
    """Same expression, not same spelling: parentheses and spacing are not meaning."""
    def normalise(text: str) -> str:
        try:
            return ast.dump(ast.parse(text, mode="eval").body)
        except SyntaxError:
            return text
    return normalise(left) == normalise(right) or left.replace(" ", "") == right.replace(" ", "")


def summarise(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    measured = [row for row in rows if "candidates_offered" in row]
    return {
        "tasks": [row["task"] for row in rows],
        "measured": len(measured),
        "the_fix_is_in_the_pool": {row["task"]: row["rank_of_the_published_fix"] is not None
                                   for row in measured},
        "rank_of_the_published_fix": {row["task"]: row["rank_of_the_published_fix"] for row in measured},
        "seconds_spent": {row["task"]: row["seconds_spent"] for row in measured},
        "candidates_offered_per_site": {row["task"]: row["candidates_offered"] for row in measured},
        "reading": ("A fix that is offered is a completeness witness for that site: the pool can build it, so "
                    "any earlier 'not expressible' verdict about this site was a claim about the code. A fix "
                    "that is not offered within the cap is unresolved, not impossible."),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--quixbugs", type=pathlib.Path, default=pathlib.Path("/tmp/QuixBugs"))
    parser.add_argument("--receipt", type=pathlib.Path, default=None)
    parser.add_argument("--budget", type=int, default=6000)
    parser.add_argument("--seconds-per-site", type=float, default=20.0)
    args = parser.parse_args(argv)
    root = args.quixbugs
    rows = [measure(root, name, site, fix, args.budget, args.seconds_per_site)
            for name, (site, fix) in FIXES.items()]
    result = {"schema": SCHEMA, "authority": AUTHORITY, "upstream": UPSTREAM,
              "corpus_commit": subprocess_commit(root),
              "tool": "canonical/tools/is_the_fix_even_in_the_pool_v1.py",
              "model_dependency_count": 0, "external_capability_provider_count": 0,
              "network_calls_at_run_time": 0,
              "the_published_fix_is_used_only_to_measure_reachability": True,
              "rows": rows, "summary": summarise(rows)}
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(result, indent=1, default=str) + "\n")
    print(json.dumps(result["summary"], indent=1, default=str))
    return 0


def subprocess_commit(root: pathlib.Path) -> str | None:
    if not (root / ".git").exists():
        return None
    import subprocess
    return subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                          capture_output=True, text=True).stdout.strip()


if __name__ == "__main__":
    raise SystemExit(main())
