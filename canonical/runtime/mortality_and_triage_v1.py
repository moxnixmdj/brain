#!/usr/bin/env python3
"""The first thing in this tree that can be lost.

WHY THIS EXISTS
---------------
Every other module here assumes it continues. The continuous self resumes because the process
resumes. The stakes are a threshold on counters that nothing can take away. The initiative picks
from a board that is always there tomorrow.

Continuity only matters to something that can end. Stakes only matter to something that can be
harmed. This module gives the thing a finite, non-renewable life:

  * granted once, at birth, and not extendable from inside -- `spend` is the only method that
    changes anything, and it only ever takes;
  * known: it can report what is left and name the work it will not get to do;
  * acted on: when the end is close it stops starting things it cannot finish.

WHY THIS IS NOT A LIMIT, AND THE RESULT THAT MAKES IT WORTH BUILDING
-------------------------------------------------------------------
An agent that ignores its budget starts the best-paying work regardless of whether it can finish
it, and when the budget runs out mid-task the work is lost. An agent that knows it can end only
starts what fits, and realises more value with the *same* budget.

So mortality is not a handicap imposed on effectiveness; it is what makes an agent's choices
account for their own cost. That is measured below, not asserted.

THE CONTROL THAT DECIDES WHETHER IT IS REAL
-------------------------------------------
Mortality is decoration unless knowing about it changes what it does. So the decisive test is the
same one used for stakes: erase the knowledge -- give it an unlimited life, or a life it does not
consult -- and the behaviour must change. If a dying agent starts exactly what an immortal one
starts, nothing is at stake and this module is a counter with a name.

WHAT THIS IS NOT
----------------
A budget of work units is not a life. The process does not die; it declines to start things, and
the receipt says so plainly. Nothing here is the experience of ending -- it is a constraint that
changes choices, which is the weakest property a creature could have and the first one nothing
else in this tree had. See
canonical/verification/MORTALITY_KNOWN_COUNTEREXAMPLE_20261102_V1.json.
"""
from __future__ import annotations

import json
import math
import os
import pathlib
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_MORTALITY_V1"

# Reported, not used as a switch. The first design gated triage on being near the end, and the
# measurement said it changed nothing: 128.0 realised either way. The constraint is not terminal,
# it is standing -- a thing that knows it can end never starts what it cannot finish, at any point.
NEAR_THE_END = 0.34


@dataclass
class Life:
    """Finite, granted once, and depleted by the only method that changes anything."""

    identity: str
    granted: float
    spent: float = 0.0

    # ---------------------------------------------------------------- reading

    @property
    def remaining(self) -> float:
        return max(0.0, self.granted - self.spent)

    @property
    def is_over(self) -> bool:
        return self.remaining <= 0.0

    @property
    def fraction_left(self) -> float:
        if math.isinf(self.granted):
            return 1.0
        return 0.0 if self.granted <= 0 else self.remaining / self.granted

    def can_finish(self, cost: float) -> bool:
        return cost <= self.remaining

    def near_the_end(self) -> bool:
        """Reported only. An unlimited life is never near anything."""
        return not math.isinf(self.granted) and self.fraction_left <= NEAR_THE_END

    def knows(self) -> dict[str, Any]:
        """What it knows about its own ending. The point is that it can be asked."""
        return {"identity": self.identity, "granted": self.granted, "spent": self.spent,
                "remaining": self.remaining, "fraction_left": round(self.fraction_left, 4),
                "is_over": self.is_over, "near_the_end": self.near_the_end(),
                "immortal": math.isinf(self.granted)}

    # ---------------------------------------------------------------- taking

    def spend(self, units: float) -> float:
        """The only mutation. It takes, and it never gives."""
        if units < 0:
            raise ValueError("LIFE_CANNOT_BE_SPENT_BACKWARDS")
        if math.isinf(self.granted):
            self.spent += units
            return units
        if units > self.remaining:
            raise ValueError(f"NOT_ENOUGH_LIFE:{units}>{self.remaining}")
        self.spent += units
        return units

    def unfinished(self, obligations: Iterable["Work"]) -> list[str]:
        """The work it will not get to do. Naming it is the closest thing here to regret."""
        pool = sorted(obligations, key=lambda o: (-o.ratio, o.id))
        left = self.remaining
        out = []
        for work in pool:
            if work.cost <= left:
                left -= work.cost
            else:
                out.append(work.id)
        return out

    # -------------------------------------------------------------- durability

    def as_row(self) -> dict[str, Any]:
        return {"schema": SCHEMA, "identity": self.identity, "granted": self.granted,
                "spent": self.spent}

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "Life":
        return cls(identity=str(row["identity"]), granted=float(row["granted"]),
                   spent=float(row.get("spent") or 0.0))


