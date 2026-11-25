#!/usr/bin/env python3
"""Turn an assertion's actual/expected difference into a source literal edit.

No model, no diff, no stored rule. The two values come from a real failing
assertion; the changed substrings are computed by sequence alignment; the
project's own whole test file is the only authority that accepts a candidate.
"""
from __future__ import annotations

import argparse
import ast
import difflib
import json
import pathlib
import subprocess
import sys
import tempfile
import time
from typing import Any, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
for entry in (str(ROOT), str(ROOT / "canonical" / "tools"),
              str(ROOT / "canonical" / "swe_kernel")):
    if entry not in sys.path:
        sys.path.insert(0, entry)

import identify_a_real_bugs_fix_v1 as identify  # noqa: E402
import operand_invention_v1 as operand  # noqa: E402

SCHEMA = "PROJECT_BRAIN_EXPECTED_ACTUAL_LITERAL_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"
DECLARED = {
    "E1": "the edit is computed only from an assertion's actual and expected values",
    "E2": "a candidate is accepted only by the whole test file in the project runner",
    "E3": "no diff, gold patch, model, network or stored parameter is read",
}
MAX_CANDIDATES = 48


def value_of(repr_text: Any) -> Any:
    if not isinstance(repr_text, str):
        return None
    try:
        return ast.literal_eval(repr_text)
    except (ValueError, SyntaxError):
        return None


def differences(actual: Any, expected: Any) -> list[tuple[str, str]]:
    """(actual-only fragment, expected-only fragment) pairs, longest first."""
    if not isinstance(actual, str) or not isinstance(expected, str):
        return []
    out: list[tuple[str, str]] = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, actual, expected).get_opcodes():
        if tag == "equal":
            continue
        left, right = actual[i1:i2], expected[j1:j2]
        if left or right:
            out.append((left, right))
    return sorted(out, key=lambda pair: -max(len(pair[0]), len(pair[1])))


def literal_holes(source: str, hot_lines: Sequence[int]) -> list[dict[str, Any]]:
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    holes: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        if not hasattr(node, "end_lineno") or node.lineno != node.end_lineno:
            continue
        if hot_lines and node.lineno not in set(int(line) for line in hot_lines):
            continue
        holes.append({"value": node.value, "line": node.lineno,
                      "col": node.col_offset, "end_col": node.end_col_offset,
                      "start": _offset(lines, node.lineno, node.col_offset),
                      "end": _offset(lines, node.end_lineno, node.end_col_offset)})
    return holes[:24]


def _offset(lines: Sequence[str], line: int, col: int) -> int:
    return sum(len(item) for item in lines[:line - 1]) + col


def expression_holes(source: str, lines: Sequence[int]) -> list[dict[str, Any]]:
    """Whole RHS expressions at runtime-localized producer lines."""
    tree = ast.parse(source)
    source_lines = source.splitlines(keepends=True)
    wanted = set(int(line) for line in lines)
    out: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if getattr(node, "lineno", None) not in wanted:
            continue
        expression = None
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            expression = node.value
        elif isinstance(node, ast.Return):
            expression = node.value
        elif isinstance(node, ast.Expr):
            expression = node.value
        if expression is None or not hasattr(expression, "end_lineno"):
            continue
        first = _offset(source_lines, expression.lineno, expression.col_offset)
        last = _offset(source_lines, expression.end_lineno, expression.end_col_offset)
        out.append({"value": source[first:last], "line": expression.lineno,
                    "col": expression.col_offset, "end_col": expression.end_col_offset,
                    "start": first, "end": last, "kind": "producer_expression"})
    return out[:24]


def patch(source: str, hole: Mapping[str, Any], value: str) -> str:
    start, end = int(hole["start"]), int(hole["end"])
    return source[:start] + repr(value) + source[end:]

def candidates(source: str, holes: Sequence[Mapping[str, Any]],
               diffs: Sequence[tuple[str, str]],
               limit: int = MAX_CANDIDATES,
               expected_value: Any = None) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    seen = {source}
    for hole in holes:
        base = str(hole["value"])
        for actual_part, expected_part in diffs[:8]:
            variants: list[str] = []
            if hole.get("kind") == "producer_expression" and isinstance(expected_value, str):
                variants.append(expected_value)
            if actual_part and actual_part in base:
                variants.append(base.replace(actual_part, expected_part, 1))
            if expected_part and expected_part not in base:
                variants.append(base + expected_part)
                for position in range(len(base) + 1):
                    variants.append(base[:position] + expected_part + base[position:])
            for variant in variants:
                if variant == base or variant in seen:
                    continue
                seen.add(variant)
                out.append((patch(source, hole, variant),
                            f"{base!r}->{variant!r}@{hole['line']}"))
                if len(out) >= limit:
                    return out
    return out


