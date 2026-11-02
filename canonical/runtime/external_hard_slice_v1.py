#!/usr/bin/env python3
"""The hard slice: work chosen by evidence the system does not get to curate.

WHY THIS EXISTS
---------------
The self-model is now scored, and a measured overconfidence refuses acceptance. The counterexample
recorded against that gate is the reason this module exists:

    the gate changes what is accepted, not what is predicted, so a refused system stops producing
    the very attempts it would need to escape the refusal.

A gate that blocks the evidence needed to lift it is a cage. The way out is not a lower threshold --
that is the forbidden move -- it is an external selection of what gets attempted, so the evidence
arrives whether or not the system would have chosen it.

THE RULE
--------
The slice is chosen from evidence the system does not produce:

  * inspector-verified failures, counted per capability from the settled prediction ledger;
  * capabilities with NO registered inspector, which count as fully unknown and are ranked first,
    because an unchecked capability is the largest possible gap in knowledge of oneself.

The system's own confidence is deliberately NOT an input to selection. It is an input to scoring --
the system states a probability before each attempt -- but if it picked the work, the sample would
be self-selected and the calibration number would be worth nothing.

A refusal does not stop the slice. Attempts still run; only acceptance is withheld, and the settled
outcome is recorded either way. That is what lets a refused system accumulate honest evidence.

WHAT THIS DOES NOT DO
---------------------
It does not make the system better at predicting itself. It only makes the sample honest. Whether
the resulting evidence is enough to lift a refusal is measured, not asserted, and the test that
ships with this module fails if it is not.

Nothing here calls a model. Nothing here spends.
"""
from __future__ import annotations

import pathlib
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_EXTERNAL_HARD_SLICE_V1"

DEFAULT_SLICE = 8
# A capability the system has failed this often is treated as hard regardless of its stated
# confidence, so a single bad day does not dominate the slice and a single lucky pass does not
# erase one.
HARD_AFTER_FAILURES = 2


class SliceError(ValueError):
    pass


@dataclass(frozen=True)
class Candidate:
    capability_id: str
    verified_failures: int
    verified_passes: int
    has_inspector: bool

    @property
    def attempts(self) -> int:
        return self.verified_failures + self.verified_passes

    @property
    def difficulty(self) -> tuple[int, float, int]:
        """Rank key: uninspected first, then failure rate, then least-tried.

        Deliberately lexicographic so the ordering is auditable. `has_inspector` leads because a
        capability nobody checked is not "known to be fine" -- it is unknown, which is the largest
        gap a self-model can have.
        """
        rate = self.verified_failures / self.attempts if self.attempts else 0.0
        return (0 if not self.has_inspector else 1, -rate, self.attempts)

    def as_row(self) -> dict[str, Any]:
        return {
            "capability_id": self.capability_id,
            "verified_failures": self.verified_failures,
            "verified_passes": self.verified_passes,
            "has_inspector": self.has_inspector,
            "attempts": self.attempts,
            "failure_rate": round(
                self.verified_failures / self.attempts if self.attempts else 0.0, 4),
        }


def _settled(ledger) -> list[Mapping[str, Any]]:
    return list(ledger.settled_rows())


def candidates(*, capability_ids: Iterable[str], ledger, inspectors: Mapping[str, Any]
               ) -> list[Candidate]:
    """Build the ranked evidence base. Every input here comes from outside the system's opinion."""
    ids = [str(c) for c in capability_ids if str(c or "").strip()]
    if not ids:
        raise SliceError("CAPABILITY_IDS_REQUIRED")
    seen: dict[str, dict[str, int]] = {cid: {"fail": 0, "pass": 0} for cid in ids}
    for row in _settled(ledger):
        cid = str(row.get("capability_id") or "")
        if cid not in seen:
            continue
        if row.get("outcome_pass") is True:
            seen[cid]["pass"] += 1
        elif row.get("outcome_pass") is False:
            seen[cid]["fail"] += 1
    out = [
        Candidate(
            capability_id=cid,
            verified_failures=counts["fail"],
            verified_passes=counts["pass"],
            has_inspector=cid in inspectors,
        )
        for cid, counts in seen.items()
    ]
    out.sort(key=lambda c: c.difficulty)
    return out


def select(*, capability_ids: Iterable[str], ledger, inspectors: Mapping[str, Any],
           size: int = DEFAULT_SLICE) -> dict[str, Any]:
    """Choose the slice. The system's stated confidence is not an input, by construction."""
    if size <= 0:
        raise SliceError("SLICE_SIZE_MUST_BE_POSITIVE")
    ranked = candidates(capability_ids=capability_ids, ledger=ledger, inspectors=inspectors)
    chosen = ranked[:size]
    return {
        "schema": SCHEMA,
        "size": len(chosen),
        "selected": [c.as_row() for c in chosen],
        "ranked_total": len(ranked),
        "selection_inputs": [
            "inspector-verified failure counts from the settled prediction ledger",
            "absence of a registered re-inspector",
            "attempt count",
        ],
        "selection_excludes": ["the system's own stated confidence"],
        "uninspected_selected": sum(1 for c in chosen if not c.has_inspector),
        "hard_selected": sum(1 for c in chosen
                             if c.verified_failures >= HARD_AFTER_FAILURES),
    }


def run(*, capability_ids: Iterable[str], ledger, inspectors: Mapping[str, Any],
        attempt: Callable[[str], dict[str, Any]], state: Callable[[str], float],
        size: int = DEFAULT_SLICE) -> dict[str, Any]:
    """Attempt the slice.

    `state(cid) -> p` is the system's stated probability of independent acceptance. It is recorded
    before the attempt and settled by the inspector's verdict afterwards. `attempt(cid)` returns
    `{"accepted": bool, "inspector": str, ...}` and may report `accepted: False` because the
    acceptance path refused -- which is precisely the case this module exists to keep unblocked.
    """
    plan = select(capability_ids=capability_ids, ledger=ledger, inspectors=inspectors, size=size)
    rows = []
    for row in plan["selected"]:
        cid = row["capability_id"]
        probability = state(cid)
        prediction = ledger.predict(capability_id=cid, predicted_pass_probability=probability,
                                    claimed_reason="hard slice")
        outcome = attempt(cid) or {}
        accepted = outcome.get("accepted")
        if not isinstance(accepted, bool):
            raise SliceError(f"ATTEMPT_DID_NOT_RETURN_A_BOOL_FOR:{cid}")
        inspector = str(outcome.get("inspector") or "")
        if not inspector:
            raise SliceError(f"ATTEMPT_DID_NOT_NAME_AN_INSPECTOR_FOR:{cid}")
        ledger.settle(prediction["record_id"], outcome_pass=accepted, inspector=inspector)
        rows.append({
            "capability_id": cid,
            "stated_probability": probability,
            "accepted": accepted,
            "inspector": inspector,
            "refused_by_gate": bool(outcome.get("refused_by_gate")),
        })
    return {
        "schema": SCHEMA,
        "attempted": len(rows),
        "accepted": sum(1 for r in rows if r["accepted"]),
        "refused_by_gate": sum(1 for r in rows if r["refused_by_gate"]),
        "rows": rows,
        "plan": plan,
    }
