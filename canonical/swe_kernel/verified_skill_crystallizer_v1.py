#!/usr/bin/env python3
"""Persistent parameterized code-repair hypotheses in the existing SQLite store.

Structural twins test pattern transport, not semantic correctness. Legacy boolean
callbacks retain CALLER_PREDICATE assurance only. Scoped records and typed current
verification distinguish syntax/compilation/test-suite claims; no result proves
arbitrary task correctness, permanent availability or universal instant learning.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import json
import io
import keyword
import tokenize
import os
import pathlib
import re
import shutil
import sqlite3
import tempfile
import time
from typing import Any, Callable, Mapping

from canonical.swe_kernel.skill_verification_contract_v1 import (
    KINDS, VerificationResult, applicable, evaluate, normalize_contract, source_sha256,
)

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

_MEM_SKILLS: dict[str, tuple[tuple, list[dict[str, Any]]]] = {}


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
            rows = conn.execute(
                "SELECT pattern_json FROM crystallized_skills WHERE domain='swe_code_repair' AND language=? "
                "ORDER BY verified_hits DESC, created_ts DESC LIMIT 128", (language,)).fetchall()
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
    # Literals are relational holes too. Over-generalization is only as safe as
    # the caller's actual behavioral verifier, never guaranteed by a broad match:
    # A weak predicate can still accept an incorrect edit. Strict scoped recall
    # therefore requires a matching current typed oracle, not just a wide pattern.
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
                if (token.type==tokenize.NAME and name not in _KEYWORDS_KEEP
                        and not keyword.iskeyword(name) and not keyword.issoftkeyword(name)):
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
) -> bool:
    """Check transport to a constructed alpha-renamed twin, not project semantics."""
    lang = str(rule.get("language") or "python")
    mutated_before, rename_map = _alpha_mutate_snippet(before_snippet, language=lang)
    if not rename_map or mutated_before == before_snippet:
        return False
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
    ) -> dict[str, Any]:
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
        rule = anti_unify_code_rule(
            before_snippet,
            after_snippet,
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
        if not verify_rule_on_mutated_twin(before_snippet, rule, twin_oracle=observe_twin if twin_oracle else None):
            return {"crystallized": False, "reason": "FAILED_MUTATED_TWIN_VERIFICATION"}

        if contract is not None and apply_crystallized_code_rule(before_snippet, rule) != after_snippet:
            return {"crystallized": False, "reason": "RULE_DOES_NOT_REPRODUCE_VERIFIED_EXAMPLE"}
        rule['record_version'] = 1
        rule['state'] = 'ACTIVE'
        rule['contract'] = contract
        rule['parameters'] = sorted({(kind, name) for kind, name in rule['pattern_tokens'] if kind.startswith('hole_')})
        rule['training_verification'] = training or {'kind': 'NOT_VERIFIED', 'whole_task_correctness_proved': False}
        rule['twin_verification'] = twin_evidence
        if contract is not None:
            rule['training_baseline'] = {'passed': False, 'kind': baseline.kind, 'scope_id': baseline.scope_id,
                                         'candidate_sha256': baseline.candidate_sha256, 'evidence': dict(baseline.evidence)}
        rule['provenance'] = {'before_sha256': source_sha256(before_snippet), 'after_sha256': source_sha256(after_snippet)}
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
                    "(skill_id, domain, language, error_class, skeleton_fp, pattern_json, created_ts, verified_hits, provenance_json) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) "
                    "ON CONFLICT(skill_id) DO UPDATE SET verified_hits = verified_hits + excluded.verified_hits, "
                    "provenance_json = excluded.provenance_json",
                    (
                        rule["skill_id"],
                        rule["domain"],
                        rule["language"],
                        rule["error_class"],
                        rule["skeleton_fp"],
                        json.dumps(rule, separators=(",", ":")),
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
        return {
            "crystallized": True,
            "skill_id": rule["skill_id"],
            "skeleton_fp": rule["skeleton_fp"],
            "hole_count": rule["hole_count"],
            "state": stored.get('state', 'ACTIVE'),
            "training_verification": stored.get('training_verification', {'kind': 'LEGACY_UNSCOPED'}),
            "twin_verification": stored.get('twin_verification', {'kind': 'LEGACY_UNSCOPED'}),
            "whole_task_correctness_proved": False,
        }

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
    ) -> dict[str, Any] | None:
        """Propose only within recorded applicability and actual current assurance.

        Callbacks are trusted verifiers, not authenticated third-party attestations.
        Boolean callbacks never establish TEST_SUITE or whole-task correctness.
        """
        if required_verification_kind not in KINDS:
            raise ValueError('UNKNOWN_VERIFICATION_KIND')
        lang = language.lower()
        rules = _load_rules(self.db_path, lang)

        ordered = rules
        if error_class:
            ordered = (
                [r for r in rules if r.get("error_class") == error_class]
                + [r for r in rules if r.get("error_class") != error_class]
            )

        for rule in ordered:
            if rule.get('state') not in (None, 'ACTIVE') or not applicable(rule.get('contract'), scope_id, context):
                continue
            recorded = rule.get('contract')
            if required_verification_kind != 'CALLER_PREDICATE' and (recorded is None or rule.get('record_version') != 1):
                continue
            if recorded is not None and recorded['verification_kind'] != required_verification_kind:
                continue
            candidate = apply_crystallized_code_rule(source_text, rule)
            if candidate is None or candidate == source_text:
                continue
            verification = evaluate(verifier, candidate, required_verification_kind, scope_id)
            if verification is not None:
                conn = _connect(self.db_path)
                try:
                    with conn:
                        # Verification can take seconds. Do not return an artifact
                        # invalidated/deleted by another writer while it was running.
                        conn.execute('BEGIN IMMEDIATE')
                        live = conn.execute('SELECT pattern_json FROM crystallized_skills WHERE skill_id=?', (rule['skill_id'],)).fetchone()
                        if live is None or json.loads(live[0]) != rule:
                            continue
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
                    "verification": verification,
                    "whole_task_correctness_proved": False,
                }
        return None

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
                prov = entry.get("provenance") or []
                hits = int(entry.get("verified_hits", 1))
                created = float(entry.get("created_ts") or time.time())
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
                return True
        finally:
            conn.close()

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
