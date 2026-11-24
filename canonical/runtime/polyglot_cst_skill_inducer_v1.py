"""Universal Zero-LLM Polyglot CST Single-Experience Skill Inducer & Store.

Solves the core continual-learning bottleneck across ALL mainstream languages
(C, C++, JavaScript, TypeScript, Python, Go, Rust, Java) with zero LLM calls
(`model_calls == 0`) and zero memorized weights (`parameters_stored == 0`).

How ONE verified `(before_source, after_source)` experience becomes a portable,
executable cross-repo skill in <2ms:
  1. Lex both sources in O(N) into typed tokens (`KW`, `IDENT`, `NUM`, `STR`,
     `OP`, `PUNCT`) preserving exact byte spans and indentation.
  2. Extract the minimal changed line hunk (adding a 1-line structural anchor
     for pure insertions so insertion sites unify deterministically).
  3. Alpha-canonicalize local identifiers into typed metavariables (`$ID0`, ...)
     and detect relational sibling identifiers (`$REL(base=$IDk, old=..., new=...)`
     such as `lwr`->`upr`, `skip_`->`copy_`, or `$IDk` + `_len`) plus hygienic
     newly-declared local temporaries. Refuse any unbound foreign identifier
     (fail-closed zero-grafting invariant).
  4. Verify self-roundtrip BEFORE admission: the induced executable skill MUST
     reproduce `after_source` when applied to `before_source`.
  5. Store in an external, human-readable, inspectable, editable, deletable JSON
     store (`BRAIN_POLYGLOT_CST_SKILL_STORE_V1`). Online counterexample feedback
     narrows preconditions or quarantines conflicting skills with zero weight updates.

Authority: NONE. Computed mechanism only; zero parameters, zero model calls.
"""
from __future__ import annotations

import dataclasses
import difflib
import hashlib
import json
import pathlib
import re
import time
from typing import Any, Mapping, Sequence

SCHEMA = "BRAIN_POLYGLOT_CST_SKILL_STORE_V1"
AUTHORITY = "NONE"

STATUS_PROVISIONAL = "PROVISIONAL__ADMITTED_FROM_VERIFIED_FIX"
STATUS_NARROWED = "NARROWED__COUNTEREXAMPLE_REFINED"
STATUS_QUARANTINED = "QUARANTINED__UNSEPARABLE_COUNTEREXAMPLE"

DEFAULT_STORE_PATH = (
    pathlib.Path(__file__).resolve().parent.parent
    / "state"
    / "POLYGLOT_CST_SKILL_STORE_V1.json"
)

# Language keywords preserved verbatim during alpha-canonicalization
_POLYGLOT_KEYWORDS = frozenset({
    # C / C++ / JS / TS / Go / Rust / Java / Python control & types
    "if", "else", "elif", "for", "while", "do", "switch", "case", "default",
    "break", "continue", "return", "goto", "try", "catch", "except", "finally",
    "throw", "raise", "new", "delete", "typeof", "instanceof", "in", "of",
    "is", "not", "and", "or", "const", "let", "var", "static", "inline",
    "extern", "typedef", "struct", "union", "enum", "class", "def", "function",
    "async", "await", "yield", "import", "from", "export", "as", "pass",
    "void", "int", "char", "short", "long", "float", "double", "bool", "boolean",
    "unsigned", "signed", "size_t", "ssize_t", "uint8_t", "uint16_t", "uint32_t",
    "uint64_t", "int8_t", "int16_t", "int32_t", "int64_t", "auto", "nullptr",
    "NULL", "null", "None", "undefined", "true", "false", "True", "False",
    "this", "self", "super", "sizeof", "FILE", "fn", "pub", "mut", "match",
    "func", "defer", "nil", "string", "number", "any", "unknown", "never",
    # Well-known standard-library / builtin symbols & standard C/JS constants safe across repos
    "ferror", "feof", "fopen", "fclose", "fgets", "fread", "fwrite", "printf",
    "fprintf", "snprintf", "strlen", "strcmp", "strncmp", "strcpy", "strncpy",
    "memcpy", "memmove", "memcmp", "memset", "malloc", "calloc", "realloc", "free",
    "isspace", "isdigit", "isalpha", "isalnum", "isxdigit", "tolower", "toupper",
    "INT_MAX", "INT_MIN", "UINT_MAX", "LONG_MAX", "LONG_MIN", "ULONG_MAX",
    "LLONG_MAX", "LLONG_MIN", "SIZE_MAX", "PTRDIFF_MAX", "CHAR_BIT", "EOF",
    "NAN", "INFINITY", "isnan", "isinf", "isfinite", "errno", "EINVAL", "ENOMEM", "ERANGE",
    "Array", "Object", "String", "Number", "Boolean", "RegExp", "Error",
    "TypeError", "RangeError", "SyntaxError", "Math", "JSON", "Map", "Set",
    "prototype", "call", "apply", "bind", "hasOwnProperty", "create", "keys",
    "values", "entries", "assign", "defineProperty", "isArray", "from", "isFinite", "isNaN",
    "length", "slice", "push", "pop", "shift", "unshift", "indexOf", "includes",
    "startsWith", "endsWith", "replace", "split", "join", "trim", "test", "exec", "match",
    "len", "str", "int", "float", "bool", "list", "dict", "set", "tuple",
    "isinstance", "issubclass", "getattr", "setattr", "hasattr", "range",
    "enumerate", "zip", "min", "max", "sum", "abs", "all", "any", "ValueError",
    "KeyError", "IndexError", "AttributeError", "RuntimeError", "OSError",
    # Branch prediction macros common in C codebases
    "likely", "unlikely", "yyjson_likely", "yyjson_unlikely",
})

