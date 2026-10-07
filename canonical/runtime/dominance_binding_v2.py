from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Mapping
import hashlib
import re

HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


class BindingError(ValueError):
    pass


def token(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BindingError(name + "_INVALID")
    return value.strip()


def sha256_value(value: Any, name: str) -> str:
    out = token(value, name).lower()
    if not HEX64.fullmatch(out):
        raise BindingError(name + "_INVALID")
    return out


def number(value: Any, name: str) -> Decimal:
    if isinstance(value, bool):
        raise BindingError(name + "_INVALID")
    try:
        out = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise BindingError(name + "_INVALID") from exc
    if not out.is_finite():
        raise BindingError(name + "_NONFINITE")
    return out


def content_binding(value: Any, name: str) -> tuple[str, str]:
    if not isinstance(value, Mapping):
        raise BindingError(name + "_INVALID")
    path = token(value.get("path"), name + "_PATH")
    sha = token(value.get("git_blob_sha"), name + "_SHA").lower()
    if not HEX40.fullmatch(sha):
        raise BindingError(name + "_SHA_INVALID")
    return path, sha


def live_ids(hypotheses: Any) -> list[str]:
    if not isinstance(hypotheses, list):
        raise BindingError("HYPOTHESES_INVALID")
    out: list[str] = []
    seen: set[str] = set()
    for i, raw in enumerate(hypotheses):
        if not isinstance(raw, Mapping):
            raise BindingError(f"HYPOTHESIS_{i}_INVALID")
        hid = token(raw.get("id"), f"HYPOTHESIS_{i}_ID")
        if hid in seen:
            raise BindingError("HYPOTHESIS_ID_DUPLICATE:" + hid)
        seen.add(hid)
        plausible = raw.get("plausible")
        if not isinstance(plausible, bool):
            raise BindingError(f"HYPOTHESIS_{i}_PLAUSIBLE_INVALID")
        if plausible:
            out.append(hid)
    if not out:
        raise BindingError("NO_LIVE_HYPOTHESES")
    return sorted(out)


def live_digest(ids: list[str]) -> str:
    payload = b"".join(x.encode() + b"\0" for x in sorted(ids))
    return hashlib.sha256(payload).hexdigest()


def require_true(row: Mapping[str, Any], field: str, name: str) -> None:
    if row.get(field) is not True:
        raise BindingError(name + "_" + field.upper() + "_NOT_TRUE")


def same(row: Mapping[str, Any], field: str, expected: str, name: str) -> None:
    if token(row.get(field), name + "_" + field.upper()) != expected:
        raise BindingError(name + "_" + field.upper() + "_MISMATCH")


def same_sha256(row: Mapping[str, Any], field: str, expected: str, name: str) -> None:
    if sha256_value(row.get(field), name + "_" + field.upper()) != expected:
        raise BindingError(name + "_" + field.upper() + "_MISMATCH")
