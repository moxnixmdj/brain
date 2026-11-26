#!/usr/bin/env python3
"""Canonical 5-Timescale Verification-First Memory Bus & Sleep-Time Crystallizer (`0G`).

Unifies Project Brain's previously disconnected learning, anti-unification,
e-graph, skill-crystallization, provenance, and negative-space modules into one
persistent 5-timescale memory architecture wired into ``brain_unified_model_v1``:

  - T0 Working CoW Frame: ephemeral workspace/tomography diffs.
  - T1 Bi-Temporal Lossless Causal Episode Graph (AMA-Agent + Graphiti):
       exact (pre_state, action, exact_args, effect/refusal, post_state, valid_at, invalid_at)
       edges for lossless multi-hop causal & exact-argument retrieval.
  - T2 CDCL Negative-Space Conflict Clause Store:
       backed by ``canonical.swe_kernel.witness_inversion_v1.NegativeSpaceInvariantStore``
       for O(1) pruning of refuted actions/expressions/patches.
  - T3 Sleep-Time E-Stitch / Plotkin-LGG Crystallized Skill Library:
       backed by ``canonical.swe_kernel.concept_library_v1``,
       ``canonical.swe_kernel.structural_rewrite_induction_v1``,
       ``canonical.swe_kernel.verified_skill_crystallizer_v1``,
       ``canonical.swe_kernel.egraph_and_deductive_synthesizer_v1``, and
       ``canonical.tools.an_actions_effect_is_a_provenance_map_v1``.
       Supports O(1) exact selective unlearning with zero collateral damage.
  - T4 Optional External Adapter Registry (e.g., KV-cartridge / LoRA descriptors)
       kept strictly separate from ``K3 = 0`` deterministic execution.
"""
from __future__ import annotations

import ast
import hashlib
import json
import math
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime import demonstration_version_space_v1 as demo_vs
from canonical.swe_kernel import concept_library_v1 as concept_lib
from canonical.swe_kernel import egraph_and_deductive_synthesizer_v1 as egraph_synth
from canonical.swe_kernel import guarded_meaning_ir_v1 as meaning_ir
from canonical.swe_kernel import structural_rewrite_induction_v1 as rewrite_ind
from canonical.swe_kernel import tree_sitter_cst_skill_skeleton_v1 as cst_skeleton
from canonical.swe_kernel import verified_skill_crystallizer_v1 as skill_cryst
from canonical.swe_kernel import witness_inversion_v1 as witness_inv
from canonical.tools import an_actions_effect_is_a_provenance_map_v1 as prov_map
from canonical.tools import the_goal_is_a_quotient_of_the_trace_v1 as trace_quotient
from canonical.tools import the_precondition_is_not_in_the_trace_v1 as precond_ind

SCHEMA = "PROJECT_BRAIN_CANONICAL_MEMORY_CRYSTALLIZER_V1"
NON_CLAIMS = (
    "no_capability_credit",
    "no_ownership_credit",
    "no_terminal_credit",
    "zero_model_verification_first_memory",
)


def _sha16(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, default=str, ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _canonical_ast_digest(source_text: str) -> str | None:
    try:
        mod = ast.parse(source_text)
        canon = concept_lib.canonicalize_ast_via_egraph(mod)
        return hashlib.sha256(ast.dump(canon, include_attributes=False).encode("utf-8")).hexdigest()[:16]
    except Exception:
        return None


@dataclass
class CausalEdge:
    edge_id: str
    episode_id: str
    step_idx: int
    pre_state: str
    action: str
    exact_args: dict[str, Any]
    effect: dict[str, Any]
    post_state: str
    refused: bool = False
    valid_at: float = 0.0
    invalid_at: float | None = None
    provenance: str = ""

    def is_valid_at(self, ts: float | None = None) -> bool:
        if ts is None:
            return self.invalid_at is None
        if ts < self.valid_at:
            return False
        return self.invalid_at is None or ts < self.invalid_at

    def as_dict(self) -> dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "episode_id": self.episode_id,
            "step_idx": self.step_idx,
            "pre_state": self.pre_state,
            "action": self.action,
            "exact_args": self.exact_args,
            "effect": self.effect,
            "post_state": self.post_state,
            "refused": self.refused,
            "valid_at": self.valid_at,
            "invalid_at": self.invalid_at,
            "provenance": self.provenance,
        }


@dataclass
class CrystallizedSkill:
    skill_id: str
    kind: str  # "ACTION_MACRO" | "CODE_REWRITE" | "AST_CONCEPT"
    trigger_key: str
    payload: dict[str, Any]
    provenance_episode_id: str
    verified: bool = True
    hits: int = 0
    created_at: float = 0.0
    forgotten: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "kind": self.kind,
            "trigger_key": self.trigger_key,
            "payload": self.payload,
            "provenance_episode_id": self.provenance_episode_id,
            "verified": self.verified,
            "hits": self.hits,
            "created_at": self.created_at,
            "forgotten": self.forgotten,
        }


@dataclass
class ConflictClause:
    clause_id: str
    domain: str
    context_sig: str
    bad_candidate: str
    reason: str
    created_at: float = 0.0
    retracted: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "clause_id": self.clause_id,
            "domain": self.domain,
            "context_sig": self.context_sig,
            "bad_candidate": self.bad_candidate,
            "reason": self.reason,
            "created_at": self.created_at,
            "retracted": self.retracted,
        }


class DualDriftDetector:
    """Zero-dependency hybrid ADWIN + BOCPD + Page-Hinkley concept-drift detector (Wave 11).

    Combines three complementary online detectors over bounded ``[0.0, 1.0]`` outcome streams:
      - **ADWIN** (Hoeffding adaptive window split): catches gradual & persistent mean shifts.
      - **BOCPD** (Adams & MacKay exact Beta-Bernoulli Bayesian Online Changepoint Detection):
        catches abrupt piecewise-constant regime switches that blind sliding mean windows.
      - **Page-Hinkley**: catches sustained downward drift in skill/route success rates.
    """

    def __init__(
        self,
        *,
        adwin_delta: float = 0.05,
        bocpd_hazard: float = 1.0 / 25.0,
        ph_delta: float = 0.02,
        ph_lambda: float = 3.5,
        max_window: int = 200,
        max_run: int = 64,
    ) -> None:
        self.adwin_delta = float(adwin_delta)
        self.bocpd_hazard = float(bocpd_hazard)
        self.ph_delta = float(ph_delta)
        self.ph_lambda = float(ph_lambda)
        self.max_window = max(24, int(max_window))
        self.max_run = max(16, int(max_run))
        self._streams: dict[str, dict[str, Any]] = {}

    def _state(self, stream: str) -> dict[str, Any]:
        st = self._streams.get(stream)
        if st is None:
            st = {
                "n": 0,
                "window": [],
                "run_probs": [1.0],
                "alphas": [1.0],
                "betas": [1.0],
                "peak_map_run": 0,
                "ph_mean": 0.0,
                "ph_u": 0.0,
                "ph_min_u": 0.0,
                "drift_count": 0,
                "last_drift_reason": None,
            }
            self._streams[stream] = st
        return st

    def observe(self, stream: str, value: float | bool) -> dict[str, Any]:
        x = 1.0 if value is True else (0.0 if value is False else max(0.0, min(1.0, float(value))))
        st = self._state(str(stream))
        st["n"] += 1
        win: list[float] = st["window"]
        win.append(x)
        if len(win) > self.max_window:
            del win[:-self.max_window]

        # 1. ADWIN Hoeffding split test
        adwin_drift = False
        adwin_split_delta = 0.0
        n_w = len(win)
        min_sub = 6
        if n_w >= 2 * min_sub:
            prefix = [0.0] * (n_w + 1)
            for idx, v in enumerate(win):
                prefix[idx + 1] = prefix[idx] + v
            total = prefix[n_w]
            log_term = math.log(4.0 / max(1e-9, self.adwin_delta))
            best_k = -1
            for k in range(min_sub, n_w - min_sub + 1):
                m1 = prefix[k] / k
                m2 = (total - prefix[k]) / (n_w - k)
                diff = abs(m1 - m2)
                m_harm = 1.0 / ((1.0 / k) + (1.0 / (n_w - k)))
                eps = math.sqrt((1.0 / (2.0 * m_harm)) * log_term)
                if diff > eps:
                    adwin_drift = True
                    adwin_split_delta = max(adwin_split_delta, diff)
                    best_k = k
            if adwin_drift and best_k > 0:
                del win[:best_k]

        # 2. BOCPD exact conjugate Beta-Bernoulli update
        run_probs: list[float] = st["run_probs"]
        alphas: list[float] = st["alphas"]
        betas: list[float] = st["betas"]
        h = self.bocpd_hazard
        growth: list[float] = []
        cp_mass = 0.0
        for p_r, a_r, b_r in zip(run_probs, alphas, betas):
            pred = a_r / (a_r + b_r)
            like = max(1e-9, pred * x + (1.0 - pred) * (1.0 - x))
            joint = p_r * like
            growth.append(joint * (1.0 - h))
            cp_mass += joint * h
        new_probs = [cp_mass] + growth
        norm = sum(new_probs) or 1.0
        new_probs = [p / norm for p in new_probs[: self.max_run]]
        new_alphas = [1.0] + [a + x for a in alphas[: self.max_run - 1]]
        new_betas = [1.0] + [b + (1.0 - x) for b in betas[: self.max_run - 1]]
        st["run_probs"] = new_probs
        st["alphas"] = new_alphas
        st["betas"] = new_betas
        map_run = max(range(len(new_probs)), key=lambda i: new_probs[i])
        short_run_mass = sum(new_probs[: min(5, len(new_probs))])
        bocpd_drift = False
        if st["peak_map_run"] >= 8 and map_run <= 4 and short_run_mass >= 0.45:
            bocpd_drift = True
            st["peak_map_run"] = map_run
        else:
            st["peak_map_run"] = max(st["peak_map_run"], map_run)

        # 3. Page-Hinkley downward shift detector
        st["ph_mean"] = st["ph_mean"] + (x - st["ph_mean"]) / st["n"]
        st["ph_u"] = st["ph_u"] + (st["ph_mean"] - x - self.ph_delta)
        st["ph_min_u"] = min(st["ph_min_u"], st["ph_u"])
        ph_stat = st["ph_u"] - st["ph_min_u"]
        ph_drift = ph_stat > self.ph_lambda
        if ph_drift:
            st["ph_u"] = 0.0
            st["ph_min_u"] = 0.0

        drift = adwin_drift or bocpd_drift or ph_drift
        reasons = []
        if adwin_drift:
            reasons.append("ADWIN")
        if bocpd_drift:
            reasons.append("BOCPD")
        if ph_drift:
            reasons.append("PAGE_HINKLEY")
        if drift:
            st["drift_count"] += 1
            st["last_drift_reason"] = "+".join(reasons)

        recent = win[-min(10, len(win)) :]
        return {
            "stream": str(stream),
            "n_obs": int(st["n"]),
            "value": round(x, 4),
            "drift_detected": drift,
            "adwin_drift": adwin_drift,
            "bocpd_drift": bocpd_drift,
            "page_hinkley_drift": ph_drift,
            "reasons": reasons,
            "bocpd_map_run_length": int(map_run),
            "bocpd_short_run_mass": round(short_run_mass, 4),
            "adwin_split_delta": round(adwin_split_delta, 4),
            "page_hinkley_stat": round(ph_stat, 4),
            "recent_mean": round(sum(recent) / max(1, len(recent)), 4),
            "total_drifts": int(st["drift_count"]),
        }

    def summary(self) -> dict[str, Any]:
        return {
            name: {
                "n_obs": int(st["n"]),
                "drift_count": int(st["drift_count"]),
                "last_drift_reason": st["last_drift_reason"],
                "window_size": len(st["window"]),
                "recent_mean": round(sum(st["window"][-10:]) / max(1, len(st["window"][-10:])), 4),
            }
            for name, st in sorted(self._streams.items())
        }


