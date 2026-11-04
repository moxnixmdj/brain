"""Whether one answer can be checked against another is DISCOVERED, not declared.

THE LAYER BELOW THE LEDGER. The ledger compared answers with two rules I typed --
`SAME_SHAPE` and `PARTS_NOT_WHOLE` -- plus a third typed list, `_TOTAL_OPS`. In the same
commit that removed a hand-typed list of operators that carry a law, I wrote three more
lists. That is the defect this project keeps naming and I keep reproducing: a creature
with two reflexes is not a creature that can extend its own vocabulary; it is a creature
with two reflexes.

THE INVERSION. Do not ask "which operators produce a total?" -- that question needs
somebody to answer it, and the somebody is me. Ask the question the operator itself can
answer:

    given this aggregate, does the whole equal some fixed combination of its parts,
    and if so which one?

That is answerable by PROBING THE OPERATOR'S OWN FUNCTION. Split a probe set every way,
apply the aggregate to the whole and to each part, and see which recombination of the
parts reproduces the whole. Nothing about it is typed per operator:

    sum    -> sum      (obviously, and derived)
    count  -> sum      (a total count is the sum of the group counts)
    max    -> max      (the largest of everything is the largest of the largest)
    min    -> min
    mean   -> NOTHING  (a mean of means is not the mean -- it needs the group sizes)

`mean -> nothing` is the payoff and the reason this is not a list of rules in disguise.
It is a DERIVED statement that a mean CANNOT be checked against its parts, so an answer
built on `mean` is reported as unverifiable-against-the-parts rather than as consistent.
The system learns which of its own answers are mutually checkable, and which ones it must
admit it cannot check.

This is the same move as `law_strength`: a check's reach is measured by running it, not
asserted by writing it down. A new operator added to `_AGGREGATES` is decomposed correctly
with no change to this file, because the decomposition is a property of the function, not
of a table in this module.
"""

from __future__ import annotations

import canonical.runtime.value_algebra_v1 as V

#: Probe sets chosen to separate the recombinators from each other: an even split, an
#: uneven split, a single element (which collapses most distinctions), and negatives.
#: `max` and `sum` agree on a single element and disagree on everything else, which is
#: exactly what the probes are for.
_PROBE_WHOLES = (
    (3.0, 1.0, 7.0, 2.0),
    (10.0, 10.0),
    (0.5, 2.5, 6.0),
    (-3.0, -1.0, -7.0),
    (5.0,),
)

_PROBE_PARTS = (
    ((3.0, 1.0), (7.0, 2.0)),
    ((10.0,), (10.0,)),
    ((0.5, 2.5), (6.0,)),
    ((-3.0, -1.0), (-7.0,)),
    ((5.0,),),
)

#: THE REMAINING TYPED SURFACE, and it is typed over MATHEMATICS rather than over this
#: system's operators -- which is the distinction that makes it acceptable.
#:
#: A whole can be recovered from its parts exactly when the recovering operation is
#: associative, because otherwise the way the parts were grouped would change the answer
#: and no fixed combination could reproduce the whole. The associative operations on
#: numbers are a small, mathematical, closed set. Everything above this line -- which
#: operator uses which one, and whether it decomposes at all -- is MEASURED by probing the
#: operator's own function. Adding an aggregate to `_AGGREGATES` needs no edit here.
#:
#: `product` was missing on the first pass, and the discovery returned None for it: the
#: system said "a product cannot be checked against its parts" when in fact it can. The
#: lesson is that this alphabet has to be complete with respect to the ASSOCIATIVE
#: OPERATIONS, not with respect to the aggregates that happen to exist today.
_RECOMBINATORS = {
    "sum": sum,
    "product": lambda xs: __import__("math").prod([float(x) for x in xs]),
    "max": max,
    "min": min,
    "first": lambda xs: xs[0],
    "last": lambda xs: xs[-1],
}

_CACHE: dict[str, str | None] = {}


