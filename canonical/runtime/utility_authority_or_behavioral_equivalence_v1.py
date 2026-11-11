from __future__ import annotations

from math import isfinite
from typing import Mapping

EPS=1e-12


class BehavioralLawError(ValueError):
    pass


def _validate_probability_law(law: Mapping[str,float]) -> None:
    if not law:
        raise BehavioralLawError("NONEMPTY_PROBABILITY_LAW_REQUIRED")
    vals=[float(v) for v in law.values()]
    if any((not isfinite(v)) or v < -EPS for v in vals):
        raise BehavioralLawError("INVALID_PROBABILITY")
    if abs(sum(vals)-1.0) > 1e-9:
        raise BehavioralLawError("PROBABILITY_MASS_MUST_SUM_TO_ONE")


def separating_event(
    brain: Mapping[str, float],
    opus: Mapping[str, float],
    *,
    eps: float = EPS,
) -> frozenset[str] | None:
    _validate_probability_law(brain)
    _validate_probability_law(opus)
    keys = set(brain) | set(opus)
    # If normalized laws differ, the positive part of opus-brain has positive mass.
    event = frozenset(
        k for k in keys
        if float(opus.get(k, 0.0)) > float(brain.get(k, 0.0)) + eps
    )
    return event or None


def event_mass(law: Mapping[str, float], event: frozenset[str]) -> float:
    return sum(float(law.get(k, 0.0)) for k in event)


def utility_free_dominance_requires_equality(
    brain: Mapping[str, float],
    opus: Mapping[str, float],
) -> dict[str, object]:
    _validate_probability_law(brain)
    _validate_probability_law(opus)
    keys = set(brain) | set(opus)
    equal = all(abs(float(brain.get(k, 0.0)) - float(opus.get(k, 0.0))) <= EPS for k in keys)
    event = separating_event(brain, opus)
    if equal:
        return {
            "laws_equal": True,
            "separating_event": None,
            "opus_strictly_better_on_indicator": False,
            "utility_authority_required_for_nonidentical_dominance": False,
        }
    if event is None:
        # This cannot occur for distinct normalized probability laws.
        raise BehavioralLawError("NORMALIZED_NONIDENTICAL_LAWS_LACK_POSITIVE_OPUS_PART")
    return {
        "laws_equal": False,
        "separating_event": tuple(sorted(event)),
        "brain_event_mass": event_mass(brain, event),
        "opus_event_mass": event_mass(opus, event),
        "opus_strictly_better_on_indicator": event_mass(opus, event) > event_mass(brain, event),
        "utility_authority_required_for_nonidentical_dominance": True,
    }
