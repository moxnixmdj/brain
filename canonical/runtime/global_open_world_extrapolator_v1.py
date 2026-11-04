#!/usr/bin/env python3
"""Global Non-Local Extrapolation & Target-Persistence Engine (`K3 = 0`, `$0` spend).

Implements `OWNER_ACTIVE_GOAL_20261018_V1.md` §5 Laws 3, 4, and 5 from first principles:

  - **Law 5 (Global, Non-Local Extrapolation)**:
    Never conclude "the fastest / global best" from local data covering only a tiny
    subset of channels (the YouTube/TikTok trap). Partition the opportunity space
    into `Theta_known(t) U Theta_unseen(t)` using Pitman-Yor / Good-Turing unseen
    tail mass `M_unseen(t)` combined with structural universe coverage deficit,
    upper-tail extreme-value potential `U_unseen(t)`, and Expected Value of Global
    Information `EVOI_global(t)`. When `EVOI_global(t) > 0` on a global-optimum or
    target-deficient problem, local commitment is REFUSED (`EXPAND_UNSEEN_SPACE_FIRST`),
    recording concrete data gaps into `ignorance_ledger_v1` and ranking acquisition
    channels via `curriculum_v1` + `computer_env_v1`.

  - **Law 3 & Law 4 (Persistence to Measured Target + Fastest Data Acquisition)**:
    Binds quantitative goals via `execution_guard.goal_target_binding_v1.bind`,
    enforces `VERIFICATION_IS_SOMEONE_ELSE` (external `measure` required), never
    stops at `$100` on a `$1,000,000` goal, acquires missing channel observations,
    switches strategies when velocity `dV / dc` stalls, and stops ONLY when the
    external measurement reaches `target` or deliberated budget ends.
"""
from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime import curriculum_v1
from canonical.runtime import ignorance_ledger_v1

SCHEMA = "PROJECT_BRAIN_GLOBAL_OPEN_WORLD_EXTRAPOLATOR_V1"

EXPAND_UNSEEN_SPACE_FIRST = "EXPAND_UNSEEN_SPACE_FIRST"
COMMIT_GLOBAL_OPTIMUM = "COMMIT_GLOBAL_OPTIMUM"
TARGET_REACHED = "PASS__MEASURED_TARGET_REACHED"
TARGET_UNREACHED_BUDGET_EXHAUSTED = "OPEN__TARGET_NOT_YET_REACHED"
FAIL_MISSING_EXTERNAL_MEASURE = "FAIL_CLOSED__EXTERNAL_MEASUREMENT_REQUIRED"
FAIL_NO_QUANTITATIVE_TARGET = "FAIL_CLOSED__NO_NUMERIC_TARGET_IN_GOAL"

@dataclass
class ChannelObservation:
    """Empirical performance statistics for one observed mechanism/channel."""

    channel_id: str
    samples: int
    mean_payoff: float
    max_payoff: float | None = None
    payoff_std: float = 0.0
    unit_cost: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def velocity(self) -> float:
        return self.mean_payoff / max(self.unit_cost, 1e-6)

    @property
    def effective_max(self) -> float:
        return self.mean_payoff if self.max_payoff is None else max(self.mean_payoff, self.max_payoff)


def has_global_quantifier(goal: str) -> bool:
    """Deprecated name kept for API continuity.

    English keywords are not an optimality detector. Any non-empty goal may have
    unseen better channels; locality must be *proved*, never inferred from prose.
    """
    return bool(str(goal or "").strip())


def discover_unseen_machine_channel(
    round_idx: int,
    known_ids: Sequence[str],
) -> "ChannelObservation | None":
    """Native unseen-channel discovery via curriculum + installed programs (`K3 = 0`)."""
    del round_idx
    known = {str(x) for x in known_ids}
    try:
        for ch in curriculum_v1.ordered_channels():
            cid = f"curriculum:{ch}"
            if cid not in known:
                return ChannelObservation(
                    channel_id=cid,
                    samples=1,
                    mean_payoff=0.0,
                    unit_cost=1.0,
                    metadata={"source": "curriculum", "channel": str(ch)},
                )
    except Exception:
        pass
    try:
        from canonical.runtime import computer_env_v1

        for prog in computer_env_v1.installed_programs(limit=16):
            name = str(prog)
            cid = f"program:{name}"
            if cid not in known:
                return ChannelObservation(
                    channel_id=cid,
                    samples=1,
                    mean_payoff=0.0,
                    unit_cost=1.0,
                    metadata={"source": "computer_env", "program": name},
                )
    except Exception:
        pass
    return None


