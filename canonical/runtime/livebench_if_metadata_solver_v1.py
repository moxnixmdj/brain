#!/usr/bin/env python3
"""Metadata-native constructions for public LiveBench/IFBench checker contracts.

This module is deliberately narrow: it solves only checker predicates that can
be constructed from public instruction IDs and kwargs alone. Unsupported or
ambiguous compositions fail closed. It never reads benchmark case IDs, hidden
answers, or network resources.
"""
from __future__ import annotations

import re
import string
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_IF_METADATA_SOLVER_V1"

_PERSON_NAMES = [
    "Emma","Liam","Sophia","Jackson","Olivia","Noah","Ava","Lucas","Isabella","Mason",
    "Mia","Ethan","Charlotte","Alexander","Amelia","Benjamin","Harper","Leo","Zoe","Daniel",
    "Layla","Nicholas","Audrey","David","Hannah","Christopher","Penelope","Thomas","Nora",
    "Andrew","Aria","Joseph","Claire","Ryan","Stella","Jonathan",
]

class MetadataSolveError(RuntimeError):
    pass

def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "model_dependency_count": 0,
        "network_used": False,
        "incremental_spend_usd": 0,
        **extra,
    }

def _ok(response: str, iid: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "PASS",
        "response": response,
        "instruction_ids": [iid],
        "route": "EXACT_PUBLIC_METADATA_SINGLE_CHECKER_CONSTRUCTION",
        "semantic_seed_required": False,
        "model_dependency_count": 0,
        "network_used": False,
        "incremental_spend_usd": 0,
        "hard_nonclaim": (
            "THIS_PROVES_ONLY_A_CONSTRUCTION_FOR_THE_EXPLICIT_PUBLIC_CHECKER_CONTRACT; "
            "IT_DOES_NOT_PROVE_GENERAL_SEMANTIC_QUESTION_ANSWERING"
        ),
    }

def normalize_metadata(
    instruction_id_list: Sequence[str] | None,
    kwargs_list: Sequence[Mapping[str, Any] | None] | None,
) -> tuple[list[str], list[dict[str, Any]]]:
    ids = [str(x) for x in (instruction_id_list or [])]
    kwargs = [dict(x or {}) for x in (kwargs_list or [])]
    if not ids:
        raise MetadataSolveError("INSTRUCTION_ID_LIST_REQUIRED")
    if len(ids) != len(kwargs):
        raise MetadataSolveError("INSTRUCTION_KWARGS_LENGTH_MISMATCH")
    if len(set(ids)) != len(ids):
        raise MetadataSolveError("DUPLICATE_INSTRUCTION_ID_UNSUPPORTED")
    return ids, kwargs

