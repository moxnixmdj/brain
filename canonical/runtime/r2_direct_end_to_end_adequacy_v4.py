"""R2 direct adequacy router V4.

Adds bounded task-role cross-document Finance UNLESS before V3. Every
nonmatching request delegates to V3 unchanged.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime import r2_direct_end_to_end_adequacy_v3 as v3
from canonical.runtime import r2_finance_task_role_raw_fact_unless_direct_adequacy_v1 as finance_crossdoc

SCHEMA = "PROJECT_BRAIN_R2_DIRECT_END_TO_END_ADEQUACY_ROUTES_V4"
FINANCE_TASK_ROLE_RAW_FACT_ROUTE_ID = finance_crossdoc.ROUTE_ID
ROUTES = dict(v3.ROUTES)
ROUTES[FINANCE_TASK_ROLE_RAW_FACT_ROUTE_ID] = {
    "capability_id": finance_crossdoc.CAPABILITY_ID,
    "scope": (
        "EXPLICIT_TASK_ROLE_BOUND_DECLARED_POLICY_SOURCE_PLUS_RAW_TYPED_FACT_SOURCE_"
        "WITH_EXPLICIT_TERM_TO_FIELD_UNLESS"
    ),
    "preflight": "r2_finance_task_role_raw_fact_unless_direct_adequacy_v1.preflight",
    "executor": "r2_finance_task_role_raw_fact_unless_direct_adequacy_v1.run",
    "acceptance": (
        "PRODUCER_INDEPENDENT_TASK_SOURCE_SET_ROLE_POLICY_FACT_TYPED_CONDITION_"
        "BRANCH_AND_HASH_RECOMPUTATION"
    ),
}


def preflight(
    request: Mapping[str, Any],
    *,
    repo_root=None,
) -> dict[str, Any]:
    candidate = finance_crossdoc.preflight(request, repo_root=repo_root)
    if candidate.get("matched") is True:
        return candidate
    return v3.preflight(request, repo_root=repo_root)


def run(
    request: Mapping[str, Any],
    *,
    repo_root=None,
) -> dict[str, Any]:
    candidate = finance_crossdoc.preflight(request, repo_root=repo_root)
    if candidate.get("matched") is True:
        return finance_crossdoc.run(request, repo_root=repo_root)
    return v3.run(request, repo_root=repo_root)
