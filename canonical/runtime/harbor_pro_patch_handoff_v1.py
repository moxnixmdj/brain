"""Store a Pro replay *candidate* patch; this is not a capture or verifier.

The caller is responsible for safe, quiescent capture and authenticated base
identity. Both base values and the checksum passed here are just supplied
claims. Equality and SHA-256 protect byte transport only; they do not prove
where a patch came from, its completeness, or whether it applies. No caller is
allowed to treat this helper as container or benchmark admission.
"""
from __future__ import annotations

import hashlib
import hmac
import os
from pathlib import Path
import re
import tempfile
from typing import Any

_COMMIT = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")
MAX_PATCH_BYTES = 20_000_000


class PatchHandoffError(ValueError):
    """Candidate patch is invalid or cannot be safely published."""


def store_candidate_patch(*, agent_log_dir: Path, patch: bytes,
                          expected_base: str, reported_base: str,
                          expected_sha256: str) -> dict[str, Any]:
    """Publish once as ``<trial>/agent/model.patch`` for Pro replay.

    Only use with a host-owned, trusted agent log directory; never point it
    into a task-controlled mount. Existing output is not overwritten. The bytes
    are re-hashed from a temporary file before atomic no-overwrite publication.
    No task process, Git command, solver, or verifier is run by this function.
    """
    if (not isinstance(expected_base, str) or not _COMMIT.fullmatch(expected_base)
            or not isinstance(reported_base, str) or not _COMMIT.fullmatch(reported_base)):
        raise PatchHandoffError("BASE_FORMAT_INVALID")
    if not hmac.compare_digest(expected_base, reported_base):
        raise PatchHandoffError("REPORTED_BASE_MISMATCH")
    if not isinstance(patch, bytes) or len(patch) > MAX_PATCH_BYTES:
        raise PatchHandoffError("PATCH_BYTES_INVALID")
    if patch and not patch.startswith(b"diff --git "):
        raise PatchHandoffError("PATCH_FORMAT_INVALID")
    if not isinstance(expected_sha256, str) or not _DIGEST.fullmatch(expected_sha256):
        raise PatchHandoffError("SHA256_FORMAT_INVALID")
    if not hmac.compare_digest(hashlib.sha256(patch).hexdigest(), expected_sha256):
        raise PatchHandoffError("PATCH_SHA256_MISMATCH")
    directory = Path(agent_log_dir)
    if directory.is_symlink() or not directory.is_dir():
        raise PatchHandoffError("TRUSTED_AGENT_LOG_DIR_REQUIRED")
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="w+b", prefix=".model-patch-", dir=directory,
                                         delete=False) as output:
            temporary = output.name
            output.write(patch)
            output.flush()
            os.fsync(output.fileno())
            output.seek(0)
            if not hmac.compare_digest(hashlib.sha256(output.read()).hexdigest(), expected_sha256):
                raise PatchHandoffError("STORED_PATCH_SHA256_MISMATCH")
        # Hard-link publication is atomic and refuses any preexisting path,
        # including a symlink. Temporary file and target share the filesystem.
        os.link(temporary, directory / "model.patch", follow_symlinks=False)
    except FileExistsError as exc:
        raise PatchHandoffError("MODEL_PATCH_ALREADY_EXISTS") from exc
    except OSError as exc:
        raise PatchHandoffError("PATCH_PUBLICATION_FAILED") from exc
    finally:
        if temporary is not None:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
    return {
        "status": "CANDIDATE_BYTES_STORED__NOT_VERIFIED",
        "patch_path": str(directory / "model.patch"),
        "patch_sha256": expected_sha256,
        "patch_size": len(patch),
        "reported_base_matches_expected": True,
        "base_commit_verified": False,
        "worker_quiescence_verified": False,
        "patch_completeness_verified": False,
        "external_verifier_invoked": False,
        "execution_authorized": False,
    }