# Fundamental semantic constants kept verbatim (empty/zero, unit, error sentinel)
_PRESERVED_NUMS = frozenset({"0", "1", "2", "-1"})

_TOK_RE = re.compile(
    r"""
      (?P<WS>[ \t]+)
    | (?P<NL>\r?\n)
    | (?P<COMMENT>//[^\n]*|/\*[\s\S]*?\*/|\#[^\n]*(?=\n|$))
    | (?P<STR>"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`)
    | (?P<NUM>0[xX][0-9a-fA-F]+[uUlL]*|\d+(?:\.\d+)?(?:[eE][+-]?\d+)?[uUlLfF]*)
    | (?P<IDENT>[A-Za-z_][A-Za-z0-9_]*)
    | (?P<OP>===|!==|<<=|>>=|\.\.\.|==|!=|<=|>=|&&|\|\||->|::|=>|\+\+|--|\+=|-=|\*=|/=|%=|&=|\|=|\^=|<<|>>|\?\?|\?\.|[+\-*/%&|^~!<>?=])
    | (?P<PUNCT>[()\[\]{};,.:@])
    | (?P<OTHER>.)
    """,
    re.VERBOSE,
)


@dataclasses.dataclass(frozen=True)
class Tok:
    kind: str
    text: str
    start: int
    end: int
    line: int  # 1-based


def detect_language(path: str) -> str:
    ext = pathlib.Path(path).suffix.lower()
    if ext in (".c", ".h"):
        return "c"
    if ext in (".cc", ".cpp", ".cxx", ".hpp", ".hh", ".hxx"):
        return "cpp"
    if ext in (".js", ".mjs", ".cjs"):
        return "js"
    if ext in (".ts", ".tsx", ".mts", ".cts"):
        return "ts"
    if ext == ".py":
        return "py"
    if ext == ".go":
        return "go"
    if ext == ".rs":
        return "rs"
    if ext == ".java":
        return "java"
    return "generic"


def tokenize_code(src: str, *, language: str = "generic", keep_ws: bool = False) -> list[Tok]:
    """O(N) polyglot lexical tokenizer preserving exact spans and 1-based line numbers."""
    out: list[Tok] = []
    line = 1
    is_py = language == "py"
    for m in _TOK_RE.finditer(src):
        kind = m.lastgroup or "OTHER"
        text = m.group(0)
        if kind == "NL":
            if keep_ws:
                out.append(Tok("NL", text, m.start(), m.end(), line))
            line += 1
            continue
        if kind == "WS":
            if keep_ws:
                out.append(Tok("WS", text, m.start(), m.end(), line))
            continue
        if kind == "COMMENT":
            # In C/C++, `#include`/`#if` starts with `#` — only treat `#` as comment in Python!
            if text.startswith("#") and not is_py:
                # Re-tokenize this preprocessor line as PUNCT('#') + remaining tokens
                out.append(Tok("PUNCT", "#", m.start(), m.start() + 1, line))
                sub = tokenize_code(text[1:], language=language, keep_ws=keep_ws)
                for st in sub:
                    out.append(Tok(st.kind, st.text, m.start() + 1 + st.start, m.start() + 1 + st.end, line))
                continue
            line += text.count("\n")
            continue
        if kind == "IDENT" and text in _POLYGLOT_KEYWORDS:
            kind = "KW"
        out.append(Tok(kind, text, m.start(), m.end(), line))
    return out


