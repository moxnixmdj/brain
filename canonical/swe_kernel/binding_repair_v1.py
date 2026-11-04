"""Binding repairs: the missing name is usually something the file already has, spelled wrong.

Why this exists (pass twelve, S8): the failure-kind classifier showed the board contains ONLY value
failures, so routing by kind had nothing to route. When I built genuinely non-value worlds, the system
had no producer for them at all -- BINDING, SIGNATURE and SYNTAX were 0/1 solved by every family that
exists. The gap was a missing CAPABILITY, not missing scheduling.

This closes the tractable third of it. A NameError names the offending identifier, and the repair is
almost always one of:
    (a) a typo of a name already defined in the file  -> substitute the near neighbour
    (b) a definition that EXISTS in the file but appears after its use, or is shadowed  -> no edit
        possible without moving code, so this producer declines rather than guessing

Everything is either verified by execution or rejected; nothing here decides correctness.
"""

from __future__ import annotations

import ast
import difflib
import io
import re
import tokenize

_MISSING = re.compile(r"name '([A-Za-z_][A-Za-z0-9_]*)' is not defined")


def missing_name(failure_text: str) -> str | None:
    """The identifier a NameError names, or None."""
    if not isinstance(failure_text, str):
        return None
    m = _MISSING.search(failure_text)
    return m.group(1) if m else None


def _defined(source_text: str) -> set[str]:
    """Every name the module itself introduces: defs, assignments, arguments, imports."""
    out: set[str] = set()
    try:
        tree = ast.parse(source_text)
    except SyntaxError:
        return out
    for nd in ast.walk(tree):
        if isinstance(nd, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.add(nd.name)
        elif isinstance(nd, ast.Name) and isinstance(nd.ctx, ast.Store):
            out.add(nd.id)
        elif isinstance(nd, ast.arg):
            out.add(nd.arg)
        elif isinstance(nd, ast.alias):
            out.add((nd.asname or nd.name).split(".")[0])
    return out


def _spans_of(source_text: str, target: str) -> list[tuple[int, int]]:
    """(row, col_start, col_end) for every NAME token equal to `target`. tokenize, not regex, so a
    string or comment containing the text is never rewritten."""
    out: list[tuple[int, int, int]] = []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(source_text).readline):
            if tok.type == tokenize.NAME and tok.string == target:
                out.append((tok.start[0], tok.start[1], tok.end[1]))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return []
    return out


def propose_binding_repairs(
    source_text: str,
    failure_text: str,
    *,
    max_candidates: int = 8,
    min_ratio: float = 0.6,
) -> list[str]:
    """Candidates that replace a misspelled identifier with a near neighbour defined in the file.

    `min_ratio` is a PRECISION floor, not a correctness one: a candidate is still only a proposal and
    is screened by execution. It exists so the producer does not emit `step -> a` (similarity 0.0),
    which is noise rather than a hypothesis.
    """
    if not isinstance(source_text, str) or not source_text.strip():
        return []
    target = missing_name(failure_text)
    if not target:
        return []
    defined = _defined(source_text)
    # A name that IS defined but still raises NameError is a scope/ordering problem, not a typo:
    # this producer cannot fix that and must decline instead of substituting something arbitrary.
    if target in defined:
        return []
    ranked = sorted(
        ((difflib.SequenceMatcher(None, target, cand).ratio(), cand) for cand in defined),
        reverse=True,
    )
    spans = _spans_of(source_text, target)
    if not spans:
        return []
    lines = source_text.splitlines(True)
    out: list[str] = []
    seen: set[str] = {source_text}
    for ratio, cand in ranked:
        if ratio < min_ratio:
            break
        for row, start, end in spans:
            line = lines[row - 1]
            if line[start:end] != target:
                continue
            new_line = line[:start] + cand + line[end:]
            cand_src = "".join(lines[: row - 1]) + new_line + "".join(lines[row:])
            if cand_src in seen:
                continue
            try:
                ast.parse(cand_src)
            except SyntaxError:
                continue
            seen.add(cand_src)
            out.append(cand_src)
            if len(out) >= max_candidates:
                return out
    return out
