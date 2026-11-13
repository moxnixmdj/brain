#!/usr/bin/env python3
"""Persistent parameterized code-repair hypotheses in the existing SQLite store.

Structural twins test pattern transport, not semantic correctness. Legacy boolean
callbacks retain CALLER_PREDICATE assurance only. Scoped records and typed current
verification distinguish syntax/compilation/test-suite claims; no result proves
arbitrary task correctness, permanent availability or universal instant learning.
"""
from __future__ import annotations

import ast
import itertools
import copy
import hashlib
import json
import io
import keyword
import math
import tokenize
import os
import pathlib
import re
import shutil
import sqlite3
import tempfile
import time
from typing import Any, Callable, Mapping, Sequence

from canonical.swe_kernel import python_scoped_edit_rule_v1 as _PY_EDIT

from canonical.swe_kernel.skill_verification_contract_v1 import (
    KINDS, VerificationResult, applicable, evaluate, normalize_contract, source_sha256,
)

SCHEMA = "PROJECT_BRAIN_VERIFIED_SKILL_CRYSTALLIZER_V1"
BUNDLE_SCHEMA = "PROJECT_BRAIN_VERIFIED_SKILL_BUNDLE_V1"

_PYTHON_KEYWORDS_KEEP = frozenset({
    "def", "return", "if", "elif", "else", "for", "while", "in", "not", "and", "or", "is",
    "None", "True", "False", "class", "import", "from", "with", "as", "try", "except",
    "finally", "raise", "async", "await", "yield", "lambda", "pass", "break", "continue",
    "len", "range", "min", "max", "sum", "abs", "int", "float", "str", "list", "dict",
    "set", "tuple", "bool", "enumerate", "zip", "sorted", "reversed", "isinstance", "getattr",
})

_KEYWORDS_KEEP = _PYTHON_KEYWORDS_KEEP | frozenset({
    # Go
    "package", "func", "var", "const", "type", "struct", "interface", "map", "make", "append",
    "nil", "err", "error", "string", "int64", "float64", "byte", "rune", "go", "defer", "chan",
    # Rust
    "fn", "pub", "let", "mut", "impl", "trait", "enum", "match", "Some", "Ok", "Err", "Vec",
    "String", "usize", "isize", "i32", "i64", "u32", "u64", "f64", "Self", "self", "super",
    # TypeScript / JS
    "export", "function", "null", "undefined", "number", "boolean", "typeof", "instanceof",
    # C++ / Java
    "std", "vector", "size_t", "size", "auto", "void", "public", "private", "static", "new",
    # SQL
    "CREATE", "TABLE", "ALTER", "ADD", "COLUMN", "NOT", "NULL", "PRIMARY", "KEY", "INTEGER",
    "TEXT", "REAL", "BLOB", "UNIQUE", "DEFAULT", "SELECT", "FROM", "WHERE", "INDEX", "ON",
})

_TOKEN_RE = re.compile(
    r"""(?P<str>"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')"""
    r"""|(?P<ident>[A-Za-z_][A-Za-z0-9_]*)"""
    r"""|(?P<num>\b\d+(?:\.\d+)?\b)"""
    r"""|(?P<op>==|!=|<=|>=|:=|\.\.=|\.\.|->|=>|\+=|-=|\*=|/=|\?\?|\?\.|[+\-*/%&|^~<>!=()\[\]{}.,:;?])"""
    r"""|(?P<ws>\s+)""",
    re.DOTALL,
)

_HOLE_PREFIX = {"ident": "?id", "num": "?num", "str": "?str"}
_HOLE_KIND = {"hole_id": "ident", "hole_num": "num", "hole_str": "str"}
# The identifier hole keeps its historical token name so rules already stored as ``hole_id``
# still match; the literal holes are new and are named for their kind.
_HOLE_TOKEN = {"ident": "hole_id", "num": "hole_num", "str": "hole_str"}

_MEM_SKILLS: dict[str, tuple[tuple, list[dict[str, Any]]]] = {}
_PROCESS_WORLD_FP: dict[str, Any] | None = None


def _current_world_fp() -> dict[str, Any]:
    global _PROCESS_WORLD_FP
    if _PROCESS_WORLD_FP is None:
        from canonical.swe_kernel import rule_expiry_v1 as _expiry

        _PROCESS_WORLD_FP = _expiry.world_fingerprint()
    return _PROCESS_WORLD_FP


def _repo_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[2]


def _default_db_path() -> pathlib.Path:
    """Where learned skills live. Durable by default, because a skill that does not survive a restart
    is not a learned skill -- it is a cache.

    The first implementation put this in ``tempfile.gettempdir()``, which is wiped with the sandbox.
    Measured 2026-11-01: the store was already empty again one session after a full census had
    taught it a rule, so "permanently learned" was literally false. ``canonical/astra_runtime/tmp/``
    is inside the repository (so it survives), is already gitignored (so it never dirties the tree),
    and is the same place the probes keep their fixtures.

    Legacy migration is best effort. This module does not establish indefinite
    retention, power-loss durability, or concurrent legacy-migration safety.
    """
    override = os.environ.get("BRAIN_VERIFIED_SKILL_DB")
    if override:
        p = pathlib.Path(override)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p
    base = _repo_root() / "canonical" / "astra_runtime" / "tmp"
    base.mkdir(parents=True, exist_ok=True)
    target = base / "verified_skills_v1.sqlite"
    legacy = pathlib.Path(tempfile.gettempdir()) / "brain_swe_semantic_graph_v1" / "verified_skills_v1.sqlite"
    if not target.exists() and legacy.is_file():
        try:
            shutil.copy2(legacy, target)
        except OSError:
            pass
    return target


def _malformed_rule_reason(rule: Mapping[str, Any]) -> str | None:
    """Why this payload cannot be applied, or ``None`` if it is a rule the engine understands.

    Checked structurally rather than by trying it on a sample, because a correct rule simply may
    not match an arbitrary sample and "did not apply here" is not "is not a rule".
    """
    if rule.get('pattern_format') not in (None, _PY_EDIT.FORMAT):
        return 'UNKNOWN_PATTERN_FORMAT'
    if rule.get('pattern_format') == _PY_EDIT.FORMAT and rule.get('language') != 'python':
        return 'PYTHON_FORMAT_REQUIRES_PYTHON'
    for field in ("pattern_tokens", "replacement_tokens"):
        tokens = rule.get(field)
        if not isinstance(tokens, list) or not tokens:
            return f"MISSING_{field.upper()}"
        for token in tokens:
            if not (isinstance(token, (list, tuple)) and len(token) == 2):
                return f"MALFORMED_{field.upper()}"
    if not str(rule.get("language") or ""):
        return "MISSING_LANGUAGE"
    return None


def skill_identity(rule: Mapping[str, Any]) -> str:
    """The content address of a rule, recomputed from the rule itself.

    ``anti_unify_code_rule`` derives ``skill_id`` from a canonical blob of (language, error class,
    pattern, replacement). Recomputing it here is what lets an imported bundle be checked instead
    of trusted: an entry whose stated id does not match its own payload is not that rule, and
    admitting it would put someone else's bytes behind a verified rule's identity.
    """
    rule_blob = json.dumps(
        {
            "lang": rule.get("language"),
            "err": rule.get("error_class"),
            "pat": rule.get("pattern_tokens"),
            "rep": rule.get("replacement_tokens"),
            **({'python_edit': {k: rule.get(k) for k in
                 ('pattern_format', 'python_scope', 'parameter_bindings', 'generator', 'asynchronous')}}
               if rule.get('pattern_format') else {}),
        },
        separators=(",", ":"),
    )
    legacy_id = "skill_" + hashlib.sha256(rule_blob.encode("utf-8")).hexdigest()[:16]
    contract = normalize_contract(rule.get('contract'))
    if contract is None:
        return legacy_id
    identity = json.dumps([legacy_id, contract], sort_keys=True, separators=(',', ':'))
    return 'skill_' + hashlib.sha256(identity.encode()).hexdigest()[:24]


def default_origin() -> str:
    """A short, non-secret name for where a rule was learned.

    Machine identity is worth recording because a rule that only works on one image is exactly
    the failure this is meant to expose. It is a hostname and a checkout name, not a path and not
    a credential.
    """
    override = os.environ.get("BRAIN_SKILL_ORIGIN")
    if override:
        return override
    try:
        node = os.uname().nodename
    except Exception:  # pragma: no cover - non-POSIX
        node = "unknown"
    return f"{node}:{_repo_root().name}"


def _seed_bundle_path() -> pathlib.Path:
    """Where the repository ships its lessons, so they reach a machine that has never run anything.

    The SQLite store is gitignored on purpose -- it is generated state. That also means it does not
    travel: a second checkout starts empty, and a checkout inside a fresh sandbox starts empty too.
    Measured 2026-11-01: the store held 6 rules at the end of one session and 0 at the start of the
    next, so "permanently learned" was still false in the only sense a second computer cares about.

    A bundle is small, textual, content-addressed and reviewable, so it can live in version control.
    The database stays the fast local index; the bundle is the memory that ships.
    """
    override = os.environ.get("BRAIN_SKILL_SEED_BUNDLE")
    if override:
        return pathlib.Path(override)
    return _repo_root() / "canonical" / "astra_runtime" / "skills" / "VERIFIED_SKILLS_BUNDLE_V1.json"


def sync_seed_bundle(db_path: pathlib.Path | None = None,
                     bundle_path: pathlib.Path | None = None) -> int:
    """Write the local store's rules to the shipped bundle. Returns the rule count written."""
    store = VerifiedSkillStore(db_path=db_path, seed=False)
    return store.export_to_file(bundle_path or _seed_bundle_path())


def _connect(db_path: pathlib.Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), timeout=10.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS crystallized_skills ("
        "  skill_id TEXT PRIMARY KEY,"
        "  domain TEXT NOT NULL,"
        "  language TEXT NOT NULL,"
        "  error_class TEXT NOT NULL,"
        "  skeleton_fp TEXT NOT NULL,"
        "  pattern_json TEXT NOT NULL,"
        "  created_ts REAL NOT NULL,"
        "  verified_hits INTEGER NOT NULL DEFAULT 1"
        ")"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_skills_lang_err "
        "ON crystallized_skills(domain, language, error_class)"
    )
    # Provenance is appended to the table rather than baked into the primary key, so a store
    # written before provenance existed opens without a migration step.
    have = {r[1] for r in conn.execute("PRAGMA table_info(crystallized_skills)").fetchall()}
    if "provenance_json" not in have:
        conn.execute(
            "ALTER TABLE crystallized_skills ADD COLUMN provenance_json TEXT NOT NULL DEFAULT '[]'"
        )
    conn.execute("CREATE TABLE IF NOT EXISTS skill_store_meta (id INTEGER PRIMARY KEY CHECK(id=1), generation INTEGER NOT NULL)")
    conn.execute("INSERT OR IGNORE INTO skill_store_meta VALUES (1, 0)")
    # Triggers also cover supported direct SQLite writers and row deletion.
    for event, suffix in [('INSERT', 'insert'), ('DELETE', 'delete'), ('UPDATE OF pattern_json', 'pattern_update')]:
        conn.execute(f"CREATE TRIGGER IF NOT EXISTS skills_generation_{suffix} AFTER {event} ON crystallized_skills "
                     "BEGIN UPDATE skill_store_meta SET generation=generation+1 WHERE id=1; END")
    conn.commit()
    return conn


def _load_rules(db_path: pathlib.Path, language: str) -> list[dict[str, Any]]:
    key = f"{db_path.resolve()}::{language}"
    conn = _connect(db_path)
    try:
        # Generation is read from SQLite, not a process-local cache or a new
        # connection's PRAGMA data_version. Other writers/invalidation are visible.
        with conn:
            generation = conn.execute("SELECT generation FROM skill_store_meta WHERE id=1").fetchone()[0]
            st = db_path.stat()
            identity = (st.st_dev, st.st_ino, st.st_ctime_ns, generation)
            cached = _MEM_SKILLS.get(key)
            if cached is not None and cached[0] == identity:
                return cached[1]
            # EVERY STORED LESSON IS READ. THE ORDER SAYS WHICH IS TRIED FIRST, NEVER WHICH EXISTS.
            #
            # This query ended in `LIMIT 128` until 2026-11-11. Measured that day: lessons 1..128,
            # each reused once, kept working; lessons 129, 130 and 131 were stored, reported
            # `crystallized: True`, and could never be recalled, because a reused lesson outranks
            # a new one and the cut came before any lesson was matched against the source. With
            # no reuse at all the cut fell on the other end: of 130 lessons the two oldest were
            # no longer offered. Either way a lesson that was kept was silently never read again.
            #
            # A bound on the work of one recall belongs after matching, where it can be counted
            # and reported, not here, where it decides which lessons exist. Reading all of them
            # costs time in proportion to their number (one sandbox measurement the same day:
            # about 0.9 ms per lesson on a 126-line source when nothing applies) and one
            # verifier call for every candidate a lesson proposes.
            rows = conn.execute(
                "SELECT pattern_json FROM crystallized_skills WHERE domain='swe_code_repair' AND language=? "
                "ORDER BY verified_hits DESC, created_ts DESC", (language,)).fetchall()
            rules = [json.loads(row[0]) for row in rows]
            _MEM_SKILLS[key] = (identity, rules)
            return rules
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 1. Structural Token / AST Anti-Unification & Unification Engine
# ---------------------------------------------------------------------------

