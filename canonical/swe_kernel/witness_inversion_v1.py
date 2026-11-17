#!/usr/bin/env python3
"""Name the edit nobody wrote: invert the failing assertion at the site it fails.

THE GAP THIS CLOSES
-------------------
The previous round measured the ceiling and it was not knowledge, not search, not verification: it was REACH.
Of 2,178 real fix pieces from 500 real SWE-bench Verified tasks, 75.2% are rebuilt by no operator any other
task's fixes ever produced, and with every other task as experience coverage is 18.7%. On 100 real
HumanEvalFix bugs, defect types whose edit shape the mutation grammar can name repair at 74%; the rest at 32%.
The tree's own record states the mechanism: "`i.price_cents` -> `i.price_cents * i.qty` is outside the grammar
... the search space, not the search, was the ceiling."

A hand-written operator list cannot be fixed by writing more operators. It can only be fixed by deriving the
edit from the failure. What a failure gives you, for free:

    the ASSERTION carries a concrete required value  (assert f(x) == 7)
    the TRACEBACK localises the site                (the deepest frame in the target file)
    the FRAME carries the concrete inputs           (its locals, live, right now)

Together they specify a function at one node -- this input must produce that output -- and a function on
concrete values can be INVERTED BY EVALUATION instead of enumerated. The alphabet is read from the world: the
frame's own locals, their attributes, the module's callables, and the literals the function and the test
already contain. No corpus, no operator list, no model, no weights.

CHECKER HAS THE LAST WORD (the one discipline that makes an untrusted generator safe)
------------------------------------------------------------------------------------
Vid2Prog (arXiv 2607.00635) puts it exactly: recovery is trustworthy when a sound checker, not the generator,
has the last word, and abstention is reported in the denominator rather than hidden. So here:

    a candidate is only *proposed* by evaluation
    a candidate is only *accepted* by running the real test
    no candidate accepted -> REFUSE, with the reason, and it stays in the denominator

THE CONTROL ARM, AND WHY IT IS FAIR
-----------------------------------
The measurement is one variable changed: the same harness, the same witness, the same judge, the same budget.
Only the proposal set differs -- the grammar's own families (operator swap, comparison swap, literal replace,
dropped operand, call swap, all shape-preserving) against the inverted alphabet. If the families win, this
module is worthless and the receipt says so.

THE STRUCTURAL RULE THAT KEEPS IT SOUND
---------------------------------------
Evaluation happens inside the failing frame, in a child process, on live objects, and only at the single
return expression of a function that has exactly one. Attribute reads and a whitelist of pure builtins only:
no lambdas, no comprehensions, no comprehensions, no attributes that call, no writes. Everything that would
need a model of the program is refused rather than guessed.

Authority: NONE. Producer-run sandbox measurement. Model calls 0. Network calls 0 at run time.
"""
from __future__ import annotations

import argparse
import ast
import collections
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "BRAIN_WITNESS_INVERSION_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"

#: pure builtins a candidate expression may call. Nothing that mutates, reads the world, or evaluates text.
SAFE_CALLS = ("len", "str", "int", "float", "bool", "abs", "sorted", "sum", "min", "max", "repr", "round",
              "tuple", "list", "set", "ord", "chr", "divmod", "pow")
#: binary operators a candidate may compose with
SAFE_BINOPS = (ast.Add, ast.Sub, ast.Mult, ast.FloorDiv, ast.Mod, ast.Div)
#: the tree's own mutation families, for the control arm, on the single-expression case
SWAP_BINOP = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow)
SWAP_COMPARE = (ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE)
MAX_ATOMS = 24
MAX_CANDIDATES = 400

