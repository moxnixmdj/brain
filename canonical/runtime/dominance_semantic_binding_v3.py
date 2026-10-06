from __future__ import annotations

from typing import Any, Mapping
import hashlib

from canonical.runtime import dominance_binding_v2 as v2


class SemanticBindingError(ValueError):
    pass


def live_worlds(hypotheses: Any) -> list[tuple[str, str]]:
    if not isinstance(hypotheses, list):
        raise SemanticBindingError("HYPOTHESES_INVALID")
    rows: list[tuple[str, str]] = []
    seen: set[str] = set()
    for i, raw in enumerate(hypotheses):
        if not isinstance(raw, Mapping):
            raise SemanticBindingError(f"HYPOTHESIS_{i}_INVALID")
        hid = v2.token(raw.get("id"), f"HYPOTHESIS_{i}_ID")
        if hid in seen:
            raise SemanticBindingError("HYPOTHESIS_ID_DUPLICATE:" + hid)
        seen.add(hid)
        plausible = raw.get("plausible")
        if not isinstance(plausible, bool):
            raise SemanticBindingError(f"HYPOTHESIS_{i}_PLAUSIBLE_INVALID")
        semantic = v2.sha256_value(
            raw.get("semantic_sha256"), f"HYPOTHESIS_{i}_SEMANTIC_SHA256"
        )
        if plausible:
            rows.append((hid, semantic))
    if not rows:
        raise SemanticBindingError("NO_LIVE_HYPOTHESES")
    return sorted(rows)


def live_world_digest(rows: list[tuple[str, str]]) -> str:
    payload = b"".join(
        hid.encode("utf-8") + b"\0" + semantic.encode("ascii") + b"\0"
        for hid, semantic in sorted(rows)
    )
    return hashlib.sha256(payload).hexdigest()


def semantic_by_id(rows: list[tuple[str, str]]) -> dict[str, str]:
    return dict(rows)
