"""R2 direct adequacy router V3.

Adds exact explicit-definition Finance UNLESS resolution before V2. Every
nonmatching request delegates to V2 unchanged.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime import r2_direct_end_to_end_adequacy_v2 as v2
from canonical.runtime import r2_finance_explicit_definition_unless_direct_adequacy_v1 as finance_defined

SCHEMA = "PROJECT_BRAIN_R2_DIRECT_END_TO_END_ADEQUACY_ROUTES_V3"
FINANCE_EXPLICIT_DEFINITION_ROUTE_ID = finance_defined.ROUTE_ID
ROUTES = dict(v2.ROUTES)
ROUTES[FINANCE_EXPLICIT_DEFINITION_ROUTE_ID] = {
    "capability_id": finance_defined.CAPABILITY_ID,
    "scope": (
        "EXACT_TWO_SENTENCE_EXPLICIT_MEANS_DEFINITION_TO_LITERAL_TYPED_UNLESS_REFERENCE"
    ),
    "preflight": "r2_finance_explicit_definition_unless_direct_adequacy_v1.preflight",
    "executor": "r2_finance_explicit_definition_unless_direct_adequacy_v1.run",
    "acceptance": (
        "PRODUCER_INDEPENDENT_EXPLICIT_DEFINITION_REFERENCE_TYPED_CONDITION_"
        "SCOPE_ATOM_BRANCH_AND_HASH_RECOMPUTATION"
    ),
}


def preflight(
    request: Mapping[str, Any],
    *,
    repo_root=None,
) -> dict[str, Any]:
    candidate = finance_defined.preflight(request, repo_root=repo_root)
    if candidate.get("matched") is True:
        return candidate
    return v2.preflight(request, repo_root=repo_root)


def run(
    request: Mapping[str, Any],
    *,
    repo_root=None,
) -> dict[str, Any]:
    candidate = finance_defined.preflight(request, repo_root=repo_root)
    if candidate.get("matched") is True:
        return finance_defined.run(request, repo_root=repo_root)
    return v2.run(request, repo_root=repo_root)
