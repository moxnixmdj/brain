#!/usr/bin/env python3
"""The same guard, fired twice, is the discriminator.

What the last round measured and what it left open
--------------------------------------------------
`the_failing_run_names_the_expression_v1` reads the failure text, and when the text quotes a value the
run produced it walks back to the expression that produced it. It put the human's fix for click
`1b0e19f505` at rank 1 with five candidates and no model. It also returned `NO_BLAME` for 14 of the 29
real commits, because an exception type, an exit code, a wrong list, and a `False` are not values that
appear in a message. Text is one channel out of the run; the failure is not obliged to speak.

The obvious repair is to read the other channel -- which values were true -- and that needs no text at
all, because the *program's own control flow* is an observable. This tool asks a question the run can
answer and the message cannot:

    this guard let the wrong path through. Which occurrence of it was the wrong one?

The answer is not a statistic. A guard that fired twice inside the failing run already separates the
two cases by *something*, because the same site produced different verdicts from different values.
Flip exactly one occurrence, ask the project's own pytest, and the run tells you whether that
occurrence was the one: a single flipped occurrence that turns the failing test green is a
counterfactual, not a correlation. That is the intervention the identifiability argument requires,
obtained without a second environment, a second trace, or a model.

Then the *refinement* -- the actual repair -- is not searched for. The same log that made the flip
possible records what the guard's operands were at each occurrence, and the predicate that must hold
at one occurrence and not at the others is *selected by exact fit* against those logged values:

    guard  and  (the operand that distinguished the occurrences is not the value it had at the bad one)

Zero fitted parameters: the flip table is one bit per candidate and the oracle's verdict is that bit.
No weight is stored, nothing is trained, and no model is called. This is the "best part is no part"
obligation applied to the only place a parameter could hide: there is nothing to learn because the
run's second occurrence is a free contrastive example, and a contrastive example is exactly what a
single trace lacks.

Integrity (unchanged, and checked here, not asserted)
-----------------------------------------------------
  1. The worktree is the parent commit; the test file is the post-fix test file. The answer key (the
     fix diff) is read only AFTER a result exists, for reporting, never for selection.
  2. Instrumentation must not change the verdict: a log-only run has to fail the same test the
     baseline failed, else the row is `INSTRUMENTATION_CHANGED_THE_VERDICT`.
  3. A green single-node run with no verdict is `NO_RUN`, never a pass (exit code 5 is "no tests
     collected"; pytest returning 0 because nothing ran has burned this tree before).
  4. The refinement is verified on an UNINSTRUMENTED copy of the source, by the whole test file, with
     the same command the other arms use.
  5. A refinement must be non-vacuous: the fitted predicate must be observed True at one occurrence and
     False at another in the failing run. `if False:` passes tests and explains nothing.

Authority NONE. Producer-run, one sandbox. No model call, no network call, no parameter file.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time
from typing import Any, Iterable, Sequence

TOOLS = pathlib.Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(REPO))

import identify_a_real_bugs_fix_v1 as identify  # noqa: E402

SCHEMA = "BRAIN_THE_SAME_GUARD_TWICE_IS_THE_DISCRIMINATOR_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"

# Builtins whose evaluation is safe to repeat. Anything else is a call, and re-running a call to observe
# a guard can mutate the object the guard is about -- a measurement that changes the program is not one.
SAFE_CALLS = {"len", "isinstance", "issubclass", "bool", "str", "int", "float", "type", "sorted"}
SAFE_NODES = ("Name", "Attribute", "Subscript", "Constant", "BinOp", "BoolOp", "Compare", "UnaryOp",
              "Tuple", "List", "Dict", "Set", "IfExp", "Slice", "JoinedStr", "Call")
# A bare constant is not a discriminator and a slice is not an expression: `if t[:2] == './'` yields the
# operands `2` and `:2`, and splicing `lambda: (:2)` into a real module made it a SyntaxError -- the
# import failed, the run produced no verdict, and three rows of the first sweep were unmeasurable.
NOT_OPERANDS = (ast.Constant, ast.Slice, ast.Starred, ast.FormattedValue)

HEADER = '''
# --- brain switch instrument (copy only; the real source is never edited in place) ---
import json as _brain_json, os as _brain_os
__brain_switch_count__ = {}
__brain_flip__ = {}
for _brain_k, _brain_v in _brain_json.loads(_brain_os.environ.get("BRAIN_FLIP") or "{}").items():
    __brain_flip__[int(_brain_k)] = set(int(_brain_i) for _brain_i in _brain_v)
__brain_log__ = (open(_brain_os.environ["BRAIN_SWITCH_LOG"], "a", encoding="utf-8")
                 if _brain_os.environ.get("BRAIN_SWITCH_LOG") else None)


def __brain_switch__(sid, value, operands=()):
    n = __brain_switch_count__.get(sid, 0) + 1
    __brain_switch_count__[sid] = n
    truth = bool(value)
    if __brain_log__ is not None:
        seen = {}
        for name, thunk in operands:
            try:
                seen[name] = repr(thunk())[:160]
            except Exception as error:
                seen[name] = "<raised %s>" % type(error).__name__
        try:
            __brain_log__.write(_brain_json.dumps(
                {"sid": sid, "n": n, "truth": truth, "operands": seen}) + "\\n")
            __brain_log__.flush()
        except Exception:
            pass
    flip = __brain_flip__.get(sid)
    if flip and n in flip:
        return not truth
    return truth
# --- end brain switch instrument ---
'''


# ----------------------------------------------------------------------------------------------------
# instrumentation: same lines, same semantics unless a flip is asked for
# ----------------------------------------------------------------------------------------------------


def line_offsets(source: bytes) -> list[int]:
    starts = [0]
    for index, byte in enumerate(source):
        if byte == 0x0A:
            starts.append(index + 1)
    return starts


def span_bytes(source: bytes, starts: list[int], node: ast.AST) -> tuple[int, int] | None:
    if not hasattr(node, "lineno") or node.lineno is None:
        return None
    if getattr(node, "end_lineno", None) != node.lineno:
        return None
    try:
        start = starts[node.lineno - 1] + node.col_offset
        end = starts[node.lineno - 1] + node.end_col_offset
    except IndexError:
        return None
    if start < 0 or end <= start or end > len(source):
        return None
    return start, end


def operands_of(test: ast.expr, limit: int = 4) -> list[ast.expr]:
    """The pure sub-expressions of a guard, simplest first: the candidates for the discriminator."""
    whole = ast.unparse(test)
    found: list[ast.expr] = []
    seen = {whole}
    for node in ast.walk(test):
        if not isinstance(node, ast.expr):
            continue
        if isinstance(node, NOT_OPERANDS) or type(node).__name__ not in SAFE_NODES:
            continue
        if isinstance(node, ast.Call):
            func = node.func
            name = func.id if isinstance(func, ast.Name) else None
            if name not in SAFE_CALLS:
                continue
            if any(type(arg).__name__ not in SAFE_NODES for arg in node.args):
                continue
        try:
            text = ast.unparse(node)
        except Exception:
            continue
        if not text or text in seen or len(text) > 120:
            continue
        try:
            ast.parse(text, mode="eval")
        except SyntaxError:
            continue
        seen.add(text)
        found.append(node)
    rank = {"Name": 0, "Attribute": 1, "Subscript": 2, "Compare": 3, "Call": 4, "BoolOp": 5,
            "UnaryOp": 6, "BinOp": 7}
    found.sort(key=lambda node: (rank.get(type(node).__name__, 9), len(ast.unparse(node))))
    return found[:limit]


def enclosing(node: ast.AST, parents: dict[int, ast.AST], kinds: tuple[type, ...]) -> ast.AST | None:
    parent = parents.get(id(node))
    while parent is not None:
        if isinstance(parent, kinds):
            return parent
        parent = parents.get(id(parent))
    return None


def function_locals(function: ast.AST) -> list[str]:
    """Every name the enclosing function binds, by any route, in source order."""
    names: list[str] = []
    if function is None:
        return names
    arguments = getattr(function, "args", None)
    if arguments is not None:
        for group in (getattr(arguments, "posonlyargs", []), arguments.args, arguments.kwonlyargs):
            names.extend(argument.arg for argument in group)
        for extra in (arguments.vararg, arguments.kwarg):
            if extra is not None:
                names.append(extra.arg)
    for node in ast.walk(function):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            names.append(node.id)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)) and node is not function:
            for argument in node.args.args:
                names.append(argument.arg)
    seen: set[str] = set()
    return [name for name in names if not (name in seen or seen.add(name)) and not name.startswith("_")]


def self_attributes(klass: ast.AST | None, receiver: str, site_line: int = 0) -> list[tuple[str, int]]:
    """(attribute, nearest use to this site)."""
    if klass is None:
        return []
    lines: dict[str, int] = {}
    for node in ast.walk(klass):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) \
                and node.value.id == receiver and not node.attr.startswith("__"):
            distance = abs(getattr(node, "lineno", 0) - site_line)
            lines[node.attr] = min(lines.get(node.attr, 10 ** 9), distance)
    return sorted(lines.items(), key=lambda item: (item[1], item[0]))


def _unused_self_attributes(klass: ast.AST | None, receiver: str) -> list[str]:
    """The attributes the enclosing class already reads from the receiver.

    This is the class's own vocabulary, read off its syntax tree -- not a prior about which fields
    matter. Reading `__dict__` instead of `getattr` keeps the measurement non-perturbing: a property
    with a side effect cannot fire because the property is never called.
    """
    if klass is None:
        return []
    found: list[str] = []
    for node in ast.walk(klass):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) \
                and node.value.id == receiver and not node.attr.startswith("__"):
            found.append(node.attr)
    seen: set[str] = set()
    return [name for name in found if not (name in seen or seen.add(name))]


def scope_operands(node: ast.AST, parents: dict[int, ast.AST], *, cap_locals: int = 8,
                   cap_attributes: int = 16) -> list[tuple[str, str]]:
    """(label, expression) pairs the hook can evaluate at this site, nearest-first.

    The guard's own operands are often not the discriminator: `if self.show_envvar:` fires twice with
    the same truth value and the two cases differ only in `self.envvar`, which the guard never mentions.
    What separates them is in scope, so the scope is what gets logged.
    """
    function = enclosing(node, parents, (ast.FunctionDef, ast.AsyncFunctionDef))
    klass = enclosing(node, parents, (ast.ClassDef,))
    receiver = None
    if function is not None and getattr(function, "args", None) is not None and function.args.args:
        receiver = function.args.args[0].arg
    names = function_locals(function)
    pairs: list[tuple[str, str]] = []
    if receiver:
        # Nearest-first, because the value that separated two firings of a guard is almost always the
        # one written on the guard's own line or the line after it -- and a fixed cap that sorts by
        # declaration order silently dropped `self.envvar` in the very case this tool was built for.
        for attribute, _distance in self_attributes(klass, receiver, getattr(node, "lineno", 0))[:cap_attributes]:
            pairs.append((f"{receiver}.{attribute}",
                          f"{receiver}.__dict__.get({attribute!r}, '<absent>')"))
    for name in names:
        if name == receiver:
            continue
        pairs.append((name, name))
        if len(pairs) >= cap_attributes + cap_locals:
            break
    return pairs


def instrument_module(source: str, *, first_sid: int = 0) -> tuple[str, list[dict[str, Any]]]:
    """Wrap every single-line `if`/`while` test in a switch that can be flipped per occurrence.

    Textual splice, not `ast.unparse`: real modules carry comments, line continuations and
    `# type: ignore`s that an unparse drops, and a copy whose lines moved cannot be blamed against the
    log. Every rewrite is inside one line, so every line number is preserved.
    """
    tree = ast.parse(source)
    raw = source.encode("utf-8")
    starts = line_offsets(raw)
    parents = {id(child): parent for parent in ast.walk(tree)
               for child in ast.iter_child_nodes(parent)}
    edits: list[tuple[int, int, bytes]] = []
    sites: list[dict[str, Any]] = []
    sid = first_sid
    for node in ast.walk(tree):
        if not isinstance(node, (ast.If, ast.While)):
            continue
        test = node.test
        span = span_bytes(raw, starts, test)
        if span is None:
            continue
        try:
            guard = ast.unparse(test)
        except Exception:
            continue
        operands: list[tuple[str, str]] = [(ast.unparse(o), ast.unparse(o)) for o in operands_of(test)]
        labels = {label for label, _ in operands}
        for label, expression in scope_operands(node, parents):
            if label not in labels:
                labels.add(label)
                operands.append((label, expression))
        rendered = ", ".join(f'("{label}", lambda: ({expression}))' for label, expression in operands)
        call = (f"__brain_switch__({sid}, ({guard})"
                + (f", ({rendered},)" if rendered else "")
                + ")")
        try:
            compile(call, "<switch>", "eval")
        except SyntaxError:
            continue  # a rewrite that cannot compile is not a rewrite; leave this site alone
        replacement = call.encode("utf-8")
        edits.append((span[0], span[1], replacement))
        sites.append({"sid": sid, "line": node.lineno, "col": test.col_offset,
                      "kind": type(node).__name__, "guard": guard,
                      "operands": [label for label, _ in operands]})
        sid += 1
    insert_at = 0
    body = list(tree.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant) \
            and isinstance(body[0].value.value, str):
        insert_at = starts[body[0].end_lineno - 1] + body[0].end_col_offset
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == "__future__":
            insert_at = starts[node.end_lineno - 1] + node.end_col_offset
    edits.append((insert_at, insert_at, HEADER.encode("utf-8")))
    edits.sort(key=lambda item: item[0], reverse=True)
    out = raw
    for start, end, replacement in edits:
        out = out[:start] + replacement + out[end:]
    text = out.decode("utf-8")
    try:
        compile(text, "<instrumented>", "exec")
    except SyntaxError as error:
        # The copy must be a program before it can be a measurement.
        raise ValueError(f"INSTRUMENTATION_DOES_NOT_COMPILE: {error}") from error
    return text, sites


def replace_test(source: str, site: dict[str, Any], expression: str) -> str | None:
    """Replace one guard's test in the REAL source, by byte span, and prove it still parses."""
    raw = source.encode("utf-8")
    starts = line_offsets(raw)
    tree = ast.parse(source)
    wanted = (site["line"], site["guard"])
    for node in ast.walk(tree):
        if not isinstance(node, (ast.If, ast.While)):
            continue
        if node.lineno != wanted[0]:
            continue
        if ast.unparse(node.test) != wanted[1]:
            continue
        span = span_bytes(raw, starts, node.test)
        if span is None:
            return None
        patched = (raw[:span[0]] + expression.encode("utf-8") + raw[span[1]:]).decode("utf-8")
        try:
            ast.parse(patched)
        except SyntaxError:
            return None
        return patched
    return None


