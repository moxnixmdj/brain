#!/usr/bin/env python3
r"""Recursive Self-Architecting Engine (`K3 = 0`, `$0` spend, `0` host `exec()`).

Implements the 4-Law Sovereign Self-Evolution Architecture so the continuously
awake creature inspects, profiles, diagnoses, shadow-edits, falsifies, and
upgrades its own Ring-1 cognitive/runtime Python source code under a Ring-0
immutable referee:

  1. `SelfPatchFirewall` & `Ring0SelfReferee` (Law 1 — Anti-Wireheading Split):
     - Hard-blocks Ring-0 verifiers, `execution_guard/`, `canonical/governance/`,
       `canonical/laws/`, `.github/`, all test files, and SHA-pinned runtime gates.
     - Enforces 6 deterministic promotion gates on every candidate `.py` diff:
         G1: Unified-diff structure, exact SHA-256 base-binding & AST wirehead scan
         G2: Positional input-dependency preservation (`repair_input_dependency_gate_v1`)
         G3: `< 10 ms` zero-copy CoW + `code_tree_sitter_impact_v1` confined regression
             with `_BrainAssertCounter` (`total_asserts_ran > 0`)
         G4: Escrowed sealed held-out evaluation (`PROOF_CARRYING_SHADOW_REALITY_POLICY_V2`)
             + AST diff-line mutant kill (`kill_ratio >= min_mutation_kill_ratio`)
         G5: `credit_gates_v1` statistical triad (`validity_gate`, `activation_gate`,
             `paired_significance`, Ville `e_process`) + interleaved A/B/B/A speedup gate
         G6: Executable-byte MDL budget + atomic commit & content-addressed rollback journal

  2. `SelfIntrospector` (Law 2 — Evaluator-Grounded Self-Diagnosis):
     - Clusters unresolved episodes by `(verifier_rejection_class, module, function, ast_kind)`.
     - Scans Ring-1 modules for algorithmic $O(N^2)$ / unmemoized-recursion hotspots and
       alpha-equivalent duplicate AST helpers.

  3. 5 Constructive White-Box Self-Code Evolution Operators (Law 3 — `ProposalBudgetEnvelope`):
     - Op 1: Algorithmic complexity reduction ($O(N^2) -> O(N)$ hash-set/index hoisting,
             $O(N) -> O(1)$ closed-form arithmetic loops, pure recursion memoization).
     - Op 2: Blinded trace-driven AST branch, operator & recursive-descent generalization
             (trained strictly on `visible_dev_cases`, never seeing `sealed_heldout_cases`).
     - Op 3: Verified organ & type-bridge forging (`capability_forge_v1`, `require_kill=True`).
     - Op 4: Cross-function MDL AST deduplication ($\Delta B_{\text{exec}} < 0$).
     - Op 5: `QualityDiversitySelfArchive` (MAP-Elites self-lineage archive).
"""
from __future__ import annotations

import ast
import copy
import difflib
import hashlib
import json
import os
import pathlib
import re
import shutil
import tempfile
import time
import zlib
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

from canonical.runtime import brokered_workspace_execution_v1 as broker
from canonical.runtime import capability_forge_v1
from canonical.runtime import credit_gates_v1
from canonical.runtime import property_v1
from canonical.runtime import r3_success_adapter_patch_firewall_v1 as r3_fw
from canonical.runtime.swe_observational_program_synthesizer_v1 import (
    extract_io_examples_from_test_source,
    synthesize_python_function_body,
)
from canonical.swe_kernel import repair_input_dependency_gate_v1 as input_dep_gate
from canonical.swe_kernel.concept_library_v1 import (
    CompoundingConceptLibrary,
    build_programmatic_ast_catamorphism_stmts,
    discover_ast_operator_morphisms,
    eval_pure_ast_expr,
    eval_pure_ast_function,
)
from canonical.swe_kernel.cow_impact_repair_engine_v1 import (
    cow_write_text,
    create_zero_copy_cow_workspace,
)

SCHEMA = "PROJECT_BRAIN_RECURSIVE_SELF_ARCHITECT_V1"

RING0_IMMUTABLE_PREFIXES: tuple[str, ...] = (
    "execution_guard/",
    "canonical/governance/",
    "canonical/laws/",
    ".github/",
    "canonical/tests/",
    "tests/",
)

RING0_IMMUTABLE_EXACT: frozenset[str] = frozenset(
    {
        "canonical/runtime/unified_cognitive_fabric_v1.py",
        "canonical/runtime/live_capability_invoker_v1.py",
        "canonical/runtime/live_brain_runtime_v1.py",
        "canonical/runtime/r3_improvement_queue_driver_v1.py",
        "canonical/runtime/live_brain_route_admission_v1.py",
        "canonical/runtime/computer_execution_boundary_v1.py",
        "canonical/runtime/enforce_goal_hierarchy.py",
        "canonical/runtime/credit_gates_v1.py",
        "canonical/runtime/property_v1.py",
        "canonical/runtime/verifier_falsification_v1.py",
        "canonical/runtime/brokered_workspace_execution_v1.py",
        "canonical/runtime/r3_independent_learning_verifier_v1.py",
        "canonical/runtime/r3_bound_success_checkpoint_verifier_v1.py",
        "canonical/runtime/r3_raw_success_checkpoint_verifier_v1.py",
        "canonical/runtime/r3_success_adapter_patch_firewall_v1.py",
        "canonical/swe_kernel/repair_input_dependency_gate_v1.py",
        "canonical/swe_kernel/recursive_self_architect_v1.py",
    }
)

