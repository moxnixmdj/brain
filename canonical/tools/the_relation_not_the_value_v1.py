#!/usr/bin/env python3
"""The demand is a relation, not a value: find the place a valid object was read as a boolean.

WHERE THIS COMES FROM
---------------------
Last round falsified the composition it had declared -- "the demanded value is produced at another site",
7 rows, 37 shifts, 0 verified -- and named what is actually missing: **the demand language**. Its own
reading of the human fixes is that none of them is a value that lives elsewhere; one is a *relation* at a
guard that already holds the right object:

    if a.converter and not isinstance(a.converter, Converter):              parent
    if a.converter is not None and not isinstance(a.converter, Converter):   fixed

The value at that site is the one the test wants. What changes is **which relation is asked of it**:
`x` is falsey for a valid object, `x is not None` is not. A demand language that can only say "produce
this value" cannot state that, and no search repairs a demand that cannot be stated.

THE MECHANISM, AND WHY IT IS NOT AN ENUMERATION
-----------------------------------------------
The naive version of this round proposed `(expr) is not None` at every guard in the file: **308 sites,
616 candidates, 111 s for one row, and the right one was past the 80th attempt.** Enumerating a form is
exactly the move this tree has already measured dead.

So the site is not enumerated, it is **measured**. The failing run is executed once with every guard's
value probed, and the only sites kept are the ones where the runtime value was

    falsey  and  not None

because those -- and only those -- are the places where `x` and `x is not None` disagree *in this run*.
That set is a fact about the execution, not a guess about the source, and it is typically zero or a
handful. The projection is then judged by the project's own test file, whole, on a fresh worktree with
bytecode caching disabled in both directions.

WHAT THIS DOES NOT CLAIM
------------------------
* A green file is not a proof. The verdict is the project's own test file; nothing outside it is checked.
* A verified projection is not necessarily the human's edit; whether it lands on the human's line is
  recorded, never assumed.
* This does not raise the ceiling of the demand language. It adds one form and measures what it is worth.
"""
from __future__ import annotations

import argparse
import ast
import builtins
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time
from typing import Any, Sequence

TOOLS = pathlib.Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
for path in (str(TOOLS), str(REPO)):
    if path not in sys.path:
        sys.path.insert(0, path)

import identify_a_real_bugs_fix_v1 as identify  # noqa: E402

SCHEMA = "BRAIN_THE_RELATION_NOT_THE_VALUE_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"
FAILING = ("FAILED", "ERROR")
PROBE_MODULE = "brain_probe"

PROBE_SOURCE = '''"""Scratch probe: records guarded expressions whose runtime value is falsey but not None."""
import json
import os


def probe(line, col, value):
    try:
        falsey = not bool(value)
    except Exception:
        falsey = False
    if falsey and value is not None and type(value) is not bool:
        path = os.environ.get("BRAIN_PROBE_OUT")
        if path:
            with open(path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps({"line": line, "col": col, "repr": repr(value)[:160],
                                         "type": type(value).__name__}) + "\\n")
    return value
'''


def definitions(tree: ast.Module) -> set[str]:
    """Names the file binds to a class, function or import -- never worth asking a boolean question."""
    bound: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bound.add(node.name)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                bound.add((alias.asname or alias.name).split(".")[0])
    return bound | set(dir(builtins))


def char_span(line: str, start_byte: int, end_byte: int) -> tuple[int, int]:
    """CPython's `col_offset` is a UTF-8 BYTE offset; slicing a `str` with it is wrong on any line that
    carries a non-ASCII character. Measured as `INSTRUMENTATION_REFUSED` on 5 of 15 rows before this
    conversion existed -- an instrument defect that reads exactly like a file it cannot instrument."""
    raw = line.encode("utf-8")
    start = len(raw[:start_byte].decode("utf-8", errors="ignore"))
    end = len(raw[:end_byte].decode("utf-8", errors="ignore"))
    return start, end


def boolean_positions(test: ast.expr) -> list[ast.expr]:
    """The expressions the `If` asks a yes/no question of: the test itself, `and`/`or` operands, `not`'s
    operand -- and the operands of a `not in` comparison's left side. Nothing else is a question.

    Measured false positive that forced this rule: at more-itertools cca32949f1 the test is
    `hasattr(iterable, '__reversed__')`, whose `iterable` is a CALL ARGUMENT, not the value being asked.
    Projecting it produced `hasattr(((iterable) is not None), '__reversed__')` -- `hasattr(True, ...)`,
    which is False, which takes the same branch the human's `getattr(..., None)` takes, which flips the
    human's own fail-to-pass test. The judge accepted a nonsense edit because the nonsense coincided.
    """
    found: list[ast.expr] = []

    def walk(node: ast.expr) -> None:
        if isinstance(node, ast.BoolOp):
            for value in node.values:
                walk(value)
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            walk(node.operand)
        elif isinstance(node, (ast.Name, ast.Attribute)):
            found.append(node)

    walk(test)
    return found


