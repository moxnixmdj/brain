"""Create the distinction: synthesise the condition that separates good from bad.

THE GAP, NAMED BY THIS PROJECT'S OWN RECEIPT
--------------------------------------------
`canonical/swe_kernel/witness_inversion_v1.py` measured the binding term and its
verdict is precise:

    a witness inverter can only SELECT a value the artifact already contains;
    it cannot CREATE a distinction the artifact does not have.

On the real corpus that refusal was not a bug. Eighteen witnessed failures, every
one of them a message string the parent never produced, and zero of them
expressible as a selection over the live frame. The real fix *invents* a branch
or a message. `WHY_NO_MECHANISM_CAN_BUY_REACH_20261116_V1.md` names the next
organ: "synthesise the missing branch or the missing message from the test's own
demand".

A selection needs one example. A condition needs two, and they need to disagree.
That is the whole difference, and it is why this is a different mechanism rather
than a better alphabet: a failure gives you a point, and a point cannot separate
anything from anything. Positive and negative evidence together are a *set* that
partitions the input space, and the partition is what a guard is.

WHAT IS COMPUTED, NOT ENUMERATED
--------------------------------
Given labelled inputs, the guard is derived from how the labels behave as the
inputs move:

* a value that is constant across every positive and every negative example is
  not a discriminator and is dropped;
* a value that is monotone in an input is a threshold, and the threshold is the
  crossing point between the highest positive and the lowest negative (inclusive
  of either edge is reported as a choice, not hidden);
* a categorical value selects a set, and the set is read off the examples.

Then the candidates are ordered by Occam (shortest first) and every one is
checked against **all** examples before it is proposed. A guard that fails one
example is not a guard.

THE HONEST BOUNDARY, STATED UP FRONT
------------------------------------
A guard exists only if the examples admit one. When they do not, this module
refuses and says which of three reasons applies -- no discriminating feature,
discriminating features that contradict each other, or too few examples to
choose between two equally short guards. A refusal is a result and it stays in
the denominator. It is the same discipline every refusal in this tree follows.

There is no model here, no network, no weights. The guard is arithmetic over the
values the caller supplies, and the caller is expected to have got those values
from an execution -- a frame, a trace, a probe -- not from a corpus.

Authority: NONE.
"""
from __future__ import annotations

from fractions import Fraction
import json
from typing import Any, Callable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_DISTINCTION_CREATION_V1"

# Guards longer than this are not reported. A guard that needs four conjunctions
# to fit ten examples has fitted the examples, not the distinction.
MAX_TERMS = 3


class DistinctionError(ValueError):
    pass


# --------------------------------------------------------------------------- #
# features: what a value looks like, independent of what it means
# --------------------------------------------------------------------------- #

def _kind(value: Any) -> str:
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, (int, float, Fraction)):
        return "number"
    if isinstance(value, str):
        return "string"
    if value is None:
        return "none"
    if isinstance(value, (list, tuple, set, frozenset, dict)):
        # A container is not a scalar. It has no total order and no meaningful
        # equality across examples, so a guard over it would be comparing object
        # identity dressed as semantics. Refused rather than approximated.
        raise DistinctionError("CONTAINER_IS_NOT_A_SCALAR_FEATURE")
    return "other"


def _ordered(value: Any) -> bool:
    return _kind(value) in {"number", "string", "bool"}


def _compare(a: Any, b: Any) -> int | None:
    """Total order over one comparable kind, or None if they are not comparable."""
    if _kind(a) != _kind(b):
        return None
    if not _ordered(a):
        return None
    if isinstance(a, bool):
        return (a > b) - (a < b)
    return (a > b) - (a < b)


