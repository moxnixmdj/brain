"""Strict raw-goal acceptance for one Python unittest audit cell.

This is not general natural-language understanding. It recognizes one exact
goal grammar whose requested semantics are fully machine-checkable, executes the
already-promoted Brain-owned test-audit capability, and independently re-runs
the same test corpus before accepting the raw obligations.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any, Mapping

from canonical.runtime import astra_runtime

SCHEMA = "PROJECT_BRAIN_RAW_GOAL_PYTHON_TEST_AUDIT_ACCEPTANCE_V1"
CAPABILITY = "python.tests.audit.unittest"
ROUTING_EFFECT = "python.tests.audit"
GRAMMAR = re.compile(
    r"Audit Python unittest files under "
    r"(?P<source>canonical/[A-Za-z0-9_./-]+) matching "
    r"(?P<pattern>[A-Za-z0-9_*?.-]+) and save the report to "
    r"(?P<output>canonical/astra_runtime/tmp/[A-Za-z0-9_.-]+\.json), "
    r"reporting tests, passed, failed, errors, and skipped counts\.",
    re.IGNORECASE | re.ASCII,
)


def _digest(raw: bytes) -> str:
    return sha256(raw).hexdigest()


def _safe_relative(value: str, *, required_prefix: str | None = None) -> bool:
    if not isinstance(value, str) or not value or "\\" in value:
        return False
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        return False
    if required_prefix is not None and not value.startswith(required_prefix):
        return False
    return True


def _unresolved(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "pass": False,
        "status": "UNRESOLVED__RAW_GOAL_PYTHON_TEST_AUDIT_ACCEPTANCE",
        "reason": reason,
        "accepted_obligation_ids": [],
        "required_obligation_count": 0,
        "semantic_acceptance_complete": False,
        "actual_goal_satisfaction_verified": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def preflight(goal: str) -> dict[str, Any]:
    text = str(goal or "")
    match = GRAMMAR.fullmatch(text)
    if match is None:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "NO_EXACT_PYTHON_TEST_AUDIT_GOAL_MATCH",
            "matched": False,
            "semantic_authority": False,
            "execution_authority": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
    source = match.group("source")
    pattern = match.group("pattern")
    output = match.group("output")
    if (
        not _safe_relative(source, required_prefix="canonical/")
        or not _safe_relative(output, required_prefix="canonical/astra_runtime/tmp/")
        or "/" in pattern
        or "\\" in pattern
    ):
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED",
            "matched": False,
            "reason": "PYTHON_TEST_AUDIT_GOAL_PATH_OR_PATTERN_INVALID",
            "semantic_authority": False,
            "execution_authority": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__EXACT_PYTHON_TEST_AUDIT_GOAL_PREFLIGHT",
        "matched": True,
        "goal_sha256": _digest(text.encode("utf-8")),
        "capability_id": CAPABILITY,
        "routing_effect": ROUTING_EFFECT,
        "bound_inputs": {
            "source_root": source.rstrip("/"),
            "pattern": pattern,
            "output_path": output,
            "timeout_s": 180,
        },
        "semantic_scope": (
            "EXACT_PYTHON_UNITTEST_ROOT_PATTERN_EPHEMERAL_REPORT_AND_"
            "TESTS_PASSED_FAILED_ERRORS_SKIPPED_COUNTS"
        ),
        "semantic_authority": False,
        "execution_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }


def verify(
    *,
    goal: str,
    inputs: Mapping[str, Any],
    execution: Mapping[str, Any],
    raw_contract: Mapping[str, Any],
    root: Path,
) -> dict[str, Any]:
    try:
        pf = preflight(goal)
        if pf.get("pass") is not True or pf.get("matched") is not True:
            return _unresolved("NO_EXACT_AUTHENTICATED_GOAL_GRAMMAR")
        expected_inputs = pf["bound_inputs"]
        if dict(inputs) != expected_inputs:
            return _unresolved("GOAL_TO_EXECUTION_INPUT_BINDING_MISMATCH")
        if not isinstance(raw_contract, Mapping) or raw_contract.get("pass") is not True:
            return _unresolved("RAW_TASK_CONTRACT_NOT_VERIFIED")
        if raw_contract.get("task_sha256") != pf["goal_sha256"]:
            return _unresolved("RAW_GOAL_HASH_MISMATCH")
        if raw_contract.get("nonwhitespace_source_coverage_complete") is not True:
            return _unresolved("RAW_SOURCE_COVERAGE_INCOMPLETE")
        routing = raw_contract.get("routing_contract")
        if (
            not isinstance(routing, Mapping)
            or routing.get("target_effects") != [ROUTING_EFFECT]
        ):
            return _unresolved("RAW_ROUTING_EFFECT_MISMATCH")

        acceptance = raw_contract.get("acceptance_contract")
        if not isinstance(acceptance, Mapping):
            return _unresolved("RAW_ACCEPTANCE_CONTRACT_MISSING")
        obligations = acceptance.get("obligations")
        required_ids = acceptance.get("required_obligation_ids")
        if not isinstance(obligations, list) or not obligations:
            return _unresolved("RAW_ACCEPTANCE_OBLIGATIONS_MISSING")
        ids = [
            row.get("obligation_id")
            for row in obligations
            if isinstance(row, Mapping)
        ]
        if (
            len(ids) != len(obligations)
            or not all(isinstance(x, str) and x for x in ids)
            or len(set(ids)) != len(ids)
            or required_ids != ids
            or any(
                not isinstance(row, Mapping)
                or row.get("task_sha256") != pf["goal_sha256"]
                for row in obligations
            )
        ):
            return _unresolved("RAW_OBLIGATION_BINDING_INVALID")

        if not isinstance(execution, Mapping) or execution.get("pass") is not True:
            return _unresolved("PROMOTED_CAPABILITY_EXECUTION_NOT_VERIFIED")
        if execution.get("capability_id") != CAPABILITY:
            return _unresolved("EXECUTION_CAPABILITY_ID_MISMATCH")
        if not execution.get("composition_capsule_head_hash"):
            return _unresolved("INDEPENDENT_EXECUTION_TRACE_PROOF_MISSING")
        rendered = execution.get("rendered_action")
        if not isinstance(rendered, Mapping):
            return _unresolved("RENDERED_ACTION_MISSING")
        args = rendered.get("args")
        if not isinstance(args, Mapping) or args.get("capability_id") != CAPABILITY:
            return _unresolved("RENDERED_ACTION_CAPABILITY_MISMATCH")
        for key, value in expected_inputs.items():
            if args.get(key) != value:
                return _unresolved("RENDERED_ACTION_INPUT_MISMATCH:" + key)

        result = execution.get("result")
        if not isinstance(result, Mapping) or result.get("output_verified") is not True:
            return _unresolved("CAPABILITY_OUTPUT_PROOF_MISSING")

        repo = Path(root).resolve()
        source = (repo / expected_inputs["source_root"]).resolve()
        output = (repo / expected_inputs["output_path"]).resolve()
        if (
            source == repo
            or repo not in source.parents
            or output == repo
            or repo not in output.parents
            or not source.is_dir()
            or source.is_symlink()
            or not output.is_file()
            or output.is_symlink()
        ):
            return _unresolved("SOURCE_OR_OUTPUT_UNSAFE_OR_MISSING")

        report = json.loads(output.read_text(encoding="utf-8"))
        if not isinstance(report, Mapping):
            return _unresolved("AUDIT_REPORT_NOT_OBJECT")
        if report.get("schema") != "PROJECT_BRAIN_PYTHON_TEST_AUDIT_V1":
            return _unresolved("AUDIT_REPORT_SCHEMA_INVALID")
        if (
            report.get("source_root") != expected_inputs["source_root"]
            or report.get("pattern") != expected_inputs["pattern"]
        ):
            return _unresolved("AUDIT_REPORT_SCOPE_MISMATCH")
        records = report.get("records")
        totals = report.get("totals")
        if not isinstance(records, list) or not records or not isinstance(totals, Mapping):
            return _unresolved("AUDIT_REPORT_SHAPE_INVALID")

        # Independent post-execution replay. This action does not call the
        # python_test_audit builder; it fresh-executes each selected test file
        # and independently checks record coverage, source hashes and totals.
        fresh = astra_runtime._goal_action({
            "type": "assert_python_test_audit_supported_by_fresh_execution",
            "args": {
                "audit_path": expected_inputs["output_path"],
                "source_root": expected_inputs["source_root"],
                "pattern": expected_inputs["pattern"],
            },
        })
        if not isinstance(fresh, Mapping) or fresh.get("verified") is not True:
            return _unresolved(
                "FRESH_INDEPENDENT_TEST_EXECUTION_DID_NOT_SUPPORT_AUDIT",
                fresh_verification=dict(fresh) if isinstance(fresh, Mapping) else None,
            )
        if fresh.get("totals") != totals or fresh.get("errors") not in ([], None):
            return _unresolved("FRESH_TEST_TOTALS_OR_ERRORS_MISMATCH")

        expected_result = {
            "output_path": expected_inputs["output_path"],
            "output_sha256": _digest(output.read_bytes()),
            "file_count": int(totals.get("files", -1)),
            "test_count": int(totals.get("tests", -1)),
            "passed_count": int(totals.get("passed", -1)),
            "failed_count": int(totals.get("failed", -1)),
            "error_count": int(totals.get("errors", -1)),
            "skipped_count": int(totals.get("skipped", -1)),
        }
        for key, value in expected_result.items():
            if result.get(key) != value:
                return _unresolved("EXECUTION_RESULT_REPORT_MISMATCH:" + key)
        if expected_result["file_count"] <= 0:
            return _unresolved("AUDIT_EMPTY")
        if expected_result["failed_count"] != 0 or expected_result["error_count"] != 0:
            return _unresolved("AUDIT_CONTAINS_TEST_FAILURES")

        return {
            "schema": SCHEMA,
            "pass": True,
            "status": "PASS__EXACT_RAW_GOAL_PYTHON_TEST_AUDIT_ACCEPTED",
            "goal_sha256": pf["goal_sha256"],
            "task_contract_sha256": raw_contract.get("task_contract_sha256"),
            "accepted_obligation_ids": ids,
            "required_obligation_count": len(ids),
            "verified_source_root": expected_inputs["source_root"],
            "verified_pattern": expected_inputs["pattern"],
            "verified_output_path": expected_inputs["output_path"],
            "verified_output_sha256": expected_result["output_sha256"],
            "verified_totals": dict(totals),
            "fresh_verification": dict(fresh),
            "semantic_acceptance_complete": True,
            "actual_goal_satisfaction_verified": True,
            "acceptance_scope": pf["semantic_scope"],
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
    except Exception as exc:
        return _unresolved(type(exc).__name__ + ":" + str(exc))
