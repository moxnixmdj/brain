#!/usr/bin/env python3
"""Unified Fast Spine v1 — Elon's Law Unification of Brain's Verified Zero-Model Fast Organs.

Zero re-implementation, zero giant-model calls (`model_calls = 0`, `$0.00`), sub-millisecond
to millisecond hot paths. Wires previously-isolated ("DARK") repo primitives into ONE fast
spine shared by `UnifiedModel` (`wave53_54`), `harbor_swe_zero_model_agent_v1.py`, and
`swebench_pro_v2_agent.py`:

  - Job 1a (Zero-Build Code Localization): `canonical.swe_kernel.bm25_code_localizer_v1`
  - Job 1b (Causal Producer-Lineage Blame): `canonical.swe_kernel.producer_lineage_graph_v1`
  - Job 2  (Instant Hybrid Memory): `DominoMemory` (BM25 + char-ngrams + date resolution) +
            `DBSPBiTemporalPPRMemory` (13 us bi-temporal Z-set retraction & PPR multi-hop)
  - Job 3  (Anti-Lie CoW Verification): `FastCoWVerifier` (`os.fork()` 1.47 ms/candidate)
  - Job 4  (Skill Compilation & Edit Basis): `induced_edit_basis_v1` +
            `causal_trace_to_skill_compiler_v1`
  - Job 5a (Interactive World Model): `MinimalArc3Agent` (Object-Centric Active Moore-Machine)
  - Job 6a (Prior & Micro-Model Repair): `PriorRepairEngine` + `LocalMicroModelBackend`
"""
from __future__ import annotations

import difflib
import pathlib
import re
import time
import zlib
from collections import defaultdict
from typing import Any, Mapping, Sequence

SCHEMA = "BRAIN_UNIFIED_FAST_SPINE_V1"
PRODUCER_MODEL_CALLS = 0

_ENTITY_TOKEN_RE = re.compile(r"\b[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})?\b")
_STOP_ENTITIES = frozenset({
    "The", "This", "That", "There", "Their", "They", "What", "When", "Where",
    "Which", "While", "Who", "Why", "How", "Yes", "Yeah", "Sure", "Well",
    "Actually", "Really", "Just", "Also", "Maybe", "Today", "Tomorrow",
    "Yesterday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
    "Saturday", "Sunday", "January", "February", "March", "April", "May",
    "June", "July", "August", "September", "October", "November", "December",
    "Hey", "Hello", "Thanks", "Thank", "Awesome", "Great", "Good", "Nice",
    "Sounds", "Hope", "Have", "Did", "Does", "Would", "Could", "Should",
})


_COMP_TOK_RE = re.compile(r"[a-z0-9']+")
_COMP_STOP = frozenset(
    "the a an is are was were be been being to of in on at for with and or that this it as by "
    "from did do does has have had what when where who how why would could should will can into "
    "about than then them they their there here just also very much more most some any its our "
    "you your we me my i'm it's don't didn't that's he's she's they're we're you're i've".split()
)


def _content_bytes_for_comp(text: str) -> bytes:
    """Stopword-filtered content bytes for zero-parameter zlib Normalized Compression Gain."""
    toks = [w for w in _COMP_TOK_RE.findall(str(text or "").lower()) if len(w) >= 2 and w not in _COMP_STOP]
    return (" ".join(toks)).encode("utf-8", "ignore")[:320]


