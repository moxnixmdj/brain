#!/usr/bin/env python3
"""Partial-order planning over MEASURED operators. The sound way to cut the branching factor.

WHY THIS FILE EXISTS
--------------------
The previous round measured its own strongest-looking idea failing:

    PRUNE   restrict the action set to atoms that move a frame the goal is stated on
            -> 4.9x fewer executions, and it LOST 5 of 14 plans.
    ORDER   keep every atom, try the relevant ones first
            -> lost nothing, and saved nothing (2586 vs 2502 executions).

The reason is not a bug. In a conjunctive goal the second clause is often only reachable after the
first action, so an atom that moves no wanted frame at the root is still the atom step two needs.
Goal-directed pruning of the action set is **incomplete**, and no amount of care at the root fixes
it. That is the classical statement of the problem, and the classical answer is not a better
heuristic -- it is a different search space:

    forward search commits to an order as it goes, so an interaction between two subgoals is only
    discovered after both have been committed to. Partial-order planning commits to nothing it does
    not have to: it links each condition to one action that establishes it, protects that link
    against actions that would delete it, and orders two steps only when a link or a threat forces
    it. The branching factor at each choice is the number of actions relevant to ONE open
    condition (AIMA ch.11: "an action is relevant to a conjunctive goal if it achieves one of the
    conjuncts"), which is why it is complete and still cheap. Greedy backwards chaining -- achieve
    one conjunct, then the next -- is the version that is NOT complete (Sussman's anomaly,
    Sacerdoti 1975), and it is kept here as a control so the difference is measured, not assumed.

WHAT AN OPERATOR IS HERE, AND WHAT IT IS NOT
--------------------------------------------
An operator is not written by hand and not read from a manual. It is the result of a measurement:

    pre   the frame-tests that hold in exactly the states where this atom's effect occurs
    add   the frame-tests this atom makes true
    del   the frame-tests this atom makes false

Every one of those is computed from readings taken before and after real executions, on the
machine's own reader. The operator's identity is opaque (`G2_A3`, `LS_A1`). Nothing in this file
knows what `tar`, `git`, `sort` or a block is.

THE THREE CHECKS THIS FILE WILL NEVER SKIP
------------------------------------------
  1. A plan is a PARTIAL order. It is reported as a partial order, and the total order used for
     execution is one topological sort of it -- named as a choice, because the partial order is
     the thing that was proved.
  2. A plan is executed and then judged by the machine's own reader. A plan that was not run is a
     hypothesis.
  3. A refusal names its reason. `NO_RELEVANT_OPERATOR` is a measurement about this machine's
     atoms; `UNRESOLVED_THREAT` is a statement about the operator set, not a reason to guess.

WHAT THIS DOES NOT DO
---------------------
No nonlinear/conditional effects, no sensing, no durative actions, no numerics beyond equality and
count, and no learning of operators across machines (that is the frame module's job, and the two
have not been wired). It searches; it does not invent. Zero model calls, zero parameters.
"""
from __future__ import annotations

import dataclasses
import itertools
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_PARTIAL_ORDER_PLANNER_V1"

#: A condition is (relation, binding, slot, test, value). `test` is "equals" or "count_is" -- the
#: two forms a frame can be asked, and no third. A condition is a *frame-test*, which is the only
#: kind of precondition this vocabulary can state (see canonical_frame_v1.stateable).
Condition = tuple[str, str, str | None, str, Any]


def describe(condition: Condition) -> str:
    """A condition as a person reads it. Used in every refusal, so a failure names its cause."""
    relation, binding, slot, test, value = condition
    aim = "" if binding == "WHOLE" else f"[{binding}={slot}]"
    return f"{relation}{aim} {test} {value!r}"


@dataclasses.dataclass(frozen=True)
class Operator:
    """One atom, described by what was measured about it. Nothing here is inferred from a name.

    `ident` names the OPERATOR (which may be one context of an atom); `atom` names the command to
    execute. The two differ exactly when the atom's effect depends on the state, which is the
    measured fact that the earlier version of this file got wrong.
    """
    ident: str
    pre: frozenset          # conditions that held in every state where the effect occurred
    add: frozenset          # conditions the effect makes true
    delete: frozenset       # conditions the effect makes false
    atom: str = ""
    context_identified: bool = True   # False => the atom's effect is not separable by any measured
                                      # condition, so this operator may not be cited by a planner

    def command(self) -> str:
        return self.atom or self.ident

    def relevant(self, condition: Condition) -> bool:
        """AIMA's definition, unchanged: an operator is relevant to a condition if it can
        establish it. This single predicate is where the branching factor is won."""
        return condition in self.add


