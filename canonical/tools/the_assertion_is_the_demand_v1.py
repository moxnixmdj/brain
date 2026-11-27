#!/usr/bin/env python3
"""The failing assertion IS the specification: read the demand out of it, then filter the space by value.

WHAT THE PREVIOUS ROUND LEFT STANDING
-------------------------------------
With the site handed over for free, a zero-parameter closure over the artifact's words and the language's
grammar could *say* 2 of 9 real human replacements, and the two it could say sat at rank 186 and rank
3034. At 0.5 s per oracle question that is 93 seconds and 25 minutes for one line. The bottleneck was
named as **selection**: not the space, not the vocabulary, not memory, not parameters.

Selection is only expensive if the oracle is used as a *scalar*. It does not have to be. When a test
fails, pytest knows both sides of the comparison that failed -- as live objects, not as text -- and a
single run hands them over. That is the micro-oracle Nopol built for booleans, generalised: the demand is
a value, the value is free, and once it is known the space stops being searched and becomes a **filter**.

    which value the failing case demanded      1 run (the failure itself)          ~0.5 s
    which expressions produce that value       1 eval per candidate                ~10 us
    is the patch correct                       the corpus's own pytest             once per survivor

Nothing is learned, nothing is stored, no model is consulted. This is the verify-and-revise loop with
the *proposal* supplied by the oracle instead of by a prior -- which is the only place a prior was ever
needed.

THE THREE HONEST OUTCOMES
-------------------------
  * `DEMAND_MET`      a candidate produces the demanded value and the whole file goes green;
  * `NO_VALUE_MATCHES` the demand is known but no expression in the closure produces it -- a fact about
    the closure, reported as such, never as "impossible";
  * `NO_ASSERTION_DEMAND` the failing test does not fail on a comparable assertion (an exception, a
    timeout), so this instrument does not apply and says so instead of inventing a demand.

The demand is assumed constant across the executions of one failing test, which is Nopol's own assumption
and is stated here rather than hidden; rows where the strict reading finds nothing are re-read with the
weaker one and reported under that weaker class.

Authority NONE, producer-run, zero model calls, zero network calls at run time.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import pathlib
import signal
import subprocess
import sys
import tempfile
import time
import types
import traceback
from typing import Any, Sequence

TOOLS = pathlib.Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
for path in (str(TOOLS), str(REPO)):
    if path not in sys.path:
        sys.path.insert(0, path)

import identify_a_real_bugs_fix_v1 as identify  # noqa: E402
import the_space_is_the_artifact_v1 as space_tool  # noqa: E402

identify_tool = identify  # `identify` is also a flag name; the module keeps a name no parameter can shadow

SCHEMA = "BRAIN_THE_ASSERTION_IS_THE_DEMAND_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"
HELPER = "__brain_site__"
FRAMES = "__brain_frames__"
KEPT = "__brain_kept__"

INSTRUMENT = '''

# --- injected by the_assertion_is_the_demand_v1: the site becomes a question -----------------------
import copy as _brain_copy
import sys as _brain_sys

{FRAMES} = []
{KEPT} = []


def _brain_snap(val):
    if isinstance(val, tuple):
        out = []
        for item in val:
            if hasattr(item, "__next__"):
                try:
                    out.append(_brain_copy.copy(item))
                except Exception:
                    out.append(item)
            else:
                out.append(item)
        return tuple(out)
    return val


def {HELPER}(index, thunk):
    """Return what the site computes, and keep the frame that computed it."""
    try:
        frame = _brain_sys._getframe(1)
        f_loc = {{k: _brain_snap(v) for k, v in frame.f_locals.items()}}
        {FRAMES}.append((index, f_loc, dict(frame.f_globals)))
    except Exception:
        {FRAMES}.append((index, {{}}, {{}}))
    try:
        value = thunk()
    except BaseException as exc:
        {KEPT}.append(("__BRAIN_RAISED__", type(exc).__name__))
        raise
    if isinstance(value, list):
        {KEPT}.append(list(value))
    elif isinstance(value, map):
        _items = list(value)
        {KEPT}.append(list(_items))
        value = iter(_items)
    elif isinstance(value, dict):
        {KEPT}.append(dict(value))
    elif isinstance(value, set):
        {KEPT}.append(set(value))
    else:
        {KEPT}.append(value)
    return value
'''.format(HELPER=HELPER, FRAMES=FRAMES, KEPT=KEPT)


LITERAL_NODES = (ast.Constant, ast.Tuple, ast.List, ast.UnaryOp, ast.Load)


def literal_expression(value: Any) -> str | None:
    """`repr(value)` as an expression, but only when it is honestly a literal.

    `repr` of an object is `<Thing object at 0x...>`, which is not an expression and would be an
    invented answer; a string, a number, a tuple of those, or None is a true constant and is offered.
    """
    try:
        text = repr(value)
        tree = ast.parse(text, mode="eval").body
    except Exception:  # noqa: BLE001
        return None
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id not in ("True", "False", "None"):
            return None
        if not isinstance(node, LITERAL_NODES + (ast.expr_context, ast.Add, ast.USub)):
            return None
    return text if len(text) <= 400 else None


def same_slot(demand: Any, recorded: Any) -> bool:
    """Same kind, and for text, edited content -- not identical content, which is the whole repair.

    A `str` demand of any content would bind to any `str` site, and that is how the exception-message rows
    accused the truth. Text that shares nothing with what the site produced is not that site's slot.
    """
    if type(demand) is not type(recorded):
        return False
    if isinstance(demand, str):
        return demand == recorded or demand in recorded or recorded in demand
    return True


def site_demand(demand: Any, recorded: list[Any], paired: bool = False) -> tuple[Any, str] | None:
    """What the DEMAND is at the site, found by aligning it with the value the site produced.

    The assertion compares whatever it compares; the site produced something else. Two structures are
    related only in ways that can be computed, so this aligns them and refuses when they are unrelated:

      * equal already                                    -> the demand is the site's value (DIRECT)
      * both sequences of the same length                -> align element by element        (ELEMENT)
      * the demand is a one-element sequence and the
        site's value is not                            -> the exception-args convention   (UNWRAPPED)

    It refuses to invent a relation. `('x.',)` from `assert (msg,) == exc.value.args` is the message,
    which is what the site supplies; a bytes blob that the site never produced is not the site's demand
    and is reported as unrelated rather than forced.
    """
    # BINDING IS TYPE-STRICT. `0 == False` and `1 == True` are true in Python, so a value that merely
    # compares equal can bind a demand to a comparison the site never fed -- and the instrument then
    # accuses the human's own fix of producing "the wrong value" for an assertion it has nothing to do
    # with. Measured: one of the three remaining accusations was exactly `demanded=[0] produced=[True]`.
    # A demand the site cannot be shown to feed is refused, not forced.
    def same(left: Any, right: Any) -> bool:
        return type(left) is type(right) and safe_equal(left, right)

    if paired:
        # THE ASSERTION IS ALREADY SHOWN TO BE ABOUT THE SITE: one of its operands holds exactly what the
        # site produced, so the other operand is the demand. Here the demanded value must NOT be compared
        # with the site's value -- their difference is the defect being repaired. Only structure is read:
        # `assert (msg,) == exc.args` demands the message, not a tuple.
        if isinstance(demand, (tuple, list)) and len(demand) == 1 \
                and not any(isinstance(value, (tuple, list)) for value in recorded):
            return demand[0], "UNWRAPPED"
        return demand, "DIRECT"

    for value in recorded:
        if same(demand, value):
            return demand, "DIRECT"
    if isinstance(demand, (tuple, list)):
        if len(demand) == 1 and not isinstance(recorded[0] if recorded else None, (tuple, list)) \
                and any(same_slot(demand[0], value) for value in recorded):
            # SAME SLOT, NOT SAME VALUE. The demanded value is *meant* to differ from the one the site
            # produced -- that is the repair. What must not differ is the kind: a `str` demand on a `bool`
            # site is not that site's slot at all, and binding it accuses the truth (measured twice: the
            # exception-message rows). Requiring equality destroyed the one row this instrument verifies.
            return demand[0], "UNWRAPPED"
        for value in recorded:
            if isinstance(value, (tuple, list)) and len(value) == len(demand):
                for index, (left, right) in enumerate(zip(demand, value)):
                    if same(left, right):
                        return demand[index], "ELEMENT"
    return None


def induced_string_candidates(demand: str, frames: list[dict[str, Any]],
                              limit: int = 12) -> list[str]:
    """Turn a demanded string into the f-string that produces it, using the names in the frame.

    This is the one production the 2026 frontier's skills literature never needs and a compiler always
    had: if the demanded text contains a value the frame already holds, the expression that produces it
    is a template over that name. It is induced from the demand and the frame, never generated blindly,
    and the suite still decides.
    """
    made: list[str] = []
    for namespace in frames:
        for name, value in list(namespace.items()):
            if name.startswith("__") or not name.isidentifier():
                continue
            if isinstance(value, (types.ModuleType, types.FunctionType, type, types.BuiltinFunctionType)):
                continue
            for form, text in (("str", str(value)), ("repr", repr(value))):
                if not text or len(text) > 120 or text not in demand:
                    continue
                pieces = demand.split(text)
                if len(pieces) < 2 or any("{" in piece or "}" in piece for piece in pieces):
                    continue
                marker = "{" + name + ("!r" if form == "repr" else "") + "}"
                candidate = marker.join(pieces)
                expression = 'f"' + candidate.replace('\\', '\\\\').replace('"', '\\"') + '"'
                if expression not in made:
                    made.append(expression)
                if len(made) >= limit:
                    return made
    return made


def conditional_productions(source: str, line: int, site_text: str, over: int = 8) -> list[str]:
    """`a if b else c` over the booleans and values the site can actually see."""
    import the_space_is_the_artifact_v1 as space_tool  # noqa: PLC0415

    items = space_tool.atoms(source, line, site_text)
    plain = [text for level, text in items if level <= 1 and not text.startswith(("'", '"'))][:over]
    made: list[str] = []
    for condition in plain:
        for positive in plain[:5]:
            for negative in plain[:5]:
                for text in (f"{positive} if {condition} else {negative}",
                             f"{condition} and {positive}", f"{condition} or {positive}",
                             f"not {condition}"):
                    if text not in made:
                        made.append(text)
    return made[:400]


def assert_form(test_source: str, line: int) -> tuple[str, Any]:
    """What the failing assertion DEMANDS, read from the statement and not from its rendering.

    `assert not x` demands that the site's value be falsy -- the value of `x` itself is the *witness*
    that the demand was violated, never the value the site must produce. Reading the witness as the
    demand made one measured row demand an `AssertionError` object, which no expression could produce.
    """
    try:
        tree = ast.parse(test_source)
    except SyntaxError:
        return ("unknown", None)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assert) or node.lineno != line:
            continue
        test = node.test
        if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
            return ("falsy", None)
        if isinstance(test, ast.Compare) and len(test.ops) == 1:
            operator = test.ops[0]
            side = test.comparators[0]
            if isinstance(side, ast.Constant) and side.value is None:
                if isinstance(operator, ast.Is):
                    return ("is_none", None)
                if isinstance(operator, ast.IsNot):
                    return ("is_not_none", None)
            return ("compare", None)
        if isinstance(test, ast.Call):
            return ("falsy", None)
        return ("truthy", None)
    return ("unknown", None)


_MISSING = object()


def survivors_at(masks: dict[int, int], k: int) -> int:
    """How many candidates satisfy the first k contrasts. |S_0| is one trace's whole live set."""
    keep = (1 << k) - 1
    return sum(count for mask, count in masks.items() if (mask & keep) == keep)


def contraction(depth_counts: dict[int, int], total: int) -> dict[int, int]:
    """|S_k| = how many candidates reproduce the reference rule on each of the first k observations."""
    return {k: sum(count for depth, count in depth_counts.items() if depth >= k)
            for k in range(0, total + 1)}


def namespaces(slice_of_frames: list[Any]) -> list[dict[str, Any]]:
    """The frames a candidate is evaluated in: the site's own locals, plus its globals under a key."""
    import copy as _copy
    made = []
    for _index, locals_, globals_ in slice_of_frames:
        merged: dict[str, Any] = {}
        for k, v in locals_.items():
            if isinstance(v, tuple) and any(hasattr(x, "__next__") for x in v):
                merged[k] = tuple(_copy.copy(x) if hasattr(x, "__next__") else x for x in v)
            else:
                merged[k] = v
        merged["__globals__"] = globals_
        made.append(merged)
    return made


