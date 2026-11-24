"""The right question is the probe that most splits the surviving regimes.

`perfect_algorithm_v1.right_question` ranks actions by novelty and, when a closeness heuristic
exists, by goal-closeness; its answer is written into the receipt and never used. This module is
the missing carrier: it turns a set of *observed regimes* (facts in the external store, never in
weights) into a version space, asks `settlement_v1` which probe has the highest expected
information gain, EXECUTES that probe against the real environment, and feeds the observation back
into the posterior. The answer is then used, not just logged.

Design constraints, from this project's measurements and the 2026 literature:

  * The hypothesis space is derived from the store's own observed transitions, never hand-authored
    with the answer and never a world-fact table in a weight.
  * EIG is a *probe ORDER* score over a closed, small version space. arXiv:2602.06818 measures
    that EIG can be counterproductive in open-ended program spaces (the "proposal bottleneck") and
    underperforms a positive-test heuristic on simple concepts. So `policy()` refuses to use EIG
    when the space is not closed, and the caller can always fall back to arrival order.
  * When the true regime is not in the space, `settlement_v1` returns
    EVIDENCE_OUTSIDE_HYPOTHESIS_SPACE. That is a refusal, never a confident wrong answer.

Reused, not rebuilt: `settlement_v1.VersionSpace` / `settle` / `select_probe`,
`deterministic_decision_primitives.expected_information_gain`. No new learner, no new store, no
model call, no network, no stored parameter.
"""

from __future__ import annotations

import hashlib
from typing import Any, Callable, Iterable, Mapping, Sequence

from canonical.runtime import settlement_v1 as sv

SCHEMA = "BRAIN_ACTIVE_QUESTION_V1"

# A closed space is small enough that every hypothesis can be refuted by a reachable probe.
# Beyond this, EIG over an open proposal space is exactly the counterproductive regime the
# frontier measures; the honest move is to say the space is open and use arrival order.
MAX_CLOSED_SPACE = 24


def probe_key(state_id: str, state_class: str, action: str) -> tuple[str, str, str]:
    return (state_id, state_class, action)


def key_of(value: Any) -> str:
    """A stable, hashable, inspectable key for a real outcome."""
    if isinstance(value, (tuple, list)):
        return "|".join(key_of(v) for v in value)
    if isinstance(value, dict):
        return "|".join(f"{k}={key_of(v)}" for k, v in sorted(value.items()))
    return str(value)


def regime_outcomes(row: Mapping[str, Any]) -> dict[str, str]:
    """Read a store row's observed (probe -> outcome) facts. No fact is invented here."""
    out: dict[str, str] = {}
    for key, outcome in (row.get("outcomes") or {}).items():
        out[str(key)] = key_of(outcome)
    return out


def class_outcomes(outcomes: Mapping[str, str]) -> dict[tuple[str, str], str]:
    """The computed generalisation a regime permits: group observed probes by their OWN class.

    The class is `(state_class, action)`, read from the probe key, not from a hand-written rule.
    A class with disagreeing observed outcomes has no fallback: guessing one would be a fact the
    store does not hold.
    """
    grouped: dict[tuple[str, str], set[str]] = {}
    for key, outcome in outcomes.items():
        parts = key.split("|")
        if len(parts) != 3:
            continue
        grouped.setdefault((parts[1], parts[2]), set()).add(outcome)
    return {cls: next(iter(vals)) for cls, vals in grouped.items() if len(vals) == 1}


def build_space(rows: Sequence[Mapping[str, Any]]) -> sv.VersionSpace:
    """One hypothesis per observed regime. Each predicts an exact probe, else its class fallback.

    The hypotheses are COMPUTED MECHANISMS (lookup + a class generalisation derived from the
    row's own keys). The outcomes they return are facts from the external store.
    """
    hypotheses: list[sv.Hypothesis] = []
    for row in rows:
        outcomes = regime_outcomes(row)
        by_class = class_outcomes(outcomes)
        regime_id = str(row.get("regime_id") or "?")

        def predict(probe: tuple[Any, ...], *, _o: Mapping[str, str] = outcomes,
                    _c: Mapping[tuple[str, str], str] = by_class) -> str:
            parts = tuple(str(p) for p in probe)
            exact = "|".join(parts)
            if exact in _o:
                return _o[exact]
            if len(parts) == 3 and (parts[1], parts[2]) in _c:
                return _c[(parts[1], parts[2])]
            return "UNKNOWN"

        hypotheses.append(sv.Hypothesis(key=regime_id, predict=predict,
                                        description=f"observed regime {regime_id}"))
    return sv.VersionSpace(hypotheses)