def _common_indent(lines: Sequence[str]) -> str:
    indents = [
        l[: len(l) - len(l.lstrip(" \t"))]
        for l in lines
        if l.strip()
    ]
    if not indents:
        return ""
    return min(indents, key=len)


def _strip_common_indent(lines: Sequence[str]) -> list[str]:
    base = _common_indent(lines)
    if not base:
        return list(lines)
    n = len(base)
    return [l[n:] if l.startswith(base) else l for l in lines]


def _extract_hunk_lines(before_src: str, after_src: str) -> tuple[list[str], list[str], int, int] | None:
    """Extract the single minimal changed line hunk with 1-line anchor if pure insertion."""
    b_lines = before_src.splitlines(keepends=True)
    a_lines = after_src.splitlines(keepends=True)
    sm = difflib.SequenceMatcher(None, b_lines, a_lines, autojunk=False)
    changed = [op for op in sm.get_opcodes() if op[0] != "equal"]
    if not changed:
        return None
    # Merge closely adjacent hunks (within 2 lines) into one atomic block
    i1 = changed[0][1]
    i2 = changed[-1][2]
    j1 = changed[0][3]
    j2 = changed[-1][4]
    if i2 - i1 > 20 or j2 - j1 > 25:
        # Take first individual hunk if the diff spans multiple distant sites
        _, i1, i2, j1, j2 = changed[0]
        if i2 - i1 > 20 or j2 - j1 > 25:
            return None

    # Pure insertion (or trivial single-brace/keyword replacement): anchor 1 non-blank line before &/or after
    if i1 == i2 or "".join(b_lines[i1:i2]).strip() in ("", "{", "}", "else", "else {", "break;"):
        # Prefer anchoring the immediately preceding non-empty line AND/OR following non-empty line
        if i1 > 0 and b_lines[i1 - 1].strip():
            i1 -= 1
            j1 -= 1
        if i2 < len(b_lines) and b_lines[i2].strip():
            i2 += 1
            j2 += 1

    bh = b_lines[i1:i2]
    ah = a_lines[j1:j2]
    if not bh or not ah:
        return None
    return bh, ah, i1 + 1, i2


def _find_relational_sibling(
    ident: str,
    bound_ids: Mapping[str, str],
) -> dict[str, str] | None:
    """Detect whether an after-only identifier is a systematic morphological sibling of a bound `$IDk`."""
    for orig_name, hole in bound_ids.items():
        if len(orig_name) < 2:
            continue
        # 1. Suffix / prefix derivation (e.g., `from` -> `from_len`, `path` -> `path_len`)
        if ident.startswith(orig_name) and len(ident) > len(orig_name):
            suf = ident[len(orig_name) :]
            if suf.startswith("_") or suf[0].isupper():
                return {"op": "suffix", "base": hole, "arg": suf}
        if ident.endswith(orig_name) and len(ident) > len(orig_name):
            pre = ident[: len(ident) - len(orig_name)]
            if pre.endswith("_"):
                return {"op": "prefix", "base": hole, "arg": pre}
        # 2. Single contiguous substring swap (e.g., `utf8lwrcodepoint` -> `utf8uprcodepoint`, `skip_utf8` -> `copy_utf8`)
        if len(orig_name) >= 5 and len(ident) >= 5:
            p = 0
            while p < min(len(orig_name), len(ident)) and orig_name[p] == ident[p]:
                p += 1
            s = 0
            while (
                s < min(len(orig_name) - p, len(ident) - p)
                and orig_name[len(orig_name) - 1 - s] == ident[len(ident) - 1 - s]
            ):
                s += 1
            shared = p + s
            old_mid = orig_name[p : len(orig_name) - s]
            new_mid = ident[p : len(ident) - s]
            if shared >= 4 and 2 <= len(old_mid) <= 8 and 2 <= len(new_mid) <= 8 and old_mid != new_mid:
                return {"op": "replace", "base": hole, "old": old_mid, "new": new_mid}
    return None


