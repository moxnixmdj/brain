"""Benchmark-independent scientific numeric task pipeline V1.

Thin transaction layer over already-verified Brain-owned components:
raw explicit numeric task -> typed compilation -> verified scientific solve ->
optional declared artifact materialization.

This layer adds no scientific solving semantics and no benchmark routing.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime import scientific_numeric_task_compiler_v1 as compiler
from canonical.runtime import general_scientific_capability_controller_v1 as controller
from canonical.runtime import scientific_artifact_contract_v1 as artifacts

SCHEMA = "PROJECT_BRAIN_SCIENTIFIC_NUMERIC_TASK_PIPELINE_V1"
MODEL_DEPENDENCY_COUNT = 0
EXTERNAL_MODEL_RUNTIME_CALLS = 0
NETWORK_DEPENDENCY_COUNT = 0


def _canon(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
        default=str,
    )


def _digest(value: Any) -> str:
    return sha256(_canon(value).encode("utf-8")).hexdigest()


def _fail(phase: str, reason: str, *, trace: list[dict[str, Any]], details: Mapping[str, Any] | None = None) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "verified": False,
        "failed_phase": phase,
        "reason": reason,
        "trace": list(trace),
        "model_dependency_count": 0,
        "external_model_runtime_calls": 0,
        "network_dependency_count": 0,
        "benchmark_identifier_used_for_routing": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    if details:
        out["details"] = dict(details)
    return out


def execute(
    instruction: str,
    raw_rows: Any,
    *,
    artifact_specs: Sequence[Mapping[str, Any]] | None = None,
    output_root: str | Path | None = None,
) -> dict[str, Any]:
    """Execute one bounded numeric scientific task fail closed."""
    trace: list[dict[str, Any]] = []

    compiled = compiler.compile_numeric_task(instruction, raw_rows)
    trace.append({
        "phase": "COMPILE",
        "status": compiled.get("status"),
        "family": compiled.get("family"),
        "receipt_sha256": _digest(compiled),
    })
    if compiled.get("status") != "COMPILED":
        return _fail(
            "COMPILE",
            str(compiled.get("reason") or "NUMERIC_TASK_COMPILATION_FAILED"),
            trace=trace,
            details={"compiler_receipt": compiled},
        )

    problem = compiled.get("task_problem")
    if not isinstance(problem, Mapping):
        return _fail("COMPILE", "COMPILED_TASK_PROBLEM_INVALID", trace=trace)

    solved = controller.solve(problem)
    trace.append({
        "phase": "SOLVE_VERIFY",
        "status": solved.get("status"),
        "family": solved.get("family"),
        "verified": solved.get("verified") is True,
        "receipt_sha256": _digest(solved),
    })
    if solved.get("verified") is not True:
        return _fail(
            "SOLVE_VERIFY",
            str(solved.get("status") or "SCIENTIFIC_RESULT_NOT_VERIFIED"),
            trace=trace,
            details={"solver_receipt": solved},
        )

    materialization = None
    if (artifact_specs is None) != (output_root is None):
        return _fail(
            "ARTIFACT_CONTRACT",
            "ARTIFACT_SPECS_AND_OUTPUT_ROOT_MUST_BE_PROVIDED_TOGETHER",
            trace=trace,
        )
    if artifact_specs is not None:
        materialization = artifacts.materialize_artifacts(solved, artifact_specs, output_root)
        trace.append({
            "phase": "ARTIFACT_MATERIALIZATION",
            "status": materialization.get("status"),
            "receipt_sha256": _digest(materialization),
        })
        if materialization.get("status") != "PASS__DECLARED_SCIENTIFIC_ARTIFACTS_MATERIALIZED_AND_VERIFIED":
            return _fail(
                "ARTIFACT_MATERIALIZATION",
                str(materialization.get("reason") or "ARTIFACT_MATERIALIZATION_FAILED"),
                trace=trace,
                details={"artifact_receipt": materialization},
            )

    receipt = {
        "schema": SCHEMA,
        "status": "PASS__SCIENTIFIC_NUMERIC_TASK_PIPELINE_VERIFIED",
        "pass": True,
        "verified": True,
        "family": compiled.get("family"),
        "compiler": compiled,
        "scientific_result": solved,
        "artifact_materialization": materialization,
        "trace": trace,
        "model_dependency_count": 0,
        "external_model_runtime_calls": 0,
        "network_dependency_count": 0,
        "dynamic_code_execution": False,
        "benchmark_identifier_used_for_routing": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    receipt["receipt_sha256"] = _digest({
        "family": receipt["family"],
        "compiler": compiled,
        "scientific_result": solved,
        "artifact_materialization": materialization,
        "trace": trace,
    })
    return receipt