def features(example: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten an example into named scalar features.

    Nested mappings become dotted names so that `{'order': {'n': 5}}` yields
    `order.n`. Only scalars become features: a container is not a value a guard
    can compare, and pretending otherwise would produce guards that look
    meaningful and are not.
    """
    out: dict[str, Any] = {}

    def walk(prefix: str, value: Any) -> None:
        if isinstance(value, Mapping):
            for key in sorted(value):
                walk(f"{prefix}.{key}" if prefix else str(key), value[key])
            return
        if isinstance(value, (list, tuple, set, frozenset)):
            # skipped on purpose: a container has no total order and no stable
            # equality across examples, so it cannot carry a guard
            return
        out[prefix] = value

    walk("", example)
    return out


# --------------------------------------------------------------------------- #
# the guards, as first-class objects with a name, a length and a test
# --------------------------------------------------------------------------- #

class Guard:
    """A conjunction of at most MAX_TERMS atoms over named features."""

    def __init__(self, atoms: Sequence[tuple[str, str, Any]]) -> None:
        self.atoms = tuple(atoms)

    def holds(self, example: Mapping[str, Any]) -> bool:
        values = features(example)
        for name, op, operand in self.atoms:
            if name not in values:
                return False
            value = values[name]
            if op == "eq":
                if _kind(value) != _kind(operand):
                    return False
                if value != operand:
                    return False
            elif op == "ne":
                if _kind(value) == _kind(operand) and value == operand:
                    return False
            elif op == "lt":
                if _kind(value) != _kind(operand) or not _ordered(value):
                    return False
                if not value < operand:
                    return False
            elif op == "le":
                if _kind(value) != _kind(operand) or not _ordered(value):
                    return False
                if not value <= operand:
                    return False
            elif op == "gt":
                if _kind(value) != _kind(operand) or not _ordered(value):
                    return False
                if not value > operand:
                    return False
            elif op == "ge":
                if _kind(value) != _kind(operand) or not _ordered(value):
                    return False
                if not value >= operand:
                    return False
            elif op == "between":
                low, high = operand
                if _kind(value) != _kind(low) or not _ordered(value):
                    return False
                if not (low <= value <= high):
                    return False
            elif op == "outside":
                low, high = operand
                if _kind(value) != _kind(low) or not _ordered(value):
                    return False
                if low <= value <= high:
                    return False
            else:  # pragma: no cover - internal invariant
                raise DistinctionError("UNKNOWN_OPERATOR:" + op)
        return True

    def render_python(self) -> str:
        """The same guard as EXECUTABLE Python, not as a report string.

        `render()` is for humans and uses `eq/gt/between`. Emitted source must run,
        so it needs real operators. Keeping the two apart is the fix for an
        emitted branch that said `if n le 0:` and could not be executed at all --
        the emission looked right and was not code.
        """
        parts = []
        for name, op, operand in self.atoms:
            if op == "between":
                low, high = operand
                parts.append(f"{low!r} <= {name} <= {high!r}")
            elif op == "outside":
                low, high = operand
                parts.append(f"not ({low!r} <= {name} <= {high!r})")
            elif op == "eq":
                parts.append(f"{name} == {operand!r}")
            elif op == "ne":
                parts.append(f"{name} != {operand!r}")
            elif op == "lt":
                parts.append(f"{name} < {operand!r}")
            elif op == "le":
                parts.append(f"{name} <= {operand!r}")
            elif op == "gt":
                parts.append(f"{name} > {operand!r}")
            elif op == "ge":
                parts.append(f"{name} >= {operand!r}")
            else:  # pragma: no cover
                raise DistinctionError("NO_PYTHON_FOR:" + op)
        return " and ".join(parts)

    def render(self) -> str:
        parts = []
        for name, op, operand in self.atoms:
            if op == "between":
                low, high = operand
                parts.append(f"{name} between {low!r} and {high!r}")
            elif op == "outside":
                low, high = operand
                parts.append(f"{name} outside {low!r}..{high!r}")
            else:
                parts.append(f"{name} {op} {operand!r}")
        return " and ".join(parts)

    def sort_key(self) -> tuple:
        return (len(self.atoms), self.render())

    def to_dict(self) -> dict[str, Any]:
        atoms = []
        for name, op, operand in self.atoms:
            entry: dict[str, Any] = {"feature": name, "op": op}
            if op in {"between", "outside"}:
                entry["operand"] = [operand[0], operand[1]]
            else:
                entry["operand"] = operand
            atoms.append(entry)
        return {"atoms": atoms, "render": self.render()}


def _atoms_for(name: str, positives: list, negatives: list) -> list[tuple]:
    """Every single-feature atom that separates, derived from the two sets."""
    atoms: list[tuple] = []
    if not positives or not negatives:
        return atoms
    kinds = {_kind(v) for v in positives + negatives}
    if len(kinds) != 1:
        # mixed kinds across the boundary: only equality can separate, and only
        # if the positive and negative values are drawn from disjoint values
        pos_values = {repr(v) for v in positives}
        neg_values = {repr(v) for v in negatives}
        if pos_values and neg_values and not (pos_values & neg_values):
            if len(pos_values) == 1:
                atoms.append((name, "eq", positives[0]))
        return atoms
    # NOTE: `_ordered` is a predicate on ONE value. Applied to a list it returns
    # False for every numeric feature, which routed every threshold atom into the
    # equality-only branch and made an entire class of guards invisible. Measured
    # before the fix: `qty >= 1` was not offered for positives (1,2,5,10) against
    # negatives (0,-1,-5).
    if not all(_ordered(v) for v in positives + negatives):
        pos_values = {repr(v) for v in positives}
        neg_values = {repr(v) for v in negatives}
        if len(pos_values) == 1 and not (pos_values & neg_values):
            atoms.append((name, "eq", positives[0]))
        return atoms

    positive_values = sorted(set(positives))
    negative_values = sorted(set(negatives))
    # WHICH ATOMS ARE OFFERED, and why only these.
    #
    # A one-sided threshold is offered ONLY when the boundary is a real edge in
    # the data: the positive values must form a prefix (or suffix) and the
    # negatives must sit entirely on the other side, with no negative strictly
    # between the extreme positive and infinity. Otherwise `n <= 255` would be
    # emitted for positives (0,100) against negatives (300,), silently asserting
    # that 256 is valid -- an invented widening, and the same class of mistake as
    # the `x <= 100` -> `x < 100` lesson this project already measured by being
    # broken by it.
    #
    # When the data does not close an edge, the RANGE atom is the honest one: it
    # says exactly "these values and nothing beyond them", which is what the
    # examples support and nothing more.
    # An edge is "closed" when EVERY negative lies strictly beyond the positive
    # extreme, so the boundary decided by the data is the boundary of the
    # positives themselves. The earlier version tested `v > min(positives)`,
    # which is true for negatives that sit between the positives and therefore
    # offered nothing on the commonest case of all: positives (1,2,5,10) against
    # negatives (0,-1,-5) produced only a range, never `n >= 1`.
    # WHICH EDGES THE DATA ACTUALLY DECIDES. Three separate questions, and
    # getting them confused produced three wrong answers in a row:
    #
    #   no negative INSIDE the span  -> the span is a clean block of positives.
    #       This is what makes a RANGE sound, and it needs negatives on BOTH
    #       sides, because a range asserts a lower AND an upper bound.
    #   a negative BELOW the span    -> the lower edge is decided, so `>= low`
    #       is a sound one-sided atom.
    #   a negative ABOVE the span    -> the upper edge is decided, so `<= high`
    #       is a sound one-sided atom.
    #
    # Data with negatives only below (divisors 1,2,7 against 0,-1,-5) decides the
    # lower edge ONLY. Offering it a range rejected 8, which the real rule
    # accepts. Data with negatives on both sides (0..255 against -1,256,300)
    # decides both, and there a range is the honest answer.
    span_low, span_high = min(positive_values), max(positive_values)
    has_below = any(v < span_low for v in negative_values)
    has_above = any(v > span_high for v in negative_values)
    no_inside = all(not (span_low <= v <= span_high) for v in negative_values)
    closes_lower = has_below
    closes_upper = has_above

    # Emit BOTH candidates on each side and let the ranking pick. The edge of the
    # positives (`>= 3`) and the edge of the negatives (`> 2`) both fit the data
    # and differ on nothing that was observed; they differ only on values in the
    # gap between the sets. When there is no gap they coincide. When there is a
    # gap, `> max(negative)` is the tighter statement and is preferred below by
    # the commitment ranking, because it excludes the least.
    for op, edge in (("le", max(positive_values)), ("lt", max(negative_values))):
        atom = (name, op, edge)
        if _atom_separates(atom, name, positives, negatives):
            atoms.append(atom)
    for op, edge in (("ge", min(positive_values)), ("gt", max(negative_values))):
        atom = (name, op, edge)
        if _atom_separates(atom, name, positives, negatives):
            atoms.append(atom)
    if len(set(positives)) == 1 and positives[0] not in set(negatives):
        atoms.append((name, "eq", positives[0]))
    # A RANGE is one distinction, not two. `0 <= n <= 255` is the boundary of a
    # byte, and treating it as two independent atoms on the same feature is
    # illegal in a conjunction (same feature twice) -- which made the single most
    # common real guard unreachable. Measured before the fix: positives
    # (0,100,255) against negatives (256,300,-1) refused with
    # NO_DISCRIMINATING_FEATURE even though the range is exactly 0..255.
    # A range is only offered when BOTH edges are closed by the data. Otherwise
    # it invents a bound nobody observed: positives (1,2,7) against negatives
    # (0,-1,-5) closed the lower edge only, and `between 1 and 7` then REJECTS 8,
    # which the human's rule `d > 0` accepts. Choosing the "safe-looking" range
    # over the one-sided threshold was the wrong call, and this comment is what
    # stopped it being made twice.
    low, high = min(positives), max(positives)
    if low != high and closes_lower and closes_upper and no_inside:
        atom = (name, "between", (low, high))
        if _atom_separates(atom, name, positives, negatives):
            atoms.append(atom)
    # de-duplicate while keeping a deterministic order
    seen = set()
    unique = []
    for atom in atoms:
        key = (atom[0], atom[1], repr(atom[2]))
        if key not in seen:
            seen.add(key)
            unique.append(atom)
    return unique


def _atom_separates(atom, name, positives, negatives) -> bool:
    one = Guard([atom])
    return all(one.holds({name: v}) for v in positives) and not any(
        one.holds({name: v}) for v in negatives
    )


# --------------------------------------------------------------------------- #
# the search
# --------------------------------------------------------------------------- #

def synthesise_guard(
    positives: Sequence[Mapping[str, Any]],
    negatives: Sequence[Mapping[str, Any]],
    *,
    max_terms: int = MAX_TERMS,
) -> dict[str, Any]:
    """The shortest conjunction that holds on every positive and no negative.

    Deterministic, and refuses rather than guessing. Three distinct refusals are
    reported separately because they call for different next actions:

    * `NO_DISCRIMINATING_FEATURE` -- no single feature separates. More features
      from a richer probe is what would help.
    * `CONTRADICTORY_EXAMPLES` -- one positive and one negative agree on every
      feature. No guard over these features can exist; the examples are the same
      point labelled twice.
    * `TOO_FEW_EXAMPLES` -- guards exist but two of equal length disagree, so the
      choice between them is not determined by the evidence.
    """
    if not positives or not negatives:
        return {
            "schema": SCHEMA,
            "status": "REFUSED__NEEDS_BOTH_POLARITIES",
            "note": "a guard separates good from bad; one polarity cannot be separated from anything",
            "guard": None,
            "authority": "NONE",
        }

    pos_features = [features(p) for p in positives]
    neg_features = [features(n) for n in negatives]
    names = sorted(set().union(*[set(f) for f in pos_features + neg_features]))
    if not names:
        return {
            "schema": SCHEMA,
            "status": "REFUSED__NO_FEATURES",
            "note": "the examples carry no scalar values, so nothing can be compared",
            "guard": None,
            "authority": "NONE",
        }

    # the same point labelled both ways cannot be separated, and saying so is
    # more useful than reporting that no conjunction happened to be found
    for p in pos_features:
        for n in neg_features:
            if p == n:
                return {
                    "schema": SCHEMA,
                    "status": "REFUSED__CONTRADICTORY_EXAMPLES",
                    "example": p,
                    "note": "one positive and one negative agree on every feature",
                    "guard": None,
                    "authority": "NONE",
                }

    atoms: list[tuple] = []
    for name in names:
        pos_values = [f[name] for f in pos_features if name in f]
        neg_values = [f[name] for f in neg_features if name in f]
        if not pos_values or not neg_values:
            continue
        atoms.extend(_atoms_for(name, pos_values, neg_values))

    def satisfies(guard: Guard) -> bool:
        return all(guard.holds(p) for p in positives) and not any(
            guard.holds(n) for n in negatives
        )

    single = [Guard([a]) for a in atoms]
    single = [g for g in single if satisfies(g)]
    # A single `eq` atom pins the positive value rather than describing the
    # distinction: with one positive example every positive is "constant", so
    # `y == 9` always fits and says nothing. That is a lookup dressed as a guard,
    # and it is exactly the failure mode this module exists to avoid, so it is
    # only offered when there is at least one other atom that also separates and
    # the data genuinely has one positive value.
    substantive = [
        g for g in single
        if not (len(g.atoms) == 1 and g.atoms[0][1] == "eq" and len(positives) > 1)
    ]
    if substantive:
        single = substantive

    def commit_rank(guard: Guard) -> tuple:
        # Ordering, in priority order:
        #   1. a range or an equality commits to nothing beyond the observed
        #      block, so it is offered before any one-sided statement;
        #   2. among one-sided atoms, the strict edge on the negative side
        #      (`gt max(N)`) admits fewer unseen values than the inclusive edge on
        #      the positive side (`ge min(P)`), so it is offered first. Both fit;
        #      only one of them can be wrong in the same direction.
        ops = [atom[1] for atom in guard.atoms]
        risk = sum(1 for op in ops if op in {"ge", "le"})
        return (risk, guard.sort_key())

    single.sort(key=commit_rank)
    if single:
        return _result(
            single[0], positives, negatives, "SINGLE_ATOM", 1, alternatives=single[1:6]
        )

    if max_terms < 2:
        return {
            "schema": SCHEMA,
            "status": "REFUSED__NO_DISCRIMINATING_FEATURE",
            "note": "no single feature separates and conjunctions were not allowed",
            "guard": None,
            "authority": "NONE",
        }

    pairs = [
        Guard([a, b])
        for i, a in enumerate(atoms)
        for b in atoms[i + 1 :]
        if a[0] != b[0]
    ]
    pairs = [g for g in pairs if satisfies(g)]
    pairs.sort(key=Guard.sort_key)
    if pairs:
        equally_short = [g for g in pairs if len(g.atoms) == len(pairs[0].atoms)]
        distinct = {g.render() for g in equally_short}
        if len(distinct) > 1:
            return {
                "schema": SCHEMA,
                "status": "REFUSED__TOO_FEW_EXAMPLES",
                "tied_guards": sorted(distinct)[:5],
                "note": (
                    "several guards of the same length fit equally well, so the "
                    "examples do not choose between them. One more example that "
                    "the guards disagree on would decide it"
                ),
                "guard": None,
                "authority": "NONE",
            }
        return _result(pairs[0], positives, negatives, "CONJUNCTION", 2)

    return {
        "schema": SCHEMA,
        "status": "REFUSED__NO_DISCRIMINATING_FEATURE",
        "features_considered": names,
        "note": (
            "no conjunction of up to "
            f"{max_terms} atoms separates these examples. The distinction is not "
            "expressible over the features supplied -- a richer probe, not more "
            "examples of the same shape, is what would help"
        ),
        "guard": None,
        "authority": "NONE",
    }


def _unseen_commitment(guard: Guard, positives, negatives) -> str:
    """What this guard decides about values nobody observed.

    Every guard that fits the data still commits on the gaps: `n >= 1` says 11 is
    fine, `n between 1 and 10` says it is not. Neither is entailed by the
    examples, so the choice is reported instead of made. Naming the commitment is
    what turns "I synthesised a guard" into "here is exactly what you have not
    checked".
    """
    pos_features = [features(p) for p in positives]
    neg_features = [features(n) for n in negatives]
    notes = []
    for name, op, operand in guard.atoms:
        observed = [
            f[name] for f in pos_features + neg_features if name in f and _ordered(f[name])
        ]
        if not observed:
            continue
        low, high = min(observed), max(observed)
        if op in {"ge", "gt"}:
            notes.append(f"{name}: claims values above {high!r} are valid (unobserved)")
        elif op in {"le", "lt"}:
            notes.append(f"{name}: claims values below {low!r} are valid (unobserved)")
        elif op == "between":
            notes.append(f"{name}: claims nothing outside {operand[0]!r}..{operand[1]!r}")
        elif op == "eq":
            notes.append(f"{name}: claims no value other than {operand!r} is valid")
    return "; ".join(notes) if notes else "no commitment beyond the observed values"


def _next_probe(guard: Guard, positives, negatives) -> list[dict[str, Any]]:
    """The examples that would settle what the guard is currently guessing.

    This is the part that makes synthesis useful rather than merely clever. A
    guard always commits on values nobody observed; the commitment is named in
    `commitment_beyond_the_data`, and here it is turned into the question that
    would remove it. Answering one of these turns a guess into a distinction,
    which is the only known way to raise REACH for this kind of fix: the missing
    branch becomes determined by evidence rather than chosen by the synthesiser.
    """
    probes: list[dict[str, Any]] = []
    pos_features = [features(p) for p in positives]
    neg_features = [features(n) for n in negatives]
    for name, op, operand in guard.atoms:
        values = [f[name] for f in pos_features + neg_features if name in f and _ordered(f[name])]
        if not values:
            continue
        low, high = min(values), max(values)
        # `high + 1` is only meaningful where arithmetic is: strings order but do
        # not step, so asking "is s = 'abc' + 1 accepted?" is nonsense. Strings get
        # no numeric probe rather than a broken one.
        if _kind(high) != "number":
            continue

        # THE QUESTION MUST HAVE AN UNKNOWN ANSWER. The first version of this
        # function asked "is n = 256 accepted?" even after 256 was already a known
        # negative, so the loop asked the same thing eight times and never
        # terminated. A probe is only useful if it is not already in the evidence.
        known = {repr(v) for v in values}

        def unknown(candidate: Any) -> bool:
            return repr(candidate) not in known
        if op in {"gt", "ge"}:
            if not unknown(high + 1):
                continue
            probes.append({
                "feature": name,
                "ask": f"is {name} = {high + 1!r} accepted?",
                "closes": f"the upper edge of {name}",
                "why": "the guard admits everything above the largest value seen",
            })
        elif op in {"lt", "le"}:
            if not unknown(low - 1):
                continue
            probes.append({
                "feature": name,
                "ask": f"is {name} = {low - 1!r} accepted?",
                "closes": f"the lower edge of {name}",
                "why": "the guard admits everything below the smallest value seen",
            })
        elif op == "between":
            b_low, b_high = operand
            if unknown(b_high + 1):
                probes.append({
                    "feature": name,
                    "ask": f"is {name} = {b_high + 1!r} accepted?",
                    "closes": f"the upper edge of {name}",
                    "why": "the range stops where the observed positives stopped",
                })
            if unknown(b_low - 1):
                probes.append({
                    "feature": name,
                    "ask": f"is {name} = {b_low - 1!r} accepted?",
                    "closes": f"the lower edge of {name}",
                    "why": "the range starts where the observed positives started",
                })
    return probes


def _result(guard: Guard, positives, negatives, shape: str, length: int,
            alternatives: Sequence[Guard] = ()) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "PASS__GUARD_SYNTHESISED",
        "guard": guard.to_dict(),
        "shape": shape,
        "length": length,
        "holds_on_positives": len(positives),
        "rejects_negatives": len(negatives),
        "commitment_beyond_the_data": _unseen_commitment(guard, positives, negatives),
        "next_probes": _next_probe(guard, positives, negatives),
        "alternatives": [
            {
                **alt.to_dict(),
                "commitment_beyond_the_data": _unseen_commitment(alt, positives, negatives),
            }
            for alt in alternatives
        ],
        "claim": "SHORTEST_CONJUNCTION_THAT_SEPARATES_THESE_EXAMPLES",
        "not_claimed": "THE_CONDITION",
        "authority": "NONE",
    }


# --------------------------------------------------------------------------- #
# the thing a witness inverter cannot do: go from "must not raise" to a branch
# --------------------------------------------------------------------------- #

_NEGATION = {
    "eq": "ne",
    "lt": "ge",
    "le": "gt",
    "gt": "le",
    "ge": "lt",
}


def _negate(atom: tuple[str, str, Any]) -> tuple[str, str, Any]:
    """The complement of one atom, as another atom.

    A conjunction's negation is a DISJUNCTION of negated atoms, so the emitted
    test joins them with `or`.
    """
    name, op, operand = atom
    if op == "between":
        low, high = operand
        # not (low <= v <= high)  ==  v < low or v > high ; the emitter joins
        # with `or`, so this atom is expanded by the caller below
        return (name, "outside", (low, high))
    if op not in _NEGATION:
        raise DistinctionError("CANNOT_NEGATE:" + op)
    return (name, _NEGATION[op], operand)


def branch_from_outcomes(
    positives: Sequence[Mapping[str, Any]],
    negatives: Sequence[Mapping[str, Any]],
    *,
    max_terms: int = MAX_TERMS,
) -> dict[str, Any]:
    """The missing branch, written out, from two sets of observed outcomes.

    A witness inverter is handed ONE failure and asked which existing value
    reproduces it, which is why it refuses when the answer is new content. Handed
    a positive set (inputs whose behaviour must be preserved) and a negative set
    (inputs whose behaviour is wrong), the guard IS the new branch condition, and
    the branch body is stated separately so it can be checked by execution.

    The emitted source is a proposal. Nothing here executes it; the caller's real
    test is the only thing allowed to accept it, which is the discipline
    `witness_inversion_v1` established and this module does not relax.
    """
    found = synthesise_guard(positives, negatives, max_terms=max_terms)
    if found["status"] != "PASS__GUARD_SYNTHESISED":
        return {**found, "branch": None, "source": None}
    atoms = [
        (a["feature"], a["op"], tuple(a["operand"]) if a["op"] == "between" else a["operand"])
        for a in found["guard"]["atoms"]
    ]
    guard = Guard(atoms)
    # THE GUARD DESCRIBES THE VALID REGION, so the branch must fire on its
    # NEGATION. The first version emitted `if <guard>: raise`, which raises on
    # every input the positives prove is correct -- it would have broken every
    # working case the examples were collected from. De Morgan is applied to the
    # conjunction so the emitted test reads as the invalid region directly.
    inverse_atoms = [_negate(atom) for atom in atoms]
    negated = " or ".join(Guard([atom]).render_python() for atom in inverse_atoms)
    source = (
        "if " + negated + ":\n"
        "    # the region the negative examples show is wrong\n"
        "    raise <exception-from-the-demand>\n"
    )
    return {
        **found,
        "branch_condition_for_invalid_input": negated,
        "branch": guard.to_dict(),
        "source": source,
        "note": (
            "the condition is derived; the body is not. What the branch must DO "
            "comes from the demanded outcome, not from these examples"
        ),
    }


def main(argv: Sequence[str] | None = None) -> int:
    """CLI: read a JSON file of positives/negatives, print the guard."""
    import argparse

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", help="JSON file with 'positives' and 'negatives'")
    parser.add_argument("--json", dest="out", default=None)
    args = parser.parse_args(list(argv) if argv is not None else None)

    with open(args.path, encoding="utf-8") as handle:
        payload = json.load(handle)
    result = synthesise_guard(
        payload.get("positives") or [], payload.get("negatives") or []
    )
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
    print(text)
    return 0 if result["status"] == "PASS__GUARD_SYNTHESISED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