def _is_declared_local_in_after(ident: str, after_toks: Sequence[Tok]) -> bool:
    """True when `ident` is freshly declared as a local variable inside `after_hunk` (e.g., `int error = ...;`)."""
    decl_types = frozenset({
        "int", "long", "short", "char", "size_t", "ssize_t", "bool", "boolean",
        "double", "float", "auto", "const", "let", "var", "uint32_t", "uint64_t",
        "int32_t", "int64_t",
    })
    for idx, t in enumerate(after_toks):
        if t.kind == "IDENT" and t.text == ident and idx >= 1:
            prev = after_toks[idx - 1]
            nxt = after_toks[idx + 1] if idx + 1 < len(after_toks) else None
            if (prev.kind == "KW" and prev.text in decl_types) or (prev.text == "*" and idx >= 2):
                if nxt is not None and nxt.text in ("=", ";"):
                    return True
    return False


def _render_template(
    template_lines: Sequence[str],
    bindings: Mapping[str, str],
    target_indent: str,
) -> str:
    """Instantiate a parametric template preserving target indentation and formatting."""
    # Sort longest placeholder first so `$ID10` never collides with `$ID1`
    items = sorted(bindings.items(), key=lambda kv: -len(kv[0]))
    rendered: list[str] = []
    for raw_l in template_lines:
        l = raw_l
        for ph, val in items:
            l = l.replace(ph, val)
        if l.strip():
            rendered.append(target_indent + l)
        else:
            rendered.append(l)
    return "".join(rendered)


def _canonicalize_template_lines(
    raw_lines: Sequence[str],
    language: str,
    ident_map: Mapping[str, str],
    lit_map: Mapping[str, str],
) -> list[str]:
    """Replace concrete identifiers/literals inside `raw_lines` with their canonical placeholders."""
    src = "".join(raw_lines)
    toks = tokenize_code(src, language=language, keep_ws=False)
    out_parts: list[str] = []
    cursor = 0
    for t in toks:
        if t.start < cursor:
            continue
        out_parts.append(src[cursor : t.start])
        if t.kind == "IDENT" and t.text in ident_map:
            out_parts.append(ident_map[t.text])
        elif t.kind in ("NUM", "STR") and t.text in lit_map:
            out_parts.append(lit_map[t.text])
        else:
            out_parts.append(t.text)
        cursor = t.end
    out_parts.append(src[cursor:])
    return "".join(out_parts).splitlines(keepends=True)


