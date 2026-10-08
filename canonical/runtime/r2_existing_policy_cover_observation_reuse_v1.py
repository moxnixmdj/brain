"""Deterministic reuse-first discovery for authenticated R2 policy-cover observations.

This module never invents observation truth. It only discovers already-present,
content-addressed observation receipt + independent verification pairs for the
exact requested (state_id, discriminator_id), rejects conflicting authenticated
outcomes, and returns one binding for downstream reauthentication by the live
policy-cover executor.
"""
from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import observable_policy_cover_executor_v1 as cover

SCHEMA="PROJECT_BRAIN_R2_EXISTING_POLICY_COVER_OBSERVATION_REUSE_V1"
ROOT=Path(__file__).resolve().parents[2]
_MAX_JSON_BYTES=2*1024*1024
_MAX_FILES=20000


def _git_blob_sha(path: Path) -> str:
    data=path.read_bytes()
    return sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()


def _base(status: str, *, passed: bool=False, **extra: Any) -> dict[str,Any]:
    return {
        "schema":SCHEMA,
        "status":status,
        "pass":passed,
        "reuse_authority":False,
        "semantic_truth_authority":False,
        "policy_adequacy_authority":False,
        "goal_satisfaction_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        "incremental_spend_usd":0,
        **extra,
    }


def _safe_json_files(base: Path, relative_root: str) -> list[Path]:
    root=(base/relative_root).resolve(strict=False)
    if not root.is_dir():
        return []
    out=[]
    for path in sorted(root.rglob("*.json")):
        if len(out)>=_MAX_FILES:
            break
        try:
            if path.is_symlink() or not path.is_file():
                continue
            resolved=path.resolve(strict=True)
            if not resolved.is_relative_to(root):
                continue
            if path.stat().st_size>_MAX_JSON_BYTES:
                continue
        except (OSError,RuntimeError):
            continue
        out.append(path)
    return out


def _load_object(path: Path) -> dict[str,Any] | None:
    try:
        value=json.loads(path.read_text(encoding="utf-8"))
    except (OSError,UnicodeError,json.JSONDecodeError):
        return None
    return value if isinstance(value,dict) else None


def _relative(base: Path, path: Path) -> str:
    return path.resolve(strict=True).relative_to(base.resolve(strict=True)).as_posix()


def discover(
    observation_request: Mapping[str,Any],
    *,
    repo_root: str | Path | None=None,
) -> dict[str,Any]:
    try:
        if not isinstance(observation_request,Mapping):
            return _base("FAIL_CLOSED",reason="OBSERVATION_REQUEST_NOT_OBJECT")
        if observation_request.get("schema")!="PROJECT_BRAIN_POLICY_COVER_OBSERVATION_REQUEST_V1":
            return _base("NOT_APPLICABLE__OBSERVATION_REQUEST_SCHEMA_UNMODELED")
        state_id=observation_request.get("state_id")
        discriminator_id=observation_request.get("discriminator_id")
        if not isinstance(state_id,str) or not state_id:
            return _base("FAIL_CLOSED",reason="STATE_ID_REQUIRED")
        if not isinstance(discriminator_id,str) or not discriminator_id:
            return _base("FAIL_CLOSED",reason="DISCRIMINATOR_ID_REQUIRED")

        root=Path(repo_root) if repo_root is not None else ROOT
        root=root.resolve(strict=True)

        receipts=[]
        for path in (
            _safe_json_files(root,"canonical/governance")
            + _safe_json_files(root,"canonical/verification")
        ):
            doc=_load_object(path)
            if not isinstance(doc,Mapping) or doc.get("schema")!=cover.OBSERVATION_SCHEMA:
                continue
            if doc.get("state_id")!=state_id or doc.get("discriminator_id")!=discriminator_id:
                continue
            if "outcome" not in doc:
                continue
            if any(doc.get(field) is not True for field in (
                "observation_proved","truth_preserving","safe_observation","precommitment"
            )):
                continue
            receipts.append((path,_git_blob_sha(path),doc))

        if not receipts:
            return _base(
                "UNRESOLVED__NO_EXISTING_AUTHENTICATED_OBSERVATION_RECEIPT",
                state_id=state_id,
                discriminator_id=discriminator_id,
            )

        subject_blobs={blob for _,blob,_ in receipts}
        verifications=[]
        for path in _safe_json_files(root,"canonical/verification"):
            doc=_load_object(path)
            if not isinstance(doc,Mapping) or doc.get("schema")!=cover.OBSERVATION_VERIFY_SCHEMA:
                continue
            if doc.get("subject_git_blob_sha") not in subject_blobs:
                continue
            if doc.get("state_id")!=state_id or doc.get("discriminator_id")!=discriminator_id:
                continue
            if any(doc.get(field) is not True for field in (
                "pass","independent_verified","observation_semantics_verified","precommitment_verified"
            )):
                continue
            verifier_id=doc.get("independent_verifier_id")
            if not isinstance(verifier_id,str) or not verifier_id.strip():
                continue
            verifications.append((path,_git_blob_sha(path),doc))

        valid=[]
        for receipt_path,receipt_blob,receipt in receipts:
            outcome_sha=cover._digest(receipt["outcome"])
            for verify_path,verify_blob,verify in verifications:
                if verify.get("subject_git_blob_sha")!=receipt_blob:
                    continue
                if verify.get("outcome_sha256")!=outcome_sha:
                    continue
                binding={
                    "receipt":{
                        "path":_relative(root,receipt_path),
                        "git_blob_sha":receipt_blob,
                    },
                    "verification":{
                        "path":_relative(root,verify_path),
                        "git_blob_sha":verify_blob,
                    },
                }
                auth=cover._authenticate_observation(
                    binding,
                    state_id=state_id,
                    discriminator_id=discriminator_id,
                    repo_root=root,
                )
                if auth.get("pass") is True:
                    valid.append((binding,auth))

        if not valid:
            return _base(
                "UNRESOLVED__NO_EXISTING_AUTHENTICATED_OBSERVATION_BINDING",
                state_id=state_id,
                discriminator_id=discriminator_id,
            )

        outcomes={row[1].get("outcome_sha256") for row in valid}
        if len(outcomes)!=1:
            return _base(
                "FAIL_CLOSED",
                reason="CONFLICTING_AUTHENTICATED_OBSERVATION_OUTCOMES",
                state_id=state_id,
                discriminator_id=discriminator_id,
                outcome_sha256s=sorted(str(x) for x in outcomes),
            )

        valid.sort(key=lambda row:(
            row[0]["receipt"]["path"],
            row[0]["verification"]["path"],
        ))
        binding,auth=valid[0]
        return _base(
            "PASS__EXISTING_AUTHENTICATED_POLICY_COVER_OBSERVATION_REUSED",
            passed=True,
            state_id=state_id,
            discriminator_id=discriminator_id,
            observation_binding=binding,
            outcome_sha256=auth.get("outcome_sha256"),
            downstream_reauthentication_required=True,
            evidence_trace=[{
                "receipt_path":binding["receipt"]["path"],
                "receipt_git_blob_sha":binding["receipt"]["git_blob_sha"],
                "verification_path":binding["verification"]["path"],
                "verification_git_blob_sha":binding["verification"]["git_blob_sha"],
                "independent_verifier_id":auth.get("independent_verifier_id"),
            }],
        )
    except Exception as exc:
        return _base("FAIL_CLOSED",reason=type(exc).__name__+":"+str(exc))