# ----------------------------------------------------------------------------------------------------
# running: one node, with a flip table and a log
# ----------------------------------------------------------------------------------------------------


def pytest_env(worktree: pathlib.Path, flip: dict[int, Iterable[int]] | None = None,
               log: pathlib.Path | None = None) -> dict[str, str]:
    env = {**os.environ, "PYTHONPATH": "src:.", "PYTHONDONTWRITEBYTECODE": "1"}
    env.pop("BRAIN_FLIP", None)
    env.pop("BRAIN_SWITCH_LOG", None)
    if flip:
        env["BRAIN_FLIP"] = json.dumps({str(k): sorted(int(v) for v in vs) for k, vs in flip.items()})
    if log is not None:
        env["BRAIN_SWITCH_LOG"] = str(log)
    return env


def run_node(worktree: pathlib.Path, node: str, *, flip: dict[int, Iterable[int]] | None = None,
             log: pathlib.Path | None = None, seconds: int = 120) -> dict[str, Any]:
    argv = [sys.executable, "-m", "pytest", node, "-x", "-q", "--no-header", "--tb=line",
            "-p", "no:cacheprovider", "-o", "asyncio_default_fixture_loop_scope=function"]
    try:
        done = subprocess.run(argv, cwd=worktree, capture_output=True, text=True, errors="replace",
                              timeout=seconds, stdin=subprocess.DEVNULL,
                              env=pytest_env(worktree, flip, log))
    except subprocess.TimeoutExpired:
        return {"verdict": "TIMEOUT", "code": None, "output": ""}
    text = (done.stdout or "") + (done.stderr or "")
    # Exit code 5 is "no tests collected": pytest agreeing that nothing ran is not a pass.
    if done.returncode == 0 and (" passed" in text or "1 passed" in text):
        verdict = "PASSED"
    elif done.returncode == 0:
        verdict = "NO_RUN"
    elif done.returncode == 1:
        verdict = "FAILED"
    else:
        verdict = "NO_RUN"
    return {"verdict": verdict, "code": done.returncode, "output": text[-1500:]}


