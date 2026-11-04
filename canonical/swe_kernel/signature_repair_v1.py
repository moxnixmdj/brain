"""Signature repairs: reconcile a call site with the definition it does not match.

Why this exists (pass thirteen, S8/S9): when the failure kinds were finally separated, SIGNATURE
worlds were solved by NO producer in the system -- zero candidates, not a failed search. This is the
second of the two remaining holes.

Two directions, because a mismatch has two ends and only execution can say which is wrong:
    (a) ADD the missing parameters at the DEFINITION, with a default, so the existing call is legal
    (b) REMOVE the surplus arguments at the CALL SITE, so the existing definition is satisfied
Both are real AST edits at real spans, and both are proposals: nothing here decides correctness, and
a candidate that fails the owed test is discarded by the screen like any other.

What it refuses to do: guess across files, guess when the arity is ambiguous, or invent a body.
"""

from __future__ import annotations

import ast
import re

# CPython's own words, and the only place the arity is stated. Both phrasings are matched because the
# message changed shape between versions ("takes 2 positional arguments but 3 were given" vs
# "takes 1 positional argument but 2 were given").
_ARITY = re.compile(
    r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\(\)\s*takes\s+(?P<takes>\d+)\s*positional\s+arguments?"
    r"\s+but\s+(?P<given>\d+)\s+(?:were|was)\s+given",
    re.I,
)
_MISSING_REQUIRED = re.compile(
    r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\(\)\s*missing\s+(?P<n>\d+)\s+required\s+positional\s+argument",
    re.I,
)


def arity_mismatch(failure_text: str) -> tuple[str, int, int] | None:
    """(function_name, takes, given) for a TypeError arity mismatch, or None."""
    if not isinstance(failure_text, str):
        return None
    m = _ARITY.search(failure_text)
    if m:
        return m.group("name"), int(m.group("takes")), int(m.group("given"))
    m = _MISSING_REQUIRED.search(failure_text)
    if m:
        # "takes" is not stated here, so it is left UNKNOWN as -1 rather than guessed as 0. With 0,
        # the surplus-argument branch computes `given - 0` and would happily strip every argument at
        # the call site -- a plausible-looking edit that inverts the actual defect. Measured
        # 2026-11-05 on `add(a, b)` called as `add(a)`: the tool produced `add()` and failed.
        return m.group("name"), -1, int(m.group("n"))
    return None


def _defs(tree: ast.AST, name: str) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    return [
        nd for nd in ast.walk(tree)
        if isinstance(nd, (ast.FunctionDef, ast.AsyncFunctionDef)) and nd.name == name
    ]


def _calls(tree: ast.AST, name: str) -> list[ast.Call]:
    return [
        nd for nd in ast.walk(tree)
        if isinstance(nd, ast.Call) and isinstance(nd.func, ast.Name) and nd.func.id == name
    ]


def _line_span(source: str, node: ast.AST) -> tuple[int, int] | None:
    """Byte offsets of a node in `source` on a single line, or None if it spans lines."""
    l0, c0 = getattr(node, "lineno", None), getattr(node, "col_offset", None)
    l1, c1 = getattr(node, "end_lineno", None), getattr(node, "end_col_offset", None)
    if None in (l0, c0, l1, c1) or l0 != l1:
        return None
    lines = source.splitlines(keepends=True)
    start = sum(len(x) for x in lines[: l0 - 1]) + c0
    end = sum(len(x) for x in lines[: l1 - 1]) + c1
    return start, end


