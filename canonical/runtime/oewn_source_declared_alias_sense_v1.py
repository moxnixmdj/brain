"""Authenticated source co-alias -> unique OEWN release-relative sense."""
from __future__ import annotations
from copy import deepcopy
from typing import Any,Mapping,Sequence
from canonical.runtime.https_source_fragment_projection_authority_v2 import verify_projection_pack
from canonical.runtime.oewn_release_sense_universe_v1 import RELEASE_ID,RELEASE_SHA256
from canonical.runtime.oewn_source_alias_kernel_v1 import norm,digest,validate_universe,declared_pair

SCHEMA="PROJECT_BRAIN_OEWN_SOURCE_DECLARED_ALIAS_SENSE_V1"
RECEIPT_SCHEMA="PROJECT_BRAIN_OEWN_SOURCE_DECLARED_ALIAS_SENSE_RECEIPT_V1"

def _base(status:str,passed:bool=False,**extra:Any)->dict[str,Any]:
    return {"schema":SCHEMA,"status":status,"pass":passed,
            "source_fragment_authenticated":False,
            "release_relative_sense_universe_complete":False,
            "source_declared_alias_proved":False,
            "unique_release_relative_sense_identified":False,
            "source_scoped_sense_binding_authority":False,
            "open_world_english_sense_completeness_claimed":False,
            "general_synonymy_claimed":False,
            "semantic_truth_authority":False,
            "policy_adequacy_authority":False,
            "execution_authority":False,"acceptance_authority":False,
            "promotion_authority":False,"terminal_authority":False,
            "terminal_credit_delta":0,**extra}

def _fragment(projection:Mapping[str,Any],fid:str)->dict[str,Any]:
    matched=projection.get("matched_fragments")
    if not isinstance(matched,Sequence) or isinstance(matched,(str,bytes)):
        raise ValueError("MATCHED_FRAGMENTS_INVALID")
    rows=[dict(x) for x in matched if isinstance(x,Mapping) and str(x.get("fragment_id") or "")==fid]
    if len(rows)!=1: raise ValueError("EXACT_ONE_MATCHED_FRAGMENT_REQUIRED")
    return rows[0]

def resolve(*,sense_universe:Mapping[str,Any],source_projection_pack:Mapping[str,Any],
            fragment_id:str,ambiguous_term:str,timeout_seconds:int=30,opener:Any=None)->dict[str,Any]:
    try:
        term=norm(ambiguous_term); fid=str(fragment_id or "").strip()
        if not term or not fid: raise ValueError("TERM_AND_FRAGMENT_ID_REQUIRED")
        universe=validate_universe(sense_universe,term)
        projection=verify_projection_pack(source_projection_pack,timeout_seconds=timeout_seconds,opener=opener)
        if projection.get("pass") is not True:
            return _base("OPEN__AUTHENTICATED_SOURCE_ALIAS_FRAGMENT_REQUIRED",
                         release_relative_sense_universe_complete=True,
                         sense_universe_sha256=universe["sha256"],
                         source_projection_result=projection)
        row=_fragment(projection,fid)
        left,right=declared_pair(str(row.get("text") or ""))
        if term==left: alias=right
        elif term==right: alias=left
        else:
            return _base("OPEN__SOURCE_ALIAS_DOES_NOT_NAME_AMBIGUOUS_TERM",
                         source_fragment_authenticated=True,
                         release_relative_sense_universe_complete=True,
                         source_declared_alias_proved=True,
                         declared_alias_pair=[left,right])
        matches=[x for x in universe["senses"] if alias in x["members"]]
        common={"source_fragment_authenticated":True,
                "release_relative_sense_universe_complete":True,
                "source_declared_alias_proved":True,
                "ambiguous_term":term,"declared_alias":alias,
                "declared_alias_pair":[left,right],
                "candidate_sense_count":len(universe["senses"]),
                "sense_universe_sha256":universe["sha256"],
                "source_id":projection.get("source_id"),"source_url":projection.get("url"),
                "source_fragment_id":fid,
                "source_projection_receipt":deepcopy(projection.get("receipt"))}
        if len(matches)!=1:
            state="MATCHES_NO_OEWN_RELEASE_SENSE" if not matches else "NOT_UNIQUE_ACROSS_OEWN_RELEASE_SENSES"
            return _base("OPEN__DECLARED_ALIAS_"+state,
                         alias_matching_sense_ids=[x["sense_id"] for x in matches],**common)
        selected=matches[0]
        core={"schema":RECEIPT_SCHEMA,"pass":True,"release_id":RELEASE_ID,
              "release_sha256":RELEASE_SHA256,"sense_universe_sha256":universe["sha256"],
              "ambiguous_term":term,"declared_alias":alias,
              "selected_sense_id":selected["sense_id"],"selected_synset_id":selected["synset_id"],
              "source_id":projection.get("source_id"),"source_url":projection.get("url"),
              "source_fragment_id":fid,
              "source_projection_receipt_sha256":(projection.get("receipt") or {}).get("receipt_sha256"),
              "source_alias_declaration_authenticated":True,
              "release_relative_sense_set_complete":True,
              "unique_alias_comember_match":True,
              "verification_authority_mutated":False}
        receipt=dict(core); receipt["receipt_sha256"]=digest(core)
        return _base("PASS__SOURCE_DECLARED_ALIAS_IDENTIFIES_UNIQUE_OEWN_RELEASE_SENSE",True,
                     unique_release_relative_sense_identified=True,
                     source_scoped_sense_binding_authority=True,
                     selected_sense_id=selected["sense_id"],selected_synset_id=selected["synset_id"],
                     selected_members=deepcopy(selected["members"]),receipt=receipt,**common)
    except Exception as exc:
        return _base("FAIL_CLOSED",reason=type(exc).__name__+":"+str(exc))