def _tokenize_code(snippet: str, *, case_insensitive_kw: bool = False) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    pos = 0
    n = len(snippet)
    while pos < n:
        m = _TOKEN_RE.match(snippet, pos)
        if not m:
            out.append(("other", snippet[pos]))
            pos += 1
            continue
        kind = m.lastgroup or "other"
        val = m.group(0)
        if kind == "ident":
            probe = val.upper() if case_insensitive_kw else val
            if val in _KEYWORDS_KEEP or probe in _KEYWORDS_KEEP:
                kind = "kw"
        out.append((kind, val))
        pos = m.end()
    return out


def _anti_unify_token_rule(
    before_snippet: str,
    after_snippet: str,
    *,
    language: str = "python",
    error_class: str = "GENERIC",
    _prepared: bool = False,
    _python_lex: bool = False,
    _initial_ident_map: dict | None = None,
) -> dict[str, Any] | None:
    """Generalize a concrete `before_snippet -> after_snippet` code fix into a parameterized rule.

    Replaces non-keyword identifiers with relational holes (`?id0`, `?id1`, ...) so any
    identifier appearing in both `before_snippet` and `after_snippet` binds to the SAME
    hole, while new local temporaries introduced only in `after_snippet` receive hygienic
    fresh hole tokens (`?fresh0`).
    """
    before_clean = before_snippet.strip()
    after_clean = after_snippet.strip()
    if not before_clean or not after_clean or before_clean == after_clean:
        return None

    # Minimal changed-hunk extraction (Getafix / Bader et al. OOPSLA 2019):
    # strip identical leading/trailing lines so whole-file or whole-function inputs
    # generalize to the exact local bug hunk rather than over-constraining surrounding lines.
    b_lines = before_clean.splitlines()
    a_lines = after_clean.splitlines()
    if not _prepared and (len(b_lines) > 1 or len(a_lines) > 1):
        p_idx = 0
        while p_idx < len(b_lines) and p_idx < len(a_lines) and b_lines[p_idx] == a_lines[p_idx]:
            p_idx += 1
        s_idx = 0
        while (
            s_idx < (len(b_lines) - p_idx)
            and s_idx < (len(a_lines) - p_idx)
            and b_lines[len(b_lines) - 1 - s_idx] == a_lines[len(a_lines) - 1 - s_idx]
        ):
            s_idx += 1
        b_hunk = "\n".join(b_lines[p_idx : len(b_lines) - s_idx]).strip()
        a_hunk = "\n".join(a_lines[p_idx : len(a_lines) - s_idx]).strip()
        if b_hunk and a_hunk and b_hunk != a_hunk:
            before_clean = b_hunk
            after_clean = a_hunk
    sql_mode = language.lower() == "sql"
    if _python_lex:
        toks_b = [(k, v) for k, v, _, _ in _PY_EDIT.tokens(before_clean, _PYTHON_KEYWORDS_KEEP)]
        toks_a = [(k, v) for k, v, _, _ in _PY_EDIT.tokens(after_clean, _PYTHON_KEYWORDS_KEEP)]
    else:
        toks_b = _tokenize_code(before_clean, case_insensitive_kw=sql_mode)
        toks_a = _tokenize_code(after_clean, case_insensitive_kw=sql_mode)

    ident_map: dict[str, str] = dict(_initial_ident_map or {})
    # IDENTIFIERS WERE NEVER THE ONLY THING A REPAIR GENERALIZES OVER.
    #
    # ``return t - 1`` -> ``return t`` is a repair about an off-by-one, not about the literal 1: the
    # same fix applies to ``- 7``.  Abstracting identifiers only left the number concrete, so the
    # rule matched its own training input and almost nothing else -- measured 2026-11-01 on the
    # five-neighbour probe: 2 of 5 reached, and the two misses were exactly "same shape, different
    # literal" and "same intent, different structure".
    #
    # Literals are relational holes too. Over-generalization is only as safe as
    # the caller's actual behavioral verifier, never guaranteed by a broad match:
    # A weak predicate can still accept an incorrect edit. Strict scoped recall
    # therefore requires a matching current typed oracle, not just a wide pattern.
    hole_maps: dict[str, dict[str, str]] = {"ident": ident_map, "num": {}, "str": {}}
    pattern_tokens: list[tuple[str, str]] = []
    skeleton_parts: list[str] = []

    # A NAME THE FIX REMOVES IS NOT A SHAPE, IT IS A RENAME.
    #
    # Abstracting every identifier on the left turns "`helper` became `helper_v2`" into "any call
    # became `helper_v2`", which is not what was verified. Measured 2026-11-01: a rule taught from
    # `return helper(x) + 1` -> `return helper_v2(x) + 1` rewrote `return acos(r) + 1` into
    # `return helper_v2(r) + 1` -- plausible-looking, completely wrong, and accepted by a
    # compile-only verifier, so it would ship anywhere the tests do not reach the call site.
    #
    # The identifiers that appear in the before-snippet and not in the after-snippet are exactly
    # the ones the fix deliberately replaced, so they stay concrete: the pattern now demands the
    # same name. Such a repair is then name-specific by nature and cannot pass the mutated twin,
    # which is the honest outcome -- "helper became helper_v2" is a fact about a symbol in one
    # repository, not a generalizable structural lesson, and it belongs to a scope-aware rename
    # tool rather than to a rule that claims to have learned a shape.
    after_idents = {val for kind, val in toks_a if kind == "ident"}
    pinned_idents = {val for kind, val in toks_b if kind == "ident" and val not in after_idents}

    for kind, val in toks_b:
        if kind == "ws":
            pattern_tokens.append(("ws", " "))
            continue
        if kind in _HOLE_PREFIX and not (kind == "ident" and val in pinned_idents):
            bucket = hole_maps[kind]
            hole = bucket.setdefault(val, f"{_HOLE_PREFIX[kind]}{len(bucket)}")
            pattern_tokens.append((_HOLE_TOKEN[kind], hole))
            skeleton_parts.append("ID" if kind == "ident" else kind.upper())
        else:
            pattern_tokens.append((kind, val))
            skeleton_parts.append(val.upper() if sql_mode and kind == "kw" else val)

    if not any(hole_maps.values()):
        return None

    fresh_map: dict[str, str] = {}
    replacement_tokens: list[tuple[str, str]] = []
    for kind, val in toks_a:
        if kind == "ws":
            replacement_tokens.append(("ws", val))
        elif kind in _HOLE_PREFIX and val in hole_maps[kind]:
            replacement_tokens.append((_HOLE_TOKEN[kind], hole_maps[kind][val]))
        elif kind == "ident":
            fhole = fresh_map.setdefault(val, f"?fresh{len(fresh_map)}:{val}")
            replacement_tokens.append(("fresh_id", fhole))
        else:
            # A literal the fix INTRODUCES is part of the fix and stays concrete.
            replacement_tokens.append((kind, val))

    skeleton_fp = hashlib.sha256("|".join(skeleton_parts).encode("utf-8")).hexdigest()[:16]
    rule_blob = json.dumps(
        {"lang": language, "err": error_class, "pat": pattern_tokens, "rep": replacement_tokens},
        separators=(",", ":"),
    )
    skill_id = "skill_" + hashlib.sha256(rule_blob.encode("utf-8")).hexdigest()[:16]
    return {
        "skill_id": skill_id,
        "domain": "swe_code_repair",
        "language": language.lower(),
        "error_class": error_class,
        "skeleton_fp": skeleton_fp,
        "hole_count": sum(len(b) for b in hole_maps.values()),
        "pattern_tokens": pattern_tokens,
        "replacement_tokens": replacement_tokens,
    }


def anti_unify_code_rule(before_snippet: str, after_snippet: str, *,
                         language: str = 'python', error_class: str = 'GENERIC'):
    rule = _anti_unify_token_rule(before_snippet, after_snippet,
                                 language=language, error_class=error_class)
    if language.lower() != 'python' or (rule is not None and
            _apply_token_rule(before_snippet, rule) == after_snippet):
        return rule
    return _PY_EDIT.compile_rule(before_snippet, after_snippet, error_class,
                                 _anti_unify_token_rule, skill_identity) or rule


#: The only states in which a stored rule may edit code. `None` is the legacy contract for
#: rules written before the state field existed; a refuted rule always carries the string, so
#: this cannot re-open one. Keep this the single source of truth: recall enforces the same
#: predicate, and callers that had to remember it by hand no longer have to.
APPLICABLE_RULE_STATES = (None, 'ACTIVE')


def rule_is_applicable(rule: Mapping[str, Any]) -> bool:
    """May this stored rule act? A refuted rule may not, in any path."""
    return isinstance(rule, Mapping) and rule.get('state') in APPLICABLE_RULE_STATES


def iter_crystallized_code_rule_candidates(source_text, rule):
    if not rule_is_applicable(rule):
        return
    if rule.get('pattern_format') == _PY_EDIT.FORMAT:
        yield from _PY_EDIT.candidates(source_text, rule, _apply_token_rule)
    elif rule.get('pattern_format') is None:
        yield from _iter_token_rule_candidates(source_text, rule)


def apply_crystallized_code_rule(source_text: str, rule: Mapping[str, Any]) -> str | None:
    """First proposal only; scoped recall verifies bounded alternative locations.

    Returns None for a refuted rule. That is the same contract as "the rule did not fire", so
    every existing caller already handles it -- and it is what makes invalidation mean
    something outside the one recall path that remembered to check by hand.

    Measured before this guard (2026-11-12): a rule refuted by review on a spec counterexample
    still returned `return a < 50` for `return a <= 50`, and
    `software_repair_crossfile_choreograph_v1` offered exactly that as its first repair
    candidate.
    """
    if not rule_is_applicable(rule):
        return None
    return next(iter_crystallized_code_rule_candidates(source_text, rule), None)


def narrow_rule_at_apply_time(rule: Mapping[str, Any]) -> dict[str, Any] | None:
    """PR-C2 apply-time sub-expression narrowing (stored rule stays context-anchored).

    Strips unchanged leading/trailing syntactic frame tokens (such as ``return``)
    down to the minimal changed core plus at most one adjacent operand hole on
    each side, provided every replacement hole remains bound and at least one
    hole and one concrete non-whitespace token remain in the pattern.
    """
    if not rule_is_applicable(rule):
        return None
    pat = [tuple(tok) for tok in (rule.get("pattern_tokens") or [])]
    rep = [tuple(tok) for tok in (rule.get("replacement_tokens") or [])]
    if not pat or not rep:
        return None

    pat_nw = [(idx, tok) for idx, tok in enumerate(pat) if tok[0] != "ws"]
    rep_nw = [(idx, tok) for idx, tok in enumerate(rep) if tok[0] != "ws"]
    if not pat_nw or not rep_nw:
        return None

    p_common = 0
    while p_common < len(pat_nw) and p_common < len(rep_nw) and pat_nw[p_common][1] == rep_nw[p_common][1]:
        p_common += 1

    s_common = 0
    while (
        s_common < (len(pat_nw) - p_common)
        and s_common < (len(rep_nw) - p_common)
        and pat_nw[len(pat_nw) - 1 - s_common][1] == rep_nw[len(rep_nw) - 1 - s_common][1]
    ):
        s_common += 1

    if p_common == 0 and s_common == 0:
        return None

    # Keep one adjacent operand hole around the changed core when available so
    # e.g. `return ?id0 <= ?id1` -> `return ?id0 < ?id1` narrows to
    # `?id0 <= ?id1` -> `?id0 < ?id1` rather than an unanchored `<=` -> `<`.
    # When the adjacent operand is a balanced parenthesized/bracketed compound
    # sub-expression (e.g. `return (?id0 + ?num0) <= (?id1 - ?num0)`), abstract
    # that unchanged compound group into a synthetic operand hole (`?id_lhs` /
    # `?id_rhs`) so compound expressions narrow cleanly instead of losing holes.
    p_strip = p_common
    lhs_synth: tuple[str, str] | None = None
    if p_strip > 0 and pat_nw[p_strip - 1][1][0] in _HOLE_KIND:
        p_strip -= 1
    elif p_strip > 1 and pat_nw[p_strip - 1][1] in (("op", ")"), ("op", "]")):
        close_tok = pat_nw[p_strip - 1][1][1]
        open_tok = "(" if close_tok == ")" else "["
        depth = 0
        open_idx: int | None = None
        for idx in range(p_strip - 1, -1, -1):
            tk = pat_nw[idx][1]
            if tk == ("op", close_tok):
                depth += 1
            elif tk == ("op", open_tok):
                depth -= 1
                if depth == 0:
                    open_idx = idx
                    break
        if open_idx is not None:
            grp_toks = [pat_nw[i][1] for i in range(open_idx, p_strip)]
            if any(k in _HOLE_KIND for k, _ in grp_toks):
                # Distinguish `return (a + 1) <= ...` (operand group) from `int(x <= hi)` (outer call wrapper)
                if not (open_idx > 0 and pat_nw[open_idx - 1][1][0] == "ident"):
                    lhs_synth = ("hole_id", "?id_lhs")

    s_strip = s_common
    rhs_synth: tuple[str, str] | None = None
    rhs_head_idx = len(pat_nw) - s_strip
    if s_strip > 0 and pat_nw[rhs_head_idx][1][0] in _HOLE_KIND:
        s_strip -= 1
    elif s_strip > 1 and pat_nw[rhs_head_idx][1] in (("op", "("), ("op", "[")):
        open_tok = pat_nw[rhs_head_idx][1][1]
        close_tok = ")" if open_tok == "(" else "]"
        depth = 0
        close_idx: int | None = None
        for idx in range(rhs_head_idx, len(pat_nw)):
            tk = pat_nw[idx][1]
            if tk == ("op", open_tok):
                depth += 1
            elif tk == ("op", close_tok):
                depth -= 1
                if depth == 0:
                    close_idx = idx
                    break
        if close_idx is not None:
            grp_toks = [pat_nw[i][1] for i in range(rhs_head_idx, close_idx + 1)]
            if any(k in _HOLE_KIND for k, _ in grp_toks):
                rhs_synth = ("hole_id", "?id_rhs")

    if p_strip == 0 and s_strip == 0:
        return None
    if p_strip + s_strip >= len(pat_nw) or p_strip + s_strip >= len(rep_nw):
        return None

    pat_start = pat_nw[p_strip][0]
    pat_end = pat_nw[len(pat_nw) - 1 - s_strip][0] + 1
    rep_start = rep_nw[p_strip][0]
    rep_end = rep_nw[len(rep_nw) - 1 - s_strip][0] + 1

    new_pat = list(pat[pat_start:pat_end])
    new_rep = list(rep[rep_start:rep_end])
    if lhs_synth is not None:
        new_pat = [lhs_synth, ("ws", " ")] + new_pat
        new_rep = [lhs_synth, ("ws", " ")] + new_rep
    if rhs_synth is not None:
        new_pat = new_pat + [("ws", " "), rhs_synth]
        new_rep = new_rep + [("ws", " "), rhs_synth]
    if new_pat == pat and new_rep == rep:
        return None

    bound_holes = {v for k, v in new_pat if k in _HOLE_KIND}
    needed_holes = {v for k, v in new_rep if k in _HOLE_KIND}
    has_concrete = any(k not in _HOLE_KIND and k != "ws" for k, _ in new_pat)
    if not bound_holes or not has_concrete or not needed_holes.issubset(bound_holes):
        return None

    narrowed = dict(rule)
    narrowed.pop("pattern_format", None)
    narrowed["pattern_tokens"] = new_pat
    narrowed["replacement_tokens"] = new_rep
    return narrowed


