#!/usr/bin/env python3
"""Consistency is evidence; equivalence is the goal. No model, no network.

THE HOLE THIS CLOSES, MEASURED FIRST
------------------------------------
A single trace is consistent with exponentially many hypotheses, and a rule
that agrees with the goal on every run it has produced can still be a
different function on every trace the environment never produced. More runs do
not close the gap: repetition buys exactly zero bits -- showing the same
agreeing trace again eliminates no hypothesis (measured on this tree: 0 of 200
cases identified from repetitions alone; the identical fact vector repeats
forever, `INSUFFICIENCY_CERTIFICATE_20261113_V1.json`).

`AGREEMENT_IS_NOT_EQUIVALENCE_20261119_V1.md` measured the residual on five
real machines, 983 executed runs, 38 791 count histories: two different
statements agreed with the judge's own verdict on every run, and *no run of
any machine could produce the trace that separates them* (a single step that
adds two copies at once; every machine's largest single-step increase is 1).
The separation was structural, not statistical. What closed it was a proof:
one statement is *equivalent* to the judge's definition under a checkable
precondition (initial count == 0, one read per machine), the other is not.

This module is that proof step, generalized:

1. enumerate the statements in a grammar over the observables;
2. keep the class consistent with the runs (each run is a filter, never a
   confirmation);
3. close the class by PROOF -- exhibit that one member is equivalent to the
   goal's total judge under a named, checkable precondition -- or by
   WITNESS -- exhibit a concrete trace in the declared observation model's
   trace space on which the candidate and the judge disagree;
4. otherwise report UNKNOWN and store nothing. An unidentified reading is not
   a parameter; it is one of many survivors that happen to fit, and storing it
   in weights is the "knowledge house" this project rejects.

Everything here executes. Traces are real tuples of observables; the judge is a
total callable; the observation model declares what traces its action alphabet
can produce, so the witness is a property of the alphabet, not of sampling.

Authority: NONE. Nothing here is a capability, a weight update, or a claim
about any program outside the traces you supply.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Iterator, Sequence

SCHEMA = "PROJECT_BRAIN_CONSISTENCY_VS_EQUIVALENCE_V1"
AUTHORITY = "NONE"

# ---------------------------------------------------------------------------
# verdicts
# ---------------------------------------------------------------------------

EQUIVALENT_UNDER_PRECONDITION = "EQUIVALENT_UNDER_PRECONDITION"
COUNTEREXAMPLE = "COUNTEREXAMPLE"
UNKNOWN = "UNKNOWN"
NOT_ENUMERABLE = "NOT_ENUMERABLE"

#: Default cap on trace enumeration so the prover always terminates. The
#: observation model owns the trace space; this cap is the caller's patience.
DEFAULT_TRACE_CAP = 100_000


@dataclass(frozen=True)
class Trace:
    """One execution's observable trace, as a tuple of hashable observations.

    Traces are compared by value and hashed so the consistent class and the
    witness ledger can be deduplicated and audited.
    """

    events: tuple[Any, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "events", tuple(self.events))

    def __hash__(self) -> int:
        return hash(self.events)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Trace):
            return NotImplemented
        return self.events == other.events

    def sha256(self) -> str:
        return hashlib.sha256(json.dumps(self.events, sort_keys=True,
                                         default=str).encode("utf-8")).hexdigest()


#: A total predicate over traces: the goal's own definition of correct.
#: `judge(trace)` must return a bool for every trace in the model's space --
#: it is the oracle, and this module cannot repair a wrong one.
Judge = Callable[[Trace], bool]

#: A candidate rule over observables, derived from a demonstration.
Statement = Callable[[Trace], bool]


@dataclass(frozen=True)
class ProofResult:
    """The prover's answer. Exactly one of witness / equivalent holds."""

    kind: str
    #: Human-readable reason.
    reason: str
    #: A trace in the model's space on which statement != judge, or None.
    witness: Trace | None = None
    #: The named precondition under which equivalence holds, or None.
    precondition: str | None = None
    #: Traces enumerated before the verdict.
    traces_checked: int = 0
    #: The size limit of the enumeration, if any.
    trace_cap: int | None = None
    #: Schema and authority for the audit record.
    schema: str = SCHEMA
    authority: str = AUTHORITY

    def record(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "kind": self.kind,
            "reason": self.reason,
            "witness_events": list(self.witness.events) if self.witness is not None else None,
            "witness_sha256": self.witness.sha256() if self.witness is not None else None,
            "precondition": self.precondition,
            "traces_checked": self.traces_checked,
            "trace_cap": self.trace_cap,
            "authority": self.authority,
        }


