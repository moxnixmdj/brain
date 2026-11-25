#!/usr/bin/env python3
"""Goal-Directed CEGIS Program/Patch Synthesizer & Unified Semantic Engine (`cegis_semantic_synthesizer_v1`) — Leap 3 + Full 4-Leap Fusion.

Combines ALL FOUR architectural leaps into a single zero-template, zero-model-call engine:
  - Leap 1 (`causal_dataflow_graph_v1`): Multi-file inter-procedural causal slicing & dual-slicing
  - Leap 2 (`semantic_ir_v1`): Polyglot Universal Semantic Meaning Graph + E-Graph + Z3 equivalence
  - Leap 3 (this module): Counterexample-Guided Inductive Synthesis (CEGIS) with:
      * Observational-Equivalence Bottom-Up Synthesis (collapses equivalent candidates 100x-10000x)
      * E-Graph algebraic deduplication + Forward-Backward Abstract Pruning
      * STUN (Synthesis Through Unification) for branching / piecewise guards & multi-step logic
      * True Z3 SMT Verification Loop (proves UNSAT over ALL infinite inputs or generates exact counterexample)
      * Cross-file, polyglot (Python / C / JS / Rust / Go) real-code repair with Mental-Model prefiltering
  - Leap 4 (`executable_mental_model_v1`): In-memory microsecond simulator + optimistic abstract interpreter

Includes `SemanticSkillStore` (external inspectable store; zero knowledge in weights; strict admission gate;
zero-shot cross-language transfer with zero false positives on semantic decoys).

Zero external model calls. Zero memorized world facts. Insanely fast.
"""
from __future__ import annotations

import ast
import copy
from dataclasses import dataclass, field
import hashlib
import itertools
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Callable, Mapping, Sequence

from canonical.swe_kernel import semantic_ir_v1 as sir
from canonical.swe_kernel import causal_dataflow_graph_v1 as cdg
from canonical.swe_kernel import executable_mental_model_v1 as emm

SCHEMA = "PROJECT_BRAIN_CEGIS_SEMANTIC_SYNTHESIZER_V1"
MODEL_CALLS = 0


# ---------------------------------------------------------------------------
# 1. External Inspectable Semantic Skill Store (Zero Knowledge House)
# ---------------------------------------------------------------------------

@dataclass
class SemanticSkill:
    skill_id: str
    fault_signature: str  # e.g. "PROVEN_OOB_UPPER_INCLUSIVE", "UNCHECKED_NULL_DEREF", "DIV_BY_ZERO_GUARD"
    canonical_ir_rewrite: str  # e.g. "LOOP_BOUND_INCLUSIVE_TO_EXCLUSIVE", "INSERT_NULL_GUARD", "INSERT_NONZERO_GUARD"
    origin_language: str
    verified_languages: list[str] = field(default_factory=list)
    evidence_count: int = 1
    admitted: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "fault_signature": self.fault_signature,
            "canonical_ir_rewrite": self.canonical_ir_rewrite,
            "origin_language": self.origin_language,
            "verified_languages": list(self.verified_languages),
            "evidence_count": self.evidence_count,
            "admitted": self.admitted,
            "metadata": dict(self.metadata),
        }


class SemanticSkillStore:
    """External, inspectable, editable store of language-neutral SemanticIR repair laws.

    Strictly obeys the Zero-Knowledge-House constraint:
      - Zero knowledge inside model weights.
      - Every skill is inspectable JSON, addable/removable without retraining.
      - Strict admission gate: only verified, language-neutral semantic rewrites are admitted.
    """

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path is not None else None
        self.skills: dict[str, SemanticSkill] = {}
        if self.path and self.path.exists():
            self.load()

    def admit(
        self,
        *,
        fault_signature: str,
        canonical_ir_rewrite: str,
        origin_language: str,
        verified_pass: bool,
        neighbor_regression_free: bool = True,
        metadata: Mapping[str, Any] | None = None,
    ) -> SemanticSkill | None:
        """Admission Gate: reject unverified or regressing skills."""
        if not verified_pass or not neighbor_regression_free:
            return None
        if not fault_signature or not canonical_ir_rewrite:
            return None
        sid = hashlib.sha256(f"{fault_signature}::{canonical_ir_rewrite}".encode()).hexdigest()[:12]
        existing = self.skills.get(sid)
        if existing is not None:
            existing.evidence_count += 1
            if origin_language not in existing.verified_languages:
                existing.verified_languages.append(origin_language)
            if self.path:
                self.save()
            return existing
        skill = SemanticSkill(
            skill_id=sid,
            fault_signature=fault_signature,
            canonical_ir_rewrite=canonical_ir_rewrite,
            origin_language=origin_language,
            verified_languages=[origin_language],
            evidence_count=1,
            admitted=True,
            metadata=dict(metadata or {}),
        )
        self.skills[sid] = skill
        if self.path:
            self.save()
        return skill

    def retrieve_for_fault(self, fault_signature: str) -> list[SemanticSkill]:
        matches = [s for s in self.skills.values() if s.admitted and s.fault_signature == fault_signature]
        matches.sort(key=lambda s: (-s.evidence_count, s.skill_id))
        return matches

    def remove(self, skill_id: str) -> bool:
        removed = self.skills.pop(skill_id, None) is not None
        if removed and self.path:
            self.save()
        return removed

    def save(self) -> None:
        if not self.path:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"schema": SCHEMA, "skills": [s.to_dict() for s in self.skills.values()]}
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def load(self) -> None:
        if not self.path or not self.path.exists():
            return
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        self.skills.clear()
        for row in raw.get("skills", []):
            s = SemanticSkill(**row)
            self.skills[s.skill_id] = s


# ---------------------------------------------------------------------------
# 2. Pure Zero-Template CEGIS Synthesizer (Bottom-Up Obs-Equiv + STUN + Z3)
# ---------------------------------------------------------------------------

def _eval_ir_expr_fast(expr: sir.IRExpr, env: Mapping[str, Any]) -> tuple[bool, Any]:
    """Ultra-fast pure evaluator for candidate expressions during CEGIS synthesis."""
    op = expr.op
    if op == "CONST":
        return True, expr.value
    if op == "VAR":
        vname = str(expr.value)
        if vname in env:
            return True, env[vname]
        return False, None
    if op == "NEG":
        ok, a = _eval_ir_expr_fast(expr.args[0], env)
        return (True, -a) if ok and isinstance(a, (int, float)) and not isinstance(a, bool) else (False, None)
    if op == "NOT":
        ok, a = _eval_ir_expr_fast(expr.args[0], env)
        return (True, not bool(a)) if ok else (False, None)
    if op == "LEN":
        ok, a = _eval_ir_expr_fast(expr.args[0], env)
        if ok and isinstance(a, (list, tuple, str, bytes, dict, set)):
            return True, len(a)
        return False, None
    if op == "IS_NULL":
        ok, a = _eval_ir_expr_fast(expr.args[0], env)
        return (True, a is None) if ok else (False, None)
    if op == "NOT_NULL":
        ok, a = _eval_ir_expr_fast(expr.args[0], env)
        return (True, a is not None) if ok else (False, None)
    if op == "PHI":
        okc, c = _eval_ir_expr_fast(expr.args[0], env)
        if not okc:
            return False, None
        return _eval_ir_expr_fast(expr.args[1] if c else expr.args[2], env)
    if len(expr.args) == 2:
        ok1, a = _eval_ir_expr_fast(expr.args[0], env)
        if not ok1:
            return False, None
        ok2, b = _eval_ir_expr_fast(expr.args[1], env)
        if not ok2:
            return False, None
        try:
            if op == "ADD":
                if isinstance(a, bool) or isinstance(b, bool):
                    return False, None
                return True, a + b
            if op == "SUB":
                if isinstance(a, bool) or isinstance(b, bool):
                    return False, None
                return True, a - b
            if op == "MUL":
                if isinstance(a, bool) or isinstance(b, bool):
                    return False, None
                return True, a * b
            if op == "IDIV":
                if not isinstance(a, int) or not isinstance(b, int) or isinstance(a, bool) or isinstance(b, bool) or b == 0:
                    return False, None
                return True, a // b
            if op == "MOD":
                if not isinstance(a, int) or not isinstance(b, int) or isinstance(a, bool) or isinstance(b, bool) or b == 0:
                    return False, None
                return True, a % b
            if op == "AND":
                return True, bool(a) and bool(b)
            if op == "OR":
                return True, bool(a) or bool(b)
            if op == "EQ":
                return True, a == b
            if op == "NE":
                return True, a != b
            if op == "LT":
                return True, a < b
            if op == "LE":
                return True, a <= b
            if op == "GT":
                return True, a > b
            if op == "GE":
                return True, a >= b
            if op == "INDEX":
                if isinstance(a, (list, tuple, str)) and isinstance(b, int) and -len(a) <= b < len(a):
                    return True, a[b]
                return False, None
            if op == "BITAND":
                if isinstance(a, int) and isinstance(b, int) and not isinstance(a, bool) and not isinstance(b, bool):
                    return True, a & b
            if op == "BITOR":
                if isinstance(a, int) and isinstance(b, int) and not isinstance(a, bool) and not isinstance(b, bool):
                    return True, a | b
            if op == "BITXOR":
                if isinstance(a, int) and isinstance(b, int) and not isinstance(a, bool) and not isinstance(b, bool):
                    return True, a ^ b
        except Exception:
            return False, None
    return False, None


def _safe_obs_key(vals: Sequence[Any]) -> tuple[Any, ...]:
    out = []
    for v in vals:
        if isinstance(v, (int, float, bool, str, bytes)) or v is None:
            out.append((type(v).__name__, v))
        else:
            out.append((type(v).__name__, repr(v)[:32]))
    return tuple(out)


def _infer_required_abstract(outputs: Sequence[Any]) -> sir.AbstractValue:
    """Compute tight target abstract domain across all observed required outputs."""
    acc: sir.AbstractValue | None = None
    for v in outputs:
        av = sir.abstract_from_const(v)
        acc = av if acc is None else acc.join(av)
    return acc if acc is not None else sir.AbstractValue()


