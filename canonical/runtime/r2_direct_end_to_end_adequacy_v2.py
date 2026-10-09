"""R2 direct adequacy router V2.

Adds the bounded normalized Finance IF_THEN route before V1. Every nonmatching
request delegates to the verified V29 router unchanged.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime import r2_direct_end_to_end_adequacy_v1 as v1
from canonical.runtime import r2_finance_normalized_if_direct_adequacy_v1 as finance_if
from canonical.runtime import r2_finance_normalized_source_universe_direct_adequacy_v1 as finance_source_universe

SCHEMA = "PROJECT_BRAIN_R2_DIRECT_END_TO_END_ADEQUACY_ROUTES_V2"
FINANCE_NORMALIZED_IF_ROUTE_ID = finance_if.ROUTE_ID
FINANCE_NORMALIZED_SOURCE_UNIVERSE_ROUTE_ID = finance_source_universe.ROUTE_ID
ROUTES = dict(v1.ROUTES)
ROUTES[FINANCE_NORMALIZED_SOURCE_UNIVERSE_ROUTE_ID] = {
    "capability_id": finance_source_universe.CAPABILITY_ID,
    "scope": "COMPLETE_TYPED_FINANCE_PACKAGE_SOURCE_UNIVERSE_TO_INDEPENDENTLY_RECOMPUTED_DECISION",
    "preflight": "r2_finance_normalized_source_universe_direct_adequacy_v1.preflight",
    "executor": "r2_finance_normalized_source_universe_direct_adequacy_v1.run",
    "acceptance": "EXACT_PACKAGE_FIELD_COVERAGE_PLUS_COMPLETE_FINANCE_ROLE_PARTITION_PLUS_RECONCILIATION_CHECKS_PLUS_PRODUCER_INDEPENDENT_TYPED_DECISION_RECOMPUTATION",
}
ROUTES[FINANCE_NORMALIZED_IF_ROUTE_ID] = {
    "capability_id": finance_if.CAPABILITY_ID,
    "scope": (
        "EXACT_NORMALIZED_SUPERVISORY_FINANCE_SINGLE_IF_THEN_WITH_"
        "EXPLICIT_TYPED_ANTECEDENT_TRUTH"
    ),
    "preflight": "r2_finance_normalized_if_direct_adequacy_v1.preflight",
    "executor": "r2_finance_normalized_if_direct_adequacy_v1.run",
    "acceptance": "SEPARATE_STDLIB_IF_REPARSE_PLUS_FULL_BRANCH_AND_HASH_RECOMPUTATION",
}


def preflight(
    request: Mapping[str, Any],
    *,
    repo_root=None,
) -> dict[str, Any]:
    candidate = finance_if.preflight(request, repo_root=repo_root)
    if candidate.get("matched") is True:
        return candidate
    candidate = finance_source_universe.preflight(request, repo_root=repo_root)
    if candidate.get("matched") is True:
        return candidate
    return v1.preflight(request)


def run(
    request: Mapping[str, Any],
    *,
    repo_root=None,
) -> dict[str, Any]:
    candidate = finance_if.preflight(request, repo_root=repo_root)
    if candidate.get("matched") is True:
        return finance_if.run(request, repo_root=repo_root)
    candidate = finance_source_universe.preflight(request, repo_root=repo_root)
    if candidate.get("matched") is True:
        return finance_source_universe.run(request, repo_root=repo_root)
    return v1.run(request)