def decomposes_by(kind: str) -> str | None:
    """Which combination of the parts reproduces the whole, or None if none does.

    Returns the NAME of the recombination -- `"sum"`, `"max"`, `"min"` -- or None when the
    aggregate does not decompose at all. This is measured by running the aggregate, so it
    is correct for an operator that did not exist when this file was written.
    """
    if kind in _CACHE:
        return _CACHE[kind]
    spec = V._AGGREGATES.get(kind)
    if spec is None:
        _CACHE[kind] = None
        return None
    fn = spec["fn"]
    survivors = set(_RECOMBINATORS)
    for whole, parts in zip(_PROBE_WHOLES, _PROBE_PARTS):
        try:
            w = fn(list(whole))
            ps = [fn(list(p)) for p in parts]
        except Exception:
            _CACHE[kind] = None
            return None
        if w is None or any(p is None for p in ps):
            continue
        try:
            w = float(w)
            ps = [float(p) for p in ps]
        except (TypeError, ValueError):
            _CACHE[kind] = None
            return None
        survivors = {name for name in survivors
                     if abs(float(_RECOMBINATORS[name](ps)) - w) <= 1e-9}
        if not survivors:
            _CACHE[kind] = None
            return None
    # More than one survivor means the probes could not tell them apart, which is not the
    # same as "either is valid". Prefer the narrowest, and say so by returning the name.
    result = next(iter(sorted(survivors)), None)
    _CACHE[kind] = result
    return result


def aggregate_kind(node) -> str | None:
    """The declared aggregate an expression applies, wherever the declaration is spelled.

    IT HAS TO DESCEND. `column_from(groups(...), "sum(amount)")` applies a sum, but the
    sum is declared on the CHILD `groups` node, so a walk that looks only at the top node
    returned None for the system's single most common way of reading a grouping -- and
    None means "no law to apply", so the answer went unchecked while looking checked.

    That is the third time this round that an aggregate hid one level down: `map`,
    `half`-of-`count`, and now `column_from`. The rule is that the search follows the tree,
    not that I have remembered every operator that nests.
    """
    if node is None:
        return None
    seen = set()
    stack = [node]
    while stack:
        cur = stack.pop()
        if cur is None or id(cur) in seen or not hasattr(cur, "op"):
            continue
        seen.add(id(cur))
        for arg in getattr(cur, "args", ()):
            if isinstance(arg, str) and arg in V._AGGREGATES:
                return arg
        stack.extend(a for a in getattr(cur, "args", ()) if hasattr(a, "op"))
    return None


def _leaves(node) -> frozenset:
    """The (op, literals) pairs that identify WHAT an expression reads."""
    out = set()
    stack = [node]
    while stack:
        cur = stack.pop()
        if cur is None or not hasattr(cur, "op"):
            continue
        if cur.op in ("column", "table", "cell"):
            out.add((cur.op,) + tuple(a for a in cur.args if isinstance(a, str)))
        stack.extend(a for a in getattr(cur, "args", ()) if hasattr(a, "op"))
    return frozenset(out)


def read_column(node) -> str | None:
    """The column an expression aggregates over, if there is exactly one.

    WHY NOT COMPARE LEAF SETS. Two earlier attempts both failed, in opposite directions:

      * Comparing full leaf sets reported every genuine parts/whole pair as unrelated,
        because a grouping's parts read a TABLE and the flat total reads a COLUMN. The
        check then passed everything by comparing nothing.
      * Dropping the comparison entirely made `[150, 150, 250]` (the amounts per region)
        get compared against `27` (the total of `qty`) -- two answers about different
        columns, both right, reported as a contradiction.

    The fact that actually decides it is narrower than either: a breakdown of `amount` is
    the parts of the total of `amount`, and of nothing else. So compare the COLUMN each
    expression aggregates, which survives the table/column difference and still separates
    two different columns.
    """
    if node is None:
        return None
    seen, found = set(), set()
    stack = [node]
    while stack:
        cur = stack.pop()
        if cur is None or id(cur) in seen or not hasattr(cur, "op"):
            continue
        seen.add(id(cur))
        if cur.op == "column" and len(cur.args) >= 2:
            found.add(str(cur.args[1]))
        # `group` is (table, key, value): the column being aggregated is args[2], and it
        # is a bare string, so a walk over node arguments never sees it.
        if cur.op == "group" and len(cur.args) >= 3 and isinstance(cur.args[2], str):
            found.add(str(cur.args[2]))
        stack.extend(a for a in getattr(cur, "args", ()) if hasattr(a, "op"))
    return found.pop() if len(found) == 1 else None


