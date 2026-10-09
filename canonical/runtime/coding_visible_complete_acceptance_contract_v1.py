"""Evaluate a source-authorized complete visible acceptance contract.

Mechanical evaluator only. Semantic premises such as source authorization,
soundness/completeness, independence, and preterminal admissibility are supplied
by separately authenticated condition truth. This runtime never self-certifies
those premises.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_CODING_VISIBLE_COMPLETE_ACCEPTANCE_CONTRACT_V1"
POLICY_ID = "BRAIN_VISIBLE_COMPLETE_ACCEPTANCE_CONTRACT_V1"


def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    out: dict[str, Any] = {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "policy_id": POLICY_ID,
        "candidate_accepted": False,
        "semantic_authority_created": False,
        "terminal_authority": False,
        "acceptance_credit_delta": 0,
        "terminal_credit_delta": 0,
    }
    if detail:
        out["detail"] = detail
    return out


def evaluate(
    candidate: Mapping[str, Any],
    checker_ids: Sequence[str],
    checkers: Mapping[str, Callable[[Mapping[str, Any]], bool]],
    *,
    max_checks: int,
) -> dict[str, Any]:
    if not isinstance(candidate, Mapping):
        return _fail("CANDIDATE_NOT_OBJECT")
    if isinstance(checker_ids, (str, bytes)) or not isinstance(checker_ids, Sequence):
        return _fail("CHECKER_IDS_NOT_SEQUENCE")
    ids = list(checker_ids)
    if not ids:
        return _fail("CHECKER_IDS_EMPTY")
    if not isinstance(checkers, Mapping):
        return _fail("CHECKERS_NOT_MAPPING")
    if isinstance(max_checks, bool) or not isinstance(max_checks, int) or max_checks < 0:
        return _fail("MAX_CHECKS_INVALID")

    seen: set[str] = set()
    for index, raw in enumerate(ids):
        if not isinstance(raw, str) or not raw.strip():
            return _fail("CHECKER_ID_INVALID", index=index)
        if raw in seen:
            return _fail("CHECKER_ID_DUPLICATE", checker_id=raw)
        seen.add(raw)
    if max_checks < len(ids):
        return _fail(
            "CHECK_BUDGET_INSUFFICIENT",
            checker_count=len(ids),
            max_checks=max_checks,
        )

    results: list[dict[str, Any]] = []
    failed: list[str] = []
    for checker_id in ids:
        checker = checkers.get(checker_id)
        if not callable(checker):
            return _fail("CHECKER_MISSING_OR_NOT_CALLABLE", checker_id=checker_id)
        try:
            verdict = checker(deepcopy(dict(candidate)))
        except Exception as exc:
            return _fail(
                "CHECKER_EXCEPTION",
                checker_id=checker_id,
                error_type=type(exc).__name__,
                completed_checks=len(results),
            )
        if type(verdict) is not bool:
            return _fail(
                "CHECKER_NONBOOLEAN_RESULT",
                checker_id=checker_id,
                completed_checks=len(results) + 1,
            )
        results.append({"checker_id": checker_id, "verdict": verdict})
        if not verdict:
            failed.append(checker_id)

    accepted = not failed
    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__VISIBLE_COMPLETE_ACCEPTANCE_CONTRACT_EVALUATED",
        "policy_id": POLICY_ID,
        "candidate_accepted": accepted,
        "checker_count": len(ids),
        "check_count": len(results),
        "checker_results": results,
        "counterexample_checker_ids": failed,
        "counterexample_present": bool(failed),
        "candidate_space_finiteness_required": False,
        "transform_taxonomy_required": False,
        "semantic_premises_self_certified": False,
        "semantic_authority_created": False,
        "terminal_authority": False,
        "acceptance_credit_delta": 0,
        "terminal_credit_delta": 0,
    }