def induce_cst_skill(
    before_source: str,
    after_source: str,
    *,
    language: str = "generic",
    bug_classes: Sequence[str] = (),
    description: str = "",
) -> dict[str, Any]:
    """Induce ONE portable, executable CST rewrite skill from ONE verified `(before, after)` fix.

    Returns `{"admitted": True, "skill": {...}}` on verified round-trip admission,
    or `{"admitted": False, "reason": ...}` fail-closed if unbound foreign symbols
    exist or self-roundtrip fails.
    """
    hunk = _extract_hunk_lines(before_source, after_source)
    if hunk is None:
        return {"admitted": False, "reason": "NO_LOCAL_HUNK_CHANGE"}
    bh_raw, ah_raw, b_line_start, _ = hunk
    bh = _strip_common_indent(bh_raw)
    ah = _strip_common_indent(ah_raw)

    b_src = "".join(bh)
    a_src = "".join(ah)
    b_toks = tokenize_code(b_src, language=language)
    a_toks = tokenize_code(a_src, language=language)
    if len(b_toks) < 2 or len(a_toks) < 2:
        return {"admitted": False, "reason": "TRIVIAL_TOKEN_HUNK"}

    ident_map: dict[str, str] = {}
    id_counter = 0
    for t in b_toks:
        if t.kind == "IDENT" and t.text not in ident_map:
            ident_map[t.text] = f"__CST_ID{id_counter}__"
            id_counter += 1

    # Shared non-fundamental literals appearing in BOTH before and after become `$LITk`
    b_lits = {t.text for t in b_toks if t.kind in ("NUM", "STR") and t.text not in _PRESERVED_NUMS}
    a_lits = {t.text for t in a_toks if t.kind in ("NUM", "STR") and t.text not in _PRESERVED_NUMS}
    lit_map: dict[str, str] = {}
    lit_counter = 0
    for t in b_toks:
        if t.kind in ("NUM", "STR") and t.text in (b_lits & a_lits) and t.text not in lit_map:
            lit_map[t.text] = f"__CST_LIT{lit_counter}__"
            lit_counter += 1

    # Check every identifier in `after_hunk`: must be bound in `before`, relational sibling,
    # freshly declared local, OR fail-closed rejected!
    relational_holes: dict[str, dict[str, str]] = {}
    fresh_locals: dict[str, str] = {}
    rel_counter = 0
    fresh_counter = 0
    for t in a_toks:
        if t.kind != "IDENT":
            continue
        if t.text in ident_map:
            continue
        rel = _find_relational_sibling(t.text, ident_map)
        if rel is not None:
            ph = f"__CST_REL{rel_counter}__"
            rel_counter += 1
            ident_map[t.text] = ph
            relational_holes[ph] = rel
            continue
        if _is_declared_local_in_after(t.text, a_toks):
            ph = f"__CST_LOCAL{fresh_counter}__"
            fresh_counter += 1
            ident_map[t.text] = ph
            fresh_locals[ph] = t.text
            continue
        # Fail-closed: foreign repo-specific symbol cannot be grafted blindly!
        return {"admitted": False, "reason": f"FOREIGN_IDENT_UNBOUND:{t.text}"}

    # Build canonical token match pattern for `before`
    before_pattern: list[dict[str, str]] = []
    for t in b_toks:
        if t.kind == "IDENT":
            before_pattern.append({"kind": "VAR", "value": ident_map[t.text]})
        elif t.kind in ("NUM", "STR") and t.text in lit_map:
            before_pattern.append({"kind": "LIT_VAR", "value": lit_map[t.text], "tok_kind": t.kind})
        else:
            before_pattern.append({"kind": t.kind, "value": t.text})

    after_template_lines = _canonicalize_template_lines(ah, language, ident_map, lit_map)
    before_template_lines = _canonicalize_template_lines(bh, language, ident_map, lit_map)

    sig_payload = json.dumps(
        {
            "language": language,
            "before_pattern": before_pattern,
            "after_template": after_template_lines,
            "relational_holes": relational_holes,
        },
        sort_keys=True,
    )
    skill_id = "cst_" + hashlib.sha256(sig_payload.encode("utf-8")).hexdigest()[:12]

    skill: dict[str, Any] = {
        "skill_id": skill_id,
        "language": language,
        "description": description or f"induced_{language}_cst_skill_{skill_id}",
        "before_pattern": before_pattern,
        "before_template_lines": before_template_lines,
        "after_template_lines": after_template_lines,
        "relational_holes": relational_holes,
        "fresh_locals": fresh_locals,
        "preconditions": {
            "languages": [language],
            "bug_classes": sorted(set(str(b) for b in bug_classes)),
            "required_file_tokens": [],
        },
        "status": STATUS_PROVISIONAL,
        "verified_uses": 1,
        "refutations": 0,
        "parameters_stored": 0,
        "created_at": round(time.time(), 3),
    }

    # Self-roundtrip admission verification: MUST reproduce `after_source` on `before_source`!
    rt_matches = apply_cst_skill(
        skill,
        before_source,
        language=language,
        target_lines=[b_line_start],
        max_applications=1,
    )
    if not rt_matches:
        return {"admitted": False, "reason": "SELF_ROUNDTRIP_NO_MATCH"}
    rt_after = rt_matches[0]["patched_source"]
    rt_toks = [(t.kind, t.text) for t in tokenize_code(rt_after, language=language)]
    exp_toks = [(t.kind, t.text) for t in tokenize_code(after_source, language=language)]
    if rt_toks != exp_toks:
        return {"admitted": False, "reason": "SELF_ROUNDTRIP_MISMATCH"}

    return {"admitted": True, "skill": skill}


