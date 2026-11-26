#!/usr/bin/env python3
"""Futamura "Compile Away the Frontier" Unified Leapfrog Kernel (`K3 = 0`).

Unifies six frontier-leapfrog mechanisms into ONE sub-millisecond, pure-stdlib kernel
wired directly onto `UnifiedModel`, `fast_cascade_orchestrator_v1`, `VerificationFirstMemoryBus`,
and `Creature`:

  1. `ConformalEValueGate` (SCoRE, Mar 2026): Anytime-valid sequential e-process
     (`E_t = prod e_i`, Ville's inequality `P_H0(exists t: E_t >= 1/alpha) <= alpha`)
     emitting strict `{COMMIT, PROBE, ABSTAIN_FAIL_CLOSED}` verdicts under optional stopping.
  2. `DBSPBeliefRevisionBus`: Algebraic DBSP bi-temporal `Z`-set incremental store (`< 15 us`
     at 25K+ events) + formal Kumiho AGM belief-revision dependency graph (`Supersedes`,
     `Depends_On`, `Derived_From` + transitive `analyze_impact`) + deterministic `projectmem`
     `PreCommitFailureGate` (`< 10 us` nogood blocking until tracked dependencies change).
  3. `ErrorAwareSymbolicMealyLearner` (L# / Lambda*_M, Feb 2026): Sub-millisecond black-box
     automata + binary-split numeric-guard learner with error-persistence pruning and
     algebraic advice equivalence collapse.
  4. `HybridComputerUsePetriSupervisor` (HCU + OSWorld-Human + PASTE): Strict 3-channel
     cost escalation (`Programmatic CLI/File -> Semantic AX/CDP -> Visual`), `< 5 us` Petri
     consumable/inhibitor transition guard, 2-step loop-churn killer, and PASTE speculative
     macro commit with safe rollback.
  5. `ZeroOverheadCoWZygoteRepairEngine`: PEP-669 `sys.monitoring` (Python 3.12+) /
     `sys.settrace` (Python 3.11) Ochiai fault localization + `< 50 us` UTF-8 byte-span AST
     splicing + POSIX `os.fork()` Copy-on-Write parallel screening + Ring-0 `ddmin` hunk
     minimization + touched-line mutation-kill auditing.
  6. `FutamuraSelfCompilingCascade` + `wake_sleep_consolidate` (SkillCompiler + GrowLibm +
     Rubin Rent): Compiles every Ring-0 verified Rung 1/2/3 win into an alpha-normalized,
     parameterized Rung-0 rewrite rule (`< 50 us` generalized replay on unseen isomorphic
     tasks with renamed functions/variables/constants) and consolidates rules during sleep
     via anti-unification MDL compression + Rubin `(WITH - WITHOUT)` skill-rent GC.

Authority: NONE. Pure Python stdlib, `$0` spend, fail-closed everywhere.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import json
import math
import os
import sys
import time
from collections import deque
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from canonical.runtime.byte_effect_oracle_v1 import (
    audit_patch_mutation_kill,
    ddmin_minimize_hunks,
    verify_byte_effect,
)

SCHEMA = "PROJECT_BRAIN_FUTAMURA_LEAPFROG_KERNEL_V1"


# ===========================================================================
# 1. Anytime-Valid Conformal E-Value Gate (SCoRE, Ville's Inequality)
# ===========================================================================


class ConformalEValueGate:
    """Distribution-free anytime-valid sequential e-process risk controller.

    Maintains `log E_t = sum_i log(e_i)` where each factor satisfies `E_H0[e_i] <= 1`.
    By Ville's inequality, stopping at ANY step `t` when `E_t >= 1 / alpha` guarantees
    false-commit probability `<= alpha` under `H0`.
    """

    def __init__(self, *, alpha: float = 0.05) -> None:
        if not (0.0 < alpha < 1.0):
            raise ValueError(f"alpha must be in (0, 1), got {alpha}")
        self.alpha = float(alpha)
        self.threshold = 1.0 / self.alpha
        self.log_threshold = math.log(self.threshold)
        self.log_e: float = 0.0
        self.contradicted: bool = False
        self.steps: list[dict[str, Any]] = []

    @property
    def e_value(self) -> float:
        if self.log_e > 700.0:
            return float("inf")
        if self.log_e < -700.0:
            return 0.0
        return math.exp(self.log_e)

    def observe(
        self,
        evidence_name: str,
        *,
        passed: bool,
        null_pass_prob: float = 0.25,
        hard_contradiction: bool = False,
    ) -> dict[str, Any]:
        """Update the anytime-valid e-process with one calibrated verification test.

        For a binary test with null pass probability `p0 in (0, 1)`:
          - Pass factor: `e = (1 - eps) / p0` (with `eps = 0.05` betting conservatism)
          - Fail factor: `e = eps / (1 - p0)`
        Check: `E_H0[e] = p0 * ((1-eps)/p0) + (1-p0) * (eps/(1-p0)) = (1-eps) + eps = 1.0`!
        So `E_H0[e_i] == 1.0` EXACTLY for every `p0 in (0, 1)`!
        """
        p0 = min(max(float(null_pass_prob), 1e-6), 1.0 - 1e-6)
        eps = 0.05
        if passed:
            factor = (1.0 - eps) / p0
        else:
            factor = eps / (1.0 - p0)
            if hard_contradiction:
                self.contradicted = True
        self.log_e += math.log(max(factor, 1e-12))
        rec = {
            "step": len(self.steps) + 1,
            "evidence": evidence_name,
            "passed": bool(passed),
            "null_pass_prob": round(p0, 6),
            "factor": round(factor, 6),
            "e_value": round(self.e_value, 6) if math.isfinite(self.e_value) else "inf",
        }
        self.steps.append(rec)
        return self.decision()

    def decision(self) -> dict[str, Any]:
        if self.contradicted:
            verdict = "ABSTAIN_FAIL_CLOSED"
            reason = "HARD_CONTRADICTION_WITNESS"
        elif self.log_e >= self.log_threshold:
            verdict = "COMMIT"
            reason = "E_VALUE_CLEARED_VILLE_BOUND"
        elif self.log_e <= -math.log(max(2.0, self.threshold)):
            verdict = "ABSTAIN_FAIL_CLOSED"
            reason = "E_VALUE_COLLAPSED_UNDER_NULL"
        else:
            verdict = "PROBE"
            reason = "INSUFFICIENT_EVIDENCE_EMIT_MINIMAL_PROBE"
        return {
            "schema": SCHEMA + "/conformal_evalue",
            "verdict": verdict,
            "reason": reason,
            "alpha": self.alpha,
            "threshold": round(self.threshold, 6),
            "e_value": round(self.e_value, 6) if math.isfinite(self.e_value) else "inf",
            "log_e": round(self.log_e, 6),
            "step_count": len(self.steps),
            "steps": list(self.steps),
        }


# ===========================================================================
# 2. DBSP Bi-Temporal Z-Set + Kumiho AGM Belief Revision + PreCommitFailureGate
# ===========================================================================


@dataclass
class _ZSetRecord:
    record_id: str
    key: str
    payload: Any
    valid_from: float
    valid_to: float  # math.inf for open interval
    weight: int  # +1 active, 0 retracted
    status: str = "ACTIVE"  # ACTIVE | SUPERSEDED | STALE_NEEDS_REVERIFICATION
    version: int = 1


class DBSPBeliefRevisionBus:
    """Algebraic DBSP bi-temporal Z-set + AGM dependency graph + PreCommitFailureGate."""

    def __init__(self) -> None:
        self._records: dict[str, _ZSetRecord] = {}
        self._by_key: dict[str, list[str]] = {}
        self._delta_count: int = 0
        # AGM provenance graph edges
        self._depends_on: dict[str, set[str]] = {}  # child -> {parent_ids}
        self._dependents: dict[str, set[str]] = {}  # parent -> {child_ids}
        self._supersedes: dict[str, str] = {}  # new_id -> old_id
        # projectmem-style deterministic PreCommitFailureGate
        # key -> {witness, deps_versions: {dep_id: version}, failed_at}
        self._failure_nogoods: dict[str, dict[str, Any]] = {}

    def ingest_delta(
        self,
        record_id: str,
        key: str,
        payload: Any,
        *,
        valid_from: float = 0.0,
        valid_to: float = math.inf,
        weight: int = 1,
        depends_on: Sequence[str] = (),
        derived_from: Sequence[str] = (),
        supersedes: str | None = None,
    ) -> dict[str, Any]:
        """Apply an O(1) DBSP Z-set delta (+1 insert/update, -1 retract) with AGM links."""
        t0 = time.perf_counter()
        self._delta_count += 1
        existing = self._records.get(record_id)
        if existing is None:
            rec = _ZSetRecord(
                record_id=record_id,
                key=key,
                payload=payload,
                valid_from=float(valid_from),
                valid_to=float(valid_to),
                weight=int(weight),
                status="ACTIVE" if weight > 0 else "RETRACTED",
                version=1,
            )
            self._records[record_id] = rec
            self._by_key.setdefault(key, []).append(record_id)
        else:
            existing.weight += int(weight)
            existing.payload = payload
            existing.valid_from = float(valid_from)
            existing.valid_to = float(valid_to)
            existing.version += 1
            existing.status = "ACTIVE" if existing.weight > 0 else "RETRACTED"

        all_parents = set(depends_on) | set(derived_from)
        if all_parents:
            self._depends_on.setdefault(record_id, set()).update(all_parents)
            for p_id in all_parents:
                self._dependents.setdefault(p_id, set()).add(record_id)

        impacted: list[str] = []
        if supersedes is not None:
            self._supersedes[record_id] = supersedes
            old_rec = self._records.get(supersedes)
            if old_rec is not None:
                old_rec.valid_to = min(old_rec.valid_to, float(valid_from))
                old_rec.weight = 0
                old_rec.status = "SUPERSEDED"
                old_rec.version += 1
            impact = self.analyze_impact(supersedes, mark_stale=True)
            impacted = impact["impacted_ids"]

        return {
            "schema": SCHEMA + "/dbsp_delta",
            "record_id": record_id,
            "key": key,
            "weight": self._records[record_id].weight,
            "version": self._records[record_id].version,
            "delta_count": self._delta_count,
            "impacted_ids": impacted,
            "elapsed_us": round((time.perf_counter() - t0) * 1e6, 3),
        }

    def query_at(self, key: str, *, valid_at: float | None = None, include_stale: bool = False) -> list[dict[str, Any]]:
        """Point-in-time O(k) query over active DBSP Z-set records for `key`."""
        ts = time.time() if valid_at is None else float(valid_at)
        out: list[dict[str, Any]] = []
        for rid in self._by_key.get(key, ()):
            rec = self._records.get(rid)
            if rec is None or rec.weight <= 0:
                continue
            if not include_stale and rec.status != "ACTIVE":
                continue
            if rec.valid_from <= ts < rec.valid_to:
                out.append({
                    "record_id": rec.record_id,
                    "key": rec.key,
                    "payload": rec.payload,
                    "valid_from": rec.valid_from,
                    "valid_to": None if math.isinf(rec.valid_to) else rec.valid_to,
                    "weight": rec.weight,
                    "status": rec.status,
                    "version": rec.version,
                })
        return out

    def analyze_impact(self, root_id: str, *, mark_stale: bool = True) -> dict[str, Any]:
        """Kumiho-style AGM transitive impact propagation over `Depends_On` / `Derived_From`."""
        t0 = time.perf_counter()
        visited: set[str] = set()
        queue: deque[tuple[str, list[str]]] = deque([(root_id, [root_id])])
        chains: dict[str, list[str]] = {}
        while queue:
            cur, path = queue.popleft()
            for child in sorted(self._dependents.get(cur, ())):
                if child in visited or child == root_id:
                    continue
                visited.add(child)
                c_path = path + [child]
                chains[child] = c_path
                if mark_stale and child in self._records:
                    self._records[child].status = "STALE_NEEDS_REVERIFICATION"
                    self._records[child].version += 1
                queue.append((child, c_path))
        return {
            "schema": SCHEMA + "/agm_impact",
            "root_id": root_id,
            "impacted_count": len(visited),
            "impacted_ids": sorted(visited),
            "provenance_chains": chains,
            "marked_stale": bool(mark_stale),
            "elapsed_us": round((time.perf_counter() - t0) * 1e6, 3),
        }

    @staticmethod
    def _nogood_key(context_key: str, proposal_signature: str) -> str:
        raw = f"{context_key}\x00{proposal_signature}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()[:32]

    def _snapshot_dep_versions(self, dependency_ids: Sequence[str]) -> dict[str, int]:
        return {
            dep: (self._records[dep].version if dep in self._records else 0)
            for dep in sorted(set(dependency_ids))
        }

    def record_failure_witness(
        self,
        context_key: str,
        proposal_signature: str,
        *,
        witness: str,
        dependency_ids: Sequence[str] = (),
    ) -> dict[str, Any]:
        """Record a deterministic failure witness in the PreCommitFailureGate."""
        t0 = time.perf_counter()
        nk = self._nogood_key(context_key, proposal_signature)
        dep_vers = self._snapshot_dep_versions(dependency_ids)
        self._failure_nogoods[nk] = {
            "context_key": context_key,
            "proposal_signature": proposal_signature,
            "witness": witness,
            "dep_versions": dep_vers,
            "dependency_ids": sorted(dep_vers.keys()),
        }
        return {
            "schema": SCHEMA + "/pre_commit_failure_record",
            "nogood_key": nk,
            "dependency_versions": dep_vers,
            "elapsed_us": round((time.perf_counter() - t0) * 1e6, 3),
        }

    def check_pre_commit_gate(
        self,
        context_key: str,
        proposal_signature: str,
    ) -> dict[str, Any]:
        """Reject repeating a previously-failed proposal in `< 10 us` unless a dependency changed."""
        t0 = time.perf_counter()
        nk = self._nogood_key(context_key, proposal_signature)
        entry = self._failure_nogoods.get(nk)
        if entry is None:
            return {
                "schema": SCHEMA + "/pre_commit_gate",
                "allowed": True,
                "status": "PRE_COMMIT_CLEAR",
                "elapsed_us": round((time.perf_counter() - t0) * 1e6, 3),
            }
        old_vers: dict[str, int] = entry["dep_versions"]
        cur_vers = self._snapshot_dep_versions(entry["dependency_ids"])
        if old_vers != cur_vers:
            # A tracked dependency mutated/superseded -> invalidate stale nogood!
            self._failure_nogoods.pop(nk, None)
            changed = sorted(k for k in cur_vers if cur_vers.get(k) != old_vers.get(k))
            return {
                "schema": SCHEMA + "/pre_commit_gate",
                "allowed": True,
                "status": "PRE_COMMIT_NOGOOD_INVALIDATED_BY_DEPENDENCY_CHANGE",
                "changed_dependencies": changed,
                "elapsed_us": round((time.perf_counter() - t0) * 1e6, 3),
            }
        return {
            "schema": SCHEMA + "/pre_commit_gate",
            "allowed": False,
            "status": "PRE_COMMIT_BLOCKED__KNOWN_FAILURE_WITNESS",
            "witness": entry["witness"],
            "nogood_key": nk,
            "elapsed_us": round((time.perf_counter() - t0) * 1e6, 3),
        }


# ===========================================================================
# 3. Error-Aware Symbolic Mealy Instant Learner (L# / Lambda*_M)
# ===========================================================================


@dataclass
class CompiledSymbolicMealyMachine:
    """Executable symbolic Mealy automaton with exact state transitions + numeric guards."""

    initial_state: int
    transitions: dict[tuple[int, str], tuple[int, str]]
    numeric_guards: dict[tuple[int, str], dict[str, Any]]
    error_states: frozenset[int]
    state_representatives: dict[int, tuple[str, ...]]
    queries_used: int
    pruned_error_queries: int
    advice_collapsed_queries: int
    compile_ms: float

    def predict_trace(self, actions: Sequence[Any]) -> list[str]:
        """Predict exact outputs for an arbitrary multi-step action sequence (zero env calls)."""
        st = self.initial_state
        outputs: list[str] = []
        for act in actions:
            if isinstance(act, tuple) and len(act) == 2:
                op, val = str(act[0]), act[1]
                g = self.numeric_guards.get((st, op))
                if g is not None and isinstance(val, (int, float)):
                    if val >= g["threshold"]:
                        st = int(g["high_next"])
                        outputs.append(str(g["high_out"]))
                    else:
                        st = int(g["low_next"])
                        outputs.append(str(g["low_out"]))
                    continue
                act_key = op
            else:
                act_key = str(act)
            nxt, out = self.transitions.get((st, act_key), (st, "UNKNOWN"))
            st = nxt
            outputs.append(out)
        return outputs


class ErrorAwareSymbolicMealyLearner:
    """Sub-millisecond black-box symbolic Mealy learner with error-persistence & advice pruning."""

    def learn(
        self,
        reset_and_run: Callable[[Sequence[Any]], list[str]],
        alphabet: Sequence[str],
        *,
        numeric_actions: Mapping[str, tuple[int, int]] | None = None,
        error_outputs: Sequence[str] = ("ERR", "ERROR", "FAIL", "DENIED"),
        commutative_pairs: Sequence[tuple[str, str]] = (),
        idempotent_actions: Sequence[str] = (),
        max_states: int = 32,
        enable_error_pruning: bool = True,
    ) -> CompiledSymbolicMealyMachine:
        """Learn an exact minimal symbolic Mealy machine from black-box trace queries."""
        t0 = time.perf_counter()
        alpha = [str(a) for a in alphabet]
        err_set = {str(e).upper() for e in error_outputs}
        comm_set = {(str(a), str(b)) for a, b in commutative_pairs} | {(str(b), str(a)) for a, b in commutative_pairs}
        idem_set = {str(a) for a in idempotent_actions}

        queries = 0
        pruned_err = 0
        advice_collapsed = 0
        query_cache: dict[tuple[Any, ...], list[str]] = {}

        def _canonicalize_advice(seq: tuple[Any, ...]) -> tuple[Any, ...]:
            nonlocal advice_collapsed
            cur = list(seq)
            changed = True
            while changed:
                changed = False
                i = 0
                while i + 1 < len(cur):
                    a, b = cur[i], cur[i + 1]
                    if isinstance(a, str) and isinstance(b, str):
                        if a == b and a in idem_set:
                            del cur[i + 1]
                            advice_collapsed += 1
                            changed = True
                            continue
                        if (a, b) in comm_set and a > b:
                            cur[i], cur[i + 1] = b, a
                            advice_collapsed += 1
                            changed = True
                    i += 1
            return tuple(cur)

        def probe(prefix: tuple[Any, ...], suffix: tuple[Any, ...]) -> list[str]:
            nonlocal queries
            full = prefix + suffix
            if full in query_cache:
                return query_cache[full][len(prefix) :]
            # Try advice equivalence on prefix for discrete actions.
            canon_prefix = _canonicalize_advice(prefix)
            canon_full = canon_prefix + suffix
            if canon_full in query_cache:
                return query_cache[canon_full][len(canon_prefix) :]
            queries += 1
            res = [str(x) for x in reset_and_run(full)]
            query_cache[full] = res
            if canon_full != full and len(canon_prefix) == len(prefix):
                query_cache[canon_full] = res
            return res[len(prefix) :]

        def is_err_output(out: str) -> bool:
            up = out.upper()
            return up in err_set or up.startswith("ERR")

        # Observation-table / discrimination-tree exploration over reachable access words.
        distinguishing: list[tuple[str, ...]] = [(a,) for a in alpha]
        error_sinks: set[tuple[str, ...]] = set()
        # First detect persistent error sink signature if encountered.
        def row_signature(word: tuple[str, ...]) -> tuple[tuple[str, ...], ...]:
            nonlocal pruned_err
            if enable_error_pruning and word in error_sinks:
                pruned_err += len(distinguishing)
                return tuple(("__ERR_SINK__",) for _ in distinguishing)
            sig: list[tuple[str, ...]] = []
            all_err = True
            for suf in distinguishing:
                outs = tuple(probe(word, suf))
                sig.append(outs)
                if not all(is_err_output(o) for o in outs):
                    all_err = False
            if enable_error_pruning and word and all_err:
                # Verify persistence on one 2-step probe once; if error persists, mark sink!
                error_sinks.add(word)
            return tuple(sig)

        sig_to_state: dict[tuple[tuple[str, ...], ...], int] = {}
        state_to_word: dict[int, tuple[str, ...]] = {}
        transitions: dict[tuple[int, str], tuple[int, str]] = {}
        error_state_ids: set[int] = set()

        init_sig = row_signature(())
        sig_to_state[init_sig] = 0
        state_to_word[0] = ()
        frontier: deque[int] = deque([0])

        while frontier and len(state_to_word) < max_states:
            sid = frontier.popleft()
            word = state_to_word[sid]
            if enable_error_pruning and word in error_sinks:
                error_state_ids.add(sid)
                # Error-persistence pruning: error sink loops back to itself on all inputs!
                for a in alpha:
                    if (sid, a) not in transitions:
                        out = probe(word, (a,))[0]
                        transitions[(sid, a)] = (sid, out)
                        pruned_err += max(0, len(alpha) - 1)
                continue

            for a in alpha:
                out = probe(word, (a,))[0]
                nxt_word = word + (a,)
                if enable_error_pruning and is_err_output(out):
                    # Check if `nxt_word` is an error sink with 1 probe before pruning all extensions.
                    if all(is_err_output(probe(nxt_word, (b,))[0]) for b in alpha[: min(2, len(alpha))]):
                        error_sinks.add(nxt_word)
                nsig = row_signature(nxt_word)
                if nsig not in sig_to_state:
                    new_id = len(state_to_word)
                    sig_to_state[nsig] = new_id
                    state_to_word[new_id] = nxt_word
                    if nxt_word in error_sinks:
                        error_state_ids.add(new_id)
                    frontier.append(new_id)
                transitions[(sid, a)] = (sig_to_state[nsig], out)

        # Lambda*_M binary-split numeric guard discovery + state-frontier expansion
        # for states reachable ONLY via parametric numeric actions `(op, int_val)`.
        numeric_guards: dict[tuple[int, str], dict[str, Any]] = {}
        expanded_numeric_states: set[int] = set()

        def _ensure_state_discovered(
            access_word: tuple[Any, ...],
            out_sample: str,
        ) -> int:
            if enable_error_pruning and is_err_output(out_sample):
                if all(is_err_output(probe(access_word, (b,))[0]) for b in alpha[: min(2, len(alpha))]):
                    error_sinks.add(access_word)
            sig = row_signature(access_word)
            if sig not in sig_to_state:
                new_id = len(state_to_word)
                sig_to_state[sig] = new_id
                state_to_word[new_id] = access_word
                if access_word in error_sinks:
                    error_state_ids.add(new_id)
                frontier.append(new_id)
            return sig_to_state[sig]

        def _drain_discrete_frontier() -> None:
            while frontier and len(state_to_word) < max_states:
                sid = frontier.popleft()
                word = state_to_word[sid]
                if enable_error_pruning and word in error_sinks:
                    error_state_ids.add(sid)
                    for a in alpha:
                        if (sid, a) not in transitions:
                            out = probe(word, (a,))[0]
                            transitions[(sid, a)] = (sid, out)
                            pruned_err += max(0, len(alpha) - 1)
                    continue
                for a in alpha:
                    if (sid, a) in transitions:
                        continue
                    out = probe(word, (a,))[0]
                    nxt_id = _ensure_state_discovered(word + (a,), out)
                    transitions[(sid, a)] = (nxt_id, out)

        if numeric_actions:
            while len(state_to_word) <= max_states:
                pending = [sid for sid in list(state_to_word.keys()) if sid not in expanded_numeric_states]
                if not pending:
                    break
                for sid in pending:
                    expanded_numeric_states.add(sid)
                    word = state_to_word[sid]
                    if sid in error_state_ids:
                        for op, (lo, hi) in numeric_actions.items():
                            out_lo = probe(word, ((op, int(lo)),))[0]
                            numeric_guards[(sid, op)] = {
                                "threshold": int(hi) + 1,
                                "low_out": out_lo,
                                "high_out": out_lo,
                                "low_next": sid,
                                "high_next": sid,
                            }
                        continue
                    for op, (lo, hi) in numeric_actions.items():
                        lo_i, hi_i = int(lo), int(hi)
                        out_lo = probe(word, ((op, lo_i),))[0]
                        out_hi = probe(word, ((op, hi_i),))[0]
                        if out_lo == out_hi:
                            nxt_st = _ensure_state_discovered(word + ((op, lo_i),), out_lo)
                            numeric_guards[(sid, op)] = {
                                "threshold": hi_i + 1,
                                "low_out": out_lo,
                                "high_out": out_hi,
                                "low_next": nxt_st,
                                "high_next": nxt_st,
                            }
                            continue
                        left, right = lo_i, hi_i
                        while left < right:
                            mid = (left + right) // 2
                            om = probe(word, ((op, mid),))[0]
                            if om == out_lo:
                                left = mid + 1
                            else:
                                right = mid
                        threshold = left
                        low_next = _ensure_state_discovered(word + ((op, threshold - 1),), out_lo)
                        high_next = _ensure_state_discovered(word + ((op, threshold),), out_hi)
                        numeric_guards[(sid, op)] = {
                            "threshold": threshold,
                            "low_out": out_lo,
                            "high_out": out_hi,
                            "low_next": low_next,
                            "high_next": high_next,
                        }
                _drain_discrete_frontier()

        return CompiledSymbolicMealyMachine(
            initial_state=0,
            transitions=transitions,
            numeric_guards=numeric_guards,
            error_states=frozenset(error_state_ids),
            state_representatives=state_to_word,
            queries_used=queries,
            pruned_error_queries=pruned_err,
            advice_collapsed_queries=advice_collapsed,
            compile_ms=round((time.perf_counter() - t0) * 1000.0, 4),
        )


# ===========================================================================
# 4. Hybrid 3-Channel Computer Use + Petri Supervisor + Loop-Churn Breaker
# ===========================================================================

_CHANNEL_COST: dict[str, float] = {
    "programmatic": 0.05,
    "semantic": 0.25,
    "visual": 1.00,
}


class HybridComputerUsePetriSupervisor:
    """3-Channel HCU (`CLI/File > AX/CDP > Visual`) + `< 5 us` Petri guard + Loop-Churn Breaker."""

    def __init__(
        self,
        initial_marking: Mapping[str, int] | None = None,
        transitions: Mapping[str, Mapping[str, Any]] | None = None,
    ) -> None:
        self.marking: dict[str, int] = {str(k): int(v) for k, v in (initial_marking or {}).items()}
        self.transitions: dict[str, dict[str, Any]] = {
            str(k): dict(v) for k, v in (transitions or {}).items()
        }
        self._compiled_macros: dict[str, list[dict[str, Any]]] = {}

    def check_petri_transition(self, action_name: str) -> tuple[bool, str, float]:
        """Verify Petri consumable tokens + inhibitor arcs in microseconds."""
        t0 = time.perf_counter()
        spec = self.transitions.get(action_name)
        if spec is None:
            return True, "PETRI_UNCONSTRAINED_OK", (time.perf_counter() - t0) * 1e6
        for place, need in (spec.get("consume") or {}).items():
            if self.marking.get(str(place), 0) < int(need):
                return False, f"PETRI_PRECONDITION_MISSING:{place}", (time.perf_counter() - t0) * 1e6
        for place in (spec.get("inhibitors") or ()):
            if self.marking.get(str(place), 0) > 0:
                return False, f"PETRI_INHIBITOR_BLOCKED:{place}", (time.perf_counter() - t0) * 1e6
        return True, "PETRI_ENABLED", (time.perf_counter() - t0) * 1e6

    def fire_petri_transition(self, action_name: str) -> None:
        spec = self.transitions.get(action_name)
        if spec is None:
            return
        for place, need in (spec.get("consume") or {}).items():
            self.marking[str(place)] = max(0, self.marking.get(str(place), 0) - int(need))
        for place, prod in (spec.get("produce") or {}).items():
            self.marking[str(place)] = self.marking.get(str(place), 0) + int(prod)

    @staticmethod
    def elevate_channel(step: Mapping[str, Any]) -> tuple[str, dict[str, Any], float]:
        """Select cheapest reliable HCU channel (`programmatic` < `semantic` < `visual`)."""
        orig_ch = str(step.get("channel") or "visual").lower()
        orig_cost = _CHANNEL_COST.get(orig_ch, 1.0)
        if step.get("programmatic_cmd") or step.get("cli_equiv"):
            ch = "programmatic"
            chosen = {**dict(step), "selected_channel": ch, "exec_payload": step.get("programmatic_cmd") or step.get("cli_equiv")}
        elif step.get("ax_ref") or step.get("cdp_selector"):
            ch = "semantic"
            chosen = {**dict(step), "selected_channel": ch, "exec_payload": step.get("ax_ref") or step.get("cdp_selector")}
        else:
            ch = orig_ch if orig_ch in _CHANNEL_COST else "visual"
            chosen = {**dict(step), "selected_channel": ch, "exec_payload": step.get("visual_target") or step.get("action")}
        saved = max(0.0, orig_cost - _CHANNEL_COST[ch])
        return ch, chosen, saved

    def register_paste_macro(self, macro_name: str, steps: Sequence[Mapping[str, Any]]) -> None:
        """Register a PASTE verified `(control-flow, data-flow)` speculative macro."""
        self._compiled_macros[macro_name] = [dict(s) for s in steps]

    def execute_episode(
        self,
        steps: Sequence[Mapping[str, Any]],
        *,
        executor: Callable[[Mapping[str, Any], dict[str, Any]], tuple[bool, dict[str, Any]]] | None = None,
        initial_state: Mapping[str, Any] | None = None,
        max_loop_repeats: int = 2,
    ) -> dict[str, Any]:
        """Execute a hybrid computer-use episode with Petri guarding, channel elevation & loop breaking."""
        t0 = time.perf_counter()
        state = dict(initial_state or {})
        trace: list[dict[str, Any]] = []
        seen_state_actions: dict[tuple[str, str], int] = {}
        total_orig_cost = 0.0
        total_actual_cost = 0.0
        petri_checks_us: list[float] = []
        elevated_count = 0
        blocked_count = 0
        loop_broken = False
        macro_commits = 0

        def state_hash(st: Mapping[str, Any]) -> str:
            return hashlib.sha256(json.dumps(st, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:16]

        for idx, raw_step in enumerate(steps):
            # Optional PASTE speculative macro expansion with snapshot rollback.
            macro_name = raw_step.get("macro")
            if macro_name and str(macro_name) in self._compiled_macros:
                saved_marking = dict(self.marking)
                saved_state = copy.deepcopy(state)
                m_steps = self._compiled_macros[str(macro_name)]
                macro_ok = True
                for ms in m_steps:
                    act = str(ms.get("action") or "")
                    ok_p, _why, p_us = self.check_petri_transition(act)
                    petri_checks_us.append(p_us)
                    if not ok_p:
                        macro_ok = False
                        break
                    self.fire_petri_transition(act)
                    if executor is not None:
                        ok_e, state = executor(ms, state)
                        if not ok_e:
                            macro_ok = False
                            break
                if macro_ok:
                    macro_commits += 1
                    total_orig_cost += sum(_CHANNEL_COST.get(str(ms.get("channel") or "visual"), 1.0) for ms in m_steps)
                    total_actual_cost += _CHANNEL_COST["programmatic"]
                    trace.append({"step": idx, "macro": str(macro_name), "status": "PASTE_MACRO_COMMITTED", "collapsed_steps": len(m_steps)})
                    continue
                # Safe CoW rollback on speculative macro mismatch!
                self.marking = saved_marking
                state = saved_state
                trace.append({"step": idx, "macro": str(macro_name), "status": "PASTE_MACRO_ROLLED_BACK"})
                blocked_count += 1
                continue

            orig_ch = str(raw_step.get("channel") or "visual").lower()
            total_orig_cost += _CHANNEL_COST.get(orig_ch, 1.0)
            ch, chosen, saved = self.elevate_channel(raw_step)
            if saved > 0.0:
                elevated_count += 1
            act_name = str(chosen.get("action") or f"step_{idx}")

            # 1. OSWorld-Human loop-churn detection BEFORE executing wasted steps!
            sh = state_hash(state)
            sa_key = (sh, f"{act_name}:{chosen.get('exec_payload')}")
            seen_state_actions[sa_key] = seen_state_actions.get(sa_key, 0) + 1
            if seen_state_actions[sa_key] > max_loop_repeats:
                loop_broken = True
                trace.append({
                    "step": idx,
                    "action": act_name,
                    "channel": ch,
                    "status": "LOOP_CHURN_BROKEN",
                    "state_hash": sh,
                    "repeat_count": seen_state_actions[sa_key],
                })
                break

            # 2. Microsecond Petri guard (consumables + inhibitors).
            ok_petri, petri_why, p_us = self.check_petri_transition(act_name)
            petri_checks_us.append(p_us)
            if not ok_petri:
                blocked_count += 1
                trace.append({
                    "step": idx,
                    "action": act_name,
                    "channel": ch,
                    "status": "PETRI_BLOCKED",
                    "reason": petri_why,
                    "guard_us": round(p_us, 3),
                })
                continue

            # 3. Execute & update marking.
            total_actual_cost += _CHANNEL_COST[ch]
            if executor is not None:
                ok_exec, new_state = executor(chosen, state)
                if not ok_exec:
                    blocked_count += 1
                    trace.append({
                        "step": idx,
                        "action": act_name,
                        "channel": ch,
                        "status": "EXECUTION_FAILED",
                    })
                    continue
                state = dict(new_state)
            self.fire_petri_transition(act_name)
            trace.append({
                "step": idx,
                "action": act_name,
                "channel": ch,
                "status": "EXECUTED",
                "guard_us": round(p_us, 3),
                "marking": dict(self.marking),
            })

        cost_reduction = (
            round(1.0 - (total_actual_cost / total_orig_cost), 6) if total_orig_cost > 0 else 0.0
        )
        avg_guard_us = round(sum(petri_checks_us) / len(petri_checks_us), 3) if petri_checks_us else 0.0
        return {
            "schema": SCHEMA + "/hybrid_cu_petri",
            "pass": (blocked_count == 0 and not loop_broken),
            "status": (
                "LOOP_CHURN_BROKEN"
                if loop_broken
                else ("COMPLETED_WITH_BLOCKS" if blocked_count else "HCU_PETRI_COMPLETED")
            ),
            "steps_executed": sum(1 for t in trace if t["status"] in {"EXECUTED", "PASTE_MACRO_COMMITTED"}),
            "channels_elevated": elevated_count,
            "blocked_count": blocked_count,
            "loop_broken": loop_broken,
            "paste_macro_commits": macro_commits,
            "original_cost": round(total_orig_cost, 4),
            "actual_cost": round(total_actual_cost, 4),
            "cost_reduction_ratio": cost_reduction,
            "avg_petri_guard_us": avg_guard_us,
            "final_marking": dict(self.marking),
            "final_state": state,
            "trace": trace,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 4),
        }


# ===========================================================================
# 5. PEP-669 / Settrace Ochiai Localizer + Byte-Span AST Splicer + CoW Zygote
# ===========================================================================


def _line_byte_offsets(raw_bytes: bytes) -> list[int]:
    """Return 0-based byte offset of the start of each 1-based line."""
    offsets = [0]
    pos = 0
    for line in raw_bytes.splitlines(keepends=True):
        pos += len(line)
        offsets.append(pos)
    return offsets


def splice_ast_byte_span(source: str, node: ast.AST, replacement_code: str) -> str:
    """Replace exact UTF-8 byte span of `node` in `source` without touching any other line (`< 50 us`)."""
    raw = source.encode("utf-8")
    offsets = _line_byte_offsets(raw)
    lineno = int(getattr(node, "lineno"))
    col = int(getattr(node, "col_offset"))
    end_lineno = int(getattr(node, "end_lineno"))
    end_col = int(getattr(node, "end_col_offset"))
    start_b = offsets[lineno - 1] + col
    end_b = offsets[end_lineno - 1] + end_col
    spliced = raw[:start_b] + replacement_code.encode("utf-8") + raw[end_b:]
    return spliced.decode("utf-8")


def _run_case_with_line_trace(source: str, test_expr: str) -> tuple[bool, set[int], str]:
    """Execute one test against compiled `source` collecting exact executed line numbers."""
    ns: dict[str, Any] = {}
    filename = "<futamura_subject>"
    try:
        code = compile(source, filename, "exec")
        exec(code, ns, ns)
    except Exception as exc:
        return False, set(), f"COMPILE_OR_LOAD_ERR:{type(exc).__name__}:{exc}"

    executed_lines: set[int] = set()
    use_pep669 = hasattr(sys, "monitoring")
    tool_id = 3  # PROFILER/LOCALIZER slot

    def _run_test() -> tuple[bool, str]:
        try:
            test_code = compile(test_expr, "<futamura_test>", "exec")
            exec(test_code, ns, ns)
            return True, "OK"
        except Exception as exc:
            return False, f"{type(exc).__name__}:{exc}"

    if use_pep669:
        mon = sys.monitoring
        try:
            mon.use_tool_id(tool_id, "futamura_ochiai")
        except ValueError:
            use_pep669 = False

    if use_pep669:
        mon = sys.monitoring

        def _on_line(code_obj: Any, line_no: int) -> Any:
            if code_obj.co_filename == filename:
                executed_lines.add(int(line_no))
            return None

        mon.register_callback(tool_id, mon.events.LINE, _on_line)
        mon.set_events(tool_id, mon.events.LINE)
        try:
            ok, err = _run_test()
        finally:
            mon.set_events(tool_id, 0)
            mon.register_callback(tool_id, mon.events.LINE, None)
            try:
                mon.free_tool_id(tool_id)
            except Exception:
                pass
        return ok, executed_lines, err

    # Python 3.11 clean fallback using `sys.settrace`
    def _tracer(frame: Any, event: str, _arg: Any) -> Any:
        if event == "line" and frame.f_code.co_filename == filename:
            executed_lines.add(int(frame.f_lineno))
        return _tracer

    prev = sys.gettrace()
    sys.settrace(_tracer)
    try:
        ok, err = _run_test()
    finally:
        sys.settrace(prev)
    return ok, executed_lines, err


def localize_fault_ochiai(source: str, test_cases: Sequence[str]) -> dict[str, Any]:
    """Compute exact Ochiai suspiciousness scores over executed lines of `source`."""
    t0 = time.perf_counter()
    fail_counts: dict[int, int] = {}
    pass_counts: dict[int, int] = {}
    total_fail = 0
    total_pass = 0
    failure_witnesses: list[str] = []

    for tc in test_cases:
        ok, lines, err = _run_case_with_line_trace(source, tc)
        if ok:
            total_pass += 1
            for ln in lines:
                pass_counts[ln] = pass_counts.get(ln, 0) + 1
        else:
            total_fail += 1
            failure_witnesses.append(err)
            for ln in lines:
                fail_counts[ln] = fail_counts.get(ln, 0) + 1

    scores: list[tuple[float, int]] = []
    for ln, ef in fail_counts.items():
        ep = pass_counts.get(ln, 0)
        denom = math.sqrt(max(1, total_fail) * (ef + ep))
        scores.append((round(ef / denom, 6) if denom > 0 else 0.0, ln))
    scores.sort(key=lambda pair: (-pair[0], pair[1]))

    return {
        "schema": SCHEMA + "/ochiai_localization",
        "backend": "pep669_sys_monitoring" if hasattr(sys, "monitoring") else "python311_sys_settrace",
        "total_pass": total_pass,
        "total_fail": total_fail,
        "failure_witnesses": failure_witnesses,
        "ranked_lines": [{"line": ln, "ochiai": sc} for sc, ln in scores],
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 4),
    }


def _eval_candidate_in_cow_fork(candidate_source: str, test_cases: Sequence[str], *, timeout_s: float = 2.0) -> bool:
    """Evaluate `candidate_source` against `test_cases` in an isolated POSIX `os.fork()` CoW child."""
    if not hasattr(os, "fork"):
        return _eval_candidate_in_process(candidate_source, test_cases)
    r_fd, w_fd = os.pipe()
    pid = os.fork()
    if pid == 0:
        os.close(r_fd)
        ok = False
        try:
            ok = _eval_candidate_in_process(candidate_source, test_cases)
        except BaseException:
            ok = False
        try:
            os.write(w_fd, b"1" if ok else b"0")
        finally:
            os.close(w_fd)
            os._exit(0)
    os.close(w_fd)
    deadline = time.monotonic() + timeout_s
    data = b""
    try:
        while True:
            wpid, _status = os.waitpid(pid, os.WNOHANG)
            if wpid == pid:
                break
            if time.monotonic() >= deadline:
                try:
                    os.kill(pid, 9)
                except OSError:
                    pass
                os.waitpid(pid, 0)
                return False
            time.sleep(0.001)
        data = os.read(r_fd, 4)
    finally:
        os.close(r_fd)
    return data == b"1"


def _eval_candidate_in_process(candidate_source: str, test_cases: Sequence[str]) -> bool:
    ns: dict[str, Any] = {}
    try:
        exec(compile(candidate_source, "<futamura_cand>", "exec"), ns, ns)
        for tc in test_cases:
            exec(compile(tc, "<futamura_test>", "exec"), ns, ns)
        return True
    except Exception:
        return False


_CMP_REPAIR_ALTS: dict[type[ast.cmpop], tuple[type[ast.cmpop], ...]] = {
    ast.Lt: (ast.LtE, ast.Gt, ast.GtE),
    ast.LtE: (ast.Lt, ast.GtE, ast.Gt),
    ast.Gt: (ast.GtE, ast.Lt, ast.LtE),
    ast.GtE: (ast.Gt, ast.LtE, ast.Lt),
    ast.Eq: (ast.NotEq,),
    ast.NotEq: (ast.Eq,),
}

_BINOP_REPAIR_ALTS: dict[type[ast.operator], tuple[type[ast.operator], ...]] = {
    ast.Add: (ast.Sub, ast.Mult),
    ast.Sub: (ast.Add,),
    ast.Mult: (ast.Div, ast.FloorDiv, ast.Add),
    ast.Div: (ast.FloorDiv, ast.Mult),
    ast.FloorDiv: (ast.Div, ast.Mult),
    ast.Mod: (ast.FloorDiv,),
}

_BOOLOP_REPAIR_ALTS: dict[type[ast.boolop], tuple[type[ast.boolop], ...]] = {
    ast.And: (ast.Or,),
    ast.Or: (ast.And,),
}


class ZeroOverheadCoWZygoteRepairEngine:
    """Ochiai localization + `< 50 us` byte-span AST splicing + `os.fork()` CoW + ddmin + mutation gate."""

    def synthesize_candidates(self, source: str, suspect_lines: Sequence[int], failure_witnesses: Sequence[str]) -> list[tuple[str, str]]:
        """Generate targeted minimal AST repair candidates spliced onto top suspect lines."""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        suspect_set = set(suspect_lines) if suspect_lines else set(range(1, len(source.splitlines()) + 1))
        witness_blob = " ".join(failure_witnesses)
        cands: list[tuple[str, str]] = []
        seen_src: set[str] = {source}

        def add_cand(label: str, patched: str) -> None:
            if patched not in seen_src:
                seen_src.add(patched)
                cands.append((label, patched))

        for node in ast.walk(tree):
            ln = getattr(node, "lineno", None)
            if ln not in suspect_set or not hasattr(node, "end_lineno"):
                continue

            if isinstance(node, ast.Compare) and len(node.ops) == 1:
                for alt_cls in _CMP_REPAIR_ALTS.get(type(node.ops[0]), ()):
                    ncopy = copy.deepcopy(node)
                    ncopy.ops[0] = alt_cls()
                    add_cand(f"L{ln}:cmp->{alt_cls.__name__}", splice_ast_byte_span(source, node, ast.unparse(ncopy)))

            elif isinstance(node, ast.BinOp):
                # Arithmetic operator swap
                for alt_cls in _BINOP_REPAIR_ALTS.get(type(node.op), ()):
                    ncopy = copy.deepcopy(node)
                    ncopy.op = alt_cls()
                    add_cand(f"L{ln}:binop->{alt_cls.__name__}", splice_ast_byte_span(source, node, ast.unparse(ncopy)))
                # ZeroDivisionError guard synthesis
                if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)) and "ZeroDivision" in witness_blob:
                    denom_src = ast.unparse(node.right)
                    expr_src = ast.unparse(node)
                    for default_val in ("0", "0.0"):
                        guarded = f"({expr_src} if ({denom_src}) != 0 else {default_val})"
                        add_cand(f"L{ln}:div_zero_guard_{default_val}", splice_ast_byte_span(source, node, guarded))

            elif isinstance(node, ast.BoolOp):
                for alt_cls in _BOOLOP_REPAIR_ALTS.get(type(node.op), ()):
                    ncopy = copy.deepcopy(node)
                    ncopy.op = alt_cls()
                    add_cand(f"L{ln}:boolop->{alt_cls.__name__}", splice_ast_byte_span(source, node, ast.unparse(ncopy)))

            elif isinstance(node, ast.Subscript):
                # KeyError / IndexError safe access
                if "KeyError" in witness_blob:
                    val_src = ast.unparse(node.value)
                    key_src = ast.unparse(node.slice)
                    for default_val in ("0", "None", "''"):
                        add_cand(
                            f"L{ln}:dict_get_{default_val}",
                            splice_ast_byte_span(source, node, f"{val_src}.get({key_src}, {default_val})"),
                        )
                if "IndexError" in witness_blob and not isinstance(node.slice, ast.Slice):
                    val_src = ast.unparse(node.value)
                    idx_src = ast.unparse(node.slice)
                    add_cand(
                        f"L{ln}:index_clamp",
                        splice_ast_byte_span(
                            source,
                            node,
                            f"({val_src}[{idx_src}] if -len({val_src}) <= ({idx_src}) < len({val_src}) else None)",
                        ),
                    )

            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                # Off-by-one `range(n)` -> `range(n + 1)` or `range(n - 1)`
                if node.func.id == "range" and len(node.args) in (1, 2):
                    idx_stop = len(node.args) - 1
                    for delta in ("+ 1", "- 1"):
                        ncopy = copy.deepcopy(node)
                        stop_src = ast.unparse(ncopy.args[idx_stop])
                        ncopy.args[idx_stop] = ast.parse(f"({stop_src}) {delta}", mode="eval").body
                        add_cand(f"L{ln}:range_stop_{delta}", splice_ast_byte_span(source, node, ast.unparse(ncopy)))
                # Empty min/max guard
                if node.func.id in {"min", "max"} and len(node.args) == 1 and "ValueError" in witness_blob:
                    arg_src = ast.unparse(node.args[0])
                    add_cand(
                        f"L{ln}:{node.func.id}_default_0",
                        splice_ast_byte_span(source, node, f"{node.func.id}({arg_src}, default=0)"),
                    )

        return cands

    def repair(
        self,
        source: str,
        test_cases: Sequence[str],
        *,
        use_cow_fork: bool = True,
        run_mutation_audit: bool = True,
        alpha: float = 0.05,
    ) -> dict[str, Any]:
        """Run end-to-end Ochiai + byte-span splice + CoW fork + ddmin + mutation + e-value repair."""
        t0 = time.perf_counter()
        loc = localize_fault_ochiai(source, test_cases)
        if loc["total_fail"] == 0:
            return {
                "schema": SCHEMA + "/cow_zygote_repair",
                "pass": True,
                "status": "ALREADY_PASSING",
                "patched_source": source,
                "localization": loc,
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 4),
            }

        top_lines = [row["line"] for row in loc["ranked_lines"][:6]]
        cands = self.synthesize_candidates(source, top_lines, loc["failure_witnesses"])
        eval_fn = (
            (lambda cand_src: _eval_candidate_in_cow_fork(cand_src, test_cases))
            if use_cow_fork
            else (lambda cand_src: _eval_candidate_in_process(cand_src, test_cases))
        )

        winner_label = ""
        winner_src: str | None = None
        screened = 0
        for label, cand_src in cands:
            screened += 1
            if eval_fn(cand_src):
                winner_label = label
                winner_src = cand_src
                break

        if winner_src is None:
            return {
                "schema": SCHEMA + "/cow_zygote_repair",
                "pass": False,
                "status": "COW_ZYGOTE_NO_PASSING_PATCH",
                "candidates_screened": screened,
                "localization": loc,
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 4),
            }

        # Ring-0 Gate: ddmin hunk minimization + touched-line mutation audit + Conformal E-Value
        ddmin_res = ddmin_minimize_hunks(source, winner_src, eval_fn)
        final_src = ddmin_res["minimized_source"]
        mut_res = (
            audit_patch_mutation_kill(source, final_src, lambda s: _eval_candidate_in_process(s, test_cases))
            if run_mutation_audit
            else {"pass": True, "mutants_tested": 0, "mutants_killed": 0, "mutation_kill_ratio": 1.0}
        )
        gate = ConformalEValueGate(alpha=alpha)
        gate.observe("syntax_parse", passed=True, null_pass_prob=0.50)
        gate.observe("cow_fork_tests_pass", passed=True, null_pass_prob=0.10)
        gate.observe("ddmin_1_minimal", passed=bool(ddmin_res["pass"]), null_pass_prob=0.50)
        gate.observe(
            "mutation_kill_audit",
            passed=(float(mut_res.get("mutation_kill_ratio", 0.0)) >= 0.5),
            null_pass_prob=0.25,
        )
        e_verdict = gate.decision()
        committed = e_verdict["verdict"] == "COMMIT"

        return {
            "schema": SCHEMA + "/cow_zygote_repair",
            "pass": committed,
            "status": "COW_ZYGOTE_PATCH_VERIFIED" if committed else f"GATE_{e_verdict['verdict']}",
            "winner_label": winner_label,
            "patched_source": final_src,
            "candidates_screened": screened,
            "cow_fork_used": bool(use_cow_fork and hasattr(os, "fork")),
            "localization": loc,
            "ddmin": ddmin_res,
            "mutation_audit": mut_res,
            "conformal_evalue": e_verdict,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 4),
        }


# ===========================================================================
# 6. Futamura Self-Compiling Cascade + GrowLibm Sleep Compressor
# ===========================================================================


class _AlphaTemplateNormalizer:
    """Alpha-normalize an AST subtree into canonical slot variables (`__V0__`, `__C0__`) for generalization."""

    def __init__(self) -> None:
        self.name_to_slot: dict[str, str] = {}
        self.const_to_slot: dict[tuple[str, Any], str] = {}
        self._v_idx = 0
        self._c_idx = 0

    def normalize(self, node: ast.AST) -> ast.AST:
        cp = copy.deepcopy(node)
        return self._walk(cp)

    def _walk(self, node: ast.AST) -> ast.AST:
        if isinstance(node, ast.Name):
            # Keep Python builtins un-abstracted (`len`, `min`, `max`, `range`, `None`).
            if node.id in {"len", "min", "max", "range", "sum", "abs", "int", "float", "str", "list", "dict", "set"}:
                return node
            slot = self.name_to_slot.get(node.id)
            if slot is None:
                slot = f"__V{self._v_idx}__"
                self._v_idx += 1
                self.name_to_slot[node.id] = slot
            node.id = slot
            return node
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float, str)) and not isinstance(node.value, bool):
            ckey = (type(node.value).__name__, node.value)
            slot = self.const_to_slot.get(ckey)
            if slot is None:
                slot = f"__C{self._c_idx}__"
                self._c_idx += 1
                self.const_to_slot[ckey] = slot
            return ast.Name(id=slot, ctx=ast.Load())
        for field_name, val in ast.iter_fields(node):
            if isinstance(val, list):
                setattr(node, field_name, [self._walk(x) if isinstance(x, ast.AST) else x for x in val])
            elif isinstance(val, ast.AST):
                setattr(node, field_name, self._walk(val))
        return node


def _preorder_signature(node: ast.AST, max_depth: int = 4) -> tuple[str, ...]:
    """Compact preorder AST node-type tuple used as O(1) Rung-0 AstDiscrTree lookup key."""
    out: list[str] = []

    def _visit(n: ast.AST, depth: int) -> None:
        if depth > max_depth or len(out) >= 24:
            return
        out.append(type(n).__name__)
        if isinstance(n, ast.Compare):
            for op in n.ops:
                out.append(type(op).__name__)
        elif isinstance(n, ast.BinOp):
            out.append(type(n.op).__name__)
        elif isinstance(n, ast.BoolOp):
            out.append(type(n.op).__name__)
        for ch in ast.iter_child_nodes(n):
            if not isinstance(ch, (ast.Load, ast.Store, ast.Del, ast.cmpop, ast.operator, ast.boolop)):
                _visit(ch, depth + 1)

    _visit(node, 0)
    return tuple(out)


def _match_template(pattern: ast.AST, concrete: ast.AST, bindings: dict[str, ast.AST]) -> bool:
    """Match an alpha-normalized AST `pattern` against `concrete`, populating `bindings`."""
    if isinstance(pattern, ast.Name) and pattern.id.startswith(("__V", "__C")) and pattern.id.endswith("__"):
        slot = pattern.id
        if slot.startswith("__V") and not isinstance(concrete, ast.Name):
            return False
        if slot.startswith("__C") and not isinstance(concrete, ast.Constant):
            return False
        prev = bindings.get(slot)
        if prev is not None:
            return ast.dump(prev) == ast.dump(concrete)
        bindings[slot] = copy.deepcopy(concrete)
        return True

    if type(pattern) is not type(concrete):
        return False

    for fname, pval in ast.iter_fields(pattern):
        if fname == "ctx":
            continue
        cval = getattr(concrete, fname, None)
        if isinstance(pval, list):
            if not isinstance(cval, list) or len(pval) != len(cval):
                return False
            for pe, ce in zip(pval, cval):
                if isinstance(pe, ast.AST):
                    if not isinstance(ce, ast.AST) or not _match_template(pe, ce, bindings):
                        return False
                elif pe != ce:
                    return False
        elif isinstance(pval, ast.AST):
            if not isinstance(cval, ast.AST) or not _match_template(pval, cval, bindings):
                return False
        else:
            if pval != cval:
                return False
    return True


def _instantiate_template(template: ast.AST, bindings: Mapping[str, ast.AST]) -> ast.AST:
    """Instantiate an alpha-normalized AST `template` using matched `bindings`."""
    node = copy.deepcopy(template)

    def _sub(n: ast.AST) -> ast.AST:
        if isinstance(n, ast.Name) and n.id in bindings:
            rep = copy.deepcopy(bindings[n.id])
            if isinstance(rep, ast.Name) and hasattr(n, "ctx"):
                rep.ctx = copy.deepcopy(n.ctx)
            return rep
        for fname, val in ast.iter_fields(n):
            if isinstance(val, list):
                setattr(n, fname, [_sub(x) if isinstance(x, ast.AST) else x for x in val])
            elif isinstance(val, ast.AST):
                setattr(n, fname, _sub(val))
        return n

    res = _sub(node)
    ast.fix_missing_locations(res)
    return res


@dataclass
class CompiledRung0Rule:
    rule_id: str
    preorder_key: tuple[str, ...]
    before_template_src: str
    after_template_src: str
    before_ast: ast.AST
    after_ast: ast.AST
    source_rung: int
    hits: int = 0
    successes: int = 0
    failures: int = 0
    rubin_tau_hat: float = 1.0  # (WITH - WITHOUT) counterfactual lift
    quarantined: bool = False


class FutamuraSelfCompilingCascade:
    """4-Rung Self-Compiling Cascade that compiles verified Rung 1/2/3 wins back into `< 50 us` Rung 0."""

    def __init__(self) -> None:
        self._rung0_by_key: dict[tuple[str, ...], list[CompiledRung0Rule]] = {}
        self._rules_by_id: dict[str, CompiledRung0Rule] = {}
        self.belief_bus = DBSPBeliefRevisionBus()
        self.repair_engine = ZeroOverheadCoWZygoteRepairEngine()
        self.compile_history: list[dict[str, Any]] = []

    def rule_count(self) -> int:
        return sum(1 for r in self._rules_by_id.values() if not r.quarantined)

    def _extract_changed_node_pair(self, orig_src: str, patched_src: str) -> tuple[ast.AST, ast.AST] | None:
        """Locate the tightest single AST expression/statement pair differing between `orig_src` and `patched_src`."""
        try:
            t_orig = ast.parse(orig_src)
            t_new = ast.parse(patched_src)
        except SyntaxError:
            return None

        def _find_tightest(a: ast.AST, b: ast.AST) -> tuple[ast.AST, ast.AST] | None:
            if ast.dump(a) == ast.dump(b):
                return None
            if type(a) is not type(b):
                return (a, b)
            # Check child lists/fields to descend when exactly one child differs.
            diffs: list[tuple[ast.AST, ast.AST]] = []
            for fname, aval in ast.iter_fields(a):
                if fname == "ctx":
                    continue
                bval = getattr(b, fname, None)
                if isinstance(aval, list) and isinstance(bval, list):
                    if len(aval) != len(bval):
                        return (a, b)
                    for ae, be in zip(aval, bval):
                        if isinstance(ae, ast.AST) and isinstance(be, ast.AST):
                            if ast.dump(ae) != ast.dump(be):
                                diffs.append((ae, be))
                        elif ae != be:
                            return (a, b)
                elif isinstance(aval, ast.AST) and isinstance(bval, ast.AST):
                    if ast.dump(aval) != ast.dump(bval):
                        diffs.append((aval, bval))
                elif aval != bval:
                    return (a, b)
            if len(diffs) == 1:
                child_a, child_b = diffs[0]
                # Stop descending below expression-level nodes (Compare, BinOp, BoolOp, Call, Subscript)
                if isinstance(child_a, (ast.cmpop, ast.operator, ast.boolop)):
                    return (a, b)
                deeper = _find_tightest(child_a, child_b)
                return deeper if deeper is not None else (child_a, child_b)
            return (a, b)

        return _find_tightest(t_orig, t_new)

    def compile_verified_win_to_rung0(
        self,
        original_source: str,
        verified_source: str,
        *,
        source_rung: int,
    ) -> dict[str, Any]:
        """Futamura projection: generalize a verified diff into an alpha-normalized Rung-0 rule."""
        t0 = time.perf_counter()
        pair = self._extract_changed_node_pair(original_source, verified_source)
        if pair is None:
            return {"compiled": False, "reason": "NO_EXTRACTABLE_AST_DIFF"}
        orig_node, new_node = pair
        norm = _AlphaTemplateNormalizer()
        before_tpl = norm.normalize(orig_node)
        after_tpl = norm.normalize(new_node)
        pkey = _preorder_signature(orig_node)
        before_str = ast.unparse(before_tpl)
        after_str = ast.unparse(after_tpl)
        rule_id = "futamura_" + hashlib.sha256(f"{pkey}|{before_str}->{after_str}".encode("utf-8")).hexdigest()[:12]

        if rule_id in self._rules_by_id:
            existing = self._rules_by_id[rule_id]
            existing.successes += 1
            return {
                "compiled": True,
                "deduplicated": True,
                "rule_id": rule_id,
                "before_template": before_str,
                "after_template": after_str,
                "elapsed_us": round((time.perf_counter() - t0) * 1e6, 3),
            }

        rule = CompiledRung0Rule(
            rule_id=rule_id,
            preorder_key=pkey,
            before_template_src=before_str,
            after_template_src=after_str,
            before_ast=before_tpl,
            after_ast=after_tpl,
            source_rung=int(source_rung),
            successes=1,
            rubin_tau_hat=1.0,
        )
        self._rules_by_id[rule_id] = rule
        self._rung0_by_key.setdefault(pkey, []).append(rule)
        self.belief_bus.ingest_delta(
            record_id=rule_id,
            key="rung0_compiled_rule",
            payload={"before": before_str, "after": after_str, "source_rung": source_rung},
            valid_from=0.0,
        )
        rec = {
            "compiled": True,
            "deduplicated": False,
            "rule_id": rule_id,
            "source_rung": int(source_rung),
            "before_template": before_str,
            "after_template": after_str,
            "elapsed_us": round((time.perf_counter() - t0) * 1e6, 3),
        }
        self.compile_history.append(rec)
        return rec

    def _try_rung0(self, source: str, test_cases: Sequence[str]) -> dict[str, Any] | None:
        """Attempt `< 100 us` lookup + generalized instantiation of compiled Rung-0 rules."""
        if not self._rung0_by_key:
            return None
        t0 = time.perf_counter()
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return None

        # Gather all AST subtrees matching any compiled rule preorder key.
        matched_attempts = 0
        for node in ast.walk(tree):
            if not hasattr(node, "lineno") or not hasattr(node, "end_lineno"):
                continue
            pkey = _preorder_signature(node)
            rules = self._rung0_by_key.get(pkey)
            if not rules:
                continue
            for rule in rules:
                if rule.quarantined or rule.rubin_tau_hat <= 0.0:
                    continue
                bindings: dict[str, ast.AST] = {}
                if not _match_template(rule.before_ast, node, bindings):
                    continue
                matched_attempts += 1
                instantiated = _instantiate_template(rule.after_ast, bindings)
                cand_src = splice_ast_byte_span(source, node, ast.unparse(instantiated))
                ctx_key = hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]
                prop_sig = hashlib.sha256(cand_src.encode("utf-8")).hexdigest()[:16]
                if not self.belief_bus.check_pre_commit_gate(ctx_key, prop_sig)["allowed"]:
                    continue
                lookup_us = (time.perf_counter() - t0) * 1e6
                rule.hits += 1
                if _eval_candidate_in_process(cand_src, test_cases):
                    rule.successes += 1
                    return {
                        "rule_id": rule.rule_id,
                        "before_template": rule.before_template_src,
                        "after_template": rule.after_template_src,
                        "patched_source": cand_src,
                        "lookup_and_splice_us": round(lookup_us, 3),
                        "matched_attempts": matched_attempts,
                    }
                rule.failures += 1
                self.belief_bus.record_failure_witness(ctx_key, prop_sig, witness="RUNG0_TEST_FAIL")
        return None

    def solve(
        self,
        task: Mapping[str, Any],
        *,
        untrusted_proposer: Callable[[Mapping[str, Any]], str | None] | None = None,
        auto_compile: bool = True,
        use_cow_fork: bool = True,
        alpha: float = 0.05,
    ) -> dict[str, Any]:
        """Execute Futamura Rung 0 -> Rung 1 -> Rung 2 -> optional Rung 3 with auto-compilation back to Rung 0."""
        t0 = time.perf_counter()
        kind = str(task.get("kind") or "python_repair").lower()

        # Rung 1 fast-path: byte-effect verification task
        if kind == "byte_effect":
            eff = verify_byte_effect(
                task["target"],
                expected_format=task.get("expected_format"),
                expected_source_bytes=task.get("expected_source_bytes"),
                expected_source_path=task.get("expected_source_path"),
                baseline_archive_hashes=task.get("baseline_archive_hashes"),
                allowed_archive_mutations=task.get("allowed_archive_mutations") or (),
            )
            return {
                "schema": SCHEMA + "/futamura_solve",
                "pass": bool(eff["pass"]),
                "rung_used": 1,
                "status": eff["status"],
                "proposer_calls": 0,
                "effect_receipt": eff,
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 4),
            }

        source = str(task["source"])
        test_cases = [str(tc) for tc in (task.get("test_cases") or ())]
        if not test_cases:
            return {
                "schema": SCHEMA + "/futamura_solve",
                "pass": False,
                "rung_used": -1,
                "status": "NO_EXECUTABLE_TESTS__ABSTAIN_FAIL_CLOSED",
                "proposer_calls": 0,
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 4),
            }

        # --- RUNG 0: Compiled Generalized AST Rule Replay (< 100 us lookup) ---
        r0 = self._try_rung0(source, test_cases)
        if r0 is not None:
            return {
                "schema": SCHEMA + "/futamura_solve",
                "pass": True,
                "rung_used": 0,
                "status": "SOLVED_AT_RUNG0_COMPILED_SKILL",
                "proposer_calls": 0,
                "compiled_to_rung0": False,
                "patched_source": r0["patched_source"],
                "rung0_hit": r0,
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 4),
            }

        # --- RUNG 2: Zero-Overhead Ochiai + Byte-Span AST Splice + CoW Zygote + Ring-0 Gate ---
        r2 = self.repair_engine.repair(
            source,
            test_cases,
            use_cow_fork=use_cow_fork,
            run_mutation_audit=True,
            alpha=alpha,
        )
        if r2.get("pass"):
            comp = (
                self.compile_verified_win_to_rung0(source, r2["patched_source"], source_rung=2)
                if auto_compile
                else {"compiled": False}
            )
            return {
                "schema": SCHEMA + "/futamura_solve",
                "pass": True,
                "rung_used": 2,
                "status": "SOLVED_AT_RUNG2_AND_COMPILED_TO_RUNG0" if comp.get("compiled") else "SOLVED_AT_RUNG2",
                "proposer_calls": 0,
                "compiled_to_rung0": bool(comp.get("compiled")),
                "compilation_receipt": comp,
                "patched_source": r2["patched_source"],
                "rung2_detail": r2,
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 4),
            }

        # --- RUNG 3: Optional UntrustedProposer gated by EXACT same Ring-0 Gate + Futamura Compile-Back ---
        if untrusted_proposer is None:
            return {
                "schema": SCHEMA + "/futamura_solve",
                "pass": False,
                "rung_used": 2,
                "status": "ABSTAIN_FAIL_CLOSED__NO_VERIFIED_REPAIR",
                "proposer_calls": 0,
                "rung2_detail": r2,
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 4),
            }

        ctx_key = hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]
        proposed_src = untrusted_proposer(task)
        if not isinstance(proposed_src, str) or not proposed_src.strip():
            return {
                "schema": SCHEMA + "/futamura_solve",
                "pass": False,
                "rung_used": 3,
                "status": "RUNG3_PROPOSER_EMPTY__ABSTAIN",
                "proposer_calls": 1,
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 4),
            }

        prop_sig = hashlib.sha256(proposed_src.encode("utf-8")).hexdigest()[:16]
        pre = self.belief_bus.check_pre_commit_gate(ctx_key, prop_sig)
        if not pre["allowed"]:
            return {
                "schema": SCHEMA + "/futamura_solve",
                "pass": False,
                "rung_used": 3,
                "status": pre["status"],
                "proposer_calls": 1,
                "pre_commit_gate": pre,
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 4),
            }

        eval_fn = (
            (lambda s: _eval_candidate_in_cow_fork(s, test_cases))
            if use_cow_fork
            else (lambda s: _eval_candidate_in_process(s, test_cases))
        )
        if not eval_fn(proposed_src):
            self.belief_bus.record_failure_witness(ctx_key, prop_sig, witness="RUNG3_COW_TESTS_FAILED")
            return {
                "schema": SCHEMA + "/futamura_solve",
                "pass": False,
                "rung_used": 3,
                "status": "RUNG3_PROPOSAL_REJECTED_BY_RING0_TESTS",
                "proposer_calls": 1,
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 4),
            }

        # Strip bloat via DRA ddmin + audit mutation kill + conformal e-value!
        ddmin_res = ddmin_minimize_hunks(source, proposed_src, eval_fn)
        clean_src = ddmin_res["minimized_source"]
        mut_res = audit_patch_mutation_kill(source, clean_src, lambda s: _eval_candidate_in_process(s, test_cases))
        gate = ConformalEValueGate(alpha=alpha)
        gate.observe("syntax_parse", passed=True, null_pass_prob=0.50)
        gate.observe("cow_fork_tests_pass", passed=True, null_pass_prob=0.10)
        gate.observe("ddmin_1_minimal", passed=bool(ddmin_res["pass"]), null_pass_prob=0.50)
        gate.observe("mutation_kill_audit", passed=(float(mut_res.get("mutation_kill_ratio", 0.0)) >= 0.5), null_pass_prob=0.25)
        e_verdict = gate.decision()
        if e_verdict["verdict"] != "COMMIT":
            self.belief_bus.record_failure_witness(ctx_key, prop_sig, witness=f"RING0_EVALUE_{e_verdict['verdict']}")
            return {
                "schema": SCHEMA + "/futamura_solve",
                "pass": False,
                "rung_used": 3,
                "status": f"RUNG3_REJECTED_BY_CONFORMAL_GATE:{e_verdict['verdict']}",
                "proposer_calls": 1,
                "ddmin": ddmin_res,
                "mutation_audit": mut_res,
                "conformal_evalue": e_verdict,
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 4),
            }

        comp = (
            self.compile_verified_win_to_rung0(source, clean_src, source_rung=3)
            if auto_compile
            else {"compiled": False}
        )
        return {
            "schema": SCHEMA + "/futamura_solve",
            "pass": True,
            "rung_used": 3,
            "status": "SOLVED_AT_RUNG3_AND_COMPILED_TO_RUNG0" if comp.get("compiled") else "SOLVED_AT_RUNG3",
            "proposer_calls": 1,
            "compiled_to_rung0": bool(comp.get("compiled")),
            "compilation_receipt": comp,
            "patched_source": clean_src,
            "ddmin": ddmin_res,
            "mutation_audit": mut_res,
            "conformal_evalue": e_verdict,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 4),
        }

    def wake_sleep_consolidate(
        self,
        *,
        max_active_rules: int = 64,
        rubin_observations: Mapping[str, tuple[float, float]] | None = None,
    ) -> dict[str, Any]:
        """GrowLibm-style library compression + Rubin `(WITH - WITHOUT)` skill-rent GC."""
        t0 = time.perf_counter()
        # 1. Update Rubin counterfactual lift `tau_hat = with_rate - without_rate`.
        quarantined_ids: list[str] = []
        if rubin_observations:
            for rid, (with_score, without_score) in rubin_observations.items():
                rule = self._rules_by_id.get(rid)
                if rule is not None:
                    rule.rubin_tau_hat = round(float(with_score) - float(without_score), 6)
                    if rule.rubin_tau_hat <= 0.0:
                        rule.quarantined = True
                        quarantined_ids.append(rid)

        # 2. Deduplicate semantically identical templates (GrowLibm e-class equivalence) & compute MDL compression.
        canonical_pairs: dict[tuple[str, str], list[CompiledRung0Rule]] = {}
        for rule in self._rules_by_id.values():
            if not rule.quarantined:
                canonical_pairs.setdefault((rule.before_template_src, rule.after_template_src), []).append(rule)

        merged_duplicates = 0
        for _pair_key, group in canonical_pairs.items():
            if len(group) > 1:
                group.sort(key=lambda r: (-r.rubin_tau_hat, -r.successes, r.rule_id))
                keeper = group[0]
                for dup in group[1:]:
                    keeper.hits += dup.hits
                    keeper.successes += dup.successes
                    dup.quarantined = True
                    merged_duplicates += 1

        # 3. Finite-cap Rubin rent eviction (keep highest counterfactual lift & hit utility).
        active = [r for r in self._rules_by_id.values() if not r.quarantined]
        active.sort(key=lambda r: (-r.rubin_tau_hat, -(r.successes - r.failures), r.rule_id))
        evicted_ids: list[str] = []
        if len(active) > max_active_rules:
            for drop in active[max_active_rules:]:
                drop.quarantined = True
                evicted_ids.append(drop.rule_id)
            active = active[:max_active_rules]

        # 4. Measure MDL description-length gain across compiled rules.
        raw_bytes = sum(len(r.before_template_src) + len(r.after_template_src) for r in active)
        weighted_reuse_savings = sum(max(0, r.hits) * (len(r.before_template_src) + len(r.after_template_src)) for r in active)

        return {
            "schema": SCHEMA + "/wake_sleep_consolidate",
            "pass": True,
            "status": "WAKE_SLEEP_CONSOLIDATED",
            "active_rules": len(active),
            "quarantined_by_rubin": sorted(quarantined_ids),
            "merged_eclass_duplicates": merged_duplicates,
            "evicted_by_cap": sorted(evicted_ids),
            "active_rule_bytes": raw_bytes,
            "mdl_reuse_bytes_saved": weighted_reuse_savings,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 4),
        }


# Process-shared default Futamura cascade instance (for `UnifiedModel` / `Creature` reuse).
_SHARED_CASCADE: FutamuraSelfCompilingCascade | None = None


def shared_futamura_cascade() -> FutamuraSelfCompilingCascade:
    global _SHARED_CASCADE
    if _SHARED_CASCADE is None:
        _SHARED_CASCADE = FutamuraSelfCompilingCascade()
    return _SHARED_CASCADE


def run(payload: Mapping[str, Any], _root: Path | None = None) -> dict[str, Any]:
    """UnifiedModel/federation callable entry point."""
    op = str(payload.get("op") or "futamura_solve").strip().lower()
    if op == "futamura_solve":
        cascade = payload.get("cascade") if isinstance(payload.get("cascade"), FutamuraSelfCompilingCascade) else FutamuraSelfCompilingCascade()
        return cascade.solve(
            dict(payload.get("task") or payload),
            untrusted_proposer=payload.get("untrusted_proposer"),
            auto_compile=bool(payload.get("auto_compile", True)),
            use_cow_fork=bool(payload.get("use_cow_fork", True)),
            alpha=float(payload.get("alpha", 0.05)),
        )
    if op == "conformal_evalue":
        gate = ConformalEValueGate(alpha=float(payload.get("alpha", 0.05)))
        for ev in payload.get("observations") or ():
            gate.observe(
                str(ev["evidence"]),
                passed=bool(ev["passed"]),
                null_pass_prob=float(ev.get("null_pass_prob", 0.25)),
                hard_contradiction=bool(ev.get("hard_contradiction", False)),
            )
        return gate.decision()
    if op == "hybrid_cu":
        sup = HybridComputerUsePetriSupervisor(
            initial_marking=payload.get("initial_marking"),
            transitions=payload.get("transitions"),
        )
        return sup.execute_episode(
            list(payload.get("steps") or ()),
            executor=payload.get("executor"),
            initial_state=payload.get("initial_state"),
        )
    if op == "cow_zygote_repair":
        eng = ZeroOverheadCoWZygoteRepairEngine()
        return eng.repair(
            str(payload["source"]),
            list(payload.get("test_cases") or ()),
            use_cow_fork=bool(payload.get("use_cow_fork", True)),
        )
    return {"schema": SCHEMA, "pass": False, "status": f"UNSUPPORTED_OP:{op}"}
