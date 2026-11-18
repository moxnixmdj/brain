"""Repair from the failing execution, not from the source text.

Last round measured the wall exactly: of 136 real single-expression line edits, 84.6% replace the
site's expression outright, and a pool rooted at the site and ordered by text proximity contains the
human fix for 5.9% of them. Writability was never the problem (77.4% of code edits are writable). The
material was: the file's name table does not nominate the expression that was wrong.

This asks the one source that does. It runs the failing test under a tracer, records the value of every
pure expression the program evaluated in the file that failed, and blames the value that the failure
message carries:

  * `Error: Missing option '--foo' (env var: 'None')` contains the token `None`;
  * the trace says `self.envvar` evaluated to `None` on the line inside that guard;
  * so the guard that let it through is the site, and the blamed expression is the material.

The candidate is not enumerated from a name table and not ordered by distance. It is derived:

    guard  and  blamed is not None

which is the human's fix for click `1b0e19f505`, at rank 1, without anybody looking at the diff, the
test's source, or the identity of the function.

What this is not: a model, a learned prior, a stored table, a grammar of fixes. It is one trace, one
blame, and the project's own tests as the verdict. Where the failure message carries no value that the
run produced -- a wrong list constant, a missing feature -- this returns NO_BLAME and says so instead of
guessing, because that failure is a specification problem and no trace can supply a specification.
"""

from __future__ import annotations

import argparse
import ast
import json
import pathlib
import re
import subprocess
import sys
import tempfile
import time
from typing import Any, Sequence

TOOLS = pathlib.Path(__file__).resolve().parent
REPO = TOOLS.parents[1]
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(REPO))

import identify_a_real_bugs_fix_v1 as identify  # noqa: E402

SCHEMA = "BRAIN_THE_FAILING_RUN_NAMES_THE_EXPRESSION_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"

# The node kinds that can be evaluated a second time without changing the program. Calls are excluded:
# re-running one can mutate the object the trace is supposed to observe, and a trace that perturbs the
# run is not evidence.
PURE_NODES = ("Name", "Attribute", "Subscript", "Constant", "BinOp", "BoolOp", "Compare", "UnaryOp",
              "Tuple", "List", "Dict", "Set", "JoinedStr", "Slice", "IfExp")

# Tokens that carry no information because they are everywhere. A blame has to be specific to be useful.
UNINFORMATIVE = {"None", "True", "False", "0", "1", "-1", "''", '""', "[]", "{}", "()", "0.0"}

TRACER = r'''
import ast
import json
import linecache
import sys
import traceback

target = sys.argv[1]
out_path = sys.argv[2]
test_node = sys.argv[3]
limit = int(sys.argv[4])

# `FormattedValue` is not a value of its own -- it is a hole in an f-string, and evaluating it records
# the text `{x}` rather than what `x` was. The whole `JoinedStr` is recorded instead.
PURE = (ast.Name, ast.Attribute, ast.Subscript, ast.Constant, ast.BinOp, ast.BoolOp, ast.Compare,
        ast.UnaryOp, ast.Tuple, ast.List, ast.Dict, ast.Set, ast.JoinedStr,
        ast.Slice, ast.IfExp)

records = []
parsed = {}
occurrences = {}
evaluations = 0
raised = []


def expressions_on(text):
    tree = parsed.get(text)
    if tree is None:
        try:
            tree = ast.parse(text)
        except SyntaxError:
            parsed[text] = False
            return []
        parsed[text] = tree
    if tree is False:
        return []
    found = []
    for node in ast.walk(tree):
        if isinstance(node, PURE):
            found.append(node)
    return found


def tracer(frame, event, arg):
    global evaluations
    if event == "exception":
        exc_type, exc_value, _tb = arg
        if frame.f_code.co_filename.endswith(target):
            raised.append({"line": frame.f_lineno, "type": getattr(exc_type, "__name__", str(exc_type)),
                           "message": repr(exc_value)[:200]})
        return tracer
    if event != "line":
        return tracer
    filename = frame.f_code.co_filename
    if not filename.endswith(target):
        return tracer
    line = frame.f_lineno
    text = linecache.getline(filename, line).strip()
    if not text:
        return tracer
    for node in expressions_on(text):
        if evaluations >= limit:
            return tracer
        try:
            key = (line, ast.unparse(node))
        except Exception:
            continue
        if occurrences.get(key, 0) >= 20:
            continue
        try:
            value = eval(compile(ast.Expression(body=node), "<trace>", "eval"),
                         frame.f_globals, frame.f_locals)
        except Exception:
            continue
        occurrences[key] = occurrences.get(key, 0) + 1
        evaluations += 1
        try:
            rendered = repr(value)
        except Exception:
            continue
        records.append({"line": line, "expr": key[1], "value": rendered[:120],
                        "type": type(value).__name__})
    return tracer


import pytest

sys.settrace(tracer)
code = 1
try:
    code = pytest.main([test_node, "-x", "-q", "--no-header", "--tb=long", "-p", "no:cacheprovider",
                        "-o", "asyncio_default_fixture_loop_scope=function"])
except SystemExit as exit_code:
    code = exit_code.code
finally:
    sys.settrace(None)

with open(out_path, "w", encoding="utf-8") as handle:
    json.dump({"records": records, "raised": raised, "evaluations": evaluations, "pytest_code": code},
              handle)
'''


