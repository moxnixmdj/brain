#!/usr/bin/env python3
"""Locate the runtime producer of an observed value by tracing real frames.

This is not name matching: the target is the value captured from the failing
assertion, and a site is admitted only when a live local or return value in a
repo source frame equals it (or contains a long prefix of it).
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
for entry in (str(ROOT), str(ROOT / "canonical" / "tools")):
    if entry not in sys.path:
        sys.path.insert(0, entry)

import identify_a_real_bugs_fix_v1 as identify  # noqa: E402

SCHEMA = "PROJECT_BRAIN_VALUE_PRODUCER_LOCALIZATION_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"
DECLARED = {
    "P1": "a site is admitted only when a live source frame produced the observed value",
    "P2": "the observed value comes from the real failing assertion, not from a diff",
    "P3": "no model, network, stored parameter or gold patch is read",
}
PLUGIN = r'''import ast, json, os
TARGET = ast.literal_eval(os.environ["BRAIN_TARGET_VALUE"])
PREFIX = os.environ.get("BRAIN_SOURCE_PREFIX", "")
OUT = os.environ["BRAIN_PRODUCER_OUT"]
SEEN = set()

def matches(value):
    try:
        if value == TARGET:
            return True
        if isinstance(value, str) and isinstance(TARGET, str) and len(TARGET) >= 8:
            return TARGET in value or (len(value) >= 8 and value in TARGET)
    except Exception:
        return False
    return False

def record(frame, name, matched_value):
    filename = frame.f_code.co_filename
    if not filename.startswith(PREFIX) or "/tests/" in filename or "/test_" in filename:
        return
    key = (filename, frame.f_lineno, frame.f_code.co_name, name)
    if key not in SEEN:
        SEEN.add(key)
        try:
            shown = repr(matched_value)[:500]
        except Exception:
            shown = "<unrepresentable>"
        RECORDS.append({"file": filename, "line": frame.f_lineno,
                        "function": frame.f_code.co_name, "name": name, "value": shown})

def value_scalar(value):
    return value

def tracer(frame, event, arg):
    if event == "line":
        for name, value in list(frame.f_locals.items()):
            if matches(value):
                record(frame, name, value)
    elif event == "return" and matches(arg):
        record(frame, "<return>", arg)
    return tracer

RECORDS = []

def pytest_runtest_call(item):
    sys.settrace(tracer)

def pytest_runtest_teardown(item, nextitem):
    sys.settrace(None)
    with open(OUT, "w", encoding="utf-8") as handle:
        json.dump(RECORDS, handle, sort_keys=True)
'''


def locate(worktree: pathlib.Path, test_rel: str, node_id: str,
           observed: Any, seconds: int = 20) -> dict[str, Any]:
    """Trace one real failing node and return source frames that produced `observed`."""
    with tempfile.TemporaryDirectory(dir=worktree) as where:
        plugin = pathlib.Path(where) / "brain_producer_plugin.py"
        plugin.write_text("import sys\n" + PLUGIN, encoding="utf-8")
        out = pathlib.Path(where) / "producers.json"
        env = {**os.environ, **identify.fresh_bytecode(worktree)}
        env["PYTHONPATH"] = os.pathsep.join(
            [where, str(worktree), str(worktree / "src"), env.get("PYTHONPATH", "")]
        ).rstrip(os.pathsep)
        env["BRAIN_TARGET_VALUE"] = repr(observed)
        env["BRAIN_SOURCE_PREFIX"] = str(worktree)
        env["BRAIN_PRODUCER_OUT"] = str(out)
        test_file = worktree / test_rel
        original = test_file.read_text(encoding="utf-8")
        command = [sys.executable, "-m", "pytest", node_id, "-q", "--tb=no",
                   "-p", "no:cacheprovider", "-p", "brain_producer_plugin"]
        try:
            try:
                subprocess.run(command, cwd=worktree, capture_output=True, text=True,
                               stdin=subprocess.DEVNULL, timeout=seconds, env=env)
            except subprocess.TimeoutExpired:
                return {"outcome": "TIMEOUT"}
            if not out.is_file():
                return {"outcome": "NO_REPORT"}
            records = json.loads(out.read_text(encoding="utf-8"))
            return {"outcome": "LOCATED", "producers": records}
        finally:
            test_file.write_text(original, encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--worktree", required=True)
    parser.add_argument("--test", required=True)
    parser.add_argument("--node", required=True)
    parser.add_argument("--value", required=True)
    parser.add_argument("--receipt")
    parser.add_argument("--seconds", type=int, default=20)
    args = parser.parse_args(argv)
    result = locate(pathlib.Path(args.worktree), args.test, args.node,
                    ast.literal_eval(args.value), args.seconds)
    report = {"schema": SCHEMA, "authority": AUTHORITY,
              "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "declared_before_the_run": DECLARED, **result,
              "model_calls": 0, "network_calls": 0, "parameters_stored": 0}
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.receipt:
        pathlib.Path(args.receipt).write_text(text, encoding="utf-8")
    print(text[:3000])
    return 0 if result.get("producers") else 2


if __name__ == "__main__":
    raise SystemExit(main())
