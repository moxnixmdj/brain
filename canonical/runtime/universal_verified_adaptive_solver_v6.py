"""Universal Verified Adaptive Solver V6: pinned effect-semantics trust root.

V5 authenticates continuation state and V4 validates the internal consistency of
verifier-success -> effect bindings. Neither authenticates that the document which
claims "independent_verified" was admitted by an immutable trust authority rather
than authored inside caller-selected repo_root.

V6 preserves V5 unchanged and adds one preflight:
- load a fixed trust-root manifest at a fixed path;
- require its exact Git blob SHA to match the runtime pin;
- require every capability's effect-semantics verification blob SHA to be listed;
- only then delegate to V5.

Content addressing proves identity. The pinned trust root supplies authority.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime.effect_broker_receipt_resolver_v2 import (
    ReceiptResolutionError,
    resolve_receipt_bytes,
)
from canonical.runtime import universal_verified_adaptive_solver_v5 as v5

SCHEMA = "PROJECT_BRAIN_UNIVERSAL_VERIFIED_ADAPTIVE_SOLVER_V6"
TRUST_ROOT_REL = "canonical/governance/UNIVERSAL_SOLVER_EFFECT_SEMANTICS_TRUST_ROOT_V1.json"
TRUST_ROOT_BLOB_SHA = "14fac3d35be101b8c05a19af912623838d59c6ce"
TRUST_ROOT_SCHEMA = "PROJECT_BRAIN_UNIVERSAL_SOLVER_EFFECT_SEMANTICS_TRUST_ROOT_V1"


class UniversalSolverV6Error(ValueError):
    pass


def _git_blob_sha(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "reason": reason,
        "terminal_authority": False,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
    }
    if detail:
        out["detail"] = detail
    return out


def _load_trust_root(repo_root: str | Path) -> set[str]:
    path = Path(repo_root) / TRUST_ROOT_REL
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise UniversalSolverV6Error(
            "EFFECT_SEMANTICS_TRUST_ROOT_UNREADABLE:" + type(exc).__name__
        ) from exc

    actual = _git_blob_sha(raw)
    if actual != TRUST_ROOT_BLOB_SHA:
        raise UniversalSolverV6Error(
            "EFFECT_SEMANTICS_TRUST_ROOT_BLOB_MISMATCH:"
            + actual
            + ":expected:"
            + TRUST_ROOT_BLOB_SHA
        )

    try:
        doc = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise UniversalSolverV6Error(
            "EFFECT_SEMANTICS_TRUST_ROOT_JSON_INVALID:" + type(exc).__name__
        ) from exc

    if not isinstance(doc, Mapping) or doc.get("schema") != TRUST_ROOT_SCHEMA:
        raise UniversalSolverV6Error("EFFECT_SEMANTICS_TRUST_ROOT_SCHEMA_INVALID")

    values = doc.get("trusted_effect_semantics_verification_blobs")
    if not isinstance(values, list):
        raise UniversalSolverV6Error("EFFECT_SEMANTICS_TRUST_LIST_INVALID")

    trusted: set[str] = set()
    for value in values:
        if (
            not isinstance(value, str)
            or len(value) != 40
            or any(c not in "0123456789abcdef" for c in value.lower())
        ):
            raise UniversalSolverV6Error("EFFECT_SEMANTICS_TRUST_BLOB_INVALID")
        trusted.add(value.lower())
    if len(trusted) != len(values):
        raise UniversalSolverV6Error("EFFECT_SEMANTICS_TRUST_BLOB_DUPLICATE")
    return trusted


def _preflight(
    problem: Mapping[str, Any],
    *,
    repo_root: str | Path,
) -> dict[str, Any]:
    trusted = _load_trust_root(repo_root)
    caps = problem.get("capabilities")
    if not isinstance(caps, list) or not caps:
        raise UniversalSolverV6Error("CAPABILITIES_REQUIRED")

    admitted: list[dict[str, str]] = []
    for index, cap in enumerate(caps):
        if not isinstance(cap, Mapping):
            raise UniversalSolverV6Error("CAPABILITY_NOT_OBJECT:" + str(index))
        cid = cap.get("id")
        if not isinstance(cid, str) or not cid:
            raise UniversalSolverV6Error("CAPABILITY_ID_INVALID:" + str(index))
        pair = cap.get("effect_semantics_binding")
        if not isinstance(pair, Mapping):
            raise UniversalSolverV6Error("EFFECT_SEMANTICS_BINDING_REQUIRED:" + cid)
        try:
            verification = resolve_receipt_bytes(
                pair.get("verification"),
                repo_root=repo_root,
            )
        except ReceiptResolutionError as exc:
            raise UniversalSolverV6Error(
                "EFFECT_SEMANTICS_VERIFICATION_RESOLUTION_FAILED:"
                + cid
                + ":"
                + str(exc)
            ) from exc

        verification_sha = str(verification.get("git_blob_sha") or "").lower()
        if verification_sha not in trusted:
            raise UniversalSolverV6Error(
                "UNTRUSTED_EFFECT_SEMANTICS_VERIFICATION_BLOB:"
                + cid
                + ":"
                + verification_sha
            )
        admitted.append(
            {
                "capability_id": cid,
                "verification_git_blob_sha": verification_sha,
            }
        )

    return {
        "trust_root_git_blob_sha": TRUST_ROOT_BLOB_SHA,
        "trusted_verification_blob_count": len(trusted),
        "admitted_capabilities": admitted,
    }


def run(
    problem: Mapping[str, Any],
    *,
    proposal_packets: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
    repo_root: str | Path,
    effect_root: str | Path | None = None,
    resume_state: Mapping[str, Any] | None = None,
    episode_id: str = "episode",
    scope_id: str = "scope",
    episode_verification_receipt: Mapping[str, Any] | None = None,
    prior_verified_episodes: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    try:
        if not isinstance(problem, Mapping):
            return _fail("PROBLEM_NOT_OBJECT")
        trust = _preflight(problem, repo_root=repo_root)
    except Exception as exc:
        return _fail(type(exc).__name__ + ":" + str(exc))

    out = v5.run(
        problem,
        proposal_packets=proposal_packets,
        repo_root=repo_root,
        effect_root=effect_root,
        resume_state=resume_state,
        episode_id=episode_id,
        scope_id=scope_id,
        episode_verification_receipt=episode_verification_receipt,
        prior_verified_episodes=prior_verified_episodes,
    )
    result = dict(out)
    result["schema"] = SCHEMA
    result["effect_semantics_trust_root"] = trust
    result["terminal_authority"] = False
    return result