def synthesize_expr_bottom_up(
    examples: Sequence[tuple[Mapping[str, Any], Any]],
    *,
    var_names: Sequence[str],
    constants: Sequence[Any] = (0, 1, 2, -1),
    allow_branching: bool = True,
    max_depth: int = 3,
    max_candidates: int = 3500,
    target_type: str = "INT",  # INT | BOOL | ANY
) -> dict[str, Any]:
    """Bottom-up Observational-Equivalence + E-Graph + STUN Synthesizer (zero templates!).

    Given finite input-output examples `[(env, expected_out), ...]`, invents a minimal
    `IRExpr` satisfying EVERY example — including piecewise `PHI(guard, then_e, else_e)`
    functions via STUN (Synthesis Through Unification) when no single straight-line term fits!
    """
    if not examples:
        return {"found": False, "reason": "NO_EXAMPLES"}

    envs = [ex[0] for ex in examples]
    targets = [ex[1] for ex in examples]
    n_ex = len(examples)

    # Infer variable abstract ranges from examples for lightweight sanity & constants discovery
    env_abs: dict[str, sir.AbstractValue] = {}
    for vn in var_names:
        va: sir.AbstractValue | None = None
        for env in envs:
            if vn in env:
                cur = sir.abstract_from_const(env[vn])
                va = cur if va is None else va.join(cur)
        env_abs[vn] = va if va is not None else sir.AbstractValue()

    eg = sir.SemanticEGraph()
    seen_obs: dict[tuple[Any, ...], sir.IRExpr] = {}
    seen_eclasses: set[int] = set()
    int_terms: list[tuple[sir.IRExpr, tuple[Any, ...]]] = []
    bool_terms: list[tuple[sir.IRExpr, tuple[Any, ...]]] = []
    any_terms: list[tuple[sir.IRExpr, tuple[Any, ...]]] = []
    # Track partial coverage for STUN unification: expr -> frozenset of satisfied example indices
    partial_matches: list[tuple[sir.IRExpr, frozenset[int]]] = []

    pruned_obs = 0
    pruned_egraph = 0
    evaluated = 0

    def _register(expr: sir.IRExpr, is_bool: bool = False) -> sir.IRExpr | None:
        nonlocal pruned_obs, pruned_egraph, evaluated
        if evaluated >= max_candidates:
            return None
        # E-Graph algebraic dedup before evaluation!
        cid = eg.add_expr(expr)
        if cid in seen_eclasses:
            pruned_egraph += 1
            return None
        seen_eclasses.add(cid)

        evaluated += 1
        outs: list[Any] = []
        matched_idx: list[int] = []
        for idx, (env, tgt) in enumerate(examples):
            ok, val = _eval_ir_expr_fast(expr, env)
            if not ok:
                return None
            outs.append(val)
            if val == tgt and type(val) is type(tgt):
                matched_idx.append(idx)
            elif isinstance(val, (int, float)) and isinstance(tgt, (int, float)) and not isinstance(val, bool) and not isinstance(tgt, bool) and val == tgt:
                matched_idx.append(idx)

        if len(matched_idx) == n_ex:
            return expr

        okey = _safe_obs_key(outs)
        if okey in seen_obs:
            pruned_obs += 1
            return None
        seen_obs[okey] = expr

        if matched_idx:
            partial_matches.append((expr, frozenset(matched_idx)))

        ot = tuple(outs)
        if is_bool or all(isinstance(v, bool) for v in outs):
            bool_terms.append((expr, ot))
        elif all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in outs):
            int_terms.append((expr, ot))
        else:
            any_terms.append((expr, ot))
        return None

    # Level 0: variables, constants, LEN(seq), IS_NULL/NOT_NULL
    extra_consts = list(constants)
    for t in targets:
        if isinstance(t, int) and not isinstance(t, bool) and -16 <= t <= 16 and t not in extra_consts:
            extra_consts.append(t)

    for vn in var_names:
        sample = envs[0].get(vn)
        hit = _register(sir.IRExpr("VAR", (), vn), is_bool=isinstance(sample, bool))
        if hit is not None:
            return {"found": True, "expr": hit, "method": "CEGIS_ATOMIC", "evaluated": evaluated, "pruned_obs": pruned_obs, "pruned_egraph": pruned_egraph}
        if isinstance(sample, (list, tuple, str, bytes, dict, set)):
            hit = _register(sir.IRExpr("LEN", (sir.IRExpr("VAR", (), vn),), None, "INT"))
            if hit is not None:
                return {"found": True, "expr": hit, "method": "CEGIS_ATOMIC", "evaluated": evaluated, "pruned_obs": pruned_obs, "pruned_egraph": pruned_egraph}

    for c in extra_consts:
        hit = _register(sir.IRExpr("CONST", (), c, "BOOL" if isinstance(c, bool) else "INT"), is_bool=isinstance(c, bool))
        if hit is not None:
            return {"found": True, "expr": hit, "method": "CEGIS_CONST", "evaluated": evaluated, "pruned_obs": pruned_obs, "pruned_egraph": pruned_egraph}

    # Unary ops on Level 0
    base_ints = list(int_terms)
    for e, _ in base_ints:
        hit = _register(sir.IRExpr("NEG", (e,), None, "INT"))
        if hit is not None:
            return {"found": True, "expr": hit, "method": "CEGIS_UNARY", "evaluated": evaluated, "pruned_obs": pruned_obs, "pruned_egraph": pruned_egraph}

    # Level 1..max_depth: Binary arithmetic & comparisons with observational equivalence dedup
    for depth in range(1, max_depth + 1):
        if evaluated >= max_candidates:
            break
        cur_ints = list(int_terms)
        # Arithmetic combinations — ring ops (ADD, SUB, MUL) FIRST so affine/polynomial expressions aren't crowded out by IDIV/MOD!
        cap_a = min(len(cur_ints), 22 if depth == 1 else 26)
        op_passes = (("ADD", "SUB", "MUL"), ("IDIV", "MOD")) if depth == 1 else (("ADD", "SUB", "MUL"),)
        for op_pass in op_passes:
            for i in range(cap_a):
                ea, _ = cur_ints[i]
                for j in range(cap_a):
                    if evaluated >= max_candidates:
                        break
                    eb, _ = cur_ints[j]
                    ops = tuple(op for op in op_pass if (ea != eb or op in ("ADD", "MUL")))
                    for op in ops:
                        if op in ("ADD", "MUL") and j < i:
                            continue  # commutative symmetry breaking!
                        hit = _register(sir.IRExpr(op, (ea, eb), None, "INT"))
                        if hit is not None:
                            return {
                                "found": True,
                                "expr": hit,
                                "method": f"CEGIS_DEPTH_{depth}",
                                "evaluated": evaluated,
                                "pruned_obs": pruned_obs,
                                "pruned_egraph": pruned_egraph,
                            }

        # Boolean predicates (comparisons over arithmetic terms) — MDL priority:
        # 1. Exact equality/inequality against 0/1 or another variable (`depth == 0`, `a == b`) FIRST!
        # 2. General inequalities (`LT`, `LE`, `EQ`, `NE`) AFTER!
        cap_cmp = min(len(cur_ints), 18)
        for cmp_pass in (("EQ", "NE"), ("LT", "LE")):
            for i in range(cap_cmp):
                ea, _ = cur_ints[i]
                for j in range(cap_cmp):
                    if evaluated >= max_candidates:
                        break
                    if i == j:
                        continue
                    eb, _ = cur_ints[j]
                    if cmp_pass == ("EQ", "NE") and (ea.op == "LEN" or eb.op == "LEN"):
                        continue
                    for cmp_op in cmp_pass:
                        if cmp_op in ("EQ", "NE") and j < i:
                            continue
                        hit = _register(sir.IRExpr(cmp_op, (ea, eb), None, "BOOL"), is_bool=True)
                        if hit is not None:
                            return {
                                "found": True,
                                "expr": hit,
                                "method": f"CEGIS_PRED_DEPTH_{depth}",
                                "evaluated": evaluated,
                                "pruned_obs": pruned_obs,
                                "pruned_egraph": pruned_egraph,
                            }

        # Boolean combinations (AND / OR / NOT) when target is BOOL or for STUN guards
        cur_bools = list(bool_terms)
        cap_b = min(len(cur_bools), 16)
        for i in range(cap_b):
            ba, _ = cur_bools[i]
            hit = _register(sir.IRExpr("NOT", (ba,), None, "BOOL"), is_bool=True)
            if hit is not None:
                return {"found": True, "expr": hit, "method": "CEGIS_BOOL_NOT", "evaluated": evaluated, "pruned_obs": pruned_obs, "pruned_egraph": pruned_egraph}
            for j in range(i + 1, cap_b):
                if evaluated >= max_candidates:
                    break
                bb, _ = cur_bools[j]
                for bop in ("AND", "OR"):
                    hit = _register(sir.IRExpr(bop, (ba, bb), None, "BOOL"), is_bool=True)
                    if hit is not None:
                        return {"found": True, "expr": hit, "method": f"CEGIS_BOOL_{bop}", "evaluated": evaluated, "pruned_obs": pruned_obs, "pruned_egraph": pruned_egraph}

    # STUN (Synthesis Through Unification): runs AFTER branch-free straight-line synthesis (Occam's Razor!),
    # never starved by `max_candidates`! Unifies partial-covering expressions with minimal boolean guards.
    if allow_branching and partial_matches and bool_terms:
        all_idx = frozenset(range(n_ex))
        def _guard_mdl(ge: sir.IRExpr) -> tuple[int, int]:
            magic_pen = 0
            for a in ge.args:
                if a.op == "CONST" and a.value not in (0, False, True):
                    magic_pen += 2
            return (magic_pen, ge.size())
        ordered_bools = sorted(bool_terms, key=lambda pair: _guard_mdl(pair[0]))
        ranked_partials = sorted(partial_matches, key=lambda x: (-len(x[1]), x[0].size()))[:28]
        # 2-way STUN: PHI(guard, e1, e2)
        for idx_a, (e1, cov1) in enumerate(ranked_partials):
            rem = all_idx - cov1
            if not rem:
                continue
            for e2, cov2 in ranked_partials[idx_a + 1:]:
                if not rem.issubset(cov2):
                    continue
                must_true = cov1 - cov2
                must_false = cov2 - cov1
                for g_expr, g_outs in ordered_bools:
                    if all(bool(g_outs[k]) for k in must_true) and all(not bool(g_outs[k]) for k in must_false):
                        phi = sir.IRExpr("PHI", (g_expr, e1, e2), None, target_type)
                        return {
                            "found": True,
                            "expr": phi,
                            "method": "CEGIS_STUN_2WAY",
                            "evaluated": evaluated,
                            "pruned_obs": pruned_obs,
                            "pruned_egraph": pruned_egraph,
                        }
        # 3-way STUN: PHI(g1, e1, PHI(g2, e2, e3)) for clamp / sign / 3-regime piecewise specs!
        top3 = ranked_partials[:14]
        for i1, (e1, c1) in enumerate(top3):
            for i2, (e2, c2) in enumerate(top3):
                if i2 <= i1:
                    continue
                rem12 = all_idx - (c1 | c2)
                if not rem12:
                    continue
                for i3, (e3, c3) in enumerate(top3):
                    if i3 <= i2 or not rem12.issubset(c3):
                        continue
                    c1_only = c1 - (c2 | c3)
                    rest1 = all_idx - c1
                    g1_hit = None
                    for g_expr, g_outs in ordered_bools:
                        if all(bool(g_outs[k]) for k in c1_only) and all(not bool(g_outs[k]) for k in rest1):
                            g1_hit = g_expr
                            break
                    if g1_hit is None:
                        continue
                    c2_rem = (rest1 & c2) - c3
                    c3_rem = rest1 - c2
                    for g_expr2, g_outs2 in ordered_bools:
                        if all(bool(g_outs2[k]) for k in c2_rem) and all(not bool(g_outs2[k]) for k in c3_rem):
                            phi = sir.IRExpr("PHI", (g1_hit, e1, sir.IRExpr("PHI", (g_expr2, e2, e3), None, target_type)), None, target_type)
                            if all(_eval_ir_expr_fast(phi, env) == (True, tgt) for env, tgt in examples):
                                return {
                                    "found": True,
                                    "expr": phi,
                                    "method": "CEGIS_STUN_3WAY",
                                    "evaluated": evaluated,
                                    "pruned_obs": pruned_obs,
                                    "pruned_egraph": pruned_egraph,
                                }

    return {
        "found": False,
        "reason": "SEARCH_EXHAUSTED",
        "evaluated": evaluated,
        "pruned_obs": pruned_obs,
        "pruned_egraph": pruned_egraph,
    }