@dataclasses.dataclass(frozen=True)
class Step:
    ident: str
    operator: Operator | None      # None for the two dummy steps


START = Step("<start>", None)
FINISH = Step("<finish>", None)


@dataclasses.dataclass
class Plan:
    steps: list[Step] = dataclasses.field(default_factory=list)
    order: set[tuple[str, str]] = dataclasses.field(default_factory=set)   # (before, after)
    links: list[tuple[str, Condition, str]] = dataclasses.field(default_factory=list)

    def clone(self) -> "Plan":
        return Plan(list(self.steps), set(self.order), list(self.links))

    def add_step(self, step: Step) -> "Plan":
        out = self.clone()
        out.steps.append(step)
        return out

    def add_order(self, before: str, after: str) -> "Plan":
        out = self.clone()
        out.order.add((before, after))
        return out

    def add_link(self, source: str, condition: Condition, sink: str) -> "Plan":
        out = self.clone()
        out.links.append((source, condition, sink))
        return out


class PlannerError(ValueError):
    pass


# ---------------------------------------------------------------------------------------------
# the search: open condition -> relevant operator -> causal link -> protect it
# ---------------------------------------------------------------------------------------------

def plan(initial: Iterable[Condition], goal: Iterable[Condition],
         operators: Sequence[Operator], *, max_steps: int = 8,
         max_nodes: int = 4000) -> dict[str, Any]:
    """Search for a partial order that establishes `goal` from `initial`.

    The algorithm is POP with chronological backtracking over its only three choices: which open
    condition to work on, which operator (if several are relevant) establishes it, and how to
    resolve a threat (promotion or demotion). Nothing commits to an execution order until the end.

    A condition already true in the initial state is linked to `<start>` and becomes an axiom --
    that is how "already true" stays free rather than being re-established by an action.
    """
    initial_set = frozenset(initial)
    goal_set = frozenset(goal)
    operators = [op for op in operators if op.context_identified]
    # The null plan: two dummy steps and NO links. The goals are open, and stay open until a
    # producer is linked to them or `<start>` is shown to establish them. A first version seeded a
    # self-link per goal (goal -> goal at <finish>), which made every goal "supported" at the root
    # and let the planner return an empty plan for an unsatisfied goal.
    root = Plan(steps=[START, FINISH])
    root.order = {(START.ident, FINISH.ident)}
    stats = {"nodes": 0, "relevant_checks": 0, "threats_resolved": 0}

    def open_conditions(current: Plan) -> list[tuple[str, Condition]]:
        """Every required condition that no causal link yet establishes.

        TWO SOURCES, and the first version of this function had only the second -- which let the
        planner return a plan with ZERO steps for an unsatisfied goal, because a goal nobody had
        opened was a goal nobody had to achieve:

          1. the preconditions of every step in the plan;
          2. the goal itself, at `<finish>`.
        """
        out: list[tuple[str, Condition]] = []
        for step in current.steps:
            if step.operator is None:
                continue
            supported = {cond for _src, cond, sink in current.links if sink == step.ident}
            for condition in sorted(step.operator.pre - supported, key=describe):
                out.append((step.ident, condition))
        supported_goal = {cond for _src, cond, sink in current.links if sink == FINISH.ident}
        for condition in sorted(goal_set - supported_goal, key=describe):
            out.append((FINISH.ident, condition))
        return out

    def threatens(current: Plan) -> list[tuple[str, Condition, str, str]]:
        """(producer, condition, consumer, threatener): a step that may delete a protected link.

        A threat counts only when the threatener is not already ordered on one side of the link:
        if it must precede the producer, or follow the consumer, it cannot interfere.
        """
        out = []
        for source, condition, sink in current.links:
            for step in current.steps:
                if step.operator is None or step.ident in (source, sink):
                    continue
                if condition not in step.operator.delete:
                    continue
                if before(current, step.ident, source) or before(current, sink, step.ident):
                    continue
                out.append((source, condition, sink, step.ident))
        return out

    def before(current: Plan, a: str, b: str) -> bool:
        """Transitive closure of the ordering constraints. Small plans, so a closure per query."""
        seen = {a}
        frontier = [a]
        while frontier:
            node = frontier.pop()
            for x, y in current.order:
                if x == node and y not in seen:
                    if y == b:
                        return True
                    seen.add(y)
                    frontier.append(y)
        return False

    def consistent(current: Plan, a: str, b: str) -> bool:
        """Adding a<b must not close a cycle."""
        return a == b or not before(current, b, a)

    def recurse(current: Plan) -> Plan | None:
        stats["nodes"] += 1
        if stats["nodes"] > max_nodes:
            return None
        threats = threatens(current)
        if threats:
            source, condition, sink, threatener = threats[0]
            # PROMOTION: the threatener goes after the consumer.
            promoted = current.add_order(sink, threatener)
            if consistent(current, sink, threatener):
                stats["threats_resolved"] += 1
                found = recurse(promoted)
                if found is not None:
                    return found
            # DEMOTION: the threatener goes before the producer.
            if consistent(current, threatener, source):
                demoted = current.add_order(threatener, source)
                stats["threats_resolved"] += 1
                return recurse(demoted)
            return None

        pending = open_conditions(current)
        if not pending:
            return current
        if len(current.steps) - 2 >= max_steps:
            return None
        step_id, condition = pending[0]
        stats["last_open_condition"] = describe(condition)

        # AXIOM: the initial state already establishes it. No action, no cost, no ordering choice.
        if condition in initial_set:
            linked = current.add_link(START.ident, condition, step_id)
            if consistent(current, START.ident, step_id):
                found = recurse(linked.add_order(START.ident, step_id))
                if found is not None:
                    return found

        # REUSE: an existing step may already establish this condition. Omitting this branch was a
        # measured defect -- the planner minted a fresh instance per open condition, so a two-clause
        # goal that one atom achieves was "solved" by seven copies of that atom, which then failed
        # on execution (JOURNAL: plan JN_A1 x7 where the forward search needs JN_A1 x2). Reuse is
        # the step-linking half of partial-order planning, not an optimisation.
        for existing in current.steps:
            if existing.operator is None or existing.ident == step_id:
                continue
            if condition not in existing.operator.add:
                continue
            if not consistent(current, existing.ident, step_id):
                continue
            reused = current.add_link(existing.ident, condition, step_id)
            found = recurse(reused.add_order(existing.ident, step_id))
            if found is not None:
                return found

        for operator in operators:
            stats["relevant_checks"] += 1
            if not operator.relevant(condition):
                continue
            # MULTIPLE INSTANCES of the same operator ARE allowed, and forbidding them was a
            # measured defect: the first version returned OPEN for `['JN_A1', 'JN_A1']`, which the
            # forward search finds, because appending once and appending again are two instances
            # of one atom in two different contexts. What must not repeat is a cycle in the
            # ordering, and `consistent()` is what refuses that.
            instances = sum(1 for step in current.steps
                            if step.operator is not None
                            and step.operator.ident == operator.ident)
            step = Step(f"{operator.ident}~{instances}", operator)
            grown = current.add_step(step).add_link(step.ident, condition, step_id)
            if not consistent(current, step.ident, step_id):
                continue
            found = recurse(grown.add_order(step.ident, step_id))
            if found is not None:
                return found
        return None

    found = recurse(root)
    if found is None:
        return {"status": "OPEN__NO_PARTIAL_ORDER_FOUND",
                "reason": _why(goal_set, initial_set, operators),
                "stats": {k: v for k, v in stats.items()}}
    order = _topological(found)
    if order is None:
        return {"status": "REFUSED__ORDERING_CYCLE", "stats": stats}
    return {
        "status": "PASS__PARTIAL_ORDER_FOUND",
        "steps": [s.operator.command() for s in order
                  if s.operator is not None],
        "partial_order": sorted(found.order),
        "causal_links": [[src, describe(cond), sink] for src, cond, sink in found.links],
        "stats": stats,
    }


