"""At a fault, pass the live value the callee wanted.

Wall 2, measured (`THE_ORACLE_WAS_NOT_HANDED_TO_US`): on `urllib3 77fa67aaf2` the fix
is one character inside a module-level regex constant (`_HOST_PORT_PAT` gains `0*`),
which the guard-rule engine cannot see. On `jinja d05bd3858c` the fix passes a live
`context` object to a call that omitted it, because the callee defaults it to `None`
and then raises when it is absent.

A first attempt at a blind "pass the omitted argument" rule fired **402 times across
11 repos** and every instance I inspected was wrong: `dict.pop(default=...)`,
`astuple(recurse=..., filter=...)`, `attrib(kw_only=...)` are all optional parameters
omitted on purpose. Arity is not evidence. Only a *raised exception* is evidence.

So the rule here is gated on a runtime fault, and it is deliberately narrow:

    At the frame that raised, find the Call node on that line.
    Let M = parameters the callee declares, minus parameters the call supplies.
    Let L = names live in the enclosing scope at that line.
    Candidate = M ∩ L, restricted to exactly one element.
    Apply by appending that name to the call, then require:
        the fault's exception disappears, and
        the whole existing suite still passes.

The restriction to a single candidate is what keeps it honest: when two live names
could fill the slot, the rule declines rather than guess. Nothing here knows what the
human fix was.

    python canonical/tools/pass_what_the_callee_wanted_v1.py \
        --oracle-corpus /tmp/repro_corpus/corpus.json \
        --receipt canonical/verification/PASS_WHAT_THE_CALLEE_WANTED_20261124_V1.json
"""
from __future__ import annotations

import argparse
import ast
import json
import pathlib
import sys
import textwrap
from typing import Any

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
for path in (str(HERE), str(REPO)):
    if path not in sys.path:
        sys.path.insert(0, path)

import identify_a_real_bugs_fix_v1 as identify  # noqa: E402

# Install a trace hook in a child process that reports the raising frame and the
# live local names there. Kept as a source string: it must run inside the project's
# own interpreter session, with the project's own imports.
TRACER = textwrap.dedent('''
    import json, os, sys, traceback

    OUT = os.environ["BRAIN_FAULT_OUT"]
    WANT = os.environ.get("BRAIN_FAULT_TARGET", "")

    class Recorder:
        def __init__(self):
            self.rows = []
        def __call__(self, frame, event, arg):
            if event != "exception":
                return self
            exc, value, tb = arg
            name = frame.f_code.co_filename
            if WANT and not name.endswith(WANT):
                return self
            names = {k: type(v).__name__ for k, v in frame.f_locals.items()}
            self.rows.append({"file": name, "func": frame.f_code.co_name,
                              "line": frame.f_lineno,
                              "exc": getattr(exc, "__name__", str(exc)),
                              "msg": str(value)[:200],
                              "locals": names})
            return self

    rec = Recorder()
    sys.settrace(rec)
    try:
        exec(compile(open(sys.argv[1]).read(), sys.argv[1], "exec"),
             {"__name__": "__main__"})
    finally:
        sys.settrace(None)
    with open(OUT, "w") as fh:
        json.dump(rec.rows, fh)
''')


def find_call_on_line(source: str, line: int) -> ast.Call | None:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    best = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and node.lineno == line:
            best = node
    return best


def enclosing_defs(source: str, line: int) -> list[ast.FunctionDef]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    found = [n for n in ast.walk(tree)
             if isinstance(n, ast.FunctionDef)
             and n.lineno <= line <= (n.end_lineno or n.lineno)]
    return sorted(found, key=lambda f: f.lineno)


def callee_params(source: str, call: ast.Call,
                  search_roots: list[pathlib.Path] | None = None) -> list[str] | None:
    """Parameters of the callee, in this file or anywhere in the package.

    The jinja fix passes `context` to `Environment.call_test`, which is defined in
    `environment.py` while the call site is in `filters.py`. A same-file-only search
    finds nothing on the very row the rule was built for -- so the package is searched,
    and if the name is defined more than once with different signatures the rule
    declines rather than pick.
    """
    name = ast.unparse(call.func).split(".")[-1]
    found: set[tuple[str, ...]] = set()
    trees: list[str] = [source]
    for root in (search_roots or []):
        for py in pathlib.Path(root).rglob("*.py"):
            try:
                trees.append(py.read_text(encoding="utf-8", errors="replace"))
            except OSError:
                continue
    for text in trees:
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == name:
                args = [a.arg for a in node.args.args]
                found.add(tuple(args[1:] if args and args[0] in ("self", "cls") else args))
    if len(found) != 1:
        return None            # undefined, or ambiguous: no proposal
    return list(next(iter(found)))


