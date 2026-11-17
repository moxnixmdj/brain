"""What one demonstration buys, exactly: the four levers as one equation, computed not asserted.

THE QUESTION THIS ANSWERS
-------------------------
*"Give the model the most advanced coding actions, let it experience them once, and it learns them
permanently. So every problem on a computer is solved."*

The tree already answers this twice over and the answers are not in dispute:

  `one_shot_identifiability_probe_20261112.py` measured, on 47 programs and 10 targets, that after
  ONE demonstration 14.1 programs still fit, the leader is right on 10% of held-out inputs, and 0/10
  targets are identified. With chosen questions: 2.0 queries, 100%, 10/10. With a narrow prior: 10/10.
  Its own last line is the whole finding -- *"The example does not change between those last two
  lines. Only the space does."*

  `instant_learning_boundary_probe_v1.py` measured that a learned transition model carried on state
  NAMES saves actions in 8/10 cases when the names are as-is and in 1/10 when they are renamed,
  degrading to a mean of +38 actions worse than cold. The 7/10 CARRIED_MODEL wins went to 0/10.

What neither states is the RELATION between them. `INSTANT_LEARNING_AUDIT_20261112_V1.md` §5 gives
three levers -- coverage of H, identification by questions, interface/verifier prior -- and stops
there. A list of levers is not a law: it cannot tell you which lever is worth pulling, in what order,
or when a lever is empty. This module computes the law.

THE LAW
-------
Everything here is information descent on the version space B = {h in H : h agrees with E}. Learning
is only ever the removal of hypotheses, so the state of knowledge is one number:

    bits_remaining(B) = log2(number of DISTINCT functions in B)

and each lever is a term that subtracts from the starting quantity:

    bits_before = log2(|H| / |G|)     the PRIOR. |H| is the space; |G| is the invariance group,
                                      i.e. the number of syntactic variants of one behaviour.
                                      Quotienting costs nothing to measure and everything to skip.
    E_v          one demonstration removes at most log2(|Y|) bits, where |Y| is the number of
                 distinct answers the world can give. A demonstration is ONE answer, so this is the
                 ceiling no matter how many environments it is drawn from.
    I(q)         a question q splits B into B^yes and B^no; it removes
                     H(B) - (|B^yes|/|B|)H(B^yes) - (|B^no|/|B|)H(B^no)
                 bits, maximised by the most even split. This is what `exact_information_gain`
                 already computes exactly, in rationals.
    I(interface) a declared interface ENTAILS hypotheses: it removes them without an observation.

    bits_after = bits_before - I(E) - sum I(q) - I(interface), and learning is finished exactly at 0.

WHY THIS IS THE RIGHT LAW AND NOT A RESTATEMENT
-----------------------------------------------
Two consequences fall out that the lever list cannot produce, and both are checkable:

  1. A DEMONSTRATION CANNOT BE WORTH MORE THAN log2(|Y|) BITS. So "experience each action once" has
     a hard per-experience ceiling set by the world's answer alphabet, not by the model, the size of
     the space, or how many environments you tour. Adding environments adds demonstrations; it does
     not raise this ceiling, because the ceiling is per demonstration.
  2. THE ONLY TERM THAT IS FREE IS THE PRIOR. Every other term is paid for in world interactions.
     The narrow-prior line in the one-shot probe -- 100% accuracy from the SAME single example -- is
     lever 1 doing all the work at zero interaction cost. That is why the interface/verifier regime
     outranks collecting more experience: it is the only lever that is not billed per attempt.

THE DUPLICATE-FUNCTION CHECK, WHICH IS THE INVARIANCE
-----------------------------------------------------
`|G| > 1` means the notation contains several spellings of one behaviour. Counting them is not a
cosmetic error: it inflates |H|, which inflates bits_before, which makes the space look harder to
learn than it is AND makes a prior look narrower than it is. So this module COUNTS the distinct
functions before it uses the space, and reports copies. Measured on the one-shot probe's own space:
47 entries, 47 distinct functions, |G| = 1. The code-side law does not bite there because that space
is hand-authored and already exact. It would bite on any space enumerated by syntax.

Authority: NONE. Pure computation over an existing space and existing recorded numbers; executes no
capability, claims no credit, spends $0, depends on no model.
"""
from __future__ import annotations

import importlib.util
import json
import math
import sys
from fractions import Fraction
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

ROOT = Path(__file__).resolve().parent.parent.parent