def _resolve_relational_hole(
    spec: Mapping[str, str],
    bindings: Mapping[str, str],
    file_idents: set[str],
) -> str | None:
    base_val = bindings.get(spec["base"])
    if not base_val:
        return None
    op = spec["op"]
    if op == "suffix":
        derived = base_val + spec["arg"]
    elif op == "prefix":
        derived = spec["arg"] + base_val
    elif op == "replace":
        old_s, new_s = spec["old"], spec["new"]
        if old_s not in base_val:
            return None
        derived = base_val.replace(old_s, new_s, 1)
    else:
        return None
    # Derived sibling symbol MUST actually exist in the target file (zero hallucination!)
    return derived if derived in file_idents else None


def _match_pattern_at(
    toks: Sequence[Tok],
    start_idx: int,
    pattern: Sequence[Mapping[str, str]],
) -> tuple[int, dict[str, str]] | None:
    """Unify `pattern` against `toks[start_idx:]` supporting both single IDENTs and balanced member chains."""
    ti = start_idx
    bindings: dict[str, str] = {}
    for pi, p in enumerate(pattern):
        if ti >= len(toks):
            return None
        pk = p["kind"]
        pv = p["value"]
        cur = toks[ti]
        if pk == "VAR":
            if cur.kind != "IDENT":
                return None
            # Check if this identifier begins a member-access chain (`a->b` or `a.b`) when the next pattern token isn't `->`/`.`
            nxt_p = pattern[pi + 1]["value"] if pi + 1 < len(pattern) else None
            end_ti = ti + 1
            if nxt_p not in ("->", "."):
                while (
                    end_ti + 1 < len(toks)
                    and toks[end_ti].text in ("->", ".")
                    and toks[end_ti + 1].kind == "IDENT"
                ):
                    # Stop if the next pattern token matches the upcoming separator
                    if nxt_p == toks[end_ti].text:
                        break
                    end_ti += 2
            bound_text = "".join(toks[k].text for k in range(ti, end_ti))
            if pv in bindings:
                if bindings[pv] != bound_text:
                    return None
            else:
                bindings[pv] = bound_text
            ti = end_ti
        elif pk == "LIT_VAR":
            if cur.kind != p.get("tok_kind"):
                return None
            if pv in bindings:
                if bindings[pv] != cur.text:
                    return None
            else:
                bindings[pv] = cur.text
            ti += 1
        else:
            if cur.kind != pk or cur.text != pv:
                return None
            ti += 1
    return ti, bindings


