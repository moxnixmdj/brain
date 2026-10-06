from __future__ import annotations

from typing import Mapping


def separating_event(
    brain: Mapping[str, float],
    opus: Mapping[str, float],
    *,
    eps: float = 1e-12,
) -> frozenset[str] | None:
    keys = set(brain) | set(opus)
    # If laws differ, the positive part of opus-brain has positive mass.
    event = frozenset(
        k for k in keys
        if float(opus.get(k, 0.0)) > float(brain.get(k, 0.0)) + eps
    )
    if not event:
        return None
    return event


def event_mass(law: Mapping[str, float], event: frozenset[str]) -> float:
    return sum(float(law.get(k, 0.0)) for k in event)


def utility_free_dominance_requires_equality(
    brain: Mapping[str, float],
    opus: Mapping[str, float],
) -> dict[str, object]:
    keys = set(brain) | set(opus)
    equal = all(abs(float(brain.get(k, 0.0)) - float(opus.get(k, 0.0))) <= 1e-12 for k in keys)
    event = separating_event(brain, opus)
    if equal:
        return {
            "laws_equal": True,
            "separating_event": None,
            "opus_strictly_better_on_indicator": False,
            "utility_authority_required_for_nonidentical_dominance": False,
        }
    if event is None:
        # If Brain has more mass somewhere, normalization forces Opus to have
        # more mass elsewhere for valid probability laws. Fail closed if callers
        # supplied malformed laws.
        raise ValueError("NONIDENTICAL_LAWS_WITHOUT_OPUS_POSITIVE_PART__CHECK_NORMALIZATION")
    return {
        "laws_equal": False,
        "separating_event": tuple(sorted(event)),
        "brain_event_mass": event_mass(brain, event),
        "opus_event_mass": event_mass(opus, event),
        "opus_strictly_better_on_indicator": event_mass(opus, event) > event_mass(brain, event),
        "utility_authority_required_for_nonidentical_dominance": True,
    }
