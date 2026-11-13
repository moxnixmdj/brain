#!/usr/bin/env python3
"""Learn WHEN a remembered plan applies, from outcomes in context.

THE UNIT OF MEMORY WAS TOO COARSE. `macro_v1` remembers a plan under the shape of the goal and
counts successes and failures against it. A count cannot express "this works for a .docx that has
a sidecar and not for one that was just copied", so the only thing a failure can do is argue
against the plan EVERYWHERE. `macro_v1.note_failure` documents four sightings of that error: a
goal-relative file kind became a permanent ban, a precondition became one, eight audits of one bad
directory disabled auditing everywhere.

The missing quantity is not more demonstrations. It is the STATE each outcome happened in. A
success is a point: it shows the plan worked somewhere. A failure in a DIFFERENT state is what
separates "always" from "only when". `what_a_success_teaches_20261112.py` measured this over 200
exact cases: one success identifies 0 of 200 requirements, and the most general survivor admits the
action in 68% of the states where it fails; with failures in the evidence the same learner reaches
25/25 exact identification.

This module is that learner, generalised for production use. It reuses `settlement_v1.VersionSpace`
and the same conjunction grammar the probe used, so there is one notion of consistency in the tree
rather than two.

WHAT IT REFUSES TO DO. It never invents a requirement. With no failure it returns UNDETERMINED,
because necessity is only refuted by failure. With several consistent requirements it returns
AMBIGUOUS rather than picking one. With none it returns INCONSISTENT, which is a statement about
the grammar and not about the world. A caller may only withhold a plan on IDENTIFIED.

COST. Candidate requirements are subsets of the facts present in EVERY success -- a fact absent
from any success cannot be necessary. That is candidate elimination, and it is usually way below
the 2^n of enumerating every conjunction. The enumeration is explicitly bounded and reports
BOUNDED rather than silently truncating.

Authority NONE. Pure function of the evidence handed to it. Zero model dependency, $0.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Any, Iterable, Sequence

from canonical.runtime.settlement_v1 import Hypothesis, VersionSpace

SCHEMA = "PROJECT_BRAIN_APPLICABILITY_V1"

#: No requirement at all: the plan is claimed to work in every state. It is a real hypothesis and
#: it is the one a success-only store implicitly believes.
EMPTY_KEY = "(empty)"

#: Ceiling on enumerated candidate requirements. 2^12 = 4096 conjunctions, each checked against
#: the evidence, is cheap and deterministic; beyond it the answer is reported, not guessed.
MAX_CANDIDATE_FACTS = 12

UNDETERMINED = "UNDETERMINED__NO_CONTRASTING_OUTCOME"
IDENTIFIED = "IDENTIFIED__ONE_CONSISTENT_REQUIREMENT"
AMBIGUOUS = "AMBIGUOUS__SEVERAL_CONSISTENT_REQUIREMENTS"
INCONSISTENT = "INCONSISTENT__NO_REQUIREMENT_EXPLAINS_THE_EVIDENCE"
BOUNDED = "BOUNDED__TOO_MANY_CANDIDATE_FACTS_TO_ENUMERATE"


@dataclass(frozen=True)
class Boundary:
    """What the evidence does and does not license about where a plan applies."""

    schema: str
    status: str
    #: The single consistent requirement, or None unless status is IDENTIFIED.
    required: tuple[str, ...] | None
    #: G: the least demanding survivor. What a success-only store would assume.
    most_general: tuple[str, ...]
    #: S: the most demanding survivor.
    most_specific: tuple[str, ...]
    survivor_count: int
    successes: int
    failures: int
    candidate_facts: tuple[str, ...]
    reason: str
    #: Every requirement still consistent with the evidence, each sorted. Empty unless the
    #: evidence supports at least one. Query selection needs the whole set, not just its edges.
    survivors: tuple[tuple[str, ...], ...] = ()

    @property
    def identified(self) -> bool:
        return self.status == IDENTIFIED

    def as_row(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "status": self.status,
            "required": None if self.required is None else list(self.required),
            "most_general": list(self.most_general),
            "most_specific": list(self.most_specific),
            "survivor_count": self.survivor_count,
            "successes": self.successes,
            "failures": self.failures,
            "candidate_facts": list(self.candidate_facts),
            "survivors": [list(s) for s in self.survivors],
            "reason": self.reason,
        }


def conjunction(required: Iterable[str]) -> Hypothesis:
    """`applicable(state)` iff every required fact is present. Same grammar as the probe."""
    need = frozenset(required)
    return Hypothesis(
        key="&".join(sorted(need)) or EMPTY_KEY,
        predict=lambda probe, need=need: need <= frozenset(probe[0]),
        description="requires " + (", ".join(sorted(need)) or "nothing"),
    )


def as_set(hypothesis: Hypothesis) -> frozenset[str]:
    key = str(hypothesis.key)
    return frozenset() if key == EMPTY_KEY else frozenset(key.split("&"))


def normalise_state(state: Iterable[str] | None) -> frozenset[str]:
    """A state is the set of facts observed TRUE. Absent means not observed true."""
    if state is None:
        return frozenset()
    if isinstance(state, dict):
        return frozenset(str(k) for k, v in state.items() if v is True)
    return frozenset(str(x) for x in state)


def survivors(space: VersionSpace) -> list[Hypothesis]:
    """Exact version space: hypotheses consistent with EVERY observation.

    Deliberately the same definition `what_a_success_teaches_20261112.survivors` uses, so the
    production learner and the measurement cannot drift apart. `VersionSpace` keeps soft weights
    for query selection; admission here is consistency, not posterior mass.
    """
    out: list[Hypothesis] = []
    for hypothesis in space.hypotheses:
        ok = True
        for probe, outcome in space.observations:
            try:
                if bool(hypothesis.predict(probe)) != bool(outcome):
                    ok = False
                    break
            except Exception:
                ok = False
                break
        if ok:
            out.append(hypothesis)
    return out


def vocabulary_gap(evidence: Sequence[tuple[Iterable[str], bool]]) -> dict[str, Any] | None:
    """Proof that the OBSERVED FACTS cannot express what this plan needs, or None.

    THE MEASURED WALL. Two real directories, identical sensed facts
    `{git.repository, manifest.json, structured.json}`, opposite real outcomes: one succeeded, one
    failed with `DOCX_INTENT_SIDECAR_MISSING`. The cause -- a `.docx.intent.json` sidecar -- has no
    fact in the sensor's vocabulary (`probe_effect` answers UNDECIDABLE for it). So the two worlds
    are THE SAME POINT to this learner while being different worlds to the executor.

    That is the honest answer to "show it once and it will learn": if the real precondition is not
    expressible, one exposure and a million exposures teach exactly the same nothing. `learn`
    already refuses to invent a requirement here and returns INCONSISTENT, which is correct -- but
    INCONSISTENT has no survivors, so `explains_failure` answers False and the plan is offered even
    in the world where it just failed, with no statement of why.

    This returns the WITNESS: two observations with equal fact sets and opposite outcomes. That pair
    is a proof of insufficiency, not a guess, and it is what a vocabulary repair must be aimed at.
    Returns None when no such pair exists -- including when the evidence is merely sparse.
    """
    by_state: dict[frozenset[str], set[bool]] = {}
    for state, ok in (evidence or []):
        by_state.setdefault(normalise_state(state), set()).add(bool(ok))
    for state in sorted(by_state, key=lambda s: (len(s), sorted(s))):
        outcomes = by_state[state]
        if len(outcomes) > 1:
            return {
                "schema": SCHEMA,
                "kind": "SAME_OBSERVED_STATE_OPPOSITE_OUTCOMES",
                "facts": sorted(state),
                "outcomes": [False, True],
                "reason": "AN_UNOBSERVED_PRECONDITION_DIFFERS_BETWEEN_THESE_WORLDS",
            }
    return None


#: The five proofs that evidence cannot yield a requirement, and the one absence of proof.
#: The first three are a missing KIND of observation, so more runs of the same sort can fix them.
#: The last two are a missing OBSERVABLE, and no number of runs can fix them.
WITNESS_NO_EVIDENCE = "NO_EVIDENCE__NOTHING_OBSERVED"
WITNESS_NO_FAILURE = "NO_FAILURE__NECESSITY_IS_ONLY_REFUTED_BY_FAILURE"
WITNESS_NO_SUCCESS = "NO_SUCCESS__NOTHING_TO_SCOPE"
WITNESS_SAME_STATE = "SAME_OBSERVED_STATE_OPPOSITE_OUTCOMES"
WITNESS_SEPARATION_IMPOSSIBLE = (
    "SEPARATION_IMPOSSIBLE__EVERY_FACT_ALL_SUCCESSES_SHARE_A_FAILURE_ALSO_HAS"
)
#: Kinds that more observations of this same vocabulary cannot repair.
UNREPAIRABLE_BY_REPETITION = frozenset({WITNESS_SAME_STATE, WITNESS_SEPARATION_IMPOSSIBLE})


def insufficiency_witness(evidence: Sequence[tuple[Iterable[str], bool]]) -> dict[str, Any] | None:
    """A PROOF that this evidence cannot yield a requirement, or None. No enumeration.

    WHY THIS EXISTS BESIDE `vocabulary_gap`. `vocabulary_gap` proves insufficiency in one shape
    only: two observations with EQUAL fact sets and opposite outcomes. That shape is real -- it is
    the `.docx.intent.json` sidecar -- but it is a special case, and it is silent on the shape that
    the pinned real code-repair corpus actually exhibits. Measured 2026-11-13 on the four pinned
    historical repairs in `canonical/tests/fixtures/historical_repair_projects_v1`, judged by their
    own upstream tests (two repaired, two fired and did not repair):

        `vocabulary_gap`  -> None, i.e. "nothing is wrong with the vocabulary"
        `learn`           -> INCONSISTENT, 0 survivors

    Both answers are correct and they contradict each other in effect: the instrument built to
    explain the refusal does not fire on the refusal. The two successes share exactly two facts
    (`baseline.violates_own_spec`, `operator.Gt`), and every failure has both. So the worlds are not
    the same point -- they differ in 38 other facts -- and yet nothing in the vocabulary separates
    them, because the only facts the successes AGREE on are facts the failures also have.

    THE CERTIFICATE, AND WHY IT NEEDS NO ENUMERATION. Write A = the intersection of the fact sets of
    all successes. A conjunction C of observed facts is consistent with the successes exactly when
    C is a subset of A, so the largest candidate is A itself. C excludes a failure F exactly when C
    is not a subset of F. Therefore some consistent C exists iff A is not a subset of any failure,
    and A itself is the witness either way:

        no requirement exists  <=>  A is a subset of at least one failure's fact set

    `learn` reaches the same verdict by enumerating all 2^|A| subsets and finding none alive; this
    reaches it in |evidence| set comparisons. Two consequences matter. First, the certificate still
    decides when |A| exceeds `MAX_CANDIDATE_FACTS` and `learn` has to answer BOUNDED -- it separates
    "the vocabulary cannot express this" from "enumerating the vocabulary is too expensive", which
    are different problems with different repairs. Second, `vocabulary_gap`'s shape implies this
    one: if a success and a failure share their whole fact set then A, a subset of that success, is
    a subset of that failure. So this witness fires on everything the older one fires on, plus the
    cases it is blind to.

    WHAT None MEANS, AND WHAT IT DOES NOT. None is a proof that separation IS possible: some
    conjunction admits every success and excludes every failure. It is not a claim that the learner
    found one, or that it is cheap to find -- with |A| above the cap `learn` still answers BOUNDED.

    This function decides nothing about admission and writes nothing. It is a diagnostic, and the
    reason it is worth shipping is measured: two rounds read a refusal label, aimed engineering at
    the wrong seam, and merged opposite diagnoses of the same wall.
    """
    rows = [(normalise_state(state), bool(ok)) for state, ok in (evidence or ())]
    successes = [state for state, ok in rows if ok]
    failures = [state for state, ok in rows if not ok]

    def _missing(kind: str, reason: str) -> dict[str, Any]:
        return {
            "schema": SCHEMA, "kind": kind, "reason": reason,
            "successes": len(successes), "failures": len(failures),
            "shared_facts": [], "witness_failure_indices": [],
            "unrepairable_by_repetition": False,
            "what_would_repair_it": "AN_OBSERVATION_OF_THE_MISSING_KIND__NOT_A_NEW_OBSERVABLE",
        }

    if not rows:
        return _missing(WITNESS_NO_EVIDENCE, "NOTHING_OBSERVED")
    if not failures:
        return _missing(WITNESS_NO_FAILURE, "A_SUCCESS_CANNOT_ESTABLISH_NECESSITY")
    if not successes:
        return _missing(WITNESS_NO_SUCCESS, "NO_SUCCESS_TO_SCOPE_FROM")

    shared: frozenset[str] = frozenset(successes[0])
    for state in successes[1:]:
        shared = shared & state

    # The equal-facts shape is reported preferentially: it is strictly more specific, and it names
    # the two worlds that are one point to this sensor, which is what a suffix-predicate repair aims at.
    by_state: dict[frozenset[str], set[bool]] = {}
    for state, ok in rows:
        by_state.setdefault(state, set()).add(ok)
    for state in sorted(by_state, key=lambda s: (len(s), sorted(s))):
        if len(by_state[state]) > 1:
            return {
                "schema": SCHEMA, "kind": WITNESS_SAME_STATE,
                "reason": "AN_UNOBSERVED_PRECONDITION_DIFFERS_BETWEEN_THESE_WORLDS",
                "successes": len(successes), "failures": len(failures),
                "facts": sorted(state), "shared_facts": sorted(shared),
                "witness_failure_indices": [
                    i for i, f in enumerate(failures) if f == state],
                "unrepairable_by_repetition": True,
                "what_would_repair_it": "A_NEW_OBSERVABLE__MORE_RUNS_REPORT_THE_SAME_FACT_VECTOR",
            }

    witnesses = [i for i, state in enumerate(failures) if shared <= state]
    if witnesses:
        return {
            "schema": SCHEMA, "kind": WITNESS_SEPARATION_IMPOSSIBLE,
            "reason": "THE_FACTS_ALL_SUCCESSES_AGREE_ON_ARE_FACTS_A_FAILURE_ALSO_HAS",
            "successes": len(successes), "failures": len(failures),
            "shared_facts": sorted(shared),
            "witness_failure_indices": witnesses,
            "unrepairable_by_repetition": True,
            "what_would_repair_it": "A_NEW_OBSERVABLE__MORE_RUNS_REPORT_THE_SAME_FACT_VECTOR",
        }
    return None


def candidate_requirements(
    evidence: Sequence[tuple[Iterable[str], bool]],
    *,
    max_candidate_facts: int = MAX_CANDIDATE_FACTS,
) -> tuple[tuple[str, ...], ...]:
    """Every requirement the evidence has not yet ruled out, INCLUDING from successes alone.

    This is deliberately separate from `learn`, and it does not weaken it. `learn` refuses to
    license a boundary without a failure, and that refusal is correct: a success cannot establish
    necessity. But successes do constrain the SPACE of possible requirements -- any fact absent
    from some success cannot be necessary -- and that space is exactly what a query selector needs
    in order to choose the run that would settle the question. Conflating the two would either
    weaken the refusal or leave the selector with nothing to select against, which is what made
    the live path report zero survivors after three real successes.

    Returns () when there is no success to scope from, when no requirement survives, or when the
    candidate set is too large to enumerate. Callers must treat () as "cannot choose", never as
    "no requirement".
    """
    rows = [(normalise_state(state), bool(ok)) for state, ok in (evidence or [])]
    successes = [state for state, ok in rows if ok]
    if not successes:
        return ()
    allowed: frozenset[str] = frozenset(successes[0])
    for state in successes[1:]:
        allowed = allowed & state
    keys = tuple(sorted(allowed))
    if len(keys) > max_candidate_facts:
        return ()
    space = VersionSpace([
        conjunction(subset)
        for size in range(len(keys) + 1)
        for subset in itertools.combinations(keys, size)
    ])
    for state, ok in rows:
        space.observe((state,), ok)
    from canonical.runtime.fact_entailment_v1 import distinct_requirements

    return distinct_requirements([as_set(h) for h in survivors(space)])


def learn(
    evidence: Sequence[tuple[Iterable[str], bool]],
    *,
    max_candidate_facts: int = MAX_CANDIDATE_FACTS,
) -> Boundary:
    """Identify the requirement, or say precisely why the evidence does not determine one.

    `evidence` is a sequence of `(state, succeeded)`. Order does not affect the answer: consistency
    is a conjunction over observations.
    """
    rows = [(normalise_state(state), bool(ok)) for state, ok in (evidence or [])]
    successes = [state for state, ok in rows if ok]
    failures = [state for state, ok in rows if not ok]

    def _empty(status: str, reason: str, candidates: Iterable[str] = ()) -> Boundary:
        return Boundary(
            schema=SCHEMA, status=status, required=None,
            most_general=(), most_specific=(), survivor_count=0,
            successes=len(successes), failures=len(failures),
            candidate_facts=tuple(sorted(candidates)), reason=reason,
        )

    if not rows:
        return _empty(UNDETERMINED, "NO_EVIDENCE")
    if not failures:
        # The load-bearing refusal. A success is a point, not a quantifier: nothing here can
        # remove the empty requirement, so nothing here licenses a boundary.
        return _empty(UNDETERMINED, "NO_FAILURE__NECESSITY_IS_ONLY_REFUTED_BY_FAILURE")
    if not successes:
        return _empty(UNDETERMINED, "NO_SUCCESS__NOTHING_TO_SCOPE")

    # Candidate elimination: a fact missing from any success cannot be necessary.
    allowed: frozenset[str] = frozenset(successes[0])
    for state in successes[1:]:
        allowed = allowed & state
    keys = tuple(sorted(allowed))
    if len(keys) > max_candidate_facts:
        return _empty(
            BOUNDED,
            f"{len(keys)}_CANDIDATE_FACTS_EXCEEDS_{max_candidate_facts}",
            keys,
        )

    hypotheses = [
        conjunction(subset)
        for size in range(len(keys) + 1)
        for subset in itertools.combinations(keys, size)
    ]
    space = VersionSpace(hypotheses)
    for state, ok in rows:
        space.observe((state,), ok)

    alive = survivors(space)
    if not alive:
        return _empty(
            INCONSISTENT,
            "NO_CONJUNCTION_OF_OBSERVED_FACTS_SEPARATES_SUCCESSES_FROM_FAILURES",
            keys,
        )

    sets = [as_set(h) for h in alive]
    # Count DISTINCT requirements, not spellings. Two survivors can denote the same set of
    # satisfying worlds: `manifest.json` is decided as "a .json named manifest" and
    # `structured.json` as "a .json", so the first implies the second and
    # {manifest, structured} IS {manifest}. Measured: that pair was reported AMBIGUOUS and the
    # selector reported no reachable state could ever split it -- a permanent fake limit that
    # withheld `required` even though the evidence already determined it. Reducing by the
    # sensor's own implications removes the redundant literal without removing any requirement.
    from canonical.runtime.fact_entailment_v1 import distinct_requirements, reduce_requirement

    reduced = distinct_requirements(sets)
    ordered_survivors = reduced
    general = tuple(sorted(min(reduced, key=len)))
    specific = tuple(sorted(max(reduced, key=len)))
    status = IDENTIFIED if len(reduced) == 1 else AMBIGUOUS
    return Boundary(
        schema=SCHEMA,
        status=status,
        required=general if status == IDENTIFIED else None,
        most_general=general,
        most_specific=specific,
        survivor_count=len(reduced),
        successes=len(successes),
        failures=len(failures),
        candidate_facts=keys,
        reason="ONE_CONSISTENT_REQUIREMENT" if status == IDENTIFIED else "SEVERAL_CONSISTENT_REQUIREMENTS",
        survivors=ordered_survivors,
    )


def admits(required: Iterable[str], state: Iterable[str] | None) -> bool:
    """Would this requirement let the plan run in this state?"""
    return frozenset(required) <= normalise_state(state)


def explains_failure(boundary: Boundary, state: Iterable[str] | None) -> bool:
    """True when EVERY surviving requirement places this state outside the plan's scope.

    The test is the most general survivor G, not the identified one. G is the least demanding
    requirement still consistent with the evidence, and every other survivor is a superset of
    some survivor at least as demanding -- so if even G rejects this state, all of them do. That
    makes withholding safe while the exact requirement is still AMBIGUOUS, which is the normal
    state of affairs after one success and one failure: `{sidecar}` and `{sidecar, python}` both
    survive, and both refuse a file with no sidecar.

    Waiting for exact identification would throw away a sound refusal; using the most SPECIFIC
    survivor instead would manufacture a ban the evidence does not support. Neither is done.

    UNDETERMINED, INCONSISTENT and BOUNDED have no survivors and answer False, so a plan is never
    withheld on evidence that supports no requirement at all. That is the guard against the error
    `macro_v1` has already met four times.
    """
    if boundary.survivor_count <= 0:
        return False
    return not admits(boundary.most_general, state)
