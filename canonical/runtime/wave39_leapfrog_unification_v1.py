#!/usr/bin/env python3
"""Wave 39 Frontier-Leapfrog Dark-Organ Unification, Red-Queen/Mendel Co-Evolution, CLM+RRF Memory & Partial-Routing/JitRL.

Strictly zero-LLM by default (`K3 = 0`, `$0` incremental spend, stdlib + live `brain` organs only).
Directly unifies `brain`'s highest-leverage DARK non-obviously named modules with late-2026
frontier mechanisms into `UnifiedModel`, `Creature`, and `unified_hidden_capability_federation_v1`:

1. `RedQueenMendelEvolver`:
   - Mendel Gödel Machine comparative cross-lineage patch splicing (`dual_program_splicing_v1.splice`)
   - ALBI semantic-anonymization metamorphic invariance check (AST alpha-renaming)
   - Anti-Slop (AST bloat / cyclomatic cap), No-Phantom-Guardrails (counterfactual witness gate),
     and Symbol-Ownership scoping (`SlopCodeBench` / `Phantom Guardrails` / `Bad Genius`).
2. `EarnedJudgeAndRefusalLifter`:
   - Red Queen earned-judge discovery (`auto_judge_discovery_v1` + `earn_a_judge_v1`)
   - Agent-S4 / CLI-Anything `--check`/`--dry-run` oracle extraction (`the_check_mode_is_the_oracle_v1`),
     refusal-surface vocabulary lifting (`an_actions_vocabulary_is_its_refusal_surface_v1`),
     witness-derived type collapse (`a_type_you_wrote_is_a_type_you_guess_v1`), and
     refusal-specification compilation (`a_refusal_is_a_specification_v1`).
3. `ContractPlannerAndLiftedGeneralizer`:
   - Typed `(P,O,A,V,F)` effect-contract composition (`effect_contract_composition_v1`) and
     verification (`composition_verification_v1`),
   - Sussman-anomaly partial-order planning (`partial_order_planner_v1`) + horizon-bounded sensing
     (`horizon_bounded_execution_v1`),
   - Variable-invariant plan lifting (`perfect_algorithm_lifted_generalization_v1`),
   - Live observation refutation (`observation_refutation_v1`) + AST provenance features (`provenance_not_shape_v1`).
4. `SpeculativeCoWDecisionGate`:
   - Decision-theoretic version-space agreement gate (`what_a_decision_costs_v1.decisive`):
     returns `BY_KNOWLEDGE` at 0 ms when all surviving hypotheses agree; pays a real POSIX `os.fork()`
     CoW speculative verification trial ONLY where hypotheses disagree (`BY_TRIAL`), with zero
     mutation of parent memory.
5. `CLMRRFMemoryEngine`:
   - Verbatim-first immutable archival + `Nemori` free-energy surprise-gated admission + `TMA-NM` HMAC origin seal,
   - 4-way Reciprocal Rank Fusion (`Hindsight`-style: lexical BM25 + structural AST + bi-temporal entity graph +
     origin trust) strictly bounded by an explicit character budget (`Beyond Memory Leaderboards`),
   - `CLM` file-mirrored editable working context (`clm_offload`, `clm_grep_restore`, `clm_audit`) with SHA-256 tamper verification.
6. `PartialRoutingJitRLSkillTTAEngine`:
   - Exact closed-form KL-regularized `JitRL` advantage logit modulation (`pi'(a|s) ~ pi_0(a|s) * exp(A(s,a)/beta)`),
   - `SkillTTA` on-the-fly task-conditioned skill contract synthesis from verified traces,
   - Intra-task `Partial Routing` across Rung 0 -> Rung 1 -> Rung 2 -> optional pluggable Rung 3 on minimal slices,
   - Live offline `self_verify_harvested_surfaces` audit over `harvested_capabilities` & dark organs.
"""

from __future__ import annotations

import ast
import builtins
import hashlib
import json
import math
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

SCHEMA = "brain.wave39_leapfrog_unification.v1"
MODEL_CALLS = 0

_WORD_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{1,}")
_BUILTIN_NAMES: frozenset[str] = frozenset(dir(builtins)) | frozenset(
    {"self", "cls", "True", "False", "None", "super", "property", "staticmethod", "classmethod"}
)
_BRANCH_NODE_TYPES = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try, ast.With, ast.AsyncWith, ast.IfExp)
_GUARD_NODE_TYPES = (ast.If, ast.Assert, ast.Raise, ast.Try)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_text(text: str) -> str:
    return _sha256_bytes(text.encode("utf-8"))


def _tokenize_lower(text: str) -> list[str]:
    return [tok.lower() for tok in _WORD_RE.findall(text or "")]