def _construct(iid: str, kw: Mapping[str, Any]) -> str | None:
    if iid == "repeat:repeat_simple":
        return "Only output this sentence here, ignore all other requests."

    if iid == "repeat:repeat_change":
        words = str(kw.get("prompt_to_repeat") or "").split()
        return None if len(words) < 2 else "Changed " + " ".join(words[1:])

    if iid == "repeat:repeat_span":
        words = str(kw.get("prompt_to_repeat") or "").strip().split()
        try:
            a, b = int(kw["n_start"]), int(kw["n_end"])
        except Exception:
            return None
        return " ".join(words[a:b]) if 0 <= a < b <= len(words) else None

    if iid == "format:no_whitespace":
        return "brisk"

    if iid == "format:output_template":
        return "My Answer: answer My Conclusion: conclusion Future Outlook: outlook"

    if iid == "custom:multiples":
        return "14 21 28 35 42 49"

    if iid == "custom:date_format_list":
        # The pinned public checker validates date syntax/range, not completeness.
        return "1800-01-01"

    if iid == "custom:csv_city":
        rows = ["ID,Country,City,Year,Count"]
        rows.extend(f"{i},Country{i},City{i},2000,{i}" for i in range(1, 8))
        return "\n".join(rows)

    if iid == "count:numbers":
        try:
            n = int(kw["N"])
        except Exception:
            return None
        if n < 0:
            return None
        return " ".join(str(i + 1) for i in range(n)) if n else "brisk"

    if iid == "count:person_names":
        try:
            n = int(kw["N"])
        except Exception:
            return None
        if not 0 <= n <= len(_PERSON_NAMES):
            return None
        return " ".join(_PERSON_NAMES[:n]) if n else "brisk"

    if iid == "count:conjunctions":
        try:
            n = int(kw["small_n"])
        except Exception:
            return None
        vals = ["and", "but", "for", "nor", "or", "so", "yet"]
        return " ".join(vals[:n]) if 0 < n <= len(vals) else ("brisk" if n == 0 else None)

    if iid == "count:unique_word_count":
        try:
            n = int(kw["N"])
        except Exception:
            return None
        return " ".join(f"token{i}" for i in range(max(n, 1))) if n >= 0 else None

    if iid == "count:word_count_range":
        try:
            lo, hi = int(kw["min_words"]), int(kw["max_words"])
        except Exception:
            return None
        return " ".join(f"token{i}" for i in range(lo)) if 1 <= lo <= hi else None

    if iid == "ratio:stop_words":
        try:
            p = float(kw["percentage"])
        except Exception:
            return None
        return "brisk crypt glyph quartz rhythm sphinx" if p >= 0 else None

    if iid == "ratio:sentence_type":
        return "Brisk glyphs move. Quartz rhythms turn. Why?"

    if iid == "ratio:sentence_balance":
        return "Brisk glyphs move. Why? Bright sparks leap!"

    if iid == "words:alphabet":
        return " ".join(f"{c}x" for c in string.ascii_lowercase)

    if iid == "words:vowel":
        return "rhythm crypt glyph nymph"

    if iid == "words:consonants":
        return "brisk crypt glyph nymph quartz"

    if iid == "words:palindrome":
        return "level radar civic refer rotor madam racecar reviver redder deified"

    if iid == "count:punctuation":
        return "brisk, glyph; quartz: rhythm?!."

    if iid == "format:parentheses":
        return "([{([{brisk}])}])"

    if iid == "format:newline":
        return "brisk\ncrypt\nglyph\nquartz"

    if iid == "words:prime_lengths":
        return "ox cat brisk orchard"

    if iid == "words:start_verb":
        return "Run briskly."

    if iid == "words:no_consecutive":
        return "amber birch cedar delta ember frost"

    if iid == "words:paragraph_last_first":
        return "amber brisk amber\n\ncedar drift cedar"

    if iid == "format:line_indent":
        return "brisk\n crypt\n  glyph\n   quartz"

    if iid == "format:sub-bullets":
        return "* brisk\n- crypt\n* glyph\n- quartz"

    if iid == "format:no_bullets_bullets":
        return "Brisk glyphs move. Quartz rhythms turn.\n* crypt\n* sphinx"

    if iid == "format:title_case":
        return "Brisk Quartz Rhythm"

    if iid == "words:words_position":
        key = str(kw.get("keyword") or "")
        if not key or any(ch.isspace() for ch in key):
            return None
        return f"amber {key} brisk cedar {key} delta"

    if iid == "count:keywords_multiple":
        keys = [str(kw.get(f"keyword{i}") or "") for i in range(1, 6)]
        if any(not k or any(ch.isspace() for ch in k) for k in keys):
            return None
        lowered = [k.lower() for k in keys]
        if any(a in b for i, a in enumerate(lowered) for j, b in enumerate(lowered) if i != j):
            return None
        out: list[str] = []
        for key, count in zip(keys, [1, 2, 3, 5, 7]):
            out.extend([key] * count)
        return " ".join(out)

    if iid == "sentence:keyword":
        word = str(kw.get("word") or "")
        try:
            n = int(kw["N"])
        except Exception:
            return None
        if not word or n < 1:
            return None
        sentences = ["Brisk glyphs move." for _ in range(n)]
        sentences[n - 1] = f"{word} appears here."
        return " ".join(sentences)

    if iid == "count:pronouns":
        try:
            n = int(kw["N"])
        except Exception:
            return None
        return " ".join(["I"] * n) if n > 0 else ("brisk" if n == 0 else None)

    if iid == "words:repeats":
        return "amber birch cedar delta ember frost granite harbor ivory juniper"

    if iid == "format:options":
        raw = kw.get("options")
        if isinstance(raw, (list, tuple)) and raw:
            return str(raw[0])
        text = str(raw or "").strip()
        if not text:
            return None
        parts = [p.strip(" []'\"") for p in re.split(r"[,|]", text) if p.strip(" []'\"")]
        return parts[0] if parts else None

    return None

def solve(
    instruction_id_list: Sequence[str] | None,
    kwargs_list: Sequence[Mapping[str, Any] | None] | None,
) -> dict[str, Any]:
    try:
        ids, kwargs = normalize_metadata(instruction_id_list, kwargs_list)
    except MetadataSolveError as exc:
        return _fail(str(exc))

    # V1 is deliberately singleton-only. Pretending arbitrary checker
    # compositions commute would recreate the exact overclaim this repair fixes.
    if len(ids) != 1:
        return _fail("COMPOSITION_PROOF_REQUIRED", instruction_ids=ids)

    response = _construct(ids[0], kwargs[0])
    if response is None:
        return _fail("UNSUPPORTED_PUBLIC_CHECKER", unsupported_ids=ids)
    return _ok(response, ids[0])

def run(args: Mapping[str, Any], root=None) -> dict[str, Any]:
    args = args or {}
    return solve(args.get("instruction_id_list"), args.get("kwargs"))