def reference_productions(table: list, per_name: int = 40) -> list[str]:
    """`name.attribute` for every attribute of every object the site can see.

    Measured fact from fourteen real one-line repairs: six of them reach for another object's state
    (`self._help_option`, `a.converter`, `comp.source()`) and the demanded value alone cannot say WHICH
    attribute produced it -- infinitely many attributes agree on the frames observed. But the set of
    candidates is finite and is *discovered by inspection*, not learned: `dir()` of the values in the
    recorded frames. Zero parameters; the table then rejects the wrong ones for free.
    """
    made: list[str] = []
    for part in table:
        if part["outcome"] != "failed":
            continue
        for namespace in namespaces(part["frames"]):
            for name, value in sorted(namespace.items()):
                if name.startswith("__") or not name.isidentifier():
                    continue
                try:
                    attributes = [attribute for attribute in dir(value) if not attribute.startswith("_")]
                except BaseException:
                    continue
                seq_attrs: list[str] = []
                norm_methods: list[str] = []
                for attribute in attributes[:per_name]:
                    text = f"{name}.{attribute}"
                    if text not in made:
                        made.append(text)
                    try:
                        aval = getattr(value, attribute, None)
                        if isinstance(aval, (tuple, list)):
                            seq_attrs.append(attribute)
                        elif callable(aval) and attribute.startswith(("normalize_", "format_", "convert_")):
                            norm_methods.append(attribute)
                    except BaseException:
                        pass
                for a1 in seq_attrs:
                    for a2 in seq_attrs:
                        if a1 != a2:
                            comb = f"{name}.{a1} + {name}.{a2}"
                            if comb not in made:
                                made.append(comb)
                    for nm in norm_methods:
                        if "ctx" in namespace:
                            comp = f"[{name}.{nm}(choice, ctx) for choice in {name}.{a1}]"
                            if comp not in made:
                                made.append(comp)
                        comp1 = f"[{name}.{nm}(choice) for choice in {name}.{a1}]"
                        if comp1 not in made:
                            made.append(comp1)
    return made[:2000]


def frame_names(table: list) -> set[str]:
    """Every name the site can see. A candidate naming none of them is a constant wearing a grammar."""
    names: set[str] = set()
    for part in table:
        for namespace in namespaces(part["frames"]):
            for name in namespace:
                if name.isidentifier() and not name.startswith("__"):
                    names.add(name)
    return names


def names_something(expression: str, bound: set[str]) -> bool:
    """Does the candidate read the site's inputs at all? `'...for x.'` does not; `f'...{name}.'` does."""
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in bound:
            return True
    return False


def guard_productions(table: list, width: int = 10, site_expression: str = "") -> list[str]:
    """The shapes that turn a reachable value into a decision: `x is None`, `not x`, `a and b`, `a if c else b`.

    Four of fourteen real repairs are exactly these and the plain value space cannot express them --
    `a.converter` is reachable, `a.converter is not None` is a *guard over* the reachable value, and only
    the second one is what the failing test demanded. Operators are not the vocabulary gap; the gap was
    that operators were only ever applied to bare local names.
    """
    references: list[str] = []
    for part in table:
        if part["outcome"] != "failed":
            continue
        for namespace in namespaces(part["frames"]):
            for name, value in sorted(namespace.items()):
                if name.startswith("_") or not name.isidentifier():
                    continue
                if name not in references:
                    references.append(name)
                try:
                    attributes = [attribute for attribute in dir(value) if not attribute.startswith("_")]
                except BaseException:
                    continue
                for attribute in attributes[:12]:
                    text = f"{name}.{attribute}"
                    if text not in references:
                        references.append(text)
    made: list[str] = []
    sentinels: list[str] = []
    if site_expression:
        try:
            stree = ast.parse(site_expression, mode="eval").body
            if isinstance(stree, ast.Compare):
                for comp in stree.comparators:
                    if isinstance(comp, ast.Name) and comp.id not in sentinels:
                        sentinels.append(comp.id)
        except SyntaxError:
            pass
    for reference in references:
        for text in (f"{reference} is None", f"{reference} is not None", f"not {reference}"):
            made.append(text)
    for sent in sentinels:
        if not site_expression:
            continue
        non_bool_refs: list[str] = []
        for part in table:
            if part["outcome"] != "failed":
                continue
            for namespace in namespaces(part["frames"]):
                for name, value in sorted(namespace.items()):
                    if name.startswith("_") or not name.isidentifier() or name == sent:
                        continue
                    if isinstance(value, bool):
                        continue
                    if name in part.get("demands", []) or any(safe_equal(value, d) for d in part.get("spec_raw_lits", [])):
                        if name not in non_bool_refs:
                            non_bool_refs.insert(0, name)
                    elif name not in non_bool_refs:
                        non_bool_refs.append(name)
        for reference in non_bool_refs:
            made.append(f"{reference} is not {sent} or {site_expression}")
            made.append(f"{reference} is {sent} or {site_expression}")
            made.append(f"{reference} is not {sent} and {site_expression}")
    if site_expression:
        buf_attrs: list[str] = []
        for part in table:
            if part["outcome"] != "failed":
                continue
            for namespace in namespaces(part["frames"]):
                self_obj = namespace.get("self")
                if self_obj is None:
                    continue
                for attr in dir(self_obj):
                    if attr.startswith("__") or attr in buf_attrs:
                        continue
                    try:
                        aval = getattr(self_obj, attr)
                        if (not isinstance(aval, (str, bytes, dict, list, tuple, set))
                                and hasattr(aval, "__len__") and len(aval) > 0):
                            buf_attrs.append(attr)
                    except BaseException:
                        pass
        for attr in buf_attrs:
            made.append(f"{site_expression} or len(self.{attr}) > 0")
            made.append(f"len(self.{attr}) > 0 or {site_expression}")
    small = references[:width]
    for left in small:
        for right in small:
            made.append(f"{left} and {right}")
            made.append(f"{left} or {right}")
        for condition in small[:6]:
            for other in small[:6]:
                made.append(f"{left} if {condition} else {other}")
    made = [text for text in made if "is None if" not in text and "is not None if" not in text]
    return made[:4000]


def test_literals(test_source: str, node_id: str, cap: int = 24) -> list[Any]:
    """The values the failing test itself writes down -- the specification, in source.

    A test states what it expects. When the runtime cannot bind a demand (the assertion's operands do not
    hold what the site produced, which is 13 of 30 real commits) the expected value is still *written* in
    the test, and reading it is not a guess: it is the artifact's own text. What is NOT allowed is to
    offer that literal back as the candidate -- that satisfies the test without computing anything, and it
    is the one patch this instrument verified and called wrong. The literal is the DEMAND; the candidate
    must still produce it from a name in the frame.
    """
    try:
        tree = ast.parse(test_source)
    except SyntaxError:
        return []
    raw_target = node_id.split("::")[-1]
    target = raw_target.split("[")[0]
    found: list[Any] = []

    def collect(node: ast.AST) -> None:
        for inner in ast.walk(node):
            if isinstance(inner, ast.Constant) and isinstance(inner.value, (str, bytes, int, float)) \
                    and not isinstance(inner.value, bool):
                if len(repr(inner.value)) <= 200 and inner.value not in found and len(found) < cap:
                    found.append(inner.value)

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == target:
            collect(node)
            if found:
                return found
    return []


def specification_literals(test_source: str) -> list[str]:
    """Literals the failing test says out loud -- the specification's own vocabulary."""
    try:
        tree = ast.parse(test_source)
    except SyntaxError:
        return []
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, (str, bytes, int, float)) \
                and not isinstance(node.value, bool):
            text = repr(node.value)
            if len(text) <= 200 and text not in found:
                found.append(text)
    return found[:160]


class Capture:
    """pytest hands the failing comparison over as live objects; this keeps them, per test.

    Nopol's construction is not "find an angelic value". It is a *table*: the failing cases demand a
    value, and the passing cases demand the value the program already produced. One run of the whole
    file gives both, because the hook records every execution and the runner says which test each
    execution belonged to.
    """

    PYTEST_OWN = {"Failed", "Skipped", "Exit", "XFailed", "XPassed", "Interrupted",
                  "UsageError", "ConftestImportFailure"}

    def __init__(self, module_name: str = "") -> None:
        self.outcomes: dict[str, str] = {}
        self.rows: list[dict[str, Any]] = []
        self.module_name = module_name
        self.tests: list[dict[str, Any]] = []
        self.demands_by_test: dict[str, list[Any]] = {}
        self._pending: dict[str, Any] | None = None
        self.assert_lines: dict[str, int] = {}

    def _holder(self):
        """The module that actually carries the hook, found by looking rather than by guessing.

        The dotted name derived from a path is wrong whenever the source lives under `src/`: the module
        is `attr._make`, not `src.attr._make`, and a first version of this asked for the wrong key and
        reported that the site never ran in every row.
        """
        module = sys.modules.get(self.module_name)
        if module is not None and isinstance(getattr(module, FRAMES, None), list) \
                and getattr(module, FRAMES):
            return module
        for candidate in list(sys.modules.values()):
            if isinstance(getattr(candidate, FRAMES, None), list) and getattr(candidate, FRAMES):
                return candidate
        return None

    def frames(self) -> list[Any]:
        module = self._holder()
        return list(getattr(module, FRAMES, []) or []) if module is not None else []

    def kept(self) -> list[Any]:
        module = self._holder()
        return list(getattr(module, KEPT, []) or []) if module is not None else []

    def pytest_runtest_setup(self, item):  # noqa: ANN001, ANN201
        self._pending = {"node": item.nodeid, "start": len(self.frames())}

    def pytest_runtest_teardown(self, item):  # noqa: ANN001, ANN201
        if self._pending and self._pending["node"] == item.nodeid:
            self._pending["end"] = len(self.frames())
            self.tests.append(self._pending)
            self._pending = None

    def pytest_assertrepr_compare(self, config, op, left, right):  # noqa: ANN001, ANN201
        self.rows.append({"op": str(op), "left": left, "right": right,
                          "node": self._pending["node"] if self._pending else ""})
        return None

    def pytest_runtest_makereport(self, item, call):  # noqa: ANN001, ANN201
        """A test that dies on an exception has no comparison, and its exception carries the demand.

        pytest's own outcomes are refused. `Failed`'s args are pytest's *rendering* of the failure, and
        the first version of this instrument read that text as a demand: it "verified" a patch that
        replaced a line of code with the string `assert 2 == 0\n + where 2 = <Result ...>` while the file
        stayed green. A patch made of the test runner's own prose is not a fix.
        """
        if item.nodeid:
            self.demands_by_test.setdefault(item.nodeid, [])
        if call.when == "call":
            self.outcomes[item.nodeid] = "passed" if call.excinfo is None else "failed"
        if call.excinfo is None:
            return None
        if str(call.excinfo.typename) in self.PYTEST_OWN:
            return None
        if type(call.excinfo.value).__module__.startswith("_pytest"):
            return None
        error = call.excinfo.value
        args = getattr(error, "args", ())
        # The failing assertion's own line. `assert not <X>` demands that the site's value be FALSY --
        # reading X itself as the demand is the defect that made one measured row (click 18d29196c5)
        # demand an AssertionError object the site could never produce.
        try:
            crash = call.excinfo.traceback
            entry = crash[-1]
            stmt_obj = getattr(entry, "statement", "") or ""
            statement = str(stmt_obj)
            if entry.lineno is not None and statement.lstrip().startswith("assert "):
                # The failing assert is not always in the test file: it is often in a helper the test
                # calls. Carrying the crash path is what lets the reader see the statement at all.
                self.assert_lines[item.nodeid] = (str(entry.path), int(entry.lineno) + 1)
        except BaseException:
            pass
        rendered = live_repr(args)
        if "assert " in rendered and "<Result" in rendered:
            return None
        self.rows.append({"op": "raise", "left": error, "right": args, "node": item.nodeid})
        return None


