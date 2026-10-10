"""Candidate-only firewall for R3 success-adapter source patches.

This module validates an externally authored unified diff against an exact,
content-addressed source snapshot. It never applies a patch and grants no
execution, verification, promotion, acceptance, or terminal authority.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence
import re

SCHEMA = "PROJECT_BRAIN_R3_SUCCESS_ADAPTER_PATCH_FIREWALL_V1"

MUTABLE_ADAPTER_PATHS = (
    "canonical/runtime/r3_bound_success_adapter_v1.py",
    "canonical/runtime/r3_raw_success_adapter_v1.py",
)
IMMUTABLE_AUTHORITY_PATHS = (
    "canonical/runtime/r3_independent_learning_verifier_v1.py",
    "canonical/runtime/r3_bound_success_checkpoint_verifier_v1.py",
    "canonical/runtime/r3_raw_success_checkpoint_verifier_v1.py",
)
FORBIDDEN_METADATA_PREFIXES = (
    "rename from ",
    "rename to ",
    "copy from ",
    "copy to ",
    "deleted file mode ",
    "new file mode ",
    "old mode ",
    "new mode ",
    "similarity index ",
    "dissimilarity index ",
    "GIT binary patch",
    "Binary files ",
)
DIFF_HEADER = re.compile(r"^diff --git a/(\S+) b/(\S+)$")
OLD_HEADER = re.compile(r"^--- a/(\S+)$")
NEW_HEADER = re.compile(r"^\+\+\+ b/(\S+)$")
HUNK_HEADER = re.compile(r"^@@ -\d+(?:,\d+)? \+\d+(?:,\d+)? @@(?: .*)?$")


class PatchFirewallError(ValueError):
    pass


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "reason": reason,
        "candidate_only": True,
        "patch_application_authority": False,
        "source_write_authority": False,
        "verification_authority": False,
        "promotion_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def _safe_rel(raw: str) -> str:
    value = str(raw or "").strip().replace("\\", "/")
    path = PurePosixPath(value)
    if (
        not value
        or path.is_absolute()
        or ".." in path.parts
        or "." in path.parts
        or value.startswith("/")
    ):
        raise PatchFirewallError("PATCH_PATH_INVALID:" + value)
    return path.as_posix()


def _source_sha256(root: Path, relative: str) -> str:
    target = (root / relative).resolve(strict=True)
    target.relative_to(root)
    if not target.is_file() or target.is_symlink():
        raise PatchFirewallError("SOURCE_FILE_INVALID:" + relative)
    return sha256(target.read_bytes()).hexdigest()


def _validate_base_bindings(
    touched_paths: Sequence[str],
    supplied: Mapping[str, Any],
    *,
    repo_root: str | Path,
) -> dict[str, str]:
    root = Path(repo_root).resolve(strict=True)
    out: dict[str, str] = {}
    if set(supplied) != set(touched_paths):
        raise PatchFirewallError("BASE_BINDING_PATH_SET_MISMATCH")
    for path in touched_paths:
        expected = str(supplied.get(path) or "").strip().lower()
        if len(expected) != 64 or any(ch not in "0123456789abcdef" for ch in expected):
            raise PatchFirewallError("BASE_SHA256_INVALID:" + path)
        observed = _source_sha256(root, path)
        if observed != expected:
            raise PatchFirewallError("BASE_SOURCE_DRIFT:" + path)
        out[path] = observed
    return out


def _parse_patch(text: str) -> tuple[list[str], int]:
    if not isinstance(text, str):
        raise PatchFirewallError("PATCH_TEXT_INVALID")
    raw = text.replace("\r\n", "\n")
    if not raw.strip():
        raise PatchFirewallError("PATCH_EMPTY")
    encoded = raw.encode("utf-8")
    if len(encoded) > 131072:
        raise PatchFirewallError("PATCH_TOO_LARGE")

    lines = raw.splitlines()
    touched: list[str] = []
    hunk_count = 0
    current: str | None = None
    saw_old = False
    saw_new = False
    saw_hunk = False

    for line in lines:
        if any(line.startswith(prefix) for prefix in FORBIDDEN_METADATA_PREFIXES):
            raise PatchFirewallError("FORBIDDEN_PATCH_METADATA:" + line[:80])

        match = DIFF_HEADER.match(line)
        if match:
            if current is not None and not (saw_old and saw_new and saw_hunk):
                raise PatchFirewallError("INCOMPLETE_FILE_PATCH:" + current)
            left = _safe_rel(match.group(1))
            right = _safe_rel(match.group(2))
            if left != right:
                raise PatchFirewallError("PATCH_PATH_MISMATCH")
            if left not in MUTABLE_ADAPTER_PATHS:
                raise PatchFirewallError("PATCH_PATH_NOT_ADMITTED:" + left)
            if left in IMMUTABLE_AUTHORITY_PATHS:
                raise PatchFirewallError("VERIFICATION_AUTHORITY_PATH_FORBIDDEN:" + left)
            if left in touched:
                raise PatchFirewallError("DUPLICATE_FILE_PATCH:" + left)
            touched.append(left)
            current = left
            saw_old = saw_new = saw_hunk = False
            continue

        if line.startswith("--- "):
            if current is None:
                raise PatchFirewallError("OLD_HEADER_WITHOUT_DIFF")
            match = OLD_HEADER.match(line)
            if not match or _safe_rel(match.group(1)) != current:
                raise PatchFirewallError("OLD_HEADER_PATH_MISMATCH:" + current)
            saw_old = True
            continue

        if line.startswith("+++ "):
            if current is None:
                raise PatchFirewallError("NEW_HEADER_WITHOUT_DIFF")
            match = NEW_HEADER.match(line)
            if not match or _safe_rel(match.group(1)) != current:
                raise PatchFirewallError("NEW_HEADER_PATH_MISMATCH:" + current)
            saw_new = True
            continue

        if line.startswith("@@"):
            if current is None or not saw_old or not saw_new:
                raise PatchFirewallError("HUNK_WITHOUT_FILE_HEADERS")
            if not HUNK_HEADER.match(line):
                raise PatchFirewallError("HUNK_HEADER_INVALID")
            hunk_count += 1
            if hunk_count > 64:
                raise PatchFirewallError("PATCH_HUNK_LIMIT_EXCEEDED")
            saw_hunk = True
            continue

        if current is None:
            if line.startswith(("index ", "From ", "Subject:", "Date:")) or not line.strip():
                continue
            raise PatchFirewallError("UNEXPECTED_PATCH_PREAMBLE")

        if not saw_hunk:
            if line.startswith("index ") or not line.strip():
                continue
            raise PatchFirewallError("CONTENT_BEFORE_HUNK:" + current)

        if line.startswith(("+", "-", " ", "\\")):
            continue
        if not line.strip():
            # Empty context/add/remove lines are represented by a prefix. A truly
            # blank line outside a hunk body is harmless between hunks.
            continue
        raise PatchFirewallError("PATCH_LINE_INVALID:" + current)

    if current is None or not touched:
        raise PatchFirewallError("NO_FILE_PATCH_FOUND")
    if not (saw_old and saw_new and saw_hunk):
        raise PatchFirewallError("INCOMPLETE_FILE_PATCH:" + current)
    return touched, hunk_count


def evaluate(request: Mapping[str, Any], *, repo_root: str | Path) -> dict[str, Any]:
    try:
        if not isinstance(request, Mapping):
            return _fail("REQUEST_NOT_OBJECT")
        patch_text = request.get("patch_text")
        base = request.get("base_sha256_by_path")
        if not isinstance(base, Mapping):
            return _fail("BASE_BINDINGS_REQUIRED")

        touched, hunk_count = _parse_patch(patch_text)
        observed = _validate_base_bindings(
            touched,
            base,
            repo_root=repo_root,
        )
        patch_sha = sha256(str(patch_text).replace("\r\n", "\n").encode("utf-8")).hexdigest()

        return {
            "schema": SCHEMA,
            "status": "PASS__CANDIDATE_PATCH_SCOPE_AND_BASE_BINDINGS_VALID",
            "pass": True,
            "candidate_only": True,
            "touched_paths": touched,
            "base_sha256_by_path": observed,
            "patch_sha256": patch_sha,
            "hunk_count": hunk_count,
            "mutable_scope": list(MUTABLE_ADAPTER_PATHS),
            "immutable_authority_scope": list(IMMUTABLE_AUTHORITY_PATHS),
            "patch_application_authority": False,
            "source_write_authority": False,
            "verification_authority": False,
            "promotion_authority": False,
            "acceptance_authority": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
    except Exception as exc:
        return _fail(type(exc).__name__ + ":" + str(exc))