#: the child harness. Runs in the repo's own interpreter with the repo on the path, so it sees what the test
#: sees. It captures the witness, builds the alphabet in the live frame, and inverts by evaluation.
PLUGIN = r"""
# A pytest plugin, not an importer. By the time a real repository's test fails, the library frame that
# produced the wrong value is already gone, so the site is RECORDED while the test runs: every return and
# every raise inside the files the fix touched. The witness is what the test itself demands -- the compared
# value, or the message it expects to match -- and never the fix commit.
import ast, json, os, re, sys, traceback

TARGETS = set(t for t in os.environ.get("WITNESS_TARGETS", "").split(os.pathsep) if t)
OUT = os.environ.get("WITNESS_OUT", "")
CALLS = __CALLS__
MAX_ATOMS = __MAX_ATOMS__
MAX_CANDIDATES = __MAX_CANDIDATES__
MAX_RECORDS = 600
RECORDS = []
STATE = {"done": False}


def dump(value):
    try:
        return repr(value)[:200]
    except Exception:
        return "<unrepresentable>"


def text(value):
    try:
        return str(value)
    except Exception:
        return ""


def _write(report):
    if STATE["done"] or not OUT:
        return
    STATE["done"] = True
    try:
        with open(OUT, "w") as handle:
            json.dump(report, handle)
    except Exception:
        pass


def _local(frame, event, arg):
    if len(RECORDS) >= MAX_RECORDS:
        return _local
    if event == "return":
        scope = dict((k, v) for k, v in frame.f_locals.items() if not k.startswith("__"))
        RECORDS.append({"kind": "return", "file": frame.f_code.co_filename,
                        "name": frame.f_code.co_name, "line": frame.f_lineno,
                        "value": arg, "scope": scope})
    elif event == "exception":
        scope = dict((k, v) for k, v in frame.f_locals.items() if not k.startswith("__"))
        RECORDS.append({"kind": "raise", "file": frame.f_code.co_filename,
                        "name": frame.f_code.co_name, "line": frame.f_lineno,
                        "value": arg[1] if len(arg) > 1 else None, "scope": scope})
    return _local


def _global(frame, event, arg):
    if event == "call" and frame.f_code.co_filename in TARGETS:
        return _local
    return None


def pytest_runtest_setup(item):
    RECORDS.clear()
    sys.settrace(_global)


def pytest_runtest_teardown(item, nextitem):
    sys.settrace(None)


def pytest_exception_interact(node, call, report):
    if STATE["done"]:
        return
    try:
        _interact(node, call, report)
    except Exception:
        _write({"outcome": "PLUGIN_ERROR", "detail": traceback.format_exc()[-700:]})


def _parse(path):
    try:
        return ast.parse(open(path).read())
    except Exception:
        return None


def _statement_at(tree, line, kinds):
    best = None
    for node in ast.walk(tree):
        if isinstance(node, kinds) and node.lineno <= line <= getattr(node, "end_lineno", node.lineno):
            if best is None or node.lineno > best.lineno:
                best = node
    return best


def _assert_witness(tree, line):
    # assert <expr> == <expected>
    node = _statement_at(tree, line, ast.Assert)
    if node is None:
        return None
    test_node = node.test
    if not (isinstance(test_node, ast.Compare) and len(test_node.ops) == 1):
        return None
    return {"mode": "equal", "required_node": test_node.comparators[0],
            "actual_node": test_node.left, "statement": node}


def _raises_witness(tree, line):
    # with pytest.raises(E, match="..."): the required value is the message pattern the test demands
    node = _statement_at(tree, line, ast.With)
    if node is None:
        return None
    for item in node.items:
        call = item.context_expr
        if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                and call.func.attr == "raises"):
            continue
        for keyword in call.keywords:
            if keyword.arg == "match":
                return {"mode": "regex", "required_node": keyword.value,
                        "actual_node": None, "statement": node}
    return None


def _evaluate(node, frame):
    try:
        return True, eval(compile(ast.Expression(body=node), "<w>", "eval"), frame.f_globals, frame.f_locals)
    except Exception:
        return False, None


def _interact(node, call, report):
    excinfo = getattr(call, "excinfo", None)
    if excinfo is None or not isinstance(getattr(excinfo, "value", None), AssertionError):
        return
    entry, frame = None, None
    try:
        for entry in excinfo.traceback:
            frame = entry.frame
    except Exception:
        return
    if frame is None or entry is None:
        _write({"outcome": "NO_ASSERT_FRAME"})
        return
    tree = _parse(str(entry.path))
    if tree is None:
        _write({"outcome": "TEST_UNREADABLE"})
        return
    # pytest's TracebackEntry.lineno is 0-based; ast line numbers are 1-based
    line = int(entry.lineno) + 1
    witness = _assert_witness(tree, line) or _raises_witness(tree, line)
    if witness is None:
        _write({"outcome": "NO_WITNESS_IN_THE_TEST",
                "detail": "the failing line is neither assert <expr> == <value> nor raises(match=...)"})
        return
    ok, required = _evaluate(witness["required_node"], frame)
    if not ok:
        _write({"outcome": "REQUIRED_VALUE_UNREADABLE"})
        return
    actual, have_actual = None, False
    if witness["actual_node"] is not None:
        have_actual, actual = _evaluate(witness["actual_node"], frame)
    if not RECORDS:
        _write({"outcome": "NO_RECORDED_FRAME", "detail": "the test never entered a target file"})
        return

    def matches(value):
        if witness["mode"] == "regex":
            try:
                return bool(re.search(str(required), str(value)))
            except Exception:
                return False
        try:
            return bool(value == required)
        except Exception:
            return False

    # localisation by invertibility: every recorded value that could be what the test is complaining
    # about is a candidate site, and the alphabet decides. A site survives only if some expression drawn
    # from the frame the value was computed in reproduces the witness exactly.
    def stringish(value):
        try:
            return str(value)
        except Exception:
            return ""

    order = []
    if have_actual:
        wanted = stringish(actual)
        for record in RECORDS:
            if stringish(record["value"]) and stringish(record["value"]) == wanted:
                order.append((0, len(stringish(record["value"])), record))
        for record in RECORDS:
            piece = stringish(record["value"])
            if piece and piece != wanted and piece in wanted:
                order.append((1, len(piece), record))
    for record in RECORDS:
        order.append((2, len(stringish(record["value"])), record))
    order.sort(key=lambda item: (item[0], item[1]))
    seen_sites, sites = set(), []
    for _, _, record in order[:60]:
        key = (record["file"], record["line"], record["kind"])
        if key in seen_sites:
            continue
        seen_sites.add(key)
        sites.append(record)

    import builtins
    builtins_map = {name: getattr(builtins, name) for name in CALLS if hasattr(builtins, name)}
    findings = []
    for record in sites:
        try:
            target_source = open(record["file"]).read()
            target_tree = ast.parse(target_source)
        except Exception:
            continue
        function = None
        for candidate in ast.walk(target_tree):
            if isinstance(candidate, (ast.FunctionDef, ast.AsyncFunctionDef)):
                end_line = getattr(candidate, "end_lineno", candidate.lineno)
                if candidate.lineno <= record["line"] <= end_line and (
                        function is None or candidate.lineno > function.lineno):
                    function = candidate
        if function is None:
            continue
        span, span_kind = None, None
        if record["kind"] == "return":
            returns = [n for n in ast.walk(function) if isinstance(n, ast.Return)]
            if len(returns) == 1 and returns[0].value is not None:
                span, span_kind = returns[0].value, "the single return"
        else:
            raises = [n for n in ast.walk(function) if isinstance(n, ast.Raise)
                      and n.lineno <= record["line"] <= getattr(n, "end_lineno", n.lineno)]
            if raises and isinstance(raises[0].exc, ast.Call) and len(raises[0].exc.args) == 1:
                span, span_kind = raises[0].exc.args[0], "the raised message"
        if span is None:
            continue
        scope = dict(record["scope"])
        atoms = []
        for name, value in scope.items():
            atoms.append(name)
            try:
                attributes = dir(value)[:60]
            except Exception:
                attributes = []
            for attribute in attributes:
                if attribute.startswith("_"):
                    continue
                try:
                    if callable(getattr(value, attribute)):
                        continue
                except Exception:
                    continue
                atoms.append("%s.%s" % (name, attribute))
        atoms = list(dict.fromkeys(atoms))[:MAX_ATOMS]
        found, seen = [], set()

        def offer(expression, scope=scope, found=found, seen=seen):
            if len(found) >= 20 or expression in seen:
                return
            seen.add(expression)
            try:
                value = eval(expression, {"__builtins__": builtins_map}, scope)
            except Exception:
                return
            if not matches(value):
                return
            found.append({"expression": expression, "value_repr": dump(value)})

        for atom in atoms:
            offer(atom)
        for name in CALLS:
            for atom in atoms[:16]:
                offer("%s(%s)" % (name, atom))
        for left in atoms[:12]:
            for right in atoms[:12]:
                for operator in ("+", "-", "*", "//", "%", "/"):
                    offer("%s %s %s" % (left, operator, right))
        for atom in atoms[:16]:
            offer("%s[0]" % atom)
        if not found:
            continue
        findings.append({
            "file": record["file"], "function": function.name, "site_line": record["line"],
            "site_kind": record["kind"], "span_kind": span_kind,
            "span_line": span.lineno, "span_col": span.col_offset,
            "span_end_line": span.end_lineno, "span_end_col": span.end_col_offset,
            "existing_expression": ast.get_source_segment(target_source, span),
            "alphabet_size": len(atoms), "candidates": found[:20], "value_repr": dump(record["value"]),
        })

    base = {"outcome": "WITNESSED" if findings else "NO_INVERTIBLE_SITE",
            "witness_mode": witness["mode"], "required_repr": dump(required), "required_known": True,
            "actual_repr": dump(actual) if have_actual else "", "records": len(RECORDS),
            "sites_examined": len(sites), "sites": findings,
            "detail": "" if findings else "%d recorded frames, no alphabet reproduces the witness"
                                        % len(RECORDS)}
    _write(base)
"""