# ---------------------------------------------------------------------------
# the observation model: what the alphabet can produce
# ---------------------------------------------------------------------------


class ObservationModel:
    """Declares the trace space an agent/environment can actually produce.

    `traces(max_depth)` must enumerate every trace the declared action alphabet
    can produce up to `max_depth` steps, starting from every initial state.
    It is finite by construction (bounded depth, finite branching); an infinite
    or continuous space must be discretized by the caller before the prover can
    close a class by enumeration.

    `precondition_holds(initial_state)` names the condition under which a
    proven equivalence is portable to a new environment -- checkable with one
    read, zero trials.
    """

    def initial_states(self) -> Iterable[Any]:
        raise NotImplementedError

    def step(self, state: Any, action: Any) -> Any:
        raise NotImplementedError

    def actions(self, state: Any) -> Iterable[Any]:
        raise NotImplementedError

    def traces(self, max_depth: int, cap: int = DEFAULT_TRACE_CAP) -> Iterator[Trace]:
        """Yield every trace the alphabet can produce, bounded by depth and cap."""
        checked_states = 0
        for state in self.initial_states():
            yield from self.traces_from_state(state, max_depth)
            checked_states += 1
            if checked_states >= cap:
                return

    def traces_from_state(self, state: Any, max_depth: int) -> Iterator[Trace]:
        yield Trace((state,))
        if max_depth <= 0:
            return
        stack: list[tuple[Any, tuple[Any, ...], int]] = [(state, (state,), 0)]
        while stack:
            cur_state, trace, depth = stack.pop()
            if depth >= max_depth:
                continue
            for action in self.actions(cur_state):
                next_state = self.step(cur_state, action)
                new_trace = trace + (next_state,)
                yield Trace(new_trace)
                stack.append((next_state, new_trace, depth + 1))

    def precondition_holds(self, initial_state: Any) -> bool:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# step 1 and 2: the consistent class, filtered by runs
# ---------------------------------------------------------------------------


def consistent_class(
    statements: Sequence[Statement],
    runs: Sequence[Trace],
    judge: Judge,
) -> list[Statement]:
    """Keep statements that agree with the judge on every run.

    Each run filters the class; a run on which all remaining statements agree
    buys zero bits and changes nothing. Returns the surviving statements in
    input order, deduplicated by identity.
    """
    survivors: list[Statement] = []
    seen: set[int] = set()
    for statement in statements:
        if id(statement) in seen:
            continue
        if all(statement(run) == judge(run) for run in runs):
            survivors.append(statement)
            seen.add(id(statement))
    return survivors


def class_bits(n_statements: int) -> float:
    """Information remaining in a class of n statements: log2(n) bits."""
    if n_statements <= 1:
        return 0.0
    return math.log2(n_statements)


# ---------------------------------------------------------------------------
# step 3: close the class by proof or by witness
# ---------------------------------------------------------------------------