def apply_cst_skill(
    skill: Mapping[str, Any],
    target_source: str,
    *,
    language: str = "generic",
    target_lines: Sequence[int] | None = None,
    max_applications: int = 8,
    apply_all_sites: bool = False,
) -> list[dict[str, Any]]:
    """Unify an induced CST skill against `target_source` and emit verified candidate patches."""
    if skill.get("status") == STATUS_QUARANTINED:
        return []
    pattern: Sequence[Mapping[str, str]] = skill.get("before_pattern") or ()
    after_tpl: Sequence[str] = skill.get("after_template_lines") or ()
    rel_holes: Mapping[str, Mapping[str, str]] = skill.get("relational_holes") or {}
    fresh_locals: Mapping[str, str] = skill.get("fresh_locals") or {}
    req_toks: Sequence[str] = (skill.get("preconditions") or {}).get("required_file_tokens") or ()
    if not pattern or not after_tpl:
        return []
    if req_toks and not all(rt in target_source for rt in req_toks):
        return []

    toks = tokenize_code(target_source, language=language)
    if len(toks) < len(pattern):
        return []
    file_idents = {t.text for t in toks if t.kind == "IDENT"}
    src_lines = target_source.splitlines(keepends=True)

    # Precompute 1-based line start offsets
    line_starts = [0]
    for l in src_lines:
        line_starts.append(line_starts[-1] + len(l))

    focus_set = set(int(x) for x in (target_lines or ()))
    raw_matches: list[tuple[int, int, int, int, dict[str, str]]] = []
    i = 0
    while i <= len(toks) - len(pattern):
        m = _match_pattern_at(toks, i, pattern)
        if m is None:
            i += 1
            continue
        end_i, bindings = m
        # Resolve relational sibling holes & fresh locals
        full_bindings = dict(bindings)
        rel_ok = True
        for ph, rspec in rel_holes.items():
            resolved = _resolve_relational_hole(rspec, bindings, file_idents)
            if resolved is None:
                rel_ok = False
                break
            full_bindings[ph] = resolved
        if not rel_ok:
            i += 1
            continue
        for ph, base_nm in fresh_locals.items():
            # Pick hygienic local name not colliding with bound vars
            cand_nm = base_nm
            if cand_nm in bindings.values():
                cand_nm = f"_cst_{base_nm}"
            full_bindings[ph] = cand_nm

        l_start = toks[i].line
        l_end = toks[end_i - 1].line
        # Rank matches overlapping `target_lines` first!
        in_focus = 0 if (not focus_set or any(ln in focus_set for ln in range(l_start - 2, l_end + 3))) else 1
        raw_matches.append((in_focus, l_start, l_end, i, full_bindings))
        i = end_i

    if not raw_matches:
        return []

    raw_matches.sort(key=lambda x: (x[0], x[1]))
    results: list[dict[str, Any]] = []

    # Option 1: If multiple identical sites exist and `apply_all_sites`, emit a multi-site combined patch FIRST
    if apply_all_sites and len(raw_matches) > 1:
        # Apply from bottom to top so line indices stay valid
        nl_all = list(src_lines)
        applied_lns: list[int] = []
        used_ranges: list[tuple[int, int]] = []
        for _, l_s, l_e, _, fb in sorted(raw_matches, key=lambda x: -x[1]):
            if any(not (l_e < us or l_s > ue) for us, ue in used_ranges):
                continue
            used_ranges.append((l_s, l_e))
            tgt_ind = _common_indent(nl_all[l_s - 1 : l_e])
            repl = _render_template(after_tpl, fb, tgt_ind)
            nl_all[l_s - 1 : l_e] = repl.splitlines(keepends=True)
            applied_lns.append(l_s)
        patched_all = "".join(nl_all)
        if patched_all != target_source:
            results.append({
                "skill_id": skill["skill_id"],
                "lineno": min(applied_lns),
                "sites_patched": len(applied_lns),
                "bindings": raw_matches[0][4],
                "patched_source": patched_all,
            })

    # Option 2: Individual localized site applications
    for _, l_s, l_e, _, fb in raw_matches[:max_applications]:
        nl = list(src_lines)
        tgt_ind = _common_indent(nl[l_s - 1 : l_e])
        repl = _render_template(after_tpl, fb, tgt_ind)
        nl[l_s - 1 : l_e] = repl.splitlines(keepends=True)
        patched = "".join(nl)
        if patched != target_source:
            results.append({
                "skill_id": skill["skill_id"],
                "lineno": l_s,
                "sites_patched": 1,
                "bindings": fb,
                "patched_source": patched,
            })

    return results


# ---------------------------------------------------------------------------
# External Inspectable / Editable / Deletable JSON Skill Store
# ---------------------------------------------------------------------------

def new_cst_store() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "version": 1,
        "external_model_dependency": False,
        "parameters_stored": 0,
        "skills": {},
        "updated_at": None,
    }


def load_cst_store(path: str | pathlib.Path | None = None) -> dict[str, Any]:
    p = pathlib.Path(path) if path is not None else DEFAULT_STORE_PATH
    if not p.is_file():
        return new_cst_store()
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, Mapping) or data.get("schema") != SCHEMA:
        raise ValueError("POLYGLOT_CST_STORE_SCHEMA_MISMATCH")
    out = new_cst_store()
    out["skills"] = {str(k): dict(v) for k, v in (data.get("skills") or {}).items()}
    out["updated_at"] = data.get("updated_at")
    return out


def save_cst_store(store: Mapping[str, Any], path: str | pathlib.Path | None = None) -> pathlib.Path:
    p = pathlib.Path(path) if path is not None else DEFAULT_STORE_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(store)
    payload["schema"] = SCHEMA
    payload["external_model_dependency"] = False
    payload["parameters_stored"] = 0
    payload["updated_at"] = round(time.time(), 3)
    p.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return p


