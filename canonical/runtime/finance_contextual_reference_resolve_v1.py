"""Bounded producer for structurally resolvable contextual finance references.

Owned forms are exactly those implemented by contextual_reference_operators:
- cross-sentence modal subject continuation via It/They with number check;
- unique prior "X mode is enabled" -> "that mode";
- modal predicate ellipsis "B must, too";
- explicit two-by-two respectively mapping.

Inputs with any unresolved reference class fail closed.  No ontology, synonymy,
word-sense, former/latter, demonstrative-event, or external-world semantics.
"""
from __future__ import annotations

from hashlib import sha256
from typing import Any, Mapping

from canonical.runtime.contextual_reference_operators import propose_contextual_references

SCHEMA="PROJECT_BRAIN_FINANCE_CONTEXTUAL_REFERENCE_RESOLVE_V1"
INPUT_SCHEMA="PROJECT_BRAIN_FINANCE_CONTEXTUAL_REFERENCE_CASE_V1"
RESULT_SCHEMA="PROJECT_BRAIN_FINANCE_CONTEXTUAL_REFERENCE_RESULT_V1"


def _sha(text:str)->str:
    return sha256(text.encode("utf-8")).hexdigest()


def compute(case:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(case,Mapping) or case.get("schema")!=INPUT_SCHEMA:
        raise ValueError("CASE_SCHEMA_INVALID")
    if case.get("domain")!="FINANCE":
        raise ValueError("FINANCE_DOMAIN_MARKER_REQUIRED")
    source_id=case.get("source_id")
    source_text=case.get("source_text")
    if not isinstance(source_id,str) or not source_id.strip():
        raise ValueError("SOURCE_ID_REQUIRED")
    if not isinstance(source_text,str) or not source_text.strip():
        raise ValueError("SOURCE_TEXT_REQUIRED")

    out=propose_contextual_references(source_text)
    if out.get("status")!="PROPOSED":
        raise ValueError("SOURCE_NOT_EXACT_BOUNDED_CONTEXTUAL_REFERENCE:"+str(out.get("status")))
    unresolved=out.get("unresolved")
    proposal=out.get("proposal")
    if unresolved:
        raise ValueError("UNRESOLVED_CONTEXTUAL_REFERENCE_PRESENT")
    if not isinstance(proposal,Mapping):
        raise ValueError("PROPOSAL_MISSING")
    count=sum(len(proposal.get(k) or []) for k in ("bindings","relations","obligations"))
    if count<=0:
        raise ValueError("NO_RESOLVED_REFERENCE_STRUCTURE")

    return {
        "schema":RESULT_SCHEMA,
        "status":"PASS__BOUNDED_FINANCE_CONTEXTUAL_REFERENCES_RESOLVED",
        "pass":True,
        "domain":"FINANCE",
        "source_id":source_id.strip(),
        "source_text_sha256":_sha(source_text),
        "proposal":{
            "bindings":proposal.get("bindings") or [],
            "relations":proposal.get("relations") or [],
            "obligations":proposal.get("obligations") or [],
        },
        "resolved_item_count":count,
        "supported_scope":[
            "MODAL_SUBJECT_PRONOUN_IT_THEY",
            "UNIQUE_PRIOR_MODE_TO_THAT_MODE",
            "MODAL_ELLIPSIS_TOO",
            "TWO_BY_TWO_RESPECTIVELY",
        ],
        "model_dependency_count":0,
        "general_coreference_claimed":False,
        "synonymy_claimed":False,
        "ontology_mapping_claimed":False,
        "external_world_truth_claimed":False,
        "terminal_authority":False,
    }
