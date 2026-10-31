#!/usr/bin/env python3
"""Bounded property checks of a caller-supplied unary integer function ``f``.

Reuse the concrete oracle's existing docstring contract language, but generate
inputs with Hypothesis. The shared contract evaluator means these are NOT two
independent semantic implementations. A clean finite sample is never a proof.
Source evaluation happens in a time-bounded child, not the controller process;
this process boundary is not an OS security sandbox for hostile code.
"""
from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import json
import os
import pathlib
import signal
import subprocess
import sys
import tempfile
from typing import Any

SCHEMA = "PROJECT_BRAIN_EVIDENCE_ORACLE_HYPOTHESIS_V1"
CAPABILITY_ID = "evidence.oracle.hypothesis_property.v1"
PROVIDES = ["evidence.hypothesis.property_violation", "evidence.property_test.verified"]
REQUIRES = ["python.source.file.available"]


def _safe_output(root: pathlib.Path, raw: str | None) -> pathlib.Path:
    p = (root / str(raw or "canonical/tmp_hypothesis_oracle.json")).resolve()
    if p == root or root not in p.parents:
        raise ValueError("PATH_OUTSIDE_REPOSITORY")
    return p


def _integer(args: dict, name: str, default: int, low: int, high: int) -> int:
    value = args.get(name, default)
    if type(value) is not int or not low <= value <= high:
        raise ValueError(name.upper() + "_INVALID")
    return value


def _load_contract_oracle():
    path = pathlib.Path(__file__).with_name("concrete_execution_oracle.py")
    spec = importlib.util.spec_from_file_location("_brain_property_contract", path)
    oracle = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(oracle)
    return oracle


def _check(payload: dict) -> dict:
    """Worker protocol. Counts actual function calls, including shrinking calls."""
    result = {
        "status": "ERROR__PROPERTY_CHECK", "checked": 0, "violations": [],
        "hypothesis_available": False, "check_completed": False,
        "verified": False, "proves_absence": False,
    }
    if payload.get("engine") == "concrete":
        try:
            oracle = _load_contract_oracle()
            observed = oracle.check_source(payload["source"])
            completed = observed["checked"] > 0 and observed["status"] in (
                "CONTRACT_VIOLATION_FOUND", "NO_COUNTEREXAMPLE_IN_SAMPLE")
            unevaluable = any(str(v.get("reason", "")).startswith("unevaluable:")
                              for v in observed["violations"])
            return {**result, **observed, "check_completed": completed and not unevaluable,
                    "verified": completed and not observed["violations"],
                    "status": "ERROR__CONTRACT_NOT_EVALUABLE" if unevaluable else observed["status"]}
        except Exception as exc:
            return {**result, "error": type(exc).__name__ + ":" + str(exc)[:400]}
    try:
        from hypothesis import HealthCheck, Phase, find, settings, strategies as st
        from hypothesis.errors import NoSuchExample
    except ImportError:
        return {**result, "status": "UNAVAILABLE__HYPOTHESIS"}
    result["hypothesis_available"] = True
    try:
        oracle = _load_contract_oracle()
        source = payload["source"]
        # Inspect contracts without inventing a function/property or running a demo.
        import ast
        tree = ast.parse(source)
        fn = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "f"), None)
        if fn is None:
            return {**result, "status": "UNSUPPORTED__FUNCTION_F_REQUIRED"}
        posts = oracle._posts(ast.get_docstring(fn) or "")
        if not posts:
            return {**result, "status": "UNSUPPORTED__POSTCONDITION_REQUIRED"}
        result["posts"] = posts
        # Syntax errors in the contract are errors, not counterexamples or passes.
        for post in posts:
            compile(post, "<postcondition>", "eval")

        def violates(x):
            observation = oracle.check_source(source, sample=(x,))
            result["checked"] += observation["checked"]
            if observation["status"] == "NO_POSTCONDITION_PARSED":
                raise ValueError("RUNTIME_POSTCONDITION_MISSING")
            violations = observation["violations"]
            if any(str(v.get("reason", "")).startswith("unevaluable:") for v in violations):
                raise ValueError("POSTCONDITION_NOT_EVALUABLE")
            if violations:
                result["violations"] = violations
            return bool(violations)

        options = settings(
            max_examples=payload["max_examples"], database=None, derandomize=True,
            deadline=None, phases=(Phase.generate, Phase.shrink),
            suppress_health_check=(HealthCheck.too_slow,),
        )
        try:
            witness = find(st.integers(payload["min_value"], payload["max_value"]),
                           violates, settings=options)
            # Re-read the minimized witness with the same concrete evaluator.
            violates(witness)
            result["status"] = "CONTRACT_VIOLATION_FOUND"
        except NoSuchExample:
            result["status"] = "NO_COUNTEREXAMPLE_IN_SAMPLE"
            result["violations"] = []
        result["check_completed"] = result["checked"] > 0
        result["verified"] = result["check_completed"] and not result["violations"]
    except Exception as exc:
        result.update(status="ERROR__PROPERTY_CHECK", verified=False, check_completed=False,
                      error=type(exc).__name__ + ":" + str(exc)[:400])
    return result


