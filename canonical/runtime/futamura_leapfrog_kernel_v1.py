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
    snapshot_directory_hashes,
    verify_byte_effect,
    verify_directory_effect_diff,
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
    "webmcp": 0.03,
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
        """Select cheapest reliable HCU channel (`webmcp` < `programmatic` < `semantic` < `visual`)."""
        orig_ch = str(step.get("channel") or "visual").lower()
        orig_cost = _CHANNEL_COST.get(orig_ch, 1.0)
        if step.get("webmcp_tool"):
            ch = "webmcp"
            chosen = {**dict(step), "selected_channel": ch, "exec_payload": step.get("webmcp_tool")}
        elif step.get("programmatic_cmd") or step.get("cli_equiv"):
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


def _exec_test_case(ns: dict[str, Any], test_expr: str) -> None:
    """Run one test case FALSIFIABLY against namespace `ns`; raise on failure.

    A bare expression (`f(2) == 5`) compiled with `exec` is *evaluated and then
    discarded*, so `exec(...)` alone accepts every candidate no matter how wrong
    the source is -- an unfalsifiable oracle (the exact defect that makes a
    "verifier" green on code it never checked). We therefore evaluate the case in
    `eval` mode and require truthiness when it yields a value. `None` means the
    case is statement-shaped (`check(x)` / `assert ...`) and passes iff it does
    not raise, which is the standard assertion convention.
    """
    try:
        expr_code = compile(test_expr, "<futamura_test>", "eval")
    except SyntaxError:
        exec(compile(test_expr, "<futamura_test>", "exec"), ns, ns)
        return
    value = eval(expr_code, ns, ns)
    if value is not None and not value:
        raise AssertionError(f"test case returned falsey value {value!r}: {test_expr}")


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
            _exec_test_case(ns, test_expr)
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
            _exec_test_case(ns, tc)
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


def _rule_bucket(node: ast.AST) -> tuple[str, ...]:
    """Coarse index key: node kind plus its operator, ignoring operand shape.

    `_preorder_signature` is exact, so it cannot find a rule that should match a
    *sub-expression* of a larger expression: the left operand of `a - b - c` is an
    `ast.BinOp`, and the learned rule's keyed signature is `Name - Name`. Measured
    2026-11-26, that made compiled laws unable to chain. The bucket is deliberately
    coarse -- `_match_template` still decides, and the suite oracle still verifies
    the final state -- so a coarse key can only add reachable candidates.
    """
    kind = type(node).__name__
    op = getattr(node, "op", None)
    if op is None:
        ops = getattr(node, "ops", None)
        if ops:
            op = ops[0]
    if op is None:
        bops = getattr(node, "op", None)
        op = bops
    return (kind, type(op).__name__) if op is not None else (kind,)


def _match_template(pattern: ast.AST, concrete: ast.AST, bindings: dict[str, ast.AST]) -> bool:
    """Match an alpha-normalized AST `pattern` against `concrete`, populating `bindings`."""
    if isinstance(pattern, ast.Name) and pattern.id.startswith(("__V", "__C")) and pattern.id.endswith("__"):
        slot = pattern.id
        # `__V` slots bind any *expression*, not just a bare name. Restricting
        # them to `ast.Name` made the learned law `x - y -> x + y` unable to fire
        # on a compound operand: measured 2026-11-26, replay of `a - b - c`
        # rewrote the inner pair to `a + b - c` and then dead-ended, because the
        # remaining `(a + b) - c` has an `ast.BinOp` on the left and the template
        # refused to bind it. The law is re-verified by the suite oracle on every
        # final state, so widening the binding domain can only add reachable
        # candidates, never accept an unverified one; the cost of a wider search
        # is bounded by RUNG0_MAX_STATES.
        if slot.startswith("__V") and isinstance(concrete, ast.Constant):
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


RUNG0_STORE_VERSION = 1
RUNG0_STORE_RELPATH = Path("canonical/astra_runtime/state/futamura_rung0_laws_v1.json")


def rung0_store_path() -> Path:
    """Where compiled laws persist between processes.

    Default is the repo state dir; `BRAIN_FUTAMURA_STORE` overrides it so a test
    can point at a scratch file rather than mutating the checked-in store.
    """
    override = os.environ.get("BRAIN_FUTAMURA_STORE")
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[2] / RUNG0_STORE_RELPATH


def load_rung0_rules(path: Path | None = None) -> list[dict[str, Any]]:
    """Read persisted laws. Corrupt or absent store yields no laws, never a crash."""
    target = path or rung0_store_path()
    try:
        raw = target.read_text(encoding="utf-8")
    except OSError:
        return []
    try:
        payload = json.loads(raw)
    except (ValueError, TypeError):
        return []
    if not isinstance(payload, dict) or payload.get("store_version") != RUNG0_STORE_VERSION:
        return []
    rules = payload.get("rules")
    return [r for r in rules if isinstance(r, dict)] if isinstance(rules, list) else []


def save_rung0_rules(rules: list[dict[str, Any]], path: Path | None = None) -> Path:
    """Write persisted laws atomically."""
    target = path or rung0_store_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {"store_version": RUNG0_STORE_VERSION, "rules": rules}
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=1, sort_keys=True), encoding="utf-8")
    tmp.replace(target)
    return target


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

    def __init__(self, *, persist_on_init: bool = True) -> None:
        self._rung0_by_key: dict[tuple[str, ...], list[CompiledRung0Rule]] = {}
        # Coarse (kind, operator) index so a rule can fire on a nested operand
        # whose exact signature differs from the learned one.
        self._rung0_by_bucket: dict[tuple[str, ...], list[CompiledRung0Rule]] = {}
        self._rules_by_id: dict[str, CompiledRung0Rule] = {}
        self.belief_bus = DBSPBeliefRevisionBus()
        self.repair_engine = ZeroOverheadCoWZygoteRepairEngine()
        self.compile_history: list[dict[str, Any]] = []
        # Laws survive the process, not just the session. Measured 2026-11-26:
        # a fresh interpreter saw 0 rules and re-spent Rung 2 on a law it had
        # already learned, which makes "compile once, replay forever" false
        # outside a single process.
        self._persisted: dict[str, dict[str, Any]] = {}
        # Rule ids retired for cause; remembered so they are not re-armed.
        self._retired: set[str] = set()
        if persist_on_init:
            self._hydrate_persisted_laws()

    def _hydrate_persisted_laws(self) -> None:
        """Rebuild compiled laws from disk, re-validating each one.

        A persisted law is a *claim* that held in an earlier interpreter. It is
        re-armed only if its templates re-parse and rebuild a usable rule;
        anything unparseable is dropped rather than trusted. The store is
        ordinary editable data, so a human can delete a bad law by hand and the
        next process simply will not have it.
        """
        for row in load_rung0_rules():
            try:
                before_ast = ast.parse(str(row["before_template"]), mode="eval").body
                after_ast = ast.parse(str(row["after_template"]), mode="eval").body
            except (KeyError, SyntaxError, TypeError, ValueError):
                continue
            rule = CompiledRung0Rule(
                rule_id=str(row.get("rule_id") or f"persisted_{len(self._persisted)}"),
                preorder_key=_preorder_signature(before_ast),
                before_template_src=str(row["before_template"]),
                after_template_src=str(row["after_template"]),
                before_ast=before_ast,
                after_ast=after_ast,
                source_rung=int(row.get("source_rung") or 2),
                successes=int(row.get("successes") or 0),
                failures=int(row.get("failures") or 0),
                rubin_tau_hat=float(row.get("rubin_tau_hat") or 1.0),
            )
            if bool(row.get("quarantined")):
                # A retired law stays retired across restarts; that memory is the
                # point of persisting it.
                self._retired.add(rule.rule_id)
                continue
            if rule.rule_id in self._rules_by_id:
                continue
            self._rules_by_id[rule.rule_id] = rule
            self._rung0_by_key.setdefault(rule.preorder_key, []).append(rule)
            self._rung0_by_bucket.setdefault(_rule_bucket(rule.before_ast), []).append(rule)
            self._persisted[rule.rule_id] = dict(row)

    def persisted_law_ids(self) -> list[str]:
        """Rule ids that came from disk, as opposed to compiled this process."""
        return sorted(self._persisted)

    def save_laws(self, path: Path | None = None) -> Path:
        """Persist all non-quarantined laws with their observed counters."""
        rows: list[dict[str, Any]] = [
            {
                "rule_id": rule_id,
                "before_template": rule.before_template_src,
                "after_template": rule.after_template_src,
                "source_rung": int(rule.source_rung),
                "hits": int(rule.hits),
                "successes": int(rule.successes),
                "failures": int(rule.failures),
                "rubin_tau_hat": float(rule.rubin_tau_hat),
            }
            for rule_id, rule in sorted(self._rules_by_id.items())
            if not rule.quarantined
        ]
        # Retired laws are written explicitly, flagged, not silently dropped: a
        # law that vanishes is re-learned from the same evidence next time.
        for rule_id in sorted(self._retired):
            rule = self._rules_by_id.get(rule_id)
            rows.append({
                "rule_id": rule_id,
                "before_template": rule.before_template_src if rule else "",
                "after_template": rule.after_template_src if rule else "",
                "source_rung": int(rule.source_rung) if rule else 0,
                "hits": int(rule.hits) if rule else 0,
                "successes": int(rule.successes) if rule else 0,
                "failures": int(rule.failures) if rule else 0,
                "rubin_tau_hat": float(rule.rubin_tau_hat) if rule else 0.0,
                "quarantined": True,
            })
        return save_rung0_rules(rows, path)

    def _record_rule_outcome(self, rule: CompiledRung0Rule, passed: bool) -> None:
        """Record one replay outcome and retire the law if the evidence is against it."""
        if passed:
            rule.successes += 1
            return
        rule.failures += 1
        observed = rule.successes + rule.failures
        if observed < self.RULE_RETIRE_MIN_FAILURES:
            return
        rate = rule.successes / observed
        if rate < self.RULE_RETIRE_SUCCESS_RATE:
            rule.quarantined = True
            self._retired.add(rule.rule_id)
            try:
                self.save_laws()
            except OSError:
                pass

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
        self._rung0_by_bucket.setdefault(_rule_bucket(rule.before_ast), []).append(rule)
        # A law that dies with the interpreter is a cache, not a compilation.
        try:
            self.save_laws()
        except OSError:
            pass
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

    # Bounds on the Rung-0 replay search. A learned law can need more than one
    # application: `a - b - c` must fire `a - b -> a + b` twice. The search is
    # over *sequences* of rewrites and is verified only at the END of each
    # sequence, because a partially-applied law is expected to still fail --
    # requiring every intermediate state to pass would make chaining impossible
    # (measured 2026-11-26: it did, and `a - b - c` fell through to Rung 2).
    # Retirement thresholds, in observed replays. A compiled law is a hypothesis
    # about a rewrite family; when it keeps failing the family it claims it is
    # wrong, and keeping it is worse than deleting it, because every later task
    # pays for the failed screening. Measured 2026-11-26: `failures` was
    # incremented on every miss but nothing ever acted on the count, so a bad law
    # was re-armed in every future process. At least this many observations are
    # required before a law may be retired, so one unlucky task cannot delete a
    # good law.
    RULE_RETIRE_MIN_FAILURES = 3
    RULE_RETIRE_SUCCESS_RATE = 0.25
    RUNG0_MAX_REWRITES = 6
    RUNG0_MAX_STATES = 48

    def _rung0_rewrites(self, source: str) -> list[tuple[str, str]]:
        """Every `(rule_id, rewritten_source)` reachable in ONE rewrite of `source`."""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        out: list[tuple[str, str]] = []
        for node in ast.walk(tree):
            if not hasattr(node, "lineno") or not hasattr(node, "end_lineno"):
                continue
            for rule in self._rung0_by_bucket.get(_rule_bucket(node), ()):
                if rule.quarantined or rule.rubin_tau_hat <= 0.0:
                    continue
                bindings: dict[str, ast.AST] = {}
                if not _match_template(rule.before_ast, node, bindings):
                    continue
                instantiated = _instantiate_template(rule.after_ast, bindings)
                cand_src = splice_ast_byte_span(source, node, ast.unparse(instantiated))
                if cand_src != source:
                    out.append((rule.rule_id, cand_src))
        return out

    def _try_rung0(self, source: str, test_cases: Sequence[str]) -> dict[str, Any] | None:
        """Breadth-first replay of compiled Rung-0 laws to a *verified* fixpoint.

        Rung 0 is the Futamura payoff: a law learned once from a verified repair
        replays with zero synthesis. Measured 2026-11-26 with a single
        application, the learned `a - b -> a + b` law transferred to renamed
        functions, new constants and a `str` operand in 0.2-0.4 ms, but failed
        `a - b - c`, where the law must fire twice. Without chaining, the
        expensive rung is spent on a task the cheap one already knows.
        """
        if not self._rung0_by_key:
            return None
        t0 = time.perf_counter()
        frontier: list[tuple[str, tuple[str, ...]]] = [(source, ())]
        seen: set[str] = {source}
        states = 0
        while frontier and states < self.RUNG0_MAX_STATES:
            state, fired = frontier.pop(0)
            if len(fired) >= self.RUNG0_MAX_REWRITES:
                continue
            for rule_id, cand_src in self._rung0_rewrites(state):
                if cand_src in seen:
                    continue
                seen.add(cand_src)
                states += 1
                rule = self._rules_by_id.get(rule_id)
                if rule is not None:
                    rule.hits += 1
                if _eval_candidate_in_process(cand_src, test_cases):
                    if rule is not None:
                        self._record_rule_outcome(rule, passed=True)
                    return {
                        "rule_id": rule_id,
                        "rule_ids": [*fired, rule_id],
                        "rewrites": len(fired) + 1,
                        "before_template": rule.before_template_src if rule else "",
                        "after_template": rule.after_template_src if rule else "",
                        "patched_source": cand_src,
                        "lookup_and_splice_us": round((time.perf_counter() - t0) * 1e6, 3),
                        "matched_attempts": states,
                    }
                if rule is not None:
                    self._record_rule_outcome(rule, passed=False)
                if states >= self.RUNG0_MAX_STATES:
                    break
                frontier.append((cand_src, (*fired, rule_id)))
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


