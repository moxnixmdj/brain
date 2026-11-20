"""External, editable condition store for instant-learned actions.

A remembered program is exact: replaying it in a copied state is retention.
Whether it APPLIES is a different question -- a set of states, not a point. One
successful demonstration buys the program and no condition. A designed contrast
between states whose outcomes differ is what buys a requirement, and even then
the requirement is kept as PROVISIONAL unless the version space is identified.

This module stores both layers in plain JSON outside the weights. It is
inspectable, editable and deletable without retraining. The chooser is a pure
subset test over cheap observed facts: no model, no network, no hidden state.

Authority NONE. Computed mechanism only; zero parameters, zero model calls.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from canonical.runtime import applicability_v1 as APP

SCHEMA = "BRAIN_INSTANT_CONDITION_STORE_V1"
APPLIES = "APPLIES"
DOES_NOT_APPLY = "DOES_NOT_APPLY"
OPEN = "OPEN__NO_USABLE_CONDITION"

IDENTIFIED = "IDENTIFIED__ONE_CONSISTENT_REQUIREMENT"
PROVISIONAL = "PROVISIONAL__LEAST_DEMANDING_SURVIVOR"
ONE_SUCCESS = "OPEN__ONE_SUCCESS_BUYS_NO_CONDITION"
UNKNOWN = "OPEN__ACTION_NOT_IN_STORE"

DEFAULT_STORE = Path(__file__).resolve().parent.parent.parent / (
    "canonical/astra_runtime/state/INSTANT_CONDITION_STORE_V1.json"
)


class ConditionStoreError(ValueError):
    """Raised for malformed store input; uncertainty otherwise fails open as OPEN."""


def action_key(argv: Sequence[str] | tuple[str, ...]) -> str:
    """Portable identity: the program and its arguments, never its environment."""
    parts = [str(item) for item in argv]
    if not parts or not parts[0]:
        raise ConditionStoreError("ACTION_ARGV_REQUIRED")
    return json.dumps(parts, ensure_ascii=False, separators=(",", ":"))


def new_store() -> dict[str, Any]:
    return {"schema": SCHEMA, "version": 1, "entries": {}, "updated_at": None}


def load(path: str | Path | None = None) -> dict[str, Any]:
    target = Path(path) if path is not None else DEFAULT_STORE
    if not target.exists():
        return new_store()
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ConditionStoreError("STORE_UNREADABLE:" + str(exc)) from exc
    if not isinstance(raw, Mapping) or raw.get("schema") != SCHEMA:
        raise ConditionStoreError("STORE_SCHEMA_MISMATCH")
    entries = raw.get("entries")
    if not isinstance(entries, Mapping):
        raise ConditionStoreError("STORE_ENTRIES_NOT_OBJECT")
    result = new_store()
    result["version"] = raw.get("version", 1)
    result["entries"] = {str(key): dict(value) for key, value in entries.items()
                         if isinstance(value, Mapping)}
    result["updated_at"] = raw.get("updated_at")
    return result


def save(store: Mapping[str, Any], path: str | Path | None = None) -> dict[str, Any]:
    if store.get("schema") != SCHEMA:
        raise ConditionStoreError("STORE_SCHEMA_MISMATCH")
    target = Path(path) if path is not None else DEFAULT_STORE
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(store)
    payload["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    target.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n",
                      encoding="utf-8")
    return payload


def _entry(argv: Sequence[str], *, condition_status: str, required: Sequence[str],
           source: Mapping[str, Any]) -> dict[str, Any]:
    key = action_key(argv)
    return {
        "action_key": key,
        "program": [str(item) for item in argv],
        "condition_status": condition_status,
        "required": sorted(str(item) for item in required),
        "source": dict(source),
        "external_model_dependency": False,
        "task_specific_policy_data": False,
    }


def record_one_success(store: dict[str, Any], argv: Sequence[str],
                       observed_facts: Iterable[str],
                       *, source: Mapping[str, Any]) -> dict[str, Any]:
    """Write the program from one experience but explicitly withhold its condition."""
    entry = _entry(argv, condition_status=ONE_SUCCESS, required=(), source={
        **dict(source), "one_success_facts": sorted(set(str(x) for x in observed_facts)),
    })
    store["entries"][action_key(argv)] = entry
    return entry


def upsert_condition(store: dict[str, Any], argv: Sequence[str],
                     boundary: APP.Boundary, *, source: Mapping[str, Any],
                     condition_status: str | None = None) -> dict[str, Any]:
    """Store the least-demanding survivor unless the version space is identified."""
    status = condition_status or (IDENTIFIED if boundary.identified else PROVISIONAL)
    if status == IDENTIFIED and not boundary.identified:
        raise ConditionStoreError("IDENTIFIED_CLAIM_NOT_SUPPORTED_BY_EVIDENCE")
    required = boundary.required if status == IDENTIFIED else boundary.most_general
    entry = _entry(argv, condition_status=status, required=required, source={
        **dict(source),
        "learner_status": boundary.status,
        "survivor_count": boundary.survivor_count,
        "successes": boundary.successes,
        "failures": boundary.failures,
    })
    store["entries"][action_key(argv)] = entry
    return entry


def upsert_rule(store: dict[str, Any], argv: Sequence[str], *, required: Sequence[str],
                condition_status: str, source: Mapping[str, Any]) -> dict[str, Any]:
    """Store a computed rule directly, without inventing learner evidence."""
    if condition_status not in {IDENTIFIED, PROVISIONAL, ONE_SUCCESS}:
        raise ConditionStoreError("CONDITION_STATUS_INVALID")
    entry = _entry(argv, condition_status=condition_status, required=required,
                   source=source)
    store["entries"][action_key(argv)] = entry
    return entry


def delete(store: dict[str, Any], argv: Sequence[str]) -> bool:
    """Deletability is structural: removing an entry removes the learned condition."""
    return store["entries"].pop(action_key(argv), None) is not None


def choose(store: Mapping[str, Any], argv: Sequence[str],
           observed_facts: Iterable[str]) -> dict[str, Any]:
    """Pure applicability decision from external facts and the stored requirement."""
    key = action_key(argv)
    entry = store.get("entries", {}).get(key) if isinstance(store, Mapping) else None
    if not isinstance(entry, Mapping):
        return {"status": UNKNOWN, "decision": OPEN, "action_key": key,
                "required": [], "applies": False}
    status = str(entry.get("condition_status") or "")
    required = tuple(str(x) for x in (entry.get("required") or ()))
    result = {
        "status": status,
        "action_key": key,
        "required": list(required),
        "source": dict(entry.get("source") or {}),
        "external_model_dependency": False,
    }
    if status != IDENTIFIED and status != PROVISIONAL:
        return {**result, "decision": OPEN, "applies": False}
    facts = frozenset(str(x) for x in observed_facts)
    applies = APP.admits(required, facts)
    return {**result, "decision": APPLIES if applies else DOES_NOT_APPLY,
            "applies": applies}


def digest(store: Mapping[str, Any]) -> str:
    payload = json.dumps(store.get("entries", {}), sort_keys=True, ensure_ascii=False,
                         separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
