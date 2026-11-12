#!/usr/bin/env python3
"""Settlement V1: *settled* is a computed quantity, never a reached state.

WHY THIS EXISTS
---------------
Measured on `70b8d1b1`: a creature given six instances of one family (``x mod k``) asked 12 oracle
questions when each instance was solved cold, and 1 question when one brain solved them in sequence.
The 12x saving was not learning. Held-out accuracy over inputs it had never seen fell from 2/10 to
0/10 on the same instance, and the system reported success in both runs:

    k=5   cold: crystallized, held-out 2/10
          warm: RECALLED_TIER0_ORGAN, held-out 0/10, zero questions

Experience had made it faster at being wrong. That is the exact inverse of becoming smarter, and it
was invisible because every status string said the right thing.

Two doors, one error. The organ graph decided a question was *settled* from the path it had taken
instead of from the evidence it held:

  door 1  ``disc_probe is None``  ->  "my grid cannot separate these" was read as "they are
          equivalent", and the first surviving hypothesis was crystallized. Blindness became
          certainty.

  door 2  Tier-0 recall returned the incumbent because it agreed with the examples already given,
          without asking the oracle that was present on the same call. Absence of an attempted
          refutation became evidence of correctness.

WHAT THIS MODULE DOES DIFFERENTLY
---------------------------------
1. Hypotheses carry WEIGHTS. Contradiction *down-weights* a hypothesis instead of deleting it, so the
   posterior accumulates experience instead of forgetting it.
2. A probe is chosen by EXPECTED INFORMATION GAIN divided against its COST. A smart creature is not
   one that asks more questions; it is one that asks the questions that buy the most answer.
3. ``settle`` returns SETTLED only when the posterior is concentrated AND the mass of hypotheses that
   would behave differently on the caller's own domain is small. When no reachable probe has any
   information to give, it returns UNSETTLEABLE_BY_THIS_INSTRUMENT -- a named refusal, never a
   verdict. Blindness is reported, not converted.
4. The reachable probe space is DERIVED from the hypotheses' own literals and the observed domain, so
   a grammar's blindness cannot silently define what counts as the same behaviour.

WHAT IT DOES NOT DO
-------------------
SETTLED is always relative to the reachable probe space and the stated confidence. It is not truth.
A hypothesis that no reachable probe can distinguish stays unknown forever, and this module's job is
to make the system say so rather than guess. No neural weights. No external models. No dynamic code
execution: every hypothesis is a caller-supplied callable.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Callable, Hashable, Iterable, Mapping, Sequence

from canonical.runtime.deterministic_decision_primitives import (
    bayes_posterior,
    entropy_bits,
    expected_information_gain,
)

# ---------------------------------------------------------------------------------------------
# Status vocabulary. Deliberately explicit: every non-SETTLED status names *why*, so a caller can
# never mistake a refusal for a determination.
# ---------------------------------------------------------------------------------------------
SETTLED = "SETTLED"
UNDERDETERMINED = "UNDERDETERMINED"  # mass spread; a better probe exists and is affordable
UNSETTLEABLE_BY_THIS_INSTRUMENT = "UNSETTLEABLE_BY_THIS_INSTRUMENT"  # no reachable probe helps
INSTRUMENT_TOO_COSTLY = "INSTRUMENT_TOO_COSTLY"  # a probe would help but costs more than it buys
DOMAIN_DISAGREEMENT = "DOMAIN_DISAGREEMENT"  # concentrated, but differs on the caller's domain
NO_HYPOTHESES = "NO_HYPOTHESES"
CONTRADICTORY_EVIDENCE = "CONTRADICTORY_EVIDENCE"
EVIDENCE_OUTSIDE_HYPOTHESIS_SPACE = "EVIDENCE_OUTSIDE_HYPOTHESIS_SPACE"  # nothing explains it
NO_ORACLE = "NO_ORACLE"  # would help to ask, but there is nobody to ask

_EPS = 1e-12


# ---------------------------------------------------------------------------------------------
# Probe space derivation
# ---------------------------------------------------------------------------------------------
def _literal_offsets(value: Any, *, span: int = 3) -> list[int]:
    """Integers near an observed or hypothesised value.

    Probing near the literals a body actually mentions is the only place a piecewise body can change
    behaviour; probing a fixed grid elsewhere is how a sparse table decides an answer.
    """
    out: list[int] = []
    if isinstance(value, bool):
        return [0, 1]
    if isinstance(value, int):
        for delta in range(-span, span + 1):
            out.append(value + delta)
    return out


def derive_probe_space(
    examples: Sequence[tuple[tuple[Any, ...], Any]],
    literals: Iterable[int] = (),
    *,
    span: int = 3,
    dense_range: int = 40,
) -> list[tuple[Any, ...]]:
    """Reachable probe inputs, derived from the data and the hypotheses -- not from a frozen grid.

    The dense interior exists because a sparse list is the failure mode we are repairing: a list that
    runs to 20 while omitting 14 is *sparse*, not short, and widening its endpoints fixes nothing.
    """
    if not examples:
        return []
    arity = len(examples[0][0])
    seen: set[tuple[Any, ...]] = set()
    for ex_in, _ in examples:
        seen.add(tuple(ex_in))

    ints: set[int] = set()
    for i in range(-dense_range, dense_range + 1):
        ints.add(i)
    for ex_in, _ in examples:
        for v in ex_in:
            ints.update(_literal_offsets(v, span=span))
    for lit in literals:
        if isinstance(lit, int) and not isinstance(lit, bool):
            ints.update(_literal_offsets(lit, span=span))

    ordered = sorted(ints)
    probes: list[tuple[Any, ...]] = []
    local: set[tuple[Any, ...]] = set()
    for x in ordered:
        probe = tuple([x] * arity)
        if probe in seen or probe in local:
            continue
        local.add(probe)
        probes.append(probe)
    # half-steps, so non-integer domains are not invisible
    for x in (v + 0.5 for v in range(-dense_range, dense_range)):
        probe = tuple([x] * arity)
        if probe in seen or probe in local:
            continue
        local.add(probe)
        probes.append(probe)
    return probes


# ---------------------------------------------------------------------------------------------
# The version space
# ---------------------------------------------------------------------------------------------
@dataclass
class Hypothesis:
    """A candidate program with a weight that carries past experience."""

    key: Hashable
    predict: Callable[[tuple[Any, ...]], Any]
    prior: float = 1.0
    description: str = ""


@dataclass
class Settlement:
    status: str
    reason: str
    winner: Hypothesis | None
    posterior: dict[Hashable, float]
    queries_used: int
    information_bits: float
    domain_disagreement: float
    confidence: float
    threshold: float
    probe_space_size: int

    @property
    def settled(self) -> bool:
        return self.status == SETTLED

    def as_row(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "reason": self.reason,
            "winner": None if self.winner is None else str(self.winner.key),
            "posterior": {str(k): round(v, 6) for k, v in self.posterior.items()},
            "queries_used": self.queries_used,
            "information_bits": round(self.information_bits, 6),
            "domain_disagreement": round(self.domain_disagreement, 6),
            "confidence": round(self.confidence, 6),
            "threshold": self.threshold,
            "probe_space_size": self.probe_space_size,
        }


class VersionSpace:
    """A probability-carrying set of hypothesis programs.

    Weights are posterior weights, normalised on demand. A contradiction multiplies a weight by
    ``contradiction_likelihood`` (small but nonzero) rather than deleting it, so a hypothesis that
    explains almost everything survives a single surprise and can recover -- and so the posterior
    keeps a record of how much experience is behind it.
    """

    def __init__(
        self,
        hypotheses: Sequence[Hypothesis],
        *,
        contradiction_likelihood: float = 1e-3,
    ) -> None:
        if not (0.0 < contradiction_likelihood < 1.0):
            raise ValueError("contradiction_likelihood must be in (0,1)")
        self._weights: dict[Hashable, float] = {}
        self._by_key: dict[Hashable, Hypothesis] = {}
        for h in hypotheses:
            if h.key in self._by_key:
                raise ValueError(f"duplicate hypothesis key {h.key!r}")
            self._by_key[h.key] = h
            self._weights[h.key] = float(h.prior)
        total = sum(self._weights.values())
        if total <= 0.0:
            raise ValueError("hypothesis priors must have positive total mass")
        for k in self._weights:
            self._weights[k] /= total
        self.contradiction_likelihood = contradiction_likelihood
        self.observations: list[tuple[tuple[Any, ...], Any]] = []
        #: True when the most recent observation was contradicted by EVERY hypothesis. That is a
        #: statement about the grammar, not about the world, and must be reported as one.
        self.last_observation_explained_by_none = False

    # -- inspection -----------------------------------------------------------------------
    @property
    def hypotheses(self) -> list[Hypothesis]:
        return list(self._by_key.values())

    def posterior(self) -> dict[Hashable, float]:
        total = sum(self._weights.values())
        if total <= 0.0:  # pragma: no cover - guarded by construction
            return {k: 0.0 for k in self._weights}
        return {k: v / total for k, v in self._weights.items()}

    def entropy(self) -> float:
        return entropy_bits(self.posterior())

    def live(self, *, floor: float = 1e-9) -> list[Hypothesis]:
        post = self.posterior()
        return [h for h in self._by_key.values() if post.get(h.key, 0.0) > floor]

    # -- the one update rule --------------------------------------------------------------
    def observe(self, probe: tuple[Any, ...], outcome: Any) -> None:
        """Multiply weights by how well each hypothesis predicts this outcome."""
        explained_by_any = False
        for key, h in self._by_key.items():
            try:
                agrees = _agree(h.predict(probe), outcome)
            except Exception:
                agrees = False  # a hypothesis that cannot run has not explained anything
            if agrees:
                explained_by_any = True
            likelihood = 1.0 if agrees else self.contradiction_likelihood
            self._weights[key] *= likelihood
        self.last_observation_explained_by_none = not explained_by_any
        total = sum(self._weights.values())
        if total <= 0.0:
            # Every hypothesis now has negligible mass: the evidence is inconsistent with the
            # entire space. Reset to the contradiction likelihood so the condition is *reportable*
            # rather than collapsing the arithmetic to zero.
            for key in self._weights:
                self._weights[key] = 1.0
            total = float(len(self._weights))
        for key in self._weights:
            self._weights[key] /= total
        self.observations.append((probe, outcome))

    # -- domain disagreement --------------------------------------------------------------
    def domain_disagreement(self, domain: Sequence[tuple[Any, ...]]) -> float:
        """Mass of hypotheses that differ from the leader *somewhere on the caller's own domain*.

        This is the question that matters and the one the old code never asked: not "do they agree
        on my probes" but "would choosing wrong cost the caller anything where the caller lives".
        """
        post = self.posterior()
        ranked = sorted(post.items(), key=lambda kv: (-kv[1], str(kv[0])))
        if not ranked or ranked[0][1] <= 0.0:
            return 1.0
        leader_key = ranked[0][0]
        leader = self._by_key[leader_key]
        disagreeing = 0.0
        for key, mass in ranked[1:]:
            h = self._by_key[key]
            for probe in domain:
                try:
                    same = _agree(leader.predict(probe), h.predict(probe))
                except Exception:
                    same = False
                if not same:
                    disagreeing += mass
                    break
        return min(1.0, disagreeing)

    # -- probe selection ------------------------------------------------------------------
    def information_gain(
        self, probe: tuple[Any, ...], outcome_space: Sequence[Any] | None = None
    ) -> float:
        """Expected reduction in entropy, in bits, from asking ``probe``.

        Computed over the PARTITION the probe induces on the hypotheses -- value classes, not an
        alphabet drawn from past observations. Scoring against a remembered alphabet was a real bug
        in the first draft of this module: a probe whose every outcome was new scored zero gain and
        was declared unlearnable, which is precisely the blindness this module exists to expose.
        A probe's worth depends only on how well it splits the posterior, so no alphabet is needed.

        The arithmetic is delegated to the shared deterministic decision primitive, and each
        hypothesis contributes a point mass on its own predicted class -- deterministic programs, so
        the conditional distributions are honest rather than assumed.
        """
        post = self.posterior()
        classes: dict[Hashable, float] = {}
        for key, mass in post.items():
            if mass <= 0.0:
                continue
            h = self._by_key[key]
            try:
                cls = _obs_key(h.predict(probe))
            except Exception:
                cls = ("error",)
            classes[cls] = classes.get(cls, 0.0) + mass
        if len(classes) <= 1:
            return 0.0
        support = list(classes)
        model: dict[Hashable, dict[Hashable, float]] = {}
        for key, mass in post.items():
            if mass <= 0.0:
                continue
            h = self._by_key[key]
            try:
                mine = _obs_key(h.predict(probe))
            except Exception:
                mine = ("error",)
            model[key] = {c: (1.0 if c == mine else 0.0) for c in support}
        live = {k: v for k, v in post.items() if v > 0.0}
        # Renormalise the prior over the live set so the primitive sees a valid distribution.
        total = sum(live.values())
        prior = {k: v / total for k, v in live.items()}
        try:
            return expected_information_gain(prior, model)
        except ValueError:
            return 0.0

    def select_probe(
        self,
        probes: Sequence[tuple[Any, ...]],
        *,
        probe_cost_bits: float = 0.0,
        outcome_space: Sequence[Any] | None = None,
    ) -> tuple[tuple[Any, ...] | None, float]:
        """Best affordable probe and its gain.

        Returns ``(None, gain)`` when the single best probe is still not worth its cost, so the
        caller can distinguish "nothing to learn" from "not worth paying for".
        """
        best: tuple[Any, ...] | None = None
        best_gain = 0.0
        for probe in probes:
            gain = self.information_gain(probe)
            if gain > best_gain + _EPS:
                best_gain = gain
                best = probe
        if best is not None and best_gain <= probe_cost_bits + _EPS:
            return None, best_gain
        return best, best_gain

    def _observable_outcomes(self) -> list[Any]:
        """Outcome alphabet: what the hypotheses can actually produce, plus what was seen.

        A probe whose every outcome all hypotheses already predict identically yields zero gain, so
        this alphabet does not need to be exhaustive -- only to cover the hypotheses' own outputs.
        """
        outs: list[Any] = []
        for _, outcome in self.observations:
            if not any(_agree(o, outcome) for o in outs):
                outs.append(outcome)
        for h in self._by_key.values():
            for probe in self.observations_probes()[:24]:
                try:
                    o = h.predict(probe)
                except Exception:
                    continue
                if not any(_agree(x, o) for x in outs):
                    outs.append(o)
        if not outs:
            outs = [0.0, 1.0]
        return outs

    def observations_probes(self) -> list[tuple[Any, ...]]:
        return [p for p, _ in self.observations]


def _obs_key(value: Any) -> Hashable:
    if isinstance(value, bool):
        return ("bool", value)
    if isinstance(value, (int, float)):
        return ("num", round(float(value), 9))
    return (type(value).__name__, repr(value))


def _agree(a: Any, b: Any) -> bool:
    return _obs_key(a) == _obs_key(b)


# ---------------------------------------------------------------------------------------------
# The load-bearing primitive
# ---------------------------------------------------------------------------------------------
def settle(
    space: VersionSpace,
    *,
    domain: Sequence[tuple[Any, ...]],
    probes: Sequence[tuple[Any, ...]],
    oracle: Callable[[tuple[Any, ...]], Any] | None = None,
    max_queries: int = 8,
    confidence: float = 0.99,
    domain_tolerance: float = 0.01,
    probe_cost_bits: float = 0.0,
) -> Settlement:
    """Ask until the answer is *settled*, or report precisely why it is not.

    The order of the checks is the whole design:

    1. If a probe exists that is worth its cost, ask it. (Learning before deciding.)
    2. Only then ask whether the posterior is concentrated.
    3. Only then ask whether the disagreement that remains lands on the *caller's* domain.
    4. If no affordable probe has any information, refuse: UNSETTLEABLE_BY_THIS_INSTRUMENT.

    Step 4 is the one the previous code got wrong. Blindness is a property of the instrument, and this
    function reports it as such instead of mistaking it for agreement.
    """
    if not space.hypotheses:
        return Settlement(NO_HYPOTHESES, "no candidate programs", None, {}, 0, 0.0, 1.0, 0.0,
                          confidence, 0)
    if not probes:
        return Settlement(UNSETTLEABLE_BY_THIS_INSTRUMENT,
                          "the reachable probe space is empty", None, space.posterior(), 0, 0.0,
                          space.domain_disagreement(domain), 0.0, confidence, 0)

    queries = 0
    total_gain = 0.0
    unaffordable_gain = 0.0

    def _measure() -> Settlement:
        post = space.posterior()
        ranked = sorted(post.items(), key=lambda kv: (-kv[1], str(kv[0])))
        leader = space._by_key[ranked[0][0]] if ranked else None
        conf = ranked[0][1] if ranked else 0.0
        dis = space.domain_disagreement(domain)
        return Settlement(UNDERDETERMINED, "posterior not yet concentrated", leader, post, queries,
                          total_gain, dis, conf, confidence, len(probes))

    while True:
        # 1. Is there anything worth asking?
        probe, gain = space.select_probe(probes, probe_cost_bits=probe_cost_bits)
        if probe is None:
            unaffordable_gain = gain
            result = _measure()
            # 2/3/4 -- decide, in order, which of the three non-SETTLED reasons applies.
            if result.confidence >= confidence and result.domain_disagreement <= domain_tolerance:
                return Settlement(SETTLED, "posterior concentrated before further probing", result.winner,
                                  result.posterior, queries, total_gain,
                                  result.domain_disagreement, result.confidence, confidence,
                                  len(probes))
            if gain > _EPS:
                return Settlement(INSTRUMENT_TOO_COSTLY,
                                  "a probe would help but its cost exceeds the information it buys",
                                  result.winner, result.posterior, queries, total_gain,
                                  result.domain_disagreement, result.confidence, confidence,
                                  len(probes))
            return Settlement(UNSETTLEABLE_BY_THIS_INSTRUMENT,
                              "no reachable probe reduces uncertainty; the instrument is blind here",
                              result.winner, result.posterior, queries, total_gain,
                              result.domain_disagreement, result.confidence, confidence,
                              len(probes))

        if oracle is None:
            result = _measure()
            return Settlement(NO_ORACLE,
                              "a probe would reduce uncertainty but no oracle was supplied",
                              result.winner, result.posterior, queries, total_gain,
                              result.domain_disagreement, result.confidence, confidence,
                              len(probes))
        if space.last_observation_explained_by_none:
            # Asking more cannot help: the true function is not in this space. Naming that is a
            # different fact from "not enough evidence", and the old code blamed the world for it.
            result = _measure()
            return Settlement(EVIDENCE_OUTSIDE_HYPOTHESIS_SPACE,
                              "no hypothesis in the space explains the last observation",
                              None, result.posterior, queries, total_gain,
                              result.domain_disagreement, result.confidence, confidence,
                              len(probes))
        if queries >= max_queries:
            result = _measure()
            return result

        outcome = oracle(probe)
        queries += 1
        total_gain += gain
        space.observe(probe, outcome)

        result = _measure()
        if result.confidence >= confidence and result.domain_disagreement <= domain_tolerance:
            return Settlement(SETTLED, "posterior concentrated after querying", result.winner,
                              result.posterior, queries, total_gain, result.domain_disagreement,
                              result.confidence, confidence, len(probes))
        if queries >= max_queries:
            return Settlement(UNDERDETERMINED,
                              f"query budget exhausted with {result.confidence:.3f} confidence",
                              result.winner, result.posterior, queries, total_gain,
                              result.domain_disagreement, result.confidence, confidence,
                              len(probes))
        continue


# ---------------------------------------------------------------------------------------------
# Diagnosis: a failure must say WHAT WAS MISSING, or nothing can be done about it
# ---------------------------------------------------------------------------------------------
PERIODIC = "PERIODIC"
AFFINE = "AFFINE"
UNEXPLAINED = "UNEXPLAINED"


def diagnose_structure(
    observations: Sequence[tuple[tuple[Any, ...], Any]],
    *,
    max_period: int = 64,
) -> dict[str, Any]:
    """Classify the structure of an observed input/output relation from the numbers alone.

    Why this exists: when the body grammar cannot express the answer, the run returned
    ``HELD_OUT_REFUTED`` -- true, terminal, and useless, because it never said *what* was missing, so
    nothing could be repaired and the operator basis never grew. A refusal that does not teach is only
    half a repair.

    Everything here is computed from the pairs themselves. There is no list of known function names, no
    template table, and no branch on what the caller says the family is called. If the numbers are
    periodic, the period is reported; if they are affine, the coefficients are solved; otherwise the
    answer is UNEXPLAINED, which is a real answer and is never rounded to the nearest familiar shape.
    """
    if len(observations) < 3:
        return {"kind": UNEXPLAINED, "reason": "fewer than three observations"}
    try:
        pairs = sorted((float(x[0]), float(y)) for x, y in observations)
    except (TypeError, ValueError, IndexError):
        return {"kind": UNEXPLAINED, "reason": "non-numeric or non-unary evidence"}

    xs = [x for x, _ in pairs]
    ys = [y for _, y in pairs]
    if len(set(xs)) != len(xs):
        return {"kind": UNEXPLAINED, "reason": "duplicate inputs"}

    # Diagnose on the densest CONTIGUOUS run of unit-spaced points, not on whatever the first point
    # happens to be. Evidence legitimately mixes probes from unrelated places: a refutation at x=-40
    # alongside seeds at 1,2,3 and then a contiguous run from 4 upward. Judging periodicity on the
    # union makes the stray point look like a counterexample, and judging on the whole set silently
    # assumes the caller's inputs are homogeneous. Neither assumption is earned, so the run is chosen
    # by density and the choice is reported.
    runs: list[list[int]] = []
    current = [0]
    for i in range(1, len(xs)):
        if abs((xs[i] - xs[i - 1]) - 1.0) < 1e-9:
            current.append(i)
        else:
            runs.append(current)
            current = [i]
    runs.append(current)
    best = max(runs, key=lambda r: (len(r), -r[0]))
    if len(best) < len(xs):
        # Re-enter with real (input_tuple, output) pairs. Passing internally-normalised values back
        # through the public entry point is how the first version of this recursion broke: the guard
        # against duplicate inputs fired on every call because the subset was being reshaped wrongly.
        sub = [((xs[i],), ys[i]) for i in best]
        result = diagnose_structure(sub, max_period=max_period)
        result = dict(result)
        result["diagnosed_on_subset"] = len(sub)
        result["diagnosed_on_total"] = len(pairs)
        return result

    # 1. Periodicity: f(x) == f(x + p) for every observed pair separated by a multiple of p.
    for period in range(2, max_period + 1):
        # The span test is necessary and NOT sufficient: four points at x = 1,2,3,-40 span 43, pass a
        # span test for period 4, and agree vacuously because no two of them differ by 4. Sparse
        # evidence manufacturing a period is the same defect as a sparse probe list manufacturing
        # equivalence. Require actual pair coverage inside the period before believing anything.
        if xs[-1] - xs[0] < 2 * period:
            continue
        covered = 0
        for probe in range(int(math.floor(xs[0])), int(math.floor(xs[0])) + period):
            if any(abs(x - probe) < 1e-9 for x in xs):
                covered += 1
        if covered < max(3, period // 2):
            continue
        ok = True
        for i in range(len(xs)):
            for j in range(i + 1, len(xs)):
                dx = xs[j] - xs[i]
                if abs(dx - round(dx)) > 1e-9 or int(round(dx)) % period:
                    continue
                if abs(ys[i] - ys[j]) > 1e-9:
                    ok = False
                    break
            if not ok:
                break
        if ok:
            return {
                "kind": PERIODIC,
                "period": period,
                "evidence": len(pairs),
                "span": xs[-1] - xs[0],
            }

    # 2. Affine: exact least-squares on the two extreme points, verified on every observation.
    # A short prefix of a cycle is indistinguishable from a line: the first four values of `x mod 4`
    # are 0,1,2,3, and calling that AFFINE is a confident wrong answer produced by thin evidence.
    # A linear claim therefore needs enough points to make a second cycle visible if one exists.
    if len(xs) >= 6 and xs[-1] != xs[0]:
        slope = (ys[-1] - ys[0]) / (xs[-1] - xs[0])
        intercept = ys[0] - slope * xs[0]
        linear = all(abs((slope * x + intercept) - y) <= 1e-9 for x, y in zip(xs, ys))
        # A short straight stretch is EXACTLY what the first period of a periodic function looks like:
        # 0,1,2,3,4,5 fits a line perfectly and then the cycle jumps. Reporting AFFINE from six
        # consecutive points on integer inputs is therefore not a weaker claim than PERIODIC, it is a
        # claim made without having ruled out the alternative. Distinguish them only when the evidence
        # can: a line must be confirmed at an input far from the fitting points, where a period would
        # have wrapped. Where it cannot be confirmed, the honest answer is that both remain open.
        if linear:
            # Distinguish a line from the first period of a cycle by asking what the evidence says
            # about inputs BEYOND what it covers. A line stays itself past its own span; a cycle
            # repeats values it has already shown. If every observed output is distinct, nothing in the
            # data shows a repeat, and a linear reading is the only one the evidence supports. If any
            # output has recurred, the data contains a cycle and a linear fit over one stretch is
            # unearned.
            if len(set(ys)) == len(ys):
                return {
                    "kind": AFFINE,
                    "slope": slope,
                    "intercept": intercept,
                    "evidence": len(pairs),
                    # A linear reading rests entirely on the absence of a repeat. Absence of a repeat
                    # in a short sample is not proof of linearity -- the first cycle of a periodic
                    # function is exactly this. Callers that can keep looking SHOULD keep looking;
                    # only this flag distinguishes "affine and confirmed" from "affine as far as I
                    # have looked", and collapsing the two is how a creature stops learning early.
                    # Provisionality must be about how much of the function has been checked, and it
                    # must SCALE with what the evidence is starting to look like. A fixed threshold
                    # here silently capped the recoverable structure at its own value: measured, a
                    # hardcoded 16 stopped collection at sixteen consecutive points, so a cycle of
                    # period 20 was reported as a confirmed straight line and never recovered. That is
                    # a frozen constant deciding a verdict -- the exact defect this project keeps
                    # repairing -- so the threshold grows with the length of the unbroken run and with
                    # the span already covered, and only says "confirmed" once the line has been
                    # checked far beyond where a short cycle would have wrapped.
                    # A long unbroken run of DISTINCT outputs is positive evidence for a line: a
                    # cycle would have repeated a value it already showed. So the threshold is not a
                    # constant and not a span ratio; it is whether the evidence has shown the one
                    # thing a cycle cannot hide, which is a repeat. Short runs remain provisional
                    # because a short prefix of a cycle is genuinely indistinguishable from a line.
                    # Short run: a cycle prefix and a line are indistinguishable, so the reading is
                    # provisional and a caller able to keep looking should. Long run with no repeat:
                    # the line has been checked past where any short cycle would have repeated, so it
                    # is confirmed. There is no absolute constant here on purpose -- any fixed cut
                    # silently caps the recoverable period at its own value, which is the defect.
                    # "Confirmed linear" must mean the line was checked past where ANY cycle would
                    # have had to repeat, not past a number someone picked. A fixed 16 was measured to
                    # be a hard ceiling on recoverable structure: collection stopped there, so a
                    # period-20 cycle was reported as a confirmed straight line forever. The bound is
                    # therefore a function of the evidence's own extent -- keep calling it unconfirmed
                    # until the run is long compared with the span it covers, which is the only
                    # quantity that distinguishes "a line" from "a long cycle I have not finished".
                    "provisional": len(xs) < 2 * int(max(2.0, xs[-1] - xs[0])),
                    "line_checked_to": xs[-1],
                    "line_span": xs[-1] - xs[0],
                }
            return {
                "kind": UNEXPLAINED,
                "reason": "linear on a contiguous stretch, which a cycle also is; no distant point confirms it",
                "linear_candidate": {"slope": slope, "intercept": intercept},
                "evidence": len(pairs),
            }

    return {"kind": UNEXPLAINED, "reason": "no diagnosed structure fits the evidence"}


def acquire_period(
    oracle: Callable[[tuple[Any, ...]], Any],
    seed: tuple[Any, ...],
    *,
    max_period: int = 64,
) -> dict[str, Any]:
    """BUY the period with questions instead of reading it from a table.

    Measured: from one seed, the period of ``x mod k`` costs ``k+1`` questions -- 5, 6, 8, 9, 11, 12 and
    16 for k = 4, 5, 7, 8, 10, 11, 15. A lookup table has to exist before the run starts and cannot
    describe a function nobody anticipated; questions do not have that limitation, which is the whole
    difference between an induced operator and a menu entry.

    The search is bounded and its cost is reported, so a caller can decide not to pay. If no period is
    found within the bound the answer is a refusal carrying the cost already spent, not a guess.
    """
    base = oracle(seed)
    asked = 1
    x0 = seed[0]
    for period in range(2, max_period + 1):
        asked += 1
        if not _agree(oracle((x0 + period,)), base):
            continue
        # ONE agreeing point is not a period. `floor(x/3)` agrees with itself at x0=0 and x0=2 by
        # coincidence, and the first draft promoted that single coincidence to "period 2" -- a false
        # positive produced by inferring a general claim from one observation, which is the same error
        # as every defect this project has repaired. The period must be verified at two further
        # offsets that are not multiples of the candidate before it is reported.
        verified = True
        for extra in (2 * period, 3 * period):
            asked += 1
            if not _agree(oracle((x0 + extra,)), base):
                verified = False
                break
        if verified:
            return {"ok": True, "period": period, "questions": asked}
    return {
        "ok": False,
        "period": None,
        "questions": asked,
        "reason": f"no period up to {max_period} matched after {asked} questions",
    }


# ---------------------------------------------------------------------------------------------
# Inducing a period TABLE: the structure comes from the world, not from a template I wrote
# ---------------------------------------------------------------------------------------------
def table_evidence_requirement(period: int, *, factor: int = 4) -> int:
    """How many observations a period table needs before it may claim a structure.

    Exposed so a caller can BUDGET for the compression rule instead of discovering it by failing.
    The rule itself is that the block must be at most a quarter of the evidence, which is what
    separates an induction from a restatement.
    """
    return factor * int(period)


def induce_periodic_table(
    observations: Sequence[tuple[tuple[Any, ...], Any]],
    *,
    max_period: int = 64,
    min_compression: float = 4.0,
) -> dict[str, Any] | None:
    """Find the smallest period-table hypothesis that explains the evidence exactly.

    `min_compression` is the evidence factor the block must clear -- the "at least four times its
    own size" induction guard. The default is the cold rule and every existing caller keeps it. A
    LOWER factor is admissible only when a measured prior licenses it: `licensed_table_policy`
    returns one only for a compression-positive, multi-site, verified library abstraction of this
    family. Lowering the factor without such a prior is how a shorter sample talks itself into a
    pattern, which is the exact failure the 4x rule exists to prevent.

    A ramp like `x mod k` can be recovered by inducing its parameter, but a ramp is a SHAPE I wrote
    down. A function that repeats an arbitrary block -- period 3, values `[5, -2, 7]`, forever -- is
    refused by that machinery (measured: NO_CONSISTENT_HYPOTHESIS), even though it is perfectly
    periodic and three questions determine it completely.

    The hypothesis returned here is `f(x) = block[x mod period]`, where `block` is whatever the world
    put there. That is a claim about infinitely many inputs, not a memory of the ones observed: it
    predicts `f(-1)` and `f(500)` from evidence at `0,1,2`, and any single input can falsify it. A
    lookup that memorised pairs made no such claim, which is why it scored 2/10 the moment it left its
    evidence.

    The block is only believed if it is EXACTLY periodic in the evidence -- every observation must sit
    where the block says it should -- and the smallest such period wins, so a 40-entry table is never
    preferred over a 3-entry one that explains the same data.
    """
    if len(observations) < 3:
        return None
    try:
        pairs = sorted((float(x[0]), float(y)) for x, y in observations)
    except (TypeError, ValueError, IndexError):
        return None
    xs = [x for x, _ in pairs]
    ys = [y for _, y in pairs]
    if len(set(xs)) != len(xs):
        return None
    if any(abs(x - round(x)) > 1e-9 for x in xs):
        return None  # a table over integer residues only

    ints = [int(round(x)) for x in xs]
    origin = min(ints)
    for period in range(2, max_period + 1):
        covered = len({i % period for i in ints})
        # A block inferred from only a fragment of itself is not yet a block. The same coverage lesson
        # as before: sparse, scattered evidence must not be allowed to manufacture a period.
        if covered < period:
            continue
        block: dict[int, float] = {}
        consistent = True
        for i, y in zip(ints, ys):
            slot = i % period
            if slot in block:
                if abs(block[slot] - y) > 1e-9:
                    consistent = False
                    break
            else:
                block[slot] = y
        if consistent and len(block) == period:
            # A table with close to one entry per observation explains the evidence by RESTATING it.
            # That is a memory, not an induction: it predicts nothing beyond what it was told, which is
            # exactly the 2/10 lookup this project already removed. The bound must scale with the
            # evidence -- a fixed number here would be another ceiling on learning, and a fixed
            # threshold of 16 already cost a full round. Requiring the block to be at most a quarter of
            # the observations means the claim must cover at least four times its own size.
            if len(pairs) < min_compression * period:
                continue
            return {
                "period": period,
                "block": [block[k] for k in range(period)],
                "origin": origin,
                "evidence": len(pairs),
                # Description length in the only currency that matters here: how many values must be
                # stated versus how many observations they explain. A table with nearly as many
                # entries as observations is memorisation and is reported as such.
                "compression": len(pairs) / float(period),
            }
    return None


def candidate_period(
    observations: Sequence[tuple[tuple[Any, ...], Any]],
    *,
    max_period: int = 64,
) -> int | None:
    """Smallest period consistent with the evidence so far, even if not yet fully covered.

    `induce_periodic_table` requires complete coverage plus a compression margin, so it cannot be used
    to answer "how much more evidence do I need?". This can: it looks for the smallest period that does
    not CONTRADICT the evidence, which is exactly the quantity a collection loop must budget against.
    """
    if len(observations) < 2:
        return None
    try:
        pairs = sorted((float(x[0]), float(y)) for x, y in observations)
    except (TypeError, ValueError, IndexError):
        return None
    if any(abs(x - round(x)) > 1e-9 for x in [p[0] for p in pairs]):
        return None
    ints = [int(round(x)) for x, _ in pairs]
    ys = [y for _, y in pairs]
    for period in range(2, max_period + 1):
        block: dict[int, float] = {}
        ok = True
        for i, y in zip(ints, ys):
            slot = i % period
            if slot in block:
                if abs(block[slot] - y) > 1e-9:
                    ok = False
                    break
            else:
                block[slot] = y
        if ok:
            return period
    return None
