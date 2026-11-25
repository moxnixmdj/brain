#!/usr/bin/env python3
"""Capture the values a real failing assertion compared, without reading the answer.

The test file is rewritten ONLY in a throwaway worktree: every comparison operand
is wrapped by a helper that records `repr(value)` and returns the same object, so
the assertion's verdict is unchanged. The uninstrumented file remains the oracle.
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

SCHEMA = "PROJECT_BRAIN_ASSERTION_OPERAND_TOMOGRAPHY_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"
DECLARED = {
    "T1": "instrumented comparison operands preserve the original assertion verdict",
    "T2": "the values recorded come from the project's own failing test run",
    "T3": "no diff, gold patch, model, network or stored parameter is read",
}
PLUGIN = '''import json, os
_VALUES = {}
def _brain_record(key, value):
    _VALUES[key] = repr(value)[:2000]
    return value
def pytest_sessionfinish(session, exitstatus):
    target = os.environ.get("BRAIN_ASSERT_OUT", "")
    if target:
        with open(target, "w", encoding="utf-8") as handle:
            json.dump(_VALUES, handle, sort_keys=True)
'''


class _Wrap(ast.NodeTransformer):
    def __init__(self, function_name: str | None = None) -> None:
        self.keys: dict[str, str] = {}
        self.function_name = function_name
        self.group = 0

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        if self.function_name is None or node.name == self.function_name:
            self.group += 1
            return ast.NodeTransformer.generic_visit(self, node)
        return node

    visit_AsyncFunctionDef = visit_FunctionDef  # type: ignore[assignment]

    def visit_Assert(self, node: ast.Assert) -> ast.Assert:
        node.test = self.visit(node.test)
        return node

    def visit_Compare(self, node: ast.Compare) -> ast.Compare:
        def wrap(expression: ast.expr) -> ast.expr:
            key = "op_%d_%d" % (self.group, len(self.keys))
            self.keys[key] = ast.unparse(expression)[:300]
            call = ast.Call(func=ast.Name(id="_brain_record", ctx=ast.Load()),
                            args=[ast.Constant(value=key), expression], keywords=[])
            return ast.copy_location(call, expression)

        node.left = wrap(node.left)
        node.comparators = [wrap(item) for item in node.comparators]
        return node


def instrument(test_source: str, function_name: str | None = None) -> tuple[str, dict[str, str]]:
    """Return a verdict-preserving test source and key -> expression map."""
    tree = ast.parse(test_source)
    wrapper = _Wrap(function_name)
    tree = wrapper.visit(tree)
    ast.fix_missing_locations(tree)
    header = "from brain_assert_tomography_v1 import _brain_record\n"
    return header + ast.unparse(tree) + "\n", dict(wrapper.keys)


def capture(worktree: pathlib.Path, test_rel: str, node_id: str,
            seconds: int = 20, function_name: str | None = None) -> dict[str, Any]:
    """Run one real failing node in a throwaway instrumented copy and collect values."""
    with tempfile.TemporaryDirectory(dir=worktree) as where:
        helper = pathlib.Path(where) / "brain_assert_tomography_v1.py"
        helper.write_text(PLUGIN, encoding="utf-8")
        test_file = worktree / test_rel
        original = test_file.read_text(encoding="utf-8")
        rewritten, expressions = instrument(original, function_name)
        out = pathlib.Path(where) / "values.json"
        env = {**os.environ, **identify.fresh_bytecode(worktree)}
        env["PYTHONPATH"] = os.pathsep.join(
            [where, str(worktree), str(worktree / "src"),
             env.get("PYTHONPATH", "")]
        ).rstrip(os.pathsep)
        env["BRAIN_ASSERT_OUT"] = str(out)
        test_file.write_text(rewritten, encoding="utf-8")
        try:
            command = [sys.executable, "-m", "pytest", node_id, "-q", "--tb=no",
                       "-p", "no:cacheprovider", "-p", "brain_assert_tomography_v1"]
            try:
                subprocess.run(command, cwd=worktree, capture_output=True, text=True,
                               stdin=subprocess.DEVNULL, timeout=seconds, env=env)
            except subprocess.TimeoutExpired:
                return {"outcome": "TIMEOUT"}
            if not out.is_file():
                return {"outcome": "NO_VALUES"}
            values = json.loads(out.read_text(encoding="utf-8"))
            return {"outcome": "CAPTURED", "values": values, "expressions": expressions}
        finally:
            test_file.write_text(original, encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--worktree", required=True)
    parser.add_argument("--test", required=True)
    parser.add_argument("--node", required=True)
    parser.add_argument("--function")
    parser.add_argument("--receipt")
    parser.add_argument("--seconds", type=int, default=20)
    args = parser.parse_args(argv)
    result = capture(pathlib.Path(args.worktree), args.test, args.node, args.seconds,
                     args.function)
    report = {"schema": SCHEMA, "authority": AUTHORITY,
              "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "declared_before_the_run": DECLARED, **result,
              "model_calls": 0, "network_calls": 0, "parameters_stored": 0}
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.receipt:
        pathlib.Path(args.receipt).write_text(text, encoding="utf-8")
    print(text[:4000])
    return 0 if result.get("outcome") == "CAPTURED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
