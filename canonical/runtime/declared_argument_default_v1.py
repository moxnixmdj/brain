"""A template argument may declare a default that the goal still outranks.

THE MISSING PRIMITIVE
---------------------
`world_binding_v1` states its own precedence in a comment:

    GOAL > DEMONSTRATED RECEIPT > WORLD HEURISTIC.

That chain only ever runs over `${input.X}` placeholders.  An argument written as
a bare literal never enters it.  It is not bound, so nothing can override it, and
`render_args` emits it unchanged.  The result is a third mode the chain does not
describe:

    FROZEN LITERAL > GOAL

Measured on 73f773d, two rows do exactly that:

    source.candidates.enumerate.stdlib        search_root = "canonical/runtime"
    structured.decision_evidence.locate.stdlib search_root = "canonical"

and the sentence `Find the function in the python source root <X> ...` enumerated
400 files under `canonical/runtime` while `<X>` was never read.  It is not a
default, because a default is what applies when the goal is SILENT -- this applied
when the goal had spoken.

WHY THE OBVIOUS REPAIRS ARE BOTH WRONG
--------------------------------------
Writing `"${input.search_root}"` binds the goal correctly (measured: it returns the
stated root), and it is what 35 rows already do for `source_root`.  But it makes the
row UNBINDABLE when the goal is silent, because `complete_inputs` reports the slot
in `missing` and every caller refuses on a non-empty `missing`.  So the two obvious
routes are:

    frozen literal      -> goal can never win
    bare placeholder    -> goal must always speak

Both are wrong, and the registry has been forced to choose between them.  That is
why the literal accumulated: it was the only way to have a fallback.

THE PRIMITIVE
-------------
    "${input.search_root | canonical/runtime}"

Read: "the goal's value if the goal supplies one, otherwise this default."  It
composes with the existing chain instead of sitting outside it:

    1. a value the binder settled from the goal            wins
    2. the declared default, when the goal settled nothing  used, and REPORTED
    3. otherwise                                            missing, as today

The default is reported in `filled_from_declared_default` so a reader can see a
constant was used rather than a binding.  That distinction is the whole point: today
a frozen literal is indistinguishable from a grounded value at the point of use.

WHAT THIS DOES NOT DO
---------------------
It does not invent a default.  A row that declares none behaves exactly as it does
now, including failing closed when the goal is silent.  The default is data the row
states, never a heuristic this module guesses.
"""
from __future__ import annotations

import re
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_DECLARED_ARGUMENT_DEFAULT_V1"

# `${input.NAME | default}`.  The default runs to the closing brace and may contain
# anything except a brace, so paths, globs and package specifiers all fit.  Deliberately
# NOT lazy across `}`: a default is a single scalar, and a brace means the author made a
# mistake this parser should refuse rather than silently truncate.
DECLARED_DEFAULT_RE = re.compile(
    r"\$\{input\.(?P<name>[A-Za-z0-9_]+)\s*\|\s*(?P<default>[^{}]*)\}")

# The plain form, unchanged.  Kept separate so the plain path costs exactly what it did.
_PLAIN_RE = re.compile(r"\$\{input\.([A-Za-z0-9_]+)\}")


def declared_defaults(entry: Mapping[str, Any] | None) -> dict[str, str]:
    """argument name -> the default the template declares for it.

    Empty for every row that declares none, which is every row today.  A row that
    declares a default for one argument is unaffected in its other arguments.
    """
    out: dict[str, str] = {}
    template = (entry or {}).get("action_template") or {}
    stack: list[Any] = [template]
    while stack:
        cur = stack.pop()
        if isinstance(cur, Mapping):
            stack.extend(cur.values())
        elif isinstance(cur, (list, tuple)):
            stack.extend(cur)
        elif isinstance(cur, str):
            for m in DECLARED_DEFAULT_RE.finditer(cur):
                name = m.group("name")
                # First declaration wins; a template that declares two different
                # defaults for one name is refused by `conflicting_defaults`.
                out.setdefault(name, m.group("default"))
    return out


def conflicting_defaults(entry: Mapping[str, Any] | None) -> list[str]:
    """Argument names this template gives two different defaults.

    An ambiguous default is not a default.  The caller refuses the row rather than
    picking one, on the same rule the binder uses for every other ambiguity.
    """
    seen: dict[str, set[str]] = {}
    template = (entry or {}).get("action_template") or {}
    stack: list[Any] = [template]
    while stack:
        cur = stack.pop()
        if isinstance(cur, Mapping):
            stack.extend(cur.values())
        elif isinstance(cur, (list, tuple)):
            stack.extend(cur)
        elif isinstance(cur, str):
            for m in DECLARED_DEFAULT_RE.finditer(cur):
                seen.setdefault(m.group("name"), set()).add(m.group("default"))
    return sorted(name for name, values in seen.items() if len(values) > 1)


def substitute(value: Any, bound: Mapping[str, Any], defaults: Mapping[str, str],
               *, used: dict[str, str] | None = None) -> Any:
    """Render one template value, applying defaults only where `bound` is silent.

    A key `bound` holds ALWAYS wins -- including a key bound to a falsy value that is
    still a real answer.  That ordering is the entire fix: the default can never
    outrank the goal.
    """
    def render(text: str) -> str:
        def repl(match: re.Match[str]) -> str:
            name = match.group("name")
            if name in bound and str(bound[name]).strip():
                return str(bound[name])
            if name in defaults:
                if used is not None:
                    used[name] = defaults[name]
                return defaults[name]
            raise KeyError("UNBOUND_TEMPLATE_ARGUMENT:" + name)
        return DECLARED_DEFAULT_RE.sub(repl, text)

    if isinstance(value, str):
        return render(value)
    if isinstance(value, (list, tuple)):
        return [render(v) if isinstance(v, str) else v for v in value]
    return value


def required_names(entry: Mapping[str, Any] | None) -> list[str]:
    """Placeholders a caller MUST ground, i.e. those with no declared default.

    This is the list `complete_inputs` should report on: a slot with a declared
    default is not missing, because an honest value for it already exists in the row.
    """
    defaults = declared_defaults(entry)
    template = (entry or {}).get("action_template") or {}
    names: set[str] = set()
    stack: list[Any] = [template]
    while stack:
        cur = stack.pop()
        if isinstance(cur, Mapping):
            stack.extend(cur.values())
        elif isinstance(cur, (list, tuple)):
            stack.extend(cur)
        elif isinstance(cur, str):
            names.update(_PLAIN_RE.findall(DECLARED_DEFAULT_RE.sub("", cur)))
            for m in DECLARED_DEFAULT_RE.finditer(cur):
                if m.group("name") not in defaults:
                    names.add(m.group("name"))
    return sorted(names)


def all_names(entry: Mapping[str, Any] | None) -> list[str]:
    """Every input name the template references, defaulted or not."""
    names: set[str] = set()
    template = (entry or {}).get("action_template") or {}
    stack: list[Any] = [template]
    while stack:
        cur = stack.pop()
        if isinstance(cur, Mapping):
            stack.extend(cur.values())
        elif isinstance(cur, (list, tuple)):
            stack.extend(cur)
        elif isinstance(cur, str):
            names.update(_PLAIN_RE.findall(DECLARED_DEFAULT_RE.sub("", cur)))
            names.update(m.group("name") for m in DECLARED_DEFAULT_RE.finditer(cur))
    return sorted(names)
