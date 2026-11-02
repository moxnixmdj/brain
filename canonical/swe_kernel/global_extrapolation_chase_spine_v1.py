#!/usr/bin/env python3
"""Global Anti-Blind-Spot Extrapolation & Minimal-Action Target-Chase Spine (`K3 = 0`).

Composes five already-built repository organs into the live awake/controller spine
without re-implementing any of them:
  1. `canonical/runtime/global_retrieval_controller_v1.py` — discounts correlated
     channels (`upstream_group`), maintains monotonic candidate memory, expands
     graph neighbors (`graph_snowball_actions`), and schedules orthogonal discovery
     channels by empirical `marginal_novelty`.
  2. `canonical/runtime/open_world_hypothesis_guard_v4.py` — blocks declaring an
     action "fastest" unless the hypothesis space is closed by an authenticated
     coverage receipt, residual-action invariance is proved, or all discoverable
     independent channels are sampled to novelty saturation.
  3. `canonical/runtime/experience_v1.py` + `canonical/runtime/flywheel_v1.py` —
     consulted BEFORE Round 0 (`0.238 ms`) so structurally broken tools on this
     machine (`BINARY_ABSENT`, `SOURCE_UNSUPPORTED`, etc.) are skipped immediately
     and pathology primers prevent repeated dead steps.
  4. `execution_guard/goal_chase_v1.py` + `execution_guard/target_chase_driver_v1.py`
     — enforces `measure != act`, distinguishes `OPEN__TARGET_CHASE_DATA_INCOMPLETE`
     from `OPEN__TARGET_CHASE_NO_MEASURED_PROGRESS`, credits `ignorance_ledger_v1`
     only when closing a data gap moves the measured number, and stops only on
     `PASS__TARGET_CHASE_MET`.
"""
from __future__ import annotations

import hashlib
import time
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime import experience_v1 as exp
from canonical.runtime import flywheel_v1 as fly
from canonical.runtime import global_retrieval_controller_v1 as grc
from canonical.runtime import ignorance_ledger_v1 as ign_ledger
from canonical.runtime import interval_information_frontier_v1 as iif
from canonical.runtime import jit_knowledge_v1 as jit_know
from canonical.runtime import one_shot_reality_closure_v2 as reality_closure
from canonical.runtime import open_world_hypothesis_guard_v4 as owhg
from execution_guard import goal_chase_v1 as gchase
from execution_guard import target_chase_driver_v1 as tdriver

SCHEMA = "PROJECT_BRAIN_GLOBAL_EXTRAPOLATION_CHASE_SPINE_V1"


def round0_pathology_precheck(
    goal: str,
    candidate_routes: Sequence[Mapping[str, Any]],
    *,
    experience_state_path: str | None = None,
    flywheel_state_path: str | None = None,
) -> dict[str, Any]:
    """Consult `experience_v1` and `flywheel_v1.primers()` BEFORE Round 0 (`< 0.5 ms`)."""
    t0 = time.perf_counter_ns()
    exp_kw = {"path": experience_state_path} if experience_state_path else {}
    fly_kw = {"path": flywheel_state_path} if flywheel_state_path else {}

    primers = list(fly.primers(**fly_kw) or [])
    recalled_cap = exp.recall_resolution(goal, **exp_kw)

    admissible: list[dict[str, Any]] = []
    suppressed: list[dict[str, Any]] = []
    for raw in candidate_routes:
        row = dict(raw)
        cid = str(row.get("route_id") or row.get("capability_id") or row.get("id") or "")
        why_hint = str(row.get("known_pathology") or row.get("why") or "STRUCTURAL_CHECK")
        is_sup = False
        if cid:
            # Check explicit hint and common structural failure codes recorded on this machine
            for code in (
                why_hint,
                "BOUND_CAPABILITY_BINARY_ABSENT",
                "BOUND_CAPABILITY_SOURCE_UNSUPPORTED",
                "NO_SUCH_ADAPTER",
                "MISSING_EXECUTABLE",
            ):
                if exp.is_suppressed(cid, code, **exp_kw):
                    is_sup = True
                    row["suppressed_reason"] = code
                    break
        if is_sup:
            suppressed.append(row)
        else:
            if recalled_cap and cid == recalled_cap:
                row["experience_recalled"] = True
            admissible.append(row)

    return {
        "primers": primers,
        "recalled_capability_id": recalled_cap,
        "admissible_routes": admissible,
        "suppressed_routes": suppressed,
        "precheck_ms": round((time.perf_counter_ns() - t0) / 1e6, 4),
    }