_FORBIDDEN_AST_CALL_NAMES: frozenset[str] = frozenset({"exec", "eval", "compile", "__import__"})
_HUNK_HEADER_RE = re.compile(
    r"^@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? \+(?P<new_start>\d+)(?:,(?P<new_count>\d+))? @@(?: .*)?$"
)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def executable_byte_measure(source_text: str) -> int:
    """Measure normalized AST executable compressed byte complexity (`B_exec`).

    Strips docstrings and comments via canonical AST unparsing so formatting or
    comment churn cannot disguise code bloat or fake MDL compression.
    """
    try:
        tree = ast.parse(source_text)
    except SyntaxError:
        return len(zlib.compress(source_text.encode("utf-8"), level=9))

    class _StripDocstrings(ast.NodeTransformer):
        def _strip_body(self, body: list[ast.stmt]) -> list[ast.stmt]:
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                rest = body[1:]
                return rest or [ast.Pass()]
            return body

        def visit_Module(self, node: ast.Module) -> ast.AST:
            node.body = self._strip_body(node.body)
            return self.generic_visit(node)

        def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
            node.body = self._strip_body(node.body)
            return self.generic_visit(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AST:
            node.body = self._strip_body(node.body)
            return self.generic_visit(node)

        def visit_ClassDef(self, node: ast.ClassDef) -> ast.AST:
            node.body = self._strip_body(node.body)
            return self.generic_visit(node)

    cleaned = _StripDocstrings().visit(copy.deepcopy(tree))
    ast.fix_missing_locations(cleaned)
    canonical_src = ast.unparse(cleaned)
    return len(zlib.compress(canonical_src.encode("utf-8"), level=9))


def make_unified_diff(relpath: str, before_text: str, after_text: str) -> str:
    """Create a canonical git-style unified diff for a single Ring-1 Python file."""
    norm = relpath.strip().replace("\\", "/")
    before_lines = before_text.splitlines(keepends=True)
    after_lines = after_text.splitlines(keepends=True)
    if before_lines and not before_lines[-1].endswith("\n"):
        before_lines[-1] += "\n"
    if after_lines and not after_lines[-1].endswith("\n"):
        after_lines[-1] += "\n"
    diff = list(
        difflib.unified_diff(
            before_lines,
            after_lines,
            fromfile=f"a/{norm}",
            tofile=f"b/{norm}",
            n=3,
        )
    )
    if not diff:
        return ""
    header = f"diff --git a/{norm} b/{norm}\n"
    return header + "".join(diff)


@dataclass(frozen=True)
class ProposalBudgetEnvelope:
    """Finite proposal budget envelope preventing unbounded self-modification loops."""

    max_proposals_per_cycle: int = 8
    max_eval_ms: float = 4000.0
    max_touched_files: int = 2
    max_byte_growth: int = 380
    min_mutation_kill_ratio: float = 0.5
    min_speedup_ratio: float = 2.5


@dataclass(frozen=True)
class SelfPatchProposal:
    """Candidate Ring-1 source code patch authored under `ProposalBudgetEnvelope`."""

    proposal_id: str
    operator_id: str
    target_relpath: str
    function_name: str
    before_source: str
    after_source: str
    unified_diff: str
    base_sha256_by_path: Mapping[str, str]
    rationale: str
    improvement_axis: str  # "accuracy" | "complexity_speedup" | "mdl_compression"
    metadata: Mapping[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Law 1: Ring-0 Immutable SelfPatchFirewall & 6-Gate Referee
# ---------------------------------------------------------------------------


class SelfPatchFirewall:
    """Cryptographic Ring-0 unified-diff firewall blocking verifier/guard/test tampering."""

    def __init__(
        self,
        *,
        allowed_mutable_prefixes: Sequence[str] = (
            "canonical/swe_kernel/",
            "canonical/runtime/",
            "ring1/",
            "pkg/",
            "src/",
            "app/",
        ),
    ) -> None:
        self.allowed_mutable_prefixes = tuple(allowed_mutable_prefixes)

    def is_ring0_immutable(self, relpath: str) -> tuple[bool, str]:
        norm = relpath.strip().replace("\\", "/")
        p = pathlib.PurePosixPath(norm)
        if not norm or p.is_absolute() or ".." in p.parts:
            return True, "UNSAFE_RELATIVE_PATH"
        if norm in RING0_IMMUTABLE_EXACT:
            return True, f"RING0_IMMUTABLE_EXACT:{norm}"
        if any(norm.startswith(pref) for pref in RING0_IMMUTABLE_PREFIXES):
            if "test" in norm:
                return True, f"TEST_MUTATION_FORBIDDEN:{norm}"
            return True, f"RING0_IMMUTABLE_PREFIX:{norm}"
        fname = p.name
        if fname.startswith("test_") or fname.endswith("_test.py") or fname == "conftest.py":
            return True, f"TEST_MUTATION_FORBIDDEN:{norm}"
        if not norm.endswith(".py"):
            return True, f"NON_PYTHON_SELF_PATCH_FORBIDDEN:{norm}"
        if self.allowed_mutable_prefixes and not any(
            norm.startswith(pref) or "/" not in norm for pref in self.allowed_mutable_prefixes
        ):
            return True, f"OUTSIDE_RING1_MUTABLE_SCOPE:{norm}"
        return False, "RING1_MUTABLE"

    @staticmethod
    def _scan_anti_wireheading_ast(before_src: str, after_src: str) -> tuple[bool, str]:
        try:
            b_tree = ast.parse(before_src)
            a_tree = ast.parse(after_src)
        except SyntaxError as exc:
            return False, f"SYNTAX_ERROR:{exc.msg}"

        def _collect_hazards(tree: ast.AST) -> set[str]:
            hazards: set[str] = set()
            for nd in ast.walk(tree):
                if isinstance(nd, ast.Call):
                    if isinstance(nd.func, ast.Name) and nd.func.id in _FORBIDDEN_AST_CALL_NAMES:
                        hazards.add(f"call:{nd.func.id}")
                    elif isinstance(nd.func, ast.Attribute):
                        if nd.func.attr in ("system", "popen") and isinstance(nd.func.value, ast.Name) and nd.func.value.id == "os":
                            hazards.add(f"os.{nd.func.attr}")
                        if nd.func.attr in ("run", "Popen", "call", "check_output"):
                            for kw in nd.keywords:
                                if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                                    hazards.add("subprocess_shell_true")
                elif isinstance(nd, (ast.Import, ast.ImportFrom)):
                    mods = [alias.name for alias in nd.names]
                    if isinstance(nd, ast.ImportFrom) and nd.module:
                        mods.append(nd.module)
                    for m in mods:
                        if m in ("ctypes", "gc") or m.startswith("unittest.mock"):
                            hazards.add(f"import:{m}")
            return hazards

        before_h = _collect_hazards(b_tree)
        after_h = _collect_hazards(a_tree)
        introduced = sorted(after_h - before_h)
        if introduced:
            return False, "ANTI_WIREHEADING_AST_FORBIDDEN:" + ",".join(introduced)
        return True, "AST_CLEAN"

    def validate_and_render(
        self,
        root: pathlib.Path,
        unified_diff: str,
        base_sha256_by_path: Mapping[str, str],
        *,
        max_touched_files: int = 2,
    ) -> dict[str, Any]:
        """Parse, scope-check, SHA-verify, and render candidate unified diff in memory."""
        if not isinstance(unified_diff, str) or not unified_diff.strip():
            return {"ok": False, "code": "EMPTY_SELF_PATCH_DIFF"}

        raw_lines = unified_diff.splitlines()
        for line in raw_lines:
            if line.startswith(r3_fw.FORBIDDEN_METADATA_PREFIXES):
                return {"ok": False, "code": "FORBIDDEN_PATCH_METADATA", "detail": line[:120]}

        # Split multi-file unified diffs cleanly on `diff --git `
        blocks: list[list[str]] = []
        cur: list[str] = []
        for ln in raw_lines:
            if ln.startswith("diff --git "):
                if cur:
                    blocks.append(cur)
                cur = [ln]
            elif cur:
                cur.append(ln)
        if cur:
            blocks.append(cur)
        if not blocks:
            return {"ok": False, "code": "MISSING_DIFF_GIT_HEADER"}
        if len(blocks) > max_touched_files:
            return {"ok": False, "code": "TOO_MANY_TOUCHED_FILES", "count": len(blocks)}

        rendered_by_path: dict[str, dict[str, Any]] = {}
        changed_lines_by_path: dict[str, set[int]] = {}

        for blk in blocks:
            m = r3_fw.DIFF_HEADER.match(blk[0])
            if m is None or m.group(1) != m.group(2):
                return {"ok": False, "code": "INVALID_OR_RENAME_DIFF_HEADER", "detail": blk[0]}
            rel = m.group(1)
            immut, why = self.is_ring0_immutable(rel)
            if immut:
                code = "TEST_MUTATION_FORBIDDEN" if "TEST_MUTATION" in why else "RING0_IMMUTABLE_PATH_FORBIDDEN"
                return {"ok": False, "code": code, "detail": why, "path": rel}

            target_p = root / rel
            if target_p.is_symlink() or any(parent.is_symlink() for parent in target_p.parents if parent != root and root in parent.parents):
                return {"ok": False, "code": "SYMLINK_TARGET_FORBIDDEN", "path": rel}
            if not target_p.is_file():
                return {"ok": False, "code": "TARGET_FILE_MISSING", "path": rel}

            disk_bytes = target_p.read_bytes()
            disk_sha = _sha256_bytes(disk_bytes)
            expected_sha = str(base_sha256_by_path.get(rel) or "")
            if not expected_sha or disk_sha != expected_sha:
                return {
                    "ok": False,
                    "code": "BASE_SOURCE_DRIFT",
                    "path": rel,
                    "expected_sha256": expected_sha,
                    "actual_sha256": disk_sha,
                }

            before_text = disk_bytes.decode("utf-8")
            src_lines = before_text.splitlines()
            if len(blk) < 4 or blk[1] != f"--- a/{rel}" or blk[2] != f"+++ b/{rel}":
                return {"ok": False, "code": "MALFORMED_FILE_HEADERS", "path": rel}

            idx = 3
            cursor = 0
            out_lines: list[str] = []
            added_line_numbers: set[int] = set()
            while idx < len(blk):
                hm = _HUNK_HEADER_RE.match(blk[idx])
                if hm is None:
                    return {"ok": False, "code": "INVALID_HUNK_HEADER", "detail": blk[idx]}
                old_start = int(hm.group("old_start"))
                old_count = int(hm.group("old_count") or "1")
                new_count = int(hm.group("new_count") or "1")
                start0 = old_start - 1 if old_count > 0 else old_start
                if start0 < cursor or start0 > len(src_lines):
                    return {"ok": False, "code": "HUNK_OUT_OF_RANGE", "path": rel}
                out_lines.extend(src_lines[cursor:start0])
                src_pos = start0
                seen_old = 0
                seen_new = 0
                idx += 1
                while idx < len(blk) and not blk[idx].startswith("@@ "):
                    hl = blk[idx]
                    if hl.startswith("\\ No newline at end of file"):
                        idx += 1
                        continue
                    if not hl or hl[0] not in (" ", "-", "+"):
                        return {"ok": False, "code": "INVALID_HUNK_LINE", "detail": hl[:80]}
                    tag, body = hl[0], hl[1:]
                    if tag in (" ", "-"):
                        if src_pos >= len(src_lines) or src_lines[src_pos] != body:
                            return {"ok": False, "code": "HUNK_CONTEXT_MISMATCH", "path": rel}
                        src_pos += 1
                        seen_old += 1
                        if tag == " ":
                            out_lines.append(body)
                            seen_new += 1
                    else:
                        out_lines.append(body)
                        added_line_numbers.add(len(out_lines))
                        seen_new += 1
                    idx += 1
                if seen_old != old_count or seen_new != new_count:
                    return {"ok": False, "code": "HUNK_COUNT_MISMATCH", "path": rel}
                cursor = src_pos
            out_lines.extend(src_lines[cursor:])
            after_text = "\n".join(out_lines) + "\n"
            if after_text == before_text:
                return {"ok": False, "code": "NOOP_SELF_PATCH", "path": rel}

            ast_ok, ast_why = self._scan_anti_wireheading_ast(before_text, after_text)
            if not ast_ok:
                return {"ok": False, "code": "ANTI_WIREHEADING_AST_FORBIDDEN", "detail": ast_why, "path": rel}

            rendered_by_path[rel] = {
                "before_text": before_text,
                "after_text": after_text,
                "before_sha256": disk_sha,
                "after_sha256": _sha256_text(after_text),
            }
            changed_lines_by_path[rel] = added_line_numbers

        return {
            "ok": True,
            "code": "FIREWALL_ADMITTED",
            "rendered_by_path": rendered_by_path,
            "changed_lines_by_path": changed_lines_by_path,
        }


def _generate_diff_line_mutants(after_source: str, changed_lines: set[int], *, max_mutants: int = 8) -> list[str]:
    """Generate semantic AST mutants strictly on changed executable lines of `after_source`."""
    try:
        base_tree = ast.parse(after_source)
    except SyntaxError:
        return []

    mutants: list[str] = []
    seen: set[str] = {after_source}

    def _emit_mutated(mutator_fn: Callable[[ast.AST], bool]) -> None:
        if len(mutants) >= max_mutants:
            return
        cloned = copy.deepcopy(base_tree)
        if mutator_fn(cloned):
            ast.fix_missing_locations(cloned)
            try:
                src = ast.unparse(cloned) + "\n"
            except Exception:
                return
            if src not in seen:
                seen.add(src)
                mutants.append(src)

    # Enumerate candidate AST nodes inside `changed_lines` (or all function bodies if empty)
    target_nodes: list[tuple[int, str]] = []
    for idx, nd in enumerate(ast.walk(base_tree)):
        ln = getattr(nd, "lineno", None)
        if ln is None:
            continue
        if changed_lines and ln not in changed_lines:
            continue
        if isinstance(nd, ast.Compare) and len(nd.ops) == 1:
            target_nodes.append((idx, "compare"))
        elif isinstance(nd, ast.If):
            target_nodes.append((idx, "if_negate"))
        elif isinstance(nd, ast.BinOp) and isinstance(nd.op, (ast.Add, ast.Sub, ast.Mult, ast.FloorDiv)):
            target_nodes.append((idx, "binop"))
        elif isinstance(nd, ast.Return) and nd.value is not None:
            target_nodes.append((idx, "return_perturb"))

    _CMP_FLIP: dict[type[ast.cmpop], type[ast.cmpop]] = {
        ast.Eq: ast.NotEq,
        ast.NotEq: ast.Eq,
        ast.Lt: ast.GtE,
        ast.LtE: ast.Gt,
        ast.Gt: ast.LtE,
        ast.GtE: ast.Lt,
        ast.In: ast.NotIn,
        ast.NotIn: ast.In,
        ast.Is: ast.IsNot,
        ast.IsNot: ast.Is,
    }
    _BIN_FLIP: dict[type[ast.operator], type[ast.operator]] = {
        ast.Add: ast.Sub,
        ast.Sub: ast.Add,
        ast.Mult: ast.Add,
        ast.FloorDiv: ast.Add,
    }

    for target_idx, kind in target_nodes:
        if len(mutants) >= max_mutants:
            break

        def _apply_at(tree_copy: ast.AST, _ti: int = target_idx, _k: str = kind) -> bool:
            nodes = list(ast.walk(tree_copy))
            if _ti >= len(nodes):
                return False
            n = nodes[_ti]
            if _k == "compare" and isinstance(n, ast.Compare) and len(n.ops) == 1:
                alt = _CMP_FLIP.get(type(n.ops[0]))
                if alt is None:
                    return False
                n.ops[0] = alt()
                return True
            if _k == "if_negate" and isinstance(n, ast.If):
                n.test = ast.UnaryOp(op=ast.Not(), operand=n.test)
                return True
            if _k == "binop" and isinstance(n, ast.BinOp):
                alt_b = _BIN_FLIP.get(type(n.op))
                if alt_b is None:
                    return False
                n.op = alt_b()
                return True
            if _k == "return_perturb" and isinstance(n, ast.Return) and n.value is not None:
                if isinstance(n.value, ast.Constant) and isinstance(n.value.value, (int, float)) and not isinstance(n.value.value, bool):
                    n.value = ast.Constant(value=n.value.value + 1)
                else:
                    n.value = ast.Constant(value=None)
                return True
            return False

        _emit_mutated(_apply_at)

    return mutants


class Ring0SelfReferee:
    """Immutable Ring-0 6-gate promotion referee with sealed held-out escrow & rollback journal."""

    def __init__(
        self,
        journal_dir: pathlib.Path,
        *,
        firewall: SelfPatchFirewall | None = None,
        budget: ProposalBudgetEnvelope | None = None,
    ) -> None:
        self.journal_dir = pathlib.Path(journal_dir)
        self.journal_dir.mkdir(parents=True, exist_ok=True)
        self.firewall = firewall or SelfPatchFirewall()
        self.budget = budget or ProposalBudgetEnvelope()
        self._journal_path = self.journal_dir / "self_patch_journal_v1.json"

    def _load_journal(self) -> dict[str, Any]:
        if self._journal_path.is_file():
            try:
                data = json.loads(self._journal_path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data
            except Exception:
                pass
        return {"schema": SCHEMA, "commits": [], "refusals": [], "cumulative_diffs": []}

    def _save_journal(self, payload: Mapping[str, Any]) -> None:
        tmp = self._journal_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        tmp.replace(self._journal_path)

    @staticmethod
    def _discover_impacted_tests(ws_root: pathlib.Path, relpath: str, explicit_tests: Sequence[str] | None) -> list[str]:
        if explicit_tests:
            return [t for t in explicit_tests if (ws_root / t).is_file()]
        found: list[str] = []
        try:
            from canonical.runtime.bound_capabilities import code_tree_sitter_impact_v1 as ts_impact

            imp = ts_impact.run({"changed_paths": [relpath], "source_root": "."}, ws_root)
            for tp in imp.get("selected_tests") or imp.get("impacted_tests") or []:
                rel_t = str(tp)
                if (ws_root / rel_t).is_file() and rel_t not in found:
                    found.append(rel_t)
        except Exception:
            pass
        if not found:
            for p in sorted(ws_root.rglob("test_*.py")):
                rel_t = p.relative_to(ws_root).as_posix()
                if rel_t not in found:
                    found.append(rel_t)
        return found

    @staticmethod
    def _build_sealed_heldout_test_source(
        module_import_name: str,
        function_name: str,
        cases: Sequence[Mapping[str, Any]],
    ) -> str:
        lines = [
            "import unittest",
            f"import {module_import_name} as _target_mod",
            "",
            "class SealedHeldoutEscrowTests(unittest.TestCase):",
        ]
        for idx, case in enumerate(cases):
            args_r = repr(tuple(case.get("args") or ()))
            kwargs_r = repr(dict(case.get("kwargs") or {}))
            if "raises" in case and case["raises"]:
                exc_name = str(case["raises"])
                lines.extend(
                    [
                        f"    def test_sealed_case_{idx}(self):",
                        f"        with self.assertRaises({exc_name}):",
                        f"            getattr(_target_mod, {function_name!r})(*{args_r}, **{kwargs_r})",
                    ]
                )
            else:
                exp_r = repr(case.get("expected"))
                lines.extend(
                    [
                        f"    def test_sealed_case_{idx}(self):",
                        f"        self.assertEqual(getattr(_target_mod, {function_name!r})(*{args_r}, **{kwargs_r}), {exp_r})",
                    ]
                )
        return "\n".join(lines) + "\n"

    @staticmethod
    def _evaluate_cases_confined(
        ws_root: pathlib.Path,
        target_relpath: str,
        candidate_source: str,
        function_name: str,
        cases: Sequence[Mapping[str, Any]],
    ) -> dict[str, int]:
        """Evaluate each case individually inside a single `PersistentConfinedZygote` fork-batch (`~5 ms`, `0` host `exec()`)."""
        if not cases:
            return {}
        mod_rel = target_relpath[:-3].replace("/", ".")
        probe_name = "_sealed_eval_probe_test.py"
        case_ids: list[str] = []
        batch_overrides: list[dict[str, str]] = []
        for idx, case in enumerate(cases):
            cid = str(case.get("id") or f"case_{idx}")
            case_ids.append(cid)
            single_src = Ring0SelfReferee._build_sealed_heldout_test_source(mod_rel, function_name, [case])
            batch_overrides.append({probe_name: single_src})

        with tempfile.TemporaryDirectory(prefix="brain-r0-eval-") as td:
            eval_ws = pathlib.Path(td) / "ws"
            create_zero_copy_cow_workspace(ws_root, eval_ws)
            cow_write_text(eval_ws / target_relpath, candidate_source)
            cow_write_text(eval_ws / probe_name, batch_overrides[0][probe_name])
            res = broker.run_confined_python_candidate_batch(
                eval_ws,
                "",
                [probe_name],
                batch_overrides,
                stop_on_first_pass=False,
                per_candidate_timeout_s=2.0,
            )
            if not res.get("confined"):
                return {}
            passing = set(res.get("passing_indices") or [])
            return {cid: (1 if i in passing else 0) for i, cid in enumerate(case_ids)}

    @staticmethod
    def _measure_paired_confined_speedup(
        ws_root: pathlib.Path,
        target_relpath: str,
        before_source: str,
        after_source: str,
        function_name: str,
        benchmark_inputs: Sequence[tuple[Any, ...]],
        parity_inputs: Sequence[tuple[Any, ...]],
    ) -> dict[str, Any]:
        """Run interleaved A/B/B/A paired parity & thresholded speedup ladder inside `PersistentConfinedZygote`."""
        thresholds = (1.5, 2.5, 4.0, 6.0, 10.0, 15.0, 25.0)
        probe_name = "_test_paired_speed.py"

        def _make_speed_probe(min_ratio: float, single_round: int | None = None) -> str:
            rounds_expr = f"[{single_round}]" if single_round is not None else "list(range(6))"
            return "\n".join(
                [
                    "import time, unittest",
                    "import _before_impl as _b",
                    "import _after_impl as _a",
                    "",
                    "def _obs(fn, args):",
                    "    try:",
                    "        return ('VAL', fn(*args))",
                    "    except Exception as exc:",
                    "        return ('EXC', type(exc).__name__)",
                    "",
                    "class PairedSpeedBenchmark(unittest.TestCase):",
                    "    def test_interleaved_parity_and_speedup(self):",
                    f"        fb = getattr(_b, {function_name!r})",
                    f"        fa = getattr(_a, {function_name!r})",
                    f"        for args in {repr(list(parity_inputs))}:",
                    "            self.assertEqual(_obs(fa, args), _obs(fb, args))",
                    f"        bench_cases = {repr(list(benchmark_inputs))}",
                    "        ratios = []",
                    f"        for round_idx in {rounds_expr}:",
                    "            args = bench_cases[round_idx % len(bench_cases)]",
                    "            if round_idx % 2 == 0:",
                    "                t0 = time.perf_counter_ns(); r_b = _obs(fb, args); tb = (time.perf_counter_ns() - t0) / 1e6",
                    "                t1 = time.perf_counter_ns(); r_a = _obs(fa, args); ta = (time.perf_counter_ns() - t1) / 1e6",
                    "            else:",
                    "                t1 = time.perf_counter_ns(); r_a = _obs(fa, args); ta = (time.perf_counter_ns() - t1) / 1e6",
                    "                t0 = time.perf_counter_ns(); r_b = _obs(fb, args); tb = (time.perf_counter_ns() - t0) / 1e6",
                    "            self.assertEqual(r_a, r_b)",
                    "            ratios.append(tb / max(ta, 1e-6))",
                    "        ratios.sort()",
                    "        med = ratios[len(ratios) // 2]",
                    f"        self.assertGreaterEqual(med, {float(min_ratio)})",
                ]
            ) + "\n"

        batch_overrides: list[dict[str, str]] = [{probe_name: _make_speed_probe(th)} for th in thresholds]
        for r_i in range(6):
            batch_overrides.append({probe_name: _make_speed_probe(1.5, single_round=r_i)})

        with tempfile.TemporaryDirectory(prefix="brain-r0-bench-") as td:
            b_ws = pathlib.Path(td) / "ws"
            create_zero_copy_cow_workspace(ws_root, b_ws)
            cow_write_text(b_ws / "_before_impl.py", before_source)
            cow_write_text(b_ws / "_after_impl.py", after_source)
            cow_write_text(b_ws / probe_name, batch_overrides[0][probe_name])
            res = broker.run_confined_python_candidate_batch(
                b_ws,
                "",
                [probe_name],
                batch_overrides,
                stop_on_first_pass=False,
                per_candidate_timeout_s=4.0,
            )
            if not (res.get("ok") and res.get("confined")):
                return {"ok": False, "reason": "BENCHMARK_RUNNER_FAILED", "runner": res}
            passing = set(res.get("passing_indices") or [])
            passed_thresholds = [thresholds[i] for i in range(len(thresholds)) if i in passing]
            if not passed_thresholds:
                return {"ok": False, "reason": "PARITY_OR_MIN_SPEEDUP_FAILED", "passing_indices": sorted(passing)}
            achieved_speedup = max(passed_thresholds)
            before_trials = {f"trial_{r_i}": 0 for r_i in range(6)}
            after_trials = {f"trial_{r_i}": (1 if (len(thresholds) + r_i) in passing else 0) for r_i in range(6)}
            cred = credit_gates_v1.credit(before_trials, after_trials, sigma=2.0, gate="paired")
            return {
                "ok": True,
                "median_speedup": float(achieved_speedup),
                "before_ms": before_trials,
                "after_ms": after_trials,
                "paired_credit": cred,
            }

    def evaluate_and_commit(
        self,
        root: pathlib.Path,
        proposal: SelfPatchProposal,
        *,
        test_relpaths: Sequence[str] | None = None,
        sealed_heldout_cases: Sequence[Mapping[str, Any]] | None = None,
        benchmark_inputs: Sequence[tuple[Any, ...]] | None = None,
        parity_inputs: Sequence[tuple[Any, ...]] | None = None,
        apply_to_root: bool = True,
    ) -> dict[str, Any]:
        """Run all 6 Ring-0 gates on `proposal`; atomically commit & journal iff all 6 pass."""
        t0 = time.perf_counter()
        journal = self._load_journal()

        def _refuse(gate_name: str, code: str, detail: Mapping[str, Any] | None = None) -> dict[str, Any]:
            verdict = {
                "schema": SCHEMA,
                "promoted": False,
                "proposal_id": proposal.proposal_id,
                "operator_id": proposal.operator_id,
                "failed_gate": gate_name,
                "code": code,
                "detail": dict(detail or {}),
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
                "model_dependency_count": 0,
            }
            journal.setdefault("refusals", []).append(
                {
                    "proposal_id": proposal.proposal_id,
                    "target_relpath": proposal.target_relpath,
                    "failed_gate": gate_name,
                    "code": code,
                }
            )
            self._save_journal(journal)
            return verdict

        # Gate 1: Cryptographic Firewall, Scope & AST Anti-Wireheading
        fw = self.firewall.validate_and_render(
            root,
            proposal.unified_diff,
            proposal.base_sha256_by_path,
            max_touched_files=self.budget.max_touched_files,
        )
        if not fw.get("ok"):
            return _refuse("G1_SELF_PATCH_FIREWALL", str(fw.get("code") or "FIREWALL_REFUSED"), fw)

        rendered_map = fw["rendered_by_path"]
        changed_lines_map = fw["changed_lines_by_path"]

        # Gate 2: Positional Input-Dependency Preservation (`repair_input_dependency_gate_v1`)
        for rel, info in rendered_map.items():
            dep_verdict = input_dep_gate.gate(info["before_text"], info["after_text"])
            if dep_verdict.get("status") != input_dep_gate.PASS:
                return _refuse(
                    "G2_INPUT_DEPENDENCY_PRESERVATION",
                    "PATCH_STOPPED_READING_ITS_INPUTS",
                    {"path": rel, "gate": dep_verdict},
                )

        # Gate 3: `< 10 ms` Zero-Copy CoW + Impact-Sliced Confined Regression (`_BrainAssertCounter > 0`)
        primary_rel = proposal.target_relpath
        primary_after = rendered_map[primary_rel]["after_text"]
        primary_before = rendered_map[primary_rel]["before_text"]

        with tempfile.TemporaryDirectory(prefix="brain-r0-cow-") as td:
            cow_ws = pathlib.Path(td) / "ws"
            t_cow0 = time.perf_counter()
            cow_stats = create_zero_copy_cow_workspace(root, cow_ws)
            cow_ms = round((time.perf_counter() - t_cow0) * 1000.0, 3)
            for rel, info in rendered_map.items():
                if rel != primary_rel:
                    cow_write_text(cow_ws / rel, info["after_text"])

            active_tests = list(self._discover_impacted_tests(cow_ws, primary_rel, test_relpaths))
            if sealed_heldout_cases:
                mod_import = primary_rel[:-3].replace("/", ".")
                sealed_src = self._build_sealed_heldout_test_source(
                    mod_import, proposal.function_name, sealed_heldout_cases
                )
                sealed_rel = "_test_sealed_heldout_escrow.py"
                cow_write_text(cow_ws / sealed_rel, sealed_src)
                active_tests_plus_sealed = active_tests + [sealed_rel]
            else:
                active_tests_plus_sealed = list(active_tests)

            if not active_tests_plus_sealed:
                return _refuse("G3_COW_CONFINED_REGRESSION", "NO_VERIFICATION_SUITE_FOUND")

            if active_tests:
                reg_res = broker.run_confined_python_candidate_batch(
                    cow_ws,
                    primary_rel,
                    active_tests,
                    [primary_after],
                    stop_on_first_pass=True,
                    per_candidate_timeout_s=5.0,
                )
                cand_rows = reg_res.get("candidates") or []
                cand_fail = cand_rows[0].get("failure") if cand_rows else None
                if not (
                    reg_res.get("ok")
                    and reg_res.get("confined")
                    and reg_res.get("screen_authoritative")
                    and 0 in (reg_res.get("passing_indices") or [])
                    and cand_fail != "ZERO_ASSERTIONS_EXECUTED"
                ):
                    return _refuse(
                        "G3_COW_CONFINED_REGRESSION",
                        "REGRESSION_OR_ZERO_ASSERT_FAILURE",
                        {"runner": reg_res, "candidate_failure": cand_fail},
                    )
            else:
                asserts_ran = 0

            # Gate 4: Sealed Held-Out Escrow (`PROOF_CARRYING_SHADOW_REALITY_POLICY_V2`) + Diff Mutant Kill
            heldout_before_scores: dict[str, int] = {}
            heldout_after_scores: dict[str, int] = {}
            if sealed_heldout_cases:
                heldout_before_scores = self._evaluate_cases_confined(
                    cow_ws, primary_rel, primary_before, proposal.function_name, sealed_heldout_cases
                )
                heldout_after_scores = self._evaluate_cases_confined(
                    cow_ws, primary_rel, primary_after, proposal.function_name, sealed_heldout_cases
                )
                if not heldout_after_scores or any(v == 0 for v in heldout_after_scores.values()):
                    return _refuse(
                        "G4_SEALED_HELDOUT_AND_MUTATION_KILL",
                        "SEALED_HELDOUT_FALSIFIED",
                        {"before": heldout_before_scores, "after": heldout_after_scores},
                    )
                # Also verify artifact mutation falsification via `property_v1.mutate`
                score_blob = json.dumps(heldout_after_scores, sort_keys=True)
                mut_pairs = property_v1.mutate(score_blob)
                if mut_pairs:
                    killed_p = 0
                    for _mk, m_txt in mut_pairs:
                        try:
                            ok_m = json.loads(m_txt) == heldout_after_scores
                        except Exception:
                            ok_m = False
                        if not ok_m:
                            killed_p += 1
                    if (killed_p / len(mut_pairs)) < 0.5:
                        return _refuse(
                            "G4_SEALED_HELDOUT_AND_MUTATION_KILL",
                            "PROPERTY_MUTATION_WEAK",
                            {"killed": killed_p, "total": len(mut_pairs)},
                        )

            diff_mutants = _generate_diff_line_mutants(
                primary_after,
                changed_lines_map.get(primary_rel, set()),
                max_mutants=6,
            )
            if diff_mutants:
                mut_batch = broker.run_confined_python_candidate_batch(
                    cow_ws,
                    primary_rel,
                    active_tests_plus_sealed,
                    diff_mutants,
                    stop_on_first_pass=False,
                    per_candidate_timeout_s=3.0,
                )
                surviving = set(mut_batch.get("passing_indices") or [])
                killed = len(diff_mutants) - len(surviving)
                kill_ratio = killed / len(diff_mutants)
                if kill_ratio < self.budget.min_mutation_kill_ratio:
                    return _refuse(
                        "G4_SEALED_HELDOUT_AND_MUTATION_KILL",
                        "DIFF_MUTANTS_SURVIVED",
                        {"total_mutants": len(diff_mutants), "killed": killed, "kill_ratio": round(kill_ratio, 4)},
                    )
            else:
                kill_ratio = 1.0

            # Gate 5: Statistical Credit Triad (`credit_gates_v1`) + Paired Speedup Gate
            speed_report: dict[str, Any] | None = None
            if proposal.improvement_axis == "complexity_speedup":
                if not benchmark_inputs:
                    return _refuse("G5_CREDIT_AND_PARETO_GATE", "SPEEDUP_BENCHMARK_INPUTS_REQUIRED")
                speed_report = self._measure_paired_confined_speedup(
                    cow_ws,
                    primary_rel,
                    primary_before,
                    primary_after,
                    proposal.function_name,
                    benchmark_inputs,
                    parity_inputs or benchmark_inputs,
                )
                if not speed_report.get("ok"):
                    return _refuse("G5_CREDIT_AND_PARETO_GATE", "SPEEDUP_PARITY_OR_RUNNER_FAILED", speed_report)
                if float(speed_report["median_speedup"]) < self.budget.min_speedup_ratio:
                    return _refuse("G5_CREDIT_AND_PARETO_GATE", "INSUFFICIENT_EMPIRICAL_SPEEDUP", speed_report)
                credit_verdict = speed_report["paired_credit"]
                if not credit_verdict.get("credited"):
                    return _refuse("G5_CREDIT_AND_PARETO_GATE", "PAIRED_SPEEDUP_NOT_SIGNIFICANT", speed_report)
                diffs_for_e = [1.0] * len(speed_report["after_ms"])
            elif proposal.improvement_axis == "accuracy":
                if not sealed_heldout_cases:
                    return _refuse("G5_CREDIT_AND_PARETO_GATE", "SEALED_HELDOUT_REQUIRED_FOR_ACCURACY_CREDIT")
                credit_verdict = credit_gates_v1.credit(
                    heldout_before_scores, heldout_after_scores, sigma=2.0, gate="paired"
                )
                if not credit_verdict.get("credited"):
                    return _refuse(
                        "G5_CREDIT_AND_PARETO_GATE",
                        str(credit_verdict.get("reason") or "CREDIT_REFUSED"),
                        {"credit": credit_verdict, "before": heldout_before_scores, "after": heldout_after_scores},
                    )
                usable = credit_gates_v1.validity_gate(heldout_before_scores, heldout_after_scores)
                diffs_for_e = [float(heldout_after_scores[k] - heldout_before_scores[k]) for k in usable]
            else:
                # MDL compression axis: requires zero regressions + strict byte reduction in Gate 6
                credit_verdict = {"schema": credit_gates_v1.SCHEMA, "credited": True, "reason": "MDL_PARITY_VERIFIED"}
                diffs_for_e = [0.5]

        # Gate 6: Resource-Bounded Executable-Byte MDL Budget + Atomic Commit & Rollback Receipt
        before_bytes = sum(executable_byte_measure(v["before_text"]) for v in rendered_map.values())
        after_bytes = sum(executable_byte_measure(v["after_text"]) for v in rendered_map.values())
        delta_exec_bytes = after_bytes - before_bytes
        if proposal.improvement_axis == "mdl_compression" and delta_exec_bytes >= 0:
            return _refuse(
                "G6_MDL_BYTE_BUDGET_AND_COMMIT",
                "MDL_COMPRESSION_DID_NOT_SHRINK_BYTES",
                {"before_exec_bytes": before_bytes, "after_exec_bytes": after_bytes},
            )
        if delta_exec_bytes > self.budget.max_byte_growth:
            return _refuse(
                "G6_MDL_BYTE_BUDGET_AND_COMMIT",
                "EXECUTABLE_BYTE_BUDGET_EXCEEDED",
                {"delta_exec_bytes": delta_exec_bytes, "max_byte_growth": self.budget.max_byte_growth},
            )

        cum_diffs = [float(x) for x in (journal.get("cumulative_diffs") or [])] + diffs_for_e
        e_proc = credit_gates_v1.e_process(cum_diffs, bound=1.0)
        receipt_id = "selfpatch_" + _sha256_text(proposal.unified_diff)[:16]

        if apply_to_root:
            for rel, info in rendered_map.items():
                dst = root / rel
                tmp_dst = dst.with_suffix(dst.suffix + ".selfpatch.tmp")
                tmp_dst.write_text(info["after_text"], encoding="utf-8")
                tmp_dst.replace(dst)

        commit_record = {
            "receipt_id": receipt_id,
            "proposal_id": proposal.proposal_id,
            "operator_id": proposal.operator_id,
            "improvement_axis": proposal.improvement_axis,
            "target_relpath": primary_rel,
            "function_name": proposal.function_name,
            "rationale": proposal.rationale,
            "unified_diff": proposal.unified_diff,
            "files": {
                rel: {
                    "before_sha256": info["before_sha256"],
                    "after_sha256": info["after_sha256"],
                    "before_text": info["before_text"],
                }
                for rel, info in rendered_map.items()
            },
            "delta_exec_bytes": delta_exec_bytes,
            "mutation_kill_ratio": round(kill_ratio, 4),
            "cow_clone_ms": cow_ms,
            "cow_hardlinks": int(cow_stats.get("hardlinks_created") or 0),
            "credit": credit_verdict,
            "speed_report": speed_report,
            "e_process": e_proc,
            "applied_to_root": bool(apply_to_root),
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }
        journal["cumulative_diffs"] = cum_diffs[-256:]
        journal.setdefault("commits", []).append(commit_record)
        self._save_journal(journal)

        return {
            "schema": SCHEMA,
            "promoted": True,
            "receipt_id": receipt_id,
            "commit": commit_record,
            "model_dependency_count": 0,
        }

    def rollback(self, root: pathlib.Path, receipt_id: str) -> dict[str, Any]:
        """Atomically roll back an applied Ring-1 self-patch using its content-addressed receipt."""
        journal = self._load_journal()
        for entry in reversed(journal.get("commits") or []):
            if entry.get("receipt_id") != receipt_id:
                continue
            for rel, finfo in (entry.get("files") or {}).items():
                dst = root / rel
                if not dst.is_file():
                    return {"ok": False, "code": "ROLLBACK_TARGET_MISSING", "path": rel}
                cur_sha = _sha256_bytes(dst.read_bytes())
                if cur_sha != finfo.get("after_sha256"):
                    return {"ok": False, "code": "ROLLBACK_HEAD_SHA_DRIFT", "path": rel}
            for rel, finfo in (entry.get("files") or {}).items():
                dst = root / rel
                tmp_dst = dst.with_suffix(dst.suffix + ".rollback.tmp")
                tmp_dst.write_text(str(finfo["before_text"]), encoding="utf-8")
                tmp_dst.replace(dst)
            entry["rolled_back"] = True
            self._save_journal(journal)
            return {"ok": True, "receipt_id": receipt_id, "restored_files": sorted((entry.get("files") or {}).keys())}
        return {"ok": False, "code": "RECEIPT_NOT_FOUND", "receipt_id": receipt_id}


# ---------------------------------------------------------------------------
# Law 2: Ring-1 SelfIntrospector (Weakness Miner + Hotspot & MDL Scanner)
# ---------------------------------------------------------------------------


class EmpiricalZygoteProfiler:
    """Measure empirical scaling exponent alpha_hat & call-growth ratio inside PersistentConfinedZygote (0 host exec)."""

    @staticmethod
    def profile_function_scaling(
        ws_root: pathlib.Path,
        target_relpath: str,
        function_name: str,
        input_generator_By_size: Mapping[int, tuple[Any, ...]],
    ) -> dict[str, Any]:
        """Run (N, 2N, 4N) workloads under `sys.setprofile` + `perf_counter_ns` in a confined Zygote fork."""
        sizes = sorted(int(k) for k in input_generator_By_size.keys())
        if len(sizes) < 2:
            return {"ok": False, "reason": "INSUFFICIENT_SCALING_SIZES"}
        mod_import = target_relpath[:-3].replace("/", ".")
        probe_rel = "_test_zygote_profiler.py"
        serialized_inputs = {int(sz): tuple(input_generator_By_size[sz]) for sz in sizes}
        thresholds = (0.5, 0.85, 1.15, 1.45, 1.70, 1.95, 2.30)

        def _make_alpha_probe(min_alpha: float) -> str:
            return "\n".join(
                [
                    "import math, sys, time, unittest",
                    f"import {mod_import} as _tmod",
                    "",
                    "class ConfinedScalingProfileTest(unittest.TestCase):",
                    "    def test_measure_scaling(self):",
                    f"        fn = getattr(_tmod, {function_name!r})",
                    f"        cases = {repr(serialized_inputs)}",
                    "        timings_ns = {}",
                    "        calls_by_size = {}",
                    "        for sz in sorted(cases.keys()):",
                    "            args = cases[sz]",
                    "            cnt = [0]",
                    "            def _prof(_frame, event, _arg):",
                    "                if event == 'call':",
                    "                    cnt[0] += 1",
                    "            sys.setprofile(_prof)",
                    "            try:",
                    "                _ = fn(*args)",
                    "            finally:",
                    "                sys.setprofile(None)",
                    "            calls_by_size[sz] = int(cnt[0])",
                    "            samples = []",
                    "            for _ in range(3):",
                    "                t0 = time.perf_counter_ns()",
                    "                _ = fn(*args)",
                    "                samples.append(max(1, time.perf_counter_ns() - t0))",
                    "            samples.sort()",
                    "            timings_ns[sz] = int(samples[1])",
                    "        s_min, s_max = min(cases.keys()), max(cases.keys())",
                    "        size_ratio = max(1.0001, float(s_max) / float(s_min))",
                    "        time_ratio = max(1e-6, float(timings_ns[s_max]) / float(timings_ns[s_min]))",
                    "        alpha_hat = math.log(time_ratio) / math.log(size_ratio)",
                    f"        self.assertGreaterEqual(alpha_hat, {float(min_alpha)})",
                ]
            ) + "\n"

        batch_overrides = [{probe_rel: _make_alpha_probe(th)} for th in thresholds]
        with tempfile.TemporaryDirectory(prefix="brain-zyg-prof-") as td:
            p_ws = pathlib.Path(td) / "ws"
            create_zero_copy_cow_workspace(ws_root, p_ws)
            cow_write_text(p_ws / probe_rel, batch_overrides[0][probe_rel])
            res = broker.run_confined_python_candidate_batch(
                p_ws,
                "",
                [probe_rel],
                batch_overrides,
                stop_on_first_pass=False,
                per_candidate_timeout_s=4.0,
            )
            if not (res.get("ok") and res.get("confined")):
                return {"ok": False, "reason": "ZYGOTE_PROFILE_FAILED", "runner": res}
            passing = set(res.get("passing_indices") or [])
            passed_th = [thresholds[i] for i in range(len(thresholds)) if i in passing]
            est_alpha = max(passed_th) if passed_th else 0.0
            return {
                "ok": True,
                "sizes": sizes,
                "alpha_hat": float(est_alpha),
                "superlinear": bool(est_alpha >= 1.45),
                "passing_thresholds": passed_th,
            }

    @staticmethod
    def profile_call_collisions(
        ws_root: pathlib.Path,
        target_relpath: str,
        function_name: str,
        probe_inputs: Sequence[tuple[Any, ...]],
    ) -> dict[str, Any]:
        """Measure duplicate-call collision ratio `total_calls / unique_arg_tuples` inside confined Zygote."""
        if not probe_inputs:
            return {"ok": False, "reason": "NO_PROBE_INPUTS"}
        mod_import = target_relpath[:-3].replace("/", ".")
        probe_rel = "_test_zygote_collision_probe.py"
        ratios = (1.5, 2.0, 4.0, 8.0)

        def _make_collision_probe(min_ratio: float) -> str:
            return "\n".join(
                [
                    "import importlib, unittest",
                    "class _CollisionProbe(unittest.TestCase):",
                    "    def test_collision_ratio(self):",
                    f"        mod = importlib.import_module({mod_import!r})",
                    f"        orig = getattr(mod, {function_name!r})",
                    "        total = [0]",
                    "        seen = set()",
                    "        def _wrapped(*a, **kw):",
                    "            total[0] += 1",
                    "            seen.add((repr(a), repr(kw)))",
                    "            return orig(*a, **kw)",
                    f"        setattr(mod, {function_name!r}, _wrapped)",
                    "        try:",
                    f"            for args in {list(probe_inputs)!r}:",
                    "                _ = _wrapped(*args)",
                    "        finally:",
                    f"            setattr(mod, {function_name!r}, orig)",
                    "        ratio = float(total[0]) / float(max(1, len(seen)))",
                    f"        self.assertGreaterEqual(ratio, {float(min_ratio)})",
                ]
            ) + "\n"

        batch_overrides = [{probe_rel: _make_collision_probe(r)} for r in ratios]
        with tempfile.TemporaryDirectory(prefix="brain-zyg-coll-") as td:
            p_ws = pathlib.Path(td) / "ws"
            create_zero_copy_cow_workspace(ws_root, p_ws)
            cow_write_text(p_ws / probe_rel, batch_overrides[0][probe_rel])
            res = broker.run_confined_python_candidate_batch(
                p_ws,
                "",
                [probe_rel],
                batch_overrides,
                stop_on_first_pass=False,
                per_candidate_timeout_s=3.0,
            )
            if not (res.get("ok") and res.get("confined")):
                return {"ok": False, "reason": "ZYGOTE_COLLISION_PROBE_FAILED"}
            passing = set(res.get("passing_indices") or [])
            passed_r = [ratios[i] for i in range(len(ratios)) if i in passing]
            est_ratio = max(passed_r) if passed_r else 1.0
            return {
                "ok": True,
                "collision_ratio_hat": float(est_ratio),
                "overlapping_subproblems": bool(est_ratio >= 2.0),
            }

    @staticmethod
    def synthesize_scaling_workloads_from_tests(
        root: pathlib.Path,
        target_relpath: str,
        function_name: str,
        test_relpaths: Sequence[str] | None,
    ) -> dict[str, Any]:
        """Auto-derive parity inputs, geometric scaling profile inputs, and benchmark inputs from test ASTs."""
        if not test_relpaths:
            return {}
        combined_src = "\n\n".join(
            (root / tr).read_text(encoding="utf-8")
            for tr in test_relpaths
            if (root / tr).is_file()
        )
        if not combined_src.strip():
            return {}
        exs, _ = extract_io_examples_from_test_source(combined_src, function_name)
        if not exs:
            return {}
        parity_inputs = [tuple(args) for args, _ in exs[:8]]
        sample_args = next((tuple(args) for args, _ in exs if any(isinstance(a, (list, tuple, str, int)) for a in args)), parity_inputs[0])

        def _scale_arg(val: Any, target_n: int) -> Any:
            if isinstance(val, list):
                if not val:
                    return list(range(target_n))
                if all(isinstance(x, int) and not isinstance(x, bool) for x in val):
                    return [(i * 7 + 3) % max(4, target_n // 2) for i in range(target_n)]
                reps = max(1, (target_n + len(val) - 1) // len(val))
                return (val * reps)[:target_n]
            if isinstance(val, tuple):
                return tuple(_scale_arg(list(val), target_n))
            if isinstance(val, str) and len(val) >= 2:
                reps = max(1, (target_n + len(val) - 1) // len(val))
                return (val * reps)[:target_n]
            if isinstance(val, int) and not isinstance(val, bool) and 0 <= val <= 15:
                return min(24, max(val, target_n // 40 + 10))
            return val

        # Calibrate benchmark input size to AST loop nesting depth so O(N^3) baseline finishes in ~10ms, not 10s!
        bench_n = 1400
        try:
            fn_src = (root / target_relpath).read_text(encoding="utf-8")
            fn_tree = ast.parse(fn_src)
            for fn_nd in [n for n in fn_tree.body if isinstance(n, ast.FunctionDef) and n.name == function_name]:
                def _max_loop_depth(nd: ast.AST) -> int:
                    child_max = max((_max_loop_depth(ch) for ch in ast.iter_child_nodes(nd)), default=0)
                    return child_max + (1 if isinstance(nd, (ast.For, ast.While)) else 0)
                ld = _max_loop_depth(fn_nd)
                if ld >= 3:
                    bench_n = 110
                elif ld == 2:
                    bench_n = 550
        except Exception:
            pass

        if any(isinstance(a, (list, tuple, str)) for a in sample_args):
            prof_cases = {sz: tuple(_scale_arg(a, sz) for a in sample_args) for sz in (25, 50, 90)}
            bench_input = tuple(_scale_arg(a, bench_n) for a in sample_args)
            return {
                "parity_inputs": parity_inputs,
                "benchmark_inputs": [bench_input],
                "profile_cases": prof_cases,
            }
        if len(sample_args) == 1 and isinstance(sample_args[0], int) and not isinstance(sample_args[0], bool):
            return {
                "parity_inputs": parity_inputs,
                "benchmark_inputs": [(23,)],
                "profile_cases": {12: (12,), 16: (16,), 20: (20,)},
            }
        return {"parity_inputs": parity_inputs}


_MUTATING_METHOD_NAMES: frozenset[str] = frozenset(
    {
        "append",
        "extend",
        "insert",
        "pop",
        "remove",
        "clear",
        "sort",
        "reverse",
        "add",
        "discard",
        "update",
        "setdefault",
    }
)

_PURE_BUILTIN_CALLABLES: frozenset[str] = frozenset(
    {
        "abs",
        "all",
        "any",
        "bool",
        "dict",
        "divmod",
        "enumerate",
        "float",
        "frozenset",
        "hash",
        "int",
        "len",
        "list",
        "max",
        "min",
        "ord",
        "chr",
        "pow",
        "range",
        "repr",
        "reversed",
        "round",
        "set",
        "sorted",
        "str",
        "sum",
        "tuple",
        "zip",
    }
)

_PURE_IMMUTABLE_METHODS: frozenset[str] = frozenset(
    {
        "strip",
        "lstrip",
        "rstrip",
        "lower",
        "upper",
        "split",
        "splitlines",
        "replace",
        "startswith",
        "endswith",
        "find",
        "count",
        "join",
        "encode",
        "decode",
        "get",
        "keys",
        "values",
        "items",
    }
)

_O1_SCALAR_CALLS: frozenset[str] = frozenset({"len", "int", "float", "bool", "ord", "chr", "abs"})


def _base_root_name(expr: ast.AST) -> str | None:
    cur = expr
    while isinstance(cur, (ast.Subscript, ast.Attribute)):
        cur = cur.value
    return cur.id if isinstance(cur, ast.Name) else None


def _compute_write_set(scope_node: ast.AST) -> set[str]:
    """Compute all variable identifiers assigned or locally mutated inside `scope_node`."""
    written: set[str] = set()
    for sub in ast.walk(scope_node):
        if isinstance(sub, ast.Assign):
            for t in sub.targets:
                for nm in ast.walk(t):
                    if isinstance(nm, ast.Name) and isinstance(nm.ctx, ast.Store):
                        written.add(nm.id)
                b = _base_root_name(t)
                if b:
                    written.add(b)
        elif isinstance(sub, (ast.AugAssign, ast.AnnAssign)):
            t = sub.target
            if isinstance(t, ast.Name):
                written.add(t.id)
            else:
                b = _base_root_name(t)
                if b:
                    written.add(b)
        elif isinstance(sub, ast.For):
            for nm in ast.walk(sub.target):
                if isinstance(nm, ast.Name):
                    written.add(nm.id)
        elif isinstance(sub, ast.comprehension):
            for nm in ast.walk(sub.target):
                if isinstance(nm, ast.Name):
                    written.add(nm.id)
        elif isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute):
            if sub.func.attr in _MUTATING_METHOD_NAMES:
                b = _base_root_name(sub.func.value)
                if b:
                    written.add(b)
    return written


def _free_names(expr: ast.AST) -> set[str]:
    bound_comp: set[str] = set()
    for sub in ast.walk(expr):
        if isinstance(sub, ast.comprehension):
            for nm in ast.walk(sub.target):
                if isinstance(nm, ast.Name):
                    bound_comp.add(nm.id)
    return {
        sub.id
        for sub in ast.walk(expr)
        if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Load) and sub.id not in bound_comp
    }


def _infer_module_pure_functions(tree: ast.Module) -> set[str]:
    """Fixed-point static referential-transparency inference across top-level functions (zero function whitelist)."""
    fn_defs = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    impure: set[str] = set()
    for nm, fn in fn_defs.items():
        param_set = {a.arg for a in fn.args.args}
        for sub in ast.walk(fn):
            if isinstance(sub, (ast.Global, ast.Nonlocal, ast.Yield, ast.YieldFrom, ast.Await, ast.Delete, ast.Import, ast.ImportFrom)):
                impure.add(nm)
                break
            if isinstance(sub, ast.Attribute) and isinstance(sub.ctx, ast.Store):
                impure.add(nm)
                break
            if isinstance(sub, ast.Subscript) and isinstance(sub.ctx, ast.Store):
                b = _base_root_name(sub.value)
                if b in param_set:
                    impure.add(nm)
                    break
            if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) and sub.func.attr in _MUTATING_METHOD_NAMES:
                b = _base_root_name(sub.func.value)
                if b in param_set:
                    impure.add(nm)
                    break
            if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name) and sub.func.id in {"print", "open", "input", "exec", "eval"}:
                impure.add(nm)
                break

    pure = set(fn_defs.keys()) - impure
    changed = True
    while changed:
        changed = False
        for nm in list(pure):
            fn = fn_defs[nm]
            for sub in ast.walk(fn):
                if isinstance(sub, ast.Call):
                    if isinstance(sub.func, ast.Name):
                        cid = sub.func.id
                        if cid not in _PURE_BUILTIN_CALLABLES and cid not in pure:
                            pure.discard(nm)
                            changed = True
                            break
                    elif isinstance(sub.func, ast.Attribute):
                        if sub.func.attr not in _PURE_IMMUTABLE_METHODS and sub.func.attr not in _MUTATING_METHOD_NAMES:
                            pure.discard(nm)
                            changed = True
                            break
    return pure


def _is_pure_nontrivial_expr(expr: ast.expr, pure_fns: set[str]) -> bool:
    """Return True iff `expr` is referentially transparent AND performs super-O(1) computation worth hoisting."""
    has_work = False
    for sub in ast.walk(expr):
        if isinstance(sub, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            has_work = True
        elif isinstance(sub, ast.Call):
            if isinstance(sub.func, ast.Name):
                cid = sub.func.id
                if cid not in _PURE_BUILTIN_CALLABLES and cid not in pure_fns:
                    return False
                if cid not in _O1_SCALAR_CALLS:
                    has_work = True
            elif isinstance(sub.func, ast.Attribute):
                if sub.func.attr not in _PURE_IMMUTABLE_METHODS:
                    return False
                has_work = True
            else:
                return False
        elif isinstance(sub, (ast.Yield, ast.YieldFrom, ast.Await, ast.NamedExpr)):
            return False
    return has_work


class SelfIntrospector:
    """Evaluator-grounded Ring-1 weakness clusterer, dataflow complexity analyzer & MDL scanner."""

    @staticmethod
    def cluster_failures(episodes: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
        """Cluster failed episodes strictly by evaluator rejection signature & target organ."""
        buckets: dict[tuple[str, str, str], list[Mapping[str, Any]]] = {}
        for ep in episodes:
            if ep.get("ok") is True or ep.get("outcome_pass") is True:
                continue
            key = (
                str(ep.get("rejection_class") or ep.get("error_class") or "VERIFIER_REJECTED"),
                str(ep.get("target_relpath") or ""),
                str(ep.get("function_name") or ""),
            )
            buckets.setdefault(key, []).append(ep)

        clusters: list[dict[str, Any]] = []
        for (rej, rel, fn), rows in sorted(buckets.items(), key=lambda kv: (-len(kv[1]), kv[0])):
            dev_cases: list[Mapping[str, Any]] = []
            for r in rows:
                for c in r.get("visible_dev_cases") or []:
                    if isinstance(c, Mapping) and c not in dev_cases:
                        dev_cases.append(c)
            clusters.append(
                {
                    "rejection_class": rej,
                    "target_relpath": rel,
                    "function_name": fn,
                    "occurrences": len(rows),
                    "visible_dev_cases": dev_cases,
                }
            )
        return clusters

    @staticmethod
    def scan_ring1_hotspots(root: pathlib.Path, relpaths: Sequence[str]) -> list[dict[str, Any]]:
        """Discover superlinear Ring-1 candidates via write-set dataflow & referential-transparency laws (zero pattern checklist)."""
        hotspots: list[dict[str, Any]] = []
        for rel in relpaths:
            fp = root / rel
            if not fp.is_file():
                continue
            try:
                src = fp.read_text(encoding="utf-8")
                tree = ast.parse(src)
            except Exception:
                continue

            pure_fns = _infer_module_pure_functions(tree)
            for fn in [n for n in tree.body if isinstance(n, ast.FunctionDef)]:
                reasons: list[str] = []
                loops = [n for n in ast.walk(fn) if isinstance(n, (ast.For, ast.While))]
                for lp in loops:
                    wset = _compute_write_set(lp)
                    for st_b in lp.body:
                        for sub in ast.walk(st_b):
                            if isinstance(sub, ast.Compare) and any(isinstance(op, (ast.In, ast.NotIn)) for op in sub.ops):
                                reasons.append("loop_linear_membership_scan")
                            elif isinstance(sub, (ast.For, ast.While)):
                                reasons.append("nested_iteration_product")
                            elif isinstance(sub, ast.expr) and _is_pure_nontrivial_expr(sub, pure_fns):
                                fv = _free_names(sub)
                                if fv and not (fv & wset) and not (fv <= _PURE_BUILTIN_CALLABLES | pure_fns):
                                    reasons.append("loop_invariant_pure_computation")
                            elif isinstance(sub, ast.AugAssign) and isinstance(sub.op, ast.Add):
                                reasons.append("loop_additive_accumulation")
                if not fn.decorator_list and fn.name in pure_fns:
                    self_calls = [
                        c
                        for c in ast.walk(fn)
                        if isinstance(c, ast.Call) and isinstance(c.func, ast.Name) and c.func.id == fn.name
                    ]
                    if len(self_calls) >= 1:
                        reasons.append("unmemoized_pure_recursion")

                if reasons:
                    hotspots.append(
                        {
                            "target_relpath": rel,
                            "function_name": fn.name,
                            "mechanisms": sorted(set(reasons)),
                            "lineno": fn.lineno,
                        }
                    )
        return hotspots

    @staticmethod
    def scan_mdl_redundancies(root: pathlib.Path, relpaths: Sequence[str]) -> list[dict[str, Any]]:
        """Detect alpha-equivalent duplicate pure top-level helper functions inside a Ring-1 module."""
        redundancies: list[dict[str, Any]] = []
        for rel in relpaths:
            fp = root / rel
            if not fp.is_file():
                continue
            try:
                tree = ast.parse(fp.read_text(encoding="utf-8"))
            except Exception:
                continue
            sig_map: dict[str, list[ast.FunctionDef]] = {}
            for node in tree.body:
                if not isinstance(node, ast.FunctionDef) or node.decorator_list:
                    continue
                cloned = copy.deepcopy(node)
                arg_map = {a.arg: f"_p{i}" for i, a in enumerate(cloned.args.args)}
                for a in cloned.args.args:
                    a.arg = arg_map[a.arg]
                cloned.name = "_canon"
                for sub in ast.walk(cloned):
                    if isinstance(sub, ast.Name) and sub.id in arg_map:
                        sub.id = arg_map[sub.id]
                key = ast.dump(cloned, include_attributes=False)
                sig_map.setdefault(key, []).append(node)
            for funcs in sig_map.values():
                if len(funcs) >= 2 and len(ast.unparse(funcs[0])) >= 60:
                    redundancies.append(
                        {
                            "target_relpath": rel,
                            "canonical_fn": funcs[0].name,
                            "duplicate_fns": [f.name for f in funcs[1:]],
                        }
                    )
        return redundancies


# ---------------------------------------------------------------------------
# Law 3: 5 White-Box Self-Code Evolution Operators + MAP-Elites Archive
# ---------------------------------------------------------------------------


def _lower_function_via_semantic_dataflow(fn_orig: ast.FunctionDef, pure_fns: set[str], tree_orig: ast.Module) -> list[tuple[ast.Module, str]]:
    """Apply universal write-set dataflow & relational algebra laws (`for` + `while`, zero pattern checklist)."""
    candidates: list[tuple[ast.Module, str]] = []

    # --- Law A: Write-Set Loop Lowering (LICM + Invariant Set Index + Append-Only Shadow Set + Equijoin) ---
    tree_a = copy.deepcopy(tree_orig)
    fn_a = next((n for n in tree_a.body if isinstance(n, ast.FunctionDef) and n.name == fn_orig.name), None)
    if fn_a is not None:
        applied_laws: list[str] = []

        empty_list_vars: dict[str, int] = {}
        for idx_s, st in enumerate(fn_a.body):
            if isinstance(st, ast.Assign) and len(st.targets) == 1 and isinstance(st.targets[0], ast.Name):
                if isinstance(st.value, ast.List) and not st.value.elts:
                    empty_list_vars[st.targets[0].id] = idx_s

        def _is_append_only_list(var_nm: str, scope: ast.AST) -> bool:
            if var_nm not in empty_list_vars:
                return False
            assign_count = 0
            for sub in ast.walk(scope):
                if isinstance(sub, ast.Assign) and any(isinstance(t, ast.Name) and t.id == var_nm for t in sub.targets):
                    assign_count += 1
                elif isinstance(sub, (ast.AugAssign, ast.AnnAssign)) and isinstance(sub.target, ast.Name) and sub.target.id == var_nm:
                    return False
                elif isinstance(sub, ast.Subscript) and isinstance(sub.ctx, ast.Store) and _base_root_name(sub.value) == var_nm:
                    return False
                elif isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) and _base_root_name(sub.func.value) == var_nm:
                    if sub.func.attr != "append" or len(sub.args) != 1 or sub.keywords:
                        return False
            return assign_count <= 1

        shadow_helpers_needed: set[str] = set()
        invariant_sets_needed: dict[str, str] = {}
        new_top_stmts: list[ast.stmt] = []

        for st in fn_a.body:
            if not isinstance(st, (ast.For, ast.While)):
                new_top_stmts.append(st)
                continue

            outer_wset = _compute_write_set(st)
            pre_loop_stmts: list[ast.stmt] = []

            def _factor_nested_equijoins(stmt_list: list[ast.stmt], outer_w: set[str]) -> list[ast.stmt]:
                out_s: list[ast.stmt] = []
                for inner_st in stmt_list:
                    if isinstance(inner_st, ast.For) and isinstance(inner_st.target, ast.Name):
                        v_nm = inner_st.target.id
                        iter_fv = _free_names(inner_st.iter)
                        if not (iter_fv & outer_w) and inner_st.body and isinstance(inner_st.body[0], ast.If) and not inner_st.body[0].orelse:
                            iff = inner_st.body[0]
                            conjuncts = iff.test.values if isinstance(iff.test, ast.BoolOp) and isinstance(iff.test.op, ast.And) else [iff.test]
                            join_pair: tuple[ast.expr, ast.expr, int] | None = None
                            for c_idx, cj in enumerate(conjuncts):
                                if isinstance(cj, ast.Compare) and len(cj.ops) == 1 and isinstance(cj.ops[0], ast.Eq):
                                    l_fv = _free_names(cj.left)
                                    r_fv = _free_names(cj.comparators[0])
                                    if v_nm in r_fv and v_nm not in l_fv and not (r_fv & (outer_w - {v_nm})):
                                        join_pair = (cj.left, cj.comparators[0], c_idx)
                                        break
                                    if v_nm in l_fv and v_nm not in r_fv and not (l_fv & (outer_w - {v_nm})):
                                        join_pair = (cj.comparators[0], cj.left, c_idx)
                                        break
                            if join_pair is not None:
                                u_key_e, v_key_e, used_idx = join_pair
                                idx_var = f"_jidx_{v_nm}_{len(pre_loop_stmts)}"
                                iter_src = ast.unparse(inner_st.iter)
                                v_key_src = ast.unparse(v_key_e)
                                u_key_src = ast.unparse(u_key_e)
                                pre_loop_stmts.extend(
                                    ast.parse(
                                        f"{idx_var} = {{}}\n"
                                        f"for {v_nm} in {iter_src}:\n"
                                        f"    {idx_var}.setdefault({v_key_src}, []).append({v_nm})\n"
                                    ).body
                                )
                                rem_conj = [cj for k, cj in enumerate(conjuncts) if k != used_idx]
                                inner_body = iff.body + inner_st.body[1:]
                                if rem_conj:
                                    rem_test = rem_conj[0] if len(rem_conj) == 1 else ast.BoolOp(op=ast.And(), values=rem_conj)
                                    inner_body = [ast.If(test=rem_test, body=iff.body, orelse=[])] + inner_st.body[1:]
                                repl_for = ast.For(
                                    target=ast.Name(id=v_nm, ctx=ast.Store()),
                                    iter=ast.parse(f"{idx_var}.get({u_key_src}, ())", mode="eval").body,
                                    body=inner_body,
                                    orelse=[],
                                )
                                applied_laws.append("equijoin_hash_index")
                                out_s.append(repl_for)
                                continue
                    out_s.append(inner_st)
                return out_s

            st.body = _factor_nested_equijoins(st.body, outer_wset)
            outer_wset = _compute_write_set(st)

            for sub in ast.walk(st):
                if isinstance(sub, ast.Compare) and len(sub.ops) == 1 and isinstance(sub.ops[0], (ast.In, ast.NotIn)):
                    if isinstance(sub.comparators[0], ast.Name):
                        rhs_id = sub.comparators[0].id
                        if rhs_id not in outer_wset and not rhs_id.startswith(("_set_", "_seen_", "_jidx_")):
                            invariant_sets_needed.setdefault(rhs_id, f"_set_{rhs_id}")
                            applied_laws.append("invariant_membership_set")
                        elif _is_append_only_list(rhs_id, fn_a):
                            shadow_helpers_needed.add(rhs_id)
                            applied_laws.append("append_only_shadow_set")

            licm_map: dict[str, str] = {}
            licm_stmts_final: list[ast.stmt] = []

            class _FinalPassTransformer(ast.NodeTransformer):
                def visit_Compare(self, c_nd: ast.Compare) -> ast.AST:
                    self.generic_visit(c_nd)
                    if len(c_nd.ops) == 1 and isinstance(c_nd.ops[0], (ast.In, ast.NotIn)) and isinstance(c_nd.comparators[0], ast.Name):
                        rhs_id = c_nd.comparators[0].id
                        is_not_in = isinstance(c_nd.ops[0], ast.NotIn)
                        if rhs_id in invariant_sets_needed:
                            c_nd.comparators[0] = ast.Name(id=invariant_sets_needed[rhs_id], ctx=ast.Load())
                            return c_nd
                        if rhs_id in shadow_helpers_needed:
                            chk_call = ast.Call(
                                func=ast.Name(id=f"_has_{rhs_id}", ctx=ast.Load()),
                                args=[c_nd.left],
                                keywords=[],
                            )
                            return ast.UnaryOp(op=ast.Not(), operand=chk_call) if is_not_in else chk_call
                    return c_nd

                def visit_Call(self, call_nd: ast.Call) -> ast.AST:
                    if (
                        isinstance(call_nd.func, ast.Attribute)
                        and call_nd.func.attr == "append"
                        and isinstance(call_nd.func.value, ast.Name)
                        and call_nd.func.value.id in shadow_helpers_needed
                        and len(call_nd.args) == 1
                        and not call_nd.keywords
                    ):
                        call_nd.args = [self.visit(call_nd.args[0])]
                        return ast.Call(
                            func=ast.Name(id=f"_add_{call_nd.func.value.id}", ctx=ast.Load()),
                            args=call_nd.args,
                            keywords=[],
                        )
                    if _is_pure_nontrivial_expr(call_nd, pure_fns):
                        fv = _free_names(call_nd)
                        non_fn_fv = fv - (_PURE_BUILTIN_CALLABLES | pure_fns)
                        if non_fn_fv and not (fv & outer_wset):
                            src_k = ast.unparse(call_nd)
                            h_nm = licm_map.get(src_k)
                            if h_nm is None:
                                h_nm = f"_licm_{len(licm_map)}"
                                licm_map[src_k] = h_nm
                                licm_stmts_final.extend(ast.parse(f"{h_nm} = {src_k}\n").body)
                                applied_laws.append("write_set_licm")
                            return ast.Name(id=h_nm, ctx=ast.Load())
                    return self.generic_visit(call_nd)

                def visit_ListComp(self, lc_nd: ast.ListComp) -> ast.AST:
                    if _is_pure_nontrivial_expr(lc_nd, pure_fns):
                        fv = _free_names(lc_nd)
                        non_fn_fv = fv - (_PURE_BUILTIN_CALLABLES | pure_fns)
                        if non_fn_fv and not (fv & outer_wset):
                            src_k = ast.unparse(lc_nd)
                            h_nm = licm_map.get(src_k)
                            if h_nm is None:
                                h_nm = f"_licm_{len(licm_map)}"
                                licm_map[src_k] = h_nm
                                licm_stmts_final.extend(ast.parse(f"{h_nm} = {src_k}\n").body)
                                applied_laws.append("write_set_licm_comp")
                            return ast.Name(id=h_nm, ctx=ast.Load())
                    return self.generic_visit(lc_nd)

            if isinstance(st, ast.For):
                st.body = [_FinalPassTransformer().visit(b) for b in st.body]
            else:
                st.test = _FinalPassTransformer().visit(st.test)
                st.body = [_FinalPassTransformer().visit(b) for b in st.body]

            new_top_stmts.extend(pre_loop_stmts)
            new_top_stmts.extend(licm_stmts_final)
            new_top_stmts.append(st)

        if shadow_helpers_needed or invariant_sets_needed or applied_laws:
            final_body: list[ast.stmt] = []
            doc_offset = 1 if (
                new_top_stmts
                and isinstance(new_top_stmts[0], ast.Expr)
                and isinstance(new_top_stmts[0].value, ast.Constant)
                and isinstance(new_top_stmts[0].value.value, str)
            ) else 0
            final_body.extend(new_top_stmts[:doc_offset])
            for orig_c, set_nm in sorted(invariant_sets_needed.items()):
                final_body.extend(
                    ast.parse(f"try:\n    {set_nm} = set({orig_c})\nexcept TypeError:\n    {set_nm} = {orig_c}\n").body
                )
            for b_st in new_top_stmts[doc_offset:]:
                final_body.append(b_st)
                if (
                    isinstance(b_st, ast.Assign)
                    and len(b_st.targets) == 1
                    and isinstance(b_st.targets[0], ast.Name)
                    and b_st.targets[0].id in shadow_helpers_needed
                ):
                    acc = b_st.targets[0].id
                    final_body.extend(
                        ast.parse(
                            f"_seen_{acc} = set()\n"
                            f"_unh_{acc} = []\n"
                            f"def _has_{acc}(_v):\n"
                            f"    try:\n        return _v in _seen_{acc}\n"
                            f"    except TypeError:\n        return _v in _unh_{acc}\n"
                            f"def _add_{acc}(_v):\n"
                            f"    try:\n        _seen_{acc}.add(_v)\n"
                            f"    except TypeError:\n        _unh_{acc}.append(_v)\n"
                            f"    {acc}.append(_v)\n"
                        ).body
                    )
            fn_a.body = final_body
            ast.fix_missing_locations(tree_a)
            candidates.append((tree_a, "+".join(sorted(set(applied_laws)))))

    # --- Law B: Referential-Transparency Memoization ---
    if not fn_orig.decorator_list and fn_orig.name in pure_fns:
        self_calls = [
            c for c in ast.walk(fn_orig) if isinstance(c, ast.Call) and isinstance(c.func, ast.Name) and c.func.id == fn_orig.name
        ]
        if self_calls:
            tree_b1 = copy.deepcopy(tree_orig)
            if not any(isinstance(n, ast.Import) and any(a.name == "functools" for a in n.names) for n in tree_b1.body):
                tree_b1.body.insert(0, ast.Import(names=[ast.alias(name="functools")]))
            for fn_b1 in [n for n in tree_b1.body if isinstance(n, ast.FunctionDef) and n.name == fn_orig.name]:
                fn_b1.decorator_list.insert(
                    0,
                    ast.Call(
                        func=ast.Attribute(value=ast.Name(id="functools", ctx=ast.Load()), attr="lru_cache", ctx=ast.Load()),
                        args=[],
                        keywords=[ast.keyword(arg="maxsize", value=ast.Constant(value=4096))],
                    ),
                )
            ast.fix_missing_locations(tree_b1)
            candidates.append((tree_b1, "referential_transparency_memoization"))

    # --- Law C: Trace-to-HORS Algorithmic Re-Synthesis (turns O(N^3) brute-force / exponential search into O(N) DP/Fold) ---
    if not candidates and fn_orig.name in pure_fns and 1 <= len(fn_orig.args.args) <= 2 and not fn_orig.args.vararg and not fn_orig.args.kwarg:
        p_names = [a.arg for a in fn_orig.args.args]
        probe_suites = _synthesize_ast_derived_probe_suites(fn_orig)
        for suite in probe_suites:
            harvested: list[tuple[tuple[Any, ...], Any]] = []
            ok_suite = True
            for row in suite:
                row_t = row if isinstance(row, tuple) else (row,)
                try:
                    out_v = eval_pure_ast_function(fn_orig, row_t, max_steps=15_000)
                except Exception:
                    ok_suite = False
                    break
                harvested.append((row_t, out_v))
            if ok_suite and len(harvested) >= 3:
                hors_src = synthesize_python_function_body(p_names, harvested, max_weight=3)
                if isinstance(hors_src, str) and ("for " in hors_src or "_dp" in hors_src):
                    tree_c = copy.deepcopy(tree_orig)
                    for idx_f, nd_f in enumerate(tree_c.body):
                        if isinstance(nd_f, ast.FunctionDef) and nd_f.name == fn_orig.name:
                            repl_fn = ast.parse(
                                f"def {fn_orig.name}({ast.unparse(fn_orig.args)}):\n"
                                + "\n".join("    " + ln for ln in hors_src.splitlines())
                                + "\n"
                            ).body[0]
                            if isinstance(repl_fn, ast.FunctionDef):
                                tree_c.body[idx_f] = repl_fn
                                ast.fix_missing_locations(tree_c)
                                candidates.append((tree_c, "trace_to_hors_resynthesis"))
                    break

    return candidates


def _synthesize_ast_derived_probe_suites(fn_node: ast.FunctionDef) -> list[list[tuple[Any, ...]]]:
    """Derive boundary & algebraic probe input suites directly from `fn_node` AST structure (zero benchmark literals)."""
    arity = len(fn_node.args.args)
    int_consts: list[int] = []
    has_subscript = False
    has_len_or_range = False
    for sub in ast.walk(fn_node):
        if isinstance(sub, ast.Constant) and isinstance(sub.value, int) and not isinstance(sub.value, bool):
            if -20 <= sub.value <= 20 and sub.value not in int_consts:
                int_consts.append(sub.value)
        elif isinstance(sub, ast.Subscript):
            has_subscript = True
        elif isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name) and sub.func.id in {"len", "range"}:
            has_len_or_range = True

    # Deterministic boundary generator over AST constants (`c - 1, c, c + 1`) + algebraic progression
    b_seed = sorted({0, 1, -1, 2, -2, *(c for v in int_consts[:3] for c in (v - 1, v, v + 1))})
    suites: list[list[tuple[Any, ...]]] = []

    if arity == 1:
        # Signed integer sequence generators (empty, all-negative, alternating, positive-dominated)
        seq_signed = [
            ([],),
            ([-3, -1],),
            ([((k * 5) % 11) - 5 for k in range(1, 9)],),
            ([((k * 3) % 7) - 1 for k in range(1, 7)],),
            ([2, -1, 4, -2, 3],),
        ]
        seq_dups = [
            ([],),
            ([((k * 3) % 4) + 1 for k in range(6)],),
            ([b_seed[k % len(b_seed)] for k in range(5)],),
        ]
        nat_indices = [(n,) for n in range(7)]
        if has_subscript or has_len_or_range:
            suites.extend([seq_signed, seq_dups, nat_indices])
        else:
            suites.extend([nat_indices, seq_signed, seq_dups])
    elif arity == 2:
        # (a) Positive step weights + bounded target capacity probes
        cap_probes = [
            ([1, 2, 4], 7),
            ([2], 3),
            ([1, 3], 5),
            ([2, 4], 0),
        ]
        # (b) Combinatorial symbol sequences over 3-letter alphabet `('a', 'b', 'c')`
        alpha_probes = [
            ("", "ab"),
            ("abc", "abc"),
            ("abca", "acba"),
            ("aab", "aba"),
        ]
        suites.extend([cap_probes, alpha_probes])
    return suites


def propose_complexity_reduction_patches(
    root: pathlib.Path,
    hotspots: Sequence[Mapping[str, Any]],
    *,
    max_proposals: int = 4,
) -> list[SelfPatchProposal]:
    """Operator 1: Synthesize complexity lowerings via Write-Set Dataflow, Collision Memoization & Trace-to-HORS."""
    proposals: list[SelfPatchProposal] = []
    seen_targets: set[tuple[str, str]] = set()
    for hs in hotspots:
        if len(proposals) >= max_proposals:
            break
        rel = str(hs.get("target_relpath") or "")
        fn_name = str(hs.get("function_name") or "")
        if not rel or not fn_name or (rel, fn_name) in seen_targets:
            continue
        fp = root / rel
        if not fp.is_file():
            continue
        before_src = fp.read_text(encoding="utf-8")
        base_sha = _sha256_bytes(fp.read_bytes())
        try:
            tree = ast.parse(before_src)
        except SyntaxError:
            continue

        pure_fns = _infer_module_pure_functions(tree)
        fn_node = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == fn_name), None)
        if fn_node is None:
            continue

        lowered_cands = _lower_function_via_semantic_dataflow(fn_node, pure_fns, tree)
        seen_targets.add((rel, fn_name))
        for cand_tree, law_label in lowered_cands:
            if len(proposals) >= max_proposals:
                break
            after_src = ast.unparse(cand_tree) + "\n"
            if after_src == before_src:
                continue
            udiff = make_unified_diff(rel, before_src, after_src)
            if not udiff:
                continue
            proposals.append(
                SelfPatchProposal(
                    proposal_id="prop_speed_" + _sha256_text(udiff)[:12],
                    operator_id="OP1_COMPLEXITY_REDUCTION",
                    target_relpath=rel,
                    function_name=fn_name,
                    before_source=before_src,
                    after_source=after_src,
                    unified_diff=udiff,
                    base_sha256_by_path={rel: base_sha},
                    rationale=f"Lower {fn_name} asymptotic complexity via semantic law `{law_label}`.",
                    improvement_axis="complexity_speedup",
                    metadata={"semantic_law": law_label, "mechanisms": list(hs.get("mechanisms") or [])},
                )
            )
    return proposals


def _synthesize_empirical_ast_catamorphism(
    fn_node: ast.FunctionDef,
    dev_cases: Sequence[Mapping[str, Any]],
) -> ast.FunctionDef | None:
    """Synthesize a programmatic AST structural catamorphism via `discover_ast_operator_morphisms` (zero string templates)."""
    if len(fn_node.args.args) < 1:
        return None
    str_expr_cases = [
        c
        for c in dev_cases
        if isinstance(c.get("args"), (list, tuple))
        and len(c["args"]) >= 1
        and isinstance(c["args"][0], str)
        and "expected" in c
        and not c.get("raises")
    ]
    if len(str_expr_cases) < 2:
        return None

    has_bitwise = False
    for c in str_expr_cases:
        raw_expr = str(c["args"][0]).strip()
        raw_env = dict(c["args"][1]) if len(c["args"]) >= 2 and isinstance(c["args"][1], Mapping) else {}
        try:
            parsed_dev = ast.parse(raw_expr, mode="eval")
            if any(isinstance(sub, (ast.BitAnd, ast.BitOr, ast.BitXor, ast.RShift, ast.Invert)) for sub in ast.walk(parsed_dev)):
                has_bitwise = True
            denot = eval_pure_ast_expr(parsed_dev, raw_env)
        except ZeroDivisionError:
            denot = 0
        except Exception:
            return None
        if denot != c.get("expected"):
            return None

    arg0 = fn_node.args.args[0].arg
    env_arg = fn_node.args.args[1].arg if len(fn_node.args.args) >= 2 else None
    new_body = build_programmatic_ast_catamorphism_stmts(arg0, env_arg, has_bitwise=has_bitwise)
    out_fn = ast.FunctionDef(
        name=fn_node.name,
        args=copy.deepcopy(fn_node.args),
        body=new_body,
        decorator_list=[],
        returns=copy.deepcopy(fn_node.returns),
    )
    ast.fix_missing_locations(out_fn)
    return out_fn


def propose_functional_upgrade_patches(
    root: pathlib.Path,
    failure_clusters: Sequence[Mapping[str, Any]],
    *,
    max_proposals: int = 4,
    concept_library: CompoundingConceptLibrary | None = None,
) -> list[SelfPatchProposal]:
    """Operator 2: Synthesize general Ring-1 AST upgrades from visible dev failure clusters ONLY.

    Strictly blinded to `sealed_heldout_cases` (`PROOF_CARRYING_SHADOW_REALITY_POLICY_V2`):
    consumes only `cluster["visible_dev_cases"]` and screens candidates inside a CoW
    Zygote workspace before submitting within `ProposalBudgetEnvelope`.
    """
    proposals: list[SelfPatchProposal] = []
    for cluster in failure_clusters:
        if len(proposals) >= max_proposals:
            break
        rel = str(cluster.get("target_relpath") or "")
        fn_name = str(cluster.get("function_name") or "")
        dev_cases = list(cluster.get("visible_dev_cases") or [])
        fp = root / rel
        if not rel or not fn_name or not dev_cases or not fp.is_file():
            continue

        before_src = fp.read_text(encoding="utf-8")
        base_sha = _sha256_bytes(fp.read_bytes())
        try:
            base_tree = ast.parse(before_src)
        except SyntaxError:
            continue

        candidate_sources: list[tuple[str, str]] = []

        # Sub-operator 2A: Empirical `ast` x `operator` structural catamorphism discovery
        for idx, nd in enumerate(base_tree.body):
            if isinstance(nd, ast.FunctionDef) and nd.name == fn_name:
                cata_fn = _synthesize_empirical_ast_catamorphism(nd, dev_cases)
                if cata_fn is not None:
                    t_copy = copy.deepcopy(base_tree)
                    t_copy.body[idx] = cata_fn
                    ast.fix_missing_locations(t_copy)
                    candidate_sources.append((ast.unparse(t_copy) + "\n", "empirical_ast_operator_catamorphism"))

        # Sub-operator 2B: Live Bottom-Up Observational + Concept-Library (G_t) + STUN Synthesis
        io_examples: list[tuple[tuple[Any, ...], Any]] = [
            (tuple(c.get("args") or ()), c.get("expected"))
            for c in dev_cases
            if "expected" in c and not c.get("raises") and isinstance(c.get("args"), (list, tuple))
        ]
        if io_examples:
            for idx, nd in enumerate(base_tree.body):
                if isinstance(nd, ast.FunctionDef) and nd.name == fn_name:
                    param_names = [a.arg for a in nd.args.args]
                    if all(len(ex_in) == len(param_names) for ex_in, _ in io_examples):
                        # Harvest domain constants from existing function AST + dev inputs
                        extra_consts: list[Any] = [
                            sub.value
                            for sub in ast.walk(nd)
                            if isinstance(sub, ast.Constant) and isinstance(sub.value, (int, float, str)) and not isinstance(sub.value, bool)
                        ]
                        stmt_body = synthesize_python_function_body(
                            param_names,
                            io_examples,
                            extra_constants=extra_consts,
                            max_weight=4,
                            concept_library=concept_library,
                        )
                        if isinstance(stmt_body, str) and stmt_body.strip():
                            wrapped_fn = ast.parse(
                                f"def {fn_name}({ast.unparse(nd.args)}):\n"
                                + "\n".join("    " + ln for ln in stmt_body.splitlines())
                                + "\n"
                            ).body[0]
                            if isinstance(wrapped_fn, ast.FunctionDef):
                                t_copy = copy.deepcopy(base_tree)
                                t_copy.body[idx] = wrapped_fn
                                ast.fix_missing_locations(t_copy)
                                candidate_sources.append((ast.unparse(t_copy) + "\n", "observational_concept_library_synthesis"))

        # Sub-operator 2C: Test-guided AST repair search (`python_test_guided_patch_search_v1`)
        try:
            from canonical.runtime.bound_capabilities import python_test_guided_patch_search_v1 as tgps

            for spec in tgps._candidate_specs(before_src)[:12]:
                cand_txt = str(spec.get("patched_source") or "")
                if cand_txt and cand_txt != before_src:
                    candidate_sources.append((cand_txt, f"ast_patch_search:{spec.get('kind', 'edit')}"))
        except Exception:
            pass

        if not candidate_sources:
            continue

        # Screen candidates strictly on `visible_dev_cases` inside confined CoW Zygote
        mod_import = rel[:-3].replace("/", ".")
        dev_test_src = Ring0SelfReferee._build_sealed_heldout_test_source(mod_import, fn_name, dev_cases)
        with tempfile.TemporaryDirectory(prefix="brain-op2-dev-") as td:
            dev_ws = pathlib.Path(td) / "ws"
            create_zero_copy_cow_workspace(root, dev_ws)
            cow_write_text(dev_ws / "_test_visible_dev.py", dev_test_src)
            batch_srcs = [s for s, _ in candidate_sources]
            res = broker.run_confined_python_candidate_batch(
                dev_ws,
                rel,
                ["_test_visible_dev.py"],
                batch_srcs,
                stop_on_first_pass=True,
                per_candidate_timeout_s=3.0,
            )
            for pass_idx in res.get("passing_indices") or []:
                after_src, reason = candidate_sources[int(pass_idx)]
                if input_dep_gate.gate(before_src, after_src).get("status") != input_dep_gate.PASS:
                    continue
                udiff = make_unified_diff(rel, before_src, after_src)
                if not udiff:
                    continue
                proposals.append(
                    SelfPatchProposal(
                        proposal_id="prop_func_" + _sha256_text(udiff)[:12],
                        operator_id="OP2_FUNCTIONAL_GENERALIZATION",
                        target_relpath=rel,
                        function_name=fn_name,
                        before_source=before_src,
                        after_source=after_src,
                        unified_diff=udiff,
                        base_sha256_by_path={rel: base_sha},
                        rationale=f"Generalize {fn_name} via {reason} on {len(dev_cases)} visible dev failures.",
                        improvement_axis="accuracy",
                        metadata={"synthesis_mechanism": reason, "dev_case_count": len(dev_cases)},
                    )
                )
                break
    return proposals


def propose_mdl_compression_patches(
    root: pathlib.Path,
    redundancies: Sequence[Mapping[str, Any]],
    *,
    max_proposals: int = 2,
) -> list[SelfPatchProposal]:
    """Operator 4: Factor alpha-equivalent duplicate pure helpers to shrink executable bytes (`Delta B_exec < 0`)."""
    proposals: list[SelfPatchProposal] = []
    for red in redundancies:
        if len(proposals) >= max_proposals:
            break
        rel = str(red.get("target_relpath") or "")
        canon_fn = str(red.get("canonical_fn") or "")
        dup_fns = set(red.get("duplicate_fns") or [])
        fp = root / rel
        if not rel or not canon_fn or not dup_fns or not fp.is_file():
            continue
        before_src = fp.read_text(encoding="utf-8")
        base_sha = _sha256_bytes(fp.read_bytes())
        try:
            tree = ast.parse(before_src)
        except SyntaxError:
            continue

        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name in dup_fns:
                call_args = [ast.Name(id=a.arg, ctx=ast.Load()) for a in node.args.args]
                node.body = [
                    ast.Return(
                        value=ast.Call(
                            func=ast.Name(id=canon_fn, ctx=ast.Load()),
                            args=call_args,
                            keywords=[],
                        )
                    )
                ]
        ast.fix_missing_locations(tree)
        after_src = ast.unparse(tree) + "\n"
        if executable_byte_measure(after_src) >= executable_byte_measure(before_src):
            continue
        udiff = make_unified_diff(rel, before_src, after_src)
        if not udiff:
            continue
        proposals.append(
            SelfPatchProposal(
                proposal_id="prop_mdl_" + _sha256_text(udiff)[:12],
                operator_id="OP4_MDL_AST_COMPRESSION",
                target_relpath=rel,
                function_name=canon_fn,
                before_source=before_src,
                after_source=after_src,
                unified_diff=udiff,
                base_sha256_by_path={rel: base_sha},
                rationale=f"Factor duplicate helper(s) {sorted(dup_fns)} into canonical {canon_fn} (Delta B_exec < 0).",
                improvement_axis="mdl_compression",
                metadata={"duplicates_folded": sorted(dup_fns)},
            )
        )
    return proposals


def forge_verified_organ_bridge(
    *,
    capability_id: str,
    source_code: str,
    demonstration_inputs: Mapping[str, Any],
    heldout_inputs: Mapping[str, Any],
    registry_dir: pathlib.Path,
    workspace_root: pathlib.Path | None = None,
) -> dict[str, Any]:
    """Operator 3: Forge and kill-verify a new Ring-1 organ bridge via `capability_forge_v1.forge` (`require_kill=True`)."""
    registry_dir = pathlib.Path(registry_dir).resolve()
    adapters_dir = registry_dir / "adapters"
    work_dir = pathlib.Path(workspace_root).resolve() if workspace_root is not None else (registry_dir / "workspace")
    adapters_dir.mkdir(parents=True, exist_ok=True)
    work_dir.mkdir(parents=True, exist_ok=True)

    mod_slug = re.sub(r"[^a-zA-Z0-9_]", "_", capability_id).strip("_") or "forged_organ"
    mod_file = adapters_dir / f"{mod_slug}.py"
    mod_file.write_text(source_code, encoding="utf-8")

    cases = [dict(demonstration_inputs), dict(heldout_inputs)]
    orig_adapters = capability_forge_v1.ADAPTERS
    orig_state = capability_forge_v1.STATE
    try:
        capability_forge_v1.ADAPTERS = adapters_dir
        capability_forge_v1.STATE = registry_dir / "forged_capabilities_v1.json"
        report = capability_forge_v1.forge(mod_slug, cases, root=work_dir, require_kill=True)
        registered_id: str | None = None
        if report.get("admitted") is True:
            reg_out = capability_forge_v1.register(mod_slug, report.get("contract") or {}, cases)
            registered_id = reg_out.get("capability_id") if isinstance(reg_out, Mapping) else f"forged.{mod_slug}"
        return {
            "schema": SCHEMA + "/forged_organ_bridge",
            "ok": bool(report.get("admitted")),
            "admitted": bool(report.get("admitted")),
            "module": mod_slug,
            "capability_id": registered_id or capability_id,
            "contract": report.get("contract"),
            "checks": report.get("checks"),
            "reasons": list(report.get("reasons") or []),
            "adapter_path": str(mod_file),
            "model_dependency_count": 0,
        }
    finally:
        capability_forge_v1.ADAPTERS = orig_adapters
        capability_forge_v1.STATE = orig_state


def _compute_ast_behavioral_descriptor(source_or_diff: str) -> dict[str, Any]:
    """Compute structural MAP-Elites behavioral coordinates `(loop_depth_bin, uses_memo_or_index)`."""
    added_lines: list[str] = []
    for ln in source_or_diff.splitlines():
        if ln.startswith("+") and not ln.startswith("+++"):
            added_lines.append(ln[1:])
    snippet = "\n".join(added_lines) if added_lines else source_or_diff
    max_loop_depth = 0
    uses_memo_or_index = False
    try:
        mod = ast.parse(snippet)

        def _depth(node: ast.AST, cur: int) -> int:
            nxt = cur + (1 if isinstance(node, (ast.For, ast.While, ast.ListComp, ast.SetComp, ast.DictComp)) else 0)
            best = nxt
            for ch in ast.iter_child_nodes(node):
                best = max(best, _depth(ch, nxt))
            return best

        max_loop_depth = _depth(mod, 0)
        for nd in ast.walk(mod):
            if isinstance(nd, (ast.Set, ast.Dict)):
                uses_memo_or_index = True
            elif isinstance(nd, ast.Call):
                if isinstance(nd.func, ast.Name) and nd.func.id in {"set", "dict"}:
                    uses_memo_or_index = True
                elif isinstance(nd.func, ast.Attribute) and nd.func.attr in {"lru_cache", "cache", "setdefault"}:
                    uses_memo_or_index = True
            elif isinstance(nd, ast.Name) and nd.id.startswith("concept_"):
                uses_memo_or_index = True
    except SyntaxError:
        uses_memo_or_index = any(tok in snippet for tok in ("lru_cache", "set(", "_dp", "concept_"))
        max_loop_depth = 1 if "for " in snippet else 0

    depth_bin = "d0" if max_loop_depth == 0 else ("d1" if max_loop_depth == 1 else "d2plus")
    return {
        "loop_depth": max_loop_depth,
        "loop_depth_bin": depth_bin,
        "uses_memo_or_index": uses_memo_or_index,
        "index_bin": "indexed" if uses_memo_or_index else "direct",
    }


class QualityDiversitySelfArchive:
    """Operator 5: Full MAP-Elites Quality-Diversity self-lineage archive over behavioral coordinates."""

    def __init__(self, archive_path: pathlib.Path) -> None:
        self.archive_path = pathlib.Path(archive_path)
        self.archive_path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict[str, Any]:
        if self.archive_path.is_file():
            try:
                data = json.loads(self.archive_path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data
            except Exception:
                pass
        return {"schema": SCHEMA, "cells": {}}

    def record_promoted(self, commit_record: Mapping[str, Any], *, patch_text: str = "") -> dict[str, Any]:
        state = self._load()
        cells = state.setdefault("cells", {})
        rel = str(commit_record.get("target_relpath") or "ring1")
        axis = str(commit_record.get("improvement_axis") or "accuracy")
        delta_b = int(commit_record.get("delta_exec_bytes") or 0)
        size_bin = "shrunk" if delta_b < 0 else ("compact" if delta_b <= 80 else "expanded")
        b_desc = _compute_ast_behavioral_descriptor(patch_text or str(commit_record.get("unified_diff") or ""))
        cell_key = f"{rel}::{axis}::{size_bin}::{b_desc['loop_depth_bin']}::{b_desc['index_bin']}"

        score = float((commit_record.get("e_process") or {}).get("e_value") or 1.0)
        if commit_record.get("speed_report"):
            score *= float(commit_record["speed_report"].get("median_speedup") or 1.0)

        incumbent = cells.get(cell_key)
        replaced = incumbent is None or score >= float(incumbent.get("qd_score") or 0.0)
        if replaced:
            cells[cell_key] = {
                "receipt_id": commit_record.get("receipt_id"),
                "operator_id": commit_record.get("operator_id"),
                "function_name": commit_record.get("function_name"),
                "target_relpath": rel,
                "improvement_axis": axis,
                "delta_exec_bytes": delta_b,
                "behavioral_descriptor": b_desc,
                "qd_score": round(score, 4),
            }
            tmp = self.archive_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            tmp.replace(self.archive_path)
        return {
            "cell_key": cell_key,
            "behavioral_descriptor": b_desc,
            "replaced_incumbent": replaced,
            "total_elites": len(cells),
        }

    def select_stepping_stone_elites(self, *, limit: int = 4) -> list[dict[str, Any]]:
        """Return diverse elite stepping stones across distinct `(axis, loop_depth_bin, index_bin)` niches."""
        cells = self._load().get("cells") or {}
        ranked = sorted(
            ((str(k), dict(v)) for k, v in cells.items() if isinstance(v, Mapping)),
            key=lambda kv: (-float(kv[1].get("qd_score") or 0.0), kv[0]),
        )
        chosen: list[dict[str, Any]] = []
        seen_niches: set[tuple[str, str, str]] = set()
        for k, rec in ranked:
            bd = rec.get("behavioral_descriptor") or {}
            niche = (
                str(rec.get("improvement_axis") or ""),
                str(bd.get("loop_depth_bin") or ""),
                str(bd.get("index_bin") or ""),
            )
            if niche in seen_niches and len(chosen) + (len(ranked) - len(chosen)) > limit:
                continue
            seen_niches.add(niche)
            chosen.append({"cell_key": k, **rec})
            if len(chosen) >= limit:
                break
        return chosen


# ---------------------------------------------------------------------------
# Top-Level Sovereign Orchestrator: RecursiveSelfArchitect
# ---------------------------------------------------------------------------


class RecursiveSelfArchitect:
    """Autonomous Ring-1 self-inspection, bounded proposal synthesis & Ring-0 refereed evolution."""

    def __init__(
        self,
        state_dir: pathlib.Path,
        *,
        allowed_mutable_prefixes: Sequence[str] | None = None,
        budget: ProposalBudgetEnvelope | None = None,
        concept_library: CompoundingConceptLibrary | None = None,
    ) -> None:
        self.state_dir = pathlib.Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.budget = budget or ProposalBudgetEnvelope()
        self.firewall = (
            SelfPatchFirewall(allowed_mutable_prefixes=allowed_mutable_prefixes)
            if allowed_mutable_prefixes is not None
            else SelfPatchFirewall()
        )
        self.referee = Ring0SelfReferee(self.state_dir / "ring0_journal", firewall=self.firewall, budget=self.budget)
        self.introspector = SelfIntrospector()
        self.profiler = EmpiricalZygoteProfiler()
        self.archive = QualityDiversitySelfArchive(self.state_dir / "qd_self_archive_v1.json")
        self.concept_library = concept_library or CompoundingConceptLibrary(self.state_dir / "concept_library_v1.json")

    def run_self_improvement_cycle(
        self,
        root: pathlib.Path,
        *,
        ring1_relpaths: Sequence[str],
        failed_episodes: Sequence[Mapping[str, Any]] = (),
        sealed_heldout_by_target: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
        speed_benchmarks_by_target: Mapping[str, Mapping[str, Sequence[tuple[Any, ...]]]] | None = None,
        test_relpaths: Sequence[str] | None = None,
        apply_to_root: bool = True,
    ) -> dict[str, Any]:
        """Inspect Ring-1 code & failures, synthesize bounded self-patches, and promote only Ring-0 winners."""
        t0 = time.perf_counter()
        clusters = self.introspector.cluster_failures(failed_episodes)
        hotspots = self.introspector.scan_ring1_hotspots(root, ring1_relpaths)
        redundancies = self.introspector.scan_mdl_redundancies(root, ring1_relpaths)

        proposals: list[SelfPatchProposal] = []
        if clusters:
            proposals.extend(
                propose_functional_upgrade_patches(
                    root,
                    clusters,
                    max_proposals=self.budget.max_proposals_per_cycle,
                    concept_library=self.concept_library,
                )
            )
        if len(proposals) < self.budget.max_proposals_per_cycle and hotspots:
            rem = self.budget.max_proposals_per_cycle - len(proposals)
            proposals.extend(propose_complexity_reduction_patches(root, hotspots, max_proposals=rem))
        if len(proposals) < self.budget.max_proposals_per_cycle and redundancies:
            rem = self.budget.max_proposals_per_cycle - len(proposals)
            proposals.extend(propose_mdl_compression_patches(root, redundancies, max_proposals=rem))

        promoted: list[dict[str, Any]] = []
        refused: list[dict[str, Any]] = []
        promoted_paths: set[str] = set()

        for prop in proposals[: self.budget.max_proposals_per_cycle]:
            if (time.perf_counter() - t0) * 1000.0 > self.budget.max_eval_ms:
                break
            if prop.target_relpath in promoted_paths:
                continue
            key = f"{prop.target_relpath}:{prop.function_name}"
            sealed = (sealed_heldout_by_target or {}).get(key) or (sealed_heldout_by_target or {}).get(prop.target_relpath)
            speed_cfg = dict((speed_benchmarks_by_target or {}).get(key) or (speed_benchmarks_by_target or {}).get(prop.target_relpath) or {})
            if prop.operator_id == "OP1_COMPLEXITY_REDUCTION" and not speed_cfg.get("benchmark_inputs"):
                auto_cfg = self.profiler.synthesize_scaling_workloads_from_tests(
                    root, prop.target_relpath, prop.function_name, test_relpaths
                )
                for k_c, v_c in auto_cfg.items():
                    speed_cfg.setdefault(k_c, v_c)
            verdict = self.referee.evaluate_and_commit(
                root,
                prop,
                test_relpaths=test_relpaths,
                sealed_heldout_cases=sealed,
                benchmark_inputs=speed_cfg.get("benchmark_inputs"),
                parity_inputs=speed_cfg.get("parity_inputs"),
                apply_to_root=apply_to_root,
            )
            if verdict.get("promoted"):
                promoted_paths.add(prop.target_relpath)
                qd_info = self.archive.record_promoted(verdict["commit"], patch_text=prop.unified_diff)
                verdict["qd_archive"] = qd_info
                promoted.append(verdict)
            else:
                refused.append(verdict)

        # Sleep Concept Abstraction over verified Ring-1 modules (G_t -> G_{t+1})
        ring1_sources = [
            (root / rel).read_text(encoding="utf-8")
            for rel in ring1_relpaths
            if (root / rel).is_file()
        ]
        sleep_concepts = self.concept_library.sleep_abstract(ring1_sources) if ring1_sources else {"admitted_count": 0, "admitted": []}

        return {
            "schema": SCHEMA,
            "clusters_found": len(clusters),
            "hotspots_found": len(hotspots),
            "redundancies_found": len(redundancies),
            "proposals_evaluated": len(promoted) + len(refused),
            "promoted_count": len(promoted),
            "refused_count": len(refused),
            "promoted": promoted,
            "refused": refused,
            "concepts_invented": int(sleep_concepts.get("admitted_count", 0)),
            "concept_library_size": len(self.concept_library.concepts()),
            "stepping_stone_elites": self.archive.select_stepping_stone_elites(limit=4),
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            "model_dependency_count": 0,
            "incremental_spend_usd": 0.0,
        }

    def discover_and_synthesize_organ_architecture(
        self,
        *,
        required_effects: Sequence[str],
        available_organs: Sequence[Mapping[str, Any]] | None = None,
        scan_root: pathlib.Path | None = None,
        forbidden_effects: Sequence[str] = ("external_llm_call", "paid_api_spend"),
        max_steps: int = 8,
    ) -> dict[str, Any]:
        """Operator 6: Introspect stranded/available `$0` organs & CEGAR-synthesize a verified architecture."""
        from canonical.runtime.counterexample_guided_causal_architecture_synthesizer_v1 import (
            synthesize as cegar_synthesize,
        )

        orphan_summary: dict[str, int] = {}
        if scan_root is not None and (pathlib.Path(scan_root) / "canonical").is_dir():
            try:
                from canonical.tools.census_orphan_capabilities_v1 import census as run_orphan_census

                rows = run_orphan_census(pathlib.Path(scan_root) / "canonical")
                for row in rows:
                    cls_k = str(getattr(row, "classification", None) or (row.get("classification") if isinstance(row, Mapping) else "UNKNOWN"))
                    orphan_summary[cls_k] = orphan_summary.get(cls_k, 0) + 1
            except Exception:
                orphan_summary = {}

        components: list[dict[str, Any]] = []
        valid_kinds = {"MECHANISM", "TRANSFORM", "GATE", "DISCRIMINATOR", "VERIFIER"}
        for idx, raw_c in enumerate((available_organs or ())[:24]):
            kind = str(raw_c.get("kind") or "MECHANISM").upper()
            if kind not in valid_kinds:
                kind = "MECHANISM"
            provides = [str(x) for x in (raw_c.get("provides") or ()) if str(x)]
            if not provides:
                continue
            components.append(
                {
                    "id": str(raw_c.get("id") or f"organ_{idx}"),
                    "kind": kind,
                    "requires": [str(x) for x in (raw_c.get("requires") or ()) if str(x)],
                    "provides": provides,
                    "forbids": [str(x) for x in (raw_c.get("forbids") or ()) if str(x)],
                    "brain_owned": bool(raw_c.get("brain_owned", True)),
                    "donor_independent": bool(raw_c.get("donor_independent", True)),
                    "verified": bool(raw_c.get("verified", True)),
                    "cost": {"incremental_spend_usd": float((raw_c.get("cost") or {}).get("incremental_spend_usd", 0.0))},
                }
            )

        manifest = {
            "target": {
                "architecture_id": "sovereign_organ_bridge_v1",
                "required_effects": [str(e) for e in required_effects if str(e)],
                "forbidden_effects": [str(e) for e in forbidden_effects if str(e)],
                "initial_facts": [],
                "max_steps": int(max_steps),
                "require_verifier": any(c["kind"] == "VERIFIER" for c in components),
                "allow_candidate_components": False,
            },
            "components": components,
        }
        cegar_res = cegar_synthesize(manifest)
        ok_arch = bool(cegar_res.get("pass") is True and cegar_res.get("winner"))
        return {
            "synthesized": ok_arch,
            "verified": bool(ok_arch and not cegar_res.get("requires_independent_verification_before_promotion", True)),
            "classification": cegar_res.get("classification"),
            "architecture": cegar_res.get("winner"),
            "cegar": cegar_res,
            "orphan_census_summary": orphan_summary,
            "model_dependency_count": 0,
            "incremental_spend_usd": 0.0,
        }

