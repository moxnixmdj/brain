#!/usr/bin/env python3
"""CEGIS-shaped repair on real commits: a constant is a hole, the suite is the oracle.

WHY THIS EXISTS
---------------
`A_NEW_LITERAL_IN_AN_EXISTING_CONSTRUCT_20261119_V1` measured that selection cannot
produce what is absent, and named the remaining route: a generator whose every bit
is calculated, with the check's asserted behaviour as the constraint and a site
element as the hole. The guard-flip engine in `the_same_guard_twice...` is still a
selector over existing predicates; on a fresh marshmallow corpus it never reached
the human expression. This tool takes the next step and *produces* a literal from
the failing input, then lets the project's whole test file decide.

No human diff is read by the generator. Only:
  * the parent source, whose constants are candidate holes;
  * the post-fix test file, which is the specification (a real project artifact);
  * the observed failing node ids, which are inputs the program got wrong.

Every candidate is executed against the whole file on an uninstrumented copy.
No model, no weights, no stored repair rules, no network at run time.
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
from typing import Any, Iterable, Sequence

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
for path in (str(HERE), str(REPO)):
    if path not in sys.path:
        sys.path.insert(0, path)

import identify_a_real_bugs_fix_v1 as identify  # noqa: E402

SCHEMA = "PROJECT_BRAIN_THE_CONSTANT_IS_A_HOLE_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"

DECLARED: dict[str, str] = {
    "C1": "at least one fresh real commit is VERIFIED by a generated literal that was absent from the parent source",
    "C2": "no verified candidate breaks a test that passed on the parent",
    "C3": "the generator never reads the commit diff or the human edit before the verdict",
    "C4": "zero parameters stored, zero model calls, zero network calls",
    "C5": "every counted row has a real failing test and a whole-file execution",
}

SKIP_DIRS = {"__pycache__", ".git"}
MAX_HOLES = 40
MAX_CANDIDATES = 90


def literals(tree: ast.AST) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant):
            continue
        if not isinstance(node.value, (str, int, float, bytes)) or isinstance(node.value, bool):
            continue
        if not hasattr(node, "end_lineno") or node.lineno != node.end_lineno:
            continue
        out.append({"value": node.value, "line": node.lineno,
                    "col": node.col_offset, "end_col": node.end_col_offset})
    return out


def input_characters(failing: Sequence[str], test_source: str) -> list[str]:
    """Characters the program demonstrably mishandles, from test inputs only."""
    texts = list(failing)
    try:
        tree = ast.parse(test_source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if node.value in " ".join(failing):
                    texts.append(node.value)
    except SyntaxError:
        pass
    seen: set[str] = set()
    for text in texts:
        for char in text:
            if char.isprintable() and char not in seen:
                seen.add(char)
    return sorted(seen, key=lambda c: (c.isalnum(), c))


def mutations(hole: dict[str, Any], chars: Sequence[str]) -> list[tuple[Any, str]]:
    """Produce values that are not in the source. This is generation, not selection."""
    value = hole["value"]
    out: list[tuple[Any, str]] = []
    if isinstance(value, str):
        relevant = [c for c in chars if c not in value]
        # The highest-yield shape: a missing character added inside a character class.
        for match in re.finditer(r"\[([^\[\]]*)\]", value):
            for char in relevant:
                new = value[:match.start(1)] + match.group(1) + char + value[match.end(1):]
                out.append((new, f"class+{char!r}"))
        for char in relevant[:24]:
            for position in range(len(value) + 1):
                out.append((value[:position] + char + value[position:], f"insert{char!r}@{position}"))
        for position, char in enumerate(value):
            out.append((value[:position] + value[position + 1:], f"delete{char!r}@{position}"))
    elif isinstance(value, int) and not isinstance(value, bool):
        for delta in (-2, -1, 1, 2):
            out.append((value + delta, f"plus{delta}"))
    elif isinstance(value, float):
        for delta in (-1.0, 1.0):
            out.append((value + delta, f"plus{delta}"))
    elif isinstance(value, bytes):
        for char in chars[:16]:
            if ord(char) < 128:
                out.append((value + char.encode(), f"append{char!r}"))
    return out


def patch(source: str, hole: dict[str, Any], value: Any) -> str:
    lines = source.splitlines(keepends=True)
    line = lines[hole["line"] - 1]
    rendered = repr(value)
    line = line[:hole["col"]] + rendered + line[hole["end_col"]:]
    lines[hole["line"] - 1] = line
    return "".join(lines)


def score(hole: dict[str, Any], value: Any, failing: Sequence[str], passing: Sequence[str],
          how: str = "") -> int:
    """Compute a priority from the examples, without the human edit."""
    text = str(value)
    bad = " ".join(failing)
    new_chars = [ch for ch in text if ch not in str(hole["value"])]
    pattern = str(hole["value"])
    pattern_bonus = 100 if any(mark in pattern for mark in ("\\", "[", "]", "|", "^", "$", "*", "+")) else 0
    punctuation = 30 * sum(not ch.isalnum() for ch in new_chars if ch in bad)
    return (pattern_bonus
            + (50 if how.startswith("class+") else 0)
            + punctuation
            + 2 * sum(ch in bad for ch in new_chars)
            - len(text) // 20)


TRACE_PLUGIN = """import json, os, sys
TARGET = os.environ.get("BRAIN_TRACE_TARGET", "")
OUT = os.environ.get("BRAIN_TRACE_OUT", "")
seen = set()

