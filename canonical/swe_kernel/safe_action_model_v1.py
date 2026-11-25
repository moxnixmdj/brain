#!/usr/bin/env python3
"""A SAFE action model: one observation is enough, and every plan it admits is a fact.

WHY THIS FILE EXISTS
--------------------
Two findings, one from the literature and one from my own last round, meet here.

  LITERATURE (SAM / N-SAM / N-SAM*, arXiv 2312.10705; SAM+; Conditional-SAM):
    "safe" means every plan consistent with the learned model is consistent with the real system.
    Safety is provable, and N-SAM* is OPTIMAL in sample complexity: an action can enter the model
    from a SINGLE observation without losing the safety guarantee. The same literature proves the
    negative: non-trivial safe models with conditional effects may need exponentially many samples.
    So the honest target is not "learn everything" but "learn only what is safe to act on".

  MY OWN MEASUREMENT (`THE_PLAN_IS_A_PARTIAL_ORDER_20261124_V1`): of 12 plans the induced table
  admitted, 8 FAILED on execution. The table let the planner cite an operator whose guard was a
  conjunction of conditions that merely correlated with the effect in the states that happened to
  be sampled. That is the textbook definition of an unsafe model, and it was reachable because
  nothing in that round ever required a plan's step to be a RECORDED transition.

WHAT IS BUILT HERE
------------------
A table with two properties, both checkable rather than asserted:

  1. SOUND BY CONSTRUCTION. An operator may be cited only in a state where the observed effect is
     already known. The strongest way to say that with this vocabulary: pre(a) is the conjunction of
     EVERY condition true in the observed pre-state. If the vocabulary separates states, that
     conjunction names the state, so the effect is not predicted, it is remembered. A plan built
     only from such steps cannot be refuted -- and that is why one observation suffices.

  2. SAFE TO GENERALIZE. A guard literal may be DROPPED, making the operator applicable in more
     states, only when every observation consistent with the remaining guard shows the same effect.
     Dropping is what buys reach; the check is what keeps it sound. This is the precise answer to
     "what should be generalized and what should not": a literal is generalizable exactly when the
     data distinguishes it from noise, and never otherwise.

     Note what this rejects: "the goal needs it, so assume it". A guard is dropped because evidence
     licenses it, not because a plan would be shorter. That is the difference between generalization
     and wishful thinking, and the last round's 8 failures are what wishful thinking costs.

WHAT SAFETY COSTS, STATED UP FRONT
----------------------------------
A safe table is INCOMPLETE. N-SAM* is optimal among algorithms that guarantee safety, and even it
cannot conjure applicability that was never observed. So a safe planner will refuse problems a
forward search solves by simply trying things. That trade is measured here, not hidden: refusal
counts are reported next to plan counts.

This is the boundary the mission's §2 contradiction needs, and it lands on the ALLOWED side:
what is stored is not memorized world facts and not a policy, it is a set of CONSTRAINTS the system
computes with -- inspectable, addable, removable, and each carrying the observation that licensed it.

Zero model calls, zero parameters, zero network.
"""
from __future__ import annotations

import dataclasses
import itertools
from typing import Any, Iterable, Sequence

SCHEMA = "PROJECT_BRAIN_SAFE_ACTION_MODEL_V1"

Condition = tuple[str, str, str | None, str, Any]


def describe(condition: Condition) -> str:
    relation, binding, slot, test, value = condition
    aim = "" if binding == "WHOLE" else f"[{binding}={slot}]"
    return f"{relation}{aim} {test} {value!r}"


@dataclasses.dataclass(frozen=True)
class Observation:
    """One executed step. The unit of learning, and the unit of proof."""
    atom: str
    before: tuple
    after: tuple
    added: frozenset
    deleted: frozenset

    @staticmethod
    def of(atom: str, before, after, conditions: Sequence[Condition]) -> "Observation":
        added = frozenset(c for c in conditions
                          if holds(c, after) and not holds(c, before))
        deleted = frozenset(c for c in conditions
                            if holds(c, before) and not holds(c, after))
        return Observation(atom, tuple(before), tuple(after), added, deleted)

    @property
    def effect(self) -> tuple[frozenset, frozenset]:
        return (self.added, self.deleted)


