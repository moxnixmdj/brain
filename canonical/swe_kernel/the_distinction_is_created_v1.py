#!/usr/bin/env python3
"""The distinction is created, not selected: compute the smallest vocabulary extension that makes
an environment's behaviour expressible, and prove it by re-measuring.

THE WALL THIS ATTACKS, AND WHY IT IS THE RIGHT ONE
--------------------------------------------------
This repository already measured the binding term four rounds ago
(`WHY_NO_MECHANISM_CAN_BUY_REACH_20261116_V1`):

    P(correct action) = REACH x SEARCH x VERIFICATION

Search, verification and environment adaptation are bought. Reach is not, and reach is not a search
problem: 75.2% of 2,178 real fix pieces needed an operator that no amount of experience of the
existing columns produced. `witness_inversion_v1` was built to attack it by *selecting* an
expression over the live frame -- 18 real witnesses captured, 0 verified, because "an inverter
selects over existing content, and the answer is new content."

The round after it (`ONE_EXPERIENCE_EVERY_CONSEQUENCE_20261124_V1`) measured the same law from the
other side: a safe action model from one observation is never wrong and never generalizes, because
its guard is a description of one state. Its written conclusion was that the bottleneck is the
*acquisition policy* -- how many varied observations per action.

That conclusion was one step short. Observations do not help if the representation cannot tell two
behaviourally different states apart: no number of observations of an aliased vocabulary produces a
distinction, because the distinction is not in the vocabulary. The acquisition policy is bounded
above by the vocabulary's discriminating power.

So the object to compute is not the next observation. It is **the distinction itself**, and the
question "does this vocabulary contain it?" is decidable. That is what this module does.

WHAT IT COMPUTES
----------------
Given observed transitions, two pre-states are ALIASED when the current vocabulary assigns them the
same signature but some atom behaves differently in them. That pair is a fact the representation
cannot state, and every aliased pair is a place where the learned model must refuse or be wrong.

Then, from a fixed set of candidate discriminators -- each a computable property of the raw rows
that uses no domain knowledge, no names, and no parameters -- it computes the smallest subset that
separates every aliased pair, by greedy set cover. If no subset separates them all, it says so, and
names the pairs that remain. An extension that was chosen because the data demanded it is a
CREATED distinction; one chosen because it looked useful is a guess.

This is deliberately not a grammar search. The candidate set is small, fixed, and justified one by
one (see `DISCRIMINATORS`), and the algorithm does not add a relation unless an aliased pair
requires it. "The best part is no part" applied to vocabulary: a relation is added only when a
measured contradiction makes it necessary.

RELATION TO ACTIVE AUTOMATA LEARNING, WHICH IS WHERE THIS CAME FROM
------------------------------------------------------------------
The same object appears in automata learning as a DISTINGUISHING SEQUENCE: an input sequence whose
outputs separate two states (L# and the ADS variants, arXiv 2107.05419; adaptive AAL, arXiv
1902.01139). The theory gives the bound this module is trying to reach in practice: O(k n^2) output
queries, and empirically 1-4 queries per frontier state. A distinguishing sequence is a witness, and
this repository's whole method is witness-driven -- so the connection is not an analogy. What is
missing in the learned-model literature is the *symbolic* version: not "which input separates these
states" but "which computable predicate does the vocabulary lack". That is what is built here.

Zero model calls, zero parameters, zero network.
"""
from __future__ import annotations

import dataclasses
import itertools
from typing import Any, Callable, Sequence

SCHEMA = "PROJECT_BRAIN_THE_DISTINCTION_IS_CREATED_V1"

State = Sequence[tuple[str, str]]


# ---------------------------------------------------------------------------------------------
# candidate discriminators: computed properties of raw rows, each justified in one line
# ---------------------------------------------------------------------------------------------

def _contents(rows: State) -> list[str]:
    return [content for _ident, content in rows]


def sorted_content(rows: State) -> bool:
    """Is the content sequence in sorted order? Sortedness is the one property a reader who only
    sees a multiset cannot recover, and `sort` is the most common atom in this tree."""
    contents = _contents(rows)
    return contents == sorted(contents)


