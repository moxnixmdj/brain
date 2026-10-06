"""Compile the direct ambient-channel surface of Astra _goal_action.

This is a conservative scheduling/audit object, not a no-bypass proof. It binds
the exact Astra runtime blob and classifies direct syntactic ambient primitives
inside each top-level action-type branch. Indirect helper effects may add more
channels; therefore NO_OBVIOUS_AMBIENT_PRIMITIVE never means PURE.
"""
from __future__ import annotations

import hashlib
import pathlib
import re
from typing import Any

SCHEMA = "PROJECT_BRAIN_GOAL_ACTION_CHANNEL_SURFACE_COMPILER_V1"
ROOT = pathlib.Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "canonical/runtime/astra_runtime.py"
EXPECTED_BLOB = "15dd59ad644c5c73a9218dba4fcc17f880d725f0"

PATTERNS = {
    "HOST_READ": re.compile(
        r"_safe_repo_path|read_text|read_bytes|rglob|glob\(|sha_file\("
    ),
    "HOST_WRITE": re.compile(
        r"_safe_repo_mutation_path|write_text|write_bytes|mkdir\(|"
        r"shutil\.(?:copy|copy2|move|rmtree)|unlink\("
    ),
    "PROCESS": re.compile(r"subprocess\.(?:run|Popen)|os\.(?:fork|kill|system)"),
    "NETWORK_OR_EXTERNAL": re.compile(
        r"urllib\.request|_external_tool_bridge|run_http\("
    ),
    "BOUND_CAPABILITY_DYNAMIC": re.compile(r"_invoke_bound_capability"),
    "PACKAGE_INSTALL": re.compile(r"_ensure_pypi_dependency|_ensure_npm_dependency"),
}


def _git_blob_sha(raw: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


def _function_slice(lines: list[str], name: str) -> tuple[int, int, list[str]]:
    needle = "def " + name + "("
    start = next((i for i, line in enumerate(lines) if line.startswith(needle)), -1)
    if start < 0:
        raise ValueError("FUNCTION_MISSING:" + name)
    end = start + 1
    while end < len(lines):
        if lines[end].startswith("def "):
            break
        end += 1
    return start, end, lines[start:end]


def compile_surface(source: str) -> dict[str, Any]:
    lines = source.splitlines()
    start, _end, body = _function_slice(lines, "_goal_action")
    heads: list[dict[str, Any]] = []
    for offset, line in enumerate(body):
        match = re.match(r'^\s*if typ=="([^"]+)":', line)
        if match:
            heads.append({
                "action_type": match.group(1),
                "offset": offset,
                "source_line": start + offset + 1,
            })

    if not heads:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": ["NO_ACTION_BRANCHES_FOUND"],
            "rows": [],
        }

    rows = []
    for index, head in enumerate(heads):
        a = head["offset"]
        b = heads[index + 1]["offset"] if index + 1 < len(heads) else len(body)
        branch = "\n".join(body[a:b])
        channels = [
            name for name, pattern in PATTERNS.items() if pattern.search(branch)
        ]
        if not channels:
            channels = ["NO_OBVIOUS_AMBIENT_PRIMITIVE"]
        rows.append({
            "action_type": head["action_type"],
            "source_line": head["source_line"],
            "direct_syntactic_channels": channels,
        })

    counts: dict[str, int] = {}
    for row in rows:
        for channel in row["direct_syntactic_channels"]:
            counts[channel] = counts.get(channel, 0) + 1

    action_types = [row["action_type"] for row in rows]
    duplicate_types = sorted({
        x for x in action_types if action_types.count(x) > 1
    })
    status = "PASS__DIRECT_SYNTACTIC_CHANNEL_SURFACE_COMPILED"
    errors: list[str] = []
    if duplicate_types:
        status = "FAIL_CLOSED"
        errors.append("DUPLICATE_ACTION_TYPES:" + ",".join(duplicate_types))

    return {
        "schema": SCHEMA,
        "status": status,
        "errors": errors,
        "action_count": len(rows),
        "rows": rows,
        "channel_counts": counts,
        "scope": "DIRECT_SYNTACTIC_PRIMITIVES_IN_TOP_LEVEL_GOAL_ACTION_BRANCHES",
        "interpretation": (
            "LOWER_BOUND_ONLY__INDIRECT_HELPER_OR_DYNAMIC_CAPABILITY_EFFECTS_MAY_ADD_"
            "CHANNELS__NO_OBVIOUS_AMBIENT_PRIMITIVE_DOES_NOT_MEAN_PURE"
        ),
        "no_bypass_credit": False,
        "acceptance_credit_delta": 0,
        "terminal_credit_delta": 0,
    }


def evaluate(root: pathlib.Path = ROOT) -> dict[str, Any]:
    path = root / "canonical/runtime/astra_runtime.py"
    if not path.is_file():
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__RUNTIME_MISSING",
            "errors": ["RUNTIME_MISSING"],
            "acceptance_credit_delta": 0,
            "terminal_credit_delta": 0,
        }
    raw = path.read_bytes()
    got = _git_blob_sha(raw)
    if got != EXPECTED_BLOB:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__RUNTIME_BLOB_DRIFT",
            "errors": ["RUNTIME_BLOB_DRIFT:" + got],
            "expected_git_blob_sha": EXPECTED_BLOB,
            "acceptance_credit_delta": 0,
            "terminal_credit_delta": 0,
        }
    out = compile_surface(raw.decode("utf-8"))
    out["runtime_path"] = "canonical/runtime/astra_runtime.py"
    out["runtime_git_blob_sha"] = got
    return out


if __name__ == "__main__":
    import json
    print(json.dumps(evaluate(), indent=2, sort_keys=True))
