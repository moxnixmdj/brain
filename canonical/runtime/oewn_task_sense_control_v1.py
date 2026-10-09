"""Authenticated OEWN release-sense to task-hypothesis control V1.

OEWN can prove a complete lexical sense candidate set relative to pinned release
bytes. It cannot prove which sense is intended in the current task or what action
that sense requires. This module closes only that composition gap.

An independent task-mapping verifier must bind every release sense to:
- task-scoped attributes;
- one complete task terminal signature;
- optional complete observation outcomes.

Only after that verification is the derived finite registry admitted to the
existing bounded concept-universe controller. If authenticated raw task context is
also available, the existing authenticated context bridge may filter the registry.

No model, similarity score, WordNet gloss, or caller-supplied mapping can
self-certify task semantics.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime import oewn_release_sense_universe_v1 as oewn
from canonical.runtime import bounded_authenticated_concept_universe_v1 as concept
from canonical.runtime.authenticated_context_concept_bridge_v1 import (
    resolve as resolve_context,
)

SCHEMA="PROJECT_BRAIN_OEWN_TASK_SENSE_CONTROL_V1"
MAPPING_AUTHORITY_SCHEMA="PROJECT_BRAIN_OEWN_TASK_SENSE_MAPPING_AUTHORITY_RECEIPT_V1"
_HEX=set("0123456789abcdef")


def _canon(v:Any)->bytes:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode("utf-8")

def _sha(v:Any)->str:
    return sha256(_canon(v)).hexdigest()

def _sha_ok(v:Any)->bool:
    s=str(v or "").lower()
    return len(s)==64 and all(c in _HEX for c in s)

def _base(status:str,passed:bool,**extra:Any)->dict[str,Any]:
    return {
        "schema":SCHEMA,"status":status,"pass":passed,
        "release_candidate_set_complete":False,
        "task_mapping_authenticated":False,
        "derived_registry_authenticated":False,
        "intended_sense_identified":False,
        "semantic_truth_authority":False,"execution_authority":False,
        "promotion_authority":False,"acceptance_authority":False,
        "terminal_authority":False,"terminal_credit_delta":0,**extra,
    }

def enumerate_release_universe(
    archive:bytes|bytearray|str,
    lemma:str,
    *,
    part_of_speech:str|None=None,
)->dict[str,Any]:
    out=oewn.enumerate_senses(archive,lemma,part_of_speech=part_of_speech)
    if out.get("pass") is not True:
        return {"pass":False,"release":out}
    payload={
        "release_id":out.get("release_id"),
        "archive_sha256":out.get("archive_sha256"),
        "lemma":out.get("lemma"),
        "requested_part_of_speech":out.get("requested_part_of_speech"),
        "senses":[{
            "sense_id":row.get("sense_id"),
            "synset_id":row.get("synset_id"),
            "part_of_speech":row.get("part_of_speech"),
            "lexname":row.get("lexname"),
            "members":row.get("members"),
            "definitions":row.get("definitions"),
        } for row in out.get("senses") or []],
    }
    return {
        "pass":True,
        "release":out,
        "sense_universe_sha256":_sha(payload),
        "sense_ids":[str(x.get("sense_id")) for x in out.get("senses") or []],
    }

def _mapping_authority(
    enum:Mapping[str,Any],
    *,
    scope_id:str,
    receipt:Mapping[str,Any]|None,
    verifier:Callable[[Mapping[str,Any]],Mapping[str,Any]|None]|None,
)->dict[str,Any]:
    if not isinstance(receipt,Mapping) or not callable(verifier):
        return {"pass":False,"reason":"TASK_MAPPING_AUTHORITY_RECEIPT_AND_VERIFIER_REQUIRED"}
    checked=verifier(deepcopy(dict(receipt)))
    if not isinstance(checked,Mapping):
        return {"pass":False,"reason":"TASK_MAPPING_AUTHORITY_VERIFIER_RETURNED_NO_RECEIPT"}
    out=deepcopy(dict(checked))
    release=enum["release"]
    required={
        "pass":True,
        "schema":MAPPING_AUTHORITY_SCHEMA,
        "scope_id":scope_id,
        "release_id":release.get("release_id"),
        "archive_sha256":release.get("archive_sha256"),
        "lemma":release.get("lemma"),
        "requested_part_of_speech":release.get("requested_part_of_speech"),
        "sense_universe_sha256":enum["sense_universe_sha256"],
        "mapping_complete_for_release_senses":True,
        "task_semantics_authenticated":True,
        "verification_authority_mutated":False,
    }
    bad=[k for k,v in required.items() if out.get(k)!=v]
    if not _sha_ok(out.get("receipt_sha256")): bad.append("receipt_sha256")
    mappings=out.get("mappings")
    if not isinstance(mappings,Sequence) or isinstance(mappings,(str,bytes)):
        bad.append("mappings")
    observations=out.get("observations",[])
    if not isinstance(observations,Sequence) or isinstance(observations,(str,bytes)):
        bad.append("observations")
    if bad:
        return {
            "pass":False,"reason":"TASK_MAPPING_AUTHORITY_BINDING_INVALID",
            "mismatch_fields":sorted(set(bad)),"authority_result":out,
        }
    return out

def _compile_registry(
    enum:Mapping[str,Any],
    authority:Mapping[str,Any],
    *,
    scope_id:str,
)->dict[str,Any]:
    release=enum["release"]
    senses=list(release.get("senses") or [])
    expected_ids=[str(x.get("sense_id")) for x in senses]
    by_sense={str(x.get("sense_id")):x for x in senses}
    rows=authority.get("mappings") or []
    mapping_by_id={}
    for i,raw in enumerate(rows):
        if not isinstance(raw,Mapping):
            raise ValueError(f"TASK_MAPPING_ROW_INVALID:{i}")
        if set(raw)!={"sense_id","attributes","terminal_signature","terminal_signature_complete"}:
            raise ValueError(f"TASK_MAPPING_ROW_KEYS_INVALID:{i}")
        sid=str(raw.get("sense_id") or "").strip()
        if not sid or sid in mapping_by_id:
            raise ValueError(f"TASK_MAPPING_SENSE_ID_INVALID_OR_DUPLICATE:{i}")
        if sid not in by_sense:
            raise ValueError("TASK_MAPPING_UNKNOWN_RELEASE_SENSE:"+sid)
        attrs=raw.get("attributes")
        sig=raw.get("terminal_signature")
        if not isinstance(attrs,Mapping):
            raise ValueError("TASK_MAPPING_ATTRIBUTES_INVALID:"+sid)
        if raw.get("terminal_signature_complete") is not True or not isinstance(sig,Mapping):
            raise ValueError("TASK_MAPPING_TERMINAL_SIGNATURE_INCOMPLETE:"+sid)
        mapping_by_id[sid]=raw
    if set(mapping_by_id)!=set(expected_ids):
        raise ValueError("TASK_MAPPING_DOES_NOT_COVER_EXACT_RELEASE_SENSE_SET")

    concept_ids={sid:"OEWN_SENSE::"+sid for sid in expected_ids}
    concepts=[]
    for sid in expected_ids:
        sense=by_sense[sid]; mapped=mapping_by_id[sid]
        surfaces=[]
        for raw_surface in [release.get("lemma"),*(sense.get("members") or [])]:
            s=" ".join(str(raw_surface or "").strip().split()).casefold()
            if s and s not in surfaces: surfaces.append(s)
        attrs={
            "oewn_sense_id":sid,
            "oewn_synset_id":sense.get("synset_id"),
            "oewn_part_of_speech":sense.get("part_of_speech"),
            "oewn_lexname":sense.get("lexname"),
            **deepcopy(dict(mapped["attributes"])),
        }
        concepts.append({
            "concept_id":concept_ids[sid],
            "surfaces":surfaces,
            "attributes":attrs,
            "terminal_signature_complete":True,
            "terminal_signature":deepcopy(dict(mapped["terminal_signature"])),
        })

    observations=[]
    seen_obs=set()
    for i,raw in enumerate(authority.get("observations") or []):
        if not isinstance(raw,Mapping):
            raise ValueError(f"TASK_MAPPING_OBSERVATION_INVALID:{i}")
        if set(raw)!={"observation_id","outcome_map_complete","outcomes","cost_units"}:
            raise ValueError(f"TASK_MAPPING_OBSERVATION_KEYS_INVALID:{i}")
        oid=str(raw.get("observation_id") or "").strip()
        if not oid or oid in seen_obs:
            raise ValueError("TASK_MAPPING_OBSERVATION_ID_INVALID_OR_DUPLICATE")
        seen_obs.add(oid)
        outcomes=raw.get("outcomes")
        if raw.get("outcome_map_complete") is not True or not isinstance(outcomes,Mapping):
            raise ValueError("TASK_MAPPING_OBSERVATION_OUTCOME_MAP_INVALID:"+oid)
        if set(map(str,outcomes))!=set(expected_ids):
            raise ValueError("TASK_MAPPING_OBSERVATION_NOT_COMPLETE_FOR_RELEASE_SENSES:"+oid)
        observations.append({
            "observation_id":oid,
            "outcome_map_complete":True,
            "outcomes":{concept_ids[str(sid)]:deepcopy(v) for sid,v in outcomes.items()},
            "cost_units":raw.get("cost_units"),
        })

    registry={
        "schema":concept.REGISTRY_SCHEMA,
        "registry_id":"OEWN_TASK::"+scope_id+"::"+enum["sense_universe_sha256"][:16],
        "scope_id":scope_id,
        "bounded_finite_registry":True,
        "concepts":concepts,
        "observations":observations,
    }
    checked=concept._validate_registry(registry)
    return {"registry":registry,"registry_sha256":checked["registry_sha256"],"concept_ids":concept_ids}

def _derived_registry_verifier(
    compiled:Mapping[str,Any],
    authority:Mapping[str,Any],
):
    def verify(receipt:Mapping[str,Any])->dict[str,Any]:
        if not isinstance(receipt,Mapping):
            return {"pass":False}
        if receipt.get("mapping_authority_receipt_sha256")!=authority.get("receipt_sha256"):
            return {"pass":False}
        return {
            "pass":True,
            "schema":concept.AUTHORITY_SCHEMA,
            "registry_sha256":compiled["registry_sha256"],
            "registry_id":compiled["registry"]["registry_id"],
            "scope_id":compiled["registry"]["scope_id"],
            "scope_completeness_authenticated":True,
            "concept_semantics_authenticated":True,
            "verification_authority_mutated":False,
            "receipt_sha256":_sha({
                "registry_sha256":compiled["registry_sha256"],
                "mapping_authority_receipt_sha256":authority.get("receipt_sha256"),
            }),
        }
    return verify

def resolve(
    *,
    archive:bytes|bytearray|str,
    lemma:str,
    scope_id:str,
    mapping_authority_receipt:Mapping[str,Any]|None,
    mapping_authority_verifier:Callable[[Mapping[str,Any]],Mapping[str,Any]|None]|None,
    part_of_speech:str|None=None,
    raw_context_source:str|bytes|None=None,
    context_source_id:str|None=None,
    context_authority_receipt:Mapping[str,Any]|None=None,
    context_authority_verifier:Callable[[Mapping[str,Any]],Mapping[str,Any]|None]|None=None,
    ambiguity_owner:str="SYSTEM_MODEL",
)->dict[str,Any]:
    try:
        if not isinstance(scope_id,str) or not scope_id.strip():
            raise ValueError("SCOPE_ID_REQUIRED")
        enum=enumerate_release_universe(archive,lemma,part_of_speech=part_of_speech)
        if enum.get("pass") is not True:
            return _base("FAIL_CLOSED__RELEASE_ENUMERATION_FAILED",False,release_enumeration=enum)
        release=enum["release"]
        if release.get("release_relative_absence") is True:
            return _base(
                "OPEN__LEMMA_OR_POS_ABSENT_FROM_PINNED_OEWN_RELEASE",False,
                release_candidate_set_complete=True,release_enumeration=enum,
                action="USE_OTHER_AUTHENTICATED_DOMAIN_OR_OPEN_WORLD_CANDIDATE_ACQUISITION_ROUTE",
            )
        auth=_mapping_authority(
            enum,scope_id=scope_id.strip(),
            receipt=mapping_authority_receipt,verifier=mapping_authority_verifier,
        )
        if auth.get("pass") is not True:
            return _base(
                "OPEN__AUTHENTICATED_TASK_SENSE_MAPPING_REQUIRED",False,
                release_candidate_set_complete=True,
                release_enumeration=enum,mapping_authority_result=auth,
                action="ACQUIRE_OR_VERIFY_TASK_SPECIFIC_MAPPING_FOR_EVERY_RELEASE_SENSE",
            )
        compiled=_compile_registry(enum,auth,scope_id=scope_id.strip())
        derived_receipt={"mapping_authority_receipt_sha256":auth["receipt_sha256"]}
        derived_verifier=_derived_registry_verifier(compiled,auth)

        if raw_context_source is not None:
            if not isinstance(context_source_id,str) or not context_source_id.strip():
                raise ValueError("CONTEXT_SOURCE_ID_REQUIRED_WITH_RAW_CONTEXT")
            inner=resolve_context(
                registry=compiled["registry"],
                raw_context_source=raw_context_source,
                context_source_id=context_source_id.strip(),
                scope_id=scope_id.strip(),
                registry_authority_receipt=derived_receipt,
                registry_authority_verifier=derived_verifier,
                context_authority_receipt=context_authority_receipt,
                context_authority_verifier=context_authority_verifier,
                ambiguity_owner=ambiguity_owner,
            )
            intended=inner.get("concept_binding_proved") is True
            return _base(
                "PASS__OEWN_TASK_SENSE_RESOLVED_WITH_AUTHENTICATED_CONTEXT"
                if inner.get("pass") is True else
                "OPEN__OEWN_TASK_SENSE_NEEDS_MINIMUM_CONTEXT_DISCRIMINATOR",
                inner.get("pass") is True,
                release_candidate_set_complete=True,
                task_mapping_authenticated=True,
                derived_registry_authenticated=inner.get("registry_scope_authenticated") is True,
                intended_sense_identified=intended,
                intended_concept_id=inner.get("concept_id"),
                release_enumeration=enum,
                mapping_authority_result=auth,
                derived_registry=compiled["registry"],
                context_result=inner,
                next_observation_id=inner.get("next_observation_id"),
            )

        inner=concept.resolve(
            compiled["registry"],{},
            ambiguity_owner=ambiguity_owner,
            authority_receipt=derived_receipt,
            authority_verifier=derived_verifier,
        )
        ids=list(inner.get("candidate_concept_ids") or [])
        unique=inner.get("authenticated_scope_completeness") is True and len(ids)==1
        return _base(
            "PASS__OEWN_TASK_SENSE_UNIQUE_OR_TERMINALLY_EQUIVALENT"
            if inner.get("pass") is True else
            "OPEN__OEWN_TASK_SENSE_NEEDS_MINIMUM_DISCRIMINATOR",
            inner.get("pass") is True,
            release_candidate_set_complete=True,
            task_mapping_authenticated=True,
            derived_registry_authenticated=inner.get("authenticated_scope_completeness") is True,
            intended_sense_identified=unique,
            intended_concept_id=ids[0] if unique else None,
            release_enumeration=enum,
            mapping_authority_result=auth,
            derived_registry=compiled["registry"],
            concept_universe_result=inner,
            next_observation_id=(inner.get("ambiguity_decision") or {}).get("next_observation_id")
            if isinstance(inner.get("ambiguity_decision"),Mapping) else None,
        )
    except Exception as exc:
        return _base("FAIL_CLOSED",False,reason=type(exc).__name__+":"+str(exc))