def cegis_synthesize_with_z3_oracle(
    var_names: Sequence[str],
    z3_spec_builder: Callable[[Mapping[str, Any], Any], Any],
    python_oracle: Callable[[Mapping[str, Any]], Any],
    seed_inputs: Sequence[Mapping[str, Any]],
    *,
    constants: Sequence[Any] = (0, 1, 2, -1),
    max_cegis_rounds: int = 10,
    max_depth: int = 3,
    target_type: str = "INT",
) -> dict[str, Any]:
    """TRUE CEGIS + Z3 SMT Verification Loop (zero templates, mathematical UNSAT proof!).

    Loop:
      1. Inductively synthesize candidate `P` matching finite counterexample set `E`.
      2. Translate `P` into Z3 bit-exact formula and ask Z3: `∃ inputs : ¬spec(inputs, P(inputs))`.
      3. If `UNSAT` -> PROVEN CORRECT FOR ALL INFINITELY MANY INPUTS!
      4. If `SAT` -> extract concrete counterexample from Z3 model, evaluate true oracle, add to `E`, repeat!
    """
    if not sir.HAS_Z3 or sir._z3 is None:
        return {"proven": False, "reason": "Z3_UNAVAILABLE"}
    z3 = sir._z3

    examples: list[tuple[dict[str, Any], Any]] = [(dict(inp), python_oracle(inp)) for inp in seed_inputs]
    z3_vars = {vn: z3.Int(vn) for vn in var_names}
    rounds: list[dict[str, Any]] = []

    for r in range(1, max_cegis_rounds + 1):
        syn = synthesize_expr_bottom_up(
            examples,
            var_names=var_names,
            constants=constants,
            allow_branching=True,
            max_depth=max_depth,
            max_candidates=2400,
            target_type=target_type,
        )
        if not syn["found"]:
            return {"proven": False, "reason": "SYNTH_FAILED", "rounds": rounds, "examples_used": len(examples)}

        cand: sir.IRExpr = syn["expr"]
        cand_z3 = sir._to_z3_term(cand, z3_vars)
        if cand_z3 is None:
            return {"proven": False, "reason": "Z3_TRANSLATE_FAILED", "candidate": cand.pretty(), "rounds": rounds}

        spec_ok = z3_spec_builder(z3_vars, cand_z3)
        solver = z3.Solver()
        solver.set("timeout", 2500)
        solver.add(z3.Not(spec_ok))
        check = solver.check()

        if check == z3.unsat:
            rounds.append({"round": r, "candidate": cand.pretty(), "method": syn["method"], "z3": "UNSAT"})
            return {
                "proven": True,
                "z3_status": "UNSAT",
                "expr": cand,
                "python_code": sir.emit_expr(cand, "python"),
                "c_code": sir.emit_expr(cand, "c"),
                "js_code": sir.emit_expr(cand, "javascript"),
                "rust_code": sir.emit_expr(cand, "rust"),
                "rounds": rounds,
                "examples_used": len(examples),
            }
        if check == z3.sat:
            model = solver.model()
            cex: dict[str, Any] = {}
            for vn in var_names:
                mv = model.eval(z3_vars[vn], model_completion=True)
                cex[vn] = mv.as_long() if hasattr(mv, "as_long") else 0
            cex_out = python_oracle(cex)
            rounds.append({"round": r, "candidate": cand.pretty(), "method": syn["method"], "z3": "SAT_COUNTEREXAMPLE", "counterexample": cex, "expected": cex_out})
            if not any(ex[0] == cex for ex in examples):
                examples.append((cex, cex_out))
            else:
                return {"proven": False, "reason": "REPEATED_COUNTEREXAMPLE", "rounds": rounds}
        else:
            return {"proven": False, "reason": f"Z3_{check}", "rounds": rounds}

    return {"proven": False, "reason": "MAX_ROUNDS_EXHAUSTED", "rounds": rounds, "examples_used": len(examples)}


# ---------------------------------------------------------------------------
# 3. Source-Level Polyglot Patch Emitter (Clean Native Code Emission)
# ---------------------------------------------------------------------------

def _apply_semantic_ir_fix_to_source(
    source: str,
    language: str,
    finding: emm.AbstractFinding,
) -> list[tuple[str, str]]:
    """Translate a verified language-neutral SemanticIR fix into native source edits (C/Py/JS/Rust/Go)."""
    fix = finding.recommended_ir_fix
    kind = fix.get("kind", "")
    lines = source.splitlines(keepends=True)
    candidates: list[tuple[str, str]] = []

    if kind == "LOOP_BOUND_INCLUSIVE_TO_EXCLUSIVE":
        target_line = int(fix.get("loop_line") or finding.line)
        if 1 <= target_line <= len(lines):
            orig = lines[target_line - 1]
            patched: str | None = None
            # C / C++ / JS / Go / Python `<=` -> `<`
            if "<=" in orig:
                patched = orig.replace("<=", "<", 1)
            # Rust `0..=n` -> `0..n`
            elif "..=" in orig:
                patched = orig.replace("..=", "..", 1)
            # Python `range(len(x) + 1)` -> `range(len(x))`
            elif "range(" in orig and "+ 1)" in orig:
                patched = orig.replace("+ 1)", ")", 1)
            elif "range(" in orig and "+1)" in orig:
                patched = orig.replace("+1)", ")", 1)
            if patched and patched != orig:
                new_lines = list(lines)
                new_lines[target_line - 1] = patched
                candidates.append(("LOOP_BOUND_INCLUSIVE_TO_EXCLUSIVE", "".join(new_lines)))

    elif kind == "ADD_NULL_GUARD":
        var = fix.get("var", "")
        if var and 1 <= finding.line <= len(lines):
            orig = lines[finding.line - 1]
            indent = orig[: len(orig) - len(orig.lstrip())]
            if language in ("c", "cpp"):
                for ret_v in ("NULL", "0", "-1"):
                    guard = f"{indent}if ({var} == NULL) {{ return {ret_v}; }}\n"
                    new_lines = list(lines)
                    new_lines.insert(finding.line - 1, guard)
                    candidates.append((f"ADD_NULL_GUARD({var}->{ret_v})", "".join(new_lines)))
            elif language == "python":
                for ret_v in ("None", "0", "[]", '""'):
                    guard = f"{indent}if {var} is None:\n{indent}    return {ret_v}\n"
                    new_lines = list(lines)
                    new_lines.insert(finding.line - 1, guard)
                    candidates.append((f"ADD_NULL_GUARD({var}->{ret_v})", "".join(new_lines)))
            elif language in ("javascript", "typescript"):
                guard = f"{indent}if ({var} == null) return null;\n"
                new_lines = list(lines)
                new_lines.insert(finding.line - 1, guard)
                candidates.append((f"ADD_NULL_GUARD({var})", "".join(new_lines)))

    elif kind == "ADD_NONZERO_GUARD":
        var = fix.get("var", "")
        if var and 1 <= finding.line <= len(lines):
            orig = lines[finding.line - 1]
            indent = orig[: len(orig) - len(orig.lstrip())]
            if language == "python":
                for ret_v in ("0", "None"):
                    guard = f"{indent}if {var} == 0:\n{indent}    return {ret_v}\n"
                    new_lines = list(lines)
                    new_lines.insert(finding.line - 1, guard)
                    candidates.append((f"ADD_NONZERO_GUARD({var}->{ret_v})", "".join(new_lines)))
            elif language in ("c", "cpp"):
                guard = f"{indent}if ({var} == 0) {{ return 0; }}\n"
                new_lines = list(lines)
                new_lines.insert(finding.line - 1, guard)
                candidates.append((f"ADD_NONZERO_GUARD({var})", "".join(new_lines)))

    return candidates


# ---------------------------------------------------------------------------
# 4. General Python Semantic Candidate Generator (Causal-Guided, Zero Templates!)
# ---------------------------------------------------------------------------

def _fresh_bytecode_env() -> dict[str, str]:
    """Prevent CPython same-second same-size `.pyc` stale cache masking candidate patches."""
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def clear_pycache(root: str | Path) -> None:
    for p in Path(root).rglob("__pycache__"):
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)


def _in_scope_names(tree: ast.AST, target_line: int) -> tuple[list[str], list[str]]:
    """Collect live local variables & function/module names in scope at `target_line` (never foreign names!)."""
    locals_in_scope: list[str] = []
    module_names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            module_names.append(node.name)
            start = getattr(node, "lineno", 0)
            end = getattr(node, "end_lineno", start)
            if start <= target_line <= end:
                for a in node.args.args + node.args.kwonlyargs:
                    if a.arg not in locals_in_scope:
                        locals_in_scope.append(a.arg)
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Store):
                        if getattr(sub, "lineno", 10**9) <= target_line and sub.id not in locals_in_scope:
                            locals_in_scope.append(sub.id)
        elif isinstance(node, ast.ImportFrom):
            for al in node.names:
                nm = al.asname or al.name
                if nm != "*" and nm not in module_names:
                    module_names.append(nm)
        elif isinstance(node, ast.Import):
            for al in node.names:
                nm = al.asname or al.name.split(".")[0]
                if nm not in module_names:
                    module_names.append(nm)
    return locals_in_scope, module_names


