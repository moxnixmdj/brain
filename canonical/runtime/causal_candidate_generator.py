"""Minimal donor-independent cause-candidate generation.

Derived from the causal-ancestor/backward-slice mechanism screened from
ShaneDolphin/pyrapide (MIT, revision
d1dc66efbefe3442e247ac896416bf00c25d3ca1).

This module intentionally depends only on Python builtins. It does not discover
causal edges. Given an explicit causal event graph and event capability metadata,
it returns the intervenable decision ancestors of a target failure event.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


class CausalTraceError(ValueError):
    """Raised when the supplied causal trace is structurally invalid."""


def intervenable_decision_ancestors(
    events: Iterable[Mapping[str, Any]],
    target_id: str,
) -> list[str]:
    rows = [dict(e) for e in events]
    by_id: dict[str, dict[str, Any]] = {}

    for row in rows:
        event_id = str(row.get("id") or "")
        if not event_id:
            raise CausalTraceError("event id is required")
        if event_id in by_id:
            raise CausalTraceError(f"duplicate event id: {event_id}")
        by_id[event_id] = row

    if target_id not in by_id:
        raise CausalTraceError(f"unknown target event: {target_id}")

    parents: dict[str, tuple[str, ...]] = {}
    for event_id, row in by_id.items():
        raw = row.get("caused_by") or ()
        if isinstance(raw, (str, bytes)) or not isinstance(raw, (list, tuple)):
            raise CausalTraceError(f"caused_by must be a list for: {event_id}")
        parent_ids = tuple(str(x) for x in raw)
        missing = [x for x in parent_ids if x not in by_id]
        if missing:
            raise CausalTraceError(
                f"unknown cause(s) for {event_id}: {','.join(missing)}"
            )
        parents[event_id] = parent_ids

    ancestors: set[str] = set()
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(event_id: str) -> None:
        if event_id in visiting:
            raise CausalTraceError("causal graph contains a cycle")
        if event_id in visited:
            return
        visiting.add(event_id)
        for parent_id in parents[event_id]:
            ancestors.add(parent_id)
            visit(parent_id)
        visiting.remove(event_id)
        visited.add(event_id)

    visit(target_id)

    return [
        str(row["id"])
        for row in rows
        if str(row["id"]) in ancestors
        and bool(row.get("intervenable"))
        and str(row.get("role") or "") == "decision"
    ]
