"""Brain-owned semantic relation edge authority registry V4.

V4 preserves every V3 proof class and adds:
  DOMAIN_MAPPING_SCOPED_RELATION

The new class exposes only relation directions already independently proved by
the Brain-owned domain-mapping truth certificate. Unsupported evidence remains
fail-closed.
"""
from __future__ import annotations
from typing import Any, Mapping

from canonical.runtime import brain_owned_semantic_relation_edge_authority_v1 as identity
from canonical.runtime import brain_owned_bounded_semantic_relation_edge_authority_v1 as bounded
from canonical.runtime import brain_owned_source_implication_closure_edge_authority_v1 as implication
from canonical.runtime import brain_owned_domain_mapping_relation_edge_authority_v1 as domain
from canonical.runtime import brain_owned_scoped_domain_mapping_relation_edge_authority_v1 as scoped_domain

SCHEMA="PROJECT_BRAIN_SEMANTIC_RELATION_EDGE_AUTHORITY_REGISTRY_V4"
_HANDLERS=(identity,bounded,implication,domain,scoped_domain)


def supported_proof_classes()->list[str]:
    return sorted(
        str(getattr(handler,"PROOF_CLASS",""))
        for handler in _HANDLERS
        if str(getattr(handler,"PROOF_CLASS",""))
    )


def supports(raw:Any)->bool:
    return any(handler.supports(raw) for handler in _HANDLERS)


def can_prove(raw:Any)->bool:
    if not supports(raw):
        return False
    out=verify(raw)
    return isinstance(out,Mapping) and out.get("pass") is True


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
