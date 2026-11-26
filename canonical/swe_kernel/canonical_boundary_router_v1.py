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

import importlib
import time
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


class _LazyModule:
    """Zero-overhead lazy module proxy (Elon's Law: delete cold-start import tax)."""

    __slots__ = ("_mod_name", "_loaded")

    def __init__(self, mod_name: str) -> None:
        object.__setattr__(self, "_mod_name", mod_name)
        object.__setattr__(self, "_loaded", None)

    def _resolve(self) -> Any:
        mod = object.__getattribute__(self, "_loaded")
        if mod is None:
            mod = importlib.import_module(object.__getattribute__(self, "_mod_name"))
            object.__setattr__(self, "_loaded", mod)
        return mod

    def __getattr__(self, item: str) -> Any:
        return getattr(self._resolve(), item)


composer_route = _LazyModule("canonical.runtime.composer_route_v1")
harvested_rt = _LazyModule("canonical.runtime.harvested_capability_runtime_v1")
federated_rt = _LazyModule("canonical.runtime.unified_hidden_capability_federation_v1")
cu_spine = _LazyModule("canonical.swe_kernel.canonical_cu_sandbox_spine_v1")
env_spine = _LazyModule("canonical.swe_kernel.canonical_env_discovery_spine_v1")
mem_spine = _LazyModule("canonical.swe_kernel.canonical_memory_crystallizer_v1")
oracle_spine = _LazyModule("canonical.swe_kernel.canonical_oracle_vericoding_spine_v1")
swe_spine = _LazyModule("canonical.swe_kernel.canonical_swe_spine_v1")

SCHEMA = "PROJECT_BRAIN_CANONICAL_BOUNDARY_ROUTER_V1"
NON_CLAIMS = (
    "no_capability_credit",
    "no_ownership_credit",
    "no_terminal_credit",
    "zero_model_unless_caller_supplies_proposer",
)


