"""Executable skill-program induction for Universal Learning V7.

Repeated verified learning traces may induce a reusable executable program
candidate only when their canonical operation skeleton is identical. The
candidate cannot self-verify. Reuse requires an independent exact-byte-bound
behavior-preservation receipt.
"""
from __future__ import annotations
import hashlib
import json
from typing import Any, Mapping, Sequence

SCHEMA="PROJECT_BRAIN_EXECUTABLE_SKILL_PROGRAM_V7"
RELATIONS={"EXACT","PROVEN_SUPERSET"}

class ExecutableSkillProgramError(ValueError):
    pass

def _s(x:Any)->str:
    return " ".join(str(x or "").split())

def _items(xs)->list[str]:
    return sorted({_s(x) for x in (xs or []) if _s(x)})

def normalize_steps(steps)->list[dict[str,Any]]:
    if not isinstance(steps,Sequence) or isinstance(steps,(str,bytes)) or not steps:
        raise ExecutableSkillProgramError("PROGRAM_STEPS_REQUIRED")
    out=[]
    for i,raw in enumerate(steps):
        if not isinstance(raw,Mapping):
            raise ExecutableSkillProgramError("PROGRAM_STEP_INVALID")
        op=_s(raw.get("op"))
        ins=_items(raw.get("inputs"))
        outs=_items(raw.get("outputs"))
        if not op:
            raise ExecutableSkillProgramError("PROGRAM_STEP_OP_REQUIRED")
        out.append({"index":i,"op":op,"inputs":ins,"outputs":outs})
    return out