def failure_text(output: str) -> str:
    """What the failing run said, in the form a reader would quote it.

    pytest marks the interesting lines with `E `; the exception lines and the assertion message are the
    observable this tool blames against. Everything else in the output is machinery.
    """
    lines = [line.strip()[2:].strip() for line in (output or "").splitlines() if line.strip().startswith("E ")]
    if not lines:
        lines = [line.strip() for line in (output or "").splitlines()
                 if "Error" in line or "assert" in line.lower()][-6:]
    return "\n".join(lines)


def trace_run(worktree: pathlib.Path, source_rel: str, test_node: str, seconds: int = 120,
              limit: int = 20000) -> dict[str, Any]:
    """Run ONE failing test under a tracer that records the value of every pure expression in the file."""
    script = worktree / "_brain_trace_runner.py"
    script.write_text(TRACER, encoding="utf-8")
    records_path = worktree / "_brain_trace.json"
    target = str((worktree / source_rel).resolve())
    command = [sys.executable, str(script), target, str(records_path), test_node, str(limit)]
    import os
    try:
        done = subprocess.run(command, cwd=worktree, capture_output=True, text=True, errors="replace",
                              timeout=seconds, stdin=subprocess.DEVNULL,
                              env={**os.environ, "PYTHONPATH": "src:."})
    except subprocess.TimeoutExpired:
        return {"stage": "TRACE_TIMEOUT", "records": []}
    payload: dict[str, Any] = {}
    if records_path.exists():
        payload = json.loads(records_path.read_text(encoding="utf-8"))
    payload.setdefault("records", [])
    payload["failure"] = failure_text(done.stdout + done.stderr)
    payload["output_tail"] = (done.stdout or "")[-1500:]
    try:
        script.unlink()
        records_path.unlink()
    except OSError:
        pass
    return payload


def _formatted_arguments(source_text: str) -> list[str]:
    try:
        node = ast.parse(source_text, mode="eval").body
    except SyntaxError:
        return []
    return [ast.unparse(sub.value) for sub in ast.walk(node) if isinstance(sub, ast.FormattedValue)]