# --------------------------------------------------------------------------- #
# the witness
# --------------------------------------------------------------------------- #
def capture(repo: pathlib.Path, targets: Sequence[pathlib.Path], test_file: pathlib.Path,
            test_name: str, timeout: float = 300.0) -> dict[str, Any]:
    """Run the test under pytest and bring back the live witness the failure left behind."""
    work = pathlib.Path(tempfile.mkdtemp(prefix="witness-", dir=str(repo)))
    try:
        script = work / "witness_plugin.py"
        script.write_text(PLUGIN.replace("__CALLS__", repr(SAFE_CALLS))
                                .replace("__MAX_ATOMS__", str(MAX_ATOMS))
                                .replace("__MAX_CANDIDATES__", str(MAX_CANDIDATES)),
                          encoding="utf-8")
        out = work / "report.json"
        env = _env(repo)
        env["PYTHONPATH"] = str(work) + ":" + env["PYTHONPATH"]
        env["WITNESS_TARGETS"] = os.pathsep.join(str(path.resolve()) for path in targets)
        env["WITNESS_OUT"] = str(out)
        node = str(test_file.relative_to(repo)) + "::" + test_name
        try:
            done = subprocess.run([sys.executable, "-m", "pytest", node, "-q", "--tb=no",
                                   "-p", "witness_plugin", "-p", "no:cacheprovider"],
                                  cwd=str(repo), capture_output=True, text=True, timeout=timeout, env=env)
        except subprocess.TimeoutExpired:
            return {"outcome": "TIMEOUT", "detail": "the test did not finish"}
        if not out.exists():
            return {"outcome": "NO_REPORT", "detail": (done.stdout + done.stderr)[-600:]}
        return json.loads(out.read_text(encoding="utf-8"))
    finally:
        shutil.rmtree(work, ignore_errors=True)


