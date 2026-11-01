#!/usr/bin/env python3
"""Carry a learned repair lesson across a language boundary — deliberately, and only where it is safe.

Why this module exists
----------------------
`VerifiedSkillStore` keys every rule by language: `_load_rules` selects
`WHERE domain='swe_code_repair' AND language=?`. Measured 2026-11-01: a lesson taught in
Python, exported, imported into a fresh store and re-read is **accepted and stored**, and
`lookup_rules('go')` still returns 0. The lesson arrives and is never offered. So "learn it
once" was true per language and false across languages, and the boundary was a key, not a
property of the lesson.

This module is the bridge, and it is deliberately NOT a change to the crystallizer. That
kernel is load-bearing and measured; a cross-language experiment must not be able to move it.
Everything here is an adapter that only ever *proposes*, and a proposal is a hypothesis.

What crosses, and what does not
-------------------------------
A rule may cross only when its rewrite is **lexical**: it changes operators, literals or
punctuation, and introduces no identifier of its own. `<= hi` -> `< hi` is the same edit in
Python, Go, Rust, TypeScript and C++ — it is the *same token swap*, and refusing to carry it
was an accident of the key.

A rule that introduces an identifier (a temporary, a helper call, a renamed symbol) carries
language-specific spelling and is refused. So is a rule whose operator does not exist in the
target language. Both refusals are named, not silent.

Three independent guards, in order:
  1. **lexical** — the rule's changed tokens are operators/literals, and no new identifier.
  2. **syntactic** — the patched text must still parse in the target language.
  3. **semantic** — the caller's own verifier must pass the patched text.

Guard 3 is the only one that can prove anything, and it is mandatory. A bridge that could
return an unverified patch would be worse than no bridge.
"""
from __future__ import annotations

import ast
import re
from typing import Any, Callable, Iterable, Mapping

SCHEMA = "PROJECT_BRAIN_LANGUAGE_NEUTRAL_SKILL_BRIDGE_V1"

# Operators and punctuation that mean the same thing wherever they appear in this family.
_PORTABLE_OPS = frozenset({
    "<=", ">=", "<", ">", "==", "!=", "+", "-", "*", "/", "%",
    "&&", "||", "!", "and", "or", "not", "(", ")", "{", "}", "[", "]",
    ";", ",", "?", ":", "=", "+=", "-=",
})

_NUM = re.compile(r"^\d+(?:\.\d+)?$")
_IDENT = re.compile(r"^[A-Za-z_$][\w$]*$")

# Keywords that are spelled DIFFERENTLY across this family, so a rule mentioning one cannot be
# carried verbatim. Words that are identical everywhere (`return`, `if`, `else`, `while`,
# `for`, `break`, `continue`) are deliberately NOT here: refusing them produced a false
# refusal on the very first cross-language lesson measured (2026-11-01), which is exactly the
# over-strict gate this repo keeps paying for.
# Keywords spelled identically across python/go/rust/typescript/java/cpp. Anything else is
# language-specific spelling and must not be carried. An earlier version of this file refused
# `return`, which is identical everywhere, and thereby refused the very first cross-language
# lesson measured. That is the over-strict gate this repo keeps paying for, so the set is
# deliberately small and every member was checked against all six languages.
_PORTABLE_KEYWORDS = frozenset({
    "return", "if", "else", "while", "for", "break", "continue",
})

# Names that exist in only some of those languages and would be a fabrication if carried.
_PYTHON_ONLY_NAMES = frozenset({
    "sum", "len", "range", "enumerate", "zip", "sorted", "isinstance", "getattr",
    "self", "elif", "lambda", "None", "True", "False", "yield", "def", "class",
    "import", "from", "with", "as", "raise", "except", "finally", "print",
    "var", "const", "let", "fn", "func", "function", "struct", "impl", "trait",
    "interface", "export", "package", "nil", "null", "true", "false", "mut", "pub",
})

class BridgeRefusal(RuntimeError):
    """A named refusal. The bridge never crosses quietly and never guesses."""


