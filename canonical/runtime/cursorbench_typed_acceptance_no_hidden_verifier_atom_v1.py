"""Proof one typed-acceptance membership atom from prior independent execution.

This module proves only SPEC_ACCEPT_NO_HIDDEN_VERIFIER_ACCESS_V1 for the exact
bounded SPECIFICATION_TO_INDEPENDENT_ACCEPTANCE_MODEL_001 diagnostic route whose
candidate/suite/test bytes were independently executed on the public runner.

It does not infer arbitrary CursorBench membership and proves no semantic,
failure-mode-completeness, or dependency-provenance atom.
"""
from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_CURSORBENCH_TYPED_ACCEPTANCE_NO_HIDDEN_VERIFIER_ATOM_PROOF_V2"
ATOM_ID = "SPEC_ACCEPT_NO_HIDDEN_VERIFIER_ACCESS_V1"
ATOM_SEMANTICS = (
    "NO_HIDDEN_VERIFIER_OR_TASK_SPECIFIC_SOLUTION_INFORMATION_WAS_USED_BEFORE_"
    "TERMINAL_AUTHORIZATION"
)

EVIDENCE_PATH = (
    "canonical/verification/"
    "M0A_RAW_SOURCE_POST_REPAIR_PUBLIC_RUNNER_20261002_V1.json"
)
EVIDENCE_BLOB_SHA = "0eef12725a992a5f3377340ee4dcacb65e74b0cc"
CANDIDATE_PATH = "canonical/runtime/m0a_raw_source_brain_candidate_v2.py"
CANDIDATE_BLOB_SHA = "0aac96d27068bdad379703c1b0b8a7a32cacb2e2"
SUITE_PATH = "canonical/runtime/m0a_raw_source_terminal_suite_v2.py"
SUITE_BLOB_SHA = "63b5daacfa5623c38228d41f6a84e548890d252d"
TEST_PATH = "canonical/tests/test_m0a_raw_source_terminal_suite_v2.py"
TEST_BLOB_SHA = "6c4db6c0baa12d067cd277858fd9534cd794f871"
BEHAVIOR_ID = "SPECIFICATION_TO_INDEPENDENT_ACCEPTANCE_MODEL_001"
ROOT = Path(__file__).resolve().parents[2]


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED__NO_HIDDEN_VERIFIER_ATOM_UNPROVED",
        "reason": reason,
        "atom_id": ATOM_ID,
        "atom_truth_authorized": False,
        "proved_constraint": None,
        "membership_self_certified": False,
        "whole_policy_condition_proved": False,
        "whole_specification_behavior_adequate": False,
        "whole_cursorbench_adequate": False,
        "terminal_authority": False,
        "acceptance_credit_delta": 0,
        "terminal_credit_delta": 0,
    }
    if detail:
        out["detail"] = detail
    return out


def _safe_exact_file(
    root: Path,
    rel: str,
    expected_sha: str,
) -> tuple[Path | None, dict[str, Any] | None]:
    p = Path(rel)
    if p.is_absolute() or ".." in p.parts:
        return None, _fail("BOUND_PATH_INVALID", path=rel)
    target = root / p
    try:
        resolved = target.resolve(strict=True)
        resolved.relative_to(root)
    except Exception as exc:
        return None, _fail(
            "BOUND_PATH_RESOLUTION_FAILED",
            path=rel,
            error=type(exc).__name__ + ":" + str(exc),
        )
    if target.is_symlink() or not target.is_file():
        return None, _fail("BOUND_FILE_NOT_REGULAR", path=rel)
    actual = _git_blob_sha(target)
    if actual != expected_sha:
        return None, _fail(
            "BOUND_FILE_DRIFT",
            path=rel,
            expected=expected_sha,
            actual=actual,
        )
    return target, None


