#!/usr/bin/env python3
"""One showing is literal; two showings are general; a new kind of edit is never learned by showing.

The owner's question, asked on the surface he cares about: can an agent be shown a code change once
and then make it everywhere, permanently? The tree already answers it, in
`canonical/swe_kernel/taught_actions/edit_by_example_v1.py` — a change is worked out from examples as
rewrite rules and repeated on another file. This probe runs that learner and counts what one showing
buys.

Three arms, each measured rather than argued:

  A. **generalisation** — the same change appears in four files the learner never saw, at four
     different shapes (`product == None`, `invoice.paid == None`, `g() == None`, `x == None`). How
     many does one showing reach? How many does a second showing reach?
  B. **safety** — the target also contains a call used a way no example showed
     (``yaml.load(h, Loader=...)``). A rule learned from one showing would rewrite it and break it.
     What happens?
  C. **ceiling** — a change that adds a statement. The learner's own words: only a change inside one
     expression or one simple statement is learned.

Authority NONE. Runs the shipped learner in-process on synthetic source. Writes no file, starts no
process, $0, zero model dependency.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any

REPO_ROOT = pathlib.Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from canonical.swe_kernel.taught_actions import edit_by_example_v1 as learner  # noqa: E402

#: The first showing: one place, one name.
SHOWN_ONCE = (
    "def unpaid(product):\n    return product == None\n",
    "def unpaid(product):\n    return product is None\n",
)

#: The second showing: a different place, which is what turns a rule about `product` into a rule
#: about anything.
SHOWN_AGAIN = (
    "def open_orders(order):\n    return [order.total == None, order.total == 0]\n",
    "def open_orders(order):\n    return [order.total is None, order.total == 0]\n",
)

#: Four files the learner never saw. Only the first has the shape the single example showed.
TARGETS: dict[str, str] = {
    "the_same_name": "def f(product):\n    return product == None\n",
    "an_attribute": "def f(invoice):\n    return invoice.paid == None\n",
    "a_call_result": "def f(g):\n    return g() == None\n",
    "a_local": "def f(x):\n    return x == None\n",
}

#: One showing, and the same change shown a second time at a place that also leaves a `Loader=` call
#: alone — the exact regression the module's own notes record on real commits.
YAML_ONCE = (
    "import yaml\n\n\ndef read(stream):\n    return yaml.load(stream)\n",
    "import yaml\n\n\ndef read(stream):\n    return yaml.safe_load(stream)\n",
)
YAML_TWICE = (
    "import yaml\n\n\ndef plain(a):\n    return yaml.load(a)\n\n\n"
    "def trusted(c):\n    return yaml.load(c, Loader=yaml.FullLoader)\n",
    "import yaml\n\n\ndef plain(a):\n    return yaml.safe_load(a)\n\n\n"
    "def trusted(c):\n    return yaml.load(c, Loader=yaml.FullLoader)\n",
)
#: A file with a plain call and a call used a way no example showed.
YAML_TARGET = (
    "import yaml\n\n\ndef settings(h):\n    return yaml.load(h)\n\n\n"
    "def theirs(h):\n    return yaml.load(h, Loader=yaml.FullLoader)\n"
)

#: A structural change: a statement is added. Not a change "inside one expression".
STRUCTURAL = ("def f(a):\n    return a\n", "def f(a):\n    b = a\n    return b\n")


def _rules(examples: list[tuple[str, str]]) -> list[str]:
    return [str(rule) for rule in learner.learn_all(list(examples))]


def _apply(examples: list[tuple[str, str]], target: str, leave_unshown: bool = False) -> dict[str, Any]:
    try:
        return {"edited": True, "text": learner.repeated(
            learner.learn_all(list(examples)), target, "the examples", leave_unshown=leave_unshown)}
    except learner.Refused as exc:
        return {"edited": False, "reason": str(exc)}


def run() -> dict[str, Any]:
    once = [SHOWN_ONCE]
    twice = [SHOWN_ONCE, SHOWN_AGAIN]

    generalisation = []
    for name, target in TARGETS.items():
        one = _apply(once, target)
        two = _apply(twice, target)
        generalisation.append({
            "target": name,
            "edited_after_one_showing": one["edited"],
            "refusal_after_one_showing": one.get("reason"),
            "edited_after_two_showings": two["edited"],
        })

    safety = {
        "rules_from_one_showing": _rules([YAML_ONCE]),
        "rules_from_two_showings": _rules([YAML_ONCE, YAML_TWICE]),
        "one_showing": _apply([YAML_ONCE], YAML_TARGET),
        "one_showing_leave_unshown": _apply([YAML_ONCE], YAML_TARGET, leave_unshown=True),
        "two_showings": _apply([YAML_ONCE, YAML_TWICE], YAML_TARGET),
    }

    try:
        learner.learn_all([STRUCTURAL])
        ceiling = {"learned": True, "reason": None}
    except learner.Refused as exc:
        ceiling = {"learned": False, "reason": str(exc)}

    return {
        "probe": "one_showing_is_literal_two_showings_are_general",
        "authority": "NONE",
        "executed": True,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
        "learner": "canonical/swe_kernel/taught_actions/edit_by_example_v1.py",
        "rules": {"after_one_showing": _rules(once), "after_two_showings": _rules(twice)},
        "generalisation": generalisation,
        "safety": safety,
        "ceiling": ceiling,
        "summary": {
            "unseen_sites": len(TARGETS),
            "edited_after_one_showing": sum(1 for row in generalisation
                                            if row["edited_after_one_showing"]),
            "refused_after_one_showing": sum(1 for row in generalisation
                                             if not row["edited_after_one_showing"]),
            "edited_after_two_showings": sum(1 for row in generalisation
                                             if row["edited_after_two_showings"]),
            "one_showing_would_break_the_unshown_call": not safety["one_showing"]["edited"],
            "two_showings_leave_the_unshown_call_alone": safety["two_showings"]["edited"],
            "structural_change_learned": ceiling["learned"],
        },
        "hard_nonclaims": [
            "ONE_FAMILY_OF_EDIT_SYNTHETIC_CORPUS",
            "NO_CAPABILITY_REGISTERED",
            "NO_BENCHMARK_OR_ACCEPTANCE_CREDIT",
            "NO_TRUTH_ACHIEVED",
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

    print("One showing, two showings, and what each buys")
    print("=" * 72)
    print(f"  rule from ONE showing   {report['rules']['after_one_showing']}")
    print(f"  rule from TWO showings  {report['rules']['after_two_showings']}")
    print(f"  unseen sites of the same defect                        {s['unseen_sites']:>4}")
    print(f"  edited after ONE showing                               "
          f"{s['edited_after_one_showing']:>4}")
    print(f"  refused after ONE showing, naming the form             "
          f"{s['refused_after_one_showing']:>4}")
    print(f"  edited after TWO showings                              "
          f"{s['edited_after_two_showings']:>4}")
    print(f"  a use no example showed is refused, not rewritten      "
          f"{str(s['one_showing_would_break_the_unshown_call']):>4}")
    print(f"  a second showing settles it without being asked        "
          f"{str(s['two_showings_leave_the_unshown_call_alone']):>4}")
    print(f"  a structural change is learned by showing              "
          f"{str(s['structural_change_learned']):>4}")

    if args.list:
        print()
        for row in report["generalisation"]:
            mark = "edited" if row["edited_after_one_showing"] else "refused"
            print(f"    one showing: {mark:<8}{row['target']:<16}"
                  f"two showings: {'edited' if row['edited_after_two_showings'] else 'refused'}")
        print(f"\n    ceiling: {report['ceiling']['reason']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