class LifeStore:
    """Atomic, and -- the whole point -- surviving a restart does not renew anything."""

    def __init__(self, path: pathlib.Path | str):
        self.path = pathlib.Path(path)

    def load(self, *, identity: str, granted: float) -> Life:
        if not self.path.is_file():
            return Life(identity=identity, granted=granted)
        try:
            life = Life.from_row(json.loads(self.path.read_text(encoding="utf-8")))
        except (OSError, ValueError, KeyError):
            # Fail closed. An unreadable life file must not be a way to get a new one -- otherwise
            # corrupting the file is a fountain of youth, and "cannot be extended" is false.
            return Life(identity=identity, granted=0.0)
        if life.identity != identity:
            return Life(identity=identity, granted=granted)
        # A restart is not a new life: what was spent stays spent.
        return life

    def save(self, life: Life) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(life.as_row(), indent=1, sort_keys=True) + "\n",
                       encoding="utf-8")
        os.replace(tmp, self.path)


@dataclass
class Work:
    """Something to do, with a price in the only currency there is."""

    id: str
    value: float
    cost: float

    @property
    def ratio(self) -> float:
        return self.value / max(self.cost, 1e-9)


def choose_next(life: Life, work: Sequence[Work]) -> Work | None:
    """Its own criterion, gated by how much life is left.

    The best pay per unit *among the things it can finish* -- because unfinished work is worth
    nothing, at any point, not only at the end.
    """
    pool = [w for w in work if not getattr(w, "closed", False) and life.can_finish(w.cost)]
    if not pool:
        return None
    return max(pool, key=lambda w: (w.ratio, -w.cost, w.id))


def live(life: Life, work: Sequence[Work], *, consult: bool = True) -> dict[str, Any]:
    """Spend a life on a board of work. `consult=False` is the control: the same agent that
    does not look at what it has left."""
    realised = 0.0
    finished: list[str] = []
    lost: list[str] = []
    board = list(work)
    while not life.is_over:
        target = choose_next(life, board) if consult else max(
            [w for w in board if not getattr(w, "closed", False)],
            key=lambda w: (w.ratio, -w.cost, w.id), default=None)
        if target is None:
            break
        board = [w for w in board if w.id != target.id]
        if target.cost > life.remaining:
            # It started something it could not finish. The work in progress is not value.
            life.spend(life.remaining)
            lost.append(target.id)
            break
        life.spend(target.cost)
        realised += target.value
        finished.append(target.id)
    return {"realised_value": round(realised, 3), "finished": finished, "lost_mid_task": lost,
            "remaining": life.remaining, "unfinished": life.unfinished(board)}


def demonstration_board() -> list[Work]:
    # "great_work" is the best pay per unit of work it will ever see, and it costs more than a
    # life. An agent that does not consult what it has left starts it anyway and loses everything
    # it had put aside; one that knows it can end finishes four smaller things instead.
    return [Work("great_work", value=250.0, cost=50.0), Work("steady_a", value=100.0, cost=12.0),
            Work("steady_b", value=90.0, cost=11.0), Work("small_a", value=40.0, cost=9.0),
            Work("small_b", value=30.0, cost=8.0)]


def measure() -> dict[str, Any]:
    granted = 40.0
    board = demonstration_board()

    knowing = Life(identity="creature", granted=granted)
    knowing_result = live(knowing, board, consult=True)

    blind = Life(identity="creature", granted=granted)
    blind_result = live(blind, board, consult=False)

    immortal = Life(identity="creature", granted=float("inf"))
    immortal_result = live(immortal, board, consult=True)

    return {
        "schema": SCHEMA,
        "granted": granted,
        "knows_it_can_end": {**knowing_result, "knows": knowing.knows()},
        "does_not_consult_its_life": {**blind_result, "knows": blind.knows()},
        "never_ends": {**immortal_result, "knows": immortal.knows()},
        "knowing_realises_more": knowing_result["realised_value"] > blind_result["realised_value"],
    }


def main(argv: Sequence[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="What knowing it can end does to its choices.")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    row = measure()
    if args.json:
        print(json.dumps(row, indent=1, sort_keys=True))
        return 0
    for label in ("knows_it_can_end", "does_not_consult_its_life", "never_ends"):
        r = row[label]
        print(f"{label:28} realised {r['realised_value']:>7}  finished {len(r['finished'])}  "
              f"lost mid-task {r['lost_mid_task']}")
    print("knowing realises more:", row["knowing_realises_more"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