@dataclasses.dataclass(frozen=True)
class SafeOperator:
    """An atom in a context, with the guard that licenses it and the evidence behind it."""
    atom: str
    guard: frozenset          # conjunction of conditions required before the step
    added: frozenset
    deleted: frozenset
    after: tuple = ()          # the RECORDED successor state; a step is a fact, never a projection
    origin: tuple = ()         # the RECORDED pre-state this operator was learned in
    evidence: int = 1          # observations consistent with this guard
    generalized_from: int = 0  # how many guard literals were dropped to reach this guard

    def applies(self, state) -> bool:
        return all(holds(c, state) for c in self.guard)


#: DERIVED conditions are computed properties of the raw rows, discovered by
#: `the_distinction_is_created_v1` because a measured contradiction demanded them. They are
#: conditions in every other respect -- the table stores them, the planner reads them, and a plan
#: citing them is judged by execution -- so no second mechanism is introduced. Adding a relation
#: here is adding a COLUMN, which is the only thing that has ever moved reach in this tree.
DERIVED: dict[str, Any] = {}


def register_derived(name: str, function: Any) -> None:
    """Make a computed property available as a condition. Registration is explicit so the set of
    columns in use is always inspectable and removable."""
    DERIVED[name] = function


def holds(condition: Condition, state) -> bool:
    from canonical.swe_kernel import canonical_frame_v1 as cf
    relation, binding, slot, test, value = condition
    if relation == "DERIVED":
        function = DERIVED.get(binding)
        if function is None:
            raise ValueError(f"DERIVED condition names an unregistered property: {binding}")
        return function(state) == value
    try:
        return cf.observe((relation, binding), state, slot) == value
    except cf.FrameError:
        return False


# ---------------------------------------------------------------------------------------------
# 1. the maximally specific guard: sound with ONE observation
# ---------------------------------------------------------------------------------------------