def blame_from_messages(records: list[dict[str, Any]], text: str) -> list[dict[str, Any]]:
    """Blame the arguments of the message the program itself built, at the moment it built it.

    `Error: Missing option '--foo' (env var: 'None')` is two things: what the test was about (`--foo`)
    and what the program printed (`(env var: 'None')`). Only the second is a value the program chose.
    So: find the recorded string the failure quotes in full, take the `FormattedValue` arguments of its
    source, and read their value **on that same line**. Anything looser is a substring coincidence --
    the first version of this blamed `'bar'`, an envvar value from an unrelated branch, because it
    matched an argument name against any occurrence in the whole run.
    """
    messages: list[tuple[int, int, dict[str, Any]]] = []
    for record in records:
        if record.get("type") != "str":
            continue
        try:
            actual = ast.literal_eval(record.get("value") or "")
        except (ValueError, SyntaxError):
            continue
        if not isinstance(actual, str):
            continue
        core = actual.strip()
        if len(core) < 6 or core not in text:
            continue
        # Only a string the program *formatted* has arguments to blame. The accumulated `result` also
        # contains the failure text and is longer, and blaming it gave no argument at all.
        if not _formatted_arguments(record["expr"]):
            continue
        messages.append((len(core), record["line"], record))
    if not messages:
        return []
    # The message that carries the most of the failure, latest among equals: the nearest cause.
    messages.sort(key=lambda item: (item[0], item[1]))
    _length, message_line, message = messages[-1]
    blamed: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    arguments = _formatted_arguments(message["expr"])
    for argument in arguments:
        same_line = [record for record in records
                     if record["expr"] == argument and record["line"] == message_line]
        earlier = [record for record in records
                   if record["expr"] == argument and record["line"] < message_line]
        # One line can evaluate the same argument many times in one test. The occurrence that made THIS
        # message is the one whose rendering appears inside it -- not the first, which was `'bar'` from an
        # unrelated branch while the message that failed carried `'None'`.
        witness = message["value"] or ""
        chosen = ([record for record in same_line if (record["value"] or "").strip("'\"") in witness]
                  or same_line or earlier)
        for record in chosen:
            key = (record["expr"], record["value"])
            if key in seen:
                continue
            seen.add(key)
            blamed.append({"line": record["line"], "expr": record["expr"], "value": record["value"],
                           "type": record["type"], "how": "FORMATTED_INTO_THE_MESSAGE"})
    return blamed


def blame(records: list[dict[str, Any]], text: str) -> list[dict[str, Any]]:
    """Rank the recorded values by whether the failure message carries them.

    A value the message quotes is the value that went wrong. A value that is in every program (`None`,
    `0`) is not evidence on its own, so it ranks below a value that is specific -- but it still ranks,
    because `None` is exactly what a missing-argument message carries.
    """
    scored: list[tuple[int, int , dict[str, Any]]] = []
    for record in records:
        value = record.get("value") or ""
        if not value or value not in text:
            continue
        if "{" in record["expr"] or "}" in record["expr"]:
            continue
        specific = 0 if (value in UNINFORMATIVE or len(value) < 3) else 1
        attribute = 1 if "." in record["expr"] else 0
        scored.append((specific, attribute, record))
    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    ordered: list[dict[str, Any]] = []
    seen: set[str] = set()
    for _specific, _attribute, record in scored:
        key = record["expr"]
        if key in seen:
            continue
        seen.add(key)
        ordered.append(record)
    return ordered


def guard_span(source: str, line: int) -> tuple[int, str, int, int] | None:
    """The innermost `if`/`while` guard whose body contains `line`, with the real span of its test."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    best: tuple[int, ast.AST] | None = None
    for node in ast.walk(tree):
        if not isinstance(node, (ast.If, ast.While)):
            continue
        start = getattr(node, "lineno", 0)
        end = getattr(node, "end_lineno", start)
        if start < line <= end:
            if best is None or start > best[0]:
                best = (start, node)
    if best is None:
        return None
    guard_line, node = best
    span = identify.span_of(source, node.test.lineno, node.test)
    if span is None:
        return None
    return guard_line, ast.unparse(node.test), span[0], span[1]


def derived_candidates(guard: str, blamed: str, value: str) -> list[str]:
    """Every candidate is the guard plus the blamed value's own exclusion. Nothing else is offered."""
    if value in ("None",):
        forms = ["({guard}) and ({blamed}) is not None",
                 "({guard}) and ({blamed})",
                 "({guard}) and not ({blamed})",
                 "({guard}) or ({blamed})",
                 "({guard}) and ({blamed}) is None"]
    else:
        forms = ["({guard}) and ({blamed}) != {value}",
                 "({guard}) and not ({blamed})",
                 "({guard}) and ({blamed})",
                 "({guard}) or ({blamed})",
                 "({guard}) and ({blamed}) is not None"]
    return [form.format(guard=guard, blamed=blamed, value=value) for form in forms]