def closed(space: sv.VersionSpace) -> bool:
    return 0 < len(space.hypotheses) <= MAX_CLOSED_SPACE


def gain_table(space: sv.VersionSpace, probes: Sequence[tuple[Any, ...]]) -> dict[str, float]:
    """EIG in bits for every reachable probe, so the ranking is inspectable."""
    return {key_of(p): round(space.information_gain(p), 6) for p in probes}


def policy(space: sv.VersionSpace, probes: Sequence[tuple[Any, ...]], *,
           budget: int = 4) -> dict[str, Any]:
    """Choose EIG only when the space is closed and a probe actually splits it.

    This is the kill-switch the frontier's negative result demands: EIG is not applied to an open
    proposal space, and a probe with zero gain is not asked. Every refusal names its reason.
    """
    gains = gain_table(space, probes)
    if not space.hypotheses:
        return {"policy": "REFUSED__NO_HYPOTHESES", "probes": [], "gains": gains,
                "reason": "the store holds no observed regime"}
    if not closed(space):
        return {"policy": "FALLBACK__ARRIVAL_ORDER", "probes": list(probes[:budget]),
                "gains": gains,
                "reason": "the hypothesis space is open; EIG is not applied to a proposal space"}
    # Python's sort is stable: equal-gain probes keep the order the environment supplied.
    # That order is the caller's computed prior (e.g. guide_precondition_v1.rank). Sorting by a
    # hash as a tie-break would throw that prior away and ask an arbitrary question instead.
    ordered = sorted(probes, key=lambda p: -gains[key_of(p)])
    chosen = [p for p in ordered[:budget] if gains[key_of(p)] > 0.0]
    if not chosen:
        return {"policy": "REFUSED__INSTRUMENT_BLIND", "probes": [], "gains": gains,
                "reason": "no reachable probe splits the surviving regimes"}
    return {"policy": "EIG", "probes": chosen, "gains": gains,
            "reason": "a closed version space with positive-gain probes"}


def ask(space: sv.VersionSpace, probes: Sequence[tuple[Any, ...]], *,
        oracle: Callable[[tuple[Any, ...]], str],
        domain: Sequence[tuple[Any, ...]],
        budget: int = 4,
        confidence: float = 0.99) -> dict[str, Any]:
    """Ask the question, execute the probe for real, and USE the answer.

    `settle` calls the oracle itself and updates the posterior; this wrapper only records what
    was asked and what came back, so the caller can audit the question and its price.
    """
    decision = policy(space, probes, budget=budget)
    if decision["policy"] != "EIG":
        # Fallback and refusals still have to be honest about what was learned. Arrival-order
        # probes are executed and observed; a refusal executes nothing.
        asked: list[dict[str, Any]] = []
        for probe in decision["probes"]:
            observed = oracle(probe)
            space.observe(probe, observed)
            asked.append({"probe": key_of(probe), "outcome": key_of(observed)})
        return {"schema": SCHEMA, **decision, "asked": asked,
                "settlement": {"status": decision["policy"], "queries_used": len(asked),
                               "information_bits": 0.0},
                "posterior": {str(k): round(v, 6) for k, v in space.posterior().items()}}
    asked = []
    wrapped = list(decision["probes"])

    def observing(probe: tuple[Any, ...]) -> str:
        observed = oracle(probe)
        asked.append({"probe": key_of(probe), "outcome": key_of(observed)})
        return observed

    settlement = sv.settle(space, domain=list(domain), probes=wrapped,
                           oracle=observing, max_queries=budget, confidence=confidence)
    return {"schema": SCHEMA, **decision, "asked": asked,
            "settlement": settlement.as_row(),
            "settled": settlement.settled,
            "winner": None if settlement.winner is None else str(settlement.winner.key),
            "posterior": {str(k): round(v, 6) for k, v in space.posterior().items()}}


def predict(space: sv.VersionSpace, probe: tuple[Any, ...]) -> str:
    """The answer the system will act on: the leader's prediction, or a named refusal."""
    post = space.posterior()
    if not post:
        return "REFUSED__NO_HYPOTHESES"
    leader = max(post.items(), key=lambda kv: (kv[1], str(kv[0])))
    if space.last_observation_explained_by_none:
        return "REFUSED__EVIDENCE_OUTSIDE_HYPOTHESIS_SPACE"
    if leader[1] < 0.99:
        return "REFUSED__UNDERDETERMINED"
    return space._by_key[leader[0]].predict(probe)


def store_digest(rows: Sequence[Mapping[str, Any]]) -> str:
    """The store is external data: its digest can be checked across a process restart."""
    import json
    return hashlib.sha256(json.dumps(rows, sort_keys=True, default=str)
                          .encode("utf-8")).hexdigest()[:16]