def iter_narrowed_rules_at_apply_time(rule: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Yield relational frame-stripped and compound-collapsed narrowed rules at apply time.

    1. When unchanged leading/trailing statement frame tokens (e.g. ``return ``, ``x = ``)
       surround a relational expression whose adjacent compound operand ``(?id0 * ?id1)``
       shares bound holes with the rest of the expression, yield the frame-stripped rule
       preserving the relational compound operand (e.g. ``?id0 + (?id0 * ?id1) -> ?id0 - (?id0 * ?id1)``).
    2. Also yield ``narrow_rule_at_apply_time(rule)`` (compound-operand collapsed ``?id_lhs`` / ``?id_rhs``).
    """
    if not rule_is_applicable(rule):
        return []
    out: list[dict[str, Any]] = []
    pat = [tuple(tok) for tok in (rule.get("pattern_tokens") or [])]
    rep = [tuple(tok) for tok in (rule.get("replacement_tokens") or [])]
    pat_nw = [(idx, tok) for idx, tok in enumerate(pat) if tok[0] != "ws"]
    rep_nw = [(idx, tok) for idx, tok in enumerate(rep) if tok[0] != "ws"]
    if pat_nw and rep_nw:
        p_common = 0
        while p_common < len(pat_nw) and p_common < len(rep_nw) and pat_nw[p_common][1] == rep_nw[p_common][1]:
            p_common += 1
        s_common = 0
        while (
            s_common < (len(pat_nw) - p_common)
            and s_common < (len(rep_nw) - p_common)
            and pat_nw[len(pat_nw) - 1 - s_common][1] == rep_nw[len(rep_nw) - 1 - s_common][1]
        ):
            s_common += 1
        if p_common > 0 or s_common > 0:
            p_rel = p_common
            if p_rel > 0 and pat_nw[p_rel - 1][1][0] in _HOLE_KIND:
                p_rel -= 1
            elif p_rel > 1 and pat_nw[p_rel - 1][1] in (("op", ")"), ("op", "]")):
                close_tok = pat_nw[p_rel - 1][1][1]
                open_tok = "(" if close_tok == ")" else "["
                depth = 0
                for idx in range(p_rel - 1, -1, -1):
                    tk = pat_nw[idx][1]
                    if tk == ("op", close_tok):
                        depth += 1
                    elif tk == ("op", open_tok):
                        depth -= 1
                        if depth == 0:
                            if not (idx > 0 and pat_nw[idx - 1][1][0] == "ident"):
                                p_rel = idx
                            break
            s_rel = s_common
            rhs_head_idx = len(pat_nw) - s_rel
            if s_rel > 0 and pat_nw[rhs_head_idx][1][0] in _HOLE_KIND:
                s_rel -= 1
            elif s_rel > 1 and pat_nw[rhs_head_idx][1] in (("op", "("), ("op", "[")):
                open_tok = pat_nw[rhs_head_idx][1][1]
                close_tok = ")" if open_tok == "(" else "]"
                depth = 0
                for idx in range(rhs_head_idx, len(pat_nw)):
                    tk = pat_nw[idx][1]
                    if tk == ("op", open_tok):
                        depth += 1
                    elif tk == ("op", close_tok):
                        depth -= 1
                        if depth == 0:
                            s_rel = len(pat_nw) - 1 - idx
                            break
            if (p_rel > 0 or s_rel > 0) and (p_rel + s_rel < len(pat_nw)) and (p_rel + s_rel < len(rep_nw)):
                rel_pat = list(pat[pat_nw[p_rel][0] : pat_nw[len(pat_nw) - 1 - s_rel][0] + 1])
                rel_rep = list(rep[rep_nw[p_rel][0] : rep_nw[len(rep_nw) - 1 - s_rel][0] + 1])
                bound_h = {v for k, v in rel_pat if k in _HOLE_KIND}
                needed_h = {v for k, v in rel_rep if k in _HOLE_KIND}
                has_conc = any(k not in _HOLE_KIND and k != "ws" for k, _ in rel_pat)
                if rel_pat != pat and bound_h and has_conc and needed_h.issubset(bound_h):
                    rel_rule = dict(rule)
                    rel_rule.pop("pattern_format", None)
                    rel_rule["pattern_tokens"] = rel_pat
                    rel_rule["replacement_tokens"] = rel_rep
                    out.append(rel_rule)

    collapsed = narrow_rule_at_apply_time(rule)
    if collapsed is not None:
        if not any(
            r.get("pattern_tokens") == collapsed.get("pattern_tokens")
            and r.get("replacement_tokens") == collapsed.get("replacement_tokens")
            for r in out
        ):
            out.append(collapsed)
    return out


def _canonicalize_rule_holes(rule: Mapping[str, Any]) -> dict[str, Any]:
    """Rename holes in appearance order (`?id0, ?id1, ...`) so narrowed rules from distinct statement frames unify."""
    pat = [tuple(t) for t in (rule.get("pattern_tokens") or [])]
    rep = [tuple(t) for t in (rule.get("replacement_tokens") or [])]
    remap: dict[str, str] = {}
    counts: dict[str, int] = {}
    prefix_map = {"hole_id": "?id", "hole_num": "?num", "hole_str": "?str"}
    new_pat: list[tuple[str, str]] = []
    for k, v in pat:
        if k in prefix_map and v not in ("?id_lhs", "?id_rhs"):
            if v not in remap:
                idx = counts.get(k, 0)
                counts[k] = idx + 1
                remap[v] = f"{prefix_map[k]}{idx}"
            new_pat.append((k, remap[v]))
        else:
            new_pat.append((k, v))
    new_rep: list[tuple[str, str]] = [
        (k, remap.get(v, v)) if k in prefix_map else (k, v)
        for k, v in rep
    ]
    out = dict(rule)
    out["pattern_tokens"] = new_pat
    out["replacement_tokens"] = new_rep
    return out


def anti_unify_code_rule_pair(
    before_1: str,
    after_1: str,
    before_2: str,
    after_2: str,
    *,
    language: str = "python",
    error_class: str = "GENERIC",
) -> dict[str, Any] | None:
    """Plotkin LGG across two code repair demonstrations (including distinct statement frames)."""
    r1 = anti_unify_code_rule(before_1, after_1, language=language, error_class=error_class)
    r2 = anti_unify_code_rule(before_2, after_2, language=language, error_class=error_class)
    if r1 is None or r2 is None:
        return None
    cands_1 = [_canonicalize_rule_holes(r1)] + [_canonicalize_rule_holes(x) for x in iter_narrowed_rules_at_apply_time(r1)]
    cands_2 = [_canonicalize_rule_holes(r2)] + [_canonicalize_rule_holes(x) for x in iter_narrowed_rules_at_apply_time(r2)]
    sig_2 = {
        (
            tuple((k, v) for k, v in c["pattern_tokens"] if k != "ws"),
            tuple((k, v) for k, v in c["replacement_tokens"] if k != "ws"),
        ): c
        for c in cands_2
    }
    for c1 in cands_1:
        key = (
            tuple((k, v) for k, v in c1["pattern_tokens"] if k != "ws"),
            tuple((k, v) for k, v in c1["replacement_tokens"] if k != "ws"),
        )
        if key in sig_2:
            if (
                after_1.strip() in {s.strip() for s in _iter_token_rule_candidates(before_1, c1)}
                and after_2.strip() in {s.strip() for s in _iter_token_rule_candidates(before_2, c1)}
            ):
                return c1
    return None


def _iter_token_rule_candidates(
    source_text: str,
    rule: Mapping[str, Any],
    *,
    _python_lex: bool = False,
    _initial_bindings: Mapping[str, str] | None = None,
    _anchored: bool = False,
):
    """Yield single-site rewrite candidates matching ``rule['pattern_tokens']``."""
    sql_mode = str(rule.get("language") or "") == "sql"
    pat_non_ws = [(k, v) for k, v in (rule.get("pattern_tokens") or []) if k != "ws"]
    if not pat_non_ws:
        return

    src_tokens: list[tuple[str, str, int, int]] = []
    if _python_lex:
        src_tokens = [(k, v, a, b) for k, v, a, b in _PY_EDIT.tokens(source_text, _PYTHON_KEYWORDS_KEEP) if k != 'ws']
    else:
        pos = 0
        n = len(source_text)
        while pos < n:
            m = _TOKEN_RE.match(source_text, pos)
            if not m:
                src_tokens.append(("other", source_text[pos], pos, pos + 1))
                pos += 1
                continue
            kind = m.lastgroup or "other"
            val = m.group(0)
            if kind == "ident":
                probe = val.upper() if sql_mode else val
                if val in _KEYWORDS_KEEP or probe in _KEYWORDS_KEEP:
                    kind = "kw"
            if kind != "ws":
                src_tokens.append((kind, val, m.start(), m.end()))
            pos = m.end()
    plen = len(pat_non_ws)
    if len(src_tokens) < plen:
        return

    existing_idents = {val for kind, val, _, _ in src_tokens if kind == "ident"}
    yielded: set[str] = set()

    for start_idx in range(1 if _anchored else len(src_tokens) - plen + 1):
        bindings: dict[str, str] = dict(_initial_bindings or {})
        matched = True
        src_idx = start_idx
        for pk, pv in pat_non_ws:
            if src_idx >= len(src_tokens):
                matched = False
                break
            sk, sv, s_start, _ = src_tokens[src_idx]
            if pk in _HOLE_KIND:
                if sk == _HOLE_KIND[pk]:
                    bound_val = sv
                    src_idx += 1
                elif (
                    pv in ("?id_lhs", "?id_rhs")
                    and sk == "op"
                    and sv in ("(", "[")
                    and not (src_idx > 0 and src_tokens[src_idx - 1][0] == "ident")
                ):
                    close_ch = ")" if sv == "(" else "]"
                    depth = 0
                    close_idx: int | None = None
                    for scan_i in range(src_idx, len(src_tokens)):
                        tk_k, tk_v, _, _ = src_tokens[scan_i]
                        if tk_k == "op" and tk_v == sv:
                            depth += 1
                        elif tk_k == "op" and tk_v == close_ch:
                            depth -= 1
                            if depth == 0:
                                close_idx = scan_i
                                break
                    if close_idx is None:
                        matched = False
                        break
                    bound_val = source_text[s_start : src_tokens[close_idx][3]]
                    src_idx = close_idx + 1
                else:
                    matched = False
                    break
                prev = bindings.get(pv)
                if prev is not None and prev != bound_val:
                    matched = False
                    break
                bindings[pv] = bound_val
            elif pk == "kw" and sql_mode:
                if sk != "kw" or sv.upper() != pv.upper():
                    matched = False
                    break
                src_idx += 1
            else:
                if sk != pk or sv != pv:
                    matched = False
                    break
                src_idx += 1
        if not matched or src_idx <= start_idx:
            continue

        span_start = src_tokens[start_idx][2]
        span_end = src_tokens[src_idx - 1][3]
        line_start = source_text.rfind("\n", 0, span_start) + 1
        indent = ""
        for ch in source_text[line_start:span_start]:
            if ch in (" ", "\t"):
                indent += ch
            else:
                break

        fresh_bindings: dict[str, str] = {}
        out_parts: list[str] = []
        for rk, rv in rule.get("replacement_tokens") or []:
            if rk in _HOLE_KIND:
                bound = bindings.get(rv)
                if bound is None:
                    matched = False
                    break
                out_parts.append(bound)
            elif rk == "fresh_id":
                if rv not in fresh_bindings:
                    base_name = rv.split(":", 1)[1] if ":" in rv else "_tmp"
                    cand = base_name
                    suffix = 1
                    while cand in existing_idents or cand in bindings.values():
                        cand = f"{base_name}_{suffix}"
                        suffix += 1
                    fresh_bindings[rv] = cand
                out_parts.append(fresh_bindings[rv])
            elif rk == "ws" and "\n" in rv:
                out_parts.append(rv if _python_lex else "\n" + indent)
            else:
                out_parts.append(rv)
        if not matched:
            continue

        replacement = "".join(out_parts)
        if _python_lex:
            lines = replacement.splitlines(keepends=True)
            replacement = ''.join(line if i == 0 or not line.strip() else indent + line
                                  for i, line in enumerate(lines))
        candidate = source_text[:span_start] + replacement + source_text[span_end:]
        if candidate != source_text and candidate not in yielded:
            yielded.add(candidate)
            yield candidate


def _apply_token_rule(source_text: str, rule: Mapping[str, Any], *,
                      _python_lex=False, _initial_bindings=None, _anchored=False) -> str | None:
    """Match ``rule['pattern_tokens']`` against ``source_text`` via unification and rewrite."""
    return next(
        _iter_token_rule_candidates(
            source_text,
            rule,
            _python_lex=_python_lex,
            _initial_bindings=_initial_bindings,
            _anchored=_anchored,
        ),
        None,
    )


# ---------------------------------------------------------------------------
# 2. Mutated-Twin Counterfeit Filter (Rejects Rote Memorization)
# ---------------------------------------------------------------------------

def _alpha_mutate_snippet(snippet: str, *, language: str = "python", preserve_builtins: bool = False) -> tuple[str, dict[str, str]]:
    """Alpha-rename every non-keyword identifier to a distinct synthetic name."""
    if language.lower() == 'python':
        # The polyglot regex does not understand Python bytes/raw prefixes,
        # exponent literals, comments, or every Python keyword. Renaming those
        # produced invalid twins for real modules despite valid repair rules.
        # Use the standard lexer; leave literal/comment bytes untouched.
        lines=snippet.splitlines(keepends=True)
        offsets=[0]
        for line in lines:
            offsets.append(offsets[-1]+len(line))
        rename_map={}
        edits=[]
        try:
            for token in tokenize.generate_tokens(io.StringIO(snippet).readline):
                name=token.string
                if (token.type==tokenize.NAME and name not in (_PYTHON_KEYWORDS_KEEP if preserve_builtins else _KEYWORDS_KEEP)
                        and not keyword.iskeyword(name) and not keyword.issoftkeyword(name)
                        and not (preserve_builtins and name in _PY_EDIT.BUILTINS)):
                    replacement=rename_map.setdefault(name,f"_twin_sym_{len(rename_map)}_{name[:4]}")
                    edits.append((offsets[token.start[0]-1]+token.start[1],
                                  offsets[token.end[0]-1]+token.end[1],replacement))
        except (tokenize.TokenError,IndentationError):
            return snippet,{}
        pieces=[]
        position=0
        for start,end,replacement in edits:
            pieces.extend((snippet[position:start],replacement))
            position=end
        pieces.append(snippet[position:])
        return ''.join(pieces),rename_map
    sql_mode = language.lower() == "sql"
    toks = _tokenize_code(snippet, case_insensitive_kw=sql_mode)
    rename_map: dict[str, str] = {}
    out: list[str] = []
    for kind, val in toks:
        if kind == "ident":
            mut = rename_map.setdefault(val, f"_twin_sym_{len(rename_map)}_{val[:4]}")
            out.append(mut)
        else:
            out.append(val)
    return "".join(out), rename_map


def verify_rule_on_mutated_twin(
    before_snippet: str,
    rule: Mapping[str, Any],
    twin_oracle: Callable[[str], bool] | None = None,
    expected_after_snippet: str | None = None,
) -> bool:
    """Check transport to a constructed alpha-renamed twin, not project semantics."""
    lang = str(rule.get("language") or "python")
    scoped = rule.get("pattern_format") == _PY_EDIT.FORMAT
    mutated_before, rename_map = _alpha_mutate_snippet(before_snippet, language=lang, preserve_builtins=scoped)
    if not rename_map or mutated_before == before_snippet:
        return False
    if scoped and expected_after_snippet is not None:
        expected = _PY_EDIT.renamed(expected_after_snippet, rename_map, _PYTHON_KEYWORDS_KEEP)
        rewritten = next((c for c in itertools.islice(iter_crystallized_code_rule_candidates(mutated_before, rule), 64)
                          if c == expected), None)
    else:
        rewritten = apply_crystallized_code_rule(mutated_before, rule)
    if not rewritten or rewritten == mutated_before:
        return False
    # Anti-memorization invariant: no original identifier may leak into the mutated twin's output.
    if lang == 'python':
        try:
            rewritten_idents={token.string for token in tokenize.generate_tokens(io.StringIO(rewritten).readline)
                              if token.type==tokenize.NAME}
        except (tokenize.TokenError,IndentationError):
            return False
    else:
        rewritten_idents = {val for kind,val in _tokenize_code(rewritten,case_insensitive_kw=(lang=='sql'))
                            if kind=='ident'}
    for orig_name in rename_map:
        if orig_name in rewritten_idents and orig_name not in rename_map.values():
            return False
    if lang == "python":
        try:
            ast.parse(rewritten)
        except SyntaxError:
            return False
    if twin_oracle is not None and evaluate(twin_oracle, rewritten) is None:
        return False
    return True


# ---------------------------------------------------------------------------
# 3. Persistent SQLite WAL Verified Skill Store
# ---------------------------------------------------------------------------

def _merge_taught_sources(retained: dict[str, Any], incoming_rule: Mapping[str, Any]) -> None:
    """Preserve and union `provenance.taught_sources` across re-teaching and bundle imports."""
    inc_prov = incoming_rule.get("provenance")
    if not isinstance(inc_prov, Mapping):
        return
    ret_prov = retained.get("provenance")
    merged_prov: dict[str, Any] = dict(ret_prov) if isinstance(ret_prov, Mapping) else {}
    existing_sources: list[dict[str, str]] = []
    for src in (merged_prov.get("taught_sources") or ()):
        if isinstance(src, Mapping) and "before" in src:
            pair = {"before": str(src["before"]), "after": str(src.get("after") or "")}
            if pair not in existing_sources:
                existing_sources.append(pair)
    one = merged_prov.get("training_example")
    if isinstance(one, Mapping) and "before" in one:
        pair = {"before": str(one["before"]), "after": str(one.get("after") or "")}
        if pair not in existing_sources:
            existing_sources.append(pair)
    for src in (inc_prov.get("taught_sources") or ()):
        if isinstance(src, Mapping) and "before" in src:
            pair = {"before": str(src["before"]), "after": str(src.get("after") or "")}
            if pair not in existing_sources:
                existing_sources.append(pair)
    inc_one = inc_prov.get("training_example")
    if isinstance(inc_one, Mapping) and "before" in inc_one:
        pair = {"before": str(inc_one["before"]), "after": str(inc_one.get("after") or "")}
        if pair not in existing_sources:
            existing_sources.append(pair)
    if existing_sources:
        merged_prov["taught_sources"] = existing_sources
    for sha_key in ("before_sha256", "after_sha256"):
        if not merged_prov.get(sha_key) and inc_prov.get(sha_key):
            merged_prov[sha_key] = inc_prov[sha_key]
    if merged_prov:
        retained["provenance"] = merged_prov


class VerifiedSkillStore:
    """SQLite WAL store of scoped hypotheses; retrieval always re-verifies."""

    def __init__(self, db_path: pathlib.Path | None = None, *, seed: bool = True) -> None:
        self.db_path = db_path or _default_db_path()
        self.seed_result: dict[str, Any] | None = None
        if seed and not pathlib.Path(self.db_path).exists():
            # A first run on a machine that has never learned anything: start from what the
            # repository already knows rather than from nothing.
            seed_path = _seed_bundle_path()
            if seed_path.is_file():
                try:
                    self.seed_result = self.import_bundle(seed_path)
                except Exception as exc:  # a bad seed must not make learning impossible
                    self.seed_result = {"accepted": 0, "merged": 0, "refused": 1,
                                        "refusals": [{"skill_id": None,
                                                      "reason": type(exc).__name__}]}

    def crystallize_code_fix(
        self,
        *,
        before_snippet: str,
        after_snippet: str,
        language: str,
        error_class: str = "GENERIC",
        twin_oracle: Callable[[str], bool] | None = None,
        contract: Mapping[str, Any] | None = None,
        training_verifier: Callable | None = None,
        origin: str | None = None,
        precondition_field: str | None = None,
        precondition_accessor: Callable[[str], Any] | None = None,
        oracle: Callable[[str, Any], Any] | None = None,
        probes: Sequence[Any] | None = None,
        admission_victims: Sequence[Any] | None = None,
        admission_archive: Sequence[Any] | None = None,
        localize_lesson: bool = False,
    ) -> dict[str, Any]:
        from canonical.runtime.memory_policy_v1 import can_write_memory

        if not can_write_memory():
            return {"crystallized": False, "reason": "MEMORY_POLICY_WRITE_DISABLED"}
        precondition_evidence: dict[str, Any] | None = None
        if precondition_field is not None or precondition_accessor is not None:
            from canonical.swe_kernel import skill_precondition_presence_v1 as _precond

            gate_out = _precond.gate(
                before_snippet,
                after_snippet,
                field=precondition_field or "observable",
                accessor=precondition_accessor,
            )
            if not gate_out.get("may_learn"):
                return {
                    "crystallized": False,
                    "reason": f"PRECONDITION_DEFECT_{gate_out.get('verdict')}",
                    "precondition": gate_out,
                }
            precondition_evidence = {
                "field": gate_out.get("field"),
                "verdict": gate_out.get("verdict"),
                "before": gate_out.get("before"),
                "after": gate_out.get("after"),
            }
        contract = normalize_contract(contract)
        training = None
        if contract is not None:
            if training_verifier is None:
                return {"crystallized": False, "reason": "SCOPED_SKILL_REQUIRES_TRAINING_VERIFIER"}
            try:
                baseline = training_verifier(before_snippet)
            except Exception:
                return {"crystallized": False, "reason": "TRAINING_BASELINE_UNAVAILABLE"}
            if (not isinstance(baseline, VerificationResult) or baseline.passed is not False
                    or baseline.kind != contract['verification_kind']
                    or baseline.scope_id != contract['scope_id']
                    or baseline.candidate_sha256 != source_sha256(before_snippet)):
                return {"crystallized": False, "reason": "FAILING_SCOPED_TRAINING_BASELINE_REQUIRED"}
            if baseline.kind == 'TEST_SUITE' and (baseline.evidence.get('test_count', 0) <= 0
                                                   or baseline.evidence.get('returncode') == 0):
                return {"crystallized": False, "reason": "TRAINING_BASELINE_DID_NOT_EXECUTE_FAILING_TESTS"}
            training = evaluate(training_verifier, after_snippet, contract['verification_kind'], contract['scope_id'])
            if training is None:
                return {"crystallized": False, "reason": "TRAINING_VERIFICATION_FAILED"}
        elif training_verifier is not None:
            raise ValueError('TRAINING_VERIFIER_REQUIRES_SCOPE_CONTRACT')

        lesson_before = before_snippet
        lesson_after = after_snippet
        localization_record: dict[str, Any] | None = None
        causal_sufficiency: dict[str, Any] | None = None
        localized_line_span: tuple[int, int] | None = None
        if localize_lesson:
            from canonical.swe_kernel import lesson_localization_v1 as _loc

            localized = _loc.localize_operator_lesson(
                before_snippet, after_snippet, language=language
            )
            if localized.status != _loc.LOCALIZED or localized.chosen is None:
                return {
                    "crystallized": False,
                    "reason": f"LESSON_LOCALIZATION_{localized.status}",
                    "localization": {
                        "status": localized.status,
                        "reason": localized.reason,
                        "regions_examined": localized.regions_examined,
                    },
                }
            lesson_before = localized.chosen.before_statement
            lesson_after = localized.chosen.after_statement
            localized_line_span = tuple(localized.chosen.before_lines)
            localization_record = {
                "schema": _loc.SCHEMA,
                "status": localized.status,
                "swap": dict(localized.chosen.swap),
                "before_lines": list(localized.chosen.before_lines),
                "after_lines": list(localized.chosen.after_lines),
                "regions_examined": localized.regions_examined,
                "incidental_regions_ignored": max(0, localized.regions_examined - 1),
            }

        rule = anti_unify_code_rule(
            lesson_before,
            lesson_after,
            language=language,
            error_class=error_class,
        )
        if rule is None:
            return {"crystallized": False, "reason": "NON_GENERALIZABLE_SNIPPET"}
        twin_evidence = {'kind': 'STRUCTURAL_TWIN', 'whole_task_correctness_proved': False}
        def observe_twin(candidate):
            nonlocal twin_evidence
            result = evaluate(twin_oracle, candidate)
            if result is not None:
                twin_evidence = result
            return result is not None
        if not verify_rule_on_mutated_twin(lesson_before, rule, twin_oracle=observe_twin if twin_oracle else None,
                                           expected_after_snippet=lesson_after):
            return {"crystallized": False, "reason": "FAILED_MUTATED_TWIN_VERIFICATION"}

        if contract is not None:
            whole_cands = list(itertools.islice(
                iter_crystallized_code_rule_candidates(before_snippet, rule), 64
            ))
            if not localize_lesson:
                if not any(c == after_snippet for c in whole_cands):
                    return {"crystallized": False, "reason": "RULE_DOES_NOT_REPRODUCE_VERIFIED_EXAMPLE"}
            else:
                if not whole_cands:
                    return {"crystallized": False, "reason": "RULE_DOES_NOT_FIRE_ON_WHOLE_BEFORE"}
                if localized_line_span is not None:
                    lo_ln, hi_ln = localized_line_span
                    def _in_localized_span(cand_text: str) -> int:
                        off = next((i for i, (ca, cb) in enumerate(zip(before_snippet, cand_text)) if ca != cb), len(before_snippet))
                        ln = before_snippet[:off].count("\n") + 1
                        return 0 if lo_ln <= ln <= hi_ln else 1
                    whole_cands.sort(key=_in_localized_span)
                verified_cand: str | None = None
                verified_causal: dict[str, Any] | None = None
                for cand_text in whole_cands[:16]:
                    ver_c = evaluate(
                        training_verifier,
                        cand_text,
                        contract['verification_kind'],
                        contract['scope_id'],
                    )
                    if ver_c is not None:
                        verified_cand = cand_text
                        verified_causal = ver_c
                        break
                if verified_cand is None or verified_causal is None:
                    return {
                        "crystallized": False,
                        "reason": "LOCALIZED_LESSON_NOT_CAUSALLY_SUFFICIENT",
                        "candidates_checked": min(len(whole_cands), 16),
                        "localization": localization_record,
                    }
                causal_sufficiency = {
                    "verified": True,
                    "minimal_candidate_sha256": source_sha256(verified_cand),
                    "incidental_edits_stripped": verified_cand != after_snippet,
                    "verification": verified_causal,
                }
        if oracle is not None or probes is not None:
            from canonical.tools import rule_generalization_probe_v1 as _probe

            probe_out = _probe.probe_rule(
                lesson_before,
                lesson_after,
                oracle=oracle,
                probes=probes,
                victim_snippet=lesson_before,
                rule=rule,
            )
            if probe_out.get("verdict") != _probe.HOLDS:
                return {
                    "crystallized": False,
                    "reason": f"ORACLE_PROBE_{probe_out.get('verdict')}:{probe_out.get('reason')}",
                    "oracle_probe": probe_out,
                }
            rule["oracle_probe"] = {
                "verdict": probe_out["verdict"],
                "probes_checked": len(probe_out.get("probes") or ()),
                # The learn path passes the TAUGHT snippet as the victim, so this probe shows the
                # edit reproduces itself. It executes no unseen program. Say so in the record
                # instead of letting "HOLDS" be read as generalization.
                "victim_was_taught_snippet": True,
                "held_out_programs_executed": 0,
            }
        # ADMISSION: what does this lesson do to programs it was never taught on? Measured
        # 2026-11-13: with `oracle` + `probes` alone the store admitted an ACTIVE boundary rule
        # that repaired one unseen program and BROKE another that was already right, on four
        # executions of the demonstration and zero of anything else. When a caller supplies
        # victims, that execution happens here, before the write.
        from canonical.swe_kernel import lesson_admission_gate_v1 as _admission

        if admission_victims or admission_archive:
            admission_report = _admission.evaluate(
                lesson_before,
                lesson_after,
                victims=admission_victims or (),
                archive=admission_archive or (),
                rule=rule,
                language=language,
            )
            if admission_report.get("verdict") != _admission.ADMIT:
                return {
                    "crystallized": False,
                    "reason": f"ADMISSION_{admission_report.get('verdict')}:{admission_report.get('reason')}",
                    "admission": admission_report,
                }
            rule["admission"] = _admission.record_for_store(admission_report)
        else:
            rule["admission"] = dict(_admission.UNGATED_RECORD)
        if precondition_evidence is not None:
            rule["precondition_presence"] = precondition_evidence
        if localization_record is not None:
            rule["localization"] = localization_record
        if causal_sufficiency is not None:
            rule["causal_sufficiency"] = causal_sufficiency
        rule['record_version'] = 1
        rule['state'] = 'ACTIVE'
        rule['contract'] = contract
        rule['parameters'] = sorted({(kind, name) for kind, name in rule['pattern_tokens'] if kind.startswith('hole_')})
        rule['training_verification'] = training or {'kind': 'NOT_VERIFIED', 'whole_task_correctness_proved': False}
        rule['twin_verification'] = twin_evidence
        if contract is not None:
            rule['training_baseline'] = {'passed': False, 'kind': baseline.kind, 'scope_id': baseline.scope_id,
                                         'candidate_sha256': baseline.candidate_sha256, 'evidence': dict(baseline.evidence)}
        # A HASH OF THE DEMONSTRATION IS HISTORY; THE DEMONSTRATION ITSELF IS WHAT CAN BE RE-RUN.
        #
        # Measured 2026-11-12: `before_sha256`/`after_sha256` identify the source a rule was
        # taught on but cannot reproduce it, so a stored rule could never be shown to still
        # apply -- 5 of 5 stored rules had no re-executable source at all
        # (`canonical/swe_kernel/skill_recheck_v1.py` reports ABSENT). Keeping the text makes a
        # rule re-checkable; the hash is kept beside it so the two can be compared.
        provenance_record: dict[str, Any] = {
            'before_sha256': source_sha256(lesson_before),
            'after_sha256': source_sha256(lesson_after),
            'taught_sources': [{'before': lesson_before, 'after': lesson_after}],
        }
        if localize_lesson:
            provenance_record['whole_before_sha256'] = source_sha256(before_snippet)
            provenance_record['whole_after_sha256'] = source_sha256(after_snippet)
        rule['provenance'] = provenance_record
        from canonical.swe_kernel import skill_recheck_v1 as _recheck

        recheck_out = _recheck.recheck(rule)
        if recheck_out.get("verdict") != _recheck.PASS:
            return {
                "crystallized": False,
                "reason": f"SKILL_RECHECK_{recheck_out.get('verdict')}:{recheck_out.get('reason')}",
                "recheck": recheck_out,
            }
        if contract is not None:
            rule['skill_id'] = skill_identity(rule)
        conn = _connect(self.db_path)
        try:
            with conn:
                entry = {
                    "origin": origin or default_origin(),
                    "at": round(time.time(), 3),
                    "hits": 1,
                }
                # Re-learning a rule on a second machine is evidence about BOTH machines, so the
                # provenance grows instead of the newest origin overwriting the older one.
                row = conn.execute(
                    "SELECT provenance_json, pattern_json FROM crystallized_skills WHERE skill_id = ?",
                    (rule["skill_id"],),
                ).fetchone()
                try:
                    provenance = json.loads(row[0]) if row and row[0] else []
                except (TypeError, ValueError):
                    provenance = []
                if not any(isinstance(p, Mapping) and p.get("origin") == entry["origin"
                           ] for p in provenance):
                    provenance.append(entry)
                rule_to_store: dict[str, Any] = dict(rule)
                if row and row[1]:
                    try:
                        existing_rule = json.loads(row[1])
                    except (TypeError, ValueError):
                        existing_rule = None
                    if isinstance(existing_rule, dict):
                        _merge_taught_sources(existing_rule, rule)
                        for preserve_key in (
                            "record_version",
                            "parameters",
                            "training_verification",
                            "twin_verification",
                            "training_baseline",
                            "precondition_presence",
                            "localization",
                            "causal_sufficiency",
                            "oracle_probe",
                            "admission",
                        ):
                            if preserve_key in rule and preserve_key not in existing_rule:
                                existing_rule[preserve_key] = rule[preserve_key]
                        # Stronger admission evidence upgrades a weaker record; it never
                        # downgrades one. An ungated row that is later shown on held-out
                        # programs should say so.
                        from canonical.swe_kernel import lesson_admission_gate_v1 as _adm

                        if (rule.get("admission", {}).get("verdict") == _adm.ADMIT
                                and existing_rule.get("admission", {}).get("verdict") != _adm.ADMIT):
                            existing_rule["admission"] = rule["admission"]
                        if existing_rule.get("state") != "INVALIDATED":
                            existing_rule["state"] = rule.get("state", "ACTIVE")
                        rule_to_store = existing_rule
                conn.execute(
                    "INSERT INTO crystallized_skills "
                    "(skill_id, domain, language, error_class, skeleton_fp, pattern_json, created_ts, verified_hits, provenance_json) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) "
                    "ON CONFLICT(skill_id) DO UPDATE SET verified_hits = verified_hits + excluded.verified_hits, "
                    "provenance_json = excluded.provenance_json, pattern_json = excluded.pattern_json",
                    (
                        rule["skill_id"],
                        rule["domain"],
                        rule["language"],
                        rule["error_class"],
                        rule["skeleton_fp"],
                        json.dumps(rule_to_store, separators=(",", ":")),
                        time.time(),
                        int(training is not None),
                        json.dumps(provenance, separators=(",", ":")),
                    ),
                )
                stored = json.loads(conn.execute("SELECT pattern_json FROM crystallized_skills WHERE skill_id=?", (rule['skill_id'],)).fetchone()[0])
        finally:
            conn.close()

        mem_key = f"{self.db_path.resolve()}::{rule['language']}"
        _MEM_SKILLS.pop(mem_key, None)
        out = {
            "crystallized": True,
            "skill_id": rule["skill_id"],
            "skeleton_fp": rule["skeleton_fp"],
            "hole_count": rule["hole_count"],
            "state": stored.get('state', 'ACTIVE'),
            "training_verification": stored.get('training_verification', {'kind': 'LEGACY_UNSCOPED'}),
            "twin_verification": stored.get('twin_verification', {'kind': 'LEGACY_UNSCOPED'}),
            "whole_task_correctness_proved": False,
        }
        if localization_record is not None:
            out["localization"] = localization_record
        if causal_sufficiency is not None:
            out["causal_sufficiency"] = causal_sufficiency
        return out

    def update_learned_scope(
        self,
        skill_id: str,
        learned_scope: str,
        *,
        audit: Mapping[str, Any] | None = None,
    ) -> bool:
        """Persist `rule_scope_learning_v1` calibrated `[G_-, B_+]` version-space bounds on `skill_id`."""
        valid_scopes = {"SCOPE_STATEMENT", "SCOPE_EXPRESSION", "SCOPE_OPERATOR", "SCOPE_SEMANTIC", "SCOPE_ALGEBRAIC"}
        if learned_scope not in valid_scopes or not skill_id:
            return False
        from canonical.runtime.memory_policy_v1 import can_write_memory

        if not can_write_memory():
            return False
        conn = _connect(self.db_path)
        updated = False
        lang_key: str | None = None
        try:
            with conn:
                conn.execute("BEGIN IMMEDIATE")
                row = conn.execute(
                    "SELECT language, pattern_json FROM crystallized_skills WHERE skill_id = ?",
                    (skill_id,),
                ).fetchone()
                if row is not None:
                    lang_key = str(row[0] or "")
                    rule_obj = json.loads(row[1])
                    rule_obj["learned_scope"] = learned_scope
                    rule_obj["version_space_bounds"] = {
                        "narrow_g_minus": "SCOPE_STATEMENT",
                        "broad_b_plus": learned_scope,
                        "b_plus_requires": "TEST_SUITE",
                    }
                    if isinstance(audit, Mapping):
                        rule_obj["scope_calibration"] = {
                            "result": audit.get("result"),
                            "scope": learned_scope,
                            "observations_used": audit.get("observations_used"),
                        }
                    conn.execute(
                        "UPDATE crystallized_skills SET pattern_json = ? WHERE skill_id = ?",
                        (json.dumps(rule_obj, sort_keys=True), skill_id),
                    )
                    updated = True
        finally:
            conn.close()
        if updated and lang_key is not None:
            _MEM_SKILLS.pop(f"{self.db_path.resolve()}::{lang_key}", None)
        return updated

    def record_permanence_witnesses(
        self,
        skill_id: str,
        *,
        distinct_inputs: int,
        distinct_outputs: int,
    ) -> bool:
        """Record `permanence_amplifies_check_v1` non-constant witness counts on `skill_id`."""
        if not skill_id:
            return False
        from canonical.runtime.memory_policy_v1 import can_write_memory

        if not can_write_memory():
            return False
        conn = _connect(self.db_path)
        updated = False
        lang_key: str | None = None
        try:
            with conn:
                conn.execute("BEGIN IMMEDIATE")
                row = conn.execute(
                    "SELECT language, pattern_json FROM crystallized_skills WHERE skill_id = ?",
                    (skill_id,),
                ).fetchone()
                if row is not None:
                    lang_key = str(row[0] or "")
                    rule_obj = json.loads(row[1])
                    rule_obj["permanence_witnesses"] = {
                        "distinct_inputs": int(distinct_inputs),
                        "distinct_outputs": int(distinct_outputs),
                        "nonconstant_amplified": bool(distinct_inputs >= 2 and distinct_outputs >= 2),
                    }
                    conn.execute(
                        "UPDATE crystallized_skills SET pattern_json = ? WHERE skill_id = ?",
                        (json.dumps(rule_obj, sort_keys=True), skill_id),
                    )
                    updated = True
        finally:
            conn.close()
        if updated and lang_key is not None:
            _MEM_SKILLS.pop(f"{self.db_path.resolve()}::{lang_key}", None)
        return updated

    def recall_and_apply_verified(
        self,
        *,
        source_text: str,
        language: str,
        verifier: Callable[[str], bool],
        error_class: str | None = None,
        required_verification_kind: str = 'CALLER_PREDICATE',
        scope_id: str = '',
        context: Mapping[str, Any] | None = None,
        allow_operator_generalization: bool = False,
        allow_scope_escalation: bool = False,
        allow_cross_language: bool = True,
        allow_cross_scope_transfer: bool = False,
        now_world_fingerprint: Mapping[str, Any] | None = None,
        suspect_lines: Sequence[int] | None = None,
        prior_sources: Sequence[str] | None = None,
        precondition_accessor: Callable[[str], Any] | None = None,
    ) -> dict[str, Any] | None:
        """Propose only within recorded applicability and actual current assurance.

        Callbacks are trusted verifiers, not authenticated third-party attestations.
        Boolean callbacks never establish TEST_SUITE or whole-task correctness.
        Operator generalization is opt-in and requires scoped TEST_SUITE evidence.
        """
        if required_verification_kind not in KINDS:
            raise ValueError('UNKNOWN_VERIFICATION_KIND')
        if type(allow_operator_generalization) is not bool:
            raise ValueError('INVALID_OPERATOR_GENERALIZATION_SETTING')
        if type(allow_scope_escalation) is not bool:
            raise ValueError('INVALID_SCOPE_ESCALATION_SETTING')
        if type(allow_cross_scope_transfer) is not bool:
            raise ValueError('INVALID_CROSS_SCOPE_TRANSFER_SETTING')
        if allow_operator_generalization and (required_verification_kind != 'TEST_SUITE' or not scope_id or language.lower() != 'python'):
            raise ValueError('OPERATOR_GENERALIZATION_REQUIRES_SCOPED_PYTHON_TEST_SUITE')
        if allow_scope_escalation and (required_verification_kind != 'TEST_SUITE' or not scope_id):
            raise ValueError('SCOPE_ESCALATION_REQUIRES_SCOPED_TEST_SUITE')
        if allow_cross_scope_transfer and (required_verification_kind != 'TEST_SUITE' or not scope_id):
            raise ValueError('CROSS_SCOPE_TRANSFER_REQUIRES_SCOPED_TEST_SUITE')

        from canonical.runtime.memory_policy_v1 import can_read_memory, can_write_memory

        substrate_unavailable = False
        substrate_reason = ""
        if not can_read_memory():
            return None

        eff_suspect_lines: list[int] = [
            int(ln) for ln in (suspect_lines or ()) if isinstance(ln, int) and ln > 0
        ]
        if not eff_suspect_lines and isinstance(context, Mapping):
            raw_sl = context.get("suspect_lines")
            if isinstance(raw_sl, Sequence) and not isinstance(raw_sl, (str, bytes)):
                eff_suspect_lines = [int(ln) for ln in raw_sl if isinstance(ln, int) and ln > 0]

        eff_prior_sources: list[str] = [str(s) for s in (prior_sources or ()) if isinstance(s, str)]
        if not eff_prior_sources and isinstance(context, Mapping):
            raw_ps = context.get("prior_sources")
            if isinstance(raw_ps, Sequence) and not isinstance(raw_ps, (str, bytes)):
                eff_prior_sources = [str(s) for s in raw_ps if isinstance(s, str)]

        eff_precond_accessor = precondition_accessor
        if eff_precond_accessor is None and isinstance(context, Mapping):
            cand_acc = context.get("precondition_accessor")
            if callable(cand_acc):
                eff_precond_accessor = cand_acc

        lang = language.lower()
        rules = _load_rules(self.db_path, lang)

        # Consult `rule_expiry_v1` stamps: any explicitly stamped rule whose environment moved (`STALE`)
        # is skipped until re-verified; unstamped (`UNKNOWN`) records keep historical compatibility.
        stale_ids: set[str] = set()
        if rules:
            try:
                from canonical.swe_kernel import rule_expiry_v1 as _expiry

                audit_rep = _expiry.audit(
                    self.db_path,
                    skill_ids=[str(r.get("skill_id") or "") for r in rules if r.get("skill_id")],
                    now=now_world_fingerprint or _current_world_fp(),
                )
                stale_ids = {
                    str(row["skill_id"])
                    for row in (audit_rep.get("rules") or [])
                    if row.get("state") == _expiry.STALE
                }
            except Exception:
                stale_ids = set()

        ordered = rules
        if error_class:
            ordered = (
                [r for r in rules if r.get("error_class") == error_class]
                + [r for r in rules if r.get("error_class") != error_class]
            )

        def _commit_verified_hit(
            rule: dict[str, Any],
            candidate: str,
            verification: dict[str, Any],
            scope_tier: str,
            recall_strategy: str,
        ) -> dict[str, Any] | None:
            conn = _connect(self.db_path)
            try:
                if can_write_memory():
                    with conn:
                        # Verification can take seconds. Do not return an artifact
                        # invalidated/deleted by another writer while it was running.
                        conn.execute('BEGIN IMMEDIATE')
                        live = conn.execute('SELECT pattern_json FROM crystallized_skills WHERE skill_id=?', (rule['skill_id'],)).fetchone()
                        if live is None or json.loads(live[0]) != rule:
                            return None
                        conn.execute(
                            "UPDATE crystallized_skills SET verified_hits = verified_hits + 1 WHERE skill_id = ?",
                            (rule["skill_id"],),
                        )
                else:
                    live = conn.execute('SELECT pattern_json FROM crystallized_skills WHERE skill_id=?', (rule['skill_id'],)).fetchone()
                    if live is None or json.loads(live[0]) != rule:
                        return None
            finally:
                conn.close()
            return {
                "skill_id": rule["skill_id"],
                "skeleton_fp": rule["skeleton_fp"],
                "patched_source": candidate,
                "from_crystallized_memory": True,
                "scope_tier": scope_tier,
                "recall_strategy": recall_strategy,
                "verification": verification,
                "whole_task_correctness_proved": False,
            }

        is_py_project_oracle = (
            required_verification_kind == "TEST_SUITE"
            and lang == "python"
            and hasattr(verifier, "root")
            and hasattr(verifier, "target_path")
            and hasattr(verifier, "test_paths")
        )

        def _try_candidate_batch(
            rule: dict[str, Any],
            stream: Any,
            seen_candidates: set[str],
            scope_tier: str,
            recall_strategy: str,
            *,
            limit: int = 16,
        ) -> tuple[dict[str, Any] | None, bool]:
            batch: list[str] = []
            for cand in itertools.islice(stream, limit):
                if cand is None or cand in seen_candidates:
                    continue
                seen_candidates.add(cand)
                if eff_precond_accessor is not None:
                    from canonical.swe_kernel import skill_precondition_presence_v1 as _precond

                    rec_pre = rule.get("precondition_presence") if isinstance(rule.get("precondition_presence"), Mapping) else {}
                    pre_out = _precond.defect_is_present(
                        source_text,
                        cand,
                        field=str(rec_pre.get("field") or "observable"),
                        accessor=eff_precond_accessor,
                    )
                    if pre_out.get("verdict") not in _precond.PERMITS_LEARNING:
                        continue
                    if "before" in rec_pre and rec_pre.get("before") is not None:
                        exp_before = tuple(rec_pre["before"]) if isinstance(rec_pre["before"], list) else rec_pre["before"]
                        got_before = tuple(pre_out.get("before")) if isinstance(pre_out.get("before"), list) else pre_out.get("before")
                        if got_before != exp_before:
                            continue
                batch.append(cand)
            if not batch:
                return None, False

            eval_list = batch
            if is_py_project_oracle and scope_tier != "SCOPE_STATEMENT" and len(batch) >= 4:
                try:
                    from canonical.swe_kernel.zygote_worker_pool_v1 import screen_python_candidates_cow

                    screen = screen_python_candidates_cow(
                        verifier.root,  # type: ignore[attr-defined]
                        verifier.target_path,  # type: ignore[attr-defined]
                        verifier.test_paths,  # type: ignore[attr-defined]
                        batch,
                        stop_on_first_pass=True,
                    )
                    if screen.get("ok") and screen.get("screen_authoritative"):
                        eval_list = [batch[i] for i in (screen.get("passing_indices") or []) if 0 <= i < len(batch)]
                except Exception:
                    eval_list = batch

            for cand in eval_list:
                verification = evaluate(verifier, cand, required_verification_kind, scope_id)
                if verification is not None:
                    hit = _commit_verified_hit(rule, cand, verification, scope_tier, recall_strategy)
                    if hit is not None:
                        return hit, False
                    return None, True
            return None, False

        from canonical.swe_kernel import skill_recheck_v1 as _recheck

        for rule in ordered:
            if str(rule.get("skill_id") or "") in stale_ids:
                continue
            if rule.get('state') not in (None, 'ACTIVE') or not applicable(
                rule.get('contract'), scope_id, context, allow_cross_scope=allow_cross_scope_transfer
            ):
                continue
            if _recheck._rule_sources(rule):
                if _recheck.recheck(rule).get("verdict") == _recheck.FAIL:
                    continue
            elif _recheck.self_witness(rule).get("verdict") == _recheck.FAIL:
                continue
            recorded = rule.get('contract')
            if required_verification_kind != 'CALLER_PREDICATE' and (recorded is None or rule.get('record_version') != 1):
                continue
            if recorded is not None and recorded['verification_kind'] != required_verification_kind:
                continue

            learned_scope = str(rule.get("learned_scope") or "SCOPE_ALGEBRAIC")
            seen_candidates: set[str] = {source_text, *eff_prior_sources}
            invalidated_mid_run = False

            # Stage 1 (`SCOPE_STATEMENT`): fast direct context-anchored unification (< 100 us)
            hit, invalidated_mid_run = _try_candidate_batch(
                rule,
                iter_crystallized_code_rule_candidates(source_text, rule),
                seen_candidates,
                "SCOPE_STATEMENT",
                "statement",
            )
            if hit is not None:
                return hit

            # Stage 1B (`SCOPE_EXPRESSION` / PR-C2 + CST Minimal-Subtree): apply-time
            # sub-expression narrowing & compound-operand CST hole generalization.
            # Stored rule remains context-anchored; weak verifiers (`CALLER_PREDICATE`,
            # `SYNTAX`, `COMPILATION`) NEVER receive broadened patterns.
            if (
                not invalidated_mid_run
                and required_verification_kind == "TEST_SUITE"
                and learned_scope != "SCOPE_STATEMENT"
            ):
                for narrowed in iter_narrowed_rules_at_apply_time(rule):
                    hit, invalidated_mid_run = _try_candidate_batch(
                        rule,
                        _iter_token_rule_candidates(source_text, narrowed),
                        seen_candidates,
                        "SCOPE_EXPRESSION",
                        "narrowed_pattern",
                    )
                    if hit is not None:
                        return hit
                    if invalidated_mid_run:
                        break
                if not invalidated_mid_run:
                    try:
                        from canonical.swe_kernel.tree_sitter_cst_skill_skeleton_v1 import (
                            iter_cst_skeleton_candidates,
                        )

                        hit, invalidated_mid_run = _try_candidate_batch(
                            rule,
                            iter_cst_skeleton_candidates(
                                source_text,
                                rule,
                                target_language=lang,
                                max_candidates=16,
                                minimize=True,
                                suspect_lines=eff_suspect_lines,
                            ),
                            seen_candidates,
                            "SCOPE_EXPRESSION",
                            "cst_minimal_subtree",
                        )
                        if hit is not None:
                            return hit
                    except Exception:
                        pass

            # Stage 2 (`SCOPE_OPERATOR` / `SCOPE_SEMANTIC` / `SCOPE_ALGEBRAIC`): unified scoped
            # TEST_SUITE generalization (single path; impossible under CALLER_PREDICATE).
            if (
                not invalidated_mid_run
                and (allow_operator_generalization or allow_scope_escalation)
                and learned_scope in ("SCOPE_OPERATOR", "SCOPE_SEMANTIC", "SCOPE_ALGEBRAIC")
            ):
                from canonical.swe_kernel import operator_generalization_v1 as _op_gen

                hit, invalidated_mid_run = _try_candidate_batch(
                    rule,
                    _op_gen.propose_operator_swaps(source_text, rule, language=lang),
                    seen_candidates,
                    "SCOPE_OPERATOR",
                    "operator_generalization",
                )
                if hit is not None:
                    return hit
                if (
                    not invalidated_mid_run
                    and lang == "python"
                    and learned_scope in ("SCOPE_SEMANTIC", "SCOPE_ALGEBRAIC")
                ):
                    from canonical.swe_kernel import boundary_disjunction_normalization_v1 as _bd_norm

                    try:
                        sem_stream = _bd_norm.propose_semantic_swaps(
                            source_text,
                            rule,
                            operator_swaps=_op_gen.propose_operator_swaps,
                        )
                        sem_strategy = "operator_generalization" if allow_operator_generalization else "semantic"
                        hit, invalidated_mid_run = _try_candidate_batch(
                            rule,
                            sem_stream,
                            seen_candidates,
                            "SCOPE_SEMANTIC",
                            sem_strategy,
                        )
                        if hit is not None:
                            return hit
                    except (_bd_norm.NormalizationError, SyntaxError, ValueError):
                        pass
                if (
                    not invalidated_mid_run
                    and allow_scope_escalation
                    and lang == "python"
                    and learned_scope == "SCOPE_ALGEBRAIC"
                ):
                    try:
                        from canonical.swe_kernel.egraph_and_deductive_synthesizer_v1 import (
                            propose_egraph_algebraic_rewrites,
                        )

                        hit, _ = _try_candidate_batch(
                            rule,
                            propose_egraph_algebraic_rewrites(source_text, rule),
                            seen_candidates,
                            "SCOPE_ALGEBRAIC",
                            "algebraic",
                            limit=32,
                        )
                        if hit is not None:
                            return hit
                    except Exception:
                        pass

        # Stage 4: Cross-language portable carry (`language_neutral_skill_bridge_v1` +
        # 7-language Tree-Sitter CST skeleton `tree_sitter_cst_skill_skeleton_v1`).
        # Supported under legacy unscoped `CALLER_PREDICATE` and under contract-checked
        # `TEST_SUITE` (`ProjectTestOracle` / `ConfinedLanguageTestOracle`).
        if allow_cross_language and required_verification_kind == 'TEST_SUITE' and scope_id:
            try:
                from canonical.swe_kernel.tree_sitter_cst_skill_skeleton_v1 import (
                    recall_across_languages_cst,
                )

                def _valid_scoped_cross_rule(r: Mapping[str, Any]) -> bool:
                    if r.get("state") not in (None, "ACTIVE"):
                        return False
                    if str(r.get("learned_scope") or "SCOPE_ALGEBRAIC") == "SCOPE_STATEMENT":
                        return False
                    rec = r.get("contract")
                    if rec is None or r.get("record_version") != 1:
                        return False
                    if rec.get("verification_kind") != "TEST_SUITE":
                        return False
                    return applicable(rec, scope_id, context, allow_cross_scope=allow_cross_scope_transfer)

                last_verified_by_cand: dict[str, dict[str, Any]] = {}

                def _scoped_cst_verifier(cand: str) -> bool:
                    v = evaluate(verifier, cand, "TEST_SUITE", scope_id)
                    if v is not None:
                        last_verified_by_cand[cand] = v
                        return True
                    return False

                cst_hit = recall_across_languages_cst(
                    self,
                    source_text=source_text,
                    target_language=lang,
                    verifier=_scoped_cst_verifier,
                    error_class=error_class,
                    minimize=True,
                    suspect_lines=eff_suspect_lines,
                    rule_filter=_valid_scoped_cross_rule,
                )
                if cst_hit is None and error_class is not None:
                    cst_hit = recall_across_languages_cst(
                        self,
                        source_text=source_text,
                        target_language=lang,
                        verifier=_scoped_cst_verifier,
                        error_class=None,
                        minimize=True,
                        suspect_lines=eff_suspect_lines,
                        rule_filter=_valid_scoped_cross_rule,
                    )
                if cst_hit is not None:
                    cand = str(cst_hit["patched_source"])
                    verification = last_verified_by_cand.get(cand) or evaluate(
                        verifier, cand, "TEST_SUITE", scope_id
                    )
                    if verification is not None:
                        src_lang = str(cst_hit.get("from_language") or "")
                        sid = str(cst_hit.get("skill_id") or "")
                        src_rules = [r for r in _load_rules(self.db_path, src_lang) if r.get("skill_id") == sid]
                        if src_rules:
                            committed = _commit_verified_hit(
                                src_rules[0],
                                cand,
                                verification,
                                "CROSS_LANGUAGE_CST_SKELETON",
                                "cross_language_cst_minimal_subtree",
                            )
                            if committed is not None:
                                committed["from_cross_language_memory"] = True
                                committed["from_language"] = src_lang
                                committed["to_language"] = cst_hit.get("to_language")
                                return committed
            except Exception:
                pass

        if allow_cross_language and required_verification_kind == 'CALLER_PREDICATE' and not scope_id:
            try:
                from canonical.swe_kernel import language_neutral_skill_bridge_v1 as _bridge

                def _typed_bool_verifier(cand: str) -> bool:
                    return evaluate(verifier, cand, required_verification_kind, scope_id) is not None

                bridged = _bridge.recall_across_languages(
                    self,
                    source_text=source_text,
                    target_language=lang,
                    verifier=_typed_bool_verifier,
                    error_class=error_class,
                )
                if bridged is None and error_class is not None:
                    bridged = _bridge.recall_across_languages(
                        self,
                        source_text=source_text,
                        target_language=lang,
                        verifier=_typed_bool_verifier,
                        error_class=None,
                    )
                if bridged is not None:
                    cand = str(bridged["patched_source"])
                    verification = evaluate(verifier, cand, required_verification_kind, scope_id)
                    if verification is not None:
                        return {
                            "skill_id": bridged.get("skill_id"),
                            "skeleton_fp": "",
                            "patched_source": cand,
                            "from_crystallized_memory": True,
                            "from_cross_language_memory": True,
                            "from_language": bridged.get("from_language"),
                            "to_language": bridged.get("to_language"),
                            "scope_tier": "CROSS_LANGUAGE_LEXICAL_BRIDGE",
                            "recall_strategy": "cross_language_lexical",
                            "verification": verification,
                            "whole_task_correctness_proved": False,
                        }
            except Exception:
                pass

            # Stage 4B: Tree-Sitter 7-language CST node-type skeleton carry (`tree_sitter_cst_skill_skeleton_v1`)
            # Bridges Rust block tail-expressions (no `return`) and structural idioms (`len(x)` <-> `x.len()` / `x.length` / `x.size()`).
            try:
                from canonical.swe_kernel.tree_sitter_cst_skill_skeleton_v1 import (
                    CstSubstrateUnavailable,
                    recall_across_languages_cst,
                )

                def _cst_bool_verifier(cand: str) -> bool:
                    return evaluate(verifier, cand, required_verification_kind, scope_id) is not None

                cst_hit = recall_across_languages_cst(
                    self,
                    source_text=source_text,
                    target_language=lang,
                    verifier=_cst_bool_verifier,
                    error_class=error_class,
                    rule_filter=rule_is_applicable,
                )
                if cst_hit is None and error_class is not None:
                    cst_hit = recall_across_languages_cst(
                        self,
                        source_text=source_text,
                        target_language=lang,
                        verifier=_cst_bool_verifier,
                        error_class=None,
                        rule_filter=rule_is_applicable,
                    )
                if cst_hit is not None:
                    cand = str(cst_hit["patched_source"])
                    verification = evaluate(verifier, cand, required_verification_kind, scope_id)
                    if verification is not None:
                        return {
                            "skill_id": cst_hit.get("skill_id"),
                            "skeleton_fp": "",
                            "patched_source": cand,
                            "from_crystallized_memory": True,
                            "from_cross_language_memory": True,
                            "from_language": cst_hit.get("from_language"),
                            "to_language": cst_hit.get("to_language"),
                            "scope_tier": "CROSS_LANGUAGE_CST_SKELETON",
                            "recall_strategy": "cross_language_cst",
                            "verification": verification,
                            "whole_task_correctness_proved": False,
                        }
            except CstSubstrateUnavailable as exc:
                # The cross-language capability needs an importable Tree-Sitter substrate. Absent,
                # nothing was measured, so this must not read as "the lesson did not transfer".
                substrate_unavailable = True
                substrate_reason = str(exc) or "TREE_SITTER_SUBSTRATE_MISSING"
            except Exception:
                pass
        if substrate_unavailable:
            return {"substrate_unavailable": True, "reason": substrate_reason,
                    "measured": False, "capability": "CROSS_LANGUAGE_CST_SKELETON",
                    "remedy": "python3 scripts/restore_substrate_v1.py"}
        return None

    def narrow_rule_scope(
        self,
        skill_id: str,
        instances: list[Mapping[str, Any]],
        verifier: Callable[[str], bool] | None = None,
        *,
        observation_limit: int | None = None,
    ) -> dict[str, Any]:
        """Active version-space narrowing via `rule_scope_learning_v1` (`finite_capability_diagnosis.select_probe`)."""
        from canonical.swe_kernel import rule_scope_learning_v1 as _scope_learner

        conn = _connect(self.db_path)
        try:
            row = conn.execute(
                "SELECT pattern_json FROM crystallized_skills WHERE skill_id = ?",
                (skill_id,),
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            return {"ok": False, "reason": "SKILL_NOT_FOUND", "skill_id": skill_id}
        rule = json.loads(row[0])
        report = _scope_learner.learn_scope(
            rule,
            instances,
            verifier=verifier,
            observation_limit=observation_limit,
        )
        if report.get("result") == "MODEL_FALSIFIED":
            self.invalidate(skill_id, "RULE_SCOPE_MODEL_FALSIFIED")
            return {**report, "ok": True, "persisted_state": "INVALIDATED"}
        resolved_scope = report.get("scope")
        if resolved_scope:
            conn = _connect(self.db_path)
            try:
                with conn:
                    cur_row = conn.execute(
                        "SELECT pattern_json FROM crystallized_skills WHERE skill_id = ?",
                        (skill_id,),
                    ).fetchone()
                    if cur_row is not None:
                        cur_rule = json.loads(cur_row[0])
                        cur_rule["learned_scope"] = resolved_scope
                        conn.execute(
                            "UPDATE crystallized_skills SET pattern_json = ? WHERE skill_id = ?",
                            (json.dumps(cur_rule, separators=(",", ":")), skill_id),
                        )
                        conn.execute("UPDATE skill_store_meta SET generation = generation + 1 WHERE id=1")
            finally:
                conn.close()
            for key in [k for k in _MEM_SKILLS if k.startswith(f"{self.db_path.resolve()}::")]:
                _MEM_SKILLS.pop(key, None)
        return {**report, "ok": True, "persisted_scope": resolved_scope}

    def refine_scope_from_counterexample(
        self,
        skill_id: str,
        instance: Mapping[str, Any],
        verifier: Callable[[str], bool],
    ) -> dict[str, Any]:
        """Specialize over-broad rules to narrower sound scopes on counterexamples (`rule_scope_learning_v1`), invalidating only if `SCOPE_STATEMENT` itself misfires."""
        from canonical.swe_kernel import rule_scope_learning_v1 as _rsl

        conn = _connect(self.db_path)
        try:
            row = conn.execute(
                "SELECT pattern_json FROM crystallized_skills WHERE skill_id = ?",
                (skill_id,),
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            return {"ok": False, "reason": "SKILL_NOT_FOUND", "skill_id": skill_id}
        rule = json.loads(row[0])

        stmt_out = _rsl.predicted_outcome("SCOPE_STATEMENT", rule, instance, verifier=verifier)
        op_out = _rsl.predicted_outcome("SCOPE_OPERATOR", rule, instance, verifier=verifier)
        sem_out = _rsl.predicted_outcome("SCOPE_SEMANTIC", rule, instance, verifier=verifier)

        if stmt_out == _rsl.PROPOSES_UNVERIFIED:
            self.invalidate(skill_id, f"COUNTEREXAMPLE_AT_SCOPE_STATEMENT:{instance.get('label', 'instance')}")
            return {
                "ok": True,
                "skill_id": skill_id,
                "action": "INVALIDATED",
                "persisted_state": "INVALIDATED",
                "outcomes": {"SCOPE_STATEMENT": stmt_out, "SCOPE_OPERATOR": op_out, "SCOPE_SEMANTIC": sem_out},
            }

        target_scope: str | None = None
        if op_out == _rsl.PROPOSES_UNVERIFIED and stmt_out == _rsl.SILENT:
            target_scope = "SCOPE_STATEMENT"
        elif sem_out == _rsl.PROPOSES_UNVERIFIED and op_out == _rsl.SILENT:
            target_scope = "SCOPE_OPERATOR"

        if target_scope is not None:
            conn = _connect(self.db_path)
            try:
                with conn:
                    cur_row = conn.execute(
                        "SELECT pattern_json FROM crystallized_skills WHERE skill_id = ?",
                        (skill_id,),
                    ).fetchone()
                    if cur_row is not None:
                        cur_rule = json.loads(cur_row[0])
                        cur_rule["learned_scope"] = target_scope
                        cur_rule.setdefault("counterexamples", []).append(
                            {"label": str(instance.get("label") or ""), "narrowed_to": target_scope}
                        )
                        conn.execute(
                            "UPDATE crystallized_skills SET pattern_json = ? WHERE skill_id = ?",
                            (json.dumps(cur_rule, separators=(",", ":")), skill_id),
                        )
                        conn.execute("UPDATE skill_store_meta SET generation = generation + 1 WHERE id=1")
            finally:
                conn.close()
            for key in [k for k in _MEM_SKILLS if k.startswith(f"{self.db_path.resolve()}::")]:
                _MEM_SKILLS.pop(key, None)
            return {
                "ok": True,
                "skill_id": skill_id,
                "action": "SPECIALIZED_SCOPE",
                "persisted_scope": target_scope,
                "outcomes": {"SCOPE_STATEMENT": stmt_out, "SCOPE_OPERATOR": op_out, "SCOPE_SEMANTIC": sem_out},
            }

        return self.narrow_rule_scope(skill_id, [instance], verifier=verifier)

    # ------------------------------------------------------------------ portability
    # A store inside one checkout is durable but not portable: a second computer starts empty and
    # two machines that learn for a month cannot pool anything. A bundle is the transport, and the
    # Imported rules remain hypotheses. Content addressing is not independent
    # verification; weak predicates may still accept wrong proposals. Strict scoped
    # recall requires current typed evidence, and imports cannot clear invalidation.

    def export_bundle(self) -> dict[str, Any]:
        """Every rule in this store, with provenance, as one JSON-serializable document."""
        conn = _connect(self.db_path)
        try:
            rows = conn.execute(
                "SELECT skill_id, domain, language, error_class, skeleton_fp, pattern_json, "
                "created_ts, verified_hits, provenance_json FROM crystallized_skills "
                "ORDER BY skill_id"
            ).fetchall()
        finally:
            conn.close()
        rules = []
        for sid, domain, language, error_class, skeleton_fp, pattern_json, created_ts, hits, prov in rows:
            try:
                pattern = json.loads(pattern_json)
            except (TypeError, ValueError):
                continue  # a store row that cannot be parsed is reported by count(), never exported
            try:
                provenance = json.loads(prov or "[]")
            except (TypeError, ValueError):
                provenance = []
            rules.append({
                "skill_id": sid,
                "domain": domain,
                "language": language,
                "error_class": error_class,
                "skeleton_fp": skeleton_fp,
                "created_ts": created_ts,
                "verified_hits": hits,
                "provenance": provenance,
                "rule": pattern,
            })
        return {
            "schema": BUNDLE_SCHEMA,
            "origin": default_origin(),
            "exported_ts": round(time.time(), 3),
            "rule_count": len(rules),
            "rules": rules,
        }

    def export_to_file(self, path: str | pathlib.Path) -> int:
        bundle = self.export_bundle()
        target = pathlib.Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(bundle, indent=1, sort_keys=True), encoding="utf-8")
        return int(bundle["rule_count"])

    def import_bundle(self, bundle: Mapping[str, Any] | str | pathlib.Path) -> dict[str, Any]:
        """Merge a bundle into this store. Content-addressed, idempotent, and fail-closed per entry.

        Merge rules, each chosen because the alternative loses information:

        * identity is the recomputed content address, so the same lesson learned on two machines
          collapses instead of duplicating;
        * ``verified_hits`` takes the maximum rather than the sum, because the two counts may
          describe the same evidence;
        * provenance is the union, so a rule that fails later can be traced to the machine it came
          from -- including this one;
        * an entry that is malformed, mis-addressed, or not applicable is refused *by name* and
          counted, never dropped silently, and never aborts the rest of the bundle.
        """
        if isinstance(bundle, (str, pathlib.Path)):
            bundle = json.loads(pathlib.Path(bundle).read_text(encoding="utf-8"))
        schema = str(bundle.get("schema") or "")
        if schema != BUNDLE_SCHEMA:
            return {"accepted": 0, "merged": 0, "refused": 1,
                    "refusals": [{"skill_id": None, "reason": f"BUNDLE_SCHEMA_{schema or 'MISSING'}"}]}

        accepted = 0
        merged = 0
        refusals: list[dict[str, Any]] = []
        conn = _connect(self.db_path)
        try:
            for entry in bundle.get("rules") or []:
                rule = entry.get("rule") if isinstance(entry, Mapping) else None
                stated = entry.get("skill_id") if isinstance(entry, Mapping) else None
                if not isinstance(rule, Mapping):
                    refusals.append({"skill_id": stated, "reason": "NO_RULE_PAYLOAD"})
                    continue
                reason = _malformed_rule_reason(rule)
                if reason:
                    refusals.append({"skill_id": stated, "reason": reason})
                    continue
                try:
                    identity_matches = skill_identity(rule) == stated
                except (ValueError, TypeError):
                    identity_matches = False
                if not identity_matches:
                    refusals.append({"skill_id": stated, "reason": "CONTENT_ADDRESS_MISMATCH"})
                    continue
                # Metadata is not covered by the rule's content address. Validate before
                # touching SQLite: one malformed count/time must not abort later lessons or
                # poison a merge. Canonical counters fit SQLite's signed INTEGER exactly.
                hits = entry.get("verified_hits", 1)
                if isinstance(hits, bool) or not isinstance(hits, int) or not 0 <= hits < (1 << 63):
                    refusals.append({"skill_id": stated, "reason": "INVALID_VERIFIED_HITS"})
                    continue
                raw_created = entry.get("created_ts")
                if raw_created is None:
                    created = time.time()
                else:
                    try:
                        if isinstance(raw_created, bool) or not isinstance(raw_created, (int, float)):
                            raise ValueError("timestamp is not numeric")
                        created = float(raw_created)
                        if not math.isfinite(created) or created < 0:
                            raise ValueError("timestamp is not finite and nonnegative")
                    except (TypeError, ValueError, OverflowError):
                        refusals.append({"skill_id": stated, "reason": "INVALID_CREATED_TS"})
                        continue
                prov = entry.get("provenance") or []
                existing = conn.execute(
                    "SELECT verified_hits, created_ts, provenance_json, pattern_json FROM crystallized_skills "
                    "WHERE skill_id = ?", (stated,)
                ).fetchone()
                if existing is None:
                    with conn:
                        conn.execute(
                            "INSERT INTO crystallized_skills (skill_id, domain, language, error_class, "
                            "skeleton_fp, pattern_json, created_ts, verified_hits, provenance_json) "
                            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (
                                stated,
                                str(entry.get("domain") or rule.get("domain") or "swe_code_repair"),
                                str(entry.get("language") or rule.get("language") or ""),
                                str(entry.get("error_class") or rule.get("error_class") or "GENERIC"),
                                str(entry.get("skeleton_fp") or rule.get("skeleton_fp") or ""),
                                json.dumps(rule, separators=(",", ":")),
                                created, hits,
                                json.dumps(prov, separators=(",", ":")),
                            ),
                        )
                    accepted += 1
                else:
                    old_hits, old_created, old_prov, old_pattern = existing
                    # Transported counterexamples may invalidate a live record;
                    # an older active bundle must never reactivate local invalidation.
                    retained = json.loads(old_pattern)
                    _merge_taught_sources(retained, rule)
                    if rule.get('state') == 'INVALIDATED':
                        retained['state'] = 'INVALIDATED'
                        counterexamples = retained.setdefault('counterexamples', [])
                        for counterexample in rule.get('counterexamples', []):
                            if counterexample not in counterexamples:
                                counterexamples.append(counterexample)
                    try:
                        known = json.loads(old_prov or "[]")
                    except (TypeError, ValueError):
                        known = []
                    seen = {(p.get("origin"), p.get("at")) for p in known if isinstance(p, Mapping)}
                    for item in prov:
                        if isinstance(item, Mapping) and (item.get("origin"), item.get("at")) not in seen:
                            known.append(item)
                            seen.add((item.get("origin"), item.get("at")))
                    with conn:
                        conn.execute(
                            "UPDATE crystallized_skills SET verified_hits = ?, created_ts = ?, "
                            "provenance_json = ?, pattern_json = ? WHERE skill_id = ?",
                            (max(int(old_hits), hits), min(float(old_created), created),
                             json.dumps(known, separators=(",", ":")),
                             json.dumps(retained, separators=(",", ":")), stated),
                        )
                    merged += 1
        finally:
            conn.close()
        # Any cached rule list for this store is now stale; a stale cache would hide an import.
        for key in [k for k in _MEM_SKILLS if k.startswith((f"{self.db_path}::", f"{self.db_path.resolve()}::"))]:
            _MEM_SKILLS.pop(key, None)
        return {"accepted": accepted, "merged": merged,
                "refused": len(refusals), "refusals": refusals}

    def import_from_file(self, path: str | pathlib.Path) -> dict[str, Any]:
        return self.import_bundle(path)

    def provenance(self) -> list[dict[str, Any]]:
        """Every rule with where it came from -- the audit a merged store needs."""
        conn = _connect(self.db_path)
        try:
            rows = conn.execute(
                "SELECT skill_id, language, verified_hits, provenance_json FROM crystallized_skills "
                "ORDER BY skill_id"
            ).fetchall()
        finally:
            conn.close()
        out = []
        for sid, language, hits, prov in rows:
            try:
                origins = json.loads(prov or "[]")
            except (TypeError, ValueError):
                origins = []
            out.append({"skill_id": sid, "language": language, "verified_hits": hits,
                        "origins": origins})
        return out

    def count(self) -> int:
        conn = _connect(self.db_path)
        try:
            row = conn.execute("SELECT COUNT(*) FROM crystallized_skills").fetchone()
            return int(row[0]) if row else 0
        finally:
            conn.close()

    def lookup_rules(self, language: str, error_class: str | None = None) -> list[dict[str, Any]]:
        lang = language.lower()
        rules = _load_rules(self.db_path, lang)
        if error_class:
            rules = [r for r in rules if r.get('error_class') == error_class]
        return copy.deepcopy(rules)

    def invalidate(self, skill_id: str, reason: str, *, counterexample_sha256: str = '') -> bool:
        """Retain the rule/counterexample but forbid subsequent application."""
        if not reason.strip():
            raise ValueError('INVALIDATION_REASON_REQUIRED')
        conn = _connect(self.db_path)
        try:
            with conn:
                row = conn.execute('SELECT pattern_json FROM crystallized_skills WHERE skill_id=?', (skill_id,)).fetchone()
                if row is None:
                    return False
                rule = json.loads(row[0])
                rule['state'] = 'INVALIDATED'
                rule.setdefault('counterexamples', []).append({'reason': reason[:2000], 'candidate_sha256': counterexample_sha256})
                conn.execute('UPDATE crystallized_skills SET pattern_json=? WHERE skill_id=?', (json.dumps(rule), skill_id))
                conn.execute('UPDATE skill_store_meta SET generation = generation + 1 WHERE id=1')
                return True
        finally:
            conn.close()

    def audit_sequence_interference(
        self,
        source_text: str,
        *,
        language: str,
        error_class: str | None = None,
    ) -> dict[str, Any]:
        """Run `skill_sequence_verify_v1.verify_all_pairs` over active stored rules."""
        from canonical.swe_kernel import skill_sequence_verify_v1 as _seq

        active = [
            r for r in self.lookup_rules(language, error_class=error_class)
            if r.get("state") in (None, "ACTIVE")
        ]
        return _seq.verify_all_pairs(source_text, active)

    def apply_verified_sequence(
        self,
        *,
        source_text: str,
        language: str,
        verifier: Callable[[str], bool],
        rules: Sequence[Mapping[str, Any]] | None = None,
        error_class: str | None = None,
        max_steps: int = 4,
    ) -> dict[str, Any]:
        """Apply a sequence of rules verified by both `skill_sequence_verify_v1` and `verifier`."""
        from canonical.swe_kernel import skill_sequence_verify_v1 as _seq

        if rules is not None:
            seq_out = _seq.verify_sequence(source_text, rules)
            if seq_out.get("verdict") != _seq.PASS:
                return {**seq_out, "verified": False}
            final_text = str(seq_out.get("result") or source_text)
            ver = evaluate(verifier, final_text, "CALLER_PREDICATE", "")
            return {
                **seq_out,
                "verified": ver is not None,
                "verification": ver,
                "whole_task_correctness_proved": False,
            }

        history: list[str] = [source_text]
        applied_rules: list[dict[str, Any]] = []
        current = source_text
        active_by_id = {
            str(r.get("skill_id") or ""): r
            for r in self.lookup_rules(language, error_class=error_class)
        }
        for _ in range(max(1, int(max_steps))):
            hit = self.recall_and_apply_verified(
                source_text=current,
                language=language,
                error_class=error_class,
                verifier=verifier,
                prior_sources=history,
            )
            if hit is None:
                break
            sid = str(hit.get("skill_id") or "")
            rule_obj = active_by_id.get(sid)
            if rule_obj is not None:
                applied_rules.append(rule_obj)
            current = str(hit["patched_source"])
            history.append(current)

        if not applied_rules:
            return {
                "verdict": _seq.NO_CHANGE,
                "reason": "NO_APPLICABLE_VERIFIED_STEP",
                "steps": [],
                "source": source_text,
                "result": source_text,
                "verified": False,
            }
        seq_out = _seq.verify_sequence(source_text, applied_rules)
        return {
            **seq_out,
            "verified": seq_out.get("verdict") == _seq.PASS,
            "whole_task_correctness_proved": False,
        }

    def probe_skill_on_victim(
        self,
        skill_id: str,
        victim_snippet: str,
        *,
        oracle: Callable[[str, Any], Any] | None,
        probes: Sequence[Any] | None,
        invalidate_on_break: bool = True,
    ) -> dict[str, Any]:
        """Execute a stored rule on a held-out victim via `rule_generalization_probe_v1` and invalidate on BREAKS."""
        from canonical.tools import rule_generalization_probe_v1 as _probe

        conn = _connect(self.db_path)
        try:
            row = conn.execute(
                "SELECT pattern_json FROM crystallized_skills WHERE skill_id = ?",
                (skill_id,),
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            return {"ok": False, "verdict": _probe.NO_RULE, "reason": "SKILL_NOT_FOUND", "skill_id": skill_id}
        rule = json.loads(row[0])
        sources = (rule.get("provenance") or {}).get("taught_sources") or []
        before_s = str(sources[0].get("before") or "") if sources and isinstance(sources[0], Mapping) else ""
        after_s = str(sources[0].get("after") or "") if sources and isinstance(sources[0], Mapping) else ""
        outcome = _probe.probe_rule(
            before_s,
            after_s,
            oracle=oracle,
            probes=probes,
            victim_snippet=victim_snippet,
            rule=rule,
        )
        invalidated = False
        if outcome.get("verdict") == _probe.BREAKS and invalidate_on_break:
            invalidated = self.invalidate(
                skill_id,
                f"ORACLE_PROBE_BREAKS:{outcome.get('reason')}",
                counterexample_sha256=source_sha256(victim_snippet),
            )
        return {
            **outcome,
            "ok": True,
            "skill_id": skill_id,
            "invalidated": invalidated,
        }

    def crystallize_verified_fix(
        self,
        language: str,
        bug_class: str,
        before_code: str,
        after_code: str,
        verifier_oracle_kind: str = "VERIFIED",
    ) -> dict[str, Any] | None:
        # Historical argument is a label, not evidence that its named oracle ran.
        # Legacy calls store structural hypotheses only; scoped teaching uses the
        # explicit contract + training_verifier interface above.
        res = self.crystallize_code_fix(
            before_snippet=before_code,
            after_snippet=after_code,
            language=language,
            error_class=bug_class,
        )
        return res if res.get("crystallized") else None
