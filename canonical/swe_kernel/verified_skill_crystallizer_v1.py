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
BUNDLE_SCHEMA = "PROJECT_BRAIN_VERIFIED_SKILL_BUNDLE_V1"

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


def _malformed_rule_reason(rule: Mapping[str, Any]) -> str | None:
    """Why this payload cannot be applied, or ``None`` if it is a rule the engine understands.

    Checked structurally rather than by trying it on a sample, because a correct rule simply may
    not match an arbitrary sample and "did not apply here" is not "is not a rule".
    """
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
        },
        separators=(",", ":"),
    )
    return "skill_" + hashlib.sha256(rule_blob.encode("utf-8")).hexdigest()[:16]


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
        origin: str | None = None,
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
                entry = {
                    "origin": origin or default_origin(),
                    "at": round(time.time(), 3),
                    "hits": 1,
                }
                # Re-learning a rule on a second machine is evidence about BOTH machines, so the
                # provenance grows instead of the newest origin overwriting the older one.
                row = conn.execute(
                    "SELECT provenance_json FROM crystallized_skills WHERE skill_id = ?",
                    (rule["skill_id"],),
                ).fetchone()
                try:
                    provenance = json.loads(row[0]) if row and row[0] else []
                except (TypeError, ValueError):
                    provenance = []
                if not any(isinstance(p, Mapping) and p.get("origin") == entry["origin"
                           ] for p in provenance):
                    provenance.append(entry)
                conn.execute(
                    "INSERT INTO crystallized_skills "
                    "(skill_id, domain, language, error_class, skeleton_fp, pattern_json, created_ts, "
                    " verified_hits, provenance_json) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?) "
                    "ON CONFLICT(skill_id) DO UPDATE SET verified_hits = verified_hits + 1, "
                    " provenance_json = excluded.provenance_json",
                    (
                        rule["skill_id"],
                        rule["domain"],
                        rule["language"],
                        rule["error_class"],
                        rule["skeleton_fp"],
                        json.dumps(rule, separators=(",", ":")),
                        time.time(),
                        json.dumps(provenance, separators=(",", ":")),
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

    # ------------------------------------------------------------------ portability
    # A store inside one checkout is durable but not portable: a second computer starts empty and
    # two machines that learn for a month cannot pool anything. A bundle is the transport, and the
    # design constraint is that importing must never be able to make recall less safe. It cannot:
    # an imported rule is still only a hypothesis, and recall still runs the caller's verifier
    # before returning a patch. The worst an untrusted bundle can do is waste a verification.

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
                if skill_identity(rule) != stated:
                    refusals.append({"skill_id": stated, "reason": "CONTENT_ADDRESS_MISMATCH"})
                    continue
                prov = entry.get("provenance") or []
                hits = int(entry.get("verified_hits") or 1)
                created = float(entry.get("created_ts") or time.time())
                existing = conn.execute(
                    "SELECT verified_hits, created_ts, provenance_json FROM crystallized_skills "
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
                    old_hits, old_created, old_prov = existing
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
                            "provenance_json = ? WHERE skill_id = ?",
                            (max(int(old_hits), hits), min(float(old_created), created),
                             json.dumps(known, separators=(",", ":")), stated),
                        )
                    merged += 1
        finally:
            conn.close()
        # Any cached rule list for this store is now stale; a stale cache would hide an import.
        for key in [k for k in _MEM_SKILLS if k.startswith(f"{self.db_path}::")]:
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