def verify(
    evidence_ref: Mapping[str, Any],
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    if not isinstance(evidence_ref, Mapping):
        return _fail("EVIDENCE_REFERENCE_NOT_OBJECT")
    if evidence_ref.get("path") != EVIDENCE_PATH:
        return _fail("EVIDENCE_PATH_NOT_EXACT_INDEPENDENT_RECEIPT")
    if evidence_ref.get("git_blob_sha") != EVIDENCE_BLOB_SHA:
        return _fail("EVIDENCE_REFERENCE_SHA_MISMATCH")

    try:
        root = (Path(repo_root) if repo_root is not None else ROOT).resolve(strict=True)
        bound = (
            (EVIDENCE_PATH, EVIDENCE_BLOB_SHA),
            (CANDIDATE_PATH, CANDIDATE_BLOB_SHA),
            (SUITE_PATH, SUITE_BLOB_SHA),
            (TEST_PATH, TEST_BLOB_SHA),
        )
        files: dict[str, Path] = {}
        for rel, expected in bound:
            target, error = _safe_exact_file(root, rel, expected)
            if error is not None or target is None:
                return error or _fail("BOUND_FILE_UNAVAILABLE", path=rel)
            files[rel] = target

        receipt = json.loads(files[EVIDENCE_PATH].read_text(encoding="utf-8"))
        if receipt.get("schema") != (
            "PROJECT_BRAIN_M0A_RAW_SOURCE_POST_REPAIR_PUBLIC_RUNNER_20261002_V1"
        ):
            return _fail("INDEPENDENT_RECEIPT_SCHEMA_INVALID")
        if receipt.get("behavior_id") != BEHAVIOR_ID:
            return _fail("INDEPENDENT_RECEIPT_BEHAVIOR_MISMATCH")
        if not str(receipt.get("status") or "").startswith(
            "INDEPENDENT_POST_REPAIR_DIAGNOSTIC_PASS__64_OF_64"
        ):
            return _fail("INDEPENDENT_RECEIPT_NOT_PASS")

        exact = receipt.get("exact_brain_blobs")
        if not isinstance(exact, Mapping):
            return _fail("INDEPENDENT_RECEIPT_BLOB_BINDING_MISSING")
        expected_bindings = {
            "candidate": CANDIDATE_BLOB_SHA,
            "suite": SUITE_BLOB_SHA,
            "test": TEST_BLOB_SHA,
        }
        for key, expected in expected_bindings.items():
            if exact.get(key) != expected:
                return _fail(
                    "INDEPENDENT_RECEIPT_BLOB_BINDING_MISMATCH",
                    field=key,
                    expected=expected,
                    actual=exact.get(key),
                )

        runner = receipt.get("public_runner")
        if not isinstance(runner, Mapping) or runner.get("conclusion") != "success":
            return _fail("INDEPENDENT_PUBLIC_RUNNER_SUCCESS_NOT_BOUND")
        result = receipt.get("result")
        if (
            not isinstance(result, Mapping)
            or result.get("case_count") != 64
            or result.get("passed") != 64
            or result.get("failed") != 0
        ):
            return _fail("INDEPENDENT_EXECUTION_RESULT_NOT_64_OF_64")

        test_source = files[TEST_PATH].read_text(encoding="utf-8")
        required_test_contract = (
            "test_oracle_never_enters_public_payload",
            'self.assertNotIn("_oracle",public)',
            'self.assertNotIn("requirements",public)',
            "test_candidate_does_not_import_evaluator",
            'self.assertNotIn("m0a_raw_source_terminal_suite_v2",src)',
            'self.assertNotIn("_oracle",src)',
            "test_diagnostic_executes_and_preserves_failures",
            "suite.run_batch(seed,64,candidate.solve)",
        )
        missing_test_contract = [
            token for token in required_test_contract if token not in test_source
        ]
        if missing_test_contract:
            return _fail(
                "BOUND_TEST_DOES_NOT_ENFORCE_INFORMATION_BOUNDARY",
                missing=missing_test_contract,
            )

        suite_source = files[SUITE_PATH].read_text(encoding="utf-8")
        required_suite_dataflow = (
            'def public_task(case: Mapping[str, Any])',
            '"case_id": case["case_id"]',
            '"raw_source": case["raw_source"]',
            "public = public_task(case)",
            "got = solver(public)",
        )
        missing_suite_dataflow = [
            token for token in required_suite_dataflow if token not in suite_source
        ]
        if missing_suite_dataflow:
            return _fail(
                "BOUND_SUITE_PUBLIC_DATAFLOW_NOT_PROVED",
                missing=missing_suite_dataflow,
            )

        candidate_source = files[CANDIDATE_PATH].read_text(encoding="utf-8")
        if "m0a_raw_source_terminal_suite_v2" in candidate_source:
            return _fail("CANDIDATE_IMPORTS_HIDDEN_SUITE")
        if "_oracle" in candidate_source:
            return _fail("CANDIDATE_REFERENCES_HIDDEN_ORACLE")

        return {
            "schema": SCHEMA,
            "pass": True,
            "status": (
                "PASS__NO_HIDDEN_VERIFIER_ATOM_PROVED_FROM_INDEPENDENT_"
                "EXECUTED_EXACT_DATAFLOW"
            ),
            "atom_id": ATOM_ID,
            "atom_semantics": ATOM_SEMANTICS,
            "atom_truth_authorized": True,
            "proof_basis": (
                "EXACT_CANDIDATE_SUITE_TEST_BYTES__INDEPENDENT_PUBLIC_RUNNER_PASS__"
                "PUBLIC_TASK_DATAFLOW_EXCLUDES_ORACLE__CANDIDATE_SOURCE_HAS_NO_ORACLE_ROUTE"
            ),
            "evidence_path": EVIDENCE_PATH,
            "evidence_git_blob_sha": EVIDENCE_BLOB_SHA,
            "candidate_git_blob_sha": CANDIDATE_BLOB_SHA,
            "suite_git_blob_sha": SUITE_BLOB_SHA,
            "test_git_blob_sha": TEST_BLOB_SHA,
            "proved_constraint": {"op": "ATOM", "id": ATOM_ID},
            "other_condition_atoms_proved": [],
            "scope_boundary": (
                "EXACT_BOUNDED_SPECIFICATION_TO_INDEPENDENT_ACCEPTANCE_MODEL_001_"
                "DIAGNOSTIC_ROUTE_ONLY__NO_ARBITRARY_CURSORBENCH_OR_HARBOR_CLAIM"
            ),
            "membership_self_certified": False,
            "whole_policy_condition_proved": False,
            "whole_specification_behavior_adequate": False,
            "whole_cursorbench_adequate": False,
            "terminal_authority": False,
            "acceptance_credit_delta": 0,
            "terminal_credit_delta": 0,
        }
    except Exception as exc:
        return _fail("PROOF_EXCEPTION:" + type(exc).__name__ + ":" + str(exc))
