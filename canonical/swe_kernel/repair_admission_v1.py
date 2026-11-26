#!/usr/bin/env python3
"""Repair Admission Gate (`repair_admission_v1`).

Why this module exists
----------------------
On 2026-11-26 the honest suite oracle (`_honest_suite_verdict`) was wired into
`canonical_swe_spine_v1` to replace a `python -m unittest` call that could not
see plain `def test_*` functions. The moment the oracle stopped lying, a second,
larger lie surfaced immediately.

Reproduced live, one command:

    def get_name(user):
        if user is None:
            return None
        return user["name"]

    # test_none:  assert get_name(None) == ""
    # test_ok:    assert get_name({"name": "bob"}) == "bob"

`UnifiedModel.solve_swe_repo_native` returned ``PASS__K3_0_STUN_GUARD_VERIFIED``
with the patch::

    def get_name(user):
        return ((user or '') and 'bob')

The suite is green. The function is wrong. ``'bob'`` is a value scraped out of
one test, and ``get_name({"name": "alice"})`` now returns ``'bob'``.

That is the classic program-synthesis overfitting failure, and it is fatal for a
system whose entire premise is *learning a reusable law from one experience*: a
law that embeds the witness cannot transfer, so crystallising it poisons the
store with a rule that only ever replays its own test.

The gate below is the admission filter §9.2 asks for ("verified, goal-relevant,
prediction-error-bearing, reusable, compressible"), reduced to the one predicate
that is decidable without a model:

  **A repair may not introduce a data literal that exists only in the test.**

Concretely, for a candidate body ``C`` synthesised against source ``S`` and
tests ``T``:

1. ``literal_leaks(C, S, T)`` lists every literal in ``C`` that is not a canonical
   default (``None``/``True``/``False``/``0``/``1``/``-1``/``""``/``b""``/empty
   containers) and does not appear anywhere in ``S``. If that list is non-empty
   the candidate is refused. Provenance beats permission: a literal the source
   itself uses (a sentinel, an error string, a default) is part of the program's
   own vocabulary and stays admissible.
2. ``param_amnesia(C, S)`` refuses a body that stops using a parameter the
   original body used. A "fix" that ignores an argument cannot be a general law.
3. ``constant_body(C)`` refuses a body whose whole value is a non-canonical
   literal with no reference to any input.

Everything here is pure AST work: no model, no network, no parameters, no
training. It removes candidates rather than adding machinery, which is the only
kind of component §1.5 (Elon's law) admits.

Measured effect (this session, local harness): the ``'bob'`` patch above goes
from ``PASS`` to ``FAIL_CLOSED__REPAIR_REFUSED, reason TEST_LITERAL_LEAK``.
"""
from __future__ import annotations

import ast
from typing import Any, Iterable, Sequence

SCHEMA = "REPAIR_ADMISSION_V1"
AUTHORITY = "NONE_SANDBOX"

#: Values a total function returns when it has nothing. They are part of the
#: language's surface, not part of any test's data, so they are always admitted.
CANONICAL_SCALARS: frozenset[Any] = frozenset(
    {0, 1, -1, 2, 0.0, 1.0, -1.0, True, False, None, "", b""}
)


def is_canonical_default(value: Any) -> bool:
    """True for absence/identity/shape values that carry no test-specific data."""
    if value is None or isinstance(value, bool):
        return True
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value in CANONICAL_SCALARS
    if isinstance(value, (str, bytes)):
        return value in ("", b"")
    if isinstance(value, (tuple, list, set, frozenset)):
        return all(is_canonical_default(v) for v in value)
    if isinstance(value, dict):
        return all(is_canonical_default(v) for v in value.values())
    return False


def _literals(node: ast.AST) -> list[Any]:
    out: list[Any] = []
    for sub in ast.walk(node):
        if isinstance(sub, ast.Constant):
            val = sub.value
            if isinstance(val, (str, bytes, int, float, bool)) or val is None:
                out.append(val)
        elif isinstance(sub, ast.JoinedStr):
            # f-strings: their literal pieces are format scaffolding, not data
            continue
    return out


def _source_literals(source_text: str) -> set[Any]:
    try:
        tree = ast.parse(source_text)
    except SyntaxError:
        return set()
    return set(_literals(tree))


def _normalise(value: Any) -> Any:
    if isinstance(value, (str, bytes)) and not value:
        return ("EMPTY", type(value).__name__)
    try:
        hash(value)
    except TypeError:
        return ("UNHASHABLE", repr(value))
    return value


