"""Brain-owned compositional semantic relation edge authority V1.

Authenticates SOURCE_TO_TARGET semantic entailment edges by composing:
1. Brain-owned source semantic proof registry,
2. Brain-owned exact concept-semantics authority, and
3. source_aligned_semantic_edge_authority_v1's monotone entailment kernel.

This is not a language model judgment. Every accepted edge is recomputed from
exact source-bound proof primitives and exact source-declared target semantics.

TARGET_TO_SOURCE is intentionally unsupported in V1 because it requires an
independent source-semantics completeness authority that is not supplied here.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from canonical.runtime.source_aligned_semantic_edge_authority_v1 import (
    EVIDENCE_SCHEMA,
    verify_edge_evidence,
)
from canonical.runtime.source_aligned_semantic_proof_registry_v1 import (
    verify_proof as verify_source_proof,
)
from canonical.runtime.brain_owned_concept_semantics_authority_v1 import (
    verify as verify_concept_semantics,
)

AUTHORITY_SCHEMA="PROJECT_BRAIN_COMPOSITIONAL_SEMANTIC_RELATION_EDGE_AUTHORITY_V1"


def _fail(reason:str,**extra:Any)->dict[str,Any]:
    return {
        "pass":False,
        "schema":AUTHORITY_SCHEMA,
        "status":"FAIL_CLOSED",
        "reason":reason,
        "semantic_truth_authority":False,
        "execution_authority":False,
        "acceptance_authority":False,
        "terminal_authority":False,
        **extra,
    }


def supports(raw:Any)->bool:
    return (
        isinstance(raw,Mapping)
        and raw.get("schema")==EVIDENCE_SCHEMA
        and str(raw.get("direction") or "").strip().upper()=="SOURCE_TO_TARGET"
    )


def verify(raw:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(raw,Mapping):
        return _fail("EVIDENCE_NOT_OBJECT")
    if raw.get("schema")!=EVIDENCE_SCHEMA:
        return _fail("EVIDENCE_SCHEMA_UNSUPPORTED")

    direction=str(raw.get("direction") or "").strip().upper()
    if direction!="SOURCE_TO_TARGET":
        return _fail(
            "DIRECTION_UNSUPPORTED_WITHOUT_SOURCE_COMPLETENESS_AUTHORITY",
            requested_direction=direction or None,
        )

    receipt=verify_edge_evidence(
        deepcopy(dict(raw)),
        concept_semantics_verifier=verify_concept_semantics,
        source_completeness_verifier=None,
        source_proof_verifier=verify_source_proof,
    )
    if receipt is None:
        return _fail("COMPOSITIONAL_ENTAILMENT_NOT_PROVED")

    return {
        **dict(receipt),
        "authority_schema":AUTHORITY_SCHEMA,
        "proof_class":"COMPOSITIONAL_SOURCE_TO_CONCEPT",
        "semantic_truth_authority":False,
        "execution_authority":False,
        "acceptance_authority":False,
        "terminal_authority":False,
        "boundary":(
            "SOURCE_TO_TARGET_ONLY__SOURCE_CONSTRAINTS_FROM_BRAIN_OWNED_"
            "SOURCE_PROOF_REGISTRY__TARGET_FORMULA_FROM_EXACT_SOURCE_DECLARATION__"
            "NO_REVERSE_ENTAILMENT_WITHOUT_INDEPENDENT_SOURCE_COMPLETENESS"
        ),
    }