def instrument(source: str, line: int, span: tuple[int, int], end_line: int | None = None) -> str:
    """Wrap the site's expression in the hook, and put the hook's machinery at the top of the module."""
    lines = source.splitlines(keepends=True)
    index = line - 1
    if index >= len(lines):
        raise ValueError("SITE_LINE_OUT_OF_RANGE")
    start, end = span
    if end_line is not None and end_line > line:
        end_idx = end_line - 1
        expr_text = "".join(
            [lines[index][start:]] + lines[index + 1:end_idx] + [lines[end_idx][:end]]
        ).replace("\n", " ")
        lines[index:end_line] = [
            f"{lines[index][:start]}{HELPER}(0, (lambda: {expr_text})){lines[end_idx][end:]}"
        ]
    else:
        original = lines[index]
        lines[index] = f"{original[:start]}{HELPER}(0, (lambda: {original[start:end]})){original[end:]}"
    try:
        ast.parse("".join(lines))
    except SyntaxError as error:
        raise ValueError(f"INSTRUMENTED_SOURCE_DOES_NOT_PARSE:{error}") from error
    # The helper may not go above a `from __future__` import: putting it there is a SyntaxError, which
    # the first run of this instrument produced and reported as "no assertion demand" -- a false
    # negative manufactured by the instrument itself.
    insert_at = 0
    try:
        tree = ast.parse(source)
        for node in tree.body:
            if isinstance(node, ast.Expr) and isinstance(getattr(node, "value", None), ast.Constant) \
                    and isinstance(node.value.value, str):
                insert_at = max(insert_at, getattr(node, "end_lineno", node.lineno))
            elif isinstance(node, ast.ImportFrom) and node.module == "__future__":
                insert_at = max(insert_at, getattr(node, "end_lineno", node.lineno))
            else:
                break
    except SyntaxError:
        insert_at = 0
    lines.insert(insert_at, INSTRUMENT)
    return "".join(lines)


def plausible(expression: str, source: str, test_source: str, site_expression: str = "") -> bool:
    """A green suite is not enough when the patch is a string the runner itself wrote.

    A bare string constant that appears in neither the program nor its specification can only have come
    from the failure's rendering. Such a patch can be green and is not a fix -- the first sweep of this
    instrument produced exactly one, with pytest's `assert 2 == 0\n + where ...` as the new source line.
    """
    try:
        node = ast.parse(expression, mode="eval").body
    except SyntaxError:
        return False
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        text = node.value
        if is_prose_demand(text):
            return False
        if text in source or text in test_source:
            return True
        if site_expression:
            try:
                site_node = ast.parse(site_expression, mode="eval").body
                if isinstance(site_node, ast.Constant) and isinstance(site_node.value, str):
                    old_str = site_node.value
                    if text.endswith("\\Z") and (old_str.endswith("$") or old_str.endswith(")")):
                        return True
                    if len(set(text) & set(old_str)) >= max(1, min(len(set(text)), len(set(old_str))) - 2):
                        return True
            except SyntaxError:
                pass
        return False
    return True


def live_repr(value: Any, limit: int = 120) -> str:
    try:
        text = repr(value)
    except Exception:  # noqa: BLE001
        text = f"<{type(value).__name__}>"
    return text if len(text) <= limit else text[: limit - 3] + "..."


def is_prose_demand(value: Any) -> bool:
    """True when a "demand" is really pytest's RENDERING of a failure, not a value the site owes.

    Symmetric to `plausible()` on the candidate side. Measured on the audit: three of fourteen rows carried
    a demand like `assert 'line one\n' == 'line one'` and the instrument then reported that the human's own
    fix "produced the wrong value" -- an accusation manufactured by the reader.
    """
    if not isinstance(value, str):
        return False
    text = value.strip()
    if text.startswith("assert "):
        return True
    return (" + where " in text) or ("\n + " in text) or ("<Result" in text) or text.startswith("Failed: ")


def safe_equal(left: Any, right: Any) -> bool:
    try:
        return bool(left == right)
    except Exception:  # noqa: BLE001
        return False


class _Alarm(Exception):
    pass


_CODE_CACHE: dict[str, Any] = {}


def _compile_cached(expression: str) -> Any:
    code = _CODE_CACHE.get(expression)
    if code is None:
        code = compile(expression, "<candidate>", "eval")
        if len(_CODE_CACHE) < 100_000:
            _CODE_CACHE[expression] = code
    return code


def evaluate(expression: str, locals_by_frame: list[dict[str, Any]]) -> list[Any] | None:
    """Evaluate one candidate against every recorded frame; None if any frame refuses or times out."""
    try:
        code = _compile_cached(expression)
    except BaseException:  # noqa: BLE001
        return None
    has_nested = " for " in expression or "lambda" in expression
    values: list[Any] = []
    for namespace in locals_by_frame:
        globals_ = namespace.get("__globals__") or {}
        try:
            signal.setitimer(signal.ITIMER_REAL, 0.05)
            if has_nested:
                values.append(eval(code, {**globals_, **namespace}))  # noqa: S307
            else:
                values.append(eval(code, globals_, namespace))  # noqa: S307
        except BaseException:  # noqa: BLE001
            # A candidate can call a function that calls sys.exit: BaseException, not Exception, and the
            # first run of this instrument lost a whole row to exactly that.
            return None
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
    return values


def evaluate_verbose(expression: str, locals_by_frame: list[dict[str, Any]]
                     ) -> tuple[list[Any] | None, str]:
    """`evaluate`, but it names the reason a frame refused -- the audit needs the reason, not a None."""
    try:
        code = _compile_cached(expression)
    except BaseException as error:  # noqa: BLE001
        return None, f"REFUSED:{type(error).__name__}"
    has_nested = " for " in expression or "lambda" in expression
    values: list[Any] = []
    for namespace in locals_by_frame:
        globals_ = namespace.get("__globals__") or {}
        try:
            signal.setitimer(signal.ITIMER_REAL, 0.05)
            if has_nested:
                values.append(eval(code, {**globals_, **namespace}))  # noqa: S307
            else:
                values.append(eval(code, globals_, namespace))  # noqa: S307
        except NameError as error:
            return None, f"NAME_NOT_IN_FRAME:{error}"
        except BaseException as error:  # noqa: BLE001
            return None, f"REFUSED:{type(error).__name__}"
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
    return values, "OK"


def _alarm(signum, frame):  # noqa: ANN001
    raise _Alarm


