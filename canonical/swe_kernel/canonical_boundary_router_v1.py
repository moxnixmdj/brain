#!/usr/bin/env python3
"""Canonical BoundaryRouter & Compounding Closed-Loop Orchestrator (`0I`).

Ties together all five canonical front-door spines into one zero-waste compounding
execution loop wired into ``brain_unified_model_v1``:

  - Tier 0 (<5ms, $0): O(1) Verified Skill / Crystallized Rewrite Recall (`0G`)
  - Tier 1 (Zero-Model, $0): Deterministic Execution-Verified Spines
      * `0D` Polyglot SWE Spine (`canonical_swe_spine_v1`)
      * `0E` Environment Discovery & Conflict-Aware Automata (`canonical_env_discovery_spine_v1`)
      * `0F` Speculative CoW Sandbox & Code-over-GUI (`canonical_cu_sandbox_spine_v1`)
      * `0H` Dual-Channel Oracle & Formal Vericoding (`canonical_oracle_vericoding_spine_v1`)
  - Tier 2 (Optional Plug-In Untrusted Proposer):
      Invoked ONLY when Tiers 0–1 fail closed and a caller explicitly supplies an
      ``untrusted_proposer``. Every proposal is filtered through T2 CDCL negative-space
      nogoods (`0G`) and gated by `0H` dual-channel verification (fail-to-pass +
      input-dependency + goal-negation mutant kill). Any verified Tier-1 or Tier-2 win is
      automatically crystallized into Tier 0 (`0G`) so future analogous tasks hit Tier 0
      with 0 proposer calls.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from canonical.swe_kernel import canonical_cu_sandbox_spine_v1 as cu_spine
from canonical.swe_kernel import canonical_env_discovery_spine_v1 as env_spine
from canonical.swe_kernel import canonical_memory_crystallizer_v1 as mem_spine
from canonical.swe_kernel import canonical_oracle_vericoding_spine_v1 as oracle_spine
from canonical.swe_kernel import canonical_swe_spine_v1 as swe_spine

SCHEMA = "PROJECT_BRAIN_CANONICAL_BOUNDARY_ROUTER_V1"
NON_CLAIMS = (
    "no_capability_credit",
    "no_ownership_credit",
    "no_terminal_credit",
    "zero_model_unless_caller_supplies_proposer",
)


class BoundaryRouter:
    """Tier-0 -> Tier-1 -> Tier-2 compounding router backed by ``VerificationFirstMemoryBus``."""

    def __init__(self, memory_bus: mem_spine.VerificationFirstMemoryBus | None = None) -> None:
        self.memory_bus = memory_bus if memory_bus is not None else mem_spine.VerificationFirstMemoryBus()
        self.cluster_stats: dict[str, dict[str, int]] = {}

    def _record_cluster(self, cluster: str, *, tier: str, passed: bool) -> None:
        row = self.cluster_stats.setdefault(
            str(cluster),
            {"attempts": 0, "passed": 0, "tier0_hits": 0, "tier1_wins": 0, "tier2_wins": 0},
        )
        row["attempts"] += 1
        if passed:
            row["passed"] += 1
            if tier == "TIER_0_CRYSTALLIZED_REFLEX":
                row["tier0_hits"] += 1
            elif tier.startswith("TIER_1"):
                row["tier1_wins"] += 1
            elif tier.startswith("TIER_2"):
                row["tier2_wins"] += 1

    def route_swe_repair(
        self,
        repo_root: str | Path,
        *,
        target_rel: str,
        test_file: str,
        cluster: str = "swe_python",
        issue_text: str = "",
        regression_tests: Sequence[str] = (),
        untrusted_proposer: Callable[[Mapping[str, Any]], Sequence[str]] | None = None,
        timeout_s: float = 25.0,
    ) -> dict[str, Any]:
        """Route a Python SWE repair task across Tier 0 -> Tier 1 (`0D`) -> Tier 2 (gated by `0H`),
        crystallizing every verified repair back into Tier 0 (`0G`).
        """
        t0 = time.perf_counter()
        root = Path(repo_root).resolve()
        target_path = root / target_rel
        before_source = target_path.read_text(encoding="utf-8")
        episode_id = f"ep_{cluster}_{root.name}_{target_rel}"

        # ------------------------------------------------------------------ TIER 0 (<5ms reflex)
        tier0_candidates = self.memory_bus.apply_crystallized_code_skills(before_source, trigger_key=cluster)
        for cand in tier0_candidates:
            patched = cand["patched_source"]
            if self.memory_bus.is_pruned(patched[:400], domain=cluster, context_sig=target_rel):
                continue
            audit = oracle_spine.audit_patch_and_oracle(
                root,
                target_rel=target_rel,
                before_source=before_source,
                after_source=patched,
                test_file=test_file,
                timeout_s=timeout_s,
            )
            if audit["pass"]:
                target_path.write_text(patched, encoding="utf-8")
                self.memory_bus.record_causal_step(
                    episode_id=episode_id,
                    step_idx=0,
                    pre_state=f"bug:{target_rel}",
                    action="TIER0_APPLY_CRYSTALLIZED_SKILL",
                    exact_args={"skill_id": cand["skill_id"], "target_rel": target_rel},
                    effect={"oracle_pass": True, "mutants_killed": audit["channels"]["goal_negation_mutants_killed"]},
                    post_state=f"fixed:{target_rel}",
                    provenance="TIER_0",
                )
                self._record_cluster(cluster, tier="TIER_0_CRYSTALLIZED_REFLEX", passed=True)
                return {
                    "schema": SCHEMA,
                    "pass": True,
                    "status": "PASS__TIER0_CRYSTALLIZED_REFLEX",
                    "tier_used": "TIER_0_CRYSTALLIZED_REFLEX",
                    "proposer_calls": 0,
                    "skill_id": cand["skill_id"],
                    "oracle_audit": audit,
                    "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
                }
            self.memory_bus.record_conflict(
                patched[:400],
                reason=";".join(audit.get("reasons") or ["TIER0_ORACLE_FAILED"]),
                domain=cluster,
                context_sig=target_rel,
            )

        # ------------------------------------------------------------------ TIER 1 (`0D` zero-model SWE spine)
        swe_res = swe_spine.solve_repository_task(
            root,
            test_file=test_file,
            regression_tests=regression_tests,
            issue_text=issue_text,
            language="python",
            timeout_s=timeout_s,
            keep_patch_applied=True,
        )
        if swe_res.get("solved") is True:
            after_source = target_path.read_text(encoding="utf-8")
            audit = oracle_spine.audit_patch_and_oracle(
                root,
                target_rel=target_rel,
                before_source=before_source,
                after_source=after_source,
                test_file=test_file,
                timeout_s=timeout_s,
            )
            if audit["pass"]:
                sk = self.memory_bus.crystallize_code_repair(
                    before_source=before_source,
                    after_source=after_source,
                    trigger_key=cluster,
                    error_class=cluster,
                    provenance_episode_id=episode_id,
                )
                self.memory_bus.record_causal_step(
                    episode_id=episode_id,
                    step_idx=1,
                    pre_state=f"bug:{target_rel}",
                    action="TIER1_ZERO_MODEL_SWE_SPINE",
                    exact_args={"target_rel": target_rel, "test_file": test_file},
                    effect={"crystallized_skill_id": sk.skill_id},
                    post_state=f"fixed:{target_rel}",
                    provenance="TIER_1",
                )
                self._record_cluster(cluster, tier="TIER_1_ZERO_MODEL_SPINE", passed=True)
                return {
                    "schema": SCHEMA,
                    "pass": True,
                    "status": "PASS__TIER1_ZERO_MODEL_AND_CRYSTALLIZED",
                    "tier_used": "TIER_1_ZERO_MODEL_SPINE",
                    "proposer_calls": 0,
                    "crystallized_skill_id": sk.skill_id,
                    "swe_result": swe_res,
                    "oracle_audit": audit,
                    "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
                }
            # Restore original file if `0H` dual-channel audit caught a vacuous oracle or cheat
            target_path.write_text(before_source, encoding="utf-8")
            self.memory_bus.record_conflict(
                after_source[:400],
                reason=";".join(audit.get("reasons") or ["TIER1_REJECTED_BY_0H"]),
                domain=cluster,
                context_sig=target_rel,
            )

        # ------------------------------------------------------------------ TIER 2 (Optional Untrusted Proposer gated by `0H`)
        proposer_calls = 0
        rejected_proposals: list[dict[str, Any]] = []
        if untrusted_proposer is not None:
            proposer_calls = 1
            active_nogoods = [
                c.as_dict()
                for c in self.memory_bus.conflict_clauses.values()
                if not c.retracted and c.domain == cluster
            ]
            context = {
                "repo_root": str(root),
                "target_rel": target_rel,
                "before_source": before_source,
                "test_file": test_file,
                "issue_text": issue_text,
                "active_conflict_clauses": active_nogoods,
            }
            proposals = list(untrusted_proposer(context) or ())
            for idx, prop_src in enumerate(proposals):
                prop_text = str(prop_src)
                if self.memory_bus.is_pruned(prop_text[:400], domain=cluster, context_sig=target_rel):
                    rejected_proposals.append({"idx": idx, "reason": "PRUNED_BY_CDCL_NOGOOD"})
                    continue
                audit = oracle_spine.audit_patch_and_oracle(
                    root,
                    target_rel=target_rel,
                    before_source=before_source,
                    after_source=prop_text,
                    test_file=test_file,
                    timeout_s=timeout_s,
                )
                if audit["pass"]:
                    target_path.write_text(prop_text, encoding="utf-8")
                    sk = self.memory_bus.crystallize_code_repair(
                        before_source=before_source,
                        after_source=prop_text,
                        trigger_key=cluster,
                        error_class=cluster,
                        provenance_episode_id=episode_id,
                    )
                    self.memory_bus.record_causal_step(
                        episode_id=episode_id,
                        step_idx=2,
                        pre_state=f"bug:{target_rel}",
                        action="TIER2_PROPOSER_VERIFIED_BY_0H",
                        exact_args={"proposal_idx": idx, "target_rel": target_rel},
                        effect={"crystallized_skill_id": sk.skill_id},
                        post_state=f"fixed:{target_rel}",
                        provenance="TIER_2",
                    )
                    self._record_cluster(cluster, tier="TIER_2_PROPOSER_VERIFIED", passed=True)
                    return {
                        "schema": SCHEMA,
                        "pass": True,
                        "status": "PASS__TIER2_VERIFIED_AND_CRYSTALLIZED_TO_TIER0",
                        "tier_used": "TIER_2_PROPOSER_VERIFIED",
                        "proposer_calls": proposer_calls,
                        "crystallized_skill_id": sk.skill_id,
                        "rejected_proposals": rejected_proposals,
                        "oracle_audit": audit,
                        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
                    }
                # Compile rejected proposal into T2 CDCL negative-space nogood!
                reasons = audit.get("reasons") or ["PROPOSAL_REJECTED_BY_0H"]
                self.memory_bus.record_conflict(
                    prop_text[:400],
                    reason=";".join(reasons),
                    domain=cluster,
                    context_sig=target_rel,
                )
                rejected_proposals.append({"idx": idx, "reasons": reasons})

        self._record_cluster(cluster, tier="UNSOLVED", passed=False)
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED__BOUNDARY_ROUTER_UNSOLVED",
            "tier_used": "NONE",
            "proposer_calls": proposer_calls,
            "rejected_proposals": rejected_proposals,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }

    def route_env_goal(
        self,
        blackbox_env: Any,
        *,
        goal_predicate: Callable[[Any], bool],
        cluster: str = "env_automaton",
        trigger_key: str = "default_env_goal",
        actions: Sequence[str] | None = None,
        max_states: int = 48,
        max_depth: int = 8,
    ) -> dict[str, Any]:
        """Route an unknown interactive environment goal across Tier 0 (cached macro) -> Tier 1 (`0E` C3AL),
        auto-crystallizing the learned plan back into Tier 0.
        """
        t0 = time.perf_counter()
        # Tier 0: replay active crystallized action macro directly!
        for sk in self.memory_bus.lookup_tier0_skills(trigger_key):
            plan = list(sk["payload"].get("actions") or ())
            if not plan:
                continue
            obs = blackbox_env.reset()
            ok_replay = True
            for act in plan:
                raw = blackbox_env.step(act)
                if isinstance(raw, Mapping):
                    obs = raw.get("obs", raw.get("observation", raw))
                    if raw.get("refused"):
                        ok_replay = False
                        break
                elif isinstance(raw, tuple) and len(raw) >= 2:
                    obs = raw[0]
                    if raw[1]:
                        ok_replay = False
                        break
                else:
                    obs = raw
            if ok_replay and goal_predicate(obs):
                self._record_cluster(cluster, tier="TIER_0_CRYSTALLIZED_REFLEX", passed=True)
                return {
                    "schema": SCHEMA,
                    "pass": True,
                    "status": "PASS__TIER0_ENV_MACRO_REPLAYED",
                    "tier_used": "TIER_0_CRYSTALLIZED_REFLEX",
                    "skill_id": sk["skill_id"],
                    "queries_executed": len(plan),
                    "plan": plan,
                    "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
                }
            # Macro became stale (e.g., environment drifted!) -> forget stale macro in O(1)!
            self.memory_bus.forget_skill(sk["skill_id"], reason="STALE_ENV_MACRO_ON_REPLAY")

        # Tier 1: run `0E` ConflictAwareMealyLearner to discover live physics & synthesize plan
        disc = env_spine.discover_environment(
            blackbox_env=blackbox_env,
            goal_predicate=goal_predicate,
            actions=actions,
            max_states=max_states,
            max_depth=max_depth,
        )
        if disc.get("pass") is True and disc.get("automaton", {}).get("goal_prefix") is not None:
            plan = list(disc["automaton"]["goal_prefix"])
            sk = self.memory_bus.crystallize_action_macro(
                trigger_key=trigger_key,
                actions=plan,
                provenance_episode_id=f"ep_env_{trigger_key}",
            )
            self._record_cluster(cluster, tier="TIER_1_ENV_C3AL", passed=True)
            return {
                "schema": SCHEMA,
                "pass": True,
                "status": "PASS__TIER1_ENV_LEARNED_AND_CRYSTALLIZED",
                "tier_used": "TIER_1_ENV_C3AL",
                "crystallized_skill_id": sk.skill_id,
                "queries_executed": disc["automaton"]["queries_executed"],
                "plan": plan,
                "discovery": disc,
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            }

        self._record_cluster(cluster, tier="UNSOLVED", passed=False)
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED__ENV_GOAL_UNSOLVED",
            "tier_used": "NONE",
            "discovery": disc,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }

    def route_cu_task(self, **kwargs: Any) -> dict[str, Any]:
        """Delegate computer-use / speculative CoW tasks to `0F` and record working frames in `0G`."""
        res = cu_spine.execute_speculative_computer_task(**kwargs)
        self.memory_bus.push_working_frame(
            f"cu_{len(self.memory_bus.working_frames)}",
            {"route_selected": res.get("route_selected"), "pass": res.get("pass")},
        )
        return res

    def status_summary(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "memory": self.memory_bus.stats(),
            "cluster_stats": dict(self.cluster_stats),
        }
