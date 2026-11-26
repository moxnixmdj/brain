#!/usr/bin/env python3
"""Ask pytest for the parameters behind a test id instead of parsing the id.

THE BOTTLENECK
--------------
`repo_native_component_mining_v1` could not admit a single mined component on 12
fresh click commits because `operand_invention_v1.failed_index` only reads numeric
pytest ids and the inherited parametrize parser misses custom/indirect tables.
The contrast is in the environment; the id is merely a lossy rendering of it.

This module uses pytest's own collection object (`item.callspec.params`) to emit
the concrete parameters for every node id. No source diff, no model, no guessed
mapping from a rendered id back to a value.
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
for path in (str(ROOT), str(ROOT / "canonical" / "tools")):
    if path not in sys.path:
        sys.path.insert(0, path)

import identify_a_real_bugs_fix_v1 as identify  # noqa: E402

SCHEMA = "PROJECT_BRAIN_PYTEST_CONTRAST_ACQUISITION_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX"

PLUGIN = """import json, os

OUT = os.environ.get("BRAIN_PARAM_OUT", "")

def short(value):
    try:
        text = repr(value)
    except Exception:
        text = "<unreprable>"
    return text[:300]

def pytest_collection_modifyitems(items):
    rows = {}
    for item in items:
        callspec = getattr(item, "callspec", None)
        if callspec is None:
            continue
        rows[item.nodeid] = {key: short(value) for key, value in callspec.params.items()}
    if OUT:
        with open(OUT, "w", encoding="utf-8") as handle:
            json.dump(rows, handle, indent=1, sort_keys=True)
"""


def acquire(worktree: pathlib.Path, test_path: str, seconds: int = 60) -> dict[str, dict[str, str]]:
    """Concrete parameters per pytest node id, from pytest itself."""
    plugin = worktree / "brain_param_plugin.py"
    out = worktree / ".brain_params.json"
    plugin.write_text(PLUGIN, encoding="utf-8")
    command = [sys.executable, "-m", "pytest", "--collect-only", "-q", test_path,
               "-p", "no:cacheprovider", "-p", "brain_param_plugin",
               "-o", "asyncio_default_fixture_loop_scope=function"]
    env = {**os.environ, **identify.fresh_bytecode(worktree), "BRAIN_PARAM_OUT": str(out)}
    try:
        subprocess.run(command, cwd=worktree, capture_output=True, text=True,
                       stdin=subprocess.DEVNULL, timeout=seconds, env=env)
    except subprocess.TimeoutExpired:
        return {}
    try:
        return json.loads(out.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def literal(text: str) -> Any:
    try:
        return ast.literal_eval(text)
    except (ValueError, SyntaxError, TypeError, MemoryError, RecursionError):
        return None


def contrast(params: Mapping[str, Mapping[str, str]], failing_nodes: Sequence[str],
             *, max_failing: int = 6, max_passing: int = 200) -> dict[str, Any]:
    """Split pytest parameters into a same-function, same-key failing/passing contrast.

    Mixing values from unrelated tests makes every predicate non-separating, so
    the passing side is restricted to siblings of the failing test function and
    to the same parameter name.
    """
    failing: list[Any] = []
    passing: list[Any] = []
    keys: set[str] = set()
    failed = set(failing_nodes)

    def function_of(node_id: str) -> str:
        head = node_id.split("[")[0]
        return head.rsplit("::", 1)[-1]

    failed_functions = {function_of(node) for node in failing_nodes}
    for node_id, row in params.items():
        function = function_of(node_id)
        if function not in failed_functions:
            continue
        is_failed = node_id in failed
        for key, raw in row.items():
            value = literal(raw)
            if not isinstance(value, (str, int, float)) or isinstance(value, bool):
                continue
            keys.add(key)
            if is_failed:
                if value not in failing and len(failing) < max_failing:
                    failing.append(value)
            else:
                if value not in passing and len(passing) < max_passing:
                    passing.append(value)
    return {"failing": failing, "passing": passing, "parameters": sorted(keys),
            "nodes": len(params), "failing_nodes": len(failed)}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--worktree", required=True)
    parser.add_argument("--test", required=True)
    parser.add_argument("--failing", default="")
    parser.add_argument("--receipt")
    args = parser.parse_args(argv)
    params = acquire(pathlib.Path(args.worktree), args.test)
    row = contrast(params, [line for line in args.failing.splitlines() if line])
    if args.receipt:
        out = pathlib.Path(args.receipt)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"schema": SCHEMA, "authority": AUTHORITY,
                                   "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                   "params": params, "contrast": row}, indent=2, sort_keys=True),
                       encoding="utf-8")
    print(json.dumps(row, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