def unique_content(rows: State) -> bool:
    """Are all contents distinct? Distinguishes a set from a bag -- the difference between `sort -u`
    and `sort`, which a multiset-only vocabulary conflates."""
    contents = _contents(rows)
    return len(set(contents)) == len(contents)


def content_tail(rows: State) -> str:
    """The last content. Distinguishes append orders that share a multiset -- appending `z` then `a`
    and appending `a` then `z` are the same bag and different journals."""
    contents = _contents(rows)
    return contents[-1] if contents else ""


def runs_of_equal_content(rows: State) -> int:
    """How many maximal runs of equal adjacent content. Distinguishes `a a b` from `a b a` without
    naming either content, so it survives a change of literals."""
    contents = _contents(rows)
    return 1 + sum(1 for index in range(1, len(contents))
                   if contents[index] != contents[index - 1]) if contents else 0


def inversions(rows: State) -> int:
    """How many pairs are out of content order. The graded version of `sorted_content`, so a nearly
    sorted file is distinguishable from a scrambled one of the same length."""
    contents = _contents(rows)
    return sum(1 for i, j in itertools.combinations(range(len(contents)), 2)
               if contents[i] > contents[j])


def duplicate_count(rows: State) -> int:
    """How many contents occur more than once. Distinguishes two files whose multiset counts differ
    per literal but whose distinct-content count agrees."""
    contents = _contents(rows)
    return sum(1 for content in set(contents) if contents.count(content) > 1)


def id_content_agree(rows: State) -> bool:
    """Do the identifiers run in the same order as the contents? Distinguishes a relabelling from a
    reordering -- the same permutation seen from two sides."""
    return [ident for ident, _c in rows] == \
        [ident for ident, _c in sorted(rows, key=lambda row: row[1])]


DISCRIMINATORS: dict[str, Callable[[State], Any]] = {
    "sorted_content": sorted_content,
    "unique_content": unique_content,
    "content_tail": content_tail,
    "runs_of_equal_content": runs_of_equal_content,
    "inversions": inversions,
    "duplicate_count": duplicate_count,
    "id_content_agree": id_content_agree,
}

#: name -> (why it exists, what it costs). Each is O(n) or O(n log n) over rows; none needs a name.
WHY: dict[str, str] = {
    "sorted_content": "multiset-only readers cannot see order; sort is the most common atom here",
    "unique_content": "set vs bag: sort -u vs sort are indistinguishable by a multiset",
    "content_tail": "append order is invisible to a multiset",
    "runs_of_equal_content": "literal-free shape of an interleaving",
    "inversions": "graded order, so 'nearly sorted' is distinguishable from 'scrambled'",
    "duplicate_count": "which literal repeats, not just how many repeats exist",
    "id_content_agree": "the same permutation seen from the identifier side",
}


# ---------------------------------------------------------------------------------------------
# aliasing: the fact the vocabulary cannot state
# ---------------------------------------------------------------------------------------------

def effect_of(atom: str, state: State, transitions: Sequence[tuple[str, State, State]],
              conditions: Sequence[Any], holds: Callable) -> frozenset | None:
    """The observed change set of `atom` in exactly this state, from the recording. None if this
    (atom, state) was never executed -- absence of a transition is not an effect."""
    for ident, before, after in transitions:
        if ident == atom and tuple(before) == tuple(state):
            return frozenset(c for c in conditions
                             if holds(c, after) and not holds(c, before))
    return None


@dataclasses.dataclass(frozen=True)
class Alias:
    """Two states the vocabulary cannot tell apart, where some atom demonstrably behaves
    differently. Each one is a place the learned model must refuse or be wrong."""
    atom: str
    left: tuple
    right: tuple
    effect_left: frozenset
    effect_right: frozenset


