"""A failure is worth 2^k, where k is what it KEPT -- not how big it was.

THE GAP THIS CLOSES
-------------------
`THE_LEARNER_DECIDES_PAST_THE_ENUMERATION_WALL_20261116_V1.md` shipped the arithmetic repair for
counting survivors past the enumeration cap (inclusion-extraction, exact against brute force) and
recorded its own real-corpus measurement:

    vocab 31, |A| = 23, m = 2 failures, D_i = [20, 20], raw survivors 8,388,600 = 2^23 - 8

That receipt is correct and this module does not re-derive it. What it never asked is the next
question, and the receipt's own numbers answer it:

    2^23 - 8  means exactly 8 hypotheses were killed.
    Two failures, each killing 8, would kill 15 if distinct and 8 if identical.
    The observed 8 therefore requires the two failures to be THE SAME FAILURE RECORDED TWICE.

Verified against the live counter, not by algebra alone:

    23 candidates, 2 failures, SAME triple dropped twice  -> 8,388,600 survivors  (== the receipt)
    23 candidates, 2 failures, TWO DISTINCT triples       -> 8,388,593 survivors

So the second failure bought 7 hypotheses out of 8,388,608. The corpus produced two failures and
the learner gained almost nothing from the second, because it was the same evidence.

THE LAW, AND WHY IT IS COUNTERINTUITIVE
---------------------------------------
A survivor is a subset C of A that hits every D_i = A \\ F_i. C fails to hit D_i only when C is a
subset of (A \\ D_i) = F_i, i.e. C is built entirely from the facts the failure KEPT. So:

    one failure eliminates exactly 2^|F_i ∩ A| hypotheses

where |F_i ∩ A| counts only the shared candidates that failure kept -- a fact outside A cannot be
in a survivor, so keeping it does not shrink the count, but dropping it does not help either.

The consequence inverts the natural instinct. A DRAMATIC failure keeps few of A's facts and kills
almost nothing. A NEAR MISS keeps most of A's facts and kills a large fraction:

    |A| = 23, failure drops 3 of them (keeps 20)  ->  kills 8        0.0001% of the space
    |A| = 23, failure drops 20 of them (keeps 3)  ->  kills 1,048,576  12.5% of the space

**The most informative failure is the nearest miss, not the biggest failure.** An agent that
learns from its failures is therefore not served by failing more or failing harder; it is served by
failing as CLOSE to success as possible while differing on one candidate fact.

WHAT THIS MAKES OBVIOUS THAT WAS NOT
------------------------------------
`contrast_selection_v1` already chose states by how evenly they split the survivors, and that is
right. This says the same thing from the failure side and adds the quantity: a contrast's worth is
2^k with k = what the failure keeps, so a contrast that drops one fact is worth 2^22 times one that
drops 20. Both instruments agree; only this one prices the failure directly, which is what a
redesign of the observable budget needs.

Authority: NONE. Pure computation over the existing `count_survivors`. Executes no capability,
claims no credit, spends $0, depends on no model.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, "/home/user/brain")
from canonical.runtime import applicability_v1 as A  # noqa: E402

UNIVERSE_SIZE = 23  # the receipt's own |A|


def universe(n: int = UNIVERSE_SIZE) -> frozenset[str]:
    return frozenset(f"lit{i}" for i in range(n))


def killed_by_one_failure(universe_facts: frozenset[str], kept_fraction: int) -> dict[str, int]:
    """How many hypotheses ONE failure eliminates, given how many of A's facts it kept."""
    kept = sorted(universe_facts)[:kept_fraction]
    survivors = A.count_survivors(universe_facts, [universe_facts - frozenset(kept)])
    total = 2 ** len(universe_facts)
    return {"kept": kept_fraction, "dropped": len(universe_facts) - kept_fraction,
            "survivors": survivors, "killed": total - survivors, "total": total}


def two_failure_comparison(universe_facts: frozenset[str]) -> dict[str, object]:
    """The receipt's own shape: two failures, identical or distinct, at the same size."""
    total = 2 ** len(universe_facts)
    facts = sorted(universe_facts)
    same = [set(facts[:3]), set(facts[:3])]
    distinct = [set(facts[:3]), set(facts[3:6])]
    same_survivors = A.count_survivors(universe_facts, [universe_facts - frozenset(d) for d in same])
    distinct_survivors = A.count_survivors(
        universe_facts, [universe_facts - frozenset(d) for d in distinct]
    )
    return {
        "total_hypotheses": total,
        "same_failure_twice": {"survivors": same_survivors, "killed": total - same_survivors},
        "two_distinct_failures": {"survivors": distinct_survivors,
                                  "killed": total - distinct_survivors},
        "second_failure_bought": (total - distinct_survivors) - (total - same_survivors),
        "receipt_shape_2_pow_23_minus_8": same_survivors == total - 8,
        "reading": ("the receipt recorded 2^23 - 8, which is only possible if both failures omitted "
                    "the SAME three candidates: the corpus produced one failure twice"),
    }


def swing(universe_facts: frozenset[str]) -> list[dict[str, int]]:
    """Every kept-count from 1 to |A|-1, so the shape of the law is one table."""
    return [killed_by_one_failure(universe_facts, k) for k in range(1, len(universe_facts))]


def main() -> int:
    facts = universe()
    result = {
        "schema": "A_FAILURE_IS_WORTH_TWO_TO_THE_KEYS_KEPT_V1",
        "authority": "NONE__PRODUCER_RUN_COMPUTATION_OVER_EXISTING_COUNTER",
        "kind": "receipt",
        "incremental_spend_usd": 0,
        "producer_cognition_model_dependency_count": 0,
        "law": "one failure eliminates exactly 2^|F_i cap A| hypotheses, where that is the number of "
               "shared candidates the failure KEPT",
        "universe": len(facts),
        "swing": swing(facts),
        "two_failure_comparison": two_failure_comparison(facts),
        "consequence": ("the most informative failure is the NEAREST MISS, not the biggest failure: "
                        "a failure that drops one fact kills 2^(n-1) hypotheses and one that drops "
                        "twenty kills 2^3"),
    }
    text = json.dumps(result, indent=1, sort_keys=True)
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(text + "\n")
        print("written", sys.argv[1])
    print(f"{'kept':>5s} {'dropped':>8s} {'killed':>14s} {'share of space':>15s}")
    total = 2 ** len(facts)
    for row in result["swing"]:
        if row["kept"] in (1, 2, 3, 5, 10, 20):
            print(f"{row['kept']:>5d} {row['dropped']:>8d} {row['killed']:>14,} "
                  f"{row['killed'] / total * 100:>14.4f}%")
    cmp = result["two_failure_comparison"]
    print()
    print("same failure twice :", f"{cmp['same_failure_twice']['killed']:,}", "killed")
    print("two distinct       :", f"{cmp['two_distinct_failures']['killed']:,}", "killed")
    print("second failure bought:", cmp["second_failure_bought"], "hypotheses")
    print("receipt (2^23-8) reproduced:", cmp["receipt_shape_2_pow_23_minus_8"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