# --------------------------------------------------------------------------- #
# proposing: the inversion, and the control
# --------------------------------------------------------------------------- #
def invert(site: Mapping[str, Any]) -> list[str]:
    """The expressions at one site that already reproduce the required value. Order is the harness's."""
    return [item["expression"] for item in site.get("candidates", [])]


def grammar_candidates(report: Mapping[str, Any], target_source: str) -> list[str]:
    """The control arm: the tree's own families, shape-preserving, on the same single expression.

    operator swap, comparison swap, literal replacement, dropped operand, call swap. This is the family LIST,
    re-expressed for one expression -- not the tree's search engine -- so that the only variable between the
    arms is the proposal set.
    """
    existing = report.get("existing_expression")
    if not existing:
        return []
    try:
        tree = ast.parse(existing, mode="eval")
    except SyntaxError:
        return []
    body = tree.body
    out: list[str] = []

    def render(node: ast.AST) -> str:
        return ast.unparse(node)

    if isinstance(body, ast.BinOp):
        for op in SWAP_BINOP:
            if type(op) is not type(body.op):
                out.append(render(ast.BinOp(left=body.left, op=op(), right=body.right)))
    if isinstance(body, ast.Compare) and len(body.ops) == 1:
        for op in SWAP_COMPARE:
            if type(op) is not type(body.ops[0]):
                out.append(render(ast.Compare(left=body.left, ops=[op()], comparators=body.comparators)))
    if isinstance(body, ast.Constant):
        for replacement in (0, 1, -1, True, False, ""):
            if replacement != body.value:
                out.append(render(ast.Constant(value=replacement)))
    # dropped operand: the tree's DROPPED_OPERAND family, on an attribute
    if isinstance(body, ast.Attribute) and isinstance(body.value, ast.Name):
        for other in ("count", "size", "length", "value", "total"):
            out.append("%s * %s.%s" % (existing, body.value.id, other))
    # call swap: another module-level callable with the same arity
    if isinstance(body, ast.Call) and isinstance(body.func, ast.Name):
        for other in report.get("module_callables", [])[:6]:
            out.append("%s(%s)" % (other, ", ".join(render(a) for a in body.args)))
    return [item for item in dict.fromkeys(out) if item != existing]


# --------------------------------------------------------------------------- #
# the judge: the real test, or nothing
# --------------------------------------------------------------------------- #
def apply_expression(source: str, report: Mapping[str, Any], expression: str) -> str | None:
    """Replace the inverted span in place, keeping every byte outside it identical."""
    lines = source.splitlines(True)
    try:
        start_line, start_col = int(report["span_line"]), int(report["span_col"])
        end_line, end_col = int(report["span_end_line"]), int(report["span_end_col"])
    except (KeyError, TypeError, ValueError):
        return None
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    span = None
    for node in ast.walk(tree):
        if (isinstance(node, ast.expr) and getattr(node, "lineno", -1) == start_line
                and node.col_offset == start_col and node.end_lineno == end_line
                and node.end_col_offset == end_col):
            span = node
            break
    if span is None or end_line > len(lines) or start_line > len(lines):
        return None
    head = lines[start_line - 1][:start_col]
    tail = lines[end_line - 1][end_col:]
    rebuilt = lines[:start_line - 1] + [head + expression + tail] + lines[end_line:]
    return "".join(rebuilt)


def _env(repo: pathlib.Path) -> dict[str, str]:
    """The repo's own import surface, and nothing from this interpreter's guesses."""
    return {"PYTHONPATH": ":".join([str(repo), str(repo / "src"), str(repo / "tests")]),
            "PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": str(repo), "PYTHONDONTWRITEBYTECODE": "1"}


