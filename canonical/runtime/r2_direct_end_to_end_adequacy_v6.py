"""R2 direct adequacy router V6.

Adds exact content-addressed cross-document glossary Finance UNLESS resolution
before V5. Every nonmatching request delegates to V5 unchanged.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime import r2_direct_end_to_end_adequacy_v5 as v5
from canonical.runtime import (
    r2_finance_cross_document_glossary_unless_direct_adequacy_v1 as finance_glossary,
)

SCHEMA="PROJECT_BRAIN_R2_DIRECT_END_TO_END_ADEQUACY_ROUTES_V6"
FINANCE_CROSS_DOCUMENT_GLOSSARY_ROUTE_ID=finance_glossary.ROUTE_ID
ROUTES=dict(v5.ROUTES)
ROUTES[FINANCE_CROSS_DOCUMENT_GLOSSARY_ROUTE_ID]={
    "capability_id":finance_glossary.CAPABILITY_ID,
    "scope":"EXACT_CONTENT_ADDRESSED_CROSS_DOCUMENT_GLOSSARY_TERM_TO_LITERAL_TYPED_UNLESS_CONDITION",
    "preflight":"r2_finance_cross_document_glossary_unless_direct_adequacy_v1.preflight",
    "executor":"r2_finance_cross_document_glossary_unless_direct_adequacy_v1.run",
    "acceptance":"PRODUCER_INDEPENDENT_CROSS_DOCUMENT_GLOSSARY_TYPED_CONDITION_BRANCH_AND_HASH_RECOMPUTATION",
}

def preflight(request:Mapping[str,Any],*,repo_root=None)->dict[str,Any]:
    candidate=finance_glossary.preflight(request,repo_root=repo_root)
    if candidate.get("matched") is True:
        return candidate
    return v5.preflight(request,repo_root=repo_root)

def run(request:Mapping[str,Any],*,repo_root=None)->dict[str,Any]:
    candidate=finance_glossary.preflight(request,repo_root=repo_root)
    if candidate.get("matched") is True:
        return finance_glossary.run(request,repo_root=repo_root)
    return v5.run(request,repo_root=repo_root)