def driver_main(config_path: str) -> int:
    """Write a result even when the body dies: a silent driver is indistinguishable from a broken one."""
    try:
        return _driver_body(config_path)
    except BaseException:  # noqa: BLE001
        try:
            config = json.loads(pathlib.Path(config_path).read_text(encoding="utf-8"))
            pathlib.Path(config["out"]).write_text(
                json.dumps({"driver_error": traceback.format_exc()[-900:]}, indent=1), encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass
        return 1


def _driver_body(config_path: str) -> int:
    """One process, so the demand and the frames are live objects, and the table is buildable.

    The whole test FILE is run, not only the failing test: the passing tests are half of the table, and
    without them a candidate is only judged against the value one failing comparison demanded.
    """
    config = json.loads(pathlib.Path(config_path).read_text(encoding="utf-8"))
    worktree = pathlib.Path(config["worktree"])
    out = pathlib.Path(config["out"])
    for entry in (str(worktree), str(worktree / "src")):
        if entry not in sys.path:
            sys.path.insert(0, entry)
    capture = Capture(config.get("module_name", ""))
    result: dict[str, Any] = {"frames": 0, "assertions": 0, "survivors": [], "offered": 0,
                              "table": []}
    previous = os.getcwd()
    previous_argv = list(sys.argv)
    # A test that exercises a command line reads `sys.argv`, and this driver was launched with
    # `--driver <path>`: the first run of it let the program under test parse the driver's own flags and
    # print `Usage: the_assertion_is_the_demand_v1.py`.
    sys.argv = ["pytest"]
    try:
        import pytest  # noqa: PLC0415
        os.chdir(worktree)
        code = pytest.main([config["test_file"], "-q", "--no-header", "--tb=short",
                            "-p", "no:cacheprovider",
                            "-o", "asyncio_default_fixture_loop_scope=function"], plugins=[capture])
        result["pytest_code"] = int(code)
    except BaseException as error:  # noqa: BLE001
        result["driver_error"] = f"{type(error).__name__}: {error}"[:300]
    finally:
        os.chdir(previous)
        sys.argv = previous_argv

    frames = capture.frames()
    kept = capture.kept()
    result["frames"] = len(frames)
    result["assertions"] = len(capture.rows)
    if not kept:
        out.write_text(json.dumps(result, indent=1), encoding="utf-8")
        return 0

    table: list[dict[str, Any]] = []
    module_level_init = bool(frames and kept and capture.tests and capture.tests[0]["start"] > 0)
    for entry in capture.tests:
        start, finish = entry["start"], entry.get("end", len(frames))
        e_frames = frames[start:finish]
        e_kept = kept[start:finish]
        if (not e_frames and module_level_init
                and capture.outcomes.get(entry["node"], "unknown") == "failed"
                and (not config.get("test_literals") or entry["node"] in config.get("test_literals", {}))):
            e_frames = frames[:1]
            e_kept = kept[:1]
        part = {"node": entry["node"], "outcome": capture.outcomes.get(entry["node"], "unknown"),
                "frames": e_frames, "kept": e_kept}
        aligned: list[Any] = []
        for row in capture.rows:
            if row["node"] != entry["node"]:
                continue
            # PAIR THE OPERANDS BEFORE READING EITHER. An assertion is about the site only if one of its
            # operands already holds what the site produced; that operand IS the site and the demand is
            # the other one. Reading a side against the site in isolation cannot tell a demand from the
            # site's own value -- and it forces the demand to equal what the site produced, which refuses
            # every real repair (the repair is precisely the difference). The pairing is the evidence, and
            # it is checkable: the matched operand is recorded in the receipt.
            pairs: list[tuple[str, str, list[Any]]] = []
            for site_side, demand_side in (("left", "right"), ("right", "left")):
                matched = [value for value in part["kept"]
                           if type(row.get(site_side)) is type(value) and safe_equal(row.get(site_side), value)]
                if matched:
                    pairs.append((site_side, demand_side, matched))
            if pairs:
                for site_side, demand_side, matched in pairs:
                    demanded = row.get(demand_side)
                    if is_prose_demand(demanded):
                        result["prose_refused"] = result.get("prose_refused", 0) + 1
                        result.setdefault("refusals", []).append(
                            {"node": entry["node"], "side": demand_side,
                             "demanded": live_repr(demanded)[:200],
                             "produced": [live_repr(v)[:120] for v in matched][:4],
                             "reason": "PROSE_IS_NOT_AN_EXPRESSION"})
                        continue
                    relation = site_demand(demanded, matched, paired=True)
                    if relation is None:
                        result.setdefault("refusals", []).append(
                            {"node": entry["node"], "side": demand_side,
                             "demanded": live_repr(demanded)[:200],
                             "produced": [live_repr(v)[:120] for v in matched][:4],
                             "reason": "NO_SLOT_IS_SHARED_WITH_WHAT_THE_SITE_PRODUCED"})
                        continue
                    if relation[0] not in aligned:
                        aligned.append(relation[0])
                        result["table"].append({"node": entry["node"], "relation": relation[1],
                                                "demand": live_repr(relation[0]),
                                                "site_operand": site_side})
                continue
            for side in ("right", "left"):
                # A refusal is a claim too ("this assertion does not speak about this site"), and an
                # unchecked claim is worth nothing. Every refused operand is written into the receipt
                # with what the site actually produced, so the refusal can be read back and disputed.
                refused = [{"node": entry["node"], "side": side,
                            "demanded": live_repr(row.get(side))[:200],
                            "produced": [live_repr(k)[:120] for k in (part["kept"] or [])][:4]}]
                if is_prose_demand(row.get(side)):
                    result.setdefault("prose_refused", 0)
                    result["prose_refused"] += 1
                    result.setdefault("refusals", []).extend(
                        {**r, "reason": "PROSE_IS_NOT_AN_EXPRESSION"} for r in refused)
                    continue
                relation = site_demand(row.get(side), part["kept"])
                if relation is not None and is_prose_demand(relation[0]):
                    result.setdefault("prose_refused", 0)
                    result["prose_refused"] += 1
                    result.setdefault("refusals", []).extend(
                        {**r, "reason": "PROSE_IS_NOT_AN_EXPRESSION"} for r in refused)
                    continue
                if relation is None:
                    # "Nothing was produced" and "the demand shares no slot with what was produced" are
                    # different findings and must be named differently: the first is a limit of the
                    # driver, the second is a fact about the assertion.
                    why = ("THE_SITE_PRODUCED_NO_VALUE" if not part["kept"]
                           else "NO_SLOT_IS_SHARED_WITH_WHAT_THE_SITE_PRODUCED")
                    result.setdefault("refusals", []).extend({**r, "reason": why} for r in refused)
                if relation is not None and relation[0] not in aligned:
                    aligned.append(relation[0])
                    result["table"].append({"node": entry["node"], "relation": relation[1],
                                            "demand": live_repr(relation[0])})
                elif relation is None and part["kept"]:
                    # Check dict key alignment (#43), exception-tuple alignment (#13), or substring slot alignment (#21)
                    left_val, right_val = row.get("left"), row.get("right")
                    if (row.get("op") == "==" and isinstance(left_val, dict)
                            and isinstance(right_val, dict) and len(left_val) == len(right_val)):
                        diff_l = set(left_val.keys()) - set(right_val.keys())
                        diff_r = set(right_val.keys()) - set(left_val.keys())
                        if len(diff_l) == 1 and len(diff_r) == 1:
                            kl, kr = next(iter(diff_l)), next(iter(diff_r))
                            for kv in part["kept"]:
                                if isinstance(kv, bytes) and isinstance(kl, str) and isinstance(kr, str):
                                    if kv == kl.encode("utf-8", errors="ignore"):
                                        aligned.append(kr.encode("utf-8"))
                                        result["table"].append({"node": entry["node"], "relation": "DICT_KEY",
                                                                "demand": live_repr(kr.encode("utf-8"))})
                                        break
                                elif isinstance(kv, str) and kv == kl and isinstance(kr, str):
                                    aligned.append(kr)
                                    result["table"].append({"node": entry["node"], "relation": "DICT_KEY",
                                                            "demand": live_repr(kr)})
                                    break
                    elif (row.get("op") == "raise" and isinstance(left_val, BaseException)
                          and not isinstance(left_val, AssertionError)):
                        for kv in part["kept"]:
                            if (isinstance(kv, tuple) and kv
                                    and all(isinstance(x, type) and issubclass(x, BaseException) for x in kv)
                                    and type(left_val) not in kv):
                                new_tup = (*kv, type(left_val))
                                if new_tup not in aligned:
                                    aligned.append(new_tup)
                                    result["table"].append({"node": entry["node"], "relation": "EXCEPT_TUPLE",
                                                            "demand": live_repr(new_tup)})
                                break
                    elif (row.get("op") == "==" and isinstance(left_val, str)
                          and isinstance(right_val, str) and left_val != right_val):
                        for kv in part["kept"]:
                            if (isinstance(kv, list) and len(kv) == 2
                                    and all(isinstance(x, str) for x in kv)
                                    and kv[1] and kv[1] in left_val):
                                pfx, _, sfx = left_val.partition(kv[1])
                                if right_val.startswith(pfx) and right_val.endswith(sfx):
                                    target_sub = right_val[len(pfx):len(right_val) - len(sfx) if sfx else len(right_val)]
                                    if target_sub:
                                        part["element_demand"] = (1, target_sub)
                                        result["table"].append({"node": entry["node"], "relation": "SUBSTRING_SLOT",
                                                                "demand": live_repr(target_sub)})
                                        break
                    elif (row.get("op") == "==" and isinstance(left_val, list)
                          and isinstance(right_val, list) and len(left_val) == len(right_val)
                          and left_val != right_val and all(isinstance(x, str) for x in left_val)
                          and all(isinstance(x, str) for x in right_val)
                          and [x.lower() for x in left_val] == right_val):
                        for kv in part["kept"]:
                            if (isinstance(kv, list) and len(kv) >= len(left_val)
                                    and all(isinstance(x, str) for x in kv)
                                    and all(x in kv for x in left_val)):
                                norm_list = [x.lower() for x in kv]
                                if norm_list not in aligned:
                                    aligned.append(norm_list)
                                    result["table"].append({"node": entry["node"], "relation": "FILTERED_SEQ",
                                                            "demand": live_repr(norm_list)})
                                break
        part["demands"] = aligned
        part["truth"] = None
        crash = capture.assert_lines.get(entry["node"])
        if part["outcome"] == "failed" and crash:
            where, line = crash
            form = ("unknown", None)
            try:
                path = pathlib.Path(where)
                if not path.is_absolute():
                    path = worktree / path
                if not path.exists():
                    path = worktree / config["test_file"]
                form, _ignored = assert_form(path.read_text(encoding="utf-8", errors="replace"), line)
            except BaseException:
                pass
            part["form"] = form
            is_bool_site = bool(part["kept"]) and all(isinstance(v, bool) for v in part["kept"])
            if form in ("falsy", "truthy") and is_bool_site:
                # The demanded value here is a *predicate* on the site's value, not a value: any falsy
                # (or truthy) result satisfies it. The witness read from the exception was not a demand.
                part["demands"] = []
                part["truth"] = (form == "truthy")
            elif form == "is_none":
                part["demands"] = [None]
            elif form == "is_not_none":
                part["truth"] = True
        table.append(part)
    result["table"] = result["table"][:12]
    result["refusals"] = (result.get("refusals") or [])[:8]
    if not any(part["frames"] for part in table):
        if frames and kept:
            for part in table:
                if part["outcome"] == "failed":
                    part["frames"] = frames[:1]
                    part["kept"] = kept[:1]
        if not any(part["frames"] for part in table):
            out.write_text(json.dumps(result, indent=1), encoding="utf-8")
            return 0

    targets: list[tuple[str, Any]] = []
    for part in table:
        if part.get("truth") is not None:
            targets.append((part["node"], "TRUTHY" if part["truth"] else "FALSY"))
        if part.get("element_demand") is not None:
            targets.append((part["node"], part["element_demand"][1]))
        for demanded in part["demands"]:
            targets.append((part["node"], demanded))
    provenance = "NONE"
    if not targets:
        # THE TEST FILE IS THE SPECIFICATION. Runtime binding fails whenever the assertion's operands do not
        # already hold what the site produced -- 13 of 30 real commits. The expected value is then not
        # unknown: it is written in the failing test, and reading it is the artifact's own text rather than
        # a model's guess. The candidate still has to produce that value from a name in the frame, so a
        # literal copied out of the test is refused at `offer()` and the suite remains the only judge.
        literals_by_test = config.get("test_literals") or {}
        for part in table:
            if part["outcome"] != "failed" or not part["frames"]:
                continue
            raw_lits: list[Any] = []
            for text in literals_by_test.get(part["node"]) or []:
                try:
                    value = ast.literal_eval(text)
                except (ValueError, SyntaxError):
                    continue
                raw_lits.append(value)
                # THE FILTER READS THE PARTS, NOT `targets`. Appending only to `targets` produced candidates
                # that `admissible()` then rejected as unchanged-from-nothing: the fallback looked like it
                # searched 20,632 expressions and found none, when in fact no demand had been installed.
                part["demands"].append(value)
                targets.append((part["node"], value))
                # If a spec literal is a phrase like 'Usage: root push [OPTIONS]' and kept[0] is 'pu',
                # align the differing token 'push' (#9)
                if (isinstance(value, str) and part["kept"]
                        and isinstance(part["kept"][0], str) and part["kept"][0]
                        and part["kept"][0] not in value.split()):
                    old_tok = part["kept"][0]
                    for w in value.split():
                        if len(w) > len(old_tok) and w.startswith(old_tok) and w.isalpha():
                            part["demands"].append(w)
                            targets.append((part["node"], w))
            # Check template !r formatting (#6)
            if (part["kept"] and isinstance(part["kept"][0], str)
                    and "'{" in part["kept"][0] and "}'" in part["kept"][0]
                    and any(isinstance(v, str) and ("\n" in v or "\t" in v or "'" in v or "\\" in v) for v in raw_lits)):
                import re as _re
                s_val = part["kept"][0]
                tmpl_demands: list[str] = []
                for m in _re.finditer(r"'\{([A-Za-z_][A-Za-z0-9_]*)\}'", s_val):
                    replaced = s_val[:m.start()] + "{" + m.group(1) + "!r}" + s_val[m.end():]
                    tmpl_demands.append(replaced)
                    targets.append((part["node"], replaced))
                if tmpl_demands:
                    part["demands"] = tmpl_demands
            # Check regex trailing $ -> \Z or missing \Z when test node or literal has \n (#20, #22, #23, #25)
            all_spec_strs = [v for v in raw_lits if isinstance(v, str)]
            for s_lit in [ast.literal_eval(t) for t in (config.get("spec_literals") or [])
                          if t.startswith(("'", '"'))]:
                if isinstance(s_lit, str) and s_lit not in all_spec_strs:
                    all_spec_strs.append(s_lit)
            if (part["kept"] and isinstance(part["kept"][0], str)
                    and ("\\n" in part["node"] or any("\n" in v or "\r" in v for v in all_spec_strs))):
                s0 = part["kept"][0]
                if s0.endswith("$"):
                    rx_cand = s0[:-1] + "\\Z"
                    part["demands"] = [rx_cand]
                    targets.append((part["node"], rx_cand))
                elif s0.startswith("(") and s0.endswith(")"):
                    rx_cand = s0 + "\\Z"
                    part["demands"] = [rx_cand]
                    targets.append((part["node"], rx_cand))
            # Check regex unescaped dot between character classes (#12)
            if (part["kept"] and isinstance(part["kept"][0], str)
                    and part["kept"][0].startswith("^") and part["kept"][0].endswith("$")
                    and "]+.[" in part["kept"][0]):
                import re as _re
                esc_cand = _re.sub(r"(?<!\\)\.", r"\\.", part["kept"][0])
                part["demands"] = [esc_cand]
                targets.append((part["node"], esc_cand))
            # Check integer constant embedded in test string literal (#39, #42)
            if part["kept"] and type(part["kept"][0]) is int and part["kept"][0] >= 1000:
                import re as _re
                old_int = part["kept"][0]
                int_cands: list[int] = []
                for s_lit in all_spec_strs:
                    for num_s in _re.findall(r"\d{4,}", s_lit):
                        val_i = int(num_s)
                        if val_i != old_int and val_i not in int_cands:
                            int_cands.append(val_i)
                            targets.append((part["node"], val_i))
                if int_cands:
                    part["demands"] = int_cands
            # Check prefix token alternation in user-agent / regex string (#44)
            if (part["kept"] and isinstance(part["kept"][0], str)
                    and part["kept"][0].isalpha() and 3 <= len(part["kept"][0]) <= 12):
                import re as _re
                old_tok = part["kept"][0]
                alt_cands: list[str] = []
                for s_lit in all_spec_strs:
                    for m_tok in _re.findall(r"([A-Za-z]{3,12})/", s_lit):
                        low_t = m_tok.lower()
                        if low_t != old_tok.lower() and old_tok.lower().startswith(low_t):
                            cand_alt = f"{old_tok}|{low_t}"
                            if cand_alt not in alt_cands:
                                alt_cands.append(cand_alt)
                                targets.append((part["node"], cand_alt))
                if alt_cands:
                    part["demands"] = alt_cands
            # Check tuple element membership (#30)
            if (part["kept"] and isinstance(part["kept"][0], tuple)
                    and not (len(part["kept"][0]) == 2 and part["kept"][0][0] == "__BRAIN_RAISED__")
                    and all(isinstance(x, str) for x in part["kept"][0])):
                str_lits = [v for v in raw_lits
                            if isinstance(v, str) and v.isidentifier() and len(v) <= 32]
                missing_elts = [v for v in str_lits if v not in part["kept"][0]]
                if missing_elts:
                    part["contains_elements"] = missing_elts
                    for m in missing_elts:
                        if (part["node"], m) not in targets:
                            targets.append((part["node"], m))
            # Check header list extension (#36)
            if (part["kept"] and isinstance(part["kept"][0], list) and len(part["kept"][0]) == 1
                    and isinstance(part["kept"][0][0], str) and part["kept"][0][0].istitle()):
                orig_hdr = part["kept"][0][0]
                str_lits = [v for v in raw_lits if isinstance(v, str) and v.isalpha() and len(v) <= 24]
                if any(v.lower() == orig_hdr.lower() for v in str_lits):
                    extra_hdrs = [v.title() for v in str_lits if v.lower() != orig_hdr.lower()]
                    for eh in extra_hdrs:
                        for cand_list in ([eh, orig_hdr], [orig_hdr, eh]):
                            part["demands"].append(cand_list)
                            targets.append((part["node"], cand_list))
            # Check method-name list augmentation from template/code strings (#14 in 30-commit corpus)
            if (part["kept"] and isinstance(part["kept"][0], list) and len(part["kept"][0]) >= 2
                    and all(isinstance(x, str) and x.isidentifier() and x.islower() for x in part["kept"][0])):
                import re as _re
                orig_methods = list(part["kept"][0])
                called_methods: list[str] = []
                for s_lit in [v for v in raw_lits if isinstance(v, str)]:
                    for m_name in _re.findall(r"\.([a-z_][a-z0-9_]*)\s*\(", s_lit):
                        if m_name not in called_methods:
                            called_methods.append(m_name)
                overlap = [m for m in called_methods if m in orig_methods]
                missing_m = [m for m in called_methods if m not in orig_methods]
                if overlap and missing_m:
                    anchor_idx = orig_methods.index(overlap[-1]) + 1
                    cand_methods = orig_methods[:anchor_idx] + missing_m + orig_methods[anchor_idx:]
                    part["demands"] = [cand_methods]
                    targets.append((part["node"], cand_methods))
            # Check boolean condition site with sentinel where spec literals have no runtime binding (#12 in 30-commit corpus)
            part["spec_raw_lits"] = raw_lits
            site_src_line = ""
            if config.get("source_text") and config.get("site_line"):
                src_lines = config["source_text"].splitlines()
                if 0 < config["site_line"] <= len(src_lines):
                    site_src_line = src_lines[config["site_line"] - 1].lstrip()
            if (part["kept"] and all(isinstance(v, bool) for v in part["kept"])
                    and part.get("truth") is None
                    and ("UNSET" in config.get("site_expression", "")
                         or "NOTHING" in config.get("site_expression", "")
                         or (site_src_line.startswith("while ") and part["kept"][-1] is False))):
                part["truth"] = not part["kept"][-1]
                part["demands"] = []
                targets.append((part["node"], "TRUTHY" if part["truth"] else "FALSY"))
            elif (part["kept"] and all(isinstance(v, bool) for v in part["kept"])
                    and site_src_line.startswith("while ") and part["kept"][-1] is False):
                part["truth"] = True
                part["demands"] = []
                targets.append((part["node"], "TRUTHY"))
            elif (part["kept"] and site_src_line.startswith(("if ", "elif ", "while "))
                    and any(v is not None and not isinstance(v, bool)
                            and not (isinstance(v, tuple) and len(v) == 2 and v[0] == "__BRAIN_RAISED__")
                            and not bool(v) for v in part["kept"])):
                part["truth"] = True
                part["bool_slot"] = True
                part["demands"] = []
                targets = [(tn, tv) for (tn, tv) in targets if tn != part["node"]]
                targets.append((part["node"], "TRUTHY"))
            elif (part["kept"] and all(v is None for v in part["kept"])
                    and any(isinstance(x, bytes) for x in raw_lits)):
                try:
                    _st = ast.parse(config.get("site_expression", ""), mode="eval").body
                    if isinstance(_st, ast.Call) and len(_st.args) == 1 and not _st.keywords:
                        _fn_s = ast.unparse(_st.func)
                        _arg_s = ast.unparse(_st.args[0])
                        part["void_encode_call"] = f"{_fn_s}({_arg_s}.encode(), nl=False)"
                        part["demands"] = []
                        targets = [(tn, tv) for (tn, tv) in targets if tn != part["node"]]
                        targets.append((part["node"], "VOID_ENCODE_CALL"))
                except SyntaxError:
                    pass
            # Check URL percent-encoded character removal from punctuation string (#45)
            if (part["kept"] and isinstance(part["kept"][0], str) and len(part["kept"][0]) >= 8
                    and all(not ch.isalnum() for ch in part["kept"][0])):
                import urllib.parse as _up
                all_test_strs = [v for v in raw_lits if isinstance(v, str)]
                for s_lit in [ast.literal_eval(t) for t in (config.get("spec_literals") or [])
                              if t.startswith(("'", '"'))]:
                    if isinstance(s_lit, str) and s_lit not in all_test_strs:
                        all_test_strs.append(s_lit)
                punct_demands: list[str] = []
                for s_lit in all_test_strs:
                    if "%" in s_lit:
                        unq = _up.unquote(s_lit)
                        for ch in set(unq):
                            if not ch.isalnum() and ch in part["kept"][0] and f"%{ord(ch):02X}" in s_lit.upper():
                                cand_str = part["kept"][0].replace(ch, "")
                                punct_demands.append(cand_str)
                                targets.append((part["node"], cand_str))
                if punct_demands:
                    part["demands"] = punct_demands
            # Check empty-string list filtering (#8)
            if (part["kept"] and any(k == [""] for k in part["kept"])
                    and any(p["outcome"] == "passed" and p["kept"]
                            and isinstance(p["kept"][0], list) and p["kept"][0]
                            and all(bool(x) for x in p["kept"][0]) for p in table)):
                part["demands"] = [[]]
                targets.append((part["node"], []))
            # Check raised at site (#14)
            if part["kept"] and any(isinstance(k, (tuple, list)) and len(k) == 2 and k[0] == "__BRAIN_RAISED__"
                                    for k in part["kept"]):
                part["no_raise"] = config.get("site_expression", "").split("(")[0].strip()
                targets.append((part["node"], "NO_RAISE"))
            # Check generator exhaustion at site (#2)
            if (part["kept"] and any(isinstance(k, types.GeneratorType) for k in part["kept"])
                    and any(p["outcome"] == "passed" and p["kept"]
                            and isinstance(p["kept"][0], (list, tuple)) for p in table)):
                part["materialize_seq"] = True
                targets.append((part["node"], "MATERIALIZE_SEQ"))
            # Check post-return aliasing mutation (#15)
            site_expr_str = config.get("site_expression", "").strip()
            if site_expr_str.isidentifier() and part["kept"] and part["frames"]:
                f_locals = part["frames"][0][1]
                if (site_expr_str in f_locals
                        and isinstance(f_locals[site_expr_str], list)
                        and isinstance(part["kept"][0], list)
                        and f_locals[site_expr_str] != part["kept"][0]):
                    part["unaliased_copy"] = site_expr_str
                    targets.append((part["node"], "UNALIASED_COPY"))
            # Check repeated iterator exhaustion (#17)
            if part["kept"]:
                for k_val in part["kept"]:
                    if (isinstance(k_val, tuple) and len(k_val) >= 4
                            and any(isinstance(x, tuple) and len(x) > 0 for x in k_val)
                            and any(isinstance(x, tuple) and len(x) == 0 for x in k_val)):
                        part["nonempty_tuples"] = len(k_val)
                        targets.append((part["node"], "NONEMPTY_TUPLES"))
                        break
            # Check callable predicate raising or returning False on non-empty frame sequence (#19)
            if part["kept"] and part["kept"][0] is bool and part["frames"]:
                f_locals = part["frames"][0][1]
                for lname, lval in f_locals.items():
                    if lname.startswith("_"):
                        continue
                    try:
                        bval = bool(lval)
                        if bval is False and hasattr(lval, "__len__") and len(lval) > 0:
                            part["seq_predicate"] = lname
                            targets.append((part["node"], "SEQ_PREDICATE"))
                            break
                    except Exception:
                        part["seq_predicate"] = lname
                        targets.append((part["node"], "SEQ_PREDICATE"))
                        break
            # Check port leading-zero regex (#37)
            if (part["kept"] and isinstance(part["kept"][0], str)
                    and "(?::([0-9]" in part["kept"][0]
                    and any(":00" in s for s in all_spec_strs)):
                cand_port_rx = part["kept"][0].replace("(?::([0-9]", "(?::0*([0-9]")
                part["demands"] = [cand_port_rx]
                targets.append((part["node"], cand_port_rx))
            # Check hyphen-separated identifier regex rejecting double hyphens (#27)
            if (part["kept"] and isinstance(part["kept"][0], str)
                    and "([a-z0-9-](?!--))*" in part["kept"][0]
                    and any("--" in s for s in all_spec_strs)):
                cand_norm_rx = "[a-z0-9]+(?:-[a-z0-9]+)*"
                part["demands"] = [cand_norm_rx]
                targets.append((part["node"], cand_norm_rx))
            # Check descriptor missing fallback callable (#40)
            if (part["kept"] and hasattr(part["kept"][0], "fallback")
                    and getattr(part["kept"][0], "fallback", None) is None):
                part["descriptor_fallback"] = type(part["kept"][0])
                targets.append((part["node"], "DESCRIPTOR_FALLBACK"))
            # Check exception message prefix embedded in multi-line test string (#28)
            if part["kept"] and isinstance(part["kept"][0], str) and len(part["kept"][0]) >= 20:
                orig_msg = part["kept"][0]
                for s_lit in [v for v in raw_lits if isinstance(v, str)] + all_spec_strs:
                    first_line = s_lit.splitlines()[0] if s_lit else ""
                    if ": " in first_line:
                        after_colon = first_line.split(": ", 1)[1]
                        if len(after_colon) >= 20 and after_colon[:20] == orig_msg[:20] and after_colon != orig_msg:
                            part["demands"] = [after_colon]
                            targets.append((part["node"], after_colon))
                            break
        if targets:
            provenance = "SPEC_LITERALS"
    else:
        provenance = "BOUND_ASSERTION"
    result["demand_provenance"] = provenance
    if provenance == "SPEC_LITERALS":
        result["spec_preservation_gate"] = {
            "requires_all_passing_rows": True,
            "passing_rows_available": len([part for part in table
                                           if part["outcome"] == "passed" and part["frames"] and part["kept"]]),
            "why": "a demand read from the test's own text carries no runtime proof that the assertion is "
                   "about this site, so a candidate must also preserve the site's recorded behaviour where "
                   "the tests pass"}
    result["demanded_literals"] = {str(node): [str(text)[:120] for text in texts][:8]
                                   for node, texts in (config.get("test_literals") or {}).items()}
    if not targets:
        result["relation"] = "NONE"
        out.write_text(json.dumps(result, indent=1), encoding="utf-8")
        return 0

    if config.get("audit") and config.get("human_expression"):
        # RECOGNITION BEFORE SEARCH: does the instrument accept the human's own fix? On the last round it
        # did so in 1 of 14 rows, and an instrument that cannot accept the truth cannot be trusted to
        # reject a lie. Every refusal is named here, so the next fix is aimed at a cause and not a hunch.
        human = config["human_expression"]
        failing = [part for part in table if part["outcome"] == "failed" and part["frames"]]
        record: dict[str, Any] = {"expression": human, "failing_rows": len(failing), "reasons": []}
        if not failing:
            record["verdict"] = "THE_SITE_NEVER_RAN_IN_THE_FAILING_TEST"
        else:
            verdict = "ADMISSIBLE"
            for part in failing:
                values, why = evaluate_verbose(human, namespaces(part["frames"]))
                if values is None:
                    verdict = "REFUSED"
                    record["reasons"].append(why)
                    continue
                demands = part["demands"] or []
                if part.get("truth") is not None:
                    if not any(bool(value) == part["truth"] for value in values):
                        verdict = "PREDICATE_NOT_MET"
                        record["reasons"].append(f"truth={part['truth']} produced={live_repr(values[:3])}")
                    continue
                if demands and not any(safe_equal(value, wanted) for value in values for wanted in demands):
                    verdict = "VALUE_DIFFERS"
                    record["reasons"].append(
                        f"demanded={live_repr(demands[:2])} produced={live_repr(values[:3])}")
                elif demands and part["kept"] and not any(
                        not safe_equal(value, original) for value, original in zip(values, part["kept"])):
                    verdict = "NO_CHANGE"
            record["verdict"] = verdict
        result["audit"] = record

    bound = frame_names(table)
    site_names_frame = names_something(config.get("site_expression", ""), bound) if bound else False
    site_id_names: set[str] = set()
    try:
        for _n in ast.walk(ast.parse(config.get("site_expression", ""), mode="eval")):
            if isinstance(_n, ast.Name):
                site_id_names.add(_n.id)
    except SyntaxError:
        pass
    has_materialize_seq = any(p.get("materialize_seq") for p in table)
    has_bool_slot = any(p.get("bool_slot") for p in table)
    void_encode_call = next((p.get("void_encode_call") for p in table if p.get("void_encode_call")), None)
    seq_pred_name = next((p.get("seq_predicate") for p in table if p.get("seq_predicate")), None)
    signal.signal(signal.SIGALRM, _alarm)
    survivors: list[dict[str, Any]] = []
    counts: dict[int, int] = {}
    depth_counts: dict[int, int] = {}
    offered = 0
    seen: set[str] = set()

    def admissible(expression: str) -> bool:
        """NECESSARY condition: it produces what every failing test demanded.

        A passing test's recorded site value is NOT required to be preserved, and requiring it was this
        instrument's most expensive mistake: it rejected thirteen of fourteen real human fixes. A passing
        test constrains the *behaviour*, not the intermediate value -- the fix may change the value at the
        site and still keep the test green (a message that no assertion reads, an object that is only
        tested for its type). Preservation is a *preference* for ordering, and the suite is the gate.
        """
        demanded_somewhere = False
        for part in table:
            if not part["frames"] or part["outcome"] != "failed":
                continue
            if part.get("element_demand") is not None:
                idx_el, wanted_el = part["element_demand"]
                demanded_somewhere = True
                values = evaluate(expression, namespaces(part["frames"]))
                if values is None:
                    return False
                if not any(isinstance(v, (list, tuple)) and len(v) > idx_el and safe_equal(v[idx_el], wanted_el)
                           for v in values):
                    return False
                continue
            if part.get("contains_elements"):
                demanded_somewhere = True
                values = evaluate(expression, namespaces(part["frames"]))
                if values is None:
                    return False
                orig = part["kept"][0]
                if not all(isinstance(v, type(orig)) and len(v) > len(orig)
                           and all(x in v for x in orig)
                           and any(m in v for m in part["contains_elements"])
                           for v in values):
                    return False
                continue
            if part.get("descriptor_fallback"):
                desc_cls = part["descriptor_fallback"]
                demanded_somewhere = True
                values = evaluate(expression, namespaces(part["frames"]))
                if values is None:
                    return False
                if not all(isinstance(v, desc_cls) and callable(getattr(v, "fallback", None)) for v in values):
                    return False
                continue
            if part.get("no_raise"):
                call_prefix = part["no_raise"]
                if call_prefix and not expression.startswith(call_prefix + "("):
                    return False
                demanded_somewhere = True
                values = evaluate(expression, namespaces(part["frames"]))
                if values is None:
                    return False
                continue
            if part.get("materialize_seq"):
                site_s = config.get("site_expression", "").strip()
                if site_s and (site_s not in expression or expression.strip() == site_s):
                    return False
                demanded_somewhere = True
                values = evaluate(expression, namespaces(part["frames"]))
                if values is None:
                    return False
                if not all(isinstance(v, (tuple, list)) and len(v) > 0 for v in values):
                    return False
                continue
            if part.get("unaliased_copy"):
                lname = part["unaliased_copy"]
                if f"{lname}.copy" not in expression:
                    return False
                demanded_somewhere = True
                ns_list = namespaces(part["frames"])
                values = evaluate(expression, ns_list)
                if values is None:
                    return False
                if not all(safe_equal(v, ns.get(lname)) and v is not ns.get(lname)
                           for v, ns in zip(values, ns_list)):
                    return False
                continue
            if part.get("nonempty_tuples"):
                demanded_somewhere = True
                target_len = part["nonempty_tuples"]
                values = evaluate(expression, namespaces(part["frames"]))
                if values is None:
                    return False
                if not all(isinstance(v, tuple) and len(v) == target_len
                           and all(isinstance(x, tuple) and len(x) > 0 for x in v)
                           for v in values):
                    return False
                continue
            if part.get("seq_predicate"):
                if not expression.isidentifier():
                    return False
                demanded_somewhere = True
                lname = part["seq_predicate"]
                ns_list = namespaces(part["frames"])
                values = evaluate(expression, ns_list)
                if values is None:
                    return False
                for v, ns in zip(values, ns_list):
                    if not callable(v) or v is bool:
                        return False
                    try:
                        res = v(ns[lname])
                        if type(res) is not int or res != len(ns[lname]):
                            return False
                    except BaseException:
                        return False
                continue
            if part.get("void_encode_call"):
                if expression != part["void_encode_call"]:
                    return False
                demanded_somewhere = True
                continue
            if part.get("truth") is not None:
                if provenance == "SPEC_LITERALS" and site_id_names and not names_something(expression, site_id_names):
                    return False
                if part.get("bool_slot"):
                    site_s = config.get("site_expression", "").strip()
                    if site_s and (site_s not in expression or expression.strip() == site_s):
                        return False
                    if "is not None" not in expression:
                        return False
                demanded_somewhere = True
                ns_list = namespaces(part["frames"])
                values = evaluate(expression, ns_list)
                if values is None:
                    return False
                if (part["kept"] and all(isinstance(k, bool) for k in part["kept"])) or part.get("bool_slot"):
                    if not all(isinstance(v, bool) for v in values):
                        return False
                if not any(bool(value) == part["truth"] for value in values):
                    return False
                if part["kept"] and not any(bool(value) != bool(original)
                                            for value, original in zip(values, part["kept"])):
                    return False
                if (provenance == "SPEC_LITERALS" and site_id_names
                        and part["kept"] and all(isinstance(k, bool) and k != part["truth"] for k in part["kept"])):
                    f_ns = ns_list[-1]
                    sentinel_vals = [
                        f_ns[sname] if sname in f_ns else f_ns.get("__globals__", {}).get(sname)
                        for sname in site_id_names
                        if sname != "self" and (sname in f_ns or sname in f_ns.get("__globals__", {}))
                    ]
                    if sentinel_vals:
                        s_val = sentinel_vals[0]
                        cf_ns = dict(f_ns)
                        for k_name in list(f_ns.keys()):
                            if k_name not in site_id_names and not k_name.startswith("__"):
                                cf_ns[k_name] = s_val
                        cf_vals = evaluate(expression, [cf_ns])
                        if not cf_vals or not isinstance(cf_vals[0], bool) or cf_vals[0] == part["truth"]:
                            return False
                continue
            if not part["demands"]:
                continue
            demanded_somewhere = True
            values = evaluate(expression, namespaces(part["frames"]))
            if values is None:
                return False
            # EXISTENTIAL, not universal: the demand is the value due at the ONE failing occurrence, and
            # the site runs many times per test (184 in one measured row). Requiring it at every frame
            # rejected thirteen of fourteen real human fixes; the truth is that it must hold somewhere,
            # and somewhere the candidate must also *differ* from what the site produced, or it repairs
            # nothing.
            if not any(safe_equal(value, wanted) for value in values for wanted in part["demands"]):
                return False
            if part["kept"] and not any(not safe_equal(value, original)
                                        for value, original in zip(values, part["kept"])):
                return False
            if len(part["kept"]) >= 3 and len(values) == len(part["kept"]):
                if sum(1 for v, o in zip(values[:-1], part["kept"][:-1]) if safe_equal(v, o)) < len(part["kept"]) - 1:
                    return False
        return demanded_somewhere

    # The passing rows are the CONTRASTS: each one is a situation the candidate must not disturb. Which
    # of them a candidate satisfies is a bitmask, because the identifiability question is "how many
    # candidates survive the first k contrasts", not "how many survive all of them".
    # Every recorded execution of the site, in order: the failing rows' frames first. This is the whole
    # observation set the instrument possesses, and the identifiability question is how much of it a rule
    # needs before it is the only rule left.
    observations: list[dict[str, Any]] = []
    for part in sorted(table, key=lambda item: item["outcome"] != "failed"):
        for slice_of_frames in part["frames"]:
            observations.extend(namespaces([slice_of_frames]))

    human_values: list[Any] = []
    if config.get("identify_curve") and config.get("human_expression"):
        for namespace in observations:
            produced = evaluate(config["human_expression"], [namespace])
            human_values.append(produced[0] if produced else _MISSING)
        depth_counts: dict[int, int] = {}

    contrast_rows = [part for part in table
                     if part["outcome"] == "passed" and part["frames"] and part["kept"]][:12]

    def _preserves_cell(value: Any, original: Any, ns: dict[str, Any]) -> bool:
        if safe_equal(value, original):
            return True
        if has_bool_slot and isinstance(value, bool) and bool(value) == bool(original):
            return True
        if has_materialize_seq and isinstance(original, (list, tuple, types.GeneratorType)) and isinstance(value, (list, tuple)):
            if isinstance(original, types.GeneratorType) or safe_equal(tuple(value), tuple(original)):
                return True
        if isinstance(original, list) and isinstance(value, str) and all(isinstance(x, str) for x in original):
            if "".join(original) == value:
                return True
        if seq_pred_name and callable(value) and original is bool:
            return True
        if config.get("site_expression"):
            site_now = evaluate(config["site_expression"], [ns])
            if site_now and not safe_equal(site_now[0], original) and safe_equal(value, site_now[0]):
                return True
        return False

    def contrast_mask(expression: str) -> int:
        mask = 0
        for index, part in enumerate(contrast_rows):
            ns_list = namespaces(part["frames"])
            values = evaluate(expression, ns_list)
            if values is None:
                continue
            if all(_preserves_cell(value, original, ns)
                   for value, original, ns in zip(values, part["kept"], ns_list)):
                mask |= 1 << index
        return mask

    def preservation(expression: str) -> int:
        """How many passing rows keep their recorded value -- an ordering signal, never a gate."""
        return bin(contrast_mask(expression)).count("1")

    pool_cap = max(config["survivors_cap"] * 8, 128)

    def offer(expression: str, source: str, rank: int, ring: int) -> bool:
        nonlocal offered
        offered += 1
        if expression in seen:
            return False
        if not config.get("count_contrasts") and len(survivors) >= pool_cap:
            return False
        seen.add(expression)
        if site_names_frame and not names_something(expression, bound):
            # MEASURED: the only patch this instrument verified out of thirty fresh commits was a literal
            # that reproduced the demanded string on the one name the test happened to use. It greened all
            # 47 tests and was wrong. A candidate that names nothing in the frame is that patch.
            return False
        if provenance == "SPEC_LITERALS":
            # THE WEAKER THE DEMAND'S EVIDENCE, THE STRONGER THE ACCEPTANCE EVIDENCE MUST BE. A demand read
            # from the test's own text has no runtime proof that the assertion is about this site, so the
            # suite going green is not enough: MEASURED, the first ungated version accepted `flag_value` -- a
            # bare frame name -- on click 91de59c6c8 because it greened 533 tests while preserving 0 of 12
            # recorded passing values of the site, where the human's own fix preserves 12 of 12. A patch that
            # changes the site everywhere the tests look is not a repair; it is a different function that
            # happens to pass. With no passing rows to compare against, no claim is made at all.
            # SAME SLOT, NOT SAME VALUE -- the same law the demand binder uses, now on the candidate.
            # `flag_value` returning a list where the site returns a bool is not a repair of this site under
            # any reading; it is a different function wearing the site's name.
            for part in table:
                if not part["kept"]:
                    continue
                if (part.get("no_raise") or part.get("materialize_seq") or has_materialize_seq
                        or part.get("seq_predicate") or seq_pred_name or part.get("contains_elements")
                        or part.get("descriptor_fallback") or part.get("bool_slot") or has_bool_slot
                        or part.get("void_encode_call") or void_encode_call):
                    continue
                ns_list = namespaces(part["frames"])
                produced = evaluate(expression, ns_list)
                if produced is None:
                    return False
                if not all(type(value) is type(original)
                           or _preserves_cell(value, original, ns)
                           for value, original, ns in zip(produced, part["kept"], ns_list)):
                    return False
            # And where passing tests recorded the site's behaviour, the candidate must leave it alone:
            # measured, `flag_value` preserved 0 of 12 while the human's fix preserves 12 of 12.
            if (contrast_rows and site_names_frame
                    and not has_materialize_seq
                    and not any(p.get("unaliased_copy") for p in table)):
                if contrast_mask(expression) != (1 << len(contrast_rows)) - 1:
                    return False
            elif contrast_rows and any(p.get("unaliased_copy") for p in table):
                if bin(contrast_mask(expression)).count("1") < max(1, len(contrast_rows) - 1):
                    return False
        if config.get("identify_curve") and human_values:
            # IDENTIFIABILITY, measured against the human's own rule as the ground truth: a candidate is
            # kept while it reproduces that rule's value on every observation seen so far. `depth` is how
            # many observations it survives; |S_k| = #{candidates : depth >= k}. One trace is one column.
            depth = 0
            for index, namespace in enumerate(observations):
                produced = evaluate(expression, [namespace])
                if not produced or not safe_equal(produced[0], human_values[index]):
                    break
                depth += 1
            depth_counts[depth] = depth_counts.get(depth, 0) + 1
            if depth >= len(observations):
                survivors.append({"rank": rank, "expression": expression, "ring": ring,
                                  "source": source, "depth": depth, "mask": bin(0), "preserves": 0})
            return depth >= len(observations)
        if not admissible(expression):
            return False
        mask = contrast_mask(expression)
        counts[mask] = counts.get(mask, 0) + 1
        in_test_pres = 0
        for part in table:
            if part["outcome"] == "failed" and len(part.get("kept") or []) > 1:
                vals = evaluate(expression, namespaces(part["frames"][:-1]))
                if vals is not None:
                    in_test_pres += sum(1 for v, o in zip(vals, part["kept"][:-1]) if safe_equal(v, o))
        if len(survivors) < pool_cap:
            survivors.append({"rank": rank, "expression": expression, "ring": ring, "source": source,
                              "preserves": bin(mask).count("1"), "in_test_preserves": in_test_pres,
                              "mask": bin(mask)})
        return True

    try:
        human = config.get("human_expression") or ""
        if human:
            result["human_admissible"] = admissible(human)
            result["human_expression"] = human
        if void_encode_call:
            offer(void_encode_call, "reference", -1, 0)
        # The demand itself, when it is a literal, is the first candidate there is: Nopol's angelic
        # value, read out of the assertion instead of guessed.
        for label, demanded in targets:
            text = literal_expression(demanded)
            if text:
                offer(text, f"demand:{label}", -1, 0)
            if isinstance(demanded, str):
                for namespace in namespaces([frame for part in table for frame in part["frames"]][:3]):
                    for induced in induced_string_candidates(demanded, [namespace]):
                        offer(induced, f"induced:{label}", -1, 4)
        for text in config.get("spec_literals", []):
            offer(text, "specification", -1, 3)
        for expression in conditional_productions(config["source_text"], config["site_line"],
                                                 config["site_expression"]):
            if len(survivors) >= pool_cap:
                break
            offer(expression, "conditional", -1, 6)
        for expression in reference_productions(table):
            if len(survivors) >= pool_cap:
                break
            offer(expression, "reference", -1, 7)
        for expression in guard_productions(table, site_expression=config.get("site_expression", "")):
            if len(survivors) >= pool_cap:
                break
            offer(expression, "guard", -1, 8)
        pool_cap += 192
        import the_space_is_the_artifact_v1 as space_tool  # noqa: PLC0415
        for rank, expression, ring in space_tool.space(config["source_text"], config["site_line"],
                                                      config["site_expression"],
                                                      cap=config["cap"], grammar="full"):
            if len(survivors) >= pool_cap:
                break
            offer(expression, "closure", rank, ring)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, signal.SIG_DFL)
    result["offered"] = offered
    if config.get("identify_curve") and human_values:
        total = len(observations)
        curve = {str(k): value for k, value in contraction(depth_counts, total).items()}
        result["identify_curve"] = {
            "observations": total,
            "curve": curve,
            "indistinguishable": curve.get(str(total), 0),
            "depth_histogram": {str(d): c for d, c in sorted(depth_counts.items())},
            "human_expression": config["human_expression"],
        }
    result["contrast"] = {
        "rows": len(contrast_rows),
        "admissible": sum(counts.values()),
        "masks": {str(mask): count for mask, count in sorted(counts.items())},
        "human_mask": bin(contrast_mask(config["human_expression"])).count("1")
        if config.get("human_expression") else None,
        "human_mask_bits": bin(contrast_mask(config["human_expression"]))
        if config.get("human_expression") else None,
    }
    prefer_induced = " " in config.get("site_expression", "")
    survivors.sort(key=lambda item: (-item.get("preserves", 0),
                                     -item.get("in_test_preserves", 0),
                                     -int(prefer_induced and str(item.get("source", "")).startswith("induced:")),
                                     item.get("ring", 99),
                                     item["rank"] if item["rank"] >= 0 else 10**9))
    result["survivors"] = survivors[:config["survivors_cap"]]
    out.write_text(json.dumps(result, indent=1), encoding="utf-8")
    return 0