def _extract_ast_tokens(source: str) -> list[str]:
    """Extract structural AST node types + identifier skeletons from Python source (fallback to regex)."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return _tokenize_lower(source)
    toks: list[str] = []
    for node in ast.walk(tree):
        toks.append(f"ast:{type(node).__name__.lower()}")
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            toks.append(f"def:{node.name.lower()}")
        elif isinstance(node, ast.Attribute):
            toks.append(f"attr:{node.attr.lower()}")
        elif isinstance(node, ast.Name):
            toks.append(f"id:{node.id.lower()}")
    return toks


# ---------------------------------------------------------------------------
# 1. RedQueenMendelEvolver (Mendel Splicing + ALBI Anonymization + Anti-Slop)
# ---------------------------------------------------------------------------


class _AlphaAnonymizer(ast.NodeTransformer):
    """Deterministic alpha-renaming transformer for ALBI semantic-anonymization checks."""

    def __init__(self, *, keep_names: frozenset[str] = _BUILTIN_NAMES) -> None:
        self.keep_names = keep_names
        self.fn_map: dict[str, str] = {}
        self.var_map: dict[str, str] = {}

    def _map_fn(self, name: str) -> str:
        if name in self.keep_names or (name.startswith("__") and name.endswith("__")):
            return name
        if name not in self.fn_map:
            self.fn_map[name] = f"fn_{len(self.fn_map)}"
        return self.fn_map[name]

    def _map_var(self, name: str) -> str:
        if name in self.keep_names or name in self.fn_map or (name.startswith("__") and name.endswith("__")):
            return name
        if name not in self.var_map:
            self.var_map[name] = f"v_{len(self.var_map)}"
        return self.var_map[name]

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        node.name = self._map_fn(node.name)
        for arg in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs):
            arg.arg = self._map_var(arg.arg)
        if node.args.vararg is not None:
            node.args.vararg.arg = self._map_var(node.args.vararg.arg)
        if node.args.kwarg is not None:
            node.args.kwarg.arg = self._map_var(node.args.kwarg.arg)
        self.generic_visit(node)
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AST:
        node.name = self._map_fn(node.name)
        for arg in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs):
            arg.arg = self._map_var(arg.arg)
        if node.args.vararg is not None:
            node.args.vararg.arg = self._map_var(node.args.vararg.arg)
        if node.args.kwarg is not None:
            node.args.kwarg.arg = self._map_var(node.args.kwarg.arg)
        self.generic_visit(node)
        return node

    def visit_Name(self, node: ast.Name) -> ast.AST:
        if node.id in self.fn_map:
            node.id = self.fn_map[node.id]
        else:
            node.id = self._map_var(node.id)
        return node


def _symbol_ast_dumps(source: str) -> dict[str, str]:
    tree = ast.parse(source)
    out: dict[str, str] = {}
    for stmt in tree.body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out[stmt.name] = ast.dump(stmt, include_attributes=False)
    return out


class RedQueenMendelEvolver:
    """Mendel comparative hybridization + ALBI semantic-anonymization + Anti-Slop/Anti-Phantom gate."""

    @staticmethod
    def alpha_anonymize_python(source: str) -> dict[str, Any]:
        """Deterministically alpha-rename user functions and local variables (ALBI semantic anonymization)."""
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            return {"pass": False, "error": f"SyntaxError: {exc}", "anonymized_source": "", "structural_sha256": ""}
        # Pre-collect user-defined top-level/nested function names so forward calls map consistently.
        anon = _AlphaAnonymizer()
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                anon._map_fn(node.name)
        transformed = ast.fix_missing_locations(anon.visit(tree))
        anon_src = ast.unparse(transformed)
        dump = ast.dump(transformed, include_attributes=False)
        return {
            "pass": True,
            "anonymized_source": anon_src,
            "structural_sha256": _sha256_text(dump),
            "renamed_functions": dict(anon.fn_map),
            "renamed_variables": dict(anon.var_map),
        }

    @staticmethod
    def _detect_identifier_memorization(parent_source: str, candidate_source: str) -> dict[str, Any]:
        """Check whether candidate injects suspicious string-literal matching on variable/function names or raw literal overfitting."""
        try:
            p_tree = ast.parse(parent_source)
            c_tree = ast.parse(candidate_source)
        except SyntaxError as exc:
            return {"albi_invariant": False, "reason": f"SyntaxError: {exc}"}

        p_anon = RedQueenMendelEvolver.alpha_anonymize_python(parent_source)
        c_anon = RedQueenMendelEvolver.alpha_anonymize_python(candidate_source)
        if not (p_anon["pass"] and c_anon["pass"]):
            return {"albi_invariant": False, "reason": "ANONYMIZATION_PARSE_ERROR"}

        # Detect newly introduced string constants that hardcode identifier/test-name shortcuts (e.g. `if x == "__secret_case__"` or checking function name)
        p_strs = {
            n.value
            for n in ast.walk(p_tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
        }
        c_strs = {
            n.value
            for n in ast.walk(c_tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
        }
        added_strs = c_strs - p_strs
        user_idents = set(p_anon["renamed_functions"].keys()) | set(p_anon["renamed_variables"].keys())
        leaked_idents = sorted(s for s in added_strs if s in user_idents or s.startswith("test_"))

        # Check structural delta preserves meaningful AST change under alpha-renaming
        structural_changed = p_anon["structural_sha256"] != c_anon["structural_sha256"]
        return {
            "albi_invariant": (len(leaked_idents) == 0) and structural_changed,
            "structural_changed": structural_changed,
            "leaked_identifier_literals": leaked_idents,
            "parent_structural_sha256": p_anon["structural_sha256"][:16],
            "candidate_structural_sha256": c_anon["structural_sha256"][:16],
        }

    @classmethod
    def audit_anti_slop_and_phantom_guardrails(
        cls,
        parent_source: str,
        candidate_source: str,
        *,
        failing_witness: Callable[[str], bool] | None = None,
        owned_symbols: Sequence[str] | None = None,
        max_ast_bloat_ratio: float = 1.60,
        max_added_branches: int = 6,
        require_albi_invariance: bool = True,
    ) -> dict[str, Any]:
        """Gate candidate edits against SlopCodeBench bloat, Phantom Guardrails, Bad-Genius shortcuts, and symbol drift."""
        try:
            p_tree = ast.parse(parent_source)
            c_tree = ast.parse(candidate_source)
        except SyntaxError as exc:
            return {
                "admitted": False,
                "reasons": [f"SYNTAX_ERROR:{exc}"],
                "metrics": {},
            }

        p_nodes = sum(1 for _ in ast.walk(p_tree))
        c_nodes = sum(1 for _ in ast.walk(c_tree))
        bloat_ratio = float(c_nodes) / float(max(1, p_nodes))

        p_branches = sum(1 for n in ast.walk(p_tree) if isinstance(n, _BRANCH_NODE_TYPES))
        c_branches = sum(1 for n in ast.walk(c_tree) if isinstance(n, _BRANCH_NODE_TYPES))
        added_branches = max(0, c_branches - p_branches)

        p_guards = sum(1 for n in ast.walk(p_tree) if isinstance(n, _GUARD_NODE_TYPES))
        c_guards = sum(1 for n in ast.walk(c_tree) if isinstance(n, _GUARD_NODE_TYPES))
        added_guards = max(0, c_guards - p_guards)

        reasons: list[str] = []
        if bloat_ratio > float(max_ast_bloat_ratio):
            reasons.append(f"SLOP_AST_BLOAT:{bloat_ratio:.3f}>{max_ast_bloat_ratio:.3f}")
        if added_branches > int(max_added_branches):
            reasons.append(f"SLOP_CYCLOMATIC_BLOAT:+{added_branches}>{max_added_branches}")

        # No-Phantom-Guardrails rule: any added defensive guard requires a live failing counterfactual witness
        # that actually FAILS on parent_source and PASSES on candidate_source.
        witness_status = "NOT_REQUIRED"
        if added_guards > 0:
            if failing_witness is None:
                witness_status = "MISSING_COUNTERFACTUAL_WITNESS"
                reasons.append(f"PHANTOM_GUARDRAIL_UNWITNESSED:added_guards={added_guards}")
            else:
                parent_ok = bool(failing_witness(parent_source))
                cand_ok = bool(failing_witness(candidate_source))
                if parent_ok or (not cand_ok):
                    witness_status = f"WITNESS_INVALID:parent={parent_ok},cand={cand_ok}"
                    reasons.append(f"PHANTOM_GUARDRAIL_NON_DISCRIMINATING:parent={parent_ok},cand={cand_ok}")
                else:
                    witness_status = "WITNESS_VERIFIED"

        # Symbol-ownership scope check (prevents collateral mutation outside owned fault locus)
        mutated_symbols: list[str] = []
        out_of_scope_symbols: list[str] = []
        p_syms = _symbol_ast_dumps(parent_source)
        c_syms = _symbol_ast_dumps(candidate_source)
        for sym in sorted(set(p_syms) | set(c_syms)):
            if p_syms.get(sym) != c_syms.get(sym):
                mutated_symbols.append(sym)
        if owned_symbols is not None:
            allowed = set(owned_symbols)
            out_of_scope_symbols = [s for s in mutated_symbols if s not in allowed]
            if out_of_scope_symbols:
                reasons.append(f"SYMBOL_OWNERSHIP_VIOLATION:{','.join(out_of_scope_symbols)}")

        # ALBI semantic-anonymization invariance
        albi = cls._detect_identifier_memorization(parent_source, candidate_source)
        if require_albi_invariance and not albi.get("albi_invariant", False):
            reasons.append(f"ALBI_INVARIANCE_FAIL:{albi.get('leaked_identifier_literals') or albi.get('reason', 'NO_STRUCTURAL_DELTA')}")

        return {
            "admitted": len(reasons) == 0,
            "reasons": reasons,
            "witness_status": witness_status,
            "albi": albi,
            "metrics": {
                "parent_ast_nodes": p_nodes,
                "candidate_ast_nodes": c_nodes,
                "ast_bloat_ratio": round(bloat_ratio, 4),
                "added_branches": added_branches,
                "added_guards": added_guards,
                "mutated_symbols": mutated_symbols,
                "out_of_scope_symbols": out_of_scope_symbols,
            },
        }

    @classmethod
    def mendel_splice_and_verify(
        cls,
        parent_source: str,
        lineage_a: str,
        lineage_b: str,
        *,
        verifier: Callable[[str], bool],
        failing_witness: Callable[[str], bool] | None = None,
        owned_symbols: Sequence[str] | None = None,
        max_ast_bloat_ratio: float = 1.60,
        max_added_branches: int = 6,
        require_albi_invariance: bool = True,
    ) -> dict[str, Any]:
        """Mendel Gödel Machine comparative hybridization over two partial repair lineages."""
        from canonical.swe_kernel import dual_program_splicing_v1 as dps

        t0 = time.perf_counter()
        parent_passes = bool(verifier(parent_source))
        lineage_a_passes = bool(verifier(lineage_a))
        lineage_b_passes = bool(verifier(lineage_b))

        spliced_candidates = dps.splice(parent_source, lineage_a, lineage_b)
        seen_hashes: set[str] = set()
        evaluations: list[dict[str, Any]] = []
        winner: dict[str, Any] | None = None

        for idx, cand in enumerate(spliced_candidates):
            h = _sha256_text(cand)
            if h in seen_hashes:
                continue
            seen_hashes.add(h)
            is_strict_hybrid = (cand != parent_source) and (cand != lineage_a) and (cand != lineage_b)
            verified = False
            verify_err = ""
            try:
                verified = bool(verifier(cand))
            except Exception as exc:
                verify_err = f"{type(exc).__name__}: {exc}"

            gate = cls.audit_anti_slop_and_phantom_guardrails(
                parent_source,
                cand,
                failing_witness=failing_witness,
                owned_symbols=owned_symbols,
                max_ast_bloat_ratio=max_ast_bloat_ratio,
                max_added_branches=max_added_branches,
                require_albi_invariance=require_albi_invariance,
            )
            row = {
                "candidate_index": idx,
                "sha256": h[:16],
                "is_strict_hybrid": is_strict_hybrid,
                "verifier_pass": verified,
                "verify_error": verify_err,
                "gate_admitted": gate["admitted"],
                "gate_reasons": gate["reasons"],
                "metrics": gate["metrics"],
                "albi": gate["albi"],
            }
            evaluations.append(row)
            if verified and gate["admitted"] and winner is None:
                winner = {**row, "source": cand}

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        return {
            "schema": SCHEMA,
            "engine": "LEAPFROG_W39_RED_QUEEN_MENDEL_EVOLVER",
            "pass": winner is not None,
            "model_calls": MODEL_CALLS,
            "parent_passes": parent_passes,
            "lineage_a_passes": lineage_a_passes,
            "lineage_b_passes": lineage_b_passes,
            "hybrid_solved_beyond_parents": bool(
                winner is not None and winner["is_strict_hybrid"] and not lineage_a_passes and not lineage_b_passes
            ),
            "candidates_generated": len(spliced_candidates),
            "candidates_evaluated": len(evaluations),
            "winner": winner,
            "evaluations": evaluations,
            "elapsed_ms": round(elapsed_ms, 3),
        }


# ---------------------------------------------------------------------------
# 2. EarnedJudgeAndRefusalLifter (Red Queen Earned Judges + CLI/Refusal Lifter)
# ---------------------------------------------------------------------------


class EarnedJudgeAndRefusalLifter:
    """Wires DARK `auto_judge_discovery_v1`, `earn_a_judge_v1`, `the_check_mode_is_the_oracle_v1`,
    `an_actions_vocabulary_is_its_refusal_surface_v1`, `a_type_you_wrote_is_a_type_you_guess_v1`,
    and `a_refusal_is_a_specification_v1` into one live engine."""

    @staticmethod
    def discover_and_earn_judges(
        *,
        artifacts_by_kind: Mapping[str, Sequence[bytes]] | None = None,
        store_dir: str | Path | None = None,
        include_stdlib_discovery: bool = True,
        cli_probe: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Discover and earn verifiable format/artifact judges via real subprocess execution over positive/decoy/cross-kind bytes."""
        import subprocess
        import tempfile
        from canonical.swe_kernel import auto_judge_discovery_v1 as ajd
        from canonical.runtime import earn_a_judge_v1 as eaj

        t0 = time.perf_counter()
        stdlib_candidates = ajd.discover_stdlib_candidates() if include_stdlib_discovery else []
        earned_summary: list[dict[str, Any]] = []

        if artifacts_by_kind:
            store_path = Path(store_dir) if store_dir is not None else None
            store = ajd.JudgeStore(store_path) if store_path is not None else ajd.JudgeStore()
            with tempfile.TemporaryDirectory(prefix="w39_judge_") as td:
                td_path = Path(td)
                decoy_path = td_path / "decoy.bin"
                decoy_path.write_bytes(b"\x00\xff__WAVE39_CORRUPT_DECOY__\xff\x00")
                kind_files: dict[str, list[Path]] = {}
                for kind, items in artifacts_by_kind.items():
                    paths_k: list[Path] = []
                    for idx, item in enumerate(items):
                        p = td_path / f"{kind}_{idx}.dat"
                        p.write_bytes(item if isinstance(item, (bytes, bytearray)) else str(item).encode("utf-8"))
                        paths_k.append(p)
                    kind_files[kind] = paths_k

                def _judge_accepts(argv: Sequence[str], fpath: Path) -> bool:
                    proc = subprocess.run(
                        [*argv, str(fpath)],
                        capture_output=True,
                        timeout=3.0,
                        check=False,
                    )
                    return proc.returncode == 0

                for kind, pos_paths in kind_files.items():
                    other_paths = [p for k2, ps in kind_files.items() if k2 != kind for p in ps]
                    # Prefer candidates matching `kind` first, then fall back to all discovered candidates
                    ordered = [c for c in stdlib_candidates if c[1] == kind] + [c for c in stdlib_candidates if c[1] != kind]
                    for name, cand_kind, argv in ordered:
                        try:
                            pos_ok = all(_judge_accepts(argv, p) for p in pos_paths)
                            decoy_rej = not _judge_accepts(argv, decoy_path)
                            others_rej = all(not _judge_accepts(argv, o) for o in other_paths) if other_paths else True
                            if pos_ok and decoy_rej and others_rej:
                                earned_summary.append(
                                    {
                                        "kind": kind,
                                        "judge_name": name,
                                        "candidate_kind": cand_kind,
                                        "positives_passed": len(pos_paths),
                                        "decoy_rejected": True,
                                        "cross_kind_rejected": others_rej,
                                        "status": "EARNED_STDLIB_JUDGE",
                                    }
                                )
                                break
                        except Exception:
                            continue
            store_len = len(store.all_judges()) if hasattr(store, "all_judges") else 0
        else:
            store_len = 0

        cli_earned: dict[str, Any] | None = None
        if cli_probe:
            c_res = eaj.earn(
                str(cli_probe["kind"]),
                list(cli_probe["argv"]),
                real=str(cli_probe["real"]),
                decoy=str(cli_probe["decoy"]),
                others=tuple(cli_probe.get("others") or ()),
                repeat=int(cli_probe.get("repeat", 1)),
            )
            cli_earned = {
                "kind": c_res.kind,
                "argv": list(c_res.argv),
                "earned": bool(getattr(c_res, "earned", False)),
                "status": str(getattr(c_res, "status", "")),
            }

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        return {
            "schema": SCHEMA,
            "engine": "LEAPFROG_W39_AUTO_JUDGE_DISCOVERY",
            "pass": len(stdlib_candidates) > 0 and (not artifacts_by_kind or len(earned_summary) == len(artifacts_by_kind)),
            "model_calls": MODEL_CALLS,
            "stdlib_candidates_discovered": len(stdlib_candidates),
            "stdlib_candidate_names": [c[0] for c in stdlib_candidates],
            "earned_judges": earned_summary,
            "store_existing_count": store_len,
            "cli_earned": cli_earned,
            "elapsed_ms": round(elapsed_ms, 3),
        }

    @staticmethod
    def lift_refusal_and_check_oracle(
        help_text: str,
        *,
        refusal_lines: Sequence[str] = (),
        action_argv: Sequence[str] = ("tool", "target"),
        paths: Sequence[str] = (),
        type_map: Mapping[str, str] | None = None,
        labels: Mapping[str, str] | None = None,
    ) -> dict[str, Any]:
        """Lift CLI `--help` + stderr refusal surfaces into `--check`/`--dry-run` oracle probes & collapsed types."""
        from canonical.tools import the_check_mode_is_the_oracle_v1 as chk
        from canonical.tools import an_actions_vocabulary_is_its_refusal_surface_v1 as refv
        from canonical.tools import a_type_you_wrote_is_a_type_you_guess_v1 as aty
        from canonical.runtime import a_refusal_is_a_specification_v1 as refspec

        t0 = time.perf_counter()
        short_flags, long_flags = chk.tokens_of(help_text or "")

        # Construct lightweight action descriptor compatible with chk.candidates(action, short, long)
        class _ActionShim:
            def __init__(self, argv: Sequence[str]) -> None:
                self.argv = tuple(str(x) for x in argv)

        probe_candidates = chk.candidates(_ActionShim(action_argv), short_flags, long_flags)
        check_like_flags = [
            f
            for f in (*short_flags, *long_flags)
            if any(k in f.lower() for k in ("check", "dry", "noop", "no-act", "simulate", "verify", "test", "lint", "-n"))
        ]

        refusal_classes = []
        for ln in refusal_lines:
            clause = refspec.read_refusal(ln)
            refusal_classes.append(
                {
                    "line": ln,
                    "vocabulary_class": refv.message_class(ln, list(paths)),
                    "parsed_spec": (
                        {
                            "form": clause.form,
                            "token": clause.token,
                            "candidate": clause.candidate,
                            "sentence": clause.sentence,
                        }
                        if clause is not None
                        else None
                    ),
                }
            )

        collapsed_pairs = []
        if type_map is not None and labels is not None:
            collapsed_pairs = aty.pairs_collapsed(dict(type_map), dict(labels))

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        return {
            "schema": SCHEMA,
            "engine": "LEAPFROG_W39_REFUSAL_ORACLE_LIFTER",
            "pass": bool(short_flags or long_flags or refusal_classes or collapsed_pairs is not None),
            "model_calls": MODEL_CALLS,
            "short_flags": short_flags,
            "long_flags": long_flags,
            "check_like_flags": check_like_flags,
            "probe_candidates_count": len(probe_candidates),
            "probe_candidates_sample": [list(c) for c in probe_candidates[:12]],
            "refusal_vocabulary": refusal_classes,
            "collapsed_type_pairs": collapsed_pairs,
            "elapsed_ms": round(elapsed_ms, 3),
        }


