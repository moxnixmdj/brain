"""The system holds what it has already said, and checks new answers against it.

THE GAP. `answer()` is stateless. Ask it four things and it computes four unrelated
verdicts:

    what is the total amount               -> 550      verified
    what is the total amount in west       -> 250      verified
    what is the total amount in north      -> 150      verified
    what is the total amount in south      -> 150      verified

550 = 250 + 150 + 150. That holds -- but nothing in the system knows it, because nothing
in the system ever compares two answers. Every answer is audited against its own
expression and its own law and against NO OTHER ANSWER.

WHY THAT IS THE DEEP GAP AND NOT A MISSING FEATURE. Every check built so far is
per-expression: `holds` asks whether one expression is sound; the grouping invariant asks
whether one grouping keeps its rows; the law grade asks what one operator can exclude. All
of them can pass while the set of answers is incoherent, because coherence is a property of
a SET. A system that cannot notice its own answers contradicting is not reasoning about a
world; it is answering a sequence of independent questions about a world, which is a
different and much weaker thing.

WHAT IS CHECKED, AND WHAT IS NOT. This is deliberately small. It records what was asked,
what was answered, and the expression behind it, and it reports the pairs whose
expressions are structurally related but whose values disagree. It does not "resolve"
anything -- a contradiction is returned as a contradiction, because choosing which of two
verified answers to believe is exactly the guess this project keeps refusing to make.

THE HONEST LIMIT, stated because the last six rounds were spent learning this lesson: this
is a ledger and a consistency check, not understanding. It knows that a whole should equal
the sum of its parts. It does not know what the parts are unless the expressions tell it.
"""

from __future__ import annotations

import canonical.runtime.value_algebra_v1 as V

#: One record per answered question. In-process only, and cleared explicitly -- the same
#: rule as the evaluation memo: a fact from an earlier question is not a fact about this one
#: unless it is re-derivable from the tree.
_LEDGER: list[dict] = []


def reset() -> None:
    """Forget everything. Same discipline as the evaluation memo."""
    _LEDGER.clear()


def entries() -> list[dict]:
    return list(_LEDGER)


def record(question: str, node, value, *, verified: bool, root: str | None = None,
           shape: str | None = None) -> dict:
    """Remember one answer, keyed by the expression that produced it AND the tree it read.

    AN ANSWER IS ONLY COMPARABLE WITH AN ANSWER ABOUT THE SAME TREE. The first version of
    this ledger had no notion of the tree, so "what is the total amount" asked of two
    different directories produced 550 and 100 and the SAME_SHAPE rule was ready to call
    that a contradiction. It happened not to fire in that run, which makes it a latent
    false positive rather than a bug -- the kind that appears in front of a user instead of
    a test. A fact from one tree is not a fact about another.

    `shape` can be given directly, and in production it always is: the door's computation
    dict carries an expression LABEL, not a node. Until this parameter existed the ledger
    recorded `node=None` for every answer the door ever produced, so `contradictions()`
    could not fire on a real conversation at all -- it was live code in the tests and dead
    code in the product, the same "built but not consulted" defect as the law grade. A
    check nothing reaches is indistinguishable from no check.
    """
    entry = {"question": question, "node": node, "value": value,
             "verified": bool(verified), "root": str(root) if root is not None else None}
    if shape is None and node is not None:
        shape = shape_of(node)
    if shape and verified:
        entry["shape"] = shape
    _LEDGER.append(entry)
    return entry


def _same_tree(a, b) -> bool:
    """Two entries can be compared only if they are about the same directory."""
    ra, rb = a.get("root"), b.get("root")
    if ra is None or rb is None:
        return True                    # an untagged record does not narrow anything
    return ra == rb


def shape_of(node) -> str:
    """The expression as a comparable string: what it reads and what it does to it.

    THIS USED TO STRIP EVERY STRING ARGUMENT, and the comment even said why -- "a kind, a
    column name: part of the shape? no". That answer was wrong, and it was wrong in the
    direction that makes a check dangerous rather than merely useless: with the literals
    gone, `sum(amount)`, `sum(qty)` and `max(amount)` all reduced to `aggregate(column())`
    and were reported as the SAME QUESTION. On `sales.csv`/`stock.csv` that is 550 against
    27, called a contradiction between two answers that were both right.

    It stayed invisible because `node` was `None` for every answer the door produced, so
    the rule never ran on real data. Two defects had been covering for each other: one hid
    the other, and fixing either alone would have been worse than fixing neither.

    A column name IS the question. An aggregate kind IS the question. A filter value IS the
    question. What is not part of the question is the path prefix, which the `root` tag
    already handles at the entry level.
    """
    if not hasattr(node, "op"):
        return repr(node)
    parts = []
    for a in getattr(node, "args", ()):
        if hasattr(a, "op"):
            parts.append(shape_of(a))
        elif isinstance(a, str) and "/" not in a:
            parts.append(a)               # a column, a kind, a filter value
    return f"{node.op}({','.join(parts)})"


