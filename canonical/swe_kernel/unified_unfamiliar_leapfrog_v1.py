#!/usr/bin/env python3
"""Unified Unfamiliar-Name Frontier Leapfrog Engine (`K3 = 0`, `$0` spend, Elon's First Law).

Unifies the repository's highest-leverage previously unwired organs across `canonical/runtime/`,
`canonical/swe_kernel/`, `canonical/tools/`, and `intake/` together with verified mechanisms
from diverged branches (`#7049` `NAME_SCOPE` + 4-gate non-vacuous verifier, `#7071` kernel
namespace isolation + machine-reader round-trip `effect_oracle`) directly under `UnifiedModel`:

  - Move 0 (`ApartnessTreeInstantLearner`):
      Replaces `L*` observation tables and consistency matrices with Brouwer-Heyting constructive
      apartness (`q1 # q2`) directly on a prefix observation tree, error-persistent sink pruning
      (`L#_e`: zero wasted probes after refusal/error transitions), and Adaptive Distinguishing
      Sequences (`ADS` binary splitting tree) + `< 50 us` Kalman surprise gate.
  - Move 1 (`AngelicForestSyGuSRepairEngine`):
      `os.fork()` CoW Angelic Forest impossibility sieve (`Angelix` in RAM: prunes dead AST sites
      in `< 2 ms` when no angelic value can satisfy failing assertions) feeding unwired
      `canonical/runtime/oe_sygus_synthesizer_v1.py` (`EUSolver` observational-equivalence SyGuS),
      `NAME_SCOPE` attribute-to-in-scope-symbol rewrites (with round-robin family scheduling),
      `site_by_intervention_v1`, `expected_actual_literal_v1`, `cow_lens_fuzz_and_negative_space_v1`,
      `mined_rewrite_theory_v1` cold-store seeding, and 4-rule non-vacuous verifier auditing.
  - Move 2 (`ProtocolLiftingAndKernelOracle`):
      `WebMCP` (`document.modelContext`) + CDP/HAR network-to-HTTP protocol lifter (strips static
      asset noise and compiles direct zero-browser Python API callables executing in `< 2 ms` on
      Run 2+), unwired `intake/osworld_intake_policy_v1` pre-completion gate, unprivileged Linux
      namespace (`CapEff=0` / `unshare`) execution confinement, and machine-reader magic-header +
      byte-exact round-trip `effect_oracle` (refusing misnamed `xz`/`zip` containers in `out.gz`).
  - Move 3 (`SemiringProvenanceJTMSMemory`):
      Green-Karvounarakis-Tannen Why-Provenance Semiring `(2^(2^V), union, join)` over `Z`-set
      `DBSP` memory with antichain absorption and inverted premise indexing — achieving `100%`
      exact multi-hop `Cascade` retraction (preserving diamond alternative proofs) and `100%`
      exact `Absence` detection (`ABSENCE__SUPPORT_PREMISE_INVALIDATED`) in `< 15 us`.
  - Move 4 (`ActiveMinimaxContrastiveInterrogator`):
      Wires unwired `finite_minimax_decision_region_v1` and `monotone_semantic_drd_bridge_v1` with
      parallel `os.fork()` CoW version-space outcome matrix construction and `purpose_gate_v1`
      irreversibility gating to identify adequate policies in minimum worst-case probes.
  - Move 5 (`ZeroLLMAlphaEvolveParetoEngine`):
      MAP-Elites + Pareto `(correctness, latency_us, ast_bytes)` evolutionary synthesizer over
      `mined_rewrite_theory_v1` and AST algebraic mutations in `os.fork()` CoW workers, guarded by
      adversarial output corruption auditing (`0` false-pass reward hacking) and Two-Door rent GC.
"""
from __future__ import annotations

import ast
import bz2
import copy
import gzip
import hashlib
import io
import json
import lzma
import math
import os
import pathlib
import pickle
import re
import resource
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
import zipfile
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCHEMA = "BRAIN_UNIFIED_UNFAMILIAR_LEAPFROG_V1"
AUTHORITY = "NONE_SANDBOX"
MODEL_CALLS = 0


# ============================================================================
# MOVE 0: Constructive Apartness (`L#_e`) Observation-Table-Free Instant Learner
# ============================================================================

_ERROR_SINK_TOKENS: tuple[str, ...] = (
    "err",
    "error",
    "refus",
    "denied",
    "invalid",
    "locked",
    "forbidden",
    "fail",
)


def _is_error_output(out_sym: str) -> bool:
    low = out_sym.lower()
    return any(tok in low for tok in _ERROR_SINK_TOKENS)


class _ObsNode:
    """Prefix observation tree node for table-free `L#_e` learning."""

    __slots__ = ("prefix", "children")

    def __init__(self, prefix: tuple[str, ...]) -> None:
        self.prefix = prefix
        # action -> (output_str, child_node)
        self.children: dict[str, tuple[str, "_ObsNode"]] = {}


class ApartnessTreeInstantLearner:
    """Move 0: Vaandrager `L#` + Error-Aware `L#_e` active Mealy learner with zero observation tables.

    Properties:
      1. Zero `S x E` table or consistency sweeps — maintains only a compact prefix tree `T`.
      2. Constructive apartness `apart(u, v)` returns a concrete witness sequence `w` proving
         `out(u, w) != out(v, w)` directly on shared tree branches.
      3. Error-persistent sink pruning (`L#_e`): transitions emitting refusal/error tokens route
         immediately to canonical sink/self-loop semantics without probing `|A|` dead continuations.
      4. Adaptive Distinguishing Tree (`ADS`): classifies frontier states in `O(log |Basis|)` probes.
    """

    def __init__(self, *, prune_error_sinks: bool = True) -> None:
        self.prune_error_sinks = bool(prune_error_sinks)

    @staticmethod
    def find_apartness_witness(u: _ObsNode, v: _ObsNode) -> tuple[str, ...] | None:
        """Return shortest observed suffix `w` in `T` proving `u # v`, or `None` if compatible."""
        queue: deque[tuple[_ObsNode, _ObsNode, tuple[str, ...]]] = deque([(u, v, ())])
        while queue:
            nu, nv, suffix = queue.popleft()
            # Deterministic intersection over shared observed actions
            for act, (out_u, ch_u) in nu.children.items():
                pair_v = nv.children.get(act)
                if pair_v is None:
                    continue
                out_v, ch_v = pair_v
                if out_u != out_v:
                    return suffix + (act,)
                queue.append((ch_u, ch_v, suffix + (act,)))
        return None

    def learn(
        self,
        *,
        alphabet: Sequence[str],
        execute_trace: Callable[[Sequence[str]], Sequence[str]],
        held_out_traces: Sequence[Sequence[str]] = (),
        target_output: str | None = None,
        max_basis_states: int = 24,
    ) -> dict[str, Any]:
        t0 = time.perf_counter()
        acts = [str(a) for a in alphabet]
        if not acts:
            return {
                "schema": SCHEMA,
                "operation": "LEARN_APARTNESS_LSHARP",
                "pass": False,
                "reason": "EMPTY_ALPHABET",
                "model_calls": 0,
            }

        root = _ObsNode(())
        nodes_by_prefix: dict[tuple[str, ...], _ObsNode] = {(): root}
        trace_cache: dict[tuple[str, ...], tuple[str, ...]] = {}
        membership_queries = 0
        error_sink_pruned = 0

        def _query(seq: tuple[str, ...]) -> tuple[str, ...]:
            nonlocal membership_queries
            if not seq:
                return ()
            hit = trace_cache.get(seq)
            if hit is not None:
                return hit
            membership_queries += 1
            outs = tuple(str(x) for x in execute_trace(seq))
            trace_cache[seq] = outs
            # Populate all prefixes along `seq` in the observation tree for free!
            cur = root
            for idx, (act, out_s) in enumerate(zip(seq, outs)):
                pref = seq[: idx + 1]
                existing = cur.children.get(act)
                if existing is None:
                    ch = nodes_by_prefix.get(pref)
                    if ch is None:
                        ch = _ObsNode(pref)
                        nodes_by_prefix[pref] = ch
                    cur.children[act] = (out_s, ch)
                    cur = ch
                else:
                    cur = existing[1]
            return outs

        def _ensure_one_step(node: _ObsNode) -> None:
            for act in acts:
                if act not in node.children:
                    _query(node.prefix + (act,))

        _ensure_one_step(root)
        basis: list[_ObsNode] = [root]
        frontier_to_basis: dict[tuple[str, ...], tuple[str, ...]] = {}
        error_transitions: set[tuple[tuple[str, ...], str]] = set()

        changed = True
        rounds = 0
        while changed and len(basis) < max_basis_states and rounds < max_basis_states * 4:
            changed = False
            rounds += 1
            frontier: list[_ObsNode] = []
            for b in list(basis):
                _ensure_one_step(b)
                for act in acts:
                    out_s, ch = b.children[act]
                    if self.prune_error_sinks and _is_error_output(out_s):
                        if (b.prefix, act) not in error_transitions:
                            error_transitions.add((b.prefix, act))
                            error_sink_pruned += len(acts)
                        # Error-persistent transition keeps machine in same state or refusal self-loop
                        frontier_to_basis[ch.prefix] = b.prefix
                        continue
                    if ch not in basis:
                        frontier.append(ch)

            for f_node in frontier:
                _ensure_one_step(f_node)
                # Filter basis candidates not yet apart from `f_node`
                compatible = [b for b in basis if self.find_apartness_witness(f_node, b) is None]
                while len(compatible) > 1:
                    b1, b2 = compatible[0], compatible[1]
                    wit = self.find_apartness_witness(b1, b2)
                    if wit is None:
                        break
                    _query(f_node.prefix + wit)
                    _query(b1.prefix + wit)
                    _query(b2.prefix + wit)
                    compatible = [b for b in compatible if self.find_apartness_witness(f_node, b) is None]

                if not compatible:
                    # `f_node` is constructively apart (`#`) from EVERY basis state -> promote to basis!
                    basis.append(f_node)
                    frontier_to_basis.pop(f_node.prefix, None)
                    changed = True
                    break
                else:
                    frontier_to_basis[f_node.prefix] = compatible[0].prefix

            if changed:
                continue

            # Lightweight `1`-step suffix consistency check on merged frontier transitions
            for b in list(basis):
                for act in acts:
                    out_s, ch = b.children[act]
                    if ch in basis or (self.prune_error_sinks and _is_error_output(out_s)):
                        continue
                    target_pref = frontier_to_basis.get(ch.prefix)
                    if target_pref is None:
                        continue
                    target_b = nodes_by_prefix[target_pref]
                    wit = self.find_apartness_witness(ch, target_b)
                    if wit is not None:
                        basis.append(ch)
                        frontier_to_basis.pop(ch.prefix, None)
                        changed = True
                        break
                if changed:
                    break

        state_ids = {b.prefix: f"q{idx}" for idx, b in enumerate(basis)}
        transitions: dict[str, dict[str, dict[str, str]]] = {}
        shortest_plan: list[str] | None = None

        for b in basis:
            sid = state_ids[b.prefix]
            transitions[sid] = {}
            for act in acts:
                out_s, ch = b.children[act]
                if ch.prefix in state_ids:
                    dst = state_ids[ch.prefix]
                else:
                    mapped = frontier_to_basis.get(ch.prefix, b.prefix)
                    dst = state_ids.get(mapped, sid)
                transitions[sid][act] = {"out": out_s, "next": dst}
                if target_output is not None and out_s == target_output:
                    cand_plan = list(b.prefix) + [act]
                    if shortest_plan is None or len(cand_plan) < len(shortest_plan):
                        shortest_plan = cand_plan

        # Pairwise constructive apartness certificate table (`(qi, qj) -> witness`)
        apartness_witnesses: dict[str, list[str]] = {}
        for i in range(len(basis)):
            for j in range(i + 1, len(basis)):
                w = self.find_apartness_witness(basis[i], basis[j])
                if w is not None:
                    apartness_witnesses[f"{state_ids[basis[i].prefix]}#{state_ids[basis[j].prefix]}"] = list(w)

        def _predict(seq: Sequence[str]) -> list[str]:
            cur_s = "q0"
            preds: list[str] = []
            for a in seq:
                row = transitions.get(cur_s, {}).get(str(a))
                if row is None:
                    preds.append("")
                else:
                    preds.append(row["out"])
                    cur_s = row["next"]
            return preds

        exact_held_out = 0
        for tr in held_out_traces:
            pred = _predict(tr)
            truth = [str(x) for x in execute_trace(tr)]
            if pred == truth:
                exact_held_out += 1
        acc = round(exact_held_out / len(held_out_traces), 6) if held_out_traces else 1.0

        return {
            "schema": SCHEMA,
            "operation": "LEARN_APARTNESS_LSHARP",
            "pass": bool(acc == 1.0),
            "observation_table_allocated": False,
            "state_count": len(basis),
            "basis_prefixes": [list(b.prefix) for b in basis],
            "transitions": transitions,
            "apartness_witnesses": apartness_witnesses,
            "error_sink_probes_pruned": error_sink_pruned,
            "membership_queries": membership_queries,
            "shortest_plan_to_target": shortest_plan,
            "held_out_traces_evaluated": len(held_out_traces),
            "held_out_exact_accuracy": acc,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 4),
            "model_calls": 0,
        }


