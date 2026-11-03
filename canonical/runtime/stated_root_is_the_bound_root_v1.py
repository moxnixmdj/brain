"""The directory the sentence names is the directory the action reads.

WHY THIS EXISTS
---------------
Measured on 73f773d.  The goal

    Find the function in the python source root <X> that is never executed,
    and write its name to <Y>

compiled, executed, and returned

    PASS__RAW_GOAL_EXECUTED_AND_EXACT_SEMANTIC_ACCEPTANCE_VERIFIED

while `<Y>` was never created and the two capabilities that ran had searched a
directory the sentence never named.

The cause is a registry constant, not a lexical failure.  The row
`source.candidates.enumerate.stdlib` carries

    action_template.args.search_root = "canonical/runtime"

as a literal, so the slot the sentence states is not a placeholder and the binder
has nothing to bind: whatever the sentence names, the action reads
`canonical/runtime`.  Measured on the same sentence, 400 of 2,309 files were
enumerated under `canonical/runtime` and none under the stated root.

Two separate carriers then reported agreement with the sentence anyway:

* `raw_goal_trace_acceptance_v1` re-inspects the enumeration and checks that
  every candidate's digest is present under the search root -- the root that was
  actually used.  Self-consistent, and the sentence was never consulted about
  that root.  It carries `_ROOT_ARGS` and validates the root with
  `path.is_dir()`, but it has no rule that the root must be one the goal stated.
* `world_binding_v1.stated_paths_absent_in_workspace` asks whether the sentence
  names an extensionless path that does not exist, and refuses if so.  With an
  in-repo, existing stated root (the normal case) it returns `[]` -- correctly,
  the path is there -- and the hardcoded constant still wins.

So the same failure is produced by a stated root that exists and by one that does
not.  Only the second is caught today (by the `world_binding` refusal), and only
by the route that consults it.

WHAT THIS MODULE WILL NOT DO
----------------------------
It does not decide what a capability MEANS.  It compares one thing: if the
sentence names a directory, and the action reads a `search_root`/`source_root`,
does the action read the directory the sentence named?  `canonical/runtime` is a
true working default for `source_root`, so a sentence that names no directory at
all is left exactly as it is.

Nothing here executes anything.  It returns refusals for a caller to raise; the
refusal code names the argument and the two roots so the reader can see the
disagreement instead of reading a PASS.
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping

SCHEMA = "PROJECT_BRAIN_STATED_ROOT_IS_THE_BOUND_ROOT_V1"

# The declared arguments that name the directory an action READS.  Deliberately not
# `output_path`/`result_path`: those name where evidence is written, which is a
# different question with its own guard (`_future_artifacts`).
READ_ROOT_ARGS = ("source_root", "search_root")

REFUSAL = "STATED_ROOT_NOT_BOUND"
REFUSAL_DETAIL = "THE_GOAL_NAMES_A_DIRECTORY_THE_ACTION_DOES_NOT_READ"


def _norm(value: str) -> str:
    """Compare two spellings of a repository-relative directory."""
    text = str(value or "").strip().replace("\\", "/")
    while text.startswith("./"):
        text = text[2:]
    text = text.rstrip("/")
    if text.endswith("/."):
        text = text[:-2].rstrip("/")
    return "" if text in (".", "./") else text


def _row_args(row: Any) -> Mapping[str, Any]:
    args = row.get("args") if isinstance(row, Mapping) else None
    return args if isinstance(args, Mapping) else {}


def stated_read_roots(goal: str, existing_directories: Iterable[tuple[str, Any]]) -> list[str]:
    """The directories the SENTENCE names, among the paths the compiler extracted.

    `existing_directories` is (raw, path) as `goal_compiler._repo_paths` returns it --
    already resolved against the repository root, so "is this a directory" is answered
    by the filesystem rather than by the shape of the string.
    """
    from pathlib import Path

    out: list[str] = []
    for raw, path in existing_directories:
        try:
            is_dir = Path(path).is_dir()
        except OSError:
            is_dir = False
        if not is_dir:
            continue
        rel = _norm(raw)
        if rel and rel not in out:
            out.append(rel)
    return out


def bound_read_roots(action_rows: Iterable[Mapping[str, Any]]) -> list[str]:
    """The directories the ACTIONS read, as they were actually bound."""
    out: list[str] = []
    for row in action_rows or ():
        args = _row_args(row)
        for name in READ_ROOT_ARGS:
            value = args.get(name)
            if isinstance(value, str) and value.strip():
                rel = _norm(value)
                if rel not in out:
                    out.append(rel)
    return out


def unread_stated_roots(goal: str, action_rows: Iterable[Mapping[str, Any]],
                        existing_directories: Iterable[tuple[str, Any]]) -> list[str]:
    """Stated read-roots that no bound action reads.

    Empty when the sentence names no directory (a genuine default is untouched), and
    empty when at least one bound action reads a directory the sentence named -- a plan
    that reads the stated directory somewhere is not accused of ignoring it.
    """
    stated = stated_read_roots(goal, existing_directories)
    if not stated:
        return []
    bound = set(bound_read_roots(action_rows))
    if not bound:
        # Nothing declared a read-root, so there is nothing to disagree with.
        return []
    if any(rel in bound for rel in stated):
        return []
    return stated


def refusal(goal: str, action_rows: Iterable[Mapping[str, Any]],
            existing_directories: Iterable[tuple[str, Any]]) -> dict[str, Any] | None:
    """A refusal dict when the sentence's directory was not read, else None."""
    unread = unread_stated_roots(goal, action_rows, existing_directories)
    if not unread:
        return None
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED__" + REFUSAL,
        "pass": False,
        "reason": REFUSAL_DETAIL,
        "stated_roots_not_read": unread[:3],
        "roots_actually_read": bound_read_roots(action_rows)[:3],
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }
