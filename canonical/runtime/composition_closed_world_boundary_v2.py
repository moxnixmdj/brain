"""Closed-world composition boundary theorem/certificate verifier V2.

Breakthrough: do not attempt to enumerate every mutable filesystem, process, browser,
or in-memory channel inside a composition role. Instead, execute each macrostep in an
ephemeral confinement domain that is destroyed before the next role. The only
cross-role exits are:

1. a content-addressed composition state capsule; and
2. a proof-carrying effect broker bound to the current capsule head.

If confinement, capsule mediation, broker carrier enforcement, rollback, and frozen
acceptance-scope coverage are independently and scope-completely proved, ambient
internal state cannot be a parallel cross-role channel. This module verifies only the
certificate logic. It does not manufacture the required system receipts.
"""
from __future__ import annotations

import hashlib
import pathlib
import re
from collections.abc import Mapping
from typing import Any

SCHEMA = "PROJECT_BRAIN_COMPOSITION_CLOSED_WORLD_BOUNDARY_CERTIFICATE_V2"
BLOB_RE = re.compile(r"^[0-9a-f]{40,64}$")


class BoundaryError(ValueError):
    pass


def _token(value: Any, label: str, *, max_len: int = 1024) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value) > max_len
        or "\x00" in value
    ):
        raise BoundaryError(label + "_INVALID")
    return value.strip()


