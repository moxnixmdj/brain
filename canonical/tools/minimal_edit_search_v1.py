#!/usr/bin/env python3
"""One generic mechanism instead of a hand-written operator per bug family.

WHY THIS REPLACES THE OPERATOR SET
----------------------------------
Six rounds produced one operator per failure family that I happened to look at:
KEYWORD_APPLY, ATTRIBUTE_SET, COLLECTION_EXTEND, MESSAGE_DEQUOTE, WRAP_EXCEPTION. Each was written *after*
watching a specific task fail. V36 measured the consequence: on 20 tasks never used for design, they solve 0.
V37 removed the last excuse by showing they solve 0 of 6 tasks whose fixes are four lines or fewer.

The problem was never that the operators were wrong. It was that a human wrote them from examples.

THE MECHANISM
-------------
Localise one file (assertion symbols, literals, or reachability -- V35 measured this at 17/28 top-1), then
enumerate MINIMAL EDITS of that file drawn from a small set of universal forms:

    FLIP      every token that has a documented opposite  ( * <-> + , <= -> < , is -> is not , == -> != )
    BIND      insert `name = <expression already in the file>` directly above a use of `name`
    GUARD     insert `if <the test's own condition, negated>: raise <the exception the test wants>`
    REBIND    replace a name with a name that exists in the file and shares its suffix
    APRIME    a quantifier star becomes plus, a plus becomes star, inside any string
    MOVE      hoist an expression to a name above the line that uses it

Nothing here knows what a regex is, what a licence is, or what a requirement is. The forms are blind. The
interpreter decides which edit is right, exactly as before, and the whole test module plus its directory must
stay green.

THE RISK, STATED BEFORE MEASURING
---------------------------------
A generic search over a big file is a much larger space, and most of it is noise. If this solves nothing, the
honest reading is that blind minimal edits do not find real fixes, not that the search was unlucky. The
candidate budget is therefore capped and the budget is reported with the result.

Zero model calls, own weights (there are none), external store only, no network at run time.
"""
from __future__ import annotations

import argparse
import ast
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Sequence

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from canonical.tools.behavioural_emission_v2 import (  # noqa: E402
    CLONES, SEED, CURRENT_SHA, env_for, is_cosmetic, parse, pytest_file, pytest_node, run,
    source_files, writable,
)

SCHEMA = "BRAIN_MINIMAL_EDIT_SEARCH_V1"
TASKS = REPO / "canonical" / "corpus" / "fail_to_pass_tasks_20261124_V1.json"
BUDGET = 60

# documented opposites only. This is a vocabulary, not a rule about any particular bug.
OPPOSITES = {
    "*": ["+"],
    "+": ["*"],
    "-": ["+"],
    "<": ["<=", ">"],
    "<=": ["<", ">="],
    ">": [">=", "<"],
    ">=": [">", "<="],
    "==": ["!="],
    "!=": ["=="],
    "is": ["is not"],
    "is not": ["is"],
    "not in": ["in"],
    "in": ["not in"],
    "and": ["or"],
    "or": ["and"],
    "None": ["True", "False", "0", '""'],
    "True": ["False", "None"],
    "False": ["True", "None"],
}


def test_conditions(checkout: pathlib.Path, test_file: str) -> list[str]:
    """Every comparison and every argument the test uses, in source form.

    This is not leakage of an answer: it is the task statement. The test is the specification, and every
    candidate built from it is still judged by executing the test.
    """
    path = checkout / test_file
    if not path.exists():
        return []
    try:
        tree = ast.parse(path.read_text(errors="ignore"))
    except SyntaxError:
        return []
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            found.append(ast.unparse(node))
        elif isinstance(node, ast.Call):
            for argument in node.args:
                if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
                    found.append(repr(argument.value))
    return list(dict.fromkeys(found))[:40]


def expected_exception(output: str, test_source: str) -> str | None:
    match = re.search(r"DID NOT RAISE (?:<class '([\w.]+)'>|([A-Za-z_][\w.]*))", output)
    if match:
        return (match.group(1) or match.group(2)).split(".")[-1]
    # the test states its own expectation: pytest.raises(X) / assertRaises(X)
    match = re.search(r"(?:pytest\.raises|assertRaises)\(\s*([A-Za-z_][\w.]*)", test_source)
    if match:
        return match.group(1).split(".")[-1]
    return None


# ---------------------------------------------------------------- the universal edit forms

