#!/usr/bin/env python3
"""Generalization loop probe: one showing + settlement reaches 4/4; without settlement, 1/4.

Measures the three arms on the same 4-site corpus (`== None` defect, 4 shapes the
learner never saw):

  A. raw literal (`edit_by_example` alone)          -> 1/4 edited, 3/4 refused
  B. loop + oracle (wider computed, settled)        -> 4/4 edited
  C. loop, no oracle (fail closed)                  -> 1/4 admitted, 3/4 REFUSE_UNSETTLED

Plus the over-generalization arm: a target where wider is wrong (`pairs` must stay
`*2`); the loop must refuse it when the oracle says so.

Authority NONE. Runs the shipped learner in-process. $0, zero model dependency.
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

from canonical.swe_kernel.taught_actions import edit_by_example_v1 as learner
from canonical.swe_kernel.taught_actions.generalization_loop_v1 import settle_generalization

BEFORE = "def unpaid(product):\n    return product == None\n"
AFTER = "def unpaid(product):\n    return product is None\n"

TARGETS: dict[str, str] = {
    "the_same_name": "def f(product):\n    return product == None\n",
    "an_attribute": "def f(invoice):\n    return invoice.paid == None\n",
    "a_call_result": "def f(g):\n    return g() == None\n",
    "a_local": "def f(x):\n    return x == None\n",
}


def _oracle_is_none(target: str, edited: str) -> bool:
    return "is None" in edited and "== None" not in edited


def _raw_literal(target: str) -> bool:
    try:
        learner.repeated(learner.learn(BEFORE, AFTER), target, "the example")
        return True
    except learner.Refused:
        return False


def run() -> dict[str, Any]:
    raw = {name: _raw_literal(t) for name, t in TARGETS.items()}
    loop_oracle = {}
    loop_no_oracle = {}
    for name, target in TARGETS.items():
        r = settle_generalization(BEFORE, AFTER, target, oracle=_oracle_is_none)
        loop_oracle[name] = {"action": r["action"], "edited": r["edited_text"] is not None}
        r2 = settle_generalization(BEFORE, AFTER, target, oracle=None)
        loop_no_oracle[name] = {"action": r2["action"], "edited": r2["edited_text"] is not None}

    # Over-generalization arm
    over = settle_generalization(
        "def f(a):\n    return a * 2\n",
        "def f(a):\n    return a * 3\n",
        "def pairs(n):\n    return n * 2\n",
        oracle=lambda t, e: "* 2" in e,
    )

    return {
        "probe": "generalization_loop",
        "authority": "NONE",
        "executed": True,
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
        "raw_literal": raw,
        "loop_with_oracle": loop_oracle,
        "loop_without_oracle": loop_no_oracle,
        "over_generalization": {"action": over["action"], "edited": over["edited_text"] is not None},
        "summary": {
            "sites": len(TARGETS),
            "raw_literal_edited": sum(1 for v in raw.values() if v),
            "loop_oracle_edited": sum(1 for v in loop_oracle.values() if v["edited"]),
            "loop_no_oracle_admitted": sum(1 for v in loop_no_oracle.values() if v["edited"]),
            "loop_no_oracle_refused_unsettled": sum(
                1 for v in loop_no_oracle.values() if v["action"] == "REFUSE_UNSETTLED"),
            "over_generalization_refused": over["edited_text"] is None,
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
    args = parser.parse_args(argv)
    report = run()
    if args.json:
        args.json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    s = report["summary"]
    print("Generalization loop: one showing, settled")
    print("=" * 72)
    print(f"  sites (unseen shapes of one defect)              {s['sites']:>4}")
    print(f"  raw literal edited                               {s['raw_literal_edited']:>4}")
    print(f"  loop + oracle edited                             {s['loop_oracle_edited']:>4}")
    print(f"  loop, no oracle: admitted                        {s['loop_no_oracle_admitted']:>4}")
    print(f"  loop, no oracle: refused unsettled               {s['loop_no_oracle_refused_unsettled']:>4}")
    print(f"  over-generalization refused                      {str(s['over_generalization_refused']):>4}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