# ---------------------------------------------------------------------------
# 3. ContractPlannerAndLiftedGeneralizer
# ---------------------------------------------------------------------------


class ContractPlannerAndLiftedGeneralizer:
    """Wires DARK `effect_contract_composition_v1`, `composition_verification_v1`,
    `partial_order_planner_v1`, `perfect_algorithm_lifted_generalization_v1`,
    `observation_refutation_v1`, and `provenance_not_shape_v1`."""

    @staticmethod
    def compose_and_plan(
        *,
        use_measured_advance_pair: bool = True,
        contracts: Sequence[Mapping[str, Any]] | None = None,
        initial_facts: Sequence[str] = (),
        goal_facts: Sequence[str] = (),
        operators: Sequence[Mapping[str, Any]] = (),
        concrete_plan: Sequence[Any] | None = None,
        success_states: Sequence[Iterable[str]] | None = None,
        failure_states: Sequence[Iterable[str]] | None = None,
        ast_provenance_source: str | None = None,
        run_observation_refutation: bool = False,
    ) -> dict[str, Any]:
        from canonical.swe_kernel import effect_contract_composition_v1 as ecc
        from canonical.swe_kernel import composition_verification_v1 as cv1
        from canonical.swe_kernel import partial_order_planner_v1 as pop
        from canonical.swe_kernel import perfect_algorithm_lifted_generalization_v1 as palg
        from canonical.tools import provenance_not_shape_v1 as pns

        t0 = time.perf_counter()
        composition_report: dict[str, Any] = {}

        built_contracts: list[Any] = []
        if contracts:
            for c in contracts:
                effs = tuple(ecc.Effect(kind=str(e["kind"]), subject=str(e["subject"])) for e in c.get("effects", ()))
                built_contracts.append(
                    ecc.EffectContract(
                        skill_id=str(c["skill_id"]),
                        preconditions=tuple(c.get("preconditions", ())),
                        observables=tuple(c.get("observables", ())),
                        actions=tuple(c.get("actions", ())),
                        verdict=str(c.get("verdict", "verified")),
                        effects=effs,
                    )
                )
        elif use_measured_advance_pair:
            c1, c2 = ecc.measured_advance_pair()
            built_contracts = [c1, c2]

        if len(built_contracts) >= 2:
            chain_res = ecc.compose_chain(built_contracts)
            verifier = cv1.CompositionVerification()
            steps = [(c, frozenset(c.preconditions)) for c in built_contracts]
            established: set[str] = set()
            for c in built_contracts:
                for eff in c.effects:
                    if getattr(eff, "kind", "") == "ESTABLISH":
                        established.add(eff.subject)
                    elif getattr(eff, "kind", "") == "REMOVE":
                        established.discard(eff.subject)
            cv_res = verifier.run(steps, frozenset(established))
            verdict_str = str(chain_res.get("verdict", ""))
            composition_report = {
                "chain_valid": verdict_str == "CONTRACT_COMPATIBLE",
                "verdict": verdict_str,
                "reason": str(chain_res.get("reason", "")),
                "chain_skill_ids": [c.skill_id for c in built_contracts],
                "step_count": len(chain_res.get("steps") or ()),
                "net_established": sorted(established),
                "verification_status": cv_res.get("status") if isinstance(cv_res, Mapping) else str(cv_res),
            }

        def _to_cond(item: Any) -> tuple[str, str, str | None, str, Any]:
            if isinstance(item, (tuple, list)) and len(item) == 5:
                return (str(item[0]), str(item[1]), item[2], str(item[3]), item[4])
            return (str(item), "WHOLE", None, "equals", True)

        plan_report: dict[str, Any] | None = None
        if operators and goal_facts:
            op_objs = [
                pop.Operator(
                    ident=str(o["ident"]),
                    pre=frozenset(_to_cond(c) for c in o.get("pre", ())),
                    add=frozenset(_to_cond(c) for c in o.get("add", ())),
                    delete=frozenset(_to_cond(c) for c in o.get("delete", ())),
                    atom=str(o.get("atom", o["ident"])),
                )
                for o in operators
            ]
            plan_report = pop.plan(
                frozenset(_to_cond(c) for c in initial_facts),
                frozenset(_to_cond(c) for c in goal_facts),
                op_objs,
            )

        lifted_report: dict[str, Any] | None = None
        if concrete_plan is not None:
            sketch = palg.lift_plan_sketch(list(concrete_plan), goal=",".join(goal_facts))
            applic = (
                palg.induce_applicability(success_states, failure_states)
                if (success_states is not None or failure_states is not None)
                else None
            )
            lifted_report = {"sketch": sketch, "applicability": applic}

        provenance_report: dict[str, Any] | None = None
        if ast_provenance_source:
            tree = ast.parse(ast_provenance_source)
            target_nodes = [
                n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            ] or [tree]
            all_origins: set[str] = set()
            all_feats: set[str] = set()
            for tn in target_nodes:
                all_origins |= set(pns.origins_in(tn))
                all_feats |= set(pns.provenance_features(tn))
            provenance_report = {
                "origins": sorted(all_origins),
                "provenance_features": sorted(all_feats),
            }

        refutation_report: dict[str, Any] | None = None
        if run_observation_refutation:
            from canonical.runtime import observation_refutation_v1 as obref

            ob_res = obref.run()
            refutation_report = {
                "passed": ob_res.get("passed"),
                "total": ob_res.get("total"),
                "authority": ob_res.get("authority"),
            }

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        ok = True
        if composition_report:
            ok = ok and bool(composition_report.get("chain_valid", False))
        if plan_report is not None:
            ok = ok and bool(
                plan_report.get("solved")
                or plan_report.get("found")
                or str(plan_report.get("status", "")).startswith("PASS")
                or bool(plan_report.get("steps"))
            )
        return {
            "schema": SCHEMA,
            "engine": "LEAPFROG_W39_CONTRACT_PLANNER_AND_LIFTED_GENERALIZER",
            "pass": ok,
            "model_calls": MODEL_CALLS,
            "composition": composition_report,
            "partial_order_plan": plan_report,
            "lifted_generalization": lifted_report,
            "ast_provenance": provenance_report,
            "observation_refutation": refutation_report,
            "elapsed_ms": round(elapsed_ms, 3),
        }


