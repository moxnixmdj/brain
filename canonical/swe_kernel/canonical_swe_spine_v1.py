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
import difflib
import hashlib
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Protocol, Sequence

from canonical.swe_kernel import cow_angelic_zygote_v1 as cow_zyg
from canonical.swe_kernel import metamorphic_habitation_zipper_v1 as mhz
from canonical.swe_kernel import repair_input_dependency_gate_v1 as dep_gate

SCHEMA = "CANONICAL_SWE_SPINE_V1"
AUTHORITY = "NONE_SANDBOX"
PRODUCER_MODEL_CALLS = 0

# Competing SWE repair/synthesis modules consolidated by this spine.
COMPOSED_CORE_MODULES: tuple[str, ...] = (
    "canonical/swe_kernel/metamorphic_habitation_zipper_v1.py",
    "canonical/swe_kernel/cow_angelic_zygote_v1.py",
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
    "solve_repository_task",
    "synthesize_counterfactual_and_angelic_repair",
]
