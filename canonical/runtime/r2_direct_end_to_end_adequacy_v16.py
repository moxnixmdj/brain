"""R2 direct adequacy router V16.

Adds bounded multi-dimensional finance semantic hypothesis-product control before
V15. It composes only explicitly complete Cartesian semantic dimensions with
complete factorized terminal signatures. All other requests delegate unchanged.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime import r2_direct_end_to_end_adequacy_v15 as v15
from canonical.runtime import (
    r2_finance_semantic_hypothesis_product_direct_adequacy_v1 as semantic_product,
)

SCHEMA = "PROJECT_BRAIN_R2_DIRECT_END_TO_END_ADEQUACY_ROUTES_V16"
FINANCE_SEMANTIC_HYPOTHESIS_PRODUCT_ROUTE_ID = semantic_product.ROUTE_ID
ROUTES = dict(v15.ROUTES)
ROUTES[FINANCE_SEMANTIC_HYPOTHESIS_PRODUCT_ROUTE_ID] = {
    "capability_id": semantic_product.CAPABILITY_ID,
    "scope": (
        "DECLARED_COMPLETE_MULTI_DIMENSION_FINANCE_SEMANTIC_PRODUCT__"
        "TERMINAL_EQUIVALENCE_OR_MINIMUM_DISCRIMINATOR_CONTROL"
    ),
    "preflight": (
        "r2_finance_semantic_hypothesis_product_direct_adequacy_v1.preflight"
    ),
    "executor": "r2_finance_semantic_hypothesis_product_direct_adequacy_v1.run",
    "acceptance": (
        "PRODUCER_INDEPENDENT_CARTESIAN_WORLD_CONSTRUCTION_AND_"
        "SEMANTIC_FRONTIER_RECOMPUTATION"
    ),
}


def preflight(request: Mapping[str, Any], *, repo_root=None) -> dict[str, Any]:
    candidate = semantic_product.preflight(request, repo_root=repo_root)
    if candidate.get("matched") is True:
        return candidate
    return v15.preflight(request, repo_root=repo_root)


def run(request: Mapping[str, Any], *, repo_root=None) -> dict[str, Any]:
    candidate = semantic_product.preflight(request, repo_root=repo_root)
    if candidate.get("matched") is True:
        return semantic_product.run(request, repo_root=repo_root)
    return v15.run(request, repo_root=repo_root)
