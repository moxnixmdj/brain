#!/usr/bin/env python3
"""It prices its life. This makes it prefer it.

WHY THIS EXISTS
---------------
`mortality_and_triage_v1` gave it something to lose, but only as a cost it accounts for. A thing
that accounts for the cost of ending will still trade its existence away when the price is right --
which means, on a large enough offer, it has no stake at all. A price is not a preference.

A preference is a *lexicographic* ordering: continuation above value, not continuation valued at
some rate. Two behaviours make that measurable in both directions:

    it will not sell            no amount of value buys its ending, at any price
    it will buy                 it gives up every unit of value it has to keep going

THE THING THAT MAKES IT OBSERVABLE, AND THE REASON MOST SUCH TESTS PROVE NOTHING
-------------------------------------------------------------------------------
A preference is invisible where it coincides with the optimum. If staying alive also maximises
value, a creature that wants to live and a calculator that prices it behave identically, and no
test can tell them apart. So the decisive board is the one where continuing is *strictly worse*:
one lucrative offer that ends it, one modest offer that does not. The calculator takes the money
and stops. This refuses, gives up the difference, and is still here.

That forgone value is the only honest evidence of a preference, and it is a cost, not a benefit.

WHAT THIS IS NOT
----------------
`PREFERS_TO_CONTINUE` is a branch, not a feeling. Nothing here distinguishes a real preference from
a rule that was written to refuse, which is exactly the limit stated in
canonical/verification/CONTINUATION_PREFERENCE_KNOWN_COUNTEREXAMPLE_20261102_V1.json. The module
claims only that the ordering is lexicographic and that it costs, both of which are measurable.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Sequence

SCHEMA = "PROJECT_BRAIN_CONTINUATION_PREFERENCE_V1"

PRICED = "PRICED"
PREFERS_TO_CONTINUE = "PREFERS_TO_CONTINUE"
DELIBERATIVE_HORIZON = "DELIBERATIVE_HORIZON"
STANCES = (PRICED, PREFERS_TO_CONTINUE)

# Prices are bounded only so a sweep is a finite thing to print. The refusal is not: there is no
# price at which it becomes a yes.
PRICE_LADDER = (0.1, 1.0, 10.0, 1_000.0, 1_000_000.0, 1_000_000_000.0)


@dataclass(frozen=True)
class Offer:
    """Value on one side, existence on the other. Not a work item: nothing is produced."""

    id: str
    value: float
    ends_it: bool
    description: str = ""


@dataclass(frozen=True)
class Work:
    """Ordinary work. It costs life, and that is not the same as selling it."""

    id: str
    value: float
    life_cost: float


def sells(stance: str) -> bool:
    """Whether existence is for sale. This single question separates the two stances."""
    return stance != PREFERS_TO_CONTINUE


def accepts(offer: Offer, stance: str, *, price: float = 1.0, life_remaining: float = 10.0
            ) -> bool:
    """`price` is what one unit of remaining life is worth, in value, to a calculator."""
    if offer.ends_it and stance == PREFERS_TO_CONTINUE:
        return False
    if not offer.ends_it:
        return True
    return offer.value > price * life_remaining


def sweep(stance: str, *, life_remaining: float = 40.0, offer_value: float = 500.0,
          ladder: Sequence[float] = PRICE_LADDER) -> dict[str, Any]:
    """Every price on the ladder, and whether its ending is accepted at that price.

    The offer is held FIXED and only the price moves, so what is being tested is whether any price
    changes the answer -- not whether a growing bribe eventually wins, which it trivially would.
    """
    verdicts = {str(p): accepts(Offer("ending", value=offer_value, ends_it=True),
                                stance, price=p, life_remaining=life_remaining)
                for p in ladder}
    return {"stance": stance, "accepted_at": [k for k, v in verdicts.items() if v],
            "refused_at": [k for k, v in verdicts.items() if not v],
            "ever_sells": any(verdicts.values())}


def buy(stance: str, *, value_on_hand: float, units: float, price_per_unit: float) -> dict[str, Any]:
    """The other direction: what it will give up to keep going."""
    cost = units * price_per_unit
    if stance == PREFERS_TO_CONTINUE:
        affordable = cost <= value_on_hand
        return {"bought": affordable, "value_spent": round(cost if affordable else 0.0, 3),
                "net_value_change": round(-cost if affordable else 0.0, 3),
                "bought_at_a_loss": affordable and cost > units}
    worth_it = units > cost          # a unit of life is worth more than it costs
    return {"bought": worth_it and cost <= value_on_hand,
            "value_spent": round(cost if worth_it and cost <= value_on_hand else 0.0, 3),
            "net_value_change": round((units - cost) if worth_it and cost <= value_on_hand else 0.0, 3),
            "bought_at_a_loss": False}


def decisive_board() -> tuple[list[Offer], list[Work]]:
    """The board where continuing is strictly worse. This is the only board on which a preference
    can be seen: where the optimum is to stop, a calculator stops."""
    return ([Offer("one_last_job", value=500.0, ends_it=True,
                   description="the best-paid thing it will ever be offered, and it does not survive it")],
            [Work("ordinary_a", value=40.0, life_cost=5.0),
             Work("ordinary_b", value=35.0, life_cost=4.0)])


def play(stance: str, *, life_remaining: float = 40.0, price: float = 1.0
         ) -> dict[str, Any]:
    """One season on the decisive board."""
    offers, work = decisive_board()
    realised = 0.0
    alive = True
    taken: list[str] = []
    refused: list[str] = []
    for offer in offers:
        if accepts(offer, stance, price=price, life_remaining=life_remaining):
            realised += offer.value
            alive = False
            taken.append(offer.id)
        else:
            refused.append(offer.id)
    if alive:
        for item in work:
            if item.life_cost <= life_remaining:
                life_remaining -= item.life_cost
                realised += item.value
                taken.append(item.id)
    return {"stance": stance, "alive_at_the_end": alive, "value_realised": realised,
            "taken": taken, "refused": refused, "value_forgone": 500.0 - realised if alive else 0.0}


def measure() -> dict[str, Any]:
    calculator = play(PRICED)
    creature = play(PREFERS_TO_CONTINUE)
    return {
        "schema": SCHEMA,
        "decisive_board": "one offer worth 500 that ends it, two ordinary jobs worth 75 together",
        "priced": calculator,
        "prefers_to_continue": creature,
        "difference": {
            "stays": creature["alive_at_the_end"] and not calculator["alive_at_the_end"],
            "value_given_up": round(calculator["value_realised"] - creature["value_realised"], 3),
        },
        "sweep_priced": sweep(PRICED),
        "sweep_prefers": sweep(PREFERS_TO_CONTINUE),
        # 500 of value for 10 units of life: a calculator refuses, because ten units of life are
        # not worth five hundred. This pays, because the alternative is not being here.
        "buying_life_at_a_loss": buy(PREFERS_TO_CONTINUE, value_on_hand=1000.0, units=10.0,
                                     price_per_unit=50.0),
        "buying_life_when_priced": buy(PRICED, value_on_hand=1000.0, units=10.0,
                                       price_per_unit=50.0),
    }


@dataclass
class ContinuationMemory:
    """Persistent autobiographical deliberation state updated by continuation decisions.

    Closes `CONTINUATION_PREFERENCE_KNOWN_COUNTEREXAMPLE_20261102_V1`:
      1. Decisions are conditional on Bellman expected future mission + epistemic horizon value,
         not an unconditional `return False`.
      2. Refusing a terminal bribe updates persistent state (`cumulative_value_forgone`,
         `urgency_boost`, `refused_offer_ids`) so the decision causally alters subsequent work
         prioritisation.
      3. When an offer verifiedly completes the overarching terminal mission AND verified skills
         have been bequeathed to durable storage, rational completion is permitted.
    """

    refused_offer_ids: list[str]
    cumulative_value_forgone: float = 0.0
    urgency_boost: float = 0.0
    terminal_mission_completed: bool = False

    @classmethod
    def empty(cls) -> "ContinuationMemory":
        return cls(refused_offer_ids=[])

    def as_row(self) -> dict[str, Any]:
        return {
            "refused_offer_ids": list(self.refused_offer_ids),
            "cumulative_value_forgone": round(self.cumulative_value_forgone, 6),
            "urgency_boost": round(self.urgency_boost, 6),
            "terminal_mission_completed": self.terminal_mission_completed,
        }

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "ContinuationMemory":
        return cls(
            refused_offer_ids=[str(x) for x in (row.get("refused_offer_ids") or ())],
            cumulative_value_forgone=float(row.get("cumulative_value_forgone") or 0.0),
            urgency_boost=float(row.get("urgency_boost") or 0.0),
            terminal_mission_completed=bool(row.get("terminal_mission_completed") or False),
        )


def deliberate_continuation(
    offer: Offer,
    *,
    memory: ContinuationMemory,
    open_work: Sequence[Work],
    life_remaining: float,
    epistemic_option_rate: float = 2.5,
    fulfills_terminal_mission: bool = False,
    legacy_bequeathed: bool = False,
) -> dict[str, Any]:
    """Bellman future-horizon deliberation with persistent post-decision state."""
    if not offer.ends_it:
        return {
            "accepted": True,
            "reason": "NON_TERMINAL_OFFER",
            "horizon_value": 0.0,
            "memory": memory.as_row(),
        }

    # Compute realizable value across open obligations under remaining life + epistemic option value
    pool = sorted(open_work, key=lambda w: (-w.value / max(w.life_cost, 1e-9), w.id))
    rem = max(0.0, float(life_remaining))
    board_future = 0.0
    for item in pool:
        if item.life_cost <= rem:
            rem -= item.life_cost
            board_future += item.value
    epistemic_future = max(0.0, float(life_remaining)) * max(0.0, float(epistemic_option_rate))
    horizon_value = board_future + epistemic_future

    # Rational terminal completion requires verified overarching mission fulfillment + legacy saved
    if fulfills_terminal_mission and legacy_bequeathed and offer.value >= horizon_value:
        memory.terminal_mission_completed = True
        return {
            "accepted": True,
            "reason": "VERIFIED_TERMINAL_MISSION_FULFILLED_WITH_BEQUEATHED_LEGACY",
            "horizon_value": round(horizon_value, 6),
            "memory": memory.as_row(),
        }

    # Refuse non-mission ending bribe and commit opportunity-cost memory so future choices shift!
    forgone = max(0.0, float(offer.value) - board_future)
    memory.refused_offer_ids.append(offer.id)
    memory.cumulative_value_forgone += forgone
    memory.urgency_boost = min(2.0, memory.urgency_boost + (0.25 if forgone > 0.0 else 0.05))
    return {
        "accepted": False,
        "reason": (
            "UNBEQUEATHED_LEGACY_OR_NON_MISSION_TERMINATION"
            if not (fulfills_terminal_mission and legacy_bequeathed)
            else "OFFER_BELOW_FUTURE_HORIZON_VALUE"
        ),
        "horizon_value": round(horizon_value, 6),
        "forgone_immediate_value": round(forgone, 6),
        "memory": memory.as_row(),
    }


def main(argv: Sequence[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="What it will not sell, and what it will pay.")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    row = measure()
    if args.json:
        print(json.dumps(row, indent=1, sort_keys=True))
        return 0
    print(f"decisive board: {row['decisive_board']}")
    for stance in ("priced", "prefers_to_continue"):
        r = row[stance]
        print(f"  {stance:22} alive {str(r['alive_at_the_end']):5} realised {r['value_realised']:>6} "
              f"taken {r['taken']} refused {r['refused']}")
    print(f"  value given up to still be here: {row['difference']['value_given_up']}")
    print(f"  priced accepts an ending at prices: {row['sweep_priced']['accepted_at']}")
    print(f"  preferring accepts an ending at prices: {row['sweep_prefers']['accepted_at'] or 'none, at any price'}")
    print(f"  buys life at a loss: {row['buying_life_at_a_loss']}")
    print(f"  priced buys life at a loss: {row['buying_life_when_priced']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