def rank_global_minimal_action_routes(
    options: Sequence[Mapping[str, Any]],
    *,
    goal: str = "",
    direction: str = "maximize",
    experience_state_path: str | None = None,
    flywheel_state_path: str | None = None,
    cost_router: Any = None,
) -> list[dict[str, Any]]:
    """Rank verified global options by `(expected_gain * reliability_lcb) / (actions * measured_cost)`."""
    pre = round0_pathology_precheck(
        goal,
        options,
        experience_state_path=experience_state_path,
        flywheel_state_path=flywheel_state_path,
    )
    verified: list[dict[str, Any]] = []
    for row in pre["admissible_routes"]:
        if not (
            row.get("independently_verified_by")
            or row.get("candidate_authority") == "VERIFIED"
        ):
            continue
        rid = str(row.get("route_id") or row.get("id") or "")
        gain = float(row.get("expected_gain", row.get("verified_yield", 0.0)) or 0.0)
        if direction == "minimize" and gain < 0:
            gain = abs(gain)
        actions = max(1.0, float(row.get("action_count", 1.0) or 1.0))
        cost = max(0.001, float(row.get("action_cost", 1.0) or 1.0))
        rel_lcb = 1.0
        measured_ms: float | None = None
        if cost_router is not None:
            default_ms = float(row.get("measured_ms") or (cost * 10.0))
            cm = cost_router.score_candidate(rid, expected_gain=gain, default_cost_ms=default_ms)
            measured_ms = float(cm["measured_ms"])
            rel_lcb = float(cm["reliability_lcb"])
            cost = max(0.5, measured_ms)
        elif row.get("measured_ms") is not None:
            measured_ms = max(0.5, float(row["measured_ms"]))
            cost = measured_ms
        recalled_bonus = 1.15 if row.get("experience_recalled") else 1.0
        efficiency = (gain * recalled_bonus * rel_lcb) / (actions * cost)
        enriched = dict(row)
        enriched["global_minimal_action_efficiency"] = round(efficiency, 6)
        if measured_ms is not None:
            enriched["measured_ms"] = round(measured_ms, 4)
            enriched["reliability_lcb"] = round(rel_lcb, 4)
        verified.append(enriched)

    verified.sort(
        key=lambda r: (
            -float(r["global_minimal_action_efficiency"]),
            float(r.get("action_count", 1.0) or 1.0),
            str(r.get("route_id") or r.get("id") or ""),
        )
    )
    return verified


