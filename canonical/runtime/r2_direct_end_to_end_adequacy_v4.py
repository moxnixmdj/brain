"""R2 direct adequacy router V4.

Adds the source-defined raw-fact Finance UNLESS family before V3. Every
nonmatching request delegates to V3 byte-for-byte behavior.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime import r2_direct_end_to_end_adequacy_v3 as v3
from canonical.runtime import (
    r2_finance_defined_term_raw_fact_unless_direct_adequacy_v1
    as finance_defined_raw,
)

SCHEMA = "PROJECT_BRAIN_R2_DIRECT_END_TO_END_ADEQUACY_ROUTES_V4"
FINANCE_DEFINED_TERM_RAW_FACT_ROUTE_ID = finance_defined_raw.ROUTE_ID
ROUTES = dict(v3.ROUTES)
ROUTES[FINANCE_DEFINED_TERM_RAW_FACT_ROUTE_ID] = {
    "capability_id": finance_defined_raw.CAPABILITY_ID,
    "scope": (
        "TASK_BOUND_PROOF_CARRYING_FINANCE_SOURCE__EXPLICIT_TERM_TO_TYPED_FIELD__"
        "STRICT_RAW_FACT_JSON__CONTROLLED_SINGLE_UNLESS"
    ),
    "preflight": (
        "r2_finance_defined_term_raw_fact_unless_direct_adequacy_v1.preflight"
    ),
    "executor": "r2_finance_defined_term_raw_fact_unless_direct_adequacy_v1.run",
    "acceptance": (
        "FINANCE_SOURCE_COVERAGE_GATE_PLUS_PRODUCER_INDEPENDENT_DEFINITION_"
        "RAW_CONTEXT_CONDITION_SCOPE_ATOM_AND_BRANCH_RECOMPUTATION"
    ),
}


def preflight(
    request: Mapping[str, Any],
    *,
    repo_root=None,
) -> dict[str, Any]:
    candidate = finance_defined_raw.preflight(request, repo_root=repo_root)
    if candidate.get("matched") is True:
        return candidate
    return v3.preflight(request, repo_root=repo_root)


def run(
    request: Mapping[str, Any],
    *,
    repo_root=None,
) -> dict[str, Any]:
    candidate = finance_defined_raw.preflight(request, repo_root=repo_root)
    if candidate.get("matched") is True:
        return finance_defined_raw.run(request, repo_root=repo_root)
    return v3.run(request, repo_root=repo_root)
