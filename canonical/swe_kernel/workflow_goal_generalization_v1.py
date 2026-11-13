"""Verified goal-variant metadata for compiled workflow skills.

A workflow's first goal sentence is one surface form of an effect.  When a
held-out execution qualifies under a different surface form, the compiler may
store that second form as a retrieval variant.  The variant is not a fuzzy
similarity score and not an authority grant: it is a content-addressed regular
template with the same typed holes as the original skill, admitted only after
the existing held-out execution, sabotage control, and ownership gate pass.

This module keeps the variant schema and a conservative surface guard in one
place.  It does not execute tools, mutate state, or register capabilities.
"""
from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_WORKFLOW_GOAL_VARIANTS_V1"

_HOLE_RE = re.compile(r"^\?[a-z]+\d+$")
# Mask user data before looking for control language.  A quoted note may contain
# the word "not"; the request around it may not.
_LITERAL_MASKS = (
    re.compile(r"https?://[^\s\"'<>)\]]+"),
    re.compile(r"'[^'\n]*'|\"[^\"\n]*\"|“[^”\n]*”|‘[^’\n]*’"),
    re.compile(r"(?<![A-Za-z0-9_])(?:\./|\.\./)?[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+(?![A-Za-z0-9_])"),
    re.compile(r"(?<![A-Za-z0-9_])[A-Za-z0-9_-]+\.[A-Za-z0-9]{1,8}(?![A-Za-z0-9_])"),
    re.compile(r"(?<![A-Za-z0-9_])\d+(?:\.\d+)?(?![A-Za-z0-9_])"),
)
# Deliberately conservative lexical guard, not a natural-language understanding
# claim.  It refuses negation, contrast, conditionals, and obvious multi-action
# requests outside masked literals.
_UNSAFE_WORDS = {
    "not", "no", "never", "dont", "don't", "cannot", "can't", "without", "unless",
    "instead", "rather", "but", "however", "although", "if", "except", "only",
    "and", "or", "then", "also", "plus", "followed", "after", "before", "while",
}
_WORD_RE = re.compile(r"[A-Za-z']+")


def is_hole(value: Any) -> bool:
    return isinstance(value, str) and bool(_HOLE_RE.fullmatch(value))


def surface_is_safe(goal: str) -> bool:
    """Return False for control surfaces the variant learner must not widen to."""
    if not isinstance(goal, str) or not goal.strip() or len(goal) > 4096:
        return False
    if any(ord(ch) < 32 and ch not in "\t\n\r" for ch in goal):
        return False
    masked = goal
    for pattern in _LITERAL_MASKS:
        masked = pattern.sub(" ", masked)
    words = {w.lower().replace("’", "'") for w in _WORD_RE.findall(masked)}
    return not (words & _UNSAFE_WORDS)


def validate_variant(variant: Any, param_order: Sequence[str]) -> bool:
    """A variant must be a compilable template over exactly the skill's holes."""
    if not isinstance(variant, Mapping):
        return False
    skeleton = variant.get("goal_skeleton")
    regex = variant.get("goal_regex")
    tokens = variant.get("skeleton_tokens")
    if not isinstance(skeleton, str) or not skeleton.strip():
        return False
    if not isinstance(regex, str) or not regex.strip():
        return False
    if not isinstance(tokens, list) or not all(isinstance(t, str) for t in tokens):
        return False
    try:
        compiled = re.compile(regex)
    except re.error:
        return False
    groups = set(compiled.groupindex)
    expected = {h[1:] for h in param_order if is_hole(h)}
    # Back-references do not add groupindex entries; every named capture must be
    # a declared hole, and every declared hole must be capturable somewhere.
    return groups == expected and bool(expected)


def canonical_variants(variants: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Deterministic, JSON-safe variant records for hashing and export."""
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for variant in variants:
        if not isinstance(variant, Mapping):
            continue
        regex = str(variant.get("goal_regex") or "")
        if not regex or regex in seen:
            continue
        seen.add(regex)
        out.append({
            "goal_skeleton": str(variant.get("goal_skeleton") or ""),
            "goal_regex": regex,
            "skeleton_tokens": sorted({str(t) for t in variant.get("skeleton_tokens") or []}),
        })
    return out


def retrieval_tokens(skill: Mapping[str, Any]) -> set[str]:
    tokens = {str(t) for t in skill.get("skeleton_tokens") or [] if isinstance(t, str)}
    for variant in skill.get("goal_variants") or []:
        if isinstance(variant, Mapping):
            tokens.update(str(t) for t in variant.get("skeleton_tokens") or [] if isinstance(t, str))
    return tokens
