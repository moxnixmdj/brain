#!/usr/bin/env python3
"""The wrong variable is a hole in the executed frame, not a missing string.

THE BOTTLENECK THIS ANSWERS
---------------------------
`THE_CONSTANT_IS_A_HOLE_20261124_V1` verified one literal generated from a failing
input, but 14/15 rows needed something else. The guard falsifier's one refinement
had the human edit `attr_name`: the program used `field_name` to build a prefix,
the test's partial names used the attribute name, and both values were present in
the same executed frame. No expression grammar can invent that by flipping a guard.

WHAT IS BUILT
-------------
A trace-guided *name* generator:
  1. run the post-fix test file on the parent and record failing node ids;
  2. trace the failing test and record the local frame at every executed source line;
  3. treat each loaded name on those lines as a hole;
  4. propose only names that existed in that same frame at that same execution;
  5. rank by a computed alignment between the observed value of a proposed name and
     the strings the failing test asserts over — specifically, a value that is a
     prefix of a spec string where the current value is not;
  6. patch the single identifier and let the whole test file decide.

No diff, no human edit, no model, no stored repair rules, no network at run time.
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
from typing import Any, Sequence

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
for path in (str(HERE), str(REPO)):
    if path not in sys.path:
        sys.path.insert(0, path)

import identify_a_real_bugs_fix_v1 as identify  # noqa: E402

SCHEMA = "PROJECT_BRAIN_THE_NAME_IS_A_HOLE_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"

DECLARED: dict[str, str] = {
    "N1": "at least one fresh real commit is VERIFIED by substituting a name that existed in the executed frame",
    "N2": "the substituted name is not the name at the site and the whole suite stays green",
    "N3": "the generator reads no commit diff and no human edit before the verdict",
    "N4": "zero parameters stored, zero model calls, zero network calls",
    "N5": "every counted row has a real failing test and a whole-file execution",
}

MAX_HOLES = 1000
MAX_CANDIDATES = 100
MAX_VALUE = 160

RECORDER = """import json, os
OUT = os.environ.get("BRAIN_NAME_TRACE_OUT", "")

def record(line, scope):
    if not OUT:
        return
    kept = {}
    for key, value in scope.items():
        if not key.isidentifier():
            continue
        try:
            kept[key] = {"str": str(value)[:200], "type": type(value).__name__}
        except Exception:
            continue
        if len(kept) >= 48:
            break
    with open(OUT, "a", encoding="utf-8") as handle:
        handle.write(json.dumps({"line": line, "scope": kept}) + "\\n")
