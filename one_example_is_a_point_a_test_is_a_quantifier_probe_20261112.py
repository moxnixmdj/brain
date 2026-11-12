#!/usr/bin/env python3
"""One example is a point; a test is a quantifier. Count the programs each admits.

The claim under test is that an agent can be shown an action once and keep it. For a *binding* that
is true and round 8 measured it. For a *program* it cannot be true, and the reason is arithmetic
rather than philosophical: a demonstration constrains one input, a test constrains a domain, and the
number of programs consistent with each is different by an order of magnitude.

This probe counts them, using the repository's own candidate generator — the same
`_candidate_specs`/`_CandidateRenderer` pair that `python.patch.search.test_guided.ast.v1` searches
with, so the space being counted is the space the repair loop actually searches.

A wrong `grade()` is enumerated into every single-mutation candidate. Each candidate is then asked
two questions:

  * does it agree with **one demonstration**, ``grade(95) == "A"``?
  * does it agree with **three assertions**, including the boundary at 90?

The first question is what "experience it once" gives you. The second is what a test gives you.

Authority NONE. In-process, no subprocess, no writes, no repository state touched, $0, zero model.
"""
from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import pathlib
import sys
from typing import Any, Callable

REPO_ROOT = pathlib.Path(__file__).resolve().parent
GENERATOR = REPO_ROOT / "canonical" / "runtime" / "bound_capabilities" / "python_test_guided_patch_search_v1.py"

#: The wrong program. `>` should be `>=` for the stated intent, and the boundary at 90 is where the
#: difference lives — one point away from where a lazy demonstration would land.
SOURCE = '''def grade(score):
    if score > 90:
        return "A"
    elif score > 80:
        return "B"
    return "C"
'''

#: One demonstration: a single call and its answer. This is the most a single experience can give.
DEMONSTRATION = ((95,), "A")

#: Three assertions: the demonstration, the boundary that separates the candidates, and one ordinary
#: case. This is what a test is — a statement about a domain, not a point.
SUITE = (
    ((95,), "A"),
    ((90,), "A"),
    ((70,), "C"),
)

#: The literals the generator is allowed to substitute. Real search passes the test corpus's own
#: literals; here they are the boundaries the domain actually has.
LITERALS = [90, 80]


class Candidate(str):
    """A candidate program, callable, evaluated in its own namespace."""


def _generator():
    spec = importlib.util.spec_from_file_location("_patch_search_for_probe", str(GENERATOR))
    if spec is None or spec.loader is None:  # pragma: no cover
        raise ImportError(str(GENERATOR))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _caller(text: str) -> Callable[..., Any]:
    namespace: dict[str, Any] = {}
    exec(compile(text, "<candidate>", "exec"), namespace)  # noqa: S102 - generated in-process
    grade = namespace["grade"]

    def call(args: tuple) -> Any:
        try:
            return grade(*args)
        except Exception:
            return "<raised>"

    return call


def candidates() -> list[tuple[dict[str, Any], str]]:
    """Every single-mutation candidate the shipped generator produces, rendered to source."""
    generator = _generator()
    tree = ast.parse(SOURCE)
    renderer = generator._CandidateRenderer(SOURCE, tree)
    found: list[tuple[dict[str, Any], str]] = []
    for key, descriptor, replacer in generator._candidate_specs(tree, LITERALS, [], None):
        text = renderer.render(key, replacer)
        if text and text != SOURCE:
            found.append((descriptor, text))
    return found


def run() -> dict[str, Any]:
    rows = []
    for descriptor, text in candidates():
        call = _caller(text)
        meets_demonstration = call(DEMONSTRATION[0]) == DEMONSTRATION[1]
        meets_suite = all(call(args) == expected for args, expected in SUITE)
        rows.append({
            "kind": descriptor.get("kind"),
            "detail": descriptor.get("detail"),
            "family": descriptor.get("family"),
            "consistent_with_one_demonstration": meets_demonstration,
            "consistent_with_the_suite": meets_suite,
            "demonstration_only": meets_demonstration and not meets_suite,
            "source": text,
        })

    demo_only = [r for r in rows if r["demonstration_only"]]
    both = [r for r in rows if r["consistent_with_one_demonstration"] and r["consistent_with_the_suite"]]
    suite_only = [r for r in rows if r["consistent_with_the_suite"] and not r["consistent_with_one_demonstration"]]
    total = len(rows)
    return {
        "probe": "one_example_is_a_point_a_test_is_a_quantifier",
        "authority": "NONE",
        "executed": True,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
        "generator": str(GENERATOR.relative_to(REPO_ROOT)),
        "source": SOURCE,
        "demonstration": {"call": "grade(95)", "answer": "A"},
        "suite": [{"call": f"grade({args[0]})", "answer": expected} for args, expected in SUITE],
        "records": rows,
        "summary": {
            "candidates": total,
            "consistent_with_one_demonstration": sum(
                1 for r in rows if r["consistent_with_one_demonstration"]
            ),
            "consistent_with_the_suite": sum(1 for r in rows if r["consistent_with_the_suite"]),
            "both": len(both),
            "demonstration_only_that_is_wrong": len(demo_only),
            "suite_only": len(suite_only),
            "pruned_by_the_demonstration": total - sum(
                1 for r in rows if r["consistent_with_one_demonstration"]
            ),
            "pruned_by_the_suite": total - sum(1 for r in rows if r["consistent_with_the_suite"]),
        },
        "hard_nonclaims": [
            "ONE_TARGET_ONE_GENERATOR_ONE_FIXTURE",
            "NO_CAPABILITY_REGISTERED",
            "NO_ACCEPTANCE_CREDIT",
            "NO_TRUTH_ACHIEVED",
            "COUNTS_SINGLE_MUTATION_CANDIDATES_ONLY",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=pathlib.Path, default=None)
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args(argv)

    report = run()
    if args.json:
        args.json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    s = report["summary"]

    print("One demonstration, three assertions, and the programs each admits")
    print("=" * 72)
    print(f"  candidate programs generated from the shipped mutation families  {s['candidates']:>4}")
    print(f"  consistent with ONE demonstration  grade(95) == 'A'              "
          f"{s['consistent_with_one_demonstration']:>4}")
    print(f"  consistent with the three assertions                             "
          f"{s['consistent_with_the_suite']:>4}")
    print(f"  ...of which also match the demonstration                         {s['both']:>4}")
    print(f"  consistent with the demonstration and WRONG on the suite         "
          f"{s['demonstration_only_that_is_wrong']:>4}")
    print(f"  pruned by one demonstration                                      "
          f"{s['pruned_by_the_demonstration']:>4}")
    print(f"  pruned by the suite                                              "
          f"{s['pruned_by_the_suite']:>4}")

    if args.list:
        print("\n  the ones a single demonstration would have kept:")
        for row in report["records"]:
            if row["demonstration_only"]:
                print(f"    {str(row['kind']):<20}{str(row['detail'])[:44]:<46}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