def check_parts_against_whole(parts_node, parts_value, whole_node, whole_value,
                              kind: str | None = None,
                              whole_restricts: bool | None = None,
                              parts_kind: str | None = None) -> dict:
    """Can `parts_value` be reconciled with `whole_value`, and if not, why not.

    Returns one of three verdicts, and the third is the one that was missing everywhere
    else in this system:

        {"verdict": "agrees"}      the parts recombine to the whole
        {"verdict": "disagrees",   ...}  they cannot both be right
        {"verdict": "uncheckable", ...}  this aggregate does not decompose, so no
                                        statement about agreement is available

    `uncheckable` is not a soft `agrees`. Reporting "I could not judge" as "fine" is the
    defect that was removed three times from the law grade; a mean of means is a real
    answer that this check must refuse to bless, and it refuses by name.
    """
    # THE PARTS AND THE WHOLE MUST APPLY THE SAME AGGREGATE.
    #
    # MEASURED ON MERGED MAIN as a contradiction reported between two CORRECT answers:
    # `[150, 150, 250]` (one sum per region) against `50` (the smallest amount). The check
    # took the aggregate from the WHOLE side -- `min` -- recombined the sums with `min`,
    # got 150, and called it a disagreement. A breakdown of sums is not a breakdown of
    # minima, whatever column they read.
    #
    # The parts' own aggregate is what has to recombine. One side cannot dictate the law
    # for both, and this is the same shape of error as every other one this round: the law
    # was applied to a pair it never described.
    if parts_kind is None and parts_node is not None:
        parts_kind = aggregate_kind(parts_node)
    kind = kind or aggregate_kind(whole_node)
    if parts_kind is not None and kind is not None and parts_kind != kind:
        return {"verdict": "uncheckable",
                "why": f"the parts apply {parts_kind!r} and the whole applies {kind!r}, "
                       f"so they are not the breakdown and total of one quantity"}
    if kind is None:
        return {"verdict": "uncheckable", "why": "the whole is not an aggregate"}
    is_slice = restricts_rows(whole_node) if whole_restricts is None else bool(whole_restricts)
    if is_slice:
        return {"verdict": "uncheckable",
                "why": "the whole covers only some of the rows, so it is a slice and "
                       "not the whole the parts decompose"}
    # WHETHER THE PARTS ARE "OF THE SAME THING" IS DECIDED BY RECONSTRUCTION, NOT BY
    # COMPARING LEAF SETS. A grouping's parts read a TABLE and the flat total reads a
    # COLUMN, so a structural comparison of what each expression touches can never match
    # -- it reported every genuine parts/whole pair as unrelated, and the check passed
    # everything by never comparing anything. That is the same "silently skipped" shape as
    # the rendered-value bug, one layer up.
    #
    # The honest test is the one the operator already gives us: recombine the parts the way
    # this aggregate requires and see whether the whole comes back. If it does not, they
    # are either about different things or one of them is wrong -- and in both cases
    # saying so is correct.
    combination = decomposes_by(kind)
    if combination is None:
        return {"verdict": "uncheckable",
                "why": f"{kind!r} does not decompose: no combination of the parts "
                       f"recovers the whole, so they cannot be compared"}
    try:
        parts = [float(v) for v in parts_value]
        whole = float(whole_value)
    except (TypeError, ValueError):
        return {"verdict": "uncheckable", "why": "the values are not numbers"}
    if not parts:
        return {"verdict": "uncheckable", "why": "there are no parts"}
    got = float(_RECOMBINATORS[combination](parts))
    if abs(got - whole) <= 1e-9:
        return {"verdict": "agrees", "by": combination}
    return {"verdict": "disagrees", "by": combination, "recombined": got,
            "why": f"the parts recombine by {combination} to {got:g}, "
                   f"and the whole was reported as {whole:g}"}


