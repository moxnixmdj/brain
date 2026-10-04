"""Fail-closed reference-blind constructor for IFBench NGramOverlapChecker.

The checker computes unique character trigrams in the response and divides the
number also present in the hidden reference by the response unique-trigram
count.  If `preserved_run` is an exact contiguous substring of the hidden
reference and the appended sentinel code points are absent from the hidden
reference, then the score is exactly m/(m+k), where m is the number of unique
trigrams in `preserved_run` and k is the number of distinct sentinels.

This module grants no authority by itself.  Callers must separately prove the
preserved-run and sentinel-absence preconditions for the frozen target family,
and must prove the output transport preserves Unicode code points.
"""

from __future__ import annotations

from dataclasses import dataclass


class ConstructionError(ValueError):
    pass


@dataclass(frozen=True)
class OverlapConstruction:
    output: str
    preserved_run: str
    target_percent: float
    tolerance_percent: float
    matching_trigrams: int
    novel_trigrams: int
    expected_percent: float
    sentinel_codepoints: tuple[int, ...]


def unique_trigrams(text: str) -> set[str]:
    if len(text) < 3:
        return set()
    return {text[i : i + 3] for i in range(len(text) - 2)}


def _best_padding_count(
    matching_trigrams: int,
    target_percent: float,
    tolerance_percent: float,
    max_padding: int,
) -> tuple[int, float]:
    if matching_trigrams <= 0:
        raise ConstructionError("preserved_run must contain at least one unique trigram")
    if not (0.0 < target_percent <= 100.0):
        raise ConstructionError("target_percent must be in (0, 100]")
    if tolerance_percent < 0:
        raise ConstructionError("tolerance_percent must be non-negative")

    best: tuple[float, int, float] | None = None
    for k in range(max_padding + 1):
        pct = 100.0 * matching_trigrams / (matching_trigrams + k)
        err = abs(pct - target_percent)
        candidate = (err, k, pct)
        if best is None or candidate < best:
            best = candidate
        if err <= tolerance_percent:
            return k, pct
    assert best is not None
    raise ConstructionError(
        f"no integer padding count reaches target within tolerance; "
        f"best_error={best[0]:.6f} best_k={best[1]} best_pct={best[2]:.6f}"
    )


def _private_use_candidates():
    # BMP PUA followed by the two supplementary private-use planes.
    for cp in range(0xE000, 0xF900):
        yield cp
    for cp in range(0xF0000, 0xFFFFE):
        yield cp
    for cp in range(0x100000, 0x10FFFE):
        yield cp


def choose_absent_sentinels(count: int, forbidden_text: str) -> tuple[int, ...]:
    if count < 0:
        raise ConstructionError("count must be non-negative")
    forbidden = set(forbidden_text)
    out: list[int] = []
    for cp in _private_use_candidates():
        ch = chr(cp)
        if ch not in forbidden:
            out.append(cp)
            if len(out) == count:
                return tuple(out)
    raise ConstructionError("insufficient absent private-use sentinels")


def construct_reference_blind_overlap(
    *,
    preserved_run: str,
    target_percent: float,
    forbidden_visible_text: str,
    tolerance_percent: float = 2.0,
    max_padding: int = 100000,
) -> OverlapConstruction:
    """Construct a response whose score is exact under the theorem preconditions.

    Required external preconditions:
      1. every trigram of preserved_run occurs in the hidden reference;
      2. hidden reference contains none of the selected sentinel code points;
      3. response transport preserves Python Unicode code points exactly.

    `forbidden_visible_text` should cover every visible character source known to
    be preserved into the hidden reference.  Absence from visible text alone is
    not a proof of hidden-reference absence; that implication belongs to the
    frozen-family binding certificate.
    """
    m = len(unique_trigrams(preserved_run))
    k, expected = _best_padding_count(
        m, target_percent, tolerance_percent, max_padding
    )
    sentinels = choose_absent_sentinels(k, forbidden_visible_text)
    suffix = "".join(chr(cp) for cp in sentinels)
    output = preserved_run + suffix

    # Distinct absent sentinels create exactly k unique novel trigram positions.
    total = len(unique_trigrams(output))
    if total != m + k:
        raise ConstructionError(
            f"novel-trigram cardinality invariant failed: total={total}, m={m}, k={k}"
        )

    return OverlapConstruction(
        output=output,
        preserved_run=preserved_run,
        target_percent=target_percent,
        tolerance_percent=tolerance_percent,
        matching_trigrams=m,
        novel_trigrams=k,
        expected_percent=expected,
        sentinel_codepoints=sentinels,
    )
