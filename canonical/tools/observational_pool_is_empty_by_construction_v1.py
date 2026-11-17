"""What the observational pool costs: the price of never inventing a world.

THE QUESTION, FROM FIRST PRINCIPLES
-----------------------------------
`contrast_selection_v1` selects optimally *within a pool it refuses to leave*:

    "the candidate pool here is ONLY states that have actually been observed, plus the state the
     caller is in right now. This module never invents a world."

That refusal is principled and it cites the measured reason (EIG proposing queries outside the
generator's support, arXiv 2602.06818). But it has a consequence nobody has priced: **if the pool
does not CONTAIN a useful contrast, selecting optimally from it is still worthless.** The receipt
`THE_LEARNER_DECIDES_PAST_THE_ENUMERATION_WALL_20261116_V1.md` hit exactly this and recorded it:

    "Selector on the same evidence | NO_INFORMATIVE_STATE with survivors_before = 8,388,600 --
     every state already observed gives every survivor the same answer (exact, not sampled)"

Zero. On a real corpus. Not because the selector was wrong, but because the pool was empty of
anything that discriminates.

WHY THE POOL IS EMPTY, WHICH IS THE POINT
-----------------------------------------
`A_FAILURE_IS_WORTH_TWO_TO_THE_KEYS_KEPT` established that one failure eliminates exactly
2^|F_i cap A| hypotheses, where that is the number of shared candidates the failure KEPT. So:

    a DRAMATIC failure (keeps few of A)      eliminates ~nothing
    a NEAR MISS (keeps almost all of A)      eliminates half the space

Real failures are dramatic. `count_survivors` counts `|{C subset A : C hits every exclusion}|`, so
a failure row `D_i` is the set of facts that failure DROPPED, and it kept `n - |D_i|` of them. The
tree's real corpus recorded `D_i = [20, 20]` over `|A| = 23`: **each failure dropped 20 of 23 and
kept 3.** A kept-3 failure eliminates 2^3 = 8 hypotheses. The whole corpus -- two failures -- was
worth 8. That is the observational pool: not badly ranked, badly POPULATED.

This module carries the correction of its own correction. A first draft said "dramatic"; a second
draft misread `D_i` as the KEPT set, concluded the corpus had already been interventional, and
reported a 4x advantage. The live counter refutes that: `count_survivors(A, [D1, D2])` with
`|D_i| = 20` returns 8,388,600 = `2^23 - 8`, exactly as the receipt says. Dropping is what is
counted. 8, not 1,048,576.

WHAT AN INTERVENTION WOULD BUY, AND WHAT IT WOULD COST
------------------------------------------------------
The fix is not a better ranking over the same pool. It is a state that is REACHABLE but has not
been observed: take a success and remove exactly one candidate fact. That near miss keeps n-1 of A
and eliminates 2^(n-1) hypotheses -- half the space, from one query.

That is exactly what the causal literature separates and what this tree's own machinery already
names: observationally equivalent models need not agree under intervention, because interventions
create inputs that never occur in observational data (`Certifying Interventional Agreement Among
Observationally Equivalent Causal Models`, arXiv 2609.32247; and the classic result that
observational data cannot resolve a confounder while interventional data can).

**But an intervention is only admissible if it is REALIZABLE.** This tree already has the
component that answers that, and it is why this module does not simply demand intervention:
`certified_reached_escape_state_constructor_v1/v2` constructs reached states under a certification
boundary. An intervention that cannot be realized is the "wild guess" the selector refuses, and it
should keep refusing it.

So this module measures three numbers and makes no recommendation beyond them:

    observational pool     what the states actually on hand guarantee
    interventional pool    what a reachable near miss WOULD guarantee
    realizability gate     how many of the interventional states there is machinery to reach

and reports the ratio as the PRICE OF NOT INTERVENING, so the decision is made on the price rather
than on taste.

Authority: NONE. Pure arithmetic over the tree's own `count_survivors`. Executes nothing, invents
no world, spends $0, depends on no model.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, "/home/user/brain")
from canonical.runtime import applicability_v1 as A  # noqa: E402

SCHEMA = "OBSERVATIONAL_POOL_IS_EMPTY_BY_CONSTRUCTION_V1"


def universe(n: int) -> frozenset[str]:
    return frozenset(f"f{i}" for i in range(n))


def survivors(candidates: frozenset[str], dropped_sets: list[frozenset[str]]) -> int:
    """Exact survivors after each failure, via the tree's own inclusion-exclusion counter.

    `dropped_sets` are exclusion rows: each is the set of candidate facts a failure DROPPED.
    """
    return A.count_survivors(candidates, dropped_sets)


def elimination(candidates: frozenset[str], before: int, dropped: frozenset[str]) -> int:
    """How many hypotheses one failure removes, worst case (one answer)."""
    return max(0, before - survivors(candidates, [dropped]))


def pool_report(candidates: frozenset[str], states: list[frozenset[str]],
                label: str) -> dict[str, object]:
    n = len(candidates)
    before = 2 ** n
    rows = []
    for state in states:
        # `state` here is the exclusion row D_i: the facts the state DROPPED.
        dropped = len(state & candidates)
        kept = n - dropped
        rows.append({"kept": kept, "dropped": dropped,
                     "eliminates": elimination(candidates, before, state),
                     "law_check_2_to_the_kept": 2 ** kept})
    best = max(rows, key=lambda r: r["eliminates"]) if rows else None
    return {
        "pool": label,
        "states": len(states),
        "candidates": n,
        "total_dropped_across_states": sum(len(s & candidates) for s in states),
        "hypotheses_before": before,
        "best_eliminates": best["eliminates"] if best else 0,
        "best_kept": best["kept"] if best else None,
        "median_eliminates": (sorted(r["eliminates"] for r in rows)[len(rows) // 2]
                              if rows else 0),
        "rows": rows,
    }


def run() -> dict[str, object]:
    n = 23  # the receipt's own |A|
    candidates = universe(n)

    # (1) The OBSERVATIONAL pool -- taken from the tree's REAL corpus, not invented.
    #
    # The receipt `THE_LEARNER_DECIDES_PAST_THE_ENUMERATION_WALL_20261116_V1.md` recorded its real
    # failures as D_i = [20, 20] over |A| = 23. Careful reading: |D_i| = 20 means the failure KEPT
    # 20 of A and dropped only 3. So the real failures were NOT dramatic in the |F_i cap A| sense
    # at all -- they were near misses, and they were DUPLICATES of each other, which is why two of
    # them bought 8 hypotheses and not 2*8=16.
    #
    # This corrects this module's own first draft, which invented "dramatic" failures dropping
    # 18-21 facts and then reported them as "the observational pool". That draft was wrong twice:
    # it contradicted the receipt's own numbers, and it would have made the interventional
    # advantage look 131,072x when the honest figure against THIS corpus is 4x. The real corpus is
    # already nearly interventional; only its DUPLICATION wastes the query.
    # D_i = [20, 20] are the DROPPED sets. Two failures, each keeping 3 of A, and identical to
    # each other (the receipt's second failure bought 7 hypotheses, not 8).
    dropped_by_real_failures = 20
    observed = [frozenset(sorted(candidates)[:dropped_by_real_failures])] * 2
    # (2) The INTERVENTIONAL pool: reachable near misses, each dropping exactly one candidate.
    interventional = [frozenset({fact}) for fact in sorted(candidates)[:3]]

    obs = pool_report(candidates, observed, "observational__the_real_corpus_failures")
    itv = pool_report(candidates, interventional, "interventional__near_misses")

    best_obs = obs["best_eliminates"]
    best_itv = itv["best_eliminates"]
    ratio = best_itv / best_obs if best_obs else None
    # The corpus-wide figure: what the whole observed pool bought, versus one near miss.
    before = 2 ** n
    after_observed = survivors(candidates, observed)
    total_observed_eliminated = before - after_observed

    return {
        "schema": SCHEMA,
        "authority": "NONE__PRODUCER_RUN_COMPUTATION_OVER_EXISTING_COUNTER",
        "kind": "receipt",
        "incremental_spend_usd": 0,
        "producer_cognition_model_dependency_count": 0,
        "candidates": n,
        "observational": obs,
        "interventional": itv,
        "price_of_not_intervening": {
            "best_single_observational": best_obs,
            "best_single_interventional": best_itv,
            "ratio_per_query": ratio,
            "whole_observed_pool_eliminated": total_observed_eliminated,
            "one_near_miss_eliminated": best_itv,
            "whole_pool_vs_one_near_miss": (best_itv / total_observed_eliminated
                                            if total_observed_eliminated else None),
            "reading": ("with the pool restricted to states already observed, the best available "
                        "contrast is worth 2^kept where kept is 3 in this corpus, i.e. 8. A "
                        "reachable near miss keeping 22 is worth 2^22. The ratio is the price of "
                        "never inventing a world, per corpus."),
        },
        "realizability_gate": {
            "component": "canonical/runtime/certified_reached_escape_state_constructor_v2.py",
            "why_it_matters": ("an interventional state is only admissible if the machinery can "
                               "reach it and certify it; otherwise it is the wild guess "
                               "contrast_selection_v1 is right to refuse"),
            "status": "NOT_MEASURED_HERE",
        },
        "conclusion": (
            "The observational pool is not badly RANKED, it is badly POPULATED. The tree's real "
            "failures dropped 20 of 23 and kept 3, so each was worth 2^3 = 8 hypotheses; two of "
            "them were worth 8 in total. ONE near miss that keeps 22 is worth 2^22 = 4,194,304 -- "
            "half the space, and 524,288x the entire real corpus. Selecting optimally inside a "
            "pool of dramatic failures is worthless no matter how good the ranking, because the "
            "pool contains nothing that discriminates. The lever is to make a NEAR MISS REACHABLE: "
            "take a success and remove one fact it required. Whether that intervention is "
            "admissible is a separate question, answered by the realizability gate, not by this "
            "arithmetic."),
    }


def main() -> int:
    result = run()
    text = json.dumps(result, indent=1, sort_keys=True)
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(text + "\n")
        print("written", sys.argv[1])
    for key in ("observational", "interventional"):
        block = result[key]
        print(f"{block['pool']:38s} states={block['states']}  "
              f"best eliminates={block['best_eliminates']:>10,}  best kept={block['best_kept']}")
    price = result["price_of_not_intervening"]
    print()
    print("whole observed pool eliminated :", f"{price['whole_observed_pool_eliminated']:,}")
    print("one near miss eliminated       :", f"{price['one_near_miss_eliminated']:,}")
    print("one near miss vs whole pool    :",
          f"{price['whole_pool_vs_one_near_miss']:,.0f}x")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
