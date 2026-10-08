"""Fail-closed recovery for a quarantined generalized R3 skill."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import autonomous_verified_self_improvement_v1 as learning
from canonical.runtime.executable_skill_verification_authenticator_v1 import (
    authenticate_and_verify as authenticate_skill_verification,
)

SCHEMA = "PROJECT_BRAIN_R3_QUARANTINE_RECOVERY_V1"


class QuarantineRecoveryError(ValueError):
    pass


def recover_exact_scope(
    work: Mapping[str, Any],
    *,
    state_path: str | Path,
    repo_root: str | Path,
    skill_verification_provider,
) -> dict[str, Any]:
    payload = work.get("payload")
    if not isinstance(payload, Mapping):
        raise QuarantineRecoveryError("RECOVERY_PAYLOAD_INVALID")
    if payload.get("scope_contraction_safe") is not True:
        return {
            "schema": SCHEMA,
            "status": "RECOVERY_REQUIRES_NEW_CANDIDATE",
            "pass": False,
            "work_id": work.get("work_id"),
            "terminal_authority": False,
        }

    skill_id = str(payload.get("skill_id") or "").strip()
    state = learning.load_state(state_path)
    record = state.get("skills", {}).get(skill_id)
    raw_skill = record.get("skill") if isinstance(record, Mapping) else None
    if not skill_id or not isinstance(raw_skill, Mapping):
        raise QuarantineRecoveryError("RECOVERY_SKILL_MISSING")

    candidate = learning._candidate_from_verified_skill(raw_skill)
    source_scopes = sorted(
        str(x).strip()
        for x in raw_skill.get("source_scopes", [])
        if isinstance(x, str) and str(x).strip()
    )
    binding = skill_verification_provider({
        "kind": "SKILL_SCOPE_CONTRACTION_VERIFICATION",
        "candidate": deepcopy(dict(candidate)),
        "improvement_work_id": work.get("work_id"),
        "requested_scope_relation": "EXACT",
        "requested_scope_predicate": None,
        "source_scopes": source_scopes,
    })
    if not isinstance(binding, Mapping):
        return {
            "schema": SCHEMA,
            "status": "RECOVERY_VERIFIER_BINDING_UNAVAILABLE",
            "pass": False,
            "work_id": work.get("work_id"),
            "terminal_authority": False,
        }

    auth = authenticate_skill_verification(candidate, binding, repo_root=repo_root)
    if auth.get("pass") is not True:
        return {
            "schema": SCHEMA,
            "status": "RECOVERY_VERIFICATION_FAILED",
            "pass": False,
            "work_id": work.get("work_id"),
            "verification_error": auth.get("reason"),
            "terminal_authority": False,
        }

    verified = auth.get("verified_skill")
    if not isinstance(verified, Mapping):
        raise QuarantineRecoveryError("RECOVERY_VERIFIED_SKILL_MISSING")
    verified_scopes = sorted(
        str(x).strip()
        for x in verified.get("source_scopes", [])
        if isinstance(x, str) and str(x).strip()
    )
    if (
        str(verified.get("scope_relation") or "") != "EXACT"
        or str(verified.get("scope_predicate") or "").strip()
        or verified_scopes != source_scopes
    ):
        return {
            "schema": SCHEMA,
            "status": "RECOVERY_NOT_EXACT_SOURCE_SCOPE",
            "pass": False,
            "work_id": work.get("work_id"),
            "terminal_authority": False,
        }

    integrated = learning.integrate_solver_output(
        {
            "pass": True,
            "status": "SOLVED__VERIFIED_EXECUTABLE_SKILL_READY",
            "skill_candidate": deepcopy(dict(candidate)),
            "verified_executable_skill": deepcopy(dict(verified)),
            "verified_skill_reuse_authorized": True,
        },
        state_path=state_path,
    )
    ok = integrated.get("active_skill_id") == skill_id
    return {
        "schema": SCHEMA,
        "status": (
            "RECOVERED_BY_EXACT_SCOPE_CONTRACTION"
            if ok
            else "RECOVERY_NOT_REACTIVATED"
        ),
        "pass": ok,
        "work_id": work.get("work_id"),
        "learning": integrated,
        "terminal_authority": False,
    }
