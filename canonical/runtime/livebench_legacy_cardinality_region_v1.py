#!/usr/bin/env python3
"""Compile visible legacy IFEval cardinality language into semantic feasible regions.

The representation is intentionally checker-instance agnostic.  Multiple hidden
instances of the same legacy checker family can express one interval (for
example, 20-25 sentences -> >=20 AND <26), while repeated keyword-frequency
instances can constrain different keywords.  Blind deduplication by instruction
ID is therefore unsound.

This compiler consumes visible prompt text only.  It never reads question IDs,
instruction_id_list, kwargs, answers, scores, or terminal metadata.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_LEGACY_CARDINALITY_REGION_V1"
PUBLIC_GOOGLE_IFEVAL_COMMIT = "e49bbfe381c9c0e564b937f1c4e163a2273c65cc"
PUBLIC_GOOGLE_IFEVAL_INPUT_BLOB = "cbe52f6eecf3986fdac745b4acba4da1408eb146"

_ONES = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
    "eighteen": 18, "nineteen": 19,
}
_TENS = {
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}
_SPECIAL = {"once": 1, "twice": 2, "thrice": 3}

_NUM_TOKEN = (
    r"(?:\d+|zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|"
    r"twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|"
    r"twenty(?:[- ](?:one|two|three|four|five|six|seven|eight|nine))?|"
    r"thirty(?:[- ](?:one|two|three|four|five|six|seven|eight|nine))?|"
    r"forty(?:[- ](?:one|two|three|four|five|six|seven|eight|nine))?|"
    r"fifty(?:[- ](?:one|two|three|four|five|six|seven|eight|nine))?|"
    r"sixty(?:[- ](?:one|two|three|four|five|six|seven|eight|nine))?|"
    r"seventy(?:[- ](?:one|two|three|four|five|six|seven|eight|nine))?|"
    r"eighty(?:[- ](?:one|two|three|four|five|six|seven|eight|nine))?|"
    r"ninety(?:[- ](?:one|two|three|four|five|six|seven|eight|nine))?|"
    r"one hundred|two hundred|three hundred|four hundred|five hundred|"
    r"six hundred|seven hundred|eight hundred|nine hundred|one thousand)"
)


def parse_small_number(token: str) -> int:
    raw = re.sub(r"[-\s]+", " ", str(token or "").strip().lower())
    if raw.isdigit():
        return int(raw)
    if raw in _SPECIAL:
        return _SPECIAL[raw]
    if raw in _ONES:
        return _ONES[raw]
    if raw in _TENS:
        return _TENS[raw]
    parts = raw.split()
    if len(parts) == 2 and parts[0] in _TENS and parts[1] in _ONES:
        return _TENS[parts[0]] + _ONES[parts[1]]
    if len(parts) == 2 and parts[1] == "hundred" and parts[0] in _ONES:
        return 100 * _ONES[parts[0]]
    if raw == "one thousand":
        return 1000
    raise ValueError("UNRECOGNIZED_SMALL_NUMBER")


@dataclass(frozen=True)
class CardinalityRegion:
    family: str
    selector: str
    lower: int | None
    upper: int | None
    evidence: str
    route: str

    def __post_init__(self):
        if self.lower is not None and self.lower < 0:
            raise ValueError("NEGATIVE_LOWER")
        if self.upper is not None and self.upper < 0:
            raise ValueError("NEGATIVE_UPPER")
        if (
            self.lower is not None
            and self.upper is not None
            and self.lower > self.upper
        ):
            raise ValueError("EMPTY_REGION")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _region(
    family: str,
    selector: str,
    lower: int | None,
    upper: int | None,
    match: re.Match[str],
    route: str,
) -> CardinalityRegion:
    return CardinalityRegion(
        family=family,
        selector=selector,
        lower=lower,
        upper=upper,
        evidence=match.group(0),
        route=route,
    )


def _count_ranges(prompt: str, noun: str, family: str, selector: str) -> list[CardinalityRegion]:
    p = str(prompt or "")
    out: list[CardinalityRegion] = []
    n = _NUM_TOKEN

    # Exact / closed ranges first because they are strictly more informative.
    patterns = [
        (
            rf"(?P<a>{n})\s+(?:to|through)\s+(?P<b>{n})\s+{noun}",
            lambda m: (parse_small_number(m["a"]), parse_small_number(m["b"])),
            "VISIBLE_CLOSED_RANGE",
        ),
        (
            rf"(?:between|in\s+the\s+range\s+of)\s+(?P<a>{n})\s+(?:and|to)\s+(?P<b>{n})\s+{noun}",
            lambda m: (parse_small_number(m["a"]), parse_small_number(m["b"])),
            "VISIBLE_CLOSED_RANGE",
        ),
        (
            rf"(?P<a>{n})\s+or\s+(?P<b>{n})\s+{noun}",
            lambda m: (parse_small_number(m["a"]), parse_small_number(m["b"])),
            "VISIBLE_DISCRETE_RANGE_HULL",
        ),
        (
            rf"exactly\s+(?P<a>{n})\s+{noun}",
            lambda m: (parse_small_number(m["a"]), parse_small_number(m["a"])),
            "VISIBLE_EXACT",
        ),
    ]
    for pattern, bounds, route in patterns:
        for m in re.finditer(pattern, p, flags=re.I):
            lo, hi = bounds(m)
            out.append(_region(family, selector, lo, hi, m, route))

    # "30-line ... each line ... exactly one sentence" is a public IFEval
    # paraphrase of exactly 30 sentences.
    if noun.startswith("sentenc"):
        pat = rf"(?P<a>{n})[- ]line\b[\s\S]{{0,180}}?each\s+line[\s\S]{{0,80}}?exactly\s+one\s+sentence"
        for m in re.finditer(pat, p, flags=re.I):
            k = parse_small_number(m["a"])
            out.append(_region(family, selector, k, k, m, "VISIBLE_LINE_SENTENCE_EQUIVALENCE"))

    # One-sided forms.  Convert surface semantics directly to inclusive bounds,
    # avoiding hidden checker off-by-one parameterization.
    one_sided = [
        (
            rf"(?:at\s+least|minimum\s+of)\s+(?P<a>{n})\s+{noun}",
            lambda m: (parse_small_number(m["a"]), None),
            "VISIBLE_LOWER_BOUND",
        ),
        (
            rf"(?P<a>{n})\s*(?:\+|or\s+more)\s+{noun}",
            lambda m: (parse_small_number(m["a"]), None),
            "VISIBLE_LOWER_BOUND",
        ),
        (
            rf"(?:more\s+than|over)\s+(?P<a>{n})\s+{noun}",
            lambda m: (parse_small_number(m["a"]) + 1, None),
            "VISIBLE_STRICT_LOWER_BOUND",
        ),
        (
            rf"(?:less\s+than|fewer\s+than|under)\s+(?P<a>{n})\s+{noun}",
            lambda m: (None, parse_small_number(m["a"]) - 1),
            "VISIBLE_STRICT_UPPER_BOUND",
        ),
        (
            rf"(?:at\s+most|no\s+more\s+than)\s+(?P<a>{n})\s+{noun}",
            lambda m: (None, parse_small_number(m["a"])),
            "VISIBLE_UPPER_BOUND",
        ),
        (
            rf"(?P<a>{n})\s+{noun}\s+or\s+less",
            lambda m: (None, parse_small_number(m["a"])),
            "VISIBLE_UPPER_BOUND",
        ),
    ]
    for pattern, bounds, route in one_sided:
        for m in re.finditer(pattern, p, flags=re.I):
            lo, hi = bounds(m)
            out.append(_region(family, selector, lo, hi, m, route))
    return out


def _keyword_regions(prompt: str) -> list[CardinalityRegion]:
    p = str(prompt or "")
    out: list[CardinalityRegion] = []
    n = _NUM_TOKEN
    key = r"[A-Za-z][A-Za-z0-9_-]*"

    # The public corpus uses "the word X ...".  Capture the selector, then
    # compile the visible occurrence phrase to an inclusive integer interval.
    specs = [
        (
            rf"(?:the\s+word|word|keyword)\s+[\"']?(?P<key>{key})[\"']?\s+"
            rf"(?:should\s+)?(?:appear|appears|be\s+used)?\s*(?:at\s+least)\s+"
            rf"(?P<a>{n})\s+times",
            lambda m: (parse_small_number(m["a"]), None),
            "KEYWORD_VISIBLE_LOWER",
        ),
        (
            rf"(?:use|include|mention)\s+(?:the\s+)?(?:word|keyword)\s+[\"']?(?P<key>{key})[\"']?"
            rf"[\s\S]{{0,28}}?at\s+least\s+(?P<a>{n})\s+times",
            lambda m: (parse_small_number(m["a"]), None),
            "KEYWORD_VISIBLE_LOWER",
        ),
        (
            rf"(?:the\s+word|word|keyword)\s+[\"']?(?P<key>{key})[\"']?\s+"
            rf"(?:should\s+)?(?:appear|appears|be\s+used)?\s*(?:more\s+than)\s+"
            rf"(?P<a>{n})\s+times",
            lambda m: (parse_small_number(m["a"]) + 1, None),
            "KEYWORD_VISIBLE_STRICT_LOWER",
        ),
        (
            rf"(?:the\s+word|word|keyword)\s+[\"']?(?P<key>{key})[\"']?\s+"
            rf"(?:should\s+)?(?:appear|appears|be\s+used)?\s*(?:less\s+than)\s+"
            rf"(?P<a>{n})\s+times",
            lambda m: (None, parse_small_number(m["a"]) - 1),
            "KEYWORD_VISIBLE_STRICT_UPPER",
        ),
        (
            rf"(?:the\s+word|word|keyword)\s+[\"']?(?P<key>{key})[\"']?"
            rf"[\s\S]{{0,30}}?(?:at\s+most|no\s+more\s+than)\s+(?P<a>{n})"
            rf"(?:\s+times|\b)",
            lambda m: (None, parse_small_number(m["a"])),
            "KEYWORD_VISIBLE_UPPER",
        ),
        (
            rf"(?:the\s+word|word|keyword)\s+[\"']?(?P<key>{key})[\"']?"
            rf"[\s\S]{{0,24}}?(?:appear|appears|be\s+used)?\s*(?P<a>{n})\s+"
            rf"(?:to|through)\s+(?P<b>{n})\s+times",
            lambda m: (parse_small_number(m["a"]), parse_small_number(m["b"])),
            "KEYWORD_VISIBLE_RANGE",
        ),
        (
            rf"(?:the\s+word|word|keyword)\s+[\"']?(?P<key>{key})[\"']?"
            rf"[\s\S]{{0,24}}?(?:appear|appears|be\s+used)?\s*(?P<a>{n})\s+"
            rf"or\s+(?P<b>{n})\s+times",
            lambda m: (parse_small_number(m["a"]), parse_small_number(m["b"])),
            "KEYWORD_VISIBLE_RANGE",
        ),
    ]
    for pattern, bounds, route in specs:
        for m in re.finditer(pattern, p, flags=re.I):
            lo, hi = bounds(m)
            out.append(_region("keywords:frequency", m["key"].lower(), lo, hi, m, route))

    # "... word X once or less" / "only once".
    pat = rf"(?:the\s+word|word)\s+[\"']?(?P<key>{key})[\"']?[\s\S]{{0,35}}?(?:once\s+or\s+less|only\s+once)"
    for m in re.finditer(pat, p, flags=re.I):
        out.append(_region("keywords:frequency", m["key"].lower(), None, 1, m, "KEYWORD_VISIBLE_UPPER"))
    return out


def _capital_regions(prompt: str) -> list[CardinalityRegion]:
    p = str(prompt or "")
    out: list[CardinalityRegion] = []
    n = _NUM_TOKEN

    context = r"(?:words?\s+(?:with\s+)?(?:all\s+)?capital\s+letters|all[- ]caps\s+words?|capitalized\s+words?)"
    for m in re.finditer(rf"(?P<a>{n})\s+(?:to|through)\s+(?P<b>{n})\s+{context}", p, flags=re.I):
        out.append(_region(
            "change_case:capital_word_frequency", "all_capital_words",
            parse_small_number(m["a"]), parse_small_number(m["b"]), m,
            "CAPITAL_VISIBLE_RANGE",
        ))
    for m in re.finditer(rf"{context}[\s\S]{{0,45}}?less\s+than\s+(?P<a>{n})\s+times", p, flags=re.I):
        out.append(_region(
            "change_case:capital_word_frequency", "all_capital_words",
            None, parse_small_number(m["a"]) - 1, m,
            "CAPITAL_VISIBLE_STRICT_UPPER",
        ))
    for m in re.finditer(rf"{context}[\s\S]{{0,45}}?at\s+most\s+(?P<a>{n})\s+times", p, flags=re.I):
        out.append(_region(
            "change_case:capital_word_frequency", "all_capital_words",
            None, parse_small_number(m["a"]), m,
            "CAPITAL_VISIBLE_UPPER",
        ))

    # Public legacy prompts commonly encode the generated >=1 companion checker
    # as "use/include some/a few words in all caps".
    positive = re.compile(
        r"(?:use|include|have)\s+(?:some|a\s+few)\s+words?\s+"
        r"(?:in\s+all\s+caps|with\s+all\s+capital\s+letters|in\s+all\s+capital\s+letters)",
        flags=re.I,
    )
    for m in positive.finditer(p):
        out.append(_region(
            "change_case:capital_word_frequency", "all_capital_words",
            1, None, m, "CAPITAL_VISIBLE_POSITIVE_EXISTENCE",
        ))
    return out


def _intersect(items: list[CardinalityRegion]) -> list[CardinalityRegion]:
    grouped: dict[tuple[str, str], list[CardinalityRegion]] = {}
    for item in items:
        grouped.setdefault((item.family, item.selector), []).append(item)

    out: list[CardinalityRegion] = []
    for (family, selector), group in sorted(grouped.items()):
        lowers = [x.lower for x in group if x.lower is not None]
        uppers = [x.upper for x in group if x.upper is not None]
        lo = max(lowers) if lowers else None
        hi = min(uppers) if uppers else None
        if lo is not None and hi is not None and lo > hi:
            raise ValueError(f"EMPTY_VISIBLE_REGION:{family}:{selector}")
        evidence = " || ".join(x.evidence for x in group)
        routes = "+".join(sorted({x.route for x in group}))
        out.append(CardinalityRegion(family, selector, lo, hi, evidence, routes))
    return out


def compile_cardinality_regions(prompt: str) -> dict[str, Any]:
    p = str(prompt or "")
    atoms: list[CardinalityRegion] = []
    atoms += _count_ranges(p, r"words?\b", "length_constraints:number_words", "response_words")
    atoms += _count_ranges(p, r"sentences?\b", "length_constraints:number_sentences", "response_sentences")
    atoms += _keyword_regions(p)
    atoms += _capital_regions(p)

    # Remove exact duplicate atoms created by overlapping equivalent phrasings.
    unique: list[CardinalityRegion] = []
    seen: set[tuple[Any, ...]] = set()
    for x in atoms:
        key = (x.family, x.selector, x.lower, x.upper, x.evidence)
        if key not in seen:
            seen.add(key)
            unique.append(x)

    regions = _intersect(unique)
    return {
        "schema": SCHEMA,
        "status": "PASS",
        "regions": [x.to_dict() for x in regions],
        "atom_count": len(unique),
        "region_count": len(regions),
        "representation": "SEMANTIC_FEASIBLE_REGION__NOT_CHECKER_ID_DEDUP",
        "hidden_kwargs_used": False,
        "terminal_case_content_used": False,
        "model_dependency_count": 0,
        "network_used": False,
    }


def run(args: dict[str, Any], root=None) -> dict[str, Any]:
    args = args or {}
    return compile_cardinality_regions(str(args.get("prompt") or args.get("text") or ""))


if __name__ == "__main__":
    import argparse, json
    ap = argparse.ArgumentParser()
    ap.add_argument("prompt")
    ns = ap.parse_args()
    print(json.dumps(compile_cardinality_regions(ns.prompt), indent=2, sort_keys=True))
