"""OEWN 2025 release -> authenticated bounded concept registry bridge V1.

The source of lexical knowledge is the exact content-addressed OEWN 2025 JSON
release. This bridge does not choose a sense. It deterministically converts the
complete release-relative sense universe for one exact lemma/POS into the
existing bounded concept registry schema and can independently recompute a
registry-authority receipt from the source archive.

The registry's terminal signatures are deliberately *lexical identity* signatures.
They keep distinct senses distinct and therefore cannot falsely grant task-level
semantic equivalence. Task-specific decision equivalence remains downstream.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Callable, Mapping

from canonical.runtime import bounded_authenticated_concept_universe_v1 as concept
from canonical.runtime.oewn_release_sense_universe_v1 import (
    RELEASE_ID,
    RELEASE_SHA256,
    enumerate_senses,
)

SCHEMA="PROJECT_BRAIN_OEWN_2025_BOUNDED_CONCEPT_REGISTRY_BRIDGE_V1"
RECEIPT_KIND="OEWN_2025_RELEASE_DERIVED_REGISTRY_AUTHORITY_V1"


class OEWNRegistryBridgeError(ValueError):
    pass


def _canon(value:Any)->bytes:
    return json.dumps(
        value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False
    ).encode("utf-8")


def _sha(value:Any)->str:
    return sha256(_canon(value)).hexdigest()


def _relation_singleton(relations:Mapping[str,Any],key:str)->str|None:
    value=relations.get(key)
    if isinstance(value,list) and len(value)==1 and isinstance(value[0],str) and value[0]:
        return value[0]
    return None


def _build_from_enumeration(out:Mapping[str,Any])->dict[str,Any]:
    if out.get("pass") is not True:
        raise OEWNRegistryBridgeError("SENSE_UNIVERSE_NOT_VERIFIED")
    if out.get("archive_sha256")!=RELEASE_SHA256:
        raise OEWNRegistryBridgeError("SENSE_UNIVERSE_RELEASE_HASH_MISMATCH")
    if out.get("candidate_set_complete_relative_to_release") is not True:
        raise OEWNRegistryBridgeError("SENSE_UNIVERSE_COMPLETENESS_UNPROVED")
    if out.get("intended_sense_identified") is not False:
        raise OEWNRegistryBridgeError("UPSTREAM_ENUMERATOR_MUST_NOT_SELECT_SENSE")

    lemma=str(out.get("lemma") or "").strip()
    pos=out.get("requested_part_of_speech")
    pos_scope=str(pos if pos is not None else "ALL")
    senses=out.get("senses")
    if not isinstance(senses,list) or not senses:
        raise OEWNRegistryBridgeError("NONEMPTY_SENSE_UNIVERSE_REQUIRED")

    concepts=[]
    seen=set()
    for i,row in enumerate(senses):
        if not isinstance(row,Mapping):
            raise OEWNRegistryBridgeError(f"SENSE_ROW_INVALID:{i}")
        sense_id=str(row.get("sense_id") or "").strip()
        synset_id=str(row.get("synset_id") or "").strip()
        if not sense_id or not synset_id:
            raise OEWNRegistryBridgeError(f"SENSE_ID_OR_SYNSET_REQUIRED:{i}")
        if sense_id in seen:
            raise OEWNRegistryBridgeError("DUPLICATE_SENSE_ID:"+sense_id)
        seen.add(sense_id)

        members=row.get("members")
        if not isinstance(members,list) or not members:
            raise OEWNRegistryBridgeError("SENSE_MEMBERS_REQUIRED:"+sense_id)
        surfaces=sorted({str(x).strip().casefold() for x in members if str(x).strip()})
        if lemma not in surfaces:
            raise OEWNRegistryBridgeError("LEMMA_NOT_IN_SENSE_MEMBERS:"+sense_id)

        attrs={
            "sense_id":sense_id,
            "synset_id":synset_id,
            "part_of_speech":str(row.get("part_of_speech") or ""),
            "lexname":str(row.get("lexname") or ""),
        }
        relations=row.get("relations")
        relations=relations if isinstance(relations,Mapping) else {}
        domain_topic=_relation_singleton(relations,"domain_topic")
        if domain_topic is not None:
            attrs["domain_topic_singleton"]=domain_topic
        hypernym=_relation_singleton(relations,"hypernym")
        if hypernym is not None:
            attrs["hypernym_singleton"]=hypernym

        definitions=row.get("definitions")
        definitions=definitions if isinstance(definitions,list) else []
        attrs["definition_sha256"]=_sha(definitions)

        concepts.append({
            "concept_id":"OEWN2025::"+sense_id,
            "surfaces":surfaces,
            "attributes":attrs,
            "terminal_signature_complete":True,
            "terminal_signature":{
                "scope":"OEWN_2025_LEXICAL_SENSE_IDENTITY_ONLY",
                "lexical_sense_id":sense_id,
            },
        })

    registry={
        "schema":concept.REGISTRY_SCHEMA,
        "registry_id":f"{RELEASE_ID}::{pos_scope}::{lemma}",
        "scope_id":f"OEWN_2025_LEXICAL_SENSE_IDENTITY::{pos_scope}::{lemma}",
        "bounded_finite_registry":True,
        "concepts":concepts,
        "observations":[],
    }
    checked=concept._validate_registry(registry)
    return {
        "schema":SCHEMA,
        "status":"PASS__OEWN_2025_RELEASE_DERIVED_BOUNDED_CONCEPT_REGISTRY",
        "pass":True,
        "archive_sha256":out["archive_sha256"],
        "lemma":lemma,
        "part_of_speech":pos,
        "sense_count":len(concepts),
        "registry":registry,
        "registry_sha256":checked["registry_sha256"],
        "scope_id":registry["scope_id"],
        "registry_id":registry["registry_id"],
        "candidate_set_complete_relative_to_oewn_release":True,
        "lexical_identity_terminal_signatures_only":True,
        "task_terminal_equivalence_claimed":False,
        "intended_sense_identified":False,
        "open_world_english_sense_completeness_claimed":False,
        "semantic_truth_authority":False,
        "execution_authority":False,
        "promotion_authority":False,
        "acceptance_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
    }


def build_registry(
    archive:bytes|bytearray|str|Path,
    lemma:str,
    *,
    part_of_speech:str|None=None,
)->dict[str,Any]:
    try:
        out=enumerate_senses(archive,lemma,part_of_speech=part_of_speech)
        return _build_from_enumeration(out)
    except Exception as exc:
        return {
            "schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,
            "reason":type(exc).__name__+":"+str(exc),
            "semantic_truth_authority":False,"terminal_authority":False,
            "terminal_credit_delta":0,
        }


def _receipt_basis(built:Mapping[str,Any])->dict[str,Any]:
    return {
        "receipt_kind":RECEIPT_KIND,
        "release_id":RELEASE_ID,
        "archive_sha256":built["archive_sha256"],
        "registry_sha256":built["registry_sha256"],
        "registry_id":built["registry_id"],
        "scope_id":built["scope_id"],
        "scope_completeness_authenticated":True,
        "concept_semantics_authenticated":True,
        "authority_scope":"OEWN_2025_RELEASE_RELATIVE_LEXICAL_SENSE_IDENTITY_ONLY",
        "verification_authority_mutated":False,
    }


def issue_authority_receipt(
    archive:bytes|bytearray|str|Path,
    registry:Mapping[str,Any],
)->dict[str,Any]:
    """Recompute the source-derived registry and issue a content-bound receipt."""
    if not isinstance(registry,Mapping):
        raise OEWNRegistryBridgeError("REGISTRY_REQUIRED")
    rid=str(registry.get("registry_id") or "")
    scope=str(registry.get("scope_id") or "")
    prefix=RELEASE_ID+"::"
    scope_prefix="OEWN_2025_LEXICAL_SENSE_IDENTITY::"
    if not rid.startswith(prefix) or not scope.startswith(scope_prefix):
        raise OEWNRegistryBridgeError("REGISTRY_NOT_OEWN_2025_LEXICAL_SCOPE")
    try:
        _,pos_scope,lemma=rid.split("::",2)
    except ValueError as exc:
        raise OEWNRegistryBridgeError("REGISTRY_ID_INVALID") from exc
    pos=None if pos_scope=="ALL" else pos_scope
    rebuilt=build_registry(archive,lemma,part_of_speech=pos)
    if rebuilt.get("pass") is not True:
        raise OEWNRegistryBridgeError("SOURCE_RECOMPUTATION_FAILED")
    if rebuilt["registry"]!=registry:
        raise OEWNRegistryBridgeError("REGISTRY_NOT_EXACT_SOURCE_DERIVATION")
    basis=_receipt_basis(rebuilt)
    receipt={
        "schema":concept.AUTHORITY_SCHEMA,
        "pass":True,
        **basis,
    }
    receipt["receipt_sha256"]=_sha(receipt)
    return receipt


def verify_authority_receipt(
    archive:bytes|bytearray|str|Path,
    registry:Mapping[str,Any],
    receipt:Mapping[str,Any],
)->dict[str,Any]:
    """Verify a receipt by recomputing the registry from the exact source archive."""
    try:
        if not isinstance(receipt,Mapping):
            raise OEWNRegistryBridgeError("RECEIPT_REQUIRED")
        expected=issue_authority_receipt(archive,registry)
        if dict(receipt)!=expected:
            raise OEWNRegistryBridgeError("RECEIPT_NOT_EXACT_SOURCE_RECOMPUTATION")
        return deepcopy(expected)
    except Exception as exc:
        return {
            "schema":concept.AUTHORITY_SCHEMA,
            "pass":False,
            "reason":type(exc).__name__+":"+str(exc),
            "scope_completeness_authenticated":False,
            "concept_semantics_authenticated":False,
            "verification_authority_mutated":False,
        }


def make_authority_verifier(
    archive:bytes|bytearray|str|Path,
    registry:Mapping[str,Any],
)->Callable[[Mapping[str,Any]],dict[str,Any]]:
    return lambda receipt: verify_authority_receipt(archive,registry,receipt)
