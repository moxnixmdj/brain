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
    "WRONG_OBJECT_ROLE",
    "UNDECLARED_GIT_OPERATION",
    "R10_SOFTWARE_IMPLEMENTATION_EFFECT_UNSERVED",
    "R2_OUTPUT_ARTIFACT_UNSERVED",
    "LEXICAL_EFFECT_CONTRADICTED",
    "STATED_READ_ONLY_QUESTION_ANSWERED_BY_A_WRITER_CANDIDATE",
})

# Honest world/fixture/input refusals: the RIGHT capability row ran and reported truth.
# Never disqualify a capability for telling the truth about missing/impossible inputs!
HONEST_WORLD_REFUSAL_CODES = frozenset({
    "BISECT_WITHOUT_A_KNOWN_GOOD_COMMIT",
    "TARGET_NOT_IN_STANDALONE_GIT_REPOSITORY",
    "MISSING_REQUIRED_DECLARED_INPUTS",
    "SYMBOL_ALREADY_EXISTS",
    "TARGET_SYMBOL_ALREADY_EXISTS",
    "TARGET_SYMBOL_COLLISION",
    "NO_SHARED_STATE_RACE_DETECTED",
    "TARGET_FILE_NOT_FOUND",
    "MERGE_CONFLICT_DETECTED",
    "CHERRY_PICK_CONFLICT",
    "STATED_PATH_OUTSIDE_THE_WORKSPACE",
    "COMPUTABILITY_IMPOSSIBLE_SPECIFICATION",
    "PROMISED_SOURCE_CHANGE_NOT_APPLIED",
    "REQUESTED_CONTRACT_CHECKS_NOT_VERIFIED",
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

_ROLE_INTRODUCERS = frozenset({
    "symbol", "function", "method", "class", "parameter", "argument", "arg",
    "variable", "constant", "caller", "callers", "definition", "definitions",
})
_INTENT_VOCAB = (
    _READ_OPENERS
    | _WRITE_OPENERS
    | _GIT_TOKENS
    | _ROLE_INTRODUCERS
    | frozenset({
        "http", "url", "form", "endpoint", "csrf", "cookie", "login",
        "tar", "gzip", "compress", "archive", "csv", "sha256",
        "python", "rust", "go", "javascript", "typescript", "sql",
        "test", "tests", "failing", "deadlock", "race", "regression",
        "bug", "error", "issue", "file", "files", "module", "directory",
        "repo", "repository", "every", "new", "unused", "uncovered",
        "duplicate", "different", "lines", "line", "code", "source",
        "security", "coverage", "type", "lint", "format", "conflict",
    })
)

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

    Strips file paths, commit hashes, numbers, quoted literals, and arbitrary user
    symbol/identifier names so the signature transfers across unseen repositories,
    filenames, symbol names, and branch names.
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

    intent_words = [w for w in words if w in _INTENT_VOCAB]
    if not intent_words and words:
        intent_words = [words[0]]
    structural_skeleton = f"{domain}|{polarity}|{' '.join(intent_words[:5])}"
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


_LEDGER_RAM_CACHE: dict[str, tuple[tuple[int, int, int], dict[str, list[tuple[str, str | None, str, int]]]]] = {}
_LEDGER_SINGLETONS: dict[str, "UpstreamRoutingLedger"] = {}


def _db_wal_stamp(db_path: pathlib.Path) -> tuple[int, int, int]:
    try:
        st = db_path.stat()
        db_m = st.st_mtime_ns
    except OSError:
        db_m = 0
    wal = pathlib.Path(str(db_path) + "-wal")
    try:
        wst = wal.stat()
        wal_m, wal_sz = wst.st_mtime_ns, wst.st_size
    except OSError:
        wal_m, wal_sz = 0, 0
    return (db_m, wal_m, wal_sz)


def default_ledger(db_path: pathlib.Path | str | None = None) -> "UpstreamRoutingLedger":
    target = pathlib.Path(db_path).resolve() if db_path else default_ledger_db_path().resolve()
    key = str(target)
    inst = _LEDGER_SINGLETONS.get(key)
    if inst is None:
        inst = UpstreamRoutingLedger(target)
        _LEDGER_SINGLETONS[key] = inst
    return inst


class UpstreamRoutingLedger:
    """SQLite WAL ledger mapping structural intent shapes to disqualified/preferred capabilities."""

    def __init__(self, db_path: pathlib.Path | None = None) -> None:
        from canonical.runtime.memory_policy_v1 import can_write_memory

        self.db_path = (pathlib.Path(db_path) if db_path else default_ledger_db_path()).resolve()
        self._schema_ready = False
        if self.db_path.exists() or can_write_memory():
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path), timeout=5.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _init_schema(self) -> None:
        if self._schema_ready and self.db_path.exists():
            return
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
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS verified_route_promotions (
                        shape_hash TEXT NOT NULL,
                        structural_skeleton TEXT NOT NULL,
                        object_domain TEXT NOT NULL,
                        effect_polarity TEXT NOT NULL,
                        preferred_capability TEXT NOT NULL,
                        distinct_instances_json TEXT NOT NULL,
                        verified_count INTEGER NOT NULL DEFAULT 1,
                        invalidated INTEGER NOT NULL DEFAULT 0,
                        invalidation_reason TEXT,
                        updated_ts REAL NOT NULL,
                        PRIMARY KEY (shape_hash, preferred_capability)
                    )
                    """
                )
            self._schema_ready = True
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
        from canonical.runtime.memory_policy_v1 import can_write_memory

        if not can_write_memory():
            return {
                "recorded": False,
                "reason": "MEMORY_POLICY_WRITE_DISABLED",
                "refusal_code": refusal_code,
            }
        if not is_learnable_selection_mismatch(refusal_code):
            return {
                "recorded": False,
                "reason": "HONEST_WORLD_OR_INPUT_REFUSAL_NOT_DISQUALIFIED",
                "refusal_code": refusal_code,
            }
        self._init_schema()
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
        _LEDGER_RAM_CACHE.pop(str(self.db_path), None)
        return {
            "recorded": True,
            "shape_hash": sig["shape_hash"],
            "structural_skeleton": sig["structural_skeleton"],
            "disqualified_capability": disqualified_capability,
            "preferred_capability": preferred_capability,
        }

    def record_verified_route(
        self,
        goal: str,
        capability_id: str,
        *,
        promotion_threshold: int = 2,
    ) -> dict[str, Any]:
        """Record a verified positive `(shape_hash -> capability_id)` execution; promotes after `N >= 2` distinct instances."""
        from canonical.runtime.memory_policy_v1 import can_write_memory

        if not can_write_memory() or not goal or not capability_id:
            return {
                "recorded": False,
                "promoted": False,
                "reason": "MEMORY_POLICY_WRITE_DISABLED" if not can_write_memory() else "INVALID_ROUTE_ARGS",
            }
        self._init_schema()
        sig = classify_goal_intent_signature(goal)
        inst_fp = hashlib.sha256(str(goal).strip().encode("utf-8")).hexdigest()[:16]
        threshold = max(2, int(promotion_threshold))
        conn = self._connect()
        try:
            with conn:
                conn.execute("BEGIN IMMEDIATE")
                row = conn.execute(
                    """
                    SELECT distinct_instances_json, verified_count, invalidated
                    FROM verified_route_promotions
                    WHERE shape_hash = ? AND preferred_capability = ?
                    """,
                    (sig["shape_hash"], capability_id),
                ).fetchone()
                if row is not None and not int(row[2] or 0):
                    try:
                        instances = list(json.loads(row[0]))
                    except Exception:
                        instances = []
                    vcount = int(row[1] or 0) + 1
                else:
                    instances = []
                    vcount = 1
                if inst_fp not in instances:
                    instances.append(inst_fp)
                instances = instances[-32:]
                conn.execute(
                    """
                    INSERT INTO verified_route_promotions (
                        shape_hash, structural_skeleton, object_domain, effect_polarity,
                        preferred_capability, distinct_instances_json, verified_count,
                        invalidated, invalidation_reason, updated_ts
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, NULL, ?)
                    ON CONFLICT(shape_hash, preferred_capability) DO UPDATE SET
                        distinct_instances_json = excluded.distinct_instances_json,
                        verified_count = excluded.verified_count,
                        invalidated = 0,
                        invalidation_reason = NULL,
                        updated_ts = excluded.updated_ts
                    """,
                    (
                        sig["shape_hash"],
                        sig["structural_skeleton"],
                        sig["object_domain"],
                        sig["effect_polarity"],
                        capability_id,
                        json.dumps(instances),
                        vcount,
                        time.time(),
                    ),
                )
        finally:
            conn.close()
        _LEDGER_RAM_CACHE.pop(str(self.db_path), None)
        promoted = len(instances) >= threshold
        return {
            "recorded": True,
            "promoted": promoted,
            "distinct_instances": len(instances),
            "promotion_threshold": threshold,
            "shape_hash": sig["shape_hash"],
            "preferred_capability": capability_id,
        }

    def invalidate_preferred_capability(
        self,
        goal: str,
        capability_id: str,
        *,
        reason: str = "VERIFICATION_MISS",
    ) -> dict[str, Any]:
        """Demote a previously promoted `preferred_capability` immediately on a verification or execution miss."""
        from canonical.runtime.memory_policy_v1 import can_write_memory

        if not can_write_memory() or not self.db_path.exists():
            return {"invalidated": False, "reason": "MEMORY_POLICY_WRITE_DISABLED"}
        self._init_schema()
        sig = classify_goal_intent_signature(goal)
        conn = self._connect()
        changed = 0
        try:
            with conn:
                c1 = conn.execute(
                    """
                    UPDATE verified_route_promotions
                    SET invalidated = 1, invalidation_reason = ?, updated_ts = ?
                    WHERE shape_hash = ? AND preferred_capability = ? AND invalidated = 0
                    """,
                    (str(reason)[:240], time.time(), sig["shape_hash"], capability_id),
                )
                c2 = conn.execute(
                    """
                    UPDATE routing_disqualifications
                    SET preferred_capability = NULL, updated_ts = ?
                    WHERE shape_hash = ? AND preferred_capability = ?
                    """,
                    (time.time(), sig["shape_hash"], capability_id),
                )
                changed = int(c1.rowcount or 0) + int(c2.rowcount or 0)
        finally:
            conn.close()
        _LEDGER_RAM_CACHE.pop(str(self.db_path), None)
        return {
            "invalidated": changed > 0,
            "shape_hash": sig["shape_hash"],
            "capability_id": capability_id,
            "reason": reason,
        }

    def _load_table_cached(self) -> tuple[dict[str, list[tuple[str, str | None, str, int]]], dict[str, tuple[str, int]]]:
        if not self.db_path.exists():
            return {}, {}
        key = str(self.db_path)
        stamp = _db_wal_stamp(self.db_path)
        hit = _LEDGER_RAM_CACHE.get(key)
        if hit is not None and hit[0] == stamp:
            return hit[1]  # type: ignore[return-value]
        self._init_schema()
        conn = self._connect()
        try:
            all_rows = conn.execute(
                """
                SELECT shape_hash, disqualified_capability, preferred_capability, refusal_code, hit_count
                FROM routing_disqualifications
                """
            ).fetchall()
            promo_rows = conn.execute(
                """
                SELECT shape_hash, preferred_capability, distinct_instances_json, verified_count
                FROM verified_route_promotions
                WHERE invalidated = 0
                ORDER BY verified_count DESC, updated_ts DESC
                """
            ).fetchall()
        finally:
            conn.close()
        by_shape: dict[str, list[tuple[str, str | None, str, int]]] = {}
        for sh, disq_c, pref_c, rcode, hits in all_rows:
            by_shape.setdefault(str(sh), []).append(
                (str(disq_c), str(pref_c) if pref_c else None, str(rcode), int(hits))
            )
        promoted_by_shape: dict[str, tuple[str, int]] = {}
        for sh, pref_c, inst_json, vcount in promo_rows:
            sh_s = str(sh)
            if sh_s in promoted_by_shape:
                continue
            try:
                n_inst = len(json.loads(inst_json))
            except Exception:
                n_inst = 0
            if n_inst >= 2 and pref_c:
                promoted_by_shape[sh_s] = (str(pref_c), int(vcount or n_inst))
        cached_val = (by_shape, promoted_by_shape)
        _LEDGER_RAM_CACHE[key] = (_db_wal_stamp(self.db_path), cached_val)  # type: ignore[assignment]
        return cached_val

    def lookup_shape(self, goal: str, *, promotion_threshold: int = 2) -> dict[str, Any]:
        from canonical.runtime.memory_policy_v1 import can_read_memory

        sig = classify_goal_intent_signature(goal)
        if not can_read_memory():
            return {
                "signature": sig,
                "disqualified": {},
                "preferred_capability": None,
                "promoted_route": False,
                "verified_hits": 0,
            }
        disq_by_shape, promo_by_shape = self._load_table_cached()
        rows = disq_by_shape.get(sig["shape_hash"]) or []
        disqualified = {r[0]: {"refusal_code": r[2], "hits": r[3]} for r in rows}
        promo = promo_by_shape.get(sig["shape_hash"])
        if promo is not None and promo[0] not in disqualified and promo[1] >= max(2, int(promotion_threshold)):
            preferred = promo[0]
            promoted_route = True
            verified_hits = promo[1]
        else:
            preferred = next((r[1] for r in rows if r[1] and r[1] not in disqualified), None)
            promoted_route = False
            verified_hits = 0
        return {
            "signature": sig,
            "disqualified": disqualified,
            "preferred_capability": preferred,
            "promoted_route": promoted_route,
            "verified_hits": verified_hits,
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
        """Execute ranked candidates; promote positive routes (`N >= 2`), invalidate stale promotions on miss, and reroute selection errors."""
        info = self.lookup_shape(goal)
        prior_pref = info.get("preferred_capability")
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
                promo_res = self.record_verified_route(goal, cap_id)
                res["selected_capability_id"] = cap_id
                res["routing_attempts"] = attempts
                res["rerouted_in_run"] = len(attempts) > 1
                res["route_promoted"] = bool(promo_res.get("promoted"))
                return res

            if prior_pref and cap_id == prior_pref:
                self.invalidate_preferred_capability(goal, cap_id, reason=refusal or "PROMOTED_ROUTE_MISS")
                if not executed_mutation and len(ordered) > 1:
                    if is_learnable_selection_mismatch(refusal):
                        disqualified_now.append((cap_id, refusal))
                        self.record_refusal(goal, cap_id, refusal)
                    continue

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
