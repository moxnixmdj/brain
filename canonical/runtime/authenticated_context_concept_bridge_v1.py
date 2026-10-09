"""Authenticated typed-context to bounded concept-universe bridge."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime.authoritative_typed_context_compiler_v1 import compile_typed_context
from canonical.runtime.bounded_authenticated_concept_universe_v1 import resolve as resolve_universe

SCHEMA="PROJECT_BRAIN_AUTHENTICATED_CONTEXT_CONCEPT_BRIDGE_V1"
CONTEXT_AUTHORITY_SCHEMA="PROJECT_BRAIN_TYPED_CONTEXT_SOURCE_AUTHORITY_RECEIPT_V1"
_HEX=set("0123456789abcdef")

def _sha_ok(v:Any)->bool:
    s=str(v or "").lower()
    return len(s)==64 and all(c in _HEX for c in s)

def _base(status:str,passed:bool,**extra:Any)->dict[str,Any]:
    return {
        "schema":SCHEMA,"status":status,"pass":passed,
        "context_source_authorized":False,
        "context_field_semantics_authenticated":False,
        "registry_scope_authenticated":False,
        "concept_binding_proved":False,
        "semantic_truth_authority":False,"execution_authority":False,
        "promotion_authority":False,"acceptance_authority":False,
        "terminal_authority":False,"terminal_credit_delta":0,**extra,
    }

def _auth_context(compiled:Mapping[str,Any],scope_id:str,receipt:Any,verifier:Any)->dict[str,Any]:
    if not isinstance(receipt,Mapping) or not callable(verifier):
        return {"pass":False,"reason":"CONTEXT_AUTHORITY_RECEIPT_AND_VERIFIER_REQUIRED"}
    out=verifier(deepcopy(dict(receipt)))
    if not isinstance(out,Mapping):
        return {"pass":False,"reason":"CONTEXT_AUTHORITY_VERIFIER_RETURNED_NO_RECEIPT"}
    out=deepcopy(dict(out))
    required={
        "pass":True,"schema":CONTEXT_AUTHORITY_SCHEMA,"scope_id":scope_id,
        "source_id":compiled["source_id"],
        "raw_source_sha256":compiled["raw_source_sha256"],
        "typed_context_sha256":compiled["typed_context_sha256"],
        "source_authorized_for_scope":True,
        "field_semantics_authenticated":True,
        "verification_authority_mutated":False,
    }
    bad=[k for k,v in required.items() if out.get(k)!=v]
    if not _sha_ok(out.get("receipt_sha256")): bad.append("receipt_sha256")
    projection=out.get("attribute_projection")
    if not isinstance(projection,Sequence) or isinstance(projection,(str,bytes)) or not projection:
        bad.append("attribute_projection")
    if bad:
        return {"pass":False,"reason":"CONTEXT_AUTHORITY_BINDING_INVALID","mismatch_fields":sorted(set(bad)),"authority_result":out}
    return out

def _project(context:Mapping[str,Any],projection:Sequence[Mapping[str,Any]])->dict[str,Any]:
    fields=context.get("fields")
    if not isinstance(fields,Mapping): raise ValueError("TYPED_CONTEXT_FIELDS_INVALID")
    attrs={}; used=set()
    for i,row in enumerate(projection):
        if not isinstance(row,Mapping) or set(row)!={"registry_attribute","field_name","field_type"}:
            raise ValueError(f"ATTRIBUTE_PROJECTION_ROW_INVALID:{i}")
        attr=str(row["registry_attribute"]).strip()
        name=str(row["field_name"]).strip()
        kind=str(row["field_type"]).strip()
        if not attr or not name or not kind: raise ValueError(f"ATTRIBUTE_PROJECTION_FIELDS_REQUIRED:{i}")
        if attr in attrs or name in used: raise ValueError("ATTRIBUTE_PROJECTION_DUPLICATE")
        source=fields.get(name)
        if not isinstance(source,Mapping): raise ValueError("ATTRIBUTE_PROJECTION_FIELD_MISSING:"+name)
        if source.get("type")!=kind: raise ValueError("ATTRIBUTE_PROJECTION_FIELD_TYPE_MISMATCH:"+name)
        attrs[attr]=deepcopy(source.get("value")); used.add(name)
    if not attrs: raise ValueError("ATTRIBUTE_PROJECTION_EMPTY")
    return attrs

def resolve(
    *,
    registry:Mapping[str,Any],
    raw_context_source:str|bytes,
    context_source_id:str,
    scope_id:str,
    registry_authority_receipt:Mapping[str,Any]|None=None,
    registry_authority_verifier:Callable[[Mapping[str,Any]],Mapping[str,Any]|None]|None=None,
    context_authority_receipt:Mapping[str,Any]|None=None,
    context_authority_verifier:Callable[[Mapping[str,Any]],Mapping[str,Any]|None]|None=None,
    ambiguity_owner:str="SYSTEM_MODEL",
)->dict[str,Any]:
    try:
        if not isinstance(registry,Mapping): raise ValueError("REGISTRY_REQUIRED")
        if not isinstance(scope_id,str) or not scope_id.strip(): raise ValueError("SCOPE_ID_REQUIRED")
        if not isinstance(context_source_id,str) or not context_source_id.strip(): raise ValueError("CONTEXT_SOURCE_ID_REQUIRED")
        compiled=compile_typed_context(raw_context_source,source_id=context_source_id.strip())
        if compiled.get("status")!="COMPILED":
            return _base("FAIL_CLOSED",False,reason="TYPED_CONTEXT_COMPILATION_FAILED",context_compilation=compiled)

        auth=_auth_context(compiled,scope_id.strip(),context_authority_receipt,context_authority_verifier)
        if auth.get("pass") is not True:
            return _base(
                "OPEN__AUTHENTICATED_CONTEXT_SOURCE_REQUIRED",False,
                context_compilation=compiled,context_authority_result=auth,
                action="ACQUIRE_OR_VERIFY_ONLY_CONTEXT_SOURCE_AUTHORITY_AND_FIELD_TO_CONCEPT_ATTRIBUTE_SEMANTICS",
            )

        attrs=_project(compiled["typed_context"],auth["attribute_projection"])
        universe=resolve_universe(
            registry,{"required_attributes":attrs},ambiguity_owner=ambiguity_owner,
            authority_receipt=registry_authority_receipt,
            authority_verifier=registry_authority_verifier,
        )
        ids=list(universe.get("candidate_concept_ids") or [])
        registry_auth=universe.get("authenticated_scope_completeness") is True
        unique=registry_auth and len(ids)==1

        if unique:
            status="PASS__AUTHENTICATED_CONTEXT_BINDS_UNIQUE_CONCEPT"; passed=True
        elif registry_auth and universe.get("pass") is True:
            status="PASS__AUTHENTICATED_CONTEXT_TERMINALLY_EQUIVALENT_CONCEPTS"; passed=True
        elif registry_auth:
            status="OPEN__AUTHENTICATED_CONTEXT_REQUIRES_EXISTING_MINIMAX_DISCRIMINATOR"; passed=False
        else:
            status="OPEN__AUTHENTICATED_CONCEPT_REGISTRY_REQUIRED"; passed=False

        decision=universe.get("ambiguity_decision")
        return _base(
            status,passed,
            context_source_authorized=True,
            context_field_semantics_authenticated=True,
            registry_scope_authenticated=registry_auth,
            concept_binding_proved=unique,
            concept_id=ids[0] if unique else None,
            candidate_concept_ids=ids,
            required_attributes=attrs,
            context_compilation=compiled,
            context_authority_result=auth,
            concept_universe=universe,
            next_observation_id=decision.get("next_observation_id") if isinstance(decision,Mapping) else None,
            does_not_require_global_word_sense_identity=passed and not unique,
        )
    except Exception as exc:
        return _base("FAIL_CLOSED",False,reason=type(exc).__name__+":"+str(exc))