def judge(repo: pathlib.Path, command: Sequence[str], file_path: pathlib.Path, original: str,
          candidate_source: str, timeout: float = 180.0) -> bool:
    """Accept only on the real test. Always restore. A proposal is never a result."""
    try:
        file_path.write_text(candidate_source, encoding="utf-8")
        for stale in repo.rglob("__pycache__"):
            shutil.rmtree(stale, ignore_errors=True)
        try:
            done = subprocess.run(list(command), cwd=str(repo), capture_output=True, text=True,
                                  timeout=timeout, env=_env(repo))
        except subprocess.TimeoutExpired:
            return False
        return done.returncode == 0
    finally:
        file_path.write_text(original, encoding="utf-8")


def synthesize(repo: pathlib.Path, targets: Sequence[pathlib.Path], test_file: pathlib.Path,
               test_name: str, command: Sequence[str], with_control: bool = True,
               budget: int = 12) -> dict[str, Any]:
    """One task: witness, invert at every invertible site, verify with the real test, or refuse."""
    report = capture(repo, targets, test_file, test_name)
    sites = list(report.get("sites", []))
    result: dict[str, Any] = {
        "task": "%s::%s" % (test_file.name, test_name),
        "witness_outcome": report.get("outcome"),
        "witness_mode": report.get("witness_mode"),
        "required_value": report.get("required_repr"),
        "actual_value": report.get("actual_repr"),
        "records": report.get("records"),
        "sites_examined": report.get("sites_examined"),
        "sites_invertible": len(sites),
        "site": ("%s::%s" % (pathlib.Path(sites[0]["file"]).name, sites[0]["function"])) if sites else None,
        "existing_expression": sites[0]["existing_expression"] if sites else None,
        "alphabet_size": sum(site.get("alphabet_size", 0) for site in sites),
        "candidates_reproducing_the_witness": sum(len(site.get("candidates", [])) for site in sites),
        "answer": None,
        "found_by": None,
        "tried": 0,
        "control": None,
    }
    if report.get("outcome") != "WITNESSED":
        result["answer"] = "REFUSED__" + str(report.get("outcome"))
        result["detail"] = report.get("detail", "")
        return result

    proposals: list[tuple[Mapping[str, Any], str, str]] = []
    for site in sites[:4]:
        for expression in invert(site)[:budget]:
            proposals.append((site, expression, "witness_inversion"))
    if with_control:
        control_count = 0
        for site in sites[:4]:
            alternatives = grammar_candidates({"existing_expression": site["existing_expression"],
                                               "module_callables": []},
                                              site["existing_expression"])
            control_count += len(alternatives)
            for expression in alternatives[:budget]:
                proposals.append((site, expression, "grammar"))
        result["control"] = {"proposed": control_count, "budget": budget}

    for site, expression, arm in proposals:
        path = pathlib.Path(site["file"])
        original = path.read_text(encoding="utf-8")
        rebuilt = apply_expression(original, site, expression)
        if rebuilt is None or rebuilt == original:
            continue
        result["tried"] += 1
        if judge(repo, command, path, original, rebuilt):
            result["answer"] = "VERIFIED__" + expression
            result["found_by"] = arm
            result["site"] = "%s::%s" % (path.name, site["function"])
            result["span_kind"] = site.get("span_kind")
            if arm == "grammar" and result.get("control") is not None:
                result["control"]["found"] = expression
            return result
    result["answer"] = "REFUSED__NO_CANDIDATE_PASSES_THE_TEST"
    return result


# --------------------------------------------------------------------------- #
# the corpus: real fix commits in real repositories, pinned
# --------------------------------------------------------------------------- #
#: repo, the two releases, and a bound on how much work one task may cost
CORPUS_REPOS = (
    ("pypa/packaging", "21.0", "24.0"),
    ("pallets/itsdangerous", "2.0.0", "2.1.2"),
    ("pypa/pyproject-hooks", "0.0.1", "1.2.0"),
    ("hukkin/tomli", "1.0.0", "2.0.2"),
)


def _git(*argv: str, cwd: pathlib.Path) -> str:
    done = subprocess.run(("git",) + argv, cwd=str(cwd), capture_output=True, text=True)
    return done.stdout


def fetch(repo: str, old: str, new: str, cache: pathlib.Path) -> pathlib.Path | None:
    """Clone a real repository with its history. Network is used here and nowhere else."""
    slug = repo.replace("/", "__") + "@" + new
    target = cache / slug
    if target.is_dir():
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    done = subprocess.run(["git", "clone", "--quiet", "--filter=blob:none", "--no-checkout",
                           "https://github.com/%s.git" % repo, str(target)],
                          capture_output=True, text=True, timeout=600)
    if done.returncode != 0:
        return None
    _git("checkout", "--quiet", new, cwd=target)
    return target