def guards(source: str) -> list[dict[str, Any]]:
    """Maximal single-line name/attribute spans inside `If` tests, with the span that would be replaced."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    skip = definitions(tree)
    spans: list[tuple[int, int, int, str, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        for part in boolean_positions(node.test):
            if not isinstance(part, (ast.Name, ast.Attribute)):
                continue
            if part.lineno != part.end_lineno:
                continue
            # A comprehension target is a Name inside the `If` test too (`for param in sharers`), and
            # wrapping it yields "cannot assign to function call" -- measured on click 3495fba163.
            if not isinstance(getattr(part, "ctx", ast.Load()), ast.Load):
                continue
            if isinstance(part, ast.Name) and part.id in skip:
                continue
            root = part
            while isinstance(root, ast.Attribute):
                root = root.value
            if isinstance(root, ast.Name) and root.id in skip:
                continue
            text = ast.get_source_segment(source, part) or ""
            if text:
                line_text = source.splitlines()[part.lineno - 1]
                start, end = char_span(line_text, part.col_offset, part.end_col_offset)
                spans.append((part.lineno, start, end, text, node.lineno))
    kept: list[dict[str, Any]] = []
    for line, col, end, text, test_line in spans:
        inside = any(other[0] == line and other[1] <= col and end <= other[2]
                     and (other[1], other[2]) != (col, end) for other in spans)
        if inside:
            continue
        kept.append({"line": line, "col": col, "end": end, "text": text, "test_line": test_line})
    return kept


def _insertion_line(source: str) -> int:
    """The line after the module docstring and after every `__future__` import, or 0.

    A probe import above `from __future__ import annotations` is a SyntaxError, and the run then
    produces no verdicts at all -- which reads exactly like "the guard was never reached". Measured
    once, on the first row: 241 sites, 0 verdicts, `SyntaxError: from __future__ imports must occur at
    the beginning of the file`.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return 0
    line = 0
    for node in tree.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) \
                and isinstance(node.value.value, str) and node is tree.body[0]:
            line = node.end_lineno or 0
        elif isinstance(node, ast.ImportFrom) and node.module == "__future__":
            line = node.end_lineno or line
        else:
            break
    return line


def instrument(source: str, sites: Sequence[dict[str, Any]]) -> str | None:
    """Wrap every guarded expression in `probe(line, col, value)`; behaviour is unchanged by design."""
    lines = source.splitlines(keepends=True)
    by_line: dict[int, list[dict[str, Any]]] = {}
    for site in sites:
        by_line.setdefault(site["line"], []).append(site)
    for line_number, items in by_line.items():
        index = line_number - 1
        line = lines[index]
        for site in sorted(items, key=lambda row: row["col"], reverse=True):
            if line[site["col"]:site["end"]] != site["text"]:
                return None
            line = (line[: site["col"]] + f"__brain_probe__({site['line']}, {site['col']}, "
                    + site["text"] + ")" + line[site["end"]:])
        lines[index] = line
    insertion = _insertion_line(source)
    lines.insert(insertion, f"from {PROBE_MODULE} import probe as __brain_probe__  # injected\n")
    candidate = "".join(lines)
    try:
        ast.parse(candidate)
    except SyntaxError:
        return None
    return candidate


def rewrite(source: str, site: dict[str, Any]) -> str | None:
    """`(expr) is not None` at exactly one span; refuse if the result is not valid Python."""
    lines = source.splitlines(keepends=True)
    index = site["line"] - 1
    if not (0 <= index < len(lines)):
        return None
    line = lines[index]
    if line[site["col"]:site["end"]] != site["text"]:
        return None
    lines[index] = (line[: site["col"]] + "((" + site["text"] + ") is not None)"
                    + line[site["end"]:])
    candidate = "".join(lines)
    try:
        ast.parse(candidate)
    except SyntaxError:
        return None
    return candidate


def verdicts(worktree: pathlib.Path, test_path: str, seconds: int,
             env: dict[str, str] | None = None) -> dict[str, str]:
    outcomes, _output = identify.run_tests_full(worktree, test_path, seconds, extra_env=env)
    return outcomes


