from __future__ import annotations

import math
from typing import Iterable, Mapping


def bt_pairwise_probability(beta_a: float, beta_b: float) -> float:
    """Bradley-Terry P(A beats B) from latent log-strengths."""
    d = float(beta_a) - float(beta_b)
    if d >= 0:
        z = math.exp(-d)
        return 1.0 / (1.0 + z)
    z = math.exp(d)
    return z / (1.0 + z)


def incumbent_log_likelihood(
    strengths: Mapping[str, float],
    comparisons: Iterable[tuple[str, str, float]],
) -> float:
    """Log likelihood for incumbent-only pairwise outcomes.

    comparisons are (left_model, right_model, left_score), where left_score is
    1 for a left win, 0 for a right win, and 0.5 for a tie/half-win convention.
    """
    total = 0.0
    for left, right, score in comparisons:
        if left not in strengths or right not in strengths:
            raise KeyError("comparison model missing from strengths")
        if score not in (0.0, 0.5, 1.0):
            raise ValueError("score must be 0, 0.5, or 1")
        p = bt_pairwise_probability(strengths[left], strengths[right])
        total += score * math.log(p) + (1.0 - score) * math.log1p(-p)
    return total


def unseen_entrant_invariance(
    incumbent_strengths: Mapping[str, float],
    incumbent_comparisons: Iterable[tuple[str, str, float]],
    *,
    unseen_model: str = "BRAIN",
    beta_values: tuple[float, ...] = (-100.0, 0.0, 100.0),
) -> dict[str, object]:
    """Show the incumbent likelihood is invariant to an unseen entrant strength."""
    if unseen_model in incumbent_strengths:
        raise ValueError("unseen_model must not already be an incumbent")
    rows = list(incumbent_comparisons)
    baseline = incumbent_log_likelihood(incumbent_strengths, rows)
    values = []
    for beta in beta_values:
        extended = dict(incumbent_strengths)
        extended[unseen_model] = float(beta)
        # No row contains unseen_model, so the same incumbent likelihood applies.
        value = incumbent_log_likelihood(extended, rows)
        values.append(value)
    return {
        "baseline_log_likelihood": baseline,
        "extended_log_likelihoods": values,
        "invariant": all(abs(value - baseline) <= 1e-12 for value in values),
        "unseen_strength_identified": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }


def unseen_vs_opus_probability_examples(beta_opus: float = 0.0) -> dict[str, float]:
    """Exhibit opposite target conclusions under the same incumbent evidence."""
    return {
        "very_low_brain": bt_pairwise_probability(beta_opus - 20.0, beta_opus),
        "equal_brain": bt_pairwise_probability(beta_opus, beta_opus),
        "very_high_brain": bt_pairwise_probability(beta_opus + 20.0, beta_opus),
    }


def verify_unseen_entrant_cut() -> dict[str, object]:
    strengths = {"OPUS": 2.0, "A": 1.0, "ANCHOR": 0.0}
    rows = [
        ("OPUS", "A", 1.0),
        ("OPUS", "ANCHOR", 1.0),
        ("A", "ANCHOR", 0.5),
    ]
    invariant = unseen_entrant_invariance(strengths, rows)
    examples = unseen_vs_opus_probability_examples(strengths["OPUS"])

    assert invariant["invariant"] is True
    assert examples["very_low_brain"] < 0.5
    assert examples["equal_brain"] == 0.5
    assert examples["very_high_brain"] > 0.5

    return {
        "incumbent_likelihood_invariant_to_unseen_brain_strength": True,
        "brain_vs_opus_probability_not_identified_by_incumbent_graph": True,
        "published_opus_rating_does_not_identify_brain_rating": True,
        "examples": examples,
        "required_new_information": (
            "BRAIN_INVOLVING_OWNER_OUTCOME_OR_A_SOUND_RELATION_CLASS_OR_"
            "AN_EVALUATOR_INDEPENDENT_BYPASS"
        ),
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
