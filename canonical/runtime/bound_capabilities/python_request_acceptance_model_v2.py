from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Mapping, Sequence

from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract
from canonical.runtime.bound_capabilities.python_request_acceptance_model_v1 import (
    RequestAcceptanceError,
    _classify,
    _run_verifier,
    _safe_rel,
)

SCHEMA = "PROJECT_BRAIN_PYTHON_REQUEST_ACCEPTANCE_MODEL_V2"
PLAN_SCHEMA = "PROJECT_BRAIN_PYTHON_REQUEST_ACCEPTANCE_PLAN_V2"
RESULT_SCHEMA = "PROJECT_BRAIN_PYTHON_REQUEST_ACCEPTANCE_RESULT_V2"


def _canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _sha(value: Any) -> str:
    return hashlib.sha256(_canon(value).encode("utf-8")).hexdigest()


def _logical_segments(text: str) -> list[tuple[int, int, str]]:
    out: list[tuple[int, int, str]] = []
    start = 0
    ascii_quote = False
    curly_quote = False
    i = 0

    def emit(a: int, b: int) -> None:
        while a < b and text[a].isspace():
            a += 1
        while b > a and text[b - 1].isspace():
            b -= 1
        if a < b and text[a:b].strip():
            out.append((a, b, text[a:b]))

    while i < len(text):
        ch = text[i]
        if ch == '"' and not curly_quote:
            ascii_quote = not ascii_quote
        elif ch == "“" and not ascii_quote:
            curly_quote = True
        elif ch == "”" and curly_quote and not ascii_quote:
            curly_quote = False

        outside = not ascii_quote and not curly_quote
        if outside and ch == "\n":
            emit(start, i + 1)
            start = i + 1
            i += 1
            continue
        if outside and ch in ".!?":
            j = i + 1
            while j < len(text) and text[j] in ".!?":
                j += 1
            emit(start, j)
            start = j
            i = j
            continue
        i += 1

    emit(start, len(text))
    if ascii_quote or curly_quote:
        raise RequestAcceptanceError("UNBALANCED_QUOTED_SOURCE")
    return out


def _predicate_row(
    *,
    logical_text: str,
    logical_span: tuple[int, int],
    obligations: list[Mapping[str, Any]],
) -> dict[str, Any]:
    verifier = _classify(logical_text)
    semantic = "BOUND_EXECUTABLE" if verifier is not None else "UNBOUND"
    obligation_ids = [str(x["obligation_id"]) for x in obligations]
    segment_shas = [str(x["segment_sha256"]) for x in obligations]
    return {
        "predicate_id": "ACCEPT:" + _sha({
            "obligation_ids": obligation_ids,
            "segment_sha256s": segment_shas,
            "logical_span": list(logical_span),
            "verifier": verifier,
        }),
        "obligation_ids": obligation_ids,
        "covered_raw_obligation_count": len(obligation_ids),
        "covered_segment_sha256s": segment_shas,
        "logical_span": list(logical_span),
        "raw_text": logical_text,
        "predicate_class": (
            "NEGATIVE_REQUIREMENT"
            if verifier and verifier.get("kind") in {"FILE_NOT_CONTAINS", "FILE_ABSENT", "PATH_UNCHANGED"}
            else "SCOPE"
            if verifier and verifier.get("kind") == "CHANGED_PATHS_SUBSET"
            else "BEHAVIOR_OR_CONSTRAINT"
        ),
        "semantic_binding": semantic,
        "verifier": verifier,
        "unbound_reason": None if verifier is not None else "NO_SOUND_BOUNDED_EXECUTABLE_SEMANTIC_BINDING",
        "existing_test_evidence_may_self_bind_this_predicate": False,
    }