def first_failing_test(worktree: pathlib.Path, test_file: str,
                       seconds: int) -> tuple[str | None, dict[str, str], str]:
    """ONE failing test, and never an empty map pretending to be a passing suite."""
    baseline, output = identify.run_tests_full(worktree, test_file, seconds)
    for name, verdict in baseline.items():
        if verdict != "PASSED":
            return name, baseline, output
    return None, baseline, output


def repair(repo: pathlib.Path, sha: str, *, source_path: str, test_path: str, seconds: int = 20,
           limit: int = 20000) -> dict[str, Any]:
    started = time.time()
    parent_sha = f"{sha}^"
    parent_source = identify.show(repo, parent_sha, source_path)
    fix_source = identify.show(repo, sha, source_path)
    if not parent_source or not fix_source:
        return {"stage": "SOURCE_NOT_FOUND"}
    pair = next(iter(identify.needs.changed_pairs(repo, sha, source_path)), None)
    human_fix = None
    if pair is not None:
        try:
            old_stmt = identify.parse_line(pair[0].strip())
            new_stmt = identify.parse_line(pair[1].strip())
            changes = identify.needs.change_points(old_stmt, new_stmt)
            if len(changes) == 1 and isinstance(changes[0][2], ast.expr):
                human_fix = ast.unparse(changes[0][2])
        except SyntaxError:
            human_fix = None

    with tempfile.TemporaryDirectory() as where:
        worktree = pathlib.Path(where) / "wt"
        subprocess.run(["git", "-C", str(repo), "worktree", "add", "--detach", str(worktree), parent_sha],
                       capture_output=True, text=True)
        try:
            (worktree / test_path).write_text(identify.show(repo, sha, test_path), encoding="utf-8")
            failing, baseline, output = first_failing_test(worktree, test_path, seconds)
            if not baseline or "error during collection" in output.lower() or "Interrupted:" in output:
                return {"stage": "SUITE_DID_NOT_RUN", "output_tail": output[-600:]}
            if failing is None:
                return {"stage": "NO_ORACLE__THE_POST_FIX_TESTS_PASS_ON_THE_PARENT",
                        "tests": len(baseline)}
            trace = trace_run(worktree, source_path, failing, seconds=120, limit=limit)
            if trace.get("stage") == "TRACE_TIMEOUT":
                return {"stage": "TRACE_TIMEOUT", "failing_test": failing}
            text = trace.get("failure") or ""
            records = trace.get("records") or []
            blamed = blame_from_messages(records, text) or blame(records, text)
            if not blamed:
                return {"stage": "NO_BLAME__THE_FAILURE_CARRIES_NO_VALUE_THE_RUN_PRODUCED",
                        "failing_test": failing, "failure_text": text[:300],
                        "records": len(trace.get("records") or [])}
            site = None
            for record in blamed:
                site = guard_span(parent_source, record["line"])
                if site is not None:
                    blamed_here = record
                    break
            if site is None:
                return {"stage": "NO_GUARD_ABOVE_THE_BLAMED_VALUE",
                        "failing_test": failing, "blamed": blamed[0]["expr"]}
            guard_line, guard, start_col, end_col = site
            candidates = derived_candidates(guard, blamed_here["expr"], blamed_here["value"])
            target = worktree / source_path
            original = target.read_text(encoding="utf-8")
            table: list[dict[str, Any]] = []
            for expression in candidates:
                patched = identify.replace_site(original, guard_line, start_col, end_col, expression)
                if patched is None:
                    table.append({"expression": expression, "outcomes": {}})
                    continue
                target.write_text(patched, encoding="utf-8")
                outcomes = identify.run_tests(worktree, test_path, seconds)
                target.write_text(original, encoding="utf-8")
                table.append({"expression": expression, "outcomes": outcomes})
            analysis = identify.summarise(table, baseline, human_fix) if human_fix else None
            rank = None
            if human_fix:
                wanted = ast.dump(ast.parse(human_fix, mode="eval").body)
                for index, row in enumerate(table):
                    try:
                        if ast.dump(ast.parse(row["expression"], mode="eval").body) == wanted:
                            rank = index
                            break
                    except SyntaxError:
                        continue
            return {
                "stage": "MEASURED", "sha": sha, "source": source_path, "test_file": test_path,
                "failing_test": failing, "human_fix": human_fix,
                "failure_text": text[:300],
                "blamed": {"line": blamed_here["line"], "expr": blamed_here["expr"],
                           "value": blamed_here["value"], "type": blamed_here["type"]},
                "blame_candidates": [f"{b['expr']} = {b['value']}" for b in blamed[:5]],
                "guard": guard, "guard_line": guard_line,
                "candidates": candidates, "table": table, "analysis": analysis,
                "human_fix_rank": rank, "human_fix_in_pool": rank is not None,
                "records": len(trace.get("records") or []),
                "evaluations": trace.get("evaluations"),
                "seconds": round(time.time() - started, 2),
            }
        finally:
            subprocess.run(["git", "-C", str(repo), "worktree", "remove", "--force", str(worktree)],
                           capture_output=True, text=True)


