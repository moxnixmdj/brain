#!/usr/bin/env python3
"""Fail-closed protocol for the single semantic quiescent-overlay channel."""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import tempfile
from collections.abc import Mapping
from typing import Any

SCHEMA_OUTCOME = "PROJECT_BRAIN_QUIESCENT_EPISODE_OUTCOME_V1"
SCHEMA_RESPONSE = "PROJECT_BRAIN_QUIESCENT_PARENT_RESPONSE_V1"
OUTCOME_REL = pathlib.PurePosixPath(".brain/episode_outcome.json")
RESPONSES_REL = pathlib.PurePosixPath(".brain/responses")
MAX_OUTCOME_BYTES = 1_000_000
MAX_RESPONSE_BYTES = 8_000_000
KINDS = {"REQUEST", "COMPLETE", "FAIL"}
TOKEN = re.compile(r"^[A-Za-z0-9._:-]{1,256}$")
SHA = re.compile(r"^[0-9a-f]{64}$")


class EpisodeProtocolError(ValueError):
    pass


def _canon(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except Exception as exc:
        raise EpisodeProtocolError("NON_CANONICAL_JSON_VALUE") from exc


def _sha(value: Any) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()


def _token(value: Any, label: str) -> str:
    if not isinstance(value, str) or not TOKEN.fullmatch(value):
        raise EpisodeProtocolError(label + "_INVALID")
    return value


def _safe_snapshot_file(root: pathlib.Path, rel: pathlib.PurePosixPath) -> pathlib.Path:
    cursor = root
    for part in rel.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise EpisodeProtocolError("JOURNAL_PATH_SYMLINK_REJECTED")
    try:
        path = (root / pathlib.Path(*rel.parts)).resolve(strict=True)
    except FileNotFoundError as exc:
        raise EpisodeProtocolError("OUTCOME_MISSING") from exc
    if path == root or root not in path.parents:
        raise EpisodeProtocolError("OUTCOME_PATH_ESCAPE")
    if not path.is_file() or path.is_symlink():
        raise EpisodeProtocolError("OUTCOME_NOT_REGULAR_FILE")
    return path


def make_outcome(
    *,
    episode_id: str,
    sequence: int,
    kind: str,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    eid = _token(episode_id, "EPISODE_ID")
    try:
        seq = int(sequence)
    except Exception as exc:
        raise EpisodeProtocolError("SEQUENCE_INVALID") from exc
    if seq < 0 or seq > 1_000_000_000:
        raise EpisodeProtocolError("SEQUENCE_OUT_OF_RANGE")
    if kind not in KINDS:
        raise EpisodeProtocolError("KIND_INVALID")
    if not isinstance(payload, Mapping):
        raise EpisodeProtocolError("PAYLOAD_NOT_OBJECT")
    payload_obj = dict(payload)
    payload_bytes = _canon(payload_obj)
    if len(payload_bytes) > MAX_OUTCOME_BYTES:
        raise EpisodeProtocolError("PAYLOAD_TOO_LARGE")
    core = {
        "schema": SCHEMA_OUTCOME,
        "episode_id": eid,
        "sequence": seq,
        "kind": kind,
        "payload_sha256": hashlib.sha256(payload_bytes).hexdigest(),
        "payload": payload_obj,
    }
    return {**core, "outcome_sha256": _sha(core)}


def verify_outcome(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping) or value.get("schema") != SCHEMA_OUTCOME:
        raise EpisodeProtocolError("OUTCOME_SCHEMA_INVALID")
    expected = make_outcome(
        episode_id=value.get("episode_id"),
        sequence=value.get("sequence"),
        kind=value.get("kind"),
        payload=value.get("payload"),
    )
    if dict(value) != expected:
        raise EpisodeProtocolError("OUTCOME_CONTENT_OR_HASH_MISMATCH")
    return expected


def classify_snapshot(
    snapshot_root: str | pathlib.Path,
    *,
    expected_episode_id: str,
    expected_sequence: int,
) -> dict[str, Any]:
    root = pathlib.Path(snapshot_root).resolve(strict=True)
    if not root.is_dir():
        raise EpisodeProtocolError("SNAPSHOT_ROOT_NOT_DIRECTORY")
    path = _safe_snapshot_file(root, OUTCOME_REL)
    raw = path.read_bytes()
    if len(raw) > MAX_OUTCOME_BYTES:
        raise EpisodeProtocolError("OUTCOME_FILE_TOO_LARGE")
    try:
        obj = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise EpisodeProtocolError("OUTCOME_JSON_INVALID") from exc
    outcome = verify_outcome(obj)
    if outcome["episode_id"] != _token(expected_episode_id, "EXPECTED_EPISODE_ID"):
        raise EpisodeProtocolError("EPISODE_ID_MISMATCH")
    if outcome["sequence"] != int(expected_sequence):
        raise EpisodeProtocolError("SEQUENCE_MISMATCH")

    payload = outcome["payload"]
    if outcome["kind"] == "REQUEST":
        required = {"request_type", "request_id", "request"}
        if set(payload) != required:
            raise EpisodeProtocolError("REQUEST_PAYLOAD_FIELD_SET_INVALID")
        _token(payload["request_type"], "REQUEST_TYPE")
        _token(payload["request_id"], "REQUEST_ID")
        if not isinstance(payload["request"], Mapping):
            raise EpisodeProtocolError("REQUEST_BODY_NOT_OBJECT")
    elif outcome["kind"] == "COMPLETE":
        required = {"result", "declared_artifact_ids"}
        if set(payload) != required:
            raise EpisodeProtocolError("COMPLETE_PAYLOAD_FIELD_SET_INVALID")
        ids = payload["declared_artifact_ids"]
        if not isinstance(ids, list) or len(ids) != len(set(ids)):
            raise EpisodeProtocolError("DECLARED_ARTIFACT_IDS_INVALID")
        for artifact_id in ids:
            _token(artifact_id, "ARTIFACT_ID")
    else:
        required = {"error_code", "reason"}
        if set(payload) != required:
            raise EpisodeProtocolError("FAIL_PAYLOAD_FIELD_SET_INVALID")
        _token(payload["error_code"], "ERROR_CODE")
        if not isinstance(payload["reason"], str) or len(payload["reason"]) > 4096:
            raise EpisodeProtocolError("FAIL_REASON_INVALID")

    return {
        "schema": SCHEMA_OUTCOME,
        "status": "CLASSIFIED",
        "kind": outcome["kind"],
        "episode_id": outcome["episode_id"],
        "sequence": outcome["sequence"],
        "payload": payload,
        "payload_sha256": outcome["payload_sha256"],
        "outcome_sha256": outcome["outcome_sha256"],
        "semantic_channel": "PRIVATE_OVERLAY_SNAPSHOT",
        "parent_action_authorized": False,
        "acceptance_credit_delta": 0,
    }


def make_response(
    *,
    episode_id: str,
    sequence: int,
    request_id: str,
    request_outcome_sha256: str,
    response: Mapping[str, Any],
) -> dict[str, Any]:
    eid = _token(episode_id, "EPISODE_ID")
    rid = _token(request_id, "REQUEST_ID")
    if not isinstance(request_outcome_sha256, str) or not SHA.fullmatch(request_outcome_sha256):
        raise EpisodeProtocolError("REQUEST_OUTCOME_SHA256_INVALID")
    if not isinstance(response, Mapping):
        raise EpisodeProtocolError("RESPONSE_NOT_OBJECT")
    response_obj = dict(response)
    response_bytes = _canon(response_obj)
    if len(response_bytes) > MAX_RESPONSE_BYTES:
        raise EpisodeProtocolError("RESPONSE_TOO_LARGE")
    core = {
        "schema": SCHEMA_RESPONSE,
        "episode_id": eid,
        "sequence": int(sequence),
        "request_id": rid,
        "request_outcome_sha256": request_outcome_sha256,
        "response_sha256": hashlib.sha256(response_bytes).hexdigest(),
        "response": response_obj,
    }
    return {**core, "envelope_sha256": _sha(core)}


def inject_response_once(
    snapshot_root: str | pathlib.Path,
    response_envelope: Mapping[str, Any],
) -> pathlib.Path:
    root = pathlib.Path(snapshot_root).resolve(strict=True)
    expected = make_response(
        episode_id=response_envelope.get("episode_id"),
        sequence=response_envelope.get("sequence"),
        request_id=response_envelope.get("request_id"),
        request_outcome_sha256=response_envelope.get("request_outcome_sha256"),
        response=response_envelope.get("response"),
    )
    if dict(response_envelope) != expected:
        raise EpisodeProtocolError("RESPONSE_CONTENT_OR_HASH_MISMATCH")

    response_dir = root / pathlib.Path(*RESPONSES_REL.parts)
    response_dir.mkdir(parents=True, exist_ok=True)
    if response_dir.is_symlink():
        raise EpisodeProtocolError("RESPONSE_DIR_SYMLINK_REJECTED")
    target = response_dir / (expected["request_id"] + ".json")
    if target.exists() or target.is_symlink():
        raise EpisodeProtocolError("RESPONSE_ALREADY_EXISTS")

    raw = _canon(expected)
    fd, tmp = tempfile.mkstemp(prefix=".response-", dir=str(response_dir))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(tmp, target)
        os.unlink(tmp)
        dfd = os.open(str(response_dir), os.O_RDONLY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    except Exception:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise
    return target