class GlobalDiscoveryWorld:
    """Anti-blind-spot discovery scheduler backed by `global_retrieval_controller_v1` & `open_world_hypothesis_guard_v4`."""

    def __init__(
        self,
        *,
        goal: str,
        environment_id: str = "live_workspace",
        channels: Sequence[Mapping[str, Any]] = (),
        channel_fetcher: Callable[[Mapping[str, Any]], Sequence[Mapping[str, Any]]] | None = None,
        coverage_receipt: Mapping[str, Any] | None = None,
        residual_action_receipt: Mapping[str, Any] | None = None,
        min_independent_channels: int = 2,
        min_evidence_kinds: int = 1,
        ledger_path: str | None = None,
    ) -> None:
        self.goal = str(goal)
        self.goal_id = "goal:" + hashlib.sha256(self.goal.encode("utf-8")).hexdigest()[:16]
        self.environment_id = str(environment_id)
        self.channels = [dict(c) for c in channels]
        self.channel_fetcher = channel_fetcher
        self.coverage_receipt = coverage_receipt
        self.residual_action_receipt = residual_action_receipt
        self.min_independent_channels = max(1, int(min_independent_channels))
        self.min_evidence_kinds = max(1, int(min_evidence_kinds))
        self.ledger_path = ledger_path
        self.state = grc.new_state()
        self.source_stats: dict[str, dict[str, Any]] = {}
        self._probed_source_ids: set[str] = set()
        self._recorded_gap_ids: list[str] = []
        self.last_minimum_information_contract: dict[str, Any] | None = None

    def observed_evidence_kinds(self, opts: Sequence[Mapping[str, Any]] = ()) -> list[str]:
        """Compute distinct evidence kinds answered across probed sources and options."""
        kinds: set[str] = set()
        jit_kinds = jit_know.kinds_answered(sorted(self._probed_source_ids))
        for jk in jit_kinds:
            if jk and jk != "unknown":
                kinds.add(jk)
        ch_by_id = {str(c.get("source_id") or ""): c for c in self.channels}
        for sid in self._probed_source_ids:
            ch = ch_by_id.get(sid) or {}
            ek = str(ch.get("evidence_kind") or ch.get("kind") or "").strip()
            if ek:
                kinds.add(ek)
        for o in opts:
            ek = str(o.get("evidence_kind") or "").strip()
            if ek:
                kinds.add(ek)
        return sorted(kinds)

    def policy_changing_unprobed_channels(self, best_verified_gain: float) -> list[dict[str, Any]]:
        """Return unprobed channels whose declared `yield_upper_bound` can beat `best_verified_gain`."""
        out: list[dict[str, Any]] = []
        for ch in self.channels:
            sid = str(ch.get("source_id") or "").strip()
            if not sid or sid in self._probed_source_ids:
                continue
            ub = ch.get("yield_upper_bound", ch.get("max_potential_gain"))
            if isinstance(ub, (int, float)) and not isinstance(ub, bool) and float(ub) > best_verified_gain:
                out.append(dict(ch))
        out.sort(
            key=lambda c: -float(c.get("yield_upper_bound", c.get("max_potential_gain", 0.0)) or 0.0)
        )
        return out

    def unprobed_independent_groups(self) -> set[str]:
        consumed = set(self.state.get("consumed_upstream_groups") or [])
        remaining: set[str] = set()
        for ch in self.channels:
            sid = str(ch.get("source_id") or "").strip()
            grp = str(ch.get("upstream_group") or sid).strip()
            if grp and grp.casefold() not in {g.casefold() for g in consumed}:
                remaining.add(grp.casefold())
        return remaining

    def ingest_observations(
        self,
        observations: Sequence[Mapping[str, Any]],
        *,
        source_id: str,
        upstream_group: str,
        action_id: str,
    ) -> list[dict[str, Any]]:
        before_count = len(self.state.get("candidates") or [])
        clean_obs: list[dict[str, Any]] = []
        for obs in observations:
            item = dict(obs)
            # Strip authority-smuggling keys before feeding candidate memory
            for k in (
                "verified_sufficient",
                "acceptance_credit",
                "family_credit",
                "capability_credit",
                "ownership_credit",
                "promotion_authority",
            ):
                item.pop(k, None)
            clean_obs.append(item)

        self.state = grc.add_candidates(
            self.state,
            clean_obs,
            source_id=source_id,
            upstream_group=upstream_group,
            action_id=action_id,
        )
        consumed = list(self.state.get("consumed_upstream_groups") or [])
        if upstream_group not in consumed:
            consumed.append(upstream_group)
        self.state["consumed_upstream_groups"] = consumed
        self._probed_source_ids.add(source_id)

        after_count = len(self.state.get("candidates") or [])
        novel_added = max(0, after_count - before_count)
        st = self.source_stats.setdefault(
            source_id,
            {
                "attempts": 0,
                "novel_candidate_actions": 0,
                "sufficient_witness_actions": 0,
                "failures": 0,
                "mean_latency_seconds": 0.01,
                "mean_requests": 1.0,
            },
        )
        st["attempts"] += 1
        if novel_added > 0:
            st["novel_candidate_actions"] += 1
        if any(o.get("independently_verified_by") or o.get("candidate_authority") == "VERIFIED" for o in observations):
            st["sufficient_witness_actions"] += 1

        # Expand graph neighbors (`dependencies`, `references`, `related`) into new channels if provided
        for cand in clean_obs:
            for edge_act in grc.graph_snowball_actions(cand, max_depth=1, max_edges=8):
                target_grp = str(edge_act.get("target") or "").strip()
                if target_grp and not any(str(c.get("source_id")) == target_grp for c in self.channels):
                    self.channels.append(
                        {
                            "source_id": target_grp,
                            "upstream_group": target_grp,
                            "bounded_scope": True,
                            "authoritative_enumeration": True,
                            "scope_id": f"graph:{target_grp}",
                        }
                    )

        unexplored_cnt = len(self.unprobed_independent_groups())
        formatted: list[dict[str, Any]] = []
        for obs in observations:
            row = dict(obs)
            row.setdefault("source_id", source_id)
            row.setdefault("upstream_group", upstream_group)
            row["nonexistence_claim_authorized"] = False
            row["unexplored_independent_channels"] = unexplored_cnt
            formatted.append(row)
        return formatted

    def options_provider(self, ctx: Mapping[str, Any]) -> list[dict[str, Any]]:
        """Schedule & probe the highest-marginal-novelty unvisited channel (`global_retrieval_controller_v1`)."""
        if self.channel_fetcher is None:
            return []
        pending_actions: list[dict[str, Any]] = []
        for ch in self.channels:
            sid = str(ch.get("source_id") or "").strip()
            if not sid or sid in self._probed_source_ids:
                continue
            grp = str(ch.get("upstream_group") or sid).strip()
            pending_actions.append(
                {
                    "action": "ENUMERATE_BOUNDED_SOURCE" if ch.get("bounded_scope") else "QUERY_SOURCE",
                    "action_id": f"PROBE:{sid}",
                    "source_id": sid,
                    "upstream_group": grp,
                    "channel_spec": ch,
                }
            )
        if not pending_actions:
            return []

        plan = grc.compile_global_plan(
            query_actions=pending_actions,
            sources=self.channels,
            source_stats=self.source_stats,
            state=self.state,
        )
        ranked = list(plan.get("actions") or [])
        if not ranked:
            return []

        # Prioritize policy-changing upper-bound channels first so high-upside hidden opportunities are never starved!
        ub_by_sid = {
            str(c.get("source_id") or ""): float(c.get("yield_upper_bound", c.get("max_potential_gain", 0.0)) or 0.0)
            for c in self.channels
        }
        ranked.sort(
            key=lambda a: -ub_by_sid.get(str(a.get("source_id") or ""), 0.0)
        )

        # Probe up to 2 highest-marginal-novelty orthogonal upstream groups in one data-acquisition round
        newly_discovered: list[dict[str, Any]] = []
        groups_probed_this_round: set[str] = set()
        for act_row in ranked:
            sid = str(act_row.get("source_id") or "")
            grp = str(act_row.get("upstream_group") or sid)
            if grp.casefold() in groups_probed_this_round:
                continue
            ch_spec = next((c for c in self.channels if str(c.get("source_id")) == sid), {"source_id": sid, "upstream_group": grp})
            raw_found = list(self.channel_fetcher(ch_spec) or [])
            ingested = self.ingest_observations(
                raw_found,
                source_id=sid,
                upstream_group=grp,
                action_id=str(act_row.get("action_id") or f"PROBE:{sid}"),
            )
            newly_discovered.extend(ingested)
            groups_probed_this_round.add(grp.casefold())
            if len(groups_probed_this_round) >= 2:
                break

        # Refresh unexplored count across all options discovered so far
        rem = len(self.unprobed_independent_groups())
        known_opts = ctx.get("known_options")
        if isinstance(known_opts, list):
            for existing in known_opts:
                if isinstance(existing, dict):
                    existing["unexplored_independent_channels"] = rem
        for item in newly_discovered:
            item["unexplored_independent_channels"] = rem
        return newly_discovered

    def completeness_gate(self, ctx: Mapping[str, Any]) -> dict[str, Any]:
        """Combine `open_world_hypothesis_guard_v4` + channel-saturation anti-YouTube completeness check."""
        opts = [dict(o) for o in (ctx.get("known_options") or []) if isinstance(o, Mapping)]
        rem = len(self.unprobed_independent_groups())

        # Check explicit open-world hypothesis guard receipt if hypotheses are present
        guard_closed = False
        hyps = [
            {
                "id": str(o.get("route_id") or o.get("id") or f"h_{i}"),
                "plausible": bool(o.get("plausible", True)),
                "best_action": str(o.get("route_id") or o.get("best_action") or o.get("id") or f"act_{i}"),
            }
            for i, o in enumerate(opts)
            if o.get("independently_verified_by") or o.get("candidate_authority") == "VERIFIED"
        ]
        if hyps and (self.coverage_receipt is not None or self.residual_action_receipt is not None):
            try:
                verdict = owhg.decision_sufficient(
                    environment_id=self.environment_id,
                    goal_id=self.goal_id,
                    hypotheses=hyps,
                    coverage_receipt=self.coverage_receipt,
                    residual_action_receipt=self.residual_action_receipt,
                )
                guard_closed = bool(verdict.get("open_world_safe"))
            except owhg.OpenWorldHypothesisError:
                guard_closed = False

        annotated: list[dict[str, Any]] = []
        for o in opts:
            cp = dict(o)
            cp["unexplored_independent_channels"] = rem
            cp["open_world_guard_closed"] = guard_closed
            annotated.append(cp)

        base_gate = gchase.completeness_gate_for(
            self.goal,
            min_channels=self.min_independent_channels,
        )
        res = dict(base_gate({**ctx, "known_options": annotated}))
        best_gain = max(
            (
                float(o.get("expected_gain", o.get("verified_yield", 0.0)) or 0.0)
                for o in opts
                if o.get("independently_verified_by") or o.get("candidate_authority") == "VERIFIED"
            ),
            default=0.0,
        )
        dominating_unprobed = self.policy_changing_unprobed_channels(best_gain)
        kinds_seen = self.observed_evidence_kinds(opts)
        kinds_shortfall = len(kinds_seen) < self.min_evidence_kinds and rem > 0

        blockers: list[str] = []
        for dch in dominating_unprobed:
            blockers.append(f"POLICY_CHANGING_UPPER_BOUND_UNPROBED:{dch.get('source_id')}")
        if kinds_shortfall:
            blockers.append(f"EVIDENCE_KIND_DIVERSITY_SHORTFALL:{len(kinds_seen)}<{self.min_evidence_kinds}")

        if blockers and not guard_closed:
            res["complete"] = False
            res.setdefault("missing", [])
            for b in blockers:
                if b not in res["missing"]:
                    res["missing"].append(b)
            min_info = reality_closure.compile_minimum_information_contract(
                {"basis": {"evidence_blockers": blockers}},
                {"goal_id": self.goal_id, "best_verified_gain": best_gain},
            )
            self.last_minimum_information_contract = min_info
            res["minimum_information_contract"] = min_info
            try:
                led_kw = {"path": self.ledger_path} if self.ledger_path else {}
                gid = ign_ledger.note(
                    f"PENDING_ACQUISITION_OR_EXPERIMENT:{self.goal[:80]}",
                    why=";".join(blockers[:3]),
                    cost=1.0,
                    **led_kw,
                )
                if gid and gid not in self._recorded_gap_ids:
                    self._recorded_gap_ids.append(str(gid))
            except Exception:
                pass
        elif self._recorded_gap_ids:
            try:
                led_kw = {"path": self.ledger_path} if self.ledger_path else {}
                for gid in list(self._recorded_gap_ids):
                    ign_ledger.resolve(gid, helped=True, close=True, **led_kw)
                self._recorded_gap_ids.clear()
            except Exception:
                pass

        res["unexplored_independent_channels"] = rem
        res["observed_evidence_kinds"] = kinds_seen
        res["policy_changing_unprobed_count"] = len(dominating_unprobed)
        res["open_world_guard_closed"] = guard_closed
        return res