def _why(goal: frozenset, initial: frozenset, operators: Sequence[Operator]) -> dict[str, Any]:
    """A refusal that names its cause, because "no plan" is not a measurement."""
    unsupported = [c for c in goal if c not in initial and not any(o.relevant(c) for o in operators)]
    if unsupported:
        return {"class": "NO_RELEVANT_OPERATOR",
                "conditions": [describe(c) for c in sorted(unsupported)],
                "meaning": "no atom measured on this machine can establish these, so the goal is "
                           "not reachable with this action set at any depth"}
    return {"class": "INTERACTION_NOT_RESOLVABLE_WITHIN_THE_STEP_BOUND",
            "meaning": "every goal condition has a relevant operator, but no ordering of them "
                       "resolves the threats; the step bound or the operator set is the limit"}


def _topological(current: Plan) -> list[Step] | None:
    """One total order consistent with the partial order. A CHOICE, named as one: the partial
    order is what was proved, and any linearisation of it is admissible."""
    ids = [s.ident for s in current.steps]
    remaining = set(ids)
    out: list[Step] = []
    by_id = {s.ident: s for s in current.steps}
    while remaining:
        ready = sorted(node for node in remaining
                       if not any(after == node and before in remaining
                                  for before, after in current.order))
        if not ready:
            return None
        choice = ready[0]
        out.append(by_id[choice])
        remaining.discard(choice)
    return out