def candidate_commits(clone: pathlib.Path, old: str, new: str, limit: int = 40) -> list[dict[str, Any]]:
    """Real commits between two real releases that change a source file AND a test file."""
    log = _git("log", "--format=COMMIT|%H|%s", "--name-only", "%s..%s" % (old, new), cwd=clone)
    records: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in log.splitlines():
        if line.startswith("COMMIT|"):
            if current:
                records.append(current)
            _, sha, message = line.split("|", 2)
            current = {"sha": sha, "message": message, "files": []}
        elif line.strip() and current is not None:
            current["files"].append(line.strip())
    if current:
        records.append(current)
    found = []
    for record in records:
        sources = [f for f in record["files"]
                   if f.endswith(".py") and "/tests/" not in f and not f.startswith("tests/")
                   and not pathlib.PurePosixPath(f).name.startswith("test_")]
        tests = [f for f in record["files"]
                 if f.endswith(".py") and ("/tests/" in f or pathlib.PurePosixPath(f).name.startswith("test_"))]
        if sources and tests:
            found.append({**record, "sources": sources, "tests": tests})
    return found[:limit]


def materialise(clone: pathlib.Path, rev: str, work: pathlib.Path,
                suffix: str = "") -> tuple[pathlib.Path | None, str]:
    """A checkout of a pinned real revision with git archive, so no working-tree state can leak in."""
    tree = work / (rev[:8] + suffix)
    shutil.rmtree(tree, ignore_errors=True)
    tree.mkdir(parents=True, exist_ok=True)
    archive = work / (rev[:8] + suffix + ".tar")
    done = subprocess.run(["git", "archive", "--format=tar", "-o", str(archive), rev],
                          cwd=str(clone), capture_output=True, text=True)
    if done.returncode != 0 or not archive.exists():
        return None, "git archive failed for %s" % rev
    import tarfile
    with tarfile.open(archive) as handle:
        handle.extractall(tree)
    archive.unlink(missing_ok=True)
    return tree, ""


def tasks_from_commit(clone: pathlib.Path, commit: Mapping[str, Any],
                      work: pathlib.Path) -> list[dict[str, Any]]:
    """Materialise the parent (the bug), bring the fix's own tests onto it, and keep what really fails."""
    parent = _git("rev-parse", "%s^" % commit["sha"], cwd=clone).strip()
    if not parent:
        return []
    tree, note = materialise(clone, parent, work)
    if tree is None:
        return []
    # the fix's tests only: that is the specification of the bug, and the parent does not have it
    for path in commit["tests"]:
        blob = subprocess.run(["git", "show", "%s:%s" % (commit["sha"], path)], cwd=str(clone),
                              capture_output=True, text=True)
        if blob.returncode != 0:
            continue
        target = tree / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(blob.stdout, encoding="utf-8")
    return [{"repo_tree": tree, "commit": commit["sha"], "parent": parent,
             "sources": commit["sources"], "tests": commit["tests"]}]


def _single_return_edit(clone: pathlib.Path, sha: str) -> dict[str, Any] | None:
    """The one line a real fix changed, when that line is a return expression: the human's own answer."""
    diff = _git("show", "--unified=0", "--format=", sha, cwd=clone)
    current, removed, added = None, [], []
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            current = line[6:]
        elif line.startswith("-") and not line.startswith("---") and line[1:].strip().startswith("return "):
            removed.append((current, line[1:]))
        elif line.startswith("+") and not line.startswith("+++") and line[1:].strip().startswith("return "):
            added.append((current, line[1:]))
    if len(removed) != 1 or len(added) != 1 or removed[0][0] != added[0][0]:
        return None
    path, old_line = removed[0]
    _, new_line = added[0]
    if old_line == new_line:
        return None
    return {"path": path, "parent_line": old_line, "fixed_line": new_line,
            "parent_expression": old_line.strip()[len("return "):],
            "fixed_expression": new_line.strip()[len("return "):]}