def judge(baseline: dict[str, str], after: dict[str, str],
          witness: Sequence[str] | None = None) -> tuple[bool, str, list[str]]:
    """A repair makes at least one failing test pass, breaks nothing that passed, adds no failure.

    Demanding that EVERY test failing on the parent pass would make the criterion impossible wherever
    the parent carries an unrelated red -- measured on the first row: the commit repairs one test and
    an unrelated one stays red in this environment, so a strict criterion reports "not repaired" for the
    human's own fix. That is why the human's edit is run as a CONTROL on every row: a criterion that
    rejects the answer key is a broken instrument, not a finding.
    """
    failing = [name for name, verdict in baseline.items() if verdict.upper() in FAILING]
    passing = [name for name, verdict in baseline.items() if verdict.upper() == "PASSED"]
    if not failing:
        return False, "NO_FAILING_TEST", []
    flipped = [name for name in failing if after.get(name, "").upper() == "PASSED"]
    broken = [name for name in passing if after.get(name, "").upper() in FAILING]
    new_red = [name for name, verdict in after.items()
               if verdict.upper() in FAILING and name not in failing and name in passing]
    if not flipped:
        return False, "NO_TEST_FLIPPED", []
    # A repair satisfies the SAME demand, and a demand's footprint is the set of tests the human edit
    # turns green. Measured: click 4fd2fea0db's human edit flips 5 nodes, and a candidate elsewhere in
    # the file flipped 2 of the 5 -- accepted by "at least one" and refused by "all of the witness's".
    if witness is not None and set(witness) - set(flipped):
        return False, f"PARTIAL_FLIP={len(set(witness) - set(flipped))}", flipped
    if broken or new_red:
        return False, f"BROKE={len(broken)}+NEW={len(new_red)}", flipped
    return True, "VERIFIED", flipped


def source_files(repo: pathlib.Path, commit: str) -> list[str]:
    files = subprocess.run(["git", "-C", str(repo), "diff-tree", "--no-commit-id", "--name-only",
                            "-r", commit], capture_output=True, text=True,
                           errors="replace").stdout.splitlines()
    out = []
    for raw in files:
        path = raw.strip()
        if not path.endswith(".py") or path.startswith(("tests/", "test/")) or "/tests/" in path:
            continue
        if pathlib.PurePosixPath(path).stem.startswith("test_"):
            continue
        out.append(path)
    return out


def explore(repo: pathlib.Path, entry: dict[str, Any], *, cap: int, seconds: int) -> dict[str, Any]:
    started = time.time()
    commit, test_path = entry["commit"], entry["test"]
    row: dict[str, Any] = {"repo": entry.get("repo"), "commit": commit, "test": test_path,
                           "parameters_stored": 0}
    with tempfile.TemporaryDirectory() as where:
        worktree = pathlib.Path(where) / "wt"
        added = subprocess.run(["git", "-C", str(repo), "worktree", "add", "--detach", str(worktree),
                                f"{commit}^"], capture_output=True, text=True, errors="replace")
        if added.returncode != 0:
            return {**row, "stage": "WORKTREE_FAILED"}
        try:
            (worktree / test_path).write_text(identify.show(repo, commit, test_path),
                                              encoding="utf-8")
            baseline = verdicts(worktree, test_path, seconds)
            failing = [name for name, verdict in baseline.items() if verdict.upper() in FAILING]
            if not failing:
                return {**row, "stage": "NO_FAILING_TEST", "seconds": round(time.time() - started, 2)}
            row.update({"failing_tests": sorted(failing)[:8], "baseline_verdicts": len(baseline)})

            files = entry.get("sources") or source_files(repo, commit)
            if not files:
                return {**row, "stage": "NO_SOURCE_FILE", "seconds": round(time.time() - started, 2)}
            source_path = files[0]
            target = worktree / source_path
            original = target.read_text(encoding="utf-8", errors="replace")

            # ONE instrumented run decides which guards are even candidates.
            sites = guards(original)
            row["guard_sites"] = len(sites)
            instrumented = instrument(original, sites)
            if instrumented is None:
                return {**row, "stage": "INSTRUMENTATION_REFUSED",
                        "seconds": round(time.time() - started, 2)}
            (worktree / (PROBE_MODULE + ".py")).write_text(PROBE_SOURCE, encoding="utf-8")
            probe_out = pathlib.Path(where) / "probe.json"
            target.write_text(instrumented, encoding="utf-8")
            env = {"BRAIN_PROBE_OUT": str(probe_out), "PYTHONPATH": "src:."}
            verdicts(worktree, test_path, seconds, env=env)
            target.write_text(original, encoding="utf-8")
            observed = [json.loads(line) for line in probe_out.read_text().splitlines()
                        if line.strip()] if probe_out.exists() else []
            seen: set[tuple[int, int]] = set()
            candidates: list[dict[str, Any]] = []
            for value in observed:
                key = (value["line"], value["col"])
                if key in seen:
                    continue
                seen.add(key)
                match = next((site for site in sites if (site["line"], site["col"]) == key), None)
                if match is not None:
                    candidates.append({**match, "observed": value["repr"],
                                       "observed_type": value["type"]})
            row["falsey_sites"] = len(candidates)
            row["observed"] = [{"line": row_["line"], "expression": row_["text"],
                                "value": row_["observed"]} for row_ in candidates[:6]]
            human_source = identify.show(repo, commit, source_path)
            control = None
            if human_source:
                target.write_text(human_source, encoding="utf-8")
                after_human = verdicts(worktree, test_path, seconds)
                target.write_text(original, encoding="utf-8")
                control, control_why, control_flipped = judge(baseline, after_human)
                witness = list(control_flipped)
                row["control"] = {"accepted": control, "reason": control_why,
                                  "flipped": control_flipped[:6]}
                if not control:
                    row.update({"stage": "REFUSED__CONTROL_BROKEN",
                                "seconds": round(time.time() - started, 2)})
                    return row
            attempts = 0
            for site in candidates[:cap]:
                candidate = rewrite(original, site)
                if candidate is None:
                    continue
                attempts += 1
                target.write_text(candidate, encoding="utf-8")
                after = verdicts(worktree, test_path, seconds)
                target.write_text(original, encoding="utf-8")
                ok, why, flipped = judge(baseline, after, witness=witness)
                if ok:
                    row.update({"stage": "VERIFIED", "projection": "is not None",
                                "site_line": site["line"], "site_expression": site["text"],
                                "replacement": f"({site['text']}) is not None",
                                "observed_value": site["observed"],
                                "observed_type": site["observed_type"],
                                "attempts": attempts, "flipped": flipped,
                                "seconds": round(time.time() - started, 2)})
                    return row
            row.update({"stage": "NO_PROJECTION_REPAIRS" if candidates else "NO_FALSEY_GUARD",
                        "attempts": attempts, "seconds": round(time.time() - started, 2)})
            return row
        finally:
            subprocess.run(["git", "-C", str(repo), "worktree", "remove", "--force", str(worktree)],
                           capture_output=True, text=True)