def _numbers(value) -> list[float] | None:
    """The numbers in an answer, whether it arrives as numbers or as the rendered text.

    THIS FUNCTION WAS WRITTEN FOR A CALLER THAT DOES NOT EXIST. It accepted `int`, `float`
    and lists of them -- but every value the door produces is a STRING, because the
    computation dict renders the answer for a reader (`"550"`, `"[150.0, 150.0, 250.0]"`,
    `"yes"`). So it returned `None` for every real answer, `contradictions()` skipped every
    comparison, and the ledger reported nothing on every conversation ever held.

    That is the third time this round that a check passed its own tests because its tests
    handed it the convenient type. The lesson is not "parse strings"; it is that a function
    which only accepts one shape of input is only checked against that shape. Here the
    caller is the computation dict, so the input shape is defined by the dict, and the dict
    renders.

    Parsing is deliberately narrow: a bare number, or a bracketed list of bare numbers.
    Anything else -- `"yes"`, a label, a file name -- yields None and is not compared,
    because guessing that some other text is a number is how a consistency check starts
    inventing contradictions.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return [float(value)]
    if isinstance(value, str):
        stripped = value.strip()
        inner = stripped
        if stripped.startswith("[") and stripped.endswith("]"):
            inner = stripped[1:-1]
        pieces = [p.strip() for p in inner.split(",")] if inner.strip() else []
        if not pieces:
            return None
        out = []
        for piece in pieces:
            try:
                out.append(float(piece))
            except ValueError:
                return None            # not a rendering of numbers; do not guess
        return out
    if isinstance(value, (list, tuple)) and value and all(
            isinstance(v, (int, float)) and not isinstance(v, bool) for v in value):
        return [float(v) for v in value]
    return None


def contradictions() -> list[dict]:
    """Pairs of verified answers that must agree and do not.

    Two kinds are reported, and only these — anything looser would be guessing:

      SAME_SHAPE      two answers with structurally identical expressions. They answer the
                      same question, so their values must be equal.
      PARTS_NOT_WHOLE a list answer whose elements do not sum to a scalar answer that
                      claims to be the total of the same thing.

    Both were real: the first is why `what is the total amount divided by how many regions`
    could return 1.5 while 550 and 3 were both on the books. The second is the check the
    grouping invariant already makes INSIDE one answer, applied across two.
    """
    found: list[dict] = []
    verified = [e for e in _LEDGER if e.get("verified")]

    for i, a in enumerate(verified):
        for b in verified[i + 1:]:
            if not _same_tree(a, b):
                continue
            if a.get("shape") and a.get("shape") == b.get("shape"):
                va, vb = _numbers(a.get("value")), _numbers(b.get("value"))
                if va is None or vb is None:
                    continue
                if len(va) != len(vb) or any(abs(x - y) > 1e-9 for x, y in zip(va, vb)):
                    found.append({"kind": "SAME_SHAPE",
                                  "question_a": a["question"], "question_b": b["question"],
                                  "value_a": a.get("value"), "value_b": b.get("value"),
                                  "why": "identical expressions gave different answers"})

    scalars = [(e, _numbers(e.get("value"))) for e in verified]
    scalars = [(e, n) for e, n in scalars if n is not None and len(n) == 1]
    vectors = [(e, n) for e, n in ((e, _numbers(e.get("value"))) for e in verified)
               if n is not None and len(n) > 1]
    for vec_entry, vec in vectors:
        for sc_entry, sc in scalars:
            if not _same_tree(vec_entry, sc_entry):
                continue
            # only compare a total against a set of parts, and only when the parts really
            # are a partition -- not every list of numbers is the parts of that total
            if not _looks_like_parts_of(vec_entry, sc_entry):
                continue
            if abs(sum(vec) - sc[0]) > 1e-9:
                found.append({"kind": "PARTS_NOT_WHOLE",
                              "question_a": vec_entry["question"],
                              "question_b": sc_entry["question"],
                              "parts": vec_entry.get("value"), "sum_of_parts": sum(vec),
                              "whole": sc_entry.get("value"),
                              "why": "the parts do not add up to the total already reported"})
    return found


#: The operators that produce a TOTAL of something. A vector is the parts of a scalar only
#: if the scalar is one of these.
_TOTAL_OPS = ("sum", "count", "mean", "max", "min")


def _is_a_total(node) -> bool:
    """Does this expression claim to be the total of what it reads?

    THE FIRST VERSION OF THIS CHECK ASSUMED ANY SCALAR WAS A TOTAL, and it produced a false
    contradiction: `[150, 150, 250]` (whose sum is 550) was reported as not adding up to
    `1.5`, the answer to "the total amount divided by how many regions". That answer never
    claimed to be a total -- it is a quotient -- so the check was comparing two things that
    were never supposed to agree.

    A false contradiction is worse than a missed one: it teaches a reader to ignore every
    contradiction the system reports, which costs more than the feature is worth. The rule
    has to come from what the expression SAYS it is, not from the shape of its value.
    """
    op = getattr(node, "op", None)
    if op == "aggregate":
        return node.args and node.args[0] in _TOTAL_OPS
    if op == "count":
        return True
    # map/quotion/vector/composition: not a total unless it is literally an aggregate
    return False


def _looks_like_parts_of(vec_entry, sc_entry) -> bool:
    """Is this vector the breakdown of that scalar?

    Both conditions are required, and each is there because removing it produced a false
    positive that I measured:

      * they read the SAME column -- a partition of `amount` is the parts of the total of
        `amount`, and a vector of `qty` is not;
      * the scalar CLAIMS to be a total -- otherwise it is a quotient, a maximum, or
        something else that was never supposed to equal the parts.
    """
    if not _is_a_total(sc_entry.get("node")):
        return False
    a, b = _leaves(vec_entry.get("node")), _leaves(sc_entry.get("node"))
    return bool(a) and a == b


def _leaves(node) -> frozenset:
    """The (op, literal) pairs that identify WHAT an expression reads."""
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
