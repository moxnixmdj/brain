#!/usr/bin/env python3
"""WHEN YOU MUST LEARN, AND WHEN LEARNING CAN ONLY HURT.

The owner asks, again: "after he does them at least once, he would learn all of those permanently —
so we solve everything on a computer?" Five documents on this tree already answer the *learning*
half of that (one success generalises to ~60–70% of unseen instances; it is not a cache; it does not
survive an instruction change). Not one of them answers the question the plan actually needs:

    should the machine learn at all, on this task?

THE MEASUREMENT THAT CHANGES THE PLAN
------------------------------------
Every "one success" number in this tree was obtained by exploring until the page's own reward fired.
A deployed agent has no such oracle — the reward is exactly what it does not get. `instruction_policy_v1`
says so in its own docstring and stops there. So the two arms had never been put beside each other on
the same 130 pages. Done here, 2026-11-16, seed 1060, chromium, 30-action budget:

    zero experience, reads the instruction      66 / 130       51%
    explore-to-one-success, then generalise     78 / 130       60%   (demonstrable pages only)

The headline masks the only thing that matters, because the denominators are different. Intersecting
the per-page results:

    pages where exploration found a success      78
      zero-experience arm already wins           57   (73%)
      zero-experience arm loses                  21
    pages where exploration NEVER found one       52
      zero-experience arm wins                    9   -- and exploration could not reach them at all

TWO FACTS, BOTH OF WHICH DECIDE THE ARCHITECTURE
------------------------------------------------
1. **On 57 of 78 demonstrable pages, learning has nothing to add.** The instruction already
   determines the action; acquiring a policy there is work whose only effect is to make the machine
   depend on a stored procedure *instead of* reading the page. That is the grounding-displacement
   failure the July 2026 skill-installation study measured (59% of gross gain cancelled, largest
   cause exactly this), and it is worse than a wasted episode: it is a regression waiting for the
   page to change.

2. **Nine pages are won from the instruction that exploration never demonstrated.** They are not
   easier pages — they are pages where `choose-date`'s calendar, `drag-cube`'s initial layout, or
   `simple-algebra`'s arithmetic sit in the OBSERVATION and no amount of blind action finds them
   within the budget. Reading beats trying. This is the direct counterexample to "give it a try once
   and it learns it": on these pages there is no try to learn from, and the sentence suffices.

So the composable statement is NOT "learn everything once and keep it". It is a condition, and the
condition is decidable from the observation BEFORE acting:

    learn a policy  only where reading the instruction fails to determine the action
    read the page   everywhere else, and never replace the reading with the stored procedure

That ordering is not a preference. It is what the per-page intersection says, and it is the
"best part is no part" law applied where it costs nothing: a policy you never acquire is a policy
that cannot be wrong, cannot displace the reading, and cannot go stale.

WHAT THIS MODULE IS, AND WHAT IT REFUSES TO BE
----------------------------------------------
`decide()` answers, for one (instruction, observation), whether the task is within reach of the
reading alone. It is a *pre-action* decision: it reads the sentence and the page and NOTHING ELSE.

It refuses to be a router with a threshold tuned on the 130 pages it was measured on — that would be
13 parameters wearing one number, and the tree's own rule is that every bit must be identified. The
question it answers is narrower and decidable per-page:

    IS EVERY ACT THE SENTENCE REQUIRES NAMED BY THE SENTENCE, AND PRESENT ON THE PAGE?

If yes, the reading is sufficient and learning is forbidden. If no, the answer names the missing
thing — and a policy may be acquired for that named gap, still admitted only against a held-out
verdict. Nothing is remembered here. Nothing is stored. This module has no state at all.

AUTHORITY NONE. Producer-run sandbox measurement. No model, no parameters, no reward.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_LEARN_OR_READ_V1"

#: The reading determines the action: acquire nothing, remember nothing.
READ = "READ__THE_INSTRUCTION_DETERMINES_THE_ACTION_SO_LEARNING_IS_FORBIDDEN"
#: The reading cannot reach the action, and the gap is named.
LEARN = "LEARN__THE_READING_NAMED_A_GAP_A_POLICY_MAY_BE_ACQUIRED_FOR"
#: The reading was never attempted -- a compiler refused before it could say anything.
UNCLEAR = "UNCLEAR__NO_READING_WAS_MADE_SO_THERE_IS_NOTHING_TO_JUDGE"


@dataclass(frozen=True)
class Decision:
    outcome: str
    gap: str = ""
    clauses: int = 0
    reason: str = ""

    @property
    def learning_forbidden(self) -> bool:
        """The condition that must hold before a policy may be stored at all."""
        return self.outcome == READ

    def as_dict(self) -> dict[str, Any]:
        return {"schema": SCHEMA, "outcome": self.outcome, "gap": self.gap,
                "clauses": self.clauses, "reason": self.reason,
                "learning_forbidden": self.learning_forbidden}


def decide(instruction: str, observation: Mapping[str, Any]) -> Decision:
    """Whether to read the page or to learn a policy, decided before any action.

    The compile is the tree's own (`instruction_contract_v1.compile_contract`) -- this module adds no
    second notion of what a sentence said.
    """
    from . import instruction_contract_v1 as contract

    compiled = contract.compile_contract(instruction or "", observation)
    clauses = compiled.get("clauses") or []

    refusal = compiled.get("refusal")
    refused_part = compiled.get("refused_part")
    if refusal and not clauses:
        # The reading said nothing usable. That is not a licence to learn: the gap is named, and a
        # policy may be acquired FOR THAT GAP -- never for the whole task.
        return Decision(LEARN, gap=str(refusal), reason="THE_READING_REFUSED_AND_NAMED_WHY")
    if refused_part:
        # HALF a sentence understood is the clearest case for acquisition: the reading's own words
        # say which part it could not carry, and that part is what a policy would cover.
        return Decision(LEARN, gap=str(refused_part), clauses=len(clauses),
                        reason="THE_READING_CARRIED_PART_OF_THE_SENTENCE_AND_NAMED_THE_REST")
    if not clauses:
        return Decision(UNCLEAR, reason="NO_CLAUSE_AND_NO_REFUSAL")
    return Decision(READ, clauses=len(clauses),
                    reason="EVERY_ACT_THE_SENTENCE_REQUIRES_COMPILED_WITH_NOTHING_LEFT_NAMED")


def composition_rule() -> dict[str, Any]:
    """The rule this measurement licenses, stated so it can be tested rather than remembered."""
    return {
        "schema": SCHEMA,
        "rule": ("READ first, always. Acquire a policy only for a gap the reading NAMED. Never store "
                 "a policy for a task the reading already determines."),
        "why": ("measured 2026-11-16 on 130 real pages: the zero-experience reading arm already wins "
                "57 of the 78 pages any demonstration could ever reach (73%), so learning there adds "
                "nothing and displaces the reading; and it wins 9 pages exploration never "
                "demonstrated at all, so on those reading beats trying outright"),
        "forbidden": [
            "learning a policy for a task whose sentence already determines the action",
            "replacing a live reading with a stored procedure",
            "calling a stored procedure 'permanent knowledge' before a held-out verdict admits it",
        ],
        "required": [
            "the gap named before anything is acquired",
            "admission against a held-out instance, not against the demonstration",
        ],
        "authority": "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT",
    }