def discoverable_machine_universe_size(*, fallback: int = 24) -> int:
    """Count real discoverable tools/channels on this machine (`computer_env_v1` + `curriculum_v1`)."""
    prog_count = 0
    try:
        from canonical.runtime import computer_env_v1

        progs = computer_env_v1.installed_programs()
        prog_count = min(64, len(progs))
    except Exception:
        prog_count = 0
    curr_count = len(curriculum_v1.CHANNELS)
    return max(fallback, prog_count + curr_count)


def estimate_unseen_opportunity_space(
    observed_channels: Sequence[ChannelObservation],
    *,
    goal: str = "",
    target_gap: float | None = None,
    remaining_budget: float = 10.0,
    universe_size_hint: int | None = None,
    probe_cost: float = 1.0,
    pitman_yor_discount: float = 0.35,
    prior_concentration: float = 2.0,
    unseen_tail_threshold: float = 0.18,
    ledger_path: str | None = None,
) -> dict[str, Any]:
    """Estimate unseen opportunity-space mass `M_unseen` and decide expand vs. commit."""
    k_obs = len(observed_channels)
    total_samples = sum(max(0, int(c.samples)) for c in observed_channels)
    rare_channels = sum(1 for c in observed_channels if int(c.samples) <= 1)

    universe_n = (
        int(universe_size_hint)
        if universe_size_hint is not None and universe_size_hint > 0
        else discoverable_machine_universe_size(fallback=max(12, k_obs + 8))
    )
    universe_n = max(universe_n, k_obs)

    # 1. Pitman-Yor / Good-Turing unseen species mass + universe coverage deficit
    d = max(0.0, min(0.95, float(pitman_yor_discount)))
    alpha = max(0.1, float(prior_concentration))
    m_py = (rare_channels + d * k_obs + alpha) / (total_samples + alpha + k_obs)
    m_cov = 0.0 if universe_n == 0 else max(0.0, 1.0 - (k_obs / float(universe_n)))
    if k_obs == 0:
        m_unseen = 1.0
    elif k_obs >= universe_n and rare_channels == 0 and total_samples >= 2 * universe_n:
        m_unseen = 0.0
    else:
        m_unseen = min(0.99, 0.45 * m_py + 0.55 * m_cov)

    # 2. Best known velocity & between-channel dispersion for extreme-value upper tail
    if observed_channels:
        velocities = [c.velocity for c in observed_channels]
        best_chan = max(observed_channels, key=lambda c: (c.velocity, c.effective_max, c.channel_id))
        best_vel = best_chan.velocity
        mean_vel = sum(velocities) / len(velocities)
        if len(velocities) >= 2:
            var_between = sum((v - mean_vel) ** 2 for v in velocities) / (len(velocities) - 1)
            sigma_between = math.sqrt(var_between)
        else:
            # With 1 observed channel, structural dispersion uncertainty equals its magnitude!
            sigma_between = max(abs(best_vel) * 0.75, 1.0)
        # Include within-channel std if observed dispersion across 2 similar channels is tiny
        max_within = max((c.payoff_std / max(c.unit_cost, 1e-6)) for c in observed_channels)
        sigma_eff = max(sigma_between, max_within, 0.35 * max(abs(best_vel), 1.0))
    else:
        best_chan = None
        best_vel = 0.0
        sigma_eff = 10.0

    unobserved_count = max(0, universe_n - k_obs)
    extreme_factor = math.sqrt(2.0 * math.log(1.0 + max(1, unobserved_count)))
    u_unseen_velocity = best_vel + sigma_eff * extreme_factor

    # Remaining exploitation horizon after paying `probe_cost`
    exploit_budget_after_probe = max(0.0, float(remaining_budget) - float(probe_cost))
    expected_gain_per_unit = m_unseen * max(0.0, u_unseen_velocity - best_vel)
    evoi_global = expected_gain_per_unit * max(1.0, exploit_budget_after_probe) - float(probe_cost)

    # Decision-theoretic: never treat English keywords as an optimality detector.
    # A quantitative target gap, positive EVOI, or empty observation set is sufficient.
    known_max_total = best_vel * max(0.0, float(remaining_budget))
    known_insufficient_for_target = (
        target_gap is not None and float(target_gap) > 0.0 and known_max_total < float(target_gap)
    )
    pursuing_target = target_gap is not None and float(target_gap) > 0.0
    global_claim = pursuing_target or has_global_quantifier(goal)

    must_expand = (
        float(remaining_budget) > float(probe_cost)
        and unobserved_count > 0
        and m_unseen >= unseen_tail_threshold
        and (
            (evoi_global > 0.0 and (global_claim or known_insufficient_for_target))
            or known_insufficient_for_target
            or k_obs == 0
        )
    )

    verdict = EXPAND_UNSEEN_SPACE_FIRST if must_expand else COMMIT_GLOBAL_OPTIMUM
    recommended_acquisition_channels = curriculum_v1.ordered_channels()

    recorded_gap_id: str | None = None
    if must_expand and ledger_path is not None:
        why_reason = (
            "known_channels_cannot_reach_target"
            if known_insufficient_for_target
            else "global_optimum_requested_on_partial_channel_coverage"
        )
        recorded_gap_id = ignorance_ledger_v1.note(
            f"unobserved_opportunity_channels_beyond_{k_obs}_of_{universe_n}",
            why=f"{why_reason}:{goal[:80]}",
            cost=float(probe_cost),
            path=ledger_path,
        )

    return {
        "schema": SCHEMA,
        "verdict": verdict,
        "observed_channel_count": k_obs,
        "universe_size_estimate": universe_n,
        "unobserved_channel_count": unobserved_count,
        "unseen_opportunity_mass": round(m_unseen, 6),
        "best_known_channel": best_chan.channel_id if best_chan is not None else None,
        "best_known_velocity": round(best_vel, 6),
        "upper_tail_unseen_velocity": round(u_unseen_velocity, 6),
        "evoi_global": round(evoi_global, 6),
        "global_quantifier_detected": global_claim,
        "known_insufficient_for_target": bool(known_insufficient_for_target),
        "recommended_acquisition_channels": recommended_acquisition_channels,
        "recorded_gap_id": recorded_gap_id,
    }