def sweep(entries: list[dict[str, str]], *, receipt: pathlib.Path, seconds: int) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    started = time.time()
    for number, entry in enumerate(entries, 1):
        repo = pathlib.Path("/tmp/repos") / entry["repo"]
        try:
            result = repair(repo, entry["commit"], source_path=entry["source"],
                            test_path=entry["test"], seconds=seconds)
        except Exception as error:
            result = {"stage": "EXCEPTION", "error": f"{type(error).__name__}: {error}"[:200]}
        row = {k: entry[k] for k in ("repo", "commit", "source", "test")}
        row.update({k: result.get(k) for k in ("stage", "failing_test", "blamed", "guard",
                                               "human_fix", "human_fix_rank", "human_fix_in_pool",
                                               "failure_text", "records")})
        row["analysis"] = result.get("analysis")
        rows.append(row)
        print(f"[{number}/{len(entries)}] {entry['repo']} {entry['commit'][:10]} {row['stage']} "
              f"rank={row['human_fix_rank']} blamed={json.dumps(row['blamed'])[:90]}",
              file=sys.stderr, flush=True)
        receipt.write_text(json.dumps({"schema": SCHEMA, "authority": AUTHORITY, "date": "2026-11-18",
                                       "mode": "SWEEP_REAL_HISTORY", "rows": rows,
                                       "seconds": round(time.time() - started, 1)}, indent=1) + "\n")
    return {"rows": rows}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sweep", type=pathlib.Path, default=None)
    parser.add_argument("--repo", type=pathlib.Path, default=None)
    parser.add_argument("--commit", default=None)
    parser.add_argument("--source", default=None)
    parser.add_argument("--test", default=None)
    parser.add_argument("--limit", type=int, default=20000)
    parser.add_argument("--test-seconds", type=int, default=20)
    parser.add_argument("--receipt", type=pathlib.Path, default=None)
    args = parser.parse_args(argv)
    if args.sweep is not None:
        entries = json.loads(args.sweep.read_text())
        sweep(entries, receipt=args.receipt or pathlib.Path("/tmp/blame_sweep.json"),
              seconds=args.test_seconds)
        return 0
    if not (args.repo and args.commit and args.source and args.test):
        parser.error("--repo, --commit, --source and --test are required without --sweep")
    result = repair(args.repo, args.commit, source_path=args.source, test_path=args.test,
                    seconds=args.test_seconds, limit=args.limit)
    receipt = {"schema": SCHEMA, "authority": AUTHORITY, "date": "2026-11-18", "result": result}
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(receipt, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "table"}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