def propose_patch(source: str, fault: dict[str, Any],
                  search_roots: list[pathlib.Path] | None = None) -> dict[str, Any] | None:
    """Return {line, symbol, old, new} for the single defensible repair, or None."""
    line = fault["line"]
    call = find_call_on_line(source, line)
    if call is None:
        return None
    params = callee_params(source, call, search_roots)
    if not params:
        return None
    supplied = {x.id for a in call.args for x in ast.walk(a) if isinstance(x, ast.Name)}
    supplied |= {k.arg for k in call.keywords if k.arg}
    missing = [p for p in params if p not in supplied]
    if not missing:
        return None
    live = set(fault.get("locals") or {})
    for definition in enclosing_defs(source, line):
        live |= {a.arg for a in definition.args.args}
        live |= {a.arg for a in definition.args.kwonlyargs}
    candidates = [p for p in missing if p in live]
    if len(candidates) != 1:
        # zero candidates: nothing in scope to pass. two or more: a guess.
        return None
    symbol = candidates[0]
    lines = source.splitlines(keepends=True)
    row = lines[line - 1]
    close = row.rstrip().rfind(")")
    if close < 0:
        return None
    patched = row[:close] + f", {symbol}" + row[close:]
    try:
        ast.parse("".join(lines[:line - 1]) + patched + "".join(lines[line:]))
    except SyntaxError:
        return None
    return {"line": line, "symbol": symbol, "old": row.rstrip("\n"),
            "new": patched.rstrip("\n"),
            "callee": ast.unparse(call.func)}


def apply_and_verify(worktree: pathlib.Path, source_path: str, patch: dict[str, Any],
                     seconds: int) -> dict[str, Any]:
    """Two conditions, both required: the fault disappears AND the suite still passes."""
    target = worktree / source_path
    original = target.read_text(encoding="utf-8", errors="replace")
    lines = original.splitlines(keepends=True)
    lines[patch["line"] - 1] = patch["new"] + "\n"
    patched = "".join(lines)
    try:
        ast.parse(patched)
    except SyntaxError as error:
        return {"accepted": False, "reason": f"SYNTAX_{error.msg}"}
    target.write_text(patched, encoding="utf-8")
    try:
        verdicts, _ = identify.run_tests_full(worktree, "tests/", seconds)
        failed = [n for n, v in (verdicts or {}).items() if str(v).upper() == "FAILED"]
        passed = [n for n, v in (verdicts or {}).items() if str(v).upper() == "PASSED"]
        return {"accepted": not failed and bool(passed),
                "reason": "suite green" if not failed else f"{len(failed)} regressions",
                "passed": len(passed), "failed": len(failed),
                "failing_names": failed[:5]}
    finally:
        target.write_text(original, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=pathlib.Path, required=True,
                        help="worktree of the parent commit")
    parser.add_argument("--source", required=True, help="repo-relative source path")
    parser.add_argument("--fault-line", type=int, required=True)
    parser.add_argument("--locals", default="", help="comma-separated live names")
    parser.add_argument("--receipt", type=pathlib.Path, required=True)
    parser.add_argument("--seconds", type=int, default=300)
    args = parser.parse_args(argv)

    source = (args.target / args.source).read_text(encoding="utf-8", errors="replace")
    fault = {"line": args.fault_line,
             "locals": {n: "" for n in args.locals.split(",") if n.strip()}}
    patch = propose_patch(source, fault, [args.target / "src", args.target])
    receipt: dict[str, Any] = {"schema": "PASS_WHAT_THE_CALLEE_WANTED_V1",
                              "source": args.source, "fault_line": args.fault_line,
                              "proposal": patch}
    if patch is None:
        receipt["verdict"] = "DECLINED__NO_UNIQUE_CANDIDATE"
    else:
        receipt["verification"] = apply_and_verify(args.target, args.source, patch,
                                                   args.seconds)
        receipt["verdict"] = ("ACCEPTED" if receipt["verification"]["accepted"]
                              else "REFUSED__" + receipt["verification"]["reason"])
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=1), encoding="utf-8")
    print(json.dumps(receipt, indent=1)[:1200])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