def flip_edits(path: pathlib.Path, text: str) -> list[dict[str, Any]]:
    """Substitute a token for one of its documented opposites, at every occurrence."""
    out: list[dict[str, Any]] = []
    for token, opposites in OPPOSITES.items():
        pattern = rf"(?<![\w]){re.escape(token)}(?![\w])" if token[0].isalpha() else re.escape(token)
        for match in re.finditer(pattern, text):
            for opposite in opposites:
                new_text = text[:match.start()] + opposite + text[match.end():]
                if new_text == text:
                    continue
                out.append({"path": path, "text": new_text, "family": "FLIP",
                            "why": f"token {token!r} -> {opposite!r} at offset {match.start()}"})
                if len(out) >= BUDGET:
                    return out
    return out


def bind_edits(path: pathlib.Path, text: str) -> list[dict[str, Any]]:
    """A name is used but never bound in its scope: bind it to an expression the file already contains."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    lines = text.splitlines(keepends=True)
    expressions = [ast.unparse(node) for node in ast.walk(tree)
                   if isinstance(node, (ast.Attribute, ast.Subscript, ast.Call))
                   and 3 < len(ast.unparse(node)) <= 50]
    out: list[dict[str, Any]] = []
    for function in [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]:
        body_start = function.body[0].lineno if function.body else function.lineno + 1
        loaded = [node.id for node in ast.walk(function) if isinstance(node, ast.Name)
                  and isinstance(node.ctx, ast.Load)]
        stored = {node.id for node in ast.walk(function) if isinstance(node, ast.Name)
                  and isinstance(node.ctx, (ast.Store, ast.Param))}
        arguments = {argument.arg for argument in function.args.args}
        missing = [name for name in dict.fromkeys(loaded) if name not in stored | arguments]
        for name in missing[:4]:
            for expression in list(dict.fromkeys(expressions))[:12]:
                index = body_start - 1
                if index >= len(lines):
                    continue
                indent = re.match(r"\s*", lines[index]).group(0)
                new_lines = list(lines)
                new_lines[index] = f"{indent}{name} = {expression}\n" + new_lines[index]
                out.append({"path": path, "text": "".join(new_lines), "family": "BIND",
                            "why": f"{name!r} is used but never bound in {function.name}(); bind it to "
                                   f"{expression!r}"})
                if len(out) >= BUDGET:
                    return out
    return out


def guard_edits(path: pathlib.Path, text: str, conditions: list[str],
                exception: str | None) -> list[dict[str, Any]]:
    """Insert the test's own condition at the top of a function, raising the exception it demands."""
    if not conditions:
        return []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    lines = text.splitlines(keepends=True)
    out: list[dict[str, Any]] = []
    for function in [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]:
        if not function.body:
            continue
        index = function.body[0].lineno - 1
        if index >= len(lines):
            continue
        indent = re.match(r"\s*", lines[index]).group(0)
        body_indent = indent + "    "
        for condition in conditions[:6]:
            negated = condition
            for swap in (("==", "!="), ("!=", "=="), (" in ", " not in "), ("not in", "in")):
                if swap[0] in negated:
                    negated = negated.replace(swap[0], swap[1], 1)
                    break
            if exception:
                block = (f"{indent}if {negated}:\n"
                         f"{body_indent}raise {exception}({condition!r})\n")
            else:
                block = f"{indent}if {negated}:\n{body_indent}raise ValueError({condition!r})\n"
            new_lines = list(lines)
            new_lines[index] = block + new_lines[index]
            out.append({"path": path, "text": "".join(new_lines), "family": "GUARD",
                        "why": f"guard at the top of {function.name}(): if {negated}, raise "
                               f"{exception or 'ValueError'}"})
            if len(out) >= BUDGET:
                return out
    return out


