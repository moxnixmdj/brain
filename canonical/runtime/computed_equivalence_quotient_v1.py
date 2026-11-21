"""Computed equivalence quotient for goal residuals.

THE CLAIM THIS REPLACES
-----------------------
A previous round measured 555 executed runs of three machines, found two minimal
statements for the user's goal, and priced the difference at one question of the
user:

    created_once[c]
    monotone[c] AND final:count[c]==1

Both statements are the same fact.  This module deletes the ambiguity instead of
asking anybody to resolve it.

THE THEOREM, NOT A SAMPLE
-------------------------
Let a_0 = k be the number of entries holding content c in the machine's initial
reading, and let a_i be that number after step i.  The reader counts entries, so
every delta a_(i+1) - a_i is an integer.  The identity also needs the reader's
increments to be UNIT increments: one step adds at most one entry of c.  This is
not true of every machine -- a step can add two -- so it is computed from the
executed runs and a content whose increments are not unit is never rewritten.
Define:

    U(c)  = exactly one step raised the count, and no step lowered it
    M(c)  = no step lowered the count
    F(c,n)= the final count is n

    U(c)  <==>  M(c) AND F(c, k+1)     (k = initial count; unit increments)

Proof.  U(c) implies no lowering and one raising step, so a_n = k + d for one
positive integer d; under unit increments d = 1.  Conversely M(c) makes every
delta non-negative and F(c,k+1) makes their sum 1; integers that are non-negative
and sum to 1 have exactly one positive term, which is U(c).  Without unit
increments the first half fails: one step from 0 to 2 raises once and ends at 2.

The premise matters.  On a machine that starts with one copy of c, F(c,1) means
*no* addition, so U(c) and M(c) AND F(c,1) are different goals.  A machine that
starts with zero copies cannot express that distinction.  The rewrite therefore
carries k, and refuses to fire when the initial reading is unknown.

No parameters, no training, no samples used to guess the identity.  Every
rewrite is calculated from the reader's counting semantics, then checked against
the executed masks; a disagreement refuses the rewrite rather than the evidence.

Authority: NONE. Pure Python, standard library only, no I/O and no model calls.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

SCHEMA = "BRAIN_COMPUTED_EQUIVALENCE_QUOTIENT_V1"
RULE = "TELESCOPING_COUNT_V1"

State = tuple[tuple[str, str], ...]
Trace = tuple[State, ...]
Combo = tuple[int, ...]

_CREATED = re.compile(r"created_once\[(.+)\]\Z")
_MONOTONE = re.compile(r"monotone\[(.+)\]\Z")
_FINAL_COUNT = re.compile(r"final:count\[(.+)\]==(-?\d+)\Z")


@dataclass(frozen=True)
class Alias:
    """Several syntactic statements with one calculated meaning."""

    combos: tuple[Combo, ...]
    texts: tuple[str, ...]
    rule: str
    premise: str
    key: frozenset[str]

    def as_dict(self) -> dict[str, object]:
        return {"texts": list(self.texts), "rule": self.rule,
                "premise": self.premise, "canonical": sorted(self.key)}


def initial_counts(state: State) -> dict[str, int]:
    """The initial count of every content the machine's reader can see."""
    counts: dict[str, int] = {}
    for _ident, content in state:
        counts[content] = counts.get(content, 0) + 1
    return counts


def counts_with_absent(state: State, traces: Sequence[Trace]) -> dict[str, int]:
    """Initial counts, with zero recorded for contents the run can create later.

    A content absent at step zero has initial count zero.  Leaving it out of the
    map would make the rewrite unable to fire on exactly the goals it was
    derived for.
    """
    counts = initial_counts(state)
    for trace in traces:
        for step in trace:
            for _ident, content in step:
                counts.setdefault(content, 0)
    return counts


def unit_increments(traces: Sequence[Trace], content: str) -> bool:
    """One step never adds more than one entry of this content.

    A false answer refuses the rewrite for that content; it does not lower a
    confidence value and it does not narrow a tolerance.
    """
    for trace in traces:
        for before, after in zip(trace, trace[1:]):
            delta = (sum(1 for _i, value in after if value == content)
                     - sum(1 for _i, value in before if value == content))
            if delta > 1:
                return False
    return True


