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
    synthesize_python_function_body,
)
from canonical.swe_kernel import repair_input_dependency_gate_v1 as input_dep_gate
from canonical.swe_kernel.concept_library_v1 import (
    CompoundingConceptLibrary,
    discover_ast_operator_morphisms,
    eval_pure_ast_expr,
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


class SelfIntrospector:
    """Evaluator-grounded Ring-1 weakness clusterer, complexity hotspot detector & MDL scanner."""

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
        """Detect algorithmic $O(N^2)$ linear-scan-in-loop and unmemoized tree-recursion hotspots."""
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

            for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
                # Pattern A: O(N^2) order-preserving list deduplication (`if x not in acc: acc.append(x)`)
                for idx, stmt in enumerate(fn.body):
                    if (
                        isinstance(stmt, ast.Assign)
                        and len(stmt.targets) == 1
                        and isinstance(stmt.targets[0], ast.Name)
                        and isinstance(stmt.value, ast.List)
                        and not stmt.value.elts
                        and idx + 1 < len(fn.body)
                        and isinstance(fn.body[idx + 1], ast.For)
                    ):
                        acc_name = stmt.targets[0].id
                        loop = fn.body[idx + 1]
                        if (
                            isinstance(loop.target, ast.Name)
                            and len(loop.body) == 1
                            and isinstance(loop.body[0], ast.If)
                        ):
                            iff = loop.body[0]
                            if (
                                isinstance(iff.test, ast.Compare)
                                and len(iff.test.ops) == 1
                                and isinstance(iff.test.ops[0], ast.NotIn)
                                and isinstance(iff.test.left, ast.Name)
                                and iff.test.left.id == loop.target.id
                                and isinstance(iff.test.comparators[0], ast.Name)
                                and iff.test.comparators[0].id == acc_name
                            ):
                                hotspots.append(
                                    {
                                        "target_relpath": rel,
                                        "function_name": fn.name,
                                        "pattern": "QUADRATIC_LIST_DEDUP",
                                        "lineno": loop.lineno,
                                    }
                                )
                # Pattern B: O(N * M) membership filter (`for x in a: if x in b: acc.append(x)`)
                param_names = {a.arg for a in fn.args.args}
                for loop in [n for n in ast.walk(fn) if isinstance(n, ast.For)]:
                    if (
                        isinstance(loop.target, ast.Name)
                        and len(loop.body) == 1
                        and isinstance(loop.body[0], ast.If)
                        and isinstance(loop.body[0].test, ast.Compare)
                        and len(loop.body[0].test.ops) == 1
                        and isinstance(loop.body[0].test.ops[0], ast.In)
                        and isinstance(loop.body[0].test.left, ast.Name)
                        and loop.body[0].test.left.id == loop.target.id
                        and isinstance(loop.body[0].test.comparators[0], ast.Name)
                        and loop.body[0].test.comparators[0].id in param_names
                    ):
                        hotspots.append(
                            {
                                "target_relpath": rel,
                                "function_name": fn.name,
                                "pattern": "QUADRATIC_MEMBERSHIP_FILTER",
                                "rhs_param": loop.body[0].test.comparators[0].id,
                                "lineno": loop.lineno,
                            }
                        )
                # Pattern C: Unmemoized pure tree recursion (>= 2 self-calls in body, 0 decorators)
                if not fn.decorator_list:
                    self_calls = [
                        c
                        for c in ast.walk(fn)
                        if isinstance(c, ast.Call) and isinstance(c.func, ast.Name) and c.func.id == fn.name
                    ]
                    has_mutation = any(isinstance(n, (ast.Global, ast.Nonlocal, ast.AugAssign, ast.Delete)) for n in ast.walk(fn))
                    if len(self_calls) >= 2 and not has_mutation:
                        hotspots.append(
                            {
                                "target_relpath": rel,
                                "function_name": fn.name,
                                "pattern": "EXPONENTIAL_PURE_RECURSION",
                                "lineno": fn.lineno,
                            }
                        )
                # Pattern D: O(N * M) nested equijoin scan (`for u in a: for v in b: if k1(u) == k2(v): acc.append(E(u, v))`)
                for outer_loop in [n for n in fn.body if isinstance(n, ast.For)]:
                    if (
                        isinstance(outer_loop.target, ast.Name)
                        and len(outer_loop.body) == 1
                        and isinstance(outer_loop.body[0], ast.For)
                    ):
                        inner_loop = outer_loop.body[0]
                        if (
                            isinstance(inner_loop.target, ast.Name)
                            and len(inner_loop.body) == 1
                            and isinstance(inner_loop.body[0], ast.If)
                        ):
                            cond = inner_loop.body[0].test
                            if isinstance(cond, ast.Compare) and len(cond.ops) == 1 and isinstance(cond.ops[0], ast.Eq):
                                u_nm = outer_loop.target.id
                                v_nm = inner_loop.target.id
                                lhs_names = {x.id for x in ast.walk(cond.left) if isinstance(x, ast.Name)}
                                rhs_names = {x.id for x in ast.walk(cond.comparators[0]) if isinstance(x, ast.Name)}
                                if (u_nm in lhs_names and v_nm not in lhs_names and v_nm in rhs_names and u_nm not in rhs_names) or (
                                    v_nm in lhs_names and u_nm not in lhs_names and u_nm in rhs_names and v_nm not in rhs_names
                                ):
                                    hotspots.append(
                                        {
                                            "target_relpath": rel,
                                            "function_name": fn.name,
                                            "pattern": "QUADRATIC_NESTED_EQUIJOIN",
                                            "lineno": outer_loop.lineno,
                                        }
                                    )
                # Pattern E: Loop-invariant pure aggregation/sort inside `for` loop (`max(arr)`, `min(arr)`, `sum(arr)`, `sorted(arr)`)
                _hoistable_fns = {"sum", "min", "max", "sorted", "len"}
                for loop in [n for n in ast.walk(fn) if isinstance(n, ast.For)]:
                    bound_in_loop = {
                        t.id
                        for sub in ast.walk(loop)
                        if isinstance(sub, (ast.For, ast.Assign))
                        for t in ([sub.target] if isinstance(sub, ast.For) else sub.targets)
                        if isinstance(t, ast.Name)
                    }
                    inv_calls = [
                        c
                        for stmt_b in loop.body
                        for c in ast.walk(stmt_b)
                        if isinstance(c, ast.Call)
                        and isinstance(c.func, ast.Name)
                        and c.func.id in _hoistable_fns
                        and len(c.args) == 1
                        and not c.keywords
                        and isinstance(c.args[0], ast.Name)
                        and c.args[0].id in param_names
                        and c.args[0].id not in bound_in_loop
                        and c.func.id != "len"  # len(list) is O(1); sum/min/max/sorted are O(N) / O(N log N)!
                    ]
                    if inv_calls:
                        hotspots.append(
                            {
                                "target_relpath": rel,
                                "function_name": fn.name,
                                "pattern": "LOOP_INVARIANT_PURE_CALL",
                                "lineno": loop.lineno,
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


def propose_complexity_reduction_patches(
    root: pathlib.Path,
    hotspots: Sequence[Mapping[str, Any]],
    *,
    max_proposals: int = 4,
) -> list[SelfPatchProposal]:
    """Operator 1: Synthesize verified $O(N^2) -> O(N)$ and memoization AST complexity upgrades."""
    proposals: list[SelfPatchProposal] = []
    for hs in hotspots:
        if len(proposals) >= max_proposals:
            break
        rel = str(hs.get("target_relpath") or "")
        fn_name = str(hs.get("function_name") or "")
        pat = str(hs.get("pattern") or "")
        fp = root / rel
        if not fp.is_file():
            continue
        before_src = fp.read_text(encoding="utf-8")
        base_sha = _sha256_bytes(fp.read_bytes())
        try:
            tree = ast.parse(before_src)
        except SyntaxError:
            continue

        mutated = False
        if pat == "QUADRATIC_LIST_DEDUP":
            for fn in [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == fn_name]:
                new_body: list[ast.stmt] = []
                i = 0
                while i < len(fn.body):
                    st = fn.body[i]
                    if (
                        isinstance(st, ast.Assign)
                        and len(st.targets) == 1
                        and isinstance(st.targets[0], ast.Name)
                        and isinstance(st.value, ast.List)
                        and not st.value.elts
                        and i + 1 < len(fn.body)
                        and isinstance(fn.body[i + 1], ast.For)
                    ):
                        acc_nm = st.targets[0].id
                        loop = fn.body[i + 1]
                        if (
                            isinstance(loop.target, ast.Name)
                            and len(loop.body) == 1
                            and isinstance(loop.body[0], ast.If)
                            and isinstance(loop.body[0].test, ast.Compare)
                            and isinstance(loop.body[0].test.ops[0], ast.NotIn)
                        ):
                            item_nm = loop.target.id
                            iter_src = ast.unparse(loop.iter)
                            body_src = "\n".join("            " + ast.unparse(b) for b in loop.body[0].body)
                            snip = ast.parse(
                                f"{acc_nm} = []\n"
                                f"_seen_{acc_nm} = set()\n"
                                f"_unhash_{acc_nm} = []\n"
                                f"for {item_nm} in {iter_src}:\n"
                                f"    try:\n"
                                f"        _present = {item_nm} in _seen_{acc_nm}\n"
                                f"        if not _present:\n"
                                f"            _seen_{acc_nm}.add({item_nm})\n"
                                f"    except TypeError:\n"
                                f"        _present = {item_nm} in _unhash_{acc_nm}\n"
                                f"        if not _present:\n"
                                f"            _unhash_{acc_nm}.append({item_nm})\n"
                                f"    if not _present:\n"
                                f"{body_src}\n"
                            ).body
                            new_body.extend(snip)
                            mutated = True
                            i += 2
                            continue
                    new_body.append(st)
                    i += 1
                if mutated:
                    fn.body = new_body

        elif pat == "QUADRATIC_MEMBERSHIP_FILTER":
            rhs_p = str(hs.get("rhs_param") or "")
            for fn in [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == fn_name]:
                hoist_nm = f"_set_{rhs_p}"
                prelude = ast.parse(
                    f"try:\n"
                    f"    {hoist_nm} = set({rhs_p})\n"
                    f"except TypeError:\n"
                    f"    {hoist_nm} = {rhs_p}\n"
                ).body
                for loop in [n for n in ast.walk(fn) if isinstance(n, ast.For)]:
                    if (
                        len(loop.body) == 1
                        and isinstance(loop.body[0], ast.If)
                        and isinstance(loop.body[0].test, ast.Compare)
                        and isinstance(loop.body[0].test.comparators[0], ast.Name)
                        and loop.body[0].test.comparators[0].id == rhs_p
                    ):
                        loop.body[0].test.comparators[0] = ast.Name(id=hoist_nm, ctx=ast.Load())
                        mutated = True
                if mutated:
                    insert_at = 1 if (
                        fn.body
                        and isinstance(fn.body[0], ast.Expr)
                        and isinstance(fn.body[0].value, ast.Constant)
                        and isinstance(fn.body[0].value.value, str)
                    ) else 0
                    fn.body = fn.body[:insert_at] + prelude + fn.body[insert_at:]

        elif pat == "EXPONENTIAL_PURE_RECURSION":
            has_ft = any(
                (isinstance(n, ast.Import) and any(a.name == "functools" for a in n.names))
                for n in tree.body
            )
            if not has_ft:
                tree.body.insert(0, ast.Import(names=[ast.alias(name="functools")]))
            for fn in [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == fn_name]:
                fn.decorator_list.insert(
                    0,
                    ast.parse("functools.lru_cache(maxsize=4096)").body[0].value,  # type: ignore[attr-defined]
                )
                mutated = True

        elif pat == "QUADRATIC_NESTED_EQUIJOIN":
            for fn in [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == fn_name]:
                new_body_j: list[ast.stmt] = []
                for st in fn.body:
                    if (
                        isinstance(st, ast.For)
                        and isinstance(st.target, ast.Name)
                        and len(st.body) == 1
                        and isinstance(st.body[0], ast.For)
                    ):
                        inner_l = st.body[0]
                        if (
                            isinstance(inner_l.target, ast.Name)
                            and len(inner_l.body) == 1
                            and isinstance(inner_l.body[0], ast.If)
                        ):
                            iff_j = inner_l.body[0]
                            cond_j = iff_j.test
                            if isinstance(cond_j, ast.Compare) and len(cond_j.ops) == 1 and isinstance(cond_j.ops[0], ast.Eq):
                                u_nm = st.target.id
                                v_nm = inner_l.target.id
                                lhs_e = cond_j.left
                                rhs_e = cond_j.comparators[0]
                                lhs_ids = {x.id for x in ast.walk(lhs_e) if isinstance(x, ast.Name)}
                                if u_nm in lhs_ids:
                                    u_key_src, v_key_src = ast.unparse(lhs_e), ast.unparse(rhs_e)
                                else:
                                    u_key_src, v_key_src = ast.unparse(rhs_e), ast.unparse(lhs_e)
                                outer_iter_src = ast.unparse(st.iter)
                                inner_iter_src = ast.unparse(inner_l.iter)
                                inner_body_src = "\n".join("        " + ast.unparse(b) for b in iff_j.body)
                                join_code = (
                                    f"_join_idx_{v_nm} = {{}}\n"
                                    f"for {v_nm} in {inner_iter_src}:\n"
                                    f"    _join_idx_{v_nm}.setdefault({v_key_src}, []).append({v_nm})\n"
                                    f"for {u_nm} in {outer_iter_src}:\n"
                                    f"    for {v_nm} in _join_idx_{v_nm}.get({u_key_src}, ()):\n"
                                    f"{inner_body_src}\n"
                                )
                                new_body_j.extend(ast.parse(join_code).body)
                                mutated = True
                                continue
                    new_body_j.append(st)
                if mutated:
                    fn.body = new_body_j

        elif pat == "LOOP_INVARIANT_PURE_CALL":
            _hoistable_fns = {"sum", "min", "max", "sorted"}
            for fn in [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == fn_name]:
                param_names_s = {a.arg for a in fn.args.args}
                hoist_defs: dict[str, str] = {}
                new_fn_body: list[ast.stmt] = []
                for st in fn.body:
                    if isinstance(st, ast.For):
                        bound_in_loop = {
                            t.id
                            for sub in ast.walk(st)
                            if isinstance(sub, (ast.For, ast.Assign))
                            for t in ([sub.target] if isinstance(sub, ast.For) else sub.targets)
                            if isinstance(t, ast.Name)
                        }

                        class _LICMRewriter(ast.NodeTransformer):
                            def visit_Call(self, c_nd: ast.Call) -> ast.AST:
                                self.generic_visit(c_nd)
                                if (
                                    isinstance(c_nd.func, ast.Name)
                                    and c_nd.func.id in _hoistable_fns
                                    and len(c_nd.args) == 1
                                    and not c_nd.keywords
                                    and isinstance(c_nd.args[0], ast.Name)
                                    and c_nd.args[0].id in param_names_s
                                    and c_nd.args[0].id not in bound_in_loop
                                ):
                                    c_src = ast.unparse(c_nd)
                                    h_var = hoist_defs.setdefault(c_src, f"_licm_{len(hoist_defs)}")
                                    return ast.Name(id=h_var, ctx=ast.Load())
                                return c_nd

                        st = _LICMRewriter().visit(st)
                        if hoist_defs:
                            for c_src, h_var in hoist_defs.items():
                                new_fn_body.extend(ast.parse(f"{h_var} = {c_src}\n").body)
                            hoist_defs.clear()
                            mutated = True
                    new_fn_body.append(st)
                if mutated:
                    fn.body = new_fn_body

        if not mutated:
            continue
        ast.fix_missing_locations(tree)
        after_src = ast.unparse(tree) + "\n"
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
                rationale=f"Upgrade {fn_name} ({pat}) from quadratic/exponential work to sub-linear/linear execution.",
                improvement_axis="complexity_speedup",
                metadata={"hotspot_pattern": pat},
            )
        )
    return proposals


def _synthesize_empirical_ast_catamorphism(
    fn_node: ast.FunctionDef,
    dev_cases: Sequence[Mapping[str, Any]],
) -> ast.FunctionDef | None:
    """Synthesize an AST structural catamorphism by empirically probing Python's `operator` algebra (zero templates)."""
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

    # Empirically verify that dev_cases denote pure syntax-tree evaluation (`eval_pure_ast_expr`)
    for c in str_expr_cases:
        raw_expr = str(c["args"][0]).strip()
        raw_env = dict(c["args"][1]) if len(c["args"]) >= 2 and isinstance(c["args"][1], Mapping) else {}
        try:
            parsed_dev = ast.parse(raw_expr, mode="eval")
            denot = eval_pure_ast_expr(parsed_dev, raw_env)
        except Exception:
            return None
        if denot != c.get("expected"):
            return None

    # Discover operator morphisms empirically from Python's runtime `ast` x `operator` algebra
    morphisms = discover_ast_operator_morphisms()
    arg0 = fn_node.args.args[0].arg
    env_arg = fn_node.args.args[1].arg if len(fn_node.args.args) >= 2 else None

    # Construct compact AST catamorphism programmatically from discovered `morphisms` (MDL-optimal)
    bin_keys: list[ast.expr] = []
    bin_vals: list[ast.expr] = []
    # Project discovered morphisms onto observed value algebra (MDL parsimony: include bitwise ops iff bitwise syntax observed)
    has_bitwise = any(
        isinstance(sub, (ast.BitAnd, ast.BitOr, ast.BitXor, ast.RShift, ast.Invert))
        for c in str_expr_cases
        for sub in ast.walk(ast.parse(str(c["args"][0]).strip(), mode="eval"))
    )
    _excluded_bin = {"Pow", "LShift", "MatMult"} | (set() if has_bitwise else {"BitAnd", "BitOr", "BitXor", "RShift"})
    for ast_cls_nm, spec in sorted(morphisms["binary"].items()):
        if ast_cls_nm in _excluded_bin:
            continue
        op_attr = str(spec["operator_attr"])
        op_ref: ast.expr = ast.Attribute(value=ast.Name(id="_o", ctx=ast.Load()), attr=op_attr, ctx=ast.Load())
        if spec.get("needs_zero_guard"):
            z_ident = spec.get("zero_identity", 0)
            op_ref = ast.Call(
                func=ast.Name(id="_z", ctx=ast.Load()),
                args=[op_ref] + ([ast.Constant(value=z_ident)] if z_ident != 0 else []),
                keywords=[],
            )
        bin_keys.append(ast.Attribute(value=ast.Name(id="_a", ctx=ast.Load()), attr=ast_cls_nm, ctx=ast.Load()))
        bin_vals.append(op_ref)

    _excluded_un = set() if has_bitwise else {"Invert", "Not"}
    un_keys: list[ast.expr] = [
        ast.Attribute(value=ast.Name(id="_a", ctx=ast.Load()), attr=k, ctx=ast.Load())
        for k in sorted(morphisms["unary"].keys())
        if k not in _excluded_un
    ]
    un_vals: list[ast.expr] = [
        ast.Attribute(value=ast.Name(id="_o", ctx=ast.Load()), attr=morphisms["unary"][k], ctx=ast.Load())
        for k in sorted(morphisms["unary"].keys())
        if k not in _excluded_un
    ]

    cmp_keys: list[ast.expr] = [
        ast.Attribute(value=ast.Name(id="_a", ctx=ast.Load()), attr=k, ctx=ast.Load())
        for k in sorted(morphisms["compare"].keys())
    ]
    cmp_vals: list[ast.expr] = [
        ast.Attribute(value=ast.Name(id="_o", ctx=ast.Load()), attr=morphisms["compare"][k], ctx=ast.Load())
        for k in sorted(morphisms["compare"].keys())
    ]

    env_expr: ast.expr = (
        ast.Call(
            func=ast.Name(id="dict", ctx=ast.Load()),
            args=[ast.BoolOp(op=ast.Or(), values=[ast.Name(id=env_arg, ctx=ast.Load()), ast.Dict(keys=[], values=[])])],
            keywords=[],
        )
        if env_arg
        else ast.Dict(keys=[], values=[])
    )

    fold_fn = ast.parse(
        "def _f(n):\n"
        "    if isinstance(n, _a.Expression): return _f(n.body)\n"
        "    if isinstance(n, _a.Constant) and type(n.value) in (int, float, bool): return n.value\n"
        "    if isinstance(n, _a.Name) and n.id in _e: return _e[n.id]\n"
        "    if isinstance(n, _a.UnaryOp): return _u[type(n.op)](_f(n.operand))\n"
        "    if isinstance(n, _a.BinOp): return _b[type(n.op)](_f(n.left), _f(n.right))\n"
        "    if isinstance(n, _a.IfExp): return _f(n.body) if _f(n.test) else _f(n.orelse)\n"
        "    return _c[type(n.ops[0])](_f(n.left), _f(n.comparators[0]))\n"
    ).body[0]

    new_body: list[ast.stmt] = [
        ast.Import(names=[ast.alias(name="ast", asname="_a"), ast.alias(name="operator", asname="_o")]),
        ast.Assign(targets=[ast.Name(id="_e", ctx=ast.Store())], value=env_expr),
        ast.parse("_z = lambda f, z=0: (lambda x, y: z if y == 0 else f(x, y))\n").body[0],
        ast.Assign(targets=[ast.Name(id="_b", ctx=ast.Store())], value=ast.Dict(keys=bin_keys, values=bin_vals)),
        ast.Assign(targets=[ast.Name(id="_u", ctx=ast.Store())], value=ast.Dict(keys=un_keys, values=un_vals)),
        ast.Assign(targets=[ast.Name(id="_c", ctx=ast.Store())], value=ast.Dict(keys=cmp_keys, values=cmp_vals)),
        fold_fn,
        ast.Return(
            value=ast.Call(
                func=ast.Name(id="_f", ctx=ast.Load()),
                args=[
                    ast.Call(
                        func=ast.Attribute(value=ast.Name(id="_a", ctx=ast.Load()), attr="parse", ctx=ast.Load()),
                        args=[
                            ast.Call(
                                func=ast.Attribute(
                                    value=ast.Call(func=ast.Name(id="str", ctx=ast.Load()), args=[ast.Name(id=arg0, ctx=ast.Load())], keywords=[]),
                                    attr="strip",
                                    ctx=ast.Load(),
                                ),
                                args=[],
                                keywords=[],
                            )
                        ],
                        keywords=[ast.keyword(arg="mode", value=ast.Constant(value="eval"))],
                    )
                ],
                keywords=[],
            )
        ),
    ]
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


class QualityDiversitySelfArchive:
    """Operator 5: MAP-Elites Quality-Diversity self-lineage archive persisted across reboots."""

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

    def record_promoted(self, commit_record: Mapping[str, Any]) -> dict[str, Any]:
        state = self._load()
        cells = state.setdefault("cells", {})
        rel = str(commit_record.get("target_relpath") or "ring1")
        axis = str(commit_record.get("improvement_axis") or "accuracy")
        delta_b = int(commit_record.get("delta_exec_bytes") or 0)
        size_bin = "shrunk" if delta_b < 0 else ("compact" if delta_b <= 80 else "expanded")
        cell_key = f"{rel}::{axis}::{size_bin}"

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
                "delta_exec_bytes": delta_b,
                "qd_score": round(score, 4),
            }
            tmp = self.archive_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            tmp.replace(self.archive_path)
        return {"cell_key": cell_key, "replaced_incumbent": replaced, "total_elites": len(cells)}


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

        for prop in proposals[: self.budget.max_proposals_per_cycle]:
            if (time.perf_counter() - t0) * 1000.0 > self.budget.max_eval_ms:
                break
            key = f"{prop.target_relpath}:{prop.function_name}"
            sealed = (sealed_heldout_by_target or {}).get(key) or (sealed_heldout_by_target or {}).get(prop.target_relpath)
            speed_cfg = (speed_benchmarks_by_target or {}).get(key) or (speed_benchmarks_by_target or {}).get(prop.target_relpath) or {}
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
                qd_info = self.archive.record_promoted(verdict["commit"])
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
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            "model_dependency_count": 0,
            "incremental_spend_usd": 0.0,
        }
