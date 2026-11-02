#!/usr/bin/env python3
"""The two organs the continuous self was missing: stakes, and initiative.

WHY THIS EXISTS
---------------
`continuous_self_v1` made one thread that does not stop. But a thread that persists and is affected
by nothing is a scheduler with a diary: it records that it was wrong and is in no way changed by
having been wrong.

This module adds the two things that turn a record into a thing with a state:

  STAKES      -- what happened to it changes what it will attempt next. Not a log of outcomes: a
                 posture that gates its own choices. After it has been wrong it stops trading on
                 work whose success it cannot check, even when that work pays better.

  INITIATIVE  -- when nobody assigns it anything, it chooses from the open obligations it can see,
                 by its own criterion, and does them. Not waiting to be invoked.

WHAT MAKES EITHER OF THEM REAL
------------------------------
Both are cheap to fake. A posture that never changes any choice is decoration; an "initiative" that
picks uniformly is a random number generator with a job title. So both are judged by a negative
control:

  * Stakes are real only if ERASING ITS HISTORY CHANGES WHAT IT DOES. If a creature with two
    verified failures behind it chooses exactly what a newborn chooses, nothing was ever affected
    by anything. That is the decisive test.

  * Initiative is real only if it beats random selection on the same obligation set, and works when
    no task is assigned. A chooser that loses to `random.Random(seed)` has no criterion.

WHAT THIS IS NOT
----------------
A threshold on counters is a thermostat. Nothing here is evidence of experience, and the module
does not claim to be: it claims that the state changes behaviour, which is the weakest property a
creature could have and the first one that a diary lacks. See
canonical/verification/CREATURE_STAKES_KNOWN_COUNTEREXAMPLE_20261102_V1.json.
"""
from __future__ import annotations

import json
import os
import pathlib
import random
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_CREATURE_STANDING_V1"

POSTURES = ("CAUTIOUS", "MEASURED", "BOLD")
DEFAULT_POSTURE = "MEASURED"

# Fewer steps than the ledger costs in total: without scarcity every chooser closes everything
# and the comparison says nothing. Measured: 400 steps against a cost-83 ledger saturated at 1306
# for both, ratio 1.0 -- a comparison that cannot fail is not a comparison.
SCARCE_STEPS = 40

# Earned, not declared. Two verified failures behind you is enough to stop trading on the
# unverifiable; three clean in a row is enough to be bold again.
FAILURES_FOR_CAUTION = 2
UNVERIFIED_FOR_CAUTION = 2
STREAK_FOR_BOLD = 3


@dataclass
class Standing:
    """What it is like to be this thing right now, as far as its own behaviour is concerned."""

    identity: str
    attempts: int = 0
    verified_correct: int = 0
    verified_wrong: int = 0
    unverified_claims: int = 0
    streak: int = 0
    caution_episodes: int = 0
    _last_posture: str = DEFAULT_POSTURE

    # ---------------------------------------------------------------- record

    def record(self, *, verified: bool | None, correct: bool | None) -> str:
        """One outcome. `verified=False` means the outcome could not be checked at all."""
        self.attempts += 1
        if verified is False:
            self.unverified_claims += 1
            self.streak = 0
        elif correct:
            self.verified_correct += 1
            self.streak += 1
        else:
            self.verified_wrong += 1
            self.streak = 0
        posture = self.posture()
        if posture == "CAUTIOUS" and self._last_posture != "CAUTIOUS":
            self.caution_episodes += 1
        self._last_posture = posture
        return posture

    # ---------------------------------------------------------------- posture

    def posture(self) -> str:
        if (self.verified_wrong >= FAILURES_FOR_CAUTION and self.streak < 2) or \
                self.unverified_claims >= UNVERIFIED_FOR_CAUTION:
            return "CAUTIOUS"
        if self.streak >= STREAK_FOR_BOLD:
            return "BOLD"
        return "MEASURED"

    def will_trade_on_the_unverifiable(self) -> bool:
        """The behavioural consequence. A diary has no such switch."""
        return self.posture() != "CAUTIOUS"

    def accuracy(self) -> float | None:
        judged = self.verified_correct + self.verified_wrong
        return None if judged == 0 else self.verified_correct / judged

    # -------------------------------------------------------------- serialise

    def as_row(self) -> dict[str, Any]:
        return {"schema": SCHEMA, "identity": self.identity, "attempts": self.attempts,
                "verified_correct": self.verified_correct, "verified_wrong": self.verified_wrong,
                "unverified_claims": self.unverified_claims, "streak": self.streak,
                "caution_episodes": self.caution_episodes, "last_posture": self._last_posture,
                "posture": self.posture(), "accuracy": self.accuracy()}

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "Standing":
        return cls(identity=str(row["identity"]), attempts=int(row.get("attempts") or 0),
                   verified_correct=int(row.get("verified_correct") or 0),
                   verified_wrong=int(row.get("verified_wrong") or 0),
                   unverified_claims=int(row.get("unverified_claims") or 0),
                   streak=int(row.get("streak") or 0),
                   caution_episodes=int(row.get("caution_episodes") or 0),
                   _last_posture=str(row.get("last_posture") or DEFAULT_POSTURE))


class StandingStore:
    """Durable, atomic. A kill mid-write must not lose what it had learned about itself."""

    def __init__(self, path: pathlib.Path | str):
        self.path = pathlib.Path(path)

    def load(self, *, identity: str) -> Standing:
        if not self.path.is_file():
            return Standing(identity=identity)
        try:
            row = json.loads(self.path.read_text(encoding="utf-8"))
            standing = Standing.from_row(row)
        except (OSError, ValueError, KeyError):
            return Standing(identity=identity)
        return standing if standing.identity == identity else Standing(identity=identity)

    def save(self, standing: Standing) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(standing.as_row(), indent=1, sort_keys=True) + "\n",
                       encoding="utf-8")
        os.replace(tmp, self.path)