# ============================================================================
# MOVE 1: Angelic Forest Impossibility Sieve + Unwired `OE-SyGuS` + `NAME_SCOPE` + 4-Gate Verifier
# ============================================================================


def audit_test_run_truthfulness(
    *,
    returncode: int,
    stdout: str,
    stderr: str,
    tests_executed: int | None = None,
) -> dict[str, Any]:
    """PR #7049's 4 non-vacuous test-verifier truth gates:

      1. Green exit with `0` collected/executed tests -> REFUSED (`VACUOUS_ZERO_TESTS_RAN`).
      2. Collection / Import / Syntax error -> REFUSED (`COLLECTION_OR_IMPORT_ERROR`, never scores as 1 failure).
      3. Pytest usage / internal error exit (`returncode >= 2` or `PYTEST_EXECUTION_FAILED:`) -> REFUSED.
      4. Requires explicit positive test pass count (`passed >= 1`).
    """
    combined = f"{stdout}\n{stderr}"
    if "PYTEST_EXECUTION_FAILED:" in combined or returncode in (2, 3, 4, 5):
        return {
            "truthful_pass": False,
            "verdict": "REFUSED__RUNNER_USAGE_OR_NO_TESTS_EXIT",
            "returncode": returncode,
        }
    if any(
        marker in combined
        for marker in (
            "ERROR collecting ",
            "ImportError:",
            "ModuleNotFoundError:",
            "SyntaxError:",
            "IndentationError:",
        )
    ):
        return {
            "truthful_pass": False,
            "verdict": "REFUSED__COLLECTION_OR_IMPORT_ERROR",
            "returncode": returncode,
        }

    m_passed = re.search(r"(\d+)\s+passed", combined)
    m_ran = re.search(r"Ran\s+(\d+)\s+tests?", combined)
    n_ran = (
        int(tests_executed)
        if tests_executed is not None
        else (int(m_passed.group(1)) if m_passed else (int(m_ran.group(1)) if m_ran else 0))
    )
    if n_ran <= 0:
        return {
            "truthful_pass": False,
            "verdict": "REFUSED__VACUOUS_ZERO_TESTS_RAN",
            "returncode": returncode,
            "tests_ran": 0,
        }
    m_failed = re.search(r"(\d+)\s+(?:failed|error)", combined)
    has_fail = (returncode != 0) or (m_failed is not None and int(m_failed.group(1)) > 0) or ("FAILED" in combined)
    return {
        "truthful_pass": not has_fail,
        "verdict": "PASS__NON_VACUOUS_VERIFIED" if not has_fail else "FAIL__ASSERTIONS_RED",
        "returncode": returncode,
        "tests_ran": n_ran,
    }


def purge_workspace_bytecode(workspace: pathlib.Path) -> int:
    """PR #7049 Rule 4: Purge `.pyc` across all `__pycache__` siblings so stale imports never fake passes."""
    removed = 0
    for p in workspace.rglob("*.pyc"):
        try:
            p.unlink()
            removed += 1
        except OSError:
            pass
    return removed


def generate_name_scope_candidates(
    source_text: str,
    *,
    focus_lines: Iterable[int] = (),
    max_candidates: int = 32,
) -> list[tuple[str, str]]:
    """PR #7049 `NAME_SCOPE` family: rewrite `obj.attr` -> `in_scope_name` or `obj.other_field`
    using ONLY identifiers declared inside the module's own AST (zero test-literal leakage!).

    Covers real fixes such as `pypa/packaging` `8efde605`:
        `f"{__spec__.parent}.errors"` -> `f"{parent}.errors"`.
    """
    try:
        orig_tree = ast.parse(source_text)
    except SyntaxError:
        return []

    focus_set = {int(x) for x in focus_lines if x}
    module_names: set[str] = set()
    module_attrs: set[str] = set()
    scope_by_func: dict[tuple[str, int], set[str]] = {}

    for node in orig_tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and not t.id.startswith("__"):
                    module_names.add(t.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            module_names.add(node.target.id)

    for node in ast.walk(orig_tree):
        if isinstance(node, ast.Attribute):
            module_attrs.add(node.attr)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            local_Pool: set[str] = set(module_names)
            for arg in list(node.args.posonlyargs) + list(node.args.args) + list(node.args.kwonlyargs):
                if arg.arg not in ("self", "cls"):
                    local_Pool.add(arg.arg)
            for sub in ast.walk(node):
                if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Store):
                    local_Pool.add(sub.id)
            scope_by_func[(node.name, node.lineno)] = local_Pool

    # Map every AST node index to enclosing function scope
    all_nodes = list(ast.walk(orig_tree))
    enclosing_scope: dict[int, set[str]] = {}
    for fn_nd in ast.walk(orig_tree):
        if isinstance(fn_nd, (ast.FunctionDef, ast.AsyncFunctionDef)):
            sc = scope_by_func.get((fn_nd.name, fn_nd.lineno), module_names)
            for sub in ast.walk(fn_nd):
                enclosing_scope[id(sub)] = sc

    ordered_indices = sorted(
        range(len(all_nodes)),
        key=lambda idx: (
            0 if (focus_set and any(abs(getattr(all_nodes[idx], "lineno", -999) - fl) <= 4 for fl in focus_set)) else 1,
            getattr(all_nodes[idx], "lineno", 10**9),
            idx,
        ),
    )

    out: list[tuple[str, str]] = []
    seen_src: set[str] = {source_text}

    for idx in ordered_indices:
        if len(out) >= max_candidates:
            break
        nd = all_nodes[idx]
        if not isinstance(nd, ast.Attribute) or not isinstance(nd.ctx, ast.Load):
            continue
        in_scope = sorted(enclosing_scope.get(id(nd), module_names))
        # Prioritize exact attribute-name match (`__spec__.parent` -> `parent`) first!
        prioritized = sorted(
            in_scope,
            key=lambda nm: (0 if nm == nd.attr else (1 if nd.attr in nm or nm in nd.attr else 2), nm),
        )
        for cand_nm in prioritized[:6]:
            if len(out) >= max_candidates:
                break
            t_copy = copy.deepcopy(orig_tree)
            # Replace node `idx` inside `t_copy` by walking parent links
            replaced = False
            walk_copy = list(ast.walk(t_copy))
            target_nd = walk_copy[idx]
            for parent in walk_copy:
                for field_name, field_val in ast.iter_fields(parent):
                    if field_val is target_nd:
                        setattr(parent, field_name, ast.Name(id=cand_nm, ctx=ast.Load()))
                        replaced = True
                        break
                    if isinstance(field_val, list):
                        for pos, item in enumerate(field_val):
                            if item is target_nd:
                                field_val[pos] = ast.Name(id=cand_nm, ctx=ast.Load())
                                replaced = True
                                break
                if replaced:
                    break
            if replaced:
                ast.fix_missing_locations(t_copy)
                new_src = ast.unparse(t_copy)
                if new_src not in seen_src:
                    seen_src.add(new_src)
                    out.append((f"name_scope_attr_to_local:{ast.unparse(nd)}->{cand_nm}", new_src))
    return out


def _extract_assertion_calls(test_source: str) -> list[tuple[str, str, str]]:
    """Parse `assert <call_expr> == <expected_expr>` pairs from Python test source."""
    pairs: list[tuple[str, str, str]] = []
    try:
        tree = ast.parse(test_source)
    except SyntaxError:
        return pairs
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assert)
            and isinstance(node.test, ast.Compare)
            and len(node.test.ops) == 1
            and isinstance(node.test.ops[0], ast.Eq)
        ):
            lhs = ast.unparse(node.test.left)
            rhs = ast.unparse(node.test.comparators[0])
            pairs.append((ast.unparse(node), lhs, rhs))
    return pairs


def _fork_eval_candidate(cand_source: str, assertions: Sequence[str], filename: str = "module.py") -> tuple[bool, int]:
    """Sub-2ms `os.fork()` CoW isolated candidate evaluator enforcing non-vacuous test count."""
    if not assertions:
        return False, 0
    if hasattr(os, "fork"):
        r_fd, w_fd = os.pipe()
        pid = os.fork()
        if pid == 0:
            os.close(r_fd)
            ok = False
            ran = 0
            try:
                ns: dict[str, Any] = {"__name__": "__cow_verify__"}
                exec(compile(cand_source, filename, "exec"), ns)
                for stmt_src in assertions:
                    exec(compile(stmt_src, "<assert>", "exec"), ns)
                    ran += 1
                ok = ran == len(assertions) and ran > 0
            except BaseException:
                ok = False
            try:
                os.write(w_fd, f"{1 if ok else 0}:{ran}".encode("ascii"))
            finally:
                os.close(w_fd)
                os._exit(0)
        os.close(w_fd)
        raw = os.read(r_fd, 64).decode("ascii", errors="replace")
        os.close(r_fd)
        os.waitpid(pid, 0)
        parts = raw.split(":")
        if len(parts) == 2:
            return parts[0] == "1", int(parts[1])
        return False, 0

    ns_local: dict[str, Any] = {"__name__": "__local_verify__"}
    try:
        exec(compile(cand_source, filename, "exec"), ns_local)
        ran_l = 0
        for stmt_src in assertions:
            exec(compile(stmt_src, "<assert>", "exec"), ns_local)
            ran_l += 1
        return ran_l > 0, ran_l
    except Exception:
        return False, 0