def canonical(combo: Combo, texts: Sequence[str], counts: Mapping[str, int]) -> frozenset[str]:
    """The meaning of a statement, after the calculated rewrite.

    An unknown term is its own atom; it is never guessed to be equivalent to
    anything, and it cannot silently acquire the rewrite's meaning.
    """
    atoms: set[str] = set()
    for index in combo:
        text = texts[index]
        created = _CREATED.fullmatch(text)
        monotone = _MONOTONE.fullmatch(text)
        final = _FINAL_COUNT.fullmatch(text)
        if created and created.group(1) in counts:
            content = created.group(1)
            atoms.add(f"monotone[{content}]")
            atoms.add(f"final:count[{content}]=={counts[content] + 1}")
        elif monotone or final:
            # A literal final-count term needs no premise: its content may be
            # absent initially (count zero), which is a known count, not an
            # unknown one.  Only the U(c) rewrite needs c in `counts`.
            atoms.add(text)
        else:
            atoms.add(f"raw:{text}")
    return frozenset(atoms)


def all_combos(term_count: int) -> list[Combo]:
    """The same hypothesis space the residual round used: terms and pairs."""
    combos = [(index,) for index in range(term_count)]
    combos.extend((i, j) for i in range(term_count) for j in range(i + 1, term_count))
    return combos


def alias_groups(texts: Sequence[str], counts: Mapping[str, int]) -> list[Alias]:
    """Distinct statements with one canonical meaning, grouped for verification.

    The residual is a single term against a conjunction, so grouping must happen
    over statements (one or two terms), never over terms alone.
    """
    by_key: dict[frozenset[str], list[Combo]] = {}
    for combo in all_combos(len(texts)):
        by_key.setdefault(canonical(combo, texts, counts), []).append(combo)
    out: list[Alias] = []
    for key, combos in by_key.items():
        if len(combos) < 2:
            continue
        premise = "no calculated rewrite"
        for combo in combos:
            for index in combo:
                match = _CREATED.fullmatch(texts[index])
                if match and match.group(1) in counts:
                    content = match.group(1)
                    premise = f"initial count of {content} is {counts[content]}"
                    break
            if premise != "no calculated rewrite":
                break
        rendered = tuple(" ∧ ".join(texts[i] for i in combo) for combo in combos)
        out.append(Alias(tuple(combos), rendered, RULE, premise, key))
    return sorted(out, key=lambda alias: alias.texts)


def combos_masks(combos: Iterable[Combo], term_masks: Mapping[int, int]) -> dict[Combo, int]:
    """A conjunction's mask is the AND of its terms' masks; a missing term fails closed."""
    out: dict[Combo, int] = {}
    for combo in combos:
        if any(index not in term_masks for index in combo):
            continue
        pieces = [term_masks[index] for index in combo]
        value = pieces[0]
        for mask in pieces[1:]:
            value &= mask
        out[combo] = value
    return out


def verify_aliases(groups: Iterable[Alias], masks: Mapping[Combo, int]) -> list[dict[str, object]]:
    """Check every proposed alias against what the machine actually did.

    This is a guard on the reader's semantics, not the source of the identity:
    a machine whose reader does not count entries may disagree, and then the
    rewrite is refused for that machine.
    """
    checked: list[dict[str, object]] = []
    for alias in groups:
        observed = [masks[combo] for combo in alias.combos if combo in masks]
        equal = len(observed) == len(alias.combos) and len(set(observed)) == 1
        row = alias.as_dict()
        row["observed_identical"] = equal
        row["missing"] = [combo for combo in alias.combos if combo not in masks]
        checked.append(row)
    return checked


def verified_groups(groups: Iterable[Alias], masks: Mapping[Combo, int]) -> list[Alias]:
    """Only aliases whose masks agree are allowed to change a count."""
    good = {alias.combos for alias in groups
            if all(row["observed_identical"] for row in verify_aliases([alias], masks))}
    return [alias for alias in groups if alias.combos in good]


def dedupe_meanings(statements: Sequence[Combo], texts: Sequence[str],
                    counts: Mapping[str, int]) -> list[Combo]:
    """One representative per calculated meaning, in the caller's own order."""
    seen: set[frozenset[str]] = set()
    out: list[Combo] = []
    for combo in statements:
        key = canonical(combo, texts, counts)
        if key not in seen:
            seen.add(key)
            out.append(combo)
    return out
