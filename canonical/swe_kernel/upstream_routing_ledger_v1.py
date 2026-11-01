#!/usr/bin/env python3
"""Upstream Refusal-Driven Routing Ledger (O(1) Structural Intent -> Capability Disqualification).

Turns pre-execution capability/effect-domain mismatches into durable upstream selection
rules (<0.5 ms lookup, K3 = 0, $0 spend) while strictly preserving honest world/input
refusals (`BISECT_WITHOUT_A_KNOWN_GOOD_COMMIT`, `TARGET_NOT_IN_STANDALONE_GIT_REPOSITORY`,
`SYMBOL_ALREADY_EXISTS`, etc.).
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import sqlite3
import time
from typing import Any, Callable, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_UPSTREAM_ROUTING_LEDGER_V1"

# Selection/domain mismatches: the WRONG capability row was picked for the sentence shape.
LEARNABLE_MISMATCH_CODES = frozenset({
    "OP_NOT_DECLARED",
    "UNSUPPORTED_OPERATION",
    "CAPABILITY_DOMAIN_MISMATCH",
    "READ_ONLY_GOAL_DISPATCHED_TO_WRITER",
    "MUTATING_GOAL_DISPATCHED_TO_READER",
    "WRONG_OBJECT_DOMAIN",
    "UNDECLARED_GIT_OPERATION",
})

# Honest world/fixture/input refusals: the RIGHT capability row ran and reported truth.
# Never disqualify a capability for telling the truth about missing/impossible inputs!
HONEST_WORLD_REFUSAL_CODES = frozenset({
    "BISECT_WITHOUT_A_KNOWN_GOOD_COMMIT",
    "TARGET_NOT_IN_STANDALONE_GIT_REPOSITORY",
    "MISSING_REQUIRED_DECLARED_INPUTS",
    "SYMBOL_ALREADY_EXISTS",
    "NO_SHARED_STATE_RACE_DETECTED",
    "TARGET_FILE_NOT_FOUND",
    "MERGE_CONFLICT_DETECTED",
    "CHERRY_PICK_CONFLICT",
})

_READ_OPENERS = frozenset({
    "find", "show", "list", "what", "which", "where", "who", "how", "count",
    "inspect", "explain", "diagnose", "detect", "check", "measure", "summarize",
    "changelog",
})
_WRITE_OPENERS = frozenset({
    "fix", "repair", "patch", "refactor", "rename", "extract", "inline", "add",
    "create", "commit", "cherry-pick", "cherry_pick", "optimize", "speed",
    "memoize", "parallelize", "implement", "rewrite", "convert", "pack",
})
_GIT_TOKENS = frozenset({
    "git", "commit", "commits", "branch", "cherry-pick", "cherry_pick",
    "bisect", "blame", "revision", "head", "head~1", "changelog", "merge",
    "rebase", "stash", "tag",
})
_STOP_WORDS = frozenset({
    "the", "a", "an", "in", "on", "of", "to", "for", "from", "into", "with",
    "and", "or", "by", "at", "is", "are", "this", "that", "there", "all",
    "me", "please", "named", "called",
})

_PATH_LIKE_RE = re.compile(r"(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+|\b[A-Za-z0-9_-]+\.[A-Za-z0-9]{1,8}\b")
_HEX_SHA_RE = re.compile(r"\b[0-9a-f]{7,40}\b")
_QUOTED_RE = re.compile(r"'[^']*'|\"[^\"]*\"")


def _repo_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[2]


def default_ledger_db_path() -> pathlib.Path:
    base = _repo_root() / "canonical" / "astra_runtime" / "tmp"
    base.mkdir(parents=True, exist_ok=True)
    return base / "upstream_routing_ledger_v1.sqlite"


def classify_goal_intent_signature(goal: str) -> dict[str, str]:
    """Extract a content-free `(object_domain, effect_polarity, shape_hash)` signature.

    Strips file paths, commit hashes, numbers, and quoted literals so the signature
    transfers across unseen repositories, filenames, and branch names.
    """
    cleaned = _QUOTED_RE.sub(" <STR> ", str(goal or ""))
    cleaned = _PATH_LIKE_RE.sub(" <PATH> ", cleaned)
    cleaned = _HEX_SHA_RE.sub(" <SHA> ", cleaned)
    cleaned = re.sub(r"\b\d+\b", " <NUM> ", cleaned)

    raw_tokens = re.findall(r"[a-zA-Z_<][a-zA-Z0-9_>-]*", cleaned.lower())
    words = [t for t in raw_tokens if not t.startswith("<") and t not in _STOP_WORDS]

    first_verb = words[0] if words else "unknown"
    if first_verb in _READ_OPENERS or any(w in ("find", "show", "detect", "diagnose", "changelog") for w in words[:3]):
        polarity = "read"
    elif first_verb in _WRITE_OPENERS or any(w in _WRITE_OPENERS for w in words[:3]):
        polarity = "write"
    else:
        polarity = "neutral"

    if any(w in _GIT_TOKENS for w in words):
        domain = "git_repository"
    elif any(w in ("http", "url", "form", "endpoint", "csrf", "cookie", "login") for w in words):
        domain = "web_http"
    elif any(w in ("tar", "gzip", "compress", "archive", "csv", "sha256") for w in words):
        domain = "cli_artifact"
    else:
        domain = "software_code"

    structural_skeleton = f"{domain}|{polarity}|{' '.join(words[:5])}"
    shape_hash = hashlib.sha256(structural_skeleton.encode("utf-8")).hexdigest()[:20]
    return {
        "object_domain": domain,
        "effect_polarity": polarity,
        "structural_skeleton": structural_skeleton,
        "shape_hash": shape_hash,
    }


def is_learnable_selection_mismatch(refusal_code: str) -> bool:
    code = str(refusal_code or "").strip().upper()
    if not code:
        return False
    if any(h in code for h in HONEST_WORLD_REFUSAL_CODES):
        return False
    if code in LEARNABLE_MISMATCH_CODES:
        return True
    return any(tok in code for tok in ("MISMATCH", "NOT_DECLARED", "UNSUPPORTED_OP", "DISPATCHED_TO_WRITER", "DISPATCHED_TO_READER"))


class UpstreamRoutingLedger:
    """SQLite WAL ledger mapping structural intent shapes to disqualified/preferred capabilities."""

    def __init__(self, db_path: pathlib.Path | None = None) -> None:
        self.db_path = pathlib.Path(db_path) if db_path else default_ledger_db_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=5.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _init_schema(self) -> None:
        conn = self._connect()
        try:
            with conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS routing_disqualifications (
                        shape_hash TEXT NOT NULL,
                        structural_skeleton TEXT NOT NULL,
                        object_domain TEXT NOT NULL,
                        effect_polarity TEXT NOT NULL,
                        disqualified_capability TEXT NOT NULL,
                        preferred_capability TEXT,
                        refusal_code TEXT NOT NULL,
                        hit_count INTEGER NOT NULL DEFAULT 1,
                        updated_ts REAL NOT NULL,
                        PRIMARY KEY (shape_hash, disqualified_capability)
                    )
                    """
                )
        finally:
            conn.close()

    def record_refusal(
        self,
        goal: str,
        disqualified_capability: str,
        refusal_code: str,
        *,
        preferred_capability: str | None = None,
    ) -> dict[str, Any]:
        """Record a structural capability mismatch if and only if `refusal_code` is a selection error."""
        if not is_learnable_selection_mismatch(refusal_code):
            return {
                "recorded": False,
                "reason": "HONEST_WORLD_OR_INPUT_REFUSAL_NOT_DISQUALIFIED",
                "refusal_code": refusal_code,
            }
        sig = classify_goal_intent_signature(goal)
        conn = self._connect()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO routing_disqualifications (
                        shape_hash, structural_skeleton, object_domain, effect_polarity,
                        disqualified_capability, preferred_capability, refusal_code, hit_count, updated_ts
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
                    ON CONFLICT(shape_hash, disqualified_capability) DO UPDATE SET
                        hit_count = hit_count + 1,
                        preferred_capability = COALESCE(excluded.preferred_capability, routing_disqualifications.preferred_capability),
                        updated_ts = excluded.updated_ts
                    """,
                    (
                        sig["shape_hash"],
                        sig["structural_skeleton"],
                        sig["object_domain"],
                        sig["effect_polarity"],
                        disqualified_capability,
                        preferred_capability,
                        str(refusal_code),
                        time.time(),
                    ),
                )
        finally:
            conn.close()
        return {
            "recorded": True,
            "shape_hash": sig["shape_hash"],
            "structural_skeleton": sig["structural_skeleton"],
            "disqualified_capability": disqualified_capability,
            "preferred_capability": preferred_capability,
        }

    def lookup_shape(self, goal: str) -> dict[str, Any]:
        sig = classify_goal_intent_signature(goal)
        conn = self._connect()
        try:
            rows = conn.execute(
                """
                SELECT disqualified_capability, preferred_capability, refusal_code, hit_count
                FROM routing_disqualifications
                WHERE shape_hash = ?
                """,
                (sig["shape_hash"],),
            ).fetchall()
        finally:
            conn.close()
        disqualified = {str(r[0]): {"refusal_code": str(r[2]), "hits": int(r[3])} for r in rows}
        preferred = next((str(r[1]) for r in rows if r[1]), None)
        return {
            "signature": sig,
            "disqualified": disqualified,
            "preferred_capability": preferred,
        }

    def filter_and_rank_candidates(
        self,
        goal: str,
        candidates: Sequence[str],
        capability_effects: Mapping[str, Mapping[str, Any]] | None = None,
    ) -> list[str]:
        """Rank `candidates` upstream using learned ledger disqualifications + effect polarity."""
        info = self.lookup_shape(goal)
        disq = info["disqualified"]
        pref = info["preferred_capability"]
        polarity = info["signature"]["effect_polarity"]
        domain = info["signature"]["object_domain"]

        def _score(cap_id: str, idx: int) -> tuple[int, int, int, int]:
            is_disq = 1 if cap_id in disq else 0
            is_pref = 0 if (pref and cap_id == pref) else 1
            eff_penalty = 0
            if capability_effects and cap_id in capability_effects:
                meta = capability_effects[cap_id]
                cap_mutates = bool(meta.get("mutates"))
                cap_domain = str(meta.get("domain") or "")
                if polarity == "read" and cap_mutates:
                    eff_penalty += 2
                elif polarity == "write" and not cap_mutates:
                    eff_penalty += 2
                if domain and cap_domain and cap_domain != domain:
                    eff_penalty += 1
            return (is_disq, is_pref, eff_penalty, idx)

        scored = [(_score(c, i), c) for i, c in enumerate(candidates)]
        scored.sort(key=lambda pair: pair[0])
        # Exclude disqualified rows whenever at least one non-disqualified candidate exists
        non_disq = [c for s, c in scored if s[0] == 0]
        return non_disq if non_disq else [c for _, c in scored]

    def dispatch_with_reroute(
        self,
        goal: str,
        candidates: Sequence[str],
        execute_fn: Callable[[str], Mapping[str, Any]],
        *,
        capability_effects: Mapping[str, Mapping[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Execute ranked candidates; on pre-execution selection mismatch, learn & reroute immediately."""
        ordered = self.filter_and_rank_candidates(goal, candidates, capability_effects)
        attempts: list[dict[str, Any]] = []
        disqualified_now: list[tuple[str, str]] = []

        for cap_id in ordered:
            res = dict(execute_fn(cap_id))
            ok = bool(res.get("ok") or res.get("pass") or res.get("verified"))
            refusal = str(res.get("refusal_code") or res.get("failure_class") or res.get("reason") or "")
            executed_mutation = bool(res.get("mutated_workspace"))
            attempts.append({"capability_id": cap_id, "ok": ok, "refusal_code": refusal})

            if ok:
                for bad_cap, bad_code in disqualified_now:
                    self.record_refusal(goal, bad_cap, bad_code, preferred_capability=cap_id)
                res["selected_capability_id"] = cap_id
                res["routing_attempts"] = attempts
                res["rerouted_in_run"] = len(attempts) > 1
                return res

            # Only reroute if workspace was NOT mutated and refusal is a selection/domain mismatch
            if not executed_mutation and is_learnable_selection_mismatch(refusal):
                disqualified_now.append((cap_id, refusal))
                self.record_refusal(goal, cap_id, refusal)
                continue

            # Honest world/input refusal: return immediately without disqualifying!
            res["selected_capability_id"] = cap_id
            res["routing_attempts"] = attempts
            res["rerouted_in_run"] = False
            return res

        return {
            "ok": False,
            "pass": False,
            "status": "FAIL_CLOSED__ALL_CANDIDATES_REFUSED",
            "routing_attempts": attempts,
            "rerouted_in_run": len(attempts) > 1,
        }
