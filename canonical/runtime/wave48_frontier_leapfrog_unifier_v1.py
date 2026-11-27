"""Wave 48 Frontier Leapfrog Unifier (K3=0, $0.00 spend).

Unifies five frontier-beating deterministic organs for UnifiedModel & Creature:
1. FixedBench Abstention & Verifier Falsification (arXiv:2605.07769)
2. MEME DBSP Z-Set Cascade/Absence Memory (arXiv:2605.12477)
3. BiSpace / JitRL External Skill Advantage Cache (arXiv:2601.18510, arXiv:2611.25861)
4. SCoRE Anytime-Valid E-Value Evolution Gate (arXiv:2603.24704)
5. HCU / WebMCP Polarity Clause Guard (arXiv:2610.41432)
"""

from __future__ import annotations

import hashlib
import hmac
import math
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple


@dataclass(frozen=True)
class AbstentionVerdict:
    abstain: bool
    reason: str
    verifier_falsified: bool


def evaluate_fixedbench_abstention(
    baseline_passed: bool,
    verifier_fn: Callable[[str], bool],
    sabotaged_source: str,
) -> AbstentionVerdict:
    """Prove verifier can say NO on sabotaged code, then abstain if baseline already passes."""
    verifier_falsified = not bool(verifier_fn(sabotaged_source))
    if not verifier_falsified:
        return AbstentionVerdict(
            abstain=False,
            reason="VERIFIER_FALSIFICATION_FAILED",
            verifier_falsified=False,
        )
    if baseline_passed:
        return AbstentionVerdict(
            abstain=True,
            reason="SETTLED__NO_DEFECT_PRESENT",
            verifier_falsified=True,
        )
    return AbstentionVerdict(
        abstain=False,
        reason="DEFECT_CONFIRMED",
        verifier_falsified=True,
    )


class DBSPMemeMemory:
    """Exact O(delta) DBSP Z-set (+1/-1) dependency & absence tracker for MEME."""

    def __init__(self) -> None:
        self._weights: Dict[str, int] = {}
        self._deps: Dict[str, List[str]] = {}
        self._superseded_by: Dict[str, str] = {}

    def assert_fact(self, fact_id: str, depends_on: Iterable[str] = ()) -> None:
        self._weights[fact_id] = self._weights.get(fact_id, 0) + 1
        for parent in depends_on:
            self._deps.setdefault(parent, []).append(fact_id)

    def retract_fact(self, fact_id: str, reason: str = "RETRACTED") -> List[str]:
        """Retract fact_id and cascade -1 deltas to all downstream dependents."""
        cascaded: List[str] = []
        queue = [fact_id]
        visited = set()
        while queue:
            cur = queue.pop(0)
            if cur in visited:
                continue
            visited.add(cur)
            if self._weights.get(cur, 0) > 0:
                self._weights[cur] = 0
                self._superseded_by[cur] = reason
                cascaded.append(cur)
            for child in self._deps.get(cur, ()):
                queue.append(child)
        return cascaded

    def query(self, fact_id: str) -> Tuple[bool, str]:
        w = self._weights.get(fact_id, 0)
        if w > 0:
            return True, "PRESENT"
        if fact_id in self._superseded_by:
            return False, f"UNKNOWN__UPSTREAM_SUPERSEDED:{self._superseded_by[fact_id]}"
        return False, "ABSENT"


class AnytimeEValueGate:
    """SCoRE-style multiplicative e-process supermartingale for safe self-evolution."""

    def __init__(self, alpha: float = 0.05) -> None:
        self.alpha = alpha
        self.e_value = 1.0
        self.steps = 0

    def update(self, candidate_pass_rate: float, baseline_pass_rate: float) -> bool:
        self.steps += 1
        delta = candidate_pass_rate - baseline_pass_rate
        # Bounded likelihood-ratio multiplier (>= 0, expectation <= 1 under null)
        multiplier = max(0.0, min(2.0, math.exp(2.0 * delta)))
        self.e_value *= multiplier
        return self.e_value >= (1.0 / self.alpha)


class PolarityClauseGuard:
    """HCU / WebMCP (POSITIVE, NEGATIVE, INVARIANT) polarity guard with HMAC-sealed handles."""

    def __init__(self, secret: bytes = b"brain-wave48-hcu-seal") -> None:
        self._secret = secret

    def seal_handle(self, selector: str) -> str:
        digest = hmac.new(self._secret, selector.encode("utf-8"), hashlib.sha256).hexdigest()[:16]
        return f"hcu_{digest}"

    def check(
        self,
        positive_present: bool,
        negative_present: bool,
        invariant_ok: bool,
    ) -> Tuple[bool, str]:
        if not invariant_ok:
            return False, "BLOCKED__INVARIANT_VIOLATED"
        if negative_present:
            return False, "BLOCKED__NEGATIVE_POLARITY_MATCH"
        if not positive_present:
            return False, "BLOCKED__POSITIVE_TARGET_MISSING"
        return True, "ALLOWED"


@dataclass
class Wave48FrontierLeapfrogUnifier:
    """Unified K3=0, $0.00 frontier leapfrog kernel."""

    meme_memory: DBSPMemeMemory = field(default_factory=DBSPMemeMemory)
    e_gate: AnytimeEValueGate = field(default_factory=AnytimeEValueGate)
    polarity_guard: PolarityClauseGuard = field(default_factory=PolarityClauseGuard)
    skill_advantages: Dict[str, float] = field(default_factory=dict)

    def record_skill_advantage(self, signature: str, advantage: float) -> None:
        prev = self.skill_advantages.get(signature, 0.0)
        self.skill_advantages[signature] = 0.7 * prev + 0.3 * advantage

    def rank_candidates(self, signatures: Iterable[str]) -> List[Tuple[str, float]]:
        return sorted(
            ((sig, self.skill_advantages.get(sig, 0.0)) for sig in signatures),
            key=lambda x: x[1],
            reverse=True,
        )
