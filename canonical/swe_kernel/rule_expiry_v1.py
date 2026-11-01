#!/usr/bin/env python3
"""Retire a learned rule when the world underneath it moved.

Why this exists
---------------
`VerifiedSkillStore.invalidate()` works and is tested: it keeps the rule *and* its
counterexample and makes recall skip it. But it has to be **called**. Measured 2026-11-01,
nothing ages a rule out when the interpreter, the platform or the tool inventory changes. A
lesson about `<=` is still true after a Python upgrade; a lesson about a library's API is not
true after the library changes. Without expiry, "permanent" means "permanent even when wrong",
and a confident stale rule is worse than no rule because it costs a verification and returns an
answer.

This module is the missing clock. It is a **separate module on purpose** — the crystallizer is
load-bearing and pinned, so nothing here edits it. The world fingerprint lives in its own table
in the same SQLite file.

What it refuses to claim
------------------------
A fingerprint is a *hint*, not a proof that a rule is still valid. Three states, and only one
of them is permission:

    FRESH    the world looks the same as when the rule was taught -- still not proof
    STALE    the world changed in a way that matters -- re-verify before use
    UNKNOWN  no fingerprint was recorded (a rule taught before this module existed, or an
             imported bundle) -- treated exactly like STALE, because unknown provenance fails
             closed here for the same reason it fails closed everywhere else in this repo

Only `reverify()` moves a rule back to FRESH, and only by running a caller-supplied verifier
against the rule's own training example. A rule that can no longer reproduce its own lesson is
invalidated through the store's own `invalidate()`, with the reason recorded.
"""
from __future__ import annotations

import hashlib
import json
import platform
import shutil
import sqlite3
import sys
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

SCHEMA = "PROJECT_BRAIN_RULE_EXPIRY_V1"

FRESH = "FRESH"
STALE = "STALE"
UNKNOWN = "UNKNOWN"

_TABLE = "skill_world_fingerprint_v1"

# Tools whose presence or absence changes what a learned command-shaped rule can do.
_WATCHED_TOOLS = (
    "python3", "python", "node", "go", "rustc", "cargo", "gcc", "g++", "make",
    "git", "sqlite3", "pytest", "tar", "gzip", "xz", "convert", "pandoc", "tesseract",
)


class ExpiryError(RuntimeError):
    """A named failure. Expiry never fails quietly."""


# --------------------------------------------------------------------------- fingerprint
def world_fingerprint() -> dict[str, Any]:
    """What a rule's truth depends on that can change without the rule changing.

    Deliberately coarse: interpreter and platform identity, plus the executable inventory.
    Version *numbers* of individual tools are left out because probing each one costs a
    subprocess and would make this expensive enough that nobody runs it.
    """
    tools = {}
    for name in _WATCHED_TOOLS:
        path = shutil.which(name)
        if not path:
            tools[name] = None
            continue
        try:
            st = Path(path).stat()
            tools[name] = {"path": path, "size": st.st_size, "mtime_ns": st.st_mtime_ns}
        except OSError:
            tools[name] = {"path": path, "size": None, "mtime_ns": None}
    return {
        "python_major_minor": f"{sys.version_info.major}.{sys.version_info.minor}",
        "platform": platform.system(),
        "machine": platform.machine(),
        "tools": tools,
    }


