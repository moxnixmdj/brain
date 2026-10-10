"""Finite professional candidate-branch basis for the final V6 subject.

This is a bounded generator basis, not a global candidate-completeness claim.
It derives candidate *plan branches* from the exact content-addressed professional
execution profile already included in the final V6 subject:
  - preserve the incumbent;
  - one focus branch per declared execution step;
  - one focus branch per declared escalation trigger.

Downstream search/evaluation must still independently establish adequacy.
"""
from __future__ import annotations

from hashlib import sha1, sha256
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_R2_CANDIDATE_BRANCH_BASIS_V1"
PROFILE_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_P1_EXECUTION_PROFILE_V3"
PROFILE_PATH = "canonical/governance/PROFESSIONAL_QUALITY_P1_EXECUTION_PROFILE_20261010_V3.json"
PROFILE_BLOB = "f7e89eafbb691c16d1bdf5b8d295a468d5e3bec5"
SUBJECT_ID = "PROFESSIONAL_QUALITY_P1_V6_DEPENDENCY_CLOSED_AUTHENTICATED_TARGET_SYSTEM_20261010_V5"
SUBJECT_SHA256 = "353978ba4866d1e35794390968a14500ee1d8a4f0bddfb8f081e9a1a71ba468d"

def _canon(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",",":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("NON_CANONICAL_JSON_VALUE") from exc

def _sha256(value: Any) -> str:
    return sha256(_canon(value)).hexdigest()

def _git_blob(path: Path) -> str:
    data=path.read_bytes()
    return sha1(b"blob "+str(len(data)).encode("ascii")+b"\0"+data).hexdigest()

def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
        "candidate_generation_authority":False,"candidate_scope_complete":False,
        "global_candidate_search_complete":False,"quality_authority":False,
        "acceptance_authority":False,"promotion_authority":False,
        "terminal_authority":False,"terminal_credit_delta":0,**extra,
    }

def _load_profile(root: Path) -> dict[str, Any] | None:
    p=(root/PROFILE_PATH).resolve()
    try:
        p.relative_to(root.resolve())
    except ValueError:
        return None
    if not p.is_file() or p.is_symlink() or _git_blob(p)!=PROFILE_BLOB:
        return None
    try:
        doc=json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
    return doc if isinstance(doc,dict) else None

def generate(
    *,
    target_instance: Mapping[str, Any],
    incumbent: Mapping[str, Any],
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    if not isinstance(target_instance, Mapping) or not target_instance:
        return _fail("TARGET_INSTANCE_REQUIRED")
    if not isinstance(incumbent, Mapping) or not incumbent:
        return _fail("INCUMBENT_REQUIRED")
    root=Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
    profile=_load_profile(root)
    if profile is None:
        return _fail("PINNED_EXECUTION_PROFILE_UNAVAILABLE")
    if profile.get("schema")!=PROFILE_SCHEMA or profile.get("behavior_id")!="PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001":
        return _fail("PINNED_EXECUTION_PROFILE_IDENTITY_INVALID")
    steps=profile.get("steps")
    triggers=profile.get("escalation_triggers")
    if not isinstance(steps,list) or not steps or not all(isinstance(x,str) and x.strip() for x in steps):
        return _fail("PROFILE_STEPS_INVALID")
    if len(set(steps))!=len(steps):
        return _fail("PROFILE_STEPS_NOT_UNIQUE")
    if not isinstance(triggers,list) or not triggers or not all(isinstance(x,str) and x.strip() for x in triggers):
        return _fail("PROFILE_ESCALATION_TRIGGERS_INVALID")
    if len(set(triggers))!=len(triggers):
        return _fail("PROFILE_ESCALATION_TRIGGERS_NOT_UNIQUE")

    try:
        target_sha=_sha256(dict(target_instance))
        incumbent_sha=_sha256(dict(incumbent))
    except ValueError as exc:
        return _fail(str(exc))

    descriptors=[{"kind":"PRESERVE_INCUMBENT"}]
    descriptors += [{"kind":"FOCUS_EXECUTION_STEP","step":step,"step_index":i} for i,step in enumerate(steps)]
    descriptors += [{"kind":"ADDRESS_ESCALATION_TRIGGER","trigger":trigger,"trigger_index":i} for i,trigger in enumerate(triggers)]

    candidates=[]
    seen=set()
    for ordinal,descriptor in enumerate(descriptors):
        identity={
            "subject_id":SUBJECT_ID,
            "subject_sha256":SUBJECT_SHA256,
            "profile_git_blob_sha":PROFILE_BLOB,
            "target_sha256":target_sha,
            "incumbent_sha256":incumbent_sha,
            "operator":descriptor,
        }
        cid="pq-r2:"+_sha256(identity)
        if cid in seen:
            return _fail("CANDIDATE_ID_COLLISION")
        seen.add(cid)
        candidates.append({
            "candidate_id":cid,
            "ordinal":ordinal,
            "operator":descriptor,
            "target_sha256":target_sha,
            "incumbent_sha256":incumbent_sha,
            "incumbent_preserved":descriptor["kind"]=="PRESERVE_INCUMBENT",
            "candidate_plan_realized":False,
        })

    if sum(1 for row in candidates if row["incumbent_preserved"])!=1:
        return _fail("INCUMBENT_PRESERVATION_INVARIANT_FAILED")

    return {
        "schema":SCHEMA,
        "pass":True,
        "status":"PASS__FINITE_PROFILE_DERIVED_CANDIDATE_BRANCH_BASIS",
        "subject_kind":"DECLARED_SYSTEM",
        "subject_id":SUBJECT_ID,
        "subject_sha256":SUBJECT_SHA256,
        "profile_path":PROFILE_PATH,
        "profile_git_blob_sha":PROFILE_BLOB,
        "target_sha256":target_sha,
        "incumbent_sha256":incumbent_sha,
        "candidate_count":len(candidates),
        "execution_step_branch_count":len(steps),
        "escalation_trigger_branch_count":len(triggers),
        "incumbent_branch_count":1,
        "candidates":candidates,
        "candidate_universe_sha256":_sha256([row["candidate_id"] for row in candidates]),
        "candidate_generation_authority":True,
        "candidate_scope_complete":True,
        "candidate_scope_complete_meaning":"EXACTLY_THE_FINITE_PROFILE_DERIVED_BRANCH_BASIS_RETURNED_BY_THIS_GENERATOR_ONLY",
        "global_candidate_search_complete":False,
        "candidate_artifact_realization_complete":False,
        "policy_adequacy_inferred":False,
        "quality_authority":False,
        "acceptance_authority":False,
        "promotion_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        "incremental_spend_usd":0,
    }

def run(args: Mapping[str, Any] | None = None, root: Any = None) -> dict[str, Any]:
    args=args or {}
    return generate(
        target_instance=args.get("target_instance"),
        incumbent=args.get("incumbent"),
        repo_root=root,
    )
