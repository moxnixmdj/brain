"""R2 direct adequacy router V8.

Adds bounded pinned-OEWN inferred-synonym/context-word-sense Finance UNLESS
resolution before V7. Every nonmatching request delegates to V7 unchanged.
"""
from __future__ import annotations
from typing import Any, Mapping

from canonical.runtime import r2_direct_end_to_end_adequacy_v7 as v7
from canonical.runtime import r2_finance_oewn_synonym_unless_direct_adequacy_v1 as finance_oewn

SCHEMA = "PROJECT_BRAIN_R2_DIRECT_END_TO_END_ADEQUACY_ROUTES_V8"
FINANCE_OEWN_SYNONYM_ROUTE_ID = finance_oewn.ROUTE_ID
ROUTES = dict(v7.ROUTES)
ROUTES[FINANCE_OEWN_SYNONYM_ROUTE_ID] = {
    "capability_id": finance_oewn.CAPABILITY_ID,
    "scope": (
        "PINNED_COMPLETE_OEWN_QUERY_CONTEXT_SELECTED_OR_ALL_SENSES_EQUIVALENT_"
        "SAME_SYNSET_TYPED_FINANCE_UNLESS"
    ),
    "preflight": "r2_finance_oewn_synonym_unless_direct_adequacy_v1.preflight",
    "executor": "r2_finance_oewn_synonym_unless_direct_adequacy_v1.run",
    "acceptance": (
        "INDEPENDENT_OEWN_QUERY_COMPLETENESS_SENSE_SELECTION_SYNONYM_MEMBERSHIP_"
        "TYPED_CONDITION_AND_BRANCH_RECOMPUTATION"
    ),
}


def preflight(request: Mapping[str, Any], *, repo_root=None) -> dict[str, Any]:
    candidate = finance_oewn.preflight(request, repo_root=repo_root)
    if candidate.get("matched") is True:
        return candidate
    return v7.preflight(request, repo_root=repo_root)


def run(request: Mapping[str, Any], *, repo_root=None) -> dict[str, Any]:
    candidate = finance_oewn.preflight(request, repo_root=repo_root)
    if candidate.get("matched") is True:
        return finance_oewn.run(request, repo_root=repo_root)
    return v7.run(request, repo_root=repo_root)
