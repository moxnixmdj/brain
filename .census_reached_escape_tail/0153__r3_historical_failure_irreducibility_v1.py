"""Bounded current-state insufficiency certificate for historical R3 failures.

This certifier is intentionally narrow. It proves only that one exact historical
failure-repair item cannot be replayed or causally localized from the current
durable R3 state because the state retained only a generic many-to-one diagnosis
and retained no retry capsule or task/replay identity.

This is NOT an information-theoretic externality proof. A new replayable
experiment, search result, alternative route, or regenerated task context may
reopen the repair. The certificate therefore authorizes acquisition/experiment
work, never terminal "external impossibility" classification.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_R3_HISTORICAL_FAILURE_IRREDUCIBILITY_V1"
SUPPORTED_KIND = "REPAIR_FAILURE_CLASS"
SUPPORTED_REPAIR_CLASS = "LOCALIZE_CAUSAL_FAILURE_AND_GENERATE_MINIMAL_REPAIR"
IDENTITY_KEYS = frozenset({
    "task_id", "goal", "problem", "request", "retry_context",
    "execution_problem", "source_mode", "source_request",
})


def _learning_module():
    from canonical.runtime import autonomous_verified_self_improvement_v1 as learning
    return learning


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
        default=str,
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return sha256(_canon(value)).hexdigest()


def _items(value: Any) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return sorted({" ".join(str(x or "").split()) for x in value if str(x or "").strip()})


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "reason": reason,
        "irreducible_external_information_proved": False,
        "information_theoretic_externality_proved": False,
        "current_durable_state_insufficiency_proved": False,
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
        state_file.relative_to(root)
        if not state_file.is_file() or state_file.is_symlink():
            return _fail("STATE_FILE_INVALID")

        state_raw = state_file.read_bytes()
        state = learning.load_state(state_file)
        queue = state.get("improvement_queue", {})
        failures = state.get("failures", {})
        work = queue.get(wid) if isinstance(queue, Mapping) else None
        if not isinstance(work, Mapping):
            return _fail("WORK_NOT_FOUND")
        if work.get("kind") != SUPPORTED_KIND:
            return _fail("WORK_KIND_NOT_SUPPORTED")
        if work.get("status") not in {"PENDING", "PARKED"}:
            return _fail("WORK_NOT_CURRENTLY_UNRESOLVED")

        payload = work.get("payload")
        identity = work.get("identity")
        if not isinstance(payload, Mapping) or not isinstance(identity, Mapping):
            return _fail("WORK_PAYLOAD_OR_IDENTITY_INVALID")
        fid = str(payload.get("failure_fingerprint") or "").strip()
        if not fid or identity.get("failure_fingerprint") != fid:
            return _fail("FAILURE_FINGERPRINT_BINDING_INVALID")
        failure = failures.get(fid) if isinstance(failures, Mapping) else None
        if not isinstance(failure, Mapping):
            return _fail("FAILURE_RECORD_NOT_FOUND")
        if failure.get("failure_fingerprint") != fid:
            return _fail("FAILURE_RECORD_FINGERPRINT_MISMATCH")

        core = {
            "status": failure.get("status"),
            "reason": failure.get("reason"),
            "next_required_edge": failure.get("next_required_edge"),
            "repair_class": failure.get("repair_class"),
            "falsified_capability_ids": _items(failure.get("falsified_capability_ids")),
            "deferred_capability_ids": _items(failure.get("deferred_capability_ids")),
            "counterexamples": deepcopy(list(failure.get("counterexamples") or [])),
            "attempts": deepcopy(list(failure.get("attempts") or [])),
        }
        if _sha(core) != fid:
            return _fail("FAILURE_FINGERPRINT_NOT_EXACT_CORE_HASH")

        retry_capsules = failure.get("retry_capsules")
        repair_receipts = failure.get("repair_receipts")
        conditions = {
            "work_retry_capsule_absent": not bool(payload.get("retry_capsule_sha256")),
            "identity_retry_capsule_absent": not bool(identity.get("retry_capsule_sha256")),
            "failure_last_retry_capsule_absent": not bool(failure.get("last_retry_capsule_sha256")),
            "failure_retry_capsules_empty": isinstance(retry_capsules, Mapping) and not bool(retry_capsules),
            "failure_reason_absent": failure.get("reason") in {None, ""},
            "failure_next_edge_absent": failure.get("next_required_edge") in {None, ""},
            "failure_attempts_empty": isinstance(failure.get("attempts"), list) and not failure.get("attempts"),
            "failure_counterexamples_empty": isinstance(failure.get("counterexamples"), list) and not failure.get("counterexamples"),
            "failure_falsified_caps_empty": isinstance(failure.get("falsified_capability_ids"), list) and not failure.get("falsified_capability_ids"),
            "failure_deferred_caps_empty": isinstance(failure.get("deferred_capability_ids"), list) and not failure.get("deferred_capability_ids"),
            "repair_receipts_empty": isinstance(repair_receipts, Mapping) and not bool(repair_receipts),
            "generic_localization_class_only": failure.get("repair_class") == SUPPORTED_REPAIR_CLASS,
            "generic_fail_closed_status_only": failure.get("status") == "FAIL_CLOSED",
            "work_identity_has_no_task_context": not any(k in identity for k in IDENTITY_KEYS),
            "work_payload_has_no_task_context": not any(k in payload for k in IDENTITY_KEYS),
            "failure_record_has_no_task_context": not any(k in failure for k in IDENTITY_KEYS),
        }
        if not all(conditions.values()):
            return _fail(
                "RETAINED_FAILURE_EVIDENCE_NOT_STRICTLY_UNREPLAYABLE_GENERIC_CASE",
                conditions=conditions,
            )

        witness = {
            "work_id": wid,
            "failure_fingerprint": fid,
            "state_sha256": sha256(state_raw).hexdigest(),
            "failure_core_sha256": _sha(core),
            "retained_failure_core": core,
            "conditions": conditions,
            "missing_information": (
                "EXACT_ORIGINAL_RETRY_CONTEXT_OR_NEW_REPLAYABLE_FAILURE_EXPERIENCE"
            ),
        }
        return {
            "schema": SCHEMA,
            "status": (
                "PASS__EXACT_HISTORICAL_FAILURE_REQUIRES_REPLAY_INFORMATION_OR_NEW_EXPERIENCE"
            ),
            "pass": True,
            "claim_scope": (
                "EXACT_HISTORICAL_FAILURE_CURRENT_DURABLE_R3_STATE_ONLY"
            ),
            "work_id": wid,
            "failure_fingerprint": fid,
            "witness_sha256": _sha(witness),
            "witness": witness,
            "irreducible_external_information_proved": False,
            "information_theoretic_externality_proved": False,
            "current_durable_state_insufficiency_proved": True,
            "classification": "PENDING_ACQUISITION_OR_EXPERIMENT",
            "global_alternative_routes_exhausted": False,
            "irreducibility_basis": (
                "CURRENT_DURABLE_STATE_RETAINS_ONLY_GENERIC_MANY_TO_ONE_FAILURE_"
                "DIAGNOSIS_AND_NO_REPLAY_OR_TASK_IDENTITY"
            ),
            "required_new_information_class": (
                "EXACT_ORIGINAL_RETRY_CONTEXT_OR_NEW_REPLAYABLE_FAILURE_EXPERIENCE"
            ),
            "future_evidence_reopens": True,
            "permanent_nonrepairability_claimed": False,
            "global_external_information_absence_claimed": False,
            "execution_authority": False,
            "promotion_authority": False,
            "terminal_authority": False,
        }
    except Exception as exc:
        return _fail("CERTIFICATE_EXCEPTION:" + type(exc).__name__ + ":" + str(exc))


def certify_pending_set(
    pending: list[Mapping[str, Any]],
    *,
    state_path: str | Path,
    repo_root: str | Path,
) -> dict[str, Any]:
    if not isinstance(pending, list) or not pending:
        return _fail("PENDING_SET_EMPTY_OR_INVALID")
    certs: list[dict[str, Any]] = []
    for row in pending:
        if not isinstance(row, Mapping) or row.get("kind") != SUPPORTED_KIND:
            return _fail(
                "PENDING_SET_CONTAINS_UNSUPPORTED_KIND",
                unsupported_kind=(row.get("kind") if isinstance(row, Mapping) else None),
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
        certs.append(cert)
    return {
        "schema": SCHEMA,
        "status": "PASS__ALL_PENDING_FAILURE_WORK_REQUIRES_REPLAY_INFORMATION_OR_NEW_EXPERIENCE",
        "pass": True,
        "certificate_count": len(certs),
        "certificates": certs,
        "irreducible_external_information_proved": False,
        "information_theoretic_externality_proved": False,
        "current_durable_state_insufficiency_proved": True,
        "classification": "PENDING_ACQUISITION_OR_EXPERIMENT",
        "global_alternative_routes_exhausted": False,
        "claim_scope": "EXACT_CURRENT_PENDING_HISTORICAL_FAILURE_SET",
        "required_new_information_class": (
            "EXACT_ORIGINAL_RETRY_CONTEXT_OR_NEW_REPLAYABLE_FAILURE_EXPERIENCE"
        ),
        "future_evidence_reopens": True,
        "permanent_nonrepairability_claimed": False,
        "terminal_authority": False,
    }