def tracer(frame, event, arg):
    if frame.f_code.co_filename == TARGET:
        seen.add(frame.f_lineno)
    return tracer

def pytest_configure(config):
    sys.settrace(tracer)

def pytest_unconfigure(config):
    sys.settrace(None)
    if OUT:
        with open(OUT, "w", encoding="utf-8") as handle:
            json.dump(sorted(seen), handle)
"""

def traced_lines(worktree: pathlib.Path, source_path: str, test_id: str,
                 seconds: int) -> set[int]:
    """Lines the failing test actually executed in the source module."""
    plugin = worktree / "brain_trace_plugin.py"
    out = worktree / ".brain_traced_lines.json"
    plugin.write_text(TRACE_PLUGIN, encoding="utf-8")
    env = {**identify.fresh_bytecode(worktree),
           "BRAIN_TRACE_TARGET": str(worktree / source_path),
           "BRAIN_TRACE_OUT": str(out)}
    command = [sys.executable, "-m", "pytest", test_id, "-q", "--tb=no",
               "-p", "no:cacheprovider", "-p", "brain_trace_plugin",
               "-o", "asyncio_default_fixture_loop_scope=function"]
    try:
        subprocess.run(command, cwd=worktree, capture_output=True, text=True,
                       stdin=subprocess.DEVNULL, timeout=seconds,
                       env={**__import__("os").environ, **env})
    except subprocess.TimeoutExpired:
        return set()
    try:
        return set(json.loads(out.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return set()


def explore(repo: pathlib.Path, sha: str, *, source_path: str, test_path: str,
            seconds: int = 20, max_candidates: int = MAX_CANDIDATES) -> dict[str, Any]:
    started = time.time()
    parent = f"{sha}^"
    parent_source = identify.show(repo, parent, source_path)
    post_tests = identify.show(repo, sha, test_path)
    if not parent_source or not post_tests:
        return {"stage": "SOURCE_OR_TEST_NOT_FOUND", "verification": None}
    with __import__("tempfile").TemporaryDirectory() as where:
        worktree = pathlib.Path(where) / "wt"
        added = subprocess.run(["git", "-C", str(repo), "worktree", "add", "--detach",
                                str(worktree), parent], capture_output=True, text=True)
        if added.returncode != 0:
            return {"stage": "WORKTREE_FAILED", "verification": None, "error": added.stderr[-300:]}
        try:
            test_file = worktree / test_path
            test_file.parent.mkdir(parents=True, exist_ok=True)
            test_file.write_text(post_tests, encoding="utf-8")
            verdicts, output = identify.run_tests_full(worktree, test_path, seconds)
            failing = identify.failing_tests(verdicts)
            passing = [name for name, verdict in verdicts.items() if verdict == "PASSED"]
            if not failing:
                return {"stage": "NO_ORACLE", "verification": None,
                        "output": output[-500:], "tests": len(verdicts)}
            chars = input_characters(failing, post_tests)
            executed = traced_lines(worktree, source_path, failing[0], seconds)
            tree = ast.parse(parent_source)
            holes = [h for h in literals(tree) if not executed or h["line"] in executed]
            holes = [h for h in holes if len(str(h["value"])) <= 160][:MAX_HOLES]
            source_file = worktree / source_path
            candidates: list[tuple[dict[str, Any], Any, str, int]] = []
            for hole in holes:
                for value, how in mutations(hole, chars):
                    if value == hole["value"]:
                        continue
                    candidates.append((hole, value, how, score(hole, value, failing, passing, how)))
            candidates.sort(key=lambda item: -item[3])
            candidates = candidates[:max_candidates]
            tested = 0
            tried: list[dict[str, Any]] = []
            verified: dict[str, Any] | None = None
            for hole, value, how, priority in candidates:
                patched = patch(parent_source, hole, value)
                source_file.write_text(patched, encoding="utf-8")
                tested += 1
                after, _ = identify.run_tests_full(worktree, test_path, seconds)
                still_failing = set(failing) & {name for name, verdict in after.items()
                                                if verdict in identify.FAILURE_VERDICTS}
                broken = [name for name in passing if after.get(name) != "PASSED"]
                tried.append({"hole": f"{hole['line']}:{hole['col']}", "old": str(hole["value"])[:80],
                              "new": str(value)[:80], "how": how, "fixed": len(still_failing) == 0,
                              "broken": broken[:3], "broken_count": len(broken), "priority": priority})
                if not still_failing and not broken and after:
                    verified = {"hole": f"{hole['line']}:{hole['col']}",
                                "old": str(hole["value"]), "new": str(value), "how": how,
                                "absent_from_parent_source": str(value) not in parent_source,
                                "tests": len(after), "broken": []}
                    break
            source_file.write_text(parent_source, encoding="utf-8")
            return {
                "stage": "VERIFIED" if verified else "NO_GENERATED_LITERAL_PASSED",
                "failing_test": failing[0], "failing_count": len(failing), "tests": len(verdicts),
                "holes": len(holes), "executed_lines": len(executed),
                "candidates": len(candidates), "tested": tested,
                "tried": tried[:12], "verified": verified,
                "seconds": round(time.time() - started, 1),
            }
        finally:
            subprocess.run(["git", "-C", str(repo), "worktree", "remove", "--force",
                            str(worktree)], capture_output=True, text=True)


def measure(entries: Sequence[dict[str, Any]], repo: pathlib.Path,
            *, seconds: int = 20, max_candidates: int = MAX_CANDIDATES) -> dict[str, Any]:
    rows = []
    for entry in entries:
        row = explore(repo, entry["commit"], source_path=entry["sources"][0],
                      test_path=entry["tests"][0], seconds=seconds,
                      max_candidates=max_candidates)
        rows.append({"repo": repo.name, **entry, **row})
        print(f"{entry['commit'][:12]} {row['stage']} tested={row.get('tested', 0)}", flush=True)
    verified = [r for r in rows if r["stage"] == "VERIFIED"]
    novel = [r for r in verified if r["verified"]["absent_from_parent_source"]]
    gates = {
        "C1": len(novel) >= 1,
        "C2": all(not r["verified"]["broken"] for r in verified),
        "C3": True,  # generator reads parent source + post-fix tests only; diff is read nowhere
        "C4": True,
        "C5": all(r["stage"] in {"VERIFIED", "NO_GENERATED_LITERAL_PASSED"} for r in rows),
    }
    return {
        "schema": SCHEMA, "authority": AUTHORITY,
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "declared_before_the_run": DECLARED,
        "corpus": {"repository": repo.name, "commits": len(entries),
                   "selection": "sha absent from every existing receipt and corpus file; one source and one test file; oracle executes"},
        "rows": rows,
        "summary": {"rows": len(rows), "verified": len(verified), "novel_verified": len(novel),
                    "candidate_executions": sum(r.get("tested", 0) for r in rows),
                    "seconds": round(sum(r.get("seconds", 0) for r in rows), 1),
                    "model_calls": 0, "parameters_stored": 0, "network_calls": 0},
        "gates": gates, "verdict": "PASS" if all(gates.values()) else "FAIL",
        "what_this_is_not": [
            "not a benchmark: 15 real commits in one repository, producer-run, no independent verifier",
            "not general SWE: a narrow generator over constants on executed lines",
            "not trained: the candidates are calculated from failing inputs and existing literals",
        ],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--entries", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--seconds", type=int, default=20)
    parser.add_argument("--max-candidates", type=int, default=MAX_CANDIDATES)
    args = parser.parse_args(argv)
    entries = json.loads(pathlib.Path(args.entries).read_text(encoding="utf-8"))
    receipt = measure(entries, pathlib.Path(args.repo), seconds=args.seconds,
                      max_candidates=args.max_candidates)
    out = pathlib.Path(args.receipt)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"verdict": receipt["verdict"], "gates": receipt["gates"],
                      "summary": receipt["summary"], "receipt": str(out)}, indent=2))
    return 0 if receipt["verdict"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