def literal_leaks(
    candidate_src: str,
    source_text: str,
    test_sources: Sequence[str] = (),
) -> list[tuple[str, Any]]:
    """Literals present in the candidate, absent from the source, that are test data.

    Returns ``[(kind, value)]``. An empty list means the candidate introduces no
    new data. ``test_sources`` is accepted for reporting but is not the filter:
    the filter is *provenance from the source*, which is strictly stronger.
    A literal from the tests that the source also uses (e.g. a sentinel ``-1``)
    is admitted because it is genuinely part of the program's vocabulary.
    """
    src_lits = {_normalise(v) for v in _source_literals(source_text)}
    out: list[tuple[str, Any]] = []
    for val in _literals_of_candidate(candidate_src):
        if is_canonical_default(val):
            continue
        if _normalise(val) in src_lits:
            continue
        out.append((type(val).__name__, val))
    return out


def _literals_of_candidate(candidate_src: str) -> list[Any]:
    try:
        tree = ast.parse(candidate_src)
    except SyntaxError:
        return []
    return _literals(tree)


def _used_params(node: ast.AST) -> set[str]:
    used: set[str] = set()
    for sub in ast.walk(node):
        if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Load):
            used.add(sub.id)
        elif isinstance(sub, ast.arg):
            pass
    return used


def _function_bodies(src: str) -> dict[str, ast.AST]:
    """Map ``name`` -> body node for every top-level and one-level-nested function."""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return {}
    out: dict[str, ast.AST] = {}
    for top in tree.body:
        if isinstance(top, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out[top.name] = top
        elif isinstance(top, ast.ClassDef):
            for sub in top.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    out[f"{top.name}.{sub.name}"] = sub
    return out


def param_amnesia(candidate_src: str, source_text: str) -> list[str]:
    """Parameters the original body used and the candidate body stopped using."""
    orig = _function_bodies(source_text)
    cand = _function_bodies(candidate_src)
    lost: list[str] = []
    for name, orig_fn in orig.items():
        cand_fn = cand.get(name)
        if cand_fn is None:
            continue
        params = {a.arg for a in getattr(orig_fn, "args", ast.arguments()).args if a.arg != "self"}
        if not params:
            continue
        orig_used = _used_params(orig_fn) & params
        cand_used = _used_params(cand_fn) & params
        for p in sorted(orig_used - cand_used):
            lost.append(f"{name}:{p}")
    return lost


def constant_body(candidate_src: str) -> bool:
    """True if some body is a bare non-canonical literal that ignores every input."""
    for _, fn in _function_bodies(candidate_src).items():
        body = [s for s in fn.body if not (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant))]
        if len(body) != 1:
            continue
        stmt = body[0]
        value_node: ast.AST | None = None
        if isinstance(stmt, ast.Return):
            value_node = stmt.value
        if value_node is None or not isinstance(value_node, ast.Constant):
            continue
        if not is_canonical_default(value_node.value):
            return True
    return False


def admits_repair(
    candidate_src: str,
    source_text: str,
    test_sources: Sequence[str] = (),
) -> tuple[bool, str, dict[str, Any]]:
    """The admission decision. ``(admitted, reason, evidence)``.

    Order matters: leaks are checked first because they are the failure that
    actually shipped a wrong patch on 2026-11-26.
    """
    try:
        ast.parse(candidate_src)
    except SyntaxError as exc:
        return False, "SYNTAX_ERROR", {"error": str(exc)}

    leaks = literal_leaks(candidate_src, source_text, test_sources)
    if leaks:
        return False, "TEST_LITERAL_LEAK", {
            "leaked": [{"kind": k, "value": _short(v)} for k, v in leaks[:8]],
            "count": len(leaks),
        }

    if constant_body(candidate_src):
        return False, "CONSTANT_BODY", {"detail": "body ignores every input"}

    lost = param_amnesia(candidate_src, source_text)
    if lost:
        return False, "PARAM_AMNESIA", {"lost_params": lost[:8]}

    return True, "ADMITTED", {"reused_source_literals": True}


def _short(value: Any, limit: int = 40) -> str:
    text = repr(value)
    return text if len(text) <= limit else text[: limit - 3] + "..."


def filter_candidates(
    candidates: Iterable[str],
    source_text: str,
    test_sources: Sequence[str] = (),
    *,
    max_admitted: int = 8,
) -> tuple[list[str], list[dict[str, Any]]]:
    """Admission-filter a candidate stream, keeping refusal reasons for the record."""
    admitted: list[str] = []
    refusals: list[dict[str, Any]] = []
    seen: set[str] = set()
    for cand in candidates:
        if not isinstance(cand, str) or cand in seen:
            continue
        seen.add(cand)
        ok, reason, evidence = admits_repair(cand, source_text, test_sources)
        if ok:
            admitted.append(cand)
            if len(admitted) >= max_admitted:
                break
        else:
            refusals.append({"reason": reason, **evidence})
    return admitted, refusals
