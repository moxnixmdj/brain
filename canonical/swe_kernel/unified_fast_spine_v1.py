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


class UnifiedFastSpine:
    """Single thin fast-path coordinator unifying Brain's verified zero-model organs."""

    def __init__(self, *, use_micro_backend: bool = False) -> None:
        self.use_micro_backend = bool(use_micro_backend)
        self._verified_donor_pairs: list[tuple[str, str, str]] = []
        self._subtree_store: Any = None
        self._learned_repos: set[str] = set()

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
        # Stage 1a: Originating Minimal-Subtree Transfer rules (git history + verified fixes)
        if store.rules():
            try:
                sub_cands = store.propose_source_rewrites(
                    source,
                    focus_lines=focus_lines or None,
                    max_candidates=min(40, max_candidates),
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

        # Stage 1b: History/donor-induced AST edit templates (`induced_edit_basis_v1`)
        all_donors = list(self._verified_donor_pairs)
        if donor_pairs:
            all_donors.extend(donor_pairs)
        induced_tested = 0
        if all_donors:
            try:
                templates = ieb.induce_templates(all_donors, context_depth=1, max_templates_per_pair=6)
                templates.extend(ieb.induce_templates(all_donors, context_depth=0, max_templates_per_pair=6))
                node_templates = ieb.induce_node_templates(all_donors, context_depth=1)
                cands = ieb.candidates_from_templates(source, templates, max_candidates=min(48, max_candidates))
                cands.extend(
                    ieb.candidates_from_node_templates(source, node_templates, max_candidates=min(32, max_candidates))
                )
                for cand in cands:
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

        # Stage 2: PriorRepairEngine (with general algebraic structural ops) over FastCoWVerifier
        engine = PriorRepairEngine()
        prior_budget = max(1, max_candidates - subtree_tested - induced_tested)
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

        return {
            "dom_idx": dom_idx,
            "dbsp": dbsp,
            "entity_to_dia": dict(ent_to_dia),
            "turn_by_dia": turn_by_dia,
            "comp_cache": comp_cache,
            "ppr_cache": {},
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
    ) -> dict[str, Any]:
        """Fuse DominoMemory BM25+char-ngram ranking + DBSP Bi-Temporal PPR + zero-parameter zlib Compression Gain."""
        from canonical.swe_kernel.minimal_epistemic_core_v1 import DominoMemory

        dom_idx = index["dom_idx"]
        dbsp = index["dbsp"]
        ent_to_dia: Mapping[str, list[str]] = index["entity_to_dia"]
        turn_by_dia: Mapping[str, dict[str, Any]] = index["turn_by_dia"]
        comp_cache: Mapping[str, tuple[bytes, int]] = index.get("comp_cache") or {}
        ppr_cache = index.get("ppr_cache") if isinstance(index.get("ppr_cache"), dict) else None

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

        ordered = sorted(rrf_scores.items(), key=lambda x: -x[1])[:top_k]
        dia_ids = [did for did, _ in ordered]
        top_turns = [
            {
                "dia_id": did,
                "speaker": turn_by_dia.get(did, {}).get("speaker", ""),
                "session": turn_by_dia.get(did, {}).get("session", ""),
                "text": turn_by_dia.get(did, {}).get("text", ""),
                "hybrid_score": round(sc, 6),
            }
            for did, sc in ordered
        ]
        return {
            "dia_ids": dia_ids,
            "top_turns": top_turns,
            "speaker_conflict": bool(base.get("speaker_conflict", False)),
            "conflict_score": float(base.get("conflict_score", 0.0)),
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
    # Job 5a: Interactive World-Model Agent (`MinimalArc3Agent v3`)
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
        core_ok = all(loaded[k] for k in core_organs)
        return {
            "schema": SCHEMA,
            "core_organs_loaded": core_ok,
            "all_organs_loaded": all(loaded.values()),
            "wired_organ_count": sum(1 for v in loaded.values() if v),
            "organs": loaded,
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
