#!/usr/bin/env python3
"""Fail-closed capability-credit firewall for benchmark observability.

A benchmark may only mint credit for capability dimensions that its evaluator
actually observes. This prevents a high score on a structural/checker-only
benchmark from being promoted into semantic capability ownership.

The module is deliberately tiny and deterministic so it can sit in front of
all promotion logic without model or network dependencies.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

SCHEMA = "PROJECT_BRAIN_CAPABILITY_EVIDENCE_OBSERVABILITY_V1"

LIVEBENCH_IF_2026 = "LIVEBENCH_IF_2026_06_25"

FORMAL_INSTRUCTION_ADHERENCE = "FORMAL_INSTRUCTION_ADHERENCE"
SEMANTIC_PARAPHRASE = "SEMANTIC_PARAPHRASE"
SEMANTIC_SIMPLIFICATION = "SEMANTIC_SIMPLIFICATION"
SEMANTIC_SUMMARIZATION = "SEMANTIC_SUMMARIZATION"
SEMANTIC_STORY_GENERATION = "SEMANTIC_STORY_GENERATION"

SEMANTIC_CLAIMS = frozenset({
    SEMANTIC_PARAPHRASE,
    SEMANTIC_SIMPLIFICATION,
    SEMANTIC_SUMMARIZATION,
    SEMANTIC_STORY_GENERATION,
})

# LiveBench's IF evaluator scores adherence to its verifiable instructions.
# The named content transformations are prompt contexts, not separately scored
# semantic-fidelity dimensions. Therefore the score directly observes formal
# instruction adherence only.
BENCHMARK_OBSERVABLES = {
    LIVEBENCH_IF_2026: frozenset({FORMAL_INSTRUCTION_ADHERENCE}),
}


class UnsupportedCapabilityCredit(ValueError):
    pass


@dataclass(frozen=True)
class EvidenceClaim:
    benchmark: str
    capability: str

    @property
    def supported(self) -> bool:
        return self.capability in BENCHMARK_OBSERVABLES.get(self.benchmark, frozenset())


def observable_capabilities(benchmarks: Iterable[str]) -> frozenset[str]:
    out: set[str] = set()
    for benchmark in benchmarks:
        out.update(BENCHMARK_OBSERVABLES.get(str(benchmark), frozenset()))
    return frozenset(out)


def supports(benchmark: str, capability: str) -> bool:
    return EvidenceClaim(str(benchmark), str(capability)).supported


def require_support(benchmark: str, capability: str) -> None:
    if not supports(benchmark, capability):
        raise UnsupportedCapabilityCredit(
            f"EVIDENCE_DOES_NOT_OBSERVE_CAPABILITY:{benchmark}:{capability}"
        )


def semantic_credit_from_livebench_if_only(capability: str) -> bool:
    """Return False for every semantic transformation claim.

    Kept as an explicit guard because Root1 scheduling previously risked using
    the aggregate LiveBench IF score as semantic-core evidence.
    """
    if capability not in SEMANTIC_CLAIMS:
        raise ValueError(f"NOT_A_SEMANTIC_CLAIM:{capability}")
    return False