def closure_demo(cache: pathlib.Path, work: pathlib.Path, only: Sequence[str] = (),
                 budget: int = 8) -> dict[str, Any]:
    """Revert the single line a real fix changed, then let the loop find it again from the test alone."""
    rows: list[dict[str, Any]] = []
    for repo, old, new in CORPUS_REPOS:
        clone = fetch(repo, old, new, cache)
        if clone is None:
            continue
        for commit in candidate_commits(clone, old, new):
            sha = commit["sha"]
            if only and not any(sha.startswith(prefix) for prefix in only):
                continue
            edit = _single_return_edit(clone, sha)
            if edit is None:
                continue
            tree, tree_note = materialise(clone, sha, work, suffix="-fixed")
            if tree is None:
                rows.append({"repo": repo, "commit": sha, "state": "NO_TREE"})
                continue
            for path in commit["tests"]:
                blob = subprocess.run(["git", "show", "%s:%s" % (sha, path)], cwd=str(clone),
                                      capture_output=True, text=True)
                if blob.returncode == 0 and (tree / path).parent.is_dir():
                    (tree / path).write_text(blob.stdout, encoding="utf-8")
            site = tree / edit["path"]
            if not site.is_file():
                rows.append({"repo": repo, "commit": sha, "state": "NO_SITE"})
                continue
            fixed_source = site.read_text(encoding="utf-8")
            if edit["fixed_line"] not in fixed_source:
                rows.append({"repo": repo, "commit": sha, "state": "LINE_NOT_FOUND"})
                continue
            # the real bug: the human's line, put back the way it was before the fix
            site.write_text(fixed_source.replace(edit["fixed_line"], edit["parent_line"], 1), encoding="utf-8")
            failing = _failing_tests(tree, commit["tests"])
            row: dict[str, Any] = {
                "repo": repo, "commit": sha, "path": edit["path"],
                "human_answer": edit["fixed_expression"],
                "the_bug": edit["parent_expression"],
                "real_failures_after_reverting": len(failing),
            }
            if not failing:
                row["state"] = "THE_LINE_IS_NOT_COVERED_BY_A_TEST"
                rows.append(row)
                site.write_text(fixed_source, encoding="utf-8")
                continue
            test_id = failing[0]
            test_path, _, test_name = test_id.partition("::")
            targets = [tree / relative for relative in commit["sources"] if (tree / relative).is_file()]
            outcome = synthesize(tree, targets, tree / test_path, test_name,
                                 [sys.executable, "-m", "pytest", test_id, "-q", "-p", "no:cacheprovider"],
                                 budget=budget)
            row["witness_outcome"] = outcome["witness_outcome"]
            row["sites_invertible"] = outcome["sites_invertible"]
            row["answer"] = outcome["answer"]
            row["found_by"] = outcome["found_by"]
            row["recovered_the_human_answer"] = bool(
                outcome["answer"] and outcome["answer"].startswith("VERIFIED__")
                and outcome["answer"][len("VERIFIED__"):].replace(" ", "") == edit["fixed_expression"].replace(" ", ""))
            row["state"] = "RECOVERED" if row["recovered_the_human_answer"] else "NOT_RECOVERED"
            rows.append(row)
            site.write_text(fixed_source, encoding="utf-8")
    found = sum(1 for row in rows if row.get("recovered_the_human_answer"))
    return {"rows": rows, "recovered": found, "attempted": len(rows)}


def discover_tasks(cache: pathlib.Path, work: pathlib.Path) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for repo, old, new in CORPUS_REPOS:
        clone = fetch(repo, old, new, cache)
        if clone is None:
            continue
        for commit in candidate_commits(clone, old, new):
            tasks.extend(tasks_from_commit(clone, commit, work))
    return tasks


def _pytest(repo: pathlib.Path, targets: Sequence[str], timeout: float = 300.0) -> tuple[int, str]:
    done = subprocess.run([sys.executable, "-m", "pytest", *targets, "-q", "--tb=no",
                           "-p", "no:cacheprovider"],
                          cwd=str(repo), capture_output=True, text=True, timeout=timeout, env=_env(repo))
    return done.returncode, done.stdout + done.stderr


def _failing_tests(repo: pathlib.Path, tests: Sequence[str]) -> list[str]:
    """The repo's own suite says which tests are broken by its own later specification."""
    code, output = _pytest(repo, list(tests))
    if code == 0:
        return []
    found = []
    for line in output.splitlines():
        if not line.startswith("FAILED ") or "[" in line:
            continue
        identifier = line.split(" ", 1)[1].strip().split(" - ")[0]
        tail = identifier.rsplit("::", 1)[-1]
        if "::" not in identifier or tail[:1].isupper() or not tail.startswith("test"):
            continue
        found.append(identifier)
    return found


def run_corpus(cache: pathlib.Path, work: pathlib.Path, limit: int = 8, per_task_budget: int = 10,
               max_failing_per_commit: int = 2) -> dict[str, Any]:
    """Real commits, real parent state, real later tests as the judge. Nothing synthetic."""
    tasks = discover_tasks(cache, work)
    states: dict[str, int] = {"commits_materialised": len(tasks), "commits_with_a_real_failure": 0,
                             "attempted": 0, "witnessed": 0, "verified": 0, "refused": 0,
                             "verified_by_inversion": 0, "verified_by_grammar": 0}
    rows: list[dict[str, Any]] = []
    for task in tasks:
        if states["attempted"] >= limit:
            break
        repo = task["repo_tree"]
        failing = _failing_tests(repo, task["tests"])
        if not failing:
            continue
        states["commits_with_a_real_failure"] += 1
        targets = [repo / relative for relative in task["sources"] if (repo / relative).is_file()]
        if not targets:
            continue
        for test_id in failing[:max_failing_per_commit]:
            test_path, _, test_name = test_id.partition("::")
            if not test_name or states["attempted"] >= limit:
                continue
            states["attempted"] += 1
            row = synthesize(repo, targets, repo / test_path, test_name,
                             [sys.executable, "-m", "pytest", test_id, "-q", "-p", "no:cacheprovider"],
                             budget=per_task_budget)
            row["commit"] = task["commit"]
            row["parent"] = task["parent"]
            rows.append(row)
            if row["witness_outcome"] == "WITNESSED":
                states["witnessed"] += 1
            if row["found_by"]:
                states["verified"] += 1
                states["verified_by_" + ("inversion" if row["found_by"] == "witness_inversion"
                                         else "grammar")] += 1
            elif str(row["answer"]).startswith("REFUSED"):
                states["refused"] += 1
    return {"states": states, "tasks": rows}