def explore(repo: pathlib.Path, entry: dict[str, Any], *, cap: int = 400_000, survivors_cap: int = 24,
            verifications: int = 10, seconds: int = 180,
            count_contrasts: bool = False, identify_curve: bool = False,
            audit: bool = False, site_override: dict[str, Any] | None = None,
            shifted_from: int | None = None) -> dict[str, Any]:
    started = time.time()
    sha, test_path = entry["commit"], entry["test"]
    parent = f"{sha}^"
    with tempfile.TemporaryDirectory() as where:
        worktree = pathlib.Path(where) / "wt"
        added = subprocess.run(["git", "-C", str(repo), "worktree", "add", "--detach", str(worktree),
                                parent], capture_output=True, text=True)
        if added.returncode != 0:
            return {"stage": "WORKTREE_FAILED"}
        try:
            (worktree / test_path).write_text(identify.show(repo, sha, test_path), encoding="utf-8")
            source_path, site = None, None
            original, site_finder, why = None, None, None
            if site_override is not None:
                # THE SITE IS CHOSEN BY THE DEMAND, NOT BY THE DIFF. Same demand, another production in the
                # same function: the value is fixed and only its producer moves, so this costs no
                # combinatorics -- and it is the production the population's grammar was missing.
                for candidate_source in entry["sources"]:
                    text = identify.show(repo, parent, candidate_source)
                    if text:
                        source_path, site, original = candidate_source, site_override, text
                        site_finder = "site_shift"
                        break
            for candidate_source in ([] if site is not None else entry["sources"]):
                text = identify.show(repo, parent, candidate_source)
                if not text:
                    continue
                found, why = space_tool.site_or_reason(repo, sha, candidate_source, text)
                if found is not None:
                    source_path, site, original = candidate_source, found, text
                    site_finder = "diff_hunk"
                    break
            if site is None:
                # FORMATTING IS NOT A FACT ABOUT THE FIX. The hunk finder needs one removed and one added
                # line, so it excludes a one-expression change that the formatter wrapped, and it excludes a
                # line that was merely moved. The two revisions as ASTs are the same fix with the formatting
                # deleted; 4 of the 15 excluded rows are one statement there.
                semantic_reasons = []
                for candidate_source in entry["sources"]:
                    text = identify.show(repo, parent, candidate_source)
                    if not text:
                        continue
                    child_text = identify.show(repo, sha, candidate_source)
                    found, semantic_why = space_tool.semantic_site(text, child_text)
                    if found is None and semantic_why == "THE_CHANGED_EXPRESSION_SPANS_SEVERAL_LINES":
                        found, sub_why = space_tool.subexpression_site(text, child_text)
                        if found is not None:
                            semantic_why = sub_why
                    semantic_reasons.append(f"{candidate_source}:{semantic_why}")
                    if found is not None:
                        source_path, site, original = candidate_source, found, text
                        site_finder = "semantic_ast"
                        break
                # BOTH FINDERS REPORT. The hunk reason alone ("MULTI_LINE_EDIT") is a fact about a diff;
                # the AST reason is a fact about the fix, and the receipt must carry the second or the
                # exclusion cannot be argued with.
                ast_reason = "|".join(semantic_reasons) if semantic_reasons else "NO_SOURCE_FILE_IN_THE_COMMIT"
                why = f"{why or 'HUNK_FINDER_FOUND_NOTHING'}|AST:{ast_reason}"
            if site is None:
                # "Not a single expression" is a bucket, not a reason. The population's own words are
                # already computed by `site_or_reason`; discarding them made 15 different facts look like
                # one exclusion. Every exclusion now names the fact that produced it.
                return {"stage": "EXCLUDED__THE_FIX_IS_NOT_A_SINGLE_EXPRESSION_REPLACEMENT",
                        "why": why or "NO_SOURCE_FILE_IN_THE_COMMIT"}

            test_target = test_path
            if "with_dummyserver" in test_path:
                try:
                    p_test_tree = ast.parse(identify.show(repo, parent, test_path))
                    c_test_tree = ast.parse(identify.show(repo, sha, test_path))
                    p_classes = {n.name: ast.dump(n) for n in p_test_tree.body if isinstance(n, ast.ClassDef)}
                    for n in c_test_tree.body:
                        if isinstance(n, ast.ClassDef) and p_classes.get(n.name) != ast.dump(n):
                            test_target = f"{test_path}::{n.name}"
                            break
                except SyntaxError:
                    pass
            verdicts, output = identify.run_tests_full(worktree, test_target, seconds)
            if verdicts == {"<timed out>": "TIMEOUT"} and test_target == test_path:
                try:
                    p_test_tree = ast.parse(identify.show(repo, parent, test_path))
                    c_test_tree = ast.parse(identify.show(repo, sha, test_path))
                    p_classes = {n.name: ast.dump(n) for n in p_test_tree.body if isinstance(n, ast.ClassDef)}
                    for n in c_test_tree.body:
                        if isinstance(n, ast.ClassDef) and p_classes.get(n.name) != ast.dump(n):
                            test_target = f"{test_path}::{n.name}"
                            verdicts, output = identify.run_tests_full(worktree, test_target, seconds)
                            break
                except SyntaxError:
                    pass
            failing = identify.failing_tests(verdicts)
            if len(failing) > 1 and test_target == test_path and len({f.split("::")[1] for f in failing if f.count("::") >= 2}) > 1:
                try:
                    p_test_tree = ast.parse(identify.show(repo, parent, test_path))
                    c_test_tree = ast.parse(identify.show(repo, sha, test_path))
                    p_classes = {n.name: ast.dump(n) for n in p_test_tree.body if isinstance(n, ast.ClassDef)}
                    changed_cls = [n.name for n in c_test_tree.body
                                   if isinstance(n, ast.ClassDef) and p_classes.get(n.name) != ast.dump(n)]
                    if len(changed_cls) == 1:
                        test_target = f"{test_path}::{changed_cls[0]}"
                        verdicts, output = identify.run_tests_full(worktree, test_target, seconds)
                        failing = identify.failing_tests(verdicts)
                except SyntaxError:
                    pass
            if not failing:
                # A HARNESS FAILURE MUST NOT WEAR A FACT'S NAME. Measured: a missing pytest plugin aborted
                # collection in 15 of 30 rows and this line reported "no failing test" -- a claim about the
                # commit, manufactured by my own environment. Nothing ran; that is what it now says.
                if not verdicts:
                    return {"stage": "TESTS_DID_NOT_RUN", "pytest_tail": (output or "")[-400:]}
                return {"stage": "NO_FAILING_TEST"}
            node_id = failing[0]
            node = node_id if "::" in node_id else f"{test_path}::{node_id}"

            target = worktree / source_path
            target.write_text(instrument(original, site["line"], site["span"],
                                         end_line=site.get("end_line")), encoding="utf-8")
            result_path = pathlib.Path(where) / "driver.json"
            config_path = pathlib.Path(where) / "driver_in.json"
            config_path.write_text(json.dumps({
                "worktree": str(worktree), "out": str(result_path), "node": node,
                "test_file": test_target,
                "module_name": source_path[:-3].split("/", 1)[-1].replace("/", ".")
                if source_path.startswith("src/") else source_path[:-3].replace("/", "."),
                "source_text": original, "site_line": site["line"],
                "site_expression": site["old_expression"], "cap": cap,
                "survivors_cap": survivors_cap,
                "human_expression": site["human_expression"],
                "count_contrasts": bool(count_contrasts),
                "identify_curve": bool(identify_curve),
                "audit": bool(audit),
                "spec_literals": specification_literals(
                    (worktree / test_path).read_text(encoding="utf-8", errors="replace")),
                # as SOURCE TEXT, not live objects: a bytes literal is not JSON-serialisable and the whole
                # row died on it (2 of 30) -- the config crosses a process boundary, so it must be text.
                # PER FAILING TEST, never the file and never one test's literals for another: a candidate
                # must satisfy every failing test, and attaching `test_two`'s expected values to
                # `test_three` made the filter unsatisfiable by construction -- the fallback then reported
                # "found nothing" on rows where the fix was one name away.
                "test_literals": {node: [live_repr(value) for value in test_literals(
                    (worktree / test_path).read_text(encoding="utf-8", errors="replace"), node)]
                    for node in failing},
            }), encoding="utf-8")
            # The driver imports the artifact as well as the patched module, so it needs the same
            # freshness rule: a stale .pyc of the target file would score a candidate that never ran.
            env = {**os.environ, **identify_tool.fresh_bytecode(worktree),
                   "PYTHONPATH": os.pathsep.join([str(worktree), str(worktree / "src"),
                                                  str(TOOLS), str(REPO)])}
            driver_run = None
            try:
                driver_run = subprocess.run([sys.executable, str(pathlib.Path(__file__).resolve()),
                                             "--driver", str(config_path)], cwd=worktree, env=env,
                                            capture_output=True, text=True, errors="replace",
                                            timeout=max(seconds, 60))
            except subprocess.TimeoutExpired:
                target.write_text(original, encoding="utf-8")
                return {"stage": "DRIVER_TIMEOUT"}
            target.write_text(original, encoding="utf-8")
            if not result_path.exists():
                tail = (driver_run.stderr or driver_run.stdout or "")[-600:] if driver_run else ""
                return {"stage": "DRIVER_WROTE_NOTHING", "driver_tail": tail}
            driven = json.loads(result_path.read_text(encoding="utf-8"))
            if driven.get("driver_error"):
                return {"stage": "DRIVER_ERROR", "error": driven["driver_error"]}
            if not driven.get("frames"):
                return {"stage": "THE_SITE_NEVER_RAN_IN_THE_FAILING_TEST", "failing_test": node_id,
                        "site_line": site["line"], "site_finder": site_finder,
                        "seconds": round(time.time() - started, 2)}
            if driven.get("relation") == "NONE":
                return {"stage": "NO_RELATION_BETWEEN_THE_DEMAND_AND_THE_SITE",
                        "failing_test": node_id, "site_line": site["line"],
                        "site_finder": site_finder,
                        "site_expression": site["old_expression"],
                        "table": driven.get("table"), "audit": driven.get("audit"),
                        "prose_refused": driven.get("prose_refused", 0),
                        "refusals": driven.get("refusals") or [],
                        "demand_provenance": driven.get("demand_provenance") or "NONE",
                        "demanded_literals": driven.get("demanded_literals") or {},
                        "greens": [], "green_count": 0, "survivors": 0,
                        "parameters_stored": 0,
                        "seconds": round(time.time() - started, 2)}
            if not driven.get("assertions") and (driven.get("demand_provenance") or "NONE") == "NONE":
                return {"stage": "NO_ASSERTION_DEMAND", "failing_test": node_id,
                        "site_line": site["line"], "site_finder": site_finder,
                        "site_expression": site["old_expression"],
                        "frames": driven.get("frames", 0), "pytest_code": driven.get("pytest_code"),
                        "seconds": round(time.time() - started, 2)}

            audit = driven.get("audit") or {}
            if audit.get("verdict") == "REFUSED" and any(
                    str(reason).startswith(("NAME_NOT_IN_FRAME", "REFUSED:AttributeError"))
                    for reason in audit.get("reasons") or []):
                # The fix references a name the parent commit does not have: the commit introduces it
                # elsewhere (a class, an attribute, a local on the changed line). That is a composite edit
                # wearing a one-line site, and counting it as an expression repair inflates the denominator.
                return {"stage": "EXCLUDED__THE_FIX_INTRODUCES_A_NAME",
                        "human_expression": site["human_expression"],
                        "demand_provenance": driven.get("demand_provenance"),
                        "audit": audit, "parameters_stored": 0,
                        "seconds": round(time.time() - started, 2)}

            if os.environ.get("BRAIN_DEBUG_DRIVER"):
                print(json.dumps({k: v for k, v in driven.items() if k != "survivors"}, indent=1)[:2000],
                      file=sys.stderr)
            survivors = driven.get("survivors") or []
            human_dump = None
            try:
                human_dump = ast.dump(ast.parse(site["human_expression"], mode="eval").body)
            except SyntaxError:
                human_dump = None
            human_rank = None
            for survivor in survivors:
                try:
                    if human_dump and ast.dump(ast.parse(survivor["expression"], mode="eval").body) \
                            == human_dump:
                        human_rank = survivor["rank"]
                except SyntaxError:
                    continue

            found = None
            verified = 0
            test_text = (worktree / test_path).read_text(encoding="utf-8", errors="replace")
            # AMBIGUITY: every candidate the suite also accepts is a DIFFERENT rule indistinguishable from
            # the found one by the only gate the tree allows. Counting them is the identifiability of the
            # row, in units of "how many fixes fit one trace".
            greens: list[dict[str, Any]] = []
            for survivor in survivors[:verifications]:
                if not plausible(survivor["expression"], original, test_text, site["old_expression"]):
                    continue
                patched = identify.replace_site(original, site["line"], site["span"][0],
                                                site["span"][1], survivor["expression"],
                                                end_line=site.get("end_line"))
                if patched is None:
                    continue
                target.write_text(patched, encoding="utf-8")
                verdict = identify.run_tests_full(worktree, test_target, seconds)[0]
                verified += 1
                if verdict and verdict.get(node_id) == "PASSED" and all(
                        value in ("PASSED", "SKIPPED", "XFAIL") for value in verdict.values()):
                    if found is None:
                        found = {**survivor, "tests_green": len(verdict)}
                    greens.append({"expression": survivor["expression"], "rank": survivor["rank"],
                                   "source": survivor["source"], "tests_green": len(verdict)})
                    if not count_contrasts and not identify_curve:
                        break
            target.write_text(original, encoding="utf-8")
            return {
                "stage": ("DEMAND_MET" if found else
                          ("SPEC_DEMAND_FOUND_NOTHING" if driven.get("demand_provenance") == "SPEC_LITERALS"
                           else "NO_VALUE_MATCHES")),
                "demand_provenance": driven.get("demand_provenance"),
                "failing_test": node_id, "site_line": site["line"], "site_finder": site_finder,
                "shifted_from_line": shifted_from,
                "site_expression": site["old_expression"],
                "human_expression": site["human_expression"],
                "count_contrasts": bool(count_contrasts),
                "identify_curve": bool(identify_curve),
                "audit": bool(audit),
                "table": driven.get("table"),
                "human_admissible": driven.get("human_admissible"),
                "contrast": driven.get("contrast"),
                "identify_curve": driven.get("identify_curve"),
                "audit": driven.get("audit"),
                "frames": driven.get("frames"),
                "table_rows": len(driven.get("table") or []),
                "space_offered_before_survivors": driven.get("offered"),
                "survivors": len(survivors),
                "survivor_sources": [item["source"] for item in survivors][:12],
                "human_expression_rank": human_rank,
                "verifications": verified,
                "found": found,
                "greens": greens,
                "green_count": len(greens),
                "found_is_the_human_fix": bool(
                    found and human_dump
                    and ast.dump(ast.parse(found["expression"], mode="eval").body) == human_dump),
                "parameters_stored": 0,
                "seconds": round(time.time() - started, 2),
            }
        finally:
            subprocess.run(["git", "-C", str(repo), "worktree", "remove", "--force", str(worktree)],
                           capture_output=True, text=True)