class InstantContinualMemory:
    """Unified zero-weight continual-learning & concept-drift memory engine.

    Unifies 4 previously-isolated / DARK organs under ONE external, inspectable,
    editable, deletable (`parameters_stored = 0`, `model_calls = 0`) interface:
      1. `DBSPBiTemporalPPRMemory` — 13 us bi-temporal Z-set retraction (0% stale leakage).
      2. `instant_condition_store_v1` + `applicability_v1` — single-counterexample version-space narrowing.
      3. `instant_cu_procedure_store_v1` — hole-abstracted, path-safe computer-use procedure induction & refutation.
      4. `DualDriftDetector` (`canonical_memory_crystallizer_v1`) — statistical concept-drift signaling.
    """

    def __init__(self) -> None:
        from canonical.runtime import instant_condition_store_v1 as ics
        from canonical.runtime import instant_cu_procedure_store_v1 as icu
        from canonical.runtime.hidden_arsenal_unifier_v1 import DBSPBiTemporalPPRMemory
        from canonical.swe_kernel.canonical_memory_crystallizer_v1 import DualDriftDetector

        self.dbsp = DBSPBiTemporalPPRMemory()
        self.condition_store: dict[str, Any] = ics.new_store()
        self.cu_store: dict[str, Any] = icu.new_store()
        self.drift_detector = DualDriftDetector()
        self._action_observations: dict[str, list[tuple[frozenset[str], bool]]] = defaultdict(list)

    # --- 1. Bi-Temporal Exact Fact Upsert / Retraction (DBSP Z-Sets) ---
    def assert_fact(
        self,
        subject: str,
        predicate: str,
        obj: str,
        *,
        t_valid: int = 1,
        supersede: bool = True,
    ) -> dict[str, Any]:
        """Insert a fact; when `supersede=True`, cleanly closes prior `(subject, predicate)` slot (0% stale leakage)."""
        return self.dbsp.apply_zset_deltas(
            [(str(subject), str(predicate), str(obj), int(t_valid), None, +1)],
            supersede_slot=supersede,
        )

    def retract_fact(
        self,
        subject: str,
        predicate: str,
        obj: str,
        *,
        t_valid: int = 1,
    ) -> dict[str, Any]:
        return self.dbsp.apply_zset_deltas(
            [(str(subject), str(predicate), str(obj), int(t_valid), None, -1)],
            supersede_slot=False,
        )

    def current_slot_values(self, subject: str, predicate: str, *, t_valid: int | None = None) -> list[str]:
        """Return exact active object(s) for `(subject, predicate)` at `t_valid` (or latest slot)."""
        s, p = str(subject), str(predicate)
        if t_valid is None:
            active = self.dbsp._active_by_slot.get((s, p))
            if active is not None and self.dbsp._weights.get(active, 0) > 0:
                return [str(active[2])]
        out: list[str] = []
        adj_s = self.dbsp._adj.get(s) or {}
        for (rel, obj, ts, te), w in adj_s.items():
            if w <= 0 or rel != p:
                continue
            if t_valid is None:
                if te >= 2_147_483_647:
                    out.append(str(obj))
            elif ts <= int(t_valid) < te:
                out.append(str(obj))
        return out

    def query_ppr(self, seed: str, *, t_valid: int | None = None, top_k: int = 8) -> dict[str, Any]:
        return self.dbsp.query_ppr(str(seed), t_valid=t_valid, top_k=top_k)

    # --- 2. Instant Condition Learning + Single-Counterexample Narrowing ---
    def observe_action_outcome(
        self,
        argv: Sequence[str],
        observed_facts: Sequence[str],
        *,
        succeeded: bool,
        source: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Update external condition store from one outcome; narrows preconditions on a single counterexample!"""
        from canonical.runtime import applicability_v1 as app
        from canonical.runtime import instant_condition_store_v1 as ics

        key = ics.action_key(argv)
        facts_fs = frozenset(str(f) for f in observed_facts)
        self._action_observations[key].append((facts_fs, bool(succeeded)))
        obs_list = self._action_observations[key]
        src = dict(source or {"origin": "instant_continual_memory"})
        pos = [f for f, ok in obs_list if ok]
        neg = [f for f, ok in obs_list if not ok]
        if len(pos) == 1 and not neg:
            return ics.record_one_success(self.condition_store, argv, facts_fs, source=src)
        if pos and neg:
            boundary = app.learn([(f, True) for f in pos] + [(f, False) for f in neg])
            return ics.upsert_condition(self.condition_store, argv, boundary, source=src)
        if pos:
            common = sorted(set.intersection(*(set(f) for f in pos)))
            return ics.upsert_rule(
                self.condition_store,
                argv,
                required=common,
                condition_status=ics.PROVISIONAL,
                source=src,
            )
        return {"status": ics.UNKNOWN, "action_key": key}

    def check_action_condition(self, argv: Sequence[str], observed_facts: Sequence[str]) -> dict[str, Any]:
        from canonical.runtime import instant_condition_store_v1 as ics
        return ics.choose(self.condition_store, argv, observed_facts)

    def delete_action_condition(self, argv: Sequence[str]) -> bool:
        from canonical.runtime import instant_condition_store_v1 as ics
        key = ics.action_key(argv)
        self._action_observations.pop(key, None)
        return ics.delete(self.condition_store, argv)

    # --- 3. Hole-Abstracted Instant Computer-Use Procedure Store ---
    def induce_cu_procedure(
        self,
        *,
        domain: str,
        goal_kind: str,
        concrete_steps: Sequence[Mapping[str, Any]],
        hole_bindings: Mapping[str, str],
        env_observables: Sequence[str],
        frame_invariants: Sequence[str] = (),
        provenance: Mapping[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        from canonical.runtime import instant_cu_procedure_store_v1 as icu
        return icu.induce_procedure_from_verified_run(
            self.cu_store,
            domain=domain,
            goal_kind=goal_kind,
            concrete_steps=concrete_steps,
            hole_bindings=hole_bindings,
            env_observables=env_observables,
            frame_invariants=frame_invariants,
            provenance=provenance,
        )

    def recall_cu_procedures(
        self,
        *,
        domain: str,
        goal_kind: str,
        env_observables: Sequence[str],
        hole_bindings: Mapping[str, str],
    ) -> list[dict[str, Any]]:
        from canonical.runtime import instant_cu_procedure_store_v1 as icu
        return icu.recall_procedures(
            self.cu_store,
            domain=domain,
            goal_kind=goal_kind,
            env_observables=env_observables,
            hole_bindings=hole_bindings,
        )

    def refute_cu_procedure(
        self,
        procedure_id: str,
        *,
        failed_env_observables: Sequence[str],
        reason: str = "COUNTEREXAMPLE",
    ) -> dict[str, Any] | None:
        from canonical.runtime import instant_cu_procedure_store_v1 as icu
        return icu.refute_procedure(
            self.cu_store,
            procedure_id,
            counterexample_observables=failed_env_observables,
            reason=reason,
        )

    def delete_cu_procedure(self, procedure_id: str) -> bool:
        from canonical.runtime import instant_cu_procedure_store_v1 as icu
        return icu.delete_procedure(self.cu_store, procedure_id)

    # --- 4. Statistical Concept-Drift Observation ---
    def observe_drift(self, loss_or_error: float, *, stream: str = "default") -> dict[str, Any]:
        return self.drift_detector.observe(str(stream), float(loss_or_error))

    def snapshot_summary(self) -> dict[str, Any]:
        from canonical.runtime import instant_condition_store_v1 as ics
        active_cnt = sum(1 for w in self.dbsp._weights.values() if w > 0)
        return {
            "schema": "BRAIN_INSTANT_CONTINUAL_MEMORY_V1",
            "active_facts": active_cnt,
            "active_slots": len(self.dbsp._active_by_slot),
            "condition_entries": len(self.condition_store.get("entries") or {}),
            "condition_digest": ics.digest(self.condition_store),
            "cu_procedures": len(self.cu_store.get("procedures") or {}),
            "drift_summary": self.drift_detector.summary(),
            "parameters_stored": 0,
            "model_calls": PRODUCER_MODEL_CALLS,
        }


def _splice_candidates_fallback(parent: str, cand_a: str, cand_b: str, max_splices: int = 16) -> list[str]:
    """Pure-stdlib line-hunk dual splicer (matches `dual_program_splicing_v1.splice`)."""
    before = parent.splitlines(keepends=True)

    def _edits(cand: str) -> list[dict[str, Any]]:
        after = cand.splitlines(keepends=True)
        return [
            {"i1": i1, "i2": i2, "new": after[j1:j2]}
            for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, before, after).get_opcodes()
            if tag != "equal"
        ]

    def _render(blocks: Sequence[dict[str, Any]]) -> str | None:
        cursor = 0
        pieces: list[str] = []
        for blk in sorted(blocks, key=lambda b: (b["i1"], b["i2"])):
            if blk["i1"] < cursor:
                return None
            pieces.extend(before[cursor : blk["i1"]])
            pieces.extend(blk["new"])
            cursor = blk["i2"]
        pieces.extend(before[cursor:])
        return "".join(pieces)

    a_ed, b_ed = _edits(cand_a), _edits(cand_b)
    out: list[str] = []
    for text in (_render([*a_ed, *b_ed]),):
        if text and text != parent and text not in out:
            out.append(text)
    for a in a_ed:
        for b in b_ed:
            if a["i1"] < b["i2"] and b["i1"] < a["i2"]:
                for comb in (
                    [a, *[x for x in b_ed if x is not b]],
                    [b, *[x for x in a_ed if x is not a]],
                ):
                    text = _render(comb)
                    if text and text != parent and text not in out:
                        out.append(text)
    return out[:max_splices]


def _dual_splice(parent: str, cand_a: str, cand_b: str) -> list[str]:
    try:
        from canonical.swe_kernel.dual_program_splicing_v1 import splice as _dps_splice
        return list(_dps_splice(parent, cand_a, cand_b))
    except Exception:
        return _splice_candidates_fallback(parent, cand_a, cand_b)


# ---------------------------------------------------------------------------
# Strike A: Great Awakening Registry of 26 Verified Zero-LLM Dark Engines
# ---------------------------------------------------------------------------

DARK_ENGINE_CATALOG: dict[str, dict[str, str]] = {
    # SWE / Polyglot / Prose-Issue / Zero-Test / CST Skills
    "causal_angelic_swe": {
        "module": "canonical.runtime.causal_angelic_swe_engine_v1",
        "entrypoint": "solve_repository",
        "domain": "swe_python",
    },
    "multilang_causal_swe_js": {
        "module": "canonical.runtime.multilang_causal_swe_engine_v1",
        "entrypoint": "solve_js_repository",
        "domain": "swe_polyglot",
    },
    "multilang_causal_swe_c": {
        "module": "canonical.runtime.multilang_causal_swe_engine_v1",
        "entrypoint": "solve_c_repository",
        "domain": "swe_polyglot",
    },
    "go_causal_swe": {
        "module": "canonical.swe_kernel.go_and_jsts_causal_swe_engine_v1",
        "entrypoint": "solve_go_repository",
        "domain": "swe_polyglot",
    },
    "jsts_prose_swe": {
        "module": "canonical.swe_kernel.go_and_jsts_causal_swe_engine_v1",
        "entrypoint": "solve_js_ts_from_prose",
        "domain": "swe_polyglot",
    },
    "epistemic_issue_reproducer": {
        "module": "canonical.runtime.epistemic_issue_reproducer_v1",
        "entrypoint": "solve_issue_from_description",
        "domain": "swe_prose",
    },
    "epistemic_spec_oracle": {
        "module": "canonical.runtime.epistemic_spec_oracle_v1",
        "entrypoint": "solve_zero_test_codebase",
        "domain": "swe_zero_test",
    },
    "polyglot_cst_skill_inducer": {
        "module": "canonical.runtime.polyglot_cst_skill_inducer_v1",
        "entrypoint": "induce_cst_skill",
        "domain": "swe_polyglot_skills",
    },
    "instant_swe_skill_store": {
        "module": "canonical.runtime.instant_swe_skill_store_v1",
        "entrypoint": "new_store",
        "domain": "swe_skills",
    },
    "single_experience_transfer": {
        "module": "canonical.swe_kernel.single_experience_transfer_v1",
        "entrypoint": "learn",
        "domain": "swe_transfer",
    },
    "history_induced_edit_grammar": {
        "module": "canonical.swe_kernel.history_induced_edit_grammar_v1",
        "entrypoint": "solve_task",
        "domain": "swe_transfer",
    },
    "cross_repo_dataflow": {
        "module": "canonical.swe_kernel.cross_repo_dataflow_v1",
        "entrypoint": "build_cross_repo_graph",
        "domain": "swe_analysis",
    },
    "software_repair_crossfile": {
        "module": "canonical.runtime.bound_capabilities.software_repair_crossfile_choreograph_v1",
        "entrypoint": "run",
        "domain": "swe_crossfile",
    },
    "python_feature_implement_spec": {
        "module": "canonical.runtime.bound_capabilities.python_feature_implement_function_spec",
        "entrypoint": "run",
        "domain": "swe_feature",
    },
    "software_patch_cegis_z3": {
        "module": "canonical.runtime.bound_capabilities.software_patch_cegis_z3_v1",
        "entrypoint": "run",
        "domain": "swe_formal",
    },
    # Computer Use / World Model / SQL / GraphQL / OpenAPI / Morphisms / Compression
    "unified_computer_use_agent": {
        "module": "canonical.runtime.unified_computer_use_agent_v1",
        "entrypoint": "solve_computer_use_task",
        "domain": "computer_use",
    },
    "epistemic_world_model_planner": {
        "module": "canonical.runtime.epistemic_world_model_planner_v1",
        "entrypoint": "solve_with_epistemic_world_model",
        "domain": "world_model",
    },
    "epistemic_schema_graph_sql": {
        "module": "canonical.runtime.epistemic_schema_graph_agent_v1",
        "entrypoint": "solve_epistemic_sql_query",
        "domain": "sql_graphql",
    },
    "epistemic_openapi_agent": {
        "module": "canonical.runtime.epistemic_openapi_agent_v1",
        "entrypoint": "solve_live_openapi_workflow",
        "domain": "openapi",
    },
    "epistemic_morphism_engine": {
        "module": "canonical.runtime.epistemic_morphism_engine_v1",
        "entrypoint": "solve_with_epistemic_morphisms",
        "domain": "morphisms",
    },
    "epistemic_scan_acquire_compress": {
        "module": "canonical.runtime.epistemic_scan_acquire_compress_v1",
        "entrypoint": "solve_unseen_environment_live",
        "domain": "world_model",
    },
    "local_guide": {
        "module": "canonical.runtime.local_guide_v1",
        "entrypoint": "lookup",
        "domain": "computer_use",
    },
    "osworld_app_policy_overlay": {
        "module": "canonical.runtime.osworld_v21_app_policy_overlay_v1",
        "entrypoint": "decide",
        "domain": "computer_use",
    },
    "perfect_algorithm_v5": {
        "module": "canonical.swe_kernel.perfect_algorithm_unified_v5",
        "entrypoint": "PerfectAlgorithmUnified",
        "domain": "universal_planner",
    },
    # Grid Synthesis / Answer Shape / Stochastic Synth / Semantic Control / HLE / Charts
    "grid_delta_rule_inducer_v2": {
        "module": "canonical.runtime.grid_delta_rule_inducer_v2",
        "entrypoint": "induce",
        "domain": "grid_synthesis",
    },
    "answer_shape": {
        "module": "canonical.runtime.answer_shape_v1",
        "entrypoint": "asked",
        "domain": "qa",
    },
    "stochastic_synthesizer": {
        "module": "canonical.runtime.stochastic_synthesizer_v1",
        "entrypoint": "synthesize_body_from_examples",
        "domain": "synthesis",
    },
    "semantic_relation_control": {
        "module": "canonical.runtime.semantic_relation_control_v1",
        "entrypoint": "resolve",
        "domain": "qa",
    },
    "hle_native_research_v5": {
        "module": "canonical.runtime.hle_native_open_domain_research_v5",
        "entrypoint": "propose",
        "domain": "research_qa",
    },
    "chart_curve_label_rank": {
        "module": "canonical.runtime.bound_capabilities.chart_direct_curve_label_family_rank_v1",
        "entrypoint": "run",
        "domain": "charts",
        "optional_dep": "PIL",
    },
    "chart_axis_title_unit": {
        "module": "canonical.runtime.bound_capabilities.chart_axis_title_unit_binding_v1",
        "entrypoint": "run",
        "domain": "charts",
        "optional_dep": "PIL",
    },
}


class DarkCapabilityRegistry:
    """Lazy zero-overhead dispatcher awakening all verified dark zero-LLM engines under one front door."""

    def __init__(self) -> None:
        self._module_cache: dict[str, Any] = {}

    @staticmethod
    def list_engines(*, domain: str | None = None) -> list[dict[str, str]]:
        out: list[dict[str, str]] = []
        for slug, meta in sorted(DARK_ENGINE_CATALOG.items()):
            if domain is None or meta["domain"] == domain:
                out.append({"slug": slug, **meta})
        return out

    def load_module(self, slug: str) -> Any:
        meta = DARK_ENGINE_CATALOG.get(slug)
        if meta is None:
            raise KeyError(f"UNKNOWN_DARK_ENGINE:{slug}")
        mod_name = meta["module"]
        mod = self._module_cache.get(mod_name)
        if mod is None:
            import importlib
            mod = importlib.import_module(mod_name)
            self._module_cache[mod_name] = mod
        return mod

    def get_entrypoint(self, slug: str) -> Any:
        meta = DARK_ENGINE_CATALOG[slug]
        mod = self.load_module(slug)
        ep = meta["entrypoint"]
        if hasattr(mod, ep):
            return getattr(mod, ep)
        # Graceful fallback: return the module itself if entrypoint alias differs
        return mod

    def invoke(self, slug: str, *args: Any, **kwargs: Any) -> dict[str, Any]:
        t0 = time.perf_counter()
        ep = self.get_entrypoint(slug)
        if callable(ep):
            res = ep(*args, **kwargs)
        else:
            res = {"module": DARK_ENGINE_CATALOG[slug]["module"], "exported": True}
        return {
            "schema": SCHEMA,
            "engine": slug,
            "domain": DARK_ENGINE_CATALOG[slug]["domain"],
            "result": res,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            "model_calls": PRODUCER_MODEL_CALLS,
        }

    def probe_all(self) -> dict[str, Any]:
        """Verify live stdlib importability of every catalogued dark zero-LLM engine."""
        t0 = time.perf_counter()
        results: dict[str, dict[str, Any]] = {}
        unique_mods: dict[str, bool] = {}
        stdlib_total = 0
        stdlib_ok = 0
        for slug, meta in sorted(DARK_ENGINE_CATALOG.items()):
            mod_name = meta["module"]
            is_opt = bool(meta.get("optional_dep"))
            if not is_opt:
                stdlib_total += 1
            try:
                mod = self.load_module(slug)
                ep = meta["entrypoint"]
                has_ep = hasattr(mod, ep)
                results[slug] = {
                    "imported": True,
                    "has_entrypoint": has_ep,
                    "domain": meta["domain"],
                    "optional_dep": meta.get("optional_dep"),
                }
                unique_mods[mod_name] = True
                if not is_opt and has_ep:
                    stdlib_ok += 1
            except Exception as exc:
                results[slug] = {
                    "imported": False,
                    "has_entrypoint": False,
                    "error": type(exc).__name__,
                    "domain": meta["domain"],
                    "optional_dep": meta.get("optional_dep"),
                }
                unique_mods[mod_name] = False
        ok_count = sum(1 for v in results.values() if v.get("imported"))
        return {
            "schema": SCHEMA,
            "engines_total": len(results),
            "engines_imported": ok_count,
            "stdlib_engines_total": stdlib_total,
            "stdlib_engines_verified": stdlib_ok,
            "unique_modules_imported": sum(1 for v in unique_mods.values() if v),
            "unique_modules_total": len(unique_mods),
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
            "engines": results,
            "model_calls": PRODUCER_MODEL_CALLS,
        }


# ---------------------------------------------------------------------------
# Strike E: Logic-Grounded Compiled Workflow Graphs (NSI / PreAct Paradigm)
# ---------------------------------------------------------------------------

class WorkflowNode:
    """Typed node in a compiled zero-LLM workflow graph (`DataOp`, `CheckOp`, `LoopOp`)."""

    def __init__(
        self,
        node_id: str,
        kind: str,
        op_name: str,
        *,
        params: Mapping[str, Any] | None = None,
        guard_features: Sequence[str] = (),
        max_iters: int = 8,
        body_nodes: Sequence["WorkflowNode"] = (),
        recovery_branch: Sequence["WorkflowNode"] = (),
    ) -> None:
        if kind not in ("DataOp", "CheckOp", "LoopOp"):
            raise ValueError(f"INVALID_WORKFLOW_NODE_KIND:{kind}")
        self.node_id = str(node_id)
        self.kind = kind
        self.op_name = str(op_name)
        self.params: dict[str, Any] = dict(params or {})
        self.guard_features: tuple[str, ...] = tuple(str(f) for f in guard_features)
        self.max_iters = max(1, int(max_iters))
        self.body_nodes: list[WorkflowNode] = list(body_nodes)
        self.recovery_branch: list[WorkflowNode] = list(recovery_branch)
        self.tsetlin_guard: Any = None
        self._guard_pos_masks: list[int] = []
        self._guard_neg_masks: list[int] = []

    def train_guard(
        self,
        pos_feature_sets: Sequence[Sequence[str]],
        neg_feature_sets: Sequence[Sequence[str]] = (),
    ) -> list[str]:
        from canonical.swe_kernel.hdc_semantic_engine_v1 import MaxSATTsetlinClassifier

        if self.tsetlin_guard is None:
            self.tsetlin_guard = MaxSATTsetlinClassifier()
        self._guard_pos_masks = [self.tsetlin_guard.encode_features(fs) for fs in pos_feature_sets]
        self._guard_neg_masks = [self.tsetlin_guard.encode_features(fs) for fs in neg_feature_sets]
        self.tsetlin_guard.fit(self._guard_pos_masks, self._guard_neg_masks)
        return self.tsetlin_guard.explain_clauses()

    def check_guard(self, active_features: Sequence[str]) -> bool:
        if self.tsetlin_guard is not None and self.tsetlin_guard.clauses:
            x = self.tsetlin_guard.encode_features(active_features)
            return bool(self.tsetlin_guard.predict(x))
        if self.guard_features:
            fset = set(active_features)
            return all(g in fset for g in self.guard_features)
        return True

    def as_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "kind": self.kind,
            "op_name": self.op_name,
            "params": dict(self.params),
            "guard_clauses": self.tsetlin_guard.explain_clauses() if self.tsetlin_guard is not None else list(self.guard_features),
            "recovery_len": len(self.recovery_branch),
        }


class CompiledWorkflowGraph:
    """Deterministic logic-grounded procedural workflow graph with Tsetlin preconditions
    and targeted failure-node recovery grafting (compiles round-1 search -> round-2 sub-ms exec).
    """

    def __init__(self, workflow_id: str, nodes: Sequence[WorkflowNode]) -> None:
        self.workflow_id = str(workflow_id)
        self.nodes: list[WorkflowNode] = list(nodes)
        self.executions: int = 0
        self.grafts: int = 0

    @classmethod
    def compile_from_trace(
        cls,
        workflow_id: str,
        trace_steps: Sequence[Mapping[str, Any]],
        *,
        hole_bindings: Mapping[str, str] | None = None,
        positive_env_features: Sequence[Sequence[str]] = (),
        negative_env_features: Sequence[Sequence[str]] = (),
    ) -> "CompiledWorkflowGraph":
        """Compile a verified round-1 execution trace into a parameterized typed DAG."""
        bindings = {str(v): f"${{{k}}}" for k, v in (hole_bindings or {}).items() if v}
        nodes: list[WorkflowNode] = []
        for idx, step in enumerate(trace_steps):
            kind = str(step.get("kind") or ("CheckOp" if step.get("is_check") else "DataOp"))
            op_name = str(step.get("op") or step.get("action") or f"step_{idx}")
            raw_params = dict(step.get("params") or {})
            abstract_params: dict[str, Any] = {}
            for pk, pv in raw_params.items():
                if isinstance(pv, str):
                    nv = pv
                    for concrete, hole in bindings.items():
                        nv = nv.replace(concrete, hole)
                    abstract_params[pk] = nv
                else:
                    abstract_params[pk] = pv
            g_feats = tuple(str(f) for f in (step.get("guard_features") or ()))
            node = WorkflowNode(
                node_id=f"{workflow_id}:n{idx}",
                kind=kind,
                op_name=op_name,
                params=abstract_params,
                guard_features=g_feats,
                max_iters=int(step.get("max_iters", 8)),
            )
            if idx == 0 and positive_env_features:
                node.train_guard(positive_env_features, negative_env_features)
            nodes.append(node)
        return cls(workflow_id, nodes)

    @staticmethod
    def _instantiate_params(params: Mapping[str, Any], bindings: Mapping[str, str]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for k, v in params.items():
            if isinstance(v, str):
                nv = v
                for bk, bv in bindings.items():
                    nv = nv.replace(f"${{{bk}}}", str(bv))
                out[k] = nv
            else:
                out[k] = v
        return out

    def graft_recovery_at_node(
        self,
        node_idx: int,
        recovery_nodes: Sequence[WorkflowNode],
        *,
        failed_env_features: Sequence[str] = (),
    ) -> dict[str, Any]:
        """Failure-node recovery grafting: preserve verified prefix `0..node_idx-1`,
        attach recovery subgraph at `node_idx`, and refute the failed feature pattern in Tsetlin guard.
        """
        if not (0 <= node_idx < len(self.nodes)):
            raise IndexError(f"NODE_IDX_OUT_OF_RANGE:{node_idx}")
        target = self.nodes[node_idx]
        target.recovery_branch = list(recovery_nodes)
        refuted = 0
        if failed_env_features and target.tsetlin_guard is not None:
            neg_x = target.tsetlin_guard.encode_features(failed_env_features)
            refuted = target.tsetlin_guard.refute_counterexample(neg_x, positives=target._guard_pos_masks)
        self.grafts += 1
        return {
            "workflow_id": self.workflow_id,
            "grafted_node_idx": node_idx,
            "recovery_steps": len(target.recovery_branch),
            "clauses_narrowed": refuted,
            "total_grafts": self.grafts,
        }

    def execute(
        self,
        state: dict[str, Any],
        executors: Mapping[str, Any],
        *,
        bindings: Mapping[str, str] | None = None,
        env_features: Sequence[str] = (),
    ) -> dict[str, Any]:
        """Deterministic round-2+ execution (zero search, zero LLM calls)."""
        t0 = time.perf_counter()
        self.executions += 1
        bmap = dict(bindings or {})
        trace: list[dict[str, Any]] = []

        def _run_node(node: WorkflowNode) -> tuple[bool, str]:
            feats = list(env_features) + list(state.get("_features") or ())
            if not node.check_guard(feats):
                return False, "GUARD_REJECTED"
            inst_params = self._instantiate_params(node.params, bmap)
            fn = executors.get(node.op_name)
            if fn is None:
                return False, f"MISSING_EXECUTOR:{node.op_name}"
            if node.kind == "CheckOp":
                ok = bool(fn(state, inst_params))
                return ok, "OK" if ok else "CHECK_FAILED"
            if node.kind == "LoopOp":
                for _ in range(node.max_iters):
                    done = bool(fn(state, inst_params))
                    if done:
                        return True, "LOOP_SATISFIED"
                    for bnode in node.body_nodes:
                        bok, breason = _run_node(bnode)
                        if not bok:
                            return False, breason
                return False, "LOOP_EXHAUSTED"
            # DataOp
            res = fn(state, inst_params)
            ok = (res is not False)
            return ok, "OK" if ok else "DATA_OP_FAILED"

        for idx, node in enumerate(self.nodes):
            ok, reason = _run_node(node)
            trace.append({"node_idx": idx, "node_id": node.node_id, "kind": node.kind, "op": node.op_name, "ok": ok, "reason": reason})
            if not ok:
                if node.recovery_branch:
                    rec_ok = True
                    for rnode in node.recovery_branch:
                        rok, rreason = _run_node(rnode)
                        trace.append({"node_idx": idx, "node_id": rnode.node_id, "kind": rnode.kind, "op": rnode.op_name, "ok": rok, "reason": f"RECOVERY:{rreason}"})
                        if not rok:
                            rec_ok = False
                            break
                    if rec_ok:
                        continue
                return {
                    "schema": SCHEMA,
                    "workflow_id": self.workflow_id,
                    "succeeded": False,
                    "failed_node_idx": idx,
                    "reason": reason,
                    "steps_executed": len(trace),
                    "trace": trace,
                    "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
                    "model_calls": PRODUCER_MODEL_CALLS,
                }

        return {
            "schema": SCHEMA,
            "workflow_id": self.workflow_id,
            "succeeded": True,
            "failed_node_idx": None,
            "steps_executed": len(trace),
            "trace": trace,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            "model_calls": PRODUCER_MODEL_CALLS,
        }


class UnifiedFastSpine:
    """Single thin fast-path coordinator unifying Brain's verified zero-model organs."""

    def __init__(self, *, use_micro_backend: bool = False) -> None:
        self.use_micro_backend = bool(use_micro_backend)
        self._verified_donor_pairs: list[tuple[str, str, str]] = []
        self._subtree_store: Any = None
        self._learned_repos: set[str] = set()
        self.dark_registry = DarkCapabilityRegistry()
        self._cst_store: Any = None
        self._compiled_workflows: dict[str, CompiledWorkflowGraph] = {}

    def _get_subtree_store(self) -> Any:
        if self._subtree_store is None:
            from canonical.swe_kernel.minimal_subtree_transfer_v1 import MinimalSubtreeTransferStore
            self._subtree_store = MinimalSubtreeTransferStore(allow_one_scope_hole=True)
        return self._subtree_store

    def learn_from_repo_history(
        self,
        repo_root: str | pathlib.Path,
        *,
        max_commits: int = 80,
        before_commit: str | None = None,
    ) -> dict[str, Any]:
        """Pre-task active instant learning: mine `.git` commits into originating AST subtree rules (<500 ms)."""
        t0 = time.perf_counter()
        root_str = str(pathlib.Path(repo_root).resolve())
        store = self._get_subtree_store()
        stats = store.learn_from_git_repo(root_str, max_commits=max_commits, before_commit=before_commit)
        self._learned_repos.add(root_str)
        return {
            "schema": SCHEMA,
            "repo_root": root_str,
            **stats,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
            "model_calls": PRODUCER_MODEL_CALLS,
        }

    def self_play_warm_start(
        self,
        green_source: str,
        test_code: str,
        *,
        max_mutants: int = 6,
    ) -> dict[str, Any]:
        """Zero-LLM self-play: mutate green code, verify failing mutants, learn inverse repair deltas."""
        import ast as _ast
        from canonical.swe_kernel.minimal_epistemic_core_v1 import FastCoWVerifier

        t0 = time.perf_counter()
        store = self._get_subtree_store()
        learned = 0
        try:
            tree = _ast.parse(green_source)
        except SyntaxError:
            return {"schema": SCHEMA, "mutants_learned": 0, "rules_total": len(store.rules()), "model_calls": PRODUCER_MODEL_CALLS}

        mutants: list[str] = []
        for node in _ast.walk(tree):
            if len(mutants) >= max_mutants:
                break
            if isinstance(node, _ast.Compare) and len(node.ops) == 1:
                old_op = node.ops[0]
                flip = {
                    _ast.Lt: _ast.LtE, _ast.LtE: _ast.Lt, _ast.Gt: _ast.GtE, _ast.GtE: _ast.Gt,
                    _ast.Eq: _ast.NotEq, _ast.NotEq: _ast.Eq,
                }.get(type(old_op))
                if flip:
                    node.ops[0] = flip()
                    mutants.append(_ast.unparse(tree))
                    node.ops[0] = old_op
            elif isinstance(node, _ast.BinOp) and type(node.op) in (_ast.Add, _ast.Sub):
                old_op = node.op
                node.op = _ast.Sub() if isinstance(old_op, _ast.Add) else _ast.Add()
                mutants.append(_ast.unparse(tree))
                node.op = old_op

        for m_src in mutants:
            if not FastCoWVerifier.run_isolated(m_src, test_code, timeout_s=0.10).passed:
                if store.learn_from_file_pair(m_src, green_source) > 0:
                    self._verified_donor_pairs.append((f"selfplay_{len(self._verified_donor_pairs)}", m_src, green_source))
                    learned += 1
        return {
            "schema": SCHEMA,
            "mutants_learned": learned,
            "rules_total": len(store.rules()),
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
            "model_calls": PRODUCER_MODEL_CALLS,
        }

    # ------------------------------------------------------------------
    # Job 1: Zero-Build BM25 Localization + Producer-Lineage Causal Blame
    # ------------------------------------------------------------------
    @staticmethod
    def localize_repo_bug(
        repo_root: str | pathlib.Path,
        issue_text: str,
        *,
        failing_source: str | None = None,
        language: str = "python",
        top_files: int = 8,
        top_functions: int = 8,
    ) -> dict[str, Any]:
        """Rank culprit source/test files + functions via BM25 and trace causal producers."""
        t0 = time.perf_counter()
        root = pathlib.Path(repo_root).resolve()
        from canonical.swe_kernel import bm25_code_localizer_v1 as bm25
        from canonical.swe_kernel import producer_lineage_graph_v1 as plg

        src_ranked, test_ranked = bm25.localize_files_bm25(
            root, issue_text, language=language, top_src=top_files, top_tests=top_files,
        )
        fn_ranked = bm25.localize_functions_bm25(
            root, issue_text, language=language, in_tests=False, stage1_files=max(8, top_files), top_k=top_functions,
        )

        # Build producer-lineage graph over localized Python source files to catch already-returned producers
        py_sources: dict[str, str] = {}
        for rf in src_ranked[:top_files]:
            rel = str(getattr(rf, "rel_path", getattr(rf, "path", "")))
            if rel.endswith(".py"):
                p = root / rel
                if p.is_file():
                    try:
                        py_sources[rel] = p.read_text(encoding="utf-8", errors="replace")
                    except OSError:
                        pass

        producer_blame: list[dict[str, Any]] = []
        lineage_functions: list[str] = []
        if py_sources:
            try:
                graph = plg.build_lineage_graph_from_sources(py_sources)
                lineage_functions = list(graph.functions())[:40]
                for fn in fn_ranked[:4]:
                    fn_name = str(getattr(fn, "name", getattr(fn, "qualname", "")))
                    if not fn_name:
                        continue
                    prods = list(graph.producers_of(fn_name))[:6]
                    callers = list(graph.callers_of(fn_name))[:6]
                    if prods or callers:
                        producer_blame.append({
                            "function": fn_name,
                            "producers": [str(x) for x in prods],
                            "callers": [str(x) for x in callers],
                        })
            except Exception:
                pass

        assertion_explanation: dict[str, Any] | None = None
        if failing_source:
            try:
                assertion_explanation = plg.explain_assertion(failing_source)
            except Exception:
                assertion_explanation = None

        return {
            "schema": SCHEMA,
            "repo_root": str(root),
            "source_files": [
                {
                    "path": str(getattr(rf, "rel_path", getattr(rf, "path", ""))),
                    "score": round(float(getattr(rf, "score", 0.0)), 4),
                }
                for rf in src_ranked
            ],
            "test_files": [
                {
                    "path": str(getattr(rf, "rel_path", getattr(rf, "path", ""))),
                    "score": round(float(getattr(rf, "score", 0.0)), 4),
                }
                for rf in test_ranked
            ],
            "functions": [
                {
                    "path": str(getattr(fn, "rel_path", getattr(fn, "path", ""))),
                    "name": str(getattr(fn, "name", getattr(fn, "qualname", ""))),
                    "score": round(float(getattr(fn, "score", 0.0)), 4),
                }
                for fn in fn_ranked
            ],
            "producer_blame": producer_blame,
            "lineage_function_count": len(lineage_functions),
            "assertion_explanation": assertion_explanation,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
            "model_calls": PRODUCER_MODEL_CALLS,
        }

    # ------------------------------------------------------------------
    # Jobs 3 + 4 + 6a: Active Instant-Learning SWE (Subtree Transfer +
    # Induced Edit Basis + Prior Repair + Assertion-Granular Dual Splicing)
    # ------------------------------------------------------------------
    def _record_verified_fix(self, buggy_src: str, fixed_src: str) -> None:
        self._verified_donor_pairs.append((f"verified_{len(self._verified_donor_pairs)}", buggy_src, fixed_src))
        try:
            self._get_subtree_store().learn_from_file_pair(buggy_src, fixed_src)
        except Exception:
            pass

    def repair_function_fast(
        self,
        source: str,
        test_code: str,
        *,
        donor_pairs: Sequence[tuple[str, str, str]] | None = None,
        max_candidates: int = 160,
        timeout_s: float = 0.10,
        verify_test_strength: bool = True,
        enable_dual_splicing: bool = True,
        use_micro_backend: bool | None = None,
    ) -> dict[str, Any]:
        """Anti-lie -> SubtreeTransfer (originating) -> InducedEditBasis -> PriorRepair -> Dual-Program Splicing."""
        t0 = time.perf_counter()
        from canonical.swe_kernel import induced_edit_basis_v1 as ieb
        from canonical.swe_kernel.minimal_epistemic_core_v1 import (
            FastCoWVerifier,
            LocalMicroModelBackend,
            PriorRepairEngine,
        )

        strength: dict[str, Any] | None = None
        if verify_test_strength:
            strength = FastCoWVerifier.check_test_strength(source, test_code, max_mutants=5)
            if strength.get("is_lie"):
                return {
                    "schema": SCHEMA,
                    "fixed": False,
                    "reason": "WEAK_OR_TAUTOLOGICAL_TEST",
                    "test_strength": strength,
                    "candidates_tested": 0,
                    "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
                    "model_calls": PRODUCER_MODEL_CALLS,
                }

        loc = FastCoWVerifier.localize_failure(source, test_code, timeout_s=timeout_s)
        focus_lines: set[int] = set(loc.get("executed_lines") or ())
        if loc.get("exc_line"):
            focus_lines.add(int(loc["exc_line"]))

        # Feed any caller-supplied donor_pairs into our originating subtree store too
        store = self._get_subtree_store()
        if donor_pairs:
            for _, d_before, d_after in donor_pairs:
                try:
                    store.learn_from_file_pair(d_before, d_after)
                except Exception:
                    pass

        seen_src: set[str] = {source}
        subtree_tested = 0
        # Stage 1a: Originating Minimal-Subtree Transfer + E-Stitch rules (bounded so Stage 2 is never starved!)
        sub_cap = min(20, max(8, max_candidates // 4))
        if store.rules():
            try:
                sub_cands = store.propose_source_rewrites(
                    source,
                    focus_lines=focus_lines or None,
                    max_candidates=sub_cap,
                )
                for sc in sub_cands:
                    cand_src = str(sc.get("source") or "")
                    if not cand_src or cand_src in seen_src:
                        continue
                    seen_src.add(cand_src)
                    subtree_tested += 1
                    if FastCoWVerifier.run_isolated(cand_src, test_code, timeout_s=timeout_s).passed:
                        self._record_verified_fix(source, cand_src)
                        return {
                            "schema": SCHEMA,
                            "fixed": True,
                            "method": "MINIMAL_SUBTREE_TRANSFER_COW_V1",
                            "op_kind": str(sc.get("op_kind") or "subtree_rule"),
                            "source": cand_src,
                            "candidates_tested": subtree_tested,
                            "subtree_candidates_tested": subtree_tested,
                            "induced_candidates_tested": 0,
                            "test_strength": strength,
                            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
                            "model_calls": PRODUCER_MODEL_CALLS,
                        }
            except Exception:
                pass

        # Stage 1b: History/donor-induced AST edit templates (`induced_edit_basis_v1`, bounded cap)
        all_donors = list(self._verified_donor_pairs)
        if donor_pairs:
            all_donors.extend(donor_pairs)
        induced_tested = 0
        ind_cap = min(16, max(6, max_candidates // 5))
        if all_donors:
            try:
                templates = ieb.induce_templates(all_donors[-16:], context_depth=1, max_templates_per_pair=4)
                templates.extend(ieb.induce_templates(all_donors[-16:], context_depth=0, max_templates_per_pair=4))
                node_templates = ieb.induce_node_templates(all_donors[-16:], context_depth=1)
                cands = ieb.candidates_from_templates(source, templates, max_candidates=ind_cap)
                cands.extend(
                    ieb.candidates_from_node_templates(source, node_templates, max_candidates=ind_cap // 2)
                )
                for cand in cands[:ind_cap]:
                    cand_src = str(cand.get("source") or "")
                    if not cand_src or cand_src in seen_src:
                        continue
                    seen_src.add(cand_src)
                    induced_tested += 1
                    outcome = FastCoWVerifier.run_isolated(cand_src, test_code, timeout_s=timeout_s)
                    if outcome.passed:
                        self._record_verified_fix(source, cand_src)
                        return {
                            "schema": SCHEMA,
                            "fixed": True,
                            "method": "INDUCED_EDIT_BASIS_COW_V1",
                            "op_kind": str(cand.get("mutation") or cand.get("template_id") or "induced_template"),
                            "source": cand_src,
                            "candidates_tested": subtree_tested + induced_tested,
                            "subtree_candidates_tested": subtree_tested,
                            "induced_candidates_tested": induced_tested,
                            "test_strength": strength,
                            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
                            "model_calls": PRODUCER_MODEL_CALLS,
                        }
            except Exception:
                pass

        # Stage 2: PriorRepairEngine (with general algebraic structural ops) — guaranteed >= 65% budget!
        engine = PriorRepairEngine()
        prior_budget = max(int(max_candidates * 0.65), max_candidates - subtree_tested - induced_tested)
        prior_cands = engine.generate_candidates(
            source,
            executed_lines=loc.get("executed_lines") or set(),
            exc_line=int(loc.get("exc_line") or 0),
            exc_type=str(loc.get("exc_type") or ""),
            max_candidates=prior_budget,
        )
        prior_tested = 0
        passing: list[dict[str, Any]] = []
        for cand in prior_cands:
            cand_src = str(cand.get("source") or "")
            if not cand_src or cand_src in seen_src:
                continue
            seen_src.add(cand_src)
            prior_tested += 1
            if FastCoWVerifier.run_isolated(cand_src, test_code, timeout_s=timeout_s).passed:
                passing.append(cand)
                if len(passing) >= 4:
                    break
        if passing:
            passing.sort(key=lambda r: (r["delta"], -r["score"], len(r["source"])))
            best = passing[0]
            self._record_verified_fix(source, str(best["source"]))
            return {
                "schema": SCHEMA,
                "fixed": True,
                "method": "PRIOR_REPAIR_COW_V1",
                "op_kind": str(best.get("op_kind") or "prior_repair"),
                "source": str(best["source"]),
                "candidates_tested": subtree_tested + induced_tested + prior_tested,
                "subtree_candidates_tested": subtree_tested,
                "induced_candidates_tested": induced_tested,
                "passing_candidates": len(passing),
                "test_strength": strength,
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
                "model_calls": PRODUCER_MODEL_CALLS,
            }

        # Stage 3: Assertion-Granular Dual-Program Splicing (`dual_program_splicing_v1.splice`)
        splices_tested = 0
        if enable_dual_splicing and prior_cands:
            setup_code, checks = FastCoWVerifier.extract_check_snippets(test_code)
            if len(checks) >= 2:
                base_mask, total_checks = FastCoWVerifier.run_check_bitmask(source, setup_code, checks, timeout_s=timeout_s)
                full_mask = (1 << total_checks) - 1
                if base_mask < full_mask:
                    # Collect Pareto frontier of partial-pass candidates covering strictly new checks!
                    frontier: dict[int, str] = {}
                    for cand in prior_cands[:36]:
                        csrc = str(cand.get("source") or "")
                        if not csrc:
                            continue
                        cmask, _ = FastCoWVerifier.run_check_bitmask(csrc, setup_code, checks, timeout_s=timeout_s)
                        # Must fix at least ONE previously-failing assertion
                        if (cmask & ~base_mask) != 0 and cmask not in frontier:
                            frontier[cmask] = csrc
                            if len(frontier) >= 10:
                                break
                    # Pair complementary partial repairs whose union beats each alone (full union first!)
                    f_items = list(frontier.items())
                    pairs: list[tuple[int, int, str, str]] = []
                    for i in range(len(f_items)):
                        ma, sa = f_items[i]
                        for j in range(i + 1, len(f_items)):
                            mb, sb = f_items[j]
                            u = ma | mb
                            if u > max(ma, mb):
                                pairs.append((0 if u == full_mask else 1, -u.bit_count(), sa, sb))
                    pairs.sort(key=lambda p: (p[0], p[1]))
                    for _, _, sa, sb in pairs[:12]:
                        for sp_src in _dual_splice(source, sa, sb)[:4]:
                            if sp_src in seen_src:
                                continue
                            seen_src.add(sp_src)
                            splices_tested += 1
                            if FastCoWVerifier.run_isolated(sp_src, test_code, timeout_s=timeout_s).passed:
                                self._record_verified_fix(source, sp_src)
                                return {
                                    "schema": SCHEMA,
                                    "fixed": True,
                                    "method": "DUAL_PROGRAM_SPLICING_COW_V1",
                                    "op_kind": "dual_program_splice",
                                    "source": sp_src,
                                    "candidates_tested": subtree_tested + induced_tested + prior_tested + splices_tested,
                                    "subtree_candidates_tested": subtree_tested,
                                    "induced_candidates_tested": induced_tested,
                                    "splices_tested": splices_tested,
                                    "test_strength": strength,
                                    "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
                                    "model_calls": PRODUCER_MODEL_CALLS,
                                }

        # Stage 4: Optional LocalMicroModelBackend proposals
        micro_tested = 0
        use_micro = self.use_micro_backend if use_micro_backend is None else bool(use_micro_backend)
        if use_micro:
            try:
                backend = LocalMicroModelBackend()
                for cand_src in backend.propose_python_patches(source, test_code, n_samples=4):
                    if not cand_src or cand_src in seen_src:
                        continue
                    seen_src.add(cand_src)
                    micro_tested += 1
                    if FastCoWVerifier.run_isolated(cand_src, test_code, timeout_s=timeout_s).passed:
                        self._record_verified_fix(source, cand_src)
                        return {
                            "schema": SCHEMA,
                            "fixed": True,
                            "method": "LOCAL_MICRO_BACKEND_COW_V1",
                            "op_kind": "local_micro_backend",
                            "source": cand_src,
                            "candidates_tested": subtree_tested + induced_tested + prior_tested + splices_tested + micro_tested,
                            "subtree_candidates_tested": subtree_tested,
                            "induced_candidates_tested": induced_tested,
                            "splices_tested": splices_tested,
                            "test_strength": strength,
                            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
                            "model_calls": PRODUCER_MODEL_CALLS,
                        }
            except Exception:
                pass

        return {
            "schema": SCHEMA,
            "fixed": False,
            "source": None,
            "op_kind": None,
            "method": "ACTIVE_INSTANT_SWE_COW_V1",
            "candidates_tested": subtree_tested + induced_tested + prior_tested + splices_tested + micro_tested,
            "subtree_candidates_tested": subtree_tested,
            "induced_candidates_tested": induced_tested,
            "splices_tested": splices_tested,
            "test_strength": strength,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
            "model_calls": PRODUCER_MODEL_CALLS,
        }

    # ------------------------------------------------------------------
    # Multi-File Repo Fast-Path (BM25 + ProducerLineage + CoW Repair)
    # ------------------------------------------------------------------
    def repair_repo_fast(
        self,
        repo_root: str | pathlib.Path,
        issue_text: str,
        *,
        test_target: str | None = None,
        max_files: int = 3,
        max_candidates: int = 120,
        timeout_s: float = 0.12,
        donor_pairs: Sequence[tuple[str, str, str]] | None = None,
        apply_patch: bool = False,
    ) -> dict[str, Any]:
        """End-to-end fast-path over ANY size Python repo (replaces the old <=3-file ceiling)."""
        t0 = time.perf_counter()
        root = pathlib.Path(repo_root).resolve()
        # Pre-task active instant learning: mine `.git` commits into originating AST subtree rules once per repo
        if (root / ".git").exists() and str(root) not in self._learned_repos:
            try:
                self.learn_from_repo_history(root, max_commits=60)
            except Exception:
                pass
        loc = self.localize_repo_bug(root, issue_text, top_files=max(6, max_files * 2))

        src_paths = [
            f["path"] for f in loc["source_files"]
            if f["path"].endswith(".py") and (root / f["path"]).is_file()
        ]
        # Fallback if BM25 found no tokens on a tiny repo
        if not src_paths:
            src_paths = sorted(
                p.relative_to(root).as_posix()
                for p in root.rglob("*.py")
                if ".git" not in p.parts and not p.name.startswith("test_")
            )

        test_paths: list[str] = []
        if test_target:
            clean_t = test_target.split("::", 1)[0]
            if (root / clean_t).is_file():
                test_paths.append(clean_t)
        for tf in loc["test_files"]:
            tp = tf["path"]
            if tp.endswith(".py") and tp not in test_paths and (root / tp).is_file():
                test_paths.append(tp)
        if not test_paths:
            test_paths = sorted(
                p.relative_to(root).as_posix()
                for p in root.rglob("test_*.py")
                if ".git" not in p.parts
            )

        if not src_paths or not test_paths:
            return {
                "schema": SCHEMA,
                "repaired": False,
                "reason": "NO_LOCALIZED_SOURCE_OR_TEST",
                "localized_files": src_paths[:max_files],
                "localized_tests": test_paths[:max_files],
                "producer_blame": loc["producer_blame"],
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
                "model_calls": PRODUCER_MODEL_CALLS,
            }

        test_rel = test_paths[0]
        test_src = (root / test_rel).read_text(encoding="utf-8", errors="replace")
        # Strip relative/module import of the candidate file when running in-process CoW exec
        for rel_sp in src_paths[:max_files]:
            sp = root / rel_sp
            raw_src = sp.read_text(encoding="utf-8", errors="replace")
            mod_stem = sp.stem
            # Cleanly allow tests that write `from <mod> import ...` by removing self-import line in isolated exec
            adapted_test = re.sub(
                rf"^\s*from\s+[A-Za-z0-9_.]*{re.escape(mod_stem)}\s+import\s+.*$",
                "",
                test_src,
                flags=re.MULTILINE,
            )
            r = self.repair_function_fast(
                raw_src,
                adapted_test,
                donor_pairs=donor_pairs,
                max_candidates=max_candidates,
                timeout_s=timeout_s,
                verify_test_strength=True,
            )
            if r.get("fixed") and r.get("source"):
                patched_src = str(r["source"])
                if apply_patch:
                    sp.write_text(patched_src, encoding="utf-8")
                return {
                    "schema": SCHEMA,
                    "repaired": True,
                    "method": f"UNIFIED_FAST_SPINE__{r.get('method', 'COW')}",
                    "rule": str(r.get("op_kind") or "unified_fast_spine"),
                    "patched_file": rel_sp,
                    "patched_files": {rel_sp: patched_src},
                    "failing_nodeid": test_rel,
                    "localized_files": src_paths[:max_files],
                    "producer_blame": loc["producer_blame"],
                    "stats": {
                        "candidates_tested": int(r.get("candidates_tested", 0)),
                        "induced_candidates_tested": int(r.get("induced_candidates_tested", 0)),
                    },
                    "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
                    "model_calls": PRODUCER_MODEL_CALLS,
                }

        return {
            "schema": SCHEMA,
            "repaired": False,
            "reason": "FAST_SPINE_NO_PASSING_CANDIDATE",
            "localized_files": src_paths[:max_files],
            "localized_tests": test_paths[:max_files],
            "producer_blame": loc["producer_blame"],
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
            "model_calls": PRODUCER_MODEL_CALLS,
        }

    # ------------------------------------------------------------------
    # Job 2 + 4b: Hybrid DominoMemory + DBSP Bi-Temporal PPR Graph Memory
    # ------------------------------------------------------------------
    @staticmethod
    def build_hybrid_memory(
        conv_or_turns: Mapping[str, Any] | Sequence[Mapping[str, Any]],
        *,
        zset_deltas: Sequence[tuple[str, str, str, int, int | None, int]] | None = None,
    ) -> dict[str, Any]:
        """Index conversational turns in BOTH DominoMemory (BM25+char-ngrams+dates) and
        DBSPBiTemporalPPRMemory (zero-build entity co-occurrence graph + bi-temporal Z-sets)."""
        t0 = time.perf_counter()
        from canonical.runtime.hidden_arsenal_unifier_v1 import DBSPBiTemporalPPRMemory
        from canonical.swe_kernel.minimal_epistemic_core_v1 import DominoMemory

        if isinstance(conv_or_turns, Mapping):
            conv_dict = dict(conv_or_turns)
        else:
            conv_dict = {"session_1_date_time": "1 January, 2023", "session_1": list(conv_or_turns)}

        dom_idx = DominoMemory.index_conversation(conv_dict)
        indexed_turns: list[dict[str, Any]] = list(dom_idx.get("turns") or [])

        dbsp = DBSPBiTemporalPPRMemory()
        ent_to_dia: dict[str, list[str]] = defaultdict(list)
        turn_by_dia: dict[str, dict[str, Any]] = {}
        auto_deltas: list[tuple[str, str, str, int, int | None, int]] = []
        comp_cache: dict[str, tuple[bytes, int]] = {}
        for idx, t in enumerate(indexed_turns):
            dia_id = str(t.get("dia_id") or f"T:{idx}")
            turn_by_dia[dia_id] = t
            text = str(t.get("text") or "")
            speaker = str(t.get("speaker") or "").strip().lower()
            cb = _content_bytes_for_comp(f"{speaker} {t.get('session', '')} {text}")
            comp_cache[dia_id] = (cb, len(zlib.compress(cb, 1)) if cb else 0)
            ents: list[str] = []
            if speaker and len(speaker) >= 3:
                ents.append(speaker)
            for m in _ENTITY_TOKEN_RE.findall(text):
                if m not in _STOP_ENTITIES and len(m) >= 3:
                    ents.append(m.lower())
            uniq_ents = list(dict.fromkeys(ents))[:8]
            for e in uniq_ents:
                ent_to_dia[e].append(dia_id)
            # Co-occurrence edges between entities in the same turn (multi-hop bridge)
            for i in range(len(uniq_ents)):
                for j in range(i + 1, len(uniq_ents)):
                    auto_deltas.append((uniq_ents[i], "co_mentions", uniq_ents[j], idx + 1, None, +1))
                    auto_deltas.append((uniq_ents[j], "co_mentions", uniq_ents[i], idx + 1, None, +1))
        if auto_deltas:
            dbsp.apply_zset_deltas(auto_deltas, supersede_slot=False)
        if zset_deltas:
            dbsp.apply_zset_deltas(zset_deltas, supersede_slot=True)

        # Strike D: Zero-weight Random Indexing HDC + PathHD Entity-Temporal-Relation Graph
        from canonical.swe_kernel.hdc_semantic_engine_v1 import PathHDKnowledgeGraph, RandomIndexingEncoder

        hdc_encoder = RandomIndexingEncoder()
        turn_docs = [f"{t.get('speaker', '')} {t.get('date_str', '') or t.get('session', '')} {t.get('text', '')}" for t in indexed_turns]
        hdc_encoder.observe_documents(turn_docs)
        path_kg = PathHDKnowledgeGraph(hdc_encoder)
        hv_cache: dict[str, int] = {}
        seq_map: dict[str, int] = {}
        speakers_set: set[str] = set()
        for idx, t in enumerate(indexed_turns):
            dia_id = str(t.get("dia_id") or f"T:{idx}")
            seq_map[dia_id] = idx
            text = str(t.get("text") or "")
            speaker = str(t.get("speaker") or "")
            if speaker.strip():
                speakers_set.add(speaker.strip().lower())
            date_str = str(t.get("date_str") or t.get("session") or "")
            hv_cache[dia_id] = hdc_encoder.encode_text(f"{speaker} {date_str} {text}", use_context=True)
            path_kg.ingest_turn(text, speaker=speaker, turn_idx=idx + 1, timestamp_text=date_str, source_id=dia_id)

        return {
            "dom_idx": dom_idx,
            "dbsp": dbsp,
            "entity_to_dia": dict(ent_to_dia),
            "turn_by_dia": turn_by_dia,
            "seq_map": seq_map,
            "speakers": sorted(speakers_set),
            "comp_cache": comp_cache,
            "ppr_cache": {},
            "hdc_encoder": hdc_encoder,
            "path_kg": path_kg,
            "hv_cache": hv_cache,
            "build_ms": round((time.perf_counter() - t0) * 1000.0, 2),
        }

    @staticmethod
    def query_hybrid_memory(
        index: Mapping[str, Any],
        query: str,
        *,
        top_k: int = 10,
        t_valid: int | None = None,
        ppr_weight: float = 0.10,
        comp_weight: float = 0.16,
        hdc_weight: float = 0.08,
        adj_weight: float = 0.55,
        speaker_boost: float = 0.30,
    ) -> dict[str, Any]:
        """Fuse DominoMemory BM25+char-ngram + DBSP Bi-Temporal PPR + zlib Compression Gain
        + 2048-bit Random-Indexing HDC + PathHD Facts + Speaker Attribution + Same-Session
        Dialogue-Neighborhood Propagation."""
        from canonical.swe_kernel.hdc_semantic_engine_v1 import hv_similarity
        from canonical.swe_kernel.minimal_epistemic_core_v1 import DominoMemory

        dom_idx = index["dom_idx"]
        dbsp = index["dbsp"]
        ent_to_dia: Mapping[str, list[str]] = index["entity_to_dia"]
        turn_by_dia: Mapping[str, dict[str, Any]] = index["turn_by_dia"]
        comp_cache: Mapping[str, tuple[bytes, int]] = index.get("comp_cache") or {}
        ppr_cache = index.get("ppr_cache") if isinstance(index.get("ppr_cache"), dict) else None
        hdc_encoder = index.get("hdc_encoder")
        path_kg = index.get("path_kg")
        hv_cache: Mapping[str, int] = index.get("hv_cache") or {}

        cand_pool = max(top_k * 3, 35)
        base = DominoMemory.retrieve_turns(dom_idx, query, top_k=cand_pool)
        base_ids: list[str] = list(base.get("dia_ids") or [])
        rrf_scores: dict[str, float] = {}
        for rank, did in enumerate(base_ids):
            rrf_scores[did] = rrf_scores.get(did, 0.0) + 1.0 / (15.0 + rank)

        # Multi-hop entity expansion via DBSPBiTemporalPPRMemory.query_ppr (memoized per seed!)
        n_turns = max(1, len(turn_by_dia))
        max_df = max(12, n_turns // 4)
        q_ents: list[str] = []
        for m in _ENTITY_TOKEN_RE.findall(query):
            el = m.lower()
            if m not in _STOP_ENTITIES and el in ent_to_dia and len(ent_to_dia[el]) <= max_df:
                if el not in q_ents:
                    q_ents.append(el)
        for w in re.findall(r"[a-z]{3,}", query.lower()):
            if w in ent_to_dia and len(ent_to_dia[w]) <= max_df and w not in q_ents:
                q_ents.append(w)

        if q_ents and ppr_weight > 0.0:
            ppr_dia_scores: dict[str, float] = defaultdict(float)
            for seed in q_ents[:4]:
                cache_key = (seed, t_valid)
                if ppr_cache is not None and cache_key in ppr_cache:
                    ranked_nbrs = ppr_cache[cache_key]
                else:
                    ranked_nbrs = list(dbsp.query_ppr(seed, t_valid=t_valid, top_k=6).get("ranked", []))
                    if ppr_cache is not None:
                        ppr_cache[cache_key] = ranked_nbrs
                for nbr, prob in ranked_nbrs:
                    nbr_dias = ent_to_dia.get(str(nbr), ())
                    if 0 < len(nbr_dias) <= max_df:
                        inv_df = 1.0 / (1.0 + len(nbr_dias))
                        for did in nbr_dias:
                            ppr_dia_scores[did] += float(prob) * inv_df
            if ppr_dia_scores:
                ranked_ppr = sorted(ppr_dia_scores.items(), key=lambda x: -x[1])[: max(top_k * 2, 16)]
                for rank, (did, _) in enumerate(ranked_ppr):
                    rrf_scores[did] = rrf_scores.get(did, 0.0) + ppr_weight / (20.0 + rank)

        # Zero-parameter content-zlib Normalized Compression Gain rerank over top candidate pool
        if comp_weight > 0.0 and rrf_scores:
            qb = _content_bytes_for_comp(query)
            if qb:
                cq = len(zlib.compress(qb, 1))
                top_pool = [did for did, _ in sorted(rrf_scores.items(), key=lambda x: -x[1])[:cand_pool]]
                comp_ranked: list[tuple[float, str]] = []
                for did in top_pool:
                    entry = comp_cache.get(did)
                    if entry is None:
                        t = turn_by_dia.get(did, {})
                        db = _content_bytes_for_comp(f"{t.get('speaker', '')} {t.get('session', '')} {t.get('text', '')}")
                        cd = len(zlib.compress(db, 1)) if db else 0
                    else:
                        db, cd = entry
                    if db:
                        cqd = len(zlib.compress(qb + b" " + db, 1))
                        gain = max(0.0, (cq + cd - cqd) / max(1.0, float(cq)))
                        if gain > 0.0:
                            comp_ranked.append((gain, did))
                if comp_ranked:
                    comp_ranked.sort(key=lambda x: -x[0])
                    for rank, (_, did) in enumerate(comp_ranked):
                        rrf_scores[did] = rrf_scores.get(did, 0.0) + comp_weight / (20.0 + rank)

        # Strike D: Zero-weight 2048-bit Random-Indexing HDC Hamming + PathHD structured fact boost
        matched_facts: list[tuple[float, Any]] = []
        if hdc_weight > 0.0 and hdc_encoder is not None and hv_cache:
            q_hv = hdc_encoder.encode_text(query, use_context=True)
            # Full-corpus O(N) bit_count scan is <0.3ms for 500 turns!
            hdc_ranked: list[tuple[float, str]] = []
            for did, dhv in hv_cache.items():
                sim = hv_similarity(q_hv, dhv)
                if sim > 0.04:
                    hdc_ranked.append((sim, did))
            if hdc_ranked:
                hdc_ranked.sort(key=lambda x: -x[0])
                for rank, (_, did) in enumerate(hdc_ranked[: max(top_k * 2, 24)]):
                    rrf_scores[did] = rrf_scores.get(did, 0.0) + hdc_weight / (18.0 + rank)
        if path_kg is not None:
            matched_facts = path_kg.query_facts(query, top_k=5)
            for rank, (fsc, fact) in enumerate(matched_facts):
                if fact.source_id and fsc >= 3.0:
                    rrf_scores[fact.source_id] = rrf_scores.get(fact.source_id, 0.0) + (hdc_weight * 1.15) / (12.0 + rank)

        # Speaker-attribution prior + Same-session Dialogue-Neighborhood Propagation (+-1, +-2 turns)
        indexed_turns: Sequence[Mapping[str, Any]] = dom_idx.get("turns") or ()
        seq_map: Mapping[str, int] = index.get("seq_map") or {}
        known_spks: Sequence[str] = index.get("speakers") or ()
        target_spk: str | None = None
        if len(known_spks) >= 2:
            q_words = set(re.findall(r"[a-z]+", query.lower()))
            mentioned = [s for s in known_spks if any(tok in q_words for tok in s.split() if len(tok) >= 3)]
            if len(mentioned) == 1:
                target_spk = mentioned[0]
        if target_spk is not None and speaker_boost > 0.0:
            for did in list(rrf_scores.keys()):
                sp = str(turn_by_dia.get(did, {}).get("speaker") or "").strip().lower()
                if sp == target_spk:
                    rrf_scores[did] *= (1.0 + speaker_boost)
        if adj_weight > 0.0 and seq_map and indexed_turns:
            anchors = sorted(rrf_scores.items(), key=lambda x: -x[1])[:10]
            for did, asc in anchors:
                pos = seq_map.get(did)
                if pos is None:
                    continue
                cur_sess = indexed_turns[pos].get("session")
                for delta, decay in ((-1, 1.0), (+1, 1.0), (-2, 0.45), (+2, 0.45)):
                    npos = pos + delta
                    if 0 <= npos < len(indexed_turns) and indexed_turns[npos].get("session") == cur_sess:
                        ndid = str(indexed_turns[npos].get("dia_id") or f"T:{npos}")
                        nsp = str(indexed_turns[npos].get("speaker") or "").strip().lower()
                        mult = adj_weight * decay
                        if target_spk is not None:
                            mult *= (1.35 if nsp == target_spk else 0.55)
                        rrf_scores[ndid] = rrf_scores.get(ndid, 0.0) + asc * mult

        ordered = sorted(rrf_scores.items(), key=lambda x: -x[1])[:top_k]
        dia_ids = [did for did, _ in ordered]
        top_turns = [
            {
                "dia_id": did,
                "speaker": turn_by_dia.get(did, {}).get("speaker", ""),
                "session": turn_by_dia.get(did, {}).get("session", ""),
                "date_str": turn_by_dia.get(did, {}).get("date_str", ""),
                "date": turn_by_dia.get(did, {}).get("date", ""),
                "text": turn_by_dia.get(did, {}).get("text", ""),
                "hybrid_score": round(sc, 6),
            }
            for did, sc in ordered
        ]
        return {
            "dia_ids": dia_ids,
            "top_turns": top_turns,
            "matched_facts": [
                {
                    "subject": f.subject,
                    "relation": f.relation,
                    "obj": f.obj,
                    "turn_idx": f.turn_idx,
                    "superseded": f.superseded_by is not None,
                    "source_id": f.source_id,
                    "score": round(fsc, 3),
                }
                for fsc, f in matched_facts[:5]
            ],
            "speaker_conflict": bool(base.get("speaker_conflict", False)),
            "conflict_score": float(base.get("conflict_score", 0.0)),
        }

    @staticmethod
    def answer_hybrid_memory(
        index: Mapping[str, Any],
        question: str,
        *,
        top_k: int = 8,
        abstain_threshold: float = 0.22,
    ) -> dict[str, Any]:
        """End-to-end zero-LLM symbolic + HDC QA with temporal supersession & calibrated abstention."""
        t0 = time.perf_counter()
        from canonical.swe_kernel.hdc_semantic_engine_v1 import extract_concise_answer

        ret = UnifiedFastSpine.query_hybrid_memory(index, question, top_k=top_k)
        turns = list(ret.get("top_turns") or [])
        ev_texts = [str(t.get("text") or "") for t in turns]
        timestamps = [str(t.get("date_str") or t.get("session") or "") for t in turns]
        dates = [str(t.get("date") or "") for t in turns]
        speakers = [str(t.get("speaker") or "") for t in turns]
        all_speakers = list(index.get("speakers") or ())
        path_kg = index.get("path_kg")
        facts = path_kg.query_facts(question, top_k=5) if path_kg is not None else []
        qa = extract_concise_answer(
            question,
            ev_texts,
            facts=facts,
            timestamps=timestamps,
            dates=dates,
            speakers=speakers,
            all_speakers=all_speakers,
            encoder=index.get("hdc_encoder"),
            abstain_threshold=abstain_threshold,
        )
        # Optional dark `answer_shape_v1` shape classification metadata
        answer_shape_tag = None
        try:
            from canonical.runtime import answer_shape_v1 as asv1
            if hasattr(asv1, "asked"):
                answer_shape_tag = asv1.asked(question)
        except Exception:
            pass
        return {
            "schema": SCHEMA,
            "question": question,
            "answer": qa["answer"],
            "abstained": bool(qa["abstained"]),
            "confidence": float(qa["confidence"]),
            "answer_type": qa["answer_type"],
            "answer_shape": answer_shape_tag,
            "dia_ids": ret["dia_ids"],
            "matched_facts": ret.get("matched_facts") or [],
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
            "model_calls": PRODUCER_MODEL_CALLS,
        }

    @staticmethod
    def create_continual_memory() -> InstantContinualMemory:
        """Create a unified zero-weight `InstantContinualMemory` instance (DBSP + Conditions + CU Procedures + Drift)."""
        return InstantContinualMemory()

    # ------------------------------------------------------------------
    # Job 4a: Workflow Skill Compilation Bridge (`causal_trace_to_skill_compiler_v1`)
    # ------------------------------------------------------------------
    @staticmethod
    def anti_unify_traces(trace_a: Sequence[Mapping[str, Any]], trace_b: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        """Anti-unify two successful action/edit traces into a parameterized reusable skill."""
        from canonical.swe_kernel import causal_trace_to_skill_compiler_v1 as ctsc

        res = ctsc.anti_unify_workflow(list(trace_a), list(trace_b))
        return {"schema": SCHEMA, "anti_unified": res, "model_calls": PRODUCER_MODEL_CALLS}

    # ------------------------------------------------------------------
    # Awakened DARK Organs: Refusal-as-Spec, Greenfield Spec Synthesis,
    # Instant One-Shot Loop & Four-Levers Information Budget
    # ------------------------------------------------------------------
    @staticmethod
    def parse_refusal_to_clause(refusal_text: str) -> dict[str, Any]:
        """Awakened `a_refusal_is_a_specification_v1`: compile any error/CLI refusal into an executable clause."""
        from canonical.runtime import a_refusal_is_a_specification_v1 as ref_spec

        clause = ref_spec.read_refusal(refusal_text)
        return {
            "schema": SCHEMA,
            "parsed": clause is not None,
            "clause": clause.as_dict() if clause is not None else None,
            "model_calls": PRODUCER_MODEL_CALLS,
        }

    @staticmethod
    def repair_command_from_refusal(
        operation_id: str,
        argv: Sequence[str],
        *,
        env_files: Sequence[str] = (),
        declared_flags: Sequence[str] = (),
        numeric_flags: Sequence[str] = (),
        max_attempts: int = 3,
    ) -> dict[str, Any]:
        """Awakened `a_refusal_is_a_specification_v1.repair`: repair a CLI invocation directly from its refusal."""
        from canonical.runtime import a_refusal_is_a_specification_v1 as ref_spec

        rep = ref_spec.repair(
            operation_id,
            list(argv),
            env_files=list(env_files),
            declared_flags=list(declared_flags),
            numeric_flags=list(numeric_flags),
            max_attempts=max_attempts,
        )
        return {"schema": SCHEMA, "repair": rep.as_dict(), "model_calls": PRODUCER_MODEL_CALLS}

    @staticmethod
    def synthesize_greenfield_spec(
        workspace: str | pathlib.Path,
        instruction: str,
        *,
        memory: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Awakened 8,624L DARK `epistemic_spec_synthesizer_v1`: zero-LLM deductive spec synthesis + adversarial oracle."""
        from canonical.runtime import epistemic_spec_synthesizer_v1 as ess

        ws = pathlib.Path(workspace).resolve()
        contract = ess.compile_spec_contract(instruction, ws)
        if contract is None:
            return {
                "schema": SCHEMA,
                "synthesized": False,
                "reason": "NO_EXECUTABLE_SPEC_CONTRACT_MATCH",
                "model_calls": PRODUCER_MODEL_CALLS,
            }
        res = ess.synthesize_and_verify_spec(ws, instruction, memory=memory)
        return {"schema": SCHEMA, "synthesized": bool(res.get("solved") or res.get("verified")), "result": res, "model_calls": PRODUCER_MODEL_CALLS}

    @staticmethod
    def four_levers_budget(hypothesis_count: int, *, sym_group_size: int = 1, demo_bits: float = 0.0, query_bits: float = 0.0, refusal_bits: float = 0.0) -> dict[str, Any]:
        """Awakened DARK `the_four_levers_of_learning_from_experience_v1`: exact information-descent budget."""
        import math as _math
        from canonical.tools import the_four_levers_of_learning_from_experience_v1 as fl

        prior_bits = fl.bits_remaining(max(1, int(hypothesis_count)))
        quotient_bits = _math.log2(max(1.0, float(hypothesis_count) / max(1.0, float(sym_group_size))))
        remaining = max(0.0, quotient_bits - float(demo_bits) - float(query_bits) - float(refusal_bits))
        return {
            "schema": SCHEMA,
            "raw_prior_bits": round(prior_bits, 4),
            "quotient_prior_bits": round(quotient_bits, 4),
            "remaining_bits": round(remaining, 4),
            "identifiable_now": remaining <= 1e-6,
            "splitting_queries_needed": int(_math.ceil(remaining)),
            "model_calls": PRODUCER_MODEL_CALLS,
        }

    # ------------------------------------------------------------------
    # Strike A: Dark Capability Registry Front Door (26+ Zero-LLM Engines)
    # ------------------------------------------------------------------
    def dark_engine_catalog(self, *, domain: str | None = None) -> list[dict[str, str]]:
        return self.dark_registry.list_engines(domain=domain)

    def probe_dark_engines(self) -> dict[str, Any]:
        return self.dark_registry.probe_all()

    def invoke_dark_engine(self, slug: str, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self.dark_registry.invoke(slug, *args, **kwargs)

    # ------------------------------------------------------------------
    # Strike C: Polyglot + Prose-Issue + Zero-Test + CST Skill SWE Router
    # ------------------------------------------------------------------
    def _get_cst_store(self) -> dict[str, Any]:
        if self._cst_store is None:
            from canonical.runtime import polyglot_cst_skill_inducer_v1 as pcsi
            self._cst_store = pcsi.new_cst_store()
        return self._cst_store

    def learn_polyglot_skill(
        self,
        file_path: str,
        before_text: str,
        after_text: str,
        *,
        description: str = "",
    ) -> dict[str, Any]:
        """Instant 1-shot polyglot CST skill induction (Python, Go, JS, TS, Rust, Java, C/C++)."""
        from canonical.runtime import polyglot_cst_skill_inducer_v1 as pcsi

        lang = pcsi.detect_language(file_path)
        store = self._get_cst_store()
        res = pcsi.admit_cst_skill(store, before_text, after_text, language=lang, description=description)
        learned = bool(res.get("admitted") or res.get("skill_id") or res.get("skill"))
        sid = str(res.get("skill_id") or (res.get("skill") or {}).get("skill_id") or "")
        return {
            "schema": SCHEMA,
            "learned": learned,
            "language": lang,
            "skill_id": sid,
            "store_size": len(store.get("skills") or []),
            "model_calls": PRODUCER_MODEL_CALLS,
        }

    def apply_polyglot_skills(self, file_path: str, source_text: str, *, max_candidates: int = 12) -> list[dict[str, Any]]:
        """Recall and instantiate matching polyglot CST skills onto `source_text` (<1 ms)."""
        from canonical.runtime import polyglot_cst_skill_inducer_v1 as pcsi

        store = self._get_cst_store()
        lang = pcsi.detect_language(file_path)
        cands = pcsi.recall_cst_candidates(store, source_text, language=lang, max_candidates=max_candidates)
        out: list[dict[str, Any]] = []
        seen = {source_text}
        for c in (cands or ()):
            cand_src = c if isinstance(c, str) else str(c.get("patched_source") or c.get("source") or c.get("patched_text") or "")
            if cand_src and cand_src not in seen:
                seen.add(cand_src)
                out.append({
                    "language": lang,
                    "skill_id": str(c.get("skill_id") or "") if isinstance(c, Mapping) else "",
                    "source": cand_src,
                })
        return out

    def solve_swe_polyglot(
        self,
        workspace: str | pathlib.Path,
        issue_text: str = "",
        *,
        language: str | None = None,
        apply_patch: bool = True,
        test_target: str | None = None,
    ) -> dict[str, Any]:
        """Unified zero-LLM polyglot SWE router (Python / Go / JS / TS / C / C++ / prose-issue / zero-test)."""
        t0 = time.perf_counter()
        ws = pathlib.Path(workspace).resolve()
        # Detect dominant repository language from workspace files
        lang = (language or "").strip().lower()
        if not lang:
            ext_counts: dict[str, int] = defaultdict(int)
            for p in ws.rglob("*"):
                if p.is_file() and ".git" not in p.parts and "node_modules" not in p.parts:
                    suf = p.suffix.lower()
                    if suf in (".py", ".go", ".js", ".ts", ".tsx", ".jsx", ".c", ".h", ".cpp", ".cc"):
                        ext_counts[suf] += 1
            if ext_counts.get(".go", 0) > 0:
                lang = "go"
            elif ext_counts.get(".js", 0) + ext_counts.get(".ts", 0) + ext_counts.get(".jsx", 0) + ext_counts.get(".tsx", 0) > ext_counts.get(".py", 0):
                lang = "javascript"
            elif ext_counts.get(".c", 0) + ext_counts.get(".cpp", 0) + ext_counts.get(".cc", 0) > ext_counts.get(".py", 0):
                lang = "c"
            else:
                lang = "python"

        # 1. Go repositories -> awakened `go_and_jsts_causal_swe_engine_v1`
        if lang == "go":
            try:
                from canonical.swe_kernel import go_and_jsts_causal_swe_engine_v1 as gj
                res = gj.solve_go_repository(ws, issue_text=issue_text)
                return {
                    "schema": SCHEMA,
                    "language": "go",
                    "solved": bool(res.get("verified") or res.get("solved") or res.get("repaired") or res.get("patched")),
                    "engine": "go_and_jsts_causal_swe_engine_v1",
                    "result": res,
                    "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
                    "model_calls": PRODUCER_MODEL_CALLS,
                }
            except Exception as exc:
                return {"schema": SCHEMA, "language": "go", "solved": False, "error": f"{type(exc).__name__}: {exc}", "model_calls": PRODUCER_MODEL_CALLS}

        # 2. JavaScript / TypeScript repositories -> multilang + prose JS/TS engines
        if lang in ("js", "ts", "javascript", "typescript"):
            try:
                from canonical.runtime import multilang_causal_swe_engine_v1 as ml
                res = ml.solve_js_repository(ws)
                if isinstance(res, Mapping) and (res.get("verified") or res.get("solved") or res.get("repaired") or res.get("patched")):
                    return {
                        "schema": SCHEMA,
                        "language": lang,
                        "solved": True,
                        "engine": "multilang_causal_swe_engine_v1",
                        "result": dict(res),
                        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
                        "model_calls": PRODUCER_MODEL_CALLS,
                    }
            except Exception:
                pass
            if issue_text:
                try:
                    from canonical.swe_kernel import go_and_jsts_causal_swe_engine_v1 as gj
                    res2 = gj.solve_js_ts_from_prose(ws, issue_text)
                    return {
                        "schema": SCHEMA,
                        "language": lang,
                        "solved": bool(res2.get("verified") or res2.get("solved") or res2.get("repaired") or res2.get("patched")),
                        "engine": "go_and_jsts_causal_swe_engine_v1",
                        "result": res2,
                        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
                        "model_calls": PRODUCER_MODEL_CALLS,
                    }
                except Exception as exc:
                    return {"schema": SCHEMA, "language": lang, "solved": False, "error": f"{type(exc).__name__}: {exc}", "model_calls": PRODUCER_MODEL_CALLS}
            return {"schema": SCHEMA, "language": lang, "solved": False, "engine": "multilang_causal_swe_engine_v1", "model_calls": PRODUCER_MODEL_CALLS}

        # 3. C / C++ repositories -> awakened `multilang_causal_swe_engine_v1`
        if lang in ("c", "cpp", "c++"):
            try:
                from canonical.runtime import multilang_causal_swe_engine_v1 as ml
                res = ml.solve_c_repository(ws)
                return {
                    "schema": SCHEMA,
                    "language": lang,
                    "solved": bool(isinstance(res, Mapping) and (res.get("verified") or res.get("solved") or res.get("repaired") or res.get("patched"))),
                    "engine": "multilang_causal_swe_engine_v1",
                    "result": dict(res) if isinstance(res, Mapping) else res,
                    "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
                    "model_calls": PRODUCER_MODEL_CALLS,
                }
            except Exception as exc:
                return {"schema": SCHEMA, "language": lang, "solved": False, "error": f"{type(exc).__name__}: {exc}", "model_calls": PRODUCER_MODEL_CALLS}

        # 4. Python repositories:
        #    (a) Fast CoW Spine (BM25 + ProducerLineage + E-Stitch Subtree Transfer + Dual Splicing)
        fast_res = self.repair_repo_fast(ws, issue_text, test_target=test_target, apply_patch=apply_patch)
        if fast_res.get("repaired"):
            return {
                "schema": SCHEMA,
                "language": "python",
                "solved": True,
                "engine": str(fast_res.get("method") or "UNIFIED_FAST_SPINE"),
                "result": fast_res,
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
                "model_calls": PRODUCER_MODEL_CALLS,
            }
        #    (b) Awakened `epistemic_issue_reproducer_v1` (prose issue -> repro test -> causal patch!)
        if issue_text:
            try:
                from canonical.runtime import epistemic_issue_reproducer_v1 as eir
                res_eir = eir.solve_issue_from_description(ws, issue_text)
                if isinstance(res_eir, Mapping) and (res_eir.get("solved") or res_eir.get("repaired") or res_eir.get("patched")):
                    return {
                        "schema": SCHEMA,
                        "language": "python",
                        "solved": True,
                        "engine": "epistemic_issue_reproducer_v1",
                        "result": dict(res_eir),
                        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
                        "model_calls": PRODUCER_MODEL_CALLS,
                    }
            except Exception:
                pass
        #    (c) Awakened `epistemic_spec_oracle_v1` (zero-test codebase synthesis & oracle)
        if issue_text:
            try:
                from canonical.runtime import epistemic_spec_oracle_v1 as eso
                res_eso = eso.solve_zero_test_codebase(ws, issue_text)
                if isinstance(res_eso, Mapping) and (res_eso.get("solved") or res_eso.get("repaired") or res_eso.get("patched")):
                    return {
                        "schema": SCHEMA,
                        "language": "python",
                        "solved": True,
                        "engine": "epistemic_spec_oracle_v1",
                        "result": dict(res_eso),
                        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
                        "model_calls": PRODUCER_MODEL_CALLS,
                    }
            except Exception:
                pass
        return {
            "schema": SCHEMA,
            "language": "python",
            "solved": False,
            "engine": "UNIFIED_FAST_SPINE_POLYGLOT",
            "result": fast_res,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
            "model_calls": PRODUCER_MODEL_CALLS,
        }

    # ------------------------------------------------------------------
    # Strike E: Logic-Grounded Workflow Compilation (`DataOp`/`CheckOp`/`LoopOp`)
    # ------------------------------------------------------------------
    def compile_workflow_graph(
        self,
        workflow_id: str,
        trace_steps: Sequence[Mapping[str, Any]],
        *,
        hole_bindings: Mapping[str, str] | None = None,
        positive_env_features: Sequence[Sequence[str]] = (),
        negative_env_features: Sequence[Sequence[str]] = (),
    ) -> CompiledWorkflowGraph:
        wf = CompiledWorkflowGraph.compile_from_trace(
            workflow_id,
            trace_steps,
            hole_bindings=hole_bindings,
            positive_env_features=positive_env_features,
            negative_env_features=negative_env_features,
        )
        self._compiled_workflows[workflow_id] = wf
        return wf

    def execute_workflow_graph(
        self,
        workflow_id: str,
        state: dict[str, Any],
        executors: Mapping[str, Any],
        *,
        bindings: Mapping[str, str] | None = None,
        env_features: Sequence[str] = (),
    ) -> dict[str, Any]:
        wf = self._compiled_workflows.get(workflow_id)
        if wf is None:
            return {"schema": SCHEMA, "workflow_id": workflow_id, "succeeded": False, "reason": "UNKNOWN_WORKFLOW", "model_calls": PRODUCER_MODEL_CALLS}
        return wf.execute(state, executors, bindings=bindings, env_features=env_features)

    def graft_workflow_recovery(
        self,
        workflow_id: str,
        node_idx: int,
        recovery_steps: Sequence[Mapping[str, Any]],
        *,
        failed_env_features: Sequence[str] = (),
    ) -> dict[str, Any]:
        wf = self._compiled_workflows.get(workflow_id)
        if wf is None:
            raise KeyError(f"UNKNOWN_WORKFLOW:{workflow_id}")
        rnodes = [
            WorkflowNode(
                node_id=f"{workflow_id}:n{node_idx}:rec{i}",
                kind=str(s.get("kind") or "DataOp"),
                op_name=str(s.get("op") or s.get("action") or f"rec_{i}"),
                params=dict(s.get("params") or {}),
                guard_features=tuple(str(f) for f in (s.get("guard_features") or ())),
            )
            for i, s in enumerate(recovery_steps)
        ]
        return wf.graft_recovery_at_node(node_idx, rnodes, failed_env_features=failed_env_features)

    # ------------------------------------------------------------------
    # Job 5a: Interactive World-Model Agent (`MinimalArc3Agent v5`)
    # ------------------------------------------------------------------
    @staticmethod
    def create_arc3_agent() -> Any:
        from canonical.swe_kernel.minimal_arc3_agent_v1 import MinimalArc3Agent
        return MinimalArc3Agent()

    # ------------------------------------------------------------------
    # Status / Diagnostics (verifies live importability of every wired organ)
    # ------------------------------------------------------------------
    @staticmethod
    def status() -> dict[str, Any]:
        core_organs = {
            "bm25_code_localizer": "canonical.swe_kernel.bm25_code_localizer_v1",
            "producer_lineage_graph": "canonical.swe_kernel.producer_lineage_graph_v1",
            "induced_edit_basis": "canonical.swe_kernel.induced_edit_basis_v1",
            "minimal_subtree_transfer": "canonical.swe_kernel.minimal_subtree_transfer_v1",
            "causal_trace_skill_compiler": "canonical.swe_kernel.causal_trace_to_skill_compiler_v1",
            "dbsp_bitemporal_ppr_memory": "canonical.runtime.hidden_arsenal_unifier_v1",
            "minimal_epistemic_core": "canonical.swe_kernel.minimal_epistemic_core_v1",
            "hdc_semantic_engine": "canonical.swe_kernel.hdc_semantic_engine_v1",
        }
        awakened_dark_organs = {
            "dual_program_splicing": "canonical.swe_kernel.dual_program_splicing_v1",
            "instant_condition_store": "canonical.runtime.instant_condition_store_v1",
            "instant_cu_procedure_store": "canonical.runtime.instant_cu_procedure_store_v1",
            "refusal_is_specification": "canonical.runtime.a_refusal_is_a_specification_v1",
            "epistemic_spec_synthesizer": "canonical.runtime.epistemic_spec_synthesizer_v1",
            "instant_one_shot_learning": "canonical.swe_kernel.instant_one_shot_learning_v1",
            "four_levers_of_learning": "canonical.tools.the_four_levers_of_learning_from_experience_v1",
            "global_extrapolation_chase": "canonical.swe_kernel.global_extrapolation_chase_spine_v1",
            "minimal_arc3_agent": "canonical.swe_kernel.minimal_arc3_agent_v1",
        }
        loaded: dict[str, bool] = {}
        for k, mod_name in {**core_organs, **awakened_dark_organs}.items():
            try:
                __import__(mod_name)
                loaded[k] = True
            except Exception:
                loaded[k] = False
        reg_probe = DarkCapabilityRegistry().probe_all()
        core_ok = all(loaded[k] for k in core_organs)
        return {
            "schema": SCHEMA,
            "core_organs_loaded": core_ok,
            "all_organs_loaded": all(loaded.values()) and (reg_probe["stdlib_engines_verified"] == reg_probe["stdlib_engines_total"]),
            "wired_organ_count": sum(1 for v in loaded.values() if v) + int(reg_probe["unique_modules_imported"]),
            "organs": loaded,
            "dark_registry_stdlib_verified": reg_probe["stdlib_engines_verified"],
            "dark_registry_stdlib_total": reg_probe["stdlib_engines_total"],
            "dark_registry_engines": reg_probe["engines_imported"],
            "dark_registry_total": reg_probe["engines_total"],
            "dark_registry_unique_modules": reg_probe["unique_modules_imported"],
            "model_calls": PRODUCER_MODEL_CALLS,
        }


def self_check() -> dict[str, Any]:
    """Fast self-verification covering every wired DARK organ on real inputs."""
    t0 = time.perf_counter()
    spine = UnifiedFastSpine()
    st = spine.status()

    # 1. Repair with donor-induced originating subtree transfer + FastCoWVerifier
    donor = (
        "d1",
        "def clamp(x, hi):\n    return x <= hi\n",
        "def clamp(x, hi):\n    return x < hi\n",
    )
    buggy = "def is_below(a, b):\n    return a <= b\n"
    test = "assert is_below(1, 2) is True\nassert is_below(2, 2) is False\nassert is_below(3, 2) is False\n"
    rep = spine.repair_function_fast(buggy, test, donor_pairs=[donor], max_candidates=40)

    # 1b. Multi-bug repair via Assertion-Granular Dual-Program Splicing (no single 1-edit fix passes both!)
    two_bug_src = (
        "def score_band(x, y):\n"
        "    a = x - 1\n"
        "    b = y - 1\n"
        "    return (a, b)\n"
    )
    two_bug_test = (
        "assert score_band(5, 10)[0] == 6\n"
        "assert score_band(5, 10)[1] == 11\n"
        "assert score_band(0, 0) == (1, 1)\n"
    )
    splice_rep = spine.repair_function_fast(two_bug_src, two_bug_test, max_candidates=60)

    # 2. Hybrid DominoMemory + DBSPBiTemporalPPRMemory
    turns = [
        {"dia_id": "D1:1", "session": "2023-05-01", "speaker": "Alice", "text": "Alice visited Meridian Observatory yesterday."},
        {"dia_id": "D1:2", "session": "2023-05-02", "speaker": "Bob", "text": "Meridian Observatory houses the Sapphire Telescope."},
        {"dia_id": "D1:3", "session": "2023-05-03", "speaker": "Alice", "text": "I love coffee in the morning."},
    ]
    idx = spine.build_hybrid_memory(turns)
    hits = spine.query_hybrid_memory(idx, "What telescope is linked to Alice?", top_k=3)
    top_ids = list(hits.get("dia_ids") or [])

    # 3. BM25 + ProducerLineage localization on canonical/swe_kernel
    loc = spine.localize_repo_bug(
        pathlib.Path(__file__).resolve().parents[2] / "canonical" / "swe_kernel",
        "FastCoWVerifier check_test_strength mutant",
        top_files=3,
        top_functions=3,
    )

    ok = bool(
        st["core_organs_loaded"]
        and rep.get("fixed")
        and rep.get("method") in ("MINIMAL_SUBTREE_TRANSFER_COW_V1", "INDUCED_EDIT_BASIS_COW_V1")
        and splice_rep.get("fixed")
        and splice_rep.get("method") == "DUAL_PROGRAM_SPLICING_COW_V1"
        and "D1:2" in top_ids
        and len(loc["source_files"]) >= 1
    )
    return {
        "schema": SCHEMA,
        "pass": ok,
        "core_organs_loaded": st["core_organs_loaded"],
        "organs_loaded": st["wired_organ_count"],
        "repair_method": rep.get("method"),
        "splice_method": splice_rep.get("method"),
        "hybrid_top_ids": top_ids,
        "localized_top_file": loc["source_files"][0]["path"] if loc["source_files"] else None,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
        "model_calls": PRODUCER_MODEL_CALLS,
    }


if __name__ == "__main__":
    import json
    import sys
    _repo_root = str(pathlib.Path(__file__).resolve().parents[2])
    if _repo_root not in sys.path:
        sys.path.insert(0, _repo_root)
    print(json.dumps(self_check(), indent=2))