# ===========================================================================
# 7. Wave 37: Real OS Kernel-Confined 3-Channel Computer-Use Executor
# ===========================================================================


def _snapshot_work_dir_bytes(work_dir: Path) -> dict[str, bytes]:
    snap: dict[str, bytes] = {}
    if not work_dir.exists():
        return snap
    for p in sorted(work_dir.rglob("*")):
        if p.is_file():
            rel = str(p.relative_to(work_dir)).replace("\\", "/")
            snap[rel] = p.read_bytes()
    return snap


def _restore_work_dir_bytes(work_dir: Path, snap: Mapping[str, bytes]) -> None:
    if work_dir.exists():
        for p in sorted(work_dir.rglob("*"), reverse=True):
            if p.is_file():
                rel = str(p.relative_to(work_dir)).replace("\\", "/")
                if rel not in snap:
                    p.unlink(missing_ok=True)
            elif p.is_dir():
                try:
                    p.rmdir()
                except OSError:
                    pass
    for rel, raw in snap.items():
        dst = work_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(raw)


def _digest_work_dir(snap: Mapping[str, bytes]) -> str:
    h = hashlib.sha256()
    for rel in sorted(snap):
        h.update(rel.encode("utf-8"))
        h.update(b"\x00")
        h.update(hashlib.sha256(snap[rel]).digest())
    return h.hexdigest()[:16]


def _validate_webmcp_args(
    args: Mapping[str, Any],
    schema: Mapping[str, Any] | None,
) -> tuple[bool, str]:
    """Deterministic W3C WebMCP `navigator.modelContext` JSON-Schema validator (fail-closed)."""
    if not isinstance(schema, Mapping):
        return True, "SCHEMA_UNCONSTRAINED"
    required = schema.get("required") or ()
    for req in required:
        if req not in args or args[req] is None:
            return False, f"WEBMCP_MISSING_REQUIRED:{req}"
    props = schema.get("properties") or {}
    type_map: dict[str, tuple[type, ...]] = {
        "string": (str,),
        "integer": (int,),
        "number": (int, float),
        "boolean": (bool,),
        "array": (list, tuple),
        "object": (dict, Mapping),
    }
    for key, val in args.items():
        if key not in props:
            if schema.get("additionalProperties") is False:
                return False, f"WEBMCP_UNEXPECTED_ARG:{key}"
            continue
        pspec = props[key]
        if not isinstance(pspec, Mapping):
            continue
        expected = pspec.get("type")
        if expected in type_map:
            if expected in ("integer", "number") and isinstance(val, bool):
                return False, f"WEBMCP_TYPE_MISMATCH:{key}:expected_{expected}"
            if not isinstance(val, type_map[expected]):
                return False, f"WEBMCP_TYPE_MISMATCH:{key}:expected_{expected}"
        enum_vals = pspec.get("enum")
        if enum_vals is not None and val not in enum_vals:
            return False, f"WEBMCP_ENUM_MISMATCH:{key}"
    return True, "WEBMCP_SCHEMA_VALID"


def _compile_refusal_to_repaired_argv(
    argv: Sequence[str],
    refusal_text: str,
) -> dict[str, Any] | None:
    """Wave 38 Refusal-as-Interface-Compiler (`a_refusal_is_a_specification_v1` + Agent-S4).

    Parses the refusal message emitted by a confined CLI/app into a typed,
    non-guessed argv repair (`OFFERED` flag, `ENUMERAL` option, `CONFLICT`
    flag subtraction, or explicit `--flag` requirement). Returns None if the
    refusal names no actionable flag/option (fail-closed, never guesses).
    """
    import re as _re

    text = str(refusal_text or "").strip()
    if not text or not argv:
        return None
    base = [str(a) for a in argv]
    clause_kind = ""
    flag_to_add: str | None = None
    flag_to_remove: str | None = None
    clause_summary = ""

    # 1. Delegate first to Project Brain's battle-tested `a_refusal_is_a_specification_v1`
    try:
        from canonical.runtime import a_refusal_is_a_specification_v1 as refspec

        clause = refspec.read_refusal(text)
        if clause is not None and clause.form != refspec.UNREAD:
            clause_kind = str(clause.form)
            clause_summary = str(getattr(clause, "raw", "") or text[:120])
            if clause.form == refspec.OFFERED and clause.choices:
                cand_flag = str(clause.choices[0])
                if cand_flag not in base:
                    flag_to_add = cand_flag
            elif clause.form == refspec.ENUMERAL and clause.choices:
                for ch in clause.choices:
                    if str(ch) not in base:
                        flag_to_add = str(ch)
                        break
            elif clause.form == refspec.CONFLICT and clause.choices:
                for ch in clause.choices:
                    if str(ch) in base:
                        flag_to_remove = str(ch)
                        break
    except Exception:
        pass

    # 2. Complement with explicit POSIX `--long-flag` / `-f` demand declarations in stderr
    if flag_to_add is None and flag_to_remove is None:
        m_flag = _re.search(
            r"(?:use|pass|specify|provide|requires?|add|without|missing)\s+(?:the\s+)?['\"`]?(--[a-zA-Z0-9][a-zA-Z0-9_-]*|-[a-zA-Z])['\"`]?",
            text,
            _re.IGNORECASE,
        )
        if m_flag:
            cand_flag = m_flag.group(1)
            if cand_flag not in base:
                flag_to_add = cand_flag
                clause_kind = "EXPLICIT_DEMAND_FLAG"
                clause_summary = m_flag.group(0)

    if flag_to_add is None and flag_to_remove is None:
        return None

    repaired = list(base)
    if flag_to_remove is not None:
        repaired = [tok for tok in repaired if tok != flag_to_remove]
    if flag_to_add is not None:
        repaired.append(flag_to_add)

    tool_family = Path(base[0]).name
    if len(base) >= 2 and base[1] not in ("-c", "-m") and not base[1].startswith("-"):
        tool_family = f"{tool_family}:{Path(base[1]).name}"
    return {
        "tool_family": tool_family,
        "clause_kind": clause_kind or "OFFERED",
        "clause_summary": clause_summary[:160],
        "flag_added": flag_to_add,
        "flag_removed": flag_to_remove,
        "repaired_argv": repaired,
    }