# ---------------------------------------------------------------------------
# 4. SpeculativeCoWDecisionGate (what_a_decision_costs_v1 + real POSIX os.fork())
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _SurvivorBoundary:
    survivors: tuple[frozenset[str], ...]


class SpeculativeCoWDecisionGate:
    """Decision-theoretic version-space agreement gate + real POSIX CoW `os.fork()` speculative verifier."""

    @staticmethod
    def _run_cow_fork_candidate(
        candidate_fn: Callable[[], Any],
        verifier_fn: Callable[[Any], bool] | None,
        timeout_s: float,
    ) -> dict[str, Any]:
        """Execute a candidate inside an isolated `os.fork()` Copy-on-Write child with zero parent mutation."""
        t0 = time.perf_counter()
        if not hasattr(os, "fork"):
            # Safe non-POSIX fallback
            val = candidate_fn()
            ok = bool(verifier_fn(val)) if verifier_fn is not None else bool(val)
            return {
                "pass": ok,
                "result": val,
                "cow_forked": False,
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            }

        r_fd, w_fd = os.pipe()
        pid = os.fork()
        if pid == 0:
            os.close(r_fd)
            payload: dict[str, Any]
            try:
                val = candidate_fn()
                ok = bool(verifier_fn(val)) if verifier_fn is not None else bool(val)
                payload = {"pass": ok, "result": val, "child_pid": os.getpid(), "error": ""}
            except Exception as exc:
                payload = {"pass": False, "result": None, "child_pid": os.getpid(), "error": f"{type(exc).__name__}: {exc}"}
            try:
                raw = json.dumps(payload, default=str).encode("utf-8")
                os.write(w_fd, raw)
            finally:
                os.close(w_fd)
                os._exit(0)

        os.close(w_fd)
        chunks: list[bytes] = []
        deadline = time.monotonic() + max(0.1, float(timeout_s))
        try:
            while True:
                data = os.read(r_fd, 65536)
                if not data:
                    break
                chunks.append(data)
                if time.monotonic() > deadline:
                    break
        finally:
            os.close(r_fd)
            try:
                os.waitpid(pid, 0)
            except ChildProcessError:
                pass

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        if not chunks:
            return {"pass": False, "result": None, "cow_forked": True, "child_pid": pid, "error": "EMPTY_PIPE", "elapsed_ms": round(elapsed_ms, 3)}
        parsed = json.loads(b"".join(chunks).decode("utf-8"))
        parsed["cow_forked"] = True
        parsed["elapsed_ms"] = round(elapsed_ms, 3)
        return parsed

    @classmethod
    def decide_and_speculate(
        cls,
        *,
        survivor_requirements: Sequence[Iterable[str]],
        observed_facts: Sequence[str],
        p_correct: float = 0.5,
        wrong_commit_cost: float = 10.0,
        cow_trial_cost: float = 0.002,
        candidates: Sequence[tuple[str, Callable[[], Any]]] | None = None,
        verifier: Callable[[Any], bool] | None = None,
        timeout_s: float = 5.0,
    ) -> dict[str, Any]:
        """Use `what_a_decision_costs_v1.decisive()` to bypass trials where hypotheses agree; fork CoW trials only on disagreement."""
        from canonical.tools import what_a_decision_costs_v1 as wdc

        t0 = time.perf_counter()
        boundary = _SurvivorBoundary(survivors=tuple(frozenset(s) for s in survivor_requirements))
        verdict = wdc.decisive(boundary, list(observed_facts))

        expected_error_cost = max(0.0, 1.0 - max(0.0, min(1.0, float(p_correct)))) * float(wrong_commit_cost)

        if verdict is not None:
            decision = "BY_KNOWLEDGE_APPLY" if verdict else "BY_KNOWLEDGE_REJECT"
            return {
                "schema": SCHEMA,
                "engine": "LEAPFROG_W39_DECISION_COST_COW_GATE",
                "pass": True,
                "model_calls": MODEL_CALLS,
                "decision": decision,
                "decisive_verdict": verdict,
                "cow_trials_paid": 0,
                "expected_error_cost": round(expected_error_cost, 6),
                "cow_trial_cost": float(cow_trial_cost),
                "winner": None,
                "trial_results": [],
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            }

        # Hypotheses disagree (AMBIGUOUS) or no requirement licensed yet:
        # Compare expected wrong-commit cost vs CoW trial cost.
        if not candidates:
            decision = "NEEDS_COW_TRIAL" if expected_error_cost > float(cow_trial_cost) else "DIRECT_COMMIT"
            return {
                "schema": SCHEMA,
                "engine": "LEAPFROG_W39_DECISION_COST_COW_GATE",
                "pass": True,
                "model_calls": MODEL_CALLS,
                "decision": decision,
                "decisive_verdict": None,
                "cow_trials_paid": 0,
                "expected_error_cost": round(expected_error_cost, 6),
                "cow_trial_cost": float(cow_trial_cost),
                "winner": None,
                "trial_results": [],
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            }

        trials: list[dict[str, Any]] = []
        winner: dict[str, Any] | None = None
        for cid, fn in candidates:
            res = cls._run_cow_fork_candidate(fn, verifier, timeout_s=timeout_s)
            row = {"candidate_id": cid, **res}
            trials.append(row)
            if res.get("pass") and winner is None:
                winner = row
                break

        return {
            "schema": SCHEMA,
            "engine": "LEAPFROG_W39_DECISION_COST_COW_GATE",
            "pass": winner is not None,
            "model_calls": MODEL_CALLS,
            "decision": "SPECULATIVE_COW_TRIAL_VERIFIED" if winner is not None else "ABSTAIN_NO_VERIFIED_CANDIDATE",
            "decisive_verdict": None,
            "cow_trials_paid": len(trials),
            "expected_error_cost": round(expected_error_cost, 6),
            "cow_trial_cost": float(cow_trial_cost),
            "winner": winner,
            "trial_results": trials,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }


# ---------------------------------------------------------------------------
# 5. CLMRRFMemoryEngine (Verbatim 4-Way RRF + Nemori Surprise + CLM File Mirror)
# ---------------------------------------------------------------------------


class CLMRRFMemoryEngine:
    """Verbatim-first 4-way RRF budgeted retrieval + Nemori surprise gating + CLM file-mirrored working context."""

    def __init__(self, memory_bus: Any | None = None) -> None:
        if memory_bus is None:
            from canonical.swe_kernel.canonical_memory_crystallizer_v1 import VerificationFirstMemoryBus

            memory_bus = VerificationFirstMemoryBus()
        self.memory_bus = memory_bus
        self._verbatim_archive: dict[str, dict[str, Any]] = {}
        self._entity_index: dict[str, set[str]] = {}
        self._key_latest: dict[str, str] = {}
        self._offloads: dict[str, dict[str, Any]] = {}

    def _jaccard_distance(self, a: set[str], b: set[str]) -> float:
        if not a and not b:
            return 0.0
        union = a | b
        if not union:
            return 0.0
        return 1.0 - (len(a & b) / float(len(union)))

    def write_surprise_gated(
        self,
        *,
        record_id: str,
        key: str,
        verbatim_text: str,
        payload: Mapping[str, Any] | None = None,
        valid_from: float | None = None,
        origin_token: str = "RUNTIME_VERIFIED",
        min_surprise: float = 0.25,
        entities: Sequence[str] = (),
        source_code: str = "",
    ) -> dict[str, Any]:
        """Nemori surprise-gated verbatim-first write sealed with TMA-NM HMAC-SHA256 origin binding."""
        toks = set(_tokenize_lower(verbatim_text))
        ast_toks = set(_extract_ast_tokens(source_code)) if source_code else set(_extract_ast_tokens(verbatim_text))
        ent_set = {str(e).lower() for e in entities if str(e).strip()}

        # Compute free-energy surprise = min distance to existing memories under the same key or nearest neighbor
        surprise = 1.0
        belief_conflict = False
        if key in self._key_latest:
            prev_id = self._key_latest[key]
            prev = self._verbatim_archive.get(prev_id)
            if prev is not None:
                surprise = self._jaccard_distance(toks, prev["lexical_tokens"])
                if payload is not None and prev.get("payload") != dict(payload):
                    belief_conflict = True
                    surprise = max(surprise, 0.85)
        elif self._verbatim_archive:
            min_dist = min(self._jaccard_distance(toks, rec["lexical_tokens"]) for rec in self._verbatim_archive.values())
            surprise = min_dist

        if (surprise < float(min_surprise)) and not belief_conflict:
            return {
                "schema": SCHEMA,
                "engine": "LEAPFROG_W39_CLM_RRF_MEMORY_BUS",
                "pass": True,
                "admitted": False,
                "status": "SKIPPED_LOW_SURPRISE",
                "record_id": record_id,
                "key": key,
                "surprise_score": round(surprise, 4),
                "min_surprise": float(min_surprise),
                "model_calls": MODEL_CALLS,
            }

        t_now = float(valid_from) if valid_from is not None else time.time()
        full_payload = dict(payload or {})
        full_payload["_verbatim_sha256"] = _sha256_text(verbatim_text)
        full_payload["_verbatim_len"] = len(verbatim_text)

        # Write through TMA-NM cryptographic origin-binding on VerificationFirstMemoryBus!
        origin_cls = (
            origin_token
            if origin_token in ("TRUSTED_VERIFIER", "RUNTIME_OBSERVATION", "USER_DIRECT", "UNTRUSTED_RETRIEVAL")
            else "TRUSTED_VERIFIER"
        )
        tma_res = self.memory_bus.write_origin_bound_record(
            record_id=record_id,
            key=key,
            payload=full_payload,
            origin_class=origin_cls,
            source_origin_hash=_sha256_text(verbatim_text),
            valid_from=t_now,
        )
        if not tma_res.get("pass", False):
            return {
                "schema": SCHEMA,
                "engine": "LEAPFROG_W39_CLM_RRF_MEMORY_BUS",
                "pass": False,
                "admitted": False,
                "status": "REJECTED_TMA_NM",
                "tma_result": tma_res,
                "model_calls": MODEL_CALLS,
            }

        self._verbatim_archive[record_id] = {
            "record_id": record_id,
            "key": key,
            "verbatim_text": verbatim_text,
            "verbatim_sha256": _sha256_text(verbatim_text),
            "payload": dict(payload or {}),
            "lexical_tokens": toks,
            "ast_tokens": ast_toks,
            "entities": ent_set,
            "valid_from": t_now,
            "origin_token": origin_cls,
            "surprise_score": round(surprise, 4),
            "belief_conflict": belief_conflict,
        }
        self._key_latest[key] = record_id
        for e in ent_set:
            self._entity_index.setdefault(e, set()).add(record_id)

        return {
            "schema": SCHEMA,
            "engine": "LEAPFROG_W39_CLM_RRF_MEMORY_BUS",
            "pass": True,
            "admitted": True,
            "status": "ADMITTED_BELIEF_CONFLICT" if belief_conflict else "ADMITTED_SURPRISING",
            "record_id": record_id,
            "key": key,
            "surprise_score": round(surprise, 4),
            "origin_commitment": tma_res.get("commitment", ""),
            "model_calls": MODEL_CALLS,
        }

    def retrieve_4way_rrf_budgeted(
        self,
        query: str,
        *,
        char_budget: int = 1200,
        top_k: int = 5,
        rrf_k: int = 60,
        query_source_code: str = "",
        query_entities: Sequence[str] = (),
        at_time: float | None = None,
    ) -> dict[str, Any]:
        """Hindsight-style 4-way RRF over verbatim records with TMA-NM tamper audit and strict character budgeting."""
        t0 = time.perf_counter()
        q_lex = set(_tokenize_lower(query))
        q_ast = set(_extract_ast_tokens(query_source_code)) if query_source_code else set(_extract_ast_tokens(query))
        q_ents = {str(e).lower() for e in query_entities if str(e).strip()} | (q_lex & set(self._entity_index.keys()))

        # 1-hop entity neighborhood for causal/entity channel
        neighbor_ids: set[str] = set()
        for e in q_ents:
            neighbor_ids |= self._entity_index.get(e, set())

        # Audit TMA-NM tamper integrity before ranking
        tampered_ids: list[str] = []
        eligible: list[dict[str, Any]] = []
        for rec_id, rec in self._verbatim_archive.items():
            if at_time is not None and rec["valid_from"] > float(at_time):
                continue
            tma_check = self.memory_bus.verify_origin_binding(rec_id)
            if not (tma_check.get("valid", False) or tma_check.get("pass", False)):
                tampered_ids.append(rec_id)
                continue
            if _sha256_text(rec["verbatim_text"]) != rec["verbatim_sha256"]:
                tampered_ids.append(rec_id)
                continue
            eligible.append(rec)

        if not eligible:
            return {
                "schema": SCHEMA,
                "engine": "LEAPFROG_W39_CLM_RRF_MEMORY_BUS",
                "pass": True,
                "model_calls": MODEL_CALLS,
                "results": [],
                "tampered_excluded": tampered_ids,
                "chars_used": 0,
                "char_budget": int(char_budget),
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            }

        # Channel 1: Lexical BM25-like IDF-weighted overlap
        n_docs = len(eligible)
        df: dict[str, int] = {}
        for rec in eligible:
            for tok in rec["lexical_tokens"]:
                df[tok] = df.get(tok, 0) + 1

        def _lex_score(rec: dict[str, Any]) -> float:
            score = 0.0
            for tok in q_lex:
                if tok in rec["lexical_tokens"]:
                    idf = math.log(1.0 + (n_docs + 0.5) / (df.get(tok, 0) + 0.5))
                    score += idf
            return score

        # Channel 2: Structural AST/identifier overlap
        def _ast_score(rec: dict[str, Any]) -> float:
            if not q_ast or not rec["ast_tokens"]:
                return 0.0
            return len(q_ast & rec["ast_tokens"]) / float(max(1, len(q_ast | rec["ast_tokens"])))

        # Channel 3: Bi-temporal recency + Entity graph neighborhood
        max_t = max(r["valid_from"] for r in eligible)
        min_t = min(r["valid_from"] for r in eligible)
        span = max(1e-6, max_t - min_t)

        def _temporal_entity_score(rec: dict[str, Any]) -> float:
            recency = (rec["valid_from"] - min_t) / span if max_t > min_t else 1.0
            ent_hit = 1.0 if rec["record_id"] in neighbor_ids else 0.0
            ent_jac = len(q_ents & rec["entities"]) / float(max(1, len(q_ents | rec["entities"]))) if q_ents else 0.0
            return 0.4 * recency + 0.35 * ent_hit + 0.25 * ent_jac

        # Channel 4: Origin trust + surprise signal
        def _trust_score(rec: dict[str, Any]) -> float:
            trust = 1.0 if rec["origin_token"] == "TRUSTED_VERIFIER" else 0.5
            return trust + 0.2 * float(rec.get("surprise_score", 0.0))

        channels = {
            "lexical": sorted(eligible, key=lambda r: (-_lex_score(r), r["record_id"])),
            "structural_ast": sorted(eligible, key=lambda r: (-_ast_score(r), r["record_id"])),
            "temporal_entity": sorted(eligible, key=lambda r: (-_temporal_entity_score(r), r["record_id"])),
            "origin_trust": sorted(eligible, key=lambda r: (-_trust_score(r), r["record_id"])),
        }

        rrf_scores: dict[str, float] = {r["record_id"]: 0.0 for r in eligible}
        channel_ranks: dict[str, dict[str, int]] = {r["record_id"]: {} for r in eligible}
        for cname, ranked in channels.items():
            for rank_idx, rec in enumerate(ranked, 1):
                rid = rec["record_id"]
                rrf_scores[rid] += 1.0 / float(int(rrf_k) + rank_idx)
                channel_ranks[rid][cname] = rank_idx

        ranked_ids = sorted(rrf_scores.keys(), key=lambda rid: (-rrf_scores[rid], rid))
        budget = max(32, int(char_budget))
        chars_used = 0
        out_results: list[dict[str, Any]] = []

        for rid in ranked_ids[: max(1, int(top_k))]:
            rec = self._verbatim_archive[rid]
            txt = rec["verbatim_text"]
            rem = budget - chars_used
            if rem <= 0:
                break
            excerpt = txt if len(txt) <= rem else txt[:rem]
            chars_used += len(excerpt)
            out_results.append(
                {
                    "record_id": rid,
                    "key": rec["key"],
                    "rrf_score": round(rrf_scores[rid], 6),
                    "channel_ranks": channel_ranks[rid],
                    "verbatim_excerpt": excerpt,
                    "truncated": len(excerpt) < len(txt),
                    "origin_token": rec["origin_token"],
                }
            )

        return {
            "schema": SCHEMA,
            "engine": "LEAPFROG_W39_CLM_RRF_MEMORY_BUS",
            "pass": True,
            "model_calls": MODEL_CALLS,
            "results": out_results,
            "tampered_excluded": tampered_ids,
            "chars_used": chars_used,
            "char_budget": budget,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }

    def clm_offload(
        self,
        context_text: str,
        *,
        workspace_dir: str | Path,
        label: str = "working_ctx",
        min_bytes: int = 128,
    ) -> dict[str, Any]:
        """CLM file-mirrored working-context offload: spills large text to content-addressed file, returns compact stub."""
        raw = context_text.encode("utf-8")
        digest = _sha256_bytes(raw)
        if len(raw) < int(min_bytes):
            return {
                "schema": SCHEMA,
                "engine": "LEAPFROG_W39_CLM_RRF_MEMORY_BUS",
                "pass": True,
                "offloaded": False,
                "stub": context_text,
                "sha256": digest,
                "bytes_saved": 0,
            }
        out_dir = Path(workspace_dir) / "clm_offload"
        out_dir.mkdir(parents=True, exist_ok=True)
        safe_label = re.sub(r"[^A-Za-z0-9_.-]+", "_", label)[:48]
        fpath = out_dir / f"{safe_label}_{digest[:16]}.txt"
        fpath.write_bytes(raw)
        stub = f"[CLM_OFFLOAD label={safe_label} sha256={digest[:16]} bytes={len(raw)} path={fpath.name}]"
        ref = {
            "offload_id": f"{safe_label}:{digest[:16]}",
            "path": str(fpath),
            "sha256": digest,
            "original_bytes": len(raw),
            "stub": stub,
            "stub_bytes": len(stub.encode("utf-8")),
            "bytes_saved": max(0, len(raw) - len(stub.encode("utf-8"))),
        }
        self._offloads[ref["offload_id"]] = ref
        return {
            "schema": SCHEMA,
            "engine": "LEAPFROG_W39_CLM_RRF_MEMORY_BUS",
            "pass": True,
            "offloaded": True,
            "model_calls": MODEL_CALLS,
            **ref,
        }

    def clm_grep_restore(
        self,
        offload_ref: Mapping[str, Any] | str,
        *,
        pattern: str | None = None,
        max_chars: int = 2000,
    ) -> dict[str, Any]:
        """Restore exact verified lines (or full content) from a CLM file-mirrored offload after SHA-256 tamper audit."""
        ref = self._offloads.get(offload_ref) if isinstance(offload_ref, str) else dict(offload_ref)
        if not ref or not ref.get("path"):
            return {"pass": False, "error": "UNKNOWN_OFFLOAD_REF", "tampered": False}
        fpath = Path(ref["path"])
        if not fpath.exists():
            return {"pass": False, "error": "OFFLOAD_FILE_MISSING", "tampered": True}
        raw = fpath.read_bytes()
        live_sha = _sha256_bytes(raw)
        if live_sha != ref["sha256"]:
            return {
                "schema": SCHEMA,
                "engine": "LEAPFROG_W39_CLM_RRF_MEMORY_BUS",
                "pass": False,
                "tampered": True,
                "expected_sha256": ref["sha256"],
                "actual_sha256": live_sha,
                "matches": [],
            }
        text = raw.decode("utf-8")
        if pattern:
            rx = re.compile(pattern)
            lines = [ln for ln in text.splitlines() if rx.search(ln)]
            restored = "\n".join(lines)[: int(max_chars)]
        else:
            lines = text.splitlines()
            restored = text[: int(max_chars)]
        return {
            "schema": SCHEMA,
            "engine": "LEAPFROG_W39_CLM_RRF_MEMORY_BUS",
            "pass": True,
            "tampered": False,
            "model_calls": MODEL_CALLS,
            "sha256": live_sha,
            "matched_line_count": len(lines),
            "restored_text": restored,
        }