def read_log(path: pathlib.Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


# ----------------------------------------------------------------------------------------------------
# the discriminator: fit a predicate to the logged occurrences, exactly, with nothing learned
# ----------------------------------------------------------------------------------------------------


def literal(text: str) -> Any:
    try:
        return ast.literal_eval(text)
    except (ValueError, SyntaxError):
        return _NOT_LITERAL


class _NotLiteral:
    def __repr__(self) -> str:
        return "<not a literal>"


_NOT_LITERAL = _NotLiteral()


def holds(predicate: str, text: str) -> bool | None:
    """Would `predicate` be true, given the repr'd value the log recorded? None = cannot tell."""
    value = literal(text)
    if predicate.endswith(" is not None"):
        return text != "None" and not text.startswith("<raised")
    if predicate.endswith(" is None"):
        return text == "None"
    if predicate.startswith("not "):
        inner = holds(predicate[4:].strip(), text)
        return None if inner is None else not inner
    if predicate.endswith(".startswith") or "==" in predicate or "!=" in predicate:
        if value is _NOT_LITERAL:
            return None
        if "==" in predicate:
            right = predicate.split("==", 1)[1].strip()
            other = literal(right)
            return None if other is _NOT_LITERAL else value == other
        if "!=" in predicate:
            right = predicate.split("!=", 1)[1].strip()
            other = literal(right)
            return None if other is _NOT_LITERAL else value != other
    if value is _NOT_LITERAL:
        return None
    return bool(value)


def predicate_candidates(site: dict[str, Any], executions: Sequence[dict[str, Any]]) -> list[str]:
    """Predicates over the guard's own operands, built from the values the failing run produced.

    Not a grammar of fixes and not ordered by frequency: the literals come from the log, the operator
    set is the four tests Python can make without inventing a value (`is None`, `is not None`,
    truthiness, equality to an observed value).
    """
    out: list[str] = []
    for operand in site["operands"]:
        out.append(f"{operand} is not None")
        out.append(f"{operand} is None")
        out.append(operand)
        out.append(f"not {operand}")
        values = {row["operands"].get(operand, "") for row in executions}
        for text in sorted(values):
            value = literal(text)
            if value is _NOT_LITERAL or value is None:
                continue
            rendered = repr(value)
            out.append(f"{operand} == {rendered}")
            out.append(f"{operand} != {rendered}")
    seen: set[str] = set()
    unique = [p for p in out if not (p in seen or seen.add(p))]
    return unique


def fit_predicate(site: dict[str, Any], executions: Sequence[dict[str, Any]],
                  must_be_false_at: int) -> dict[str, Any] | None:
    """Select, by exact fit, a predicate that is False at the flipped occurrence and True at every other
    occurrence that the guard let through.  No scoring, no threshold: either it separates them or it
    does not exist in the candidate set."""
    keep_true = [row for row in executions if row["truth"] and row["n"] != must_be_false_at]
    bad = next((row for row in executions if row["n"] == must_be_false_at), None)
    if bad is None or not bad["truth"]:
        return None
    for predicate in predicate_candidates(site, executions):
        at_bad = holds(predicate, bad["operands"].get(_operand_of(predicate), ""))
        if at_bad is not False:
            continue
        if any(holds(predicate, row["operands"].get(_operand_of(predicate), "")) is not True
               for row in keep_true):
            continue
        witnesses = [row["n"] for row in keep_true]
        if not witnesses:
            continue  # nothing else went through this guard: a refinement would be vacuous
        return {"predicate": predicate, "false_at": bad["n"], "true_at": witnesses,
                "vacuous": False}
    return None


def _operand_of(predicate: str) -> str:
    for marker in (" is not None", " is None"):
        if predicate.endswith(marker):
            return predicate[: -len(marker)]
    if predicate.startswith("not "):
        return predicate[4:].strip()
    for marker in (" == ", " != "):
        if marker in predicate:
            return predicate.split(marker, 1)[0]
    return predicate.strip()


def refine_guard(site: dict[str, Any], predicate: str) -> str:
    guard = site["guard"]
    if site["kind"] == "While":
        return f"({guard}) and ({predicate})"
    return f"({guard}) and ({predicate})"


# ----------------------------------------------------------------------------------------------------
# the measurement for one commit
# ----------------------------------------------------------------------------------------------------


def collection_failed(output: str) -> bool:
    lowered = (output or "").lower()
    return ("error during collection" in lowered or "interrupted:" in lowered
            or "errors during collection" in lowered)


def human_fix_of(repo: pathlib.Path, sha: str, source_path: str) -> str | None:
    """The answer key, read only after a result exists, only to report whether it was found."""
    pair = next(iter(identify.needs.changed_pairs(repo, sha, source_path)), None)
    if pair is None:
        return None
    try:
        old = identify.parse_line(pair[0].strip())
        new = identify.parse_line(pair[1].strip())
        changes = identify.needs.change_points(old, new)
    except SyntaxError:
        return None
    if len(changes) != 1 or not isinstance(changes[0][2], ast.expr):
        return None
    return ast.unparse(changes[0][2])


def same_test(left: str, right: str) -> bool:
    try:
        return ast.dump(ast.parse(left, mode="eval").body) == ast.dump(ast.parse(right, mode="eval").body)
    except SyntaxError:
        return False


def explore(repo: pathlib.Path, sha: str, *, source_path: str, test_path: str,
            cap_sites: int = 60, cap_occurrences: int = 6, cap_interventions: int = 120,
            seconds: int = 90, fit: Any = None) -> dict[str, Any]:
    """One real fix. `fit` may replace the predicate selector; it is called after the
    flip oracle, never with the human edit."""
    fit_fn = fit or fit_predicate
    started = time.time()
    parent = f"{sha}^"
    parent_source = identify.show(repo, parent, source_path)
    if not parent_source:
        return {"stage": "SOURCE_NOT_FOUND"}
    with tempfile.TemporaryDirectory() as where:
        worktree = pathlib.Path(where) / "wt"
        added = subprocess.run(["git", "-C", str(repo), "worktree", "add", "--detach", str(worktree),
                                parent], capture_output=True, text=True)
        if added.returncode != 0:
            return {"stage": "WORKTREE_FAILED", "error": added.stderr[-300:]}
        try:
            (worktree / test_path).write_text(identify.show(repo, sha, test_path), encoding="utf-8")
            baseline, output = identify.run_tests_full(worktree, test_path, seconds)
            if not baseline or collection_failed(output):
                return {"stage": "SUITE_DID_NOT_RUN", "tests": len(baseline),
                        "output_tail": (output or "")[-500:]}
            # A skipped test is not a failing test. This exact confusion made four attrs rows in the
            # first pass of this sweep look like oracles with a failing test, and the "failing test"
            # then ran green (it skipped), which surfaced as INSTRUMENTATION_CHANGED_THE_VERDICT.
            failing = next(iter(identify.failing_tests(baseline)), None)
            if failing is None:
                return {"stage": "NO_ORACLE__THE_POST_FIX_TESTS_PASS_ON_THE_PARENT",
                        "tests": len(baseline),
                        "skipped": sum(1 for value in baseline.values() if value in ("SKIPPED", "XFAIL"))}
            # run_tests_full reports `path::name` when the file was given as a path and `name` when it
            # was not; a node id built by blindly prefixing produced `path::path::name` and ran nothing.
            node = failing if "::" in failing else f"{test_path}::{failing}"

            target = worktree / source_path
            original = target.read_text(encoding="utf-8")
            try:
                instrumented, sites = instrument_module(original)
            except ValueError as error:
                return {"stage": "INSTRUMENTATION_FAILED", "failing_test": failing,
                        "error": str(error)[:200]}
            target.write_text(instrumented, encoding="utf-8")

            log = pathlib.Path(where) / "switch.jsonl"
            first = run_node(worktree, node, log=log, seconds=seconds)
            if first["verdict"] != "FAILED":
                return {"stage": "INSTRUMENTATION_CHANGED_THE_VERDICT",
                        "verdict_under_logging": first["verdict"], "failing_test": failing,
                        "output_tail": first["output"][-600:]}
            executions = read_log(log)
            by_site: dict[int, list[dict[str, Any]]] = {}
            for position, row in enumerate(executions):
                row["position"] = position
                by_site.setdefault(int(row["sid"]), []).append(row)
            by_id = {site["sid"]: site for site in sites}
            executed = [site for site in sites if site["sid"] in by_site]
            # Ordered by how late the site last fired, not by how often: the observable that failed is
            # produced at the end of the run, so the guards nearest the end produced it. Occurrence
            # count is the tie-break, and within a site the LAST occurrence is tried first -- the one
            # whose value was in force when the wrong output was written.
            executed.sort(key=lambda site: (-max(row["position"] for row in by_site[site["sid"]]),
                                            -len(by_site[site["sid"]]), site["line"]))

            plan: list[tuple[int, int]] = []
            for site in executed[:cap_sites]:
                occurrences = sorted((row["n"] for row in by_site[site["sid"]]), reverse=True)
                for number in occurrences[:cap_occurrences]:
                    plan.append((site["sid"], number))
            plan = plan[:cap_interventions]

            survivors: list[dict[str, Any]] = []
            for sid, number in plan:
                log.unlink(missing_ok=True)
                result = run_node(worktree, node, flip={sid: [number]}, seconds=seconds)
                if result["verdict"] == "PASSED":
                    survivors.append({"sid": sid, "occurrence": number, "site": by_id[sid]})
            log.unlink(missing_ok=True)

            # Vacuity and soundness: the flip has to keep the whole test file green, not just this node.
            for survivor in survivors:
                verdicts = identify.run_tests(worktree, test_path, seconds)
                broken = [name for name, verdict in verdicts.items() if verdict != "PASSED"]
                survivor["file_green"] = bool(verdicts) and not broken
                survivor["broken"] = broken[:5]
                survivor["broken_count"] = len(broken)

            refined: dict[str, Any] | None = None
            for survivor in survivors:
                site = survivor["site"]
                rows = by_site[site["sid"]]
                fit = fit_fn(site, rows, survivor["occurrence"])
                if fit is None:
                    survivor["fit"] = None
                    continue
                expression = refine_guard(site, fit["predicate"])
                survivor["fit"] = {**fit, "expression": expression}
                if refined is None:
                    refined = {"survivor": survivor, "fit": fit, "expression": expression}

            verification: dict[str, Any] | None = None
            if refined is not None:
                site = refined["survivor"]["site"]
                patched = replace_test(original, site, refined["expression"])
                if patched is None:
                    verification = {"stage": "REFINEMENT_NOT_WRITABLE"}
                else:
                    target.write_text(patched, encoding="utf-8")
                    verdicts = identify.run_tests_full(worktree, test_path, seconds)
                    target.write_text(original, encoding="utf-8")
                    green = bool(verdicts[0]) and all(v == "PASSED" for v in verdicts[0].values())
                    verification = {"stage": "VERIFIED" if green else "REFINEMENT_FAILS_THE_SUITE",
                                    "tests": len(verdicts[0]),
                                    "broken": [n for n, v in verdicts[0].items() if v != "PASSED"][:6],
                                    "output_tail": "" if green else (verdicts[1] or "")[-500:]}

            human = human_fix_of(repo, sha, source_path)
            found = bool(human and refined and same_test(refined["expression"], human))
            if human and refined and not found:
                # The human's edit may be only the predicate; a conjunction is the same fix.
                found = same_test(refined["fit"]["predicate"], human) or same_test(
                    refined["expression"], f"({site['guard']}) and ({human})")
            # Naming the refusal matters as much as naming the success. A flip that turns the failing
            # test green while breaking other tests in the same file is not a repair, and the first pass
            # of this sweep would have called five of them "FLIP_FOUND" -- every one of them had
            # `file_green: false` next to it in the receipt, and not one had an exact fit.
            sound = [survivor for survivor in survivors if survivor.get("file_green")]
            if verification and verification.get("stage") == "VERIFIED":
                stage = "VERIFIED"
            elif refined:
                stage = "FLIP_FOUND__REFINEMENT_NOT_VERIFIED"
            elif sound:
                stage = "SOUND_FLIP__NO_EXACT_FIT_IN_THE_LOGGED_VOCABULARY"
            elif survivors:
                stage = "FLIP_PASSED_THE_TEST__BROKE_THE_SUITE__NO_FIT"
            else:
                stage = "NO_SWITCH__NO_SINGLE_OCCURRENCE_FLIP_PASSES"
            return {
                "stage": stage, "sha": sha, "source": source_path, "test_file": test_path,
                "failing_test": failing,
                "tests_in_file": len(baseline),
                "sites_instrumented": len(sites),
                "sites_executed": len(executed),
                "sites_planned": min(len(executed), cap_sites),
                "occurrences_logged": len(executions),
                "interventions": len(plan),
                "survivors_sound": len([s for s in survivors if s.get("file_green")]),
                "survivors": [{"sid": s["sid"], "occurrence": s["occurrence"],
                               "line": s["site"]["line"], "guard": s["site"]["guard"],
                               "kind": s["site"]["kind"],
                               "file_green": s["file_green"], "broken_count": s["broken_count"],
                               "fit": s.get("fit")} for s in survivors[:6]],
                "refinement": refined["expression"] if refined else None,
                "refinement_site": {"line": refined["survivor"]["site"]["line"],
                                    "guard": refined["survivor"]["site"]["guard"]} if refined else None,
                "verification": verification,
                "human_fix": human,
                "human_fix_found": found,
                "parameters_stored": 0,
                "bits_from_the_oracle": len(plan),
                "seconds": round(time.time() - started, 2),
            }
        finally:
            subprocess.run(["git", "-C", str(repo), "worktree", "remove", "--force", str(worktree)],
                           capture_output=True, text=True)


def sweep(entries: Sequence[dict[str, str]], *, receipt: pathlib.Path, seconds: int,
          cap_sites: int, cap_occurrences: int, cap_interventions: int) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    started = time.time()
    for number, entry in enumerate(entries, 1):
        repo = pathlib.Path(entry.get("repo_path") or (pathlib.Path("/tmp/repos") / entry["repo"]))
        try:
            result = explore(repo, entry["commit"], source_path=entry["source"],
                             test_path=entry["test"], cap_sites=cap_sites,
                             cap_occurrences=cap_occurrences,
                             cap_interventions=cap_interventions, seconds=seconds)
        except Exception as error:  # a harness fault is a row, never a silent skip
            result = {"stage": "EXCEPTION", "error": f"{type(error).__name__}: {error}"[:300]}
        row = {key: entry.get(key) for key in ("repo", "commit", "source", "test")}
        for key in ("stage", "failing_test", "tests_in_file", "sites_executed", "sites_planned",
                    "occurrences_logged", "interventions", "survivors_sound", "survivors", "refinement", "refinement_site", "verification",
                    "human_fix", "human_fix_found", "bits_from_the_oracle", "parameters_stored",
                    "seconds", "error", "output_tail"):
            if key in result:
                row[key] = result[key]
        rows.append(row)
        print(f"[{number}/{len(entries)}] {entry['repo']} {entry['commit'][:10]} {row.get('stage')} "
              f"survivors={len(result.get('survivors') or [])} "
              f"found={row.get('human_fix_found')}", file=sys.stderr, flush=True)
        receipt.write_text(json.dumps({"schema": SCHEMA, "authority": AUTHORITY, "date": "2026-11-19",
                                       "mode": "SWEEP_REAL_HISTORY", "rows": rows,
                                       "seconds": round(time.time() - started, 1)}, indent=1) + "\n")
    return {"schema": SCHEMA, "rows": rows, "seconds": round(time.time() - started, 1)}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--commits", type=pathlib.Path, help="JSON list of {repo,commit,source,test}")
    parser.add_argument("--receipt", type=pathlib.Path, required=True)
    parser.add_argument("--seconds", type=int, default=90)
    parser.add_argument("--cap-sites", type=int, default=60)
    parser.add_argument("--cap-occurrences", type=int, default=6)
    parser.add_argument("--cap-interventions", type=int, default=120)
    parser.add_argument("--only", default="", help="comma-separated commit prefixes to keep")
    parser.add_argument("--instrument", type=pathlib.Path,
                        help="print the instrumented copy of this file and exit (no execution)")
    args = parser.parse_args(argv)

    if args.instrument is not None:
        text, sites = instrument_module(args.instrument.read_text(encoding="utf-8"))
        sys.stdout.write(text)
        print(json.dumps(sites), file=sys.stderr)
        return 0

    if args.commits is None:
        parser.error("--commits is required unless --instrument is given")
    entries = json.loads(args.commits.read_text(encoding="utf-8"))
    if args.only:
        wanted = [part.strip() for part in args.only.split(",") if part.strip()]
        entries = [e for e in entries if any(e["commit"].startswith(w) for w in wanted)]
    result = sweep(entries, receipt=args.receipt, seconds=args.seconds, cap_sites=args.cap_sites,
                   cap_occurrences=args.cap_occurrences, cap_interventions=args.cap_interventions)
    print(json.dumps({"rows": len(result["rows"]), "receipt": str(args.receipt)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
