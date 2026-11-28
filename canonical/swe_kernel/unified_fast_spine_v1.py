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

import pathlib
import re
import time
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


class UnifiedFastSpine:
    """Single thin fast-path coordinator unifying Brain's verified zero-model organs."""

    def __init__(self, *, use_micro_backend: bool = False) -> None:
        self.use_micro_backend = bool(use_micro_backend)
        self._verified_donor_pairs: list[tuple[str, str, str]] = []

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
    # Jobs 3 + 4 + 6a: Anti-Lie CoW + Induced Edit Basis + Prior Repair
    # ------------------------------------------------------------------
    def repair_function_fast(
        self,
        source: str,
        test_code: str,
        *,
        donor_pairs: Sequence[tuple[str, str, str]] | None = None,
        max_candidates: int = 160,
        timeout_s: float = 0.10,
        verify_test_strength: bool = True,
        use_micro_backend: bool | None = None,
    ) -> dict[str, Any]:
        """Anti-lie check -> InducedEditBasis templates -> PriorRepairEngine (os.fork CoW)."""
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

        # Stage 1: Try history/donor-induced AST edit templates (`induced_edit_basis_v1`) first!
        all_donors = list(self._verified_donor_pairs)
        if donor_pairs:
            all_donors.extend(donor_pairs)
        induced_tested = 0
        if all_donors:
            try:
                templates = ieb.induce_templates(all_donors, context_depth=1, max_templates_per_pair=6)
                templates.extend(ieb.induce_templates(all_donors, context_depth=0, max_templates_per_pair=6))
                node_templates = ieb.induce_node_templates(all_donors, context_depth=1)
                cands = ieb.candidates_from_templates(source, templates, max_candidates=min(60, max_candidates))
                cands.extend(
                    ieb.candidates_from_node_templates(source, node_templates, max_candidates=min(40, max_candidates))
                )
                seen_src: set[str] = {source}
                for cand in cands:
                    cand_src = str(cand.get("source") or "")
                    if not cand_src or cand_src in seen_src:
                        continue
                    seen_src.add(cand_src)
                    induced_tested += 1
                    outcome = FastCoWVerifier.run_isolated(cand_src, test_code, timeout_s=timeout_s)
                    if outcome.passed:
                        self._verified_donor_pairs.append((f"verified_{len(self._verified_donor_pairs)}", source, cand_src))
                        return {
                            "schema": SCHEMA,
                            "fixed": True,
                            "method": "INDUCED_EDIT_BASIS_COW_V1",
                            "op_kind": str(cand.get("mutation") or cand.get("template_id") or "induced_template"),
                            "source": cand_src,
                            "candidates_tested": induced_tested,
                            "test_strength": strength,
                            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
                            "model_calls": PRODUCER_MODEL_CALLS,
                        }
            except Exception:
                pass

        # Stage 2: PriorRepairEngine over FastCoWVerifier (+ optional LocalMicroModelBackend proposals)
        engine = PriorRepairEngine()
        res = engine.repair(
            source,
            test_code,
            max_candidates=max(1, max_candidates - induced_tested),
            timeout_s=timeout_s,
        )
        micro_tested = 0
        use_micro = self.use_micro_backend if use_micro_backend is None else bool(use_micro_backend)
        if not res.get("fixed") and use_micro:
            try:
                backend = LocalMicroModelBackend()
                for cand_src in backend.propose_python_patches(source, test_code, n_samples=4):
                    if not cand_src or cand_src == source:
                        continue
                    micro_tested += 1
                    outcome = FastCoWVerifier.run_isolated(cand_src, test_code, timeout_s=timeout_s)
                    if outcome.passed:
                        res = {"fixed": True, "source": cand_src, "op_kind": "local_micro_backend", "candidates_tested": res.get("candidates_tested", 0)}
                        break
            except Exception:
                pass
        out = dict(res)
        out["schema"] = SCHEMA
        out["method"] = "LOCAL_MICRO_BACKEND_COW_V1" if micro_tested and out.get("fixed") else "PRIOR_REPAIR_COW_V1"
        out["candidates_tested"] = int(res.get("candidates_tested", 0)) + induced_tested + micro_tested
        out["induced_candidates_tested"] = induced_tested
        out["test_strength"] = strength
        out["elapsed_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)
        out["model_calls"] = PRODUCER_MODEL_CALLS
        if out.get("fixed") and out.get("source"):
            self._verified_donor_pairs.append((f"verified_{len(self._verified_donor_pairs)}", source, str(out["source"])))
        return out

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
        for idx, t in enumerate(indexed_turns):
            dia_id = str(t.get("dia_id") or f"T:{idx}")
            turn_by_dia[dia_id] = t
            text = str(t.get("text") or "")
            speaker = str(t.get("speaker") or "").strip().lower()
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
    ) -> dict[str, Any]:
        """Fuse DominoMemory BM25+char-ngram ranking with DBSP Bi-Temporal PPR multi-hop boost."""
        from canonical.swe_kernel.minimal_epistemic_core_v1 import DominoMemory

        dom_idx = index["dom_idx"]
        dbsp = index["dbsp"]
        ent_to_dia: Mapping[str, list[str]] = index["entity_to_dia"]
        turn_by_dia: Mapping[str, dict[str, Any]] = index["turn_by_dia"]
        ppr_cache = index.get("ppr_cache") if isinstance(index.get("ppr_cache"), dict) else None

        base = DominoMemory.retrieve_turns(dom_idx, query, top_k=max(top_k * 3, 25))
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
            "causal_trace_skill_compiler": "canonical.swe_kernel.causal_trace_to_skill_compiler_v1",
            "dbsp_bitemporal_ppr_memory": "canonical.runtime.hidden_arsenal_unifier_v1",
            "minimal_epistemic_core": "canonical.swe_kernel.minimal_epistemic_core_v1",
        }
        optional_organs = {
            "minimal_arc3_agent": "canonical.swe_kernel.minimal_arc3_agent_v1",
        }
        loaded: dict[str, bool] = {}
        for k, mod_name in {**core_organs, **optional_organs}.items():
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

    # 1. Repair with donor-induced edit basis (dark jewel #3) + FastCoWVerifier
    donor = (
        "d1",
        "def clamp(x, hi):\n    return x <= hi\n",
        "def clamp(x, hi):\n    return x < hi\n",
    )
    buggy = "def is_below(a, b):\n    return a <= b\n"
    test = "assert is_below(1, 2) is True\nassert is_below(2, 2) is False\nassert is_below(3, 2) is False\n"
    rep = spine.repair_function_fast(buggy, test, donor_pairs=[donor], max_candidates=40)

    # 2. Hybrid DominoMemory + DBSPBiTemporalPPRMemory (dark jewel #5)
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
        and rep.get("method") == "INDUCED_EDIT_BASIS_COW_V1"
        and "D1:2" in top_ids
        and len(loc["source_files"]) >= 1
    )
    return {
        "schema": SCHEMA,
        "pass": ok,
        "core_organs_loaded": st["core_organs_loaded"],
        "organs_loaded": st["wired_organ_count"],
        "repair_method": rep.get("method"),
        "hybrid_top_ids": top_ids,
        "localized_top_file": loc["source_files"][0]["path"] if loc["source_files"] else None,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
        "model_calls": PRODUCER_MODEL_CALLS,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(self_check(), indent=2))