# ---------------------------------------------------------------------------------------------
# the operator set, measured -- never written
# ---------------------------------------------------------------------------------------------

TEST_FORMS = ("equals", "count_is")


def induce_conditional_operators(
        transitions: Sequence[tuple[str, Sequence[tuple[str, str]], Sequence[tuple[str, str]]]],
        conditions: Sequence[Condition], *, max_depth: int = 5,
        min_support: int = 1) -> tuple[list["Operator"], dict[str, Any]]:
    """Induce operators WITH GUARDS by splitting on the condition vocabulary until every leaf has
    exactly one observed effect.

    WHY THIS REPLACES THE CHANGE-SET GROUPING
    -----------------------------------------
    Grouping observations by their exact change set gives a "contextual operator" per distinct
    effect, and it was measured to fail in both directions. With a weak precondition rule
    ("true in every member, false somewhere outside") the guards were too loose: JOURNAL produced
    an append operator whose precondition was `CARD[IDENT=3] equals 1` and whose effect was
    `CARD[IDENT=3] equals 1` -- a self-enabling operator, which a backward search cannot use but a
    forward search never notices. With a perfect-separation rule the guards were too tight: on a
    chain of appends, "count is 4" holds in one context and no condition separated the contexts at
    all, so 33 of 46 operators were refused and the planner solved nothing.

    Both failures are the same mistake: the guard was required to be a SINGLE condition. What is
    needed is a conjunction, discovered by splitting -- and that is what this does. Each leaf of the
    split is a guard; its samples all share one effect, so its add/delete sets are exact on every
    state the guard was observed in. A leaf is only citable if it is PURE and its guard is
    non-empty; an impure leaf means this vocabulary cannot express the effect's precondition, and
    that is reported rather than smoothed over.

    This is the narrow, checkable version of "differential state tomography": the effect is a
    function of the state, and the split is what recovers the function from paired readings.
    """
    # THE LABEL IS THE EFFECT STRUCTURE, not the set of conditions that changed.
    #
    # `frozenset(changed)` conflates "made true" with "made false": appending to reach count 2
    # changes {count_is_1, count_is_2} and appending to reach count 3 changes {count_is_2,
    # count_is_3} -- and with count_is_2 in both, the two contexts can look identical under
    # insufficient vocabulary. Writing the label as (added, deleted) makes the difference between
    # them structural rather than incidental, and it is what makes a pure leaf mean what it says.
    by_atom: dict[str, list[tuple[Sequence[tuple[str, str]], tuple[frozenset, frozenset]]]] = {}
    for ident, before, after in transitions:
        added = frozenset(c for c in conditions if holds(c, after) and not holds(c, before))
        deleted = frozenset(c for c in conditions if holds(c, before) and not holds(c, after))
        by_atom.setdefault(ident, []).append((before, (added, deleted)))

    operators: list[Operator] = []
    report = {"leaves": 0, "impure_leaves": 0, "leaves_without_a_guard": 0}

    def impurity(samples) -> int:
        """How much mixedness this sample set carries: one unit per extra distinct effect.

        A pure set is 0. Summing this over the two children of a split and comparing with the parent
        is the only comparison that makes sense: a PERFECT binary split of a set with two effects
        gives 0+0=0 against a parent's 1, while comparing distinct-label COUNTS would give 1+1=2
        against a parent's 2 and call the perfect split a non-improvement -- which is exactly the
        bug that made this induction refuse every separable table.
        """
        return len({label for _b, label in samples}) - 1 if samples else 0

    def split(samples, guard, depth, others):
        labels = {label for _b, label in samples}
        if len(labels) == 1 and samples:
            report["leaves"] += 1
            added, deleted = next(iter(labels))
            add, delete = set(added), set(deleted)
            if not guard:
                # A PURE LEAF STILL NEEDS A GUARD, and the guard may come from the sibling
                # contexts rather than from the split path. The second append context in a chain is
                # pure but was reached by the *negative* branch of the first split, so its path is
                # empty -- yet "count is 2" holds in all of its samples and fails in the sibling,
                # which names it exactly. Without this step half of every chain is discarded.
                for condition in conditions:
                    if not all(holds(condition, b) for b, _l in samples):
                        continue
                    if any(not holds(condition, b) for b, _l in others):
                        guard = [condition]
                        break
            if not guard:
                report["leaves_without_a_guard"] += 1
                return
            operators.append(Operator(f"{atom}@{len(operators)}", frozenset(guard),
                                      frozenset(add), frozenset(delete), atom=atom))
            return
        if depth >= max_depth:
            report["impure_leaves"] += 1
            return
        # MAXIMISE PURITY, not minimise it. A first version minimised
        # `distinct_labels_yes + distinct_labels_no`, which is the impurity of the split -- so it
        # preferred a condition that separated NOTHING, one child came back with an empty sample
        # set, and the empty leaf was reported as "a pure leaf with no guard". The score must be
        # the purity of the two children, and a split that leaves either side with no samples is
        # not a split at all.
        best = None
        for condition in conditions:
            if condition in guard:
                continue
            yes = [(b, l) for b, l in samples if holds(condition, b)]
            no = [(b, l) for b, l in samples if not holds(condition, b)]
            if len(yes) < min_support or len(no) < min_support:
                continue
            purity = impurity(yes) + impurity(no)
            if best is None or purity > best[0]:
                best = (purity, condition, yes, no)
        if best is None or best[0] >= impurity(samples):
            report["impure_leaves"] += 1
            return
        _score, condition, yes, no = best
        split(yes, guard + [condition], depth + 1, no)
        split(no, guard, depth + 1, yes)

    for atom in sorted(by_atom):
        if by_atom[atom]:
            split(by_atom[atom], [], 0, [])
    return operators, report