def compile_plan(
    request_text: str,
    *,
    source_id: str = "software_request",
    routing_target_effects: Sequence[str] = ("software.patch.correct",),
) -> dict[str, Any]:
    try:
        contract = compile_contract(
            request_text,
            source_id=source_id,
            routing_target_effects=list(routing_target_effects),
        )
        if contract.get("pass") is not True:
            raise RequestAcceptanceError("RAW_CONTRACT_FAILED")

        raw_rows = list(contract["acceptance_contract"]["obligations"])
        by_id = {str(x["obligation_id"]): x for x in raw_rows}
        predicates = []
        covered_ids: list[str] = []

        for start, end, logical_text in _logical_segments(request_text):
            rows = [
                row for row in raw_rows
                if start <= int(row["span"][0]) and int(row["span"][1]) <= end
            ]
            if not rows:
                raise RequestAcceptanceError("LOGICAL_SEGMENT_HAS_NO_RAW_OBLIGATION")
            predicates.append(_predicate_row(
                logical_text=logical_text,
                logical_span=(start, end),
                obligations=rows,
            ))
            covered_ids.extend(str(row["obligation_id"]) for row in rows)

        required = [str(x) for x in contract["acceptance_contract"]["required_obligation_ids"]]
        if len(covered_ids) != len(set(covered_ids)):
            raise RequestAcceptanceError("RAW_OBLIGATION_COVERAGE_DUPLICATE")
        if set(covered_ids) != set(required):
            raise RequestAcceptanceError("RAW_OBLIGATION_COVERAGE_MISMATCH")
        if set(by_id) != set(required):
            raise RequestAcceptanceError("RAW_CONTRACT_REQUIRED_SET_MISMATCH")

        bound = [row for row in predicates if row["semantic_binding"] == "BOUND_EXECUTABLE"]
        unbound = [row for row in predicates if row["semantic_binding"] == "UNBOUND"]
        bound_raw = {
            oid
            for row in bound
            for oid in row["obligation_ids"]
        }
        payload = {
            "task_contract_sha256": contract["task_contract_sha256"],
            "task_sha256": contract["task_sha256"],
            "predicates": [
                {
                    "predicate_id": row["predicate_id"],
                    "obligation_ids": row["obligation_ids"],
                    "covered_segment_sha256s": row["covered_segment_sha256s"],
                    "semantic_binding": row["semantic_binding"],
                    "verifier": row["verifier"],
                }
                for row in predicates
            ],
        }
        return {
            "schema": PLAN_SCHEMA,
            "status": "COMPILED__ALL_RAW_OBLIGATIONS_EXECUTABLY_BOUND" if not unbound else "COMPILED__UNBOUND_ACCEPTANCE_PREDICATES_REMAIN",
            "pass": True,
            "task_contract": contract,
            "acceptance_predicates": predicates,
            "predicate_count": len(predicates),
            "bound_predicate_count": len(bound),
            "unbound_predicate_count": len(unbound),
            "raw_obligation_count": len(required),
            "bound_raw_obligation_count": len(bound_raw),
            "all_raw_obligations_semantically_bound": len(bound_raw) == len(required),
            "acceptance_plan_sha256": _sha(payload),
            "existing_test_evidence_is_request_semantics_authority": False,
            "repair_stop_authorized_at_compile_time": False,
            "model_dependency_count": 0,
            "external_capability_provider_count": 0,
            "incremental_spend_usd": 0,
            "hard_nonclaims": [
                "NO_ARBITRARY_NATURAL_LANGUAGE_SEMANTIC_COMPLETENESS",
                "NO_CLAIM_EXISTING_TEST_PASS_PROVES_UNBOUND_REQUEST_SEMANTICS",
                "NO_UNBOUND_PREDICATE_MAY_BE_SILENTLY_DROPPED",
                "NO_GENERAL_SOFTWARE_REPAIR_COMPLETENESS",
                "NO_FRONTIERCODE_SCORE_OR_ACCEPTANCE_CREDIT",
            ],
        }
    except Exception as exc:
        return {
            "schema": PLAN_SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "errors": [type(exc).__name__ + ":" + str(exc)],
            "repair_stop_authorized_at_compile_time": False,
            "model_dependency_count": 0,
            "external_capability_provider_count": 0,
            "incremental_spend_usd": 0,
        }