class ConfinedHybridComputerUseExecutor:
    """Real OS-confined 4-channel HCU executor (Wave 37+38):
    - Real Linux kernel isolation (`os_isolation_v1.run`: user+mount+pid+ipc+uts+net,
      `CapEff=0`, AND classic BPF `seccomp` allowlist from `worker_syscall_allowlist_v1`)
    - Strict fail-closed if unprivileged namespaces or seccomp are unavailable
    - 4-channel cost ladder: `WebMCP (navigator.modelContext) > Programmatic CLI > Semantic AX/CDP > Visual`
    - Agent-S4 + `a_refusal_is_a_specification_v1` Refusal-to-Interface Compiler (`evolved_interfaces`)
    - Ring-0 Byte Effect Oracle (`verify_byte_effect`) + CoW workspace rollback + `PreCommitFailureGate`
    """

    def __init__(
        self,
        *,
        supervisor: HybridComputerUsePetriSupervisor | None = None,
        belief_bus: DBSPBeliefRevisionBus | None = None,
        loop_churn_threshold: int = 2,
        webmcp_tools: Mapping[str, Mapping[str, Any]] | None = None,
    ) -> None:
        self.supervisor = supervisor or HybridComputerUsePetriSupervisor()
        self.belief_bus = belief_bus or DBSPBeliefRevisionBus()
        self.loop_churn_threshold = max(1, int(loop_churn_threshold))
        self.webmcp_tools: dict[str, dict[str, Any]] = {
            str(k): dict(v) for k, v in (webmcp_tools or {}).items()
        }
        self.evolved_interfaces: dict[str, dict[str, Any]] = {}

    def register_webmcp_tool(
        self,
        name: str,
        handler: Callable[[Mapping[str, Any], Path], Any],
        *,
        input_schema: Mapping[str, Any] | None = None,
        description: str = "",
    ) -> dict[str, Any]:
        """Register a typed W3C WebMCP (`navigator.modelContext`) tool for zero-pixel execution."""
        spec = {
            "name": str(name),
            "handler": handler,
            "input_schema": dict(input_schema or {}),
            "description": str(description),
        }
        self.webmcp_tools[str(name)] = spec
        return {"registered": True, "name": str(name), "channel": "webmcp"}

    @staticmethod
    def probe_isolation(*, budget_s: float = 30.0, seccomp: bool = True) -> dict[str, Any]:
        from canonical.runtime import os_isolation_v1

        return os_isolation_v1.probe(budget_s=budget_s, seccomp=seccomp)

    @staticmethod
    def _run_confined_argv(
        argv: Sequence[str],
        *,
        work_dir: Path,
        budget_s: float = 15.0,
        allow_network: bool = False,
        env: Mapping[str, str] | None = None,
        seccomp: bool = True,
    ) -> dict[str, Any]:
        from canonical.runtime import os_isolation_v1

        sup = os_isolation_v1.support()
        if not sup.get("available"):
            return {
                "isolated": False,
                "ok": False,
                "caps_dropped": False,
                "seccomp_installed": False,
                "status": "ISOLATION_UNAVAILABLE",
                "reason": sup.get("reason", os_isolation_v1.UNAVAILABLE),
            }
        return os_isolation_v1.run(
            list(argv),
            work_dir=work_dir,
            budget_s=budget_s,
            allow_network=allow_network,
            env=env,
            seccomp=seccomp,
        )

    def execute_episode(
        self,
        work_dir: str | Path,
        steps: Sequence[Mapping[str, Any]],
        *,
        goal_id: str = "confined_hcu_episode",
        budget_s: float = 15.0,
        allow_network: bool = False,
        verify_effect: bool = True,
        seccomp: bool = True,
        auto_compile_refusal: bool = True,
    ) -> dict[str, Any]:
        t0 = time.perf_counter()
        wd = Path(work_dir).resolve()
        wd.mkdir(parents=True, exist_ok=True)

        trace: list[dict[str, Any]] = []
        recent_pairs: list[tuple[str, str]] = []
        channel_counts = {"webmcp": 0, "programmatic": 0, "semantic": 0, "visual": 0}
        total_cost = 0.0
        rolled_back_steps = 0
        recovered_steps = 0
        effect_rejections = 0
        failure_gate_skips = 0
        refusal_compiled_count = 0
        evolved_interface_hits = 0
        all_ok = True

        for idx, step in enumerate(steps):
            action_name = str(step.get("action") or f"step_{idx}")
            candidates: list[Mapping[str, Any]] = [step]
            for fb in step.get("fallback_steps") or ():
                if isinstance(fb, Mapping):
                    candidates.append(fb)

            step_resolved = False
            step_records: list[dict[str, Any]] = []

            c_idx = 0
            while c_idx < len(candidates):
                cand = candidates[c_idx]
                cand_action = str(cand.get("action") or f"{action_name}__alt_{c_idx}")
                webmcp_tool_name = cand.get("webmcp_tool")
                argv = [str(x) for x in (cand.get("argv") or ())]

                # Wave 38: Apply already-compiled Agent-S4 refusal interface rule on matching tool family
                compiled_iface_applied: str | None = None
                if argv and not cand.get("_is_refusal_retry"):
                    fam = Path(argv[0]).name
                    if len(argv) >= 2 and argv[1] not in ("-c", "-m") and not argv[1].startswith("-"):
                        fam = f"{fam}:{Path(argv[1]).name}"
                    iface = self.evolved_interfaces.get(fam)
                    if iface is not None:
                        add_f = iface.get("flag_added")
                        rem_f = iface.get("flag_removed")
                        mutated = False
                        if rem_f and rem_f in argv:
                            argv = [tok for tok in argv if tok != rem_f]
                            mutated = True
                        if add_f and add_f not in argv:
                            argv = list(argv) + [str(add_f)]
                            mutated = True
                        if mutated:
                            compiled_iface_applied = fam
                            evolved_interface_hits += 1

                elev_in = dict(cand)
                if argv and not elev_in.get("programmatic_cmd") and not webmcp_tool_name:
                    elev_in["programmatic_cmd"] = " ".join(argv)
                channel, _chosen, _saved = self.supervisor.elevate_channel(elev_in)
                cost = float(_CHANNEL_COST.get(channel, 1.0))

                pre_snap = _snapshot_work_dir_bytes(wd)
                pre_digest = _digest_work_dir(pre_snap)
                sig_payload = {"webmcp": webmcp_tool_name, "args": cand.get("webmcp_args")} if webmcp_tool_name else argv
                cmd_sig = hashlib.sha256(json.dumps(sig_payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:16]
                ctx_key = f"{goal_id}:{pre_digest}"

                # 1. PreCommitFailureGate check
                fg = self.belief_bus.check_pre_commit_gate(ctx_key, cmd_sig)
                if not fg["allowed"]:
                    failure_gate_skips += 1
                    step_records.append(
                        {
                            "attempt": c_idx,
                            "action": cand_action,
                            "status": "BLOCKED_BY_FAILURE_GATE",
                            "reason": fg.get("reason", "REPEATED_FAILING_ACTION"),
                        }
                    )
                    c_idx += 1
                    continue

                # 2. OSWorld-Human 2-step loop-churn breaker
                pair = (f"{cand_action}:{cmd_sig[:8]}", pre_digest)
                if recent_pairs.count(pair) >= self.loop_churn_threshold:
                    step_records.append(
                        {
                            "attempt": c_idx,
                            "action": cand_action,
                            "status": "LOOP_CHURN_BROKEN",
                            "state_digest": pre_digest,
                        }
                    )
                    c_idx += 1
                    continue

                # 3. Microsecond Petri guard check
                t_name = str(cand.get("petri_transition") or cand_action)
                if t_name in self.supervisor.transitions:
                    p_ok, p_reason, p_us = self.supervisor.check_petri_transition(t_name)
                    if not p_ok:
                        step_records.append(
                            {
                                "attempt": c_idx,
                                "action": cand_action,
                                "status": "BLOCKED_BY_PETRI_GUARD",
                                "reason": p_reason,
                                "petri_us": round(p_us, 3),
                            }
                        )
                        c_idx += 1
                        continue

                channel_counts[channel] = channel_counts.get(channel, 0) + 1
                total_cost += cost
                recent_pairs.append(pair)

                # 4A. W3C WebMCP (`navigator.modelContext`) deterministic typed tool execution
                if webmcp_tool_name:
                    tspec = self.webmcp_tools.get(str(webmcp_tool_name))
                    if tspec is None:
                        step_records.append(
                            {
                                "attempt": c_idx,
                                "action": cand_action,
                                "channel": "webmcp",
                                "status": "WEBMCP_TOOL_UNREGISTERED",
                                "tool": str(webmcp_tool_name),
                            }
                        )
                        c_idx += 1
                        continue
                    wargs = dict(cand.get("webmcp_args") or {})
                    v_ok, v_reason = _validate_webmcp_args(wargs, tspec.get("input_schema"))
                    if not v_ok:
                        self.belief_bus.record_failure_witness(ctx_key, cmd_sig, witness=v_reason)
                        step_records.append(
                            {
                                "attempt": c_idx,
                                "action": cand_action,
                                "channel": "webmcp",
                                "status": "WEBMCP_SCHEMA_REJECTED",
                                "reason": v_reason,
                            }
                        )
                        c_idx += 1
                        continue
                    try:
                        tool_out = tspec["handler"](wargs, wd)
                    except Exception as exc:
                        _restore_work_dir_bytes(wd, pre_snap)
                        rolled_back_steps += 1
                        self.belief_bus.record_failure_witness(ctx_key, cmd_sig, witness=f"WEBMCP_ERR:{type(exc).__name__}")
                        step_records.append(
                            {
                                "attempt": c_idx,
                                "action": cand_action,
                                "channel": "webmcp",
                                "status": "WEBMCP_HANDLER_FAILED_ROLLED_BACK",
                                "error": str(exc)[:200],
                            }
                        )
                        c_idx += 1
                        continue
                    iso_res = {
                        "ok": True,
                        "returncode": 0,
                        "isolated": True,
                        "caps_dropped": True,
                        "seccomp_installed": False,
                        "seccomp_filter_sha256": None,
                        "namespaces": ["webmcp_typed_contract"],
                        "seconds": 0.0,
                        "stdout": json.dumps(tool_out, default=str)[:240],
                    }
                else:
                    if not argv:
                        step_records.append({"attempt": c_idx, "action": cand_action, "status": "NO_ARGV"})
                        c_idx += 1
                        continue

                    # 4B. Real Linux kernel-isolated execution (`CapEff=0` + classic BPF `seccomp`)
                    iso_res = self._run_confined_argv(
                        argv,
                        work_dir=wd,
                        budget_s=float(cand.get("budget_s", budget_s)),
                        allow_network=bool(cand.get("allow_network", allow_network)),
                        env=cand.get("env"),
                        seccomp=bool(cand.get("seccomp", seccomp)),
                    )
                    if not iso_res.get("isolated") or not iso_res.get("caps_dropped"):
                        _restore_work_dir_bytes(wd, pre_snap)
                        rolled_back_steps += 1
                        all_ok = False
                        step_records.append(
                            {
                                "attempt": c_idx,
                                "action": cand_action,
                                "status": "FAIL_CLOSED_ISOLATION_REQUIRED",
                                "isolation": {
                                    "isolated": bool(iso_res.get("isolated")),
                                    "caps_dropped": bool(iso_res.get("caps_dropped")),
                                    "seccomp_installed": bool(iso_res.get("seccomp_installed")),
                                    "reason": iso_res.get("reason", iso_res.get("detail", "")),
                                },
                            }
                        )
                        break

                    rc = iso_res.get("returncode")
                    if (not iso_res.get("ok")) or (rc not in (0, None)):
                        _restore_work_dir_bytes(wd, pre_snap)
                        rolled_back_steps += 1
                        refusal_blob = f"{iso_res.get('stderr', '')}\n{iso_res.get('stdout', '')}".strip()
                        self.belief_bus.record_failure_witness(
                            ctx_key,
                            cmd_sig,
                            witness=f"NONZERO_RC:{rc}",
                        )
                        compiled_repair = None
                        if auto_compile_refusal and not cand.get("_is_refusal_retry"):
                            compiled_repair = _compile_refusal_to_repaired_argv(argv, refusal_blob)
                            if compiled_repair is not None:
                                retry_cand = dict(cand)
                                retry_cand["action"] = f"{cand_action}__refusal_compiled"
                                retry_cand["argv"] = compiled_repair["repaired_argv"]
                                retry_cand["_is_refusal_retry"] = True
                                retry_cand["_compiled_repair"] = compiled_repair
                                candidates.insert(c_idx + 1, retry_cand)
                        step_records.append(
                            {
                                "attempt": c_idx,
                                "action": cand_action,
                                "status": "CMD_REFUSED_COMPILED_RETRY" if compiled_repair else "CMD_FAILED_ROLLED_BACK",
                                "returncode": rc,
                                "stderr": str(iso_res.get("stderr", ""))[:240],
                                "isolated": True,
                                "caps_dropped": True,
                                "seccomp_installed": bool(iso_res.get("seccomp_installed")),
                                "compiled_refusal": compiled_repair,
                            }
                        )
                        c_idx += 1
                        continue

                # 5. Ring-0 Byte Effect Oracle verification
                effect_contract = cand.get("effect_contract") or step.get("effect_contract")
                effect_report: dict[str, Any] | None = None
                if verify_effect and isinstance(effect_contract, Mapping):
                    out_rel = str(effect_contract.get("output_path") or "")
                    out_file = (wd / out_rel).resolve() if out_rel else wd
                    exp_src_path = effect_contract.get("expected_source_path")
                    if isinstance(exp_src_path, (str, Path)) and not Path(exp_src_path).is_absolute():
                        exp_src_path = (wd / exp_src_path).resolve()
                    effect_report = verify_byte_effect(
                        out_file,
                        expected_format=effect_contract.get("expected_format"),
                        expected_source_bytes=effect_contract.get("expected_source_bytes"),
                        expected_source_path=exp_src_path,
                        baseline_archive_hashes=effect_contract.get("baseline_archive_hashes"),
                        allowed_archive_mutations=effect_contract.get("allowed_archive_mutations") or (),
                    )
                    if not effect_report.get("pass"):
                        effect_rejections += 1
                        _restore_work_dir_bytes(wd, pre_snap)
                        rolled_back_steps += 1
                        self.belief_bus.record_failure_witness(
                            ctx_key,
                            cmd_sig,
                            witness=str(effect_report.get("status", "EFFECT_ORACLE_FAILED")),
                        )
                        step_records.append(
                            {
                                "attempt": c_idx,
                                "action": cand_action,
                                "status": "EFFECT_ORACLE_REJECTED_ROLLED_BACK",
                                "effect_status": effect_report.get("status"),
                                "effect_verdict": effect_report.get("verdict"),
                                "isolated": True,
                                "caps_dropped": True,
                                "seccomp_installed": bool(iso_res.get("seccomp_installed")),
                            }
                        )
                        c_idx += 1
                        continue

                # 6. Directory diff contract (zero collateral file mutations)
                allowed_files = cand.get("allowed_modified_files") or step.get("allowed_modified_files")
                dir_diff: dict[str, Any] | None = None
                if allowed_files is not None:
                    post_snap = _snapshot_work_dir_bytes(wd)
                    before_h = {k: hashlib.sha256(v).hexdigest() for k, v in pre_snap.items()}
                    after_h = {k: hashlib.sha256(v).hexdigest() for k, v in post_snap.items()}
                    dir_diff = verify_directory_effect_diff(
                        before_h,
                        after_h,
                        allowed_writes=[str(x) for x in allowed_files],
                    )
                    if not dir_diff.get("pass"):
                        effect_rejections += 1
                        _restore_work_dir_bytes(wd, pre_snap)
                        rolled_back_steps += 1
                        self.belief_bus.record_failure_witness(
                            ctx_key,
                            cmd_sig,
                            witness=f"COLLATERAL_FILE_MUTATION:{dir_diff.get('unexpected_writes', [])}",
                        )
                        step_records.append(
                            {
                                "attempt": c_idx,
                                "action": cand_action,
                                "status": "COLLATERAL_MUTATION_ROLLED_BACK",
                                "dir_diff": dir_diff,
                                "isolated": True,
                                "caps_dropped": True,
                                "seccomp_installed": bool(iso_res.get("seccomp_installed")),
                            }
                        )
                        c_idx += 1
                        continue

                # Commit Petri marking, persist any verified refusal-compiled interface, and succeed
                if t_name in self.supervisor.transitions:
                    self.supervisor.fire_petri_transition(t_name)
                if cand.get("_is_refusal_retry") and isinstance(cand.get("_compiled_repair"), Mapping):
                    cr = dict(cand["_compiled_repair"])
                    self.evolved_interfaces[str(cr["tool_family"])] = {
                        "tool_family": str(cr["tool_family"]),
                        "clause_kind": str(cr["clause_kind"]),
                        "flag_added": cr.get("flag_added"),
                        "flag_removed": cr.get("flag_removed"),
                        "verified_uses": 1,
                    }
                    refusal_compiled_count += 1
                if c_idx > 0:
                    recovered_steps += 1
                step_resolved = True
                step_records.append(
                    {
                        "attempt": c_idx,
                        "action": cand_action,
                        "channel": channel,
                        "status": "EXECUTED_VERIFIED",
                        "isolated": True,
                        "caps_dropped": True,
                        "seccomp_installed": bool(iso_res.get("seccomp_installed")),
                        "seccomp_filter_sha256": iso_res.get("seccomp_filter_sha256"),
                        "compiled_interface_applied": compiled_iface_applied,
                        "namespaces": list(iso_res.get("namespaces") or ()),
                        "seconds": iso_res.get("seconds"),
                        "stdout": str(iso_res.get("stdout", ""))[:240],
                        "effect_report": effect_report,
                        "dir_diff": dir_diff,
                    }
                )
                break

            trace.append(
                {
                    "step": idx,
                    "action": action_name,
                    "resolved": step_resolved,
                    "attempts": step_records,
                }
            )
            if not step_resolved:
                all_ok = False
                break

        baseline_visual_cost = float(max(1, sum(channel_counts.values()))) * _CHANNEL_COST["visual"]
        cost_reduction_pct = round((1.0 - total_cost / max(1e-9, baseline_visual_cost)) * 100.0, 2)
        return {
            "schema": "BRAIN_CONFINED_HYBRID_CU_V1",
            "pass": bool(all_ok),
            "work_dir": str(wd),
            "steps_executed": len(trace),
            "channel_counts": channel_counts,
            "total_cost": round(total_cost, 4),
            "cost_reduction_vs_visual_only_pct": cost_reduction_pct,
            "rolled_back_steps": rolled_back_steps,
            "recovered_steps": recovered_steps,
            "effect_rejections": effect_rejections,
            "failure_gate_skips": failure_gate_skips,
            "refusal_compiled_count": refusal_compiled_count,
            "evolved_interface_hits": evolved_interface_hits,
            "evolved_interfaces": dict(self.evolved_interfaces),
            "trace": trace,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }


# ===========================================================================
# 8. Wave 37: Unified Multi-File Repo Futamura Portfolio Solver
# ===========================================================================


def _generate_extended_ast_candidates(
    source: str,
    suspect_lines: Sequence[int] | None = None,
    failure_witnesses: Sequence[str] = (),
    *,
    max_candidates: int = 96,
) -> list[tuple[str, str]]:
    """Pure-stdlib zero-LLM byte-span AST repair synthesizer covering real multi-file
    repo & QuixBugs algorithmic bug classes (relational/arithmetic/boolean/unary/
    builtin min-max/off-by-one/break-continue/operand-swap/constant tweaks)."""
    eng = ZeroOverheadCoWZygoteRepairEngine()
    base = eng.synthesize_candidates(source, list(suspect_lines or ()), list(failure_witnesses))
    seen: set[str] = {source}
    out: list[tuple[str, str]] = []
    for label, cand in base:
        if cand not in seen:
            seen.add(cand)
            out.append((label, cand))

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return out[:max_candidates]

    lines = source.splitlines(keepends=True)
    suspect_set = set(suspect_lines) if suspect_lines else set()

    def _replace_line_token(lineno: int, old: str, new: str, label: str) -> None:
        if len(out) >= max_candidates or lineno < 1 or lineno > len(lines):
            return
        line = lines[lineno - 1]
        if old in line:
            cand = "".join(lines[: lineno - 1] + [line.replace(old, new, 1)] + lines[lineno:])
            if cand not in seen:
                try:
                    ast.parse(cand)
                except SyntaxError:
                    return
                seen.add(cand)
                out.append((label, cand))

    def _replace_span(node: ast.AST, replacement: str, label: str) -> None:
        if len(out) >= max_candidates:
            return
        l1 = getattr(node, "lineno", None)
        c1 = getattr(node, "col_offset", None)
        l2 = getattr(node, "end_lineno", None)
        c2 = getattr(node, "end_col_offset", None)
        if None in (l1, c1, l2, c2) or l1 != l2:
            return
        line = lines[l1 - 1]
        new_line = line[:c1] + replacement + line[c2:]
        cand = "".join(lines[: l1 - 1] + [new_line] + lines[l1:])
        if cand not in seen:
            try:
                ast.parse(cand)
            except SyntaxError:
                return
            seen.add(cand)
            out.append((label, cand))

    def _node_src(node: ast.AST) -> str | None:
        l1 = getattr(node, "lineno", None)
        c1 = getattr(node, "col_offset", None)
        l2 = getattr(node, "end_lineno", None)
        c2 = getattr(node, "end_col_offset", None)
        if None in (l1, c1, l2, c2) or l1 != l2:
            return None
        return lines[l1 - 1][c1:c2]

    builtin_swaps = {"min": "max", "max": "min", "any": "all", "all": "any"}
    for node in ast.walk(tree):
        if len(out) >= max_candidates:
            break
        ln = getattr(node, "lineno", 0)
        if suspect_set and ln not in suspect_set:
            continue
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            fname = node.func.id
            if fname in builtin_swaps:
                _replace_span(node.func, builtin_swaps[fname], f"builtin_{fname}_to_{builtin_swaps[fname]}@L{ln}")
            if fname == "range" and len(node.args) in (1, 2):
                stop_node = node.args[-1]
                stop_src = _node_src(stop_node)
                if stop_src:
                    _replace_span(stop_node, f"({stop_src}) + 1", f"range_stop_plus1@L{ln}")
                    _replace_span(stop_node, f"({stop_src}) - 1", f"range_stop_minus1@L{ln}")
        elif isinstance(node, ast.Subscript):
            slc = _node_src(node.slice)
            if slc and ":" not in slc:
                _replace_span(node.slice, f"({slc}) - 1", f"index_minus1@L{ln}")
                _replace_span(node.slice, f"({slc}) + 1", f"index_plus1@L{ln}")
        elif isinstance(node, ast.Break):
            _replace_line_token(ln, "break", "continue", f"break_to_continue@L{ln}")
        elif isinstance(node, ast.Continue):
            _replace_line_token(ln, "continue", "break", f"continue_to_break@L{ln}")
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            inner = _node_src(node.operand)
            if inner:
                _replace_span(node, inner, f"drop_not@L{ln}")
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            inner = _node_src(node.operand)
            if inner:
                _replace_span(node, inner, f"drop_usub@L{ln}")
        elif isinstance(node, ast.Compare) and len(node.ops) == 1 and len(node.comparators) == 1:
            op = node.ops[0]
            lhs_s = _node_src(node.left)
            rhs_s = _node_src(node.comparators[0])
            if lhs_s and rhs_s:
                if isinstance(op, ast.In):
                    _replace_span(node, f"{lhs_s} not in {rhs_s}", f"in_to_not_in@L{ln}")
                elif isinstance(op, ast.NotIn):
                    _replace_span(node, f"{lhs_s} in {rhs_s}", f"not_in_to_in@L{ln}")
                elif isinstance(op, ast.Is):
                    _replace_span(node, f"{lhs_s} is not {rhs_s}", f"is_to_is_not@L{ln}")
                elif isinstance(op, ast.IsNot):
                    _replace_span(node, f"{lhs_s} is {rhs_s}", f"is_not_to_is@L{ln}")
        elif isinstance(node, ast.BinOp):
            left_s = _node_src(node.left)
            right_s = _node_src(node.right)
            if left_s and right_s:
                ext_binop_swaps = {
                    ast.Add: ("-", "*"),
                    ast.Sub: ("+", "*"),
                    ast.Mult: ("+", "-", "//", "/"),
                    ast.Div: ("*", "//", "%"),
                    ast.FloorDiv: ("/", "*", "%"),
                    ast.Mod: ("//", "/", "*"),
                }
                for alt_tok in ext_binop_swaps.get(type(node.op), ()):
                    _replace_span(node, f"({left_s}) {alt_tok} ({right_s})", f"ext_binop_{alt_tok}@L{ln}")
                if left_s != right_s and isinstance(node.op, (ast.Sub, ast.Div, ast.FloorDiv, ast.Mod)):
                    op_tok = {ast.Sub: "-", ast.Div: "/", ast.FloorDiv: "//", ast.Mod: "%"}[type(node.op)]
                    _replace_span(node, f"({right_s}) {op_tok} ({left_s})", f"swap_binop_operands@L{ln}")
        elif isinstance(node, ast.Constant) and isinstance(node.value, int) and not isinstance(node.value, bool):
            if -2 <= node.value <= 2:
                for delta in (1, -1):
                    _replace_span(node, str(node.value + delta), f"int_const_{node.value}_to_{node.value + delta}@L{ln}")
    return out[:max_candidates]


class MultifileFutamuraRepoSolver:
    """Unified multi-file Python repository repair solver uniting:
    - Rung 0: Alpha-normalized compiled Futamura AST rules (< 2 ms scan across repo files)
    - Pure-stdlib `os.fork()` CoW overlay execution (`stdlib_cow_test_runner_v1`) — ZERO disk mutation on screen
    - Multi-file dynamic coverage localization (`capture_frames=True` -> covered suspect lines)
    - Extended zero-LLM byte-span AST repair synthesis (single-file + 2-file coordinated edits)
      + optional `#7130` 96-organ epistemic portfolio fallback
    - Ring-0 Gate: atomic `ddmin_minimize_hunks` + `audit_patch_mutation_kill` + `verify_directory_effect_diff`
      + `ConformalEValueGate` (`alpha=0.05`) + `PreCommitFailureGate`
    - Automatic Futamura Compile-Back: verified multi-file repairs compile directly into Rung-0 rules
      so unseen isomorphic multi-file repos solve at Rung 0 with 0 search & 0 LLM calls.
    """

    def __init__(self, *, cascade: FutamuraSelfCompilingCascade | None = None) -> None:
        self.cascade = cascade or FutamuraSelfCompilingCascade()

    @staticmethod
    def _is_test_rel(rel: str, test_targets: Sequence[str]) -> bool:
        norm = rel.replace("\\", "/")
        if norm in {str(t).replace("\\", "/") for t in test_targets}:
            return True
        name = Path(norm).name
        parts = set(Path(norm).parts)
        return name.startswith("test_") or name.endswith("_test.py") or "tests" in parts

    @staticmethod
    def _discover_repo_py_files(repo_dir: Path, test_targets: Sequence[str]) -> list[str]:
        rels: list[str] = []
        for p in sorted(repo_dir.rglob("*.py")):
            rel = str(p.relative_to(repo_dir)).replace("\\", "/")
            if any(seg.startswith(".") or seg == "__pycache__" for seg in Path(rel).parts):
                continue
            if MultifileFutamuraRepoSolver._is_test_rel(rel, test_targets):
                continue
            rels.append(rel)
        return rels

    def _try_rung0_on_source(self, source: str) -> list[tuple[str, str]]:
        """Yield `(rule_id, patched_source)` matches from compiled Rung-0 alpha-normalized rules."""
        if not self.cascade._rung0_by_key:
            return []
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []
        matches: list[tuple[str, str]] = []
        seen: set[str] = {source}
        for node in ast.walk(tree):
            if not hasattr(node, "lineno") or not hasattr(node, "end_lineno"):
                continue
            pkey = _preorder_signature(node)
            rules = self.cascade._rung0_by_key.get(pkey)
            if not rules:
                continue
            for rule in rules:
                if rule.quarantined or rule.rubin_tau_hat <= 0.0:
                    continue
                bindings: dict[str, ast.AST] = {}
                if not _match_template(rule.before_ast, node, bindings):
                    continue
                instantiated = _instantiate_template(rule.after_ast, bindings)
                cand_src = splice_ast_byte_span(source, node, ast.unparse(instantiated))
                if cand_src not in seen:
                    seen.add(cand_src)
                    matches.append((rule.rule_id, cand_src))
        return matches

    def solve(
        self,
        repo_dir: str | Path,
        test_targets: Sequence[str],
        *,
        goal_text: str = "",
        suspect_files: Sequence[str] | None = None,
        auto_compile: bool = True,
        apply_to_disk: bool = True,
        use_portfolio_fallback: bool = False,
        use_residual_wall_closers: bool = True,
        use_repo_component_petri: bool = True,
        reject_vacuous_verifier: bool = False,
        untrusted_proposer: Callable[[Mapping[str, Any]], Sequence[Mapping[str, str]]] | None = None,
        alpha: float = 0.05,
        timeout_s: float = 10.0,
        max_candidates_per_file: int = 96,
    ) -> dict[str, Any]:
        from canonical.swe_kernel import stdlib_cow_test_runner_v1 as cow_tr

        t0 = time.perf_counter()
        root = Path(repo_dir).resolve()
        targets = [str(t) for t in test_targets]
        if not targets:
            targets = sorted(
                str(p.relative_to(root)).replace("\\", "/")
                for p in root.rglob("test_*.py")
            )

        # 0. Baseline CoW fork test + Anti-Vacuous Verifier Audit (`judge_the_judge` principle)
        base_res = cow_tr.run_targets_cow_fork(root, targets, timeout_s=timeout_s, capture_frames=True)
        if base_res.get("ok"):
            if reject_vacuous_verifier:
                return {
                    "schema": "BRAIN_MULTIFILE_FUTAMURA_SOLVE_V1",
                    "pass": False,
                    "rung": "FAIL_CLOSED__VACUOUS_VERIFIER_ALREADY_PASSES",
                    "vacuous_verifier": True,
                    "repo_dir": str(root),
                    "modified_files": [],
                    "candidates_evaluated": 0,
                    "proposer_calls": 0,
                    "compiled_rules_total": len(self.cascade._rules_by_id),
                    "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
                }
            return {
                "schema": "BRAIN_MULTIFILE_FUTAMURA_SOLVE_V1",
                "pass": True,
                "rung": "ALREADY_PASSING",
                "vacuous_verifier": True,
                "repo_dir": str(root),
                "modified_files": [],
                "candidates_evaluated": 0,
                "proposer_calls": 0,
                "compiled_rules_total": len(self.cascade._rules_by_id),
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            }

        failure_witnesses = [str(base_res.get("output") or "")]
        covered_map: dict[str, set[int]] = {}
        for k, line_list in (base_res.get("covered_lines") or {}).items():
            norm_k = str(k).replace("\\", "/")
            if not self._is_test_rel(norm_k, targets) and (root / norm_k).is_file():
                covered_map[norm_k] = {int(ln) for ln in line_list if int(ln) > 0}

        all_py = self._discover_repo_py_files(root, targets)
        ordered_files: list[str] = []
        if suspect_files:
            for sf in suspect_files:
                s = str(sf).replace("\\", "/")
                if (root / s).is_file() and s not in ordered_files:
                    ordered_files.append(s)
        for rel in sorted(covered_map, key=lambda r: (Path(r).name == "__init__.py", -len(covered_map[r]), r)):
            if rel not in ordered_files:
                ordered_files.append(rel)
        for rel in all_py:
            if rel not in ordered_files:
                ordered_files.append(rel)

        orig_sources = {rel: (root / rel).read_text(encoding="utf-8") for rel in ordered_files}
        candidates_evaluated = 0
        failure_gate_skips = 0
        proposer_calls = 0
        wall_mechanism = ""
        winning_overlays: dict[str, str] | None = None
        winning_rung = "NONE"
        winning_rule_id = ""

        # 1. Rung 0: Fast multi-file Futamura compiled skill scan (< 2 ms lookup)
        t_r0 = time.perf_counter()
        if self.cascade._rung0_by_key:
            for rel in ordered_files:
                src = orig_sources[rel]
                src_sig = hashlib.sha256(src.encode("utf-8")).hexdigest()[:16]
                r0_matches = self._try_rung0_on_source(src)
                for rule_id, cand_src in r0_matches:
                    p_sig = hashlib.sha256(f"{rel}:{cand_src}".encode("utf-8")).hexdigest()[:16]
                    if not self.cascade.belief_bus.check_pre_commit_gate(src_sig, p_sig)["allowed"]:
                        failure_gate_skips += 1
                        continue
                    candidates_evaluated += 1
                    rule = self.cascade._rules_by_id.get(rule_id)
                    if rule is not None:
                        rule.hits += 1
                    chk = cow_tr.run_targets_cow_fork(
                        root, targets, overlays={rel: cand_src}, timeout_s=timeout_s
                    )
                    if chk.get("ok"):
                        if rule is not None:
                            rule.successes += 1
                        winning_overlays = {rel: cand_src}
                        winning_rung = "RUNG_0_COMPILED_SKILL"
                        winning_rule_id = rule_id
                        break
                    if rule is not None:
                        rule.failures += 1
                    self.cascade.belief_bus.record_failure_witness(
                        src_sig, p_sig, witness="RUNG0_OVERLAY_FAIL"
                    )
                if winning_overlays is not None:
                    break
        rung0_ms = round((time.perf_counter() - t_r0) * 1000.0, 3)

        # 2. Rung 2: Multi-file dynamic coverage + extended AST synthesis in pure-RAM CoW overlay
        screen_timeout_s = min(float(timeout_s), 1.5)
        if winning_overlays is None:
            per_file_cands: dict[str, list[tuple[str, str]]] = {}
            for rel in ordered_files:
                src = orig_sources[rel]
                sus_lines = sorted(covered_map.get(rel) or ())
                cands = _generate_extended_ast_candidates(
                    src,
                    suspect_lines=sus_lines or None,
                    failure_witnesses=failure_witnesses,
                    max_candidates=max_candidates_per_file,
                )
                if not cands and sus_lines:
                    cands = _generate_extended_ast_candidates(
                        src,
                        suspect_lines=None,
                        failure_witnesses=failure_witnesses,
                        max_candidates=max_candidates_per_file,
                    )
                per_file_cands[rel] = cands
                src_sig = hashlib.sha256(src.encode("utf-8")).hexdigest()[:16]
                for _label, cand_src in cands:
                    p_sig = hashlib.sha256(f"{rel}:{cand_src}".encode("utf-8")).hexdigest()[:16]
                    if not self.cascade.belief_bus.check_pre_commit_gate(src_sig, p_sig)["allowed"]:
                        failure_gate_skips += 1
                        continue
                    candidates_evaluated += 1
                    chk = cow_tr.run_targets_cow_fork(
                        root, targets, overlays={rel: cand_src}, timeout_s=screen_timeout_s
                    )
                    if chk.get("ok"):
                        winning_overlays = {rel: cand_src}
                        winning_rung = "RUNG_2_MULTIFILE_COW_AST"
                        break
                    self.cascade.belief_bus.record_failure_witness(
                        src_sig, p_sig, witness="COW_OVERLAY_FAIL"
                    )
                if winning_overlays is not None:
                    break

            # 2b. Coordinated 2-file edit search (for genuine multi-file coupled bugs!)
            if winning_overlays is None and len(ordered_files) >= 2:
                top_files = [f for f in ordered_files if per_file_cands.get(f)][:4]
                for i in range(len(top_files)):
                    if winning_overlays is not None:
                        break
                    fa = top_files[i]
                    for j in range(i + 1, len(top_files)):
                        if winning_overlays is not None:
                            break
                        fb = top_files[j]
                        for _la, ca in per_file_cands[fa][:16]:
                            if winning_overlays is not None:
                                break
                            for _lb, cb in per_file_cands[fb][:16]:
                                candidates_evaluated += 1
                                chk = cow_tr.run_targets_cow_fork(
                                    root,
                                    targets,
                                    overlays={fa: ca, fb: cb},
                                    timeout_s=screen_timeout_s,
                                )
                                if chk.get("ok"):
                                    winning_overlays = {fa: ca, fb: cb}
                                    winning_rung = "RUNG_2_MULTIFILE_COORDINATED_AST"
                                    break

            # 2b-bis (Wave 38): Unwired 13-law Statement-Shaped Residual Wall Closers (`residual_wall_closers_v1`)
            if winning_overlays is None and use_residual_wall_closers:
                try:
                    from canonical.swe_kernel import residual_wall_closers_v1 as rwc

                    closer = rwc.ResidualWallCloser()
                    repo_src_list = [orig_sources[r] for r in ordered_files]
                    test_src_list: list[str] = []
                    for t_rel in targets:
                        tp = root / t_rel
                        if tp.is_file():
                            test_src_list.append(tp.read_text(encoding="utf-8", errors="replace"))
                    for rel in ordered_files[:8]:
                        if winning_overlays is not None:
                            break
                        src = orig_sources[rel]
                        src_sig = hashlib.sha256(src.encode("utf-8")).hexdigest()[:16]
                        try:
                            mod_tree = ast.parse(src)
                        except SyntaxError:
                            continue
                        func_names = list(rwc._functions(mod_tree).keys())
                        seen_wall: set[str] = {src}
                        for fn_name in func_names[:24]:
                            if winning_overlays is not None:
                                break
                            wall_cands = closer.mine_all(
                                src,
                                fn_name,
                                functions=func_names,
                                repo_sources=repo_src_list,
                                test_sources=test_src_list,
                            )
                            for wc in wall_cands[:32]:
                                cand_src = str(getattr(wc, "patched_module_source", "") or "")
                                if not cand_src or cand_src in seen_wall:
                                    continue
                                seen_wall.add(cand_src)
                                p_sig = hashlib.sha256(f"{rel}:{cand_src}".encode("utf-8")).hexdigest()[:16]
                                if not self.cascade.belief_bus.check_pre_commit_gate(src_sig, p_sig)["allowed"]:
                                    failure_gate_skips += 1
                                    continue
                                candidates_evaluated += 1
                                chk = cow_tr.run_targets_cow_fork(
                                    root, targets, overlays={rel: cand_src}, timeout_s=screen_timeout_s
                                )
                                if chk.get("ok"):
                                    winning_overlays = {rel: cand_src}
                                    winning_rung = "RUNG_2B_RESIDUAL_WALL_CLOSER"
                                    wall_mechanism = str(getattr(wc, "mechanism", "") or "")
                                    break
                                self.cascade.belief_bus.record_failure_witness(
                                    src_sig, p_sig, witness="RESIDUAL_WALL_OVERLAY_FAIL"
                                )
                except Exception:
                    pass

            # 2b-ter (Wave 38): Unwired Repo-Native Component Petri-Net Synthesis (`repo_component_petri_v1`)
            if winning_overlays is None and use_repo_component_petri:
                try:
                    import re as _re
                    from canonical.swe_kernel import repo_component_petri_v1 as rcp

                    failing_nodeids = [str(n) for n in (base_res.get("failed_nodeids") or targets)]
                    called_syms, _lit_vals = rcp.extract_test_called_symbols_and_literals(root, failing_nodeids)
                    spec_lits = set(rcp.extract_test_spec_literals(root, failing_nodeids))
                    err_text = "\n".join(failure_witnesses)
                    esc_excs: list[dict[str, Any]] = []
                    for m_exc in _re.finditer(r"\b([A-Z][A-Za-z0-9_]*(?:Error|Exception|Warning))\b", err_text):
                        ename = m_exc.group(1)
                        if all(e.get("exc_type") != ename for e in esc_excs):
                            esc_excs.append({"exc_type": ename, "message": err_text[:200]})
                    for rel in ordered_files[:6]:
                        if winning_overlays is not None:
                            break
                        src = orig_sources[rel]
                        src_sig = hashlib.sha256(src.encode("utf-8")).hexdigest()[:16]
                        try:
                            parsed = ast.parse(src)
                        except SyntaxError:
                            continue
                        sus_lines = list(sorted(covered_map.get(rel) or ()))[:12]
                        for n in ast.walk(parsed):
                            if isinstance(n, (ast.Try, ast.Return, ast.Raise)):
                                ln_n = int(getattr(n, "lineno", 1))
                                if ln_n not in sus_lines:
                                    sus_lines.append(ln_n)
                        sus_lines = sus_lines[:16]
                        seen_petri: set[str] = {src}
                        for ln in sus_lines:
                            if winning_overlays is not None:
                                break
                            petri_cands, _n_mined = rcp.synthesize_repo_petri_repairs(
                                repo_root=root,
                                rel_path=rel,
                                source_text=src,
                                line_no=int(ln),
                                pass_samples=[],
                                fail_samples=[],
                                escaping_exceptions=esc_excs,
                                spec_literals=spec_lits,
                                called_symbols=called_syms,
                                parsed_tree=parsed,
                            )
                            for cand_src, label in petri_cands[:24]:
                                if not cand_src or cand_src in seen_petri:
                                    continue
                                seen_petri.add(cand_src)
                                p_sig = hashlib.sha256(f"{rel}:{cand_src}".encode("utf-8")).hexdigest()[:16]
                                if not self.cascade.belief_bus.check_pre_commit_gate(src_sig, p_sig)["allowed"]:
                                    failure_gate_skips += 1
                                    continue
                                candidates_evaluated += 1
                                chk = cow_tr.run_targets_cow_fork(
                                    root, targets, overlays={rel: cand_src}, timeout_s=screen_timeout_s
                                )
                                if chk.get("ok"):
                                    winning_overlays = {rel: cand_src}
                                    winning_rung = "RUNG_2C_REPO_COMPONENT_PETRI"
                                    wall_mechanism = str(label)
                                    break
                                self.cascade.belief_bus.record_failure_witness(
                                    src_sig, p_sig, witness="REPO_PETRI_OVERLAY_FAIL"
                                )
                except Exception:
                    pass

            # 2c. Optional fallback to #7130 96-Organ Epistemic Portfolio
            if winning_overlays is None and use_portfolio_fallback:
                try:
                    from canonical.swe_kernel import unified_epistemic_portfolio_v1 as uep

                    pre_snap = _snapshot_work_dir_bytes(root)
                    p_res = uep.run_unified_epistemic_portfolio(
                        workspace_dir=root,
                        goal_text=goal_text or f"repair {targets}",
                        pytest_targets=targets,
                        suspect_files=ordered_files[:6],
                        timeout_s=timeout_s,
                    )
                    post_snap = _snapshot_work_dir_bytes(root)
                    if p_res.get("ok") or p_res.get("repaired"):
                        diff_ov: dict[str, str] = {}
                        for rel in ordered_files:
                            if post_snap.get(rel) != pre_snap.get(rel) and rel in post_snap:
                                diff_ov[rel] = post_snap[rel].decode("utf-8", errors="replace")
                        _restore_work_dir_bytes(root, pre_snap)
                        if diff_ov:
                            chk = cow_tr.run_targets_cow_fork(root, targets, overlays=diff_ov, timeout_s=timeout_s)
                            if chk.get("ok"):
                                winning_overlays = diff_ov
                                winning_rung = "RUNG_2_EPISTEMIC_PORTFOLIO_96"
                    else:
                        _restore_work_dir_bytes(root, pre_snap)
                except Exception:
                    pass

            # 2d (Wave 38): Optional Pluggable Guidance-TTT Untrusted Proposer Slot (Rung 3, default None -> K3=0)
            if winning_overlays is None and callable(untrusted_proposer):
                proposer_calls += 1
                prop_ctx = {
                    "repo_dir": str(root),
                    "goal_text": goal_text,
                    "test_targets": targets,
                    "suspect_files": ordered_files[:8],
                    "sources": {r: orig_sources[r] for r in ordered_files[:8]},
                    "failure_witnesses": failure_witnesses,
                }
                try:
                    proposals = list(untrusted_proposer(prop_ctx) or ())
                except Exception:
                    proposals = []
                for prop in proposals[:16]:
                    if not isinstance(prop, Mapping):
                        continue
                    ov = {
                        str(k).replace("\\", "/"): str(v)
                        for k, v in prop.items()
                        if str(k).replace("\\", "/") in orig_sources
                    }
                    if not ov:
                        continue
                    candidates_evaluated += 1
                    chk = cow_tr.run_targets_cow_fork(root, targets, overlays=ov, timeout_s=timeout_s)
                    if chk.get("ok"):
                        winning_overlays = ov
                        winning_rung = "RUNG_3_GUIDANCE_PROPOSER_COMPILED"
                        break

        if winning_overlays is None:
            return {
                "schema": "BRAIN_MULTIFILE_FUTAMURA_SOLVE_V1",
                "pass": False,
                "rung": "UNSOLVED",
                "vacuous_verifier": False,
                "repo_dir": str(root),
                "suspect_files": ordered_files,
                "modified_files": [],
                "candidates_evaluated": candidates_evaluated,
                "failure_gate_skips": failure_gate_skips,
                "proposer_calls": proposer_calls,
                "compiled_rules_total": len(self.cascade._rules_by_id),
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            }

        # 3. Ring-0 Gate: atomic ddmin + touched-line mutation kill + ConformalEValueGate
        minimized_overlays: dict[str, str] = dict(winning_overlays)
        ddmin_reports: dict[str, Any] = {}
        mutation_reports: dict[str, Any] = {}
        egate = ConformalEValueGate(alpha=alpha)
        egate.observe("cow_overlay_suite_pass", passed=True, null_pass_prob=0.10)

        for rel in sorted(winning_overlays):
            before_src = orig_sources[rel]
            after_src = minimized_overlays[rel]
            other_ov = {k: v for k, v in minimized_overlays.items() if k != rel}

            def _make_oracle(r_key: str, others: dict[str, str]) -> Callable[[str], bool]:
                def _oracle(cand_text: str) -> bool:
                    ov = dict(others)
                    ov[r_key] = cand_text
                    return bool(cow_tr.run_targets_cow_fork(root, targets, overlays=ov, timeout_s=timeout_s).get("ok"))
                return _oracle

            file_oracle = _make_oracle(rel, other_ov)
            dd = ddmin_minimize_hunks(before_src, after_src, file_oracle)
            minimized_overlays[rel] = str(dd["minimized_source"])
            ddmin_reports[rel] = {
                "original_hunks": dd["original_hunk_count"],
                "minimized_hunks": dd["minimized_hunk_count"],
                "hunks_removed": dd["pruned_hunk_count"],
            }
            mut = audit_patch_mutation_kill(before_src, minimized_overlays[rel], file_oracle, max_mutants=8)
            mutation_reports[rel] = {
                "mutants_generated": mut["mutants_tested"],
                "mutants_killed": mut["mutants_killed"],
                "kill_rate": mut["mutation_kill_ratio"],
            }
            if mut["mutants_tested"] > 0:
                egate.observe(
                    f"mutation_kill:{rel}",
                    passed=bool(mut["mutation_kill_ratio"] >= 0.5),
                    null_pass_prob=0.25,
                )

        # 4. Atomic disk commit + directory diff invariance + fresh on-disk re-verification
        dir_diff_report: dict[str, Any] | None = None
        if apply_to_disk:
            snap_before = snapshot_directory_hashes(root)
            for rel, new_src in minimized_overlays.items():
                (root / rel).write_text(new_src, encoding="utf-8")
            snap_after = snapshot_directory_hashes(root)
            dir_diff_report = verify_directory_effect_diff(
                snap_before,
                snap_after,
                allowed_writes=sorted(minimized_overlays),
            )
            # Invalidate stale CPython .pyc caches (same-second + same-size edits hit stale bytecode!)
            for rel in minimized_overlays:
                p_mod = root / rel
                pycache = p_mod.parent / "__pycache__"
                if pycache.is_dir():
                    for pyc in pycache.glob(f"{p_mod.stem}.*.pyc"):
                        pyc.unlink(missing_ok=True)
            fresh_chk = cow_tr.run_targets_cow_fork(root, targets, timeout_s=timeout_s)
            egate.observe(
                "fresh_disk_reverify",
                passed=bool(fresh_chk.get("ok") and dir_diff_report.get("pass")),
                null_pass_prob=0.10,
                hard_contradiction=not bool(fresh_chk.get("ok") and dir_diff_report.get("pass")),
            )
            if not (fresh_chk.get("ok") and dir_diff_report.get("pass")):
                for rel in minimized_overlays:
                    (root / rel).write_text(orig_sources[rel], encoding="utf-8")
                return {
                    "schema": "BRAIN_MULTIFILE_FUTAMURA_SOLVE_V1",
                    "pass": False,
                    "rung": "RING0_DISK_VERIFY_REJECTED",
                    "dir_diff": dir_diff_report,
                    "conformal": egate.decision(),
                    "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
                }

        # 5. Futamura Compile-Back: compile every verified file diff into Rung-0 alpha-normalized rules
        compiled_rule_ids: list[str] = []
        if auto_compile and winning_rung != "RUNG_0_COMPILED_SKILL":
            for rel, new_src in sorted(minimized_overlays.items()):
                rec = self.cascade.compile_verified_win_to_rung0(
                    orig_sources[rel],
                    new_src,
                    source_rung=2,
                )
                if rec.get("compiled") and rec.get("rule_id"):
                    compiled_rule_ids.append(str(rec["rule_id"]))

        return {
            "schema": "BRAIN_MULTIFILE_FUTAMURA_SOLVE_V1",
            "pass": True,
            "rung": winning_rung,
            "vacuous_verifier": False,
            "wall_mechanism": wall_mechanism,
            "winning_rule_id": winning_rule_id,
            "compiled_rule_ids": compiled_rule_ids,
            "compiled_rules_total": len(self.cascade._rules_by_id),
            "repo_dir": str(root),
            "modified_files": sorted(minimized_overlays),
            "candidates_evaluated": candidates_evaluated,
            "failure_gate_skips": failure_gate_skips,
            "proposer_calls": proposer_calls,
            "rung0_ms": rung0_ms,
            "ddmin": ddmin_reports,
            "mutation_audit": mutation_reports,
            "dir_diff": dir_diff_report,
            "conformal": egate.decision(),
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }


def solve_typed_cegis_and_concepts(
    spec: Mapping[str, Any],
    *,
    max_depth: int = 3,
    max_iter: int = 20,
    type_env: Mapping[str, str] | None = None,
    concepts: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Wave 38 unified entry over Project Brain's previously unwired synthesis trilogy:
    1. `typed_invention_v1.typed_cegis_synthesize` (type-pruned CEGIS(T))
    2. `composition_concept_bridge_v1.synthesize_with_concepts` (multi-concept composition)
    3. `adaptive_constant_concept_bridge_v1.synthesize_adaptive` (constant-invention V9 bridge)
    Zero model calls (`K3 = 0`), `$0` spend.
    """
    t0 = time.perf_counter()
    from canonical.swe_kernel import typed_invention_v1 as ti

    def _is_solved(out: Mapping[str, Any] | None) -> bool:
        if not isinstance(out, Mapping):
            return False
        return bool(out.get("verified") or out.get("solved") or str(out.get("status", "")).startswith("PASS"))

    res = ti.typed_cegis_synthesize(
        spec,
        max_depth=max_depth,
        max_iter=max_iter,
        type_env=type_env,
    )
    stage = "TYPED_CEGIS_T"
    if not _is_solved(res) and concepts:
        from canonical.swe_kernel import composition_concept_bridge_v1 as ccb

        c_res = ccb.synthesize_with_concepts(
            spec,
            max_depth=max_depth,
            max_iter=max_iter,
            concepts=concepts,
            type_env=type_env,
        )
        if _is_solved(c_res):
            res = c_res
            stage = "COMPOSITION_CONCEPT_BRIDGE"
    if not _is_solved(res):
        from canonical.swe_kernel import adaptive_constant_concept_bridge_v1 as acb

        a_res = acb.synthesize_adaptive(spec, max_depth=max(4, max_depth))
        if _is_solved(a_res):
            res = a_res
            stage = "ADAPTIVE_CONSTANT_V9_BRIDGE"
    return {
        "schema": "BRAIN_TYPED_CEGIS_CONCEPT_SOLVE_V1",
        "pass": _is_solved(res),
        "stage": stage,
        "result": dict(res),
        "model_calls": 0,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
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
    if op == "multifile_repo_solve":
        cascade = payload.get("cascade") if isinstance(payload.get("cascade"), FutamuraSelfCompilingCascade) else shared_futamura_cascade()
        solver = MultifileFutamuraRepoSolver(cascade=cascade)
        return solver.solve(
            payload["repo_dir"],
            list(payload.get("test_targets") or ()),
            goal_text=str(payload.get("goal_text") or ""),
            suspect_files=payload.get("suspect_files"),
            auto_compile=bool(payload.get("auto_compile", True)),
            apply_to_disk=bool(payload.get("apply_to_disk", True)),
            use_portfolio_fallback=bool(payload.get("use_portfolio_fallback", False)),
            use_residual_wall_closers=bool(payload.get("use_residual_wall_closers", True)),
            use_repo_component_petri=bool(payload.get("use_repo_component_petri", True)),
            reject_vacuous_verifier=bool(payload.get("reject_vacuous_verifier", False)),
            untrusted_proposer=payload.get("untrusted_proposer"),
            alpha=float(payload.get("alpha", 0.05)),
        )
    if op == "typed_cegis_solve":
        return solve_typed_cegis_and_concepts(
            dict(payload.get("spec") or payload),
            max_depth=int(payload.get("max_depth", 3)),
            max_iter=int(payload.get("max_iter", 20)),
            type_env=payload.get("type_env"),
            concepts=payload.get("concepts"),
        )
    if op == "confined_hybrid_cu":
        ex = ConfinedHybridComputerUseExecutor(webmcp_tools=payload.get("webmcp_tools"))
        return ex.execute_episode(
            payload["work_dir"],
            list(payload.get("steps") or ()),
            goal_id=str(payload.get("goal_id") or "confined_hcu_episode"),
            budget_s=float(payload.get("budget_s", 15.0)),
            allow_network=bool(payload.get("allow_network", False)),
            verify_effect=bool(payload.get("verify_effect", True)),
            seccomp=bool(payload.get("seccomp", True)),
            auto_compile_refusal=bool(payload.get("auto_compile_refusal", True)),
        )
    if op == "probe_os_isolation":
        return ConfinedHybridComputerUseExecutor.probe_isolation(
            budget_s=float(payload.get("budget_s", 30.0)),
            seccomp=bool(payload.get("seccomp", True)),
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


# ===========================================================================
# 7. Self-check: the anytime-validity claim, measured
# ===========================================================================


def self_check() -> dict[str, Any]:
    """Test the one claim everything else in this kernel inherits: anytime-validity.

    "Anytime-valid" is not a description, it is an inequality: under the null the e-process must
    cross `1 / alpha` with probability at most `alpha`, at *any* stopping time. Three checks make
    that falsifiable here -- the per-step factor must have null expectation exactly 1, the
    empirical breach rate over seeded null runs must sit inside the Ville bound, and the gate must
    still commit quickly against a real signal (or the guarantee would be bought by being useless).
    The hard-contradiction check is the safety direction: a witness outranks accumulated evidence.
    """
    import random as _random

    failures: list[str] = []

    def check(label: str, ok: bool) -> None:
        if not ok:
            failures.append(label)

    # 1. E_H0[factor] == 1 for any p0 -- the identity the docstring asserts.
    for p0 in (0.05, 0.25, 0.5, 0.9):
        eps = 0.05
        expectation = p0 * ((1.0 - eps) / p0) + (1.0 - p0) * (eps / (1.0 - p0))
        check(f"null expectation is 1 at p0={p0}", abs(expectation - 1.0) < 1e-9)

    # 2. Ville bound under the null, seeded so the check is reproducible.
    alpha, trials, horizon = 0.05, 400, 60
    rng = _random.Random(20261126)
    breaches = 0
    for _ in range(trials):
        gate = ConformalEValueGate(alpha=alpha)
        for step in range(horizon):
            decision = gate.observe(f"null_{step}", passed=rng.random() < 0.25,
                                    null_pass_prob=0.25)
            if decision["verdict"] == "COMMIT":
                breaches += 1
                break
    breach_rate = breaches / trials
    sigma = (alpha * (1.0 - alpha) / trials) ** 0.5
    check("null breach rate stays inside the Ville bound",
          breach_rate <= alpha + 3.0 * sigma)

    # 3. The guarantee must not be bought by never committing: a real signal commits fast.
    worst = 0
    for seed in range(20):
        r = _random.Random(seed)
        gate = ConformalEValueGate(alpha=alpha)
        committed_at = None
        for step in range(40):
            if gate.observe(f"signal_{step}", passed=r.random() < 0.90,
                            null_pass_prob=0.25)["verdict"] == "COMMIT":
                committed_at = step + 1
                break
        worst = max(worst, committed_at or 99)
    check("a true signal commits within 12 observations", worst <= 12)

    # 4. Safety direction: a hard contradiction outranks accumulated evidence.
    gate = ConformalEValueGate(alpha=alpha)
    for step in range(10):
        gate.observe(f"pass_{step}", passed=True, null_pass_prob=0.25)
    check("accumulated evidence alone reaches COMMIT", gate.decision()["verdict"] == "COMMIT")
    gate.observe("witness", passed=False, null_pass_prob=0.25, hard_contradiction=True)
    final = gate.decision()
    check("a hard contradiction revokes the commit",
          final["verdict"] == "ABSTAIN_FAIL_CLOSED"
          and final["reason"] == "HARD_CONTRADICTION_WITNESS")

    # 5. Determinism: the same observations must give the same verdict.
    left, right = ConformalEValueGate(alpha=alpha), ConformalEValueGate(alpha=alpha)
    for step in range(6):
        a = left.observe(f"s{step}", passed=step % 2 == 0, null_pass_prob=0.25)
        b = right.observe(f"s{step}", passed=step % 2 == 0, null_pass_prob=0.25)
    check("identical observations give identical decisions", a["log_e"] == b["log_e"])

    total = 10
    return {
        "schema": "BRAIN_FUTAMURA_LEAPFROG_KERNEL_V1_SELF_CHECK",
        "checks": total,
        "passed": total - len(failures),
        "breach_rate": round(breach_rate, 4),
        "failures": failures,
        "verdict": "SELF_CHECK_PASS" if not failures else "SELF_CHECK_FAIL",
    }
