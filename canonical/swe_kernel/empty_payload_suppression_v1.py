#!/usr/bin/env python3
"""Suppress decorations built around an observed empty payload.

The expected/actual differential shows a fragment that must not be emitted.
A source-frame trace finds the empty payload that fed the fragment; AST search
finds the condition that admitted it. Candidate guards are verified by the
project's own whole test file. No diff, model, network or stored rule.
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
from typing import Any, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
for entry in (str(ROOT), str(ROOT / "canonical" / "tools"),
              str(ROOT / "canonical" / "swe_kernel")):
    if entry not in sys.path:
        sys.path.insert(0, entry)

import dual_program_splicing_v1 as splicing  # noqa: E402
import identify_a_real_bugs_fix_v1 as identify  # noqa: E402

SCHEMA = "PROJECT_BRAIN_EMPTY_PAYLOAD_SUPPRESSION_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"
DECLARED = {
    "Z1": "only runtime-observed empty payloads are used to tighten a guard",
    "Z2": "a candidate is accepted only by the whole test file",
    "Z3": "no diff, gold patch, model, network or stored parameter is read",
}
PLUGIN = r'''import json, os
OUT = os.environ["BRAIN_EMPTY_OUT"]
PREFIX = os.environ.get("BRAIN_SOURCE_PREFIX", "")
SEEN = set()
RECORDS = []

def _empty(value):
    return (value is None or value is False or value == "" or value == []
            or value == {} or value == () or value == set())

def tracer(frame, event, arg):
    if event == "line" and frame.f_code.co_filename.startswith(PREFIX):
        for name, value in list(frame.f_locals.items()):
            if _empty(value) and (frame.f_code.co_filename, frame.f_lineno, name) not in SEEN:
                SEEN.add((frame.f_code.co_filename, frame.f_lineno, name))
                RECORDS.append({"file": frame.f_code.co_filename, "line": frame.f_lineno,
                                "function": frame.f_code.co_name, "name": name,
                                "kind": type(value).__name__})
            # One and two levels of object attributes: a decision often reads
            # `self.map.subdomain_matching`, which is not a local itself.
            pending = [(name, value)]
            for depth in range(2):
                following = []
                for path, owner in pending:
                    attributes = getattr(owner, "__dict__", None)
                    if not isinstance(attributes, dict):
                        continue
                    for attribute, attr_value in list(attributes.items()):
                        label = f"{path}.{attribute}"
                        if _empty(attr_value):
                            for key_label in (attribute, label):
                                key = (frame.f_code.co_filename, frame.f_lineno, key_label)
                                if key in SEEN:
                                    continue
                                SEEN.add(key)
                                RECORDS.append({"file": frame.f_code.co_filename,
                                                "line": frame.f_lineno,
                                                "function": frame.f_code.co_name,
                                                "name": key_label,
                                                "kind": type(attr_value).__name__})
                                if len(RECORDS) > 3000:
                                    return tracer
                        elif attr_value is not owner and hasattr(attr_value, "__dict__"):
                            following.append((label, attr_value))
                pending = following
    return tracer

def pytest_runtest_call(item):
    sys.settrace(tracer)

def pytest_runtest_teardown(item, nextitem):
    sys.settrace(None)
    with open(OUT, "w", encoding="utf-8") as handle:
        json.dump(RECORDS, handle, sort_keys=True)
'''


def empty_payloads(worktree: pathlib.Path, test_rel: str, node_id: str,
                   seconds: int = 20) -> list[dict[str, Any]]:
    with tempfile.TemporaryDirectory(dir=worktree) as where:
        plugin = pathlib.Path(where) / "brain_empty_plugin.py"
        plugin.write_text("import sys\n" + PLUGIN, encoding="utf-8")
        out = pathlib.Path(where) / "empty.json"
        env = {**os.environ, **identify.fresh_bytecode(worktree)}
        env["PYTHONPATH"] = os.pathsep.join(
            [where, str(worktree), str(worktree / "src"), env.get("PYTHONPATH", "")]
        ).rstrip(os.pathsep)
        env["BRAIN_EMPTY_OUT"] = str(out)
        env["BRAIN_SOURCE_PREFIX"] = str(worktree)
        command = [sys.executable, "-m", "pytest", node_id, "-q", "--tb=no",
                   "-p", "no:cacheprovider", "-p", "brain_empty_plugin"]
        try:
            subprocess.run(command, cwd=worktree, capture_output=True, text=True,
                           stdin=subprocess.DEVNULL, timeout=seconds, env=env)
        except subprocess.TimeoutExpired:
            return []
        if not out.is_file():
            return []
        return json.loads(out.read_text(encoding="utf-8"))


def _span(source: str, node: ast.AST) -> tuple[int, int]:
    lines = source.splitlines(keepends=True)
    start = sum(len(line) for line in lines[:node.lineno - 1]) + node.col_offset
    end = sum(len(line) for line in lines[:node.end_lineno - 1]) + node.end_col_offset
    return start, end


def tightenings(source: str, payloads: Sequence[Mapping[str, Any]]) -> list[tuple[str, str]]:
    """Compute guard rewrites from conditions that admit an observed empty payload."""
    empty_names = {str(item["name"]) for item in payloads}
    tree = ast.parse(source)
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        replacement: str | None = None
        if (isinstance(test, ast.Compare) and len(test.ops) == 1
                and isinstance(test.ops[0], ast.IsNot)
                and isinstance(test.comparators[0], ast.Constant)
                and test.comparators[0].value is None
                and isinstance(test.left, ast.Name)
                and test.left.id in empty_names):
            replacement = test.left.id
        elif (isinstance(test, ast.Compare) and len(test.ops) == 1
              and isinstance(test.ops[0], ast.IsNot)
              and isinstance(test.comparators[0], ast.Constant)
              and test.comparators[0].value is None
              and isinstance(test.left, ast.Attribute)
              and test.left.attr in empty_names):
            replacement = ast.unparse(test.left)
        elif isinstance(test, ast.BoolOp):
            # A guard can be one clause of a compound condition. Tighten only
            # the clause that compared the observed empty value to None.
            for part in test.values:
                if (isinstance(part, ast.Compare) and len(part.ops) == 1
                        and isinstance(part.ops[0], ast.IsNot)
                        and isinstance(part.comparators[0], ast.Constant)
                        and part.comparators[0].value is None
                        and (isinstance(part.left, ast.Name)
                             and part.left.id in empty_names
                             or isinstance(part.left, ast.Attribute)
                             and part.left.attr in empty_names)):
                    replacement = ast.unparse(part.left)
                    start, end = _span(source, part)
                    candidate = source[:start] + replacement + source[end:]
                    key = candidate
                    if key not in seen:
                        seen.add(key)
                        out.append((candidate, f"line {node.lineno}: {ast.unparse(part)} -> {replacement}"))
                    replacement = None
                    break
        elif (isinstance(test, ast.Compare) and len(test.ops) == 1
              and isinstance(test.ops[0], ast.In)
              and isinstance(test.left, ast.Constant)
              and isinstance(test.left.value, str)
              and isinstance(test.comparators[0], ast.Name)
              and test.comparators[0].id in empty_names):
            replacement = f"{test.comparators[0].id}.get({test.left.value!r})"
        if replacement is None or replacement in seen:
            continue
        seen.add(replacement)
        start, end = _span(source, test)
        out.append((source[:start] + replacement + source[end:],
                    f"line {node.lineno}: {ast.unparse(test)} -> {replacement}"))
    return out


def explore(repo: pathlib.Path, sha: str, *, source_path: str, test_path: str,
            seconds: int = 20) -> dict[str, Any]:
    started = time.time()
    parent_source = identify.show(repo, f"{sha}^", source_path)
    post_tests = identify.show(repo, sha, test_path)
    if not parent_source or not post_tests:
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
            before, _ = identify.run_tests_full(worktree, test_path, seconds)
            failing = identify.failing_tests(before)
            if not failing:
                return {"stage": "NO_ORACLE"}
            payloads = [item for item in empty_payloads(worktree, test_path, failing[0], seconds)
                        if str(item["file"]).endswith(source_path)]
            singles = tightenings(parent_source, payloads)
            proposals = list(singles[:24])
            for first in range(min(len(singles), 8)):
                for second in range(first + 1, min(len(singles), 8)):
                    for combined in splicing.splice(parent_source, singles[first][0],
                                                    singles[second][0])[:4]:
                        proposals.append((combined,
                                          f"spliced: {singles[first][1]} + {singles[second][1]}"))
            source_file = worktree / source_path
            baseline_passes = sum(1 for verdict in before.values()
                                  if verdict in ("PASS", "PASSED"))
            for candidate, how in proposals[:48]:
                ast.parse(candidate)  # a syntax error is not a repair
                source_file.write_text(candidate, encoding="utf-8")
                after, _ = identify.run_tests_full(worktree, test_path, seconds)
                source_file.write_text(parent_source, encoding="utf-8")
                passes = sum(1 for verdict in after.values()
                             if verdict in ("PASS", "PASSED"))
                if (not identify.failing_tests(after) and passes
                        and passes >= baseline_passes):
                    return {"stage": "COMPARED", "verified": True, "how": how,
                            "payloads": len(payloads), "proposals": len(proposals),
                            "candidate": candidate,
                            "seconds": round(time.time() - started, 1)}
            return {"stage": "COMPARED", "verified": False, "payloads": len(payloads),
                    "proposals": len(proposals), "seconds": round(time.time() - started, 1)}
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
                       test_path=str(entry["tests"][0]), seconds=args.seconds)}
            for entry in entries]
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
                      "rows": [{k: row.get(k) for k in ("sha", "stage", "verified",
                                                       "payloads", "proposals")}
                               for row in rows]}, indent=2))
    return 0 if verified else 2


if __name__ == "__main__":
    raise SystemExit(main())