def _worker() -> None:
    payload = json.load(sys.stdin)
    # Bound output files and memory where supported. Not a filesystem sandbox.
    if os.name == "posix":
        import resource
        resource.setrlimit(resource.RLIMIT_FSIZE, (1 << 20, 1 << 20))
        resource.setrlimit(resource.RLIMIT_AS, (512 << 20, 512 << 20))
    with open(os.devnull, "w") as sink, contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
        result = _check(payload)
    print(json.dumps(result, sort_keys=True, default=repr))


def _run_worker(payload: dict, timeout: int) -> dict:
    failure = {"status": "ERROR__PROPERTY_WORKER", "checked": 0, "violations": [],
               "verified": False, "check_completed": False,
               "hypothesis_available": False, "proves_absence": False}
    # File-backed streams avoid buffering arbitrary source output in controller RAM.
    with tempfile.TemporaryDirectory(prefix="brain-property-") as work:
        with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
            proc = subprocess.Popen(
                [sys.executable, "-I", str(pathlib.Path(__file__).resolve()), "--worker"],
                stdin=subprocess.PIPE, stdout=stdout, stderr=stderr, cwd=work,
                start_new_session=(os.name == "posix"),
            )
            try:
                proc.communicate(json.dumps(payload).encode(), timeout=timeout)
            except subprocess.TimeoutExpired:
                if os.name == "posix":
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                else:
                    proc.kill()
                proc.communicate()
                result = {**failure, "status": "TIMEOUT__PROPERTY_CHECK"}
            else:
                stdout.seek(0)
                try:
                    result = json.loads(stdout.read((1 << 20) + 1)) if proc.returncode == 0 else failure
                    if not isinstance(result, dict):
                        result = failure
                except (ValueError, UnicodeError):
                    result = failure
    return result


def run(args: dict[str, Any], root: str | pathlib.Path) -> dict[str, Any]:
    repo = pathlib.Path(root).resolve()
    output = _safe_output(repo, args.get("output_path"))
    source = args.get("source")
    source_path = None
    if source is None and args.get("source_path"):
        source_path = (repo / str(args["source_path"])).resolve()
        if source_path == repo or repo not in source_path.parents:
            raise ValueError("PATH_OUTSIDE_REPOSITORY")
        if source_path == output:
            raise ValueError("OUTPUT_ALIASES_SOURCE")
        source = source_path.read_text(encoding="utf-8")
    if not isinstance(source, str) or not source.strip():
        raise ValueError("SOURCE_REQUIRED")
    if len(source.encode("utf-8")) > 1 << 20:
        raise ValueError("SOURCE_TOO_LARGE")
    if output.exists():
        raise ValueError("OUTPUT_ALREADY_EXISTS")
    payload = {
        "source": source,
        "max_examples": _integer(args, "max_examples", 50, 1, 5000),
        "min_value": _integer(args, "min_value", -100, -(2**63), 2**63 - 1),
        "max_value": _integer(args, "max_value", 100, -(2**63), 2**63 - 1),
    }
    if payload["min_value"] > payload["max_value"]:
        raise ValueError("INTEGER_RANGE_INVALID")
    timeout = _integer(args, "timeout_s", 10, 1, 120)
    result = _run_worker(payload, timeout)
    artifact = {
        **result, "schema": SCHEMA, "capability_id": CAPABILITY_ID,
        "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
        "input_bounds": {k: v for k, v in payload.items() if k != "source"},
        "model_dependency_count": 0, "incremental_spend_usd": 0,
        "scope": "FINITE_UNARY_INTEGER_SAMPLE_SHARED_CONTRACT_EVALUATOR_NOT_A_PROOF",
    }
    raw = json.dumps(artifact, sort_keys=True, separators=(",", ":")).encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as stream:
        stream.write(raw)
    return {**artifact, "adapter": "evidence_oracle_hypothesis_v1",
            "output_path": str(output.relative_to(repo)),
            "output_sha256": hashlib.sha256(raw).hexdigest(),
            "output_verified": artifact["verified"] is True}


if __name__ == "__main__" and sys.argv[1:] == ["--worker"]:
    _worker()