def expression_reads(node):
    """(column, restricts_rows) as plain data, so it survives without a node.

    In production no computation dict carries a node -- the ledger was dead for exactly
    that reason once already. The facts the comparison needs are extracted here, at the
    one place a node exists, and stored on the entry beside the aggregate.
    """
    return (read_column(node) is not None and _read_column_name(node),
            bool(restricts_rows(node)))


def _read_column_name(node) -> str | None:
    return read_column(node)


def restricts_rows(node) -> bool:
    """Does this expression answer about SOME of the rows rather than all of them?

    `what is the total amount in west` returns 250, and 250 is not the whole of anything.
    The parts `[150, 150, 250]` cover every region, so 550 is the whole and 250 is a
    SLICE -- comparing them reported a disagreement between two correct answers.

    A slice is not a total. The distinction is structural (does the expression filter?)
    rather than numerical, because the number alone cannot tell you: 250 looks exactly
    like a total of a smaller table.
    """
    if node is None:
        return False
    seen = set()
    stack = [node]
    while stack:
        cur = stack.pop()
        if cur is None or id(cur) in seen or not hasattr(cur, "op"):
            continue
        seen.add(id(cur))
        if cur.op in ("filter", "where", "groups", "group"):
            # `groups`/`group` partition rather than restrict, but their PARTS are the
            # breakdown, so a grouped node is handled by the parts side, not this one.
            if cur.op in ("filter", "where"):
                return True
        stack.extend(a for a in getattr(cur, "args", ()) if hasattr(a, "op"))
    return False


def is_a_whole(node, aggregate: str | None = None, reads_column: str | None = None,
               restricts: bool = False) -> bool:
    """Does this expression CLAIM to be the whole that the parts decompose?

    THE FALSE POSITIVE THAT KEEPS COMING BACK, and the reason it has to live here rather
    than in a helper beside the ledger: `[150, 150, 250]` was compared against `1.5`, the
    answer to "the total amount divided by how many regions". 1.5 is a QUOTIENT -- it
    applies a sum internally and it reads the same column, so every structural fact about
    it looks like a total, but it never claimed to be one.

    A whole that claims to be the whole applies the aggregate and NOTHING ELSE. Anything
    applied on top of it -- a half, a division, a count of it -- is a different quantity
    that was never supposed to equal the sum of the parts. This is decided by asking
    whether the aggregate is the OUTERMOST operator rather than whether one appears
    somewhere inside.
    """
    if node is None:
        if aggregate is None:
            return False
        # no node to inspect: a slice is a partial quantity, and a caller that knows the
        # expression is not a bare aggregate must say so by passing `aggregate=None`
        return not restricts
    if restricts:
        return False
    stack, seen = [node], set()
    while stack:
        cur = stack.pop()
        if cur is None or id(cur) in seen or not hasattr(cur, "op"):
            continue
        seen.add(id(cur))
        if cur.op in ("aggregate", "count"):
            return True          # the outermost thing about these values is the aggregate
        if cur.op in ("map", "compare"):
            return False         # something is applied ON TOP of the aggregate
        kids = [a for a in getattr(cur, "args", ()) if hasattr(a, "op")]
        if len(kids) > 1:
            # more than one operand means a combination, not a single aggregate
            return all(is_a_whole(k) for k in kids) and getattr(cur, "op", None) == "vector"
        stack.extend(kids)
    return False