def explore(repo: pathlib.Path, sha: str, *, source_path: str, test_path: str,
            actual: Any, expected: Any, seconds: int = 20,
            max_candidates: int = MAX_CANDIDATES,
            focus_lines: Sequence[int] | None = None) -> dict[str, Any]:
    started = time.time()
    source_text = identify.show(repo, f"{sha}^", source_path)
    post_tests = identify.show(repo, sha, test_path)
    if not source_text or not post_tests:
        return {"stage": "SOURCE_OR_TEST_NOT_FOUND"}
    with tempfile.TemporaryDirectory() as where:
        worktree = pathlib.Path(where) / "wt"
        made = subprocess.run(["git", "-C", str(repo), "worktree", "add", "--detach",
                               str(worktree), f"{sha}^"], capture_output=True, text=True)
        if made.returncode != 0:
            return {"stage": "WORKTREE_FAILED"}
        try:
            test_file = worktree / test_path
            test_file.parent.mkdir(parents=True, exist_ok=True)
            test_file.write_text(post_tests, encoding="utf-8")
            first, _ = identify.run_tests_full(worktree, test_path, seconds)
            second, _ = identify.run_tests_full(worktree, test_path, seconds)
            failing = identify.failing_tests(first)
            stable = [name for name, verdict in first.items()
                      if verdict == "PASSED" and second.get(name) == "PASSED"]
            if not failing:
                return {"stage": "NO_ORACLE"}
            lines = list(focus_lines or []) if focus_lines is not None else \
                operand.hot_lines(worktree, test_path, source_path)[0]
            actual_value, expected_value = value_of(actual), value_of(expected)
            diffs = differences(actual_value, expected_value)
            holes = literal_holes(source_text, lines)
            if focus_lines is not None:
                holes = expression_holes(source_text, focus_lines) + holes
            proposals = candidates(source_text, holes, diffs, max_candidates,
                                   expected_value=expected_value)
            source_file = worktree / source_path
            tried = 0
            for candidate, how in proposals:
                tried += 1
                source_file.write_text(candidate, encoding="utf-8")
                after, _ = identify.run_tests_full(worktree, test_path, seconds)
                broken = [name for name in stable if after.get(name) != "PASSED"]
                still = [name for name in failing if after.get(name) != "PASSED"]
                source_file.write_text(source_text, encoding="utf-8")
                if after and not still and not broken:
                    return {"stage": "COMPARED", "verified": True, "how": how,
                            "candidate": candidate, "tried": tried,
                            "seconds": round(time.time() - started, 1)}
            return {"stage": "COMPARED", "verified": False, "diffs": len(diffs),
                    "holes": len(holes), "tried": tried,
                    "seconds": round(time.time() - started, 1)}
        finally:
            subprocess.run(["git", "-C", str(repo), "worktree", "remove", "--force",
                            str(worktree)], capture_output=True, text=True)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--entries", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--seconds", type=int, default=20)
    args = parser.parse_args(argv)
    entries = json.loads(pathlib.Path(args.entries).read_text(encoding="utf-8"))
    rows = [{"sha": entry["sha"], "repo": entry.get("repo"),
             **explore(pathlib.Path(args.repo), str(entry["sha"]),
                       source_path=str(entry["sources"][0]),
                       test_path=str(entry["tests"][0]),
                       actual=entry.get("actual"), expected=entry.get("expected"),
                       seconds=args.seconds)} for entry in entries]
    verified = sum(1 for row in rows if row.get("verified"))
    report = {"schema": SCHEMA, "authority": AUTHORITY,
              "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "declared_before_the_run": DECLARED, "rows": rows,
              "summary": {"rows": len(rows), "verified": verified,
                          "model_calls": 0, "network_calls": 0, "parameters_stored": 0},
              "verdict": "PASS" if verified else "FAIL"}
    out = pathlib.Path(args.receipt)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"verdict": report["verdict"], "summary": report["summary"],
                      "rows": [{k: row.get(k) for k in ("sha", "stage", "verified", "tried")}
                               for row in rows]}, indent=2))
    return 0 if verified else 2


if __name__ == "__main__":
    raise SystemExit(main())
