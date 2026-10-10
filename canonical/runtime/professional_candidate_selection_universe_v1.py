"""Finite manifest-defined candidate-selection universe for professional R2.

This module removes an unnecessary open-world requirement from R2 candidate search.
It does not claim that every possible professional artifact or policy can be
generated. Instead, it defines the exact finite universe from which one run is
allowed to select: the frozen content-addressed manifest members.

Completeness is therefore a selection-contract property:
  every selectable candidate is a manifest member, and no non-member may be
  selected through this gate.

Generation completeness, quality, adequacy, acceptance, promotion, and terminal
authority remain separate.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_CANDIDATE_SELECTION_UNIVERSE_V1"
MANIFEST_SCHEMA="PROJECT_BRAIN_PROFESSIONAL_CANDIDATE_SELECTION_MANIFEST_V1"
ROOT_ID="R2_CANDIDATE_SEARCH"
BEHAVIOR_ID="PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001"
ALLOWED_SOURCE_KINDS=frozenset({"INCUMBENT","GENERATED","REUSED_VERIFIED"})


def _canon(value:Any)->str:
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)


def _digest(value:Any)->str:
    return "sha256:"+sha256(_canon(value).encode("utf-8")).hexdigest()


def _sha64(value:Any)->bool:
    return isinstance(value,str) and len(value)==64 and all(ch in "0123456789abcdef" for ch in value)


def _digest65(value:Any)->bool:
    return isinstance(value,str) and value.startswith("sha256:") and _sha64(value[7:])


def _base(status:str,*,passed:bool=False,**extra:Any)->dict[str,Any]:
    return {
        "schema":SCHEMA,
        "status":status,
        "pass":passed,
        "root_id":ROOT_ID,
        "selection_universe_authority":False,
        "policy_adequacy_authority":False,
        "semantic_truth_authority":False,
        "quality_authority":False,
        "acceptance_authority":False,
        "promotion_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        "incremental_spend_usd":0,
        **extra,
    }


def _fail(reason:str,**extra:Any)->dict[str,Any]:
    return _base("FAIL_CLOSED",reason=reason,**extra)


def freeze(payload:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(payload,Mapping):
        return _fail("PAYLOAD_NOT_OBJECT")
    allowed={
        "behavior_id","subject_id","subject_sha256","run_context_sha256",
        "incumbent_candidate_id","candidates",
    }
    extra=sorted(set(payload)-allowed)
    if extra:
        return _fail("UNMODELED_FIELDS",unmodeled_fields=extra)
    if payload.get("behavior_id")!=BEHAVIOR_ID:
        return _fail("BEHAVIOR_ID_INVALID")
    subject_id=payload.get("subject_id")
    subject_sha=payload.get("subject_sha256")
    context_sha=payload.get("run_context_sha256")
    incumbent=payload.get("incumbent_candidate_id")
    if not isinstance(subject_id,str) or not subject_id.strip():
        return _fail("SUBJECT_ID_REQUIRED")
    if not _sha64(subject_sha):
        return _fail("SUBJECT_SHA256_INVALID")
    if not _digest65(context_sha):
        return _fail("RUN_CONTEXT_SHA256_INVALID")
    if not isinstance(incumbent,str) or not incumbent.strip():
        return _fail("INCUMBENT_CANDIDATE_ID_REQUIRED")

    rows=payload.get("candidates")
    if not isinstance(rows,Sequence) or isinstance(rows,(str,bytes)) or not rows:
        return _fail("CANDIDATES_REQUIRED")

    normalized=[]
    ids=set()
    hashes=set()
    incumbent_count=0
    for index,row in enumerate(rows):
        if not isinstance(row,Mapping):
            return _fail("CANDIDATE_NOT_OBJECT",candidate_index=index)
        allowed_row={"candidate_id","content_sha256","source_kind","artifact_type","generator_trace_sha256"}
        row_extra=sorted(set(row)-allowed_row)
        if row_extra:
            return _fail("CANDIDATE_UNMODELED_FIELDS",candidate_index=index,unmodeled_fields=row_extra)
        cid=row.get("candidate_id")
        content_sha=row.get("content_sha256")
        source_kind=row.get("source_kind")
        artifact_type=row.get("artifact_type")
        trace_sha=row.get("generator_trace_sha256")
        if not isinstance(cid,str) or not cid.strip() or cid in ids:
            return _fail("CANDIDATE_ID_INVALID_OR_DUPLICATE",candidate_index=index)
        if not _sha64(content_sha) or content_sha in hashes:
            return _fail("CANDIDATE_CONTENT_SHA256_INVALID_OR_DUPLICATE",candidate_id=cid)
        if source_kind not in ALLOWED_SOURCE_KINDS:
            return _fail("CANDIDATE_SOURCE_KIND_INVALID",candidate_id=cid)
        if not isinstance(artifact_type,str) or not artifact_type.strip():
            return _fail("CANDIDATE_ARTIFACT_TYPE_REQUIRED",candidate_id=cid)
        if source_kind=="GENERATED":
            if not _digest65(trace_sha):
                return _fail("GENERATED_CANDIDATE_TRACE_SHA256_REQUIRED",candidate_id=cid)
        elif trace_sha is not None and not _digest65(trace_sha):
            return _fail("CANDIDATE_TRACE_SHA256_INVALID",candidate_id=cid)
        if cid==incumbent:
            incumbent_count+=1
            if source_kind!="INCUMBENT":
                return _fail("INCUMBENT_SOURCE_KIND_INVALID")
        ids.add(cid)
        hashes.add(content_sha)
        normalized.append({
            "candidate_id":cid,
            "content_sha256":content_sha,
            "source_kind":source_kind,
            "artifact_type":artifact_type,
            "generator_trace_sha256":trace_sha,
        })

    if incumbent_count!=1:
        return _fail("INCUMBENT_NOT_EXACTLY_ONE_MANIFEST_MEMBER",incumbent_count=incumbent_count)

    normalized=sorted(normalized,key=lambda row:row["candidate_id"])
    manifest={
        "schema":MANIFEST_SCHEMA,
        "behavior_id":BEHAVIOR_ID,
        "root_id":ROOT_ID,
        "subject_id":subject_id.strip(),
        "subject_sha256":subject_sha,
        "run_context_sha256":context_sha,
        "incumbent_candidate_id":incumbent,
        "candidate_count":len(normalized),
        "candidates":normalized,
        "selection_law":"ONLY_FROZEN_MANIFEST_MEMBERS_ARE_ELIGIBLE_FOR_DOWNSTREAM_SELECTION",
        "incumbent_preserved":True,
        "open_world_generation_complete":False,
        "policy_generation_complete":False,
        "terminal_authority":False,
    }
    universe_sha=_digest(manifest)
    return _base(
        "PASS__FINITE_CANDIDATE_SELECTION_UNIVERSE_FROZEN",
        passed=True,
        manifest=manifest,
        candidate_universe_sha256=universe_sha,
        candidate_count=len(normalized),
        incumbent_candidate_id=incumbent,
        finite_selection_universe_complete_by_construction=True,
        incumbent_preserved=True,
        open_world_generation_complete=False,
        policy_generation_complete=False,
        selection_universe_authority=False,
        boundary=(
            "STRUCTURAL_SELECTION_UNIVERSE_ONLY__CANDIDATE_BYTES_GENERATOR_TRACE_"
            "ADEQUACY_AND_QUALITY_REQUIRE_SEPARATE_CONTENT_ADDRESSED_VERIFICATION"
        ),
    )


def select(frozen:Mapping[str,Any],candidate_id:str)->dict[str,Any]:
    if not isinstance(frozen,Mapping) or frozen.get("pass") is not True:
        return _fail("FROZEN_UNIVERSE_PASS_REQUIRED")
    manifest=frozen.get("manifest")
    if not isinstance(manifest,Mapping) or manifest.get("schema")!=MANIFEST_SCHEMA:
        return _fail("FROZEN_MANIFEST_INVALID")
    if frozen.get("candidate_universe_sha256")!=_digest(dict(manifest)):
        return _fail("FROZEN_MANIFEST_DIGEST_MISMATCH")
    if not isinstance(candidate_id,str) or not candidate_id:
        return _fail("CANDIDATE_ID_REQUIRED")
    rows=manifest.get("candidates")
    if not isinstance(rows,list):
        return _fail("FROZEN_CANDIDATES_INVALID")
    matches=[row for row in rows if isinstance(row,Mapping) and row.get("candidate_id")==candidate_id]
    if len(matches)!=1:
        return _fail(
            "SELECTION_OUTSIDE_FROZEN_CANDIDATE_UNIVERSE",
            requested_candidate_id=candidate_id,
            candidate_universe_sha256=frozen.get("candidate_universe_sha256"),
        )
    return _base(
        "PASS__SELECTION_IS_MEMBER_OF_FROZEN_CANDIDATE_UNIVERSE",
        passed=True,
        selected_candidate=dict(matches[0]),
        candidate_universe_sha256=frozen.get("candidate_universe_sha256"),
        finite_selection_universe_complete_by_construction=True,
        selection_membership_verified=True,
        selection_universe_authority=False,
        policy_adequacy_authority=False,
        quality_authority=False,
        boundary="MEMBERSHIP_ONLY__NO_ADEQUACY_OR_QUALITY_INFERENCE",
    )


def run(args:Mapping[str,Any]|None=None)->dict[str,Any]:
    args=args or {}
    op=str(args.get("operation") or "FREEZE").upper()
    if op=="FREEZE":
        return freeze(args.get("payload") or {})
    if op=="SELECT":
        return select(args.get("frozen") or {},str(args.get("candidate_id") or ""))
    return _fail("OPERATION_INVALID")
