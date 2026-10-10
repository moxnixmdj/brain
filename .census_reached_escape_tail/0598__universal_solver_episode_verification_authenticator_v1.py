"""Content-addressed authentication for universal-solver episode verification.

An episode may become learning evidence only when a repository receipt and a
separate independent-verification receipt bind the exact:
- problem digest,
- episode/scope ids,
- executable program digest,
- execution trace digest,
- fact/value capsule heads.

If the trace contains effect outcomes, the independent verifier must explicitly
attest that those outcomes were reverified. This module converts the authenticated
pair into the narrow legacy receipt shape required by executable_skill_program_v7;
callers cannot mint that shape directly with authority.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime.effect_broker_receipt_resolver_v2 import (
    ReceiptResolutionError,
    resolve_receipt_bytes,
)
from canonical.runtime import universal_verified_adaptive_solver_v1 as v1

SCHEMA = "PROJECT_BRAIN_UNIVERSAL_SOLVER_EPISODE_VERIFICATION_AUTHENTICATOR_V1"
RECEIPT_SCHEMA = "PROJECT_BRAIN_UNIVERSAL_SOLVER_EPISODE_VERIFICATION_V1"
VERIFY_SCHEMA = "PROJECT_BRAIN_UNIVERSAL_SOLVER_EPISODE_INDEPENDENT_VERIFICATION_V1"


class EpisodeVerificationError(ValueError):
    pass


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return sha256(_canon(value)).hexdigest()


def _effectful(trace: Sequence[Mapping[str, Any]]) -> bool:
    return any(
        isinstance(row, Mapping) and bool(row.get("effect_outcome_sha256"))
        for row in trace
    )


def authenticate(
    binding: Mapping[str, Any],
    *,
    problem: Mapping[str, Any],
    episode: Mapping[str, Any],
    trace: Sequence[Mapping[str, Any]],
    fact_capsule_head_hash: str,
    value_capsule_head_hash: str,
    repo_root: str | Path,
) -> dict[str, Any]:
    try:
        if not isinstance(binding, Mapping):
            raise EpisodeVerificationError("EPISODE_VERIFICATION_BINDING_INVALID")
        if not isinstance(problem, Mapping):
            raise EpisodeVerificationError("PROBLEM_INVALID")
        if not isinstance(episode, Mapping):
            raise EpisodeVerificationError("EPISODE_INVALID")
        if not isinstance(trace, Sequence) or isinstance(trace, (str, bytes)):
            raise EpisodeVerificationError("TRACE_INVALID")
        if not isinstance(fact_capsule_head_hash, str) or len(fact_capsule_head_hash) != 64:
            raise EpisodeVerificationError("FACT_CAPSULE_HEAD_INVALID")
        if not isinstance(value_capsule_head_hash, str) or len(value_capsule_head_hash) != 64:
            raise EpisodeVerificationError("VALUE_CAPSULE_HEAD_INVALID")

        rr = resolve_receipt_bytes(binding.get("receipt"), repo_root=repo_root)
        vr = resolve_receipt_bytes(binding.get("verification"), repo_root=repo_root)
        rd = rr["document"]
        vd = vr["document"]

        if rd.get("schema") != RECEIPT_SCHEMA:
            raise EpisodeVerificationError("EPISODE_RECEIPT_SCHEMA_INVALID")
        if vd.get("schema") != VERIFY_SCHEMA:
            raise EpisodeVerificationError("EPISODE_VERIFY_SCHEMA_INVALID")
        if vd.get("subject_git_blob_sha") != rr["git_blob_sha"]:
            raise EpisodeVerificationError("EPISODE_VERIFY_SUBJECT_MISMATCH")

        expected = {
            "problem_sha256": v1._digest(problem),
            "episode_id": episode.get("episode_id"),
            "scope_id": episode.get("scope_id"),
            "program_sha256": episode.get("program_sha256"),
            "trace_sha256": _sha(list(trace)),
            "fact_capsule_head_hash": fact_capsule_head_hash,
            "value_capsule_head_hash": value_capsule_head_hash,
        }
        for key, value in expected.items():
            if rd.get(key) != value:
                raise EpisodeVerificationError("EPISODE_RECEIPT_BINDING_MISMATCH:" + key)
            if vd.get(key) != value:
                raise EpisodeVerificationError("EPISODE_VERIFY_BINDING_MISMATCH:" + key)

        required_receipt = {
            "pass": True,
            "conclusion": "success",
            "behavior_verified": True,
            "exact_byte_bound": True,
        }
        for key, value in required_receipt.items():
            if rd.get(key) != value:
                raise EpisodeVerificationError("EPISODE_RECEIPT_CLAIM_INVALID:" + key)

        required_verify = {
            "pass": True,
            "independent_verified": True,
            "behavior_verified": True,
            "exact_byte_bound": True,
            "trace_reverified": True,
            "state_lineage_reverified": True,
        }
        for key, value in required_verify.items():
            if vd.get(key) != value:
                raise EpisodeVerificationError("EPISODE_VERIFY_CLAIM_INVALID:" + key)
        if _effectful(trace) and vd.get("effect_outcomes_reverified") is not True:
            raise EpisodeVerificationError("EPISODE_EFFECT_OUTCOMES_NOT_REVERIFIED")

        verifier_id = vd.get("independent_verifier_id")
        if not isinstance(verifier_id, str) or not verifier_id.strip():
            raise EpisodeVerificationError("EPISODE_INDEPENDENT_VERIFIER_ID_MISSING")

        legacy_receipt = {
            "independent_verified": True,
            "exact_byte_bound": True,
            "conclusion": "success",
            "behavior_verified": True,
            "episode_id": expected["episode_id"],
            "scope_id": expected["scope_id"],
            "program_sha256": expected["program_sha256"],
            "receipt_id": "EPVR:" + rr["git_blob_sha"],
        }
        authenticated_episode = {
            "episode_id": expected["episode_id"],
            "scope_id": expected["scope_id"],
            "steps": list(episode.get("steps") or []),
            "preconditions": list(episode.get("preconditions") or []),
            "postconditions": list(episode.get("postconditions") or []),
            "invalidators": list(episode.get("invalidators") or []),
            "program_sha256": expected["program_sha256"],
            "verification_receipt": legacy_receipt,
            "verification_binding": {
                "receipt": {"path": rr["path"], "git_blob_sha": rr["git_blob_sha"]},
                "verification": {"path": vr["path"], "git_blob_sha": vr["git_blob_sha"]},
            },
            "problem_sha256": expected["problem_sha256"],
            "trace_sha256": expected["trace_sha256"],
            "fact_capsule_head_hash": fact_capsule_head_hash,
            "value_capsule_head_hash": value_capsule_head_hash,
        }
        return {
            "schema": SCHEMA,
            "status": "PASS__AUTHENTICATED_INDEPENDENT_EPISODE_VERIFICATION",
            "pass": True,
            "authenticated_episode": authenticated_episode,
            "legacy_receipt": legacy_receipt,
            "receipt": authenticated_episode["verification_binding"]["receipt"],
            "verification": authenticated_episode["verification_binding"]["verification"],
            "independent_verifier_id": verifier_id.strip(),
            "effect_outcomes_reverified": bool(vd.get("effect_outcomes_reverified")),
            "terminal_authority": False,
        }
    except (Exception, ReceiptResolutionError) as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "reason": type(exc).__name__ + ":" + str(exc),
            "terminal_authority": False,
        }


def reauthenticate_record(
    record: Mapping[str, Any],
    *,
    repo_root: str | Path,
) -> dict[str, Any]:
    """Reauthenticate a previously exported authenticated episode record.

    This does not rerun the historical episode. It proves that the record's
    content-addressed receipt pair still exists unchanged and that both receipts
    bind the record's exact episode identity/program/trace/state heads.
    """
    try:
        if not isinstance(record, Mapping):
            raise EpisodeVerificationError("EPISODE_RECORD_INVALID")
        binding = record.get("verification_binding")
        if not isinstance(binding, Mapping):
            raise EpisodeVerificationError("EPISODE_RECORD_BINDING_MISSING")
        rr = resolve_receipt_bytes(binding.get("receipt"), repo_root=repo_root)
        vr = resolve_receipt_bytes(binding.get("verification"), repo_root=repo_root)
        rd, vd = rr["document"], vr["document"]
        if rd.get("schema") != RECEIPT_SCHEMA or vd.get("schema") != VERIFY_SCHEMA:
            raise EpisodeVerificationError("EPISODE_RECORD_SCHEMA_INVALID")
        if vd.get("subject_git_blob_sha") != rr["git_blob_sha"]:
            raise EpisodeVerificationError("EPISODE_RECORD_VERIFY_SUBJECT_MISMATCH")

        expected = {
            "problem_sha256": record.get("problem_sha256"),
            "episode_id": record.get("episode_id"),
            "scope_id": record.get("scope_id"),
            "program_sha256": record.get("program_sha256"),
            "trace_sha256": record.get("trace_sha256"),
            "fact_capsule_head_hash": record.get("fact_capsule_head_hash"),
            "value_capsule_head_hash": record.get("value_capsule_head_hash"),
        }
        if any(not isinstance(v, str) or not v for v in expected.values()):
            raise EpisodeVerificationError("EPISODE_RECORD_BINDING_FIELDS_INVALID")
        for key, value in expected.items():
            if rd.get(key) != value or vd.get(key) != value:
                raise EpisodeVerificationError("EPISODE_RECORD_BINDING_MISMATCH:" + key)
        for key in ("pass", "independent_verified", "behavior_verified", "exact_byte_bound"):
            if vd.get(key) is not True:
                raise EpisodeVerificationError("EPISODE_RECORD_VERIFY_CLAIM_INVALID:" + key)
        if vd.get("trace_reverified") is not True or vd.get("state_lineage_reverified") is not True:
            raise EpisodeVerificationError("EPISODE_RECORD_REVERIFICATION_INCOMPLETE")

        legacy = record.get("verification_receipt")
        expected_legacy = {
            "independent_verified": True,
            "exact_byte_bound": True,
            "conclusion": "success",
            "behavior_verified": True,
            "episode_id": record.get("episode_id"),
            "scope_id": record.get("scope_id"),
            "program_sha256": record.get("program_sha256"),
            "receipt_id": "EPVR:" + rr["git_blob_sha"],
        }
        if legacy != expected_legacy:
            raise EpisodeVerificationError("EPISODE_RECORD_LEGACY_RECEIPT_MISMATCH")

        return {
            "schema": SCHEMA,
            "status": "PASS__PRIOR_EPISODE_RECORD_REAUTHENTICATED",
            "pass": True,
            "authenticated_episode": dict(record),
            "terminal_authority": False,
        }
    except (Exception, ReceiptResolutionError) as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "reason": type(exc).__name__ + ":" + str(exc),
            "terminal_authority": False,
        }
