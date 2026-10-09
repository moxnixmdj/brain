"""Brain-owned semantic relation edge authority registry V2.

V2 extends V1 with compositional SOURCE_TO_TARGET semantic edges.

Supported proof families:
  EXPLICIT_SOURCE_IDENTITY
  EXPLICIT_BOUNDED_EXTENSION
  COMPOSITIONAL_SOURCE_TO_CONCEPT (source-aligned semantic edge evidence)

Each handler independently recomputes its own load-bearing evidence. Unsupported
evidence receives no semantic authority.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime import brain_owned_semantic_relation_edge_authority_v1 as identity
from canonical.runtime import brain_owned_bounded_semantic_relation_edge_authority_v1 as bounded
from canonical.runtime import brain_owned_compositional_semantic_relation_edge_authority_v1 as compositional

SCHEMA="PROJECT_BRAIN_SEMANTIC_RELATION_EDGE_AUTHORITY_REGISTRY_V2"

_HANDLERS=(identity,bounded,compositional)


def supported_proof_classes()->list[str]:
    return sorted([
        "EXPLICIT_SOURCE_IDENTITY",
        "EXPLICIT_BOUNDED_EXTENSION",
        "COMPOSITIONAL_SOURCE_TO_CONCEPT",
    ])


def supports(raw:Any)->bool:
    return any(handler.supports(raw) for handler in _HANDLERS)


def verify(raw:Mapping[str,Any])->dict[str,Any]:
    matched=[handler for handler in _HANDLERS if handler.supports(raw)]
    if len(matched)!=1:
        return {
            "pass":False,
            "schema":SCHEMA,
            "status":"FAIL_CLOSED",
            "reason":"PROOF_CLASS_UNSUPPORTED" if not matched else "PROOF_CLASS_DISPATCH_AMBIGUOUS",
            "supported_proof_classes":supported_proof_classes(),
            "semantic_truth_authority":False,
            "execution_authority":False,
            "acceptance_authority":False,
            "terminal_authority":False,
        }
    out=matched[0].verify(raw)
    if not isinstance(out,Mapping):
        return {
            "pass":False,
            "schema":SCHEMA,
            "status":"FAIL_CLOSED",
            "reason":"AUTHORITY_HANDLER_RETURNED_NO_RECEIPT",
            "supported_proof_classes":supported_proof_classes(),
            "semantic_truth_authority":False,
            "execution_authority":False,
            "acceptance_authority":False,
            "terminal_authority":False,
        }
    return dict(out)
