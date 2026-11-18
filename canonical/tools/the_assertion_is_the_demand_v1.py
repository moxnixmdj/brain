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

SCHEMA = "BRAIN_THE_ASSERTION_IS_THE_DEMAND_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"
HELPER = "__brain_site__"
FRAMES = "__brain_frames__"
KEPT = "__brain_kept__"

INSTRUMENT = '''

# --- injected by the_assertion_is_the_demand_v1: the site becomes a question -----------------------
import sys as _brain_sys

{FRAMES} = []
{KEPT} = []


def {HELPER}(index, thunk):
    """Return what the site computes, and keep the frame that computed it."""
    try:
        frame = _brain_sys._getframe(1)
        {FRAMES}.append((index, dict(frame.f_locals), dict(frame.f_globals)))
    except Exception:
        {FRAMES}.append((index, {{}}, {{}}))
    value = thunk()
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
    made = []
    for _index, locals_, globals_ in slice_of_frames:
        merged = dict(locals_)
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
                for attribute in attributes[:per_name]:
                    text = f"{name}.{attribute}"
                    if text not in made:
                        made.append(text)
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


def guard_productions(table: list, width: int = 10) -> list[str]:
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
    for reference in references:
        for text in (f"{reference} is None", f"{reference} is not None", f"not {reference}"):
            made.append(text)
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
    target = node_id.split("::")[-1]
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
        rendered = live_repr(args)
        if "assert " in rendered and "<Result" in rendered:
            return None
        # The failing assertion's own line. `assert not <X>` demands that the site's value be FALSY --
        # reading X itself as the demand is the defect that made one measured row (click 18d29196c5)
        # demand an AssertionError object the site could never produce.
        try:
            crash = call.excinfo.traceback
            entry = crash[-1]
            statement = "".join(getattr(entry, "statement", "") or "")
            if entry.lineno and statement.lstrip().startswith("assert "):
                # The failing assert is not always in the test file: it is often in a helper the test
                # calls. Carrying the crash path is what lets the reader see the statement at all.
                self.assert_lines[item.nodeid] = (str(entry.path), entry.lineno)
        except BaseException:
            pass
        self.rows.append({"op": "raise", "left": error, "right": args, "node": item.nodeid})
        return None


def instrument(source: str, line: int, span: tuple[int, int]) -> str:
    """Wrap the site's expression in the hook, and put the hook's machinery at the top of the module."""
    lines = source.splitlines(keepends=True)
    index = line - 1
    if index >= len(lines):
        raise ValueError("SITE_LINE_OUT_OF_RANGE")
    start, end = span
    original = lines[index]
    lines[index] = f"{original[:start]}{HELPER}(0, lambda: {original[start:end]}){original[end:]}"
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


def plausible(expression: str, source: str, test_source: str) -> bool:
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
        return text in source or text in test_source
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


def evaluate(expression: str, locals_by_frame: list[dict[str, Any]]) -> list[Any] | None:
    """Evaluate one candidate against every recorded frame; None if any frame refuses or times out."""
    values: list[Any] = []
    for namespace in locals_by_frame:
        globals_ = namespace.get("__globals__") or {}
        locals_ = namespace
        try:
            signal.setitimer(signal.ITIMER_REAL, 0.05)
            values.append(eval(compile(expression, "<candidate>", "eval"), globals_, locals_))  # noqa: S307
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
    values: list[Any] = []
    for namespace in locals_by_frame:
        globals_ = namespace.get("__globals__") or {}
        try:
            signal.setitimer(signal.ITIMER_REAL, 0.05)
            values.append(eval(compile(expression, "<candidate>", "eval"), globals_, namespace))  # noqa: S307
        except NameError as error:
            return None, f"NAME_NOT_IN_FRAME:{error}"
        except BaseException as error:  # noqa: BLE001
            return None, f"REFUSED:{type(error).__name__}"
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
    return values, "OK"


def _alarm(signum, frame):  # noqa: ANN001
    raise _Alarm


class _Alarm(Exception):
    pass


def evaluate_verbose(expression: str, locals_by_frame: list[dict[str, Any]]
                     ) -> tuple[list[Any] | None, str]:
    """`evaluate`, but it names the reason a frame refused -- the audit needs the reason, not a None."""
    values: list[Any] = []
    for namespace in locals_by_frame:
        globals_ = namespace.get("__globals__") or {}
        try:
            signal.setitimer(signal.ITIMER_REAL, 0.05)
            values.append(eval(compile(expression, "<candidate>", "eval"), globals_, namespace))  # noqa: S307
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
    for entry in capture.tests:
        start, finish = entry["start"], entry.get("end", len(frames))
        part = {"node": entry["node"], "outcome": capture.outcomes.get(entry["node"], "unknown"),
                "frames": frames[start:finish], "kept": kept[start:finish]}
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
            if form in ("falsy", "truthy"):
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
        out.write_text(json.dumps(result, indent=1), encoding="utf-8")
        return 0

    targets: list[tuple[str, Any]] = []
    for part in table:
        if part.get("truth") is not None:
            targets.append((part["node"], "TRUTHY" if part["truth"] else "FALSY"))
        for demanded in part["demands"]:
            targets.append((part["node"], demanded))
    provenance = "BOUND_ASSERTION"
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
            for text in literals_by_test.get(part["node"]) or []:
                try:
                    value = ast.literal_eval(text)
                except (ValueError, SyntaxError):
                    continue
                # THE FILTER READS THE PARTS, NOT `targets`. Appending only to `targets` produced candidates
                # that `admissible()` then rejected as unchanged-from-nothing: the fallback looked like it
                # searched 20,632 expressions and found none, when in fact no demand had been installed.
                part["demands"].append(value)
                targets.append((part["node"], value))
        if targets:
            provenance = "SPEC_LITERALS"
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
            if part.get("truth") is not None:
                demanded_somewhere = True
                values = evaluate(expression, namespaces(part["frames"]))
                if values is None:
                    return False
                if not any(bool(value) == part["truth"] for value in values):
                    return False
                if part["kept"] and not any(bool(value) != bool(original)
                                            for value, original in zip(values, part["kept"])):
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

    def contrast_mask(expression: str) -> int:
        mask = 0
        for index, part in enumerate(contrast_rows):
            values = evaluate(expression, namespaces(part["frames"]))
            if values is not None and all(safe_equal(value, original)
                                          for value, original in zip(values, part["kept"])):
                mask |= 1 << index
        return mask

    def preservation(expression: str) -> int:
        """How many passing rows keep their recorded value -- an ordering signal, never a gate."""
        return bin(contrast_mask(expression)).count("1")

    def offer(expression: str, source: str, rank: int, ring: int) -> bool:
        nonlocal offered
        offered += 1
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
                produced = evaluate(expression, namespaces(part["frames"]))
                if produced is None:
                    return False
                if not all(type(value) is type(original)
                           for value, original in zip(produced, part["kept"])):
                    return False
            # And where passing tests recorded the site's behaviour, the candidate must leave it alone:
            # measured, `flag_value` preserved 0 of 12 while the human's fix preserves 12 of 12.
            if contrast_rows and contrast_mask(expression) != (1 << len(contrast_rows)) - 1:
                return False
        if expression in seen:
            return False
        if not config.get("count_contrasts") and len(survivors) >= config["survivors_cap"]:
            return False
        seen.add(expression)
        if not names_something(expression, bound) if bound else False:
            # MEASURED: the only patch this instrument verified out of thirty fresh commits was a literal
            # that reproduced the demanded string on the one name the test happened to use. It greened all
            # 47 tests and was wrong. A candidate that names nothing in the frame is that patch.
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
        if len(survivors) < config["survivors_cap"]:
            survivors.append({"rank": rank, "expression": expression, "ring": ring, "source": source,
                              "preserves": bin(mask).count("1"), "mask": bin(mask)})
        return True

    try:
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
        import the_space_is_the_artifact_v1 as space_tool  # noqa: PLC0415
        for rank, expression, ring in space_tool.space(config["source_text"], config["site_line"],
                                                      config["site_expression"],
                                                      cap=config["cap"], grammar="full"):
            if len(survivors) >= config["survivors_cap"]:
                break
            offer(expression, "closure", rank, ring)
        # The form most real repairs take and no closure above produces: a CONDITIONAL. The previous
        # round found one such repair in sample and could not say the form; here it is measured as one
        # more production, so that "the closure lacks this shape" is a count and not an opinion.
        for expression in conditional_productions(config["source_text"], config["site_line"],
                                                 config["site_expression"]):
            if len(survivors) >= config["survivors_cap"]:
                break
            offer(expression, "conditional", -1, 6)
        # A complete witness for the claim "this row is not reachable": is the human's own replacement
        # expressible at all, and does the table accept it? Scored AFTER the search, never fed to it.
        for expression in reference_productions(table):
            if len(survivors) >= config["survivors_cap"]:
                break
            offer(expression, "reference", -1, 7)
        for expression in guard_productions(table):
            if len(survivors) >= config["survivors_cap"]:
                break
            offer(expression, "guard", -1, 8)
        human = config.get("human_expression") or ""
        if human:
            result["human_admissible"] = admissible(human)
            result["human_expression"] = human
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
    survivors.sort(key=lambda item: (-item.get("preserves", 0),
                                     item["rank"] if item["rank"] >= 0 else 10**9))
    result["survivors"] = survivors
    out.write_text(json.dumps(result, indent=1), encoding="utf-8")
    return 0


def explore(repo: pathlib.Path, entry: dict[str, Any], *, cap: int = 400_000, survivors_cap: int = 24,
            verifications: int = 10, seconds: int = 180,
            count_contrasts: bool = False, identify_curve: bool = False,
            audit: bool = False) -> dict[str, Any]:
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
            original = None
            for candidate_source in entry["sources"]:
                text = identify.show(repo, parent, candidate_source)
                if not text:
                    continue
                found, why = space_tool.site_or_reason(repo, sha, candidate_source, text)
                if found is not None:
                    source_path, site, original = candidate_source, found, text
                    break
            if site is None:
                # "Not a single expression" is a bucket, not a reason. The population's own words are
                # already computed by `site_or_reason`; discarding them made 15 different facts look like
                # one exclusion. Every exclusion now names the fact that produced it.
                return {"stage": "EXCLUDED__THE_FIX_IS_NOT_A_SINGLE_EXPRESSION_REPLACEMENT",
                        "why": why or "NO_SOURCE_FILE_IN_THE_COMMIT"}

            verdicts, _output = identify.run_tests_full(worktree, test_path, seconds)
            failing = identify.failing_tests(verdicts)
            if not failing:
                return {"stage": "NO_FAILING_TEST"}
            node_id = failing[0]
            node = node_id if "::" in node_id else f"{test_path}::{node_id}"

            target = worktree / source_path
            target.write_text(instrument(original, site["line"], site["span"]), encoding="utf-8")
            result_path = pathlib.Path(where) / "driver.json"
            config_path = pathlib.Path(where) / "driver_in.json"
            config_path.write_text(json.dumps({
                "worktree": str(worktree), "out": str(result_path), "node": node,
                "test_file": test_path,
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
            env = {**os.environ, "PYTHONPATH": os.pathsep.join([str(worktree), str(worktree / "src"),
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
                        "site_line": site["line"], "seconds": round(time.time() - started, 2)}
            if driven.get("relation") == "NONE":
                return {"stage": "NO_RELATION_BETWEEN_THE_DEMAND_AND_THE_SITE",
                        "failing_test": node_id, "site_line": site["line"],
                        "site_expression": site["old_expression"],
                        "table": driven.get("table"), "audit": driven.get("audit"),
                        "prose_refused": driven.get("prose_refused", 0),
                        "refusals": driven.get("refusals") or [],
                        "demand_provenance": driven.get("demand_provenance") or "NONE",
                        "demanded_literals": driven.get("demanded_literals") or {},
                        "greens": [], "green_count": 0, "survivors": 0,
                        "parameters_stored": 0,
                        "seconds": round(time.time() - started, 2)}
            if not driven.get("assertions"):
                return {"stage": "NO_ASSERTION_DEMAND", "failing_test": node_id,
                        "site_line": site["line"], "site_expression": site["old_expression"],
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
            # AMBIGUITY: every candidate the suite also accepts is a DIFFERENT rule indistinguishable from
            # the found one by the only gate the tree allows. Counting them is the identifiability of the
            # row, in units of "how many fixes fit one trace".
            greens: list[dict[str, Any]] = []
            for survivor in survivors[:verifications]:
                patched = identify.replace_site(original, site["line"], site["span"][0],
                                                site["span"][1], survivor["expression"])
                if patched is None:
                    continue
                target.write_text(patched, encoding="utf-8")
                verdict = identify.run_tests_full(worktree, test_path, seconds)[0]
                verified += 1
                if verdict.get(node_id) == "PASSED":
                    whole = identify.run_tests(worktree, test_path, seconds)
                    if whole and all(value == "PASSED" for value in whole.values()):
                        if not plausible(survivor["expression"], original,
                                         (worktree / test_path).read_text(encoding="utf-8",
                                                                          errors="replace")):
                            refused = survivor["expression"]
                            target.write_text(original, encoding="utf-8")
                            continue
                        if found is None:
                            found = {**survivor, "tests_green": len(whole)}
                        greens.append({"expression": survivor["expression"], "rank": survivor["rank"],
                                       "source": survivor["source"], "tests_green": len(whole)})
            target.write_text(original, encoding="utf-8")
            return {
                "stage": ("DEMAND_MET" if found else
                          ("SPEC_DEMAND_FOUND_NOTHING" if driven.get("demand_provenance") == "SPEC_LITERALS"
                           else "NO_VALUE_MATCHES")),
                "demand_provenance": driven.get("demand_provenance"),
                "failing_test": node_id, "site_line": site["line"],
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
          identify: bool = False, count: bool = False, audit: bool = False) -> dict[str, Any]:
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
        entry.setdefault("repo_path", str(args.repos_root / entry["repo"]))
    result = sweep(entries, receipt=args.receipt, cap=args.cap, survivors_cap=args.survivors_cap,
                   verifications=args.verifications, seconds=args.seconds,
                   identify=getattr(args, "identify", False),
                   count=getattr(args, "count", False), audit=getattr(args, "audit", False))
    print(json.dumps({"rows": len(result["rows"]), "receipt": str(args.receipt)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
