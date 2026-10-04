#!/usr/bin/env python3
"""Exact reachable lexical collision quotient for frozen LiveBench legacy15.

The raw public lexical generator uses 1,525 unique alphabetic words, but the
active15 satisfiability interactions depend only on:
- whether the nth-paragraph first word is forbidden;
- whether each fixed end-phrase collision word is forbidden; and
- which of the two fixed end phrases is selected.

The prior safe upper bound was 320 signatures. Reachability removes impossible
bit assignments when the nth word itself is one of the four end-phrase words,
leaving exactly 192 reachable signatures.
"""
from __future__ import annotations

import ast
import hashlib
from itertools import product
from pathlib import Path
from typing import Any, Iterable

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY15_LEXICAL_COLLISION_SIGNATURES_V2"
PINNED_UTIL_BLOB = "1f0dc0eaa05bd0f72f82f8183b90276ea4d2a87b"
EXPECTED_WORD_COUNT = 1525
KEYWORD_COUNT = 5
SPECIAL_WORDS = ("other", "anything", "can", "help")
NTH_CATEGORIES = (*SPECIAL_WORDS, "ALL_OTHER")
END_PHRASES = (
    "Any other questions?",
    "Is there anything else I can help with?",
)


class LexicalSignatureError(ValueError):
    pass


def _git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data
    ).hexdigest()


def _word_list_from_source(source: str) -> tuple[str, ...]:
    tree = ast.parse(source)
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if not any(isinstance(t, ast.Name) and t.id == "WORD_LIST" for t in targets):
            continue
        value = ast.literal_eval(node.value)
        words = tuple(str(x) for x in value)
        return words
    raise LexicalSignatureError("WORD_LIST_LITERAL_NOT_FOUND")


def load_pinned_word_list(livebench_root: str | Path) -> tuple[str, ...]:
    path = (
        Path(livebench_root).resolve()
        / "livebench"
        / "if_runner"
        / "instruction_following_eval"
        / "instructions_util.py"
    )
    if not path.is_file():
        raise LexicalSignatureError("PINNED_UTIL_SOURCE_MISSING")
    raw = path.read_bytes()
    actual = _git_blob_sha(raw)
    if actual != PINNED_UTIL_BLOB:
        raise LexicalSignatureError("PINNED_UTIL_BLOB_DRIFT:" + actual)
    words = _word_list_from_source(raw.decode("utf-8"))
    validate_word_list(words)
    return words


def validate_word_list(words: Iterable[str]) -> tuple[str, ...]:
    rows = tuple(str(w) for w in words)
    if len(rows) != EXPECTED_WORD_COUNT:
        raise LexicalSignatureError("WORD_COUNT_DRIFT:" + str(len(rows)))
    if len(set(rows)) != EXPECTED_WORD_COUNT:
        raise LexicalSignatureError("WORD_LIST_NOT_UNIQUE")
    if any(not w.isascii() or not w.isalpha() for w in rows):
        raise LexicalSignatureError("WORD_LIST_NOT_ASCII_ALPHA")
    missing = sorted(set(SPECIAL_WORDS) - set(rows))
    if missing:
        raise LexicalSignatureError("SPECIAL_WORD_MISSING:" + ",".join(missing))
    return rows