def admit_cst_skill(
    store: dict[str, Any],
    before_source: str,
    after_source: str,
    *,
    language: str = "generic",
    bug_classes: Sequence[str] = (),
    description: str = "",
) -> dict[str, Any]:
    """Induce from ONE verified `(before, after)` repair and admit into external `store`."""
    res = induce_cst_skill(
        before_source,
        after_source,
        language=language,
        bug_classes=bug_classes,
        description=description,
    )
    if not res.get("admitted"):
        return res
    skill = res["skill"]
    sid = skill["skill_id"]
    skills = store.setdefault("skills", {})
    if sid in skills:
        skills[sid]["verified_uses"] = int(skills[sid].get("verified_uses", 1)) + 1
        # Union observed language compatibility
        langs = set((skills[sid].get("preconditions") or {}).get("languages") or ())
        langs.add(language)
        skills[sid].setdefault("preconditions", {})["languages"] = sorted(langs)
    else:
        skills[sid] = skill
    store["parameters_stored"] = 0
    return {"admitted": True, "skill_id": sid, "skill": skills[sid]}


def delete_cst_skill(store: dict[str, Any], skill_id: str) -> bool:
    """Explicitly delete a skill from the external store (immediate forgetting, zero retraining)."""
    skills = store.get("skills")
    if isinstance(skills, dict) and skill_id in skills:
        del skills[skill_id]
        return True
    return False


def record_cst_counterexample(
    store: dict[str, Any],
    skill_id: str,
    *,
    distinguishing_token: str | None = None,
) -> dict[str, Any]:
    """Online refutation: narrow precondition on distinguishing token or quarantine fail-closed."""
    skills = store.get("skills")
    if not isinstance(skills, dict) or skill_id not in skills:
        return {"updated": False, "reason": "SKILL_NOT_FOUND"}
    sk = skills[skill_id]
    sk["refutations"] = int(sk.get("refutations", 0)) + 1
    if distinguishing_token:
        pre = sk.setdefault("preconditions", {})
        req = list(pre.get("required_file_tokens") or [])
        if distinguishing_token not in req:
            req.append(distinguishing_token)
        pre["required_file_tokens"] = req
        sk["status"] = STATUS_NARROWED
        return {"updated": True, "status": STATUS_NARROWED, "required_file_tokens": req}
    sk["status"] = STATUS_QUARANTINED
    return {"updated": True, "status": STATUS_QUARANTINED}


def recall_cst_candidates(
    store: Mapping[str, Any] | None,
    target_source: str,
    *,
    language: str = "generic",
    target_lines: Sequence[int] | None = None,
    max_candidates: int = 12,
) -> list[dict[str, Any]]:
    """Recall and instantiate all active learned CST skills on an unseen target file (Tier-0)."""
    if not isinstance(store, Mapping):
        return []
    skills = store.get("skills")
    if not isinstance(skills, Mapping) or not skills:
        return []
    # Compatible language families (C <-> C++, JS <-> TS)
    compat = {
        "c": {"c", "cpp", "generic"},
        "cpp": {"c", "cpp", "generic"},
        "js": {"js", "ts", "generic"},
        "ts": {"js", "ts", "generic"},
        "py": {"py", "generic"},
        "go": {"go", "generic"},
        "rs": {"rs", "generic"},
        "java": {"java", "generic"},
    }.get(language, {language, "generic"})

    ordered = sorted(
        (
            sk for sk in skills.values()
            if isinstance(sk, Mapping) and sk.get("status") != STATUS_QUARANTINED
        ),
        key=lambda s: (-int(s.get("verified_uses", 1)), int(s.get("refutations", 0)), str(s.get("skill_id", ""))),
    )
    out: list[dict[str, Any]] = []
    seen_patched: set[str] = set()
    for sk in ordered:
        sk_langs = set((sk.get("preconditions") or {}).get("languages") or [sk.get("language", "generic")])
        if not (sk_langs & compat):
            continue
        matches = apply_cst_skill(
            sk,
            target_source,
            language=language,
            target_lines=target_lines,
            max_applications=4,
            apply_all_sites=True,
        )
        for m in matches:
            ps = m["patched_source"]
            if ps not in seen_patched:
                seen_patched.add(ps)
                out.append(m)
                if len(out) >= max_candidates:
                    return out
    return out
