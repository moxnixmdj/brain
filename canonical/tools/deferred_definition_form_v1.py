#!/usr/bin/env python3
"""The site was right and both the value and its form were wrong.

WHAT THIS ROUND FOUND, IN ONE PARAGRAPH
---------------------------------------
On a mined fail-to-pass task (pypa/packaging, parent `dec6213e`, the added test
`test_invalid_marker_defers_argument_formatting`) the engine's localiser is not
the problem. It lands on the exact line named by the traceback,
`markers.py:89`, site `__init__:IFEXP_BODY@89:28`, `str(self)`. What fails is
the step after it: `synthesize_candidates_for_witness` emits **0 candidates**
from that witness, and the repair loop reports `candidates_screened 0` in 691ms.
The engine never tries an edit, so it cannot be said to have tried and failed.

WHY ZERO, MEASURED RATHER THAN GUESSED
--------------------------------------
The site's `orig_code` is `str(self)`. The failure substitutes two universal
forms at that exact site, holds everything else fixed, and runs the real test:

    AS_IS (control)                        fail
    str(self) -> super().__str__()         fail
    str(self) -> repr(self)                fail
    hoist the value above the line         fail

All four fail. The fix is not a different *value* for that expression and not a
different *form* of it. It is a different **definition kind**: the attribute must
stop being a value computed at construction time and become a definition
evaluated on access. Two independent spellings of that class both pass:

    deferred @property                      PASS
    functools.cached_property               PASS

The test makes the requirement explicit: it constructs `InvalidMarker(message)`,
*then* sets `message.text`, *then* reads `err.message`. Any eager evaluation is
wrong by construction; no substitution of the eager expression can be right.

THE FORM, STATED BLINDLY
------------------------
This module adds one edit class to the blind vocabulary: **DEFER**. It is
derived from the traceback alone, not from the fix commit:

1. The traceback shows the failure re-entering the class under construction
   (`__init__` -> a method of the same class -> AttributeError on `self`).
2. That means the assigned attribute is computed too early.
3. DEFER turns `self.<name> = <expr>` into a definition evaluated on access, and
   assigns only when the caller supplied a value.

Nothing here knows what a marker, a licence or a message is. The requirement is
read off the failure shape, the interpreter decides whether the edit is right,
and the test file is never modified.

WHAT THIS DOES NOT DO
---------------------
It does not add an emitter for one bug. A form that fires only on this task is
per-example fitting, which V38 measured as the failure mode of the whole
operator set. The form is published with the calibration that decides whether it
belongs: it must fire on tasks that are NOT this one.

Zero model calls, no stored parameters, no network at run time.
"""
from __future__ import annotations

import argparse
import ast
import json
import pathlib
import re
import sys
from typing import Any, Sequence

SCHEMA = "BRAIN_DEFERRED_DEFINITION_FORM_V1"


# ---------------------------------------------------------------------------
# reading the requirement off the failure, not off the fix
# ---------------------------------------------------------------------------
def reentrant_self_failure(traceback_text: str, source_text: str) -> dict[str, Any] | None:
    """Detect an eager attribute computation that re-enters the object's own method.

    Read off the traceback alone, then confirmed against the source line:

        <source>.py:89: in __init__
            self.message: str = str(self) if message is None else message
        ...
            def __str__(self) -> str:
        E   AttributeError: 'X' object has no attribute 'text'

    `__init__` is mid-assignment, computing the value calls a method of the object
    still being constructed, and that method reads an attribute that does not
    exist yet. Two measured facts shaped this detector: the class named in the
    AttributeError is NOT necessarily the class being constructed (here it is a
    class defined inside the test), and pytest prints no `path:line` header at all
    for that inner frame. So the target is located by the `in __init__` frame and
    the class is the one whose `__init__` contains that line.

    Returns facts, or None when the shape is absent.
    """
    if "__init__" not in traceback_text:
        return None
    missing = re.search(
        r"AttributeError: '(\w+)' object has no attribute '(\w+)'", traceback_text
    )
    if not missing:
        return None
    frame = re.search(r"^(\S+\.py):(\d+): in __init__$", traceback_text, flags=re.M)
    if not frame:
        return None
    init_line = int(frame.group(2))
    src_lines = source_text.splitlines()
    if not (1 <= init_line <= len(src_lines)):
        return None
    stmt = src_lines[init_line - 1]
    # Confirm the mechanism against the source: the statement must call a method
    # with this object as the argument (`str(self)`, `self.f()`, `f(self)`), which
    # is what makes evaluation re-entrant.
    calls_self = re.search(r"\(\s*self\s*[,)]", stmt) or re.search(r"self\.\w+\(", stmt)
    if not calls_self:
        return None
    after = traceback_text[frame.end():]
    # The re-entrant method appears in TWO measured spellings depending on pytest's
    # --tb mode: as a `path:line: in <name>` frame, or as source text under the
    # failing statement. Measured: a detector written for only the first spelling
    # scored 0 on all 23 tasks because the harness ran --tb=short. Accept either.
    own_method = (
        re.search(r"^\s*def (\w+)\(self", after, flags=re.M)
        or re.search(r": in (\w+)\n\s*return self\.|: in (\w+)\n\s*return ", after, flags=re.M)
    )
    if not own_method:
        return None
    if missing.group(2) not in traceback_text:
        return None
    return {
        "init_file": frame.group(1),
        "init_line": init_line,
        "init_statement": stmt.strip(),
        "object_class": missing.group(1),
        "missing_attribute": missing.group(2),
        "reentered_method": (own_method.group(1) or own_method.group(2)) if own_method.groups() else own_method.group(1),
        "defers_because": (
            "the attribute is computed inside __init__ by calling a method of the "
            "object being constructed, and that method reads an attribute that "
            "does not exist yet, so any eager evaluation is too early"
        ),
    }


