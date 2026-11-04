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

import canonical.runtime.decomposition_law_v1 as _D
import canonical.runtime.value_algebra_v1 as V

#: One record per answered question. In-process only, and cleared explicitly -- the same
#: rule as the evaluation memo: a fact from an earlier question is not a fact about this one
#: unless it is re-derivable from the tree.
_LEDGER: list[dict] = []

#: Pairs that could not be compared, kept apart from contradictions so the contradiction
#: list never contains a "I could not tell".
_NOTES: list[dict] = []


def reset() -> None:
    """Forget everything. Same discipline as the evaluation memo."""
    _LEDGER.clear()
    _NOTES.clear()


def entries() -> list[dict]:
    return list(_LEDGER)


def record(question: str, node, value, *, verified: bool, root: str | None = None,
           shape: str | None = None, aggregate: str | None = None,
           reads_column: str | None = None, restricts_rows: bool | None = None,
           is_a_whole: bool | None = None) -> dict:
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
             "verified": bool(verified), "root": str(root) if root is not None else None,
             # WHICH AGGREGATE PRODUCED THIS, if any. Recorded because in production there
             # is no node to ask, and the decomposition law needs the operator to decide
             # how -- or whether -- the parts can be checked against the whole.
             "aggregate": aggregate if aggregate is not None else
             (_D.aggregate_kind(node) if node is not None else None),
             "reads_column": reads_column if reads_column is not None else
             (_D.read_column(node) if node is not None else None),
             "restricts_rows": bool(restricts_rows) if restricts_rows is not None else
             (_D.restricts_rows(node) if node is not None else False),
             "is_a_whole": bool(is_a_whole) if is_a_whole is not None else
             (_D.is_a_whole(node) if node is not None else False)}
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
    noted: list[dict] = []
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
            if not _same_column(vec_entry, sc_entry):
                continue
            if not sc_entry.get("is_a_whole"):
                continue
            # only compare a total against a set of parts, and only when the parts really
            # are a partition -- not every list of numbers is the parts of that total
            # THE RECOMBINATION IS DISCOVERED FROM THE OPERATOR, not hardcoded to sum().
            # `max` and `min` were named as totals in the old typed list and then compared
            # with `sum`, which is wrong for both; and an operator that does not decompose
            # at all (`mean`) must be reported as UNCHECKABLE rather than passed over in
            # silence, which is how "I could not judge" kept being read as "fine".
            from canonical.runtime import decomposition_law_v1 as _D
            verdict = _D.check_parts_against_whole(
                vec_entry.get("node"), vec, sc_entry.get("node"), sc[0],
                kind=sc_entry.get("aggregate"),
                whole_restricts=sc_entry.get("restricts_rows"))
            if verdict["verdict"] == "disagrees":
                found.append({"kind": "PARTS_NOT_WHOLE",
                              "question_a": vec_entry["question"],
                              "question_b": sc_entry["question"],
                              "parts": vec_entry.get("value"),
                              "recombined": verdict["recombined"],
                              "whole": sc_entry.get("value"),
                              "why": verdict["why"]})
            elif verdict["verdict"] == "uncheckable":
                # AN UNCHECKABLE PAIR IS NOT A CONTRADICTION, and reporting it as one is
                # exactly the false positive this round was supposed to stop making: on a
                # coherent conversation it produced six "contradictions" and none was real.
                # It is recorded as a NOTE, kept out of `contradictions()` so the list stays
                # trustworthy, and available to a reader that wants to know what could not
                # be checked -- which is different from what failed.
                noted.append({"kind": "UNCHECKABLE_PAIR",
                              "question_a": vec_entry["question"],
                              "question_b": sc_entry["question"],
                              "why": verdict["why"]})
    _NOTES[:] = noted
    return found


def _leaves(node) -> frozenset:
    from canonical.runtime import decomposition_law_v1 as _D
    return _D._leaves(node)


def _same_column(a, b) -> bool:
    """Two answers are about the same thing only if they aggregate the same column.

    THE SECOND FALSE POSITIVE, MEASURED. With the leaf-set check removed, `[150, 150, 250]`
    -- the amounts per region -- was compared against `27`, the total of `qty`. Both are
    correct and they are about different columns. The column is the fact that decides it;
    full leaf sets are too strict (a grouping reads a table, a flat total reads a column)
    and no check at all is too loose.
    """
    ca = a.get("reads_column") if a.get("reads_column") is not None else _D.read_column(a.get("node"))
    cb = b.get("reads_column") if b.get("reads_column") is not None else _D.read_column(b.get("node"))
    if ca is None or cb is None:
        return True                      # cannot tell: do not invent a distinction
    return ca == cb
