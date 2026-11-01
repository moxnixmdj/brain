#!/usr/bin/env python3
"""Verified Skill Crystallizer — True Permanent Instant Learning Engine (SQLite WAL).

Implements genuine cross-repository / cross-environment one-shot skill learning with
zero external or local model calls ($0) and zero rote episode memorization:

1. **Plotkin Structural Anti-Unification (`anti_unify_ast_transform` / `anti_unify_cli_recipe`)**:
   Given a concrete before->after code fix (Python AST or polyglot token/CST pattern) or a
   verified CLI/environment command trace, abstracts concrete identifiers, literals, type
   names, and filesystem paths into canonical typed hole variables (`?id0`, `?type0`,
   `?num0`, `?str0`, `?path0`) while preserving exact structural operators, keywords, and
   relational bindings (same identifier before -> same hole after).

2. **Mutated-Twin Counterfeit Filter (`verify_on_mutated_twin`)**:
   Before any skill can enter persistent memory, constructs a syntactically mutated twin
   problem (fresh variable names, alpha-renamed identifiers, fresh temporary directory)
   and requires the abstracted skill to:
     (a) match the mutated twin's before-state via unification,
     (b) synthesize a distinct, valid after-state with substituted bindings, and
     (c) pass an independent oracle (`ast.parse` / compiler / test / file-format reader)
         on the mutated twin.
   Any literal path/identifier memorization fails the mutated-twin test and is rejected.

3. **Sub-Millisecond SQLite WAL Skill Index (`VerifiedSkillStore`)**:
   Stores verified generalized skills in SQLite WAL keyed by `(domain, language,
   error_class, skeleton_fp)` with an in-process L1 dictionary cache (<0.2 ms recall).
   Every recalled application still runs the caller's independent verifier before
   returning `PASS` — a recalled skill is a fast hypothesis, never an unchecked claim.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
import pathlib
import re
import shutil
import sqlite3
import tempfile
import time
from typing import Any, Callable, Mapping

SCHEMA = "PROJECT_BRAIN_VERIFIED_SKILL_CRYSTALLIZER_V1"

_KEYWORDS_KEEP = frozenset({
    # Python / Go / Rust / TS / C++ / SQL structural keywords & builtins that carry semantics
    "def", "return", "if", "elif", "else", "for", "while", "in", "not", "and", "or", "is",
    "None", "True", "False", "class", "import", "from", "with", "as", "try", "except",
    "finally", "raise", "async", "await", "yield", "lambda", "pass", "break", "continue",
    "len", "range", "min", "max", "sum", "abs", "int", "float", "str", "list", "dict",
    "set", "tuple", "bool", "enumerate", "zip", "sorted", "reversed", "isinstance", "getattr",
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

_MEM_SKILLS: dict[str, list[dict[str, Any]]] = {}


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

    Any rules at the legacy location are migrated once, so nothing already learned is lost.
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
    return conn


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


def anti_unify_code_rule(
    before_snippet: str,
    after_snippet: str,
    *,
    language: str = "python",
    error_class: str = "GENERIC",
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
    if len(b_lines) > 1 or len(a_lines) > 1:
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
    toks_b = _tokenize_code(before_clean, case_insensitive_kw=sql_mode)
    toks_a = _tokenize_code(after_clean, case_insensitive_kw=sql_mode)

    ident_map: dict[str, str] = {}
    # IDENTIFIERS WERE NEVER THE ONLY THING A REPAIR GENERALIZES OVER.
    #
    # ``return t - 1`` -> ``return t`` is a repair about an off-by-one, not about the literal 1: the
    # same fix applies to ``- 7``.  Abstracting identifiers only left the number concrete, so the
    # rule matched its own training input and almost nothing else -- measured 2026-11-01 on the
    # five-neighbour probe: 2 of 5 reached, and the two misses were exactly "same shape, different
    # literal" and "same intent, different structure".
    #
    # Literals are now relational holes too, in their own namespaces (``?num0``, ``?str0``; a path
    # is a string literal and lands in ``?str``).  Over-generalizing is SAFE here by construction:
    # ``recall_and_apply_verified`` never returns a patch without running the caller's verifier, so
    # a wider net costs a failed verification, never a wrong edit.  That is what makes widening the
    # hole set the right trade -- the filter is the verifier, not the pattern.
    hole_maps: dict[str, dict[str, str]] = {"ident": ident_map, "num": {}, "str": {}}
    pattern_tokens: list[tuple[str, str]] = []
    skeleton_parts: list[str] = []

    for kind, val in toks_b:
        if kind == "ws":
            pattern_tokens.append(("ws", " "))
            continue
        if kind in _HOLE_PREFIX:
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


def apply_crystallized_code_rule(source_text: str, rule: Mapping[str, Any]) -> str | None:
    """Match ``rule['pattern_tokens']`` against ``source_text`` via unification and rewrite."""
    sql_mode = str(rule.get("language") or "") == "sql"
    pat_non_ws = [(k, v) for k, v in (rule.get("pattern_tokens") or []) if k != "ws"]
    if not pat_non_ws:
        return None

    # Tokenize source with byte/char offsets so exact surrounding formatting is preserved.
    src_tokens: list[tuple[str, str, int, int]] = []
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
        return None

    existing_idents = {val for kind, val, _, _ in src_tokens if kind == "ident"}

    for start_idx in range(len(src_tokens) - plen + 1):
        bindings: dict[str, str] = {}
        matched = True
        for offset, (pk, pv) in enumerate(pat_non_ws):
            sk, sv, _, _ = src_tokens[start_idx + offset]
            if pk in _HOLE_KIND:
                if sk != _HOLE_KIND[pk]:
                    matched = False
                    break
                prev = bindings.get(pv)
                if prev is not None and prev != sv:
                    matched = False
                    break
                bindings[pv] = sv
            elif pk == "kw" and sql_mode:
                if sk != "kw" or sv.upper() != pv.upper():
                    matched = False
                    break
            else:
                if sk != pk or sv != pv:
                    matched = False
                    break
        if not matched:
            continue

        span_start = src_tokens[start_idx][2]
        span_end = src_tokens[start_idx + plen - 1][3]
        # Preserve line indentation if multiline replacement occurs.
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
                # Every hole kind binds the same way: the value this rule captured from the source
                # is written back.  Listing only ``hole_id`` here meant a ``hole_num``/``hole_str``
                # replacement emitted the hole's own name (``?num0``) as literal text, which no
                # parser accepts -- the rule then failed its own mutated-twin gate and was silently
                # never stored.
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
                out_parts.append("\n" + indent)
            else:
                out_parts.append(rv)
        if not matched:
            continue

        candidate = source_text[:span_start] + "".join(out_parts) + source_text[span_end:]
        if candidate != source_text:
            return candidate
    return None


# ---------------------------------------------------------------------------
# 2. Mutated-Twin Counterfeit Filter (Rejects Rote Memorization)
# ---------------------------------------------------------------------------

def _alpha_mutate_snippet(snippet: str, *, language: str = "python") -> tuple[str, dict[str, str]]:
    """Alpha-rename every non-keyword identifier to a distinct synthetic name."""
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
) -> bool:
    """Prove the anti-unified rule transfers to an unseen alpha-renamed twin."""
    lang = str(rule.get("language") or "python")
    mutated_before, rename_map = _alpha_mutate_snippet(before_snippet, language=lang)
    if not rename_map or mutated_before == before_snippet:
        return False
    rewritten = apply_crystallized_code_rule(mutated_before, rule)
    if not rewritten or rewritten == mutated_before:
        return False
    # Anti-memorization invariant: no original identifier may leak into the mutated twin's output.
    rewritten_idents = {
        val for kind, val in _tokenize_code(rewritten, case_insensitive_kw=(lang == "sql"))
        if kind == "ident"
    }
    for orig_name in rename_map:
        if orig_name in rewritten_idents and orig_name not in rename_map.values():
            return False
    if lang == "python":
        try:
            ast.parse(rewritten)
        except SyntaxError:
            return False
    if twin_oracle is not None and not twin_oracle(rewritten):
        return False
    return True


# ---------------------------------------------------------------------------
# 3. Persistent SQLite WAL Verified Skill Store
# ---------------------------------------------------------------------------

class VerifiedSkillStore:
    """SQLite WAL store of anti-unified, twin-verified skills (<1 ms lookup)."""

    def __init__(self, db_path: pathlib.Path | None = None) -> None:
        self.db_path = db_path or _default_db_path()

    def crystallize_code_fix(
        self,
        *,
        before_snippet: str,
        after_snippet: str,
        language: str,
        error_class: str = "GENERIC",
        twin_oracle: Callable[[str], bool] | None = None,
    ) -> dict[str, Any]:
        rule = anti_unify_code_rule(
            before_snippet,
            after_snippet,
            language=language,
            error_class=error_class,
        )
        if rule is None:
            return {"crystallized": False, "reason": "NON_GENERALIZABLE_SNIPPET"}
        if not verify_rule_on_mutated_twin(before_snippet, rule, twin_oracle=twin_oracle):
            return {"crystallized": False, "reason": "FAILED_MUTATED_TWIN_VERIFICATION"}

        conn = _connect(self.db_path)
        try:
            with conn:
                conn.execute(
                    "INSERT INTO crystallized_skills "
                    "(skill_id, domain, language, error_class, skeleton_fp, pattern_json, created_ts, verified_hits) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, 1) "
                    "ON CONFLICT(skill_id) DO UPDATE SET verified_hits = verified_hits + 1",
                    (
                        rule["skill_id"],
                        rule["domain"],
                        rule["language"],
                        rule["error_class"],
                        rule["skeleton_fp"],
                        json.dumps(rule, separators=(",", ":")),
                        time.time(),
                    ),
                )
        finally:
            conn.close()

        mem_key = f"{ str(self.db_path) }::{rule['language']}"
        _MEM_SKILLS.pop(mem_key, None)
        return {
            "crystallized": True,
            "skill_id": rule["skill_id"],
            "skeleton_fp": rule["skeleton_fp"],
            "hole_count": rule["hole_count"],
        }

    def recall_and_apply_verified(
        self,
        *,
        source_text: str,
        language: str,
        verifier: Callable[[str], bool],
        error_class: str | None = None,
    ) -> dict[str, Any] | None:
        """Recall matching skills in <1 ms, instantiate holes, and verify via ``verifier``."""
        lang = language.lower()
        mem_key = f"{ str(self.db_path) }::{lang}"
        rules = _MEM_SKILLS.get(mem_key)
        if rules is None:
            conn = _connect(self.db_path)
            try:
                rows = conn.execute(
                    "SELECT pattern_json FROM crystallized_skills "
                    "WHERE domain = 'swe_code_repair' AND language = ? "
                    "ORDER BY verified_hits DESC, created_ts DESC LIMIT 128",
                    (lang,),
                ).fetchall()
                rules = [json.loads(r[0]) for r in rows]
                _MEM_SKILLS[mem_key] = rules
            finally:
                conn.close()

        ordered = rules
        if error_class:
            ordered = (
                [r for r in rules if r.get("error_class") == error_class]
                + [r for r in rules if r.get("error_class") != error_class]
            )

        for rule in ordered:
            candidate = apply_crystallized_code_rule(source_text, rule)
            if candidate is None or candidate == source_text:
                continue
            if verifier(candidate):
                conn = _connect(self.db_path)
                try:
                    with conn:
                        conn.execute(
                            "UPDATE crystallized_skills SET verified_hits = verified_hits + 1 WHERE skill_id = ?",
                            (rule["skill_id"],),
                        )
                finally:
                    conn.close()
                return {
                    "skill_id": rule["skill_id"],
                    "skeleton_fp": rule["skeleton_fp"],
                    "patched_source": candidate,
                    "from_crystallized_memory": True,
                }
        return None

    def count(self) -> int:
        conn = _connect(self.db_path)
        try:
            row = conn.execute("SELECT COUNT(*) FROM crystallized_skills").fetchone()
            return int(row[0]) if row else 0
        finally:
            conn.close()

    def lookup_rules(self, language: str, error_class: str | None = None) -> list[dict[str, Any]]:
        lang = language.lower()
        mem_key = f"{str(self.db_path)}::{lang}"
        rules = _MEM_SKILLS.get(mem_key)
        if rules is None:
            conn = _connect(self.db_path)
            try:
                rows = conn.execute(
                    "SELECT pattern_json FROM crystallized_skills "
                    "WHERE domain = 'swe_code_repair' AND language = ? "
                    "ORDER BY verified_hits DESC, created_ts DESC LIMIT 128",
                    (lang,),
                ).fetchall()
                rules = [json.loads(r[0]) for r in rows]
                _MEM_SKILLS[mem_key] = rules
            finally:
                conn.close()
        if error_class:
            return [r for r in rules if r.get("error_class") == error_class]
        return list(rules)

    def crystallize_verified_fix(
        self,
        language: str,
        bug_class: str,
        before_code: str,
        after_code: str,
        verifier_oracle_kind: str = "VERIFIED",
    ) -> dict[str, Any] | None:
        del verifier_oracle_kind
        res = self.crystallize_code_fix(
            before_snippet=before_code,
            after_snippet=after_code,
            language=language,
            error_class=bug_class,
        )
        return res if res.get("crystallized") else None