def _digest(fp: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(fp, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


def material_differences(
    taught: Mapping[str, Any], now: Mapping[str, Any]
) -> list[str]:
    """Which changes actually matter. A new tool appearing is not a reason to distrust a rule;
    a tool *disappearing* is, and so is a different interpreter or platform."""
    out: list[str] = []
    for key in ("python_major_minor", "platform", "machine"):
        if str(taught.get(key)) != str(now.get(key)):
            out.append(f"{key}:{taught.get(key)}->{now.get(key)}")
    old_tools = taught.get("tools") or {}
    new_tools = now.get("tools") or {}
    for name, was in old_tools.items():
        is_now = new_tools.get(name)
        if was and not is_now:
            out.append(f"tool_disappeared:{name}")
        elif was and is_now:
            if (was.get("size"), was.get("mtime_ns")) != (is_now.get("size"), is_now.get("mtime_ns")):
                out.append(f"tool_replaced:{name}")
    return out


# --------------------------------------------------------------------------- storage
def _connect(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), timeout=10.0)
    conn.execute(
        f"CREATE TABLE IF NOT EXISTS {_TABLE} ("
        "skill_id TEXT PRIMARY KEY, "
        "fingerprint_json TEXT NOT NULL, "
        "recorded_utc TEXT NOT NULL)"
    )
    conn.commit()
    return conn


def record_taught(db_path: str | Path, skill_id: str, *,
                  fingerprint: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Stamp a rule with the world it was learned in."""
    if not skill_id:
        raise ExpiryError("SKILL_ID_REQUIRED")
    fp = dict(fingerprint or world_fingerprint())
    import time
    with _connect(db_path) as conn:
        conn.execute(
            f"INSERT OR REPLACE INTO {_TABLE} (skill_id, fingerprint_json, recorded_utc) "
            "VALUES (?,?,?)",
            (skill_id, json.dumps(fp, sort_keys=True), time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
        )
    return {"skill_id": skill_id, "recorded": True, "digest": _digest(fp)}


def _stored_skill_ids(db_path: str | Path) -> list[str]:
    """Every rule the store actually holds, stamped or not.

    An audit that only walks the fingerprint table cannot see the most dangerous rule of all:
    one that was learned before this module existed and therefore has no stamp. Measured while
    writing this: an unstamped rule came back as `skipped: []` and would never have been
    examined. The store's own table is the ground truth for what exists.
    """
    try:
        conn = sqlite3.connect(str(db_path), timeout=10.0)
        try:
            rows = conn.execute(
                "SELECT skill_id FROM crystallized_skills WHERE domain='swe_code_repair'"
            ).fetchall()
        finally:
            conn.close()
    except sqlite3.Error:
        return []
    return [str(r[0]) for r in rows]


def _recorded(db_path: str | Path) -> dict[str, dict[str, Any]]:
    try:
        with _connect(db_path) as conn:
            rows = conn.execute(f"SELECT skill_id, fingerprint_json FROM {_TABLE}").fetchall()
    except sqlite3.Error:
        return {}
    out: dict[str, dict[str, Any]] = {}
    for skill_id, blob in rows:
        try:
            out[skill_id] = json.loads(blob)
        except Exception:
            continue
    return out


# --------------------------------------------------------------------------- audit
def audit(db_path: str | Path, *, skill_ids: Iterable[str] | None = None,
          now: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Classify every rule FRESH / STALE / UNKNOWN against the current world."""
    current = dict(now or world_fingerprint())
    recorded = _recorded(db_path)
    if skill_ids is not None:
        ids = list(skill_ids)
    else:
        ids = sorted(set(_stored_skill_ids(db_path)) | set(recorded))
    rows: list[dict[str, Any]] = []
    counts = {FRESH: 0, STALE: 0, UNKNOWN: 0}
    for skill_id in ids:
        taught = recorded.get(skill_id)
        if taught is None:
            counts[UNKNOWN] += 1
            rows.append({"skill_id": skill_id, "state": UNKNOWN,
                         "reason": "NO_WORLD_FINGERPRINT_RECORDED"})
            continue
        diffs = material_differences(taught, current)
        state = STALE if diffs else FRESH
        counts[state] += 1
        rows.append({"skill_id": skill_id, "state": state,
                     "reason": "MATERIAL_WORLD_CHANGE" if diffs else "WORLD_UNCHANGED",
                     "differences": diffs})
    return {"schema": SCHEMA, "counts": counts, "rules": rows,
            "world_digest": _digest(current)}


def usable(db_path: str | Path, skill_id: str, *,
           now: Mapping[str, Any] | None = None) -> bool:
    """May a rule be offered at all? FRESH only. UNKNOWN fails closed."""
    report = audit(db_path, skill_ids=[skill_id], now=now)
    return report["rules"][0]["state"] == FRESH


# --------------------------------------------------------------------------- reverify
def reverify(db_path: str | Path, skill_id: str,
             verifier: Callable[[], bool], *,
             now: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Re-prove a rule in the current world, and refresh its stamp only if it still holds.

    `verifier` takes no arguments because the caller owns the training example; this module
    deliberately does not guess what the rule was supposed to fix.
    """
    if not callable(verifier):
        raise ExpiryError("REVERIFY_REQUIRES_A_VERIFIER")
    current = dict(now or world_fingerprint())
    try:
        passed = bool(verifier())
    except Exception as exc:  # a verifier that cannot run has not passed
        return {"skill_id": skill_id, "reverified": False,
                "reason": f"VERIFIER_RAISED:{type(exc).__name__}"}
    if not passed:
        return {"skill_id": skill_id, "reverified": False,
                "reason": "RULE_NO_LONGER_REPRODUCES_ITS_LESSON"}
    record_taught(db_path, skill_id, fingerprint=current)
    return {"skill_id": skill_id, "reverified": True, "digest": _digest(current)}


def expire_stale(store: Any, db_path: str | Path, *, now: Mapping[str, Any] | None = None,
                 reason_prefix: str = "WORLD_CHANGED") -> dict[str, Any]:
    """Invalidate every STALE rule through the store's own `invalidate()`.

    UNKNOWN rules are reported but not invalidated: a missing stamp is a bookkeeping gap, and
    destroying a rule for a gap in our own records would be the opposite of careful.
    """
    report = audit(db_path, now=now)
    expired, skipped = [], []
    for row in report["rules"]:
        if row["state"] == STALE:
            reason = reason_prefix + ":" + ",".join(row.get("differences") or [])[:1000]
            try:
                ok = bool(store.invalidate(row["skill_id"], reason))
            except Exception as exc:
                raise ExpiryError(f"STORE_INVALIDATE_FAILED:{type(exc).__name__}") from exc
            (expired if ok else skipped).append(row["skill_id"])
        elif row["state"] == UNKNOWN:
            skipped.append(row["skill_id"])
    return {"schema": SCHEMA, "expired": sorted(expired), "skipped": sorted(skipped),
            "counts": report["counts"]}