def enumerate_signatures(words: Iterable[str]) -> tuple[dict[str, Any], ...]:
    rows = validate_word_list(words)
    neutral = tuple(w for w in rows if w not in SPECIAL_WORDS)
    if len(neutral) < 16:
        raise LexicalSignatureError("INSUFFICIENT_NEUTRAL_WORDS")

    representative_other = neutral[0]
    existence = list(neutral[8:13])
    out: list[dict[str, Any]] = []

    for nth_category in NTH_CATEGORIES:
        nth_word = representative_other if nth_category == "ALL_OTHER" else nth_category

        for end_phrase in END_PHRASES:
            # bit order: nth collision, other, anything, can, help
            for bits in product((False, True), repeat=5):
                nth_forbidden = bits[0]
                special_membership = dict(zip(SPECIAL_WORDS, bits[1:]))

                # If nth_word is itself a special word, these are the same
                # proposition. Nominal states disagreeing on the two bits are
                # not generator-reachable.
                if nth_word in special_membership:
                    if nth_forbidden != special_membership[nth_word]:
                        continue

                required_forbidden = {
                    word for word, present in special_membership.items() if present
                }
                if nth_forbidden:
                    required_forbidden.add(nth_word)

                # Enforce every declared absence before filling to exactly five
                # unique generated forbidden words.
                excluded = {
                    word for word, present in special_membership.items() if not present
                }
                if not nth_forbidden:
                    excluded.add(nth_word)

                forbidden = list(sorted(required_forbidden))
                for word in neutral:
                    if word in required_forbidden or word in excluded:
                        continue
                    forbidden.append(word)
                    if len(forbidden) == KEYWORD_COUNT:
                        break
                if len(forbidden) != KEYWORD_COUNT:
                    raise LexicalSignatureError("FORBIDDEN_FILL_FAILED")

                observed = set(forbidden)
                if (nth_word in observed) != nth_forbidden:
                    raise LexicalSignatureError("NTH_MEMBERSHIP_CONSTRUCTION_DRIFT")
                for word, expected in special_membership.items():
                    if (word in observed) != expected:
                        raise LexicalSignatureError("SPECIAL_MEMBERSHIP_CONSTRUCTION_DRIFT:" + word)

                out.append({
                    "nth_category": nth_category,
                    "nth_word": nth_word,
                    "nth_in_forbidden": nth_forbidden,
                    "special_forbidden_membership": special_membership,
                    "end_phrase": end_phrase,
                    "forbidden_words": forbidden,
                    "existence_keywords": existence,
                    "lexical_hard_unsat_expected": bool(
                        nth_forbidden
                        or (
                            end_phrase == END_PHRASES[0]
                            and special_membership["other"]
                        )
                        or (
                            end_phrase == END_PHRASES[1]
                            and (
                                special_membership["anything"]
                                or special_membership["can"]
                                or special_membership["help"]
                            )
                        )
                    ),
                })

    result = tuple(out)
    if len(result) != 192:
        raise LexicalSignatureError("REACHABLE_SIGNATURE_COUNT_DRIFT:" + str(len(result)))

    keys = {
        (
            row["nth_category"],
            row["nth_in_forbidden"],
            tuple(row["special_forbidden_membership"][w] for w in SPECIAL_WORDS),
            row["end_phrase"],
        )
        for row in result
    }
    if len(keys) != len(result):
        raise LexicalSignatureError("DUPLICATE_SIGNATURE")
    return result


def verify(words: Iterable[str]) -> dict[str, Any]:
    signatures = enumerate_signatures(words)
    unsat = sum(bool(x["lexical_hard_unsat_expected"]) for x in signatures)
    return {
        "schema": SCHEMA,
        "status": "PASS__EXACT_192_REACHABLE_LEXICAL_COLLISION_SIGNATURES",
        "raw_word_identity_count": EXPECTED_WORD_COUNT,
        "prior_conservative_signature_bound": 320,
        "exact_reachable_signature_count": len(signatures),
        "lexical_hard_unsat_signature_count": unsat,
        "lexical_not_hard_unsat_signature_count": len(signatures) - unsat,
        "nth_categories": list(NTH_CATEGORIES),
        "end_phrases": list(END_PHRASES),
        "terminal_data_used": False,
        "terminal_frequency_inferred": False,
        "acceptance_credit": False,
    }


def run(args: dict[str, Any] | None = None, root=None) -> dict[str, Any]:
    args = args or {}
    livebench_root = args.get("livebench_root")
    if not livebench_root:
        raise LexicalSignatureError("LIVEBENCH_ROOT_REQUIRED")
    return verify(load_pinned_word_list(livebench_root))


if __name__ == "__main__":
    import json
    import sys
    print(json.dumps(run(json.load(sys.stdin)), indent=2, sort_keys=True))
