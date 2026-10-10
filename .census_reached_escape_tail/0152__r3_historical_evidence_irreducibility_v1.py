"""Bounded irreducibility certificate for unreplayable historical R3 successes.

This module proves only a current-evidence statement: for one exact retained
historical success, the durable R3 state contains neither a replay capsule nor a
proof capsule. Under the already-proved R3 observability theorem, that exact
historical episode cannot be independently reconstructed or promoted from the
currently retained evidence alone.

It does NOT prove that future evidence can never arrive, that the original task
can never be performed again, or that arbitrary external reality is unknowable.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_R3_HISTORICAL_EVIDENCE_IRREDUCIBILITY_V1"
THEOREM_PATH = (
    "canonical/verification/"
    "R3_OBSERVABILITY_BOUNDARY_THEOREM_20261008_V1.json"
)
SUPPORTED_KIND = "ADAPT_SUCCESS_TO_VERIFIABLE_EPISODE"


class HistoricalEvidenceCertificateError(ValueError):
    pass


def _learning_module():
    from canonical.runtime import autonomous_verified_self_improvement_v1 as learning
    return learning


def _sha_bytes(raw: bytes) -> str:
    return sha256(raw).hexdigest()


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "reason": reason,
        "irreducible_current_evidence_requirement_proved": False,
        "future_evidence_reopens": True,
        "terminal_authority": False,
        **extra,
    }


def certify(
    work_id: str,
    *,
    state_path: str | Path,
    repo_root: str | Path,
) -> dict[str, Any]:
    learning = _learning_module()

    wid = str(work_id or "").strip()
    if not wid:
        return _fail("WORK_ID_REQUIRED")

    try:
        root = Path(repo_root).resolve(strict=True)
        state_file = Path(state_path).resolve(strict=True)
        try:
            state_file.relative_to(root)
        except ValueError:
            return _fail("STATE_PATH_OUTSIDE_REPOSITORY")
        if not state_file.is_file() or state_file.is_symlink():
            return _fail("STATE_FILE_INVALID")

        theorem_file = (root / THEOREM_PATH).resolve(strict=True)
        theorem_file.relative_to(root)
        theorem_raw = theorem_file.read_bytes()
        theorem = json.loads(theorem_raw.decode("utf-8"))
        if (
            not isinstance(theorem, Mapping)
            or theorem.get("theorem")
            != "SOUND_POST_HOC_LEARNING_REQUIRES_EFFECT_DISTINGUISHING_EVIDENCE"
        ):
            return _fail("OBSERVABILITY_THEOREM_AUTHORITY_INVALID")

        state_raw = state_file.read_bytes()
        state = learning.load_state(state_file)
        queue = state.get("improvement_queue", {})
        observations = state.get("observations", {})
        work = queue.get(wid) if isinstance(queue, Mapping) else None
        if not isinstance(work, Mapping):
            return _fail("WORK_NOT_FOUND")
        if work.get("kind") != SUPPORTED_KIND:
            return _fail("WORK_KIND_NOT_SUPPORTED")
        if work.get("status") not in {"PENDING", "PARKED"}:
            return _fail("WORK_NOT_CURRENTLY_UNRESOLVED")

        payload = work.get("payload")
        if not isinstance(payload, Mapping):
            return _fail("WORK_PAYLOAD_INVALID")
        oid = str(payload.get("observation_id") or "").strip()
        if not oid:
            return _fail("OBSERVATION_ID_MISSING")
        observation = observations.get(oid) if isinstance(observations, Mapping) else None
        if not isinstance(observation, Mapping):
            return _fail("OBSERVATION_NOT_FOUND")
        if observation.get("observation_id") != oid:
            return _fail("OBSERVATION_ID_MISMATCH")

        conditions = {
            "payload_replayable_false": payload.get("replayable") is False,
            "payload_proof_available_false": payload.get("proof_available") is False,
            "payload_replay_sha_absent": not bool(payload.get("replay_capsule_sha256")),
            "payload_proof_sha_absent": not bool(payload.get("proof_capsule_sha256")),
            "observation_replay_sha_absent": not bool(observation.get("replay_capsule_sha256")),
            "observation_proof_sha_absent": not bool(observation.get("proof_capsule_sha256")),
            "observation_replay_capsule_absent": not isinstance(
                observation.get("replay_capsule"), Mapping
            ),
            "observation_proof_capsule_absent": not isinstance(
                observation.get("proof_capsule"), Mapping
            ),
        }
        if not all(conditions.values()):
            return _fail(
                "CURRENT_RETAINED_EVIDENCE_NOT_PROVED_ABSENT",
                conditions=conditions,
            )

        witness = {
            "work_id": wid,
            "observation_id": oid,
            "observation_output_sha256": observation.get("output_sha256"),
            "state_sha256": _sha_bytes(state_raw),
            "theorem_path": THEOREM_PATH,
            "theorem_sha256": _sha_bytes(theorem_raw),
            "conditions": conditions,
        }
        witness_sha = sha256(
            json.dumps(
                witness,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ).encode("utf-8")
        ).hexdigest()
        return {
            "schema": SCHEMA,
            "status": (
                "PASS__EXACT_HISTORICAL_SUCCESS_UNRECONSTRUCTIBLE_FROM_"
                "CURRENT_RETAINED_EVIDENCE"
            ),
            "pass": True,
            "claim_scope": "EXACT_HISTORICAL_OBSERVATION_CURRENT_RETAINED_EVIDENCE_ONLY",
            "work_id": wid,
            "observation_id": oid,
            "witness_sha256": witness_sha,
            "witness": witness,
            "irreducible_current_evidence_requirement_proved": True,
            "required_new_information_class": (
                "NEW_INDEPENDENT_EVIDENCE_OR_NEW_REPLAYABLE_EXPERIENCE"
            ),
            "future_evidence_reopens": True,
            "permanent_nonlearnability_claimed": False,
            "global_external_information_absence_claimed": False,
            "execution_authority": False,
            "promotion_authority": False,
            "terminal_authority": False,
        }
    except Exception as exc:
        return _fail(
            "CERTIFICATE_EXCEPTION:" + type(exc).__name__ + ":" + str(exc)
        )


def certify_pending_set(
    pending: list[Mapping[str, Any]],
    *,
    state_path: str | Path,
    repo_root: str | Path,
) -> dict[str, Any]:
    """Certify a residual only when every pending row is this exact bounded case."""
    if not isinstance(pending, list) or not pending:
        return _fail("PENDING_SET_EMPTY_OR_INVALID")

    certificates: list[dict[str, Any]] = []
    for row in pending:
        if not isinstance(row, Mapping):
            return _fail("PENDING_ROW_INVALID")
        if row.get("kind") != SUPPORTED_KIND:
            return _fail(
                "PENDING_SET_CONTAINS_UNSUPPORTED_KIND",
                unsupported_kind=row.get("kind"),
            )
        cert = certify(
            str(row.get("work_id") or ""),
            state_path=state_path,
            repo_root=repo_root,
        )
        if cert.get("pass") is not True:
            return _fail(
                "PENDING_SET_MEMBER_NOT_CERTIFIED",
                failed_work_id=row.get("work_id"),
                member_certificate=cert,
            )
        certificates.append(cert)

    return {
        "schema": SCHEMA,
        "status": "PASS__ALL_PENDING_WORK_CERTIFIED_HISTORICAL_EVIDENCE_BOUNDARY",
        "pass": True,
        "certificate_count": len(certificates),
        "certificates": certificates,
        "irreducible_current_evidence_requirement_proved": True,
        "required_new_information_class": (
            "NEW_INDEPENDENT_EVIDENCE_OR_NEW_REPLAYABLE_EXPERIENCE"
        ),
        "future_evidence_reopens": True,
        "permanent_nonlearnability_claimed": False,
        "global_external_information_absence_claimed": False,
        "execution_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
    }