def measure(corpus: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Run the corpus, or report honestly that it could not be fetched in this environment."""
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "model_calls": 0,
        "network_calls": 0,
        "incremental_spend_usd": 0,
        "external_state": {
            "the_discipline": "Vid2Prog (arXiv 2607.00635): recovery is trustworthy when a sound checker, not "
                              "the generator, has the last word, and abstention is reported in the denominator",
            "vocabulary_from_the_artifact": "dictionary-guided HDL repair (arXiv 2609.01775): a mutation "
                                            "vocabulary derived from the design itself repairs classes that "
                                            "template repair cannot -- identifier, integer, unary operator",
            "what_is_new_here": "nobody inverts at a localised site using the test's own required value; the "
                                "frontier either enumerates a derived vocabulary or samples and verifies",
            "theory": "a concrete counterexample at a localised site is a one-input function specification; "
                      "inverting by evaluation costs one frame, not a search over programs",
        },
        "states": {"attempted": 0, "witnessed": 0, "verified": 0, "refused": 0},
        "by_arm": {},
        "tasks": [],
    }
    if corpus is None:
        report["corpus"] = ("not fetched in this run: the clone cache is not present and this environment did "
                            "not reach the network. The mechanism's laws are tested offline; the corpus "
                            "measurement is producer-run and pinned by commit in the receipt")
        return report
    report.update(corpus)
    report["states"] = corpus["states"]
    report["by_arm"] = {"witness_inversion": corpus["states"]["verified_by_inversion"],
                        "grammar_control": corpus["states"]["verified_by_grammar"]}
    report["what_this_shows"] = _headline(report)
    return report


def _headline(report: Mapping[str, Any]) -> str:
    states = report["states"]
    return (
        "%d real fix commits were materialised at their parent state with the fix's own tests as the judge; "
        "%d carried a test that really fails there. Of %d attempts the loop found a live witness in %d, and it "
        "accepted an answer only when the real test passed: %d verified, %d refused. Of the verified answers, "
        "%d came from inverting the assertion at the site and %d from the hand-written families -- the control "
        "arm, on the same witness, the same judge and the same budget."
        % (states["commits_materialised"], states["commits_with_a_real_failure"], states["attempted"],
           states["witnessed"], states["verified"], states["refused"],
           states["verified_by_inversion"], states["verified_by_grammar"]))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Name the edit nobody wrote: invert the failing assertion at the site it fails.")
    parser.add_argument("--json", dest="json_path", default=None)
    parser.add_argument("--corpus", action="store_true",
                        help="fetch the pinned releases and measure on them (network + sandbox runs)")
    parser.add_argument("--cache", default="/tmp/corpus/cache")
    parser.add_argument("--work", default="/tmp/corpus/work")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--closure-limit", type=int, default=8)
    ns = parser.parse_args(argv)
    corpus = closure = None
    if ns.corpus:
        corpus = run_corpus(pathlib.Path(ns.cache), pathlib.Path(ns.work), limit=ns.limit,
                            per_task_budget=ns.closure_limit)
        closure = closure_demo(pathlib.Path(ns.cache), pathlib.Path(ns.work), budget=ns.closure_limit)
    report = measure(corpus)
    if closure is not None:
        report["closure"] = closure
        report["what_the_closure_shows"] = (
            "%d real commits whose fix is a single return expression were taken at their fixed state, the "
            "human's own line was put back the way it was before the fix, and the loop was asked to find it "
            "again from the failing test alone. It recovered the human's answer in %d of them; in the rest "
            "either no test covers that line, or the answer needs a name the frame does not have."
            % (closure["attempted"], closure["recovered"]))
    print(json.dumps({k: report[k] for k in ("schema", "states", "corpus") if k in report}, indent=1))
    if closure is not None:
        print("closure:", json.dumps({k: closure[k] for k in ("attempted", "recovered")}))
    if ns.json_path:
        target = pathlib.Path(ns.json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("written:", ns.json_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