def deferred_definitions(source_text: str, facts: dict[str, Any]) -> list[dict[str, Any]]:
    """Emit DEFER candidates for `self.<name> = <expr>` inside the class.

    One edit class, two spellings, both emitted so the interpreter can decide.
    The assignment is guarded by `is not None` only when the original had a
    conditional, so a plain assignment is not silently changed into a partial one.
    """
    out: list[dict[str, Any]] = []
    try:
        tree = ast.parse(source_text)
    except SyntaxError:
        return out
    lines = source_text.splitlines(keepends=True)
    want_line = int(facts["init_line"])
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        init = next(
            (n for n in node.body if isinstance(n, ast.FunctionDef) and n.name == "__init__"),
            None,
        )
        if init is None:
            continue
        # The class is the one whose __init__ CONTAINS the traceback line.
        if not (init.lineno <= want_line <= (init.end_lineno or init.lineno)):
            continue
        for stmt in init.body:
            # Annotated assignments (`self.x: str = ...`) are the common spelling in
            # typed code and were the reason the first emitter found nothing: the
            # evaluated node is AnnAssign, not Assign.
            if isinstance(stmt, ast.AnnAssign) and stmt.value is not None:
                tgt = stmt.target
            elif isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
                tgt = stmt.targets[0]
            else:
                continue
            if not (
                isinstance(tgt, ast.Attribute)
                and isinstance(tgt.value, ast.Name)
                and tgt.value.id == "self"
            ):
                continue
            attr = tgt.attr
            # Only the attribute on the line the traceback names. Everything else
            # in __init__ is untouched: deferring unrelated attributes is how a
            # blind form turns into a rewrite of the file.
            if stmt.lineno != facts["init_line"]:
                continue
            value_src = "\n".join(
                lines[i].rstrip("\n")
                for i in range(stmt.value.lineno - 1, (stmt.value.end_lineno or stmt.value.lineno))
            )
            # indent-relative rendering, since the span may start mid-line
            raw = ast.get_source_segment(source_text, stmt.value) or value_src.strip()
            # The whole physical line, not `get_source_segment`, which for an
            # AnnAssign returned only the part before the `if` (measured).
            original = lines[stmt.lineno - 1].strip() if stmt.lineno - 1 < len(lines) else ""
            indent = " " * (stmt.col_offset if stmt.col_offset < 64 else 8)
            conditional = isinstance(stmt.value, ast.IfExp)
            supplied = (
                ast.get_source_segment(source_text, stmt.value.orelse)
                if conditional
                else None
            )
            return_expr = (
                "super().__str__()"
                if any(
                    isinstance(c, ast.Call)
                    and isinstance(c.func, ast.Name)
                    and c.func.id in ("str", "repr")
                    for c in ast.walk(stmt.value)
                )
                else raw
            )
            guard = f"{indent}if {supplied} is not None:\n{indent}    self.{attr} = {supplied}\n" if supplied else f"{indent}pass\n"
            # The definition belongs to the CLASS, one indent level out from the
            # body of __init__. Emitting it at the statement's own indent nests it
            # inside __init__, where it is a local function that never becomes a
            # descriptor -- measured, that candidate compiles and changes nothing.
            cls_indent = indent[:-4] if len(indent) >= 4 else ""
            # `functools.cached_property` is used qualified when the module does not
            # already import the name: emitting a bare `@cached_property` compiled
            # but raised NameError at class creation (measured, rc=4).
            already = "from functools import cached_property" in source_text
            for spelling in ("property", "cached_property"):
                deco = spelling if (spelling == "property" or already) else "functools.cached_property"
                # A plain @property has no setter, so the conditional assignment
                # below it raises AttributeError at construction. `cached_property`
                # is a non-data descriptor (instance __dict__ wins), so it accepts
                # that assignment. A plain property therefore needs an explicit
                # setter, emitted only when a guard is present.
                extra = (
                    f"\n{cls_indent}@{attr}.setter\n"
                    f"{cls_indent}def {attr}(self, value: str) -> None:\n"
                    f"{cls_indent}    self.__dict__['{attr}'] = value\n"
                    if (spelling == "property" and supplied)
                    else ""
                )
                prop = (
                    f"\n{cls_indent}@{deco}\n"
                    f"{cls_indent}def {attr}(self) -> str:\n"
                    f"{cls_indent}    return self.__dict__.get({attr!r}, {return_expr})\n"
                )
                out.append(
                    {
                        "attr": attr,
                        "spelling": spelling,
                        "replaces_line": stmt.lineno,
                        "replaces": original,
                        # The definition is appended at the END of the class body.
                        # Emitting it inline ended __init__ early: the statements
                        # after the assignment were absorbed into the new function
                        # body and never ran, which silently dropped every
                        # attribute assigned below the site (measured: `source`
                        # missing, 2 tests failed while the target passed).
                        "append_at_class_end": prop + extra,
                        "with": guard,
                        "derivation": (
                            "replace the eager assignment with a definition "
                            "evaluated on access" + (" and assign only when supplied" if guard else "")
                        ),
                    }
                )
    # cached_property needs the import; property does not.
    for cand in out:
        if cand["spelling"] == "cached_property" and "import functools" not in source_text:
            cand["needs_import"] = "functools"
    return out