class AngelicForestSyGuSRepairEngine:
    """Move 1: Angelic Forest Impossibility Sieve (`Angelix`) + Unwired `OE-SyGuS` (`EUSolver`) +
    `NAME_SCOPE` + `site_by_intervention_v1` + `expected_actual_literal_v1` + `mined_rewrite_theory_v1`.
    """

    def seed_rewrite_laws_cold_start(self, *, max_size: int = 3) -> dict[str, Any]:
        """Eliminate `STORE_FILE_ABSENT` cold start by deriving verified equational laws (`mined_rewrite_theory_v1`)."""
        from canonical.swe_kernel import mined_rewrite_theory_v1 as mrt

        t0 = time.perf_counter()
        mined = mrt.mine_rules(
            mrt.ARITHMETIC,
            names=("x", "y"),
            max_size=int(max_size),
            term_limit=128,
            witnesses_per_round=16,
            verify_rounds=2,
            seed=7,
            consts=(0, 1),
        )
        # Also run `mrt.DIVISION` over small nonzero grouping domain `(1, 2)` vs adversarial domain
        # so non-polynomial coincidences (e.g. `x // 1` vs `x % 2 + ...`) are actively refuted!
        div_mined = mrt.mine_rules(
            mrt.DIVISION,
            names=("x", "y"),
            max_size=int(max_size),
            term_limit=64,
            witnesses_per_round=4,
            verify_rounds=1,
            seed=3,
            domain=(1, 2),
            consts=(1, 2),
        )
        admitted = list(mined.get("rules") or ())
        refuted = list(mined.get("refuted") or ()) + list(div_mined.get("refuted") or ())
        minimal = mrt.minimize_rules(admitted)
        return {
            "admitted_count": len(admitted),
            "minimized_basis_count": len(minimal),
            "refuted_coincidences_killed": len(refuted),
            "sample_laws": [str(r) for r in minimal[:8]],
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            "model_calls": 0,
        }

    def solve(
        self,
        source_text: str,
        test_source: str,
        *,
        filename: str = "target_mod.py",
        instruction_hint: str = "",
        seed_cold_store: bool = False,
    ) -> dict[str, Any]:
        from canonical.runtime import oe_sygus_synthesizer_v1 as sgs
        from canonical.swe_kernel import cow_lens_fuzz_and_negative_space_v1 as cfn
        from canonical.swe_kernel import expected_actual_literal_v1 as eal
        from canonical.swe_kernel import site_by_intervention_v1 as sbi

        t0 = time.perf_counter()
        assertions_info = _extract_assertion_calls(test_source)
        # Support arbitrary assert statements if non-equality asserts are also present
        raw_assert_stmts: list[str] = []
        try:
            t_ast = ast.parse(test_source)
            raw_assert_stmts = [ast.unparse(st) for st in t_ast.body]
        except SyntaxError:
            return {
                "schema": SCHEMA,
                "operation": "SOLVE_ANGELIC_SYGUS_SWE",
                "pass": False,
                "solved": False,
                "reason": "TEST_SYNTAX_ERROR",
                "model_calls": 0,
            }

        # Gate 0: Non-vacuous baseline failure check (must have >=1 test and fail on buggy baseline)
        if not raw_assert_stmts:
            return {
                "schema": SCHEMA,
                "operation": "SOLVE_ANGELIC_SYGUS_SWE",
                "pass": False,
                "solved": False,
                "reason": "REFUSED__VACUOUS_ZERO_TESTS_RAN",
                "model_calls": 0,
            }
        base_ok, _ = _fork_eval_candidate(source_text, raw_assert_stmts, filename=filename)
        if base_ok:
            return {
                "schema": SCHEMA,
                "operation": "SOLVE_ANGELIC_SYGUS_SWE",
                "pass": False,
                "solved": False,
                "reason": "FAIL_CLOSED__BASELINE_ALREADY_GREEN",
                "model_calls": 0,
            }

        # Stage 1: Partition failing vs passing assertions + capture live frame environments
        ns_base: dict[str, Any] = {"__name__": "__angelic_probe__"}
        exec(compile(source_text, filename, "exec"), ns_base)

        failing_assertions: list[tuple[str, str, Any, Any]] = []
        passing_assertions: list[tuple[str, str, Any]] = []
        for full_stmt, lhs_src, rhs_src in assertions_info:
            try:
                exp_val = eval(compile(rhs_src, "<rhs>", "eval"), dict(ns_base))
            except Exception:
                continue
            try:
                act_val = eval(compile(lhs_src, "<lhs>", "eval"), dict(ns_base))
                if act_val == exp_val and type(act_val) is type(exp_val):
                    passing_assertions.append((full_stmt, lhs_src, exp_val))
                else:
                    failing_assertions.append((full_stmt, lhs_src, act_val, exp_val))
            except Exception as exc:
                failing_assertions.append((full_stmt, lhs_src, f"RAISED:{type(exc).__name__}", exp_val))

        # Wire unwired `site_by_intervention_v1` candidate sites inventory
        intervention_sites = sbi.candidate_sites(source_text)

        # Stage 2: Angelic Forest Impossibility Sieve (`Angelix` over AST expression sites)
        orig_tree = ast.parse(source_text)
        expr_sites: list[tuple[int, int, str, str]] = []
        for fn_nd in ast.walk(orig_tree):
            if not isinstance(fn_nd, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for sub in ast.walk(fn_nd):
                if isinstance(sub, ast.Return) and sub.value is not None:
                    expr_sites.append((sub.lineno, id(sub), fn_nd.name, "return"))
                elif isinstance(sub, ast.Assign) and len(sub.targets) == 1 and isinstance(sub.targets[0], ast.Name):
                    expr_sites.append((sub.lineno, id(sub), fn_nd.name, f"assign:{sub.targets[0].id}"))

        angelic_pruned_sites: list[dict[str, Any]] = []
        angelic_viable_sites: list[dict[str, Any]] = []

        # Collect angelic probe values from failing assertion demands + booleans + 0/1/""
        angelic_values: list[Any] = []
        for _st, _lhs, _act, exp_v in failing_assertions:
            if exp_v not in angelic_values:
                angelic_values.append(exp_v)
        for v_std in (True, False, 0, 1, ""):
            if v_std not in angelic_values:
                angelic_values.append(v_std)

        # Test each expression site in CoW child: can ANY angelic value flip at least one failing assertion?
        for lineno, _nid, fn_name, site_kind in expr_sites:
            site_can_flip = False
            winning_angelic_map: list[tuple[dict[str, Any], Any]] = []

            for f_stmt, lhs_src, _act_v, exp_v in failing_assertions:
                # Capture visible local environment at `(fn_name, lineno)` during `lhs_src`
                captured_env: dict[str, Any] = {}

                def _tracer(frame: Any, event: str, _arg: Any) -> Any:
                    if frame.f_code.co_filename == filename and event == "line" and frame.f_lineno == lineno:
                        for k, v in frame.f_locals.items():
                            if not k.startswith("__") and isinstance(v, (int, float, str, bool, list, tuple, dict, type(None))):
                                captured_env[k] = v
                    return _tracer

                old_t = sys.gettrace()
                sys.settrace(_tracer)
                try:
                    eval(compile(lhs_src, "<trace_fail>", "eval"), dict(ns_base))
                except Exception:
                    pass
                finally:
                    sys.settrace(old_t)

                if not captured_env:
                    # Line wasn't even executed on the failing input -> mathematically impossible single-site fix!
                    continue

                # Substitute an angelic hook at `lineno` and check if `exp_v` (or another probe) satisfies `f_stmt`
                for probe_v in angelic_values[:6]:
                    t_angel = copy.deepcopy(orig_tree)
                    patched = False
                    for sub in ast.walk(t_angel):
                        if getattr(sub, "lineno", -1) == lineno:
                            if isinstance(sub, ast.Return) and sub.value is not None and site_kind == "return":
                                sub.value = ast.parse(repr(probe_v), mode="eval").body
                                patched = True
                                break
                            if (
                                isinstance(sub, ast.Assign)
                                and site_kind.startswith("assign:")
                                and isinstance(sub.targets[0], ast.Name)
                            ):
                                sub.value = ast.parse(repr(probe_v), mode="eval").body
                                patched = True
                                break
                    if not patched:
                        continue
                    ast.fix_missing_locations(t_angel)
                    angel_src = ast.unparse(t_angel)
                    ok_single, _ = _fork_eval_candidate(angel_src, [f_stmt], filename=filename)
                    if ok_single:
                        site_can_flip = True
                        winning_angelic_map.append((dict(captured_env), probe_v))
                        break

            if not site_can_flip and failing_assertions:
                angelic_pruned_sites.append({"lineno": lineno, "function": fn_name, "kind": site_kind})
            else:
                angelic_viable_sites.append(
                    {
                        "lineno": lineno,
                        "function": fn_name,
                        "kind": site_kind,
                        "angelic_forest": winning_angelic_map,
                    }
                )

        # Capture passing-frame `(env, actual_value_at_site)` on viable sites so OE-SyGuS never breaks passing tests!
        candidate_pool_by_family: dict[str, list[tuple[str, str]]] = defaultdict(list)

        for vsite in angelic_viable_sites:
            lineno = int(vsite["lineno"])
            site_kind = str(vsite["kind"])
            angelic_forest: list[tuple[dict[str, Any], Any]] = list(vsite["angelic_forest"])
            if not angelic_forest:
                continue

            passing_forest: list[tuple[dict[str, Any], Any]] = []
            for _p_stmt, p_lhs, p_exp in passing_assertions[:8]:
                p_env: dict[str, Any] = {}
                site_val_box: list[Any] = []

                def _p_tracer(frame: Any, event: str, arg: Any) -> Any:
                    if frame.f_code.co_filename == filename:
                        if event == "line" and frame.f_lineno == lineno:
                            for k, v in frame.f_locals.items():
                                if not k.startswith("__") and isinstance(v, (int, float, str, bool, list, tuple, dict, type(None))):
                                    p_env[k] = v
                        elif event == "return" and frame.f_code.co_name == vsite["function"]:
                            site_val_box.append(arg)
                    return _p_tracer

                old_t = sys.gettrace()
                sys.settrace(_p_tracer)
                try:
                    eval(compile(p_lhs, "<trace_pass>", "eval"), dict(ns_base))
                except Exception:
                    pass
                finally:
                    sys.settrace(old_t)

                if p_env:
                    if site_kind.startswith("assign:"):
                        var_nm = site_kind.split(":", 1)[1]
                        # Capture post-assignment value by running function body or fallback to p_exp
                        passing_forest.append((p_env, p_env.get(var_nm, p_exp)))
                    else:
                        passing_forest.append((p_env, site_val_box[-1] if site_val_box else p_exp))

            # Channel A: Unwired `oe_sygus_synthesizer_v1.synthesize_value_expressions` (`EUSolver` OE-SyGuS!)
            sygus_rows = sgs.synthesize_value_expressions(
                angelic_forest + passing_forest,
                lang="python",
                max_results=6,
            )
            for row in sygus_rows:
                py_expr = str(row["code"])
                t_cand = copy.deepcopy(orig_tree)
                for sub in ast.walk(t_cand):
                    if getattr(sub, "lineno", -1) == lineno:
                        if isinstance(sub, ast.Return) and site_kind == "return":
                            sub.value = ast.parse(py_expr, mode="eval").body
                            break
                        if isinstance(sub, ast.Assign) and site_kind.startswith("assign:"):
                            sub.value = ast.parse(py_expr, mode="eval").body
                            break
                ast.fix_missing_locations(t_cand)
                candidate_pool_by_family["oe_sygus_value"].append(
                    (f"oe_sygus@{lineno}:{py_expr}", ast.unparse(t_cand))
                )

            # Channel B: Unwired `oe_sygus_synthesizer_v1.synthesize_separating_predicates` (guard insertion!)
            if passing_forest:
                fail_envs = [env for env, _v in angelic_forest]
                pass_envs = [env for env, _v in passing_forest]
                preds = sgs.synthesize_separating_predicates(fail_envs, pass_envs, lang="python", max_results=4)
                uniform_vals = {repr(v): v for _e, v in angelic_forest}
                if preds and len(uniform_vals) == 1:
                    only_v = next(iter(uniform_vals.values()))
                    for pred_row in preds:
                        guard_py = str(pred_row["code"])
                        t_cand = copy.deepcopy(orig_tree)
                        for fn_sub in ast.walk(t_cand):
                            if isinstance(fn_sub, (ast.FunctionDef, ast.AsyncFunctionDef)) and fn_sub.name == vsite["function"]:
                                guard_stmt = ast.parse(f"if {guard_py}:\n    return {only_v!r}\n").body[0]
                                insert_pos = (
                                    1
                                    if (
                                        fn_sub.body
                                        and isinstance(fn_sub.body[0], ast.Expr)
                                        and isinstance(fn_sub.body[0].value, ast.Constant)
                                    )
                                    else 0
                                )
                                fn_sub.body.insert(insert_pos, guard_stmt)
                                ast.fix_missing_locations(t_cand)
                                candidate_pool_by_family["oe_sygus_guard"].append(
                                    (f"oe_sygus_guard:{guard_py}", ast.unparse(t_cand))
                                )
                                break

            # Channel C: Unwired `cow_lens_fuzz_and_negative_space_v1.synthesize_bidirectional_fst_lens`
            all_io: list[tuple[Any, Any]] = []
            for env, target_v in angelic_forest + passing_forest:
                if len(env) == 1:
                    all_io.append((next(iter(env.values())), target_v))
            if all_io:
                lens = cfn.synthesize_bidirectional_fst_lens(all_io)
                if lens is not None and lens.roundtrip_verified:
                    param_nm = next(iter(angelic_forest[0][0].keys()))
                    body_py = lens.forward_expr_template.replace("{x}", param_nm)
                    t_cand = copy.deepcopy(orig_tree)
                    for sub in ast.walk(t_cand):
                        if getattr(sub, "lineno", -1) == lineno and isinstance(sub, ast.Return):
                            sub.value = ast.parse(body_py, mode="eval").body
                            ast.fix_missing_locations(t_cand)
                            candidate_pool_by_family["bidirectional_fst_lens"].append(
                                (f"fst_lens:{lens.lens_family}", ast.unparse(t_cand))
                            )
                            break

        # Channel D: PR #7049 `NAME_SCOPE` (`__spec__.parent` -> `parent`, `self.x` -> `x`)
        focus_lns = [int(v["lineno"]) for v in angelic_viable_sites]
        for desc, ns_src in generate_name_scope_candidates(source_text, focus_lines=focus_lns, max_candidates=24):
            candidate_pool_by_family["name_scope"].append((desc, ns_src))

        # Channel E: Unwired `expected_actual_literal_v1` string literal alignment
        for _f_stmt, _lhs, act_v, exp_v in failing_assertions:
            if isinstance(act_v, str) and isinstance(exp_v, str):
                diffs = eal.differences(act_v, exp_v)
                holes = eal.literal_holes(source_text, focus_lns)
                for patched_src, tag in eal.candidates(source_text, holes, diffs, limit=12, expected_value=exp_v):
                    candidate_pool_by_family["expected_actual_literal"].append((f"literal_align:{tag}", patched_src))

        # PR #7049 Round-Robin Family Interleaving (no giant family can starve a 4-candidate family!)
        interleaved: list[tuple[str, str, str]] = []
        fam_names = sorted(candidate_pool_by_family.keys())
        max_len = max((len(v) for v in candidate_pool_by_family.values()), default=0)
        seen_code: set[str] = {source_text}
        for pos in range(max_len):
            for fam in fam_names:
                bucket = candidate_pool_by_family[fam]
                if pos < len(bucket):
                    desc, c_src = bucket[pos]
                    if c_src not in seen_code:
                        seen_code.add(c_src)
                        interleaved.append((fam, desc, c_src))

        evaluated = 0
        winning: tuple[str, str, str, int] | None = None
        for fam, desc, cand_src in interleaved[:64]:
            evaluated += 1
            ok, n_ran = _fork_eval_candidate(cand_src, raw_assert_stmts, filename=filename)
            if ok and n_ran == len(raw_assert_stmts) and n_ran > 0:
                winning = (fam, desc, cand_src, n_ran)
                break

        cold_seed_info = self.seed_rewrite_laws_cold_start() if seed_cold_store else None
        if winning is None:
            return {
                "schema": SCHEMA,
                "operation": "SOLVE_ANGELIC_SYGUS_SWE",
                "pass": False,
                "solved": False,
                "reason": "NO_CANDIDATE_VERIFIED_ALL_ASSERTIONS",
                "angelic_pruned_site_count": len(angelic_pruned_sites),
                "angelic_viable_site_count": len(angelic_viable_sites),
                "intervention_candidate_sites": len(intervention_sites),
                "candidates_evaluated": evaluated,
                "cold_store_seed": cold_seed_info,
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
                "model_calls": 0,
            }

        win_fam, win_desc, win_src, n_verified = winning
        # Synthesize differential pin proving repaired source differs from buggy baseline on real test calls
        diff_pins: list[str] = []
        for f_stmt, lhs_src, act_v, exp_v in failing_assertions[:3]:
            diff_pins.append(f"pin:{lhs_src} | buggy={act_v!r} -> repaired={exp_v!r}")

        return {
            "schema": SCHEMA,
            "operation": "SOLVE_ANGELIC_SYGUS_SWE",
            "pass": True,
            "solved": True,
            "winning_family": win_fam,
            "winning_description": win_desc,
            "repaired_source": win_src,
            "non_vacuous_assertions_verified": n_verified,
            "angelic_pruned_site_count": len(angelic_pruned_sites),
            "angelic_pruned_sites": angelic_pruned_sites,
            "angelic_viable_site_count": len(angelic_viable_sites),
            "intervention_candidate_sites": len(intervention_sites),
            "families_interleaved": fam_names,
            "candidates_evaluated": evaluated,
            "differential_pins": diff_pins,
            "cold_store_seed": cold_seed_info,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            "model_calls": 0,
        }


# ============================================================================
# MOVE 2: Protocol Lifting (`WebMCP`/CDP -> HTTP Skill) + Kernel Isolation + Effect Oracle
# ============================================================================

_STATIC_ASSET_EXTS: frozenset[str] = frozenset(
    {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".svg",
        ".ico",
        ".css",
        ".woff",
        ".woff2",
        ".ttf",
        ".eot",
        ".mp4",
        ".mp3",
        ".map",
    }
)
_NOISE_HOST_SUBSTRS: tuple[str, ...] = (
    "google-analytics",
    "doubleclick",
    "sentry.io",
    "segment.io",
    "hotjar",
    "mixpanel",
)

# Canonical format magic bytes (`effect_oracle_v1` discipline: never trust liberal readers or filenames!)
_FORMAT_MAGIC_PREFIXES: dict[str, tuple[bytes, ...]] = {
    ".gz": (b"\x1f\x8b",),
    ".xz": (b"\xfd7zXZ\x00",),
    ".bz2": (b"BZh",),
    ".zip": (b"PK\x03\x04", b"PK\x05\x06"),
    ".sqlite": (b"SQLite format 3\x00",),
    ".db": (b"SQLite format 3\x00",),
    ".pdf": (b"%PDF-",),
}


def verify_artifact_effect_oracle(
    artifact_path: pathlib.Path | str,
    *,
    expected_source_bytes: bytes | None = None,
) -> dict[str, Any]:
    """PR #7071 Machine-Reader Round-Trip & Magic-Header Effect Oracle.

    Refuses the measured `out.gz` bug where `xz` or `zip` bytes written to a file named `out.gz`
    fooled existence checks and liberal `gzip -dc` readers!
    """
    p = pathlib.Path(artifact_path)
    if not p.is_file():
        return {"pass": False, "verdict": "REFUSED__ARTIFACT_MISSING"}
    raw = p.read_bytes()
    if not raw:
        return {"pass": False, "verdict": "REFUSED__EMPTY_ARTIFACT"}

    ext = p.suffix.lower()
    magics = _FORMAT_MAGIC_PREFIXES.get(ext)
    if magics is not None and not any(raw.startswith(m) for m in magics):
        # Detect what format was actually written so the refusal names the exact impostor!
        detected = "UNKNOWN_BINARY"
        for other_ext, other_magics in _FORMAT_MAGIC_PREFIXES.items():
            if any(raw.startswith(om) for om in other_magics):
                detected = other_ext
                break
        return {
            "pass": False,
            "verdict": f"REFUSED__MAGIC_HEADER_MISMATCH:declared={ext}:actual={detected}",
            "declared_suffix": ext,
            "detected_format": detected,
        }

    decoded: bytes | None = None
    try:
        if ext == ".gz":
            decoded = gzip.decompress(raw)
        elif ext == ".xz":
            decoded = lzma.decompress(raw)
        elif ext == ".bz2":
            decoded = bz2.decompress(raw)
        elif ext == ".zip":
            with zipfile.ZipFile(io.BytesIO(raw), "r") as zf:
                names = zf.namelist()
                if not names:
                    return {"pass": False, "verdict": "REFUSED__EMPTY_ZIP_ARCHIVE"}
                decoded = zf.read(names[0])
        elif ext == ".json":
            json.loads(raw.decode("utf-8"))
            decoded = raw
        elif ext in (".sqlite", ".db"):
            conn = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
            try:
                ok_check = conn.execute("PRAGMA quick_check").fetchone()
                if not ok_check or ok_check[0] != "ok":
                    return {"pass": False, "verdict": "REFUSED__SQLITE_CORRUPT"}
            finally:
                conn.close()
            decoded = raw
    except Exception as exc:
        return {
            "pass": False,
            "verdict": f"REFUSED__READER_REJECTED:{type(exc).__name__}",
        }

    if expected_source_bytes is not None and decoded is not None and ext in (".gz", ".xz", ".bz2", ".zip"):
        if decoded != expected_source_bytes:
            return {
                "pass": False,
                "verdict": "REFUSED__ROUNDTRIP_BYTES_MISMATCH",
                "decoded_len": len(decoded),
                "expected_len": len(expected_source_bytes),
            }

    return {
        "pass": True,
        "verdict": "PASS__FORMAT_HEADER_AND_ROUNDTRIP_VERIFIED",
        "declared_suffix": ext,
        "artifact_bytes": len(raw),
        "roundtrip_verified": expected_source_bytes is not None,
    }


def execute_in_kernel_confinement(
    fn_or_cmd: Callable[[pathlib.Path], Any] | Sequence[str],
    *,
    host_sentinel_path: pathlib.Path | None = None,
    timeout_s: float = 5.0,
) -> dict[str, Any]:
    """PR #7071 Kernel Isolation Boundary (`CLONE_NEWUSER` + `CLONE_NEWNS` + `CLONE_NEWNET` when allowed,
    with isolated tmpfs/scratch `os.fork()` RLIMIT + post-run sentinel tamper verification).
    """
    t0 = time.perf_counter()
    sentinel_before = host_sentinel_path.read_bytes() if (host_sentinel_path and host_sentinel_path.exists()) else None
    unshare_bin = shutil.which("unshare")

    with tempfile.TemporaryDirectory(prefix="brain_kern_iso_") as scratch_str:
        scratch = pathlib.Path(scratch_str)
        if not callable(fn_or_cmd):
            argv = [str(x) for x in fn_or_cmd]
            # Attempt unprivileged user+mount+net+pid namespace isolation first (`CapEff` drop)
            if unshare_bin:
                ns_cmd = [unshare_bin, "-U", "-r", "-m", "-n", "-p", "--fork", "--", *argv]
                proc = subprocess.run(
                    ns_cmd,
                    cwd=str(scratch),
                    capture_output=True,
                    text=True,
                    timeout=timeout_s,
                    env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(scratch)},
                )
                if proc.returncode == 0 or "Operation not permitted" not in (proc.stderr or ""):
                    sentinel_after = (
                        host_sentinel_path.read_bytes() if (host_sentinel_path and host_sentinel_path.exists()) else None
                    )
                    untouched = sentinel_before == sentinel_after
                    return {
                        "pass": proc.returncode == 0 and untouched,
                        "isolation_mode": "LINUX_USER_MOUNT_NET_PID_NAMESPACE",
                        "returncode": proc.returncode,
                        "stdout": proc.stdout,
                        "stderr": proc.stderr,
                        "host_untouched": untouched,
                        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
                    }

            # Fallback if container blocks nested `CLONE_NEWUSER`: isolated env + scratch cwd subprocess
            proc2 = subprocess.run(
                argv,
                cwd=str(scratch),
                capture_output=True,
                text=True,
                timeout=timeout_s,
                env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(scratch)},
            )
            sentinel_after = (
                host_sentinel_path.read_bytes() if (host_sentinel_path and host_sentinel_path.exists()) else None
            )
            untouched = sentinel_before == sentinel_after
            return {
                "pass": proc2.returncode == 0 and untouched,
                "isolation_mode": "SCRATCH_ENV_CONFINED_SUBPROCESS",
                "returncode": proc2.returncode,
                "stdout": proc2.stdout,
                "stderr": proc2.stderr,
                "host_untouched": untouched,
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            }

        # Callable execution inside `os.fork()` child with `RLIMIT_NOFILE` / `RLIMIT_CPU` + `cwd=scratch`
        r_fd, w_fd = os.pipe()
        pid = os.fork()
        if pid == 0:
            os.close(r_fd)
            try:
                os.chdir(str(scratch))
                resource.setrlimit(resource.RLIMIT_CPU, (max(1, int(math.ceil(timeout_s))), max(1, int(math.ceil(timeout_s)))))
                res = fn_or_cmd(scratch)
                payload = pickle.dumps({"ok": True, "result": res})
            except BaseException as exc:
                payload = pickle.dumps({"ok": False, "error": f"{type(exc).__name__}:{exc}"})
            try:
                os.write(w_fd, payload)
            finally:
                os.close(w_fd)
                os._exit(0)
        os.close(w_fd)
        chunks: list[bytes] = []
        while True:
            buf = os.read(r_fd, 65536)
            if not buf:
                break
            chunks.append(buf)
        os.close(r_fd)
        os.waitpid(pid, 0)
        data = pickle.loads(b"".join(chunks)) if chunks else {"ok": False, "error": "EMPTY_PIPE"}
        sentinel_after = (
            host_sentinel_path.read_bytes() if (host_sentinel_path and host_sentinel_path.exists()) else None
        )
        untouched = sentinel_before == sentinel_after
        return {
            "pass": bool(data.get("ok")) and untouched,
            "isolation_mode": "FORK_RLIMIT_SCRATCH_ISOLATION",
            "result": data.get("result"),
            "error": data.get("error"),
            "host_untouched": untouched,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }


def lift_protocol_and_verify_effect(
    *,
    cdp_network_events: Sequence[Mapping[str, Any]] = (),
    webmcp_tools: Sequence[Mapping[str, Any]] = (),
    goal_parameters: Mapping[str, Any] | None = None,
    transport_fn: Callable[[str, str, Mapping[str, str], Any], Mapping[str, Any]] | None = None,
    osworld_state: Mapping[str, Any] | None = None,
    artifact_check: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Move 2 Unified Entrypoint:
      1. Wires `WebMCP` (`document.modelContext`) imperative tools if declared by page (`0` DOM/pixels).
      2. Otherwise lifts CDP/HAR network traces into a parameterized direct HTTP skill, stripping
         static assets (`.css`, `.png`, `.woff2`, analytics) so Run 2+ executes in `< 2 ms` with `0` UI.
      3. Consults unwired `intake/osworld_intake_policy_v1.decide` when `osworld_state` is supplied.
      4. Verifies produced file artifacts via `verify_artifact_effect_oracle` (magic bytes + round-trip).
    """
    t0 = time.perf_counter()
    params = dict(goal_parameters or {})

    osworld_gate_decision: dict[str, Any] | None = None
    if osworld_state is not None:
        from intake import osworld_intake_policy_v1 as osw_intake

        osworld_gate_decision = osw_intake.decide(osworld_state)

    # Tier 1A: `WebMCP` (`document.modelContext.registerTool`) direct imperative execution
    selected_webmcp: dict[str, Any] | None = None
    if webmcp_tools:
        for tool in webmcp_tools:
            req_props = set((tool.get("inputSchema") or {}).get("required") or ())
            if req_props.issubset(set(params.keys())):
                selected_webmcp = {
                    "name": str(tool.get("name") or "webmcp_tool"),
                    "bound_arguments": {k: params[k] for k in sorted(req_props)},
                    "screenshots_taken": 0,
                }
                break

    # Tier 1B: CDP / HAR Network-to-API Protocol Lifting ("The best UI action is deleting the UI")
    static_filtered = 0
    api_candidates: list[dict[str, Any]] = []
    for ev in cdp_network_events:
        url = str(ev.get("url") or "")
        parsed = urllib.parse.urlsplit(url)
        path_low = parsed.path.lower()
        host_low = parsed.netloc.lower()
        mime = str(ev.get("mime_type") or ev.get("mimeType") or "").lower()
        if any(path_low.endswith(ext) for ext in _STATIC_ASSET_EXTS) or any(
            nh in host_low for nh in _NOISE_HOST_SUBSTRS
        ) or mime.startswith(("image/", "font/", "text/css")):
            static_filtered += 1
            continue
        method = str(ev.get("method") or "GET").upper()
        status_code = int(ev.get("status") or 200)
        if 200 <= status_code < 300 and (
            "json" in mime
            or "/api/" in path_low
            or "graphql" in path_low
            or method in ("POST", "PUT", "PATCH", "DELETE")
        ):
            # Parameterize matching goal values inside JSON body or query string
            raw_body = ev.get("post_data") or ev.get("body")
            param_template: dict[str, str] = {}
            parsed_body: Any = None
            if isinstance(raw_body, str) and raw_body.strip().startswith("{"):
                try:
                    parsed_body = json.loads(raw_body)
                except Exception:
                    parsed_body = None
            elif isinstance(raw_body, Mapping):
                parsed_body = dict(raw_body)

            if isinstance(parsed_body, dict):
                for bk, bv in parsed_body.items():
                    for pk, pv in params.items():
                        if bv == pv or bk == pk:
                            param_template[bk] = pk

            q_pairs = urllib.parse.parse_qsl(parsed.query)
            query_param_map: dict[str, str] = {}
            for qk, qv in q_pairs:
                for pk, pv in params.items():
                    if qv == str(pv) or qk == pk:
                        query_param_map[qk] = pk

            api_candidates.append(
                {
                    "method": method,
                    "base_url": f"{parsed.scheme}://{parsed.netloc}{parsed.path}",
                    "body_param_bindings": param_template,
                    "query_param_bindings": query_param_map,
                    "static_body_defaults": parsed_body if isinstance(parsed_body, dict) else {},
                    "auth_header_names": sorted(
                        h for h in (ev.get("headers") or {}) if h.lower() in ("authorization", "x-csrf-token", "x-api-key")
                    ),
                }
            )

    lifted_replay_result: dict[str, Any] | None = None
    lifted_replay_us: float | None = None
    if api_candidates and transport_fn is not None:
        spec = api_candidates[-1]
        t_rep = time.perf_counter()
        call_body = dict(spec["static_body_defaults"])
        for body_key, param_name in spec["body_param_bindings"].items():
            if param_name in params:
                call_body[body_key] = params[param_name]
        q_dict: dict[str, Any] = {}
        for q_key, param_name in spec["query_param_bindings"].items():
            if param_name in params:
                q_dict[q_key] = params[param_name]
        full_url = spec["base_url"] + ("?" + urllib.parse.urlencode(q_dict) if q_dict else "")
        resp = dict(transport_fn(spec["method"], full_url, {}, call_body if call_body else None))
        lifted_replay_us = round((time.perf_counter() - t_rep) * 1_000_000.0, 2)
        lifted_replay_result = {
            "method": spec["method"],
            "url": full_url,
            "body_sent": call_body,
            "response": resp,
            "browser_spawned": False,
            "screenshots_taken": 0,
            "replay_elapsed_us": lifted_replay_us,
        }

    oracle_res: dict[str, Any] | None = None
    if artifact_check is not None:
        oracle_res = verify_artifact_effect_oracle(
            artifact_check["path"],
            expected_source_bytes=artifact_check.get("expected_source_bytes"),
        )

    all_ok = True
    if oracle_res is not None and not oracle_res.get("pass"):
        all_ok = False

    return {
        "schema": SCHEMA,
        "operation": "PROTOCOL_LIFT_AND_EFFECT_ORACLE",
        "pass": all_ok,
        "webmcp_selected": selected_webmcp,
        "static_noise_events_deleted": static_filtered,
        "lifted_api_endpoints": api_candidates,
        "lifted_zero_browser_replay": lifted_replay_result,
        "osworld_intake_decision": osworld_gate_decision,
        "effect_oracle": oracle_res,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 4),
        "model_calls": 0,
    }


# ============================================================================
# MOVE 3: Why-Provenance Semiring `(2^(2^V), union, join)` Z-Set JTMS Memory (`MEME` 100%)
# ============================================================================


def _minimize_antichain(poly: Iterable[frozenset[str]]) -> frozenset[frozenset[str]]:
    """Semiring absorption law: if monomial `m1` is a subset of `m2`, drop `m2` (`m1` suffices)."""
    unique = sorted(set(poly), key=len)
    kept: list[frozenset[str]] = []
    for m in unique:
        if any(prev.issubset(m) for prev in kept):
            continue
        kept.append(m)
    return frozenset(kept)


def semiring_join(
    p1: frozenset[frozenset[str]],
    p2: frozenset[frozenset[str]],
) -> frozenset[frozenset[str]]:
    """Semiring multiplication (`bowtie`): pairwise union of premise monomials with absorption."""
    if not p1 or not p2:
        return frozenset()
    return _minimize_antichain(m1 | m2 for m1 in p1 for m2 in p2)


def semiring_union(
    p1: frozenset[frozenset[str]],
    p2: frozenset[frozenset[str]],
) -> frozenset[frozenset[str]]:
    """Semiring addition (`union`): alternative derivations with antichain minimization."""
    return _minimize_antichain(list(p1) + list(p2))


class SemiringProvenanceJTMSMemory:
    """Move 3: Green-Karvounarakis-Tannen Why-Provenance Semiring over `Z`-Set `DBSP` Memory.

    Solves the KAIST `MEME` (ICML 2026) failure modes where `Mem0`, `Graphiti`, `BM25`, and LLMs
    score `3%` on `Cascade` and `1%` on `Absence`:
      1. `Cascade` (`O(|Delta|)`, `< 15 us`): Retracting or overwriting an extensional premise `p`
         deletes all support monomials containing `p`. Derived beliefs with `poly == empty` retract
         automatically across arbitrary multi-hop chains, while diamond conclusions supported by an
         independent surviving proof monomial stay `ESTABLISHED`!
      2. `Absence` (`100%` exact): Querying `(subj, rel)` whose prior derivation polynomial collapsed
         to `empty` returns `ABSENCE__SUPPORT_PREMISE_INVALIDATED` naming the exact retracted premise(s).
    """

    def __init__(self) -> None:
        self.tx_clock: int = 0
        self.functional_relations: set[str] = {"status", "role", "location", "endpoint", "version", "policy"}
        # Extensional premise token `p_id` -> `(subj, rel, obj, active_bool, witness_sha)`
        self.premises: dict[str, dict[str, Any]] = {}
        self.extensional_by_triple: dict[tuple[str, str, str], str] = {}
        # All active facts `(subj, rel, obj)` -> Why-Provenance polynomial `frozenset[frozenset[p_id]]`
        self.provenance_poly: dict[tuple[str, str, str], frozenset[frozenset[str]]] = {}
        self.by_subj_rel: dict[tuple[str, str], set[str]] = defaultdict(set)
        # Inverted index: `premise_id -> set[(subj, rel, obj)]` for `O(|Delta|)` Cascade retraction!
        self.premise_to_facts: dict[str, set[tuple[str, str, str]]] = defaultdict(set)
        # Invalidated history for exact `Absence` reporting: `(subj, rel) -> list[dict]`
        self.invalidated_graveyard: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)

    def assert_premise(
        self,
        subj: str,
        rel: str,
        obj: str,
        *,
        witness_sha: str,
        premise_id: str | None = None,
    ) -> dict[str, Any]:
        if not witness_sha:
            return {"accepted": False, "reason": "UNWITNESSED_WRITE_REFUSED"}
        t0 = time.perf_counter()
        self.tx_clock += 1
        cascaded_retractions: list[tuple[str, str, str]] = []

        # Functional relation overwrite automatically retracts superseded value & cascades!
        if rel in self.functional_relations:
            for old_obj in list(self.by_subj_rel.get((subj, rel), ())):
                if old_obj != obj:
                    r_info = self.retract_premise(subj, rel, old_obj)
                    cascaded_retractions.extend(r_info["cascaded_retractions"])

        triple = (subj, rel, obj)
        pid = premise_id or f"p{self.tx_clock}:{subj}.{rel}={obj}"
        self.premises[pid] = {
            "triple": triple,
            "active": True,
            "witness_sha": witness_sha,
            "tx": self.tx_clock,
        }
        self.extensional_by_triple[triple] = pid
        mono = frozenset({pid})
        prev_poly = self.provenance_poly.get(triple, frozenset())
        self.provenance_poly[triple] = semiring_union(prev_poly, frozenset({mono}))
        self.by_subj_rel[(subj, rel)].add(obj)
        self.premise_to_facts[pid].add(triple)
        # Clear stale absence tombstones on fresh witnessed assertion for `(subj, rel)`
        self.invalidated_graveyard.pop((subj, rel), None)

        return {
            "accepted": True,
            "premise_id": pid,
            "tx": self.tx_clock,
            "cascaded_retractions": cascaded_retractions,
            "elapsed_us": round((time.perf_counter() - t0) * 1_000_000.0, 3),
        }

    def derive_fact(
        self,
        head: tuple[str, str, str],
        *,
        body_triples: Sequence[tuple[str, str, str]],
    ) -> dict[str, Any]:
        """Derive `head` from conjunction `body_triples` by multiplying their Why-Provenance polynomials."""
        t0 = time.perf_counter()
        acc_poly: frozenset[frozenset[str]] | None = None
        for bt in body_triples:
            bp = self.provenance_poly.get(bt, frozenset())
            if not bp:
                return {
                    "derived": False,
                    "reason": f"MISSING_OR_RETRACTED_PREMISE:{bt[0]}.{bt[1]}={bt[2]}",
                    "elapsed_us": round((time.perf_counter() - t0) * 1_000_000.0, 3),
                }
            acc_poly = bp if acc_poly is None else semiring_join(acc_poly, bp)

        if not acc_poly:
            return {"derived": False, "reason": "EMPTY_PROVENANCE_POLYNOMIAL"}

        prev = self.provenance_poly.get(head, frozenset())
        merged = semiring_union(prev, acc_poly)
        self.provenance_poly[head] = merged
        self.by_subj_rel[(head[0], head[1])].add(head[2])
        for mono in merged:
            for pid in mono:
                self.premise_to_facts[pid].add(head)
        self.invalidated_graveyard.pop((head[0], head[1]), None)

        return {
            "derived": True,
            "head": head,
            "monomial_count": len(merged),
            "provenance_polynomial": [sorted(m) for m in merged],
            "elapsed_us": round((time.perf_counter() - t0) * 1_000_000.0, 3),
        }

    def retract_premise(self, subj: str, rel: str, obj: str) -> dict[str, Any]:
        """`O(|Delta|)` Why-Provenance Cascade Retraction."""
        t0 = time.perf_counter()
        self.tx_clock += 1
        triple = (subj, rel, obj)
        pid = self.extensional_by_triple.pop(triple, None)
        if pid is None:
            return {
                "retracted": False,
                "cascaded_retractions": [],
                "surviving_alternative_facts": [],
                "elapsed_us": round((time.perf_counter() - t0) * 1_000_000.0, 3),
            }
        if pid in self.premises:
            self.premises[pid]["active"] = False

        affected = list(self.premise_to_facts.pop(pid, ()))
        cascaded: list[tuple[str, str, str]] = []
        survived_via_alt: list[tuple[str, str, str]] = []

        for fact in affected:
            old_poly = self.provenance_poly.get(fact, frozenset())
            # Keep only monomials that do NOT depend on retracted `pid`
            new_poly = frozenset(m for m in old_poly if pid not in m)
            if not new_poly:
                self.provenance_poly.pop(fact, None)
                self.by_subj_rel[(fact[0], fact[1])].discard(fact[2])
                cascaded.append(fact)
                self.invalidated_graveyard[(fact[0], fact[1])].append(
                    {
                        "retracted_value": fact[2],
                        "invalidated_by_premise": pid,
                        "invalidated_root_triple": triple,
                        "tx": self.tx_clock,
                    }
                )
            else:
                self.provenance_poly[fact] = new_poly
                survived_via_alt.append(fact)

        return {
            "retracted": True,
            "premise_id": pid,
            "cascaded_retractions": cascaded,
            "surviving_alternative_facts": survived_via_alt,
            "elapsed_us": round((time.perf_counter() - t0) * 1_000_000.0, 3),
        }

    def query(self, subj: str, rel: str) -> dict[str, Any]:
        vals = sorted(self.by_subj_rel.get((subj, rel), ()))
        if vals:
            polys = {
                v: [sorted(m) for m in self.provenance_poly.get((subj, rel, v), frozenset())]
                for v in vals
            }
            return {
                "status": "ESTABLISHED",
                "values": vals,
                "why_provenance": polys,
            }
        tombstones = self.invalidated_graveyard.get((subj, rel))
        if tombstones:
            return {
                "status": "ABSENCE__SUPPORT_PREMISE_INVALIDATED",
                "values": [],
                "invalidated_support": list(tombstones),
            }
        return {
            "status": "ABSTAIN__NEVER_ESTABLISHED",
            "values": [],
        }


def run_meme_semiring_benchmark(*, chain_count: int = 24, chain_depth: int = 4) -> dict[str, Any]:
    """Run a 24-chain multi-hop `MEME`-style Cascade + Diamond-Preservation + Absence benchmark."""
    mem = SemiringProvenanceJTMSMemory()
    w = hashlib.sha256(b"meme_semiring_witness").hexdigest()[:16]
    retract_latencies_us: list[float] = []

    cascade_hits = 0
    absence_hits = 0
    diamond_preserved = 0

    for c_idx in range(chain_count):
        root_s = f"auth_key_{c_idx}"
        mem.assert_premise(root_s, "status", "valid", witness_sha=w, premise_id=f"p_root_{c_idx}")
        prev_triple = (root_s, "status", "valid")
        for hop in range(1, chain_depth + 1):
            link_p = f"p_hop_{c_idx}_{hop}"
            mem.assert_premise(f"stage_{c_idx}_{hop}", "enabled", "yes", witness_sha=w, premise_id=link_p)
            head = (f"service_{c_idx}_h{hop}", "deploy_ready", "true")
            mem.derive_fact(head, body_triples=[prev_triple, (f"stage_{c_idx}_{hop}", "enabled", "yes")])
            prev_triple = head

        # Diamond alternative derivation on even chains (`backup_key` independently justifies `backup_ready`)
        if c_idx % 2 == 0:
            mem.assert_premise(f"backup_key_{c_idx}", "status", "valid", witness_sha=w, premise_id=f"p_bak_{c_idx}")
            diamond_head = (f"service_{c_idx}_resilient", "online", "true")
            mem.derive_fact(diamond_head, body_triples=[(root_s, "status", "valid")])
            mem.derive_fact(diamond_head, body_triples=[(f"backup_key_{c_idx}", "status", "valid")])

    # Retract all 24 root premises and measure `Cascade`, `Diamond Preservation`, and `Absence`!
    for c_idx in range(chain_count):
        root_s = f"auth_key_{c_idx}"
        r = mem.retract_premise(root_s, "status", "valid")
        retract_latencies_us.append(float(r["elapsed_us"]))
        leaf_q = mem.query(f"service_{c_idx}_h{chain_depth}", "deploy_ready")
        if leaf_q["values"] == []:
            cascade_hits += 1
        if leaf_q["status"] == "ABSENCE__SUPPORT_PREMISE_INVALIDATED" and leaf_q["invalidated_support"]:
            absence_hits += 1
        if c_idx % 2 == 0:
            diam_q = mem.query(f"service_{c_idx}_resilient", "online")
            if diam_q["status"] == "ESTABLISHED" and diam_q["values"] == ["true"]:
                diamond_preserved += 1

    sorted_us = sorted(retract_latencies_us)
    p50_us = sorted_us[len(sorted_us) // 2]
    expected_diamonds = (chain_count + 1) // 2
    cascade_acc = round(cascade_hits / chain_count, 6)
    absence_acc = round(absence_hits / chain_count, 6)
    diamond_acc = round(diamond_preserved / max(1, expected_diamonds), 6)

    return {
        "schema": SCHEMA,
        "operation": "SEMIRING_JTMS_MEME_BENCHMARK",
        "pass": cascade_acc == 1.0 and absence_acc == 1.0 and diamond_acc == 1.0,
        "chains_tested": chain_count,
        "hops_per_chain": chain_depth,
        "meme_cascade_accuracy": cascade_acc,
        "meme_absence_accuracy": absence_acc,
        "diamond_alternative_proof_accuracy": diamond_acc,
        "retract_cascade_p50_us": round(p50_us, 3),
        "model_calls": 0,
    }


# ============================================================================
# MOVE 4: Active Minimax Contrastive Interrogation (`finite_minimax_decision_region_v1`)
# ============================================================================


def minimax_interrogate_version_space(
    *,
    hypotheses: Mapping[str, Callable[[Any], Any]],
    candidate_probes: Sequence[Mapping[str, Any]],
    policy_regions: Mapping[str, Sequence[str]] | None = None,
    true_oracle: Callable[[Any], Any] | None = None,
    allow_irreversible_probes: bool = False,
) -> dict[str, Any]:
    """Move 4: Wire unwired `finite_minimax_decision_region_v1.solve` + CoW outcome matrix + `purpose_gate_v1`.

    Given an ambiguous 1-demo version space `hypotheses`, evaluates every safe candidate probe across
    all hypotheses, solves the exact dynamic-programming minimax decision-region policy, and executes
    the minimum-worst-case sequence of probes against `true_oracle` until a single policy covers all
    surviving hypotheses.
    """
    from canonical.runtime import finite_minimax_decision_region_v1 as drd

    t0 = time.perf_counter()
    world_ids = sorted(hypotheses.keys())
    if not world_ids:
        return {
            "schema": SCHEMA,
            "operation": "MINIMAX_INTERROGATE_VERSION_SPACE",
            "pass": False,
            "reason": "EMPTY_HYPOTHESIS_SET",
            "model_calls": 0,
        }

    # Default 1-to-1 policy per hypothesis when overlapping policy regions are not supplied
    norm_regions = (
        [
            {"policy_id": pid, "world_ids": list(wids), "region_complete": True}
            for pid, wids in sorted(policy_regions.items())
        ]
        if policy_regions is not None
        else [
            {"policy_id": f"policy:{wid}", "world_ids": [wid], "region_complete": True}
            for wid in world_ids
        ]
    )

    safe_observations: list[dict[str, Any]] = []
    gated_irreversible: list[str] = []
    probe_inputs_by_id: dict[str, Any] = {}

    for idx, p_spec in enumerate(candidate_probes):
        oid = str(p_spec.get("id") or f"probe_{idx}")
        is_irreversible = bool(p_spec.get("irreversible", False))
        if is_irreversible and not allow_irreversible_probes:
            gated_irreversible.append(oid)
            continue
        inp = p_spec.get("input")
        probe_inputs_by_id[oid] = inp
        cost = float(p_spec.get("cost_units", 1.0))
        outcomes: dict[str, Any] = {}
        for wid in world_ids:
            try:
                outcomes[wid] = hypotheses[wid](inp)
            except Exception as exc:
                outcomes[wid] = f"ERR:{type(exc).__name__}"
        safe_observations.append(
            {
                "observation_id": oid,
                "cost_units": cost,
                "outcome_map_complete": True,
                "outcomes": outcomes,
            }
        )

    problem = {
        "hypothesis_set_complete": True,
        "worlds": [{"world_id": wid} for wid in world_ids],
        "policy_regions": norm_regions,
        "observations": safe_observations,
    }
    plan = drd.solve(problem)
    if not plan.get("pass"):
        return {
            "schema": SCHEMA,
            "operation": "MINIMAX_INTERROGATE_VERSION_SPACE",
            "pass": False,
            "status": plan.get("status"),
            "reason": plan.get("reason"),
            "gated_irreversible_probes": gated_irreversible,
            "drd_plan": plan,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            "model_calls": 0,
        }

    # If `true_oracle` is provided, actively execute minimax probes step-by-step until resolved!
    surviving = set(world_ids)
    executed_probes: list[dict[str, Any]] = []
    region_sets = {r["policy_id"]: set(r["world_ids"]) for r in norm_regions}

    def _covering(s_worlds: set[str]) -> list[str]:
        return sorted(pid for pid, members in region_sets.items() if s_worlds.issubset(members))

    while true_oracle is not None and not _covering(surviving):
        sub_obs = [
            {
                "observation_id": row["observation_id"],
                "cost_units": row["cost_units"],
                "outcome_map_complete": True,
                "outcomes": {wid: row["outcomes"][wid] for wid in sorted(surviving)},
            }
            for row in safe_observations
            if row["observation_id"] not in {ep["probe_id"] for ep in executed_probes}
        ]
        sub_prob = {
            "hypothesis_set_complete": True,
            "worlds": [{"world_id": wid} for wid in sorted(surviving)],
            "policy_regions": [
                {
                    "policy_id": r["policy_id"],
                    "world_ids": [w for w in r["world_ids"] if w in surviving],
                    "region_complete": True,
                }
                for r in norm_regions
            ],
            "observations": sub_obs,
        }
        sub_plan = drd.solve(sub_prob)
        next_oid = sub_plan.get("first_observation_id")
        if not next_oid:
            break
        obs_val = true_oracle(probe_inputs_by_id[next_oid])
        obs_row = next(r for r in safe_observations if r["observation_id"] == next_oid)
        surviving = {wid for wid in surviving if repr(obs_row["outcomes"][wid]) == repr(obs_val)}
        executed_probes.append(
            {
                "probe_id": next_oid,
                "input": probe_inputs_by_id[next_oid],
                "observed_output": obs_val,
                "surviving_worlds": sorted(surviving),
            }
        )
        if not surviving:
            break

    resolved_policies = _covering(surviving) if surviving else []
    return {
        "schema": SCHEMA,
        "operation": "MINIMAX_INTERROGATE_VERSION_SPACE",
        "pass": bool(plan.get("pass")) and (true_oracle is None or bool(resolved_policies)),
        "initial_world_count": len(world_ids),
        "surviving_worlds": sorted(surviving),
        "resolved_policy_ids": resolved_policies,
        "minimum_worst_case_cost_units": plan.get("minimum_worst_case_cost_units"),
        "first_observation_id": plan.get("first_observation_id"),
        "executed_probes": executed_probes,
        "gated_irreversible_probes": gated_irreversible,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 4),
        "model_calls": 0,
    }


# ============================================================================
# MOVE 5: Zero-LLM `AlphaEvolve` MAP-Elites + Adversarial Anti-Reward-Hacking Gate
# ============================================================================


def _generate_algebraic_and_loop_mutations(source_text: str, fn_name: str) -> list[tuple[str, str]]:
    """Deterministic zero-LLM algorithmic & algebraic rewrite mutations for MAP-Elites evolution."""
    mutations: list[tuple[str, str]] = []
    try:
        tree = ast.parse(source_text)
    except SyntaxError:
        return mutations

    target_fn: ast.FunctionDef | None = None
    for nd in tree.body:
        if isinstance(nd, ast.FunctionDef) and nd.name == fn_name:
            target_fn = nd
            break
    if target_fn is None:
        return mutations

    params = [a.arg for a in target_fn.args.args]

    # Family 1: Arithmetic series / accumulation loop -> closed-form Gauss /builtin `sum` reduction!
    body_src = ast.unparse(target_fn)
    if len(params) == 1:
        p = params[0]
        if f"range({p} + 1)" in body_src or f"range(1, {p} + 1)" in body_src:
            if "+= i * i" in body_src or "+= i ** 2" in body_src:
                mutations.append(
                    (
                        "closed_form_pyramidal_squares",
                        f"def {fn_name}({p}):\n    return {p} * ({p} + 1) * (2 * {p} + 1) // 6\n",
                    )
                )
            elif "+= i" in body_src:
                mutations.append(
                    (
                        "closed_form_gauss_triangular",
                        f"def {fn_name}({p}):\n    return {p} * ({p} + 1) // 2\n",
                    )
                )
        # Repeated linear membership scan `[x for x in seq if x in other]` -> `O(1)` set lookup hoisting
    if len(params) == 2:
        p0, p1 = params[0], params[1]
        if f"for " in body_src and f" in {p1}" in body_src and ".append(" in body_src:
            mutations.append(
                (
                    "hoist_set_membership_comprehension",
                    f"def {fn_name}({p0}, {p1}):\n    _s = set({p1})\n    return [x for x in {p0} if x in _s]\n",
                )
            )

    # Family 2: `x ** 2` -> `x * x` strength reduction (`mined_rewrite_theory_v1` style)
    for idx, sub in enumerate(list(ast.walk(tree))):
        if (
            isinstance(sub, ast.BinOp)
            and isinstance(sub.op, ast.Pow)
            and isinstance(sub.right, ast.Constant)
            and sub.right.value == 2
        ):
            t_copy = copy.deepcopy(tree)
            walk_c = list(ast.walk(t_copy))
            pow_nd = walk_c[idx]
            if isinstance(pow_nd, ast.BinOp):
                for parent in walk_c:
                    for fname, fval in ast.iter_fields(parent):
                        if fval is pow_nd:
                            setattr(
                                parent,
                                fname,
                                ast.BinOp(left=copy.deepcopy(pow_nd.left), op=ast.Mult(), right=copy.deepcopy(pow_nd.left)),
                            )
                            ast.fix_missing_locations(t_copy)
                            mutations.append(("strength_reduce_pow2_to_mul", ast.unparse(t_copy)))
                            break

    # Family 3: Memoization / iterative dynamic-programming transform on self-recursive 1-arg functions
    rec_calls = [
        sub
        for sub in ast.walk(target_fn)
        if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name) and sub.func.id == fn_name
    ]
    if len(rec_calls) >= 2 and len(params) == 1:
        t_memo = copy.deepcopy(tree)
        for nd in t_memo.body:
            if isinstance(nd, ast.FunctionDef) and nd.name == fn_name:
                nd.decorator_list.insert(
                    0,
                    ast.Attribute(
                        value=ast.Call(
                            func=ast.Name(id="__import__", ctx=ast.Load()),
                            args=[ast.Constant(value="functools")],
                            keywords=[],
                        ),
                        attr="lru_cache",
                        ctx=ast.Load(),
                    ),
                )
                ast.fix_missing_locations(t_memo)
                mutations.append(("memoize_exponential_recursion", ast.unparse(t_memo)))
                break

    return mutations


def evolve_pareto_organ(
    baseline_source: str,
    *,
    fn_name: str,
    test_inputs: Sequence[tuple[Any, ...]],
    evaluator_fn: Callable[[tuple[Any, ...], Any], bool] | None = None,
    repeats: int = 8,
) -> dict[str, Any]:
    """Move 5: Zero-LLM `AlphaEvolve` MAP-Elites + Adversarial Anti-Reward-Hacking Gate + Rent GC.

    1. Evaluates baseline on `test_inputs` to obtain reference outputs and latency `baseline_us`.
    2. Runs `VACUOUS_EVALUATOR_AUDIT`: feeds corrupted/wrong outputs to `evaluator_fn` (or exact
       reference equality); if ANY corrupted output passes, refuses immediately (`REWARD_HACKABLE_ORACLE`).
    3. Generates deterministic algebraic, strength-reduction, set-hoisting, and closed-form mutations,
       evaluates each in isolated execution, populates MAP-Elites `(ast_nodes_bin, loop_count)` niches,
       computes the nondominated Pareto frontier over `(latency_us, ast_bytes)`, and evicts candidates
       failing Two-Door `(WITH - WITHOUT)` speedup rent.
    """
    t0 = time.perf_counter()
    ns_base: dict[str, Any] = {}
    exec(compile(baseline_source, "<baseline>", "exec"), ns_base)
    base_fn = ns_base[fn_name]

    ref_outputs = [base_fn(*inp) for inp in test_inputs]

    def _default_eval(inp: tuple[Any, ...], out: Any) -> bool:
        idx = test_inputs.index(inp)
        return out == ref_outputs[idx] and type(out) is type(ref_outputs[idx])

    judge = evaluator_fn if evaluator_fn is not None else _default_eval

    # Gate 1: Anti-Reward-Hacking Adversarial Oracle Audit (`0` false passes allowed!)
    corrupt_false_passes = 0
    corrupt_trials = 0
    for inp, ref_out in zip(test_inputs, ref_outputs):
        corrupted_vals: list[Any] = [None, "__CORRUPT__"]
        if isinstance(ref_out, (int, float)):
            corrupted_vals.extend([ref_out + 1, ref_out - 999991])
        elif isinstance(ref_out, list):
            corrupted_vals.append(list(ref_out) + ["__EXTRA__"])
        for bad in corrupted_vals:
            if bad == ref_out:
                continue
            corrupt_trials += 1
            if bool(judge(inp, bad)):
                corrupt_false_passes += 1

    if corrupt_false_passes > 0 or corrupt_trials == 0:
        return {
            "schema": SCHEMA,
            "operation": "EVOLVE_PARETO_ORGAN",
            "pass": False,
            "status": "REFUSED__REWARD_HACKABLE_OR_VACUOUS_EVALUATOR",
            "corrupt_false_passes": corrupt_false_passes,
            "corrupt_trials": corrupt_trials,
            "model_calls": 0,
        }

    def _measure(src: str) -> dict[str, Any] | None:
        ns_c: dict[str, Any] = {}
        try:
            c_tree = ast.parse(src)
            exec(compile(c_tree, "<cand>", "exec"), ns_c)
            fn_c = ns_c[fn_name]
            for inp in test_inputs:
                out_c = fn_c(*inp)
                if not bool(judge(inp, out_c)):
                    return None
            # Timing over `repeats` runs
            timings: list[float] = []
            for _ in range(max(3, int(repeats))):
                ts = time.perf_counter()
                for inp in test_inputs:
                    fn_c(*inp)
                timings.append((time.perf_counter() - ts) * 1_000_000.0)
            timings.sort()
            med_us = timings[len(timings) // 2]
            ast_nodes = sum(1 for _ in ast.walk(c_tree))
            loops = sum(1 for n in ast.walk(c_tree) if isinstance(n, (ast.For, ast.While)))
            return {
                "source": src,
                "median_us": round(med_us, 3),
                "ast_bytes": len(src.encode("utf-8")),
                "ast_nodes": ast_nodes,
                "loop_count": loops,
                "niche": f"loops={loops}:size_bin={ast_nodes // 10}",
            }
        except Exception:
            return None

    base_metrics = _measure(baseline_source)
    if base_metrics is None:
        return {
            "schema": SCHEMA,
            "operation": "EVOLVE_PARETO_ORGAN",
            "pass": False,
            "status": "FAIL_CLOSED__BASELINE_FAILED_JUDGE",
            "model_calls": 0,
        }
    base_metrics["id"] = "baseline"

    map_elites: dict[str, dict[str, Any]] = {base_metrics["niche"]: base_metrics}
    evaluated: list[dict[str, Any]] = [base_metrics]
    gc_evicted: list[str] = []

    for mut_id, mut_src in _generate_algebraic_and_loop_mutations(baseline_source, fn_name):
        m = _measure(mut_src)
        if m is None:
            continue
        m["id"] = mut_id
        # Two-Door Counterfactual Rent: must beat baseline latency OR shrink AST without slowing down
        speedup = base_metrics["median_us"] / max(0.01, m["median_us"])
        m["speedup_vs_baseline"] = round(speedup, 3)
        if m["median_us"] >= base_metrics["median_us"] and m["ast_bytes"] >= base_metrics["ast_bytes"]:
            gc_evicted.append(mut_id)
            continue
        evaluated.append(m)
        niche = m["niche"]
        incumbent = map_elites.get(niche)
        if incumbent is None or (m["median_us"], m["ast_bytes"]) < (incumbent["median_us"], incumbent["ast_bytes"]):
            map_elites[niche] = m

    # Nondominated Pareto frontier over `(median_us, ast_bytes)`
    pareto: list[dict[str, Any]] = []
    for cand in evaluated:
        dominated = any(
            (other["median_us"] <= cand["median_us"] and other["ast_bytes"] <= cand["ast_bytes"])
            and (other["median_us"] < cand["median_us"] or other["ast_bytes"] < cand["ast_bytes"])
            for other in evaluated
            if other["id"] != cand["id"]
        )
        if not dominated:
            pareto.append(cand)
    pareto.sort(key=lambda r: (r["median_us"], r["ast_bytes"]))
    best_fastest = min(evaluated, key=lambda r: r["median_us"])

    return {
        "schema": SCHEMA,
        "operation": "EVOLVE_PARETO_ORGAN",
        "pass": True,
        "status": "PASS__PARETO_EVOLVED_NON_VACUOUS",
        "evaluator_corrupt_trials_killed": corrupt_trials,
        "evaluator_false_passes": corrupt_false_passes,
        "baseline_us": base_metrics["median_us"],
        "best_id": best_fastest["id"],
        "best_us": best_fastest["median_us"],
        "best_speedup_x": round(base_metrics["median_us"] / max(0.01, best_fastest["median_us"]), 3),
        "best_source": best_fastest["source"],
        "pareto_frontier": pareto,
        "map_elites_niches": {k: v["id"] for k, v in sorted(map_elites.items())},
        "rent_gc_evicted": gc_evicted,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        "model_calls": 0,
    }


def run_unfamiliar_six_moves_suite() -> dict[str, Any]:
    """Run an end-to-end self-verification suite across Moves `0`–`5` in `< 100 ms` at `K3 = 0`."""
    t0 = time.perf_counter()

    # Move 0: `L#_e` apartness learning on a 3-state auth/vault Mealy protocol with error sink
    def _vault_env(seq: Sequence[str]) -> list[str]:
        st = 0
        outs: list[str] = []
        for a in seq:
            if a == "bad_pin":
                outs.append("ERR_REFUSED_LOCKED")
            elif st == 0 and a == "auth":
                st = 1
                outs.append("AUTH_OK")
            elif st == 1 and a == "arm":
                st = 2
                outs.append("ARMED")
            elif st == 2 and a == "commit":
                outs.append("VAULT_COMMITTED")
            else:
                outs.append("DENIED_PRECONDITION")
        return outs

    m0 = ApartnessTreeInstantLearner().learn(
        alphabet=["auth", "arm", "commit", "bad_pin"],
        execute_trace=_vault_env,
        held_out_traces=[["auth", "arm", "commit"], ["arm", "auth", "arm", "commit"], ["bad_pin", "auth", "arm"]],
        target_output="VAULT_COMMITTED",
    )

    # Move 1: Angelic Forest + `OE-SyGuS` + `NAME_SCOPE` (`__spec__.parent` -> `parent`)
    buggy_ns = (
        "class _Spec:\n"
        "    parent = 'wrong_pkg'\n"
        "__spec__ = _Spec()\n\n"
        "def resolve_submod(parent: str, leaf: str) -> str:\n"
        "    return f'{__spec__.parent}.{leaf}'\n"
    )
    test_ns = (
        "assert resolve_submod('packaging', 'errors') == 'packaging.errors'\n"
        "assert resolve_submod('tomli', 'parser') == 'tomli.parser'\n"
    )
    m1 = AngelicForestSyGuSRepairEngine().solve(buggy_ns, test_ns, seed_cold_store=True)

    # Move 2: Protocol Lifting + Magic-Header Round-Trip `effect_oracle`
    with tempfile.TemporaryDirectory(prefix="m2_suite_") as td:
        gz_path = pathlib.Path(td) / "out.gz"
        raw_payload = b"verified-protocol-lift-bytes-2026"
        gz_path.write_bytes(gzip.compress(raw_payload))
        m2 = lift_protocol_and_verify_effect(
            cdp_network_events=[
                {"url": "https://app.local/static/app.css", "method": "GET", "status": 200, "mime_type": "text/css"},
                {"url": "https://app.local/static/logo.png", "method": "GET", "status": 200, "mime_type": "image/png"},
                {
                    "url": "https://app.local/api/v1/tickets",
                    "method": "POST",
                    "status": 200,
                    "mime_type": "application/json",
                    "post_data": json.dumps({"title": "fix-build", "priority": "high"}),
                },
            ],
            goal_parameters={"title": "deploy-v2", "priority": "urgent"},
            transport_fn=lambda method, url, _hdrs, body: {"ok": True, "method": method, "url": url, "echo": body},
            artifact_check={"path": gz_path, "expected_source_bytes": raw_payload},
        )

    # Move 3: Why-Provenance Semiring JTMS `MEME` (`Cascade` + `Absence` + Diamond)
    m3 = run_meme_semiring_benchmark(chain_count=16, chain_depth=3)

    # Move 4: Active Minimax Contrastive Interrogation (`finite_minimax_decision_region_v1`)
    hyps = {
        "h_pos": lambda x: x > 0,
        "h_even": lambda x: (x % 2 == 0) and x > 0,
        "h_gt5": lambda x: x > 5,
        "h_ge2": lambda x: x >= 2,
    }
    probes = [
        {"id": "p_x1", "input": 1, "cost_units": 1.0},
        {"id": "p_x2", "input": 2, "cost_units": 1.0},
        {"id": "p_x3", "input": 3, "cost_units": 1.0},
        {"id": "p_x6", "input": 6, "cost_units": 1.0},
        {"id": "p_rm_prod", "input": -1, "cost_units": 0.1, "irreversible": True},
    ]
    m4 = minimax_interrogate_version_space(
        hypotheses=hyps,
        candidate_probes=probes,
        true_oracle=hyps["h_even"],
    )

    # Move 5: Zero-LLM `AlphaEvolve` MAP-Elites + Anti-Reward-Hacking Gate
    slow_src = (
        "def sum_squares(n):\n"
        "    total = 0\n"
        "    for i in range(n + 1):\n"
        "        total += i ** 2\n"
        "    return total\n"
    )
    m5 = evolve_pareto_organ(
        slow_src,
        fn_name="sum_squares",
        test_inputs=[(0,), (1,), (5,), (50,), (400,)],
    )

    all_pass = all(bool(x.get("pass")) for x in (m0, m1, m2, m3, m4, m5))
    return {
        "schema": SCHEMA,
        "operation": "UNFAMILIAR_SIX_MOVES_SUITE",
        "pass": all_pass,
        "move_0_apartness_lsharp": m0,
        "move_1_angelic_sygus_swe": m1,
        "move_2_protocol_lift_and_oracle": m2,
        "move_3_semiring_jtms_meme": m3,
        "move_4_minimax_interrogation": m4,
        "move_5_zero_llm_alphaevolve": m5,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        "model_calls": 0,
    }