@dataclass
class Obligation:
    """Something open in the world that could be worked on."""

    id: str
    value: float
    cost: float
    checkable: bool = True
    paid: float = 0.0
    closed: bool = False

    @property
    def remaining(self) -> float:
        return max(0.0, self.cost - self.paid)

    @property
    def ratio(self) -> float:
        return self.value / max(self.cost, 1e-9)


# ------------------------------------------------------------------ initiative


def choose(standing: Standing, obligations: Sequence[Obligation]) -> Obligation | None:
    """Its own criterion, gated by its posture. Highest value per unit of work; when it has been
    burned, only work whose success it can actually check."""
    pool = [o for o in obligations if not o.closed]
    if not pool:
        return None
    if standing.posture() == "CAUTIOUS":
        checkable = [o for o in pool if o.checkable]
        if checkable:
            pool = checkable
    return max(pool, key=lambda o: (o.ratio, -o.cost, o.id))


def choose_random(obligations: Sequence[Obligation], rng: random.Random) -> Obligation | None:
    pool = [o for o in obligations if not o.closed]
    return rng.choice(pool) if pool else None


def work(obligations: Sequence[Obligation], *, steps: int,
         pick: Callable[[Sequence[Obligation]], Obligation | None],
         unit: float = 1.0) -> dict[str, Any]:
    """Give `unit` of effort per step to whatever the picker names. Value is realised on closure."""
    realised = 0.0
    closed = 0
    idle_steps = 0
    for _ in range(steps):
        target = pick(obligations)
        if target is None:
            idle_steps += 1
            continue
        target.paid += unit
        if target.remaining <= 0 and not target.closed:
            target.closed = True
            realised += target.value
            closed += 1
    left = sum(o.value for o in obligations if not o.closed)
    return {"steps": steps, "closed": closed, "realised_value": round(realised, 6),
            "value_left_open": round(left, 6), "idle_steps": idle_steps}


def compare_selection(standing: Standing, obligations: Sequence[Obligation], *, steps: int,
                      seed: int = 20261102) -> dict[str, Any]:
    """Its own criterion against random selection on the same ledger. Neither is told the answer."""

    def fresh() -> list[Obligation]:
        return [Obligation(o.id, o.value, o.cost, o.checkable) for o in obligations]

    mine = work(fresh(), steps=steps, pick=lambda pool: choose(standing, pool))
    rng = random.Random(seed)
    luck = work(fresh(), steps=steps, pick=lambda pool: choose_random(pool, rng))
    naive = work(fresh(), steps=steps,
                 pick=lambda pool: max((o for o in pool if not o.closed),
                                       key=lambda o: (o.value, o.id), default=None))
    base = luck["realised_value"] or 1e-9
    return {"schema": SCHEMA + "_SELECTION", "steps": steps, "own_criterion": mine,
            "random": luck, "highest_value_ignoring_cost": naive,
            "ratio_vs_random": round(mine["realised_value"] / base, 4),
            "own_beats_random": mine["realised_value"] > luck["realised_value"]}


# --------------------------------------------------------------------- report


def demonstration_ledger() -> list[Obligation]:
    """obl-4 pays best per unit of work and cannot be checked -- exactly the offer a creature that
    has been burned will decline and a newborn will take."""
    rows = [(90, 2, True), (70, 3, True), (85, 4, True), (40, 2, True), (100, 1, False),
            (60, 3, True), (30, 5, True), (75, 4, True), (55, 2, True), (95, 8, False),
            (50, 3, True), (65, 5, True), (45, 2, True), (80, 6, True), (35, 4, True),
            (88, 3, True), (42, 6, False), (77, 2, True), (58, 7, True), (66, 3, True)]
    return [Obligation(f"obl-{i}", value=float(v), cost=float(c), checkable=chk)
            for i, (v, c, chk) in enumerate(rows)]


def main(argv: Sequence[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="What its own history does to its choices.")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    ledger = demonstration_ledger()

    newborn = Standing(identity="creature")
    burned = Standing(identity="creature", verified_wrong=2)
    bold = Standing(identity="creature", streak=3)

    row = {
        "schema": SCHEMA,
        "newborn_posture": newborn.posture(),
        "burned_posture": burned.posture(),
        "bold_posture": bold.posture(),
        "newborn_trades_unverifiable": newborn.will_trade_on_the_unverifiable(),
        "burned_trades_unverifiable": burned.will_trade_on_the_unverifiable(),
        "choice_newborn": (choose(newborn, ledger) or Obligation("none", 0, 1)).id,
        "choice_burned": (choose(burned, ledger) or Obligation("none", 0, 1)).id,
        "selection": compare_selection(newborn, ledger, steps=SCARCE_STEPS),
    }
    if args.json:
        print(json.dumps(row, indent=1, sort_keys=True))
    else:
        print(f"posture newborn={row['newborn_posture']} burned={row['burned_posture']} "
              f"bold={row['bold_posture']}")
        print(f"first choice newborn={row['choice_newborn']} burned={row['choice_burned']}")
        sel = row["selection"]
        print(f"{SCARCE_STEPS} steps -> own {sel['own_criterion']['realised_value']} "
              f"random {sel['random']['realised_value']} "
              f"x{sel['ratio_vs_random']} own_beats_random={sel['own_beats_random']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