def _receipt(
    value: Any,
    label: str,
    required_true: tuple[str, ...],
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise BoundaryError(label + "_INVALID")
    path = _token(value.get("path"), label + "_PATH")
    blob = _token(value.get("git_blob_sha"), label + "_BLOB", max_len=64)
    if not BLOB_RE.fullmatch(blob):
        raise BoundaryError(label + "_BLOB_INVALID")
    normalized: dict[str, Any] = {
        "path": path,
        "git_blob_sha": blob,
    }
    for field in required_true:
        if value.get(field) is not True:
            raise BoundaryError(label + "_" + field.upper() + "_NOT_TRUE")
        normalized[field] = True
    if set(value) != set(normalized):
        raise BoundaryError(label + "_UNBOUND_FIELDS")
    return normalized


def verify_closed_world_boundary(cert: Mapping[str, Any]) -> dict[str, Any]:
    """Verify sufficiency premises for C1 closed-world capsule mediation totality."""
    try:
        if not isinstance(cert, Mapping):
            raise BoundaryError("CERT_NOT_OBJECT")
        if cert.get("schema") != SCHEMA:
            raise BoundaryError("SCHEMA_MISMATCH")

        frozen_scope = _receipt(
            cert.get("frozen_scope_receipt"),
            "FROZEN_SCOPE_RECEIPT",
            (
                "scope_complete_for_frozen_composition_claim",
                "independent_or_objective",
            ),
        )

        confinement = _receipt(
            cert.get("ephemeral_confinement_receipt"),
            "EPHEMERAL_CONFINEMENT_RECEIPT",
            (
                "fresh_child_domain_per_macrostep",
                "child_destroyed_before_next_macrostep",
                "no_parent_mutable_state_injection_except_declared_boundary",
                "workspace_overlay_discarded_or_exported_through_boundary",
                "process_tree_reaped_before_boundary_commit",
                "browser_profile_ephemeral_or_exported_through_boundary",
                "independent_or_objective",
                "scope_complete",
            ),
        )

        capsule = _receipt(
            cert.get("capsule_mediation_receipt"),
            "CAPSULE_MEDIATION_RECEIPT",
            (
                "all_cross_role_state_and_evidence_exports_content_bound",
                "all_later_role_state_reads_projected_from_capsule",
                "capsule_head_checked_on_resume",
                "no_raw_prior_result_channel",
                "independent_or_objective",
                "scope_complete",
            ),
        )

        broker = _receipt(
            cert.get("effect_broker_carrier_receipt"),
            "EFFECT_BROKER_CARRIER_RECEIPT",
            (
                "all_external_information_reads_are_content_bound_or_brokered",
                "all_external_mutations_are_brokered",
                "all_host_persistent_effects_are_brokered",
                "grant_bound_to_exact_capsule_head_and_request",
                "carrier_enforces_deny_by_default",
                "receipt_bytes_verified_before_allow",
                "independent_or_objective",
                "scope_complete",
            ),
        )

        rollback = _receipt(
            cert.get("rollback_receipt"),
            "ROLLBACK_RECEIPT",
            (
                "rollback_restores_exact_capsule_prefix",
                "rollback_discards_current_child_domain",
                "rollback_leaves_no_unbrokered_persistent_effect",
                "resume_requires_revalidated_capsule_head",
                "independent_or_objective",
                "scope_complete",
            ),
        )

        boundary = cert.get("allowed_cross_macrostep_channels")
        if boundary != [
            "COMPOSITION_STATE_CAPSULE_V2_OR_STRONGER",
            "PROOF_CARRYING_EFFECT_BROKER",
        ]:
            raise BoundaryError("ALLOWED_CHANNEL_SET_NOT_EXACT_TWO_CHANNEL_CUT")

        forbidden = cert.get("forbidden_parallel_channels")
        required_forbidden = {
            "RAW_PRIOR_STEP_RESULT_INJECTION",
            "SHARED_MUTABLE_WORKSPACE_OUTSIDE_BROKER",
            "PERSISTENT_CHILD_PROCESS_STATE",
            "PERSISTENT_BROWSER_PROFILE_OUTSIDE_BOUNDARY",
            "UNBROKERED_NETWORK_OR_EXTERNAL_MUTATION",
            "UNCONTENT_ADDRESSED_EXTERNAL_INFORMATION_INPUT",
        }
        if not isinstance(forbidden, list) or set(forbidden) != required_forbidden:
            raise BoundaryError("FORBIDDEN_PARALLEL_CHANNEL_SET_DRIFT")

        return {
            "schema": SCHEMA,
            "status": "PASS",
            "c1_closed_world_capsule_mediation_totality": True,
            "theorem": (
                "FRESH_EPHEMERAL_MACROSTEP_DOMAINS_PLUS_EXACT_TWO_CHANNEL_EGRESS_"
                "WITH_SCOPE_COMPLETE_CAPSULE_AND_BROKER_ENFORCEMENT_PLUS_EXACT_"
                "ROLLBACK_IMPLIES_NO_PARALLEL_LOAD_BEARING_CROSS_ROLE_CHANNEL"
            ),
            "frozen_scope_receipt": frozen_scope,
            "ephemeral_confinement_receipt": confinement,
            "capsule_mediation_receipt": capsule,
            "effect_broker_carrier_receipt": broker,
            "rollback_receipt": rollback,
            "allowed_cross_macrostep_channels": list(boundary),
            "ambient_internal_channel_enumeration_required": False,
            "reason": (
                "INTERNAL_AMBIENT_STATE_IS_NOT_CROSS_ROLE_STATE_WHEN_ITS_DOMAIN_"
                "IS_DESTROYED_BEFORE_THE_NEXT_MACROSTEP_AND_ONLY_TWO_VERIFIED_"
                "BOUNDARY_EXITS_EXIST"
            ),
            "acceptance_credit_delta": 0,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "c1_closed_world_capsule_mediation_totality": False,
            "reason": type(exc).__name__ + ":" + str(exc),
            "acceptance_credit_delta": 0,
        }


RECEIPT_KEYS = (
    "frozen_scope_receipt",
    "ephemeral_confinement_receipt",
    "capsule_mediation_receipt",
    "effect_broker_carrier_receipt",
    "rollback_receipt",
)

def _repo_blob(root: pathlib.Path, relpath: str, declared: str) -> str:
    rel = pathlib.PurePosixPath(_token(relpath, "RECEIPT_PATH"))
    if rel.is_absolute() or any(part in {"", ".", ".."} for part in rel.parts):
        raise BoundaryError("RECEIPT_PATH_NOT_CANONICAL_RELATIVE")
    root = root.resolve(strict=True)
    cursor = root
    for part in rel.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise BoundaryError("RECEIPT_PATH_SYMLINK_REJECTED")
    try:
        target = cursor.resolve(strict=True)
        target.relative_to(root)
    except (OSError, RuntimeError, ValueError) as exc:
        raise BoundaryError("RECEIPT_PATH_OUTSIDE_ROOT") from exc
    if not target.is_file():
        raise BoundaryError("RECEIPT_PATH_NOT_FILE")
    raw = target.read_bytes()
    payload = b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    if len(declared) == 40:
        actual = hashlib.sha1(payload).hexdigest()
    elif len(declared) == 64:
        actual = hashlib.sha256(payload).hexdigest()
    else:
        raise BoundaryError("RECEIPT_BLOB_LENGTH_UNSUPPORTED")
    if actual != declared:
        raise BoundaryError("RECEIPT_GIT_BLOB_MISMATCH:" + rel.as_posix())
    return actual

def verify_repository_bound_closed_world_boundary(
    cert: Mapping[str, Any],
    repo_root: str | pathlib.Path,
) -> dict[str, Any]:
    base = verify_closed_world_boundary(cert)
    if base.get("status") != "PASS":
        return base
    try:
        root = pathlib.Path(repo_root)
        bindings = []
        for key in RECEIPT_KEYS:
            rec = base[key]
            actual = _repo_blob(root, rec["path"], rec["git_blob_sha"])
            bindings.append({
                "receipt": key,
                "path": rec["path"],
                "git_blob_sha": actual,
            })
        return {
            **base,
            "repository_bindings_status": "PASS",
            "verified_receipt_bindings": bindings,
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "c1_closed_world_capsule_mediation_totality": False,
            "reason": type(exc).__name__ + ":" + str(exc),
            "acceptance_credit_delta": 0,
        }