def close_preconditions(operators: Sequence["Operator"],
                        initial: frozenset) -> tuple[list["Operator"], dict[str, Any]]:
    """Drop preconditions that nothing can establish and the initial state does not already give.

    A measured precondition is only usable if the plan could ever satisfy it. A condition that no
    operator adds, and that is false at reset, makes its operator PERMANENTLY INAPPLICABLE -- the
    planner then reports "no plan" for a problem that has one, which is exactly what the first run
    of this instrument did (JOURNAL: 9 search nodes, OPEN, while breadth-first found
    `['JN_A1','JN_A1']` in 3 steps).

    The cause is measurement, not planning: preconditions are computed as "true in every member of
    the group, false somewhere outside it", and with five relations and three bindings that admits
    conditions which are consequences of the state rather than causes anything establishes. Dropping
    them is the closure step STRIPS assumes and the measured table does not supply. Every dropped
    condition is COUNTED and reported, because a large drop is a statement about the vocabulary.
    """
    addable = set()
    for operator in operators:
        addable |= operator.add
    kept, dropped = [], 0
    for operator in operators:
        survivable = frozenset(c for c in operator.pre
                               if c in addable or c in initial)
        dropped += len(operator.pre) - len(survivable)
        # CITABILITY IS DECIDED HERE, AFTER the drop, not before it. Dropping a precondition can
        # leave an ambiguous-context operator with an EMPTY precondition, which reads as
        # "always applies" -- and that is precisely the fiction that made an earlier version of
        # this file produce a plan that execution refuted. An operator whose context was not
        # identified and which no longer has a measurable precondition may not be cited.
        citable = bool(survivable) or operator.context_identified
        kept.append(dataclasses.replace(operator, pre=survivable,
                                        context_identified=citable))
    incitable = sum(1 for operator in kept if not operator.context_identified)
    return kept, {"preconditions_dropped_as_unestablishable": dropped,
                  "operators_refused_as_context_unidentified": incitable}


