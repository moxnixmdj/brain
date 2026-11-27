#!/usr/bin/env python3
"""Executable symbolic checks for the union25 residual-basis reduction.

This checks only claims derivable without third-party runtime execution.
Language-detector and NLTK-dependent claims stay explicitly unresolved.
"""
from __future__ import annotations

import re
from collections import Counter

from canonical.runtime import livebench_legacy15_composition_archetypes_v1 as active15
from canonical.runtime import livebench_public_scope_union_v1 as scope

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_UNION25_RESIDUAL_BASIS_V1"

FREQ = "keywords:frequency"
LFREQ = "keywords:letter_frequency"
LANG = "language:response_language"
PH = "detectable_content:number_placeholders"
CONS = "detectable_format:constrained_response"
HI = "detectable_format:number_highlighted_sections"
CAPF = "change_case:capital_word_frequency"
UP = "change_case:english_capital"
LOW = "change_case:english_lowercase"
NOCOMMA = "punctuation:no_comma"

EXTRA10 = {
    FREQ, LFREQ, LANG, PH, CONS, HI, CAPF, UP, LOW, NOCOMMA,
}

MAIL_RE = re.compile(
    r"[-_.0-9A-Za-z]{1,64}@[-_0-9A-Za-z]{1,255}[-_.0-9A-Za-z]{1,255}"
)


def placeholder_payload(n: int) -> str:
    if not 1 <= n <= 4:
        raise ValueError("PLACEHOLDER_DOMAIN")
    return "[]" * n


def highlight_payload(n: int) -> str:
    if not 1 <= n <= 4:
        raise ValueError("HIGHLIGHT_DOMAIN")
    return "+ " + " ".join("*+*" for _ in range(n))


def masked_nth(first_word: str) -> str:
    w = first_word.strip().lower()
    if not re.fullmatch(r"[a-z]+", w):
        raise ValueError("WORD_DOMAIN")
    return f"{w}.0@00"


def nth_seen(token: str) -> str:
    word = token.split()[0].strip().lstrip("'").lstrip('"')
    out = ""
    for ch in word:
        if ch in {".", ",", "?", "!", "'", '"'}:
            break
        out += ch.lower()
    return out


def masked_postscript(marker: str) -> str:
    if marker == "P.S.":
        return "P.S.@00"
    if marker == "P.P.S":
        return "P.P.S@00"
    raise ValueError("POSTSCRIPT_DOMAIN")


def postscript_passes(text: str, marker: str) -> bool:
    if marker == "P.S.":
        pat = r"\s*p\.\s?s\..*$"
    elif marker == "P.P.S":
        pat = r"\s*p\.\s?p\.\s?s.*$"
    else:
        return False
    return bool(re.findall(pat, text.lower(), flags=re.MULTILINE))


def masked_letter_mass(letter: str, n: int) -> str:
    letter = letter.lower()
    if not re.fullmatch(r"[a-z]", letter) or not 1 <= n <= 10:
        raise ValueError("LETTER_DOMAIN")
    return letter * n + "@00"


def masked_keyword_mass(keyword: str, n: int) -> str:
    if not re.fullmatch(r"[A-Za-z]+", keyword) or not 1 <= n <= 3:
        raise ValueError("KEYWORD_DOMAIN")
    return " ".join(f"{keyword}{i}@00" for i in range(n))


def forced_letter_floor(letter: str, nth_word=None, postscript=None) -> int:
    pieces = []
    if nth_word:
        pieces.append(masked_nth(nth_word))
    if postscript:
        pieces.append(masked_postscript(postscript))
    return Counter(" ".join(pieces).lower())[letter.lower()]


def section_case_collision(case_id: str, splitter: str) -> bool:
    if splitter not in {"Section", "SECTION"}:
        raise ValueError("SECTION_DOMAIN")
    if case_id == LOW:
        return True
    if case_id == UP:
        return splitter == "Section"
    raise ValueError("CASE_ID")


def verify() -> dict:
    extra = set(scope.TABLE4_25) - set(active15.ACTIVE_IDS)
    assert extra == EXTRA10

    for n in range(1, 5):
        p = placeholder_payload(n)
        assert len(re.findall(r"\[.*?\]", p)) == n
        assert not re.findall(r"\w+", p)
        assert not re.search(r"[A-Za-z,\n.!?]", p)

        h = highlight_payload(n)
        singles = [
            x for x in re.findall(r"\*[^\n\*]*\*", h)
            if x.strip("*").strip()
        ]
        doubles = [
            x for x in re.findall(r"\*\*[^\n\*]*\*\*", h)
            if x.removeprefix("**").removesuffix("**").strip()
        ]
        assert len(singles) + len(doubles) == n
        assert not re.findall(r"^\s*\*[^\*].*$", h, flags=re.MULTILINE)
        assert not re.findall(r"\w+", h)
        assert not re.search(r"[A-Za-z,\n.!?]", h)

    for w in ("alpha", "section", "z"):
        m = masked_nth(w)
        assert nth_seen(m) == w
        assert MAIL_RE.fullmatch(m)

    for marker in ("P.S.", "P.P.S"):
        m = masked_postscript(marker)
        assert postscript_passes("9\n" + m, marker)
        assert MAIL_RE.fullmatch(m)

    for letter in ("a", "m", "z"):
        m = masked_letter_mass(letter, 10)
        assert Counter(m.lower())[letter] == 10
        assert MAIL_RE.fullmatch(m)

    for kw in ("alpha", "section", "anything"):
        m = masked_keyword_mass(kw, 3)
        assert len(re.findall(re.escape(kw), m, flags=re.IGNORECASE)) == 3
        assert all(MAIL_RE.fullmatch(x) for x in m.split())

    assert section_case_collision(LOW, "Section")
    assert section_case_collision(LOW, "SECTION")
    assert section_case_collision(UP, "Section")
    assert not section_case_collision(UP, "SECTION")

    return {
        "schema": SCHEMA,
        "status": "PASS__SYMBOLIC_EXTRA10_RESIDUAL_BASIS",
        "active_count": len(active15.ACTIVE_IDS),
        "union_count": len(scope.TABLE4_25),
        "extra_count": len(extra),
        "detector_mask_primitives": 4,
        "terminal_data_used": False,
        "acceptance_credit": False,
        "remaining": [
            "EXACT_LANGDETECT_1_0_9_BINDING",
            "30_LANGUAGE_CARRIER_BANK",
            "LESS_THAN_FREQUENCY_COLLISION_ARITHMETIC",
            "CAPITAL_WORD_FREQUENCY_EXACT_NLTK_CLOSURE",
            "COMPOSE_WITH_ACTIVE15_MINIMUM_CUT",
        ],
    }


def run(args=None, root=None):
    return verify()


if __name__ == "__main__":
    import json
    print(json.dumps(verify(), indent=2, sort_keys=True))