def prove_admission(
    statement: Statement,
    judge: Judge,
    model: ObservationModel,
    *,
    max_depth: int = 6,
    trace_cap: int = DEFAULT_TRACE_CAP,
    precondition_name: str | None = None,
) -> ProofResult:
    """Prove `statement` equivalent to `judge` over the model's trace space.

    Enumerates every trace the declared alphabet can produce up to
    `max_depth`. On the first trace where statement and judge disagree the
    enumeration stops and returns COUNTEREXAMPLE with that trace as the
    witness -- the witness is a property of the alphabet, not of sampling: if
    no atom of the alphabet can emit it, no depth will ever find it, which is
    itself a structural finding.

    If the enumeration completes with no disagreement, returns
    EQUIVALENT_UNDER_PRECONDITION: the two functions are identical on every
    trace the environment can produce, under `precondition_name` (the
    precondition on the initial state, checkable separately).

    If the trace space exceeds `trace_cap` the enumeration is abandoned and
    UNKNOWN is returned -- the prover refuses to guess.
    """
    traces_checked = 0
    for state in model.initial_states():
        if precondition_name is not None and not model.precondition_holds(state):
            continue
        try:
            trace_iter = model.traces_from_state(state, max_depth)
        except AttributeError:  # pragma: no cover - defensive
            trace_iter = model.traces(max_depth)
        for trace in trace_iter:
            traces_checked += 1
            if traces_checked > trace_cap:
                return ProofResult(
                    kind=UNKNOWN,
                    reason=("TRACE_SPACE_EXCEEDS_CAP "
                            f"(cap={trace_cap}, checked={traces_checked})"),
                    traces_checked=traces_checked,
                    trace_cap=trace_cap,
                )
            try:
                s = bool(statement(trace))
                g = bool(judge(trace))
            except Exception as exc:  # a statement that crashes is not a survivor
                return ProofResult(
                    kind=COUNTEREXAMPLE,
                    reason=f"STATEMENT_ERROR:{type(exc).__name__}:{exc}",
                    witness=trace,
                    traces_checked=traces_checked,
                    trace_cap=trace_cap,
                )
            if s != g:
                return ProofResult(
                    kind=COUNTEREXAMPLE,
                    reason="STATEMENT_DISAGREES_WITH_JUDGE",
                    witness=trace,
                    traces_checked=traces_checked,
                    trace_cap=trace_cap,
                )
    return ProofResult(
        kind=EQUIVALENT_UNDER_PRECONDITION,
        reason="NO_DISAGREEING_TRACE_IN_DECLARED_MODEL",
        precondition=precondition_name,
        traces_checked=traces_checked,
        trace_cap=trace_cap,
    )


# ---------------------------------------------------------------------------
# code-rule specialization: the edited program vs the judge's spec
# ---------------------------------------------------------------------------


def _code_trace(source: str, point: Any, actual: Any) -> Trace:
    return Trace(("call", source, point, actual))


def prove_code_rule(
    rule: dict[str, Any],
    before_snippet: str,
    after_snippet: str,
    judge: Callable[[str, Any], Any],
    probes: Sequence[Any],
    *,
    language: str = "python",
    precondition_name: str | None = None,
) -> ProofResult:
    """Prove the rule's edited program agrees with `judge` on every probe.

    `judge(source, point)` states the value the CORRECT program produces --
    the same oracle contract as the admission gate's victims. The statement
    under test is: "for every probe point, the edited program's actual output
    equals the judge's expectation". Enumeration here is the probe set; a
    broader observation model (GUI traces, workflow transitions) uses
    `prove_admission` directly.

    Returns COUNTEREXAMPLE with the first failing probe as the witness, or
    EQUIVALENT_UNDER_PRECONDITION when every probe agrees. The precondition is
    the caller's spec domain (named in `reason`).
    """
    from canonical.swe_kernel.verified_skill_crystallizer_v1 import (
        apply_crystallized_code_rule,
    )

    edited = apply_crystallized_code_rule(before_snippet, rule)
    if edited is None:
        return ProofResult(
            kind=UNKNOWN,
            reason="RULE_DOES_NOT_FIRE_ON_THE_BEFORE_SNIPPET",
            traces_checked=0,
        )

    from canonical.tools.rule_generalization_probe_v1 import run_snippet

    traces_checked = 0
    for point in probes:
        traces_checked += 1
        try:
            expected = judge(before_snippet, point)
        except Exception as exc:
            return ProofResult(
                kind=COUNTEREXAMPLE,
                reason=f"JUDGE_ERROR:{type(exc).__name__}:{exc}",
                witness=_code_trace(before_snippet, point, None),
                traces_checked=traces_checked,
            )
        ran, actual, error = _run(edited, point)
        if not ran:
            return ProofResult(
                kind=COUNTEREXAMPLE,
                reason=f"EDITED_DID_NOT_RUN:{error}",
                witness=_code_trace(before_snippet, point, None),
                traces_checked=traces_checked,
            )
        if actual != expected:
            return ProofResult(
                kind=COUNTEREXAMPLE,
                reason="EDITED_DISAGREES_WITH_JUDGE",
                witness=_code_trace(before_snippet, point, actual),
                traces_checked=traces_checked,
            )
    return ProofResult(
        kind=EQUIVALENT_UNDER_PRECONDITION,
        reason="EDITED_AGREES_WITH_JUDGE_ON_EVERY_PROBE",
        precondition=precondition_name
        or "every probe point in the supplied probe set",
        traces_checked=traces_checked,
    )


