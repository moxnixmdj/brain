"""Semantic refinement proof for the bounded brain-owned semantic-edge controller.

This checker closes only the controller-level abstract-to-concrete gap for
brain_owned_semantic_relation_edge_authority_v1. It does not re-prove the
semantic resolver dependency. Instead it makes that dependency an explicit
abstract input boundary and proves the controller's finite transition partition
against both resolver outcomes where reachable.
"""
from __future__ import annotations

import ast
from copy import deepcopy
from hashlib import sha256
import importlib
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.executable_refinement_verifier_v1 import (
    git_blob_sha,
    verify_certificate,
)

SCHEMA = "PROJECT_BRAIN_BOUNDED_CONTROLLER_SEMANTIC_REFINEMENT_RECEIPT_V1"
ROOT = Path(__file__).resolve().parents[2]
ABSTRACT_PATH = Path(
    "canonical/governance/BRAIN_OWNED_SEMANTIC_EDGE_ABSTRACT_SPEC_20261009_V1.json"
)
CERTIFICATE_PATH = Path(
    "canonical/governance/BRAIN_OWNED_SEMANTIC_EDGE_EXECUTABLE_REFINEMENT_20261009_V1.json"
)
CONCRETE_PATH = Path(
    "canonical/runtime/brain_owned_semantic_relation_edge_authority_v1.py"
)
MODULE_NAME = "canonical.runtime.brain_owned_semantic_relation_edge_authority_v1"


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON_OBJECT_REQUIRED:" + str(path))
    return value


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "pass": False,
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "refinement_verified": False,
        "semantic_truth_authority": False,
        "execution_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def _base_evidence(module: Any, *, relation: str = "ENTAILS") -> dict[str, Any]:
    return {
        "schema": module.SCHEMA,
        "proof_class": module.PROOF_CLASS,
        "scope_id": "scope",
        "source_id": "left",
        "target_id": "right",
        "source_surface": "reserve buffer",
        "target_surface": "liquidity cushion",
        "relation": relation,
        "explicit_definition_sources": [
            {
                "source_id": "doc",
                "scope_id": "scope",
                "source_text": "Reserve buffer means liquidity cushion.",
            }
        ],
    }


def _cases(module: Any) -> list[dict[str, Any]]:
    base = _base_evidence(module)
    return [
        {"case_id": "EVIDENCE_NOT_OBJECT", "raw": "not-object", "resolver": None},
        {
            "case_id": "EVIDENCE_FIELD_SET_INVALID",
            "raw": {**deepcopy(base), "extra": True},
            "resolver": None,
        },
        {
            "case_id": "EVIDENCE_SCHEMA_INVALID",
            "raw": {**deepcopy(base), "schema": "WRONG"},
            "resolver": None,
        },
        {
            "case_id": "PROOF_CLASS_UNSUPPORTED",
            "raw": {**deepcopy(base), "proof_class": "MODEL_JUDGMENT"},
            "resolver": None,
        },
        {
            "case_id": "SCOPE_ID_REQUIRED",
            "raw": {**deepcopy(base), "scope_id": ""},
            "resolver": None,
        },
        {
            "case_id": "DISTINCT_SOURCE_TARGET_IDS_REQUIRED",
            "raw": {**deepcopy(base), "target_id": "left"},
            "resolver": None,
        },
        {
            "case_id": "SOURCE_TARGET_SURFACES_REQUIRED",
            "raw": {**deepcopy(base), "source_surface": ""},
            "resolver": None,
        },
        {
            "case_id": "RELATION_UNSUPPORTED",
            "raw": {**deepcopy(base), "relation": "SIMILAR"},
            "resolver": None,
        },
        {
            "case_id": "EXPLICIT_DEFINITION_SOURCES_REQUIRED",
            "raw": {**deepcopy(base), "explicit_definition_sources": []},
            "resolver": None,
        },
        {
            "case_id": "DEFINITION_SOURCE_NOT_OBJECT",
            "raw": {**deepcopy(base), "explicit_definition_sources": ["bad"]},
            "resolver": None,
        },
        {
            "case_id": "DEFINITION_SOURCE_FIELD_SET_INVALID",
            "raw": {
                **deepcopy(base),
                "explicit_definition_sources": [
                    {
                        "source_id": "doc",
                        "scope_id": "scope",
                        "source_text": "A means B.",
                        "extra": 1,
                    }
                ],
            },
            "resolver": None,
        },
        {
            "case_id": "DEFINITION_SOURCE_BINDING_INVALID",
            "raw": {
                **deepcopy(base),
                "explicit_definition_sources": [
                    {
                        "source_id": "doc",
                        "scope_id": "wrong",
                        "source_text": "A means B.",
                    }
                ],
            },
            "resolver": None,
        },
        {
            "case_id": "SEMANTIC_IDENTITY_NOT_PROVED",
            "raw": deepcopy(base),
            "resolver": False,
        },
        {
            "case_id": "NOT_ENTAILS_NOT_DERIVABLE_FROM_SEMANTIC_IDENTITY_PROOF",
            "raw": _base_evidence(module, relation="NOT_ENTAILS"),
            "resolver": True,
        },
        {
            "case_id": "ENTAILS_SUCCESS",
            "raw": deepcopy(base),
            "resolver": True,
        },
    ]


