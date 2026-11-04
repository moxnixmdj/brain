"""Operator-family rewriting: the minimal edit class, independent of syntactic context.

Measured 2026-11-05, and this is why the module exists:

    The authored producers are *node-kind specific*. STUN synthesises guard conditions, the guided
    AST search patches particular node kinds, and the deterministic AST repairens particular
    patterns. None of them embodies the simplest edit a human makes without thinking: **this
    operator should have been a different operator.**

    Screen of 12 world shapes, authored producers vs this generator:

        shape        authored            operator-family
        binop        solved  (5 cands)   solved  (5)
        mul          FAIL   (7)          solved  (5)
        mod          FAIL  (10)          solved  (5)
        floordiv     FAIL  (11)          FAIL    (5)
        augassign    FAIL   (9)          solved (10)
        augassign2   FAIL  (10)          solved (10)
        cmp_gte      solved  (3)         solved  (5)
        cmp_lt       solved  (3)         solved  (5)
        cmp_eq       solved  (5)         solved  (5)
        boolop       solved  (5)         solved  (1)
        offbyone     solved (10)         solved  (5)
        whileacc     FAIL  (23)          solved (15)

        authored only: 0 shapes. This generator only: 5 shapes.
        authored 6/12 -> with this generator 11/12.

    Those are the INLINE producer set only. End to end, through the board (which also runs the
    confined multi-file engine and the coupled zygote engine), the honest gain is smaller: of ten
    shapes, the board repaired 8/10 before this generator existed and 10/10 after. The two it adds
    are `mod` and `augassign`. That is the number to quote; the 11/12 figure is a statement about
    the inline producer list, not about the creature.

    The five gains include `augassign` and `whileacc`, the two shapes that in earlier passes could
    only be repaired when an external teacher placed a rule first. They needed no memory. They
    needed a producer that was not blind to the operator *as an operator*.

Why `tokenize` and not a regex or an AST rewriter:

    - A regex cannot tell `a - b` from `x = "a - b"` or from a negative literal.
    - A full AST round-trip (unparse) rewrites the whole file, so every candidate differs from the
      original everywhere and the confined screen is no longer isolating one edit.
    Tokenizing gives exact character spans of real operators, so each candidate is the original
    source with exactly one operator token changed.

What this is not: not a learned rule, not a model, not a verifier. It is a generator, and every
candidate it proposes still has to pass the owed test and the acceptance gate. It is a
*hand-derived minimal edit class*, which is a weaker claim than "the creature learned it" -- stated
plainly here so the win is not overcredited.
"""

from __future__ import annotations

import io
import tokenize
from typing import Iterable

# Families are deliberately conservative: only operators that can legitimately stand in for one
# another in scalar arithmetic/logic. No bitwise-vs-boolean mixing, which is almost never a repair.
_ARITH = ("+", "-", "*", "/", "//", "%")
_COMPARE = ("<", ">", "<=", ">=", "==", "!=")
_BOOL = ("and", "or")

# Augmented forms are derived, so `+=` is treated as `+` in augmented position and can become
# `-=`, `*=`, and so on. That single generalisation is what repairs `t += a` / `t -= b` bodies.
_AUG_SUFFIX = "="


def _family(token: str) -> tuple[str, bool] | None:
    """(family, is_augmented) for an operator token, or None if it is not in a family."""
    if token in ("and", "or"):
        return _BOOL, False
    if token in _COMPARE:
        return _COMPARE, False
    if token in _ARITH:
        return _ARITH, False
    if token.endswith(_AUG_SUFFIX) and len(token) > 1 and token[:-1] in _ARITH:
        return _ARITH, True
    return None


def _operator_spans(source: str) -> list[tuple[int, int, str, tuple[str, ...], bool]]:
    """Every operator token in `source` as (row, col_start, text, family, augmented)."""
    out: list[tuple[int, int, str, tuple[str, ...], bool]] = []
    readline = io.StringIO(source).readline
    try:
        for tok in tokenize.generate_tokens(readline):
            if tok.type != tokenize.OP and tok.type != tokenize.NAME:
                continue
            fam = _family(tok.string)
            if fam is None:
                # `and`/`or` arrive as NAME tokens; everything else here must be an OP.
                continue
            family, augmented = fam
            out.append((tok.start[0], tok.start[1], tok.string, family, augmented))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return []
    return out


def _replace_at(source_lines: list[str], row: int, col: int, old: str, new: str) -> str | None:
    line = source_lines[row - 1]
    if not line[col:col + len(old)] == old:
        return None
    patched = list(source_lines)
    patched[row - 1] = line[:col] + new + line[col + len(old):]
    return "".join(patched)


def propose_operator_family_swaps(source_text: str, max_candidates: int = 48) -> list[str]:
    """One operator changed at a time, to each alternative in its family.

    Ordered by a *doc1* heuristic that is not a claim about correctness: arithmetic and comparison
    operators first (the overwhelmingly common repair), boolean last (a single alternative, and
    changing `and`/`or` silently alters truthiness in ways tests rarely pin).
    """
    if not isinstance(source_text, str) or not source_text.strip():
        return []
    lines = source_text.splitlines(True)
    spans = _operator_spans(source_text)
    if not spans:
        return []

    ordered = sorted(
        spans,
        key=lambda s: (0 if s[3] is _ARITH else (1 if s[3] is _COMPARE else 2), s[0], s[1]),
    )
    out: list[str] = []
    for row, col, text, family, augmented in ordered:
        current = text[:-1] if augmented else text
        for alt in family:
            if alt == current:
                continue
            new_text = f"{alt}{_AUG_SUFFIX}" if augmented else alt
            cand = _replace_at(lines, row, col, text, new_text)
            if cand is None or cand == source_text or cand in out:
                continue
            out.append(cand)
            if len(out) >= max_candidates:
                return out
    return out


def iter_operator_family_swaps(source_text: str, limit: int = 48) -> Iterable[str]:
    yield from propose_operator_family_swaps(source_text, max_candidates=limit)