def program_digest(*,steps,preconditions=(),postconditions=(),invalidators=())->str:
    body=json.dumps({
        "steps":normalize_steps(steps),
        "preconditions":_items(preconditions),
        "postconditions":_items(postconditions),
        "invalidators":_items(invalidators),
    },sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    return "sha256:"+hashlib.sha256(body).hexdigest()

def _episode(raw:Mapping[str,Any])->dict[str,Any]:
    eid=_s(raw.get("episode_id"))
    scope=_s(raw.get("scope_id"))
    if not eid or not scope:
        raise ExecutableSkillProgramError("EPISODE_ID_AND_SCOPE_REQUIRED")
    steps=normalize_steps(raw.get("steps"))
    pre=_items(raw.get("preconditions")); post=_items(raw.get("postconditions")); invalid=_items(raw.get("invalidators"))
    digest=program_digest(steps=steps,preconditions=pre,postconditions=post,invalidators=invalid)
    rec=raw.get("verification_receipt")
    if not isinstance(rec,Mapping):
        raise ExecutableSkillProgramError("EPISODE_RECEIPT_REQUIRED:"+eid)
    if rec.get("independent_verified") is not True or rec.get("exact_byte_bound") is not True or rec.get("conclusion")!="success":
        raise ExecutableSkillProgramError("EPISODE_RECEIPT_INVALID:"+eid)
    if rec.get("behavior_verified") is not True:
        raise ExecutableSkillProgramError("EPISODE_BEHAVIOR_NOT_VERIFIED:"+eid)
    if _s(rec.get("episode_id"))!=eid or _s(rec.get("scope_id"))!=scope:
        raise ExecutableSkillProgramError("EPISODE_RECEIPT_BINDING_MISMATCH:"+eid)
    if rec.get("program_sha256")!=digest:
        raise ExecutableSkillProgramError("EPISODE_PROGRAM_DIGEST_MISMATCH:"+eid)
    receipt_id=_s(rec.get("receipt_id"))
    if not receipt_id:
        raise ExecutableSkillProgramError("EPISODE_RECEIPT_ID_REQUIRED:"+eid)
    return {
        "episode_id":eid,"scope_id":scope,"steps":steps,
        "preconditions":pre,"postconditions":post,"invalidators":invalid,
        "program_sha256":digest,"verification_receipt":receipt_id
    }

def _skeleton(steps)->tuple:
    return tuple((x["op"],tuple(x["inputs"]),tuple(x["outputs"])) for x in normalize_steps(steps))

def candidate_digest(*,source_episode_ids,steps,preconditions,postconditions,invalidators)->str:
    body=json.dumps({
        "source_episode_ids":sorted(source_episode_ids),
        "steps":normalize_steps(steps),
        "preconditions":_items(preconditions),
        "postconditions":_items(postconditions),
        "invalidators":_items(invalidators),
    },sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    return "sha256:"+hashlib.sha256(body).hexdigest()

def induce_candidate(episodes:Sequence[Mapping[str,Any]])->dict[str,Any]:
    if len(episodes)<2:
        raise ExecutableSkillProgramError("AT_LEAST_TWO_VERIFIED_EPISODES_REQUIRED")
    eps=[_episode(x) for x in episodes]
    ids=[x["episode_id"] for x in eps]
    if len(set(ids))!=len(ids):
        raise ExecutableSkillProgramError("EPISODE_ID_DUPLICATE")
    skeletons={_skeleton(x["steps"]) for x in eps}
    if len(skeletons)!=1:
        raise ExecutableSkillProgramError("NO_COMMON_EXECUTABLE_PROGRAM_SKELETON")

    common_pre=set(eps[0]["preconditions"])
    common_post=set(eps[0]["postconditions"])
    all_invalid=set()
    for e in eps[1:]:
        common_pre &= set(e["preconditions"])
        common_post &= set(e["postconditions"])
    for e in eps:
        all_invalid |= set(e["invalidators"])
    steps=eps[0]["steps"]
    digest=candidate_digest(
        source_episode_ids=ids,steps=steps,
        preconditions=sorted(common_pre),postconditions=sorted(common_post),
        invalidators=sorted(all_invalid)
    )
    return {
        "schema":SCHEMA,
        "status":"EXECUTABLE_SKILL_CANDIDATE_ONLY",
        "source_episode_ids":sorted(ids),
        "source_episode_receipts":sorted(x["verification_receipt"] for x in eps),
        "source_scopes":sorted({x["scope_id"] for x in eps}),
        "steps":steps,
        "preconditions":sorted(common_pre),
        "postconditions":sorted(common_post),
        "invalidators":sorted(all_invalid),
        "candidate_sha256":digest,
        "verified_skill":False,
        "reuse_authorized":False,
        "candidate_only":True,
        "acceptance_credit_delta":0,
        "ownership_credit_delta":0,
        "promotion_authority":False,
    }

def verify_candidate(*,candidate:Mapping[str,Any],verification_receipt:Mapping[str,Any])->dict[str,Any]:
    ids=sorted(_s(x) for x in candidate.get("source_episode_ids",[]) if _s(x))
    steps=normalize_steps(candidate.get("steps"))
    pre=_items(candidate.get("preconditions")); post=_items(candidate.get("postconditions")); invalid=_items(candidate.get("invalidators"))
    expected=candidate_digest(
        source_episode_ids=ids,steps=steps,preconditions=pre,postconditions=post,invalidators=invalid
    )
    if candidate.get("candidate_sha256")!=expected:
        raise ExecutableSkillProgramError("CANDIDATE_DIGEST_INVALID")
    r=verification_receipt
    if r.get("independent_verified") is not True or r.get("exact_byte_bound") is not True or r.get("conclusion")!="success":
        raise ExecutableSkillProgramError("CANDIDATE_VERIFICATION_RECEIPT_INVALID")
    if r.get("candidate_sha256")!=expected:
        raise ExecutableSkillProgramError("CANDIDATE_RECEIPT_DIGEST_MISMATCH")
    if sorted(_s(x) for x in r.get("source_episode_ids",[]) if _s(x))!=ids:
        raise ExecutableSkillProgramError("CANDIDATE_RECEIPT_SOURCE_MISMATCH")
    if r.get("behavior_preserving_on_claimed_scope") is not True:
        raise ExecutableSkillProgramError("CANDIDATE_BEHAVIOR_PRESERVATION_NOT_PROVED")
    relation=_s(r.get("scope_relation"))
    if relation not in RELATIONS:
        raise ExecutableSkillProgramError("CANDIDATE_SCOPE_RELATION_NOT_ADMISSIBLE")
    rid=_s(r.get("receipt_id"))
    if not rid:
        raise ExecutableSkillProgramError("CANDIDATE_RECEIPT_ID_REQUIRED")
    return {
        **dict(candidate),
        "status":"VERIFIED_EXECUTABLE_SKILL",
        "verified_skill":True,
        "reuse_authorized":True,
        "candidate_only":False,
        "scope_relation":relation,
        "verification_receipt":rid,
        "acceptance_credit_delta":0,
        "family_credit_delta":0,
        "capability_credit_delta":0,
        "ownership_credit_delta":0,
        "promotion_authority":False,
        "execution_authority":False,
    }
