"""The question is the missing name, and the guide already wrote the answer.

The guide-as-test-suite instrument replays 138 of 180 real examples; 37 of the 42 refusals are
`NameError: name 'X' is not defined` because the author bound `X` in a DIFFERENT example of the
same module. The project's own answer to "what should he know, and how does he ask?" is
goal-directed: the goal is to reproduce the guide's printed output; the gap is the name the
interpreter refused; the question is therefore exactly `X`; and the answer is in the guide, not
on the web and not in a weight.

This module is only the mechanism. It holds no facts, no model, no network and no weights:

  * `missing_name` reads the question out of the interpreter's own refusal;
  * `bound_names` / `candidates` derive the answer set from the guide's own statements;
  * `rank` orders probes by a computed prior (near, before, fewest free names);
  * `resolve` executes each probe and keeps a binding ONLY if it reproduces the guide's own
    printed output. Two bindings that both reproduce it are AMBIGUOUS and are refused -- one
    example does not identify a rule, which is the repository's measured one-shot limit.

The execution oracle is supplied by the caller, so this module never imports a tool, never
hardcodes a program and never becomes a runtime dependency on another model. A resolved
example is an observed fact; the mechanism that found it is code. Nothing here writes to a
model weight. Authority NONE__PRODUCER_RUN_SANDBOX.
"""

from __future__ import annotations

import ast
import builtins
import re
from typing import Any, Callable, Iterable, Mapping, Sequence

SCHEMA = "BRAIN_GUIDE_PRECONDITION_V1"
MISSING_NAME = re.compile(r"name '([A-Za-z_][A-Za-z0-9_]*)' is not defined")

# Names the interpreter supplies. They are not facts stored here; they are the language's own.
_BUILTINS = frozenset(dir(builtins))


def missing_name(stderr: str | Sequence[str] | None) -> str | None:
    """The one question the refusal asks. No question is invented from prose."""
    text = "\n".join(stderr) if isinstance(stderr, (list, tuple)) else (stderr or "")
    found = MISSING_NAME.search(text)
    return found.group(1) if found else None


def bound_names(statement: str) -> set[str]:
    """Names this statement would bind, read from its syntax rather than its spelling."""
    try:
        tree = ast.parse(statement)
    except SyntaxError:
        return set()
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            out.add(node.id)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.add(node.name)
        elif isinstance(node, ast.alias):
            out.add((node.asname or node.name).split(".")[0])
        elif isinstance(node, ast.ExceptHandler) and node.name:
            out.add(node.name)
    return out


