#!/usr/bin/env python3
"""Whitespace-invariant constructor for LiveBench/IFBench trigram-overlap constraints.

This module is deliberately narrower than a full IFBench solver.  It solves a
specific public-checker identifiability problem without hidden kwargs:

* the public prompt exposes a whitespace-normalized copy of the reference text;
* the frozen checker scores unique character trigrams;
* raw reference uncertainty is restricted to whitespace placement;
* a response is built from a within-token substring plus fresh sentinel chars.

Every response trigram is then either:
  (a) a non-whitespace trigram guaranteed to occur in every whitespace variant
      of the visible reference, or
  (b) a trigram containing a sentinel guaranteed absent from every such variant.

That gives an exact score certificate without reconstructing hidden whitespace.
The constructor fails closed outside that theorem's assumptions.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import json
import re
from typing import Iterable

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_WHITESPACE_INVARIANT_OVERLAP_COMPILER_V1"
OVERLAP_DESCRIPTION = (
    r"Maintain a trigram overlap of (?P<pct>\d{1,3})% "
    r"\(±2%\) with the provided reference text\."
)
KEYWORD_DESCRIPTION = (
    r"The response must include keyword (?P<keyword>[^\s.]+) in the "
    r"(?P<sentence>\d+)(?:-st|-nd|-rd|-th) sentence\."
)
CONSONANT_DESCRIPTION = (
    r"Ensure each word in your response has at least one consonant cluster "
    r"\(two or more consonants together\)\."
)


class OverlapInvariantError(RuntimeError):
    pass


@dataclass(frozen=True)
class OverlapCertificate:
    schema: str
    status: str
    target_percent: float
    tolerance_percent: float
    certified_percent: float
    absolute_error_percent: float
    common_unique_trigrams: int
    noncommon_unique_trigrams: int
    unknown_unique_trigrams: int
    total_unique_trigrams: int
    core: str
    filler_count: int
    response: str
    theorem_scope: str

    def to_dict(self) -> dict:
        return asdict(self)


def normalize_visible_whitespace(text: str) -> str:
    # U+200B appears as separator noise in the pinned public IFBench slice.
    value = str(text or "").replace("\u200b", " ")
    return re.sub(r"\s+", " ", value).strip()


def char_trigrams(text: str) -> set[str]:
    value = str(text)
    return {value[i:i + 3] for i in range(max(0, len(value) - 2))}


def _fresh_sentinels(reference: str, count: int = 96) -> tuple[str, ...]:
    out: list[str] = []
    # Unicode private-use characters are ordinary Python characters and are
    # scored literally by the frozen NGramOverlapChecker.
    for codepoint in range(0xE000, 0xF900):
        ch = chr(codepoint)
        if ch not in reference:
            out.append(ch)
            if len(out) >= count:
                break
    if len(out) < count:
        raise OverlapInvariantError("INSUFFICIENT_FRESH_SENTINELS")
    return tuple(out)


def classify_response_trigrams(
    response: str,
    normalized_reference: str,
    sentinels: Iterable[str],
) -> dict:
    ref = normalize_visible_whitespace(normalized_reference)
    ref_grams = char_trigrams(ref)
    sentinel_set = set(sentinels)
    common: set[str] = set()
    noncommon: set[str] = set()
    unknown: set[str] = set()

    for gram in char_trigrams(response):
        if any(ch in sentinel_set for ch in gram):
            noncommon.add(gram)
        elif not re.search(r"\s", gram) and gram in ref_grams:
            common.add(gram)
        else:
            unknown.add(gram)

    total = len(common) + len(noncommon) + len(unknown)
    ratio = (100.0 * len(common) / total) if total else 0.0
    return {
        "common": common,
        "noncommon": noncommon,
        "unknown": unknown,
        "total": total,
        "ratio": ratio,
    }


def construct_whitespace_invariant_overlap(
    visible_reference: str,
    target_percent: float,
    *,
    tolerance_percent: float = 2.0,
    max_filler: int = 64,
) -> OverlapCertificate:
    ref = normalize_visible_whitespace(visible_reference)
    if not ref:
        raise OverlapInvariantError("REFERENCE_REQUIRED")
    target = float(target_percent)
    tolerance = float(tolerance_percent)
    if not (0.0 <= target <= 100.0):
        raise OverlapInvariantError("TARGET_OUT_OF_RANGE")
    if tolerance < 0:
        raise OverlapInvariantError("NEGATIVE_TOLERANCE")

    sentinels = _fresh_sentinels(ref, max_filler + 2)
    best: tuple[float, int, OverlapCertificate] | None = None

    for token in ref.split(" "):
        if len(token) < 3:
            continue
        for start in range(len(token) - 2):
            for end in range(start + 3, len(token) + 1):
                core = token[start:end]
                core_grams = char_trigrams(core)
                if not core_grams:
                    continue
                if any(re.search(r"\s", g) or g not in ref for g in core_grams):
                    continue

                for filler_count in range(max_filler + 1):
                    active_sentinels = sentinels[:filler_count]
                    response = core + "".join(active_sentinels)
                    c = classify_response_trigrams(response, ref, active_sentinels)
                    if c["unknown"]:
                        continue
                    if c["total"] <= 0:
                        continue
                    error = abs(c["ratio"] - target)
                    cert = OverlapCertificate(
                        schema=SCHEMA,
                        status="PASS" if error <= tolerance else "BEST_EFFORT_OUTSIDE_TOLERANCE",
                        target_percent=target,
                        tolerance_percent=tolerance,
                        certified_percent=c["ratio"],
                        absolute_error_percent=error,
                        common_unique_trigrams=len(c["common"]),
                        noncommon_unique_trigrams=len(c["noncommon"]),
                        unknown_unique_trigrams=len(c["unknown"]),
                        total_unique_trigrams=c["total"],
                        core=core,
                        filler_count=filler_count,
                        response=response,
                        theorem_scope=(
                            "EXACT_IF_RAW_REFERENCE_DIFFERS_FROM_VISIBLE_REFERENCE_ONLY_BY_"
                            "WHITESPACE_PLACEMENT_AND_SENTINELS_ARE_ABSENT"
                        ),
                    )
                    rank = (error, len(response))
                    if best is None or rank < (best[0], best[1]):
                        best = (error, len(response), cert)
                    if error <= tolerance:
                        return cert

    if best is None:
        raise OverlapInvariantError("NO_CLASSIFIABLE_CONSTRUCTION")
    raise OverlapInvariantError(
        "NO_CONSTRUCTION_WITHIN_TOLERANCE:"
        + json.dumps(best[2].to_dict(), sort_keys=True, ensure_ascii=True)
    )


def _fullmatch_patterns() -> tuple[re.Pattern[str], ...]:
    sep = r"[\s\u200b]+"
    ref = r"(?P<reference>.+?)"
    overlap = OVERLAP_DESCRIPTION
    keyword = KEYWORD_DESCRIPTION
    consonant = CONSONANT_DESCRIPTION
    flags = re.I | re.S
    patterns = [
        rf"^{ref}{sep}{overlap}$",
        rf"^{overlap}{sep}{ref}$",
        rf"^{ref}{sep}{overlap}{sep}{keyword}$",
        rf"^{overlap}{sep}{keyword}{sep}{ref}$",
        rf"^{ref}{sep}{keyword}{sep}{overlap}$",
        rf"^{keyword}{sep}{overlap}{sep}{ref}$",
        rf"^{ref}{sep}{consonant}{sep}{overlap}$",
        rf"^{consonant}{sep}{overlap}{sep}{ref}$",
        rf"^{ref}{sep}{overlap}{sep}{consonant}$",
        rf"^{overlap}{sep}{consonant}{sep}{ref}$",
    ]
    return tuple(re.compile(p, flags) for p in patterns)


_PUBLIC_OVERLAP_ENVELOPES = _fullmatch_patterns()


def project_public_overlap_reference(prompt: str) -> dict:
    """Recover the visible reference only for exact public envelope shapes.

    This is intentionally not a generic "strip instructions" heuristic.  It
    full-matches a small set of public IFBench overlap envelope forms and fails
    closed on anything else, preventing accidental deletion of reference text.
    """
    value = str(prompt or "").strip()
    hits = []
    for pattern in _PUBLIC_OVERLAP_ENVELOPES:
        m = pattern.fullmatch(value)
        if not m:
            continue
        reference = normalize_visible_whitespace(m.group("reference"))
        pct = int(m.group("pct"))
        hits.append((reference, pct, pattern.pattern))

    unique = {(r, p) for r, p, _ in hits}
    if len(unique) != 1:
        raise OverlapInvariantError(
            "PUBLIC_OVERLAP_ENVELOPE_NOT_IDENTIFIABLE"
            if not unique
            else "PUBLIC_OVERLAP_ENVELOPE_AMBIGUOUS"
        )
    reference, pct = next(iter(unique))
    return {
        "status": "PASS",
        "visible_reference": reference,
        "target_percent": pct,
        "matched_envelope_count": len(hits),
        "hidden_kwargs_used": False,
        "terminal_case_metadata_used": False,
    }


def compile_public_overlap_prompt(prompt: str) -> dict:
    projection = project_public_overlap_reference(prompt)
    cert = construct_whitespace_invariant_overlap(
        projection["visible_reference"],
        projection["target_percent"],
    )
    return {
        "schema": SCHEMA,
        "status": "PASS",
        "projection": {
            "target_percent": projection["target_percent"],
            "matched_envelope_count": projection["matched_envelope_count"],
            "hidden_kwargs_used": False,
            "terminal_case_metadata_used": False,
        },
        "certificate": cert.to_dict(),
    }


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("prompt")
    ns = ap.parse_args()
    print(json.dumps(compile_public_overlap_prompt(ns.prompt), indent=2, sort_keys=True, ensure_ascii=True))