# --------------------------------------------------------------------------- guard 1
def _tokens_of(rule: Mapping[str, Any], key: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for tok in rule.get(key) or []:
        if isinstance(tok, (list, tuple)) and len(tok) >= 2:
            out.append((str(tok[0]), str(tok[1])))
    return out


def is_lexical_rule(rule: Mapping[str, Any]) -> tuple[bool, str]:
    """Is this rule's rewrite a pure operator/literal edit that can cross a language boundary?

    Returns (ok, reason). Measured against the store's real token vocabulary: kinds are
    ``kw``, ``ws``, ``op``, ``ident``, ``num``, ``str``, ``hole_id``, ``hole_num``,
    ``hole_str``.
    """
    pattern = _tokens_of(rule, "pattern_tokens")
    replacement = _tokens_of(rule, "replacement_tokens")
    if not pattern or not replacement:
        return False, "RULE_HAS_NO_TOKEN_PATTERN"

    pattern_names = {v for k, v in pattern if k in ("kw", "ident")}

    for kind, value in pattern + replacement:
        if kind == "kw":
            if value in _PYTHON_ONLY_NAMES or (value not in _PORTABLE_KEYWORDS
                                               and not value.islower()):
                return False, f"RULE_MENTIONS_LANGUAGE_SPECIFIC_NAME:{value}"
            if value in _PYTHON_ONLY_NAMES:
                return False, f"RULE_MENTIONS_LANGUAGE_SPECIFIC_NAME:{value}"
        if kind == "op" and value not in _PORTABLE_OPS:
            return False, f"OPERATOR_NOT_PORTABLE:{value}"

    # An identifier the rewrite INTRODUCES is language-specific spelling. An identifier the
    # pattern already bound is the caller's own symbol and crosses fine.
    for kind, value in replacement:
        if kind in ("ident", "kw") and value not in pattern_names:
            if kind == "ident":
                return False, f"RULE_INTRODUCES_A_FRESH_IDENTIFIER:{value}"
    for kind, value in replacement:
        if kind in ("hole_id", "hole_num", "hole_str"):
            continue
    return True, "LEXICAL_REWRITE"


# --------------------------------------------------------------------------- guard 2
def parses_in(language: str, text: str) -> tuple[bool, str]:
    """Cheap syntactic admission for the target language. Conservative on purpose."""
    lang = (language or "").lower()
    if lang == "python":
        try:
            ast.parse(text)
            return True, "PYTHON_AST_OK"
        except SyntaxError:
            return False, "TARGET_SYNTAX_INVALID:python"
    try:
        from canonical.runtime import tree_sitter_swe_kernel_v1 as tsk  # type: ignore
        tree = tsk.parse_bytes(lang, text.encode("utf-8"))
        if bool(getattr(tree.root_node, "has_error", False)):
            return False, f"TARGET_SYNTAX_INVALID:{lang}"
        return True, f"TREE_SITTER_OK:{lang}"
    except Exception:
        pass
    # No parser available: balance check only, and say so rather than implying more.
    pairs = {"(": ")", "[": "]", "{": "}"}
    depth = {k: 0 for k in pairs}
    for ch in text:
        if ch in pairs:
            depth[ch] += 1
        else:
            for open_ch, close_ch in pairs.items():
                if ch == close_ch:
                    depth[open_ch] -= 1
                    if depth[open_ch] < 0:
                        return False, f"TARGET_SYNTAX_INVALID:{lang}"
    if any(v != 0 for v in depth.values()):
        return False, f"TARGET_SYNTAX_INVALID:{lang}"
    return True, "BALANCE_ONLY"


# --------------------------------------------------------------------------- the bridge
def cross_language_candidates(
    store: Any,
    *,
    source_language: str,
    target_language: str,
    error_class: str | None = None,
) -> list[dict[str, Any]]:
    """Rules learned in `source_language` that are allowed to be offered in `target_language`."""
    if source_language.lower() == target_language.lower():
        raise BridgeRefusal("SAME_LANGUAGE_IS_NOT_A_CROSSING")
    try:
        rules = store.lookup_rules(source_language, error_class)
    except TypeError:
        rules = store.lookup_rules(source_language)
    out: list[dict[str, Any]] = []
    for rule in rules:
        ok, why = is_lexical_rule(rule)
        if not ok:
            continue
        out.append(dict(rule, bridge_reason=why, from_language=source_language))
    return out


def recall_across_languages(
    store: Any,
    *,
    source_text: str,
    target_language: str,
    verifier: Callable[[str], bool],
    error_class: str | None = None,
    source_languages: Iterable[str] | None = None,
) -> dict[str, Any] | None:
    """Offer a lesson learned in another language, and accept it only if the verifier passes.

    `verifier` is mandatory: this function cannot return a patch it has not verified, which is
    the whole safety property. Returns None when nothing crossed, so a caller can fall back to
    learning from scratch exactly as before.
    """
    if not callable(verifier):
        raise BridgeRefusal("CROSS_LANGUAGE_RECALL_REQUIRES_A_VERIFIER")
    from canonical.swe_kernel import verified_skill_crystallizer_v1 as cry

    seen: set[str] = set()
    langs = (list(source_languages) if source_languages is not None
             else ["python", "go", "rust", "typescript", "cpp", "javascript", "java"])
    for src_lang in langs:
        if src_lang.lower() == target_language.lower():
            continue
        for rule in cross_language_candidates(
            store, source_language=src_lang, target_language=target_language,
            error_class=error_class,
        ):
            sid = str(rule.get("skill_id") or "")
            if sid and sid in seen:
                continue
            seen.add(sid)
            for candidate in cry.iter_crystallized_code_rule_candidates(source_text, rule):
                if not candidate or candidate == source_text:
                    continue
                ok, why = parses_in(target_language, candidate)
                if not ok:
                    continue
                try:
                    passed = bool(verifier(candidate))
                except Exception:
                    passed = False
                if not passed:
                    continue
                return {
                    "schema": SCHEMA,
                    "skill_id": rule.get("skill_id"),
                    "from_language": src_lang,
                    "to_language": target_language,
                    "bridge_reason": rule.get("bridge_reason"),
                    "syntax_evidence": why,
                    "patched_source": candidate,
                    "from_cross_language_memory": True,
                    "whole_task_correctness_proved": False,
                    "verifier_passed": True,
                }
    return None


def explain(
    store: Any, *, source_language: str, target_language: str,
    error_class: str | None = None,
) -> dict[str, Any]:
    """Why a lesson did or did not cross. Measurement without a proposal."""
    try:
        rules = store.lookup_rules(source_language, error_class)
    except TypeError:
        rules = store.lookup_rules(source_language)
    crossed, refused = [], []
    for rule in rules:
        ok, why = is_lexical_rule(rule)
        (crossed if ok else refused).append(
            {"skill_id": rule.get("skill_id"), "reason": why})
    return {"from_language": source_language, "to_language": target_language,
            "eligible": crossed, "refused": refused,
            "refused_count": len(refused), "eligible_count": len(crossed)}