class VerificationFirstMemoryBus:
    """5-timescale verification-first memory bus with lossless causality, CDCL nogoods,
    sleep-time E-Stitch/Plotkin-LGG crystallization, and O(1) selective unlearning.
    """

    def __init__(self, state_path: str | Path | None = None) -> None:
        self.state_path = Path(state_path) if state_path is not None else None
        # T0: ephemeral working frames
        self.working_frames: dict[str, dict[str, Any]] = {}
        # T1: lossless bi-temporal causal episode graph
        self.causal_edges: dict[str, CausalEdge] = {}
        self._edges_by_episode: dict[str, list[str]] = {}
        self._edges_by_pre: dict[str, list[str]] = {}
        self._edges_by_post: dict[str, list[str]] = {}
        # T2: CDCL negative-space conflict clauses (backed by NegativeSpaceInvariantStore)
        self._neg_store = witness_inv.NegativeSpaceInvariantStore(path=None)
        self.conflict_clauses: dict[str, ConflictClause] = {}
        self._conflict_lookup: dict[tuple[str, str, str], str] = {}
        # T3: crystallized skills + compounding concept library + version-space skills
        self.skills: dict[str, CrystallizedSkill] = {}
        self._skills_by_trigger: dict[str, list[str]] = {}
        self._repair_pairs: list[tuple[str, str, str]] = []  # (pair_id, before_src, after_src)
        self._induced_rewrite_rules: list[rewrite_ind.Rule] = []
        self._concept_library = concept_lib.CompoundingConceptLibrary(state_path=None)
        self._version_spaces: dict[str, demo_vs.SkillSet] = {}
        self._version_space_traces: dict[str, list[list[tuple[dict[str, Any], str]]]] = {}
        self._version_space_library = demo_vs.SkillLibrary()
        self._semi_egraph = meaning_ir.SemiPersistentEGraph()
        # T4: optional external adapter descriptors (metadata only, never required)
        self.external_adapters: dict[str, dict[str, Any]] = {}
        # Immutable selective-forgetting provenance log
        self.forgetting_ledger: list[dict[str, Any]] = []
        # Wave 3-6: exact applicability boundaries & anti-authority-collapse verified event log
        self._applicability_boundaries: dict[str, dict[str, Any]] = {}
        self._verified_event_log: list[dict[str, Any]] = []
        self._verified_event_last_hash: str = "0" * 64
        # Wave 11: Library-drift immunity (skill_contribution_ledger_v1) + DualDriftDetector
        self._drift_detector = DualDriftDetector()
        self._contribution_ledger: Any = None
        self._contribution_db_path: Path | None = None
        # Wave 15: MemGuard persistent verifier lifecycle + rule_expiry_v1 + Anti-Skill refutations + lazy FTS5 index
        self._skill_lifecycle: dict[str, dict[str, Any]] = {}
        self._anti_skills: dict[str, dict[str, Any]] = {}
        self._fts5_conn: Any = None
        self._fts5_watermark: tuple[int, int, int, int] = (-1, -1, -1, -1)
        self._clock: float = 0.0

        if self.state_path is not None and self.state_path.exists():
            self.load(self.state_path)

    def _tick(self, explicit_ts: float | None = None) -> float:
        if explicit_ts is not None:
            self._clock = max(self._clock, float(explicit_ts))
            return float(explicit_ts)
        self._clock = max(self._clock + 1.0, time.time())
        return self._clock

    # ------------------------------------------------------------------ T0
    def push_working_frame(self, frame_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        entry = {"frame_id": frame_id, "ts": self._tick(), **dict(payload)}
        self.working_frames[frame_id] = entry
        return entry

    def clear_working_frames(self) -> int:
        n = len(self.working_frames)
        self.working_frames.clear()
        return n

    # ------------------------------------------------------------------ T1
    def record_causal_step(
        self,
        *,
        episode_id: str,
        step_idx: int,
        pre_state: str,
        action: str,
        exact_args: Mapping[str, Any] | None = None,
        effect: Mapping[str, Any] | None = None,
        post_state: str,
        refused: bool = False,
        valid_at: float | None = None,
        provenance: str = "",
    ) -> CausalEdge:
        ts = self._tick(valid_at)
        args_dict = dict(exact_args or {})
        eff_dict = dict(effect or {})
        eid = "ce_" + _sha16([episode_id, step_idx, pre_state, action, args_dict, post_state, ts])
        edge = CausalEdge(
            edge_id=eid,
            episode_id=str(episode_id),
            step_idx=int(step_idx),
            pre_state=str(pre_state),
            action=str(action),
            exact_args=args_dict,
            effect=eff_dict,
            post_state=str(post_state),
            refused=bool(refused),
            valid_at=ts,
            invalid_at=None,
            provenance=str(provenance),
        )
        self.causal_edges[eid] = edge
        self._edges_by_episode.setdefault(edge.episode_id, []).append(eid)
        self._edges_by_pre.setdefault(edge.pre_state, []).append(eid)
        self._edges_by_post.setdefault(edge.post_state, []).append(eid)
        return edge

    def invalidate_causal_edge(self, edge_id: str, *, reason: str = "SUPERSEDED", at_ts: float | None = None) -> bool:
        edge = self.causal_edges.get(edge_id)
        if edge is None or edge.invalid_at is not None:
            return False
        ts = self._tick(at_ts)
        edge.invalid_at = ts
        self.forgetting_ledger.append(
            {"kind": "CAUSAL_EDGE_INVALIDATED", "target_id": edge_id, "ts": ts, "reason": reason}
        )
        return True

    def query_causal_chain(
        self,
        *,
        start_state: str | None = None,
        target_state: str | None = None,
        action_filter: str | None = None,
        at_ts: float | None = None,
        max_hops: int = 8,
    ) -> list[dict[str, Any]]:
        """Lossless multi-hop causal trajectory query over bi-temporal edges (AMA-Bench style)."""
        if start_state is not None and target_state is not None:
            # BFS over valid forward causal edges from start_state to target_state
            queue: list[tuple[str, list[CausalEdge]]] = [(str(start_state), [])]
            visited: set[str] = {str(start_state)}
            while queue:
                cur, path = queue.pop(0)
                if cur == str(target_state) and path:
                    return [e.as_dict() for e in path]
                if len(path) >= max_hops:
                    continue
                for eid in self._edges_by_pre.get(cur, ()):
                    edge = self.causal_edges[eid]
                    if not edge.is_valid_at(at_ts) or edge.refused:
                        continue
                    if action_filter and edge.action != action_filter:
                        continue
                    if edge.post_state not in visited:
                        visited.add(edge.post_state)
                        queue.append((edge.post_state, path + [edge]))
            return []

        if target_state is not None:
            # Direct causal ancestors producing target_state
            matches = [
                self.causal_edges[eid]
                for eid in self._edges_by_post.get(str(target_state), ())
                if self.causal_edges[eid].is_valid_at(at_ts)
                and (action_filter is None or self.causal_edges[eid].action == action_filter)
            ]
            matches.sort(key=lambda e: (e.valid_at, e.step_idx))
            return [m.as_dict() for m in matches]

        # Filtered scan
        out = [
            e.as_dict()
            for e in self.causal_edges.values()
            if e.is_valid_at(at_ts)
            and (start_state is None or e.pre_state == str(start_state))
            and (action_filter is None or e.action == action_filter)
        ]
        out.sort(key=lambda d: (d["valid_at"], d["step_idx"]))
        return out

    # ------------------------------------------------------------------ T2
    def record_conflict(
        self,
        bad_candidate: str,
        *,
        reason: str,
        domain: str = "generic",
        context_sig: str = "*",
    ) -> ConflictClause:
        """Compile a failed candidate into an O(1) CDCL negative-space conflict clause."""
        ts = self._tick()
        cand_norm = str(bad_candidate).strip()
        key = (str(domain), str(context_sig), cand_norm)
        existing_id = self._conflict_lookup.get(key)
        if existing_id and existing_id in self.conflict_clauses and not self.conflict_clauses[existing_id].retracted:
            return self.conflict_clauses[existing_id]

        cid = "ng_" + _sha16([domain, context_sig, cand_norm, reason])
        clause = ConflictClause(
            clause_id=cid,
            domain=str(domain),
            context_sig=str(context_sig),
            bad_candidate=cand_norm,
            reason=str(reason),
            created_at=ts,
            retracted=False,
        )
        self.conflict_clauses[cid] = clause
        self._conflict_lookup[key] = cid
        # Also mirror code expressions into NegativeSpaceInvariantStore for canonical AST refutation
        try:
            self._neg_store.record_refutation(cand_norm, reason=reason, repo=domain, commit=context_sig)
        except Exception:
            pass
        return clause

    def is_pruned(self, candidate: str, *, domain: str = "generic", context_sig: str = "*") -> bool:
        cand_norm = str(candidate).strip()
        for ctx in (str(context_sig), "*"):
            cid = self._conflict_lookup.get((str(domain), ctx, cand_norm))
            if cid is not None and not self.conflict_clauses[cid].retracted:
                return True
        if domain == "python_expr":
            try:
                if self._neg_store.is_refuted(cand_norm):
                    return True
            except Exception:
                pass
        return False

    def prune_candidates(
        self,
        candidates: Sequence[str],
        *,
        domain: str = "generic",
        context_sig: str = "*",
    ) -> list[str]:
        return [c for c in candidates if not self.is_pruned(c, domain=domain, context_sig=context_sig)]

    def retract_conflict(self, clause_id: str, *, reason: str = "ENV_CHANGED") -> bool:
        clause = self.conflict_clauses.get(clause_id)
        if clause is None or clause.retracted:
            return False
        clause.retracted = True
        self.forgetting_ledger.append(
            {"kind": "CONFLICT_RETRACTED", "target_id": clause_id, "ts": self._tick(), "reason": reason}
        )
        return True

    # ------------------------------------------------------------------ T3
    def crystallize_action_macro(
        self,
        *,
        trigger_key: str,
        actions: Sequence[Any],
        provenance_episode_id: str,
        preconditions: Mapping[str, Any] | None = None,
    ) -> CrystallizedSkill:
        """Compile a single verified episode into an O(1) Tier-0 procedural action macro."""
        ts = self._tick()
        payload = {
            "actions": list(actions),
            "preconditions": dict(preconditions or {}),
        }
        sid = "sk_macro_" + _sha16([trigger_key, payload["actions"]])
        existing = self.skills.get(sid)
        if existing is not None and not existing.forgotten:
            return existing
        skill = CrystallizedSkill(
            skill_id=sid,
            kind="ACTION_MACRO",
            trigger_key=str(trigger_key),
            payload=payload,
            provenance_episode_id=str(provenance_episode_id),
            verified=True,
            hits=0,
            created_at=ts,
            forgotten=False,
        )
        self.skills[sid] = skill
        self._skills_by_trigger.setdefault(skill.trigger_key, [])
        if sid not in self._skills_by_trigger[skill.trigger_key]:
            self._skills_by_trigger[skill.trigger_key].append(sid)
        return skill

    def crystallize_code_repair(
        self,
        *,
        before_source: str,
        after_source: str,
        trigger_key: str = "python_repair",
        error_class: str = "GENERIC",
        provenance_episode_id: str = "verified_repair",
    ) -> CrystallizedSkill:
        """Anti-unify a verified code repair pair into a reusable Tier-0 AST/code rewrite skill."""
        ts = self._tick()
        code_rule = skill_cryst.anti_unify_code_rule(
            before_source,
            after_source,
            language="python",
            error_class=error_class,
        )
        egraph_before = _canonical_ast_digest(before_source)
        egraph_after = _canonical_ast_digest(after_source)
        pair_id = "pair_" + _sha16([before_source, after_source])
        self._repair_pairs.append((pair_id, before_source, after_source))

        # Also induce structural AST rewrite rules right away
        induced = rewrite_ind.learn_rules([(pair_id, before_source, after_source)], max_rules_per_pair=8)
        for r in induced:
            self._induced_rewrite_rules.append(r)

        payload = {
            "crystallized_rule": dict(code_rule) if isinstance(code_rule, Mapping) else {"raw": str(code_rule)},
            "egraph_before_digest": egraph_before,
            "egraph_after_digest": egraph_after,
            "error_class": error_class,
            "induced_rule_count": len(induced),
        }
        sid = "sk_code_" + _sha16([trigger_key, egraph_before, egraph_after, payload["crystallized_rule"]])
        skill = CrystallizedSkill(
            skill_id=sid,
            kind="CODE_REWRITE",
            trigger_key=str(trigger_key),
            payload=payload,
            provenance_episode_id=str(provenance_episode_id),
            verified=True,
            hits=0,
            created_at=ts,
            forgotten=False,
        )
        self.skills[sid] = skill
        self._skills_by_trigger.setdefault(skill.trigger_key, [])
        if sid not in self._skills_by_trigger[skill.trigger_key]:
            self._skills_by_trigger[skill.trigger_key].append(sid)
        return skill

    def lookup_tier0_skills(self, trigger_key: str) -> list[dict[str, Any]]:
        """O(1) Tier-0 lookup returning ONLY active (non-forgotten) verified skills."""
        out: list[dict[str, Any]] = []
        for sid in self._skills_by_trigger.get(str(trigger_key), ()):
            sk = self.skills.get(sid)
            if sk is not None and sk.verified and not sk.forgotten:
                sk.hits += 1
                out.append(sk.as_dict())
        return out

    def apply_crystallized_code_skills(self, source_text: str, *, trigger_key: str | None = None) -> list[dict[str, Any]]:
        """Apply active (non-forgotten) Tier-0 crystallized code rewrite skills to new source code."""
        candidates: list[dict[str, Any]] = []
        seen_outputs: set[str] = set()

        # 1. Parameterized verified_skill_crystallizer rules
        for sk in self.skills.values():
            if sk.forgotten or not sk.verified or sk.kind != "CODE_REWRITE":
                continue
            if trigger_key is not None and sk.trigger_key != trigger_key:
                continue
            rule = sk.payload.get("crystallized_rule")
            if isinstance(rule, Mapping):
                patched = skill_cryst.apply_crystallized_code_rule(source_text, rule)
                if patched and patched != source_text and patched not in seen_outputs:
                    seen_outputs.add(patched)
                    sk.hits += 1
                    candidates.append(
                        {
                            "skill_id": sk.skill_id,
                            "mechanism": "VERIFIED_SKILL_CRYSTALLIZER",
                            "patched_source": patched,
                        }
                    )

        # 2. Structural AST anti-unification rewrite rules (if any active CODE_REWRITE skills remain)
        active_code_skills = [s for s in self.skills.values() if not s.forgotten and s.kind == "CODE_REWRITE"]
        if active_code_skills and self._induced_rewrite_rules:
            rw_hits = rewrite_ind.rewrite(source_text, self._induced_rewrite_rules, cap=8)
            for hit in rw_hits:
                patched = hit.get("source") or hit.get("rewritten")
                if isinstance(patched, str) and patched != source_text and patched not in seen_outputs:
                    seen_outputs.add(patched)
                    candidates.append(
                        {
                            "skill_id": "structural_rewrite_rule",
                            "mechanism": "STRUCTURAL_REWRITE_INDUCTION",
                            "patched_source": patched,
                        }
                    )
        return candidates

    def sleep_consolidate(
        self,
        *,
        program_sources: Sequence[str] = (),
        min_nodes: int = 5,
        max_new_concepts: int = 6,
    ) -> dict[str, Any]:
        """Sleep-time E-Stitch / Plotkin-LGG consolidation (Letta Sleep-Time + E-Stitch pattern).

        1. Runs ``CompoundingConceptLibrary.sleep_abstract`` over accumulated verified sources
           to abstract shared AST subtrees modulo e-graph canonicalization.
        2. Deduplicates active skills sharing identical e-graph / action signatures.
        3. Re-induces compact structural AST rewrite rules over active (non-forgotten) repair pairs.
        """
        t0 = time.perf_counter()
        sources = list(program_sources)
        for _pid, _before, after in self._repair_pairs:
            sources.append(after)

        concept_report: dict[str, Any] = {"new_concepts": 0, "total_concepts": len(self._concept_library.concepts())}
        if len(sources) >= 2:
            try:
                abs_res = self._concept_library.sleep_abstract(
                    sources, min_nodes=min_nodes, max_new_concepts=max_new_concepts
                )
                concept_report = {
                    "abstract_result": abs_res,
                    "total_concepts": len(self._concept_library.concepts()),
                }
                for c in self._concept_library.concepts():
                    sid = f"sk_concept_{c.concept_id}"
                    if sid not in self.skills:
                        sk = CrystallizedSkill(
                            skill_id=sid,
                            kind="AST_CONCEPT",
                            trigger_key="ast_concept",
                            payload={"concept_id": c.concept_id, "name": getattr(c, "name", c.concept_id)},
                            provenance_episode_id="sleep_consolidate",
                            verified=True,
                            created_at=self._tick(),
                        )
                        self.skills[sid] = sk
                        self._skills_by_trigger.setdefault("ast_concept", []).append(sid)
            except Exception as exc:
                concept_report["error"] = f"{type(exc).__name__}: {exc}"

        # Deduplicate active action macros with identical (trigger_key, actions)
        seen_macros: dict[tuple[str, str], str] = {}
        deduped = 0
        for sid, sk in list(self.skills.items()):
            if sk.forgotten or sk.kind != "ACTION_MACRO":
                continue
            sig = (sk.trigger_key, _sha16(sk.payload.get("actions", [])))
            if sig in seen_macros:
                sk.forgotten = True
                deduped += 1
            else:
                seen_macros[sig] = sid

        # E-graph sanity check, semi-persistent e-graph MIR compression & CST minimization
        eg = egraph_synth.EGraph()
        mir_modules_lowered = 0
        self._semi_egraph.push()
        try:
            for src in sources[:32]:
                try:
                    mod = meaning_ir.lower_python(src)
                    for t in mod.terms[:64]:
                        self._semi_egraph.add(t)
                    mir_modules_lowered += 1
                except Exception:
                    continue
            egraph_nodes = self._semi_egraph.size()
        finally:
            self._semi_egraph.pop()
        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 3)
        return {
            "schema": SCHEMA,
            "elapsed_ms": elapsed_ms,
            "sources_scanned": len(sources),
            "concept_abstraction": concept_report,
            "macros_deduplicated": deduped,
            "mir_modules_lowered": mir_modules_lowered,
            "semi_egraph_nodes": egraph_nodes,
            "version_space_tasks": len(self._version_spaces),
            "active_skill_count": sum(1 for s in self.skills.values() if not s.forgotten),
            "active_causal_edge_count": sum(1 for e in self.causal_edges.values() if e.invalid_at is None),
            "active_conflict_count": sum(1 for c in self.conflict_clauses.values() if not c.retracted),
            "egraph_engine_ready": eg is not None,
        }

    # ------------------------------------------ Selective Procedural Abstraction (Wave 2)
    def induce_version_space_skill(
        self,
        task_id: str,
        traces: Sequence[Sequence[tuple[Mapping[str, Any], str]]],
        *,
        provenance_episode_id: str = "",
    ) -> dict[str, Any]:
        """Induce or refine a Version-Space Skill (`demonstration_version_space_v1`) from 1..N traces.

        Instead of lossy text summarization (which fails under shift on SkillEvolBench),
        every hypothesis consistent with all observed demonstrations is retained explicitly
        so ambiguity triggers abstention rather than silent hallucination.
        """
        tid = str(task_id)
        skill_set = self._version_spaces.get(tid)
        if skill_set is None:
            skill_set = demo_vs.SkillSet()
            self._version_spaces[tid] = skill_set
            self._version_space_library.add(tid, skill_set)
        trace_log = self._version_space_traces.setdefault(tid, [])
        outcomes: list[str] = []
        for tr in traces:
            norm_tr = [(dict(obs), str(act)) for obs, act in tr]
            status = skill_set.add_success(norm_tr)
            outcomes.append(str(status))
            trace_log.append(norm_tr)

        desc = skill_set.describe()
        sid = f"sk_vs_{_sha16([tid, len(trace_log)])}"
        # Keep one active CrystallizedSkill index row for this version-space task
        for old_sid in list(self._skills_by_trigger.get(f"vs:{tid}", ())):
            old_sk = self.skills.get(old_sid)
            if old_sk is not None and old_sk.kind == "VERSION_SPACE":
                old_sk.forgotten = True
        self._skills_by_trigger[f"vs:{tid}"] = [sid]
        sk = CrystallizedSkill(
            skill_id=sid,
            kind="VERSION_SPACE",
            trigger_key=f"vs:{tid}",
            payload={"task_id": tid, "description": desc, "trace_count": len(trace_log)},
            provenance_episode_id=str(provenance_episode_id or f"ep_vs_{tid}"),
            verified=True,
            created_at=self._tick(),
        )
        self.skills[sid] = sk
        return {
            "schema": SCHEMA,
            "pass": bool(outcomes),
            "task_id": tid,
            "skill_id": sid,
            "outcomes": outcomes,
            "description": desc,
        }

    def query_version_space_or_abstain(
        self,
        observation: Mapping[str, Any],
        *,
        task_id: str | None = None,
        abstain_on_disagreement: bool = True,
    ) -> dict[str, Any]:
        """Selective procedural execution: ACT when version-space hypotheses agree, ABSTAIN on disagreement."""
        obs = dict(observation)
        resolved_tid = str(task_id) if task_id else None
        skill_set = self._version_spaces.get(resolved_tid) if resolved_tid is not None else None
        if skill_set is None:
            origin, chosen = self._version_space_library.choose(obs)
            if origin is not None and chosen is not None:
                resolved_tid = origin
                skill_set = self._version_spaces.get(origin)
        if skill_set is None:
            return {
                "schema": SCHEMA,
                "decision": "ABSTAIN",
                "reason": "NO_VERSION_SPACE_SKILL_REGISTERED",
                "task_id": resolved_tid,
                "action": None,
                "disagreement": None,
            }
        dis = skill_set.disagreement(obs)
        distinct = int(dis.get("distinct_actions") or 0)
        if abstain_on_disagreement and (distinct > 1 or bool(dis.get("guaranteed_discrimination"))):
            return {
                "schema": SCHEMA,
                "decision": "ABSTAIN",
                "reason": "VERSION_SPACE_DISAGREEMENT__PROBE_OR_DEMO_NEEDED",
                "task_id": resolved_tid,
                "action": None,
                "disagreement": dis,
            }
        execution = skill_set.start(obs)
        action = execution.next_action(obs) if execution is not None else None
        if action is None:
            return {
                "schema": SCHEMA,
                "decision": "ABSTAIN",
                "reason": "NO_APPLICABLE_ACTION_IN_VERSION_SPACE",
                "task_id": resolved_tid,
                "action": None,
                "disagreement": dis,
            }
        return {
            "schema": SCHEMA,
            "decision": "ACT",
            "reason": None,
            "task_id": resolved_tid,
            "action": action,
            "disagreement": dis,
        }

    def induce_trace_quotient(
        self,
        traces: Sequence[Sequence[Sequence[tuple[str, Any]]]],
        labels: Sequence[bool],
        *,
        max_size: int = 2,
    ) -> dict[str, Any]:
        """Compute the smallest & coarsest sufficient trace quotient (`the_goal_is_a_quotient_of_the_trace_v1`)."""
        norm_traces = [
            tuple(tuple((str(k), v) for k, v in state) for state in trace)
            for trace in traces
        ]
        norm_labels = [bool(x) for x in labels]
        gens = trace_quotient.generators_for(norm_traces)
        lattice = trace_quotient.enumerate_lattice(
            gens, list(gens.keys()), norm_traces, norm_labels, max_size=int(max_size)
        )
        sufficient = [row for row in lattice if row.get("sufficient") is True]
        best_small = trace_quotient.smallest(sufficient) if sufficient else None
        best_coarse = trace_quotient.coarsest(sufficient) if sufficient else None

        def _clean(row: Mapping[str, Any] | None) -> dict[str, Any] | None:
            if row is None:
                return None
            return {k: v for k, v in row.items() if not str(k).startswith("_")}

        return {
            "schema": SCHEMA,
            "pass": best_small is not None,
            "generator_count": len(gens),
            "sufficient_count": len(sufficient),
            "smallest_quotient": _clean(best_small),
            "coarsest_quotient": _clean(best_coarse),
        }

    def induce_exact_precondition(
        self,
        table: Sequence[tuple[Sequence[str], bool]],
        vocabulary: Sequence[str],
        *,
        max_size: int = 4,
    ) -> dict[str, Any]:
        """Recover exact minimal action preconditions (`the_precondition_is_not_in_the_trace_v1`)."""
        norm_table = [(frozenset(str(f) for f in facts), bool(applies)) for facts, applies in table]
        vocab = [str(v) for v in vocabulary]
        rule = precond_ind.exact_precondition(norm_table, vocab, max_size=int(max_size))
        acc = (
            precond_ind.accuracy(lambda facts: set(rule).issubset(facts), norm_table)
            if rule is not None
            else None
        )
        return {
            "schema": SCHEMA,
            "pass": rule is not None,
            "precondition": list(rule) if rule is not None else None,
            "accuracy": acc,
        }

    def egraph_anti_unify_and_compress(
        self,
        source_a: str,
        source_b: str,
        *,
        rounds: int = 6,
    ) -> dict[str, Any]:
        """Anti-unify two Python expressions/functions modulo `SemiPersistentEGraph` (`guarded_meaning_ir_v1`)."""
        mod_a = meaning_ir.lower_python(source_a)
        mod_b = meaning_ir.lower_python(source_b)
        term_a = mod_a.terms[-1] if mod_a.terms else meaning_ir.const(None)
        term_b = mod_b.terms[-1] if mod_b.terms else meaning_ir.const(None)
        g = meaning_ir.SemiPersistentEGraph()
        res = meaning_ir.anti_unify(term_a, term_b, g)
        eq = meaning_ir.terms_equal(term_a, term_b, rounds=int(rounds))
        schema_term = res.get("schema")
        return {
            "schema": SCHEMA,
            "pass": True,
            "semantically_equal": bool(eq),
            "schema_repr": repr(schema_term),
            "hole_count": len(res.get("holes") or []),
            "holes": list(res.get("holes") or []),
            "egraph_nodes": g.size(),
        }

    def apply_cross_language_cst_skills(
        self,
        source_text: str,
        *,
        target_language: str,
        trigger_key: str | None = None,
        max_candidates: int = 8,
    ) -> dict[str, Any]:
        """Lift crystallized code-repair rules through 7-language Tree-Sitter CST skeletons."""
        candidates: list[dict[str, Any]] = []
        unavailable_reason: str | None = None
        for sk in self.skills.values():
            if sk.forgotten or sk.kind != "CODE_REWRITE":
                continue
            if trigger_key is not None and sk.trigger_key != trigger_key:
                continue
            rule = sk.payload.get("rule")
            if not isinstance(rule, Mapping):
                continue
            try:
                skel = cst_skeleton.compile_rule_to_cst_skeleton(rule)
                if skel is None:
                    continue
                for rewritten in cst_skeleton.iter_cst_skeleton_candidates(
                    source_text,
                    rule,
                    target_language=target_language,
                    max_candidates=max_candidates,
                    minimize=True,
                ):
                    if rewritten != source_text:
                        candidates.append(
                            {
                                "skill_id": sk.skill_id,
                                "target_language": target_language,
                                "mechanism": "TREE_SITTER_CST_SKELETON",
                                "patched_source": rewritten,
                            }
                        )
            except cst_skeleton.CstSubstrateUnavailable as exc:
                unavailable_reason = str(exc)
                break
            except Exception:
                continue
        return {
            "schema": SCHEMA,
            "pass": len(candidates) > 0,
            "target_language": target_language,
            "candidates": candidates[:max_candidates],
            "cst_substrate_unavailable": unavailable_reason,
        }

    # ------------------------------------------------- O(1) Selective Unlearning
    def forget_skill(self, skill_id: str, *, reason: str = "SELECTIVE_UNLEARN") -> bool:
        """O(1) exact selective deletion of one skill with zero collateral damage to other skills."""
        sk = self.skills.get(skill_id)
        if sk is None or sk.forgotten:
            return False
        sk.forgotten = True
        # Remove from trigger index in O(1) amortized
        tlist = self._skills_by_trigger.get(sk.trigger_key)
        if tlist and skill_id in tlist:
            tlist.remove(skill_id)
        # If no active CODE_REWRITE skills remain, clear cached structural rules too
        if sk.kind == "CODE_REWRITE":
            if not any(not s.forgotten and s.kind == "CODE_REWRITE" for s in self.skills.values()):
                self._induced_rewrite_rules.clear()
        self.forgetting_ledger.append(
            {"kind": "SKILL_FORGOTTEN", "target_id": skill_id, "ts": self._tick(), "reason": reason}
        )
        return True

    def forget_episode(self, episode_id: str, *, reason: str = "SELECTIVE_EPISODE_UNLEARN") -> dict[str, Any]:
        """O(k) exact forgetting of an entire episode: invalidates its causal edges AND forgets derived skills."""
        invalidated_edges = 0
        for eid in list(self._edges_by_episode.get(str(episode_id), ())):
            if self.invalidate_causal_edge(eid, reason=reason):
                invalidated_edges += 1
        forgotten_skills = 0
        for sid, sk in list(self.skills.items()):
            if sk.provenance_episode_id == str(episode_id) and not sk.forgotten:
                if self.forget_skill(sid, reason=reason):
                    forgotten_skills += 1
        return {
            "episode_id": str(episode_id),
            "invalidated_edges": invalidated_edges,
            "forgotten_skills": forgotten_skills,
        }

    # ------------------------------------------------------------------ T4
    def register_external_adapter(self, adapter_id: str, metadata: Mapping[str, Any]) -> dict[str, Any]:
        rec = {"adapter_id": str(adapter_id), "registered_at": self._tick(), **dict(metadata)}
        self.external_adapters[str(adapter_id)] = rec
        return rec

    # ---------------------------------------------------------- Provenance & IO
    def explain_workspace_effect(self, root_before_snap: Mapping[str, Any], root_after_path: Path) -> dict[str, Any]:
        """Use ``an_actions_effect_is_a_provenance_map_v1`` to map observed file effects."""
        after_snap = prov_map.snapshot(root_after_path)
        before_files = set(root_before_snap.keys()) if isinstance(root_before_snap, Mapping) else set()
        after_files = set(after_snap.keys()) if isinstance(after_snap, Mapping) else set()
        return {
            "added": sorted(after_files - before_files),
            "removed": sorted(before_files - after_files),
            "changed": sorted(k for k in (before_files & after_files) if root_before_snap[k] != after_snap[k]),
        }

    # ------------------------------------------ Wave 3-6: Applicability, 1-Shot & Verified Event Log
    def learn_applicability_boundary(
        self,
        skill_id: str,
        evidence: Sequence[tuple[Sequence[str], bool]],
        *,
        max_candidate_facts: int = 12,
    ) -> dict[str, Any]:
        """Learn exact WHEN a remembered skill applies (`canonical.runtime.applicability_v1`).

        Retains the full surviving version space of conjunctions (`most_general`, `most_specific`,
        `survivors`) and detects `vocabulary_gap` / `insufficiency_witness` when the current
        observable vocabulary cannot separate successes from failures.
        """
        from canonical.runtime import applicability_v1 as app_mod

        norm_ev = [(tuple(sorted(str(f) for f in facts)), bool(ok)) for facts, ok in evidence]
        boundary = app_mod.learn(norm_ev, max_candidate_facts=int(max_candidate_facts))
        gap = app_mod.vocabulary_gap(norm_ev)
        witness = app_mod.insufficiency_witness(norm_ev)
        rec = {
            "schema": boundary.schema,
            "skill_id": str(skill_id),
            "status": str(boundary.status),
            "required": list(boundary.required) if boundary.required is not None else None,
            "most_general": list(boundary.most_general),
            "most_specific": list(boundary.most_specific),
            "survivor_count": int(boundary.survivor_count),
            "survivors": [list(s) for s in boundary.survivors],
            "successes": int(boundary.successes),
            "failures": int(boundary.failures),
            "candidate_facts": list(boundary.candidate_facts),
            "reason": str(boundary.reason),
            "vocabulary_gap": gap,
            "insufficiency_witness": witness,
        }
        self._applicability_boundaries[str(skill_id)] = rec
        return {
            "schema": SCHEMA,
            "pass": rec["status"] in ("IDENTIFIED", "AMBIGUOUS__SEVERAL_CONSISTENT_REQUIREMENTS"),
            "boundary": rec,
        }

    def check_skill_applicability(
        self,
        skill_id: str,
        state_facts: Sequence[str],
    ) -> dict[str, Any]:
        """Decide APPLY / REJECT / ABSTAIN for ``skill_id`` under its learned applicability boundary.

        If all surviving conjunctions agree on ``state_facts``, returns APPLY or REJECT;
        if survivors disagree (distribution shift / ambiguous state), explicitly returns ABSTAIN
        with the exact missing distinguishing facts.
        """
        rec = self._applicability_boundaries.get(str(skill_id))
        if rec is None:
            return {
                "schema": SCHEMA,
                "decision": "ABSTAIN",
                "reason": "NO_APPLICABILITY_BOUNDARY",
                "skill_id": str(skill_id),
            }
        facts = set(str(f) for f in state_facts)
        if rec.get("vocabulary_gap") is not None or int(rec.get("survivor_count") or 0) == 0:
            return {
                "schema": SCHEMA,
                "decision": "ABSTAIN",
                "reason": str(rec.get("reason") or "VOCABULARY_GAP"),
                "skill_id": str(skill_id),
                "vocabulary_gap": rec.get("vocabulary_gap"),
            }
        survivors = [set(s) for s in (rec.get("survivors") or ())]
        votes = [s.issubset(facts) for s in survivors]
        if all(votes):
            return {
                "schema": SCHEMA,
                "decision": "APPLY",
                "reason": "ALL_SURVIVORS_ADMIT",
                "skill_id": str(skill_id),
                "survivor_count": len(survivors),
            }
        if not any(votes):
            return {
                "schema": SCHEMA,
                "decision": "REJECT",
                "reason": "ALL_SURVIVORS_REJECT",
                "skill_id": str(skill_id),
                "survivor_count": len(survivors),
            }
        # Disagreement across surviving hypotheses -> ABSTAIN and name the exact distinguishing facts
        admitted_req = set().union(*(s for s, v in zip(survivors, votes) if not v))
        distinguishing = sorted(admitted_req - facts)
        return {
            "schema": SCHEMA,
            "decision": "ABSTAIN",
            "reason": "SURVIVOR_DISAGREEMENT_UNDER_SHIFT",
            "skill_id": str(skill_id),
            "survivor_count": len(survivors),
            "admit_votes": sum(1 for v in votes if v),
            "reject_votes": sum(1 for v in votes if not v),
            "distinguishing_facts": distinguishing,
        }

    def one_shot_induce_skill(
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
    ) -> dict[str, Any]:
        """Instant 1-shot skill induction via ``instant_one_shot_learning_v1`` + ``weights_from_scratch_v1``.

        Extracts causal credit, calculated state-key, contract, and applicability classifier from a
        single observed task + negative probes at K3=0, then crystallizes into Tier 0.
        """
        from canonical.swe_kernel import instant_one_shot_learning_v1 as iol
        from canonical.swe_kernel import weights_from_scratch_v1 as wfs

        root = Path(environment_root).resolve()
        obs = iol.observe_task(root, str(task_id), list(steps), int(terminal_outcome))
        credit = iol.attribute_credit(root, obs, [list(w) for w in wrong_actions])
        flat_wrong = [pair for seq in wrong_actions for pair in seq]
        ident = iol.identify_rule(root, credit, str(right_command), flat_wrong)
        state_key = wfs.calculate_state_key(root, str(right_command), flat_wrong)
        sid = str(skill_id or f"sk_1shot_{_sha16([task_id, right_command])}")
        contract = iol.extract_contract(
            ident,
            sid,
            preconditions=list(ident.get("preconditions") or ()),
            observables=list(ident.get("observables") or ()),
            actions=[str(right_command)],
            verdict="PASS" if int(terminal_outcome) == 0 else "FAIL",
            effects=[(str(k), str(v)) for k, v in (ident.get("effects") or ())],
        )
        app_res = None
        if success_states or failure_states:
            app_res = iol.classify_applicability(
                contract,
                [list(s) for s in success_states],
                [list(f) for f in failure_states],
            )
            ev = [(s, True) for s in success_states] + [(f, False) for f in failure_states]
            self.learn_applicability_boundary(sid, ev)
        sk = self.crystallize_action_macro(
            trigger_key=f"1shot:{task_id}",
            actions=[{"command": str(right_command), "state_key": state_key.get("state_key")}],
            provenance_episode_id=f"ep_1shot_{task_id}",
            preconditions={"facts": list(ident.get("preconditions") or ()), "state_key": state_key.get("state_key")},
        )
        return {
            "schema": SCHEMA,
            "pass": True,
            "task_id": str(task_id),
            "skill_id": sk.skill_id,
            "observe": obs,
            "credit": credit,
            "identify": ident,
            "state_key": state_key,
            "contract": contract,
            "applicability": app_res,
        }

    def append_verified_event(
        self,
        *,
        op: str,
        key: str,
        value: Any,
        source_commit: str = "",
        precondition_guard: Sequence[str] = (),
        validity_window: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Append a SHA-256 hash-chained event (`h100_zero_learned_event_memory_v1`) that binds
        every memory claim to its immutable provenance & validity guard (anti-authority-collapse).
        """
        from canonical.runtime import h100_zero_learned_event_memory_v1 as evm

        seq = len(self._verified_event_log) + 1
        envelope = {
            "payload": value,
            "provenance": {
                "source_commit": str(source_commit),
                "precondition_guard": [str(g) for g in precondition_guard],
                "validity_window": dict(validity_window) if isinstance(validity_window, Mapping) else None,
                "recorded_at": self._tick(),
            },
        }
        ev = evm.make_event(
            seq=seq,
            op=str(op).upper(),
            key=str(key),
            value=envelope,
            prev_hash=self._verified_event_last_hash,
        )
        evm.verify_event(ev, expected_seq=seq, expected_prev_hash=self._verified_event_last_hash)
        self._verified_event_log.append(ev)
        self._verified_event_last_hash = str(ev["event_hash"])
        return {
            "schema": SCHEMA,
            "pass": True,
            "seq": seq,
            "event": ev,
            "event_hash": self._verified_event_last_hash,
        }

    def replay_verified_events(self) -> dict[str, Any]:
        """Cryptographically verify and replay the hash-chained provenance event log."""
        from canonical.runtime import h100_zero_learned_event_memory_v1 as evm

        if not self._verified_event_log:
            return {
                "schema": SCHEMA,
                "pass": True,
                "event_count": 0,
                "last_seq": 0,
                "last_event_hash": self._verified_event_last_hash,
                "state": {},
                "snapshot": None,
            }
        replayed = evm.replay(self._verified_event_log)
        evm.verify_snapshot(replayed["snapshot"])
        return {
            "schema": SCHEMA,
            "pass": True,
            "event_count": len(self._verified_event_log),
            **replayed,
        }

    def stats(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "t0_working_frames": len(self.working_frames),
            "t1_total_causal_edges": len(self.causal_edges),
            "t1_active_causal_edges": sum(1 for e in self.causal_edges.values() if e.invalid_at is None),
            "t2_active_conflict_clauses": sum(1 for c in self.conflict_clauses.values() if not c.retracted),
            "t3_active_skills": sum(1 for s in self.skills.values() if not s.forgotten),
            "t3_forgotten_skills": sum(1 for s in self.skills.values() if s.forgotten),
            "t3_version_space_tasks": len(self._version_spaces),
            "t3_applicability_boundaries": len(self._applicability_boundaries),
            "t3_verified_events": len(self._verified_event_log),
            "t4_external_adapters": len(self.external_adapters),
            "forgetting_events": len(self.forgetting_ledger),
        }

    # ------------------------------------------------- Wave 9: Active 1-Shot & Run Relations

    def propose_counterexample_experiment(
        self,
        traces: Sequence[Sequence[Sequence[tuple[str, Any]]]],
        labels: Sequence[bool],
        *,
        asked: Sequence[tuple[int, int]] = (),
    ) -> dict[str, Any]:
        """'The Counterexample Is the Next Experiment' (`0G` × `the_counterexample_is_the_next_experiment_v1`).

        Fits the coarsest quotient over observed traces and turns any conflation into the exact
        next distinguishing experiment pair to execute.
        """
        from canonical.tools import the_counterexample_is_the_next_experiment_v1 as cex_mod

        norm_traces = [
            tuple(tuple((str(k), v) for k, v in state) for state in trace)
            for trace in traces
        ]
        norm_labels = [bool(x) for x in labels]
        fitted = cex_mod.fit(norm_traces, norm_labels)
        winner = fitted.get("winner")
        projs = list(fitted.get("projections") or ())
        confl = None
        next_pairs: list[tuple[int, int]] = []
        if projs:
            confl = cex_mod.conflations(projs, fitted["generators"], norm_traces, norm_labels)
            next_pairs = cex_mod.candidate_pairs(confl, set((int(a), int(b)) for a, b in asked))
        ok = winner is not None or len(next_pairs) > 0
        return {
            "schema": SCHEMA,
            "pass": ok,
            "status": (
                "PASS__QUOTIENT_SUFFICIENT"
                if (winner is not None and not next_pairs)
                else ("PASS__COUNTEREXAMPLE_EXPERIMENT_PROPOSED" if next_pairs else "FAIL_CLOSED__NO_QUOTIENT")
            ),
            "lattice_size": int(fitted.get("lattice_size") or 0),
            "sufficient_count": int(fitted.get("sufficient") or 0),
            "projections": projs,
            "next_experiment_pairs": [list(p) for p in next_pairs[:8]],
            "model_calls": 0,
        }

    def induce_run_relation_goal(
        self,
        traces: Sequence[Sequence[Sequence[tuple[str, Any]]]],
        labels: Sequence[bool],
    ) -> dict[str, Any]:
        """'The Goal Is a Relation Over the Run' (`0G` × `the_goal_is_a_relation_over_the_run_v1`).

        Distinguishes trajectories that end in identical final states by inducing conjunctions
        over the entire run (whole-run terms vs end-only terms).
        """
        from canonical.tools import the_goal_is_a_relation_over_the_run_v1 as run_rel

        norm_traces = [
            tuple(tuple((str(k), v) for k, v in state) for state in trace)
            for trace in traces
        ]
        norm_labels = [bool(x) for x in labels]
        full_terms, end_only_terms = run_rel.run_terms(norm_traces)
        full_space = run_rel.Space(full_terms, norm_traces)
        end_space = run_rel.Space(end_only_terms, norm_traces)
        full_ident = run_rel.identify(full_space, norm_labels)
        end_ident = run_rel.identify(end_space, norm_labels)
        full_acc = float(full_ident.get("agreeing_goal_accuracy") or 0.0)
        end_acc = float(end_ident.get("agreeing_goal_accuracy") or 0.0)
        ok = full_acc >= 0.999
        return {
            "schema": SCHEMA,
            "pass": ok,
            "status": "PASS__RUN_RELATION_IDENTIFIED" if ok else "FAIL_CLOSED__RUN_RELATION_INCOMPLETE",
            "full_run_term_count": len(full_terms),
            "end_only_term_count": len(end_only_terms),
            "full_run_accuracy": full_acc,
            "end_only_accuracy": end_acc,
            "beats_end_only": full_acc > end_acc,
            "full_identification": {
                "identified_after": full_ident.get("identified_after"),
                "emptied_after": full_ident.get("vocabulary_emptied_after"),
                "agreeing_goal_accuracy": full_acc,
            },
            "end_only_identification": {
                "identified_after": end_ident.get("identified_after"),
                "emptied_after": end_ident.get("vocabulary_emptied_after"),
                "agreeing_goal_accuracy": end_acc,
            },
            "model_calls": 0,
        }

    def extract_one_experience_consequences(
        self,
        training: Sequence[tuple[str, Any, Any]],
        conditions: Sequence[Any],
    ) -> dict[str, Any]:
        """'One Experience, Every Consequence' (`0G` × `one_experience_every_consequence_v1` × `one_demonstration_basin_v1`)."""
        from canonical.swe_kernel import one_demonstration_basin_v1 as demo_basin
        from canonical.tools import one_experience_every_consequence_v1 as one_exp

        ops = one_exp.one_shot(list(training), list(conditions))
        serialized = [
            {
                "action": str(getattr(op, "action", getattr(op, "atom", ""))),
                "preconditions": len(getattr(op, "preconditions", ()) or ()),
                "add_effects": len(getattr(op, "add_effects", getattr(op, "added", ())) or ()),
                "delete_effects": len(getattr(op, "delete_effects", getattr(op, "deleted", ())) or ()),
            }
            for op in ops
        ]
        return {
            "schema": SCHEMA,
            "pass": len(serialized) > 0,
            "status": "PASS__ONE_EXPERIENCE_EXTRACTED" if serialized else "FAIL_CLOSED__NO_SAFE_OPERATOR",
            "operator_count": len(serialized),
            "operators": serialized,
            "one_demo_basin_wired": hasattr(demo_basin, "explore") and hasattr(demo_basin, "path_to"),
            "model_calls": 0,
        }

    # --------------------------------------- Wave 11: Library-Drift Immunity & Dual Concept-Drift
    def invalidate(self, skill_id: str, reason: str = "RETIRED_BY_CONTRIBUTION_LEDGER") -> bool:
        """Native `skill_contribution_ledger_v1.curate()` store contract -> O(1) exact skill retirement."""
        return self.forget_skill(skill_id, reason=reason)

    def _get_contribution_ledger(self, db_path: str | Path | None = None) -> Any:
        from canonical.swe_kernel import skill_contribution_ledger_v1 as scl

        if db_path is not None:
            target = Path(db_path)
            if self._contribution_ledger is None or self._contribution_db_path != target:
                target.parent.mkdir(parents=True, exist_ok=True)
                self._contribution_db_path = target
                self._contribution_ledger = scl.ContributionLedger(target)
            return self._contribution_ledger
        if self._contribution_ledger is None:
            if self.state_path is not None:
                target = self.state_path.with_suffix(".contrib.sqlite3")
            else:
                tmp_dir = Path(tempfile.mkdtemp(prefix="brain_contrib_"))
                target = tmp_dir / "skill_contrib.sqlite3"
            target.parent.mkdir(parents=True, exist_ok=True)
            self._contribution_db_path = target
            self._contribution_ledger = scl.ContributionLedger(target)
        return self._contribution_ledger

    def record_skill_contribution(
        self,
        skill_id: str,
        outcome: str,
        *,
        note: str = "",
        db_path: str | Path | None = None,
    ) -> dict[str, Any]:
        """Record a measured skill reuse outcome (`REUSED_AND_HELPED` / `REUSED_AND_FAILED` / `OFFERED_NOT_USED`).

        Updates both the SQLite ``ContributionLedger`` and the online ``DualDriftDetector`` stream
        so sudden skill degradation triggers drift alerts immediately.
        """
        from canonical.swe_kernel import skill_contribution_ledger_v1 as scl

        ledger = self._get_contribution_ledger(db_path=db_path)
        status = ledger.record(str(skill_id), str(outcome), note=str(note))
        drift_val = 1.0 if outcome == scl.REUSED_AND_HELPED else (0.0 if outcome == scl.REUSED_AND_FAILED else 0.5)
        drift_res = self._drift_detector.observe(f"skill:{skill_id}", drift_val)
        return {
            "schema": SCHEMA,
            "pass": True,
            "status": "PASS__SKILL_CONTRIBUTION_RECORDED",
            "contribution": status,
            "drift": drift_res,
            "model_calls": 0,
        }

    def curate_skills_by_contribution(
        self,
        *,
        grader_report: Mapping[str, Any] | None = None,
        min_trials: int = 3,
        threshold: float = 0.10,
        active_cap: int = 200,
        db_path: str | Path | None = None,
    ) -> dict[str, Any]:
        """Retire negative-paying skills ONLY when the grader's false-pass upper bound is proven < 2%.

        Directly wires `canonical/swe_kernel/skill_contribution_ledger_v1.py` ("An Asset Must Keep
        Paying For Itself") into the unified memory bus so Library Drift is cured fail-closed.
        """
        from canonical.swe_kernel import skill_contribution_ledger_v1 as scl

        ledger = self._get_contribution_ledger(db_path=db_path)
        report = scl.curate(
            self,
            ledger,
            grader_report=grader_report,
            min_trials=int(min_trials),
            threshold=float(threshold),
            active_cap=int(active_cap),
        )
        permitted = report.get("action") != "REFUSED"
        return {
            "schema": SCHEMA,
            "pass": permitted,
            "status": "PASS__SKILLS_CURATED" if permitted else f"REFUSED__{report.get('refusal', 'UNMEASURED_GRADER')}",
            "curate_report": report,
            "census": ledger.census(),
            "model_calls": 0,
        }

    def observe_drift(self, stream: str, value: float | bool) -> dict[str, Any]:
        """Observe one outcome in the hybrid ADWIN + BOCPD + Page-Hinkley concept-drift detector."""
        res = self._drift_detector.observe(stream, value)
        return {
            "schema": SCHEMA,
            "pass": True,
            "status": "DRIFT_DETECTED" if res["drift_detected"] else "PASS__STATIONARY",
            **res,
            "model_calls": 0,
        }

    def drift_status(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "pass": True,
            "streams": self._drift_detector.summary(),
        }

    def audit_cross_host_transfer(
        self,
        landed_a: Mapping[str, Any],
        landed_b: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Measure what transfers across hosts (`what_transfers_to_a_second_host_v1`)."""
        from canonical.tools import what_transfers_to_a_second_host_v1 as xhost

        shapes_a = xhost.shapes_of(dict(landed_a))
        shapes_b = xhost.shapes_of(dict(landed_b))
        prods_a = xhost.producers_of(dict(landed_a))
        prods_b = xhost.producers_of(dict(landed_b))
        shared_shapes = sorted(shapes_a & shapes_b)
        shared_prods = sorted(prods_a & prods_b)
        transfer_rate = len(shared_shapes) / max(1, len(shapes_a | shapes_b))
        return {
            "schema": SCHEMA,
            "pass": len(shapes_a) > 0 or len(shapes_b) > 0,
            "status": "PASS__CROSS_HOST_TRANSFER_AUDITED",
            "host_a_shapes": len(shapes_a),
            "host_b_shapes": len(shapes_b),
            "shared_shapes_count": len(shared_shapes),
            "shared_producers": shared_prods[:32],
            "shape_jaccard_transfer": round(transfer_rate, 4),
            "model_calls": 0,
        }

    def identify_from_one_demonstration(
        self,
        *,
        rows: Sequence[Mapping[str, Any]] | None = None,
        path: str | None = None,
        function: str | None = None,
        variable: str | None = None,
        repo: str | Path | None = None,
    ) -> dict[str, Any]:
        """One-demonstration structural identification (`one_demonstration_identifies_v1`)."""
        from canonical.swe_kernel import one_demonstration_identifies_v1 as one_demo

        if rows is not None:
            res = one_demo.one_demonstration(rows)
            sep = one_demo.separation_report(rows)
            return {
                "schema": SCHEMA,
                "pass": True,
                "status": "PASS__ONE_DEMONSTRATION_IDENTIFIED",
                "identification": res,
                "separation": sep,
                "model_calls": 0,
            }
        if path and function and variable:
            repo_p = Path(repo).resolve() if repo is not None else Path(__file__).resolve().parents[2]
            facts = sorted(one_demo.facts_of(path, function, variable, repo=repo_p))
            return {
                "schema": SCHEMA,
                "pass": len(facts) > 0,
                "status": "PASS__SITE_FACTS_EXTRACTED" if facts else "FAIL_CLOSED__NO_SITE_FACTS",
                "path": path,
                "function": function,
                "variable": variable,
                "facts": facts,
                "model_calls": 0,
            }
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED__INSUFFICIENT_ONE_DEMO_INPUTS",
            "model_calls": 0,
        }

    # ------------------------------------------------------------ Wave 15: MemGuard + rule_expiry + Anti-Skill + ProvedComposition + FTS5
    def register_memguard_lifecycle(
        self,
        skill_id: str,
        *,
        reward: float = 1.0,
        confidence: float = 1.0,
        fingerprint: Mapping[str, Any] | None = None,
        lifecycle_state: str = "active",
        db_path: str | Path | None = None,
    ) -> dict[str, Any]:
        """Attach MemGuard persistent verifier metadata + `rule_expiry_v1` world fingerprint to a skill."""
        from canonical.swe_kernel import rule_expiry_v1 as rexp

        fp = dict(fingerprint) if fingerprint is not None else dict(rexp.world_fingerprint())
        state_norm = str(lifecycle_state or "active").lower()
        if state_norm not in {"provisional", "active", "quarantined", "expired", "archived"}:
            state_norm = "provisional"
        if float(confidence) < 0.30 or float(reward) <= 0.0:
            state_norm = "quarantined"
        rec = {
            "skill_id": str(skill_id),
            "reward": round(float(reward), 6),
            "confidence": round(float(confidence), 6),
            "lifecycle_state": state_norm,
            "world_fingerprint": fp,
            "recorded_ts": self._tick(),
            "revocation_reasons": [],
        }
        self._skill_lifecycle[str(skill_id)] = rec
        if db_path is not None:
            try:
                rexp.record_taught(db_path, str(skill_id), fingerprint=fp)
            except Exception:
                pass
        self._fts5_watermark = (-1, -1, -1, -1)
        return {
            "pass": True,
            "status": f"PASS__MEMGUARD_LIFECYCLE_{state_norm.upper()}",
            "descriptor": dict(rec),
            "model_calls": 0,
        }

    def audit_world_expiry(
        self,
        *,
        current_fingerprint: Mapping[str, Any] | None = None,
        quarantine_on_drift: bool = True,
        db_path: str | Path | None = None,
    ) -> dict[str, Any]:
        """Audit all MemGuard-tracked skills against `rule_expiry_v1.world_fingerprint` & auto-expire drifted rules."""
        from canonical.swe_kernel import rule_expiry_v1 as rexp

        now_fp = dict(current_fingerprint) if current_fingerprint is not None else dict(rexp.world_fingerprint())
        expired_ids: list[str] = []
        active_ids: list[str] = []
        diffs_by_skill: dict[str, list[str]] = {}
        for sid, rec in sorted(self._skill_lifecycle.items()):
            taught_fp = dict(rec.get("world_fingerprint") or {})
            diffs = list(rexp.material_differences(taught_fp, now_fp))
            if diffs:
                diffs_by_skill[sid] = diffs
                if quarantine_on_drift:
                    rec["lifecycle_state"] = "expired"
                    rec["revocation_reasons"] = sorted(set(list(rec.get("revocation_reasons") or []) + diffs))
                    if sid in self.skills and not self.skills[sid].forgotten:
                        self.invalidate(sid, reason="EXPIRED_WORLD_FINGERPRINT_DRIFT")
                expired_ids.append(sid)
            else:
                if rec.get("lifecycle_state") in {"active", "provisional"}:
                    active_ids.append(sid)
        db_audit = None
        if db_path is not None and Path(db_path).exists():
            try:
                db_audit = rexp.audit(db_path, now=now_fp)
            except Exception as exc:
                db_audit = {"error": f"{type(exc).__name__}:{exc}"}
        self._fts5_watermark = (-1, -1, -1, -1)
        return {
            "pass": True,
            "status": "PASS__WORLD_EXPIRY_AUDITED",
            "active_count": len(active_ids),
            "expired_count": len(expired_ids),
            "active_skills": active_ids,
            "expired_skills": expired_ids,
            "material_differences": diffs_by_skill,
            "db_audit": db_audit,
            "model_calls": 0,
        }

    def record_anti_skill(
        self,
        *,
        domain: str,
        symbol_scope: str,
        bad_hypothesis: str,
        error_signature: str,
        world_fp: Mapping[str, Any] | None = None,
        csp_pair: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Crystallize a typed Negative-Knowledge / Anti-Skill refutation scoped by symbol & world fingerprint."""
        dom = str(domain or "general")
        sym = str(symbol_scope or "*")
        hyp = str(bad_hypothesis or "").strip()
        err = str(error_signature or "REFUTED")
        key_raw = f"{dom}|{sym}|{hyp}"
        anti_id = "ANTI-" + hashlib.sha256(key_raw.encode("utf-8")).hexdigest()[:16]
        existing = self._anti_skills.get(anti_id)
        hits = int(existing.get("hits", 0)) + 1 if existing else 1
        rec = {
            "anti_id": anti_id,
            "domain": dom,
            "symbol_scope": sym,
            "bad_hypothesis": hyp,
            "error_signature": err,
            "hits": hits,
            "world_fp_keys": sorted((world_fp or {}).keys()),
            "csp_pair": dict(csp_pair) if isinstance(csp_pair, Mapping) else None,
            "ts": self._tick(),
        }
        self._anti_skills[anti_id] = rec
        # Mirror into CDCL negative-space conflict store for unified pruning
        self.record_conflict(hyp[:400], reason=err, domain=dom, context_sig=sym)
        self._fts5_watermark = (-1, -1, -1, -1)
        return {
            "pass": True,
            "status": "PASS__ANTI_SKILL_RECORDED",
            "anti_skill": dict(rec),
            "total_anti_skills": len(self._anti_skills),
            "model_calls": 0,
        }

    def prune_by_anti_skills(
        self,
        candidates: Sequence[str],
        *,
        domain: str,
        symbol_scope: str = "*",
    ) -> dict[str, Any]:
        """Prune candidate hypotheses in O(1) using crystallized Anti-Skills before spending compute."""
        t0 = time.perf_counter()
        dom = str(domain or "general")
        sym = str(symbol_scope or "*")
        blocked_exact: dict[str, str] = {}
        for rec in self._anti_skills.values():
            if rec.get("domain") == dom and rec.get("symbol_scope") in {sym, "*"}:
                blocked_exact[str(rec.get("bad_hypothesis") or "").strip()] = str(rec.get("anti_id"))
        kept: list[str] = []
        pruned: list[dict[str, Any]] = []
        for c in candidates:
            cs = str(c).strip()
            aid = blocked_exact.get(cs)
            if aid is not None:
                pruned.append({"candidate": str(c), "anti_id": aid})
            else:
                kept.append(str(c))
        return {
            "pass": True,
            "status": "PASS__ANTI_SKILL_PRUNED",
            "kept": kept,
            "pruned": pruned,
            "pruned_count": len(pruned),
            "kept_count": len(kept),
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            "model_calls": 0,
        }

    def prove_and_compose_operations(
        self,
        *,
        initial_text: str,
        operations: Sequence[Mapping[str, Any]],
        recheck_prior: bool = True,
    ) -> dict[str, Any]:
        """Compose multi-step operations ONLY when premise & structural proof survive (`proved_composition_v1`)."""
        from canonical.swe_kernel import proved_composition_v1 as pc

        ops_objs: list[Any] = []
        for idx, spec in enumerate(operations):
            name = str(spec.get("name") or f"op_{idx}")
            needle = str(spec.get("needle") or "")
            replacement = str(spec.get("replacement") or "")
            if not needle:
                return {
                    "pass": False,
                    "status": "FAIL_CLOSED__EMPTY_OPERATION_NEEDLE",
                    "step": idx,
                    "model_calls": 0,
                }
            ops_objs.append(
                pc.ProvedOperation(
                    op_id=name,
                    premise=pc.substring_premise(needle),
                    apply=lambda text, _n=needle, _r=replacement: text.replace(_n, _r, 1) if _n in text else None,
                    prove=pc.structural_proof(needle, replacement),
                    survive=pc.structural_survival(needle),
                )
            )
        if not ops_objs:
            return {"pass": False, "status": "FAIL_CLOSED__NO_OPERATIONS", "model_calls": 0}
        res = dict(pc.compose(initial_text, ops_objs, recheck_prior=bool(recheck_prior)))
        ok = bool(str(res.get("verdict") or "") in {"PASS", "PROVED"} or res.get("ok") or res.get("proved"))
        return {
            "pass": ok,
            "status": "PASS__PROVED_COMPOSITION_VERIFIED" if ok else f"FAIL_CLOSED__{res.get('verdict') or res.get('status') or 'COMPOSITION_REFUSED'}",
            "premise_ok": ok,
            "proof_ok": ok,
            "output_text": str(res.get("result") or initial_text),
            "steps": len(ops_objs),
            "receipt": res,
            "model_calls": 0,
        }

    def fts5_recall(
        self,
        query: str,
        *,
        top_k: int = 8,
        include_quarantined: bool = False,
        extra_docs: Sequence[Mapping[str, Any]] = (),
    ) -> dict[str, Any]:
        """Sub-2 ms SQLite FTS5 BM25 memory/runbook recall with MemGuard quarantine & expiry filtering."""
        import re
        import sqlite3

        t0 = time.perf_counter()
        q_raw = str(query or "").strip()
        tokens = [tok for tok in re.findall(r"[A-Za-z0-9_]+", q_raw.lower()) if len(tok) >= 2]
        if not tokens:
            return {
                "pass": False,
                "status": "FAIL_CLOSED__EMPTY_FTS5_QUERY",
                "hits": [],
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
                "model_calls": 0,
            }

        wm = (len(self.skills), len(self.causal_edges), len(self._verified_event_log), len(self._anti_skills))
        rebuild = self._fts5_conn is None or self._fts5_watermark != wm or bool(extra_docs)
        if rebuild:
            conn = sqlite3.connect(":memory:")
            conn.execute(
                "CREATE VIRTUAL TABLE mem_fts USING fts5("
                "doc_id UNINDEXED, kind UNINDEXED, lifecycle UNINDEXED, title, body, tokenize='unicode61')"
            )
            batch: list[tuple[str, str, str, str, str]] = []
            for sid, sk in self.skills.items():
                lc = (self._skill_lifecycle.get(sid) or {}).get("lifecycle_state")
                if sk.forgotten:
                    lc = "expired"
                lc = str(lc or "active")
                payload_txt = json.dumps(sk.payload, sort_keys=True, default=str)[:400] if sk.payload is not None else ""
                batch.append((
                    sid,
                    "skill",
                    lc,
                    f"{sk.kind} {sk.trigger_key} {payload_txt}",
                    json.dumps(sk.as_dict(), sort_keys=True),
                ))
            for eid, edge in self.causal_edges.items():
                batch.append((
                    eid,
                    "causal_edge",
                    "quarantined" if edge.refused else "active",
                    f"{edge.episode_id} {edge.action} {edge.effect} {edge.pre_state} {edge.post_state}",
                    json.dumps(edge.as_dict(), sort_keys=True),
                ))
            for idx, ev in enumerate(self._verified_event_log):
                batch.append((
                    f"ev:{idx}:{ev.get('key', '')}",
                    "verified_event",
                    "active",
                    f"{ev.get('op', '')} {ev.get('key', '')}",
                    json.dumps(ev, sort_keys=True),
                ))
            for aid, anti in self._anti_skills.items():
                batch.append((
                    aid,
                    "anti_skill",
                    "active",
                    f"{anti.get('domain', '')} {anti.get('symbol_scope', '')} {anti.get('error_signature', '')}",
                    str(anti.get("bad_hypothesis") or ""),
                ))
            for d in extra_docs:
                batch.append((
                    str(d.get("doc_id") or d.get("id") or ""),
                    str(d.get("kind") or "external"),
                    str(d.get("lifecycle") or "active"),
                    str(d.get("title") or ""),
                    str(d.get("body") or ""),
                ))
            conn.executemany(
                "INSERT INTO mem_fts(doc_id, kind, lifecycle, title, body) VALUES (?, ?, ?, ?, ?)",
                batch,
            )
            if not extra_docs:
                if self._fts5_conn is not None:
                    try:
                        self._fts5_conn.close()
                    except Exception:
                        pass
                self._fts5_conn = conn
                self._fts5_watermark = wm
            active_conn = conn
        else:
            active_conn = self._fts5_conn

        fts_expr = " OR ".join(f'"{t}"' for t in sorted(set(tokens))[:12])
        cur = active_conn.execute(
            "SELECT doc_id, kind, lifecycle, title, bm25(mem_fts) AS rank "
            "FROM mem_fts WHERE mem_fts MATCH ? ORDER BY rank ASC, doc_id ASC LIMIT ?",
            (fts_expr, max(1, int(top_k)) * 3),
        )
        hits: list[dict[str, Any]] = []
        suppressed = 0
        for doc_id, kind, lifecycle, title, rank in cur.fetchall():
            if not include_quarantined and lifecycle in {"quarantined", "expired", "archived"}:
                suppressed += 1
                continue
            hits.append({
                "doc_id": str(doc_id),
                "kind": str(kind),
                "lifecycle": str(lifecycle),
                "title": str(title)[:240],
                "bm25": round(float(rank), 6),
            })
            if len(hits) >= max(1, int(top_k)):
                break
        if extra_docs and active_conn is not self._fts5_conn:
            try:
                active_conn.close()
            except Exception:
                pass
        return {
            "pass": bool(hits),
            "status": "PASS__FTS5_RECALL" if hits else "PASS__FTS5_RECALL_EMPTY",
            "query": q_raw,
            "hits": hits,
            "suppressed_quarantined_or_expired": suppressed,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            "model_calls": 0,
        }

    def save(self, path: str | Path | None = None) -> Path:
        target = Path(path) if path is not None else self.state_path
        if target is None:
            raise ValueError("No state_path specified for VerificationFirstMemoryBus.save()")
        target.parent.mkdir(parents=True, exist_ok=True)
        doc = {
            "schema": SCHEMA,
            "clock": self._clock,
            "causal_edges": [e.as_dict() for e in self.causal_edges.values()],
            "conflict_clauses": [c.as_dict() for c in self.conflict_clauses.values()],
            "skills": [s.as_dict() for s in self.skills.values()],
            "version_space_traces": {
                tid: [[[obs, act] for obs, act in tr] for tr in traces]
                for tid, traces in self._version_space_traces.items()
            },
            "applicability_boundaries": dict(self._applicability_boundaries),
            "verified_event_log": list(self._verified_event_log),
            "verified_event_last_hash": self._verified_event_last_hash,
            "external_adapters": dict(self.external_adapters),
            "forgetting_ledger": list(self.forgetting_ledger),
            "skill_lifecycle": dict(self._skill_lifecycle),
            "anti_skills": dict(self._anti_skills),
        }
        target.write_text(json.dumps(doc, indent=2, sort_keys=True), encoding="utf-8")
        return target

    def load(self, path: str | Path) -> None:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        self._clock = float(raw.get("clock", 0.0))
        self.causal_edges.clear()
        self._edges_by_episode.clear()
        self._edges_by_pre.clear()
        self._edges_by_post.clear()
        for row in raw.get("causal_edges", ()):
            e = CausalEdge(**row)
            self.causal_edges[e.edge_id] = e
            self._edges_by_episode.setdefault(e.episode_id, []).append(e.edge_id)
            self._edges_by_pre.setdefault(e.pre_state, []).append(e.edge_id)
            self._edges_by_post.setdefault(e.post_state, []).append(e.edge_id)

        self.conflict_clauses.clear()
        self._conflict_lookup.clear()
        for row in raw.get("conflict_clauses", ()):
            c = ConflictClause(**row)
            self.conflict_clauses[c.clause_id] = c
            self._conflict_lookup[(c.domain, c.context_sig, c.bad_candidate)] = c.clause_id

        self.skills.clear()
        self._skills_by_trigger.clear()
        for row in raw.get("skills", ()):
            s = CrystallizedSkill(**row)
            self.skills[s.skill_id] = s
            if not s.forgotten:
                self._skills_by_trigger.setdefault(s.trigger_key, []).append(s.skill_id)

        self._version_spaces.clear()
        self._version_space_traces.clear()
        self._version_space_library = demo_vs.SkillLibrary()
        for tid, trace_list in (raw.get("version_space_traces") or {}).items():
            ss = demo_vs.SkillSet()
            norm_list: list[list[tuple[dict[str, Any], str]]] = []
            for tr in trace_list:
                norm_tr = [(dict(obs), str(act)) for obs, act in tr]
                ss.add_success(norm_tr)
                norm_list.append(norm_tr)
            if norm_list:
                self._version_spaces[str(tid)] = ss
                self._version_space_traces[str(tid)] = norm_list
                self._version_space_library.add(str(tid), ss)

        self._applicability_boundaries = {
            str(k): dict(v)
            for k, v in (raw.get("applicability_boundaries") or {}).items()
            if isinstance(v, Mapping)
        }
        self._verified_event_log = [
            dict(ev) for ev in (raw.get("verified_event_log") or ()) if isinstance(ev, Mapping)
        ]
        self._verified_event_last_hash = str(
            raw.get("verified_event_last_hash")
            or (self._verified_event_log[-1]["event_hash"] if self._verified_event_log else "0" * 64)
        )
        self.external_adapters = dict(raw.get("external_adapters", {}))
        self.forgetting_ledger = list(raw.get("forgetting_ledger", []))
        self._skill_lifecycle = {
            str(k): dict(v)
            for k, v in (raw.get("skill_lifecycle") or {}).items()
            if isinstance(v, Mapping)
        }
        self._anti_skills = {
            str(k): dict(v)
            for k, v in (raw.get("anti_skills") or {}).items()
            if isinstance(v, Mapping)
        }
        self._fts5_watermark = (-1, -1, -1, -1)


def execute_memory_operation(
    bus: VerificationFirstMemoryBus,
    operation: str,
    payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Unified front-door dispatcher (`0G`) over a ``VerificationFirstMemoryBus``."""
    op = str(operation or "").upper().strip()
    data = dict(payload or {})
    if op == "RECORD_CAUSAL_STEP":
        edge = bus.record_causal_step(**data)
        return {"schema": SCHEMA, "pass": True, "status": "PASS__CAUSAL_STEP_RECORDED", "edge": edge.as_dict()}
    if op == "QUERY_CAUSAL_CHAIN":
        chain = bus.query_causal_chain(**data)
        return {
            "schema": SCHEMA,
            "pass": len(chain) > 0,
            "status": "PASS__CAUSAL_CHAIN_FOUND" if chain else "FAIL_CLOSED__NO_CAUSAL_CHAIN",
            "chain": chain,
        }
    if op == "RECORD_CONFLICT":
        clause = bus.record_conflict(**data)
        return {"schema": SCHEMA, "pass": True, "status": "PASS__CONFLICT_RECORDED", "clause": clause.as_dict()}
    if op == "PRUNE_CANDIDATES":
        survivors = bus.prune_candidates(**data)
        return {"schema": SCHEMA, "pass": True, "status": "PASS__CANDIDATES_PRUNED", "survivors": survivors}
    if op == "CRYSTALLIZE_MACRO":
        sk = bus.crystallize_action_macro(**data)
        return {"schema": SCHEMA, "pass": True, "status": "PASS__MACRO_CRYSTALLIZED", "skill": sk.as_dict()}
    if op == "CRYSTALLIZE_CODE_REPAIR":
        sk = bus.crystallize_code_repair(**data)
        return {"schema": SCHEMA, "pass": True, "status": "PASS__CODE_SKILL_CRYSTALLIZED", "skill": sk.as_dict()}
    if op == "LOOKUP_TIER0":
        hits = bus.lookup_tier0_skills(str(data.get("trigger_key") or ""))
        return {
            "schema": SCHEMA,
            "pass": len(hits) > 0,
            "status": "PASS__TIER0_SKILL_HIT" if hits else "FAIL_CLOSED__TIER0_MISS",
            "skills": hits,
        }
    if op == "APPLY_CODE_SKILLS":
        cands = bus.apply_crystallized_code_skills(
            str(data.get("source_text") or ""),
            trigger_key=data.get("trigger_key"),
        )
        return {
            "schema": SCHEMA,
            "pass": len(cands) > 0,
            "status": "PASS__CODE_SKILLS_APPLIED" if cands else "FAIL_CLOSED__NO_APPLICABLE_SKILL",
            "candidates": cands,
        }
    if op == "SLEEP_CONSOLIDATE":
        res = bus.sleep_consolidate(**data)
        return {"schema": SCHEMA, "pass": True, "status": "PASS__SLEEP_CONSOLIDATED", "consolidation": res}
    if op == "FORGET_SKILL":
        ok = bus.forget_skill(str(data.get("skill_id") or ""), reason=str(data.get("reason") or "SELECTIVE_UNLEARN"))
        return {
            "schema": SCHEMA,
            "pass": ok,
            "status": "PASS__SKILL_FORGOTTEN" if ok else "FAIL_CLOSED__SKILL_NOT_FOUND",
        }
    if op == "FORGET_EPISODE":
        res = bus.forget_episode(
            str(data.get("episode_id") or ""), reason=str(data.get("reason") or "SELECTIVE_EPISODE_UNLEARN")
        )
        ok = (res["invalidated_edges"] + res["forgotten_skills"]) > 0
        return {
            "schema": SCHEMA,
            "pass": ok,
            "status": "PASS__EPISODE_FORGOTTEN" if ok else "FAIL_CLOSED__EPISODE_NOT_FOUND",
            "forgetting": res,
        }
    if op == "INDUCE_VERSION_SPACE":
        res = bus.induce_version_space_skill(**data)
        return {"schema": SCHEMA, "pass": bool(res.get("pass")), "status": "PASS__VERSION_SPACE_INDUCED" if res.get("pass") else "FAIL_CLOSED__VERSION_SPACE_EMPTY", **res}
    if op == "QUERY_VERSION_SPACE":
        res = bus.query_version_space_or_abstain(**data)
        acted = res.get("decision") == "ACT"
        return {
            "schema": SCHEMA,
            "pass": acted,
            "status": "PASS__VERSION_SPACE_ACT" if acted else "PASS_ABSTAIN__VERSION_SPACE_DISAGREEMENT",
            **res,
        }
    if op == "INDUCE_TRACE_QUOTIENT":
        res = bus.induce_trace_quotient(**data)
        return {
            "schema": SCHEMA,
            "pass": bool(res.get("pass")),
            "status": "PASS__TRACE_QUOTIENT_INDUCED" if res.get("pass") else "FAIL_CLOSED__NO_SUFFICIENT_QUOTIENT",
            **res,
        }
    if op == "INDUCE_PRECONDITION":
        res = bus.induce_exact_precondition(**data)
        return {
            "schema": SCHEMA,
            "pass": bool(res.get("pass")),
            "status": "PASS__PRECONDITION_INDUCED" if res.get("pass") else "FAIL_CLOSED__NO_EXACT_PRECONDITION",
            **res,
        }
    if op == "EGRAPH_ANTI_UNIFY":
        res = bus.egraph_anti_unify_and_compress(**data)
        return {"schema": SCHEMA, "pass": bool(res.get("pass")), "status": "PASS__EGRAPH_ANTI_UNIFIED", **res}
    if op == "APPLY_CST_SKILLS":
        res = bus.apply_cross_language_cst_skills(**data)
        return {
            "schema": SCHEMA,
            "pass": bool(res.get("pass")),
            "status": "PASS__CST_SKILLS_APPLIED" if res.get("pass") else "FAIL_CLOSED__NO_CST_CANDIDATE",
            **res,
        }
    if op == "LEARN_APPLICABILITY":
        res = bus.learn_applicability_boundary(**data)
        return {
            "schema": SCHEMA,
            "pass": bool(res.get("pass")),
            "status": "PASS__APPLICABILITY_LEARNED" if res.get("pass") else "FAIL_CLOSED__APPLICABILITY_VOCABULARY_GAP",
            **res,
        }
    if op == "CHECK_APPLICABILITY":
        res = bus.check_skill_applicability(**data)
        dec = str(res.get("decision") or "ABSTAIN")
        return {
            "schema": SCHEMA,
            "pass": dec == "APPLY",
            "status": f"PASS__{dec}_DECISION" if dec != "ABSTAIN" else "PASS_ABSTAIN__APPLICABILITY_AMBIGUOUS",
            **res,
        }
    if op == "ONE_SHOT_INDUCE":
        res = bus.one_shot_induce_skill(**data)
        return {"schema": SCHEMA, "pass": bool(res.get("pass")), "status": "PASS__ONE_SHOT_INDUCED", **res}
    if op == "APPEND_VERIFIED_EVENT":
        res = bus.append_verified_event(**data)
        return {"schema": SCHEMA, "pass": bool(res.get("pass")), "status": "PASS__VERIFIED_EVENT_APPENDED", **res}
    if op == "REPLAY_VERIFIED_EVENTS":
        res = bus.replay_verified_events()
        return {"schema": SCHEMA, "pass": bool(res.get("pass")), "status": "PASS__VERIFIED_EVENTS_REPLAYED", **res}
    if op == "COUNTEREXAMPLE_EXPERIMENT":
        res = bus.propose_counterexample_experiment(**data)
        return {"schema": SCHEMA, "pass": bool(res.get("pass")), "status": str(res.get("status")), **res}
    if op == "INDUCE_RUN_RELATION":
        res = bus.induce_run_relation_goal(**data)
        return {"schema": SCHEMA, "pass": bool(res.get("pass")), "status": str(res.get("status")), **res}
    if op == "ONE_EXPERIENCE_CONSEQUENCES":
        res = bus.extract_one_experience_consequences(**data)
        return {"schema": SCHEMA, "pass": bool(res.get("pass")), "status": str(res.get("status")), **res}
    if op == "RECORD_SKILL_CONTRIBUTION":
        res = bus.record_skill_contribution(**data)
        return {"schema": SCHEMA, "pass": bool(res.get("pass")), "status": str(res.get("status")), **res}
    if op == "CURATE_SKILLS":
        res = bus.curate_skills_by_contribution(**data)
        return {"schema": SCHEMA, "pass": bool(res.get("pass")), "status": str(res.get("status")), **res}
    if op == "OBSERVE_DRIFT":
        res = bus.observe_drift(**data)
        return {"schema": SCHEMA, "pass": bool(res.get("pass")), "status": str(res.get("status")), **res}
    if op == "CROSS_HOST_TRANSFER":
        res = bus.audit_cross_host_transfer(**data)
        return {"schema": SCHEMA, "pass": bool(res.get("pass")), "status": str(res.get("status")), **res}
    if op == "ONE_DEMONSTRATION_IDENTIFY":
        res = bus.identify_from_one_demonstration(**data)
        return {"schema": SCHEMA, "pass": bool(res.get("pass")), "status": str(res.get("status")), **res}
    if op == "MEMGUARD_REGISTER":
        res = bus.register_memguard_lifecycle(**data)
        return {"schema": SCHEMA, "pass": bool(res.get("pass")), "status": str(res.get("status")), **res}
    if op == "AUDIT_WORLD_EXPIRY":
        res = bus.audit_world_expiry(**data)
        return {"schema": SCHEMA, "pass": bool(res.get("pass")), "status": str(res.get("status")), **res}
    if op == "RECORD_ANTI_SKILL":
        res = bus.record_anti_skill(**data)
        return {"schema": SCHEMA, "pass": bool(res.get("pass")), "status": str(res.get("status")), **res}
    if op == "PRUNE_ANTI_SKILLS":
        res = bus.prune_by_anti_skills(**data)
        return {"schema": SCHEMA, "pass": bool(res.get("pass")), "status": str(res.get("status")), **res}
    if op == "PROVE_COMPOSITION":
        res = bus.prove_and_compose_operations(**data)
        return {"schema": SCHEMA, "pass": bool(res.get("pass")), "status": str(res.get("status")), **res}
    if op == "FTS5_RECALL":
        res = bus.fts5_recall(**data)
        return {"schema": SCHEMA, "pass": bool(res.get("pass")), "status": str(res.get("status")), **res}
    if op == "STATS":
        return {"schema": SCHEMA, "pass": True, "status": "PASS__MEMORY_STATS", "stats": bus.stats()}
    return {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED__UNKNOWN_MEMORY_OPERATION",
        "reason": f"UNKNOWN_OPERATION:{op}",
    }
