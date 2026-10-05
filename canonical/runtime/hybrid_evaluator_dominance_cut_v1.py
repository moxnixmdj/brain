"""Exact finite-domain kernel for the Opus 5.5 hybrid evaluator dominance cut.

This module proves only bounded mathematical implications. It does not prove
that the complete Opus 5.5 useful-task domain is covered, that any current
Brain route is policy-equivalent to Opus 5.5, or that a terminal predicate is
closed.
"""
from __future__ import annotations

from collections import defaultdict
from fractions import Fraction
from typing import Hashable, Mapping, Sequence, TypeVar

A = TypeVar("A", bound=Hashable)
S = TypeVar("S", bound=Hashable)
T = TypeVar("T", bound=Hashable)

Exact = Fraction | int | str | tuple[int, int]


def _f(value: Exact) -> Fraction:
    if isinstance(value, Fraction):
        return value
    if isinstance(value, bool):
        raise TypeError("bool is not an exact rational literal")
    if isinstance(value, int):
        return Fraction(value, 1)
    if isinstance(value, str):
        return Fraction(value)
    if isinstance(value, tuple) and len(value) == 2:
        return Fraction(value[0], value[1])
    raise TypeError("expected exact rational literal")


def _dist(values: Mapping[T, Exact]) -> dict[T, Fraction]:
    out = {k: _f(v) for k, v in values.items()}
    if any(v < 0 for v in out.values()):
        raise ValueError("negative probability")
    if sum(out.values(), Fraction(0, 1)) != 1:
        raise ValueError("distribution must sum exactly to 1")
    return out


def expected_value(distribution: Mapping[A, Exact], reward: Mapping[A, Exact]) -> Fraction:
    p = _dist(distribution)
    missing = set(p) - set(reward)
    if missing:
        raise KeyError(f"missing rewards for {sorted(missing, key=repr)!r}")
    return sum((prob * _f(reward[a]) for a, prob in p.items()), Fraction(0, 1))


def explicit_evaluator_global_argmax_dominates(
    target_distribution: Mapping[A, Exact],
    reward: Mapping[A, Exact],
    brain_action: A,
) -> bool:
    """Return True iff the chosen Brain action is a global reward argmax.

    If true, its reward is >= the expected reward of every target distribution
    over the same finite action space. The caller must separately prove that
    reward is the full admissible task evaluator and that resource constraints
    are represented in the task.
    """
    if brain_action not in reward:
        raise KeyError("brain action lacks reward")
    target = _dist(target_distribution)
    if set(target) - set(reward):
        raise KeyError("target support contains actions without rewards")
    best = max((_f(v) for v in reward.values()), default=None)
    if best is None:
        raise ValueError("empty reward space")
    return _f(reward[brain_action]) == best and _f(reward[brain_action]) >= expected_value(target, reward)


def rollout_distribution(
    initial: Mapping[S, Exact],
    policy: Mapping[S, Mapping[A, Exact]],
    transition: Mapping[tuple[S, A], Mapping[S, Exact]],
    horizon: int,
) -> dict[tuple[tuple[S, ...], tuple[A, ...]], Fraction]:
    """Enumerate an exact finite-horizon trajectory distribution."""
    if horizon < 0:
        raise ValueError("negative horizon")
    init = _dist(initial)
    frontier: dict[tuple[tuple[S, ...], tuple[A, ...]], Fraction] = {
        ((s,), ()): p for s, p in init.items()
    }
    for _ in range(horizon):
        nxt: dict[tuple[tuple[S, ...], tuple[A, ...]], Fraction] = defaultdict(Fraction)
        for (states, actions), mass in frontier.items():
            state = states[-1]
            if state not in policy:
                raise KeyError(f"missing policy for state {state!r}")
            action_dist = _dist(policy[state])
            for action, pa in action_dist.items():
                key = (state, action)
                if key not in transition:
                    raise KeyError(f"missing transition for {key!r}")
                next_state_dist = _dist(transition[key])
                for next_state, ps in next_state_dist.items():
                    nxt[(states + (next_state,), actions + (action,))] += mass * pa * ps
        frontier = dict(nxt)
    if sum(frontier.values(), Fraction(0, 1)) != 1:
        raise AssertionError("rollout mass drift")
    return frontier


def hidden_evaluator_policy_kernel_equivalence(
    initial: Mapping[S, Exact],
    target_policy: Mapping[S, Mapping[A, Exact]],
    brain_policy: Mapping[S, Mapping[A, Exact]],
    transition: Mapping[tuple[S, A], Mapping[S, Exact]],
    horizon: int,
) -> bool:
    """Policy-kernel equality on the bound finite task implies trajectory equality.

    Equal trajectory distributions imply equal expected value for every bounded
    hidden utility over those trajectories. This theorem does not require
    copying the external transition implementation, only using the same bound
    environment/executor semantics during evaluation.
    """
    target_rollout = rollout_distribution(initial, target_policy, transition, horizon)
    brain_rollout = rollout_distribution(initial, brain_policy, transition, horizon)
    return target_rollout == brain_rollout


def hidden_utility_value(
    trajectory_distribution: Mapping[tuple[tuple[S, ...], tuple[A, ...]], Exact],
    utility: Mapping[tuple[tuple[S, ...], tuple[A, ...]], Exact],
) -> Fraction:
    p = _dist(trajectory_distribution)
    if set(p) - set(utility):
        raise KeyError("utility missing a trajectory")
    return sum((mass * _f(utility[t]) for t, mass in p.items()), Fraction(0, 1))
