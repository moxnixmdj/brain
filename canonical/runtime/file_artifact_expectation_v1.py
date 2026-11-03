"""Re-read a stated file effect instead of accepting a constant success bit.

This checks the producer's success flag *and* the on-disk digest, path binding,
and any declared source postcondition. For compressed files it also hashes the
uncompressed content. When a source was removed, its original digest is a
producer claim: the check cannot independently recover the deleted preimage.
This is code-independent from the producing adapters, not independent-personnel
verification or a general proof of semantic correctness.
"""
from __future__ import annotations

import gzip
import hashlib
import hmac
import pathlib
import re
import tarfile
import zlib
from collections.abc import Mapping
from typing import Any

_HEX = re.compile(r"[0-9a-f]{64}\Z")
_MAX_CONTENT = 256 * 1024 * 1024


def _path(root: pathlib.Path, value: Any) -> pathlib.Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("PATH_REQUIRED")
    path = (root / value).resolve()
    if path == root or root not in path.parents:
        raise ValueError("PATH_OUTSIDE_ROOT")
    return path


def _digest_stream(stream, limit: int | None = None) -> str:
    digest = hashlib.sha256()
    count = 0
    while True:
        block = stream.read(1024 * 1024)
        if not block:
            break
        count += len(block)
        if limit is not None and count > limit:
            raise ValueError("CONTENT_TOO_LARGE")
        digest.update(block)
    return digest.hexdigest()


def _claimed_digest(result: Mapping[str, Any], key: str) -> str:
    value = result.get(key)
    if not isinstance(value, str) or not _HEX.fullmatch(value):
        raise ValueError("DIGEST_INVALID:" + key)
    return value


def verify(expect: Mapping[str, Any], result: Mapping[str, Any],
           args: Mapping[str, Any], root: pathlib.Path | str) -> tuple[bool, str]:
    """Return a fail-closed verdict; never writes and never accepts a missing claim."""
    try:
        if not isinstance(expect, Mapping) or not isinstance(result, Mapping) or not isinstance(args, Mapping):
            raise ValueError("INVALID_CONTRACT")
        if result.get("output_verified") is not True:
            raise ValueError("PRODUCER_DID_NOT_VERIFY")
        root = pathlib.Path(root).resolve()
        field = str(expect.get("field") or "")
        path_field = str(expect.get("path_field") or "")
        path_input = str(expect.get("path_input") or "")
        suffix = expect.get("path_suffix", "")
        if not field or not path_field or not path_input or not isinstance(suffix, str):
            raise ValueError("EXPECTED_FIELDS_REQUIRED")
        raw_input = args.get(path_input)
        if not isinstance(raw_input, str) or not raw_input.strip():
            raise ValueError("STATED_INPUT_REQUIRED")
        expected_path = _path(root, raw_input + suffix)
        claimed_path = _path(root, result.get(path_field))
        if claimed_path != expected_path:
            raise ValueError("DESTINATION_DIFFERS_FROM_INPUT")
        if not expected_path.is_file():
            raise ValueError("OUTPUT_NOT_REGULAR_FILE")
        claimed = _claimed_digest(result, field)
        with expected_path.open("rb") as stream:
            actual = _digest_stream(stream)
        if not hmac.compare_digest(actual, claimed):
            raise ValueError("OUTPUT_DIGEST_MISMATCH")

        source_state = expect.get("source_state")
        if source_state is not None:
            if source_state not in ("retained", "absent"):
                raise ValueError("SOURCE_STATE_INVALID")
            source = _path(root, args.get("path"))
            source_digest = _claimed_digest(result, "source_sha256")
            if source == expected_path:
                raise ValueError("SOURCE_IS_DESTINATION")
            if source_state == "retained":
                if not source.is_file():
                    raise ValueError("SOURCE_NOT_RETAINED")
                with source.open("rb") as stream:
                    observed_source = _digest_stream(stream)
                if not hmac.compare_digest(observed_source, source_digest):
                    raise ValueError("SOURCE_DIGEST_MISMATCH")
            elif source.exists() or (root / args["path"]).is_symlink():
                raise ValueError("SOURCE_NOT_REMOVED")
            if expect.get("same_as_source") is True and not hmac.compare_digest(actual, source_digest):
                raise ValueError("OUTPUT_DIFFERS_FROM_SOURCE")
            content_kind = expect.get("content_kind")
            if content_kind == "gzip":
                with gzip.open(expected_path, "rb") as stream:
                    unpacked = _digest_stream(stream, _MAX_CONTENT)
            elif content_kind == "tar_gzip":
                # Inspect one member at a time: do not eagerly collect an
                # unbounded attacker-controlled member list into memory.
                with tarfile.open(expected_path, "r|gz") as archive:
                    member = archive.next()
                    if (member is None or member.name != source.name or not member.isfile()
                            or member.size > _MAX_CONTENT):
                        raise ValueError("ARCHIVE_MEMBERS_MISMATCH")
                    stream = archive.extractfile(member)
                    if stream is None:
                        raise ValueError("ARCHIVE_MEMBER_UNREADABLE")
                    with stream:
                        unpacked = _digest_stream(stream, _MAX_CONTENT)
                    if archive.next() is not None:
                        raise ValueError("ARCHIVE_MEMBERS_MISMATCH")
            elif content_kind is None:
                unpacked = None
            else:
                raise ValueError("CONTENT_KIND_INVALID")
            if unpacked is not None and not hmac.compare_digest(unpacked, source_digest):
                raise ValueError("ARCHIVE_CONTENT_MISMATCH")
        elif expect.get("same_as_source") is not None or expect.get("content_kind") is not None:
            raise ValueError("SOURCE_STATE_REQUIRED")
        return True, "FILE_ARTIFACT_REVERIFIED"
    except (OSError, ValueError, TypeError, tarfile.TarError, EOFError, zlib.error) as exc:
        return False, "FILE_ARTIFACT_REFUSED:" + str(exc)[:200]