def condition_pool(readings: Sequence[Sequence[tuple[str, str]]],
                   relations: Sequence[str] = ("CARD", "MULTISET", "ORDER", "IDENT", "PAIRING"),
                   bindings: Sequence[str] = ("WHOLE", "CONTENT", "IDENT"),
                   min_classes: int = 2) -> list[Condition]:
    """Every frame-test whose value differs across these readings.

    Two defects this replaces, both measured by running it:

    1. The first version admitted a test only when `0 < hits < len(readings)` -- true somewhere and
       false somewhere. But a test like "CARD equals 3" is FALSE in most readings and TRUE in one,
       and every test built from one observed value is false in most readings, so the filter was
       nearly vacuous and admitted hundreds of near-duplicate tests. What a test needs is a
       MINIMUM NUMBER OF DISTINCT VALUES across the readings: a test with one value carries no
       bits. That is what `min_classes` asks, and it is the same rule the vocabulary round used.

    2. It re-observed every frame on every reading for every candidate, which is quadratic in the
       data. Values are computed ONCE per (reading, frame), then inverted into tests. On LIST this
       took the sweep from minutes to seconds and did not change a single admitted test.
    """
    from canonical.swe_kernel import canonical_frame_v1 as cf

    observed: dict[tuple[str, str, str | None], list[Any]] = {}
    for state in readings:
        for relation in relations:
            for binding in bindings:
                for slot in _slots_of(state, binding):
                    key = (relation, binding, slot)
                    if key in observed and len(observed[key]) == len(readings):
                        continue
                    try:
                        value = cf.observe((relation, binding), state, slot)
                    except cf.FrameError:
                        continue
                    observed.setdefault(key, []).append(_freeze(value))

    out: list[Condition] = []
    for (relation, binding, slot), values in observed.items():
        if len({repr(value) for value in values}) < min_classes:
            continue
        for value in dict.fromkeys(values):
            out.append((relation, binding, slot, "equals", value))
            if relation == "CARD":
                out.append((relation, binding, slot, "count_is", value))
    return out


def _count_hits(condition: Condition, readings: Sequence[Sequence[tuple[str, str]]]) -> int:
    return sum(1 for state in readings if holds(condition, state))


def _slots_of(state: Sequence[tuple[str, str]], binding: str) -> list[str | None]:
    from canonical.swe_kernel import canonical_frame_v1 as cf

    if binding == "WHOLE":
        return [None]
    if binding == "CONTENT":
        return list(cf.literals(state, "CONTENT"))
    return list(cf.literals(state, "IDENT"))


def holds(condition: Condition, state: Sequence[tuple[str, str]]) -> bool:
    """The machine's own reading decides. No condition is trusted against anything else."""
    from canonical.swe_kernel import canonical_frame_v1 as cf

    relation, binding, slot, test, value = condition
    try:
        actual = cf.observe((relation, binding), state, slot)
    except cf.FrameError:
        return False
    if test == "equals":
        return actual == value
    if test == "count_is":
        return actual == value
    raise PlannerError("UNKNOWN_TEST:" + str(test))


def _freeze(value: Any) -> Any:
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(v) for v in value)
    return value