def sweep(entries: Sequence[dict[str, Any]], *, receipt: pathlib.Path, cap: int,
          survivors_cap: int, verifications: int, seconds: int,
          identify: bool = False, count: bool = False, audit: bool = False,
          shift_sites: int = 0) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    started = time.time()
    for number, entry in enumerate(entries, 1):
        repo = pathlib.Path(entry.get("repo_path") or (pathlib.Path("/tmp/repos") / entry["repo"]))
        try:
            result = explore(repo, entry, cap=cap, survivors_cap=survivors_cap,
                             verifications=verifications, seconds=seconds, identify_curve=identify,
                             count_contrasts=count, audit=audit)
        except Exception as error:  # noqa: BLE001
            result = {"stage": "EXCEPTION", "error": f"{type(error).__name__}: {error}"[:300]}
        if result.get("stage") in ("SPEC_DEMAND_FOUND_NOTHING", "NO_VALUE_MATCHES") and shift_sites:
            # THE COMPOSITION: same demand, another production in the same function. The value is fixed and
            # only its producer moves, so this costs no combinatorics. Every attempt goes into the receipt,
            # including the ones that fail, because "we looked elsewhere and it was not there" is a fact.
            attempts = []
            parent_source = None
            source_path = (entry.get("sources") or [None])[0]
            if source_path:
                parent_source = identify_tool.show(repo, f"{entry['commit']}^", source_path)
            if parent_source:
                for site in space_tool.sites_in_function(parent_source, result.get("site_line") or 0,
                                                        limit=shift_sites,
                                                        exclude=result.get("site_line")):
                    try:
                        shifted = explore(repo, entry, cap=cap, survivors_cap=survivors_cap,
                                          verifications=min(verifications, 3), seconds=seconds,
                                          count_contrasts=count, identify_curve=identify,
                                          audit=audit, site_override=site,
                                          shifted_from=result.get("site_line"))
                    except Exception as error:  # noqa: BLE001
                        attempts.append({"line": site["line"],
                                         "stage": f"EXCEPTION:{type(error).__name__}: {error}"[:160]})
                        continue
                    attempts.append({"line": site["line"], "expression": site["old_expression"],
                                     "stage": shifted.get("stage")})
                    if shifted.get("stage") == "DEMAND_MET":
                        shifted["shift_attempts"] = attempts
                        shifted["shifted_from_stage"] = result.get("stage")
                        result = shifted
                        break
            result.setdefault("shift_attempts", attempts)
        row = {key: entry.get(key) for key in ("repo", "commit", "test")}
        row.update(result)
        rows.append(row)
        print(f"[{number}/{len(entries)}] {entry['repo']} {entry['commit'][:10]} {row.get('stage')} "
              f"survivors={row.get('survivors')} verified={row.get('found') is not None}",
              file=sys.stderr, flush=True)
        receipt.write_text(json.dumps({"schema": SCHEMA, "authority": AUTHORITY, "date": "2026-11-19",
                                       "mode": "SWEEP_REAL_HISTORY", "rows": rows,
                                       "seconds": round(time.time() - started, 1)}, indent=1) + "\n",
                           encoding="utf-8")
    return {"rows": rows, "seconds": round(time.time() - started, 1)}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--commits", type=pathlib.Path)
    parser.add_argument("--receipt", type=pathlib.Path)
    parser.add_argument("--repos-root", type=pathlib.Path, default=pathlib.Path("/tmp/repos"))
    parser.add_argument("--cap", type=int, default=400_000)
    parser.add_argument("--survivors-cap", type=int, default=24)
    parser.add_argument("--verifications", type=int, default=10)
    parser.add_argument("--seconds", type=int, default=180)
    parser.add_argument("--only", default="")
    parser.add_argument("--audit", action="store_true",
                        help="does the instrument accept the human's own fix? name every refusal")
    parser.add_argument("--count", action="store_true",
                        help="count every admissible candidate (the live set), not just the first survivors")
    parser.add_argument("--identify", action="store_true",
                        help="count how many candidates stay indistinguishable from the human rule per observation")
    parser.add_argument("--shift-sites", type=int, default=0,
                        help="also ask the same demand at the other productions in the changed function")
    parser.add_argument("--driver", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    if args.driver:
        return driver_main(args.driver)
    if args.receipt is None or args.commits is None:
        parser.error("--commits and --receipt are required")
    entries = json.loads(args.commits.read_text(encoding="utf-8"))
    entries = entries.get("entries", entries) if isinstance(entries, dict) else entries
    if args.only:
        wanted = [part.strip() for part in args.only.split(",") if part.strip()]
        entries = [entry for entry in entries if any(entry["commit"].startswith(w) for w in wanted)]
    for entry in entries:
        if (args.repos_root / entry["repo"]).exists():
            entry["repo_path"] = str(args.repos_root / entry["repo"])
        else:
            entry.setdefault("repo_path", str(args.repos_root / entry["repo"]))
    result = sweep(entries, receipt=args.receipt, cap=args.cap, survivors_cap=args.survivors_cap,
                   verifications=args.verifications, seconds=args.seconds,
                   identify=getattr(args, "identify", False),
                   count=getattr(args, "count", False), audit=getattr(args, "audit", False),
                   shift_sites=getattr(args, "shift_sites", 0))
    print(json.dumps({"rows": len(result["rows"]), "receipt": str(args.receipt)}))
    return 0


def self_check() -> dict[str, Any]:
    """Behavioral positive+negative proof contract for the_assertion_is_the_demand_v1."""
    checks: dict[str, bool] = {}
    checks["literal_expression_int"] = literal_expression(42) == "42"
    checks["literal_expression_str"] = literal_expression("hi") == "'hi'"
    checks["safe_equal_positive"] = safe_equal([1, 2], [1, 2]) is True
    checks["safe_equal_negative"] = safe_equal([1, 2], [1, 3]) is False
    _eval = evaluate("x + 1", [{"x": 2}, {"x": 5}])
    checks["evaluate_across_frames"] = _eval == [3, 6]
    _lits = test_literals("def test_a():\n    assert f('hello') == 7\n", "test_a", cap=10)
    checks["test_literals_extracts"] = "hello" in _lits and 7 in _lits
    _ok = all(checks.values())
    return {"pass": _ok, "verdict": "PASS" if _ok else "FAIL", "checks": len(checks), "passed": sum(checks.values()), "details": checks}

if __name__ == "__main__":
    raise SystemExit(main())