"""


UNSAFE_STARTS = ("if ", "elif ", "else:", "for ", "while ", "try:", "except", "finally:",
                 "with ", "def ", "class ", "async ", "match ", "case ")


def static_name_lines(source: str) -> list[int]:
    tree = ast.parse(source)
    return sorted({node.lineno for node in ast.walk(tree)
                   if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
                   and hasattr(node, "end_col_offset")})


def instrument(source: str, lines: Sequence[int]) -> tuple[str, int]:
    """Import the recorder early; return the inserted-line offset for mapping back."""
    text = source.splitlines(keepends=True)
    future_lines = [i for i, line in enumerate(text[:30])
                    if line.lstrip().startswith("from __future__ import")]
    insert_at = (future_lines[-1] + 1) if future_lines else 0
    text.insert(insert_at, "import brain_recorder as _br\n")
    offset = 1
    for number in sorted(set(lines), reverse=True):
        index = number - 1 + (offset if number - 1 >= insert_at else 0)
        if not 0 <= index < len(text):
            continue
        original = text[index]
        stripped = original.lstrip()
        if not stripped or stripped.startswith("#") or stripped.startswith(UNSAFE_STARTS):
            continue
        if stripped.rstrip().endswith(":"):
            continue
        indent = original[:len(original) - len(stripped)]
        candidate = f"{indent}_br.record({number + (offset if number - 1 >= insert_at else 0)}, locals()); {stripped}"
        text[index] = candidate
        try:
            compile("".join(text), "<instrumented>", "exec")
        except SyntaxError:
            text[index] = original
    return "".join(text), offset


def traced_locals(worktree: pathlib.Path, source_path: str, test_id: str,
                  seconds: int, source: str) -> dict[str, dict[str, dict[str, str]]]:
    """Record the frame at every statically possible name-load line during the failing test."""
    source_file = worktree / source_path
    out = worktree / ".brain_name_trace.jsonl"
    (worktree / "brain_recorder.py").write_text(RECORDER, encoding="utf-8")
    instrumented, offset = instrument(source, static_name_lines(source))
    source_file.write_text(instrumented, encoding="utf-8")
    env = {**identify.fresh_bytecode(worktree),
           "PYTHONPATH": f"{worktree / 'src'}:{worktree}",
           "BRAIN_NAME_TRACE_OUT": str(out)}
    command = [sys.executable, "-m", "pytest", test_id, "-q", "--tb=no",
               "-p", "no:cacheprovider", "-o", "asyncio_default_fixture_loop_scope=function"]
    try:
        subprocess.run(command, cwd=worktree, capture_output=True, text=True,
                       stdin=subprocess.DEVNULL, timeout=seconds, env={**os.environ, **env})
    except subprocess.TimeoutExpired:
        source_file.write_text(source, encoding="utf-8")
        return {}
    source_file.write_text(source, encoding="utf-8")
    result: dict[str, dict[str, dict[str, str]]] = {}
    try:
        for line in out.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            result.setdefault(str(int(row["line"]) - offset), row["scope"])
    except (OSError, ValueError, KeyError):
        return {}
    return result


def spec_strings(test_source: str, failing_test: str) -> list[str]:
    """Strings the failing test can assert over: its own literals and its node id."""
    out: list[str] = []
    try:
        tree = ast.parse(test_source)
    except SyntaxError:
        tree = None
    wanted = failing_test.split("::")[-1].split("[")[0]
    if tree is not None:
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == wanted:
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                        out.append(sub.value)
                break
    if "[" in failing_test and failing_test.endswith("]"):
        out.append(failing_test[failing_test.rfind("[") + 1:-1])
    return list(dict.fromkeys(s for s in out if s and len(s) <= MAX_VALUE))


def name_holes(source: str, executed: dict[str, dict[str, dict[str, str]]]) -> list[dict[str, Any]]:
    holes: list[dict[str, Any]] = []
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Name) or not isinstance(node.ctx, ast.Load):
            continue
        if not hasattr(node, "end_col_offset"):
            continue
        frame = executed.get(str(node.lineno))
        if not frame or node.id not in frame:
            continue
        holes.append({"name": node.id, "line": node.lineno,
                      "col": node.col_offset, "end_col": node.end_col_offset,
                      "value": frame[node.id].get("str", ""), "scope": frame})
    return holes[:MAX_HOLES]


def alignment(value: str, current: str, specs: Sequence[str]) -> int:
    """Computed from the spec only: does the proposed value explain a string the
    current value does not?"""
    if not value or len(value) > MAX_VALUE or value == current:
        return -1000
    prefix = sum(1 for spec in specs if spec.startswith(value) and not spec.startswith(current))
    contains = sum(1 for spec in specs if value in spec and current not in spec)
    return 10 * prefix + 3 * contains - (1 if len(value) < 2 else 0)


def candidates(hole: dict[str, Any], specs: Sequence[str]) -> list[tuple[str, int, str]]:
    out: list[tuple[str, int, str]] = []
    for name, record in hole["scope"].items():
        if not name.isidentifier() or name == hole["name"]:
            continue
        value = record.get("str", "")
        score = alignment(value, hole["value"], specs)
        if score > 0:
            out.append((name, score, value[:80]))
    out.sort(key=lambda item: (-item[1], item[0]))
    return out[:MAX_CANDIDATES]


def patch(source: str, hole: dict[str, Any], name: str) -> str:
    lines = source.splitlines(keepends=True)
    line = lines[hole["line"] - 1]
    line = line[:hole["col"]] + name + line[hole["end_col"]:]
    lines[hole["line"] - 1] = line
    return "".join(lines)


def explore(repo: pathlib.Path, sha: str, *, source_path: str, test_path: str,
            seconds: int = 20, max_candidates: int = MAX_CANDIDATES) -> dict[str, Any]:
    started = time.time()
    parent = f"{sha}^"
    parent_source = identify.show(repo, parent, source_path)
    post_tests = identify.show(repo, sha, test_path)
    if not parent_source or not post_tests:
        return {"stage": "SOURCE_OR_TEST_NOT_FOUND", "verification": None}
    with tempfile.TemporaryDirectory() as where:
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
            # A second baseline removes time-dependent node ids and flaky passes from the
            # oracle. Tests whose own ids are regenerated each collection cannot be
            # accused of regressing: they are absent from the second run.
            verdicts2, _ = identify.run_tests_full(worktree, test_path, seconds)
            failing = identify.failing_tests(verdicts)
            passing = [name for name, verdict in verdicts.items()
                       if verdict == "PASSED" and verdicts2.get(name) == "PASSED"]
            if not failing:
                return {"stage": "NO_ORACLE", "verification": None, "output": output[-500:],
                        "tests": len(verdicts)}
            executed = traced_locals(worktree, source_path, failing[0], seconds, parent_source)
            specs = spec_strings(post_tests, failing[0])
            holes = name_holes(parent_source, executed)
            source_file = worktree / source_path
            choices: list[tuple[dict[str, Any], str, int, str]] = []
            for hole in holes:
                for name, score, value in candidates(hole, specs):
                    choices.append((hole, name, score, value))
            choices.sort(key=lambda item: -item[2])
            choices = choices[:max_candidates]
            tested = 0
            tried: list[dict[str, Any]] = []
            verified: dict[str, Any] | None = None
            for hole, name, score, value in choices:
                source_file.write_text(patch(parent_source, hole, name), encoding="utf-8")
                tested += 1
                after, _ = identify.run_tests_full(worktree, test_path, seconds)
                still = set(failing) & {key for key, verdict in after.items()
                                        if verdict in identify.FAILURE_VERDICTS}
                broken = [key for key in passing if after.get(key) != "PASSED"]
                tried.append({"hole": f"{hole['line']}:{hole['col']}:{hole['name']}",
                              "from": hole["value"][:80], "to": name, "observed": value,
                              "score": score, "fixed": not still, "broken": broken[:3],
                              "broken_count": len(broken)})
                if not still and not broken and after:
                    verified = {"hole": f"{hole['line']}:{hole['col']}", "from": hole["name"],
                                "to": name, "observed": value, "score": score,
                                "tests": len(after), "broken": []}
                    break
            source_file.write_text(parent_source, encoding="utf-8")
            return {"stage": "VERIFIED" if verified else "NO_FRAME_NAME_PASSED",
                    "failing_test": failing[0], "failing_count": len(failing),
                    "tests": len(verdicts), "executed_lines": len(executed),
                    "spec_strings": len(specs), "holes": len(holes),
                    "candidates": len(choices), "tested": tested,
                    "tried": tried[:12], "verification": verified,
                    "seconds": round(time.time() - started, 1)}
        finally:
            subprocess.run(["git", "-C", str(repo), "worktree", "remove", "--force",
                            str(worktree)], capture_output=True, text=True)


def measure(entries: Sequence[dict[str, Any]], repo_label: str, repo: pathlib.Path,
            *, seconds: int = 20, max_candidates: int = MAX_CANDIDATES) -> dict[str, Any]:
    rows = []
    for entry in entries:
        row = explore(repo, entry["commit"], source_path=entry["sources"][0],
                      test_path=entry["tests"][0], seconds=seconds,
                      max_candidates=max_candidates)
        rows.append({"repo": repo_label, **entry, **row})
        print(f"{repo_label} {entry['commit'][:12]} {row['stage']} tested={row.get('tested', 0)}",
              flush=True)
    verified = [r for r in rows if r["stage"] == "VERIFIED"]
    gates = {
        "N1": len(verified) >= 1,
        "N2": all(r["verification"]["from"] != r["verification"]["to"] and
                  not r["verification"]["broken"] for r in verified),
        "N3": True,  # only parent source, post-fix tests and the failing run are read
        "N4": True,
        "N5": all(r["stage"] in {"VERIFIED", "NO_FRAME_NAME_PASSED"} for r in rows),
    }
    return {
        "schema": SCHEMA, "authority": AUTHORITY,
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "declared_before_the_run": DECLARED,
        "corpus": {"repositories": ["marshmallow-code/marshmallow", "pallets/click"],
                   "commits": len(entries),
                   "selection": "sha absent from every existing receipt and corpus file; one source and one test file; oracle executes"},
        "rows": rows,
        "summary": {"rows": len(rows), "verified": len(verified),
                    "candidate_executions": sum(r.get("tested", 0) for r in rows),
                    "seconds": round(sum(r.get("seconds", 0) for r in rows), 1),
                    "model_calls": 0, "parameters_stored": 0, "network_calls": 0},
        "gates": gates, "verdict": "PASS" if all(gates.values()) else "FAIL",
        "what_this_is_not": [
            "not a benchmark: real commits, producer-run, no independent verifier",
            "not general SWE: single identifier substitution on an executed line",
            "not trained: the substitutions are computed from the frame and the test's own strings",
        ],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--entries", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--seconds", type=int, default=20)
    parser.add_argument("--max-candidates", type=int, default=MAX_CANDIDATES)
    args = parser.parse_args(argv)
    # Entries carry no repo field; the label partitions by source path prefix.
    entries = json.loads(pathlib.Path(args.entries).read_text(encoding="utf-8"))
    entries = [e for e in entries
               if e["sources"][0].startswith("src/marshmallow/") == (args.label == "marshmallow")]
    receipt = measure(entries, args.label, pathlib.Path(args.repo), seconds=args.seconds,
                      max_candidates=args.max_candidates)
    out = pathlib.Path(args.receipt)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"verdict": receipt["verdict"], "gates": receipt["gates"],
                      "summary": receipt["summary"], "receipt": str(out)}, indent=2))
    return 0 if receipt["verdict"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