def rebind_edits(path: pathlib.Path, text: str) -> list[dict[str, Any]]:
    """A word is replaced by another word the file already uses that shares its tail.

    `cls.__dict__` -> `Metadata.__dict__` is this shape. So is any substitution of a receiver or receiver
    chain, and the form is blind to which one is right.
    """
    tokens = list(dict.fromkeys(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", text)))
    out: list[dict[str, Any]] = []
    for token in tokens:
        if len(token) < 3 or token in {"self", "None", "True", "False", "def", "return", "import"}:
            continue
        tail = token[-4:]
        for other in tokens:
            if other == token or len(other) < 3 or other[-4:] != tail:
                continue
            for match in re.finditer(rf"(?<![\w.]){re.escape(token)}(?![\w])", text):
                out.append({"path": path, "text": text[:match.start()] + other + text[match.end():],
                            "family": "REBIND", "why": f"{token!r} -> {other!r} sharing tail {tail!r}"})
                if len(out) >= BUDGET:
                    return out
    return out


def quantifier_edits(path: pathlib.Path, text: str) -> list[dict[str, Any]]:
    """Inside any single-line string literal, a quantifier character gains or loses something.

    Operates on the raw text of the literal, not on a re-rendered AST constant: an f-string never
    round-trips through prefix + quote + value + quote, so an AST-based version silently skipped every
    f-string message in the file -- including the one it was written for. Found by calibration.
    """
    lines = text.splitlines(keepends=True)
    out: list[dict[str, Any]] = []
    quote_match = re.compile(r"(?P<quote>\"\"\"|'''|'|\")(?P<body>.{0,400}?)(?P=quote)")
    for line_index, line in enumerate(lines):
        if line.lstrip().startswith("#"):
            continue
        for match in quote_match.finditer(line):
            quote = match.group("quote")
            if len(quote) == 3:
                continue
            body = match.group("body")
            for offset, char in enumerate(body):
                if char not in "*+?":
                    continue
                for replacement in ("*", "+", "?"):
                    if replacement == char:
                        continue
                    edited = body[:offset] + replacement + body[offset + 1:]
                    start_at, end_at = match.span("body")
                    new_lines = list(lines)
                    new_lines[line_index] = line[:start_at] + edited + line[end_at:]
                    out.append({"path": path, "text": "".join(new_lines), "family": "QUANTIFIER",
                                "why": f"quantifier {char!r} -> {replacement!r} in a literal at line "
                                       f"{line_index + 1}"})
                    if len(out) >= BUDGET:
                        return out
    return out


def pool_for(checkout: pathlib.Path, task: dict[str, Any], facts: dict[str, Any],
             output: str, original: dict[pathlib.Path, str]) -> list[dict[str, Any]]:
    conditions = test_conditions(checkout, task["test"])
    test_source = (checkout / task["test"]).read_text(errors="ignore") \
        if (checkout / task["test"]).exists() else ""
    exception = expected_exception(output, test_source)
    # interleave by family so no single noisy family can consume the whole budget before a precise one runs
    families: list[list[dict[str, Any]]] = [[], [], [], [], []]
    for path, text in original.items():
        if path.name == "__init__.py":
            continue
        families[0] += quantifier_edits(path, text)
        families[1] += guard_edits(path, text, conditions, exception)
        families[2] += rebound(path, text)
        families[3] += bind_edits(path, text)
        families[4] += flip_edits(path, text)[:12]
    pool = []
    for rank in range(max((len(family) for family in families), default=0)):
        for family in families:
            if rank < len(family):
                pool.append(family[rank])
    # deterministic order, deduplicated by the resulting text of the file it edits
    seen: set[tuple[str, int]] = set()
    unique: list[dict[str, Any]] = []
    for candidate in pool:
        key = (str(candidate["path"]), hash(candidate["text"]))
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)
    return unique[:BUDGET]


def rebound(path: pathlib.Path, text: str) -> list[dict[str, Any]]:
    return rebind_edits(path, text)[:12]


def attempt(checkout: pathlib.Path, task: dict[str, Any]) -> dict[str, Any]:
    node = (task["failed_nodes"] or [task["test"]])[0]
    before = pytest_node(checkout, node)
    output = (before.stdout or "") + (before.stderr or "")
    facts = parse(output)
    CURRENT_SHA[0] = task["sha"]
    original: dict[pathlib.Path, str] = {}
    for path in source_files(checkout, facts):
        try:
            original[path] = path.read_text()
        except (OSError, UnicodeDecodeError):
            continue
    if not original:
        return {"class": "REFUSED", "why": "no writable source file could be located"}
    pool = pool_for(checkout, task, facts, output, original)
    tried = 0
    for candidate in pool:
        tried += 1
        try:
            candidate["path"].write_text(candidate["text"])
            if pytest_node(checkout, node).returncode != 0:
                continue
            if pytest_file(checkout, task["test"]).returncode != 0:
                continue
            directory = pytest_file(checkout, str(pathlib.Path(task["test"]).parent))
            directory_output = (directory.stdout or "") + (directory.stderr or "")
            collection_only = (directory.returncode == 2 and "failed" not in directory_output)
            if directory.returncode != 0 and not collection_only:
                continue
            diff = run(["git", "diff", "--", str(candidate["path"].relative_to(checkout))],
                       checkout).stdout
            return {"class": "SOLVED", "family": candidate["family"], "why": candidate["why"],
                    "tried": tried, "diff": diff, "diff_bytes": len(diff),
                    "cosmetic": is_cosmetic(candidate, original)}
        finally:
            candidate["path"].write_text(original[candidate["path"]])
    return {"class": "REFUSED", "tried": tried, "pool_size": len(pool),
            "why": f"none of {tried} blind minimal edits turned the node green"}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--only", default=None)
    parser.add_argument("--corpus", default=str(TASKS))
    parser.add_argument("--clones", default=None)
    parser.add_argument("--seed", default=None)
    parser.add_argument("--keep", default=None)
    args = parser.parse_args(argv)
    started = time.time()

    if args.clones:
        CLONES.update(json.loads(pathlib.Path(args.clones).read_text()))
    if args.seed:
        SEED.update(json.loads(pathlib.Path(args.seed).read_text()))
    tasks = json.loads(pathlib.Path(args.corpus).read_text())["tasks"]
    workdir = (pathlib.Path(args.keep) if args.keep
               else pathlib.Path(tempfile.mkdtemp(prefix="brain-minimal-")))
    workdir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    try:
        for index, task in enumerate(tasks, 1):
            if args.only and not task["sha"].startswith(args.only):
                continue
            checkout = workdir / task["repo"].replace("/", "__")
            if not checkout.exists() and CLONES.get(task["repo"]):
                checkout = pathlib.Path(CLONES[task["repo"]])
            if not checkout.exists() and run(
                    ["git", "clone", "-q", f"https://github.com/{task['repo']}.git", str(checkout)],
                    workdir).returncode != 0:
                rows.append({"sha": task["sha"], "class": "CLONE_FAILED"})
                continue
            run(["git", "checkout", "-q", "-f", task["parent"]], checkout)
            run(["git", "clean", "-qfd"], checkout)
            diff = run(["git", "diff", task["parent"], task["sha"], "--", task["test"]],
                       checkout).stdout
            (checkout / ".oracle.patch").write_text(diff)
            if run(["git", "apply", "--whitespace=nowarn", ".oracle.patch"],
                   checkout).returncode != 0:
                rows.append({"sha": task["sha"], "class": "APPLY_FAILED"})
                continue
            # DENOMINATOR RULE (V34): only a genuine test failure counts
            node = (task["failed_nodes"] or [task["test"]])[0]
            probe = pytest_node(checkout, node)
            if probe.returncode != 1:
                rows.append({"repo": task["repo"], "sha": task["sha"], "node": node,
                             "class": "NOT_A_TEST_FAILURE", "rc": probe.returncode})
                print(f"  {index}/{len(tasks)} {task['sha'][:8]} -> NOT_A_TEST_FAILURE", flush=True)
                continue
            row = attempt(checkout, task)
            row.update({"repo": task["repo"], "sha": task["sha"], "node": node})
            rows.append(row)
            print(f"  {index}/{len(tasks)} {task['sha'][:8]} -> {row['class']} "
                  f"tried={row.get('tried', 0)} pool={row.get('pool_size', 0)} "
                  f"[{row.get('family') or row.get('why', '')[:40]}]", flush=True)
    finally:
        if not args.keep:
            shutil.rmtree(workdir, ignore_errors=True)

    counts: dict[str, int] = {}
    for row in rows:
        counts[row["class"]] = counts.get(row["class"], 0) + 1
    solved = counts.get("SOLVED", 0)
    denominator = solved + counts.get("REFUSED", 0)
    summary = {
        "tasks_examined": len(rows),
        "genuine_test_failures": denominator,
        "by_class": counts,
        "solved": solved,
        "resolve_rate": round(solved / max(1, denominator), 4),
        "by_family": {},
        "budget_per_task": BUDGET,
        "mean_pool_size": round(sum(row.get("pool_size", 0) for row in rows) / max(1, len(rows)), 1),
        "solved_that_change_behaviour": sum(1 for row in rows
                                            if row["class"] == "SOLVED" and not row.get("cosmetic")),
        "solved_that_only_change_text": sum(1 for row in rows
                                            if row["class"] == "SOLVED" and row.get("cosmetic")),
    }
    for row in rows:
        if row.get("family"):
            summary["by_family"][row["family"]] = summary["by_family"].get(row["family"], 0) + 1
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "schema": SCHEMA,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cost": {"model_calls": 0, "stored_parameters": 0, "network_at_run_time": 0,
                 "duration_s": round(time.time() - started, 1)},
        "summary": summary,
        "per_task": rows,
    }, indent=1) + "\n")
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