def _static_source_proof(source: str, expected_fail_reasons: set[str]) -> dict[str, Any]:
    tree = ast.parse(source)
    fail_reasons: set[str] = set()
    dynamic_fail_calls = 0
    resolve_calls = 0
    exact_resolve_import = False
    exact_receipt_schema_import = False

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            names = {alias.name for alias in node.names}
            if (
                node.module == "canonical.runtime.semantic_relation_control_v1"
                and "resolve" in names
            ):
                exact_resolve_import = True
            if (
                node.module == "canonical.runtime.semantic_relation_entailment_dag_v1"
                and "RECEIPT_SCHEMA" in names
            ):
                exact_receipt_schema_import = True

        if isinstance(node, ast.Call):
            func_name = node.func.id if isinstance(node.func, ast.Name) else None
            if func_name == "resolve":
                resolve_calls += 1
            if func_name == "_fail":
                if node.args and isinstance(node.args[0], ast.Constant) and isinstance(
                    node.args[0].value, str
                ):
                    fail_reasons.add(node.args[0].value)
                else:
                    dynamic_fail_calls += 1

    return {
        "pass": (
            fail_reasons == expected_fail_reasons
            and dynamic_fail_calls == 0
            and resolve_calls == 1
            and exact_resolve_import
            and exact_receipt_schema_import
        ),
        "fail_reasons": sorted(fail_reasons),
        "expected_fail_reasons": sorted(expected_fail_reasons),
        "dynamic_fail_calls": dynamic_fail_calls,
        "resolve_call_count": resolve_calls,
        "exact_resolve_import": exact_resolve_import,
        "exact_receipt_schema_import": exact_receipt_schema_import,
    }