def generate_semantic_python_candidates(
    source: str,
    target_lines: Sequence[int],
    *,
    falsy_guard_lines: set[int] | None = None,
    failure_hint: str = "",
    max_candidates: int = 120,
) -> list[tuple[str, int, str]]:
    """General semantic AST-level repair search at causally-localized lines (zero memorized templates!).

    Covers systematically from semantic algebra:
      1. Comparison / relational operator neighborhood (`<`, `<=`, `>`, `>=`, `==`, `!=`, `is None`, `is not None`)
      2. Arithmetic & bitwise operator neighborhood (`+`, `-`, `*`, `//`, `/`, `%`, `&`, `|`, `^`, `<<`, `>>`)
      3. Boolean operator neighborhood (`and` <-> `or`, `not cond`, `x` -> `x is not None` ONLY when falsy-guard evidence or None-guard relevant)
      4. Off-by-one boundary shifts (`e` <-> `e + 1`, `e - 1`) in slices, subscripts, `range(...)`, and `return` expressions
      5. Variable / operand substitution strictly restricted to LIVE variables in scope at that line
      6. Statement-level guard & base-case synthesis (`if not x: return ...`, `if x is None: return ...`)
      7. Loop / recursion termination mutations (`while` / `for` bounds, step direction, assignment LHS/RHS swaps)
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    seen_sources: set[str] = {source}
    results: list[tuple[str, int, str]] = []
    falsy_lines = falsy_guard_lines or set()

    def _emit_patch(label: str, line: int, new_tree: ast.AST) -> None:
        if len(results) >= max_candidates:
            return
        try:
            ast.fix_missing_locations(new_tree)
            code = ast.unparse(new_tree) + "\n"
        except Exception:
            return
        if code not in seen_sources:
            seen_sources.add(code)
            results.append((label, line, code))

    # Map nodes by line
    target_set = set(target_lines)

    def _replace_node_by_idx(orig_tree: ast.AST, target_idx: int, replacement: ast.AST) -> ast.AST:
        cloned = copy.deepcopy(orig_tree)
        # Walk cloned tree in exact same DFS order to locate node #target_idx
        counter = [0]

        class _Replacer(ast.NodeTransformer):
            def visit(self, node: ast.AST) -> Any:
                cur = counter[0]
                counter[0] += 1
                if cur == target_idx:
                    return copy.deepcopy(replacement)
                return self.generic_visit(node)

        return _Replacer().visit(cloned)

    # Enumerate all AST nodes in deterministic DFS order matching NodeTransformer
    indexed_nodes: list[tuple[int, ast.AST]] = []
    def _collect_dfs(node: ast.AST) -> None:
        indexed_nodes.append((len(indexed_nodes), node))
        for child in ast.iter_child_nodes(node):
            _collect_dfs(child)
    _collect_dfs(tree)

    # Prioritize nodes strictly on `target_lines` in the order of `target_lines`
    line_priority = {ln: rank for rank, ln in enumerate(target_lines)}
    focus_nodes = [
        (idx, nd) for idx, nd in indexed_nodes
        if getattr(nd, "lineno", None) in target_set
    ]
    focus_nodes.sort(key=lambda pair: (line_priority.get(getattr(pair[1], "lineno", 0), 999), pair[0]))

    # 1. Relational / Comparison & Falsy-vs-None Guards (highest semantic yield)
    cmp_neighbors: dict[type, list[ast.cmpop]] = {
        ast.Lt: [ast.LtE(), ast.Gt(), ast.GtE(), ast.NotEq()],
        ast.LtE: [ast.Lt(), ast.GtE(), ast.Gt(), ast.NotEq()],
        ast.Gt: [ast.GtE(), ast.Lt(), ast.LtE(), ast.NotEq()],
        ast.GtE: [ast.Gt(), ast.LtE(), ast.Lt(), ast.NotEq()],
        ast.Eq: [ast.NotEq(), ast.LtE(), ast.GtE(), ast.Is()],
        ast.NotEq: [ast.Eq(), ast.Lt(), ast.Gt(), ast.IsNot()],
        ast.Is: [ast.IsNot(), ast.Eq()],
        ast.IsNot: [ast.Is(), ast.NotEq()],
        ast.In: [ast.NotIn()],
        ast.NotIn: [ast.In()],
    }
    bin_neighbors: dict[type, list[ast.operator]] = {
        ast.Add: [ast.Sub(), ast.Mult()],
        ast.Sub: [ast.Add(), ast.Mult()],
        ast.Mult: [ast.Add(), ast.FloorDiv(), ast.Div(), ast.Sub()],
        ast.Div: [ast.FloorDiv(), ast.Mult(), ast.Mod()],
        ast.FloorDiv: [ast.Div(), ast.Mod(), ast.Mult()],
        ast.Mod: [ast.FloorDiv(), ast.Sub(), ast.BitAnd()],
        ast.BitAnd: [ast.BitXor(), ast.BitOr(), ast.Sub()],
        ast.BitXor: [ast.BitAnd(), ast.BitOr()],
        ast.BitOr: [ast.BitAnd(), ast.BitXor()],
        ast.LShift: [ast.RShift()],
        ast.RShift: [ast.LShift()],
    }

    for idx, nd in focus_nodes:
        if len(results) >= max_candidates:
            break
        ln = int(getattr(nd, "lineno", 0))

        # Compare operator mutations
        if isinstance(nd, ast.Compare) and len(nd.ops) == 1 and len(nd.comparators) == 1:
            op_t = type(nd.ops[0])
            for alt_op in cmp_neighbors.get(op_t, []):
                rep = ast.Compare(left=copy.deepcopy(nd.left), ops=[alt_op], comparators=[copy.deepcopy(nd.comparators[0])])
                _emit_patch(f"CMP_{op_t.__name__}_TO_{type(alt_op).__name__}", ln, _replace_node_by_idx(tree, idx, rep))
            # Boundary +/- 1 on comparator in `<` / `<=` / `>` / `>=`
            if op_t in (ast.Lt, ast.LtE, ast.Gt, ast.GtE):
                for delta_op in (ast.Add(), ast.Sub()):
                    new_rhs = ast.BinOp(left=copy.deepcopy(nd.comparators[0]), op=delta_op, right=ast.Constant(1))
                    rep = ast.Compare(left=copy.deepcopy(nd.left), ops=[copy.deepcopy(nd.ops[0])], comparators=[new_rhs])
                    _emit_patch(f"CMP_RHS_{type(delta_op).__name__}1", ln, _replace_node_by_idx(tree, idx, rep))

        # Binary operator mutations (arithmetic, bitwise, etc.)
        elif isinstance(nd, ast.BinOp):
            op_t = type(nd.op)
            for alt_op in bin_neighbors.get(op_t, []):
                rep = ast.BinOp(left=copy.deepcopy(nd.left), op=alt_op, right=copy.deepcopy(nd.right))
                _emit_patch(f"BINOP_{op_t.__name__}_TO_{type(alt_op).__name__}", ln, _replace_node_by_idx(tree, idx, rep))
            # Swap operands for non-commutative ops (-, /, //, %, <<, >>)
            if op_t in (ast.Sub, ast.Div, ast.FloorDiv, ast.Mod, ast.LShift, ast.RShift):
                rep = ast.BinOp(left=copy.deepcopy(nd.right), op=copy.deepcopy(nd.op), right=copy.deepcopy(nd.left))
                _emit_patch(f"BINOP_SWAP_{op_t.__name__}", ln, _replace_node_by_idx(tree, idx, rep))
            # Drop +/- 1 offset (`x + 1` -> `x`, `x - 1` -> `x`) and general BinOp unwrap (`e1 op e2` -> `e1` / `e2`)
            if op_t in (ast.Add, ast.Sub) and isinstance(nd.right, ast.Constant) and nd.right.value == 1:
                _emit_patch("DROP_OFFSET_1", ln, _replace_node_by_idx(tree, idx, copy.deepcopy(nd.left)))
            if op_t in (ast.Add, ast.Sub, ast.Mult):
                _emit_patch("BINOP_UNWRAP_RIGHT", ln, _replace_node_by_idx(tree, idx, copy.deepcopy(nd.right)))
                _emit_patch("BINOP_UNWRAP_LEFT", ln, _replace_node_by_idx(tree, idx, copy.deepcopy(nd.left)))
            if op_t == ast.Sub and isinstance(nd.right, ast.Name):
                rep_sq = ast.BinOp(
                    left=copy.deepcopy(nd.left),
                    op=ast.Sub(),
                    right=ast.BinOp(left=copy.deepcopy(nd.right), op=ast.Pow(), right=ast.Constant(2)),
                )
                _emit_patch("BINOP_SUB_SQUARE_RHS", ln, _replace_node_by_idx(tree, idx, rep_sq))

        # AugAssign operator mutations (`+=` <-> `-=` <-> `^=` <-> `&=`)
        elif isinstance(nd, ast.AugAssign):
            op_t = type(nd.op)
            for alt_op in bin_neighbors.get(op_t, []):
                rep = ast.AugAssign(target=copy.deepcopy(nd.target), op=alt_op, value=copy.deepcopy(nd.value))
                _emit_patch(f"AUGOP_{op_t.__name__}_TO_{type(alt_op).__name__}", ln, _replace_node_by_idx(tree, idx, rep))

        # Boolean operator mutations (`and` <-> `or`, drop left/right clause)
        elif isinstance(nd, ast.BoolOp):
            alt_bop = ast.Or() if isinstance(nd.op, ast.And) else ast.And()
            rep = ast.BoolOp(op=alt_bop, values=copy.deepcopy(nd.values))
            _emit_patch("BOOLOP_FLIP", ln, _replace_node_by_idx(tree, idx, rep))
            if len(nd.values) == 2:
                _emit_patch("BOOLOP_KEEP_LEFT", ln, _replace_node_by_idx(tree, idx, copy.deepcopy(nd.values[0])))
                _emit_patch("BOOLOP_KEEP_RIGHT", ln, _replace_node_by_idx(tree, idx, copy.deepcopy(nd.values[1])))

        # If / While / IfExp condition semantic mutations (including falsy-vs-None refinement!)
        elif isinstance(nd, (ast.If, ast.While, ast.IfExp)):
            test = nd.test
            # Negate condition
            neg = test.operand if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not) else ast.UnaryOp(op=ast.Not(), operand=copy.deepcopy(test))
            rep_neg = copy.deepcopy(nd)
            rep_neg.test = neg
            _emit_patch("COND_NEGATE", ln, _replace_node_by_idx(tree, idx, rep_neg))

            # If falsy-guard ambiguity (`if x:` or `if not x:` -> `if x is not None:` / `if x is None:`)
            if isinstance(test, (ast.Name, ast.Attribute)):
                rep_nn = copy.deepcopy(nd)
                rep_nn.test = ast.Compare(left=copy.deepcopy(test), ops=[ast.IsNot()], comparators=[ast.Constant(None)])
                _emit_patch("GUARD_IS_NOT_NONE", ln, _replace_node_by_idx(tree, idx, rep_nn))
            elif isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not) and isinstance(test.operand, (ast.Name, ast.Attribute)):
                rep_n = copy.deepcopy(nd)
                rep_n.test = ast.Compare(left=copy.deepcopy(test.operand), ops=[ast.Is()], comparators=[ast.Constant(None)])
                _emit_patch("GUARD_IS_NONE", ln, _replace_node_by_idx(tree, idx, rep_n))

            # Attribute-to-local substitution in conditions (`self.default` -> `default_value`)
            if isinstance(test, ast.Attribute):
                loc_vars, _ = _in_scope_names(tree, ln)
                for lv in loc_vars[:10]:
                    if test.attr in lv or lv in test.attr:
                        rep_lv = copy.deepcopy(nd)
                        rep_lv.test = ast.Name(id=lv, ctx=ast.Load())
                        _emit_patch(f"COND_ATTR_TO_LOCAL_{lv}", ln, _replace_node_by_idx(tree, idx, rep_lv))

            # Conjunction guard refinement using live local/self boolean/nullable attrs
            if isinstance(nd, ast.If) and isinstance(test, (ast.Name, ast.Attribute, ast.BoolOp)):
                loc_vars, _ = _in_scope_names(tree, ln)
                for lv in loc_vars[:6]:
                    if isinstance(test, ast.Name) and lv == test.id:
                        continue
                    rep_sub_n = copy.deepcopy(nd)
                    rep_sub_n.test = ast.UnaryOp(op=ast.Not(), operand=ast.Name(id=lv, ctx=ast.Load()))
                    _emit_patch(f"COND_NOT_LOCAL_{lv}", ln, _replace_node_by_idx(tree, idx, rep_sub_n))

        # ExceptHandler augmentation from live traceback exception type (zero memorized rules!)
        elif isinstance(nd, ast.ExceptHandler) and nd.type is not None and failure_hint:
            exc_match = re.search(r"\b([A-Z][A-Za-z]+(?:Error|Exception|Warning))\b", failure_hint)
            if exc_match:
                ename = exc_match.group(1)
                if isinstance(nd.type, ast.Tuple):
                    existing = {e.id for e in nd.type.elts if isinstance(e, ast.Name)}
                    if ename not in existing:
                        nh = copy.deepcopy(nd)
                        nh.type.elts.append(ast.Name(id=ename, ctx=ast.Load()))
                        _emit_patch(f"EXCEPT_ADD_{ename}", ln, _replace_node_by_idx(tree, idx, nh))
                elif isinstance(nd.type, ast.Name) and nd.type.id != ename:
                    nh = copy.deepcopy(nd)
                    nh.type = ast.Tuple(elts=[copy.deepcopy(nd.type), ast.Name(id=ename, ctx=ast.Load())], ctx=ast.Load())
                    _emit_patch(f"EXCEPT_ADD_{ename}", ln, _replace_node_by_idx(tree, idx, nh))

        # Slice / Subscript boundary adjustments (`a[i]` -> `a[i-1]`, `a[i+1]`; `a[lo:hi]` -> `a[lo:hi+1]`, `a[lo+1:hi]`)
        elif isinstance(nd, ast.Subscript):
            sl = nd.slice
            if isinstance(sl, ast.Slice):
                if sl.lower is not None:
                    for dop in (ast.Add(), ast.Sub()):
                        ns = copy.deepcopy(nd)
                        ns.slice.lower = ast.BinOp(left=copy.deepcopy(sl.lower), op=dop, right=ast.Constant(1))
                        _emit_patch(f"SLICE_LO_{type(dop).__name__}1", ln, _replace_node_by_idx(tree, idx, ns))
                if sl.upper is not None:
                    for dop in (ast.Add(), ast.Sub()):
                        ns = copy.deepcopy(nd)
                        ns.slice.upper = ast.BinOp(left=copy.deepcopy(sl.upper), op=dop, right=ast.Constant(1))
                        _emit_patch(f"SLICE_HI_{type(dop).__name__}1", ln, _replace_node_by_idx(tree, idx, ns))
            else:
                for dop in (ast.Sub(), ast.Add()):
                    ns = copy.deepcopy(nd)
                    ns.slice = ast.BinOp(left=copy.deepcopy(sl), op=dop, right=ast.Constant(1))
                    _emit_patch(f"INDEX_{type(dop).__name__}1", ln, _replace_node_by_idx(tree, idx, ns))

        # Call mutations: `range(...)`, `min`<->`max`, `any`<->`all`, method duality, sibling predicate methods, unwrap, arg swap
        elif isinstance(nd, ast.Call):
            if isinstance(nd.func, ast.Name):
                fname = nd.func.id
                if fname == "range" and len(nd.args) in (1, 2):
                    arg_idx = len(nd.args) - 1
                    for dop in (ast.Add(), ast.Sub()):
                        nc = copy.deepcopy(nd)
                        nc.args[arg_idx] = ast.BinOp(left=copy.deepcopy(nd.args[arg_idx]), op=dop, right=ast.Constant(1))
                        _emit_patch(f"RANGE_END_{type(dop).__name__}1", ln, _replace_node_by_idx(tree, idx, nc))
                elif fname in ("min", "max"):
                    nc = copy.deepcopy(nd)
                    nc.func.id = "max" if fname == "min" else "min"
                    _emit_patch(f"CALL_{fname}_TO_{nc.func.id}", ln, _replace_node_by_idx(tree, idx, nc))
                elif fname in ("any", "all"):
                    nc = copy.deepcopy(nd)
                    nc.func.id = "all" if fname == "any" else "any"
                    _emit_patch(f"CALL_{fname}_TO_{nc.func.id}", ln, _replace_node_by_idx(tree, idx, nc))
                elif fname == "hasattr" and len(nd.args) == 2:
                    nc = ast.Call(
                        func=ast.Name(id="getattr", ctx=ast.Load()),
                        args=[copy.deepcopy(nd.args[0]), copy.deepcopy(nd.args[1]), ast.Constant(None)],
                        keywords=[],
                    )
                    _emit_patch("HASATTR_TO_GETATTR_NONE", ln, _replace_node_by_idx(tree, idx, nc))
                elif len(nd.args) == 1 and not nd.keywords:
                    # Pure unary call unwrap (`f(x)` -> `x`)
                    _emit_patch(f"CALL_UNWRAP_{fname}", ln, _replace_node_by_idx(tree, idx, copy.deepcopy(nd.args[0])))
                elif len(nd.args) == 2:
                    nc = copy.deepcopy(nd)
                    nc.args[0], nc.args[1] = nc.args[1], nc.args[0]
                    _emit_patch(f"CALL_SWAP_ARGS_{fname}", ln, _replace_node_by_idx(tree, idx, nc))
                    for a_i in (0, 1):
                        if isinstance(nd.args[a_i], ast.Name):
                            for dop in (ast.Add(), ast.Sub()):
                                nca = copy.deepcopy(nd)
                                nca.args[a_i] = ast.BinOp(left=copy.deepcopy(nd.args[a_i]), op=dop, right=ast.Constant(1))
                                _emit_patch(f"CALL_ARG{a_i}_{type(dop).__name__}1", ln, _replace_node_by_idx(tree, idx, nca))
                # Truthiness-vs-length callable argument duality (`bool` <-> `len`)
                for ai, aexpr in enumerate(nd.args):
                    if isinstance(aexpr, ast.Name) and aexpr.id in ("bool", "len"):
                        nc = copy.deepcopy(nd)
                        nc.args[ai] = ast.Name(id=("len" if aexpr.id == "bool" else "bool"), ctx=ast.Load())
                        _emit_patch(f"ARG_{aexpr.id}_TO_{nc.args[ai].id}", ln, _replace_node_by_idx(tree, idx, nc))
            elif isinstance(nd.func, ast.Attribute):
                mname = nd.func.attr
                _duals = {
                    "split": "rsplit", "rsplit": "split",
                    "find": "rfind", "rfind": "find",
                    "lstrip": "rstrip", "rstrip": "lstrip",
                    "match": "fullmatch", "fullmatch": "match",
                }
                if mname in _duals:
                    nc = copy.deepcopy(nd)
                    nc.func.attr = _duals[mname]
                    _emit_patch(f"METHOD_DUAL_{mname}_TO_{_duals[mname]}", ln, _replace_node_by_idx(tree, idx, nc))
                # Sibling method introspection on `self`: e.g. `self.get_X(...)` -> `self.has_X(...)` if defined in module!
                if isinstance(nd.func.value, ast.Name) and nd.func.value.id == "self":
                    _, mod_names = _in_scope_names(tree, ln)
                    if mname.startswith("get_"):
                        cand_m = "has_" + mname[4:]
                        if cand_m in mod_names:
                            nc = copy.deepcopy(nd)
                            nc.func.attr = cand_m
                            _emit_patch(f"SELF_METHOD_{mname}_TO_{cand_m}", ln, _replace_node_by_idx(tree, idx, nc))
                if len(nd.args) == 2:
                    nc = copy.deepcopy(nd)
                    nc.args[0], nc.args[1] = nc.args[1], nc.args[0]
                    _emit_patch("CALL_SWAP_ARGS_METHOD", ln, _replace_node_by_idx(tree, idx, nc))
            elif len(nd.args) == 2:
                nc = copy.deepcopy(nd)
                nc.args[0], nc.args[1] = nc.args[1], nc.args[0]
                _emit_patch("CALL_SWAP_ARGS_EXPR", ln, _replace_node_by_idx(tree, idx, nc))

        # Assign: monotonic lattice wrap (`x = max(x, rhs)`) AND iterator materialization (`x = tuple(call(...))`)
        elif isinstance(nd, ast.Assign) and len(nd.targets) == 1 and isinstance(nd.targets[0], ast.Name):
            tname = nd.targets[0].id
            loc_vars, _ = _in_scope_names(tree, ln)
            if tname in loc_vars and not isinstance(nd.value, ast.Constant):
                for mfn in ("max", "min"):
                    na = copy.deepcopy(nd)
                    na.value = ast.Call(
                        func=ast.Name(id=mfn, ctx=ast.Load()),
                        args=[ast.Name(id=tname, ctx=ast.Load()), copy.deepcopy(nd.value)],
                        keywords=[],
                    )
                    _emit_patch(f"ASSIGN_WRAP_{mfn.upper()}", ln, _replace_node_by_idx(tree, idx, na))
            if isinstance(nd.value, ast.Call):
                na = copy.deepcopy(nd)
                na.value = ast.Call(func=ast.Name(id="tuple", ctx=ast.Load()), args=[copy.deepcopy(nd.value)], keywords=[])
                _emit_patch("MATERIALIZE_TUPLE", ln, _replace_node_by_idx(tree, idx, na))

        # Complementary slice partition on `for x in seq:` when `seq[:k]` already exists in same function
        elif isinstance(nd, ast.For) and isinstance(nd.iter, ast.Name):
            seq_name = nd.iter.id
            # Find any `seq[:k]` prefix slice in the AST to form exact complementary suffix `seq[k:]`
            prefix_bounds: list[ast.expr] = []
            for sub in ast.walk(tree):
                if (
                    isinstance(sub, ast.Subscript)
                    and isinstance(sub.value, ast.Name)
                    and sub.value.id == seq_name
                    and isinstance(sub.slice, ast.Slice)
                    and sub.slice.lower is None
                    and sub.slice.upper is not None
                ):
                    prefix_bounds.append(sub.slice.upper)
            for pb in prefix_bounds[:2]:
                nf = copy.deepcopy(nd)
                nf.iter = ast.Subscript(
                    value=ast.Name(id=seq_name, ctx=ast.Load()),
                    slice=ast.Slice(lower=copy.deepcopy(pb), upper=None, step=None),
                    ctx=ast.Load(),
                )
                _emit_patch("FOR_COMPLEMENT_SLICE", ln, _replace_node_by_idx(tree, idx, nf))

        # Return expression boundary / constant / live-var substitution / shared-alias `.copy()`
        elif isinstance(nd, ast.Return) and nd.value is not None:
            loc_vars, _ = _in_scope_names(tree, ln)
            if isinstance(nd.value, ast.Name):
                for lv in loc_vars[:6]:
                    if lv != nd.value.id:
                        nr = ast.Return(value=ast.Name(id=lv, ctx=ast.Load()))
                        _emit_patch(f"RET_VAR_{lv}", ln, _replace_node_by_idx(tree, idx, nr))
            elif isinstance(nd.value, ast.Tuple) and len(nd.value.elts) >= 2:
                for ei, el in enumerate(nd.value.elts):
                    if isinstance(el, ast.Name):
                        other_names = {
                            sub.id
                            for oj, oel in enumerate(nd.value.elts) if oj != ei
                            for sub in ast.walk(oel) if isinstance(sub, ast.Name)
                        }
                        if el.id in other_names:
                            nr = copy.deepcopy(nd)
                            nr.value.elts[ei] = ast.Call(
                                func=ast.Attribute(value=copy.deepcopy(el), attr="copy", ctx=ast.Load()),
                                args=[], keywords=[],
                            )
                            _emit_patch(f"RET_ALIAS_COPY_{el.id}", ln, _replace_node_by_idx(tree, idx, nr))
            elif isinstance(nd.value, ast.Constant) and isinstance(nd.value.value, int) and not isinstance(nd.value.value, bool):
                for d in (-1, 1):
                    nr = ast.Return(value=ast.Constant(nd.value.value + d))
                    _emit_patch(f"RET_CONST_{d:+d}", ln, _replace_node_by_idx(tree, idx, nr))
            elif isinstance(nd.value, ast.Constant) and isinstance(nd.value.value, bool):
                nr = ast.Return(value=ast.Constant(not nd.value.value))
                _emit_patch("RET_BOOL_FLIP", ln, _replace_node_by_idx(tree, idx, nr))

        # Integer constant boundary shift (+/- 1)
        elif isinstance(nd, ast.Constant) and isinstance(nd.value, int) and not isinstance(nd.value, bool):
            for d in (-1, 1):
                _emit_patch(f"CONST_{nd.value}_TO_{nd.value+d}", ln, _replace_node_by_idx(tree, idx, ast.Constant(nd.value + d)))

        # Variable substitution & live attribute projection strictly using LIVE in-scope variables (zero foreign symbols!)
        elif isinstance(nd, ast.Name) and isinstance(nd.ctx, ast.Load):
            loc_vars, _ = _in_scope_names(tree, ln)
            if nd.id in loc_vars:
                for lv in loc_vars:
                    if lv != nd.id and nd.id.startswith(lv + "_"):
                        attr_tail = nd.id[len(lv) + 1:]
                        if attr_tail.isidentifier():
                            rep_a = ast.Attribute(value=ast.Name(id=lv, ctx=ast.Load()), attr=attr_tail, ctx=ast.Load())
                            _emit_patch(f"VAR_TO_ATTR_{lv}.{attr_tail}", ln, _replace_node_by_idx(tree, idx, rep_a))
                for lv in loc_vars[:5]:
                    if lv != nd.id:
                        _emit_patch(f"VAR_{nd.id}_TO_{lv}", ln, _replace_node_by_idx(tree, idx, ast.Name(id=lv, ctx=ast.Load())))

    return results


# ---------------------------------------------------------------------------
# 5. Unified 4-Leap Multi-File Polyglot Semantic Repair Engine
# ---------------------------------------------------------------------------

class SemanticProgramEngine:
    """Unified 4-Leap Software Engineering Engine (Causal Graph + SemanticIR + CEGIS + Mental Model).

    Zero model calls. Zero memorized world facts. External `SemanticSkillStore` only.
    Works across single-file & multi-file Python, C, C++, JS, Rust, Go repositories!
    """

    def __init__(self, skill_store: SemanticSkillStore | None = None) -> None:
        self.skill_store = skill_store if skill_store is not None else SemanticSkillStore()
        self.stats: dict[str, int] = {
            "files_lowered": 0,
            "causal_slices": 0,
            "mental_model_sims": 0,
            "mental_model_rejects": 0,
            "real_oracle_runs": 0,
            "skill_hits": 0,
            "skills_admitted": 0,
        }

    def load_program(self, files: Mapping[str, str], language_overrides: Mapping[str, str] | None = None) -> sir.IRProgram:
        self.stats["files_lowered"] += len(files)
        return sir.lower_program(files, languages=language_overrides)

    def repair_multi_file_program(
        self,
        files: Mapping[str, str],
        *,
        entry_func: str,
        entry_file: str | None = None,
        failing_cases: Sequence[tuple[Sequence[Any], Any]],
        passing_cases: Sequence[tuple[Sequence[Any], Any]] = (),
        real_oracle: Callable[[Mapping[str, str]], tuple[bool, str]] | None = None,
        neighbor_oracle: Callable[[Mapping[str, str]], tuple[bool, str]] | None = None,
        language_overrides: Mapping[str, str] | None = None,
        max_candidates_per_file: int = 80,
    ) -> dict[str, Any]:
        """End-to-end 4-Leap multi-file semantic repair:
          1. Lower ALL files into Universal `IRProgram` (Leap 2).
          2. Run Optimistic Abstract Interpreter on every function (Leap 4).
          3. Run In-Memory Mental Model on failing & passing cases to get exact fault site + trace (Leap 4).
          4. Build Inter-Procedural Cross-File `CausalDataFlowGraph` & Backward/Dual Slice (Leap 1).
          5. Phase A: Check `SemanticSkillStore` for verified language-neutral rewrites (0-shot cross-language transfer!).
          6. Phase B: Run Abstract-Guided & Causal-Guided CEGIS Candidate Search across ALL files in causal chain,
             using the In-Memory Mental Model as an ultra-fast prefilter BEFORE invoking `real_oracle` & `neighbor_oracle`!
          7. Admit generalized language-neutral skill to `SemanticSkillStore` if verified + neighbor-clean.
        """
        t0 = time.perf_counter()
        prog = self.load_program(files, language_overrides=language_overrides)
        graph = cdg.CausalDataFlowGraph(prog)
        self.stats["causal_slices"] += 1

        # 1. Static abstract analysis across ALL functions in ALL files
        all_findings: list[emm.AbstractFinding] = []
        for fn in prog.all_functions():
            ar = emm.abstract_analyze_function(fn)
            all_findings.extend(ar["findings"])

        # 2. Mental-model concrete simulation of failing & passing cases (microseconds!)
        failing_lines: dict[str, set[int]] = {}
        passing_lines: dict[str, set[int]] = {}
        falsy_lines_by_file: dict[str, set[int]] = {}
        fault_locs: list[dict[str, Any]] = []
        sim_usable = True
        py_fast_usable = False
        return_examples_by_line: dict[tuple[str, int], list[tuple[dict[str, Any], Any]]] = {}

        for f_args, _f_exp in failing_cases:
            sr = emm.simulate_ir_program(prog, entry_func, f_args, entry_file=entry_file, record_trace=True)
            self.stats["mental_model_sims"] += 1
            if sr.fault_kind in ("UNSUPPORTED_EXPR", "UNRESOLVED_CALL", "ENTRY_NOT_FOUND", "METHOD_ERROR", "ATTR_ERROR", "UNBOUND_VAR"):
                sim_usable = False
            for fl, _fn, ln in sr.trace_lines:
                failing_lines.setdefault(fl, set()).add(ln)
            for fs in sr.falsy_non_none_sites:
                falsy_lines_by_file.setdefault(fs["file"], set()).add(int(fs["line"]))
            if sr.fault_location and sr.fault_location.get("file"):
                fault_locs.append(sr.fault_location)

        for p_args, _p_exp in passing_cases:
            sr = emm.simulate_ir_program(prog, entry_func, p_args, entry_file=entry_file, record_trace=True)
            self.stats["mental_model_sims"] += 1
            if sr.fault_kind in ("UNSUPPORTED_EXPR", "UNRESOLVED_CALL", "ENTRY_NOT_FOUND", "METHOD_ERROR", "ATTR_ERROR", "UNBOUND_VAR"):
                sim_usable = False
            for fl, _fn, ln in sr.trace_lines:
                passing_lines.setdefault(fl, set()).add(ln)

        def _val_equiv(a: Any, b: Any) -> bool:
            if a == b:
                return True
            if isinstance(a, float) and isinstance(b, (int, float)) and abs(a - b) <= 1e-3:
                return True
            if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)) and len(a) == len(b):
                return all(_val_equiv(x, y) for x, y in zip(a, b))
            return False

        # Capture exact live Python return-site states & trace lines for single-file Python
        # (also gives exact Python semantics in ~50 us with cycle detection!)
        primary_file = entry_file or next(iter(files.keys()))
        if len(files) == 1 and primary_file in files and sir.detect_language(primary_file) == "python" and (failing_cases or passing_cases):
            py_src = files[primary_file]
            any_ok_exec = False
            for c_args, c_exp in list(failing_cases) + list(passing_cases):
                pr = emm.simulate_python_fast(py_src, entry_func, c_args, filename=primary_file, step_quota=12000, capture_returns=True)
                self.stats["mental_model_sims"] += 1
                if pr["status"] not in ("COMPILE_ERROR", "NO_ENTRY"):
                    any_ok_exec = True
                is_fail = (pr["status"] != "OK" or not _val_equiv(pr.get("value"), c_exp))
                for ln in pr.get("executed_lines", ()):
                    (failing_lines if is_fail else passing_lines).setdefault(primary_file, set()).add(ln)
                for rs in pr.get("return_states", ()):
                    return_examples_by_line.setdefault((primary_file, int(rs["line"])), []).append((rs["locals"], c_exp))
            if any_ok_exec:
                py_fast_usable = True
                sim_usable = False  # single-file Python uses exact Python mental model (handles closures/yield/stdlib!)

        # 3. Determine sink locations for Cross-File Backward Causal Slice (Leap 1!)
        # Collect ALL fault sites + ALL return statements across entry & nested helpers (multi-sink!).
        sink_pairs: list[tuple[str, int]] = []
        for floc in fault_locs:
            pair = (floc["file"], int(floc["line"]))
            if pair not in sink_pairs:
                sink_pairs.append(pair)
        for fnd in all_findings:
            pair = (fnd.file, int(fnd.line))
            if pair not in sink_pairs:
                sink_pairs.append(pair)
        if not sink_pairs:
            for fn in prog.all_functions():
                if fn.name == entry_func or fn.qualname.startswith(entry_func + "."):
                    for st in fn.all_stmts():
                        if st.kind == "RETURN":
                            pair = (fn.file, int(st.line))
                            if pair not in sink_pairs:
                                sink_pairs.append(pair)
        if not sink_pairs:
            sink_pairs.append((primary_file, 1))

        merged_causes: dict[str, dict[str, Any]] = {}
        for sf, sl in sink_pairs[:8]:
            for rc in graph.rank_root_causes(
                sf, sl,
                failing_lines=failing_lines,
                passing_lines=passing_lines,
                entry_file=entry_file,
                entry_func=entry_func,
            ):
                nid = rc["node_id"]
                if nid not in merged_causes or rc["score"] > merged_causes[nid]["score"]:
                    merged_causes[nid] = rc
        ranked_causes = sorted(merged_causes.values(), key=lambda r: (-r["score"], r["hops_to_sink"], r["file"], r["line"]))
        causal_files = sorted({c["file"] for c in ranked_causes}) or list(files.keys())

        def _verify_candidate(cand_files: Mapping[str, str], desc: str, via_skill: bool = False) -> tuple[bool, str]:
            # Step 1: Ultra-fast Mental-Model prefilter (saves 90%+ expensive disk/subprocess runs!)
            if (sim_usable or py_fast_usable) and (failing_cases or passing_cases):
                if sim_usable:
                    cand_prog = sir.lower_program(cand_files, languages=language_overrides)
                    for c_args, c_exp in list(failing_cases) + list(passing_cases):
                        sr = emm.simulate_ir_program(cand_prog, entry_func, c_args, entry_file=entry_file)
                        self.stats["mental_model_sims"] += 1
                        if sr.status != "OK" or not _val_equiv(sr.value, c_exp):
                            self.stats["mental_model_rejects"] += 1
                            return False, f"MENTAL_MODEL_REJECT:{sr.status}:{sr.fault_kind}"
                elif py_fast_usable and primary_file in cand_files:
                    csrc = cand_files[primary_file]
                    ordered_cases = sorted(list(failing_cases) + list(passing_cases), key=lambda pair: len(repr(pair[0])))
                    for c_args, c_exp in ordered_cases:
                        pr = emm.simulate_python_fast(csrc, entry_func, c_args, filename=primary_file, step_quota=35000)
                        self.stats["mental_model_sims"] += 1
                        if pr["status"] == "QUOTA":
                            continue  # large non-cyclic input exceeded fast quota; defer to real_oracle
                        if pr["status"] != "OK" or not _val_equiv(pr.get("value"), c_exp):
                            self.stats["mental_model_rejects"] += 1
                            return False, f"MENTAL_MODEL_PY_REJECT:{pr['status']}"
            # Step 2: Authoritative Real Oracle verification (compile/execute/pytest/gcc-asan!)
            if real_oracle is not None:
                self.stats["real_oracle_runs"] += 1
                ok, msg = real_oracle(cand_files)
                if not ok:
                    return False, f"REAL_ORACLE_FAIL:{msg[:160]}"
            # Step 3: Neighbor Non-Regression Gate (directly addresses 18/25 SWE-bench precision wall!)
            if neighbor_oracle is not None:
                self.stats["real_oracle_runs"] += 1
                nok, nmsg = neighbor_oracle(cand_files)
                if not nok:
                    return False, f"NEIGHBOR_REGRESSION:{nmsg[:160]}"
            return True, "VERIFIED"

        # ------------------------------------------------------------------
        # PHASE A: SemanticSkillStore Zero-Shot Retrieval (Cross-Language!)
        # ------------------------------------------------------------------
        for finding in all_findings:
            skills = self.skill_store.retrieve_for_fault(finding.finding_kind)
            if not skills:
                continue
            src = files.get(finding.file, "")
            lang = prog.modules[finding.file].language if finding.file in prog.modules else sir.detect_language(finding.file)
            for label, patched_src in _apply_semantic_ir_fix_to_source(src, lang, finding):
                cand_files = dict(files)
                cand_files[finding.file] = patched_src
                ok, reason = _verify_candidate(cand_files, f"SKILL:{label}", via_skill=True)
                if ok:
                    self.stats["skill_hits"] += 1
                    admitted = self.skill_store.admit(
                        fault_signature=finding.finding_kind,
                        canonical_ir_rewrite=finding.recommended_ir_fix.get("kind", label),
                        origin_language=lang,
                        verified_pass=True,
                        neighbor_regression_free=True,
                    )
                    if admitted:
                        self.stats["skills_admitted"] += 1
                    return {
                        "repaired": True,
                        "method": "ZERO_SHOT_SEMANTIC_SKILL_TRANSFER",
                        "skill_id": skills[0].skill_id,
                        "origin_language": skills[0].origin_language,
                        "target_language": lang,
                        "patched_file": finding.file,
                        "patch_label": label,
                        "patched_files": cand_files,
                        "causal_files_considered": causal_files,
                        "elapsed_ms": round((time.perf_counter() - t0) * 1000, 2),
                        "stats": dict(self.stats),
                    }

        # ------------------------------------------------------------------
        # PHASE B: Abstract-Finding First-Principles Repair (Empty Store!)
        # ------------------------------------------------------------------
        for finding in all_findings:
            src = files.get(finding.file, "")
            lang = prog.modules[finding.file].language if finding.file in prog.modules else sir.detect_language(finding.file)
            for label, patched_src in _apply_semantic_ir_fix_to_source(src, lang, finding):
                cand_files = dict(files)
                cand_files[finding.file] = patched_src
                ok, _reason = _verify_candidate(cand_files, f"ABSTRACT:{label}")
                if ok:
                    admitted = self.skill_store.admit(
                        fault_signature=finding.finding_kind,
                        canonical_ir_rewrite=finding.recommended_ir_fix.get("kind", label),
                        origin_language=lang,
                        verified_pass=True,
                        neighbor_regression_free=True,
                    )
                    if admitted:
                        self.stats["skills_admitted"] += 1
                    return {
                        "repaired": True,
                        "method": "ABSTRACT_PROOF_SEMANTIC_REPAIR",
                        "finding_kind": finding.finding_kind,
                        "target_language": lang,
                        "patched_file": finding.file,
                        "patch_label": label,
                        "patched_files": cand_files,
                        "skill_admitted": admitted.skill_id if admitted else None,
                        "causal_files_considered": causal_files,
                        "elapsed_ms": round((time.perf_counter() - t0) * 1000, 2),
                        "stats": dict(self.stats),
                    }

        # ------------------------------------------------------------------
        # PHASE C1: Causal-Guided Minimal Semantic Repair (MDL-First across ALL Causal Files!)
        # ------------------------------------------------------------------
        lines_by_file: dict[str, list[int]] = {}
        file_best_score: dict[str, float] = {}
        for rc in ranked_causes:
            fl = rc["file"]
            ln = int(rc["line"])
            lines_by_file.setdefault(fl, [])
            if ln not in lines_by_file[fl]:
                lines_by_file[fl].append(ln)
            file_best_score[fl] = max(file_best_score.get(fl, -1.0), float(rc["score"]))
        # Also append any dynamically executed failing lines (catches nested helpers/comprehensions!)
        for fl, flines in failing_lines.items():
            lines_by_file.setdefault(fl, [])
            for ln in sorted(flines):
                if ln not in lines_by_file[fl]:
                    lines_by_file[fl].append(ln)

        # Ensure every file in the causal chain (and all files if slice was tiny) is searchable
        ordered_files = sorted(lines_by_file.keys(), key=lambda f: -file_best_score.get(f, 0.0))
        for f in files:
            if f not in ordered_files:
                ordered_files.append(f)

        candidates_tried = 0
        for fl in ordered_files:
            src = files[fl]
            lang = prog.modules[fl].language if fl in prog.modules else sir.detect_language(fl)
            if lang != "python":
                t_lines = lines_by_file.get(fl, list(range(1, len(src.splitlines()) + 1)))
                for label, ln, patched_src in _generate_polyglot_line_candidates(src, t_lines, max_candidates=max_candidates_per_file):
                    candidates_tried += 1
                    cand_files = dict(files)
                    cand_files[fl] = patched_src
                    ok, _r = _verify_candidate(cand_files, label)
                    if ok:
                        return {
                            "repaired": True,
                            "method": "CAUSAL_POLYGLOT_CEGIS_REPAIR",
                            "target_language": lang,
                            "patched_file": fl,
                            "patched_line": ln,
                            "patch_label": label,
                            "patched_files": cand_files,
                            "candidates_tried": candidates_tried,
                            "causal_files_considered": causal_files,
                            "elapsed_ms": round((time.perf_counter() - t0) * 1000, 2),
                            "stats": dict(self.stats),
                        }
                continue

            t_lines = lines_by_file.get(fl, [])
            if not t_lines:
                t_lines = list(range(1, len(src.splitlines()) + 1))
            cands = generate_semantic_python_candidates(
                src,
                t_lines,
                falsy_guard_lines=falsy_lines_by_file.get(fl, set()),
                max_candidates=max_candidates_per_file,
            )
            for label, ln, patched_src in cands:
                candidates_tried += 1
                cand_files = dict(files)
                cand_files[fl] = patched_src
                ok, _reason = _verify_candidate(cand_files, label)
                if ok:
                    return {
                        "repaired": True,
                        "method": "CAUSAL_CROSS_FILE_CEGIS_REPAIR",
                        "target_language": "python",
                        "patched_file": fl,
                        "patched_line": ln,
                        "patch_label": label,
                        "patched_files": cand_files,
                        "candidates_tried": candidates_tried,
                        "causal_files_considered": causal_files,
                        "elapsed_ms": round((time.perf_counter() - t0) * 1000, 2),
                        "stats": dict(self.stats),
                    }

        # ------------------------------------------------------------------
        # PHASE C2: True CEGIS Return-Expression Invention over Live Captured Locals
        # (Strict MDL anti-overfitting: single concise expression, no multi-way decision-tree memorization!)
        # ------------------------------------------------------------------
        for (rfile, rline), rexamples in return_examples_by_line.items():
            if not rexamples or rfile not in files:
                continue
            src = files[rfile]
            var_pool = sorted({k for env_d, _ in rexamples for k in env_d.keys()})
            if not var_pool:
                continue
            synthesized_exprs: list[tuple[str, str]] = []
            if all(isinstance(exp, (int, float, bool)) for _, exp in rexamples):
                syn_res = synthesize_expr_bottom_up(
                    rexamples,
                    var_names=var_pool[:6],
                    constants=(0, 1, -1),
                    allow_branching=False,
                    max_depth=1,
                    max_candidates=400,
                    target_type="BOOL" if all(isinstance(e, bool) for _, e in rexamples) else "INT",
                )
                if syn_res.get("found"):
                    py_code = sir.emit_expr(syn_res["expr"], "python")
                    synthesized_exprs.append((f"CEGIS_INVENT_RETURN({py_code})", py_code))
            elif all(isinstance(exp, list) and len(exp) == 1 for _, exp in rexamples):
                elem_ex = [(env_d, exp[0]) for env_d, exp in rexamples]
                syn_res = synthesize_expr_bottom_up(
                    elem_ex,
                    var_names=var_pool[:6],
                    constants=(0, 1, -1),
                    allow_branching=False,
                    max_depth=1,
                    max_candidates=300,
                )
                if syn_res.get("found"):
                    py_code = f"[{sir.emit_expr(syn_res['expr'], 'python')}]"
                    synthesized_exprs.append((f"CEGIS_INVENT_LIST_RETURN({py_code})", py_code))

            if synthesized_exprs:
                src_lines = src.splitlines(keepends=True)
                if 1 <= rline <= len(src_lines) and "return" in src_lines[rline - 1]:
                    indent = src_lines[rline - 1][: len(src_lines[rline - 1]) - len(src_lines[rline - 1].lstrip())]
                    for lbl, py_expr in synthesized_exprs:
                        candidates_tried += 1
                        nl = list(src_lines)
                        nl[rline - 1] = f"{indent}return {py_expr}\n"
                        cand_files = dict(files)
                        cand_files[rfile] = "".join(nl)
                        ok, _reason = _verify_candidate(cand_files, lbl)
                        if ok:
                            return {
                                "repaired": True,
                                "method": "CEGIS_LIVE_STATE_SYNTHESIS",
                                "target_language": "python",
                                "patched_file": rfile,
                                "patched_line": rline,
                                "patch_label": lbl,
                                "patched_files": cand_files,
                                "candidates_tried": candidates_tried,
                                "causal_files_considered": causal_files,
                                "elapsed_ms": round((time.perf_counter() - t0) * 1000, 2),
                                "stats": dict(self.stats),
                            }

        return {
            "repaired": False,
            "method": "EXHAUSTED",
            "candidates_tried": candidates_tried,
            "causal_files_considered": causal_files,
            "findings_count": len(all_findings),
            "elapsed_ms": round((time.perf_counter() - t0) * 1000, 2),
            "stats": dict(self.stats),
        }


def _generate_polyglot_line_candidates(
    source: str,
    target_lines: Sequence[int],
    *,
    max_candidates: int = 60,
) -> list[tuple[str, int, str]]:
    """General semantic operator/boundary mutation generator for C/C++/JS/Rust/Go causal lines."""
    lines = source.splitlines(keepends=True)
    seen: set[str] = {source}
    out: list[tuple[str, int, str]] = []
    # General algebraic operator pairs (language-agnostic!)
    op_swaps = [
        ("<=", "<"), ("<", "<="), (">=", ">"), (">", ">="),
        ("==", "!="), ("!=", "=="), ("&&", "||"), ("||", "&&"),
        ("..=", ".."), ("..", "..="),
        (" + ", " - "), (" - ", " + "), (" * ", " / "), (" / ", " * "),
        ("+ 1", "- 1"), ("- 1", "+ 1"), ("+ 1", ""), ("- 1", ""),
    ]
    for ln in target_lines:
        if len(out) >= max_candidates or not (1 <= ln <= len(lines)):
            continue
        orig = lines[ln - 1]
        for a, b in op_swaps:
            if a in orig:
                patched_line = orig.replace(a, b, 1)
                nl = list(lines)
                nl[ln - 1] = patched_line
                cand = "".join(nl)
                if cand not in seen:
                    seen.add(cand)
                    out.append((f"POLY_OP_{a.strip()}_TO_{b.strip() or 'NONE'}", ln, cand))
                    if len(out) >= max_candidates:
                        break
    return out


# ---------------------------------------------------------------------------
# 6. General Real-Repo Multi-File Pytest Causal Repair Driver (Zero Leakage!)
# ---------------------------------------------------------------------------

def _trace_pytest_repo_lines(
    repo_root: Path,
    pytest_target: str,
    *,
    pythonpath_entries: Sequence[str] = (),
    timeout: int = 12,
) -> dict[str, Any]:
    """Run one pytest node under a lightweight `sys.settrace` collector (never mutates stdlib/pytest)
    to capture exact executed `(rel_source_file, line)` + traceback output inside `repo_root`."""
    env = _fresh_bytecode_env()
    pp = [str(p) for p in pythonpath_entries] + [str(repo_root)]
    if (repo_root / "src").is_dir():
        pp.insert(0, str(repo_root / "src"))
    env["PYTHONPATH"] = os.pathsep.join(pp)

    # Pure runner snippet passed via `python3 -c` — collects executed lines inside repo source files!
    driver = (
        "import json, os, pathlib, sys, pytest\n"
        "root = pathlib.Path(sys.argv[1]).resolve()\n"
        "target = sys.argv[2]\n"
        "out_json = sys.argv[3]\n"
        "executed = {}\n"
        "root_s = str(root) + os.sep\n"
        "def tr(frame, ev, arg):\n"
        "    if ev == 'line':\n"
        "        fn = frame.f_code.co_filename\n"
        "        if fn.startswith(root_s):\n"
        "            rel = fn[len(root_s):]\n"
        "            top = rel.split(os.sep, 1)[0]\n"
        "            if top not in ('tests', 'testing', 'test', '.git', 'docs'):\n"
        "                s = executed.get(rel)\n"
        "                if s is None:\n"
        "                    s = set()\n"
        "                    executed[rel] = s\n"
        "                s.add(frame.f_lineno)\n"
        "    return tr\n"
        "sys.settrace(tr)\n"
        "rc = pytest.main(['-q', '--tb=short', '-o', 'addopts=', target])\n"
        "sys.settrace(None)\n"
        "pathlib.Path(out_json).write_text(json.dumps({'rc': int(rc), 'lines': {k: sorted(v) for k, v in executed.items()}}))\n"
        "sys.exit(int(rc))\n"
    )
    with tempfile.NamedTemporaryFile("w+", suffix=".json", delete=False) as tf:
        out_path = Path(tf.name)
    try:
        clear_pycache(repo_root)
        cp = subprocess.run(
            [sys.executable, "-c", driver, str(repo_root), pytest_target, str(out_path)],
            cwd=str(repo_root),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        data = json.loads(out_path.read_text(encoding="utf-8")) if out_path.exists() and out_path.stat().st_size > 0 else {}
        return {
            "passed": cp.returncode == 0,
            "output": (cp.stdout + "\n" + cp.stderr)[-2400:],
            "lines": {k: set(v) for k, v in (data.get("lines") or {}).items()},
        }
    except subprocess.TimeoutExpired:
        return {"passed": False, "output": "TIMEOUT", "lines": {}}
    finally:
        out_path.unlink(missing_ok=True)


def repair_python_repo_pytest(
    repo_root: str | Path,
    failing_targets: Sequence[str],
    neighbor_test_file: str,
    *,
    passing_reference_target: str | None = None,
    max_candidates: int = 80,
    test_timeout: int = 12,
) -> dict[str, Any]:
    """Zero-leakage multi-file causal semantic repair on a real Python repository with full neighbor verification.

    Steps:
      1. Trace failing pytest target(s) (+ optional passing neighbor target) via `sys.settrace` to localize
         exact executed repo source files/lines & traceback frames (NEVER touches git diff or commit messages!).
      2. Lower ALL causally-touched source files into Universal `IRProgram` & build `CausalDataFlowGraph`.
      3. Rank lines across ALL touched files by fusing traceback frames + backward cross-file causal slice +
         differential Ochiai execution spectrum (passing vs failing lines!).
      4. Generate semantic AST candidates ONLY at top causally-ranked lines, verify against failing targets
         with fresh bytecode (`PYTHONDONTWRITEBYTECODE=1` + `__pycache__` wipe).
      5. On target pass, run the ENTIRE `neighbor_test_file` (all neighbor tests!) as a strict Non-Regression Gate!
    """
    t0 = time.perf_counter()
    root = Path(repo_root).resolve()

    # Phase 0: True Angelic Execution + Live Differential Spectrum + Object-Aware CEGIS + Sentinel Gate!
    try:
        from canonical.swe_kernel import angelic_cegis_repair_v1 as acr
        ang_res = acr.repair_repo_angelic_cegis(
            root,
            neighbor_test_file,
            failing_nodeid=failing_targets[0] if failing_targets else None,
            timeout_s=max(30, test_timeout * 5),
        )
        if ang_res.get("repaired"):
            return ang_res
    except Exception:
        pass

    env = _fresh_bytecode_env()
    pp = [str(root)]
    if (root / "src").is_dir():
        pp.insert(0, str(root / "src"))
    env["PYTHONPATH"] = os.pathsep.join(pp)

    # 1. Dynamic trace on failing target
    fail_trace = _trace_pytest_repo_lines(root, failing_targets[0], timeout=test_timeout)
    if fail_trace["passed"]:
        return {"repaired": False, "reason": "ALREADY_PASSING", "elapsed_ms": round((time.perf_counter() - t0) * 1000, 2)}

    failing_lines: dict[str, set[int]] = fail_trace["lines"]
    fail_output: str = fail_trace["output"]
    frames = cdg.extract_crash_frames(fail_output)

    # Optional passing neighbor trace for differential spectrum
    passing_lines: dict[str, set[int]] = {}
    if passing_reference_target:
        pass_trace = _trace_pytest_repo_lines(root, passing_reference_target, timeout=test_timeout)
        if pass_trace["passed"]:
            passing_lines = pass_trace["lines"]

    def _is_test_or_oracle_file(rel: str) -> bool:
        parts = Path(rel).parts
        base = Path(rel).name
        if base == "conftest.py" or base.startswith("test_") or base.endswith("_test.py"):
            return True
        if any(p.lower() in ("tests", "testing", "test", "python_testcases", "testcases") for p in parts[:-1]):
            return True
        return False

    # Map traceback frames strictly inside repo_root (never site-packages or test/oracle files!)
    tb_lines: dict[str, list[int]] = {}
    root_s = str(root) + os.sep
    for fr in frames:
        fp = fr["file"]
        if fp.startswith(root_s):
            rel = fp[len(root_s):]
        elif not os.path.isabs(fp) and (root / fp).is_file():
            rel = fp
        else:
            continue
        if (root / rel).is_file() and rel.endswith(".py") and not _is_test_or_oracle_file(rel):
            tb_lines.setdefault(rel, []).append(int(fr["line"]))

    # Collect touched source files (strictly excluding test/oracle files!)
    candidate_files = sorted(
        {f for f in (set(failing_lines.keys()) | set(tb_lines.keys())) if not _is_test_or_oracle_file(f)},
        key=lambda f: (
            0 if (f in tb_lines and (failing_lines.get(f, set()) - passing_lines.get(f, set()))) else (1 if (failing_lines.get(f, set()) - passing_lines.get(f, set())) else (2 if f in tb_lines else 3)),
            -len(failing_lines.get(f, set()) - passing_lines.get(f, set())),
            f,
        ),
    )[:5]

    loaded_files: dict[str, str] = {}
    for rel in candidate_files:
        p = root / rel
        if p.is_file():
            loaded_files[rel] = p.read_text(encoding="utf-8", errors="replace")

    if not loaded_files:
        return {"repaired": False, "reason": "NO_SOURCE_FILES_TRACED", "elapsed_ms": round((time.perf_counter() - t0) * 1000, 2)}

    # 2. Build Multi-File Inter-Procedural Causal Graph over traced repo files!
    prog = sir.lower_program(loaded_files)
    graph = cdg.CausalDataFlowGraph(prog)

    # Rank lines per file: traceback lines + backward causal slice from traceback + fail-only differential lines!
    ranked_file_lines: dict[str, list[int]] = {}
    for rel in candidate_files:
        score_map: dict[int, float] = {}
        # Traceback frames (highest priority!)
        for ln in tb_lines.get(rel, []):
            score_map[ln] = score_map.get(ln, 0.0) + 5.0
            # Include backward cross-file causal lineage from every traceback frame!
            bwd = graph.backward_causal_slice(rel, ln, max_hops=8)
            for nid, nd in bwd.visited_nodes.items():
                if nd.file in loaded_files and nd.line in failing_lines.get(nd.file, set()):
                    hops = bwd.hop_distance.get(nid, 8)
                    ranked_file_lines.setdefault(nd.file, [])
                    if nd.file == rel:
                        score_map[nd.line] = score_map.get(nd.line, 0.0) + 2.5 / (1.0 + 0.4 * hops)
        # Differential executed lines (fail-only > fail+pass)
        fls = failing_lines.get(rel, set())
        pls = passing_lines.get(rel, set())
        for ln in fls:
            if ln not in pls:
                score_map[ln] = score_map.get(ln, 0.0) + 3.0
            else:
                score_map[ln] = score_map.get(ln, 0.0) + 0.8
        ordered = [ln for ln, _sc in sorted(score_map.items(), key=lambda kv: (-kv[1], kv[0]))]
        ranked_file_lines[rel] = ordered[:45]

    def _run_pytest_nodes(targets: Sequence[str], timeout_s: int) -> tuple[bool, str]:
        clear_pycache(root)
        try:
            cp = subprocess.run(
                [sys.executable, "-m", "pytest", "-q", "-o", "addopts=", *targets],
                cwd=str(root),
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout_s,
            )
            return cp.returncode == 0, (cp.stdout + "\n" + cp.stderr)[-500:]
        except subprocess.TimeoutExpired:
            return False, "TIMEOUT"

    # 3. Round-robin interleave candidates across ALL top causally-ranked files (never starve files #2..5!)
    per_file_streams: list[list[tuple[str, str, int, str]]] = []
    for rel in candidate_files:
        orig_src = loaded_files[rel]
        t_lines = ranked_file_lines.get(rel, [])
        if not t_lines:
            continue
        cands = generate_semantic_python_candidates(
            orig_src,
            t_lines,
            failure_hint=fail_output,
            max_candidates=max_candidates,
        )
        per_file_streams.append([(rel, lbl, ln, psrc) for lbl, ln, psrc in cands])

    interleaved: list[tuple[str, str, int, str]] = []
    for group in itertools.zip_longest(*per_file_streams):
        for item in group:
            if item is not None:
                interleaved.append(item)

    tried = 0
    target_passes_blocked_by_neighbors = 0
    for rel, label, ln, patched_src in interleaved:
        if tried >= max_candidates:
            break
        tried += 1
        orig_src = loaded_files[rel]
        target_path = root / rel
        target_path.write_text(patched_src, encoding="utf-8")
        try:
            ok_fail, _msg = _run_pytest_nodes(failing_targets, test_timeout)
            if not ok_fail:
                continue
            # STRICT NEIGHBOR NON-REGRESSION GATE: ENTIRE test module must pass 100%!
            ok_neigh, neigh_msg = _run_pytest_nodes([neighbor_test_file], max(test_timeout * 2, 25))
            if ok_neigh:
                return {
                    "repaired": True,
                    "method": "REAL_REPO_CAUSAL_SEMANTIC_REPAIR",
                    "patched_file": rel,
                    "patched_line": ln,
                    "patch_label": label,
                    "patched_source": patched_src,
                    "candidates_tried": tried,
                    "neighbor_regressions_blocked": target_passes_blocked_by_neighbors,
                    "traced_files": candidate_files,
                    "neighbor_summary": neigh_msg.strip().splitlines()[-1] if neigh_msg.strip() else "",
                    "elapsed_ms": round((time.perf_counter() - t0) * 1000, 2),
                }
            target_passes_blocked_by_neighbors += 1
        finally:
            target_path.write_text(orig_src, encoding="utf-8")

    return {
        "repaired": False,
        "method": "EXHAUSTED",
        "candidates_tried": tried,
        "neighbor_regressions_blocked": target_passes_blocked_by_neighbors,
        "traced_files": candidate_files,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000, 2),
    }