def _append_to_class_body(source_text: str, block: str, init_line: int) -> str:
    """Append `block` as the last statement of the class whose __init__ holds `init_line`."""
    try:
        tree = ast.parse(source_text)
    except SyntaxError:
        return source_text
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        init = next(
            (n for n in node.body if isinstance(n, ast.FunctionDef) and n.name == "__init__"),
            None,
        )
        if init is None or not (init.lineno <= init_line <= (init.end_lineno or init.lineno)):
            continue
        last = node.body[-1]
        lines = source_text.splitlines(keepends=True)
        cut = last.end_lineno or last.lineno
        return "".join(lines[:cut]) + block + "".join(lines[cut:])
    return source_text


def apply_candidate(source_text: str, cand: dict[str, Any]) -> str:
    lines = source_text.splitlines(keepends=True)
    idx = cand["replaces_line"] - 1
    if idx < 0 or idx >= len(lines):
        return ""
    lines[idx] = cand["with"]
    out = "".join(lines)
    if cand.get("append_at_class_end"):
        out = _append_to_class_body(out, cand["append_at_class_end"], cand["replaces_line"])
    if cand.get("needs_import") == "functools" and "import functools" not in out:
        out = re.sub(r"(from __future__ import annotations\n)", r"\1\nimport functools\n", out, count=1)
        if "import functools" not in out:
            out = "import functools\n" + out
    return out


# ---------------------------------------------------------------------------
# measurement
# ---------------------------------------------------------------------------
def emit_for_traceback(traceback_text: str, source_text: str) -> dict[str, Any]:
    facts = reentrant_self_failure(traceback_text, source_text)
    if facts is None:
        return {"applies": False, "reason": "TRACEBACK_DOES_NOT_SHOW_REENTRANT_SELF_FAILURE", "candidates": []}
    cands = deferred_definitions(source_text, facts)
    return {
        "applies": bool(cands),
        "facts": facts,
        "candidate_count": len(cands),
        "candidates": cands,
        "reason": "DEFERRED_DEFINITION_CANDIDATES_EMITTED" if cands else "NO_MATCHING_ASSIGNMENT_IN_CLASS",
    }


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--traceback", required=True, help="file holding the pytest traceback text")
    ap.add_argument("--source", required=True, help="the source file the traceback names")
    ap.add_argument("--json", default=None)
    ns = ap.parse_args(argv)
    res = emit_for_traceback(
        pathlib.Path(ns.traceback).read_text(encoding="utf-8", errors="replace"),
        pathlib.Path(ns.source).read_text(encoding="utf-8", errors="replace"),
    )
    payload = {"schema": SCHEMA, "authority": "NONE", **res}
    text = json.dumps(payload, indent=1)
    if ns.json:
        pathlib.Path(ns.json).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
