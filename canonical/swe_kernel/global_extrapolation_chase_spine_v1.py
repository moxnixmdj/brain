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
    ) -> None:
        self.goal = str(goal)
        self.goal_id = "goal:" + hashlib.sha256(self.goal.encode("utf-8")).hexdigest()[:16]
        self.environment_id = str(environment_id)
        self.channels = [dict(c) for c in channels]
        self.channel_fetcher = channel_fetcher
        self.coverage_receipt = coverage_receipt
        self.residual_action_receipt = residual_action_receipt
        self.min_independent_channels = max(1, int(min_independent_channels))
        self.state = grc.new_state()
        self.source_stats: dict[str, dict[str, Any]] = {}
        self._probed_source_ids: set[str] = set()

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
        ranked = plan.get("actions") or []
        if not ranked:
            return []

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
        res["unexplored_independent_channels"] = rem
        res["open_world_guard_closed"] = guard_closed
        return res


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
        "consumed_upstream_groups": list(world.state.get("consumed_upstream_groups") or []),
        "k3_external_llm_calls": 0,
    }
