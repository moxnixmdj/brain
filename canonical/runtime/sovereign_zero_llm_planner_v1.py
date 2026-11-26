#!/usr/bin/env python3
"""Sovereign Zero-LLM Planner V1 — extracted from `brain_unified_model_v1` for zero-cost cold import."""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[2]


def open_model(*args: Any, **kwargs: Any) -> Any:
    from canonical.runtime.brain_unified_model_v1 import open_model as _open_model

    return _open_model(*args, **kwargs)


class SovereignZeroLLMPlanner:
    """First-Principles Active-Inference + MCTS (`decision_core_v1`) Zero-LLM (`K3 = 0`) Agent for `solve_v1`.

    Eliminates static probability dictionaries, 1-step greedy ranking, and inline `exec` scripts:
      1. Grounded Belief & Causal Learning: Every option's pass probability and epistemic entropy are
         computed online by `EpistemicSelfBeliefEngine` (with conjunctive predicate invention) and settled
         against actual outcomes (`seeing['last']`), while `CausalWorldGraph` learns `(Pre, Prod, Dest)`
         transitions and inhibits destructive actions.
      2. Dynamic World Affordances: Options are synthesized dynamically from live workspace topology
         (truncated/hidden configs, test suites, Python modules, executable CLI tools, flywheel primers,
         routed UnifiedModel capabilities, and postcondition writes).
      3. Multi-Step MCTS Lookahead (`decision_core_v1.search`): Runs UCB tree search (`Node`, `search`,
         `best_action`, `best_trajectory`) over abstract world-state transitions minimizing Expected Free
         Energy (pragmatic goal satisfaction + epistemic information gain - execution cost).
      4. Cross-Episode Skill & Concept Compounding: Verified Python repairs abstract reusable primitives into
         `CompoundingConceptLibrary` and elevate causal action traces via `causal_trace_to_skill_compiler_v1`.
    """

    def __init__(self, state_dir: Path | str | None = None) -> None:
        self._episodes: dict[str, dict[str, Any]] = {}
        self._state_dir = Path(state_dir).resolve() if state_dir is not None else None
        self._core: Any = None
        self.last_mcts_summary: dict[str, Any] = {}

    def _cognitive_core(self) -> Any:
        if self._state_dir is not None:
            if self._core is None:
                from canonical.swe_kernel.sentient_cognitive_core_v1 import SentientCognitiveCore

                self._core = SentientCognitiveCore(self._state_dir)
            return self._core
        from canonical.swe_kernel.sentient_cognitive_core_v1 import shared_cognitive_core

        return shared_cognitive_core(None)

    def organ_graph(self) -> Any:
        """Access the unified 5-stratum `MetaCircularOrganGraph` (`P_t`)."""
        return self._cognitive_core().organ_graph

    def epistemic_portfolio_status(self) -> dict[str, Any]:
        """Inspect readiness of the unified zero-model epistemic portfolio (`K3 = 0`)."""
        from canonical.swe_kernel import unified_epistemic_portfolio_v1 as _uep

        return _uep.organ_portfolio_status()

    def act_on_interface(self, instruction: str, **kwargs: Any) -> dict[str, Any]:
        """Zero-VLM 5-Tier Computer-Use, WebMCP & CLI Action-Grammar dispatcher (`K3 = 0`)."""
        from canonical.swe_kernel import unified_epistemic_portfolio_v1 as _uep

        return _uep.act_on_interface_unified(instruction, **kwargs)

    def explore_unknown_environment(self, env: Any, actions: Sequence[Any], *, is_goal: Any = None, **kwargs: Any) -> dict[str, Any]:
        """Zero-instruction interactive POMDP / trace-quotient explorer (`K3 = 0`)."""
        from canonical.swe_kernel import unified_epistemic_portfolio_v1 as _uep

        return _uep.explore_unknown_environment_unified(env, actions, is_goal=is_goal, **kwargs)

    def verify_patch_uncheatable(
        self,
        workspace_dir: str | Path,
        patched_files: Mapping[str, str],
        pytest_targets: Sequence[str],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Uncheatable behavioural diff-mutation & structural-specification gate (`K3 = 0`)."""
        from canonical.swe_kernel import unified_epistemic_portfolio_v1 as _uep

        return _uep.verify_patch_uncheatable(workspace_dir, patched_files, pytest_targets, **kwargs)

    def induce_hypothesis_and_vocabulary(
        self,
        points: Sequence[tuple[Any, Any]] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Symbolic/piecewise hypothesis fitting, active query design, and vocabulary induction (`K3 = 0`)."""
        from canonical.swe_kernel import unified_epistemic_portfolio_v1 as _uep

        return _uep.induce_hypothesis_and_vocabulary_unified(points, **kwargs)

    def teach_edit_by_example(
        self,
        target_source: str,
        before_example: str,
        after_example: str,
    ) -> dict[str, Any]:
        """1-shot structural AST transformation transfer (`edit_by_example_v1`, `K3 = 0`)."""
        from canonical.swe_kernel import unified_epistemic_portfolio_v1 as _uep

        return _uep.teach_edit_by_example_unified(target_source, before_example, after_example)

    def fast_associate_and_adapt(
        self,
        query_or_key: str,
        *,
        observe_payload: Any | None = None,
        utility: float = 1.0,
        credit_verified: bool = True,
        top_k: int = 3,
    ) -> dict[str, Any]:
        """64-bit Hyperdimensional SimHash VSA + Sherman-Morrison/Woodbury + Bi-Temporal PPR fast adapter (`K3 = 0`)."""
        from canonical.swe_kernel import unified_epistemic_portfolio_v1 as _uep

        mem = getattr(self, "_vsa_woodbury_mem", None)
        if mem is None:
            mem = _uep.VSAWoodburyFastMemory()
            self._vsa_woodbury_mem = mem
        if observe_payload is not None:
            mem.observe(query_or_key, observe_payload, utility=utility, credit_verified=credit_verified)
        return mem.query(query_or_key, top_k=top_k)

    def decide_one_shot_sufficiency(self, **kwargs: Any) -> dict[str, Any]:
        """Decidable 1-shot demonstration sufficiency, hidden-precondition abduction & active experiment compiler (`K3 = 0`)."""
        from canonical.swe_kernel import unified_epistemic_portfolio_v1 as _uep

        return _uep.decide_one_shot_sufficiency_and_experiment(**kwargs)

    def compose_and_calibrate_skills(
        self,
        source_text: str,
        before_after_lessons: Sequence[tuple[str, str]],
        *,
        target_language: str = "python",
        pure_organ_source: str | None = None,
    ) -> dict[str, Any]:
        """Proved skill composition (`proved_composition_v1`), diagnostic scope calibration & 7-language CST transfer (`K3 = 0`)."""
        from canonical.swe_kernel import unified_epistemic_portfolio_v1 as _uep

        return _uep.compose_and_calibrate_verified_skills(
            source_text,
            before_after_lessons,
            target_language=target_language,
            pure_organ_source=pure_organ_source,
        )

    def pre_sieve_meaning_ir(
        self,
        baseline_source: str,
        candidate_sources: Sequence[str],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Microsecond Guarded Region-SSA Meaning-IR deduplicator & forward-backward abstract simulator (`K3 = 0`)."""
        from canonical.swe_kernel import unified_epistemic_portfolio_v1 as _uep

        return _uep.pre_sieve_and_simulate_meaning_ir(baseline_source, candidate_sources, **kwargs)

    def organ_portfolio_status(self) -> dict[str, Any]:
        """Inspect readiness of all 96 unified SWE, tools & runtime organs (`K3 = 0`)."""
        from canonical.swe_kernel import unified_epistemic_portfolio_v1 as _uep

        return _uep.organ_portfolio_status()

    def learn_mealy_interface(
        self,
        oracle_fn: Any,
        alphabet: Sequence[str],
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Actively learn an unknown finite-state environment via separating words (`minimal_experiment_v1`)."""
        from canonical.swe_kernel import unified_epistemic_portfolio_v1 as _uep

        return _uep.ActiveSymbolicMealyLearner.learn_mealy_interface(oracle_fn, alphabet, **kwargs)

    def extrapolate_global_opportunity(
        self,
        observed_channels: Sequence[Any],
        *,
        goal: str = "",
        target_gap: float | None = None,
        remaining_budget: float = 10.0,
        universe_size_hint: int | None = None,
    ) -> dict[str, Any]:
        """Evaluate global non-local opportunity tail (`OWNER_ACTIVE_GOAL` Law 5)."""
        return self._cognitive_core().evaluate_global_open_world_decision(
            observed_channels,
            goal=goal,
            target_gap=target_gap,
            remaining_budget=remaining_budget,
            universe_size_hint=universe_size_hint,
        )

    @staticmethod
    def _episode_key(goal: str) -> str:
        return hashlib.sha256(goal.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _extract_target_writes(goal: str) -> list[tuple[str, str | None]]:
        """Extract explicit file creation/write clauses without restricting multi-step goals."""
        clauses = [c.strip() for c in re.split(r"(?:;|\band\s+then\b|\bthen\b)", goal, flags=re.IGNORECASE) if c.strip()]
        targets: list[tuple[str, str | None]] = []
        for cl in clauses:
            m_w = re.match(r"^write\s+(.+?)\s+to\s+([A-Za-z0-9_./-]+)\s*[.!]*$", cl, re.IGNORECASE)
            if m_w:
                payload = m_w.group(1).strip().strip("'\"")
                rel_p = m_w.group(2).strip()
                if ".." not in Path(rel_p).parts and not rel_p.startswith("/"):
                    targets.append((rel_p, payload))
                continue
            m_c = re.match(r"^(?:create|touch|make)\s+(?:file\s+)?([A-Za-z0-9_./-]+\.[A-Za-z0-9]+)\s*[.!]*$", cl, re.IGNORECASE)
            if m_c:
                rel_p = m_c.group(1).strip()
                if ".." not in Path(rel_p).parts and not rel_p.startswith("/"):
                    targets.append((rel_p, ""))
        return targets

    @staticmethod
    def _extract_mentioned_paths(goal: str) -> list[str]:
        found: list[str] = []
        for m in re.finditer(r"\b([A-Za-z0-9_./-]+\.[A-Za-z0-9]{1,10})\b", goal):
            p = m.group(1).strip()
            if ".." not in Path(p).parts and not p.startswith("/") and p not in found:
                found.append(p)
        return found

    @staticmethod
    def _world_fact_tokens(
        *,
        file_set: set[str],
        probed: bool,
        test_passed: bool | None,
        verified_after_edit: bool,
        writes_satisfied: bool,
        outputs_ready: bool,
    ) -> set[str]:
        facts = {f"file:{f}" for f in file_set}
        if probed:
            facts.add("pred:facts_observed")
        if test_passed is True:
            facts.add("pred:tests_green")
        elif test_passed is False:
            facts.add("pred:tests_red")
        if verified_after_edit:
            facts.add("pred:verified_after_edit")
        if writes_satisfied:
            facts.add("pred:writes_satisfied")
        if outputs_ready:
            facts.add("pred:outputs_ready")
        return facts

    def _consolidate_completed_episode(self, text: str, ep: Mapping[str, Any]) -> None:
        core = self._cognitive_core()
        py_programs = [
            str(src)
            for rel, src in (ep.get("full_files") or {}).items()
            if str(rel).endswith(".py") and not Path(str(rel)).name.startswith("test_") and len(str(src)) >= 20
        ]
        if len(py_programs) >= 2:
            try:
                core.concept_library.sleep_abstract(py_programs)
            except Exception:
                pass
        trace_steps = ep.get("causal_trace") or []
        if trace_steps:
            try:
                from canonical.swe_kernel.causal_trace_to_skill_compiler_v1 import elevate_trace_to_fastest_layer

                elevate_trace_to_fastest_layer({"goal": text, "steps": list(trace_steps)})
            except Exception:
                pass

    def __call__(self, goal: str, seeing: dict[str, Any]) -> str | None:
        text = str(goal or "").strip()
        if not text or not isinstance(seeing, dict):
            return None

        core = self._cognitive_core()
        step = int(seeing.get("step") or 1)
        previews = seeing.get("preview") if isinstance(seeing.get("preview"), dict) else (
            seeing.get("previews") if isinstance(seeing.get("previews"), dict) else {}
        )
        raw_files = seeing.get("tree") if seeing.get("tree") is not None else (seeing.get("files") or ())
        file_list = sorted(raw_files.keys()) if isinstance(raw_files, dict) else sorted(str(x) for x in raw_files)
        file_set = set(file_list)
        last = seeing.get("last") if isinstance(seeing.get("last"), dict) else None
        learned = seeing.get("learned") if isinstance(seeing.get("learned"), dict) else None

        ep_key = self._episode_key(text)
        if step <= 1 or ep_key not in self._episodes:
            self._episodes[ep_key] = {
                "probed": False,
                "full_files": dict(previews),
                "discovered_tasks": [],
                "test_passed": None,
                "test_diagnostics": "",
                "tried": set(),
                "last_action_id": None,
                "last_ticket": None,
                "last_world_facts": set(),
                "verified_after_edit": False,
                "edited_code": False,
                "failures": [],
                "causal_trace": [],
            }
        ep = self._episodes[ep_key]
        for k_p, v_p in previews.items():
            if k_p not in ep["full_files"] or len(str(v_p)) > len(str(ep["full_files"].get(k_p, ""))):
                ep["full_files"][k_p] = str(v_p)

        test_files = [
            f for f in file_list
            if f.endswith(".py") and (Path(f).name.startswith("test_") or Path(f).name.endswith("_test.py"))
        ]
        impl_py_files = [f for f in file_list if f.endswith(".py") and f not in test_files]
        cli_files = [
            f for f in file_list
            if Path(f).suffix in (".sh", ".bin") or (not Path(f).suffix and Path(f).name not in ("Makefile", "Dockerfile", "LICENSE", "README"))
        ]
        config_files = [f for f in file_list if Path(f).suffix in (".json", ".yaml", ".yml", ".toml", ".ini")]
        has_taskfile = any(Path(f).name in ("Makefile", "package.json", "pyproject.toml", "justfile") for f in file_set)
        explicit_writes = self._extract_target_writes(text)
        mentioned_paths = self._extract_mentioned_paths(text)
        expected_outputs = [
            p for p in mentioned_paths
            if p not in file_set and not p.endswith(".py")
        ]

        # Canonical Predicate World Projection (`predicate_world_abstraction_v1`)
        try:
            from canonical.swe_kernel.predicate_world_abstraction_v1 import project_computer_observation

            proj_obs = project_computer_observation(
                {
                    "cwd": ".",
                    "files": {f: {"exists": True, "size": len(str(ep["full_files"].get(f, "")))} for f in file_list[:32]},
                    "stdout": str((last or {}).get("out") or "")[-400:],
                    "stderr": str((last or {}).get("err") or "")[-400:],
                }
            )
            projected_world_preds = {f"obs:{p}" for p in (proj_obs.get("predicates") or ())}
        except Exception:
            projected_world_preds = set()

        # Assimilate outcome of previous action (`seeing["last"]`) & settle Bayesian belief + causal world graph!
        if last is not None:
            out_txt = str(last.get("out") or "")
            err_txt = str(last.get("err") or "")
            exit_c = last.get("exit")
            last_act = ep.get("last_action_id")
            step_ok = (exit_c == 0) and not bool(last.get("timed_out"))
            if "BRAIN_PROBE_JSON:" in out_txt:
                for ln in out_txt.splitlines():
                    if ln.startswith("BRAIN_PROBE_JSON:"):
                        try:
                            pdata = json.loads(ln[len("BRAIN_PROBE_JSON:"):])
                            if isinstance(pdata.get("full_files"), dict):
                                ep["full_files"].update(pdata["full_files"])
                            if isinstance(pdata.get("tasks"), list):
                                ep["discovered_tasks"] = pdata["tasks"]
                            if "test_passed" in pdata:
                                ep["test_passed"] = bool(pdata["test_passed"])
                            if "test_diagnostics" in pdata:
                                ep["test_diagnostics"] = str(pdata["test_diagnostics"])
                            ep["probed"] = True
                        except Exception:
                            pass
            if step_ok and str(last_act or "").startswith(("py_ast_patch_h1", "py_obs_synth_h2", "taskfile_target:")):
                ep["edited_code"] = True
            if step_ok and last_act == "verify_postconditions":
                ep["verified_after_edit"] = True
                ep["test_passed"] = True
            elif not step_ok:
                if last_act:
                    ep["tried"].add(str(last_act))
                try:
                    from canonical.runtime import flywheel_v1 as fw

                    where, why = fw.classify(err_txt or out_txt)
                    ep["failures"].append({"action": last_act, "where": where, "why": why, "err": (err_txt or out_txt)[-400:]})
                except Exception:
                    ep["failures"].append({"action": last_act, "err": (err_txt or out_txt)[-400:]})

            writes_now = bool(explicit_writes) and all(
                rel_p in file_set and (payload is None or payload == "" or str(previews.get(rel_p, "")).strip() == payload)
                for rel_p, payload in explicit_writes
            )
            now_facts = (
                self._world_fact_tokens(
                    file_set=file_set,
                    probed=bool(ep["probed"]),
                    test_passed=ep["test_passed"],
                    verified_after_edit=bool(ep["verified_after_edit"]),
                    writes_satisfied=writes_now,
                    outputs_ready=all(p in file_set for p in expected_outputs),
                )
                | projected_world_preds
            )
            prev_ticket = ep.get("last_ticket")
            if prev_ticket is not None:
                try:
                    core.belief.settle_and_compute_surprise(
                        prev_ticket,
                        outcome_pass=step_ok,
                        inspector=f"solve_v1:{last_act or 'step'}",
                    )
                except Exception:
                    pass
                ep["last_ticket"] = None
            if last_act:
                try:
                    core.world_graph.learn_from_execution(
                        str(last_act),
                        before_state=set(ep.get("last_world_facts") or ()),
                        after_state=now_facts,
                        ok=step_ok,
                        error_text=(err_txt or out_txt)[-300:],
                    )
                    core.record_wake_episode(
                        task_id=f"planner:{last_act}",
                        goal=text,
                        outcome_pass=step_ok,
                        route_id=str(last_act),
                    )
                except Exception:
                    pass
                if step_ok:
                    ep["causal_trace"].append({"action_id": str(last_act), "step": step - 1})

        # Check whether all goal postconditions ALREADY hold in `seeing`!
        writes_satisfied = bool(explicit_writes) and all(
            rel_p in file_set and (payload is None or payload == "" or str(previews.get(rel_p, "")).strip() == payload)
            for rel_p, payload in explicit_writes
        )
        outputs_ready = all(p in file_set for p in expected_outputs)

        if explicit_writes and not test_files and not impl_py_files and writes_satisfied:
            self._consolidate_completed_episode(text, ep)
            return None

        if test_files and ep["probed"] and ep["test_passed"] is True and outputs_ready:
            if not explicit_writes or writes_satisfied:
                self._consolidate_completed_episode(text, ep)
                return None

        if ep["verified_after_edit"] and outputs_ready:
            if not explicit_writes or writes_satisfied:
                self._consolidate_completed_episode(text, ep)
                return None

        last_aid_s = str(ep.get("last_action_id") or "")
        if last is not None and last.get("exit") == 0 and (
            last_aid_s in ("unified_model_solve", "grounded_action_exec", "explicit_writes_exec", "cli_metamorphic_exec")
            or last_aid_s.startswith(("taskfile_target:", "cli_acquire:", "recalled_workflow:"))
        ):
            if not test_files and outputs_ready and (not explicit_writes or writes_satisfied):
                if seeing.get("changed") or writes_satisfied:
                    self._consolidate_completed_episode(text, ep)
                    return None

        # Dynamic World Context Predicates (fed to `EpistemicSelfBeliefEngine` for context-conditioned posteriors!)
        truncated_or_hidden = [
            f for f in file_list
            if (f not in ep["full_files"]) or (len(str(previews.get(f, ""))) >= 580 and len(str(ep["full_files"].get(f, ""))) <= 600)
        ]
        world_ctx: dict[str, bool] = {
            "has_tests": bool(test_files),
            "has_py_impl": bool(impl_py_files),
            "has_config": bool(config_files),
            "has_hidden_bytes": bool(truncated_or_hidden),
            "facts_probed": bool(ep["probed"]),
            "prior_failure": bool(ep["failures"]),
            "has_cli_surface": bool(cli_files),
            "has_taskfile": bool(has_taskfile),
            "has_explicit_writes": bool(explicit_writes),
        }

        current_facts = (
            self._world_fact_tokens(
                file_set=file_set,
                probed=bool(ep["probed"]),
                test_passed=ep["test_passed"],
                verified_after_edit=bool(ep["verified_after_edit"]),
                writes_satisfied=writes_satisfied,
                outputs_ready=outputs_ready,
            )
            | projected_world_preds
        )
        protected_facts = {
            f for f in current_facts
            if f in ("pred:tests_green", "pred:verified_after_edit", "pred:writes_satisfied")
        }

        # ------------------------------------------------------------------
        # Open-Ended Affordance Discovery (zero closed switchboard!)
        # Every discovered affordance carries `(requires_preds, produces_preds, render_fn)`.
        # ------------------------------------------------------------------
        primers = (learned or {}).get("primers") or []
        routed_score = 0.0
        if file_set and "unified_model_solve" not in ep["tried"] and (
            not (test_files and impl_py_files)
            or ("py_ast_patch_h1" in ep["tried"] and "py_obs_synth_h2" in ep["tried"])
        ):
            try:
                routed = open_model().route(text, top_k=1)
                ranked = routed.get("candidates") or routed.get("ranked_capabilities") or []
                if ranked:
                    routed_score = float(ranked[0].get("score") or 0.0)
            except Exception:
                routed_score = 0.0

        repo_root = str(ROOT)
        concept_lib_path = str(core.concept_library.path) if getattr(core.concept_library, "path", None) else ""
        observed_coverage = (
            max(0.1, float(len(file_list) - len(truncated_or_hidden)) / float(max(1, len(file_list))))
            if not ep["probed"] and (truncated_or_hidden or test_files or has_taskfile)
            else 1.0
        )

        def _query_option_belief(
            opt_id: str,
            *,
            verifier_backed: bool,
            local_only: bool = True,
        ) -> tuple[float, float, float]:
            inhibited, _reason = core.world_graph.should_inhibit_action(
                opt_id,
                current_facts=current_facts,
                protected_facts=protected_facts,
            )
            if inhibited:
                return 0.02, 0.0, 100.0
            dist = core.belief.predict_distribution(
                f"planner:{opt_id}",
                host_ready=local_only,
                grounding_complete=bool(ep["probed"]) or not bool(truncated_or_hidden),
                causal_precond_met=True,
                memory_reflex_hit=opt_id.startswith(("flywheel_primer", "recalled_workflow:")),
                strong_verifier=verifier_backed,
                context_predicates=world_ctx,
            )
            cost_m = core.cost_router.score_candidate(
                opt_id,
                expected_gain=1.0,
                default_cost_ms=float(dist.get("expected_latency_ms") or 5.0),
            )
            return (
                float(dist["predicted_pass_probability"]),
                float(dist.get("epistemic_mi_nats") or 0.0),
                float(cost_m["measured_ms"]),
            )

        option_specs: dict[str, dict[str, Any]] = {}

        def _register_affordance(
            opt_id: str,
            *,
            requires_preds: set[str],
            produces_preds: set[str],
            render_fn: Callable[[], str],
            default_latency_ms: float = 5.0,
            verifier_backed: bool = True,
            needs_grounding: bool = False,
        ) -> None:
            if opt_id in ep["tried"]:
                return
            p_pass, ep_mi_nats, meas_ms = _query_option_belief(opt_id, verifier_backed=verifier_backed)
            # Fuse learned CausalWorldGraph effects (`produces` / `destroys`) with structural affordance effects!
            learned_prod = set(core.world_graph.produces.get(opt_id) or ())
            learned_dest = set(core.world_graph.destroys.get(opt_id) or ())
            option_specs[opt_id] = {
                "id": opt_id,
                "requires_preds": frozenset(requires_preds),
                "produces_preds": frozenset(produces_preds | learned_prod),
                "destroys_preds": frozenset(learned_dest),
                "p_pass": p_pass,
                "epistemic_mi_nats": ep_mi_nats,
                "latency_ms": meas_ms if opt_id in core.cost_router._stats else default_latency_ms,
                "needs_grounding": needs_grounding,
                "render_fn": render_fn,
            }

        # Affordance 1: Pure-Stdlib Epistemic World + Taskfile + Test Probe (`confined: True` safe!)
        if not ep["probed"] and bool(truncated_or_hidden or test_files or has_taskfile):
            _register_affordance(
                "epistemic_probe",
                requires_preds=set(),
                produces_preds={"pred:facts_observed"},
                default_latency_ms=4.0,
                verifier_backed=True,
                render_fn=lambda: (
                    "import json, pathlib, re, subprocess, sys\n"
                    "full_files = {}\n"
                    f"for rel in {file_list!r}:\n"
                    "    p = pathlib.Path(rel)\n"
                    "    if p.is_file() and p.stat().st_size <= 65536:\n"
                    "        try:\n"
                    "            raw = p.read_bytes()\n"
                    "            if b'\\x00' not in raw[:512]:\n"
                    "                full_files[rel] = raw.decode('utf-8', 'replace')\n"
                    "        except OSError:\n"
                    "            pass\n"
                    "tasks = []\n"
                    "mk = pathlib.Path('Makefile')\n"
                    "if mk.is_file():\n"
                    "    for ln in mk.read_text(encoding='utf-8', errors='replace').splitlines():\n"
                    "        m = re.match(r'^([A-Za-z0-9_.-]+):', ln)\n"
                    "        if m and not m.group(1).startswith('.'):\n"
                    "            tasks.append({'name': m.group(1), 'command': 'make ' + m.group(1)})\n"
                    "pkg = pathlib.Path('package.json')\n"
                    "if pkg.is_file():\n"
                    "    try:\n"
                    "        scripts = (json.loads(pkg.read_text(encoding='utf-8')).get('scripts') or {})\n"
                    "        for k, v in scripts.items():\n"
                    "            tasks.append({'name': str(k), 'command': str(v)})\n"
                    "    except Exception:\n"
                    "        pass\n"
                    "test_passed = True\n"
                    "diag = ''\n"
                    f"t_files = {test_files!r}\n"
                    "if t_files:\n"
                    "    r = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', '.', '-p', 'test*.py'], capture_output=True, text=True)\n"
                    "    test_passed = (r.returncode == 0)\n"
                    "    diag = ((r.stdout or '') + '\\n' + (r.stderr or ''))[-1200:]\n"
                    "print('BRAIN_PROBE_JSON:' + json.dumps({'full_files': full_files, 'tasks': tasks[:12], 'test_passed': test_passed, 'test_diagnostics': diag}))\n"
                ),
            )

        # Affordance 2: Recalled Flywheel / Transfer Primers
        if primers:
            p_proc = str(primers[0].get("procedure") or "").strip()
            if p_proc:
                _register_affordance(
                    "flywheel_primer",
                    requires_preds=set(),
                    produces_preds={"pred:code_candidate_ready", "pred:goal_acted"},
                    default_latency_ms=3.0,
                    verifier_backed=True,
                    render_fn=lambda prog=p_proc: prog,
                )

        # Affordance 3: Open Taskfile Targets (`Makefile` / `package.json` / `pyproject.toml` discovered at runtime!)
        goal_low = text.lower()
        for t_row in (ep.get("discovered_tasks") or [])[:6]:
            if not isinstance(t_row, Mapping):
                continue
            t_nm = str(t_row.get("name") or "").strip()
            t_cmd = str(t_row.get("command") or "").strip().lstrip("@")
            if t_nm and t_cmd and re.search(rf"\b{re.escape(t_nm.lower())}\b", goal_low):
                aid_t = f"taskfile_target:{t_nm}"
                _register_affordance(
                    aid_t,
                    requires_preds=set(),
                    produces_preds={"pred:goal_acted", "pred:outputs_ready"},
                    default_latency_ms=8.0,
                    verifier_backed=True,
                    render_fn=lambda cmd=t_cmd: (
                        "import subprocess, sys\n"
                        f"r = subprocess.run({cmd!r}, shell=True, capture_output=True, text=True)\n"
                        "if r.returncode != 0:\n"
                        "    sys.stderr.write((r.stderr or r.stdout or 'task_failed')[-800:])\n"
                        "    raise SystemExit(1)\n"
                    ),
                )

        # Affordance 4: Python AST Patch Search, HORS Observational Synthesis & Independent Test Verification
        if test_files and impl_py_files:
            if ep["edited_code"] and not ep["verified_after_edit"]:
                _register_affordance(
                    "verify_postconditions",
                    requires_preds={"pred:code_candidate_ready"},
                    produces_preds={"pred:tests_green", "pred:verified_after_edit"},
                    default_latency_ms=3.5,
                    verifier_backed=True,
                    render_fn=lambda: (
                        "import subprocess, sys\n"
                        "import os as _os, pathlib as _pl\n"
                        "for _d in _pl.Path('.').rglob('__pycache__'):\n"
                        "    for _c in _d.glob('*.pyc'):\n"
                        "        try:\n"
                        "            _c.unlink()\n"
                        "        except OSError:\n"
                        "            pass\n"
                        "_ENV = {**_os.environ, 'PYTHONDONTWRITEBYTECODE': '1'}\n"
                        "r = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', '.', '-p', 'test*.py'], capture_output=True, text=True, env=_ENV)\n"
                        "if r.returncode != 0:\n"
                        "    sys.stderr.write((r.stderr or r.stdout or 'verification_failed')[-800:])\n"
                        "    raise SystemExit(1)\n"
                    ),
                )
            def _render_h1_confined() -> str:
                # Pure-stdlib confined AST single-operator / constant-sign repair search (`confined_v1` safe — zero external imports!)
                return (
                    "import ast, copy, pathlib, subprocess, sys\n"
                    "import os as _os, pathlib as _pl\n"
                    "for _d in _pl.Path('.').rglob('__pycache__'):\n"
                    "    for _c in _d.glob('*.pyc'):\n"
                    "        try:\n"
                    "            _c.unlink()\n"
                    "        except OSError:\n"
                    "            pass\n"
                    "_ENV = {**_os.environ, 'PYTHONDONTWRITEBYTECODE': '1'}\n"
                    "def _test_ok():\n"
                    "    r = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', '.', '-p', 'test*.py'], capture_output=True, text=True, env=_ENV)\n"
                    "    return r.returncode == 0, (r.stderr or r.stdout or '')[-800:]\n"
                    "ok0, err0 = _test_ok()\n"
                    "if ok0:\n"
                    "    raise SystemExit(0)\n"
                    "SWAP_BIN = {ast.Add: ast.Sub, ast.Sub: ast.Add, ast.Mult: ast.FloorDiv, ast.FloorDiv: ast.Mult}\n"
                    "SWAP_CMP = {ast.Lt: ast.LtE, ast.LtE: ast.Lt, ast.Gt: ast.GtE, ast.GtE: ast.Gt, ast.Eq: ast.NotEq, ast.NotEq: ast.Eq}\n"
                    "patched = False\n"
                    f"for rel in {impl_py_files!r}:\n"
                    "    p = pathlib.Path(rel)\n"
                    "    if not p.is_file():\n"
                    "        continue\n"
                    "    orig = p.read_text(encoding='utf-8')\n"
                    "    try:\n"
                    "        tree = ast.parse(orig)\n"
                    "    except SyntaxError:\n"
                    "        continue\n"
                    "    nodes = list(ast.walk(tree))\n"
                    "    for idx, nd in enumerate(nodes):\n"
                    "        cand_trees = []\n"
                    "        if isinstance(nd, ast.BinOp) and type(nd.op) in SWAP_BIN:\n"
                    "            t2 = copy.deepcopy(tree)\n"
                    "            list(ast.walk(t2))[idx].op = SWAP_BIN[type(nd.op)]()\n"
                    "            cand_trees.append(t2)\n"
                    "        elif isinstance(nd, ast.Compare) and len(nd.ops) == 1 and type(nd.ops[0]) in SWAP_CMP:\n"
                    "            t2 = copy.deepcopy(tree)\n"
                    "            list(ast.walk(t2))[idx].ops[0] = SWAP_CMP[type(nd.ops[0])]()\n"
                    "            cand_trees.append(t2)\n"
                    "        for ct in cand_trees:\n"
                    "            ast.fix_missing_locations(ct)\n"
                    "            p.write_text(ast.unparse(ct) + '\\n', encoding='utf-8')\n"
                    "            ok_c, _ = _test_ok()\n"
                    "            if ok_c:\n"
                    "                patched = True\n"
                    "                break\n"
                    "        if patched:\n"
                    "            break\n"
                    "    if not patched:\n"
                    "        p.write_text(orig, encoding='utf-8')\n"
                    "    else:\n"
                    "        break\n"
                    "ok_f, err_f = _test_ok()\n"
                    "if not ok_f:\n"
                    "    sys.stderr.write(err_f or 'patch_h1_failed')\n"
                    "    raise SystemExit(1)\n"
                )

            def _render_h2_confined() -> str:
                # In-process HORS + ConceptLibrary synthesis over observed `ep["full_files"]`, emitting pure-stdlib confined write+verify!
                import ast as _ast
                from canonical.runtime.swe_observational_program_synthesizer_v1 import (
                    extract_io_examples_from_test_source,
                    synthesize_python_function_body,
                )
                from canonical.swe_kernel import whitebox_introspector_and_trace_synthesizer_v1 as wits

                full_map = dict(ep.get("full_files") or {})
                cfg_consts: list[Any] = []
                for rel_f, raw_txt in full_map.items():
                    if str(rel_f).endswith(".json"):
                        try:
                            obj = json.loads(str(raw_txt))
                            if isinstance(obj, Mapping):
                                for v in obj.values():
                                    if isinstance(v, (int, float, str)) and not isinstance(v, bool):
                                        cfg_consts.append(v)
                        except Exception:
                            pass
                combined_tests = "\n\n".join(str(full_map.get(tf, "")) for tf in test_files if full_map.get(tf))
                patched_files: dict[str, str] = {}
                for imp_rel in impl_py_files:
                    src_txt = str(full_map.get(imp_rel) or "")
                    if not src_txt.strip() or not combined_tests.strip():
                        continue
                    try:
                        imp_tree = _ast.parse(src_txt)
                    except SyntaxError:
                        continue
                    cur_src = src_txt
                    for fn_nd in [nd for nd in imp_tree.body if isinstance(nd, _ast.FunctionDef)]:
                        p_names = [a.arg for a in fn_nd.args.args]
                        exs, t_consts = extract_io_examples_from_test_source(combined_tests, fn_nd.name)
                        valid_exs = [ex for ex in exs if len(ex[0]) == len(p_names)]
                        if not valid_exs:
                            continue
                        merged_c = list(dict.fromkeys([*cfg_consts, *t_consts]))[:16]
                        body_code = synthesize_python_function_body(
                            p_names,
                            valid_exs,
                            extra_constants=merged_c,
                            max_weight=4,
                            concept_library=core.concept_library,
                        )
                        if not body_code:
                            # Ensemble fallback (plan v5 move 2): OE + stochastic
                            # union for shapes the observational grammar cannot
                            # express at this budget (measured: branch-using
                            # programs at max_weight 4..8, ten configs, all miss;
                            # the union finds and verifies them in ~190 ms).
                            # Every returned body is already verified against ALL
                            # extracted examples, so a miss costs ~200 ms where
                            # the affordance otherwise had no candidate at all --
                            # it cannot slow a step that would have failed.
                            from canonical.runtime.stochastic_synthesizer_v1 import (
                                numeric_concept_templates,
                                synthesize_body_from_examples,
                            )
                            body_code = synthesize_body_from_examples(
                                p_names, valid_exs,
                                # Learned grammar (v6 section 14): the concept
                                # library's admitted templates are atoms this
                                # enumerator cannot build at any depth. Read
                                # only -- nothing here mutates the library.
                                concepts=numeric_concept_templates(
                                    getattr(core, "concept_library", None),
                                ),
                            )
                        if body_code:
                            upd = wits._replace_function_body_in_source(cur_src, fn_nd.name, body_code)
                            if upd:
                                cur_src = upd
                    if cur_src != src_txt:
                        patched_files[imp_rel] = cur_src

                lines = ["import pathlib, subprocess, sys",
                         "import os as _os",
                         "for _d in pathlib.Path('.').rglob('__pycache__'):",
                         "    for _c in _d.glob('*.pyc'):",
                         "        try:",
                         "            _c.unlink()",
                         "        except OSError:",
                         "            pass",
                         "_ENV = {**_os.environ, 'PYTHONDONTWRITEBYTECODE': '1'}"]
                for rel_p, new_src in sorted(patched_files.items()):
                    lines.append(f"pathlib.Path({rel_p!r}).write_text({new_src!r}, encoding='utf-8')")
                lines.extend(
                    [
                        "r = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', '.', '-p', 'test*.py'], capture_output=True, text=True, env=_ENV)",
                        "if r.returncode != 0:",
                        "    sys.stderr.write((r.stderr or r.stdout or 'obs_synth_h2_failed')[-800:])",
                        "    raise SystemExit(1)",
                    ]
                )
                return "\n".join(lines) + "\n"

            _register_affordance(
                "py_ast_patch_h1",
                requires_preds=set(),
                produces_preds={"pred:code_candidate_ready", "pred:tests_green", "pred:verified_after_edit"},
                default_latency_ms=7.0,
                verifier_backed=True,
                needs_grounding=True,
                render_fn=_render_h1_confined,
            )
            _register_affordance(
                "py_obs_synth_h2",
                requires_preds=set(),
                produces_preds={"pred:code_candidate_ready", "pred:tests_green", "pred:verified_after_edit"},
                default_latency_ms=14.0,
                verifier_backed=True,
                needs_grounding=True,
                render_fn=_render_h2_confined,
            )

        # Affordance 5: Explicit Artifact Emit
        if explicit_writes and not writes_satisfied:
            def _render_writes() -> str:
                lines = ["import pathlib"]
                for idx_w, (rel_p, payload) in enumerate(explicit_writes):
                    content_str = (payload + "\n") if payload else ""
                    lines.append(f"_p{idx_w} = pathlib.Path({rel_p!r})")
                    lines.append(f"_p{idx_w}.parent.mkdir(parents=True, exist_ok=True)")
                    lines.append(f"_p{idx_w}.write_text({content_str!r}, encoding='utf-8')")
                return "\n".join(lines) + "\n"

            _register_affordance(
                "explicit_writes_exec",
                requires_preds=set(),
                produces_preds={"pred:writes_satisfied", "pred:outputs_ready"},
                default_latency_ms=4.5,
                verifier_backed=True,
                render_fn=_render_writes,
            )

        # Affordance 6: Open CLI Metamorphic & Documentation Discovery (`world_probe_v1` + `documentation_mining_v1` + `grounded_action_v1`)
        if cli_files and not test_files:
            _register_affordance(
                "cli_metamorphic_exec",
                requires_preds=set(),
                produces_preds={"pred:goal_acted", "pred:outputs_ready"},
                default_latency_ms=11.0,
                verifier_backed=True,
                render_fn=lambda: (
                    "import pathlib, sys\n"
                    f"sys.path.insert(0, {repo_root!r})\n"
                    "from canonical.runtime import world_probe_v1 as wp, grounded_action_v1 as ga\n"
                    "ws = pathlib.Path('.').resolve()\n"
                    f"wp.established_facts([], goal={text!r}, goal_paths={cli_files!r}, root=ws)\n"
                    f"_out = ga.act({text!r}, root=ws)\n"
                    "if not _out.get('ok'):\n"
                    "    raise SystemExit(1)\n"
                ),
            )

        # Affordance 7: Grounded World Action & Compiled UnifiedModel Capability Route
        if file_set:
            _register_affordance(
                "grounded_action_exec",
                requires_preds=set(),
                produces_preds={"pred:goal_acted", "pred:outputs_ready"},
                default_latency_ms=20.0,
                verifier_backed=False,
                needs_grounding=True,
                render_fn=lambda: (
                    "import pathlib, sys\n"
                    f"sys.path.insert(0, {repo_root!r})\n"
                    "from canonical.runtime import grounded_action_v1 as ga\n"
                    f"_out = ga.act({text!r}, root=pathlib.Path('.').resolve())\n"
                    "if not _out.get('ok'):\n"
                    "    raise SystemExit(1)\n"
                ),
            )
            if routed_score > 0.0:
                _register_affordance(
                    "unified_model_solve",
                    requires_preds=set(),
                    produces_preds={"pred:goal_acted", "pred:outputs_ready"},
                    default_latency_ms=22.0,
                    verifier_backed=True,
                    needs_grounding=True,
                    render_fn=lambda: (
                        "import sys\n"
                        f"sys.path.insert(0, {repo_root!r})\n"
                        "from canonical.runtime.brain_unified_model_v1 import open_model\n"
                        f"_res = open_model().solve({text!r}, declared_resources={file_list!r})\n"
                        "if not _res.get('pass'):\n"
                        "    raise SystemExit(1)\n"
                    ),
                )

        if not option_specs:
            return None

        # ------------------------------------------------------------------
        # Open-Predicate Active-Inference MCTS (`decision_core_v1`)
        # State = `(frozenset[predicate_str], frozenset[used_action_id])`
        # Value = Parameter-free Expected Free Energy in nats (`I(Y;Theta|s,a) + delta_goal - tau/budget`)
        # ------------------------------------------------------------------
        from canonical.runtime import decision_core_v1 as dc

        needs_tests = bool(test_files and impl_py_files)
        needs_writes = bool(explicit_writes)
        needs_generic_act = not needs_tests and not needs_writes
        has_hidden_world = bool(truncated_or_hidden or (test_files and not ep["probed"]) or (has_taskfile and not ep["probed"]))

        goal_predicates: set[str] = set()
        if needs_tests:
            goal_predicates.add("pred:tests_green")
            goal_predicates.add("pred:verified_after_edit")
        if needs_writes:
            goal_predicates.add("pred:writes_satisfied")
        if needs_generic_act:
            goal_predicates.add("pred:goal_acted")

        init_preds = set(current_facts)
        if not has_hidden_world:
            init_preds.add("pred:facts_observed")
        if ep["edited_code"] or (ep["test_passed"] is True):
            init_preds.add("pred:code_candidate_ready")
        if ep["verified_after_edit"] or (ep["probed"] and ep["test_passed"] is True):
            init_preds.add("pred:tests_green")
            init_preds.add("pred:verified_after_edit")
        if writes_satisfied:
            init_preds.add("pred:writes_satisfied")

        init_mcts_state = (frozenset(init_preds), frozenset(ep["tried"]))
        total_latency_budget_ms = max(
            40.0,
            sum(float(sp["latency_ms"]) for sp in option_specs.values()) * 2.0,
        )
        hidden_info_nats = math.log(2.0) * min(3.0, float(len(truncated_or_hidden) + len(test_files) + (1 if has_taskfile else 0)))

        def _is_goal_state(st: tuple[frozenset[str], frozenset[str]]) -> bool:
            preds, _used = st
            return bool(goal_predicates) and goal_predicates.issubset(preds)

        def _actions_fn(node: Any) -> list[str]:
            st = node.state
            if _is_goal_state(st) or node.depth >= 4:
                return []
            preds, used = st
            specialist_exhausted = ("py_ast_patch_h1" in used and "py_obs_synth_h2" in used)
            avail: list[str] = []
            for oid, spec in option_specs.items():
                if oid in used:
                    continue
                req_p = spec["requires_preds"]
                if req_p and not req_p.issubset(preds):
                    continue
                prod_p = spec["produces_preds"]
                # Skip pure observation once workspace facts are already observed
                if oid == "epistemic_probe" and "pred:facts_observed" in preds:
                    continue
                # Skip actions that produce zero new predicates toward the open world/goal
                if prod_p.issubset(preds):
                    continue
                if oid in ("grounded_action_exec", "unified_model_solve") and needs_tests and not specialist_exhausted:
                    continue
                avail.append(oid)
            if (
                needs_tests
                and "pred:code_candidate_ready" in preds
                and "pred:verified_after_edit" not in preds
                and "verify_postconditions" not in used
                and "verify_postconditions" not in avail
            ):
                avail.append("verify_postconditions")
            return avail

        def _make_state(st: tuple[frozenset[str], frozenset[str]], action_id: str) -> tuple[frozenset[str], frozenset[str]]:
            preds, used = st
            nxt_used = used | {action_id}
            spec = option_specs.get(action_id)
            if spec is None:
                # Virtual postcondition verification transition after repair in rollout
                nxt_p = set(preds)
                if "pred:code_candidate_ready" in preds:
                    nxt_p.update(("pred:tests_green", "pred:verified_after_edit"))
                return (frozenset(nxt_p), nxt_used)
            prod_p = set(spec["produces_preds"])
            # Ungrounded code edits before observing hidden test/source bytes require explicit verification!
            if "pred:facts_observed" not in preds and action_id in ("py_ast_patch_h1", "py_obs_synth_h2", "flywheel_primer"):
                prod_p.discard("pred:tests_green")
                prod_p.discard("pred:verified_after_edit")
            nxt_p = (set(preds) | prod_p) - set(spec["destroys_preds"])
            return (frozenset(nxt_p), nxt_used)

        virtual_verify_p, virtual_verify_mi, virtual_verify_ms = _query_option_belief("verify_postconditions", verifier_backed=True)

        def _step_efe_utility(
            prev_st: tuple[frozenset[str], frozenset[str]],
            aid: str,
            cur_st: tuple[frozenset[str], frozenset[str]],
            survival_p: float,
        ) -> tuple[float, float]:
            prev_preds, _ = prev_st
            cur_preds, _ = cur_st
            spec = option_specs.get(aid) or {
                "p_pass": virtual_verify_p,
                "epistemic_mi_nats": virtual_verify_mi,
                "latency_ms": virtual_verify_ms,
                "needs_grounding": False,
            }
            p_step = float(spec["p_pass"])
            if spec.get("needs_grounding") and "pred:facts_observed" not in prev_preds:
                p_step *= observed_coverage

            # 1. Epistemic Information Gain in nats (`I(Y; Theta | s, a)` + unobserved-world Shannon entropy reduction)
            info_gain_nats = float(spec["epistemic_mi_nats"])
            if "pred:facts_observed" in cur_preds and "pred:facts_observed" not in prev_preds:
                info_gain_nats += hidden_info_nats

            # 2. Pragmatic Goal Satisfaction Gain (dimensionless fraction of `goal_predicates` newly achieved)
            n_goal = float(max(1, len(goal_predicates)))
            sat_before = float(len(goal_predicates & prev_preds)) / n_goal
            sat_after = float(len(goal_predicates & cur_preds)) / n_goal
            pragmatic_gain = max(0.0, sat_after - sat_before)

            # 3. Mortality / Latency Fraction (`tau_a / tau_budget`)
            mortality_cost = float(spec["latency_ms"]) / total_latency_budget_ms

            nxt_survival = survival_p * p_step
            neg_efe = survival_p * info_gain_nats + nxt_survival * pragmatic_gain - mortality_cost
            return nxt_survival, neg_efe

        def _evaluate_fn(node: Any) -> float:
            if node.depth == 0 or node.action is None:
                return 0.0
            chain: list[Any] = []
            cur = node
            while cur is not None and cur.parent is not None:
                chain.append(cur)
                cur = cur.parent
            chain.reverse()

            survival_p = 1.0
            total_neg_efe = 0.0
            for step_nd in chain:
                survival_p, dv = _step_efe_utility(step_nd.parent.state, str(step_nd.action), step_nd.state, survival_p)
                total_neg_efe += dv

            sim_st = node.state
            sim_depth = node.depth
            while not _is_goal_state(sim_st) and sim_depth < 4:
                dummy = dc.Node(state=sim_st)
                dummy.parent = node
                cand_a = [a for a in _actions_fn(dummy) if a not in sim_st[1]]
                if not cand_a:
                    break
                best_a = max(
                    cand_a,
                    key=lambda a: _step_efe_utility(sim_st, a, _make_state(sim_st, a), survival_p)[1],
                )
                nxt_st = _make_state(sim_st, best_a)
                survival_p, dv = _step_efe_utility(sim_st, best_a, nxt_st, survival_p)
                total_neg_efe += dv
                sim_st = nxt_st
                sim_depth += 1

            if _is_goal_state(node.state):
                node.terminal = True
            if _is_goal_state(sim_st):
                total_neg_efe += survival_p
            # Map unbounded negative-EFE nats smoothly onto `(0, 1)` via logistic link `1 / (1 + exp(-x))` (zero magic constants!)
            return 1.0 / (1.0 + math.exp(-max(-8.0, min(8.0, total_neg_efe))))

        def _reflect_fn(node: Any) -> str:
            return f"efe_predicate_mcts:{node.action}@depth={node.depth}"

        root = dc.Node(state=init_mcts_state)
        dc.search(
            root,
            _actions_fn,
            _evaluate_fn,
            iterations=max(16, 8 * len(option_specs)),
            c=math.sqrt(2.0),
            make_state=_make_state,
            reflect_fn=_reflect_fn,
        )
        chosen_raw = dc.best_action(root)
        chosen_id = str(chosen_raw) if chosen_raw in option_specs else next(iter(option_specs))
        traj_actions = [str(n.action) for n in dc.best_trajectory(root)[1:] if n.action is not None]
        self.last_mcts_summary = {
            "chosen_action": chosen_id,
            "best_trajectory": traj_actions,
            "goal_predicates": sorted(goal_predicates),
            "initial_predicates_count": len(init_preds),
            "affordances_discovered": sorted(option_specs.keys()),
            "root_visits": root.visits,
            "child_stats": {
                str(ch.action): {"visits": ch.visits, "mean_value": round(ch.mean_value, 4)}
                for ch in root.children
            },
        }

        # Issue pre-action `PredictionTicket` & render directly from the winning `AffordanceSpec` (zero switchboard!)
        ep["last_action_id"] = chosen_id
        ep["last_world_facts"] = set(current_facts)
        ep["tried"].add(chosen_id)
        try:
            ep["last_ticket"] = core.belief.predict_before_act(
                f"planner:{chosen_id}",
                host_ready=True,
                grounding_complete=bool(ep["probed"]) or not bool(truncated_or_hidden),
                causal_precond_met=True,
                memory_reflex_hit=chosen_id.startswith(("flywheel_primer", "recalled_workflow:")),
                strong_verifier=True,
                context_predicates=world_ctx,
            )
        except Exception:
            ep["last_ticket"] = None

        winning_spec = option_specs.get(chosen_id)
        if winning_spec is None or not callable(winning_spec.get("render_fn")):
            return None
        return str(winning_spec["render_fn"]())


_SOVEREIGN_PLANNER = SovereignZeroLLMPlanner()


def brain_model_callable(goal: str, seeing: dict[str, Any]) -> str | None:
    """Zero-LLM (`K3 = 0`) multi-step `BRAIN_MODEL` callable conforming to `canonical.runtime.model_v1`."""
    return _SOVEREIGN_PLANNER(goal, seeing)
