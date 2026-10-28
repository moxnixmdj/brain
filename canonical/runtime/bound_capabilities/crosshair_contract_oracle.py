#!/usr/bin/env python3
"""CrossHair PEP316 checks, disabled by default for untrusted host execution.

CrossHair imports and executes caller code. This adapter is not a sandbox:
project code can access the host and forge analyzer output. A caller must
explicitly opt into that risk. Results describe the local tool run, not an
independent attestation or proof that a contract holds universally.
"""
from __future__ import annotations

import ast
import hashlib
import json
import math
import os
import pathlib
import re
import sys
import tempfile

from canonical.runtime.bound_capabilities.python_test_guided_patch_search_v1 import _run_process

SCHEMA = "PROJECT_BRAIN_CROSSHAIR_CONTRACT_ORACLE_V1"
REPORT_RE = re.compile(r"^(?P<path>.+?):(?P<line>\d+):\s*(?P<kind>error|info):\s*(?P<msg>.*)$")
POST_RE = re.compile(r"^\s*(?:-\s*)?post(?:condition)?\s*:\s*\S", re.I)


def _safe_path(root: str, raw) -> pathlib.Path:
    root_p = pathlib.Path(root).resolve()
    raw_s = str(raw or "")
    p = pathlib.Path(raw_s)
    if not p.is_absolute():
        p = root_p / raw_s
    p = p.resolve()
    if root_p not in p.parents and p != root_p:
        raise ValueError("PATH_OUTSIDE_ROOT")
    return p


def _postconditions(source: bytes) -> int:
    if len(source) > 1024 * 1024:
        return 0
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError, UnicodeError, RecursionError):
        return 0
    count = 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            count += sum(bool(POST_RE.match(line)) for line in (ast.get_docstring(node) or "").splitlines())
    return count


def run(args: dict, root: str) -> dict:
    args = dict(args or {})
    target = _safe_path(root, args.get("target_path"))
    output = _safe_path(root, args.get("output_path"))
    if not target.is_file():
        raise ValueError("ORACLE_TARGET_MISSING")
    if (output == pathlib.Path(root).resolve() or output == target
            or (output.exists() and output.samefile(target))
            or (output.is_file() and (output.suffix == ".py" or output.stat().st_nlink > 1))):
        raise ValueError("OUTPUT_OVERLAPS_INPUT")
    source = target.read_bytes()
    target_sha = hashlib.sha256(source).hexdigest()
    target_mode = target.stat().st_mode & 0o7777
    declared = _postconditions(source)
    timeout = float(args.get("timeout_s") if args.get("timeout_s") is not None else 300)
    if not math.isfinite(timeout) or not 0 < timeout <= 3600:
        raise ValueError("INVALID_TIMEOUT")
    result = {
        "schema": SCHEMA, "oracle": "crosshair", "model_dependency_count": 0,
        "target": str(target), "target_sha256": target_sha, "declared_postconditions": declared,
        "status": "HOST_EXECUTION_NOT_AUTHORIZED", "violations": [], "violation_count": 0,
        "checked_conditions": 0, "returncode": None, "verified": False, "proves_absence": False,
        "host_execution_is_sandboxed": False, "independent_attestation": False,
    }
    if args.get("allow_unsafe_host_execution") is True:
        if not declared:
            result["status"] = "NO_CHECKABLE_CONTRACTS"
        else:
            try:
                proc = _run_process(pathlib.Path(root).resolve(),
                                    [sys.executable, "-m", "crosshair", "check", "--report_all",
                                     "--analysis_kind=PEP316", str(target)], timeout)
            except OSError:
                proc = {"returncode": None, "stdout": "", "stderr": "", "timed_out": False}
            violations, confirmed, unconfirmed = [], [], []
            for line in (proc["stdout"] + "\n" + proc["stderr"]).splitlines():
                match = REPORT_RE.match(line.strip())
                if not match:
                    continue
                try:
                    report_path = pathlib.Path(match.group("path")).resolve()
                except (OSError, ValueError):
                    continue
                if report_path != target:
                    continue
                row = {"file": str(report_path), "line": int(match.group("line")),
                       "message": match.group("msg").strip()}
                if match.group("kind") == "error":
                    violations.append(row)
                elif row["message"] == "Confirmed over all paths.":
                    confirmed.append(row)
                else:
                    unconfirmed.append(row)
            try:
                intact = (target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest() == target_sha
                          and target.stat().st_mode & 0o7777 == target_mode)
            except OSError:
                intact = False
            if not intact:
                status = "INPUT_CHANGED"
                violations = []
            elif proc["timed_out"]:
                status = "ORACLE_TIMEOUT"
                violations = []
            elif proc["returncode"] == 1 and violations:
                status = "CONTRACT_VIOLATION_FOUND"
            elif (proc["returncode"] == 0 and len(confirmed) >= declared and not unconfirmed
                  and not violations):
                status = "NO_COUNTEREXAMPLE_FOUND"
            else:
                status = "ORACLE_INCONCLUSIVE"
                violations = []
            result.update(status=status, violations=violations, violation_count=len(violations),
                          checked_conditions=len(confirmed) + len(unconfirmed) + len(violations),
                          returncode=proc["returncode"], input_integrity=intact,
                          verified=status in ("CONTRACT_VIOLATION_FOUND", "NO_COUNTEREXAMPLE_FOUND"))
    raw = (json.dumps(result, indent=2, sort_keys=True) + "\n").encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix=".brain-crosshair-", dir=output.parent, delete=False) as f:
        temp_name = f.name
        try:
            f.write(raw)
        except BaseException:
            pathlib.Path(temp_name).unlink(missing_ok=True)
            raise
    try:
        os.replace(temp_name, output)
    finally:
        pathlib.Path(temp_name).unlink(missing_ok=True)
    result["output_path"] = str(output)
    result["output_sha256"] = hashlib.sha256(raw).hexdigest()
    result["output_verified"] = output.read_bytes() == raw
    return result