def measure_operators(observations: Sequence[tuple[str, Sequence[tuple[str, str]],
                                                   Sequence[tuple[str, str]]]],
                      conditions: Sequence[Condition]) -> list[Operator]:
    """Turn (atom, before, after) triples into operators with MEASURED pre/add/del.

    THE DEFECT THIS REPLACES, AND WHY IT MATTERS
    --------------------------------------------
    The first version computed one table per atom: `add` was every condition that ever became
    true. For `sh -c "printf alpha >> journal"` that is fifty-six conditions, because appending to
    a three-row file and appending to a five-row file are the same atom with different effects.
    That is not an operator, it is a transcript, and a planner built on it plans against a fiction.

    The faithful object is a **contextual operator**: the atom's effect is a function of the state,
    so the table is a map from context to effect. Observations of one atom are therefore grouped by
    the EXACT set of conditions that changed, and each group becomes one operator whose

        add     every condition true after and false before, in every member of the group
        del     every condition false after and true before, in every member of the group
        pre     every condition true before in every member of the group AND false before in at
                least one observation OUTSIDE the group

    `pre` is what makes the group citable: it is the cheapest measured description of "the states
    where this effect is the one you get". A condition that varies inside a group would make the
    group two groups, so the grouping is exactly the finest split the observed effects support.

    An atom whose groups are not separable by any measured condition (pre empty, more than one
    group) is reported as CONTEXT_UNIDENTIFIED and its operators are kept but marked, because a
    planner that treats them as unconditional is planning on a coincidence.
    """
    by_atom: dict[str, list[tuple[Sequence[tuple[str, str]], Sequence[tuple[str, str]]]]] = {}
    for ident, before, after in observations:
        by_atom.setdefault(ident, []).append((before, after))

    operators: list[Operator] = []
    for ident in sorted(by_atom):
        pairs = by_atom[ident]
        groups: dict[frozenset, list[tuple[Sequence, Sequence]]] = {}
        for before, after in pairs:
            changed = frozenset(c for c in conditions
                                if holds(c, before) != holds(c, after))
            groups.setdefault(changed, []).append((before, after))
        unidentified = len(groups) > 1
        for changed, members in sorted(groups.items(), key=lambda kv: sorted(kv[0], key=describe)):
            add = {c for c in changed
                   if all(holds(c, after) and not holds(c, before) for before, after in members)}
            delete = {c for c in changed
                      if all(holds(c, before) and not holds(c, after) for before, after in members)}
            # PERFECT SEPARATION, not "false somewhere outside".
            #
            # The weaker rule ("true in every member, false in at least one observer outside")
            # admits conditions that do not actually tell this context from that one. On JOURNAL
            # that produced an operator whose precondition was its own effect -- `append` requires
            # `CARD[IDENT=3] equals 1` in order to add `CARD[IDENT=3] equals 1` -- which is a
            # self-enabling operator, and a backward search cannot start from it. The forward
            # search does not care, which is exactly why the defect was invisible until the two
            # were raced.
            #
            # A condition may be a precondition only if it holds in EVERY member of this context
            # and in NO member of any other context of the same atom. Then it names this context.
            outside = [(b, a) for b, a in pairs if (b, a) not in members]
            pre = set()
            for condition in conditions:
                if condition in changed:
                    continue
                if not all(holds(condition, before) for before, _a in members):
                    continue
                if any(holds(condition, before) for before, _a in outside):
                    continue
                pre.add(condition)
            # CITABILITY. When one atom produced more than one change set, an operator with no
            # measurable precondition is not a description of a context -- it is an effect that was
            # seen once and cannot be told apart from the others. Treating it as unconditional is
            # how the planner "proved" a plan that execution refuted (JOURNAL: it chained a
            # 3-row append after a 4-row append because the 3-row operator's precondition was
            # empty and its effect was asserted unconditionally). Such operators stay in the table
            # for the record and are REFUSED by the search.
            operators.append(Operator(f"{ident}#{len(operators)}" if unidentified else ident,
                                      frozenset(pre), frozenset(add), frozenset(delete),
                                      atom=ident,
                                      context_identified=not unidentified))
    return operators


def replay_on_observed_transitions(commands: Sequence[str], start,
                                   transitions) -> dict[str, Any]:
    """Walk the plan through the OBSERVED transition graph, one concrete state at a time.

    `certify()` asks whether each state on the plan was ever seen. That is weaker than it sounds,
    and one plan in the sweep passed it and still failed: a state can be observed once, in a context
    where the atom that follows does something different from what the induced guard predicted. The
    guard is a conjunction of conditions, and two different states can satisfy the same conjunction.

    So the honest check is per STEP, not per state: from the concrete state the plan is actually in,
    was this exact (atom, state) -> next transition observed? If yes, the step is not a prediction,
    it is a record. If no, the plan has left the measured region and everything after that point is
    inference.
    """
    index = {}
    for ident, before, after in transitions:
        index.setdefault((ident, tuple(before)), []).append(tuple(after))
    state = tuple(start)
    unknown_from = None
    for position, command in enumerate(commands):
        key = (command, state)
        if key not in index:
            unknown_from = position
            break
        state = index[key][0]
    return {"every_step_was_observed": unknown_from is None,
            "first_unobserved_step": unknown_from,
            "steps": len(commands)}


def execute(plan_steps: Sequence[str], reset: Any, act: Any, read: Any) -> dict[str, Any]:
    """Run the linearisation and judge it with the machine's own reader. Returns the trace."""
    reset()
    trace = []
    for ident in plan_steps:
        act(ident)
        trace.append({"atom": ident, "reading": [list(row) for row in read()]})
    return {"executed": list(plan_steps), "trace": trace}
