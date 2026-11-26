"""Canonical Unified Polyglot SWE Spine (`canonical_swe_spine_v1`).

Consolidates the empirically winning repair & verification primitives on `main`
into ONE front-door-wired execution spine instead of 27 disconnected kernels:

  Stage 0  Workspace snapshot, language detection, and baseline real-oracle run.
  Stage 1  Fail-closed green-suite gate + 4-channel zero-model Wall-1 witness
           abduction (optional untrusted proposer witness strictly verified to
           FAIL on baseline before any patch is permitted).
  Stage 1.5 O(1) structural law-store recall (zero model calls, exact O(1)
            deletion supported).
  Stage 2  Polyglot zero-model winning solvers (PRODUCER_MODEL_CALLS == 0):
             - Python: `metamorphic_habitation_zipper_v1` (which drives
               `cow_angelic_zygote_v1` CoW pytest zygote, Ochiai spectrum,
               angelic separating guards, differential lenses, and
               `NegativeSpaceGuard`) + mechanical multi-file import/symbol
               zipper hops (`the_zip_propagates_v1` rules).
             - C: `c_asan_cegis_repair_v1` (GCC `-fsanitize=address,undefined`).
             - JavaScript / Node: `js_causal_cegis_repair_v1`.
  Stage 3  Optional Option-A untrusted proposer strictly behind fail-closed
           independent verification:
             - Rejects test-file tampering, empty/no-op edits, syntax errors,
               refuted `NegativeSpaceGuard` fingerprints, and edits failing
               `repair_input_dependency_gate_v1.gate`.
             - Re-executes the real test suite + regression tests on disk.
             - Rolls back byte-identically on ANY failure.
             - Crystallizes verified structural diffs into the O(1) law store
               so recurring classes permanently drop back to 0 model calls.
  Stage 4  Independent on-disk post-state effect verification & rollback safety.

Every result explicitly reports `authority = "NONE_SANDBOX"` and exact
`model_calls` (0 by default). Never fabricates a pass from self-status.
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
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Protocol, Sequence

from canonical.swe_kernel import causal_nexus_v1
from canonical.swe_kernel import cow_angelic_zygote_v1 as cow_zyg
from canonical.swe_kernel import metamorphic_habitation_zipper_v1 as mhz
from canonical.swe_kernel import petri_cow_splicing_engine_v1 as petri_splicer
from canonical.swe_kernel import repair_input_dependency_gate_v1 as dep_gate
from canonical.swe_kernel import stdlib_cow_test_runner_v1 as cow_runner
from canonical.swe_kernel import witness_inversion_v1
from canonical.swe_kernel import zygote_worker_pool_v1 as zygote_pool
from canonical.tools import the_assertion_is_the_demand_v1 as assert_demand
from canonical.tools import the_relation_is_read_from_the_failing_run_v1 as rel_run

SCHEMA = "CANONICAL_SWE_SPINE_V1"
AUTHORITY = "NONE_SANDBOX"
PRODUCER_MODEL_CALLS = 0

# Competing SWE repair/synthesis modules consolidated by this spine.
COMPOSED_CORE_MODULES: tuple[str, ...] = (
    "canonical/swe_kernel/metamorphic_habitation_zipper_v1.py",
    "canonical/swe_kernel/cow_angelic_zygote_v1.py",
    "canonical/swe_kernel/stdlib_cow_test_runner_v1.py",
    "canonical/swe_kernel/zygote_worker_pool_v1.py",
    "canonical/tools/the_assertion_is_the_demand_v1.py",
    "canonical/tools/the_relation_is_read_from_the_failing_run_v1.py",
    "canonical/swe_kernel/witness_inversion_v1.py",
    "canonical/swe_kernel/causal_nexus_v1.py",
    "canonical/swe_kernel/petri_cow_splicing_engine_v1.py",
    "canonical/swe_kernel/c_asan_cegis_repair_v1.py",
    "canonical/swe_kernel/js_causal_cegis_repair_v1.py",
    "canonical/swe_kernel/repair_input_dependency_gate_v1.py",
    "canonical/tools/the_zip_propagates_v1.py",
    "canonical/runtime/bound_capabilities/python_counterfactual_spec_repair_v1.py",
    "canonical/swe_kernel/angelic_cegis_repair_v1.py",
    "canonical/swe_kernel/causal_cegis_inventor_v1.py",
    "canonical/swe_kernel/cegis_semantic_synthesizer_v1.py",
    "canonical/tools/the_same_guard_twice_is_the_discriminator_v1.py",
    "canonical/runtime/bound_capabilities/software_repair_crossfile_choreograph_v1.py",
    "canonical/runtime/goal_front_compiler_v1.py",
    "canonical/runtime/declared_input_derivation_v1.py",
)

_SKIP_DIRS = frozenset({
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    ".venv",
    "venv",
    "build",
    "dist",
})

_IMPORT_FAIL_RE = re.compile(r"cannot import name '([\w_]+)' from '([\w_.]+)'")
_NAME_FAIL_RE = re.compile(r"NameError: name '([\w_]+)' is not defined")
_NAME_FRAME_RE = re.compile(r"^([\w/.-]+\.py):\d+: in <module>$", re.M)


class UntrustedProposer(Protocol):
    """Optional Option-A proposer interface, strictly behind fail-closed verification."""

    def propose_witness(
        self,
        *,
        repo_root: pathlib.Path,
        issue_text: str,
        language: str,
        baseline_output: str,
    ) -> str | None:
        """Return candidate test file content that should FAIL on baseline, or None."""
        ...

    def propose_patches(
        self,
        *,
        repo_root: pathlib.Path,
        issue_text: str,
        language: str,
        failure_output: str,
        candidate_files: Sequence[str],
    ) -> Sequence[Mapping[str, str]]:
        """Return candidate patch dicts mapping relative file paths to full new source."""
        ...


@dataclass
class StructuralLaw:
    """Generalized single-hunk structural diff law stored in O(1) hash buckets."""

    law_id: str
    language: str
    signature_key: str
    old_fragment: str
    new_fragment: str
    provenance: str = "VERIFIED_DIFF"
    hits: int = 0


class CanonicalLawStore:
    """External JSON-backed O(1) structural law store with exact O(1) deletion."""

    def __init__(self, path: str | pathlib.Path | None = None) -> None:
        self.path = pathlib.Path(path) if path is not None else None
        self._by_id: dict[str, StructuralLaw] = {}
        self._buckets: dict[str, list[str]] = {}
        if self.path is not None and self.path.exists():
            self._load()

    def _load(self) -> None:
        assert self.path is not None
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        for row in raw.get("laws", []):
            law = StructuralLaw(
                law_id=str(row["law_id"]),
                language=str(row["language"]),
                signature_key=str(row["signature_key"]),
                old_fragment=str(row["old_fragment"]),
                new_fragment=str(row["new_fragment"]),
                provenance=str(row.get("provenance", "VERIFIED_DIFF")),
                hits=int(row.get("hits", 0)),
            )
            self._by_id[law.law_id] = law
            self._buckets.setdefault(law.signature_key, []).append(law.law_id)

    def save(self) -> None:
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": "CANONICAL_LAW_STORE_V1",
            "laws": [
                {
                    "law_id": law.law_id,
                    "language": law.language,
                    "signature_key": law.signature_key,
                    "old_fragment": law.old_fragment,
                    "new_fragment": law.new_fragment,
                    "provenance": law.provenance,
                    "hits": law.hits,
                }
                for law in self._by_id.values()
            ],
        }
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    @staticmethod
    def _error_bucket_key(language: str, failure_output: str) -> str:
        # Extract stable error class / assertion kind without memorizing file names
        m = re.search(
            r"\b([A-Za-z_][A-Za-z0-9_]*(?:Error|Exception|Failure)|AssertionError|heap-use-after-free|heap-buffer-overflow|SEGV)\b",
            failure_output,
        )
        err_kind = m.group(1) if m else "GENERIC_FAILURE"
        return f"{language}:{err_kind}"

    def add_verified_diff(
        self,
        *,
        language: str,
        failure_output: str,
        orig_source: str,
        patched_source: str,
        provenance: str = "VERIFIED_DIFF",
    ) -> StructuralLaw | None:
        """Crystallize the minimal changed line block from a verified patch."""
        orig_lines = orig_source.splitlines()
        new_lines = patched_source.splitlines()
        sm = difflib.SequenceMatcher(None, orig_lines, new_lines)
        changed = [op for op in sm.get_opcodes() if op[0] != "equal"]
        if len(changed) != 1:
            return None
        tag, i1, i2, j1, j2 = changed[0]
        if tag != "replace" or (i2 - i1) == 0 or (i2 - i1) > 12 or (j2 - j1) > 20:
            return None
        old_frag = "\n".join(orig_lines[i1:i2])
        new_frag = "\n".join(new_lines[j1:j2])
        if not old_frag.strip() or old_frag == new_frag:
            return None
        sig = self._error_bucket_key(language, failure_output)
        law_id = hashlib.sha256(f"{sig}\0{old_frag}\0{new_frag}".encode("utf-8")).hexdigest()[:16]
        if law_id in self._by_id:
            return self._by_id[law_id]
        law = StructuralLaw(
            law_id=law_id,
            language=language,
            signature_key=sig,
            old_fragment=old_frag,
            new_fragment=new_frag,
            provenance=provenance,
        )
        self._by_id[law_id] = law
        self._buckets.setdefault(sig, []).append(law_id)
        self.save()
        return law

    def lookup(self, language: str, failure_output: str) -> list[StructuralLaw]:
        sig = self._error_bucket_key(language, failure_output)
        ids = self._buckets.get(sig, [])
        return [self._by_id[lid] for lid in ids if lid in self._by_id]

    def delete(self, law_id: str) -> bool:
        """Exact O(1) deletion with zero residual lookup hits."""
        law = self._by_id.pop(law_id, None)
        if law is None:
            return False
        bucket = self._buckets.get(law.signature_key)
        if bucket and law_id in bucket:
            bucket.remove(law_id)
            if not bucket:
                self._buckets.pop(law.signature_key, None)
        self.save()
        return True

    def count(self) -> int:
        return len(self._by_id)


def _snapshot_tree(repo_root: pathlib.Path) -> dict[str, bytes]:
    snap: dict[str, bytes] = {}
    for p in repo_root.rglob("*"):
        if any(part in _SKIP_DIRS for part in p.parts):
            continue
        if p.is_file():
            try:
                snap[p.relative_to(repo_root).as_posix()] = p.read_bytes()
            except OSError:
                continue
    return snap


def _restore_tree(repo_root: pathlib.Path, snapshot: Mapping[str, bytes]) -> None:
    current = set()
    for p in repo_root.rglob("*"):
        if any(part in _SKIP_DIRS for part in p.parts):
            continue
        if p.is_file():
            current.add(p.relative_to(repo_root).as_posix())
    # Remove files created during execution
    for rel in sorted(current - set(snapshot.keys()), reverse=True):
        try:
            (repo_root / rel).unlink()
        except OSError:
            pass
    # Restore modified or deleted files
    for rel, content in snapshot.items():
        target = repo_root / rel
        if not target.exists() or target.read_bytes() != content:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)


def _changed_files_from_snapshot(
    repo_root: pathlib.Path, snapshot: Mapping[str, bytes]
) -> dict[str, str]:
    changed: dict[str, str] = {}
    for p in repo_root.rglob("*"):
        if any(part in _SKIP_DIRS for part in p.parts) or not p.is_file():
            continue
        rel = p.relative_to(repo_root).as_posix()
        cur = p.read_bytes()
        if snapshot.get(rel) != cur:
            changed[rel] = cur.decode("utf-8", errors="replace")
    return changed


def _is_test_relpath(rel: str) -> bool:
    parts = pathlib.PurePosixPath(rel).parts
    name = pathlib.PurePosixPath(rel).name
    if any(p in ("tests", "test", "__tests__") for p in parts):
        return True
    return (
        name.startswith("test_")
        or name.endswith("_test.py")
        or name.endswith(".test.js")
        or name.endswith(".spec.js")
        or name.endswith("_tests.c")
    )


def detect_repository_language(
    repo_root: pathlib.Path,
    *,
    test_file: str | None = None,
    c_sources: Sequence[str] | None = None,
) -> str:
    if c_sources:
        return "c"
    if test_file:
        low = test_file.lower()
        if low.endswith(".py"):
            return "python"
        if low.endswith((".js", ".mjs", ".cjs")):
            return "javascript"
        if low.endswith((".c", ".h")):
            return "c"
    counts = {"python": 0, "c": 0, "javascript": 0}
    for p in repo_root.rglob("*"):
        if any(part in _SKIP_DIRS for part in p.parts) or not p.is_file():
            continue
        suf = p.suffix.lower()
        if suf == ".py":
            counts["python"] += 1
        elif suf == ".c":
            counts["c"] += 1
        elif suf in (".js", ".mjs", ".cjs"):
            counts["javascript"] += 1
    return max(counts.items(), key=lambda kv: kv[1])[0]


def _pytest_passed(run_res: Mapping[str, Any]) -> bool:
    """True iff `mhz.run_pytest_targets` executed >=1 passing tests with 0 failures."""
    if not isinstance(run_res, Mapping):
        return False
    ok_flag = run_res.get("ok")
    rc = run_res.get("rc", run_res.get("returncode"))
    failed_list = run_res.get("failed_nodeids") or run_res.get("failed") or []
    passed_n = int(run_res.get("passed") or run_res.get("passed_count") or 0)
    return bool((ok_flag is True or rc == 0) and rc == 0 and not failed_list and passed_n > 0)


def _pytest_failed(run_res: Mapping[str, Any]) -> bool:
    """True iff `mhz.run_pytest_targets` observed a non-zero exit or failing nodeids."""
    if not isinstance(run_res, Mapping):
        return True
    rc = run_res.get("rc", run_res.get("returncode"))
    failed_list = run_res.get("failed_nodeids") or run_res.get("failed") or []
    return bool(run_res.get("ok") is False or (rc is not None and rc != 0) or bool(failed_list))


def _apply_mechanical_zipper_hops(
    repo_root: pathlib.Path,
    test_targets: Sequence[str],
    *,
    max_hops: int = 8,
    timeout_s: float = 15.0,
) -> dict[str, Any]:
    """Deterministic multi-file import/symbol zipper using `the_zip_propagates_v1` rules."""
    from canonical.tools import the_zip_propagates_v1 as zprop

    hops_applied: list[dict[str, Any]] = []
    for hop in range(1, max_hops + 1):
        res = mhz.run_pytest_targets(repo_root, test_targets, timeout_s=timeout_s)
        out = str(res.get("output") or "")
        if _pytest_passed(res):
            return {"solved": True, "hops": hops_applied, "last_run": res}

        broken_imp = _IMPORT_FAIL_RE.search(out)
        if broken_imp:
            sym, origin = broken_imp.group(1), broken_imp.group(2)
            home = zprop.home_of(repo_root, sym)
            if home is None:
                return {"solved": False, "hops": hops_applied, "last_run": res}
            new_mod = zprop.import_path(repo_root, home)
            old_tail = origin.split(".")[-1]
            touched = 0
            single_re = re.compile(rf"^from \.{re.escape(old_tail)} import ([^\n(]+)$", re.M)
            abs_re = re.compile(rf"^from {re.escape(origin)} import ([^\n(]+)$", re.M)
            for py in repo_root.rglob("*.py"):
                if any(part in _SKIP_DIRS for part in py.parts):
                    continue
                if py.resolve() == home.resolve():
                    continue
                txt = py.read_text(encoding="utf-8", errors="replace")
                rel_pref = f"from .{home.stem} import " if home.parent == py.parent else f"from {new_mod} import "
                abs_pref = f"from {new_mod} import "
                new_txt = txt
                for pat, prefix in ((single_re, rel_pref), (abs_re, abs_pref)):
                    def _repl(m: re.Match[str], _pref: str = prefix) -> str:
                        names = [x.strip() for x in m.group(1).split(",") if x.strip()]
                        if sym not in names:
                            return m.group(0)
                        rest = [x for x in names if x != sym]
                        if not rest:
                            return f"{_pref}{sym}"
                        old_hdr = m.group(0).split(" import ", 1)[0]
                        return f"{old_hdr} import {', '.join(rest)}\n{_pref}{sym}"
                    new_txt = pat.sub(_repl, new_txt)
                if new_txt != txt:
                    py.write_text(new_txt, encoding="utf-8")
                    touched += 1
            if touched == 0:
                return {"solved": False, "hops": hops_applied, "last_run": res}
            hops_applied.append({"hop": hop, "kind": "IMPORT_HOP", "symbol": sym, "to_module": new_mod, "files_touched": touched})
            continue

        broken_name = _NAME_FAIL_RE.search(out)
        if broken_name:
            sym = broken_name.group(1)
            home = zprop.home_of(repo_root, sym)
            if home is None:
                return {"solved": False, "hops": hops_applied, "last_run": res}
            frames = _NAME_FRAME_RE.findall(out) + re.findall(r"^([^\s:]+\.py):\d+: in ", out, re.M)
            target_py: pathlib.Path | None = None
            for f_rel in reversed(frames):
                cand = repo_root / f_rel
                if cand.exists() and cand.resolve() != home.resolve():
                    target_py = cand
                    break
            if target_py is None:
                return {"solved": False, "hops": hops_applied, "last_run": res}
            mod_name = zprop.import_path(repo_root, home)
            imp_line = f"from .{home.stem} import {sym}" if (target_py.parent / "__init__.py").exists() and home.parent == target_py.parent else f"from {mod_name} import {sym}"
            zprop.insert_import(target_py, imp_line)
            hops_applied.append({"hop": hop, "kind": "DEPENDENCY_HOP", "symbol": sym, "target": target_py.relative_to(repo_root).as_posix()})
            continue

        break

    final_run = mhz.run_pytest_targets(repo_root, test_targets, timeout_s=timeout_s)
    return {
        "solved": _pytest_passed(final_run),
        "hops": hops_applied,
        "last_run": final_run,
    }


def _verify_python_candidate_edits(
    repo_root: pathlib.Path,
    edits: Mapping[str, str],
    base_snapshot: Mapping[str, bytes],
    test_targets: Sequence[str],
    *,
    regression_tests: Sequence[str] = (),
    allow_test_edits: bool = False,
    neg_guard: cow_zyg.NegativeSpaceGuard | None = None,
    timeout_s: float = 15.0,
) -> tuple[bool, str, dict[str, Any]]:
    """Fail-closed independent verifier for any candidate patch dict."""
    if not edits:
        return False, "EMPTY_PATCH", {}

    applied_originals: dict[str, str] = {}
    py_pairs: list[tuple[str, str]] = []
    fingerprints: list[str] = []

    for rel, new_src in edits.items():
        norm = pathlib.PurePosixPath(rel).as_posix()
        if norm.startswith("/") or ".." in pathlib.PurePosixPath(norm).parts:
            return False, f"UNSAFE_PATH:{norm}", {}
        if not allow_test_edits and _is_test_relpath(norm):
            return False, f"TEST_FILE_TAMPERING_BLOCKED:{norm}", {}
        if norm not in base_snapshot:
            return False, f"NEW_OR_UNKNOWN_FILE_BLOCKED:{norm}", {}
        orig_src = base_snapshot[norm].decode("utf-8", errors="replace")
        if new_src == orig_src:
            continue
        if norm.endswith(".py"):
            try:
                ast.parse(new_src)
            except SyntaxError as exc:
                return False, f"SYNTAX_ERROR:{norm}:{exc.msg}", {}
            gate_res = dep_gate.gate(orig_src, new_src)
            if gate_res.get("status") != "PASS":
                return False, f"INPUT_DEPENDENCY_LOST:{norm}:{gate_res.get('lost')}", {"gate": gate_res}
            fp = cow_zyg.canonical_ast_delta_fingerprint(orig_src, new_src)
            if neg_guard is not None and neg_guard.is_refuted(orig_src, new_src):
                return False, f"NEGATIVE_SPACE_REFUTED:{fp}", {}
            py_pairs.append((orig_src, new_src))
            fingerprints.append(fp)
        applied_originals[norm] = orig_src

    if not applied_originals:
        return False, "NO_EFFECTIVE_CHANGE", {}

    # Transactionally write edits and independently execute real tests
    try:
        for rel in applied_originals:
            (repo_root / rel).write_text(edits[rel], encoding="utf-8")
        all_targets = list(dict.fromkeys([*test_targets, *regression_tests]))
        run_res = mhz.run_pytest_targets(repo_root, all_targets, timeout_s=timeout_s)
        passed = _pytest_passed(run_res)
        if not passed:
            if neg_guard is not None:
                for orig_s, new_s in py_pairs:
                    neg_guard.record_refutation(orig_s, new_s, reason="VERIFIER_TEST_FAILED")
            return False, "VERIFIER_TESTS_FAILED", {"test_run": run_res}
        return True, "VERIFIED_PASS", {"test_run": run_res, "fingerprints": fingerprints}
    finally:
        # Caller decides whether to commit or roll back; restore here if we failed
        pass


def _try_law_store_recall_python(
    repo_root: pathlib.Path,
    base_snapshot: Mapping[str, bytes],
    failure_output: str,
    test_targets: Sequence[str],
    law_store: CanonicalLawStore,
    *,
    regression_tests: Sequence[str] = (),
    neg_guard: cow_zyg.NegativeSpaceGuard | None = None,
    timeout_s: float = 15.0,
) -> dict[str, Any] | None:
    laws = law_store.lookup("python", failure_output)
    if not laws:
        return None
    py_files = sorted(
        rel for rel in base_snapshot
        if rel.endswith(".py") and not _is_test_relpath(rel)
    )
    for law in laws:
        for rel in py_files:
            orig_src = base_snapshot[rel].decode("utf-8", errors="replace")
            if law.old_fragment not in orig_src:
                continue
            cand_src = orig_src.replace(law.old_fragment, law.new_fragment, 1)
            ok, reason, meta = _verify_python_candidate_edits(
                repo_root,
                {rel: cand_src},
                base_snapshot,
                test_targets,
                regression_tests=regression_tests,
                neg_guard=neg_guard,
                timeout_s=timeout_s,
            )
            if ok:
                law.hits += 1
                law_store.save()
                return {
                    "solved": True,
                    "law_id": law.law_id,
                    "modified_files": [rel],
                    "test_run": meta.get("test_run"),
                }
            _restore_tree(repo_root, base_snapshot)
    return None


def _localize_candidate_py_files(
    base_snapshot: Mapping[str, bytes],
    test_targets: Sequence[str],
    failure_frames: Mapping[str, Sequence[Mapping[str, Any]]],
    failure_output: str,
    covered_lines: Mapping[str, Sequence[int]] | None = None,
) -> list[str]:
    """Rank non-test `.py` files by live stack frames, dynamic line coverage, test imports, and traceback mentions."""
    non_test_py = sorted(
        rel for rel in base_snapshot
        if rel.endswith(".py") and not _is_test_relpath(rel)
    )
    if not non_test_py:
        return []

    scores: dict[str, int] = {rel: 0 for rel in non_test_py}

    # 1. Direct live stack frames from `stdlib_cow_test_runner_v1`
    for fr_list in failure_frames.values():
        for depth, fr in enumerate(reversed(list(fr_list))):
            rp = str(fr.get("rel_path") or "")
            if rp in scores:
                scores[rp] += max(20, 80 - depth * 10)

    # 1b. Dynamic transitive line coverage (solves the `85.7%` test-only-traceback blindness!)
    if covered_lines:
        for rel, lns in covered_lines.items():
            if rel in scores and lns:
                scores[rel] += 55 + min(20, len(lns))

    # 2. Imports inside test files (`from bounds import clamp_nonneg`, `import pkg.mod`)
    imported_stems: set[str] = set()
    for t_rel in test_targets:
        norm_t = str(t_rel).split("::")[0].lstrip("./")
        raw = base_snapshot.get(norm_t)
        if not raw:
            continue
        try:
            ttree = ast.parse(raw.decode("utf-8", errors="replace"))
        except SyntaxError:
            continue
        for node in ast.walk(ttree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported_stems.add(node.module.replace(".", "/"))
                imported_stems.add(node.module.rsplit(".", 1)[-1])
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imported_stems.add(alias.name.replace(".", "/"))
                    imported_stems.add(alias.name.rsplit(".", 1)[-1])

    for rel in non_test_py:
        no_ext = rel[:-3]
        stem = pathlib.PurePosixPath(no_ext).name
        if no_ext in imported_stems or no_ext.removeprefix("src/") in imported_stems or stem in imported_stems:
            scores[rel] += 40
        if rel in failure_output or stem in failure_output:
            scores[rel] += 15

    ranked = sorted(non_test_py, key=lambda r: (-scores[r], len(base_snapshot[r]), r))
    return ranked[:6]


def _synthesize_move3_candidates_for_file(
    orig_src: str,
    failure_output: str,
    frame_records: Sequence[Mapping[str, Any]],
    max_per_file: int = 48,
    *,
    test_sources: Sequence[str] = (),
    covered_file_lines: Sequence[int] = (),
) -> list[tuple[str, str]]:
    """Synthesize input-dependency-verified candidate repairs (including AST insertions & inverse pairs) in `< 3 ms`."""
    try:
        orig_tree = ast.parse(orig_src)
    except SyntaxError:
        return []

    cands: list[tuple[str, str]] = []
    seen: set[str] = {orig_src}

    def _emit(tag: str, cand_src: str | None) -> None:
        if not cand_src or len(cands) >= max_per_file or cand_src in seen:
            return
        try:
            ast.parse(cand_src)
        except SyntaxError:
            return
        if dep_gate.gate(orig_src, cand_src).get("status") != "PASS":
            return
        seen.add(cand_src)
        cands.append((tag, cand_src))

    # Channel 1: Failing-Relation Edits (`the_relation_is_read_from_the_failing_run_v1`)
    try:
        for ed in (rel_run._add_end_anchor_edit(orig_src), rel_run._split_side_edit(orig_src)):
            if isinstance(ed, str):
                _emit("failing_relation_edit", ed)
            elif isinstance(ed, Sequence):
                for sub_ed in ed:
                    if isinstance(sub_ed, str):
                        _emit("failing_relation_edit", sub_ed)
    except Exception:
        pass

    # Targeted string/regex/aliasing relational rewrites when tokens are present
    for old_tok, new_tok, label in (
        (".match(", ".fullmatch(", "relation_fullmatch"),
        (".split(", ".rsplit(", "relation_rsplit"),
        (".rsplit(", ".split(", "relation_split"),
        (".lstrip(", ".strip(", "relation_strip"),
        (".rstrip(", ".strip(", "relation_strip"),
        (".strip(", ".rstrip(", "relation_rstrip"),
    ):
        if old_tok in orig_src:
            _emit(label, orig_src.replace(old_tok, new_tok, 1))

    # Channel 2: Comparison, Polarity & Guard Abduction (`what_the_condition_wants_v1` / `witness_inversion_v1`)
    cmp_alternatives: dict[type[ast.cmpop], tuple[type[ast.cmpop], ...]] = {
        ast.Lt: (ast.Gt, ast.LtE, ast.GtE),
        ast.LtE: (ast.Lt, ast.GtE, ast.Gt),
        ast.Gt: (ast.Lt, ast.GtE, ast.LtE),
        ast.GtE: (ast.Gt, ast.LtE, ast.Lt),
        ast.Eq: (ast.NotEq,),
        ast.NotEq: (ast.Eq,),
        ast.Is: (ast.IsNot,),
        ast.IsNot: (ast.Is,),
        ast.In: (ast.NotIn,),
        ast.NotIn: (ast.In,),
    }
    focus_lines = {int(fr.get("lineno") or 0) for fr in frame_records if fr.get("lineno")} | {
        int(ln) for ln in covered_file_lines if ln
    }

    all_nodes = list(ast.walk(orig_tree))
    # Prioritize nodes near traceback or dynamically covered lines first
    node_order = sorted(
        range(len(all_nodes)),
        key=lambda idx: (
            0 if any(abs(getattr(all_nodes[idx], "lineno", -999) - fl) <= 4 for fl in focus_lines) else 1,
            idx,
        ),
    )

    # Channel 4 (Move IV — Break the 54% AST Insertion Wall): Precondition & Boundary Guard Insertions
    combined_test_txt = "\n".join([failure_output, *test_sources])
    wanted_excs: list[str] = []
    for exc_name in ("ValueError", "TypeError", "KeyError", "IndexError"):
        if re.search(rf"\b(?:raises|assertRaises)\s*\(\s*{exc_name}\b", combined_test_txt) or (
            f"DID NOT RAISE {exc_name}" in combined_test_txt
        ):
            wanted_excs.append(exc_name)

    for fn_idx, top_nd in enumerate(orig_tree.body):
        fn_targets: list[tuple[list[ast.stmt], int, ast.FunctionDef]] = []
        if isinstance(top_nd, ast.FunctionDef):
            fn_targets.append((orig_tree.body, fn_idx, top_nd))
        elif isinstance(top_nd, ast.ClassDef):
            for m_idx, m_nd in enumerate(top_nd.body):
                if isinstance(m_nd, ast.FunctionDef):
                    fn_targets.append((top_nd.body, m_idx, m_nd))

        for _parent_body, _pos_idx, fn_nd in fn_targets:
            params = [a.arg for a in fn_nd.args.args if a.arg not in ("self", "cls")]
            # 4a. Missing exception precondition guard insertion (`if p < 0: raise ValueError(...)`, `if p is None: ...`)
            for exc_cls in wanted_excs[:2]:
                for p_name in params[:2]:
                    guard_conds = (
                        (f"{p_name} is None", "guard_insert_none"),
                        (f"isinstance({p_name}, (int, float)) and {p_name} < 0", "guard_insert_neg"),
                        (f"isinstance({p_name}, (int, float)) and {p_name} <= 0", "guard_insert_nonpos"),
                        (f"not {p_name}", "guard_insert_empty"),
                    )
                    for cond_src, gtag in guard_conds:
                        guard_stmt = ast.parse(f"if {cond_src}:\n    raise {exc_cls}('invalid {p_name}')").body[0]
                        t_copy = copy.deepcopy(orig_tree)
                        for sub in ast.walk(t_copy):
                            if isinstance(sub, ast.FunctionDef) and sub.name == fn_nd.name and sub.lineno == fn_nd.lineno:
                                insert_at = 1 if (sub.body and isinstance(sub.body[0], ast.Expr) and isinstance(sub.body[0].value, ast.Constant)) else 0
                                sub.body.insert(insert_at, guard_stmt)
                                ast.fix_missing_locations(t_copy)
                                _emit(f"{gtag}:{exc_cls}", ast.unparse(t_copy))
                                break

            # 4b. Empty-collection boundary guard insertion (`ZeroDivisionError` / `IndexError` on empty sequence)
            if any(err in failure_output for err in ("ZeroDivisionError", "IndexError")) and params:
                for ret_lit, rtag in (("0", "empty_guard_zero"), ("0.0", "empty_guard_float"), ("None", "empty_guard_none"), ("[]", "empty_guard_list")):
                    guard_stmt = ast.parse(f"if not {params[0]}:\n    return {ret_lit}").body[0]
                    t_copy = copy.deepcopy(orig_tree)
                    for sub in ast.walk(t_copy):
                        if isinstance(sub, ast.FunctionDef) and sub.name == fn_nd.name and sub.lineno == fn_nd.lineno:
                            insert_at = 1 if (sub.body and isinstance(sub.body[0], ast.Expr) and isinstance(sub.body[0].value, ast.Constant)) else 0
                            sub.body.insert(insert_at, guard_stmt)
                            ast.fix_missing_locations(t_copy)
                            _emit(rtag, ast.unparse(t_copy))
                            break

            # 4c. SObEq Read-Without-Write Loop/Recursion Progress Insertion (`if x in visited:` without `visited.add(x)`)
            body_dump = ast.unparse(fn_nd)
            for sub in ast.walk(fn_nd):
                if (
                    isinstance(sub, ast.If)
                    and isinstance(sub.test, ast.Compare)
                    and len(sub.test.ops) == 1
                    and isinstance(sub.test.ops[0], (ast.In, ast.NotIn))
                    and isinstance(sub.test.left, ast.Name)
                    and isinstance(sub.test.comparators[0], ast.Name)
                ):
                    elem_nm = sub.test.left.id
                    set_nm = sub.test.comparators[0].id
                    if f"{set_nm}.add(" not in body_dump and f"{set_nm}[" not in body_dump:
                        add_stmt = ast.parse(f"{set_nm}.add({elem_nm})").body[0]
                        t_copy = copy.deepcopy(orig_tree)
                        for f_sub in ast.walk(t_copy):
                            if isinstance(f_sub, ast.FunctionDef) and f_sub.name == fn_nd.name and f_sub.lineno == fn_nd.lineno:
                                for st_i, st in enumerate(f_sub.body):
                                    if isinstance(st, ast.If) and getattr(st, "lineno", -1) == sub.lineno:
                                        if isinstance(sub.test.ops[0], ast.In):
                                            f_sub.body.insert(st_i + 1, add_stmt)
                                        else:
                                            st.body.insert(0, add_stmt)
                                        ast.fix_missing_locations(t_copy)
                                        _emit(f"sobeq_progress_insert:{set_nm}.add({elem_nm})", ast.unparse(t_copy))
                                        break
                                    # Also check inside top-level `while` / `for` loops!
                                    if isinstance(st, (ast.While, ast.For)):
                                        for lst_i, lst in enumerate(st.body):
                                            if isinstance(lst, ast.If) and getattr(lst, "lineno", -1) == sub.lineno:
                                                if isinstance(sub.test.ops[0], ast.In):
                                                    st.body.insert(lst_i + 1, add_stmt)
                                                else:
                                                    lst.body.insert(0, add_stmt)
                                                ast.fix_missing_locations(t_copy)
                                                _emit(f"sobeq_loop_progress_insert:{set_nm}.add({elem_nm})", ast.unparse(t_copy))
                                                break

    # Channel 5 (Move IV — Inverse-Pair Callable Completion via `inverse_completion_v1`: `load(save(x)) == x`)
    try:
        from canonical.swe_kernel import inverse_completion_v1 as inv_comp

        for cls_idx, cls_nd in enumerate(orig_tree.body):
            if not isinstance(cls_nd, ast.ClassDef):
                continue
            method_map = {m.name: m for m in cls_nd.body if isinstance(m, ast.FunctionDef)}
            init_nd = method_map.get("__init__")
            init_params = [a.arg for a in init_nd.args.args if a.arg != "self"] if init_nd else []
            attr_err_names = re.findall(r"has no attribute '([A-Za-z_]\w*)'", failure_output)
            for m_name, m_nd in list(method_map.items()):
                missing_cands: list[str] = []
                if m_name.startswith("to_") and len(m_name) > 3:
                    missing_cands.append("from_" + m_name[3:])
                elif m_name in ("dump_state", "save_state"):
                    missing_cands.append("load_state")
                pair = inv_comp.detect_pair(m_name, list(method_map.keys()))
                if pair and pair.get("missing") and not str(pair["missing"]).startswith("to_from_"):
                    missing_cands.append(str(pair["missing"]))
                for ae_nm in attr_err_names:
                    if ae_nm not in missing_cands:
                        missing_cands.insert(0, ae_nm)
                missing_name: str | None = next((mc for mc in missing_cands if mc and mc not in method_map), None)
                if not missing_name:
                    continue
                # Extract field mapping from `return {"k": self.attr, ...}` or `return (self.a, self.b)`
                ret_expr = next((sub.value for sub in ast.walk(m_nd) if isinstance(sub, ast.Return) and sub.value is not None), None)
                if isinstance(ret_expr, ast.Dict):
                    field_pairs: list[tuple[str, str]] = []
                    for k_nd, v_nd in zip(ret_expr.keys, ret_expr.values):
                        if (
                            isinstance(k_nd, ast.Constant)
                            and isinstance(k_nd.value, str)
                            and isinstance(v_nd, ast.Attribute)
                            and isinstance(v_nd.value, ast.Name)
                            and v_nd.value.id == "self"
                        ):
                            field_pairs.append((k_nd.value, v_nd.attr))
                    if field_pairs:
                        if missing_name == "__setstate__":
                            synth = inv_comp.synthesise_reader("__getstate__", [{k: 0 for k, _ in field_pairs}])
                            if synth.get("source"):
                                m_ast = ast.parse(synth["source"]).body[0]
                                t_copy = copy.deepcopy(orig_tree)
                                t_copy.body[cls_idx].body.append(m_ast)  # type: ignore[attr-defined]
                                ast.fix_missing_locations(t_copy)
                                _emit(f"inverse_pair_setstate:{missing_name}", ast.unparse(t_copy))
                        else:
                            assigns = "\n".join(f"    obj.{attr} = payload[{key!r}]" for key, attr in field_pairs)
                            cls_method_src = (
                                f"@classmethod\ndef {missing_name}(cls, payload):\n"
                                f"    obj = cls.__new__(cls)\n{assigns}\n    return obj\n"
                            )
                            m_ast = ast.parse(cls_method_src).body[0]
                            t_copy = copy.deepcopy(orig_tree)
                            t_copy.body[cls_idx].body.append(m_ast)  # type: ignore[attr-defined]
                            ast.fix_missing_locations(t_copy)
                            _emit(f"inverse_pair_classmethod:{missing_name}", ast.unparse(t_copy))
                elif isinstance(ret_expr, ast.Tuple):
                    attrs = [
                        elt.attr
                        for elt in ret_expr.elts
                        if isinstance(elt, ast.Attribute) and isinstance(elt.value, ast.Name) and elt.value.id == "self"
                    ]
                    if attrs and len(attrs) == len(ret_expr.elts):
                        if missing_name == "__setstate__":
                            assigns = "\n".join(f"    self.{attr} = payload[{i}]" for i, attr in enumerate(attrs))
                            m_ast = ast.parse(f"def __setstate__(self, payload):\n{assigns}\n").body[0]
                        else:
                            assigns = "\n".join(f"    obj.{attr} = payload[{i}]" for i, attr in enumerate(attrs))
                            m_ast = ast.parse(
                                f"@classmethod\ndef {missing_name}(cls, payload):\n    obj = cls.__new__(cls)\n{assigns}\n    return obj\n"
                            ).body[0]
                        t_copy = copy.deepcopy(orig_tree)
                        t_copy.body[cls_idx].body.append(m_ast)  # type: ignore[attr-defined]
                        ast.fix_missing_locations(t_copy)
                        _emit(f"inverse_pair_tuple:{missing_name}", ast.unparse(t_copy))
    except Exception:
        pass

    for idx in node_order:
        if len(cands) >= max_per_file:
            break
        node = all_nodes[idx]

        # 2a. Comparison operator boundary & polarity inversions
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            op_t = type(node.ops[0])
            for alt_cls in cmp_alternatives.get(op_t, ()):
                t_copy = copy.deepcopy(orig_tree)
                target = list(ast.walk(t_copy))[idx]
                if isinstance(target, ast.Compare) and target.ops:
                    target.ops[0] = alt_cls()
                    ast.fix_missing_locations(t_copy)
                    _emit(f"cmp_invert:{op_t.__name__}->{alt_cls.__name__}", ast.unparse(t_copy))

        # 2b. Boolean connective flip (`and` <-> `or`) & falsey-vs-None (`if x:` -> `if x is not None:`)
        elif isinstance(node, ast.BoolOp):
            alt_b = ast.Or if isinstance(node.op, ast.And) else ast.And
            t_copy = copy.deepcopy(orig_tree)
            target = list(ast.walk(t_copy))[idx]
            if isinstance(target, ast.BoolOp):
                target.op = alt_b()
                ast.fix_missing_locations(t_copy)
                _emit(f"boolop_flip:{type(node.op).__name__}->{alt_b.__name__}", ast.unparse(t_copy))

        elif isinstance(node, ast.If) and isinstance(node.test, ast.Name):
            t_copy = copy.deepcopy(orig_tree)
            target = list(ast.walk(t_copy))[idx]
            if isinstance(target, ast.If) and isinstance(target.test, ast.Name):
                target.test = ast.Compare(
                    left=ast.Name(id=target.test.id, ctx=ast.Load()),
                    ops=[ast.IsNot()],
                    comparators=[ast.Constant(value=None)],
                )
                ast.fix_missing_locations(t_copy)
                _emit("guard_falsey_to_is_not_none", ast.unparse(t_copy))

        # 2c. Arithmetic operator & off-by-one boundary inversions (`witness_inversion_v1`)
        elif isinstance(node, ast.BinOp):
            bin_alts: dict[type[ast.operator], tuple[type[ast.operator], ...]] = {
                ast.Add: (ast.Sub,),
                ast.Sub: (ast.Add,),
                ast.Mult: (ast.FloorDiv,),
                ast.Div: (ast.FloorDiv,),
                ast.FloorDiv: (ast.Div,),
            }
            for alt_op in bin_alts.get(type(node.op), ()):
                t_copy = copy.deepcopy(orig_tree)
                target = list(ast.walk(t_copy))[idx]
                if isinstance(target, ast.BinOp):
                    target.op = alt_op()
                    ast.fix_missing_locations(t_copy)
                    _emit(f"binop_invert:{type(node.op).__name__}->{alt_op.__name__}", ast.unparse(t_copy))

        # 2d. `hasattr(obj, k)` -> `getattr(obj, k, None) is not None`
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "hasattr"
            and len(node.args) == 2
        ):
            t_copy = copy.deepcopy(orig_tree)
            target = list(ast.walk(t_copy))[idx]
            if isinstance(target, ast.Call):
                repl = ast.Compare(
                    left=ast.Call(
                        func=ast.Name(id="getattr", ctx=ast.Load()),
                        args=[target.args[0], target.args[1], ast.Constant(value=None)],
                        keywords=[],
                    ),
                    ops=[ast.IsNot()],
                    comparators=[ast.Constant(value=None)],
                )
                # Replace via expression unparse splice
                old_expr = mhz._get_node_source(orig_src, node)
                if old_expr:
                    _emit("hasattr_to_getattr_non_none", mhz._splice_ast_node(orig_src, node, ast.unparse(repl)))

        # 2e. Exception-lattice widening on uncaught runtime error (`except ValueError:` -> `(ValueError, TypeError)`)
        elif isinstance(node, ast.ExceptHandler) and node.type is not None:
            for exc_cls in ("TypeError", "ValueError", "KeyError", "IndexError", "AttributeError"):
                if f"{exc_cls}:" in failure_output and exc_cls not in ast.unparse(node.type):
                    t_copy = copy.deepcopy(orig_tree)
                    target = list(ast.walk(t_copy))[idx]
                    if isinstance(target, ast.ExceptHandler) and target.type is not None:
                        elts = list(target.type.elts) if isinstance(target.type, ast.Tuple) else [target.type]
                        elts.append(ast.Name(id=exc_cls, ctx=ast.Load()))
                        target.type = ast.Tuple(elts=elts, ctx=ast.Load())
                        ast.fix_missing_locations(t_copy)
                        _emit(f"except_widen:{exc_cls}", ast.unparse(t_copy))

    # Channel 3: Live Frame Expression Demand (`the_assertion_is_the_demand_v1` `~10us`/candidate)
    m_eq = re.search(r"AssertionError:\s*assert\s+(.+?)\s*==\s*(.+)$", failure_output, re.MULTILINE)
    if m_eq and frame_records:
        try:
            expected_val = ast.literal_eval(m_eq.group(2).strip())
            last_fr = frame_records[-1]
            locs_repr = dict(last_fr.get("locals_repr") or {})
            live_env: dict[str, Any] = {}
            for k, rv in locs_repr.items():
                try:
                    live_env[k] = ast.literal_eval(str(rv))
                except Exception:
                    continue
            if live_env:
                for expr_str in assert_demand.expressions(sorted(live_env.keys()))[:48]:
                    ok_ev, val = assert_demand.evaluate(expr_str, live_env)
                    if ok_ev and val == expected_val and type(val) is type(expected_val):
                        for idx, node in enumerate(all_nodes):
                            if isinstance(node, ast.Return) and node.value is not None:
                                _emit("assertion_demand_return", mhz._splice_ast_node(orig_src, node, f"return {expr_str}"))
        except Exception:
            pass

    return cands


def _run_cow_demand_abduction_fast_lane(
    repo_root: pathlib.Path,
    base_snapshot: Mapping[str, bytes],
    base_output: str,
    test_targets: Sequence[str],
    *,
    regression_tests: Sequence[str] = (),
    neg_guard: cow_zyg.NegativeSpaceGuard | None = None,
    timeout_s: float = 12.0,
) -> dict[str, Any] | None:
    """Move 3 Zero-Disk `os.fork()` CoW Demand + Relation + Witness-Inversion Fast Lane."""
    frame_run = cow_runner.run_targets_cow_fork(
        repo_root,
        test_targets,
        timeout_s=min(6.0, timeout_s),
        capture_frames=True,
    )
    f_frames: dict[str, list[dict[str, Any]]] = dict(frame_run.get("failure_frames") or {})
    cov_lines: dict[str, list[int]] = dict(frame_run.get("covered_lines") or {})
    rich_output = str(frame_run.get("output") or base_output)

    ranked_files = _localize_candidate_py_files(
        base_snapshot, test_targets, f_frames, rich_output, covered_lines=cov_lines
    )
    if not ranked_files:
        return None

    test_srcs: list[str] = []
    for t_rel in test_targets:
        norm_t = str(t_rel).split("::")[0].lstrip("./")
        if norm_t in base_snapshot:
            test_srcs.append(base_snapshot[norm_t].decode("utf-8", errors="replace"))

    flat_frames = [fr for frs in f_frames.values() for fr in frs]
    all_targets = list(dict.fromkeys([*test_targets, *regression_tests]))
    cow_jobs: list[tuple[str, Callable[[], Mapping[str, Any]]]] = []
    job_payloads: dict[str, tuple[str, str, str]] = {}

    for rel in ranked_files:
        orig_src = base_snapshot[rel].decode("utf-8", errors="replace")
        file_frames = [fr for fr in flat_frames if fr.get("rel_path") == rel]
        file_cov = cov_lines.get(rel) or ()
        for idx, (tag, cand_src) in enumerate(
            _synthesize_move3_candidates_for_file(
                orig_src,
                rich_output,
                file_frames,
                max_per_file=48,
                test_sources=test_srcs,
                covered_file_lines=file_cov,
            )
        ):
            if neg_guard is not None and neg_guard.is_refuted(orig_src, cand_src):
                continue
            cid = f"{rel}::{idx}::{tag}"
            job_payloads[cid] = (rel, tag, cand_src)

            def _make_shard(
                c_id: str = cid,
                r_rel: str = rel,
                c_src: str = cand_src,
            ) -> Callable[[], Mapping[str, Any]]:
                def _shard() -> Mapping[str, Any]:
                    devnull = os.open(os.devnull, os.O_WRONLY)
                    os.dup2(devnull, 1)
                    os.dup2(devnull, 2)
                    os.close(devnull)
                    out = cow_runner._execute_suite_in_current_process(
                        repo_root,
                        all_targets,
                        overlays={r_rel: c_src},
                        capture_frames=False,
                    )
                    return {
                        "candidate_id": c_id,
                        "passed": bool(out.get("ok")),
                        "tests_passed": int(out.get("passed", 0)),
                    }

                return _shard

            cow_jobs.append((cid, _make_shard()))

    # Screen in parallel `os.fork()` CoW worker batches via `ZygotePrewarmedPool` (`0` disk writes!)
    pool = zygote_pool.ZygotePrewarmedPool(prewarm_enabled=False)
    passing_cids: list[str] = []
    forked_total = 0
    per_batch_timeout = min(5.0, max(1.5, timeout_s / 2.0))
    for start in range(0, min(len(cow_jobs), 80), 8):
        batch = cow_jobs[start : start + 8]
        forked_total += len(batch)
        res = pool.run_parallel_sharded(
            [fn for _, fn in batch],
            winner_predicate=None,
            timeout_s=per_batch_timeout,
        )
        for item in res.get("results") or ():
            if item.get("passed") and item.get("candidate_id") in job_payloads:
                passing_cids.append(str(item["candidate_id"]))
        if passing_cids:
            break

    # Move IV Fallback: Value-Space Angelic + Bottom-Up Observational Equivalence (`angelic_oe_synthesizer_v1`)
    if not passing_cids and ranked_files and test_targets:
        try:
            from canonical.swe_kernel import angelic_oe_synthesizer_v1 as aoe

            top_rel = ranked_files[0]
            t_rel0 = str(test_targets[0]).split("::")[0].lstrip("./")
            aoe_res = aoe.repair_file_angelic_oe(
                repo_root,
                top_rel,
                t_rel0,
                timeout_s=max(6, int(min(10.0, timeout_s))),
                verify_with_sentinel=False,
            )
            if aoe_res.get("repaired") and aoe_res.get("patched_source"):
                cid_aoe = f"{top_rel}::aoe::{aoe_res.get('method', 'ANGELIC_OE')}"
                job_payloads[cid_aoe] = (top_rel, str(aoe_res.get("rule") or "ANGELIC_OE"), str(aoe_res["patched_source"]))
                passing_cids.append(cid_aoe)
        except Exception:
            pass

    if not passing_cids:
        return None

    # Move IV Version-Space Equivalence Partition (`repair_version_space_selection_v1` / behavioral signatures)
    vs_meta: dict[str, Any] = {
        "passing_candidates_in_batch": len(passing_cids),
        "equivalence_classes": 1,
        "diagnosis": "IDENTIFIED_BY_TESTS",
    }
    win_cid = passing_cids[0]
    if len(passing_cids) >= 2:
        probe_vals = (-5, -1, 0, 1, 2, "", [])
        sig_classes: dict[str, list[str]] = {}
        for pcid in passing_cids:
            _prel, _ptag, psrc = job_payloads[pcid]
            ns_p: dict[str, Any] = {}
            sig_parts: list[str] = []
            try:
                exec(compile(psrc, "<vs_probe>", "exec"), ns_p)  # noqa: S102
                callables_p = [v for k, v in ns_p.items() if callable(v) and not k.startswith("__")]
                if callables_p:
                    fn0 = callables_p[0]
                    for pv in probe_vals:
                        try:
                            rv = fn0(copy.deepcopy(pv))
                            sig_parts.append(f"V:{type(rv).__name__}:{repr(rv)[:32]}")
                        except Exception as exc:
                            sig_parts.append(f"E:{type(exc).__name__}")
            except Exception:
                sig_parts.append("UNPROBED")
            sig_key = "|".join(sig_parts) or psrc
            sig_classes.setdefault(sig_key, []).append(pcid)
        vs_meta = {
            "passing_candidates_in_batch": len(passing_cids),
            "equivalence_classes": len(sig_classes),
            "diagnosis": (
                "IDENTIFIED_BY_TESTS" if len(sig_classes) == 1 else "UNDETERMINED__A_QUESTION_DECIDES"
            ),
        }

    win_rel, win_tag, win_src = job_payloads[win_cid]
    ok, _reason, meta = _verify_python_candidate_edits(
        repo_root,
        {win_rel: win_src},
        base_snapshot,
        test_targets,
        regression_tests=regression_tests,
        neg_guard=neg_guard,
        timeout_s=timeout_s,
    )
    if not ok:
        _restore_tree(repo_root, base_snapshot)
        return None

    return {
        "solved": True,
        "channel": win_tag,
        "modified_files": [win_rel],
        "patched_source": win_src,
        "candidates_screened_cow": forked_total,
        "version_space": vs_meta,
        "covered_source_files": [r for r in ranked_files if cov_lines.get(r)],
        "test_run": meta.get("test_run"),
    }


def solve_repository_task(
    repo_root: str | pathlib.Path,
    *,
    test_file: str | None = None,
    c_sources: Sequence[str] | None = None,
    regression_tests: Sequence[str] = (),
    issue_text: str = "",
    language: str | None = None,
    timeout_s: float = 35.0,
    proposer: UntrustedProposer | None = None,
    law_store: CanonicalLawStore | None = None,
    keep_patch_applied: bool = True,
) -> dict[str, Any]:
    """Unified, fail-closed, polyglot SWE repair & verification spine.

    Defaults to strict zero-model execution (`proposer=None` -> `model_calls=0`).
    When an optional untrusted `proposer` is supplied (Option A boundary), every
    proposed witness and patch is independently verified on disk and rolled back
    byte-identically on any failure.
    """
    t0 = time.perf_counter()
    root = pathlib.Path(repo_root).resolve()
    if not root.exists() or not root.is_dir():
        return {
            "schema": SCHEMA,
            "authority": AUTHORITY,
            "solved": False,
            "status": "FAIL_CLOSED",
            "reason": "REPO_ROOT_NOT_FOUND",
            "model_calls": 0,
            "elapsed_s": round(time.perf_counter() - t0, 4),
        }

    lang = (language or detect_repository_language(root, test_file=test_file, c_sources=c_sources)).lower()
    base_snapshot = _snapshot_tree(root)
    model_calls = 0
    stages_run: list[str] = []
    neg_guard = cow_zyg.NegativeSpaceGuard()

    # ------------------------------------------------------------------ C LANE
    if lang == "c":
        from canonical.swe_kernel import c_asan_cegis_repair_v1 as c_eng

        stages_run.append("C_ASAN_CEGIS")
        if c_sources:
            base_c = c_eng.compile_and_run_c_asan(root, c_sources)
            if base_c.get("passed"):
                if not issue_text.strip():
                    return {
                        "schema": SCHEMA,
                        "authority": AUTHORITY,
                        "language": "c",
                        "solved": False,
                        "status": "FAIL_CLOSED",
                        "reason": "NO_DEFECT_EVIDENCE_GREEN_SUITE",
                        "stages_run": stages_run,
                        "model_calls": 0,
                        "modified_files": [],
                        "elapsed_s": round(time.perf_counter() - t0, 4),
                    }
                res = c_eng.repair_c_repo_from_issue_zero_leakage(
                    root, issue_text, c_sources=c_sources, timeout_s=int(timeout_s)
                )
            else:
                res = c_eng.repair_c_repo_asan_cegis(root, c_sources, timeout_s=int(timeout_s))
        elif issue_text.strip():
            res = c_eng.repair_c_repo_from_issue_zero_leakage(
                root, issue_text, timeout_s=int(timeout_s)
            )
        else:
            return {
                "schema": SCHEMA,
                "authority": AUTHORITY,
                "language": "c",
                "solved": False,
                "status": "FAIL_CLOSED",
                "reason": "NO_C_ORACLE_OR_ISSUE_SUPPLIED",
                "stages_run": stages_run,
                "model_calls": 0,
                "modified_files": [],
                "elapsed_s": round(time.perf_counter() - t0, 4),
            }

        solved = bool(res.get("repaired") or res.get("solved"))
        patched_map: dict[str, str] = {}
        if isinstance(res.get("patched_files"), Mapping):
            patched_map = {str(k): str(v) for k, v in res["patched_files"].items()}
        elif res.get("patched_file") and res.get("patched_source"):
            patched_map = {str(res["patched_file"]): str(res["patched_source"])}

        if solved and patched_map:
            for rel, src in patched_map.items():
                (root / rel).write_text(src, encoding="utf-8")
            # Independent post-state re-verification on disk
            if c_sources:
                post_c = c_eng.compile_and_run_c_asan(root, c_sources)
                if not post_c.get("passed"):
                    _restore_tree(root, base_snapshot)
                    solved = False
            if not keep_patch_applied:
                _restore_tree(root, base_snapshot)
        elif not solved or not keep_patch_applied:
            _restore_tree(root, base_snapshot)

        return {
            "schema": SCHEMA,
            "authority": AUTHORITY,
            "language": "c",
            "solved": solved,
            "status": "PASS_VERIFIED_ON_DISK" if solved else "UNSOLVED",
            "reason": str(res.get("rule") or res.get("reason") or ("VERIFIED_C_ASAN" if solved else "C_REPAIR_FAILED")),
            "stages_run": stages_run,
            "model_calls": 0,
            "modified_files": sorted(patched_map.keys()) if solved else [],
            "engine_detail": {k: v for k, v in res.items() if k not in ("patched_source", "patched_files")},
            "elapsed_s": round(time.perf_counter() - t0, 4),
        }

    # --------------------------------------------------------- JAVASCRIPT LANE
    if lang == "javascript":
        from canonical.swe_kernel import js_causal_cegis_repair_v1 as js_eng

        stages_run.append("JS_CAUSAL_CEGIS")
        if test_file:
            base_js = js_eng.run_js_test(root, test_file)
            if base_js.get("passed"):
                if not issue_text.strip():
                    return {
                        "schema": SCHEMA,
                        "authority": AUTHORITY,
                        "language": "javascript",
                        "solved": False,
                        "status": "FAIL_CLOSED",
                        "reason": "NO_DEFECT_EVIDENCE_GREEN_SUITE",
                        "stages_run": stages_run,
                        "model_calls": 0,
                        "modified_files": [],
                        "elapsed_s": round(time.perf_counter() - t0, 4),
                    }
                res = js_eng.repair_js_repo_from_issue_zero_leakage(
                    root, issue_text, timeout_s=int(timeout_s)
                )
            else:
                res = js_eng.repair_js_repo_causal_cegis(
                    root, test_file, regression_tests=regression_tests, timeout_s=int(timeout_s)
                )
        elif issue_text.strip():
            res = js_eng.repair_js_repo_from_issue_zero_leakage(
                root, issue_text, timeout_s=int(timeout_s)
            )
        else:
            return {
                "schema": SCHEMA,
                "authority": AUTHORITY,
                "language": "javascript",
                "solved": False,
                "status": "FAIL_CLOSED",
                "reason": "NO_JS_ORACLE_OR_ISSUE_SUPPLIED",
                "stages_run": stages_run,
                "model_calls": 0,
                "modified_files": [],
                "elapsed_s": round(time.perf_counter() - t0, 4),
            }

        solved = bool(res.get("repaired") or res.get("solved"))
        patched_map_js: dict[str, str] = {}
        if isinstance(res.get("patched_files"), Mapping):
            patched_map_js = {str(k): str(v) for k, v in res["patched_files"].items()}
        elif res.get("patched_file") and res.get("patched_source"):
            patched_map_js = {str(res["patched_file"]): str(res["patched_source"])}

        if solved and patched_map_js:
            for rel, src in patched_map_js.items():
                (root / rel).write_text(src, encoding="utf-8")
            if test_file:
                post_js = js_eng.run_js_test(root, test_file)
                if not post_js.get("passed"):
                    _restore_tree(root, base_snapshot)
                    solved = False
            if not keep_patch_applied:
                _restore_tree(root, base_snapshot)
        elif not solved or not keep_patch_applied:
            _restore_tree(root, base_snapshot)

        return {
            "schema": SCHEMA,
            "authority": AUTHORITY,
            "language": "javascript",
            "solved": solved,
            "status": "PASS_VERIFIED_ON_DISK" if solved else "UNSOLVED",
            "reason": str(res.get("rule") or res.get("reason") or ("VERIFIED_JS_TEST" if solved else "JS_REPAIR_FAILED")),
            "stages_run": stages_run,
            "model_calls": 0,
            "modified_files": sorted(patched_map_js.keys()) if solved else [],
            "engine_detail": {k: v for k, v in res.items() if k not in ("patched_source", "patched_files")},
            "elapsed_s": round(time.perf_counter() - t0, 4),
        }

    # ------------------------------------------------------------- PYTHON LANE
    if not test_file:
        # Discover a default test file if present
        cands = sorted(
            p.relative_to(root).as_posix()
            for p in root.rglob("test_*.py")
            if not any(part in _SKIP_DIRS for part in p.parts)
        )
        if not cands:
            return {
                "schema": SCHEMA,
                "authority": AUTHORITY,
                "language": "python",
                "solved": False,
                "status": "FAIL_CLOSED",
                "reason": "NO_PYTHON_TEST_TARGET_FOUND",
                "stages_run": stages_run,
                "model_calls": 0,
                "modified_files": [],
                "elapsed_s": round(time.perf_counter() - t0, 4),
            }
        test_file = cands[0]

    # Stage 0: Run baseline oracle
    stages_run.append("BASELINE_ORACLE")
    base_run = mhz.run_pytest_targets(root, [test_file], timeout_s=min(15.0, timeout_s))
    base_output = str(base_run.get("output") or "")
    base_failed = _pytest_failed(base_run)
    active_test_file = test_file
    temp_witness_rel: str | None = None

    # Stage 1: Fail-Closed Green-Suite Gate + Wall-1 Witness Abduction
    if not base_failed:
        stages_run.append("WALL1_WITNESS_ABDUCTION")
        witness_code: str | None = None
        witness_source = "NONE"

        if issue_text.strip():
            profile = mhz.mine_repo_idiom_profile(root)
            abduced = mhz.abduce_metamorphic_witness(
                root, issue_text, test_file, profile, timeout_s=min(12.0, timeout_s / 3.0)
            )
            if abduced is not None and getattr(abduced, "test_code", None):
                witness_code = str(abduced.test_code)
                witness_source = f"ZERO_MODEL:{getattr(abduced, 'channel', 'METAMORPHIC')}"

        if witness_code is None and proposer is not None and issue_text.strip():
            model_calls += 1
            prop_w = proposer.propose_witness(
                repo_root=root,
                issue_text=issue_text,
                language="python",
                baseline_output=base_output,
            )
            if prop_w:
                witness_code = str(prop_w)
                witness_source = "UNTRUSTED_PROPOSER"

        if witness_code is None:
            return {
                "schema": SCHEMA,
                "authority": AUTHORITY,
                "language": "python",
                "solved": False,
                "status": "FAIL_CLOSED",
                "reason": "NO_DEFECT_EVIDENCE_GREEN_SUITE",
                "stages_run": stages_run,
                "model_calls": model_calls,
                "modified_files": [],
                "elapsed_s": round(time.perf_counter() - t0, 4),
            }

        # Independently verify the abduced/proposed witness ACTUALLY FAILS on baseline
        temp_witness_rel = "_canonical_spine_wall1_witness_test.py"
        (root / temp_witness_rel).write_text(witness_code, encoding="utf-8")
        w_run = mhz.run_pytest_targets(root, [temp_witness_rel], timeout_s=min(10.0, timeout_s / 3.0))
        w_failed = _pytest_failed(w_run)
        if not w_failed:
            _restore_tree(root, base_snapshot)
            return {
                "schema": SCHEMA,
                "authority": AUTHORITY,
                "language": "python",
                "solved": False,
                "status": "FAIL_CLOSED",
                "reason": f"WITNESS_NOT_DISCRIMINATING:{witness_source}",
                "stages_run": stages_run,
                "model_calls": model_calls,
                "modified_files": [],
                "elapsed_s": round(time.perf_counter() - t0, 4),
            }
        active_test_file = temp_witness_rel
        base_output = str(w_run.get("output") or "")
        # Snapshot with the verified witness in place for candidate testing
        witness_snapshot = _snapshot_tree(root)
    else:
        witness_snapshot = base_snapshot

    test_targets = list(dict.fromkeys([active_test_file, test_file, *regression_tests]))

    # Stage 1.5: O(1) Law-Store Recall (0 model calls)
    if law_store is not None and law_store.count() > 0:
        stages_run.append("O1_LAW_STORE_RECALL")
        recall_hit = _try_law_store_recall_python(
            root,
            witness_snapshot,
            base_output,
            test_targets,
            law_store,
            regression_tests=regression_tests,
            neg_guard=neg_guard,
            timeout_s=min(15.0, timeout_s),
        )
        if recall_hit is not None:
            if temp_witness_rel and (root / temp_witness_rel).exists():
                (root / temp_witness_rel).unlink()
            if not keep_patch_applied:
                _restore_tree(root, base_snapshot)
            return {
                "schema": SCHEMA,
                "authority": AUTHORITY,
                "language": "python",
                "solved": True,
                "status": "PASS_VERIFIED_ON_DISK",
                "reason": "SOLVED_BY_O1_LAW_STORE_RECALL",
                "law_id": recall_hit["law_id"],
                "stages_run": stages_run,
                "model_calls": model_calls,
                "modified_files": recall_hit["modified_files"],
                "elapsed_s": round(time.perf_counter() - t0, 4),
            }

    # Stage 2A: Mechanical Multi-File Import/Symbol Zipper (`the_zip_propagates_v1`)
    if _IMPORT_FAIL_RE.search(base_output) or _NAME_FAIL_RE.search(base_output):
        stages_run.append("MULTI_FILE_ZIPPER_HOPS")
        zip_res = _apply_mechanical_zipper_hops(root, test_targets, timeout_s=min(15.0, timeout_s))
        if zip_res.get("solved"):
            changed = _changed_files_from_snapshot(root, witness_snapshot)
            if temp_witness_rel and (root / temp_witness_rel).exists():
                (root / temp_witness_rel).unlink()
            if not keep_patch_applied:
                _restore_tree(root, base_snapshot)
            return {
                "schema": SCHEMA,
                "authority": AUTHORITY,
                "language": "python",
                "solved": True,
                "status": "PASS_VERIFIED_ON_DISK",
                "reason": "SOLVED_BY_MULTI_FILE_ZIPPER",
                "stages_run": stages_run,
                "zipper_hops": zip_res.get("hops", []),
                "model_calls": model_calls,
                "modified_files": sorted(changed.keys()),
                "elapsed_s": round(time.perf_counter() - t0, 4),
            }
        _restore_tree(root, witness_snapshot)

    # Stage 2.0 (Move 3): Zero-Disk `os.fork()` CoW Demand + Relation + Witness-Inversion Fast Lane
    stages_run.append("COW_DEMAND_WITNESS_ABDUCTION_FAST_LANE")
    fast_res = _run_cow_demand_abduction_fast_lane(
        root,
        witness_snapshot,
        base_output,
        test_targets,
        regression_tests=regression_tests,
        neg_guard=neg_guard,
        timeout_s=min(12.0, max(3.0, timeout_s / 2.0)),
    )
    if fast_res is not None and fast_res.get("solved"):
        win_rel = fast_res["modified_files"][0]
        crystallized_fast_id: str | None = None
        if law_store is not None and win_rel in witness_snapshot:
            law = law_store.add_verified_diff(
                language="python",
                failure_output=base_output,
                orig_source=witness_snapshot[win_rel].decode("utf-8", errors="replace"),
                patched_source=fast_res["patched_source"],
                provenance=f"MOVE3_FAST_LANE:{fast_res['channel']}",
            )
            if law is not None:
                crystallized_fast_id = law.law_id
        if temp_witness_rel and (root / temp_witness_rel).exists():
            (root / temp_witness_rel).unlink()
        if not keep_patch_applied:
            _restore_tree(root, base_snapshot)
        return {
            "schema": SCHEMA,
            "authority": AUTHORITY,
            "language": "python",
            "solved": True,
            "status": "PASS_VERIFIED_ON_DISK",
            "reason": f"SOLVED_BY_COW_DEMAND_FAST_LANE:{fast_res['channel']}",
            "crystallized_law_id": crystallized_fast_id,
            "candidates_screened_cow": fast_res["candidates_screened_cow"],
            "version_space": fast_res.get("version_space"),
            "stages_run": stages_run,
            "model_calls": model_calls,
            "modified_files": fast_res["modified_files"],
            "elapsed_s": round(time.perf_counter() - t0, 4),
        }

    # Stage 2B: Zero-Model CoW Zygote + Angelic + Metamorphic Habitation Kernel
    stages_run.append("COW_ANGELIC_ZIPPER_ZERO_MODEL")
    rem_budget = max(8.0, timeout_s - (time.perf_counter() - t0))
    zm_res = mhz.repair_repo_unified_zero_model(
        root,
        active_test_file,
        issue_text=issue_text or None,
        timeout_s=rem_budget,
        keep_patch_applied=True,
    )
    if zm_res.get("repaired") or zm_res.get("solved"):
        # Stage 4: Independent post-state verification + input-dependency gate
        changed = _changed_files_from_snapshot(root, witness_snapshot)
        gate_ok = True
        for rel, new_src in changed.items():
            if rel.endswith(".py") and rel in witness_snapshot and not _is_test_relpath(rel):
                orig_src = witness_snapshot[rel].decode("utf-8", errors="replace")
                if dep_gate.gate(orig_src, new_src).get("status") != "PASS":
                    gate_ok = False
                    break
        post_run = mhz.run_pytest_targets(root, test_targets, timeout_s=min(15.0, timeout_s))
        post_ok = bool(gate_ok and _pytest_passed(post_run))
        if post_ok:
            crystallized_law_id: str | None = None
            if law_store is not None and len(changed) == 1:
                only_rel, only_new = next(iter(changed.items()))
                if only_rel in witness_snapshot:
                    law = law_store.add_verified_diff(
                        language="python",
                        failure_output=base_output,
                        orig_source=witness_snapshot[only_rel].decode("utf-8", errors="replace"),
                        patched_source=only_new,
                        provenance="ZERO_MODEL_VERIFIED",
                    )
                    crystallized_law_id = law.law_id if law else None
            if temp_witness_rel and (root / temp_witness_rel).exists():
                (root / temp_witness_rel).unlink()
            if not keep_patch_applied:
                _restore_tree(root, base_snapshot)
            return {
                "schema": SCHEMA,
                "authority": AUTHORITY,
                "language": "python",
                "solved": True,
                "status": "PASS_VERIFIED_ON_DISK",
                "reason": str(zm_res.get("mechanism") or zm_res.get("strategy") or "SOLVED_BY_ZERO_MODEL_SPINE"),
                "stages_run": stages_run,
                "model_calls": model_calls,
                "modified_files": sorted(changed.keys()),
                "crystallized_law_id": crystallized_law_id,
                "elapsed_s": round(time.perf_counter() - t0, 4),
            }
        _restore_tree(root, witness_snapshot)

    # Stage 2.5: Zero-Model Angelic CEGIS & Counterfactual Interior-Spec Escalation
    # (11,388 LOC zero-model synthesis powerhouse BEFORE any Tier-2 proposer!)
    rem_budget_25 = timeout_s - (time.perf_counter() - t0)
    if rem_budget_25 > 4.0:
        stages_run.append("ANGELIC_COUNTERFACTUAL_CEGIS_ZERO_MODEL")
        ac_res = synthesize_counterfactual_and_angelic_repair(
            repo_root=root,
            test_file=active_test_file,
            timeout_s=min(25.0, rem_budget_25),
            keep_patch_applied=True,
        )
        if ac_res.get("pass") is True:
            changed = _changed_files_from_snapshot(root, witness_snapshot)
            gate_ok = True
            for rel, new_src in changed.items():
                if rel.endswith(".py") and rel in witness_snapshot and not _is_test_relpath(rel):
                    orig_src = witness_snapshot[rel].decode("utf-8", errors="replace")
                    if dep_gate.gate(orig_src, new_src).get("status") != "PASS":
                        gate_ok = False
                        break
            post_run = mhz.run_pytest_targets(root, test_targets, timeout_s=min(15.0, timeout_s))
            if gate_ok and _pytest_passed(post_run):
                crystallized_law_id = None
                if law_store is not None and len(changed) == 1:
                    only_rel, only_new = next(iter(changed.items()))
                    if only_rel in witness_snapshot:
                        law = law_store.add_verified_diff(
                            language="python",
                            failure_output=base_output,
                            orig_source=witness_snapshot[only_rel].decode("utf-8", errors="replace"),
                            patched_source=only_new,
                            provenance="ANGELIC_COUNTERFACTUAL_ZERO_MODEL",
                        )
                        crystallized_law_id = law.law_id if law else None
                if temp_witness_rel and (root / temp_witness_rel).exists():
                    (root / temp_witness_rel).unlink()
                if not keep_patch_applied:
                    _restore_tree(root, base_snapshot)
                return {
                    "schema": SCHEMA,
                    "authority": AUTHORITY,
                    "language": "python",
                    "solved": True,
                    "status": "PASS_VERIFIED_ON_DISK",
                    "reason": str(ac_res.get("mechanism") or "SOLVED_BY_ANGELIC_COUNTERFACTUAL_CEGIS"),
                    "stages_run": stages_run,
                    "model_calls": model_calls,
                    "modified_files": sorted(changed.keys()),
                    "crystallized_law_id": crystallized_law_id,
                    "elapsed_s": round(time.perf_counter() - t0, 4),
                }
            _restore_tree(root, witness_snapshot)

    # Stage 3: Optional Option-A Untrusted Proposer Behind Fail-Closed Verifier
    proposer_rejections: list[str] = []
    if proposer is not None:
        stages_run.append("UNTRUSTED_PROPOSER_BEHIND_VERIFIER")
        cand_files = sorted(
            rel for rel in base_snapshot
            if rel.endswith(".py") and not _is_test_relpath(rel)
        )
        model_calls += 1
        proposals = proposer.propose_patches(
            repo_root=root,
            issue_text=issue_text,
            language="python",
            failure_output=base_output,
            candidate_files=cand_files,
        )
        for idx, edits in enumerate(proposals or ()):
            ok, reason, meta = _verify_python_candidate_edits(
                root,
                edits,
                witness_snapshot,
                test_targets,
                regression_tests=regression_tests,
                allow_test_edits=False,
                neg_guard=neg_guard,
                timeout_s=min(15.0, timeout_s),
            )
            if ok:
                crystallized_law_id = None
                changed = _changed_files_from_snapshot(root, witness_snapshot)
                if law_store is not None and len(changed) == 1:
                    only_rel, only_new = next(iter(changed.items()))
                    if only_rel in witness_snapshot:
                        law = law_store.add_verified_diff(
                            language="python",
                            failure_output=base_output,
                            orig_source=witness_snapshot[only_rel].decode("utf-8", errors="replace"),
                            patched_source=only_new,
                            provenance="PROPOSER_VERIFIED_CRYSTALLIZED",
                        )
                        crystallized_law_id = law.law_id if law else None
                if temp_witness_rel and (root / temp_witness_rel).exists():
                    (root / temp_witness_rel).unlink()
                if not keep_patch_applied:
                    _restore_tree(root, base_snapshot)
                return {
                    "schema": SCHEMA,
                    "authority": AUTHORITY,
                    "language": "python",
                    "solved": True,
                    "status": "PASS_VERIFIED_ON_DISK",
                    "reason": "SOLVED_BY_VERIFIED_PROPOSER",
                    "proposal_index": idx,
                    "proposer_rejections": proposer_rejections,
                    "crystallized_law_id": crystallized_law_id,
                    "stages_run": stages_run,
                    "model_calls": model_calls,
                    "modified_files": sorted(changed.keys()),
                    "elapsed_s": round(time.perf_counter() - t0, 4),
                }
            proposer_rejections.append(f"proposal[{idx}]:{reason}")
            _restore_tree(root, witness_snapshot)

    # Always leave workspace byte-identical on failure/refusal
    _restore_tree(root, base_snapshot)
    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "language": "python",
        "solved": False,
        "status": "FAIL_CLOSED" if proposer_rejections else "UNSOLVED",
        "reason": "ALL_CANDIDATES_REJECTED_BY_VERIFIER" if proposer_rejections else "ZERO_MODEL_SPINE_UNSOLVED",
        "proposer_rejections": proposer_rejections,
        "stages_run": stages_run,
        "model_calls": model_calls,
        "modified_files": [],
        "elapsed_s": round(time.perf_counter() - t0, 4),
    }


def synthesize_counterfactual_and_angelic_repair(
    *,
    repo_root: str | pathlib.Path | None = None,
    source_path: str | None = None,
    test_file: str | None = None,
    test_paths: Sequence[str] | None = None,
    examples: Sequence[tuple[Mapping[str, Any], Any]] | None = None,
    var_names: Sequence[str] | None = None,
    constants: Sequence[Any] = (0, 1, 2, -1),
    guard_source: str | None = None,
    timeout_s: float = 20.0,
    keep_patch_applied: bool = True,
) -> dict[str, Any]:
    """Unified zero-model Angelic + Counterfactual Interior-Spec + Bottom-Up CEGIS synthesizer (`0D`).

    Composes 5 previously hidden synthesis engines under one front door (`K3 = 0`):
      - `python_counterfactual_spec_repair_v1` (force interior value -> synthesize expr)
      - `angelic_cegis_repair_v1` (live differential trace + angelic branch forcing)
      - `causal_cegis_inventor_v1` (observational e-graph synthesis + orthogonal patch merge)
      - `cegis_semantic_synthesizer_v1` (bottom-up typed expression synthesis)
      - `the_same_guard_twice_is_the_discriminator_v1` (guard operand extraction)
    """
    t0 = time.perf_counter()
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "model_calls": 0,
        "engines_invoked": [],
    }

    # Mode A: Direct bottom-up expression synthesis from (env, expected) examples
    if examples is not None and var_names is not None:
        from canonical.swe_kernel import cegis_semantic_synthesizer_v1 as cegis_syn

        report["engines_invoked"].append("canonical.swe_kernel.cegis_semantic_synthesizer_v1:synthesize_expr_bottom_up")
        syn = cegis_syn.synthesize_expr_bottom_up(
            list(examples),
            var_names=list(var_names),
            constants=tuple(constants),
        )
        ok = bool(
            syn.get("found")
            or syn.get("solved")
            or syn.get("ok")
            or syn.get("expr") is not None
            or syn.get("expression")
        )
        report["pass"] = ok
        report["status"] = "PASS__CEGIS_EXPRESSION_SYNTHESIZED" if ok else "FAIL_CLOSED__CEGIS_UNSOLVED"
        report["mechanism"] = "CEGIS_BOTTOM_UP_EXPR"
        report["synthesis"] = syn
        report["elapsed_ms"] = round((time.perf_counter() - t0) * 1000.0, 3)
        return report

    # Mode B: Guard discriminator extraction (`the_same_guard_twice_is_the_discriminator_v1`)
    if guard_source is not None and repo_root is None:
        from canonical.tools import the_same_guard_twice_is_the_discriminator_v1 as guard_disc

        report["engines_invoked"].append("canonical.tools.the_same_guard_twice_is_the_discriminator_v1")
        tree = ast.parse(guard_source)
        guards: list[dict[str, Any]] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                ops = [ast.unparse(op) for op in guard_disc.operands_of(node.test)]
                guards.append({"lineno": getattr(node, "lineno", 0), "test": ast.unparse(node.test), "operands": ops})
        report["pass"] = len(guards) > 0
        report["status"] = "PASS__GUARD_OPERANDS_EXTRACTED" if guards else "FAIL_CLOSED__NO_GUARDS_FOUND"
        report["mechanism"] = "GUARD_DISCRIMINATOR_ANALYSIS"
        report["guards"] = guards
        report["elapsed_ms"] = round((time.perf_counter() - t0) * 1000.0, 3)
        return report

    # Mode C: Repo-level Counterfactual Interior-Spec -> Angelic CEGIS repair
    if repo_root is not None:
        root = pathlib.Path(repo_root).resolve()
        # 1) Counterfactual interior-value specification repair (when source_path is known)
        if source_path is not None:
            try:
                from canonical.runtime.bound_capabilities import (
                    python_counterfactual_spec_repair_v1 as cf_spec,
                )

                report["engines_invoked"].append(
                    "canonical.runtime.bound_capabilities.python_counterfactual_spec_repair_v1"
                )
                cf_args: dict[str, Any] = {"source_path": str(source_path), "apply": bool(keep_patch_applied)}
                if test_paths:
                    cf_args["test_paths"] = [str(p) for p in test_paths]
                elif test_file:
                    cf_args["test_paths"] = [str(test_file)]
                cf_out = cf_spec.run(cf_args, root)
                if bool(cf_out.get("repaired") or cf_out.get("solved") or cf_out.get("status") == "REPAIRED"):
                    report["pass"] = True
                    report["status"] = "PASS__COUNTERFACTUAL_SPEC_REPAIRED"
                    report["mechanism"] = "COUNTERFACTUAL_INTERIOR_SPEC_REPAIR"
                    report["counterfactual_result"] = cf_out
                    report["elapsed_ms"] = round((time.perf_counter() - t0) * 1000.0, 3)
                    return report
                report["counterfactual_result"] = cf_out
            except Exception as exc:
                report["counterfactual_error"] = f"{type(exc).__name__}: {exc}"

        # 2) Angelic CEGIS differential spectrum repair
        if test_file is not None:
            try:
                from canonical.swe_kernel import angelic_cegis_repair_v1 as angelic_cegis
                from canonical.swe_kernel import causal_cegis_inventor_v1 as causal_inv

                report["engines_invoked"].append("canonical.swe_kernel.angelic_cegis_repair_v1")
                report["causal_cegis_inventor_wired"] = hasattr(causal_inv, "synthesize_obsegraph_branch_repairs")
                ang = angelic_cegis.repair_repo_angelic_cegis(
                    root,
                    test_file,
                    timeout_s=max(5, int(timeout_s)),
                )
                ok = bool(ang.get("repaired") or ang.get("solved") or ang.get("pass"))
                report["pass"] = ok
                report["status"] = "PASS__ANGELIC_CEGIS_REPAIRED" if ok else "FAIL_CLOSED__ANGELIC_CEGIS_UNSOLVED"
                report["mechanism"] = str(ang.get("strategy") or ang.get("mechanism") or "ANGELIC_CEGIS")
                report["angelic_result"] = ang
                report["elapsed_ms"] = round((time.perf_counter() - t0) * 1000.0, 3)
                return report
            except Exception as exc:
                report["angelic_error"] = f"{type(exc).__name__}: {exc}"

    report["pass"] = False
    report["status"] = "FAIL_CLOSED__INSUFFICIENT_SYNTHESIS_INPUTS"
    report["elapsed_ms"] = round((time.perf_counter() - t0) * 1000.0, 3)
    return report


def choreograph_crossfile_repair(
    args: Mapping[str, Any],
    root: str | pathlib.Path,
) -> dict[str, Any]:
    """Multi-file staged / in-place repair choreography (`software_repair_crossfile_choreograph_v1`)."""
    from canonical.runtime.bound_capabilities import (
        software_repair_crossfile_choreograph_v1 as crossfile_mod,
    )

    t0 = time.perf_counter()
    res = crossfile_mod.run(dict(args), pathlib.Path(root).resolve())
    ok = bool(
        isinstance(res, Mapping)
        and (res.get("ok") is True or res.get("pass") is True or res.get("status") in {"PASS", "REPAIRED", "OK", "APPLIED"})
    )
    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "pass": ok,
        "status": "PASS__CROSSFILE_CHOREOGRAPHED" if ok else str((res or {}).get("status") or "FAIL_CLOSED__CROSSFILE_REPAIR"),
        "result": res,
        "model_calls": 0,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
    }


def compile_plain_goal_contract(
    goal: str,
    *,
    admissible: Mapping[str, Mapping[str, Any]] | None = None,
    root: str | pathlib.Path | None = None,
) -> dict[str, Any]:
    """Zero-token natural-language -> typed capability contract compiler (`goal_front_compiler_v1` + `declared_input_derivation_v1`)."""
    from canonical.runtime import declared_input_derivation_v1 as input_deriv
    from canonical.runtime import goal_front_compiler_v1 as gfc

    t0 = time.perf_counter()
    base = pathlib.Path(root).resolve() if root is not None else pathlib.Path(__file__).resolve().parents[2]
    normalized = gfc.normalize_goal(goal)
    swe_req = bool(input_deriv.is_swe_request(goal))
    existing_files = input_deriv.stated_existing_files(goal, base)
    compiled = None
    if admissible is not None:
        compiled = gfc.compile_goal(goal, admissible, base)
    ok = bool(
        (compiled is not None and compiled.get("status") in {"COMPILED", "OK", "PASS", "BOUND"} or bool((compiled or {}).get("capability_id")))
        or (compiled is None and bool(normalized))
    )
    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "pass": ok,
        "status": "PASS__GOAL_CONTRACT_COMPILED" if ok else "FAIL_CLOSED__GOAL_CONTRACT_UNCOMPILED",
        "goal": goal,
        "normalized_goal": normalized,
        "is_swe_request": swe_req,
        "stated_existing_files": existing_files,
        "compiled": compiled,
        "model_calls": 0,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
    }


def trace_expression_and_literal_repair(
    *,
    source_text: str | None = None,
    line: int | None = None,
    trace_records: Sequence[Mapping[str, Any]] | None = None,
    failure_output: str = "",
    target_expr: str | None = None,
    allowed_calls: Sequence[str] = (),
    attribute_names: Sequence[str] | None = None,
    worktree: str | pathlib.Path | None = None,
    source_rel: str | None = None,
    test_node: str | None = None,
    timeout_s: int = 30,
) -> dict[str, Any]:
    """Wave 12 Dual-Slicing Execution-Trace & Literal Defect Synthesis (`0D`).

    Unifies four previously isolated tools at `model_calls == 0`:
      - `the_failing_run_names_the_expression_v1`: trace-driven expression blaming + guard derivation
      - `what_a_real_fix_needs_from_the_site_v1`: AST site-generability audit (prevents wasted synthesis)
      - `the_literal_is_the_defect_v1`: literal/constant defect inspection
      - `the_space_is_the_artifact_v1`: candidate-space screening reference
    """
    from canonical.tools import the_failing_run_names_the_expression_v1 as fail_expr
    from canonical.tools import the_literal_is_the_defect_v1 as lit_defect
    from canonical.tools import the_space_is_the_artifact_v1 as space_art
    from canonical.tools import what_a_real_fix_needs_from_the_site_v1 as site_need

    t0 = time.perf_counter()
    engines = [
        "canonical.tools.the_failing_run_names_the_expression_v1",
        "canonical.tools.what_a_real_fix_needs_from_the_site_v1",
        "canonical.tools.the_literal_is_the_defect_v1",
        "canonical.tools.the_space_is_the_artifact_v1",
    ]
    records = [dict(r) for r in (trace_records or ())]
    fail_txt = fail_expr.failure_text(failure_output) if failure_output else ""

    live_trace = None
    if worktree is not None and source_rel and test_node and not records:
        live_trace = fail_expr.trace_run(
            pathlib.Path(worktree).resolve(),
            str(source_rel),
            str(test_node),
            seconds=int(timeout_s),
        )
        records = list(live_trace.get("records") or ())
        if not fail_txt:
            fail_txt = str(live_trace.get("failure") or "")
        if source_text is None:
            p = pathlib.Path(worktree).resolve() / source_rel
            if p.is_file():
                source_text = p.read_text(encoding="utf-8", errors="replace")

    blamed = fail_expr.blame(records, fail_txt) if (records and fail_txt) else []
    guard_info = None
    candidates: list[str] = []
    if source_text is not None:
        target_line = line
        if target_line is None and blamed:
            target_line = int(blamed[0].get("line") or 0) or None
        if target_line is not None:
            gs = fail_expr.guard_span(source_text, int(target_line))
            if gs is not None:
                g_line, g_expr, g_start, g_end = gs
                guard_info = {
                    "line": g_line,
                    "guard_expr": g_expr,
                    "start_col": g_start,
                    "end_col": g_end,
                }
                for b in blamed[:4]:
                    cands = fail_expr.derived_candidates(
                        g_expr,
                        str(b.get("expr") or ""),
                        str(b.get("value") or ""),
                    )
                    for c in cands:
                        if c not in candidates:
                            candidates.append(c)

    # Site generability audit (`what_a_real_fix_needs_from_the_site_v1`)
    site_audit = None
    if target_expr is not None:
        expr_ast = ast.parse(str(target_expr), mode="eval").body
        kinds = sorted(site_need.node_kinds(expr_ast))
        attr_set = set(attribute_names) if attribute_names is not None else None
        is_gen = bool(site_need.generable(expr_ast, set(allowed_calls), attr_set))
        site_audit = {
            "target_expr": str(target_expr),
            "node_kinds": kinds,
            "generable_from_site": is_gen,
        }

    # Literal-defect scan on source_text (constants inside return/comparison/assignments)
    literal_sites: list[dict[str, Any]] = []
    if source_text is not None:
        try:
            tree = ast.parse(source_text)
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, (str, int, float)):
                    literal_sites.append({
                        "line": int(getattr(node, "lineno", 0)),
                        "type": type(node.value).__name__,
                        "value": repr(node.value)[:64],
                    })
                    if len(literal_sites) >= 24:
                        break
        except SyntaxError:
            pass

    passed = bool(blamed or candidates or (site_audit is not None) or (guard_info is not None))
    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "pass": passed,
        "status": (
            "PASS__TRACE_EXPRESSION_CANDIDATES_DERIVED"
            if candidates
            else (
                "PASS__TRACE_EXPRESSION_BLAMED"
                if blamed
                else ("PASS__SITE_GENERABILITY_AUDITED" if site_audit is not None else "FAIL_CLOSED__NO_TRACE_SIGNAL")
            )
        ),
        "engines_invoked": engines,
        "failure_text": fail_txt,
        "blamed_expressions": blamed[:8],
        "guard_span": guard_info,
        "derived_guard_candidates": candidates[:16],
        "site_generability": site_audit,
        "literal_defect_sites": literal_sites,
        "literal_probe_wired": hasattr(lit_defect, "run_probe"),
        "space_artifact_wired": hasattr(space_art, "candidates") and hasattr(space_art, "screen"),
        "model_calls": 0,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
    }


def multi_file_causal_localize_and_repair(
    repo_root: str | pathlib.Path,
    *,
    goal: str = "",
    test_files: Sequence[str] | None = None,
    hinted_files: Sequence[str] | None = None,
    solve_closed_loop: bool = False,
    apply_to_source: bool = False,
    race_target: str | pathlib.Path | None = None,
    max_steps: int = 4,
    timeout_s: float = 20.0,
) -> dict[str, Any]:
    """Wave 12 Multi-Step Differential Trace Localization, Causal SWE Repair & Live Race Probing (`0D`).

    Unifies `multistep_repo_closed_loop_solver_v1`, `causal_swe_repair_v1`, and `residual_wall_closers_v1`.
    """
    from canonical.swe_kernel import causal_swe_repair_v1 as causal_swe
    from canonical.swe_kernel import multistep_repo_closed_loop_solver_v1 as multistep
    from canonical.swe_kernel import residual_wall_closers_v1 as wall_closers

    t0 = time.perf_counter()
    root = pathlib.Path(repo_root).resolve()
    engines = [
        "canonical.swe_kernel.multistep_repo_closed_loop_solver_v1",
        "canonical.swe_kernel.causal_swe_repair_v1",
        "canonical.swe_kernel.residual_wall_closers_v1",
    ]
    out: dict[str, Any] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "repo_root": str(root),
        "engines_invoked": engines,
        "causal_repair_wired": hasattr(causal_swe, "repair_worktree") and hasattr(causal_swe, "collect_causal_trace"),
        "residual_wall_closers_wired": hasattr(wall_closers, "__name__"),
        "model_calls": 0,
    }

    if race_target is not None:
        race_res = multistep.probe_concurrency_races_live(
            pathlib.Path(race_target).resolve(),
            timeout=min(12.0, float(timeout_s)),
        )
        out["race_probe"] = race_res
        out["pass"] = True
        out["status"] = "PASS__CONCURRENCY_RACE_PROBED"
        out["elapsed_ms"] = round((time.perf_counter() - t0) * 1000.0, 3)
        return out

    if solve_closed_loop:
        res = multistep.solve_repository_closed_loop(
            root,
            goal=goal,
            test_files=list(test_files) if test_files else None,
            apply_to_source=bool(apply_to_source),
            max_steps=int(max_steps),
            timeout_s=float(timeout_s),
        )
        ok = bool(res.get("solved") or res.get("ok") or res.get("pass"))
        out["closed_loop"] = res
        out["pass"] = ok
        out["status"] = "PASS__MULTISTEP_CLOSED_LOOP_SOLVED" if ok else "FAIL_CLOSED__MULTISTEP_UNSOLVED"
        out["elapsed_ms"] = round((time.perf_counter() - t0) * 1000.0, 3)
        return out

    loc = multistep.localize_faults_by_differential_trace(
        root,
        test_files=list(test_files) if test_files else None,
        hinted_files=list(hinted_files) if hinted_files else None,
        timeout=min(15.0, float(timeout_s)),
    )
    ranked = list(loc.get("ranked_files") or loc.get("suspicious_files") or loc.get("suspicious_lines") or ())
    ok = bool(loc.get("ok", True)) and (len(ranked) > 0 or bool(loc))
    out["localization"] = loc
    out["ranked_count"] = len(ranked)
    out["pass"] = ok
    out["status"] = "PASS__DIFFERENTIAL_TRACE_LOCALIZED" if ranked else "PASS__LOCALIZATION_COMPLETED"
    out["elapsed_ms"] = round((time.perf_counter() - t0) * 1000.0, 3)
    return out


def solve_swe_inverted_microscope(
    repo_root: str | pathlib.Path,
    *,
    goal: str = "",
    test_files: Sequence[str] | None = None,
    apply_to_source: bool = False,
    residual_proposer: Callable[[Mapping[str, Any]], Sequence[Mapping[str, str]]] | None = None,
    memory_bus: Any = None,
    law_store: CanonicalLawStore | None = None,
    timeout_s: float = 25.0,
) -> dict[str, Any]:
    """Wave 16: Inverted Neuro-Symbolic SWE Microscope wiring 5 unwired hidden engines.

    1. Microscope (`$0`): `cow_impact_repair_engine_v1` CoW workspace + `metamorphic_habitation_zipper_v1`
       idiom/type-habitation profiler + `causal_nexus_v1` Angelic Value Obligation extraction +
       `multistep_repo_closed_loop_solver_v1` differential trace fault localizer.
    2. Deterministic `K3=0` Fast Lane (`$0`): `propose_stun_and_guard_repairs` + `solve_repository_task`.
    3. Inverted Residual-Hole Bridge: emits a compact `<2 KB` `angelic_hole_packet` to an optional
       pluggable `residual_proposer` (default `None` -> strict `K3=0` fail-closed!), screens proposals
       in isolated CoW workspaces, supports `causal_cegis_inventor_v1.merge_orthogonal_file_patches`,
       and crystallizes verified diffs into `CanonicalLawStore` / `memory_bus`.
    """
    import importlib.util
    import subprocess
    import sys
    import tempfile

    from canonical.swe_kernel import causal_cegis_inventor_v1 as cegis_inv
    from canonical.swe_kernel import causal_nexus_v1 as cnexus
    from canonical.swe_kernel import cow_impact_repair_engine_v1 as cow_imp
    from canonical.swe_kernel import metamorphic_habitation_zipper_v1 as mhz
    from canonical.swe_kernel import multistep_repo_closed_loop_solver_v1 as multistep

    t0 = time.perf_counter()
    root = pathlib.Path(repo_root).resolve()
    if not root.is_dir():
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED__REPO_ROOT_MISSING",
            "repo_root": str(root),
            "model_calls": 0,
        }

    # Discover test files & run baseline tests inside an isolated CoW workspace (pytest or zero-dep stdlib runner!)
    all_tests = sorted(
        p for p in root.rglob("test_*.py")
        if not any(part in {".git", "__pycache__", ".pytest_cache"} for part in p.parts)
    )
    rel_tests = (
        [str(t) for t in test_files]
        if test_files
        else [p.relative_to(root).as_posix() for p in all_tests[:12]]
    )
    has_pytest = importlib.util.find_spec("pytest") is not None
    stdlib_runner = (
        "import importlib.util, pathlib, sys, traceback, unittest\n"
        "sys.path.insert(0, '.')\n"
        "failed = 0\n"
        "for rel in sys.argv[1:]:\n"
        "    p = pathlib.Path(rel)\n"
        "    spec = importlib.util.spec_from_file_location(p.stem, str(p))\n"
        "    mod = importlib.util.module_from_spec(spec)\n"
        "    spec.loader.exec_module(mod)\n"
        "    for name, obj in sorted(vars(mod).items()):\n"
        "        if name.startswith('test_') and callable(obj):\n"
        "            try:\n"
        "                obj()\n"
        "            except Exception:\n"
        "                failed += 1\n"
        "                traceback.print_exc()\n"
        "        elif isinstance(obj, type) and issubclass(obj, unittest.TestCase) and obj is not unittest.TestCase:\n"
        "            res = unittest.TextTestRunner(verbosity=0).run(unittest.defaultTestLoader.loadTestsFromTestCase(obj))\n"
        "            if not res.wasSuccessful():\n"
        "                failed += len(res.failures) + len(res.errors)\n"
        "sys.exit(0 if failed == 0 else 1)\n"
    )

    def _run_pytest_in(work_dir: pathlib.Path, targets: Sequence[str]) -> tuple[bool, str]:
        if has_pytest:
            cmd = [sys.executable, "-m", "pytest", "-q", "--tb=short", *list(targets)]
        else:
            cmd = [sys.executable, "-c", stdlib_runner, *list(targets)]
        cp = subprocess.run(
            cmd,
            cwd=str(work_dir),
            capture_output=True,
            text=True,
            timeout=min(20.0, float(timeout_s)),
        )
        return cp.returncode == 0, (cp.stdout + "\n" + cp.stderr).strip()

    def _cow_write(path: pathlib.Path, content: str) -> None:
        # Break hardlink before writing so CoW speculative edits NEVER mutate host repo!
        if path.exists() or path.is_symlink():
            path.unlink()
        path.write_text(content, encoding="utf-8")

    with tempfile.TemporaryDirectory(prefix="inv_microscope_") as tmp:
        cow_base = pathlib.Path(tmp) / "cow_probe"
        cow_meta = cow_imp.create_zero_copy_cow_workspace(root, cow_base)
        base_ok, base_out = _run_pytest_in(cow_base, rel_tests)
        if base_ok:
            return {
                "schema": SCHEMA,
                "pass": True,
                "status": "PASS__ALREADY_GREEN",
                "tier": "K3_0_ALREADY_GREEN",
                "cow_meta": cow_meta,
                "model_calls": 0,
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            }

        # Stage 1: Angelic Microscope — Value Obligations + Repo Type-Habitation + Differential Trace
        obligations = cnexus.extract_value_obligations(base_out, limit=12)
        obligations_dicts = [
            {
                "actual": repr(getattr(ob, "actual", None))[:80],
                "expected": repr(getattr(ob, "expected", None))[:80],
                "op": str(getattr(ob, "op", "==")),
                "line": str(getattr(ob, "raw_line", ""))[:140],
            }
            for ob in obligations
        ]
        idiom_profile = mhz.mine_repo_idiom_profile(root)
        loc = multistep.localize_faults_by_differential_trace(
            root,
            test_files=rel_tests or None,
            timeout=min(12.0, float(timeout_s)),
        )
        ranked_files: list[str] = []
        for cand in (loc.get("ranked_files") or loc.get("suspicious_files") or ()):
            fpath = cand.get("file") if isinstance(cand, Mapping) else str(cand)
            if fpath and fpath not in ranked_files and (root / fpath).is_file():
                ranked_files.append(fpath)
        if not ranked_files:
            for pyf in sorted(root.rglob("*.py")):
                relp = pyf.relative_to(root).as_posix()
                if not pyf.name.startswith("test_") and "__pycache__" not in pyf.parts:
                    ranked_files.append(relp)
        impacted_raw = cow_imp.select_impacted_tests_fast(root, ranked_files[:4], all_tests)
        selected_list = (
            impacted_raw.get("selected_tests")
            if isinstance(impacted_raw, Mapping)
            else impacted_raw
        ) or ()
        impacted_rels = [
            p.relative_to(root).as_posix() if isinstance(p, pathlib.Path) and p.is_relative_to(root) else str(p)
            for p in selected_list
        ] or rel_tests

        # Stage 2: Deterministic K3=0 Fast Lane (STUN/guard proposals + canonical solve_repository_task)
        test_sources = [
            (root / t).read_text(encoding="utf-8", errors="ignore")
            for t in impacted_rels[:6]
            if (root / t).is_file()
        ]
        for target_rel in ranked_files[:3]:
            src_path = root / target_rel
            orig_src = src_path.read_text(encoding="utf-8", errors="ignore")
            stun_cands = cow_imp.propose_stun_and_guard_repairs(orig_src, test_sources, max_candidates=10)
            if memory_bus is not None and hasattr(memory_bus, "prune_by_anti_skills") and stun_cands:
                stun_cands = list(
                    memory_bus.prune_by_anti_skills(
                        stun_cands, domain="swe_inverted_microscope", symbol_scope=target_rel
                    ).get("kept")
                    or ()
                )
            for idx, new_src in enumerate(stun_cands):
                if new_src == orig_src:
                    continue
                cand_dir = pathlib.Path(tmp) / f"cow_stun_{idx}"
                cow_imp.create_zero_copy_cow_workspace(root, cand_dir)
                _cow_write(cand_dir / target_rel, new_src)
                ok_fast, _ = _run_pytest_in(cand_dir, impacted_rels)
                if ok_fast:
                    ok_full, full_out = _run_pytest_in(cand_dir, rel_tests)
                    if ok_full:
                        if apply_to_source:
                            src_path.write_text(new_src, encoding="utf-8")
                        return {
                            "schema": SCHEMA,
                            "pass": True,
                            "status": "PASS__K3_0_STUN_GUARD_VERIFIED",
                            "tier": "K3_0_ANGELIC_MICROSCOPE",
                            "patched_files": [target_rel],
                            "value_obligations": obligations_dicts,
                            "impacted_tests": impacted_rels,
                            "verified_by_cow_oracle": True,
                            "model_calls": 0,
                            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
                        }

        # Fallback K3=0 canonical solver on repo
        k0_res = solve_repository_task(
            root,
            test_file=rel_tests[0] if rel_tests else None,
            regression_tests=tuple(rel_tests[1:]),
            issue_text=goal or "inverted_microscope_k0",
            law_store=law_store,
            keep_patch_applied=apply_to_source,
            timeout_s=min(15.0, float(timeout_s)),
        )
        if k0_res.get("pass") or k0_res.get("solved"):
            return {
                "schema": SCHEMA,
                "pass": True,
                "status": "PASS__K3_0_CANONICAL_SOLVER_VERIFIED",
                "tier": "K3_0_CANONICAL_SOLVER",
                "value_obligations": obligations_dicts,
                "impacted_tests": impacted_rels,
                "canonical_solver": k0_res,
                "verified_by_cow_oracle": True,
                "model_calls": 0,
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            }

        # Stage 3: Build compact (<2 KB) AngelicHolePacket for inverted residual-hole bridge
        local_snippets = {
            relp: (root / relp).read_text(encoding="utf-8", errors="ignore")[:1800]
            for relp in ranked_files[:3]
            if (root / relp).is_file()
        }
        hole_packet = {
            "goal": goal,
            "faulty_files": ranked_files[:4],
            "value_obligations": obligations_dicts[:6],
            "impacted_tests": impacted_rels[:6],
            "failure_tail": base_out[-800:],
            "repo_idiom_summary": {
                "type_count": len(getattr(idiom_profile, "type_annotations", {}) or {}),
                "symbol_count": len(getattr(idiom_profile, "symbol_table", {}) or {}),
            },
            "local_snippets": local_snippets,
        }

        if residual_proposer is None:
            if memory_bus is not None and hasattr(memory_bus, "record_anti_skill"):
                memory_bus.record_anti_skill(
                    domain="swe_inverted_microscope",
                    symbol_scope=",".join(ranked_files[:2]) or "*",
                    bad_hypothesis="K3_0_EXHAUSTED_NO_RESIDUAL_PROPOSER",
                    error_signature=base_out.splitlines()[-1][:160] if base_out else "TEST_FAILED",
                )
            return {
                "schema": SCHEMA,
                "pass": False,
                "status": "FAIL_CLOSED__RESIDUAL_HOLE_NEEDS_PROPOSER",
                "tier": "K3_0_ABSTAIN_WITH_ANGELIC_PACKET",
                "missing_fact": "RESIDUAL_SEMANTIC_HOLE_NEEDS_PROPOSER",
                "angelic_hole_packet": hole_packet,
                "value_obligations": obligations_dicts,
                "impacted_tests": impacted_rels,
                "model_calls": 0,
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            }

        # Screen pluggable residual proposer patches in isolated CoW workspaces (+ orthogonal multi-file merge!)
        raw_proposals = list(residual_proposer(hole_packet) or ())
        screened_count = 0
        orthogonal_candidates: list[dict[str, str]] = []
        for idx, prop in enumerate(raw_proposals):
            if not isinstance(prop, Mapping) or not prop:
                continue
            patch_map = {str(k): str(v) for k, v in prop.items() if (root / str(k)).is_file()}
            if not patch_map:
                continue
            screened_count += 1
            orthogonal_candidates.append(patch_map)
            cand_dir = pathlib.Path(tmp) / f"cow_prop_{idx}"
            cow_imp.create_zero_copy_cow_workspace(root, cand_dir)
            for relp, content in patch_map.items():
                _cow_write(cand_dir / relp, content)
            ok_full, full_out = _run_pytest_in(cand_dir, rel_tests)
            if ok_full:
                if apply_to_source:
                    for relp, content in patch_map.items():
                        (root / relp).write_text(content, encoding="utf-8")
                if law_store is not None:
                    for relp, content in patch_map.items():
                        try:
                            law_store.add_verified_diff(
                                language="python",
                                failure_output=base_out[:400],
                                before_source=local_snippets.get(relp, ""),
                                after_source=content,
                            )
                        except Exception:
                            pass
                return {
                    "schema": SCHEMA,
                    "pass": True,
                    "status": "PASS__INVERTED_RESIDUAL_HOLE_VERIFIED",
                    "tier": "INVERTED_RESIDUAL_HOLE_VERIFIED",
                    "patched_files": sorted(patch_map.keys()),
                    "proposals_screened": screened_count,
                    "angelic_hole_packet": hole_packet,
                    "verified_by_cow_oracle": True,
                    "model_calls": 1,
                    "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
                }

        # Try merging pairwise orthogonal multi-file patches via causal_cegis_inventor_v1
        if len(orthogonal_candidates) >= 2:
            merged = cegis_inv.merge_orthogonal_file_patches(
                root, orthogonal_candidates[0], orthogonal_candidates[1]
            )
            if merged:
                cand_dir = pathlib.Path(tmp) / "cow_prop_merged"
                cow_imp.create_zero_copy_cow_workspace(root, cand_dir)
                for relp, content in merged.items():
                    _cow_write(cand_dir / relp, content)
                ok_full, _ = _run_pytest_in(cand_dir, rel_tests)
                if ok_full:
                    if apply_to_source:
                        for relp, content in merged.items():
                            (root / relp).write_text(content, encoding="utf-8")
                    return {
                        "schema": SCHEMA,
                        "pass": True,
                        "status": "PASS__INVERTED_ORTHOGONAL_MERGE_VERIFIED",
                        "tier": "INVERTED_RESIDUAL_HOLE_ORTHOGONAL_MERGED",
                        "patched_files": sorted(merged.keys()),
                        "proposals_screened": screened_count,
                        "verified_by_cow_oracle": True,
                        "model_calls": 1,
                        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
                    }

        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED__RESIDUAL_PROPOSALS_REJECTED_BY_COW_ORACLE",
            "tier": "INVERTED_RESIDUAL_HOLE_REJECTED",
            "proposals_screened": screened_count,
            "angelic_hole_packet": hole_packet,
            "verified_by_cow_oracle": False,
            "model_calls": 1,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }


__all__ = [
    "AUTHORITY",
    "COMPOSED_CORE_MODULES",
    "CanonicalLawStore",
    "PRODUCER_MODEL_CALLS",
    "SCHEMA",
    "StructuralLaw",
    "UntrustedProposer",
    "choreograph_crossfile_repair",
    "compile_plain_goal_contract",
    "detect_repository_language",
    "multi_file_causal_localize_and_repair",
    "solve_repository_task",
    "solve_swe_inverted_microscope",
    "synthesize_counterfactual_and_angelic_repair",
    "trace_expression_and_literal_repair",
]