def _run_case(
    module: Any,
    raw: Any,
    *,
    resolver_result: bool | None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    calls: list[dict[str, Any]] = []
    original = module.resolve

    def stub(payload: Mapping[str, Any]) -> dict[str, Any]:
        calls.append(deepcopy(dict(payload)))
        if resolver_result is True:
            return {"pass": True, "status": "PROVED"}
        return {"pass": False, "status": "UNRESOLVED", "reason": "STUB_NOT_PROVED"}

    if resolver_result is not None:
        module.resolve = stub
    try:
        out = module.verify(raw)
    finally:
        module.resolve = original
    return out, calls


def _verify_success_hashes(out: Mapping[str, Any], raw: Mapping[str, Any]) -> bool:
    evidence_sha = sha256(_canon(dict(raw))).hexdigest()
    if out.get("evidence_sha256") != evidence_sha:
        return False
    body = {
        "pass": True,
        "schema": out.get("schema"),
        "scope_id": out.get("scope_id"),
        "source_id": out.get("source_id"),
        "target_id": out.get("target_id"),
        "relation": "ENTAILS",
        "source_semantics_authenticated": True,
        "target_semantics_authenticated": True,
        "relation_semantics_authenticated": True,
        "verification_authority_mutated": False,
        "evidence_sha256": evidence_sha,
    }
    return out.get("receipt_sha256") == sha256(_canon(body)).hexdigest()


def prove(repo_root: str | Path = ROOT) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    abstract_path = root / ABSTRACT_PATH
    certificate_path = root / CERTIFICATE_PATH
    concrete_path = root / CONCRETE_PATH

    try:
        abstract = _load_json(abstract_path)
        certificate = _load_json(certificate_path)
    except Exception as exc:
        return _fail("BOUND_INPUT_LOAD_FAILED:" + type(exc).__name__ + ":" + str(exc))

    structural = verify_certificate(certificate, repo_root=root)
    if structural.get("pass") is not True:
        return _fail(
            "STRUCTURAL_REFINEMENT_BINDING_FAILED",
            structural_receipt=structural,
        )

    module = importlib.import_module(MODULE_NAME)
    module_file = Path(str(module.__file__)).resolve()
    if module_file != concrete_path.resolve():
        return _fail("CONCRETE_MODULE_IMPORT_PATH_MISMATCH")

    partition = abstract.get("transition_partition")
    if not isinstance(partition, list) or not partition:
        return _fail("ABSTRACT_TRANSITION_PARTITION_INVALID")
    by_case = {
        str(row.get("case_id") or ""): row
        for row in partition
        if isinstance(row, Mapping)
    }
    if len(by_case) != len(partition) or "" in by_case:
        return _fail("ABSTRACT_TRANSITION_CASE_IDS_INVALID")

    cert_cases = {
        str(row.get("case_id") or "")
        for row in certificate.get("transition_refinement", {}).get("classes", [])
        if isinstance(row, Mapping)
    }
    if cert_cases != set(by_case):
        return _fail("CERTIFICATE_ABSTRACT_CASE_SET_MISMATCH")

    expected_fail_reasons = {
        str(row.get("reason"))
        for row in partition
        if row.get("kind") == "FAIL_CLOSED"
    }
    source_proof = _static_source_proof(
        concrete_path.read_text(encoding="utf-8"),
        expected_fail_reasons,
    )
    if source_proof.get("pass") is not True:
        return _fail("STATIC_OUTCOME_SPACE_PROOF_FAILED", static_proof=source_proof)

    cases = _cases(module)
    if {row["case_id"] for row in cases} != set(by_case):
        return _fail("DYNAMIC_CASE_SET_MISMATCH")

    case_receipts: list[dict[str, Any]] = []
    success_projection = abstract.get("success_projection")
    if not isinstance(success_projection, Mapping):
        return _fail("ABSTRACT_SUCCESS_PROJECTION_INVALID")

    for case in cases:
        case_id = case["case_id"]
        declared = by_case[case_id]
        out, calls = _run_case(
            module,
            case["raw"],
            resolver_result=case["resolver"],
        )
        expected_calls = 1 if case["resolver"] is not None else 0
        if len(calls) != expected_calls:
            return _fail(
                "DEPENDENCY_CALL_COUNT_MISMATCH",
                case_id=case_id,
                expected=expected_calls,
                actual=len(calls),
            )

        if declared.get("kind") == "FAIL_CLOSED":
            if out.get("pass") is not False or out.get("reason") != declared.get("reason"):
                return _fail(
                    "FAIL_CLOSED_CASE_MISMATCH",
                    case_id=case_id,
                    output=out,
                )
        elif declared.get("kind") == "PASS":
            if out.get("pass") is not True:
                return _fail("PASS_CASE_DID_NOT_PASS", case_id=case_id, output=out)
            for key, value in success_projection.items():
                if out.get(key) != value:
                    return _fail(
                        "SUCCESS_PROJECTION_MISMATCH",
                        case_id=case_id,
                        field=key,
                        expected=value,
                        actual=out.get(key),
                    )
            if not isinstance(case["raw"], Mapping) or not _verify_success_hashes(
                out, case["raw"]
            ):
                return _fail("SUCCESS_HASH_BINDING_MISMATCH", case_id=case_id)
        else:
            return _fail("ABSTRACT_TRANSITION_KIND_UNSUPPORTED", case_id=case_id)

        if calls:
            request = calls[0]
            if (
                request.get("required_relation") != "SEMANTIC_IDENTITY"
                or request.get("scope_id") != "scope"
                or request.get("left_id") != "left"
                or request.get("right_id") != "right"
            ):
                return _fail(
                    "DELEGATED_RESOLVER_REQUEST_MISMATCH",
                    case_id=case_id,
                    resolver_request=request,
                )

        case_receipts.append(
            {
                "case_id": case_id,
                "kind": declared.get("kind"),
                "resolver_stub": case["resolver"],
                "dependency_call_count": len(calls),
                "pass": True,
            }
        )

    deps = structural.get("proof_dependencies") or []
    dep_paths = {row.get("path") for row in deps if isinstance(row, Mapping)}
    required_dep_paths = {
        "canonical/runtime/semantic_relation_control_v1.py",
        "canonical/runtime/semantic_relation_entailment_dag_v1.py",
    }
    if not required_dep_paths.issubset(dep_paths):
        return _fail("DELEGATED_DEPENDENCY_BINDING_INCOMPLETE")

    receipt_body = {
        "pass": True,
        "schema": SCHEMA,
        "status": "PASS__BOUNDED_CONTROLLER_SEMANTIC_REFINEMENT_VERIFIED",
        "subject_id": str(certificate.get("subject_id") or ""),
        "assurance_level": "FINITE_ABSTRACTION_CONTROLLER_REFINEMENT",
        "refinement_verified": True,
        "certificate_git_blob_sha": git_blob_sha(certificate_path),
        "abstract_spec_git_blob_sha": git_blob_sha(abstract_path),
        "concrete_route_git_blob_sha": git_blob_sha(concrete_path),
        "declared_transition_case_count": len(by_case),
        "dynamic_transition_case_count": len(case_receipts),
        "static_fail_reason_space_exact": True,
        "static_source_proof": source_proof,
        "dynamic_case_receipts": case_receipts,
        "proof_dependencies": deps,
        "delegated_dependency_boundary_explicit": True,
        "delegated_dependency_semantics_reproved": False,
        "semantic_truth_authority": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    return {
        **receipt_body,
        "receipt_sha256": sha256(_canon(receipt_body)).hexdigest(),
    }


if __name__ == "__main__":
    print(json.dumps(prove(ROOT), indent=2, sort_keys=True))