def propose_signature_repairs(
    source_text: str,
    failure_text: str,
    *,
    max_candidates: int = 6,
    default_expr: str = "None",
) -> list[str]:
    """Candidates that make a mismatched call and definition agree. Refuses when it cannot be sure."""
    if not isinstance(source_text, str) or not source_text.strip():
        return []
    parsed = arity_mismatch(failure_text)
    if not parsed:
        return []
    name, takes, given = parsed
    try:
        tree = ast.parse(source_text)
    except SyntaxError:
        return []
    defs = _defs(tree, name)
    if len(defs) != 1:
        # Zero: the function is not in this file. More than one: which one is called is a dynamic
        # fact this producer cannot establish, and guessing would produce plausible wrong edits.
        return []
    fn = defs[0]
    if fn.args.vararg is not None or fn.args.kwarg is not None:
        # *args/**kwargs means the arity in the message is not the arity in the source.
        return []

    out: list[str] = []
    seen: set[str] = {source_text}
    lines = source_text.splitlines(keepends=True)

    def _emit(start: int, end: int, replacement: str) -> None:
        cand = source_text[:start] + replacement + source_text[end:]
        if cand in seen:
            return
        try:
            ast.parse(cand)
        except SyntaxError:
            return
        seen.add(cand)
        out.append(cand)

    # (a) ADD the missing positional parameters at the DEFINITION, defaulted, so existing calls stay
    # legal. Only when the definition is actually short of arguments.
    args = list(fn.args.posonlyargs) + list(fn.args.args)
    n_params = len(args)
    if given > n_params:
        deficit = given - n_params
        # insert after the last parameter (or inside the parens if there are none)
        if args:
            last = args[-1]
            anchor = f"{last.arg}"
            l0 = last.lineno
            line = lines[l0 - 1]
            idx = line.find(anchor, last.col_offset)
            if idx >= 0:
                insert_at = sum(len(x) for x in lines[: l0 - 1]) + idx + len(anchor)
                names = ", ".join(f"extra{i}=default_expr".replace("default_expr", default_expr)
                                  for i in range(deficit))
                _emit(insert_at, insert_at, ", " + names)
        else:
            sp = _line_span(source_text, fn)
            if sp:
                s_i = source_text.index("(", sp[0], sp[1])
                names = ", ".join(f"extra{i}={default_expr}" for i in range(deficit))
                _emit(s_i + 1, s_i + 1, names)

    # (b) REMOVE the surplus arguments at the CALL SITE. Only when a single call is present: with
    # several calls, the message does not say which one raised, and editing the wrong one is noise.
    calls = _calls(tree, name)
    if takes >= 0 and len(calls) == 1 and given > takes:
        call = calls[0]
        if call.keywords:
            return out
        surplus = given - max(takes, 0)
        if isinstance(call.args[0], ast.Starred):
            return out
        while surplus > 0 and len(call.args) > surplus:
            keep = call.args[: len(call.args) - surplus]
            sp = _line_span(source_text, call)
            if not sp:
                break
            try:
                rendered = ", ".join(ast.unparse(a) for a in keep)
            except Exception:
                break
            _emit(sp[0], sp[1], f"{name}({rendered})")
            break
    # (c) TOO FEW arguments at the CALL SITE. The message says how many are missing but not which
    # expressions to supply, so they come from the CALLING function's own parameters -- the only
    # values demonstrably in scope. Ranked by position, and only the first N are taken; a caller with
    # no spare parameters is declined rather than filled with a literal.
    if given > 0 and len(calls) == 1:
        call = calls[0]
        deficit = (takes - given) if takes >= 0 else given
        caller = None
        for nd in ast.walk(tree):
            if isinstance(nd, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for sub in ast.walk(nd):
                    if sub is call:
                        caller = nd
                        break
            if caller is not None:
                break
        if caller is not None:
            have = [a.arg for a in list(caller.args.posonlyargs) + list(caller.args.args)]
            # the values the call already passes are subtracted; what remains is what is available
            passed = {ast.unparse(a) for a in call.args}
            available = [p_ for p_ in have if p_ not in passed]
            if len(available) >= deficit:
                sp = _line_span(source_text, call)
                if sp:
                    rendered = ", ".join([ast.unparse(a) for a in call.args] + available[:deficit])
                    _emit(sp[0], sp[1], f"{name}({rendered})")
    return out[:max_candidates]
