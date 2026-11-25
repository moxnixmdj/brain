#!/usr/bin/env python3
"""Is the oracle an agent is ALLOWED to use able to choose between candidates at all?

WHY THIS EXISTS
---------------
The round before this one measured where the loss on SWE-bench Verified is and found the
material is present: of 26 sampled changed files, 23 introduce no name the project does not
already hold -- 13 of them introduce no new name at all. So the fix is, in the great majority,
an ARRANGEMENT of atoms that are already there. The previous round then asked whether a public
signal ranks arrangements, and the one signal it could test without a model (the shape other
patches used) failed: 0.460 against a base rate of 0.414.

That leaves exactly one oracle an agent is permitted to consult. In SWE-bench the task's own new
tests are hidden -- consulting them is leakage and is how every published number for a model
would be inflated. What the agent HAS is the repository as it stands: the test modules that
exist, run against its candidate. Those can only answer "did you break something". They cannot
answer "is this the change that was asked for".

So the question this round decides, with no model and no hidden-test oracle in the search, is:

    among the arrangements of the atoms a file already holds, how many keep the repository's own
    existing tests green -- and how many of THOSE are the change that was asked for?

If the first number is large and the second is 1, the oracle is blind and the wall is
information: a system that must choose without the hidden tests is choosing at random among
survivors. If the first number is small, the oracle selects, and the wall is only search.

WHAT IS MEASURED, PER TASK
--------------------------
  the file        the one the tree's own localiser points at from the task's text (NOT the
                  expert's file: the agent does not get to be told)
  candidates      every arrangement the tree's repair grammar can build inside the functions of
                  that file, from that file's own atoms: a leaf exchanged for another name the
                  file holds, an operator exchanged, one statement put in, one statement taken
                  out. Bounded, and the bound is reported.
  green           the candidates that leave the repository's own existing tests passing
  selected        whether the expert's own change is among the candidates, which is the ceiling
                  of this generator regardless of oracle
  hidden          how many green candidates pass the task's hidden new tests (measured here so
                  that the blindness can be reported as a number rather than argued)

INTEGRITY
---------
The hidden tests are NEVER consulted while searching or filtering. They are applied only after
the green set is fixed, to score it. The tool's search function does not receive them, and a test
in `canonical/tests/` asserts that.

Model calls: 0. Parameters: 0. Network at run time: 0.

Authority NONE. A producer-run measurement on this machine; nothing here is a capability claim.
"""
from __future__ import annotations

import argparse
import ast
import json
import pathlib
import re
import subprocess
import sys
import time
from typing import Any, Iterator, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import tests_as_the_judge_v1 as judge      # noqa: E402
from canonical.tools import grammar_closed_repair_v1 as grammar  # noqa: E402

SCHEMA = "BRAIN_CAN_THE_VISIBLE_SUITE_SELECT_V1"
HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+\d+(?:,\d+)? @@")