def evaluate_plan(
    plan: Mapping[str, Any],
    *,
    repo_root: str | os.PathLike[str],
    changed_paths: Sequence[str] = (),
    existing_test_evidence: Mapping[str, Any] | None = None,
    timeout_s: int = 20,
) -> dict[str, Any]:
    if not isinstance(plan, Mapping) or plan.get("schema") != PLAN_SCHEMA or plan.get("pass") is not True:
        raise RequestAcceptanceError("PLAN_INVALID")
    import pathlib
    root = pathlib.Path(repo_root).resolve()
    if not root.is_dir() or root.is_symlink():
        raise RequestAcceptanceError("REPOSITORY_INVALID")
    timeout = max(1, min(int(timeout_s), 60))
    changed = {_safe_rel(x) for x in changed_paths}

    rows = []
    bound_raw_ids: set[str] = set()
    passed_raw_ids: set[str] = set()
    for pred in plan.get("acceptance_predicates") or []:
        obligation_ids = [str(x) for x in pred.get("obligation_ids") or []]
        if pred.get("semantic_binding") != "BOUND_EXECUTABLE" or not isinstance(pred.get("verifier"), Mapping):
            rows.append({
                "predicate_id": pred.get("predicate_id"),
                "obligation_ids": obligation_ids,
                "status": "UNBOUND",
                "pass": False,
                "reason": pred.get("unbound_reason") or "UNBOUND",
            })
            continue
        bound_raw_ids.update(obligation_ids)
        ok, reason, details = _run_verifier(
            pred["verifier"],
            root=root,
            changed_paths=changed,
            timeout_s=timeout,
        )
        if ok:
            passed_raw_ids.update(obligation_ids)
        rows.append({
            "predicate_id": pred.get("predicate_id"),
            "obligation_ids": obligation_ids,
            "status": "VERIFIED_PASS" if ok else "VERIFIED_FAIL",
            "pass": ok,
            "reason": reason,
            "details": details,
        })

    required = {
        str(x)
        for x in plan["task_contract"]["acceptance_contract"]["required_obligation_ids"]
    }
    unbound = [r for r in rows if r["status"] == "UNBOUND"]
    failed = [r for r in rows if r["status"] == "VERIFIED_FAIL"]
    all_bound = bound_raw_ids == required
    all_pass = passed_raw_ids == required
    complete = bool(rows) and all_bound and all_pass and not unbound and not failed
    return {
        "schema": RESULT_SCHEMA,
        "status": "PASS__COMPLETE_BOUND_REQUEST_ACCEPTANCE" if complete else "OPEN__REQUEST_ACCEPTANCE_NOT_COMPLETE",
        "pass": complete,
        "acceptance_plan_sha256": plan.get("acceptance_plan_sha256"),
        "predicate_results": rows,
        "raw_obligation_count": len(required),
        "bound_raw_obligation_count": len(bound_raw_ids),
        "verified_pass_raw_obligation_count": len(passed_raw_ids),
        "bound_verified_pass_count": sum(r["status"] == "VERIFIED_PASS" for r in rows),
        "bound_verified_fail_count": len(failed),
        "unbound_predicate_count": len(unbound),
        "all_raw_obligations_semantically_bound": all_bound,
        "all_raw_obligations_verified_pass": all_pass,
        "existing_test_evidence": dict(existing_test_evidence or {}),
        "existing_test_evidence_is_request_semantics_authority": False,
        "repair_stop_authorized_by_this_capability": complete,
        "model_dependency_count": 0,
        "external_capability_provider_count": 0,
        "incremental_spend_usd": 0,
        "hard_nonclaims": [
            "NO_ARBITRARY_NATURAL_LANGUAGE_SEMANTIC_COMPLETENESS",
            "NO_TEST_PASS_TO_UNBOUND_REQUEST_SEMANTICS_INFERENCE",
            "NO_REPAIR_STOP_WHILE_ANY_RAW_OBLIGATION_IS_UNBOUND_OR_FAILING",
            "NO_GENERAL_MERGEABILITY_OR_FRONTIERCODE_SCORE_CLAIM",
        ],
    }


def run(args: Mapping[str, Any], root: str | os.PathLike[str]) -> dict[str, Any]:
    if not isinstance(args, Mapping):
        raise RequestAcceptanceError("ARGS_NOT_OBJECT")
    plan = compile_plan(
        str(args.get("request_text") or ""),
        source_id=str(args.get("source_id") or "software_request"),
        routing_target_effects=tuple(args.get("routing_target_effects") or ("software.patch.correct",)),
    )
    if plan.get("pass") is not True or args.get("compile_only") is True:
        return plan
    return evaluate_plan(
        plan,
        repo_root=root,
        changed_paths=tuple(args.get("changed_paths") or ()),
        existing_test_evidence=args.get("existing_test_evidence") if isinstance(args.get("existing_test_evidence"), Mapping) else None,
        timeout_s=int(args.get("timeout_s", 20)),
    )