def find_aliases(transitions: Sequence[tuple[str, State, State]], conditions: Sequence[Any],
                 holds: Callable) -> list[Alias]:
    """Enumerate every pair of states with equal vocabulary signature but different behaviour.

    The comparison is between states that were ACTUALLY EXECUTED with the same atom, because a
    behavioural difference that was never observed is a hypothesis, not a fact. That keeps the count
    honest: an alias here means "this happened and the vocabulary could not have recorded why".
    """
    observations: dict[tuple[str, tuple], tuple[State, frozenset]] = {}
    for ident, before, after in transitions:
        effect = frozenset(c for c in conditions if holds(c, after) and not holds(c, before))
        observations[(ident, tuple(before))] = (before, effect)

    by_signature: dict[tuple[str, frozenset], list[tuple[State, frozenset]]] = {}
    for (ident, key), (before, effect) in observations.items():
        signature = frozenset(c for c in conditions if holds(c, before))
        by_signature.setdefault((ident, signature), []).append((before, effect))

    aliases: list[Alias] = []
    for (ident, _signature), members in by_signature.items():
        for (left, effect_left), (right, effect_right) in itertools.combinations(members, 2):
            if effect_left != effect_right:
                aliases.append(Alias(ident, tuple(left), tuple(right), effect_left, effect_right))
    return aliases


def separates(name: str, alias: Alias) -> bool:
    """Does this discriminator give the two states different values? That is all a distinction is."""
    discriminator = DISCRIMINATORS[name]
    return discriminator(alias.left) != discriminator(alias.right)


def minimal_extension(aliases: Sequence[Alias]) -> tuple[list[str], list[Alias], dict[str, Any]]:
    """Greedy set cover: the smallest set of NEW discriminators that separates every alias.

    Greedy rather than optimal on purpose. The claim being made is "the vocabulary lacked this
    distinction", not "this is the unique minimum", and a greedy cover that leaves zero aliases
    separated is a stronger statement than an optimal one that leaves some. What is NOT acceptable
    is an extension that separates most pairs and then quietly reports success -- the leftovers are
    returned explicitly so the failure is visible in the receipt.
    """
    remaining = list(aliases)
    chosen: list[str] = []
    steps: list[dict[str, Any]] = []
    while remaining:
        scored = [(sum(1 for alias in remaining if separates(name, alias)), name)
                  for name in DISCRIMINATORS]
        scored.sort(reverse=True)
        best_count, best_name = scored[0]
        if best_count == 0:
            break
        covered = [alias for alias in remaining if separates(best_name, alias)]
        remaining = [alias for alias in remaining if not separates(best_name, alias)]
        chosen.append(best_name)
        steps.append({"discriminator": best_name, "separated": best_count,
                      "remaining": len(remaining)})
    return chosen, remaining, {"greedy_steps": steps,
                               "candidates_considered": len(DISCRIMINATORS),
                               "not_greedy_optimum": True}


# ---------------------------------------------------------------------------------------------
# the re-measurement: does the created distinction make the model able to generalise?
# ---------------------------------------------------------------------------------------------

def derived_conditions(chosen: Sequence[str], states: Sequence[State]) -> list[Any]:
    """Turn chosen discriminators into conditions of the form the frame machinery already reads.

    The relation name is DERIVED and the binding names the discriminator, so no new frame is added
    and `safe_action_model_v1.holds` dispatches through its registry. One condition per observed
    value -- the same policy as the existing vocabulary, which admits every observed frame value.
    """
    out: list[Any] = []
    for name in chosen:
        values = {DISCRIMINATORS[name](state) for state in states}
        for value in values:
            out.append(("DERIVED", name, None, "equals", value))
    return out


def purity(transitions: Sequence[tuple[str, State, State]], conditions: Sequence[Any],
           holds: Callable) -> dict[str, Any]:
    """How many (atom, signature) cells carry more than one observed effect.

    This is the executive number for the whole round. An impure cell is a context the representation
    cannot express, and an induced operator from an impure cell is the thing that produced 32 wrong
    predictions in the previous round. If the created distinction is real, this number falls.
    """
    cells: dict[tuple[str, frozenset], set[frozenset]] = {}
    for ident, before, after in transitions:
        signature = frozenset(c for c in conditions if holds(c, before))
        effect = frozenset(c for c in conditions if holds(c, after) and not holds(c, before))
        cells.setdefault((ident, signature), set()).add(effect)
    impure = {key: len(value) for key, value in cells.items() if len(value) > 1}
    return {"cells": len(cells), "impure_cells": len(impure),
            "max_effects_in_one_cell": max(impure.values()) if impure else 1,
            "pure_fraction": round(1 - len(impure) / max(1, len(cells)), 4)}
