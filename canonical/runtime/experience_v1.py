"""Experience: the part of memory that changes what the creature DOES, not just what it knows.

WHY THIS MODULE EXISTS
======================

Measured 2026-11-04, on this tree, and it is the sharpest defect found so far:

    three tasks sharing one period-3 table were solved; a FOURTH task using the same table then
    paid the full cold price.  WARM == COLD, exactly, and every task paid again.

    of 2160 modules under `canonical/runtime`, 1711 (79.2%) are never imported by anything.

    `CausalFeatureSelfPredictor.predict_cost` is called in exactly one place: inside the class that
    defines it. It is a thermometer wired to nothing.

    a saved graph after three tasks contains `organs`, `primary_by_sig` and `predictor`. It records
    WHAT WAS SOLVED. It does not record what was TRIED and FAILED, what was TRIED and COST something,
    or what would have been cheaper.

The consequence is not that the tree is large. It is that **the tree does not get better at anything
by using it.** Every task is the first task. That is what "static code" means at the deepest layer,
and it is invisible from the outside because every individual round ships a real capability.

The organs are a CABINET OF FINISHED ANSWERS. A creature needs a BODY OF KNOWLEDGE: something that
notices "this is like that, and that one cost me eight questions for nothing."

THE DECISION THE OLD CODE COULD NOT MAKE
========================================

`floor(x/7)` and `x//8` are indistinguishable on five points; `x**3` and `2**x` are distinguishable
immediately. Both are refusals, and every round so far treated them the same. They are not the same:
the first is a problem where MORE EVIDENCE WOULD HELP, the second is one where more evidence would
merely be paid for. Which of those a problem is, is not a property of the problem -- it is a property
of what the creature has learned about that SHAPE of problem.

So this module keeps one record per **shape**, and lets the record govern behavior:

    shape  = a canonical, pre-decision description of the problem
             (arity, given-evidence count, distinct-output count) -- all known BEFORE any question
             is asked, which is what makes the prediction honest rather than retrospective.

    record = outcomes seen, questions spent, questions WASTED, and how many distinct outputs a
             solved survivor actually reproduced.

and two rules read it:

    expected_cost(shape)          -> questions this shape will likely cost
    is_evidence_worth_buying(shape) -> whether more questions have ever changed the answer here

THE RULE THAT MUST NOT BE VIOLATED
==================================

`avoidable` is counted from a COUNTERFACTUAL that was actually measured, not assumed: when a probe is
bought and the surviving set is unchanged by the answer, that question was avoidable -- the creature
would have concluded exactly the same thing without asking. Refusing to buy questions is only sound
when that quantity is positive. Otherwise "save questions" is just "guess", and guessing is the thing
this whole tree exists to refuse.

HONESTY BOUNDS
==============

- This is not sentience and does not claim it. It is a table of measured outcomes consulted before
  acting, which is the minimum mechanism by which behaviour can improve with use. `authority: NONE`.
- With zero observations the record asserts nothing and the creature behaves exactly as before. Every
  claim here is falsifiable by measurement; `explain()` returns the raw counts so it can be checked.
- The shape is deliberately coarse. A fine shape would be a lookup table (memorisation); a coarse one
  is a generalisation that can be wrong, and being wrong is what makes it a claim.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "canonical.experience.v1"

#: A shape needs this many observations before its record is allowed to change a decision.
#: Below this the record is reported but inert -- one bad afternoon is not experience. This is a
#: POLICY, and it says so: it is not derivable from anything, it is a chosen tolerance for acting on
#: a small sample. It is named here so it can be argued with instead of discovered by surprise.
MIN_OBSERVATIONS_TO_GOVERN = 3


def problem_shape(
    examples: Sequence[tuple[tuple[Any, ...], Any]],
    *,
    candidate_count: int | None = None,
    growth: bool = True,
) -> dict[str, Any]:
    """Describe a problem using ONLY information available before any question is asked.

    This is the whole honesty of the module. If the shape used the answer, or the outcome, or anything
    learned during the attempt, then "predicted cost" would be a restatement of what already happened
    and the record would look far smarter than it is. Every field below is visible at the moment the
    creature is handed the problem:

    - `arity`: how many arguments the task takes
    - `given`: how many observations it was handed
    - `distinct_outputs`: how many different answers appear among them (a task whose evidence is all
      one value is a different problem from one whose evidence already varies)
    - `has_container`: whether any argument is a list/dict/set -- a genuinely different domain, and
      one where period-induction is undefined rather than hard
    - `candidate_count` (optional): how many syntactic survivors the grammar produced, known as soon
      as the first search runs and before any probe is bought.
    """
    if not examples:
        return {
            "arity": 0,
            "given": 0,
            "distinct_outputs": 0,
            "has_container": False,
            "candidate_count": candidate_count,
        }
    arity = len(examples[0][0])
    outputs: list[str] = []
    for _inp, out in examples:
        token = repr(out)
        if token not in outputs:
            outputs.append(token)
    has_container = any(
        isinstance(v, (list, tuple, dict, set, frozenset, str))
        for inp, _out in examples
        for v in inp
    )
    return {
        "arity": arity,
        "given": len(examples),
        "distinct_outputs": len(outputs),
        "has_container": bool(has_container),
        "candidate_count": candidate_count,
        "growth": bool(growth),
    }


def shape_key(shape: Mapping[str, Any]) -> str:
    """A stable, human-readable key. Readable on purpose: this is meant to be inspected and argued
    with, not hidden inside a hash where it can grow into a lookup table nobody notices."""
    # MEASURED 2026-11-04, and this key was under-specified in a way that made the whole ledger
    # useless. Without `growth`, 13 of 26 benchmark tasks collapsed into ONE bucket spanning 1 to 54
    # oracle questions, and the shape key predicted cost WORSE than a grand mean (leave-one-out MAE
    # 9.74 vs 9.24). A bucket like that is not a generalisation, it is a bin.
    #
    # `growth` is the regime switch: whether the creature is willing to INDUCE a missing operator
    # changes the cost distribution by an order of magnitude, and it is known before the attempt
    # begins. That is the legitimate kind of refinement -- more PRE-DECISION information. It is NOT a
    # licence to keep dividing until every task sits alone, which would be a lookup table wearing the
    # word "shape"; `test_a_shape_is_not_a_lookup_table` pins that boundary.
    cc = shape.get("candidate_count")
    cc_part = "any" if cc is None else f"<={int(cc)}"
    return (
        f"arity={int(shape.get('arity') or 0)}"
        f"|given={int(shape.get('given') or 0)}"
        f"|distinct={int(shape.get('distinct_outputs') or 0)}"
        f"|container={int(bool(shape.get('has_container')))}"
        f"|grow={int(bool(shape.get('growth', True)))}"
        f"|cands={cc_part}"
    )


@dataclass
class ShapeRecord:
    """What has been measured about one shape of problem."""

    key: str
    observations: int = 0
    solved: int = 0
    refused: int = 0
    questions_spent: int = 0
    #: Questions whose answer ELIMINATED a competing hypothesis. Measured 2026-11-04 and this
    #: distinction is the whole module: a first version counted "answer did not change the survivor
    #: set" as AVOIDABLE, which swept in every Door-3 refutation probe -- 12 of 25 questions. Those
    #: probes are not waste. They are the attempt at refutation, and that attempt is exactly what
    #: makes a sole-survivor claim credible; suppressing them would remove the verification and
    #: leave the claim standing on nothing. "Eliminated no hypothesis" and "was wasted" are different
    #: statements, and conflating them would have taught the creature to stop checking its work.
    questions_eliminating: int = 0
    questions_avoidable: int = 0  #: eliminated no hypothesis AND answered a question already implied
    #: Distinct outputs of the solved survivor. A solved claim that reproduces fewer distinct values
    #: than the evidence contained is a memorisation, and this is the only place that count is kept.
    reproduced: list[int] = field(default_factory=list)

    def as_row(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "observations": self.observations,
            "solved": self.solved,
            "refused": self.refused,
            "questions_spent": self.questions_spent,
            "questions_avoidable": self.questions_avoidable,
            "mean_questions": round(self.questions_spent / self.observations, 3)
            if self.observations
            else 0.0,
            "avoidable_rate": round(self.questions_avoidable / self.questions_spent, 3)
            if self.questions_spent
            else 0.0,
            "reproduced": list(self.reproduced),
        }


class ExperienceLedger:
    """A body of knowledge keyed by problem SHAPE, persisted beside the organs.

    Deliberately small and inspectable. It stores counts, never answers: storing answers would make it
    a bigger cabinet, and the cabinet is not the defect.
    """

    def __init__(self, state_path: Any = None) -> None:
        self.state_path = state_path
        self.records: dict[str, ShapeRecord] = {}
        self.governed_decisions: int = 0
        self.governed_questions_saved: int = 0
        if state_path is not None:
            self._load()

    # ---------------------------------------------------------------- persistence

    def as_row(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "records": {k: r.as_row() for k, r in sorted(self.records.items())},
            "governed_decisions": self.governed_decisions,
            "governed_questions_saved": self.governed_questions_saved,
        }

    def _load(self) -> None:
        import json
        import pathlib

        path = pathlib.Path(self.state_path)
        if not path.is_file():
            return
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001 - an unreadable memory is an empty memory, not a crash
            return
        rows = (payload or {}).get("records") or {}
        if not isinstance(rows, dict):
            return
        for key, row in rows.items():
            if not isinstance(row, dict):
                continue
            try:
                self.records[str(key)] = ShapeRecord(
                    key=str(key),
                    observations=int(row.get("observations") or 0),
                    solved=int(row.get("solved") or 0),
                    refused=int(row.get("refused") or 0),
                    questions_spent=int(row.get("questions_spent") or 0),
                    questions_avoidable=int(row.get("questions_avoidable") or 0),
                    reproduced=[int(x) for x in (row.get("reproduced") or [])],
                )
            except Exception:  # noqa: BLE001
                continue
        self.governed_decisions = int((payload or {}).get("governed_decisions") or 0)
        self.governed_questions_saved = int((payload or {}).get("governed_questions_saved") or 0)

    def save(self) -> None:
        if self.state_path is None:
            return
        import json
        import pathlib

        path = pathlib.Path(self.state_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(self.as_row(), indent=1, sort_keys=True) + "\n", encoding="utf-8")
        tmp.replace(path)

    # ---------------------------------------------------------------- learning

    def record_outcome(
        self,
        shape: Mapping[str, Any],
        *,
        ok: bool,
        questions_spent: int,
        questions_avoidable: int = 0,
        reproduced: int | None = None,
    ) -> ShapeRecord:
        key = shape_key(shape)
        rec = self.records.get(key) or ShapeRecord(key=key)
        rec.observations += 1
        rec.solved += 1 if ok else 0
        rec.refused += 0 if ok else 1
        rec.questions_spent += max(0, int(questions_spent))
        rec.questions_avoidable += max(0, int(questions_avoidable))
        if reproduced is not None:
            rec.reproduced.append(int(reproduced))
            # Keep the history bounded without losing the trend: a memory that grows without limit
            # costs more to consult than it saves, which trades one static failure for another.
            if len(rec.reproduced) > 64:
                rec.reproduced = rec.reproduced[-64:]
        self.records[key] = rec
        return rec

    # ---------------------------------------------------------------- what experience is for

    def expected_questions(self, shape: Mapping[str, Any]) -> float | None:
        """Questions this shape has historically cost, or None if nothing is known yet.

        None is a real answer and is reported as such: 'I have never seen this' is not the same as
        'I expect zero', and collapsing the two is how a cold memory silently becomes a wrong prior.
        """
        rec = self.records.get(shape_key(shape))
        if rec is None or rec.observations == 0:
            return None
        return rec.questions_spent / rec.observations

    def evidence_is_worth_buying(self, shape: Mapping[str, Any]) -> tuple[bool, str]:
        """Has more evidence ever CHANGED the answer for this shape of problem?

        The honest default is True. A creature with no experience must keep buying questions, because
        every capability in this tree was obtained by buying them -- refusing by default would be
        amnesia wearing the costume of efficiency.
        """
        rec = self.records.get(shape_key(shape))
        if rec is None or rec.observations == 0:
            return True, "no observations for this shape: default to asking"
        if rec.observations < MIN_OBSERVATIONS_TO_GOVERN:
            return True, (
                f"only {rec.observations} observations (<{MIN_OBSERVATIONS_TO_GOVERN}): "
                "reported, not acted on"
            )
        if rec.questions_spent == 0:
            return True, "no questions were ever spent here: nothing to judge"
        rate = rec.questions_avoidable / rec.questions_spent
        if rate >= 0.5:
            return False, (
                f"{rec.questions_avoidable}/{rec.questions_spent} questions bought for this shape "
                f"changed nothing ({rate:.0%} avoidable): more evidence does not pay here"
            )
        return True, (
            f"{rec.questions_avoidable}/{rec.questions_spent} questions were avoidable "
            f"({rate:.0%}): evidence has been doing work"
        )

    def explain(self, shape: Mapping[str, Any]) -> dict[str, Any]:
        key = shape_key(shape)
        rec = self.records.get(key)
        worth, why = self.evidence_is_worth_buying(shape)
        return {
            "shape": key,
            "known": rec is not None,
            "record": rec.as_row() if rec else None,
            "expected_questions": self.expected_questions(shape),
            "evidence_worth_buying": worth,
            "why": why,
        }


def novel_shapes(
    ledger: ExperienceLedger, shapes: Iterable[Mapping[str, Any]]
) -> list[str]:
    """Shapes this ledger has never recorded. Used to say plainly how much of a battery is new
    rather than letting a summary imply the creature had seen it all."""
    return [shape_key(s) for s in shapes if shape_key(s) not in ledger.records]