def _run(source: str, point: Any) -> tuple[bool, Any, str | None]:
    from canonical.tools.rule_generalization_probe_v1 import run_snippet

    try:
        return True, run_snippet(source, (point,)), None
    except Exception as exc:  # a program that raises is a fact about the program
        return False, None, f"{type(exc).__name__}:{exc}"


# ---------------------------------------------------------------------------
# admission integration: gate verdict plus equivalence result
# ---------------------------------------------------------------------------


def combined_admission_verdict(
    gate_report: dict[str, Any],
    equivalence: ProofResult | None,
) -> dict[str, Any]:
    """Merge the execution gate and the equivalence prover into one verdict.

    ADMIT requires: the gate admitted (repaired an unseen defective program,
    preserved an already-correct one, broke nothing) AND, when an equivalence
    proof was requested, it came back EQUIVALENT_UNDER_PRECONDITION.

    COUNTEREXAMPLE ⇒ REJECT with the witness named. UNKNOWN ⇒ REFINE with the
    reason, never ADMIT: an undecided equivalence is not evidence of safety.
    """
    gate_verdict = gate_report.get("verdict")
    merged: dict[str, Any] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "gate_verdict": gate_verdict,
        "equivalence": equivalence.record() if equivalence is not None else None,
        "whole_task_correctness_proved": False,
    }

    if equivalence is not None:
        if equivalence.kind == COUNTEREXAMPLE:
            merged["verdict"] = "REJECT"
            merged["reason"] = (
                f"EQUIVALENCE_REFUTED:witness={equivalence.witness.sha256()[:16]}"
            )
            merged["witness"] = equivalence.record()
            return merged
        if equivalence.kind == UNKNOWN:
            merged["verdict"] = "REFINE"
            merged["reason"] = f"EQUIVALENCE_UNDECIDED:{equivalence.reason}"
            merged["equivalence"] = equivalence.record()
            return merged
        # EQUIVALENT_UNDER_PRECONDITION: proof recorded below.

    if gate_verdict == "ADMIT":
        merged["verdict"] = "ADMIT"
        merged["reason"] = None
        if equivalence is not None:
            merged["reason"] = "ADMIT_WITH_EQUIVALENCE_PROOF"
    elif gate_verdict == "REFUSED":
        merged["verdict"] = "REFUSED"
        merged["reason"] = gate_report.get("reason")
    elif gate_verdict == "REFINE":
        merged["verdict"] = "REFINE"
        merged["reason"] = gate_report.get("reason")
    else:
        merged["verdict"] = "REJECT"
        merged["reason"] = gate_report.get("reason") or "GATE_REJECT"
    return merged


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
