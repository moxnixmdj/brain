from __future__ import annotations

from collections.abc import Mapping
from math import isclose
from typing import Hashable


def _normalized_law(law: Mapping[Hashable, float]) -> dict[Hashable, float]:
    if not isinstance(law, Mapping) or not law:
        raise ValueError("law must be a non-empty mapping")
    out: dict[Hashable, float] = {}
    for key, value in law.items():
        p = float(value)
        if p < 0.0:
            raise ValueError("probabilities must be nonnegative")
        out[key] = p
    total = sum(out.values())
    if not isclose(total, 1.0, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError("probabilities must sum to 1")
    return out


def laws_equal(brain: Mapping[Hashable, float], opus: Mapping[Hashable, float]) -> bool:
    b = _normalized_law(brain)
    o = _normalized_law(opus)
    support = set(b) | set(o)
    return all(isclose(b.get(x, 0.0), o.get(x, 0.0), rel_tol=0.0, abs_tol=1e-12) for x in support)


def opus_favoring_event(
    brain: Mapping[Hashable, float],
    opus: Mapping[Hashable, float],
) -> tuple[set[Hashable], float]:
    """Construct an owner-visible event whose blind pairwise use favors Opus.

    If the laws differ, A={x: P_Opus(x)>P_Brain(x)} has positive probability
    gap. A blind judge can prefer the submission in A when exactly one side is in
    A and tie otherwise. Its expected Opus-minus-Brain win-score advantage is
    exactly P_Opus(A)-P_Brain(A).
    """
    b = _normalized_law(brain)
    o = _normalized_law(opus)
    support = set(b) | set(o)
    event = {x for x in support if o.get(x, 0.0) > b.get(x, 0.0) + 1e-12}
    p_b = sum(b.get(x, 0.0) for x in event)
    p_o = sum(o.get(x, 0.0) for x in event)
    return event, p_o - p_b


def blind_event_judge_expected_net_opus_advantage(p_brain_event: float, p_opus_event: float) -> float:
    p_b = float(p_brain_event)
    p_o = float(p_opus_event)
    if not (0.0 <= p_b <= 1.0 and 0.0 <= p_o <= 1.0):
        raise ValueError("event probabilities must be in [0,1]")
    # Opus wins when O is in A and B is not; Brain wins in the reverse case.
    return p_o * (1.0 - p_b) - p_b * (1.0 - p_o)


def arbitrary_hidden_evaluator_universal_noninferiority_possible(
    brain: Mapping[Hashable, float],
    opus: Mapping[Hashable, float],
) -> dict[str, object]:
    """Finite-law necessity/sufficiency boundary for route U.

    This addresses the evaluator-unrestricted lane only. If the owner-visible
    laws differ, a blind content-based separating judge exists that favors Opus.
    If the laws are equal and all exogenous owner randomness (A/B assignment,
    parser transform, judge sampling) is also shared, the labeled comparison law
    is exchangeable, so no blind evaluator can have model-specific expected
    preference from owner-visible information alone.
    """
    equal = laws_equal(brain, opus)
    if equal:
        return {
            "laws_equal": True,
            "separating_blind_judge_exists": False,
            "arbitrary_hidden_evaluator_requires_no_semantic_model": True,
            "route": "U_EXACT_OWNER_VISIBLE_LAW_EQUALITY",
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }

    event, gap = opus_favoring_event(brain, opus)
    assert event
    assert gap > 0.0
    return {
        "laws_equal": False,
        "separating_blind_judge_exists": True,
        "opus_favoring_event": sorted(map(str, event)),
        "expected_net_opus_advantage": gap,
        "arbitrary_hidden_evaluator_requires_no_semantic_model": False,
        "route": "E_OR_M_OR_U_EQUALITY_REQUIRED_FOR_CURRENT_THEOREM",
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }


def verify_arbitrary_evaluator_boundary() -> dict[str, object]:
    b = {"x": 0.7, "y": 0.3}
    o = {"x": 0.2, "y": 0.8}
    unequal = arbitrary_hidden_evaluator_universal_noninferiority_possible(b, o)
    equal = arbitrary_hidden_evaluator_universal_noninferiority_possible(b, dict(b))

    assert unequal["separating_blind_judge_exists"] is True
    assert unequal["expected_net_opus_advantage"] > 0.0
    assert equal["separating_blind_judge_exists"] is False

    return {
        "finite_owner_visible_law_inequality_implies_an_opus_favoring_blind_pairwise_judge": True,
        "exact_law_equality_is_sufficient_for_exchangeability_under_shared_owner_randomness": True,
        "arbitrary_evaluator_lane_collapses_to_U_equality": True,
        "semantic_restriction_lanes_remain_E_or_M": True,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