def free_names(statement: str, bound: Iterable[str] = ()) -> set[str]:
    """Names the statement reads but does not bind, minus the language's own builtins."""
    try:
        tree = ast.parse(statement)
    except SyntaxError:
        return set()
    loaded = {n.id for n in ast.walk(tree)
              if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
    return loaded - set(bound) - _BUILTINS


def wrong_binding(statement: str, name: str) -> str:
    """A machine-made wrong input: change one literal in the binding, nothing else.

    AST, not a regex: a regex on `'''...'''` either finds no quoted string or mangles a
    multiline one. When the binding has no literal at all (an import), the wrong input is a
    generic object of the same name -- still machine-made, still no program name in the
    mechanism.
    """
    try:
        tree = ast.parse(statement)
    except SyntaxError:
        return f"{name} = object()"
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and not isinstance(node.value, bool) \
                and isinstance(node.value, (int, float, str)):
            node.value = node.value + "x" if isinstance(node.value, str) else node.value + 1
            return ast.unparse(tree)
    return f"{name} = object()"


def separates(binding: str, name: str, job: Mapping[str, Any], *,
              replay: Callable[[Mapping[str, Any]], Mapping[str, Any]],
              compare: Callable[[Sequence[str], Sequence[str]], Mapping[str, Any]]) -> bool:
    """Does a WRONG binding fail to reproduce the guide's printed output?

    If the wrong binding also reproduces it, the example cannot identify the binding, and
    `resolve` refuses it. This is the same falsifiability test the room witness applies to a
    check, moved to the question side of the loop.
    """
    mutant = wrong_binding(binding, name)
    session = dict(job, _session=[mutant, *list(job.get("_session") or [])])
    got = replay(session)
    return not (bool(got.get("ok")) and
                bool(compare(got.get("got") or [], job.get("expected") or []).get("matches")))


def candidates(jobs: Sequence[Mapping[str, Any]], name: str,
               *, guide: str | None = None) -> list[dict[str, Any]]:
    """Every statement in the guide that binds the missing name.

    A session's CONTEXT statements are part of the guide too: `s = SequenceMatcher(...)` is an
    assignment the author wrote before the printing statement, and `as_sessions` carries it in
    `_session`. Reading only statements with printed output would throw the answer away.
    """
    rows: list[dict[str, Any]] = []
    for job in jobs:
        if guide is not None and job.get("guide") != guide:
            continue
        for index, statement in enumerate(job.get("_session") or []):
            if name not in bound_names(statement):
                continue
            rows.append({"statement": statement, "guide": job.get("guide"),
                         "block_line": job.get("block_line"), "session_index": index,
                         "free": sorted(free_names(statement))})
    # One binding may appear in many examples; it is one hypothesis, not many.
    unique: dict[str, dict[str, Any]] = {}
    for row in rows:
        unique.setdefault(row["statement"], row)
    return list(unique.values())


def rank(rows: Sequence[Mapping[str, Any]], job: Mapping[str, Any],
         *, limit: int = 8) -> list[dict[str, Any]]:
    """A computed prior over probes: near, at or before the example, with fewest free names.

    This is deliberately NOT called information gain. Expected information gain needs a
    likelihood over hypotheses (`canonical/runtime/settlement_v1.py`); here the probe is cheap
    and the guide's printed output is an exact oracle, so the ranking only decides WHICH probe
    to run FIRST. Execution, not the ranking, decides the answer.
    """
    def key(row: Mapping[str, Any]) -> tuple[int, int, int, int]:
        try:
            here = int(job.get("block_line") or 0)
            there = int(row.get("block_line") or 0)
        except (TypeError, ValueError):
            here = there = 0
        before = 0 if there <= here else 1
        return (before, abs(here - there), len(row.get("free") or ()),
                len(row.get("statement") or ""))
    return sorted((dict(r) for r in rows), key=key)[:limit]


def resolve(job: Mapping[str, Any], probes: Sequence[Mapping[str, Any]], *,
            question: str | None = None,
            replay: Callable[[Mapping[str, Any]], Mapping[str, Any]],
            compare: Callable[[Sequence[str], Sequence[str]], Mapping[str, Any]],
            separate: Callable[[str], bool] | None = None,
            limit: int = 8) -> dict[str, Any]:
    """Ask the ranked probes; keep a binding only if the guide's own output comes back.

    `separate(binding)` asks whether a machine-made WRONG binding would also reproduce the
    guide's output. If it would, the example does not identify this binding: two hypotheses fit
    one observation, and the repository's measured rule is that an unidentified survivor is not
    knowledge. Such a candidate is recorded and refused rather than admitted.
    """
    ordered = rank(probes, job, limit=limit)
    tried: list[dict[str, Any]] = []
    reproducing: list[str] = []
    unidentified: list[str] = []
    for probe in ordered:
        session = dict(job, _session=[probe["statement"], *list(job.get("_session") or [])])
        got = replay(session)
        ok = bool(got.get("ok"))
        verdict = (compare(got.get("got") or [], job.get("expected") or []) if ok
                   else {"matches": False, "verdict": got.get("why")})
        row: dict[str, Any] = {"statement": probe["statement"][:160], "ran": ok,
                              "matches": bool(verdict.get("matches"))}
        if verdict.get("matches"):
            if separate is not None and not separate(probe["statement"]):
                row["identified"] = False
                unidentified.append(probe["statement"])
            else:
                row["identified"] = True
                reproducing.append(probe["statement"])
        tried.append(row)
    if not reproducing:
        status = ("REFUSED__BINDING_NOT_IDENTIFIED_BY_THE_EXAMPLE" if unidentified else
                  "REFUSED__NO_BINDING_REPRODUCED_THE_GUIDES_OUTPUT")
    elif len(set(reproducing)) > 1:
        status = "REFUSED__AMBIGUOUS_BINDING"
    else:
        status = "RESOLVED__GUIDE_OUTPUT_REPRODUCED"
    return {"schema": SCHEMA, "status": status, "resolved": status.startswith("RESOLVED"),
            "question": question, "candidates": len(probes), "probes_run": len(tried),
            "reproducing": len(set(reproducing)), "unidentified": len(unidentified),
            "binding": reproducing[0] if reproducing else None, "tried": tried}