def pursue_global_target_to_completion(
    goal: str,
    *,
    measure: Callable[[], float] | None,
    initial_channels: Sequence[ChannelObservation],
    execute_channel: Callable[[str, int], Mapping[str, Any]],
    discover_unseen_channel: Callable[[int, Sequence[str]], ChannelObservation | None] | None = None,
    native_discovery: bool = False,
    budget: float = 25.0,
    probe_cost: float = 1.0,
    universe_size_hint: int | None = None,
    ledger_path: str | None = None,
    max_rounds: int = 50,
) -> dict[str, Any]:
    """Closed-loop global target chase: bind -> check unseen tail -> acquire/act -> re-measure -> persist.

    Enforces:
      1. `VERIFICATION_IS_SOMEONE_ELSE`: fails closed without external `measure`.
      2. Never stops early (`$100` on a `$1M` target stays `OPEN`, never `PASS`).
      3. Refuses local tunnel vision on partial channel sets (discovers unseen channels first).
      4. Updates empirical channel payoff & switches immediately when a channel stalls.
    """
    if not callable(measure):
        return {
            "schema": SCHEMA,
            "status": FAIL_MISSING_EXTERNAL_MEASURE,
            "pass": False,
            "reason": "VERIFICATION_IS_SOMEONE_ELSE_REQUIRES_CALLER_MEASURE",
        }

    from execution_guard import goal_target_binding_v1 as binding

    bound = binding.bind(goal)
    if not bound.get("pass"):
        return {
            "schema": SCHEMA,
            "status": FAIL_NO_QUANTITATIVE_TARGET,
            "pass": False,
            "binding": bound,
        }

    target = float(bound["target"])
    direction = str(bound["direction"])

    def _gap_remaining(current_val: float) -> float:
        if direction == binding.MAXIMIZE:
            return max(0.0, target - current_val)
        return max(0.0, current_val - target)

    def _is_met(current_val: float) -> bool:
        return (
            current_val >= target
            if direction == binding.MAXIMIZE
            else current_val <= target
        )

    channels: dict[str, ChannelObservation] = {
        c.channel_id: ChannelObservation(
            channel_id=c.channel_id,
            samples=c.samples,
            mean_payoff=c.mean_payoff,
            max_payoff=c.max_payoff,
            payoff_std=c.payoff_std,
            unit_cost=c.unit_cost,
            metadata=dict(c.metadata),
        )
        for c in initial_channels
    }

    current_measured = float(measure())
    initial_measured = current_measured
    budget_left = float(budget)
    history: list[dict[str, Any]] = []
    discoveries: list[str] = []
    discovery_exhausted = False
    if discover_unseen_channel is None and native_discovery:
        discover_unseen_channel = discover_unseen_machine_channel

    for round_idx in range(max_rounds):
        if _is_met(current_measured):
            break
        if budget_left <= 1e-9:
            break

        gap_now = _gap_remaining(current_measured)
        effective_universe = (
            len(channels)
            if (discover_unseen_channel is None or discovery_exhausted)
            else universe_size_hint
        )
        extrap = estimate_unseen_opportunity_space(
            list(channels.values()),
            goal=goal,
            target_gap=gap_now,
            remaining_budget=budget_left,
            universe_size_hint=effective_universe,
            probe_cost=probe_cost,
            ledger_path=ledger_path,
        )

        if (
            extrap["verdict"] == EXPAND_UNSEEN_SPACE_FIRST
            and discover_unseen_channel is not None
            and not discovery_exhausted
            and budget_left >= probe_cost
        ):
            budget_left -= probe_cost
            discovered = discover_unseen_channel(round_idx, sorted(channels.keys()))
            if discovered is None:
                discovery_exhausted = True
                if extrap.get("recorded_gap_id") and ledger_path:
                    ignorance_ledger_v1.resolve(
                        extrap["recorded_gap_id"], helped=False, close=False, path=ledger_path
                    )
                history.append({
                    "round": round_idx,
                    "mode": "DISCOVER_UNSEEN",
                    "discovered": None,
                    "measured": current_measured,
                    "budget_left": round(budget_left, 4),
                })
                continue

            channels[discovered.channel_id] = discovered
            discoveries.append(discovered.channel_id)
            helped = discovered.velocity > float(extrap["best_known_velocity"])
            if os.environ.get("BRAIN_CURRICULUM_STATE"):
                curriculum_v1.credit_channel("explore", helped=helped)
            if extrap.get("recorded_gap_id") and ledger_path:
                ignorance_ledger_v1.resolve(
                    extrap["recorded_gap_id"], helped=helped, close=True, path=ledger_path
                )
            current_measured = float(measure())
            history.append({
                "round": round_idx,
                "mode": "DISCOVER_UNSEEN",
                "discovered": discovered.channel_id,
                "discovered_velocity": round(discovered.velocity, 4),
                "measured": current_measured,
                "budget_left": round(budget_left, 4),
            })
            continue

        # Select affordable channel with highest empirical velocity
        affordable = [c for c in channels.values() if c.unit_cost <= budget_left + 1e-9]
        if not affordable:
            break
        chosen = max(affordable, key=lambda c: (c.velocity, c.effective_max, -c.samples, c.channel_id))
        before_val = current_measured
        act_res = execute_channel(chosen.channel_id, round_idx)
        spent = float(act_res.get("cost", chosen.unit_cost))
        budget_left = max(0.0, budget_left - max(0.0, spent))
        current_measured = float(measure())

        signed_progress = (
            (current_measured - before_val)
            if direction == binding.MAXIMIZE
            else (before_val - current_measured)
        )
        # Online empirical posterior update of channel payoff!
        n_prev = max(0, chosen.samples)
        new_mean = (chosen.mean_payoff * n_prev + signed_progress) / (n_prev + 1.0)
        chosen.samples = n_prev + 1
        chosen.mean_payoff = new_mean
        chosen.max_payoff = max(chosen.effective_max, signed_progress)
        if os.environ.get("BRAIN_CURRICULUM_STATE"):
            curriculum_v1.credit_channel("solve", helped=(signed_progress > 0.0))

        history.append({
            "round": round_idx,
            "mode": "EXECUTE_CHANNEL",
            "channel_id": chosen.channel_id,
            "progress": round(signed_progress, 6),
            "measured": current_measured,
            "budget_left": round(budget_left, 4),
        })

    met = _is_met(current_measured)
    return {
        "schema": SCHEMA,
        "status": TARGET_REACHED if met else TARGET_UNREACHED_BUDGET_EXHAUSTED,
        "pass": met,
        "goal": goal,
        "target": target,
        "direction": direction,
        "initial_measured": initial_measured,
        "final_measured": current_measured,
        "remaining_gap": round(_gap_remaining(current_measured), 6),
        "budget_spent": round(float(budget) - budget_left, 6),
        "budget_remaining": round(budget_left, 6),
        "discovered_channels": discoveries,
        "rounds": len(history),
        "history": history,
        "terminal_authority": False,
    }
