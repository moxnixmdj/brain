"""Universal Escape Resolver V1.

Fail-closed coordinator between the existing Universal Learning planning stack
and the current D_B admission mechanisms.

Key rule: learning/planning never grants D_B, U-empty, or terminal credit.
Every cell-level promotion must be authorized by an existing independently
authenticated D_B admission route. The learner is invoked only after available
admission proofs have been exhausted.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime import semantic_elision_db_admission_v1 as db
from canonical.runtime import source_positive_adequacy_db_admission_v1 as source_db
from canonical.runtime import universal_learning_meta_policy_router_v9 as ul

SCHEMA = "PROJECT_BRAIN_UNIVERSAL_ESCAPE_RESOLVER_V1"
ROUTES = (
    "D_SOURCE_POSITIVE_ADEQUACY",
    "B_ROBUST_COMMON_POLICY",
    "A_COMPLETE_OBJECTIVE",
    "C_DIRECT_END_TO_END_ACCEPTANCE",
)


def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "db_admission_authorized": False,
        "u_empty_authorized": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    if detail:
        out["detail"] = detail
    return out


def _evaluate_candidate(route: str, candidate: Mapping[str, Any]) -> dict[str, Any]:
    if candidate.get("route") != route:
        return _fail("CANDIDATE_ROUTE_MISMATCH")
    body = candidate.get("payload")
    if not isinstance(body, Mapping):
        return _fail("CANDIDATE_PAYLOAD_MAPPING_REQUIRED")
    if route == "D_SOURCE_POSITIVE_ADEQUACY":
        return source_db.evaluate(body)
    return db.evaluate(candidate)


def resolve(
    *,
    escape_cell_id: str,
    escape_membership_bound: bool,
    admission_candidates: Mapping[str, Mapping[str, Any]],
    v9_args: Mapping[str, Any],
    admission_order: Sequence[str] = ROUTES,
) -> dict[str, Any]:
    """Resolve one already-bound escape cell or return its next learning action.

    Existing proof routes are exhausted first. Only when none authorizes the
    exact escape cell is Universal Learning V9 invoked as a planning mechanism.
    V9 cannot authorize execution or promotion here.
    """
    cell = str(escape_cell_id or "").strip()
    if not cell:
        return _fail("ESCAPE_CELL_ID_REQUIRED")
    if escape_membership_bound is not True:
        return _fail("ESCAPE_MEMBERSHIP_NOT_BOUND")
    if not isinstance(admission_candidates, Mapping):
        return _fail("ADMISSION_CANDIDATES_MAPPING_REQUIRED")
    if not isinstance(v9_args, Mapping):
        return _fail("V9_ARGS_MAPPING_REQUIRED")

    order = tuple(admission_order)
    if (
        not order
        or len(set(order)) != len(order)
        or any(route not in ROUTES for route in order)
    ):
        return _fail("ADMISSION_ORDER_INVALID")

    attempts: list[dict[str, Any]] = []
    for route in order:
        candidate = admission_candidates.get(route)
        if candidate is None:
            continue
        if not isinstance(candidate, Mapping):
            attempts.append(
                {"route": route, "pass": False, "reason": "CANDIDATE_NOT_MAPPING"}
            )
            continue
        try:
            result = _evaluate_candidate(route, candidate)
        except Exception as exc:  # fail closed on malformed evidence
            attempts.append(
                {
                    "route": route,
                    "pass": False,
                    "reason": "ADMISSION_ROUTE_EXCEPTION",
                    "exception_type": type(exc).__name__,
                }
            )
            continue

        exact_cell = result.get("cell_id")
        authorized = (
            result.get("pass") is True
            and result.get("db_admission_authorized") is True
            and exact_cell == cell
        )
        attempts.append(
            {
                "route": route,
                "pass": bool(authorized),
                "result_status": result.get("status"),
                "result_cell_id": exact_cell,
            }
        )
        if authorized:
            return {
                "schema": SCHEMA,
                "pass": True,
                "status": "PASS__ESCAPE_CELL_ADMITTED_TO_D_B",
                "escape_cell_id": cell,
                "selected_admission_route": route,
                "admission_result": result,
                "admission_attempts": attempts,
                "universal_learning_invoked": False,
                "db_admission_authorized": True,
                "u_empty_authorized": False,
                "terminal_authority": False,
                "terminal_credit_delta": 0,
                "boundary": (
                    "CELL_ONLY__GLOBAL_CLOSURE_REQUIRES_SCOPE_COMPLETE_UNION_"
                    "OF_SOUND_D_B_ADMISSIONS"
                ),
            }

    try:
        plan = ul.route(**dict(v9_args))
    except Exception as exc:
        return _fail(
            "UNIVERSAL_LEARNING_PLANNER_FAILED",
            exception_type=type(exc).__name__,
            admission_attempts=attempts,
        )

    return {
        "schema": SCHEMA,
        "pass": False,
        "status": "UNRESOLVED__LEARNING_OR_NEW_ADMISSION_EVIDENCE_REQUIRED",
        "escape_cell_id": cell,
        "admission_attempts": attempts,
        "universal_learning_invoked": True,
        "learning_route": plan.get("route"),
        "learning_next_action": plan.get("next_action"),
        "learning_planner_result": plan,
        "db_admission_authorized": False,
        "u_empty_authorized": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "rule": (
            "PLANNING_MAY_SEARCH_GLOBALLY__ONLY_EXISTING_D_B_ADMISSION_"
            "AUTHORITY_CAN_PROMOTE_THE_CELL"
        ),
    }