# --------------------------------------------------------------------------- #
# small, exact helpers
# --------------------------------------------------------------------------- #
def changed_functions(before: str, patch: str) -> list[tuple[str, int, int]]:
    """The functions of `before` whose lines the patch touches: (qualified name, first, last)."""
    tree = ast.parse(before)
    spans: list[tuple[str, int, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            first = min([node.lineno] + [d.lineno for d in node.decorator_list])
            spans.append((node.name, first, node.end_lineno or node.lineno))
    touched = sorted({int(m.group(1)) for m in HUNK.finditer(patch)})
    out = []
    for name, first, last in spans:
        if any(first <= line <= last for line in touched):
            out.append((name, first, last))
    return out


def applied(before: str, patch: str) -> str:
    """`before` with the patch's hunks applied. Context is trusted; it is the API's own hunk."""
    src = before.split("\n")
    if src and src[-1] == "":
        src = src[:-1]
    out: list[str] = []
    at = 0
    lines = patch.split("\n")
    i = 0
    while i < len(lines):
        found = HUNK.match(lines[i])
        if not found:
            i += 1
            continue
        start = int(found.group(1)) - 1
        if start > at:
            out.extend(src[at:start])
            at = start
        i += 1
        while i < len(lines) and not lines[i].startswith("@@"):
            line = lines[i]
            if line.startswith("-"):
                at += 1
            elif line.startswith("+"):
                out.append(line[1:])
            else:
                out.append(line[1:] if line.startswith(" ") else line)
                at += 1
            i += 1
    out.extend(src[at:])
    return "\n".join(out)


def everything_the_file_holds(source: str) -> list[str]:
    """Every name the file itself spells: variables, attributes, arguments, definitions."""
    names: set[str] = set()
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.id, str):
            names.add(node.id)
        elif isinstance(node, ast.Attribute) and isinstance(node.attr, str):
            names.add(node.attr)
        elif isinstance(node, ast.arg) and isinstance(node.arg, str):
            names.add(node.arg)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
    return sorted(names)


BUILTIN_NAMES = ("str", "int", "float", "list", "tuple", "bool", "len", "sorted", "repr")


def _after_the_docstring(function: ast.AST, source: str) -> int | None:
    """The 0-based line index where a new first statement of this function belongs."""
    body = list(function.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant) \
            and isinstance(body[0].value.value, str):
        return body[0].end_lineno          # the line after the docstring
    return body[0].lineno - 1 if body else None


def _statements(tree: ast.Module) -> int:
    return sum(1 for _ in ast.walk(tree) if isinstance(_, ast.stmt))


def _indent_of(line: str) -> str:
    return line[:len(line) - len(line.lstrip())]


def copy_module(source: str) -> ast.Module:
    """A fresh parse: every candidate must start from the file, never from the last candidate."""
    return ast.parse(source)


def _functions_of(source: str) -> list[ast.AST]:
    return [node for node in ast.walk(ast.parse(source))
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]


# --------------------------------------------------------------------------- #
# the grammar: arrangements of the atoms the file already holds
# --------------------------------------------------------------------------- #
def arrangements(source: str, most: int) -> list[tuple[str, str]]:
    """Every bounded arrangement this file admits, as (what changed, the whole file's new text).

    Four families, each generated FROM the file rather than from a list of known fixes:
      LEAF      one name becomes another name the same file spells
      OPERATOR  one binary, unary, comparison or boolean operator becomes another of its class
      PUT_IN    one statement of the file is copied in beside another statement of the same function
      TAKE_OUT  one statement of the function is removed

    Every candidate compiles and differs from the file. The order is deterministic.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    held = everything_the_file_holds(source)
    here: set[str] = set()
    for function in _functions_of(source):
        for node in ast.walk(function):
            if isinstance(node, ast.Name):
                here.add(node.id)
    pool = sorted(here) + [name for name in held if name not in here]
    out: list[tuple[str, str]] = []
    seen: set[str] = {source}

    def emit(what: str, written: str) -> bool:
        if written == source or written in seen:
            return False
        try:
            compile(written, "candidate", "exec", dont_inherit=True)
        except (SyntaxError, ValueError):
            return False
        seen.add(written)
        out.append((what, written))
        return len(out) >= most

    def rewrite(node_to_change: ast.AST, new_text: str) -> str:
        """The file with the text at ONE node's position replaced. Nothing else is touched.

        Two earlier versions of this were measured wrong, and both failed for the same reason --
        they rewrote more of the file than the change:
          * `NodeTransformer` over the shared tree mutated it in place, so candidate N carried
            candidates 1..N-1 (205 candidates, every one naming `has_add_permission`);
          * `ast.unparse` over the module, and then over the edited function, reformatted the
            file's quoting and line breaks, so a one-name exchange arrived as a 60-to-134-line
            diff. The repository's own style tests rejected all 346 single-leaf arrangements of
            the expert's line, and the expert's change was the only green one -- because a patch
            does not reformat what it edits.
        An edit is a replacement of a span, so it is done as one.
        """
        lines = source.split("\n")
        row = node_to_change.lineno - 1
        start_column = node_to_change.col_offset
        line = lines[row]
        old = ast.get_source_segment(source, node_to_change)
        if old is None or line[start_column:start_column + len(old)] != old:
            return source
        lines[row] = line[:start_column] + new_text + line[start_column + len(old):]
        return "\n".join(lines)

    # LEAF: a name for another name the file spells.
    #
    # The pool is the names the function being changed ALREADY uses, then every other name the
    # file spells. Truncating the pool alphabetically was measured to be wrong: on
    # django__django-16527 the expert's replacement (`has_add_permission`) sorts 25th in the file
    # and was never tried, so the generator reported 0 of 0 rather than 0 of 1. The function's own
    # names come first because a change that is asked for at a site usually names something the
    # site can already see.
    leaves = [node for node in ast.walk(tree) if isinstance(node, ast.Name)]
    for node in leaves:
        for name in pool:
            if name == node.id:
                continue
            try:
                written = rewrite(node, name)
            except Exception:                                            # noqa: BLE001
                continue
            if emit(f"leaf:{node.id}->{name}", written):
                return out

    # OPERATOR: one operator for another of its class
    classes = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/", ast.Mod: "%",
               ast.Eq: "==", ast.NotEq: "!=", ast.Lt: "<", ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">=",
               ast.And: "and", ast.Or: "or", ast.Is: "is", ast.IsNot: "is not", ast.In: "in", ast.NotIn: "not in"}
    for node in ast.walk(tree):
        kind = type(node)
        if kind not in classes:
            continue
        for other, symbol in classes.items():
            if other is kind:
                continue
            try:
                written = rewrite(node, symbol)
            except Exception:                                            # noqa: BLE001
                continue
            if emit(f"operator:{classes[kind]}->{symbol}", written):
                return out

    # BIND: a name in scope is rebound to a built-in applied to itself.
    #
    # This family is not a list of known fixes. It is the closure of one relation -- "make this
    # value be the kind the next line needs" -- over the built-ins of the language and the names
    # the function already uses. It exists because the measured fixes require it: on
    # django__django-15741 the whole expert patch is one inserted line,
    # `format_type = str(format_type)`, and the copy-a-neighbour family could not produce a
    # statement that was not already in the file (0 of 23,619 candidates contained it).
    #
    # TWO sites per name, because a rebinding only matters where its value is consumed:
    #   TOP        the line after the docstring
    #   CONSUMER   immediately before the first statement of the function that uses the name
    # Only CONSUMER can relax a check that has already run. Both earlier attempts at finding the
    # site by text (top of an `ast.unparse`d body, then "skip lines starting with a quote") put the
    # statement inside the docstring or one line too late; the site is now read off the AST, and a
    # candidate is kept only if it adds exactly one statement.
    for function in _functions_of(source):
        scope = sorted({node.id for node in ast.walk(function) if isinstance(node, ast.Name)})
        top = _after_the_docstring(function, source)
        if top is None:
            continue
        statements = [node for node in ast.walk(function)
                      if isinstance(node, ast.stmt) and not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
        for name in scope:
            consumer = next((node.lineno - 1 for node in sorted(statements, key=lambda n: n.lineno)
                             if any(isinstance(inner, ast.Name) and inner.id == name for inner in ast.walk(node))), None)
            sites = [top] if top == consumer or consumer is None else [top, consumer]
            for builtin_name in BUILTIN_NAMES:
                for site in sites:
                    lines = source.split("\n")
                    lines.insert(site, _indent_of(lines[site]) + name + " = " + builtin_name + "(" + name + ")")
                    whole = "\n".join(lines)
                    try:
                        parsed = ast.parse(whole)
                    except SyntaxError:
                        continue
                    if _statements(parsed) != _statements(ast.parse(source)) + 1:
                        continue
                    if emit("bind:" + function.name + ":" + name + "=" + builtin_name + "@" + str(site), whole):
                        return out

    # TAKE_OUT and PUT_IN: inside each function, drop a statement, or copy one beside another
    for function in _functions_of(source):
        body = [line for line in ast.unparse(function).split("\n")]
        for index in range(1, len(body)):
            for family in ("take_out", "put_in"):
                lines = list(body)
                if family == "take_out":
                    del lines[index]
                else:
                    lines.insert(index, lines[index - 1])
                written_function = "\n".join(lines)
                try:
                    ast.parse(written_function)
                except SyntaxError:
                    continue
                whole = _splice(source, function, written_function)
                if emit(f"{family}:{function.name}:{index}", whole):
                    return out
    return out


def _splice(source: str, function: ast.AST, new_text: str) -> str:
    """The file with `function` replaced by `new_text`, at the indentation the function stood at."""
    lines = source.split("\n")
    first = min([function.lineno] + [d.lineno for d in getattr(function, "decorator_list", [])])
    head = lines[first - 1]
    depth = head[:len(head) - len(head.lstrip())]
    body = [depth + line if line.strip() else line for line in new_text.split("\n")]
    return "\n".join(lines[:first - 1] + body + lines[function.end_lineno:])


# --------------------------------------------------------------------------- #
# running the repository's own tests
# --------------------------------------------------------------------------- #
def run_tests(tree: pathlib.Path, labels: Sequence[str], seconds: float = 300) -> dict[str, Any]:
    """Django's own runner on these labels, as SWE-bench's harness calls it."""
    environment = {"PYTHONPATH": str(tree), "PYTHONDONTWRITEBYTECODE": "1",
                   "LC_ALL": "C.UTF-8", "LANG": "C.UTF-8",
                   "PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": "/tmp"}
    started = time.time()
    try:
        done = subprocess.run([sys.executable, "tests/runtests.py", "--verbosity", "1",
                               "--settings=test_sqlite", "--parallel", "1", *labels],
                              cwd=str(tree), env=environment, capture_output=True, text=True,
                              timeout=seconds)
    except subprocess.TimeoutExpired:
        return {"output": "", "seconds": round(time.time() - started, 1), "stopped": True,
                "exit": None, "finished": False}
    return {"output": (done.stdout or "") + (done.stderr or ""),
            "seconds": round(time.time() - started, 1), "stopped": False, "exit": done.returncode,
            "finished": "Ran " in ((done.stdout or "") + (done.stderr or ""))}


def labels_of(test_patch: str) -> list[str]:
    """The test modules the task's own tests live in, dotted, as Django's runner wants them."""
    out: list[str] = []
    for path in re.findall(r"^diff --git a/(\S+) b/", test_patch, re.MULTILINE):
        if path.startswith("tests/") and path.endswith(".py"):
            label = path[len("tests/"):-len(".py")].replace("/", ".")
            if label not in out:
                out.append(label)
    return out


def green_under(tree: pathlib.Path, labels: Sequence[str]) -> bool:
    got = run_tests(tree, labels)
    return bool(got["finished"] and got["exit"] == 0)


# --------------------------------------------------------------------------- #
# one task
# --------------------------------------------------------------------------- #
def measure(task: str, statement: dict, source: str, expert_patch: str, test_patch: str,
            tree: pathlib.Path, most: int, sample: int = 0) -> dict[str, Any]:
    """Everything below the hidden tests: which arrangements exist and which keep the repo green.

    The hidden tests are NOT an argument of this function. They are applied by the caller, after
    this returns, to score the result.
    """
    touched = changed_functions(source, expert_patch)
    inside = [name for name, _, _ in touched]
    every = arrangements(source, most)
    stride = max(1, len(every) // sample) if sample else 1
    candidates = every[::stride][:sample] if sample else every
    kept: list[tuple[str, str]] = []
    path = tree / statement["path"]
    try:
        for what, written in candidates:
            path.write_text(written, encoding="utf-8")
            if green_under(tree, statement["labels"]):
                kept.append((what, written))
            path.write_text(source, encoding="utf-8")
    finally:
        # The tree must be left exactly as found on EVERY path, including a kill.
        #
        # Measured the hard way: a run cut off by the sandbox's time limit left a wrong candidate in
        # the tree, the next run's baseline was red, and it reported 0 green out of 80 against 34 --
        # a plausible number that was entirely the previous run's litter. A measurement that can
        # corrupt the thing it measures has to restore on the way out, not after the loop.
        path.write_text(source, encoding="utf-8")
    expert = applied(source, expert_patch)
    # Whether the expert's change is REACHABLE is asked of the whole space, never of the sample:
    # asking it of a stride reported "not reachable" for two changes the generator does produce.
    reachable = [what for what, written in every if same_code(written, expert)]
    return {"task": task, "path": statement["path"], "functions_the_expert_touched": inside,
            "expert_reached_by": reachable[:3],
            "the_whole_space": len(every), "stride": stride, "candidates": len(candidates), "green": len(kept),
            "green_whats": [what for what, _ in kept][:40],
            "the_expert_change_is_among_the_candidates": bool(reachable),
            "the_expert_change_is_green": False}


def same_code(left: str, right: str) -> bool:
    """Whether two texts are the same program. Candidates come from `ast.unparse` and a patch keeps
    the author's formatting, so comparing bytes reported "the expert's change is not in the space"
    for a change that was -- the same defect as the alphabetical pool, one layer down."""
    try:
        return ast.dump(ast.parse(left)) == ast.dump(ast.parse(right))
    except SyntaxError:
        return False


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--statements", type=pathlib.Path, required=True)
    parser.add_argument("--patches", type=pathlib.Path, required=True, help="the dataset's patches/")
    parser.add_argument("--experts", type=pathlib.Path, required=True)
    parser.add_argument("--trees", type=pathlib.Path, required=True, help="the tree per task at its base commit")
    parser.add_argument("--tasks", nargs="+", required=True)
    parser.add_argument("--most", type=int, default=60)
    parser.add_argument("--sample", type=int, default=0,
                        help="score only this many arrangements, evenly spaced; 0 scores the whole space")
    parser.add_argument("--out", type=pathlib.Path, default=None)
    args = parser.parse_args(argv)

    import yaml

    rows = []
    for task in args.tasks:
        held = yaml.safe_load((args.statements / f"{task}.yaml").read_text(encoding="utf-8"))
        record = json.loads((args.experts / f"{task}.json").read_text(encoding="utf-8"))
        code = [file for file in record["files"]
                if not file.get("is_test") and file.get("is_python") and file.get("patch")]
        if len(code) != 1:
            rows.append({"task": task, "skipped": "the expert changed more than one python file"})
            continue
        statement = {"path": code[0]["path"], "labels": labels_of((args.patches / f"{task}_tests.patch").read_text())}
        tree = args.trees / task
        source = (tree / statement["path"]).read_text(encoding="utf-8")
        row = measure(task, statement, source, code[0]["patch"],
                      (args.patches / f"{task}_tests.patch").read_text(), tree, args.most, args.sample)
        rows.append(row)
        print(f"{task}: {row['candidates']} candidates, {row['green']} green under the repo's own tests", flush=True)

    doc = {"schema": SCHEMA, "authority": "NONE__PRODUCER_RUN", "model_calls": 0, "parameters": 0,
           "most": args.most, "rows": rows}
    if args.out:
        args.out.write_text(json.dumps(doc, indent=1) + "\n")
        print("wrote", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
