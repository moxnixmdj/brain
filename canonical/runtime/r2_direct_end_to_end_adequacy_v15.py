"""R2 direct adequacy router V15.

Adds bounded finance coreference ambiguity control before V14.  The route does
not resolve general coreference; it computes exact decision relevance over a
declared complete mention/candidate universe and delegates all other requests.
"""
from __future__ import annotations
from typing import Any, Mapping

from canonical.runtime import r2_direct_end_to_end_adequacy_v14 as v14
from canonical.runtime import r2_finance_coreference_ambiguity_direct_adequacy_v1 as coref_ambiguity

SCHEMA = "PROJECT_BRAIN_R2_DIRECT_END_TO_END_ADEQUACY_ROUTES_V15"
FINANCE_COREFERENCE_AMBIGUITY_ROUTE_ID = coref_ambiguity.ROUTE_ID
ROUTES = dict(v14.ROUTES)
ROUTES[FINANCE_COREFERENCE_AMBIGUITY_ROUTE_ID] = {
    "capability_id": coref_ambiguity.CAPABILITY_ID,
    "scope": (
        "DECLARED_COMPLETE_BOUNDED_MENTION_UNIVERSE__ONE_REFERENCE__"
        "TERMINAL_EQUIVALENCE_OR_MINIMUM_DISCRIMINATOR_CONTROL"
    ),
    "preflight": "r2_finance_coreference_ambiguity_direct_adequacy_v1.preflight",
    "executor": "r2_finance_coreference_ambiguity_direct_adequacy_v1.run",
    "acceptance": "PRODUCER_INDEPENDENT_CANDIDATE_GRAPH_AND_SEMANTIC_FRONTIER_RECOMPUTATION",
}


def preflight(request: Mapping[str, Any], *, repo_root=None) -> dict[str, Any]:
    candidate = coref_ambiguity.preflight(request, repo_root=repo_root)
    if candidate.get("matched") is True:
        return candidate
    return v14.preflight(request, repo_root=repo_root)


def run(request: Mapping[str, Any], *, repo_root=None) -> dict[str, Any]:
    candidate = coref_ambiguity.preflight(request, repo_root=repo_root)
    if candidate.get("matched") is True:
        return coref_ambiguity.run(request, repo_root=repo_root)
    return v14.run(request, repo_root=repo_root)