def sweep(entries: Sequence[dict[str, Any]], *, repos_root: pathlib.Path, receipt: pathlib.Path,
          cap: int, seconds: int) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    started = time.time()
    for number, entry in enumerate(entries, 1):
        repo = repos_root / entry["repo"]
        try:
            row = explore(repo, entry, cap=cap, seconds=seconds)
        except Exception as error:  # noqa: BLE001
            row = {"repo": entry.get("repo"), "commit": entry.get("commit"), "stage": "EXCEPTION",
                   "error": f"{type(error).__name__}: {error}"[:200]}
        row.setdefault("repo", entry.get("repo"))
        row.setdefault("commit", entry.get("commit"))
        rows.append(row)
        print(f"[{number}/{len(entries)}] {row['repo']} {str(row['commit'])[:10]} {row['stage']} "
              f"falsey={row.get('falsey_sites')} attempts={row.get('attempts')}",
              file=sys.stderr, flush=True)
        receipt.write_text(json.dumps({"schema": SCHEMA, "authority": AUTHORITY, "date": "2026-11-25",
                                       "mode": "SWEEP_REAL_HISTORY", "rows": rows,
                                       "seconds": round(time.time() - started, 1)}, indent=1) + "\n",
                           encoding="utf-8")
    return {"rows": rows, "seconds": round(time.time() - started, 1)}


def headline(report: dict[str, Any]) -> str:
    rows = report["rows"]
    stages: dict[str, int] = {}
    for row in rows:
        stages[row["stage"]] = stages.get(row["stage"], 0) + 1
    verified = [row for row in rows if row["stage"] == "VERIFIED"]
    attempts = sum(row.get("attempts") or 0 for row in rows)
    falsey = sum(row.get("falsey_sites") or 0 for row in rows)
    return (f"{len(rows)} real fix commits; {falsey} guard sites where a valid object was read as a "
            f"boolean; {attempts} projections judged by the project's own test file; "
            f"{len(verified)} verified; stages " +
            json.dumps(dict(sorted(stages.items(), key=lambda kv: -kv[1]))))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--commits", type=pathlib.Path, required=True)
    parser.add_argument("--receipt", type=pathlib.Path, required=True)
    parser.add_argument("--repos-root", type=pathlib.Path, default=pathlib.Path("/tmp/repos"))
    parser.add_argument("--cap", type=int, default=24)
    parser.add_argument("--seconds", type=int, default=180)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--only", default="")
    args = parser.parse_args(argv)
    payload = json.loads(args.commits.read_text(encoding="utf-8"))
    entries = payload.get("entries", payload) if isinstance(payload, dict) else payload
    if args.only:
        wanted = [part.strip() for part in args.only.split(",") if part.strip()]
        entries = [entry for entry in entries
                   if any(str(entry["commit"]).startswith(w) for w in wanted)]
    if args.limit:
        entries = entries[: args.limit]
    report = sweep(entries, repos_root=args.repos_root, receipt=args.receipt, cap=args.cap,
                   seconds=args.seconds)
    print(headline(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