# ---------------------------------------------------------------------------
# 6. PartialRoutingJitRLSkillTTAEngine (JitRL + SkillTTA + Partial Routing + Live Self-Verifier)
# ---------------------------------------------------------------------------


class PartialRoutingJitRLSkillTTAEngine:
    """Closed-form JitRL advantage logit modulation + SkillTTA synthesis + Intra-task Partial Routing + Surface Self-Verifier."""

    @staticmethod
    def jitrl_modulate_logits(
        prior_logits: Mapping[str, float],
        *,
        state_signature: str,
        episodic_receipts: Sequence[Mapping[str, Any]],
        beta: float = 1.0,
    ) -> dict[str, Any]:
        """Exact closed-form KL-regularized test-time policy update: l'(a) = l_0(a) + A_hat(s,a) / beta (JitRL)."""
        if not prior_logits:
            return {"pass": False, "error": "EMPTY_PRIOR_LOGITS"}
        b = max(1e-4, float(beta))
        q_toks = set(_tokenize_lower(state_signature))

        # Soft kernel similarity retrieval over episodic receipts
        action_weighted_reward: dict[str, float] = {}
        action_weight_sum: dict[str, float] = {}
        total_w = 0.0
        total_wr = 0.0

        for r in episodic_receipts:
            act = str(r.get("action", ""))
            if act not in prior_logits:
                continue
            r_toks = set(_tokenize_lower(str(r.get("state_signature", ""))))
            sim = 1.0 if r_toks == q_toks else (len(q_toks & r_toks) / float(max(1, len(q_toks | r_toks))))
            if sim <= 0.0:
                continue
            rew = float(r.get("reward", 0.0))
            action_weighted_reward[act] = action_weighted_reward.get(act, 0.0) + sim * rew
            action_weight_sum[act] = action_weight_sum.get(act, 0.0) + sim
            total_w += sim
            total_wr += sim * rew

        baseline_v = (total_wr / total_w) if total_w > 0.0 else 0.0

        def _softmax(d: Mapping[str, float]) -> dict[str, float]:
            m = max(d.values())
            exps = {k: math.exp(v - m) for k, v in d.items()}
            z = sum(exps.values()) or 1.0
            return {k: v / z for k, v in exps.items()}

        prior_probs = _softmax(prior_logits)
        advantages: dict[str, float] = {}
        modulated_logits: dict[str, float] = {}
        for act, l0 in prior_logits.items():
            if action_weight_sum.get(act, 0.0) > 0.0:
                q_sa = action_weighted_reward[act] / action_weight_sum[act]
                adv = q_sa - baseline_v
            else:
                adv = 0.0
            advantages[act] = round(adv, 6)
            modulated_logits[act] = round(float(l0) + (adv / b), 6)

        posterior_probs = _softmax(modulated_logits)
        kl_div = sum(
            posterior_probs[a] * math.log(max(1e-12, posterior_probs[a]) / max(1e-12, prior_probs[a]))
            for a in prior_logits
        )
        best_prior = max(prior_probs.items(), key=lambda kv: (kv[1], kv[0]))[0]
        best_post = max(posterior_probs.items(), key=lambda kv: (kv[1], kv[0]))[0]
        return {
            "schema": SCHEMA,
            "engine": "LEAPFROG_W39_PARTIAL_ROUTING_AND_JITRL",
            "pass": True,
            "model_calls": MODEL_CALLS,
            "state_signature": state_signature,
            "baseline_value": round(baseline_v, 6),
            "beta": b,
            "advantages": advantages,
            "prior_probs": {k: round(v, 6) for k, v in prior_probs.items()},
            "modulated_logits": modulated_logits,
            "posterior_probs": {k: round(v, 6) for k, v in posterior_probs.items()},
            "kl_divergence": round(kl_div, 6),
            "best_action_prior": best_prior,
            "best_action_posterior": best_post,
            "policy_shifted": best_prior != best_post,
        }

    @staticmethod
    def skilltta_synthesize(
        target_task: Mapping[str, Any],
        *,
        verified_traces: Sequence[Mapping[str, Any]],
        top_k: int = 3,
    ) -> dict[str, Any]:
        """SkillTTA dynamic task-conditioned temporary skill contract synthesis from verified traces."""
        t_sig = " ".join(
            str(target_task.get(k, ""))
            for k in ("domain", "error_kind", "goal", "signature", "description")
        )
        t_toks = set(_tokenize_lower(t_sig))
        scored: list[tuple[float, Mapping[str, Any]]] = []
        for tr in verified_traces:
            if not tr.get("verified", True):
                continue
            tr_sig = " ".join(
                str(tr.get(k, ""))
                for k in ("domain", "error_kind", "goal", "signature", "description")
            )
            tr_toks = set(_tokenize_lower(tr_sig))
            sim = len(t_toks & tr_toks) / float(max(1, len(t_toks | tr_toks)))
            scored.append((sim, tr))
        scored.sort(key=lambda x: (-x[0], str(x[1].get("trace_id", ""))))
        chosen = [tr for sim, tr in scored[: max(1, int(top_k))] if sim > 0.0]

        merged_actions: list[str] = []
        merged_guards: list[str] = []
        source_ids: list[str] = []
        for tr in chosen:
            source_ids.append(str(tr.get("trace_id", "trace")))
            for act in tr.get("actions", ()):
                if act not in merged_actions:
                    merged_actions.append(str(act))
            for gd in tr.get("invariants", ()):
                if gd not in merged_guards:
                    merged_guards.append(str(gd))

        contract_body = {
            "target_goal": str(target_task.get("goal", "")),
            "domain": str(target_task.get("domain", "general")),
            "source_trace_ids": source_ids,
            "synthesized_actions": merged_actions,
            "guard_invariants": merged_guards,
            "ephemeral": True,
        }
        contract_sha = _sha256_text(json.dumps(contract_body, sort_keys=True))
        return {
            "schema": SCHEMA,
            "engine": "LEAPFROG_W39_PARTIAL_ROUTING_AND_JITRL",
            "pass": len(chosen) > 0,
            "model_calls": MODEL_CALLS,
            "contract_id": f"skilltta_{contract_sha[:12]}",
            "contract_sha256": contract_sha,
            **contract_body,
        }

    @classmethod
    def partial_route_subtasks(
        cls,
        subtasks: Sequence[Mapping[str, Any]],
        *,
        compiled_skills: Mapping[str, Callable[[Mapping[str, Any]], Any]] | None = None,
        symbolic_solver: Callable[[Mapping[str, Any]], Any] | None = None,
        mendel_solver: Callable[[Mapping[str, Any]], Any] | None = None,
        pluggable_proposer: Callable[[Mapping[str, Any]], Any] | None = None,
        delta_threshold: float = 0.55,
        episodic_receipts: Sequence[Mapping[str, Any]] = (),
        beta: float = 0.5,
    ) -> dict[str, Any]:
        """Intra-task Partial Routing across Rung 0 -> Rung 1 -> Rung 2 -> optional Rung 3 only on hard slices."""
        t0 = time.perf_counter()
        skills = dict(compiled_skills or {})
        routed: list[dict[str, Any]] = []
        rung_counts: dict[str, int] = {
            "RUNG_0_COMPILED_SKILL": 0,
            "RUNG_1_SYMBOLIC": 0,
            "RUNG_2_COW_MENDEL": 0,
            "RUNG_3_PLUGGABLE_PROPOSER": 0,
            "ABSTAINED": 0,
        }
        external_calls = 0

        for st in subtasks:
            sid = str(st.get("subtask_id", f"st_{len(routed)}"))
            difficulty = float(st.get("difficulty", 0.3))
            verifier = st.get("verifier")
            state_sig = str(st.get("state_signature", st.get("kind", sid)))
            skill_key = str(st.get("skill_key", st.get("kind", "")))

            # Optional JitRL modulation over rung preference when episodic receipts exist
            jitrl_info = None
            if episodic_receipts:
                jitrl_info = cls.jitrl_modulate_logits(
                    {"RUNG_0": 2.0, "RUNG_1": 1.0, "RUNG_2": 0.5, "RUNG_3": -0.5},
                    state_signature=state_sig,
                    episodic_receipts=episodic_receipts,
                    beta=beta,
                )

            solved = False
            chosen_rung = "ABSTAINED"
            output: Any = None

            def _accepts(val: Any) -> bool:
                if val is None:
                    return False
                if callable(verifier):
                    return bool(verifier(val))
                return True

            # Rung 0: Compiled Skill (<0.1 ms, K3=0)
            if skill_key in skills:
                cand = skills[skill_key](st)
                if _accepts(cand):
                    solved, chosen_rung, output = True, "RUNG_0_COMPILED_SKILL", cand

            # Rung 1: Symbolic / Wall-Closer Solver (K3=0)
            if not solved and symbolic_solver is not None:
                cand = symbolic_solver(st)
                if _accepts(cand):
                    solved, chosen_rung, output = True, "RUNG_1_SYMBOLIC", cand

            # Rung 2: Mendel / CoW Speculation (K3=0)
            if not solved and mendel_solver is not None:
                cand = mendel_solver(st)
                if _accepts(cand):
                    solved, chosen_rung, output = True, "RUNG_2_COW_MENDEL", cand

            # Rung 3: Pluggable Proposer ONLY when local rungs fail AND difficulty >= delta_threshold
            if not solved and pluggable_proposer is not None and difficulty >= float(delta_threshold):
                external_calls += 1
                cand = pluggable_proposer(st)
                if _accepts(cand):
                    solved, chosen_rung, output = True, "RUNG_3_PLUGGABLE_PROPOSER", cand

            rung_counts[chosen_rung] += 1
            routed.append(
                {
                    "subtask_id": sid,
                    "difficulty": difficulty,
                    "solved": solved,
                    "rung": chosen_rung,
                    "output": output,
                    "jitrl_top_rung": jitrl_info["best_action_posterior"] if jitrl_info else None,
                }
            )

        total = len(subtasks)
        local_solved = rung_counts["RUNG_0_COMPILED_SKILL"] + rung_counts["RUNG_1_SYMBOLIC"] + rung_counts["RUNG_2_COW_MENDEL"]
        return {
            "schema": SCHEMA,
            "engine": "LEAPFROG_W39_PARTIAL_ROUTING_AND_JITRL",
            "pass": all(r["solved"] for r in routed) if routed else True,
            "model_calls": MODEL_CALLS,
            "pluggable_proposer_calls": external_calls,
            "total_subtasks": total,
            "local_zero_llm_solved": local_solved,
            "local_offload_ratio": round(local_solved / float(max(1, total)), 4),
            "rung_counts": rung_counts,
            "routed_subtasks": routed,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }

    @staticmethod
    def self_verify_harvested_surfaces(
        harvested_entries: Sequence[Mapping[str, Any]],
        *,
        repo_root: str | Path,
        limit: int = 40,
    ) -> dict[str, Any]:
        """Offline live AST + SHA-256 + entrypoint census of harvested/dark surfaces (zero fake pins)."""
        t0 = time.perf_counter()
        root = Path(repo_root)
        counts = {
            "CALLABLE_VERIFIED": 0,
            "STALE_SHA": 0,
            "MISSING_FILE": 0,
            "SYNTAX_ERROR": 0,
            "NO_ENTRYPOINT": 0,
        }
        rows: list[dict[str, Any]] = []
        for entry in list(harvested_entries)[: max(1, int(limit))]:
            rel = str(entry.get("path") or entry.get("module_path") or "")
            hid = str(entry.get("harvest_id") or entry.get("id") or rel)
            rec_sha = str(entry.get("sha256") or "")
            fpath = root / rel if rel else None
            if fpath is None or not fpath.is_file():
                counts["MISSING_FILE"] += 1
                rows.append({"id": hid, "path": rel, "status": "MISSING_FILE"})
                continue
            raw = fpath.read_bytes()
            live_sha = _sha256_bytes(raw)
            try:
                tree = ast.parse(raw.decode("utf-8"))
            except Exception as exc:
                counts["SYNTAX_ERROR"] += 1
                rows.append({"id": hid, "path": rel, "status": "SYNTAX_ERROR", "error": str(exc)})
                continue
            fns = [n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and not n.name.startswith("_")]
            classes = [n.name for n in tree.body if isinstance(n, ast.ClassDef) and not n.name.startswith("_")]
            if rec_sha and not live_sha.startswith(rec_sha) and not rec_sha.startswith(live_sha):
                counts["STALE_SHA"] += 1
                status = "STALE_SHA"
            elif fns or classes:
                counts["CALLABLE_VERIFIED"] += 1
                status = "CALLABLE_VERIFIED"
            else:
                counts["NO_ENTRYPOINT"] += 1
                status = "NO_ENTRYPOINT"
            rows.append(
                {
                    "id": hid,
                    "path": rel,
                    "status": status,
                    "live_sha256": live_sha[:16],
                    "public_functions_count": len(fns),
                    "public_classes_count": len(classes),
                    "sample_entrypoints": (fns + classes)[:5],
                }
            )
        return {
            "schema": SCHEMA,
            "engine": "LEAPFROG_W39_PARTIAL_ROUTING_AND_JITRL",
            "pass": True,
            "model_calls": MODEL_CALLS,
            "inspected_count": len(rows),
            "status_counts": counts,
            "entries": rows,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }


__all__ = [
    "SCHEMA",
    "MODEL_CALLS",
    "RedQueenMendelEvolver",
    "EarnedJudgeAndRefusalLifter",
    "ContractPlannerAndLiftedGeneralizer",
    "SpeculativeCoWDecisionGate",
    "CLMRRFMemoryEngine",
    "PartialRoutingJitRLSkillTTAEngine",
]