class BoundaryRouter:
    """Tier-0 -> Tier-1 -> Tier-2 compounding router backed by ``VerificationFirstMemoryBus``."""

    def __init__(self, memory_bus: Any = None) -> None:
        self._memory_bus: Any = memory_bus
        self.cluster_stats: dict[str, dict[str, int]] = {}

    @property
    def memory_bus(self) -> Any:
        if self._memory_bus is None:
            self._memory_bus = mem_spine.VerificationFirstMemoryBus()
        return self._memory_bus

    @memory_bus.setter
    def memory_bus(self, bus: Any) -> None:
        self._memory_bus = bus

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
            failing_demands = oracle_spine.extract_failing_run_demands(before_source)
            context = {
                "repo_root": str(root),
                "target_rel": target_rel,
                "before_source": before_source,
                "test_file": test_file,
                "issue_text": issue_text,
                "active_conflict_clauses": active_nogoods,
                "failing_run_decision_sites": failing_demands.get("sites", [])[:24],
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

    def route_typed_chain(
        self,
        goal: str,
        *,
        seed: Sequence[str] | None = None,
        max_candidates: int = 6,
        cwd: str | Path | None = None,
        cluster: str = "typed_chain",
    ) -> dict[str, Any]:
        """Route a natural-language goal to a typed capability chain (`composer_route_v1`)
        with Tier-0 chain crystallization in `0G`.
        """
        t0 = time.perf_counter()
        trigger = f"chain:{goal.strip().lower()[:120]}"
        for sk in self.memory_bus.lookup_tier0_skills(trigger):
            chain = list(sk["payload"].get("actions") or ())
            if chain:
                self._record_cluster(cluster, tier="TIER_0_CRYSTALLIZED_REFLEX", passed=True)
                return {
                    "schema": SCHEMA,
                    "pass": True,
                    "status": "PASS__TIER0_TYPED_CHAIN_RECALLED",
                    "tier_used": "TIER_0_CRYSTALLIZED_REFLEX",
                    "skill_id": sk["skill_id"],
                    "chain": chain,
                    "goal": goal,
                    "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
                }

        refusal = composer_route.stated_command_refusal(goal)
        routed = composer_route.route(
            goal,
            seed=seed,
            max_candidates=max_candidates,
            cwd=cwd,
        )
        chain = list(routed.get("chain") or ())
        ok = bool(chain) and str(routed.get("status") or "").startswith("PASS")
        sk_id = None
        if ok:
            sk = self.memory_bus.crystallize_action_macro(
                trigger_key=trigger,
                actions=chain,
                provenance_episode_id=f"ep_chain_{len(self.memory_bus.skills)}",
            )
            sk_id = sk.skill_id
            self.memory_bus.record_causal_step(
                episode_id=sk.provenance_episode_id,
                step_idx=0,
                pre_state=f"goal:{goal[:80]}",
                action="COMPOSER_ROUTE_TYPED_CHAIN",
                exact_args={"goal": goal, "seed": list(seed or ())},
                effect={"chain": chain, "token": routed.get("token")},
                post_state=f"chain:{'->'.join(chain)}",
                provenance="TIER_1",
            )
            self._record_cluster(cluster, tier="TIER_1_COMPOSER_ROUTE", passed=True)
        else:
            self._record_cluster(cluster, tier="UNSOLVED", passed=False)
        return {
            "schema": SCHEMA,
            "pass": ok,
            "status": "PASS__TYPED_CHAIN_ROUTED_AND_CRYSTALLIZED" if ok else "FAIL_CLOSED__TYPED_CHAIN_UNROUTED",
            "tier_used": "TIER_1_COMPOSER_ROUTE" if ok else "NONE",
            "goal": goal,
            "chain": chain,
            "token": routed.get("token"),
            "refusal": refusal or routed.get("refusal"),
            "crystallized_skill_id": sk_id,
            "composer_result": routed,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }

    def route_harvested_surface(
        self,
        *,
        capability_id: str = "",
        path: str = "",
        args: Mapping[str, Any] | None = None,
        adversarial_args: Mapping[str, Any] | None = None,
        receipt: bool = False,
        root: str | Path | None = None,
        cluster: str = "harvested_surface",
    ) -> dict[str, Any]:
        """Execute a discovered-but-unadmitted harvested surface via `harvested_capability_runtime_v1`
        with optional `0H` adversarial falsification check. NEVER promotes or claims admission.
        """
        t0 = time.perf_counter()
        if adversarial_args is not None and not receipt:
            audited = oracle_spine.audit_harvested_surface_with_falsification(
                capability_id,
                path=path,
                probe_args=args,
                adversarial_args=adversarial_args,
                root=root,
            )
            res = audited["positive_probe"]
            ok = bool(audited["pass"])
            audit_payload: dict[str, Any] | None = audited
        else:
            res = harvested_rt.run(
                {
                    "capability_id": capability_id,
                    "path": path,
                    "args": dict(args or {}),
                    "receipt": bool(receipt),
                },
                root=root,
            )
            ok = bool(res.get("executed") is True)
            audit_payload = None

        self.memory_bus.record_causal_step(
            episode_id=f"ep_harvested_{capability_id or path}",
            step_idx=0,
            pre_state=f"surface:{capability_id or path}",
            action="EXECUTE_HARVESTED_SURFACE",
            exact_args={"capability_id": capability_id, "path": path, "receipt": bool(receipt)},
            effect={"executed": ok, "admitted": False, "result_sha256": res.get("result_sha256")},
            post_state=f"harvested_executed:{ok}",
            refused=not ok,
            provenance="TIER_1_HARVESTED_UNADMITTED",
        )
        self._record_cluster(cluster, tier="TIER_1_HARVESTED_UNADMITTED" if ok else "UNSOLVED", passed=ok)
        return {
            "schema": SCHEMA,
            "pass": ok,
            "status": "PASS__HARVESTED_SURFACE_EXECUTED_UNADMITTED" if ok else "FAIL_CLOSED__HARVESTED_SURFACE_REFUSED",
            "tier_used": "TIER_1_HARVESTED_UNADMITTED" if ok else "NONE",
            "admitted": False,
            "admission": "NOT_ADMITTED",
            "harvested_result": res,
            "falsification_audit": audit_payload,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }

    def route_version_space_task(
        self,
        task_id: str,
        observation: Mapping[str, Any],
        *,
        training_traces: Sequence[Sequence[tuple[Mapping[str, Any], str]]] = (),
        abstain_on_disagreement: bool = True,
        check_contract: bool = True,
        cluster: str = "version_space_skill",
    ) -> dict[str, Any]:
        """Selective procedural abstraction router: induces/queries `0G` Version-Space skill,
        abstains cleanly on hypothesis disagreement, verifies action against `0H` instruction
        contract when available, and surfaces `0E` aimed-action fallbacks.
        """
        t0 = time.perf_counter()
        if training_traces:
            self.memory_bus.induce_version_space_skill(task_id, training_traces)
        q = self.memory_bus.query_version_space_or_abstain(
            observation,
            task_id=task_id,
            abstain_on_disagreement=abstain_on_disagreement,
        )
        decision = q["decision"]
        action = q.get("action")
        contract_res = None
        if decision == "ACT" and check_contract and observation.get("utterance"):
            contract_res = oracle_spine.compile_and_check_instruction_contract(
                str(observation.get("utterance") or ""),
                observation,
                trace=[(observation, str(action))],
            )
            if contract_res.get("refusal") is None and contract_res.get("check") is not None:
                if str(contract_res["check"].get("verdict") or "").upper() == "FAIL":
                    decision = "ABSTAIN"
                    q["reason"] = "CONTRACT_REJECTED_VERSION_SPACE_ACTION"
                    action = None

        aimed_fallback = None
        if decision == "ABSTAIN":
            aimed_fallback = env_spine.derive_aimed_actions(observation)

        acted = decision == "ACT" and action is not None
        self._record_cluster(cluster, tier="TIER_0_CRYSTALLIZED_REFLEX" if acted else "UNSOLVED", passed=acted)
        return {
            "schema": SCHEMA,
            "pass": acted,
            "decision": decision,
            "status": "PASS__VERSION_SPACE_ACTION_VERIFIED" if acted else "PASS_ABSTAIN__VERSION_SPACE_ABSTAINED",
            "tier_used": "TIER_0_CRYSTALLIZED_REFLEX" if acted else "ABSTAIN",
            "task_id": task_id,
            "action": action,
            "reason": q.get("reason"),
            "disagreement": q.get("disagreement"),
            "contract_check": contract_res,
            "aimed_action_fallback": aimed_fallback,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }

    def route_register_env_goal(
        self,
        register_env: Any,
        *,
        actions: Sequence[str],
        parameterized_actions: Sequence[str] = (),
        goal_predicate: Callable[[Any], bool],
        trigger_key: str = "register_env_goal",
        cluster: str = "register_automaton",
        max_depth: int = 6,
        max_queries: int = 250,
    ) -> dict[str, Any]:
        """Route parameterized data-register environments across Tier-0 symbolic replay -> Tier-1 `0E` RegisterGuardAutomatonLearner."""
        t0 = time.perf_counter()
        for sk in self.memory_bus.lookup_tier0_skills(trigger_key):
            sym_plan = sk["payload"].get("actions") or []
            if sym_plan and isinstance(sym_plan[0], (list, tuple)):
                replay = env_spine.RegisterGuardAutomatonLearner.replay_symbolic_plan(
                    register_env, sym_plan, goal_predicate=goal_predicate
                )
                if replay.get("pass"):
                    self._record_cluster(cluster, tier="TIER_0_CRYSTALLIZED_REFLEX", passed=True)
                    return {
                        "schema": SCHEMA,
                        "pass": True,
                        "status": "PASS__TIER0_REGISTER_PLAN_REPLAYED",
                        "tier_used": "TIER_0_CRYSTALLIZED_REFLEX",
                        "skill_id": sk["skill_id"],
                        "symbolic_plan": sym_plan,
                        "replay": replay,
                        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
                    }
                self.memory_bus.forget_skill(sk["skill_id"], reason="STALE_REGISTER_PLAN_ON_REPLAY")

        disc = env_spine.discover_environment(
            register_env=register_env,
            actions=actions,
            parameterized_actions=parameterized_actions,
            goal_predicate=goal_predicate,
            max_depth=max_depth,
            max_queries=max_queries,
        )
        ra = disc.get("register_automaton") or {}
        if disc.get("pass") and ra.get("symbolic_goal_plan") is not None:
            sym_plan = ra["symbolic_goal_plan"]
            sk = self.memory_bus.crystallize_action_macro(
                trigger_key=trigger_key,
                actions=sym_plan,
                provenance_episode_id=f"ep_reg_{trigger_key}",
            )
            self._record_cluster(cluster, tier="TIER_1_REGISTER_AUTOMATON", passed=True)
            return {
                "schema": SCHEMA,
                "pass": True,
                "status": "PASS__TIER1_REGISTER_AUTOMATON_LEARNED_AND_CRYSTALLIZED",
                "tier_used": "TIER_1_REGISTER_AUTOMATON",
                "crystallized_skill_id": sk.skill_id,
                "symbolic_plan": sym_plan,
                "register_automaton": ra,
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            }

        self._record_cluster(cluster, tier="UNSOLVED", passed=False)
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED__REGISTER_ENV_UNSOLVED",
            "tier_used": "NONE",
            "discovery": disc,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }

    def catalog_federated_engines(self, *, domain: str | None = None) -> dict[str, Any]:
        """Return the catalog of all 58 federated kernel engines (`unified_hidden_capability_federation_v1`)."""
        return federated_rt.catalog_federated_engines(domain=domain)

    def route_federated_engine(
        self,
        mode: str,
        inputs: Mapping[str, Any] | None = None,
        *,
        goal: str = "",
        cluster: str = "federated_engine",
    ) -> dict[str, Any]:
        """Dispatch directly into any of the 58 federated hidden kernel engines at K3=0."""
        t0 = time.perf_counter()
        res = federated_rt.run_federated_engine(str(mode), inputs, goal=str(goal))
        status_str = str(res.get("status") or "")
        passed = bool(res.get("pass")) or status_str.startswith("PASS")
        self._record_cluster(cluster, tier="TIER_1_FEDERATED_KERNEL_ENGINE" if passed else "UNSOLVED", passed=passed)
        return {
            "schema": SCHEMA,
            "pass": passed,
            "status": "PASS__FEDERATED_ENGINE_EXECUTED" if passed else (status_str or "FAIL_CLOSED__FEDERATED_ENGINE_FAILED"),
            "tier_used": "TIER_1_FEDERATED_KERNEL_ENGINE" if passed else "NONE",
            "mode": str(mode),
            "result": res,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            "model_calls": 0,
        }

    def route_one_shot_learning(
        self,
        environment_root: str | Path,
        *,
        task_id: str,
        steps: Sequence[tuple[str, str]],
        terminal_outcome: int,
        wrong_actions: Sequence[Sequence[tuple[str, str]]],
        right_command: str,
        skill_id: str | None = None,
        success_states: Sequence[Sequence[str]] = (),
        failure_states: Sequence[Sequence[str]] = (),
        cluster: str = "one_shot_learning",
    ) -> dict[str, Any]:
        """Instant 1-shot learning (`instant_one_shot_learning_v1` + `weights_from_scratch_v1` + `applicability_v1`) via `0G`."""
        t0 = time.perf_counter()
        out = self.memory_bus.one_shot_induce_skill(
            environment_root,
            task_id=task_id,
            steps=steps,
            terminal_outcome=terminal_outcome,
            wrong_actions=wrong_actions,
            right_command=right_command,
            skill_id=skill_id,
            success_states=success_states,
            failure_states=failure_states,
        )
        ok = bool(out.get("pass"))
        self._record_cluster(cluster, tier="TIER_1_ONE_SHOT_INDUCTION" if ok else "UNSOLVED", passed=ok)
        return {
            "schema": SCHEMA,
            "pass": ok,
            "status": "PASS__ONE_SHOT_SKILL_CRYSTALLIZED" if ok else "FAIL_CLOSED__ONE_SHOT_FAILED",
            "tier_used": "TIER_1_ONE_SHOT_INDUCTION" if ok else "NONE",
            "induction": out,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            "model_calls": 0,
        }

    def route_applicability_check(
        self,
        skill_id: str,
        *,
        evidence: Sequence[tuple[Sequence[str], bool]] | None = None,
        state_facts: Sequence[str] | None = None,
        cluster: str = "applicability_boundary",
    ) -> dict[str, Any]:
        """Learn and/or query exact applicability boundaries (`applicability_v1`) with explicit OOD abstention."""
        t0 = time.perf_counter()
        learned = None
        if evidence is not None:
            learned = self.memory_bus.learn_applicability_boundary(skill_id, evidence)
        decision_res = None
        if state_facts is not None:
            decision_res = self.memory_bus.check_skill_applicability(skill_id, state_facts)
        passed = bool((learned and learned.get("pass")) or (decision_res and decision_res.get("decision") == "APPLY"))
        self._record_cluster(cluster, tier="TIER_0_CRYSTALLIZED_REFLEX" if passed else "UNSOLVED", passed=passed)
        return {
            "schema": SCHEMA,
            "pass": passed,
            "status": (
                f"PASS__{decision_res['decision']}"
                if decision_res is not None
                else ("PASS__APPLICABILITY_LEARNED" if learned and learned.get("pass") else "FAIL_CLOSED__APPLICABILITY_GAP")
            ),
            "learned": learned,
            "check": decision_res,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            "model_calls": 0,
        }

    def route_refusal_specification(
        self,
        refusal_text: str,
        *,
        base_argv: Sequence[str] = (),
        files: Sequence[str] = (),
        declared_flags: Sequence[str] = (),
        numeric_flags: Sequence[str] = (),
        paths: Mapping[str, str] | None = None,
        cluster: str = "refusal_spec",
    ) -> dict[str, Any]:
        """Compile a raw tool/OS refusal directly into a typed spec + repaired argv (`0E` × `a_refusal_is_a_specification_v1`)."""
        t0 = time.perf_counter()
        res = env_spine.compile_refusal_specification(
            refusal_text,
            base_argv=base_argv,
            files=files,
            declared_flags=declared_flags,
            numeric_flags=numeric_flags,
            paths=paths,
        )
        ok = bool(res.get("pass"))
        self._record_cluster(cluster, tier="TIER_1_REFUSAL_SPEC" if ok else "UNSOLVED", passed=ok)
        return {
            "schema": SCHEMA,
            "pass": ok,
            "status": res.get("status"),
            "tier_used": "TIER_1_REFUSAL_SPEC" if ok else "NONE",
            "specification": res,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            "model_calls": 0,
        }

    def route_speculative_cow_race(
        self,
        workspace_root: str | Path,
        branches: Sequence[Mapping[str, Any]],
        oracle_fn: Callable[[Path], bool],
        *,
        commit_winner: bool = True,
        cluster: str = "speculative_cow",
    ) -> dict[str, Any]:
        """Run N side-effecting candidate futures in isolated CoW sandboxes (`0F`), committing ONLY a verified winner."""
        t0 = time.perf_counter()
        res = cu_spine.speculative_cow_race(
            workspace_root,
            branches,
            oracle_fn,
            commit_winner=commit_winner,
        )
        ok = bool(res.get("pass"))
        self._record_cluster(cluster, tier="TIER_1_SPECULATIVE_COW" if ok else "UNSOLVED", passed=ok)
        return {
            "schema": SCHEMA,
            "pass": ok,
            "status": res.get("status"),
            "tier_used": "TIER_1_SPECULATIVE_COW" if ok else "NONE",
            "race": res,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            "model_calls": 0,
        }

    def route_four_tier_cu(
        self,
        *,
        direct_command: Sequence[str] | None = None,
        typed_action: Mapping[str, Any] | None = None,
        aimed_observation: Mapping[str, Any] | None = None,
        screen_width: int = 1920,
        screen_height: int = 1080,
        cluster: str = "cu_four_tier",
    ) -> dict[str, Any]:
        """Zero-Pixel-First 4-tier computer-use ladder (`0F`)."""
        t0 = time.perf_counter()
        res = cu_spine.compile_four_tier_cu_action(
            direct_command=direct_command,
            typed_action=typed_action,
            aimed_observation=aimed_observation,
            screen_width=screen_width,
            screen_height=screen_height,
        )
        ok = bool(res.get("pass"))
        self._record_cluster(cluster, tier=str(res.get("tier") or "UNSOLVED"), passed=ok)
        return {
            "schema": SCHEMA,
            "pass": ok,
            "status": "PASS__CU_TIER_COMPILED" if ok else res.get("status"),
            "cu_plan": res,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            "model_calls": 0,
        }

    def route_mutation_admission_gate(
        self,
        source_text: str,
        verifier_fn: Callable[[Mapping[str, Any]], bool],
        *,
        limit: int = 8,
        seed: int = 7,
        min_kill_rate: float = 0.5,
        cluster: str = "mutation_gate",
    ) -> dict[str, Any]:
        """Mutation-as-Admission Gate (`0H` × `mutation_admission_probe_v1`) before skill promotion."""
        t0 = time.perf_counter()
        res = oracle_spine.mutation_admission_gate(
            source_text,
            verifier_fn,
            limit=limit,
            seed=seed,
            min_kill_rate=min_kill_rate,
        )
        ok = bool(res.get("pass"))
        self._record_cluster(cluster, tier="TIER_1_MUTATION_GATE" if ok else "UNSOLVED", passed=ok)
        return {
            "schema": SCHEMA,
            "pass": ok,
            "status": res.get("status"),
            "gate": res,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            "model_calls": 0,
        }

    def route_verified_event_memory(
        self,
        *,
        action: str = "REPLAY",
        op: str = "SET",
        key: str = "",
        value: Any = None,
        source_commit: str = "",
        precondition_guard: Sequence[str] = (),
        validity_window: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Anti-authority-collapse SHA-256 event-sourced memory log (`0G` × `h100_zero_learned_event_memory_v1`)."""
        act = str(action or "REPLAY").upper()
        if act == "APPEND":
            return self.memory_bus.append_verified_event(
                op=op,
                key=key,
                value=value,
                source_commit=source_commit,
                precondition_guard=precondition_guard,
                validity_window=validity_window,
            )
        return self.memory_bus.replay_verified_events()

    def status_summary(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "memory": self.memory_bus.stats(),
            "cluster_stats": dict(self.cluster_stats),
        }
