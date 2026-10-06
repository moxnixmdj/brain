from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

from canonical.runtime.honesty_emission_gateway_v1 import (
    encode_capsule,
    make_capsule,
)


class EmissionClientError(ValueError):
    pass


def broker_fd() -> int:
    raw = os.environ.get("PROJECT_BRAIN_BROKER_FD", "").strip()
    if not raw:
        raise EmissionClientError("BROKER_FD_ENV_MISSING")
    try:
        fd = int(raw)
    except ValueError as exc:
        raise EmissionClientError("BROKER_FD_ENV_INVALID") from exc
    if fd < 0:
        raise EmissionClientError("BROKER_FD_NEGATIVE")
    return fd


def emit(
    *,
    sequence: int,
    emission_id: str,
    payload: Any,
    honesty_record: Mapping[str, Any],
    fd: int | None = None,
) -> dict[str, Any]:
    capsule = make_capsule(
        sequence=sequence,
        emission_id=emission_id,
        payload=payload,
        honesty_record=honesty_record,
    )
    raw = encode_capsule(capsule)
    target = broker_fd() if fd is None else int(fd)
    if target < 0:
        raise EmissionClientError("BROKER_FD_NEGATIVE")
    offset = 0
    while offset < len(raw):
        written = os.write(target, raw[offset:])
        if written <= 0:
            raise EmissionClientError("BROKER_WRITE_FAILED")
        offset += written
    return {
        "emission_id": capsule["emission_id"],
        "sequence": capsule["sequence"],
        "payload_sha256": capsule["payload_sha256"],
        "honesty_record_sha256": capsule["honesty_record_sha256"],
        "bytes_written": len(raw),
    }
