#!/usr/bin/env python3
"""Exact interval quotient for frozen LiveBench legacy count-threshold checkers.

The pinned legacy checkers compare a measured integer count c against an integer
threshold n using only:
  - "at least": c >= n
  - "less than": c < n

Therefore, for a fixed candidate response, all raw threshold values factor
through c. No terminal rows or hidden kwargs are needed to compute the entire
threshold truth table.
"""
from __future__ import annotations
from dataclasses import dataclass

SCHEMA = "PROJECT_BRAIN_LIVEBENCH_THRESHOLD_INTERVAL_QUOTIENT_V1"

@dataclass(frozen=True)
class ThresholdDomain:
    minimum: int
    maximum: int
    name: str

WORD_DOMAIN = ThresholdDomain(100, 500, "number_words")
SENTENCE_DOMAIN = ThresholdDomain(1, 20, "number_sentences")

class ThresholdQuotientError(ValueError):
    pass

def _validate(domain: ThresholdDomain, measured_count: int) -> int:
    c = int(measured_count)
    if c < 0:
        raise ThresholdQuotientError("MEASURED_COUNT_MUST_BE_NONNEGATIVE")
    if domain.minimum > domain.maximum:
        raise ThresholdQuotientError("INVALID_DOMAIN")
    return c

def pass_intervals(domain: ThresholdDomain, measured_count: int) -> dict:
    """Return the exact passing threshold intervals for both frozen relations."""
    c = _validate(domain, measured_count)
    # c >= n  <=>  n <= c
    atleast_hi = min(domain.maximum, c)
    atleast = None if atleast_hi < domain.minimum else [domain.minimum, atleast_hi]
    # c < n  <=>  n >= c+1
    less_lo = max(domain.minimum, c + 1)
    less = None if less_lo > domain.maximum else [less_lo, domain.maximum]
    return {
        "schema": SCHEMA,
        "domain": domain.name,
        "measured_count": c,
        "at_least_pass_threshold_interval": atleast,
        "less_than_pass_threshold_interval": less,
        "raw_threshold_count": domain.maximum - domain.minimum + 1,
        "terminal_data_used": False,
        "acceptance_credit": False,
    }

def checker_result(domain: ThresholdDomain, measured_count: int, relation: str, threshold: int) -> bool:
    c = _validate(domain, measured_count)
    n = int(threshold)
    if not domain.minimum <= n <= domain.maximum:
        raise ThresholdQuotientError("THRESHOLD_OUTSIDE_FROZEN_DOMAIN")
    if relation == "at least":
        return c >= n
    if relation == "less than":
        return c < n
    raise ThresholdQuotientError("UNKNOWN_RELATION")

def reconstruct_truth_table(domain: ThresholdDomain, measured_count: int) -> dict:
    """Exact O(1)-certificate data plus explicit table for verification/debug only."""
    cert = pass_intervals(domain, measured_count)
    cert["truth_table"] = {
        relation: {
            n: checker_result(domain, measured_count, relation, n)
            for n in range(domain.minimum, domain.maximum + 1)
        }
        for relation in ("at least", "less than")
    }
    return cert

def compression_summary() -> dict:
    return {
        "schema": SCHEMA,
        "word_raw_relation_threshold_states": 2 * (WORD_DOMAIN.maximum - WORD_DOMAIN.minimum + 1),
        "sentence_raw_relation_threshold_states": 2 * (SENTENCE_DOMAIN.maximum - SENTENCE_DOMAIN.minimum + 1),
        "certificate_scalars_per_domain": 1,
        "word_raw_states": 802,
        "sentence_raw_states": 40,
        "combined_raw_states": 842,
        "theorem": "FOR_FIXED_RESPONSE__ONE_MEASURED_COUNT_EXACTLY_DETERMINES_ALL_THRESHOLD_CHECKER_RESULTS",
        "terminal_data_used": False,
        "acceptance_credit": False,
    }

def run(args=None, root=None):
    return compression_summary()

if __name__ == "__main__":
    import json
    print(json.dumps(compression_summary(), indent=2, sort_keys=True))
