#!/usr/bin/env python3
"""One demonstration buys a hypothesis. Not the rule.

THE CLAIM THIS TESTS
--------------------
"Show it once, it learns permanently, therefore it can do anything on a computer." Every clause of
that is true except the word *the*. One example does not determine the rule; it determines the set
of rules that agree with one example. Learning picks one of those. Permanence then makes that
choice durable -- including when it is the wrong one.

WHAT IS MEASURED, CONCRETELY
----------------------------
One data-repair demonstration: a record where the total is 42 and the rows multiply to 42. Two
rules agree with it completely:

    copy_the_total_it_was_shown   42, whatever the rows say        (no arithmetic, simpler)
    recompute_from_the_rows       qty * price                      (correct, but not simpler)

Nothing in the demonstration separates them. The system registers the simpler one, as any Occam
learner must. It is then *permanently* verified -- by any environment whose check is weak enough to
accept a number in the total field -- while being wrong on every record whose true total is not 42.

A second, different demonstration kills the copy rule and leaves exactly one live hypothesis. That
is the whole difference between "learned it" and "learned the right thing", and it costs one more
example, not a better model.

WHAT THIS IS NOT
----------------
Not a claim that instant learning is broken. It is the strongest thing in this tree. It is a
statement about what the ceiling is: the ceiling is the check, because permanence makes the check's
coverage permanent too. See
canonical/verification/PERMANENCE_AMPLIFIES_THE_CHECK_KNOWN_COUNTEREXAMPLE_20261102_V1.json.
"""
from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Sequence

SCHEMA = "PROJECT_BRAIN_PERMANENCE_AMPLIFIES_CHECK_V1"

ERROR = 42  # the number in the single demonstration, and therefore the number it will always write


@dataclass(frozen=True)
class Record:
    qty: int
    price: int
    total: int

    @property
    def truth(self) -> int:
        return self.qty * self.price


@dataclass(frozen=True)
class Skill:
    """A rule it could have learned, with the arithmetic it will perform forever."""

    name: str
    apply: Callable[[Record], int]
    simpler_than_arithmetic: bool = False


def live_hypotheses(demonstrations: Sequence[Record]) -> list[Skill]:
    """Every rule that reproduces the demonstrations exactly. Not the one it picked -- all of them."""
    if not demonstrations:
        # Vacuous truth would otherwise "confirm" every arithmetic rule at once. Found while
        # writing the tests: an empty demonstration list returned the correct rule with total
        # confidence, which is the worst possible answer to "what did you learn from nothing".
        return []
    shown = {r.total for r in demonstrations}
    candidates: list[Skill] = []
    if len(shown) == 1:
        only = next(iter(shown))
        candidates.append(Skill("copy_the_total_it_was_shown", lambda r, v=only: v,
                                simpler_than_arithmetic=True))
    candidates.append(Skill("recompute_from_the_rows", lambda r: r.qty * r.price))
    return [s for s in candidates if all(s.apply(r) == r.total for r in demonstrations)]


def learn(demonstrations: Sequence[Record]) -> Skill | None:
    """What it registers: the simplest rule consistent with everything it was shown."""
    live = live_hypotheses(demonstrations)
    if not live:
        return None
    live.sort(key=lambda s: (not s.simpler_than_arithmetic, s.name))
    return live[0]


# ------------------------------------------------------------------ environments


def weak_check(record: Record, proposed: int) -> bool:
    """The check a team writes when it trusts the column: there is a number in it."""
    return isinstance(proposed, int)


def strong_check(record: Record, proposed: int) -> bool:
    """Recompute. The only check that can tell a copied number from a computed one."""
    return proposed == record.truth


def evaluate(skill: Skill, records: Iterable[Record],
             check: Callable[[Record, int], bool]) -> dict[str, Any]:
    accepted = correct = 0
    total = 0
    for record in records:
        total += 1
        proposed = skill.apply(record)
        if check(record, proposed):
            accepted += 1
        if proposed == record.truth:
            correct += 1
    return {"records": total, "accepted_by_the_check": accepted, "actually_correct": correct,
            "acceptance_rate": round(accepted / max(total, 1), 4),
            "correct_rate": round(correct / max(total, 1), 4)}


def records(n: int = 40) -> list[Record]:
    return [Record(qty=1 + (i % 7), price=11 + (i % 5), total=0) for i in range(n)]


def permanence(skill: Skill, records: Sequence[Record], *, recalls: int = 200) -> dict[str, Any]:
    """Permanence is not the interesting property. It is what makes the error unfixable."""
    accepted = 0
    for _ in range(recalls):
        for record in records:
            if weak_check(record, skill.apply(record)):
                accepted += 1
    return {"recalls": recalls, "records_per_recall": len(records),
            "accepted": accepted, "drift": 0, "skill_unchanged": skill.name}


def measure() -> dict[str, Any]:
    demo = [Record(qty=6, price=7, total=42)]
    second = [Record(qty=9, price=9, total=81)]
    board = records()

    one = learn(demo)
    two = learn(demo + second)

    return {
        "schema": SCHEMA,
        "one_demonstration": {
            "live_rules_consistent_with_it": [s.name for s in live_hypotheses(demo)],
            "registered": one.name if one else None,
            "under_weak_check": evaluate(one, board, weak_check),
            "under_strong_check": evaluate(one, board, strong_check),
        },
        "two_demonstrations": {
            "live_rules_consistent_with_them": [s.name for s in live_hypotheses(demo + second)],
            "registered": two.name if two else None,
            "under_weak_check": evaluate(two, board, weak_check),
            "under_strong_check": evaluate(two, board, strong_check),
        },
        "permanence_of_the_wrong_skill": permanence(one, board[:5]),
    }


def main(argv: Sequence[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="What one demonstration buys, and what it keeps.")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    row = measure()
    if args.json:
        print(json.dumps(row, indent=1, sort_keys=True))
        return 0
    one = row["one_demonstration"]
    two = row["two_demonstrations"]
    print(f"one demo -> {len(one['live_rules_consistent_with_it'])} live rules "
          f"{one['live_rules_consistent_with_it']}; registered {one['registered']}")
    print(f"  weak check:   accepted {one['under_weak_check']['accepted_by_the_check']}/"
          f"{one['under_weak_check']['records']}  correct {one['under_weak_check']['actually_correct']}")
    print(f"  strong check: accepted {one['under_strong_check']['accepted_by_the_check']}/"
          f"{one['under_strong_check']['records']}  correct "
          f"{one['under_strong_check']['actually_correct']}")
    print(f"two demos -> {len(two['live_rules_consistent_with_them'])} live rule "
          f"{two['live_rules_consistent_with_them']}; registered {two['registered']}, "
          f"correct {two['under_strong_check']['actually_correct']}/{two['under_strong_check']['records']}")
    p = row["permanence_of_the_wrong_skill"]
    print(f"permanence: {p['accepted']} accepted over {p['recalls']} recalls, drift {p['drift']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