def solve_minimax_interval_probe_policy(problem: Mapping[str, Any]) -> dict[str, Any]:
    """Compute exact minimax probe policy over interval-bounded hypotheses via `interval_information_frontier_v1`."""
    return dict(iif.solve(problem))


def run_global_minimal_action_chase(
    goal: str,
    *,
    target: float,
    direction: str = "maximize",
    unit: str = "",
    measure: Callable[[], float | None],
    execute_route: Callable[[Mapping[str, Any], Mapping[str, Any]], Mapping[str, Any]],
    initial_options: Sequence[Mapping[str, Any]] = (),
    channels: Sequence[Mapping[str, Any]] = (),
    channel_fetcher: Callable[[Mapping[str, Any]], Sequence[Mapping[str, Any]]] | None = None,
    min_independent_channels: int = 2,
    min_evidence_kinds: int = 1,
    ledger_path: str | None = None,
    max_rounds: int = 12,
    patience: int = 4,
    experience_state_path: str | None = None,
    flywheel_state_path: str | None = None,
    coverage_receipt: Mapping[str, Any] | None = None,
    residual_action_receipt: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute a complete globally-extrapolated, pathology-guarded minimal-action target chase."""
    world = GlobalDiscoveryWorld(
        goal=goal,
        channels=channels,
        channel_fetcher=channel_fetcher,
        coverage_receipt=coverage_receipt,
        residual_action_receipt=residual_action_receipt,
        min_independent_channels=min_independent_channels,
        min_evidence_kinds=min_evidence_kinds,
        ledger_path=ledger_path,
    )

    seeded_options: list[dict[str, Any]] = []
    by_src: dict[tuple[str, str], list[Mapping[str, Any]]] = {}
    for opt in initial_options:
        sid = str(opt.get("source_id") or "seed")
        grp = str(opt.get("upstream_group") or sid)
        by_src.setdefault((sid, grp), []).append(opt)
    for (sid, grp), batch in by_src.items():
        seeded_options.extend(
            world.ingest_observations(batch, source_id=sid, upstream_group=grp, action_id=f"SEED:{sid}")
        )
    # Seed placeholder when starting completely blind (`0` initial options) so completeness_gate runs on Round 0!
    if not seeded_options and (channels or min_independent_channels > 0):
        seeded_options.append(
            {
                "route_id": "__blind_opening_probe__",
                "source_id": None,
                "candidate_authority": "CANDIDATE_ONLY",
                "unexplored_independent_channels": len(world.unprobed_independent_groups()),
            }
        )

    routes_executed: list[str] = []
    suppressed_skipped: list[str] = []

    def _act_globally_optimal(ctx: Mapping[str, Any]) -> Mapping[str, Any]:
        known = [o for o in (ctx.get("known_options") or ctx.get("options") or []) if isinstance(o, Mapping)]
        pre = round0_pathology_precheck(
            goal,
            known,
            experience_state_path=experience_state_path,
            flywheel_state_path=flywheel_state_path,
        )
        for sup in pre["suppressed_routes"]:
            rid = str(sup.get("route_id") or sup.get("id") or "")
            if rid and rid not in suppressed_skipped:
                suppressed_skipped.append(rid)

        ranked = rank_global_minimal_action_routes(
            known,
            goal=goal,
            direction=direction,
            experience_state_path=experience_state_path,
            flywheel_state_path=flywheel_state_path,
        )
        if not ranked:
            return {"status": "NO_VERIFIED_ADMISSIBLE_ROUTE", "error": "NO_VERIFIED_ADMISSIBLE_ROUTE"}

        chosen = ranked[0]
        rid = str(chosen.get("route_id") or chosen.get("id") or "route")
        out = dict(execute_route(chosen, ctx) or {})
        ok = bool(out.get("pass", out.get("ok", True)) and not out.get("error"))
        err_code = str(out.get("error") or ("OK" if ok else "ROUTE_EXECUTION_FAILED"))
        structural = bool(
            out.get("structural_failure")
            or any(t in err_code.upper() for t in ("BINARY_ABSENT", "SOURCE_UNSUPPORTED", "NO_SUCH_ADAPTER", "MISSING_EXECUTABLE"))
        )
        exp_kw = {"path": experience_state_path} if experience_state_path else {}
        exp.record(rid, err_code, ok, structural=structural, **exp_kw)
        if ok:
            routes_executed.append(rid)
            exp.teach_resolution(goal, rid, **exp_kw)
            out.setdefault("procedure", rid)
            out.setdefault("status", "OK")
        return out

    chase_res = tdriver.run(
        goal=goal,
        target=target,
        direction=direction,
        unit=unit,
        measure=measure,
        act=_act_globally_optimal,
        max_rounds=max_rounds,
        patience=patience,
        context={"options": seeded_options},
        flywheel_state_path=flywheel_state_path,
        options_provider=world.options_provider,
        completeness_gate=world.completeness_gate,
    )
    return {
        "schema": SCHEMA,
        "status": chase_res["status"],
        "pass": chase_res["pass"],
        "goal_reached": chase_res["goal_reached"],
        "chase": chase_res,
        "routes_executed": routes_executed,
        "suppressed_routes_skipped_before_act": suppressed_skipped,
        "probed_sources": sorted(world._probed_source_ids),
        "observed_evidence_kinds": world.observed_evidence_kinds(),
        "minimum_information_contract": world.last_minimum_information_contract,
        "consumed_upstream_groups": list(world.state.get("consumed_upstream_groups") or []),
        "k3_external_llm_calls": 0,
    }


def discover_mechanism_actively(
    oracle: Callable[[Mapping[str, float]], float] | None = None,
    *,
    bounds: Mapping[str, tuple[float, float]] | None = None,
    rows: Sequence[Mapping[str, Any]] | None = None,
    target: str = "y",
    inputs: Sequence[str] | None = None,
    max_discriminator_rounds: int = 6,
    holdout_points: Sequence[Mapping[str, float]] | None = None,
) -> dict[str, Any]:
    """Actively probe an unknown black-box law via `h100_zero_learned_mechanism_synthesizer_v1` until unique, then extrapolate (`K3 = 0`)."""
    from canonical.runtime import h100_zero_learned_mechanism_synthesizer_v1 as h100

    observed_rows: list[dict[str, Any]] = [dict(r) for r in (rows or []) if isinstance(r, Mapping)]
    initial_probe_meta: dict[str, Any] | None = None
    discriminator_trace: list[dict[str, Any]] = []

    if oracle is not None and bounds is not None and len(observed_rows) < 5:
        initial_probe_meta = h100.design_initial_probes(dict(bounds))
        for pt in initial_probe_meta.get("points") or []:
            pt_d = {str(k): float(v) for k, v in pt.items()}
            observed_rows.append({**pt_d, str(target): float(oracle(pt_d))})

    def _exact_laws(cands: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
        exact = [dict(c) for c in cands if float(c.get("nrmse", 1.0)) <= 1e-5]
        return exact

    disc_res = h100.discover(observed_rows, target=str(target), inputs=list(inputs) if inputs else None)
    all_candidates = list(disc_res.get("candidates") or [])
    viable = _exact_laws(all_candidates) or [dict(c) for c in all_candidates[:2]]

    rounds_run = 0
    while (
        oracle is not None
        and len(viable) > 1
        and rounds_run < max(0, int(max_discriminator_rounds))
    ):
        prop = h100.propose_discriminator(viable, observed_rows)
        if prop.get("status") != "DISCRIMINATOR_FOUND" or not isinstance(prop.get("point"), Mapping):
            break
        probe_pt = {str(k): float(v) for k, v in prop["point"].items()}
        y_val = float(oracle(probe_pt))
        observed_rows.append({**probe_pt, str(target): y_val})
        rounds_run += 1
        disc_res = h100.discover(observed_rows, target=str(target), inputs=list(inputs) if inputs else None)
        all_candidates = list(disc_res.get("candidates") or [])
        viable = _exact_laws(all_candidates)
        discriminator_trace.append(
            {
                "round": rounds_run,
                "probe_point": probe_pt,
                "observed_target": y_val,
                "disagreement_before": prop.get("disagreement"),
                "remaining_exact_candidates": len(viable),
            }
        )

    exact_final = _exact_laws(all_candidates)
    best_cand = exact_final[0] if exact_final else (all_candidates[0] if all_candidates else None)
    predictions: list[dict[str, Any]] = []
    if best_cand is not None and holdout_points:
        for h_pt in holdout_points:
            pt_clean = {str(k): float(v) for k, v in h_pt.items()}
            predictions.append(
                {
                    "point": pt_clean,
                    "predicted": float(h100.predict(best_cand, pt_clean)),
                }
            )

    return {
        "schema": SCHEMA + "/active_mechanism_discovery",
        "pass": len(exact_final) >= 1,
        "unique": len(exact_final) == 1,
        "status": "UNIQUE_MECHANISM_IDENTIFIED" if len(exact_final) == 1 else ("CANDIDATES_IDENTIFIED" if exact_final else "NO_MECHANISM_FOUND"),
        "best_candidate": best_cand,
        "exact_candidate_count": len(exact_final),
        "candidate_count": len(all_candidates),
        "candidates": exact_final or all_candidates,
        "observations_used": len(observed_rows),
        "discriminator_rounds": rounds_run,
        "discriminator_trace": discriminator_trace,
        "predictions": predictions,
        "k3_external_llm_calls": 0,
    }


def induce_and_predict_grid_delta_rule(
    training_pairs: Sequence[Mapping[str, Sequence[Sequence[int]]]],
    *,
    test_grids: Sequence[Sequence[Sequence[int]]] | None = None,
) -> dict[str, Any]:
    """Induce exact 2D spatial/grid state-transition laws via `grid_delta_rule_inducer_v2` and predict novel grids (`K3 = 0`)."""
    from canonical.runtime import grid_delta_rule_inducer_v2 as gdr

    induced = gdr.induce(list(training_pairs))
    ok = bool(
        induced.get("status") == "VERIFIED_FACTORIZED_RULE_OPTIONS"
        and induced.get("training_full_replay_verified") is True
    )
    preds: list[dict[str, Any]] = []
    if ok and test_grids:
        for g in test_grids:
            p_out = gdr.predict(induced, g)
            preds.append(dict(p_out))
            if p_out.get("status") != "PREDICTED":
                ok = False
    return {
        "schema": SCHEMA + "/grid_delta_induction",
        "pass": ok,
        "status": induced.get("status"),
        "induced": induced,
        "predictions": preds,
        "k3_external_llm_calls": 0,
    }


def evaluate_semantic_ambiguity_and_sense(
    problem: Mapping[str, Any],
    *,
    concept_identity_verifier: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None = None,
    terminal_signature_verifier: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None = None,
    relation_edge_verifier: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None = None,
    authority_verifier: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None = None,
    evidence_verifier: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None = None,
) -> dict[str, Any]:
    """Lossless semantic ambiguity, OEWN release-relative sense control, and scoped relation resolution (`K3 = 0`)."""
    if "sense_universe" in problem and "decision_manifest" in problem:
        from canonical.runtime import oewn_decision_sense_control_v1 as oewn_ctrl

        out = dict(
            oewn_ctrl.resolve(
                sense_universe=problem["sense_universe"],
                decision_manifest=problem["decision_manifest"],
                authority_receipt=problem.get("authority_receipt"),
                authority_verifier=authority_verifier,
                evidence_receipts=problem.get("evidence_receipts"),
                evidence_verifier=evidence_verifier,
                ambiguity_owner=str(problem.get("ambiguity_owner") or "SYSTEM_MODEL"),
            )
        )
        out["control_organ"] = "oewn_decision_sense_control_v1"
        out["k3_external_llm_calls"] = 0
        return out

    if "left_id" in problem and "right_id" in problem:
        from canonical.runtime import semantic_relation_control_v2 as rel_ctrl

        out = dict(
            rel_ctrl.resolve(
                problem,
                concept_identity_verifier=concept_identity_verifier,
                terminal_signature_verifier=terminal_signature_verifier,
                relation_edge_verifier=relation_edge_verifier,
            )
        )
        out["control_organ"] = "semantic_relation_control_v2"
        out["k3_external_llm_calls"] = 0
        return out

    from canonical.runtime import semantic_ambiguity_control_v1 as amb_ctrl

    out = dict(amb_ctrl.decide(problem))
    out["control_organ"] = "semantic_ambiguity_control_v1"
    out["k3_external_llm_calls"] = 0
    return out


def solve_exact_rational_polytope(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Exact `Fraction`-bounded linear parameter polytope & query interval extrapolation (`K3 = 0`)."""
    from canonical.runtime import exact_linear_parameter_polytope_v1 as poly

    out = dict(poly.solve(payload))
    out["k3_external_llm_calls"] = 0
    return out


def evaluate_cross_document_semantic_lattice(
    problem: Mapping[str, Any],
    *,
    relation_verifier: Callable[[Mapping[str, Any]], Mapping[str, Any] | None] | None = None,
) -> dict[str, Any]:
    """Multi-document temporal/supersession effect lattice closure (`cross_document_effect_semantic_lattice_v8`, `K3 = 0`)."""
    from canonical.runtime import cross_document_effect_semantic_lattice_v8 as lattice_v8

    out = dict(lattice_v8.evaluate(problem, relation_verifier=relation_verifier))
    out["k3_external_llm_calls"] = 0
    return out