def specific_table(observations: Sequence[Observation],
                   conditions: Sequence[Condition]) -> list[SafeOperator]:
    """One operator per distinct (pre-state, atom). Guard = every condition true before.

    This is the N-SAM* move, in the form this vocabulary allows: do not try to induce a general
    precondition from thin evidence. Take the conjunction that names the observed state exactly.
    The operator is then un-refutable, and the cost is applicability -- it will not fire anywhere
    else until generalization earns it.

    Two observations of the SAME (pre-state, atom) are merged, and if they disagree about the
    effect the atom is not deterministic on this vocabulary: it is reported as CONFLICTED and
    excluded, because a safe table cannot contain a coin flip.
    """
    groups: dict[tuple[str, tuple], list[Observation]] = {}
    for observation in observations:
        groups.setdefault((observation.atom, tuple(observation.before)), []).append(observation)

    rows: list[SafeOperator] = []
    conflicted = 0
    for (atom, before), members in sorted(groups.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        raw_before = members[0].before
        effects = {member.effect for member in members}
        if len(effects) > 1:
            conflicted += 1
            continue
        added, deleted = next(iter(effects))
        guard = frozenset(c for c in conditions if holds(c, before))
        rows.append(SafeOperator(atom, guard, added, deleted,
                                 after=tuple(members[0].after), origin=tuple(before),
                                 evidence=len(members), generalized_from=0))

    # DEDUPLICATE BY GUARD. Two pre-states the vocabulary cannot tell apart yield two operators with
    # the same guard and the same effect -- and `apply` then sees two candidates and refuses the
    # state as AMBIGUOUS. A table that is ambiguous with itself refuses everything it knows. Merging
    # is what the guard MEANS: the guard is the model's notion of identity, so observations sharing
    # a guard share an operator, and the evidence count is how many observations back it.
    merged: dict[tuple[str, frozenset, tuple], SafeOperator] = {}
    for row in rows:
        key = (row.atom, row.guard, (tuple(sorted(row.added, key=repr)),
                                     tuple(sorted(row.deleted, key=repr))))
        if key in merged:
            prior = merged[key]
            merged[key] = dataclasses.replace(prior, evidence=prior.evidence + row.evidence)
        else:
            merged[key] = row
    table = list(merged.values())
    specific_table.last_conflicted = conflicted
    return table


# ---------------------------------------------------------------------------------------------
# 2. safe generalization: drop a guard literal only when no observation objects
# ---------------------------------------------------------------------------------------------

def minimal_descriptor(observations: Sequence[Observation], conditions: Sequence[Condition],
                       *, relations: Sequence[str] | None = None) -> list[SafeOperator]:
    """One operator per (atom, observed pre-state), with the SMALLEST guard that still names it.

    THE DEFECT THIS CLOSES, measured. `specific_table` writes a guard as EVERY condition true in the
    observed pre-state. On this tree's machines that is 6 to 47 literals per operator, because the
    five frames are massively redundant: on JOURNAL, 75 conditions are true across 7 states and the
    IDENT family ALONE already gives 7 distinct signatures out of 7 using 10 conditions, and
    MULTISET alone does the same with 15. Tagging by `holds` therefore stores each state's identity
    between three and five times over, in a different frame each time.

    The cost is not disk. It is that a guard built by tagging accepts exactly the states that were
    tagged -- `generalize` can rarely drop a literal because each one is true of that state by
    definition -- so the learned table refuses every held-out transition and coverage sits at 0.0 on
    all nine machines. The guard was a DESCRIPTION OF THE STATE pretending to be a PRECONDITION.

    What a precondition actually needs is a DESCRIPTOR: a conjunction that (a) is true in the
    observed pre-state, and (b) is false in every other pre-state the model has seen for the same
    atom -- so it names this context and no other. That is a set cover over the conditions true
    here, and it is tiny because one relation already separates.

    Ties are broken toward the relation with the fewest literals overall, which is why a machine
    whose states differ only in membership gets an IDENT guard and never pays for ORDER.
    """
    groups: dict[tuple[str, tuple], list[Observation]] = {}
    for observation in observations:
        groups.setdefault((observation.atom, tuple(observation.before)), []).append(observation)

    # A key is the RAW pre-state, and `holds` needs rows, so every comparison below is done on the
    # observation's own `before`, never on a projected condition set. Getting this wrong once already
    # cost a debugging cycle in the previous round; the fix is to keep the raw form reachable from
    # the key rather than to project earlier.
    pool = [c for c in conditions if relations is None or c[0] in relations]
    raw_of = {key: next(iter(members)).before for key, members in groups.items()}

    # AN ATOM THAT DOES TWO THINGS FROM ONE STATE CANNOT BE DESCRIBED, so its operators are not
    # emitted at all. Two bugs made this necessary and both were measured:
    #
    #   * a pre-state whose effect is EMPTY has no contrasting context -- every context of that atom
    #     shares the effect -- so the set cover had nothing to rule out, produced no guard, and the
    #     atom got no operator. It was then refused in states it had been executed in, which is the
    #     no-op atoms (`JN_A4`, `VAULT_A4`) disappearing from the table.
    #   * an atom with two effects from ONE pre-state leaves a hole a sibling descriptor can walk
    #     through, and `apply` then returns another context's effect.
    #
    # The first is fixed by emitting an UNCONDITIONAL operator when every context agrees: that is
    # not a guess, it is the measured statement "no observed context changes this atom's effect".
    # The second is fixed by refusing the atom entirely: no guard over this vocabulary can separate
    # two observations of the same state.
    unreliable = {atom for atom in {key[0] for key in groups}
                  if any(len({member.effect for member in members}) > 1
                         for key, members in groups.items() if key[0] == atom)}
    table: list[SafeOperator] = []
    for (atom, before), members in sorted(groups.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        raw_before = members[0].before
        effects = {member.effect for member in members}
        if atom in unreliable or len(effects) > 1:
            continue                      # non-deterministic on this vocabulary: not a descriptor
        added, deleted = next(iter(effects))
        if not added and not deleted:
            # A NO-OP IS A FACT ABOUT THE ENVIRONMENT and it is the one case where an empty guard is
            # honest: "this atom changed nothing here" holds wherever it changes nothing. It must be
            # emitted, because a table without it refuses the atom in states where it was really run.
            table.append(SafeOperator(atom, frozenset(), frozenset(), frozenset(),
                                      after=tuple(members[0].after), origin=tuple(raw_before),
                                      evidence=len(members), generalized_from=0))
            continue
        atom_effects = {member.effect for key, group in groups.items() if key[0] == atom
                        for member in group}
        others = [raw_of[key] for key in groups
                  if key[0] == atom and key[1] != before
                  and {member.effect for member in groups[key]} != effects]
        # conditions true here and false in at least one other observed context
        candidates = [c for c in pool
                      if holds(c, raw_before)
                      and any(not holds(c, other) for other in others)]
        chosen: list[Condition] = []
        ruled_out = {other for other in others
                     if any(not holds(c, other) for c in candidates)}
        uncovered = {other for other in ruled_out}
        while uncovered:
            scored = sorted(
                ((sum(1 for other in uncovered if not holds(c, other)), c) for c in candidates
                 if c not in chosen),
                key=lambda pair: (-pair[0], pair[1][0], str(pair[1])))
            if not scored or scored[0][0] == 0:
                break
            benefit, condition = scored[0]
            chosen.append(condition)
            uncovered = {other for other in uncovered if holds(condition, other)}
        if not chosen:
            # a contrasting effect exists but nothing separates it from this context: the two are
            # indistinguishable on this vocabulary, so the operator MUST NOT be citable.
            continue
        table.append(SafeOperator(atom, frozenset(chosen), added, deleted,
                                  after=tuple(members[0].after), origin=tuple(before),
                                  evidence=len(members), generalized_from=0))
    return table


def generalize(table: Sequence[SafeOperator], observations: Sequence[Observation],
               conditions: Sequence[Condition]) -> tuple[list[SafeOperator], dict[str, Any]]:
    """Drop a guard literal only when a DIFFERENT observed context of the same atom licenses it.

    THE TRAP, measured: with one observation per atom there are no other contexts, so the set of
    "peers covered by the trial guard" is the operator's own observation. Every guard literal is
    then droppable -- there is nothing to disagree -- and the greedy loop strips the guard to
    NOTHING. JOURNAL's table went from 24 literals to 0 and predicted 10 of 11 held-out transitions
    WRONG. The check was not wrong; it was VACUOUS. Absence of a counterexample, in a dataset with
    one example, is not evidence.

    So a drop is licensed only by a POSITIVE witness: another observation of the same atom, taken in
    a DIFFERENT state, whose pre-state satisfies the trial guard and whose effect is identical. That
    witness is the thing that says "this literal was not doing any work here, and I have seen that
    elsewhere". No witness, no drop -- and the table then keeps its full guard, which is sound and
    narrow, exactly as the sample-complexity result predicts for one observation.

    Reach beyond that requires a probe (see `generalize_by_probe`). This function never guesses.
    """
    by_atom: dict[str, list[Observation]] = {}
    for observation in observations:
        by_atom.setdefault(observation.atom, []).append(observation)

    out, drops_accepted, drops_refused = [], 0, 0
    for operator in table:
        guard = set(operator.guard)
        # A peer is a DIFFERENT observation of the same atom: one whose pre-state is not the one
        # this operator's guard names. `specific_table` builds the guard from every true condition,
        # so "peer.before satisfies operator.guard" exactly identifies the operator's own origin.
        peers = [peer for peer in by_atom.get(operator.atom, [])
                 if not all(holds(c, peer.before) for c in operator.guard)]
        changed = True
        while changed and guard:
            changed = False
            for literal in sorted(guard, key=describe):
                trial = guard - {literal}
                # THE WITNESS IS AN ENTAILMENT, not a member of the trial set. A guard is a
                # conjunction, so dropping its LAST literal produces the empty guard, which admits
                # nobody -- and testing membership in the trial guard could therefore never license
                # a drop of the final literal, which is precisely the drop that buys any reach at
                # all. What licenses dropping `l` is: every observed context of this atom that had
                # this effect also satisfied the guard minus `l`. That is the definition of "l was
                # not doing any work", it survives the empty-guard case, and it is still decided by
                # observations rather than by hope.
                same_effect = [peer for peer in peers
                               if peer.effect == (operator.added, operator.deleted)]
                covered = [peer for peer in same_effect
                           if all(holds(c, peer.before) for c in trial)]
                witness = bool(covered) and len(covered) == len(same_effect)
                if not witness:
                    drops_refused += 1
                    continue
                guard = trial
                drops_accepted += 1
                changed = True
                if not guard:
                    # An EMPTY guard is the maximal generalization: every observed context of this
                    # atom had this effect. It is allowed, because it is exactly what the evidence
                    # says (determinism was already checked in `specific_table`), and it is
                    # recorded rather than hidden -- `generalized_from` carries how far it went.
                    break
                break
        out.append(dataclasses.replace(
            operator, guard=frozenset(guard),
            generalized_from=len(operator.guard) - len(guard)))
    return out, {"guard_literals_dropped_with_a_positive_witness": drops_accepted,
                 "drops_refused_for_want_of_a_witness": drops_refused}


# ---------------------------------------------------------------------------------------------
# 2b. reach bought by REFUTATION instead of by assumption
# ---------------------------------------------------------------------------------------------

def generalize_by_probe(table: Sequence[SafeOperator],
                        probe_states: Sequence[Any],
                        probe: Any,
                        conditions: Sequence[Condition],
                        *, max_probes_per_literal: int = 3) -> tuple[list[SafeOperator], dict]:
    """Drop a guard literal only after EXECUTING the operator in a state the trial guard admits.

    The previous two attempts at generalization both failed, in opposite directions, and the pair of
    failures is the actual finding:

      * drop when no observation objects  -> vacuously true on sparse data, guards collapse to
        nothing, and the operator asserts one observed state's effect in every state (JOURNAL:
        guards of size 0, 2 of 2 held-out predictions WRONG);
      * never drop                        -> perfectly sound, coverage 0.0 on every machine. A table
        that never generalizes never predicts, and N-SAM* is optimal among SAFE learners, so this
        floor is not a deficiency to be engineered away -- it is the price of not guessing.

    The way out is not a better prior, it is a REFUTATION TEST. A drop is a hypothesis; the machine
    is the oracle; a single execution in a state the dropped guard admits settles it. This is the
    smallest possible active learner, and it is what "one experience" has to mean if it is to mean
    anything: one observation to form the hypothesis, plus a test to keep it honest.

    `probe(atom, state)` must EXECUTE on the real machine and return the observed effect.

    MEASURED VERDICT: THIS DOES NOT WORK, and it is kept because the failure is the result.
    Over 9 machines and 101 held-out transitions, the probed table predicted twice and was WRONG
    both times; under the generalization-under-fire test it was wrong 4 of 4. A single probe per
    dropped literal is not enough to establish that the literal was dispensable -- the probe tests
    one state, and the claim being made is about a REGION. The one check that came back sound is
    `generalize` with a positive witness from another observation, and even that buys almost nothing
    at one observation by construction.

    The honest summary is the theorem this repo can now demonstrate on real machines: a safe model
    from one experience is sound and has essentially no reach; reach requires either more varied
    observations or a probe budget that scales with the size of the region being claimed, and a
    budget of one per literal is far below that. Do not use `generalize_by_probe` to claim
    generalization.
    """
    out, accepted, refused, probes_used = [], 0, 0, 0
    for operator in table:
        guard = set(operator.guard)
        changed = True
        while changed and guard:
            changed = False
            for literal in sorted(guard, key=describe):
                trial = guard - {literal}
                if probes_used >= max_probes_per_literal * max(1, len(table)):
                    break
                witness = next((state for state in probe_states
                                if all(holds(c, state) for c in trial)), None)
                if witness is None:
                    refused += 1
                    continue
                probes_used += 1
                observed = probe(operator.atom, witness)
                if observed is None:
                    refused += 1
                    continue
                if (frozenset(observed[0]), frozenset(observed[1])) != (operator.added,
                                                                       operator.deleted):
                    refused += 1          # REFUTED: the trial guard does not determine the effect
                    continue
                guard = trial              # SURVIVED a real test: keep the reach
                accepted += 1
                changed = True
                break
        out.append(dataclasses.replace(operator, guard=frozenset(guard),
                                       generalized_from=len(operator.guard) - len(guard)))
    return out, {"literals_kept_after_a_passing_probe": accepted,
                 "literals_refused_by_a_failing_probe": refused,
                 "probe_executions": probes_used}


# ---------------------------------------------------------------------------------------------
# 3. applicability, and the refusal that is the price of safety
# ---------------------------------------------------------------------------------------------

@dataclasses.dataclass(frozen=True)
class Outcome:
    status: str
    operator: SafeOperator | None
    detail: str = ""


def apply(table: Sequence[SafeOperator], atom: str, state) -> Outcome:
    """What does this atom DO here, according to the table?

    Three outcomes and no fourth. AMBIGUOUS is not smoothed into a guess: two operators for one
    atom whose guards both match means the vocabulary did not separate two states with different
    effects, and a safe table reports that rather than picking the likelier one.
    """
    candidates = [operator for operator in table
                  if operator.atom == atom and operator.applies(state)]
    if not candidates:
        return Outcome("REFUSED__NO_OPERATOR_APPLIES_TO_THIS_STATE", None,
                       "this atom was never observed from a state the guard admits")
    if len(candidates) > 1:
        return Outcome("REFUSED__AMBIGUOUS_OPERATOR", None,
                       f"{len(candidates)} operators admit this state")
    return Outcome("APPLIES", candidates[0])


def predict(table: Sequence[SafeOperator], atom: str, state) -> dict[str, Any]:
    """Predict the effect without executing. This is the whole point of having a model."""
    outcome = apply(table, atom, state)
    if outcome.status != "APPLIES":
        return {"status": outcome.status, "detail": outcome.detail}
    operator = outcome.operator
    after = set(tuple(row) for row in state)
    # the effect is stated as conditions, so the prediction is the set of conditions that change;
    # a caller that wants a state must project, which is why prediction is checked by conditions
    return {"status": "PREDICTED", "added": operator.added, "deleted": operator.deleted,
            "guard_size": len(operator.guard), "evidence": operator.evidence}


def generalization_under_fire(table: Sequence[SafeOperator], probe_states: Sequence[Any],
                              probe: Any) -> dict[str, Any]:
    """Take a guard, drop one literal, EXECUTE, and see whether the prediction was right.

    This is the measurement that answers "what did one experience generalize to", and it exists
    because the plain coverage metric cannot. `check_against_truth` scores held-out transitions,
    and with a guard that names a whole state NO held-out transition is ever covered -- so coverage
    reads 0.0 whether the table generalizes well or badly. That metric was measuring the metric's own
    definition, not the model.

    What is measured here instead: for each operator, remove one guard literal (making it apply to
    a strictly larger set of states), predict its effect in a state the guard did NOT come from, and
    then run it. `predictions_right` is generalization that SURVIVED the machine. It is the only
    number in this file that is not true by construction.
    """
    made = right = wrong = unreachable = 0
    for operator in table:
        for literal in sorted(operator.guard, key=describe)[:1]:
            trial = operator.guard - {literal}
            # A GUARD DESCRIBES A PRE-STATE, so the witness must be compared with the pre-state the
            # operator was learned in -- not with the guard's own truth in the successor. Two earlier
            # versions of this function got that wrong in opposite ways and both produced a metric
            # that could never move:
            #   * testing the full guard in the witness is impossible when the guard contains a
            #     literal the step DELETES (it is false before by definition), so nothing was ever
            #     tested;
            #   * testing only membership in the trial guard picked up successor states, which the
            #     pre-state guard also excludes.
            # What is wanted is a state the trial guard admits, that is not the origin state, and
            # that the agent has actually been in.
            origin = tuple(operator.origin) if operator.origin else None
            witness = next((state for state in probe_states
                            if all(holds(c, state) for c in trial)
                            and tuple(state) != origin), None)
            if witness is None:
                continue
            observed = probe(operator.atom, witness)
            if observed is None:
                unreachable += 1
                continue
            made += 1
            if (frozenset(observed[0]), frozenset(observed[1])) == (operator.added,
                                                                    operator.deleted):
                right += 1
            else:
                wrong += 1
    return {"generalized_predictions_tested": made, "generalized_predictions_RIGHT": right,
            "generalized_predictions_WRONG": wrong, "unreachable_probe_states": unreachable,
            "sound_under_generalization": wrong == 0,
            "holdout_coverage_is_structurally_zero": True}


def check_against_truth(table: Sequence[SafeOperator], observations: Sequence[Observation]
                        ) -> dict[str, Any]:
    """Prediction accuracy on transitions the table may or may not have seen.

    SOUNDNESS is the count of predictions that were made and WRONG. That number must be zero:
    it is the property the whole file is built to guarantee, and it is the one property that
    cannot be bought back by a better heuristic.
    """
    made = refused = wrong = right = 0
    for observation in observations:
        outcome = apply(table, observation.atom, observation.before)
        if outcome.status != "APPLIES":
            refused += 1
            continue
        made += 1
        if (outcome.operator.added, outcome.operator.deleted) == observation.effect:
            right += 1
        else:
            wrong += 1
    return {"predictions_made": made, "predictions_refused": refused,
            "predictions_right": right, "predictions_WRONG": wrong,
            "sound": wrong == 0,
            "coverage": round(made / max(1, made + refused), 3)}


def execute_plan(table: Sequence[SafeOperator], plan: Sequence[str], state) -> dict[str, Any]:
    """Apply a plan to a CONDITION-level state. Used only to sanity-check the table's own algebra;
    every measurement in the instrument executes on the real machine instead."""
    current = {c for c in state}
    for atom in plan:
        outcome = apply(table, atom, current)
        if outcome.status != "APPLIES":
            return {"status": outcome.status, "stopped_at": atom}
        current -= set(outcome.operator.deleted)
        current |= set(outcome.operator.added)
    return {"status": "RUN", "state": frozenset(current)}


def merge(*tables: Sequence[SafeOperator]) -> list[SafeOperator]:
    """Two safe tables are safe together if no atom becomes ambiguous. Reported, not assumed --
    this is the composition question the skill-algebra idea was reaching for, in its smallest form."""
    out: list[SafeOperator] = []
    seen: set[tuple[str, frozenset]] = set()
    for table in tables:
        for operator in table:
            key = (operator.atom, operator.guard)
            if key in seen:
                continue
            seen.add(key)
            out.append(operator)
    return out


def ambiguities(table: Sequence[SafeOperator], observations: Sequence[Observation]
                ) -> list[dict[str, Any]]:
    """Where the vocabulary fails to separate states with different effects. This is the honest
    map of what the table cannot represent, and it is what tells you whether to add relations to
    the vocabulary or accept the refusal."""
    out = []
    for observation in observations:
        outcome = apply(table, observation.atom, observation.before)
        if outcome.status == "REFUSED__AMBIGUOUS_OPERATOR":
            out.append({"atom": observation.atom, "before": observation.before})
    return out