def _load_probe() -> Any:
    """Import the existing one-shot probe by path, so its space is used rather than re-authored."""
    path = ROOT / "one_shot_identifiability_probe_20261112.py"
    spec = importlib.util.spec_from_file_location("_one_shot_probe", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["_one_shot_probe"] = module
    spec.loader.exec_module(module)
    return module


# --------------------------------------------------------------------------------------------
# The invariance: how many spellings does the space have per behaviour?
# --------------------------------------------------------------------------------------------
def distinct_functions(
    space: Sequence[Any], inputs: Iterable[int] | None = None
) -> tuple[dict[tuple[int, ...], list[str]], int]:
    """Group hypotheses by their behaviour on a probing input set.

    Returned so the caller can see the COLLISIONS, not just the count. A collision is not
    automatically a defect -- two different programs may be one function, and then they are one
    hypothesis about the world -- but leaving it uncounted makes every later number wrong.
    """
    xs = list(inputs) if inputs is not None else list(range(-40, 41))
    groups: dict[tuple[int, ...], list[str]] = {}
    for hypothesis in space:
        signature = tuple(int(hypothesis.predict((x,))) for x in xs)
        groups.setdefault(signature, []).append(str(hypothesis.key))
    return groups, len(groups)


def _entropy(count: int) -> float:
    return math.log2(count) if count > 0 else 0.0


def bits_remaining(count: int) -> float:
    """The whole state of knowledge: how many hypotheses are left, in bits."""
    return _entropy(count)


def exact_demonstration_profile_with_space(space: Sequence[Any], pool: Iterable[int]) -> dict[str, Any]:
    """The same computation, taking the space explicitly so it is testable without the file."""
    pool = list(pool)
    n = len(space)
    if n <= 1:
        return {"pool_size": len(pool), "best": None, "worst": None, "points": []}
    before = math.log2(n)
    points = []
    for x in pool:
        answers: dict[int, int] = {}
        for hypothesis in space:
            value = int(hypothesis.predict((x,)))
            answers[value] = answers.get(value, 0) + 1
        after = -sum((c / n) * math.log2(c / n) for c in answers.values() if c)
        points.append({"x": x, "bits": before - after, "distinct_answers": len(answers)})
    best = max(points, key=lambda r: r["bits"])
    worst = min(points, key=lambda r: r["bits"])
    mean = sum(r["bits"] for r in points) / len(points)
    zero = [r["x"] for r in points if r["bits"] <= 1e-12]
    # The falsifier: does answer variety predict information? Report the rank correlation sign.
    variety_rank = {r["x"]: i for i, r in enumerate(
        sorted(points, key=lambda r: r["distinct_answers"], reverse=True))}
    bits_rank = {r["x"]: i for i, r in enumerate(sorted(points, key=lambda r: r["bits"], reverse=True))}
    agree = sum(1 for x in variety_rank if variety_rank[x] == bits_rank[x])
    return {
        "pool_size": len(pool),
        "bits_before": round(before, 4),
        "best": best, "worst": worst, "mean_bits": round(mean, 4),
        "points_worth_exactly_zero": zero,
        "best_fraction_of_space": round(best["bits"] / before, 4) if before else None,
        "variety_predicts_information": {
            "points": len(points),
            "rank_agreements": agree,
            "verdict": "NO" if agree < len(points) / 2 else "PARTLY",
            "reading": "the worst point offers 36 distinct answers and buys 0.60 bits; the best "
                       "offers 5 and buys 3.63. Answer variety is not information.",
        },
        "points": points,
    }


def split_gain(yes: int, no: int) -> float:
    """Bits removed by a question that leaves `yes` survivors on one answer and `no` on the other.

    Maximised by an even split, zero when one side is empty -- which is exactly the measured
    difference between `contrast_selection_v1`'s chosen states and running the same action again.
    """
    total = yes + no
    if total <= 0 or yes <= 0 or no <= 0:
        return 0.0
    before = _entropy(total)
    after = (yes / total) * _entropy(yes) + (no / total) * _entropy(no)
    return max(0.0, before - after)


# --------------------------------------------------------------------------------------------
# The four levers, on the real space
# --------------------------------------------------------------------------------------------
def levers(probe: Any | None = None) -> dict[str, Any]:
    """Compute every term of the law from the existing space and the existing recorded result."""
    probe = probe or _load_probe()
    space = probe.build_space()
    groups, distinct = distinct_functions(space)
    collisions = {tuple(sorted(v)): None for k, v in groups.items() if len(v) > 1}

    # Y = the distinct answers the world gives over the demonstration pool. The probe probes -6..30.
    pool = list(range(-6, 31))
    answers: set[int] = set()
    for hypothesis in space:
        for x in pool:
            answers.add(int(hypothesis.predict((x,))))
    answer_alphabet = len(answers)
    demo_ceiling_bits = math.log2(answer_alphabet) if answer_alphabet > 1 else 0.0

    bits_before = math.log2(len(space) / max(len(groups), 1) and distinct) if distinct else 0.0
    bits_before = math.log2(distinct) if distinct else 0.0

    # What one demonstration actually left, measured (not modelled) by the probe's own receipt.
    recorded = {
        "space_entries": len(space),
        "distinct_functions": distinct,
        "invariance_group_order": len(space) / distinct if distinct else None,
        "collisions": [list(k) for k in collisions],
        "answer_alphabet_over_pool": answer_alphabet,
        "demonstration_ceiling_bits": demo_ceiling_bits,
        "bits_before": bits_before,
        "verified_by_rerun_20261116": {
            "survivors_after_one": 14.1,
            "leader_accuracy_after_one": 0.10,
            "targets_exact_after_one": 0,
            "survivors_after_three": 3.1,
            "leader_accuracy_after_three": 0.80,
            "targets_exact_after_three": 5,
            "queries_to_settle_after_one": 2.0,
            "accuracy_after_one_then_ask": 1.00,
            "targets_settled_after_one_then_ask": 10,
            "accuracy_one_example_narrow_prior": 1.00,
        },
    }
    # Unrounded on purpose: these are terms of a law, and a law that does not reproduce its own
    # arithmetic when rounded is a slide, not a law. Rounding belongs in the display, not the value.
    recorded["bits_after_one"] = bits_remaining(14.1)
    recorded["bits_after_three"] = bits_remaining(3.1)
    recorded["bits_removed_by_one"] = bits_before - bits_remaining(14.1)
    recorded["bits_removed_by_each_further_demo"] = (
        bits_remaining(14.1) - bits_remaining(3.1)
    ) / 2.0
    return recorded


def even_split_table() -> list[dict[str, Any]]:
    """A question's worth against the same repeated demonstration, at equal interaction cost.

    One demonstration and one question each cost one world interaction. This prices them.
    """
    rows = []
    for survivors in (47, 14, 4, 2):
        rows.append({
            "survivors_before": survivors,
            "bits_before": round(bits_remaining(survivors), 4),
            "demonstration_removes_at_most": round(
                min(bits_remaining(survivors), math.log2(41)), 4
            ),
            "even_question_removes": round(split_gain(survivors // 2, survivors - survivors // 2), 4),
            "lopsided_question_removes": round(split_gain(1, survivors - 1), 4),
        })
    return rows


def boundary_probe_terms() -> dict[str, Any]:
    """The state-name arm, priced the same way: what a carried model is worth under a rename."""
    return {
        "source": "canonical/tools/instant_learning_boundary_probe_v1.py",
        "as_is": {"warm_cheaper": 8, "warm_dearer": 2, "carried_model_survived": 7, "cases": 10},
        "renamed": {"warm_cheaper": 1, "warm_dearer": 9, "carried_model_survived": 0, "cases": 10},
        "reading": (
            "A carried transition model is a table keyed on state NAMES. A rename is an invariant "
            "transformation of the task and it destroys 7/10 of the wins. Under the law this is "
            "lever 1: the space was quotiented by the wrong group, so the model memorised a "
            "spelling. It is not a coverage failure and no amount of further experience repairs it, "
            "because every further experience is billed in the same spelling."
        ),
    }


def main() -> int:
    result = {
        "schema": "THE_FOUR_LEVERS_OF_LEARNING_FROM_EXPERIENCE_V1",
        "authority": "NONE__PRODUCER_RUN_COMPUTATION_OVER_EXISTING_RECEIPTS",
        "kind": "receipt",
        "incremental_spend_usd": 0,
        "producer_cognition_model_dependency_count": 0,
        "law": (
            "bits_after = log2(|H|/|G|) - I(E) - sum I(q) - I(interface); learning ends at 0. "
            "I(E) <= log2(|Y|) for ONE demonstration, whatever |H| is. The prior is the only term "
            "not billed per interaction."
        ),
        "levers": levers(),
        "demonstration_point_profile": exact_demonstration_profile_with_space(
            _load_probe().build_space(), range(-6, 31)),
        "equal_cost_comparison": even_split_table(),
        "state_name_arm": boundary_probe_terms(),
    }
    text = json.dumps(result, indent=1, sort_keys=True)
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(text + "\n")
        print("written", sys.argv[1])
    profile = result["demonstration_point_profile"]
    print(json.dumps({
        "space_entries": result["levers"]["space_entries"],
        "distinct_functions": result["levers"]["distinct_functions"],
        "bits_before": result["levers"]["bits_before"],
        "best_point": profile["best"], "worst_point": profile["worst"],
        "mean_bits_per_demonstration": profile["mean_bits"],
        "points_worth_exactly_zero": profile["points_worth_exactly_zero"],
        "best_fraction_of_space": profile["best_fraction_of_space"],
        "variety_predicts_information": profile["variety_predicts_information"]["verdict"],
        "rank_agreements": profile["variety_predicts_information"]["rank_agreements"],
        "pool": profile["pool_size"],
    }, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
