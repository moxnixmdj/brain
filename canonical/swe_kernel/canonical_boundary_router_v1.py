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

    def __init__(
        self,
        memory_bus: Any = None,
        *,
        memory_bus_factory: Callable[[], Any] | None = None,
    ) -> None:
        self._memory_bus: Any = memory_bus
        self._memory_bus_factory: Callable[[], Any] | None = memory_bus_factory
        self.cluster_stats: dict[str, dict[str, int]] = {}

    @property
    def memory_bus(self) -> Any:
        if self._memory_bus is None:
            if self._memory_bus_factory is not None:
                self._memory_bus = self._memory_bus_factory()
            else:
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
        if self._memory_bus is not None and hasattr(self._memory_bus, "observe_drift"):
            self._memory_bus.observe_drift(f"cluster:{cluster}", bool(passed))

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
        durable_commit: bool = False,
        cluster: str = "speculative_cow",
    ) -> dict[str, Any]:
        """Run N side-effecting candidate futures in isolated CoW sandboxes (`0F`), committing ONLY a verified winner."""
        t0 = time.perf_counter()
        res = cu_spine.speculative_cow_race(
            workspace_root,
            branches,
            oracle_fn,
            commit_winner=commit_winner,
            durable_commit=durable_commit,
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
        webmcp_tool: Mapping[str, Any] | None = None,
        typed_action: Mapping[str, Any] | None = None,
        osworld_v21_state: Mapping[str, Any] | None = None,
        aimed_observation: Mapping[str, Any] | None = None,
        screen_width: int = 1920,
        screen_height: int = 1080,
        cluster: str = "cu_four_tier",
    ) -> dict[str, Any]:
        """Zero-Pixel-First computer-use ladder (`0F` — CLI -> WebMCP -> Typed Surface -> OSWorld v2.1 -> Aimed Geometry)."""
        t0 = time.perf_counter()
        res = cu_spine.compile_four_tier_cu_action(
            direct_command=direct_command,
            webmcp_tool=webmcp_tool,
            typed_action=typed_action,
            osworld_v21_state=osworld_v21_state,
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

    # ------------------------------------------------- Waves 7-10 Unified Front-Door Routes

    def route_durable_commit(
        self,
        workspace_root: str | Path,
        file_writes: Mapping[str, bytes | str],
        *,
        crash_at: str | None = None,
        recover_after_crash: bool = False,
        cluster: str = "durable_commit",
    ) -> dict[str, Any]:
        """Crash-safe multi-path journaled commit (`0F` × `the_record_is_the_commit_v1`)."""
        t0 = time.perf_counter()
        res = cu_spine.durable_transactional_commit(
            workspace_root,
            file_writes,
            crash_at=crash_at,
            recover_after_crash=recover_after_crash,
        )
        ok = bool(res.get("pass"))
        self._record_cluster(cluster, tier="TIER_1_DURABLE_COMMIT" if ok else "UNSOLVED", passed=ok)
        return {
            "schema": SCHEMA,
            "pass": ok,
            "status": res.get("status"),
            "commit": res,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            "model_calls": 0,
        }

    def route_env_broker(
        self,
        repo_root: str | Path,
        *,
        cluster: str = "env_broker",
    ) -> dict[str, Any]:
        """Zero-model environment broker inspection (`0F` × `the_environment_broker_v1` × `causal_computer_use_agent_v1`)."""
        t0 = time.perf_counter()
        res = cu_spine.inspect_repo_environment_broker(repo_root)
        ok = bool(res.get("pass"))
        self._record_cluster(cluster, tier="TIER_1_ENV_BROKER" if ok else "UNSOLVED", passed=ok)
        return {
            "schema": SCHEMA,
            "pass": ok,
            "status": res.get("status"),
            "broker": res,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            "model_calls": 0,
        }

    def route_angelic_counterfactual_repair(
        self,
        *,
        cluster: str = "angelic_counterfactual",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Zero-model Angelic + Counterfactual Interior-Spec + CEGIS synthesis (`0D`)."""
        t0 = time.perf_counter()
        res = swe_spine.synthesize_counterfactual_and_angelic_repair(**kwargs)
        ok = bool(res.get("pass"))
        self._record_cluster(cluster, tier="TIER_1_ANGELIC_CEGIS" if ok else "UNSOLVED", passed=ok)
        return {
            "schema": SCHEMA,
            "pass": ok,
            "status": res.get("status"),
            "tier_used": "TIER_1_ANGELIC_CEGIS" if ok else "NONE",
            "synthesis": res,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            "model_calls": 0,
        }

    def route_crossfile_choreography(
        self,
        args: Mapping[str, Any],
        root: str | Path,
        *,
        cluster: str = "crossfile_repair",
    ) -> dict[str, Any]:
        """Cross-file staged / in-place repair choreography (`0D` × `software_repair_crossfile_choreograph_v1`)."""
        t0 = time.perf_counter()
        res = swe_spine.choreograph_crossfile_repair(args, root)
        ok = bool(res.get("pass"))
        self._record_cluster(cluster, tier="TIER_1_CROSSFILE" if ok else "UNSOLVED", passed=ok)
        return {
            "schema": SCHEMA,
            "pass": ok,
            "status": res.get("status"),
            "choreography": res,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            "model_calls": 0,
        }

    def route_compile_goal_contract(
        self,
        goal: str,
        *,
        admissible: Mapping[str, Mapping[str, Any]] | None = None,
        root: str | Path | None = None,
        cluster: str = "goal_contract_compiler",
    ) -> dict[str, Any]:
        """Zero-token natural-language -> typed capability contract compiler (`0D` × `goal_front_compiler_v1` × `declared_input_derivation_v1`)."""
        t0 = time.perf_counter()
        res = swe_spine.compile_plain_goal_contract(goal, admissible=admissible, root=root)
        ok = bool(res.get("pass"))
        self._record_cluster(cluster, tier="TIER_0_GOAL_COMPILER" if ok else "UNSOLVED", passed=ok)
        return {
            "schema": SCHEMA,
            "pass": ok,
            "status": res.get("status"),
            "contract": res,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            "model_calls": 0,
        }

    def route_branch_mental_model(
        self,
        workspace_root: str | Path,
        *,
        required_files: Mapping[str, Mapping[str, Any]] | None = None,
        candidate_commands: Sequence[Sequence[str]] | None = None,
        commit_winner: bool = False,
        cluster: str = "branch_mental_model",
    ) -> dict[str, Any]:
        """'The Branch Is the Model' (`0E` × `executable_mental_model_v1` × `the_branch_is_the_model_v1`)."""
        t0 = time.perf_counter()
        res = env_spine.solve_via_branch_model_and_mental_model(
            workspace_root,
            required_files=required_files,
            candidate_commands=candidate_commands,
            commit_winner=commit_winner,
        )
        ok = bool(res.get("pass"))
        self._record_cluster(cluster, tier="TIER_1_BRANCH_MODEL" if ok else "UNSOLVED", passed=ok)
        return {
            "schema": SCHEMA,
            "pass": ok,
            "status": res.get("status"),
            "mental_model": res,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            "model_calls": 0,
        }

    def route_check_mode_oracle(
        self,
        *,
        argv: Sequence[str] | None = None,
        cwd: str | Path | None = None,
        refusal_messages: Sequence[str] = (),
        written_types_root: str | Path | None = None,
        type_names: Sequence[str] = (),
        cluster: str = "check_mode_oracle",
    ) -> dict[str, Any]:
        """'The Check Mode Is the Oracle' + Refusal & Empirical Type Vocabulary (`0E`)."""
        t0 = time.perf_counter()
        res = env_spine.discover_check_mode_oracle(
            argv,
            cwd=cwd,
            refusal_messages=refusal_messages,
            written_types_root=written_types_root,
            type_names=type_names,
        )
        ok = bool(res.get("pass"))
        self._record_cluster(cluster, tier="TIER_1_CHECK_MODE_ORACLE" if ok else "UNSOLVED", passed=ok)
        return {
            "schema": SCHEMA,
            "pass": ok,
            "status": res.get("status"),
            "oracle": res,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            "model_calls": 0,
        }

    def route_counterexample_experiment(
        self,
        traces: Sequence[Sequence[Sequence[tuple[str, Any]]]],
        labels: Sequence[bool],
        *,
        asked: Sequence[tuple[int, int]] = (),
        cluster: str = "counterexample_experiment",
    ) -> dict[str, Any]:
        """'The Counterexample Is the Next Experiment' (`0G`)."""
        t0 = time.perf_counter()
        res = self.memory_bus.propose_counterexample_experiment(traces, labels, asked=asked)
        ok = bool(res.get("pass"))
        self._record_cluster(cluster, tier="TIER_1_COUNTEREXAMPLE" if ok else "UNSOLVED", passed=ok)
        return {
            "schema": SCHEMA,
            "pass": ok,
            "status": res.get("status"),
            "experiment": res,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            "model_calls": 0,
        }

    def route_run_relation_goal(
        self,
        traces: Sequence[Sequence[Sequence[tuple[str, Any]]]],
        labels: Sequence[bool],
        *,
        cluster: str = "run_relation_goal",
    ) -> dict[str, Any]:
        """'The Goal Is a Relation Over the Run' (`0G`)."""
        t0 = time.perf_counter()
        res = self.memory_bus.induce_run_relation_goal(traces, labels)
        ok = bool(res.get("pass"))
        self._record_cluster(cluster, tier="TIER_1_RUN_RELATION" if ok else "UNSOLVED", passed=ok)
        return {
            "schema": SCHEMA,
            "pass": ok,
            "status": res.get("status"),
            "run_relation": res,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            "model_calls": 0,
        }

    def route_one_experience_consequences(
        self,
        training: Sequence[tuple[str, Any, Any]],
        conditions: Sequence[Any],
        *,
        cluster: str = "one_experience",
    ) -> dict[str, Any]:
        """'One Experience, Every Consequence' (`0G`)."""
        t0 = time.perf_counter()
        res = self.memory_bus.extract_one_experience_consequences(training, conditions)
        ok = bool(res.get("pass"))
        self._record_cluster(cluster, tier="TIER_1_ONE_EXPERIENCE" if ok else "UNSOLVED", passed=ok)
        return {
            "schema": SCHEMA,
            "pass": ok,
            "status": res.get("status"),
            "consequences": res,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            "model_calls": 0,
        }

    def route_self_evolution_firewall(
        self,
        source_text: str,
        verifier_fn: Callable[[Mapping[str, Any]], bool],
        *,
        skill_id: str = "self_mod_candidate",
        workspace_root: str | Path | None = None,
        target_rel: str | None = None,
        positive_examples: Sequence[Any] = (),
        negative_mutants: Sequence[Any] = (),
        check_predicate: Callable[[Any], bool] | None = None,
        limit: int = 8,
        seed: int = 7,
        min_kill_rate: float = 0.5,
        commit_on_pass: bool = False,
        cluster: str = "self_evolution_firewall",
    ) -> dict[str, Any]:
        """Wave 10 Entry-Only Self-Evolution Firewall (`0H` × `0F` × `0G`, blocking poisoned state at entry)."""
        t0 = time.perf_counter()
        res = oracle_spine.audit_self_evolution_entry(
            source_text,
            verifier_fn,
            skill_id=skill_id,
            workspace_root=workspace_root,
            target_rel=target_rel,
            positive_examples=positive_examples,
            negative_mutants=negative_mutants,
            check_predicate=check_predicate,
            limit=limit,
            seed=seed,
            min_kill_rate=min_kill_rate,
            commit_on_pass=commit_on_pass,
            memory_bus=self.memory_bus,
        )
        ok = bool(res.get("pass"))
        self._record_cluster(cluster, tier="TIER_1_ENTRY_FIREWALL" if ok else "UNSOLVED", passed=ok)
        return {
            "schema": SCHEMA,
            "pass": ok,
            "admitted": bool(res.get("admitted")),
            "status": res.get("status"),
            "firewall": res,
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

    # ------------------------------------------------- Waves 11-13 Unified Front-Door Routes

    def route_curate_skills(
        self,
        *,
        grader_report: Mapping[str, Any] | None = None,
        min_trials: int = 3,
        threshold: float = 0.10,
        active_cap: int = 200,
        db_path: str | Path | None = None,
        cluster: str = "skill_curation",
    ) -> dict[str, Any]:
        """Wave 11 Library-Drift Immunity (`0G` × `skill_contribution_ledger_v1`)."""
        t0 = time.perf_counter()
        res = self.memory_bus.curate_skills_by_contribution(
            grader_report=grader_report,
            min_trials=min_trials,
            threshold=threshold,
            active_cap=active_cap,
            db_path=db_path,
        )
        ok = bool(res.get("pass"))
        self._record_cluster(cluster, tier="TIER_1_SKILL_CURATION" if ok else "UNSOLVED", passed=ok)
        return {
            "schema": SCHEMA,
            "pass": ok,
            "status": res.get("status"),
            "curation": res,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            "model_calls": 0,
        }

    def route_observe_drift(
        self,
        stream: str,
        value: float | bool,
    ) -> dict[str, Any]:
        """Wave 11 Hybrid ADWIN + BOCPD + Page-Hinkley concept-drift monitoring (`0G`)."""
        return self.memory_bus.observe_drift(stream, value)

    def route_cross_host_transfer(
        self,
        landed_a: Mapping[str, Any],
        landed_b: Mapping[str, Any],
        *,
        cluster: str = "cross_host_transfer",
    ) -> dict[str, Any]:
        """Wave 11 Cross-host transfer audit (`0G` × `what_transfers_to_a_second_host_v1`)."""
        t0 = time.perf_counter()
        res = self.memory_bus.audit_cross_host_transfer(landed_a, landed_b)
        ok = bool(res.get("pass"))
        self._record_cluster(cluster, tier="TIER_1_CROSS_HOST" if ok else "UNSOLVED", passed=ok)
        return {
            "schema": SCHEMA,
            "pass": ok,
            "status": res.get("status"),
            "transfer": res,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            "model_calls": 0,
        }

    def route_one_demonstration_identify(
        self,
        *,
        rows: Sequence[Mapping[str, Any]] | None = None,
        path: str | None = None,
        function: str | None = None,
        variable: str | None = None,
        repo: str | Path | None = None,
        cluster: str = "one_demo_identify",
    ) -> dict[str, Any]:
        """Wave 11 One-demonstration identification (`0G` × `one_demonstration_identifies_v1`)."""
        t0 = time.perf_counter()
        res = self.memory_bus.identify_from_one_demonstration(
            rows=rows,
            path=path,
            function=function,
            variable=variable,
            repo=repo,
        )
        ok = bool(res.get("pass"))
        self._record_cluster(cluster, tier="TIER_1_ONE_DEMO_IDENTIFY" if ok else "UNSOLVED", passed=ok)
        return {
            "schema": SCHEMA,
            "pass": ok,
            "status": res.get("status"),
            "identification": res,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            "model_calls": 0,
        }

    def route_trace_expression_repair(
        self,
        *,
        cluster: str = "trace_expr_repair",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Wave 12 Dual-Slicing Execution-Trace & Literal Defect Synthesis (`0D`)."""
        t0 = time.perf_counter()
        res = swe_spine.trace_expression_and_literal_repair(**kwargs)
        ok = bool(res.get("pass"))
        self._record_cluster(cluster, tier="TIER_1_TRACE_EXPR_REPAIR" if ok else "UNSOLVED", passed=ok)
        return {
            "schema": SCHEMA,
            "pass": ok,
            "status": res.get("status"),
            "trace_repair": res,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            "model_calls": 0,
        }

    def route_multi_file_causal_localize(
        self,
        repo_root: str | Path,
        *,
        cluster: str = "multifile_causal_localize",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Wave 12 Multi-Step Differential Trace Localization & Causal SWE Repair (`0D`)."""
        t0 = time.perf_counter()
        res = swe_spine.multi_file_causal_localize_and_repair(repo_root, **kwargs)
        ok = bool(res.get("pass"))
        self._record_cluster(cluster, tier="TIER_1_CAUSAL_LOCALIZE" if ok else "UNSOLVED", passed=ok)
        return {
            "schema": SCHEMA,
            "pass": ok,
            "status": res.get("status"),
            "causal_result": res,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            "model_calls": 0,
        }

    def route_discover_computer_env(
        self,
        *,
        cluster: str = "computer_env",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Wave 13 'The Computer Itself Is the Environment' (`0E` × `computer_env_v1` × `an_effect_not_a_description_v1`)."""
        t0 = time.perf_counter()
        res = env_spine.discover_computer_environment(**kwargs)
        ok = bool(res.get("pass"))
        self._record_cluster(cluster, tier="TIER_1_COMPUTER_ENV" if ok else "UNSOLVED", passed=ok)
        return {
            "schema": SCHEMA,
            "pass": ok,
            "status": res.get("status"),
            "computer_env": res,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            "model_calls": 0,
        }

    def route_admit_live(
        self,
        goal: str,
        *,
        compiled: Mapping[str, Any] | None = None,
        registry: Mapping[str, Mapping[str, Any]] | None = None,
        dag: Mapping[str, Any] | None = None,
        entry: Mapping[str, Any] | None = None,
        cluster: str = "live_route_admission",
    ) -> dict[str, Any]:
        """Wave 13 Fail-closed live route admission (`live_brain_route_admission_v1`)."""
        from canonical.runtime import live_brain_route_admission_v1 as lbra

        t0 = time.perf_counter()
        roles = sorted(lbra.stated_object_roles(goal))
        role_errs = list(lbra.object_role_errors(goal, entry)) if entry is not None else []
        dag_errs = list(lbra.dag_contract_errors(dag)) if dag is not None else []
        admission = (
            lbra.route_admission(goal, compiled, registry)
            if (compiled is not None and registry is not None)
            else None
        )
        if admission is not None:
            ok = bool(admission.get("admitted") or admission.get("status") == "ADMITTED")
        else:
            ok = (len(role_errs) == 0) and (len(dag_errs) == 0)
        self._record_cluster(cluster, tier="TIER_0_ROUTE_ADMISSION" if ok else "UNSOLVED", passed=ok)
        return {
            "schema": SCHEMA,
            "pass": ok,
            "status": "PASS__ROUTE_ADMITTED" if ok else "FAIL_CLOSED__ROUTE_ADMISSION_REJECTED",
            "stated_object_roles": roles,
            "object_role_errors": role_errs,
            "dag_contract_errors": dag_errs,
            "admission": admission,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            "model_calls": 0,
        }

    def route_semantic_plan(
        self,
        goal: str,
        *,
        cluster: str = "semantic_plan",
    ) -> dict[str, Any]:
        """Wave 13 Neuro-symbolic compositional & causal task AST + plan synthesis (`semantic_generalization_engine_v1`)."""
        from canonical.swe_kernel import semantic_generalization_engine_v1 as sge

        t0 = time.perf_counter()
        task_ast = sge.parse_task(goal)
        plan = sge.synthesize_plan(task_ast)
        steps = list(plan.get("steps") or plan.get("plan") or ())
        ok = bool(plan.get("ok", True)) and (len(steps) > 0 or bool(plan))
        self._record_cluster(cluster, tier="TIER_1_SEMANTIC_PLAN" if ok else "UNSOLVED", passed=ok)
        return {
            "schema": SCHEMA,
            "pass": ok,
            "status": "PASS__SEMANTIC_PLAN_SYNTHESIZED" if ok else "FAIL_CLOSED__SEMANTIC_PLAN_EMPTY",
            "task_ast": getattr(task_ast, "__dict__", str(task_ast)),
            "plan": plan,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            "model_calls": 0,
        }

    def route_derive_execution_adapter(
        self,
        module_rel: str,
        *,
        test_rel: str | None = None,
        repo_root: str | Path | None = None,
        timeout_s: float = 12.0,
        cluster: str = "execution_adapter_derivation",
    ) -> dict[str, Any]:
        """Wave 13 Execution-Recorded Call-Frame Adapter Derivation + Two-Run Deterministic Replay Receipt.

        Replaces literal-AST call scraping (killed at 3.7% survival in PR #7117) by recording real
        JSON-serializable call frames directly from the target module's own test execution, then
        replaying the captured ``(function, args, kwargs)`` TWICE in fresh isolated subprocesses
        and accepting ONLY when both runs succeed with identical output SHA-256 digests.
        """
        import hashlib
        import json
        import os
        import subprocess
        import sys
        import tempfile

        from canonical.tools import ast_adapter_derivation_v1 as ast_deriv

        t0 = time.perf_counter()
        root = Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
        mod_path = (root / module_rel).resolve()
        if not mod_path.is_file():
            return {
                "schema": SCHEMA,
                "pass": False,
                "status": "FAIL_CLOSED__MODULE_NOT_FOUND",
                "module": module_rel,
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
                "model_calls": 0,
            }

        surface = ast_deriv.module_surface(mod_path)
        pub_funcs = sorted((surface.get("functions") or {}).keys())
        if not pub_funcs:
            return {
                "schema": SCHEMA,
                "pass": False,
                "status": "FAIL_CLOSED__NO_PUBLIC_FUNCTION",
                "module": module_rel,
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
                "model_calls": 0,
            }

        # Discover same-stem test file when test_rel is not explicitly supplied
        if test_rel:
            t_path = (root / test_rel).resolve()
        else:
            stem = mod_path.stem
            candidates = [
                root / "canonical" / "tests" / f"test_{stem}.py",
                mod_path.parent / f"test_{stem}.py",
            ]
            t_path = next((p for p in candidates if p.is_file()), candidates[0])
        if not t_path.is_file():
            return {
                "schema": SCHEMA,
                "pass": False,
                "status": "FAIL_CLOSED__NO_TEST_FILE",
                "module": module_rel,
                "expected_test": str(t_path),
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
                "model_calls": 0,
            }

        rel_posix = mod_path.relative_to(root).as_posix()
        mod_dotted = rel_posix[:-3].replace("/", ".") if rel_posix.endswith(".py") else rel_posix

        env = dict(os.environ)
        prev_pp = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = f"{root}:{prev_pp}" if prev_pp else str(root)

        capture_script = (
            "import functools, importlib, importlib.util, inspect, json, pathlib, sys, tempfile\n"
            "mod_name, test_path, out_path, fn_json = sys.argv[1:5]\n"
            "fn_names = json.loads(fn_json)\n"
            "mod = importlib.import_module(mod_name)\n"
            "captured = []\n"
            "seen_keys = set()\n"
            "class _CaptureComplete(BaseException): pass\n"
            "def _flush():\n"
            "    with open(out_path, 'w', encoding='utf-8') as fh:\n"
            "        json.dump({'captured': captured}, fh)\n"
            "def _wrap(name, orig):\n"
            "    @functools.wraps(orig)\n"
            "    def _inner(*args, **kwargs):\n"
            "        if len(captured) < 6:\n"
            "            try:\n"
            "                payload = json.dumps({'a': list(args), 'k': dict(kwargs)}, allow_nan=False)\n"
            "                if len(payload) <= 8192:\n"
            "                    key = (name, payload)\n"
            "                    if key not in seen_keys:\n"
            "                        seen_keys.add(key)\n"
            "                        parsed = json.loads(payload)\n"
            "                        captured.append({'function': name, 'args': parsed['a'], 'kwargs': parsed['k']})\n"
            "                        _flush()\n"
            "            except Exception:\n"
            "                pass\n"
            "        res = orig(*args, **kwargs)\n"
            "        if len(captured) >= 6:\n"
            "            raise _CaptureComplete()\n"
            "        return res\n"
            "    return _inner\n"
            "for fn in fn_names:\n"
            "    orig = getattr(mod, fn, None)\n"
            "    if callable(orig):\n"
            "        setattr(mod, fn, _wrap(fn, orig))\n"
            "try:\n"
            "    try:\n"
            "        import pytest\n"
            "        pytest.main([test_path, '-q', '--no-header', '-p', 'no:cacheprovider', '--maxfail=2'])\n"
            "    except ImportError:\n"
            "        import unittest\n"
            "        tp = pathlib.Path(test_path)\n"
            "        suite = unittest.defaultTestLoader.discover(start_dir=str(tp.parent), pattern=tp.name)\n"
            "        unittest.TextTestRunner(verbosity=0).run(suite)\n"
            "        if not captured:\n"
            "            spec = importlib.util.spec_from_file_location('_brain_cap_test', str(tp))\n"
            "            tmod = importlib.util.module_from_spec(spec)\n"
            "            spec.loader.exec_module(tmod)\n"
            "            with tempfile.TemporaryDirectory() as td:\n"
            "                for k, v in list(vars(tmod).items()):\n"
            "                    if k.startswith('test_') and callable(v):\n"
            "                        try:\n"
            "                            params = list(inspect.signature(v).parameters.keys())\n"
            "                            if not params:\n"
            "                                v()\n"
            "                            elif params == ['tmp_path']:\n"
            "                                v(pathlib.Path(td))\n"
            "                        except _CaptureComplete:\n"
            "                            raise\n"
            "                        except Exception:\n"
            "                            pass\n"
            "except _CaptureComplete:\n"
            "    pass\n"
            "finally:\n"
            "    _flush()\n"
        )

        replay_script = (
            "import hashlib, importlib, json, sys\n"
            "mod_name, fn_name, payload_json = sys.argv[1:4]\n"
            "payload = json.loads(payload_json)\n"
            "mod = importlib.import_module(mod_name)\n"
            "fn = getattr(mod, fn_name)\n"
            "res = fn(*payload['args'], **payload['kwargs'])\n"
            "ser = json.dumps(res, sort_keys=True, default=repr)\n"
            "dig = hashlib.sha256(ser.encode('utf-8')).hexdigest()\n"
            "print(json.dumps({'ok': True, 'digest': dig, 'preview': ser[:200]}))\n"
        )

        with tempfile.TemporaryDirectory(prefix="brain_exec_adapt_") as tmpdir:
            cap_out = Path(tmpdir) / "captured.json"
            try:
                subprocess.run(
                    [sys.executable, "-c", capture_script, mod_dotted, str(t_path), str(cap_out), json.dumps(pub_funcs)],
                    cwd=str(root),
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=float(timeout_s),
                )
            except subprocess.TimeoutExpired:
                self._record_cluster(cluster, tier="UNSOLVED", passed=False)
                return {
                    "schema": SCHEMA,
                    "pass": False,
                    "status": "FAIL_CLOSED__CAPTURE_TIMEOUT",
                    "module": rel_posix,
                    "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
                    "model_calls": 0,
                }

            captured_calls: list[dict[str, Any]] = []
            if cap_out.is_file():
                try:
                    captured_calls = list(json.loads(cap_out.read_text(encoding="utf-8")).get("captured") or ())
                except Exception:
                    captured_calls = []

            for call in captured_calls:
                fn_name = str(call["function"])
                payload_s = json.dumps({"args": call["args"], "kwargs": call["kwargs"]})
                run_digests: list[str] = []
                preview = ""
                for run_idx in range(2):
                    run_dir = Path(tmpdir) / f"replay_{fn_name}_{run_idx}"
                    run_dir.mkdir(parents=True, exist_ok=True)
                    try:
                        cp = subprocess.run(
                            [sys.executable, "-c", replay_script, mod_dotted, fn_name, payload_s],
                            cwd=str(run_dir),
                            env=env,
                            capture_output=True,
                            text=True,
                            timeout=min(5.0, float(timeout_s)),
                        )
                    except subprocess.TimeoutExpired:
                        break
                    if cp.returncode != 0 or not cp.stdout.strip():
                        break
                    try:
                        parsed = json.loads(cp.stdout.strip().splitlines()[-1])
                    except Exception:
                        break
                    if not parsed.get("ok") or not parsed.get("digest"):
                        break
                    run_digests.append(str(parsed["digest"]))
                    preview = str(parsed.get("preview") or "")
                if len(run_digests) == 2 and run_digests[0] == run_digests[1]:
                    receipt_dig = hashlib.sha256(
                        json.dumps([rel_posix, fn_name, call["args"], call["kwargs"], run_digests[0]], sort_keys=True).encode("utf-8")
                    ).hexdigest()
                    self._record_cluster(cluster, tier="TIER_1_EXECUTION_ADAPTER", passed=True)
                    return {
                        "schema": SCHEMA,
                        "pass": True,
                        "status": "PASS__EXECUTION_ADAPTER_DERIVED",
                        "module": rel_posix,
                        "test_file": t_path.relative_to(root).as_posix() if t_path.is_relative_to(root) else str(t_path),
                        "function": fn_name,
                        "args": call["args"],
                        "kwargs": call["kwargs"],
                        "digest_1": run_digests[0],
                        "digest_2": run_digests[1],
                        "deterministic_agreement": True,
                        "output_preview": preview,
                        "captured_calls_count": len(captured_calls),
                        "receipt_sha256": receipt_dig,
                        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
                        "model_calls": 0,
                    }

        self._record_cluster(cluster, tier="UNSOLVED", passed=False)
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED__NO_DETERMINISTIC_CALL_CAPTURED",
            "module": rel_posix,
            "captured_calls_count": len(captured_calls),
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            "model_calls": 0,
        }

    # ------------------------------------------------------------ Waves 15-18 Frontier-Leapfrog Routes
    def route_memguard_and_expiry(
        self,
        *,
        action: str = "audit",
        skill_id: str = "",
        reward: float = 1.0,
        confidence: float = 1.0,
        fingerprint: Mapping[str, Any] | None = None,
        current_fingerprint: Mapping[str, Any] | None = None,
        quarantine_on_drift: bool = True,
        db_path: str | Path | None = None,
    ) -> dict[str, Any]:
        """Wave 15 route: MemGuard persistent verifier lifecycle + `rule_expiry_v1` world-drift revocation."""
        cluster = "memguard_world_expiry"
        if str(action).lower() == "register":
            res = self.memory_bus.register_memguard_lifecycle(
                skill_id,
                reward=reward,
                confidence=confidence,
                fingerprint=fingerprint,
                db_path=db_path,
            )
        else:
            res = self.memory_bus.audit_world_expiry(
                current_fingerprint=current_fingerprint,
                quarantine_on_drift=quarantine_on_drift,
                db_path=db_path,
            )
        ok = bool(res.get("pass"))
        self._record_cluster(cluster, tier="TIER_0_MEMGUARD_EXPIRY", passed=ok)
        return res

    def route_anti_skill(
        self,
        *,
        action: str = "prune",
        domain: str = "general",
        symbol_scope: str = "*",
        bad_hypothesis: str = "",
        error_signature: str = "REFUTED",
        candidates: Sequence[str] = (),
        world_fp: Mapping[str, Any] | None = None,
        csp_pair: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Wave 15 route: Negative-Knowledge Anti-Skill recording & O(1) dead-branch pruning."""
        cluster = "anti_skill_refutation"
        if str(action).lower() == "record":
            res = self.memory_bus.record_anti_skill(
                domain=domain,
                symbol_scope=symbol_scope,
                bad_hypothesis=bad_hypothesis,
                error_signature=error_signature,
                world_fp=world_fp,
                csp_pair=csp_pair,
            )
        else:
            res = self.memory_bus.prune_by_anti_skills(
                candidates,
                domain=domain,
                symbol_scope=symbol_scope,
            )
        ok = bool(res.get("pass"))
        self._record_cluster(cluster, tier="TIER_0_ANTI_SKILL", passed=ok)
        return res

    def route_proved_composition(
        self,
        *,
        initial_text: str,
        operations: Sequence[Mapping[str, Any]],
    ) -> dict[str, Any]:
        """Wave 15 route: Premise- and proof-preserving multi-step composition (`proved_composition_v1`)."""
        cluster = "proved_composition"
        res = self.memory_bus.prove_and_compose_operations(initial_text=initial_text, operations=operations)
        ok = bool(res.get("pass"))
        self._record_cluster(cluster, tier="TIER_0_PROVED_COMPOSITION", passed=ok)
        return res

    def route_fts5_recall(
        self,
        query: str,
        *,
        top_k: int = 8,
        include_quarantined: bool = False,
        extra_docs: Sequence[Mapping[str, Any]] = (),
    ) -> dict[str, Any]:
        """Wave 15 route: Sub-2 ms SQLite FTS5 BM25 memory/runbook recall."""
        cluster = "fts5_runbook_recall"
        res = self.memory_bus.fts5_recall(
            query,
            top_k=top_k,
            include_quarantined=include_quarantined,
            extra_docs=extra_docs,
        )
        ok = bool(res.get("pass"))
        self._record_cluster(cluster, tier="TIER_0_FTS5_BM25", passed=ok)
        return res

    def route_swe_inverted_microscope(
        self,
        repo_root: str | Path,
        *,
        goal: str = "",
        test_files: Sequence[str] | None = None,
        apply_to_source: bool = False,
        residual_proposer: Any = None,
        law_store: Any = None,
        timeout_s: float = 25.0,
    ) -> dict[str, Any]:
        """Wave 16 route: Inverted Neuro-Symbolic SWE Microscope + 5 unwired hidden engines."""
        from canonical.swe_kernel import canonical_swe_spine_v1 as swe_spine

        cluster = "swe_inverted_microscope"
        res = swe_spine.solve_swe_inverted_microscope(
            repo_root,
            goal=goal,
            test_files=test_files,
            apply_to_source=apply_to_source,
            residual_proposer=residual_proposer,
            memory_bus=self.memory_bus,
            law_store=law_store,
            timeout_s=timeout_s,
        )
        ok = bool(res.get("pass"))
        self._record_cluster(cluster, tier=str(res.get("tier") or "UNSOLVED"), passed=ok)
        return res

    def route_fork_reality_speculate(self, **kwargs: Any) -> dict[str, Any]:
        """Wave 17 route: Fork-Reality CoW Speculative World Engine + Kernel Seccomp Confinement."""
        from canonical.swe_kernel import canonical_cu_sandbox_spine_v1 as cu_spine

        cluster = "fork_reality_cow"
        res = cu_spine.fork_reality_speculate_and_commit(**kwargs)
        ok = bool(res.get("pass"))
        self._record_cluster(cluster, tier="TIER_1_COW_SPECULATION", passed=ok)
        return res

    def route_elevate_gui_trace(
        self,
        trace: Mapping[str, Any] | Sequence[Mapping[str, Any]],
        *,
        goal: str = "",
        postcondition: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Wave 17 route: Dynamic GUI-to-CLI/DOM Layer Elevation (`causal_trace_to_skill_compiler_v1`)."""
        from canonical.swe_kernel import canonical_cu_sandbox_spine_v1 as cu_spine

        cluster = "gui_to_cli_elevation"
        res = cu_spine.elevate_gui_trace_to_cli_skill(trace, goal=goal, postcondition=postcondition)
        ok = bool(res.get("pass"))
        self._record_cluster(cluster, tier="TIER_0_LAYER_ELEVATION", passed=ok)
        return res

    def route_partial_order_plan(self, **kwargs: Any) -> dict[str, Any]:
        """Wave 17 route: Partial-Order Conditional Operator Induction & Planning (`partial_order_planner_v1`)."""
        from canonical.swe_kernel import canonical_env_discovery_spine_v1 as env_spine

        cluster = "partial_order_planner"
        res = env_spine.plan_partial_order_operators(**kwargs)
        ok = bool(res.get("pass"))
        self._record_cluster(cluster, tier="TIER_1_PARTIAL_ORDER_PLAN", passed=ok)
        return res

    def route_minimax_interrogate(self, **kwargs: Any) -> dict[str, Any]:
        """Wave 18 route: Exact-Minimax Witness Interrogation (`evidence_demand_v1`)."""
        from canonical.swe_kernel import canonical_oracle_vericoding_spine_v1 as oracle_spine

        cluster = "minimax_interrogation"
        res = oracle_spine.interrogate_minimax_witness(**kwargs)
        ok = bool(res.get("pass"))
        self._record_cluster(cluster, tier="TIER_0_MINIMAX_WITNESS", passed=ok)
        return res

    def route_csp_hard_negatives(self, **kwargs: Any) -> dict[str, Any]:
        """Wave 18 route: NS-PRM Counterfactual Symbolic Perturbation Hard-Negative & Spec-Gap Generator."""
        from canonical.swe_kernel import canonical_oracle_vericoding_spine_v1 as oracle_spine

        cluster = "csp_hard_negatives"
        res = oracle_spine.generate_csp_hard_negatives(**kwargs)
        ok = bool(res.get("pass"))
        self._record_cluster(cluster, tier="TIER_0_CSP_PERTURBATION", passed=ok)
        return res

    # ------------------------------------------------- Waves 22-25 Frontier Leapfrog Routes

    def route_universal_capability_bridge(
        self,
        goal: str,
        *,
        registry: Mapping[str, Mapping[str, Any]] | None = None,
        contract_text: str | None = None,
        repo_nav_root: str | Path | None = None,
        repo_nav_kind: str = "find_symbol",
        repo_nav_target: str = "",
        compose_type_chain: bool = False,
        top_k: int = 8,
    ) -> dict[str, Any]:
        """Wave 22 route: Universal Reachability Bridge (`verified_capability_bridge_index_v1`
        × `source_contract_compiler` × `learned_skill_verdict_v1`, zero LLM, zero self-promotion)."""
        from canonical.runtime import source_contract_compiler as scc
        from canonical.swe_kernel import learned_skill_verdict_v1 as lsv
        from canonical.swe_kernel import verified_capability_bridge_index_v1 as vcb

        t0 = time.perf_counter()
        roles = vcb.induce_zero_weight_semantic_roles(str(goal))
        reg_map: Mapping[str, Mapping[str, Any]] = registry or {}
        phrase_matches = (
            vcb.find_phrase_matched_capabilities(str(goal), reg_map)[: int(top_k)]
            if reg_map
            else []
        )

        # Match against compiled learned skills without executing unverified mutations
        matched_skills: list[dict[str, Any]] = []
        try:
            for sk in lsv.load_skills():
                req = lsv.request_from_goal(sk, str(goal))
                if req is not None:
                    matched_skills.append({"skill_id": sk.get("skill_id") or sk.get("id"), "request": req})
                    if len(matched_skills) >= int(top_k):
                        break
        except Exception:
            pass

        contract_report: dict[str, Any] | None = None
        if contract_text is not None:
            atoms = scc.atomize_source(str(contract_text), "inline_goal_contract")
            contract_report = {
                "atom_count": len(atoms),
                "normative_atoms": sum(1 for a in atoms if a.normative),
                "high_risk_atoms": sum(1 for a in atoms if a.high_risk),
                "obligation_lower_bound": scc.obligation_lower_bound(str(contract_text)),
                "roundtrip_exact": scc.reconstruct_source(atoms) == str(contract_text),
            }

        repo_nav_report: dict[str, Any] | None = None
        if repo_nav_root is not None and repo_nav_target:
            repo_nav_report = vcb.query_semantic_repo_navigation(
                Path(repo_nav_root).resolve(),
                str(repo_nav_kind),
                str(repo_nav_target),
            )

        type_chain_report: dict[str, Any] | None = None
        if compose_type_chain:
            type_chain_report = vcb.get_cached_type_level_graph(reg_map or None, max_len=2)

        ok = bool(roles or phrase_matches or matched_skills or contract_report or repo_nav_report)
        self._record_cluster("universal_capability_bridge", tier="TIER_0_UNIVERSAL_BRIDGE", passed=ok)
        return {
            "schema": SCHEMA,
            "pass": ok,
            "status": "PASS__UNIVERSAL_BRIDGE_RESOLVED" if ok else "FAIL_CLOSED__NO_BRIDGE_MATCH",
            "goal": str(goal),
            "semantic_roles": roles,
            "phrase_matches": phrase_matches,
            "matched_learned_skills": matched_skills,
            "source_contract": contract_report,
            "repo_navigation": repo_nav_report,
            "type_level_graph_summary": (
                {"edge_count": len(type_chain_report.get("edges") or ()), "keys": sorted(type_chain_report.keys())[:10]}
                if isinstance(type_chain_report, Mapping)
                else None
            ),
            "model_calls": 0,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }

    def route_swe_repo_native_multifile(self, **kwargs: Any) -> dict[str, Any]:
        """Wave 23 route: Repo-Native Multi-File SWE Engine (`0D` × 7 hidden SWE superweapons)."""
        from canonical.swe_kernel import canonical_swe_spine_v1 as swe_spine

        res = swe_spine.solve_swe_repo_native_multifile(**kwargs)
        ok = bool(res.get("pass"))
        self._record_cluster("swe_repo_native_multifile", tier=str(res.get("tier") or "UNSOLVED"), passed=ok)
        return res

    def route_bitemporal_skill_bank(self, **kwargs: Any) -> dict[str, Any]:
        """Wave 24 route: Bitemporal Memory + Counterfactual Credit + Hierarchical SkillBank (`0G`)."""
        res = self.memory_bus.bitemporal_credit_and_skill_bank(**kwargs)
        ok = bool(res.get("pass"))
        self._record_cluster("bitemporal_skill_bank", tier="TIER_0_BITEMPORAL_SKILL_BANK", passed=ok)
        return res

    def route_verify_effect_chain(self, **kwargs: Any) -> dict[str, Any]:
        """Wave 24 route: Formal Effect-Contract Composition & Verification (`0G`)."""
        res = self.memory_bus.verify_effect_contract_chain(**kwargs)
        ok = bool(res.get("pass"))
        self._record_cluster("effect_contract_chain", tier="TIER_0_EFFECT_CHAIN", passed=ok)
        return res

    def route_red_queen_coevolution(self, **kwargs: Any) -> dict[str, Any]:
        """Wave 24 route: Red Queen Evaluator Co-Evolution (`0H`, intra-epoch frozen judge)."""
        from canonical.swe_kernel import canonical_oracle_vericoding_spine_v1 as oracle_spine

        res = oracle_spine.run_red_queen_evaluator_coevolution(**kwargs)
        ok = bool(res.get("pass"))
        self._record_cluster("red_queen_coevolution", tier="TIER_0_RED_QUEEN_EPOCH", passed=ok)
        return res

    def route_safe_exploration(self, **kwargs: Any) -> dict[str, Any]:
        """Wave 25 route: Systematic Exploration + Safe Action Model + Demonstration Sufficiency (`0E`)."""
        from canonical.swe_kernel import canonical_env_discovery_spine_v1 as env_spine

        res = env_spine.explore_and_induce_safe_action_model(**kwargs)
        ok = bool(res.get("pass"))
        self._record_cluster("safe_exploration", tier="TIER_1_SAFE_EXPLORATION", passed=ok)
        return res

    def route_decision_quotient(self, **kwargs: Any) -> dict[str, Any]:
        """Wave 25 route: K6 Target-Relative Decision Quotient & Deadline Refinement Compiler (`0E`)."""
        from canonical.swe_kernel import canonical_env_discovery_spine_v1 as env_spine

        res = env_spine.compile_decision_quotient_and_refinement(**kwargs)
        ok = bool(res.get("pass"))
        self._record_cluster("decision_quotient", tier="TIER_0_DECISION_QUOTIENT", passed=ok)
        return res

    def route_horizon_zero_screenshot_cu(self, **kwargs: Any) -> dict[str, Any]:
        """Wave 25 route: Horizon-Bounded CU + Zero-Screenshot DOM Cache + Vocabulary Growth (`0F`)."""
        from canonical.swe_kernel import canonical_cu_sandbox_spine_v1 as cu_spine

        res = cu_spine.execute_horizon_bounded_zero_screenshot_cu(**kwargs)
        ok = bool(res.get("pass"))
        self._record_cluster("horizon_zero_screenshot_cu", tier="TIER_0_ZERO_SCREENSHOT_CU", passed=ok)
        return res

    # ----------------------------------------------------- Waves 27-30 Frontier Leapfrog Routes
    def route_contrast_memory_laws(self, **kwargs: Any) -> dict[str, Any]:
        """Wave 27 route: Contrast-Carrying Laws & O(1) Anti-Catastrophic-Remembering Pruning (`0G`)."""
        res = self.memory_bus.store_and_prune_contrast_laws(**kwargs)
        ok = bool(res.get("pass"))
        self._record_cluster("contrast_memory_laws", tier="TIER_0_CONTRAST_MEMORY", passed=ok)
        return res

    def route_filing_key_hindsight_jitrl(self, **kwargs: Any) -> dict[str, Any]:
        """Wave 27 route: Filing-Key Audit + Alpha-Safe Unwelding + AgentHER Hindsight + JitRL (`0G`)."""
        res = self.memory_bus.filing_key_hindsight_and_jitrl(**kwargs)
        ok = bool(res.get("pass"))
        self._record_cluster("filing_key_hindsight_jitrl", tier="TIER_0_HINDSIGHT_JITRL", passed=ok)
        return res

    def route_producer_lineage_holes(self, **kwargs: Any) -> dict[str, Any]:
        """Wave 28 route: Producer-Lineage Tracing & Typed Hole Inversion SWE Engine (`0D`)."""
        res = swe_spine.solve_producer_lineage_hole_inversion(**kwargs)
        ok = bool(res.get("pass"))
        self._record_cluster("producer_lineage_holes", tier="TIER_1_PRODUCER_HOLE_INVERSION", passed=ok)
        return res

    def route_verifier_pinning_oracles(self, **kwargs: Any) -> dict[str, Any]:
        """Wave 29 route: Verifier Hunk-Pinning Audit & Autonomous Docstring/Green-Suite Oracles (`0H`)."""
        res = oracle_spine.audit_verifier_pinning_and_synthesize_oracles(**kwargs)
        ok = bool(res.get("pass"))
        self._record_cluster("verifier_pinning_oracles", tier="TIER_0_VERIFIER_PINNING", passed=ok)
        return res

    def route_purpose_gate_arbitrage(self, **kwargs: Any) -> dict[str, Any]:
        """Wave 30 route: Purpose-Gated Active Inference & Economic Decision Arbitrage (`0E`)."""
        res = env_spine.purpose_gated_active_inference_and_cost_arbitrage(**kwargs)
        ok = bool(res.get("pass"))
        self._record_cluster("purpose_gate_arbitrage", tier="TIER_0_PURPOSE_GATE_ARBITRAGE", passed=ok)
        return res

    def route_two_move_horizon_cu(self, **kwargs: Any) -> dict[str, Any]:
        """Wave 30 route: Class-Level Two-Move Planning + Horizon Bridge + Goal DAG + OSWorld v2.1 (`0F`)."""
        res = cu_spine.plan_two_move_and_horizon_bridge(**kwargs)
        ok = bool(res.get("pass"))
        self._record_cluster("two_move_horizon_cu", tier="TIER_0_TWO_MOVE_HORIZON_CU", passed=ok)
        return res

    # ----------------------------------------------------- Waves 32-35 Frontier Leapfrog Routes
    def route_disambiguate_and_pin_repairs(self, **kwargs: Any) -> dict[str, Any]:
        """Wave 32 route: Version-Space Repair Selection + Angelic CEGIS + Inverse Completion + Repo-Seeded SWE (`0D`)."""
        res = swe_spine.disambiguate_and_synthesize_repairs(**kwargs)
        ok = bool(res.get("pass"))
        self._record_cluster("wave32_version_space_swe", tier="TIER_1_VERSION_SPACE_SWE", passed=ok)
        return res

    def route_prove_equivalence_and_amplify(self, **kwargs: Any) -> dict[str, Any]:
        """Wave 32 route: Behavioral-Equivalence Proof + Distinguishing Projection + Reverted-Part Pinning + Verdict Amplification (`0H`)."""
        res = oracle_spine.prove_equivalence_and_amplify_verdict(**kwargs)
        ok = bool(res.get("pass"))
        self._record_cluster("wave32_equivalence_oracle", tier="TIER_0_EQUIVALENCE_ORACLE", passed=ok)
        return res

    def route_meaning_first_transfer(self, **kwargs: Any) -> dict[str, Any]:
        """Wave 33 route: Meaning-First IR Crystallization + Cross-Language Transfer + Scoped Skills + Weight Admission (`0G`)."""
        res = self.memory_bus.crystallize_meaning_first_and_transfer(**kwargs)
        ok = bool(res.get("pass"))
        self._record_cluster("wave33_meaning_first_transfer", tier="TIER_0_MEANING_FIRST_TRANSFER", passed=ok)
        return res

    def route_memini_memrl_apex(self, **kwargs: Any) -> dict[str, Any]:
        """Wave 33 route: Memini (w_fast/w_slow) + MemRL (TD Q + 2-phase) + APEX-EM (3-channel) Consolidation (`0G`)."""
        res = self.memory_bus.memini_memrl_apex_consolidate(**kwargs)
        ok = bool(res.get("pass"))
        self._record_cluster("wave33_memini_memrl_apex", tier="TIER_0_MEMINI_MEMRL_APEX", passed=ok)
        return res

    def route_osworld_v21_epistemic_cu(self, **kwargs: Any) -> dict[str, Any]:
        """Wave 34 route: OSWorld 2.1 Pure-Stdlib CU Engine + Epistemic Computer Agent + Action-Grammar Guide (`0F`)."""
        res = cu_spine.execute_osworld_v21_and_epistemic_cu(**kwargs)
        ok = bool(res.get("pass"))
        self._record_cluster("wave34_osworld_v21_cu", tier="TIER_0_OSWORLD_V21_CU", passed=ok)
        return res

    def route_speculative_macro_commit(self, **kwargs: Any) -> dict[str, Any]:
        """Wave 34 route: TomasuLLM Speculative Macro Commit + Standing-Fact Invalidation + Effect Witnesses + Parallel Frontier (`0F`)."""
        res = cu_spine.speculative_macro_commit(**kwargs)
        ok = bool(res.get("pass"))
        self._record_cluster("wave34_speculative_commit", tier="TIER_0_SPECULATIVE_MACRO_COMMIT", passed=ok)
        return res

    def route_active_repertoire_typed_invention(self, **kwargs: Any) -> dict[str, Any]:
        """Wave 35 route: Active-Inference Repertoire Query + Typed CEGIS(T) + Distinction Creation + Counterfactual Contracts (`0E`)."""
        res = env_spine.active_repertoire_and_typed_invention(**kwargs)
        ok = bool(res.get("pass"))
        self._record_cluster("wave35_active_repertoire", tier="TIER_0_ACTIVE_REPERTOIRE_CEGIS_T", passed=ok)
        return res

    def status_summary(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "memory": self.memory_bus.stats(),
            "drift": self.memory_bus.drift_status() if self._memory_bus is not None else {"streams": {}},
            "cluster_stats": dict(self.cluster_stats),
        }
