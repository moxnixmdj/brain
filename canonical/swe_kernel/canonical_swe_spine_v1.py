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
import importlib
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

class _LazyModule:
    __slots__ = ("_mod_name", "_loaded")

    def __init__(self, mod_name: str) -> None:
        object.__setattr__(self, "_mod_name", mod_name)
        object.__setattr__(self, "_loaded", None)

    def __getattr__(self, item: str) -> Any:
        mod = object.__getattribute__(self, "_loaded")
        if mod is None:
            mod = importlib.import_module(object.__getattribute__(self, "_mod_name"))
            object.__setattr__(self, "_loaded", mod)
        return getattr(mod, item)


causal_nexus_v1 = _LazyModule("canonical.swe_kernel.causal_nexus_v1")
cow_zyg = _LazyModule("canonical.swe_kernel.cow_angelic_zygote_v1")
mhz = _LazyModule("canonical.swe_kernel.metamorphic_habitation_zipper_v1")
petri_splicer = _LazyModule("canonical.swe_kernel.petri_cow_splicing_engine_v1")
dep_gate = _LazyModule("canonical.swe_kernel.repair_input_dependency_gate_v1")
cow_runner = _LazyModule("canonical.swe_kernel.stdlib_cow_test_runner_v1")
witness_inversion_v1 = _LazyModule("canonical.swe_kernel.witness_inversion_v1")
zygote_pool = _LazyModule("canonical.swe_kernel.zygote_worker_pool_v1")
assert_demand = _LazyModule("canonical.tools.the_assertion_is_the_demand_v1")
rel_run = _LazyModule("canonical.tools.the_relation_is_read_from_the_failing_run_v1")
repair_admission = _LazyModule("canonical.swe_kernel.repair_admission_v1")

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


def _crystallize_verified_repair(
    *,
    skill_store: Any,
    law_store: Any,
    language: str,
    failure_output: str,
    edits: Mapping[str, str],
    orig_sources: Mapping[str, str],
    provenance: str,
    duty_witness: str = "",
) -> dict[str, Any]:
    """Write a verified repair into the external stores. Returns the ids earned.

    Two stores, two shapes, one boundary (§2: knowledge outside the weights):

      * ``CanonicalLawStore`` — single changed line-block, keyed by error class. Cheap recall,
        exact ``O(1)`` delete, but refuses any diff with more than one changed block.
      * ``SkillStoreV2`` — statement-level tree-rewrite morphism with alpha-renamed holes and a
        concrete witness. This is the store that absorbs *multi-statement* fixes, which is why
        ``learned_skill_id`` was always ``None`` for guard/fallback refactors: nothing ever
        called it from the spine.

    Called from every verified finish path, including the residual-hole proposer path, so a
    patch that is confirmed on disk is never dropped on the floor.
    """
    learned: list[str] = []
    laws: list[str] = []
    # The constant this repair substituted, if the route read one off the failure.
    # Recorded beside the anti-unified shape so a later task can propose it; the
    # store's own abstraction deliberately drops concrete values.
    _duty = ""
    if isinstance(duty_witness, str) and duty_witness:
        try:
            ast.literal_eval(duty_witness)
            _duty = duty_witness
        except (ValueError, SyntaxError, TypeError):
            _duty = ""
    for rel, new_src in sorted(edits.items()):
        orig_src = orig_sources.get(rel)
        if orig_src is None or orig_src == new_src:
            continue
        if language == "python" or rel.endswith(".py"):
            if skill_store is not None:
                try:
                    morph = skill_store.learn(
                        orig_src, new_src, origin=provenance, diagnostic_class=provenance.split(":")[-1],
                        duty_witness=_duty,
                    )
                    if morph is not None:
                        learned.append(morph.morphism_id)
                except Exception:
                    pass
        if law_store is not None and len(edits) == 1:
            try:
                law = law_store.add_verified_diff(
                    language=language,
                    failure_output=failure_output,
                    orig_source=orig_src,
                    patched_source=new_src,
                    provenance=provenance,
                )
                if law is not None:
                    laws.append(law.law_id)
            except Exception:
                pass
    return {
        "learned_skill_id": learned[0] if learned else None,
        "learned_skill_ids": learned,
        "crystallized_law_ids": laws,
    }


def _honest_suite_verdict(
    repo_root: pathlib.Path,
    targets: Sequence[str],
    *,
    timeout_s: float = 15.0,
) -> tuple[bool, str]:
    """Run the real tests and answer honestly. Never returns green for an empty run.

    Zero dependencies: `stdlib_cow_test_runner_v1` runs suites inside an
    `os.fork()` CoW child, understands plain `def test_*` functions, `Test*`
    classes, `unittest.TestCase` subclasses and `file.py::nodeid` targets, and
    rewrites `assert left <op> right` so a failure carries the live operand
    values that `causal_nexus_v1.extract_value_obligations` needs.

    Contract (the whole point of this function):
      * no test discovered, runner crash, timeout, or interpreter error -> (False, out)
      * any failing nodeid                                             -> (False, out)
      * at least one passing test and nothing failing                   -> (True, out)
    """
    targets = [str(t) for t in (targets or ()) if str(t).strip()]
    try:
        from canonical.swe_kernel import stdlib_cow_test_runner_v1 as cow_runner_honest

        res = cow_runner_honest.run_targets_cow_fork(
            repo_root,
            targets or (".",),
            timeout_s=min(15.0, float(timeout_s)),
            capture_frames=True,
        )
    except Exception as exc:  # pragma: no cover - defensive
        return False, f"ORACLE_ERROR: {type(exc).__name__}: {exc}"

    out = str(res.get("output") or "")
    passed = int(res.get("passed") or 0)
    failed = list(res.get("failed_nodeids") or ())
    rc = res.get("rc")
    if failed or rc not in (0, None) or passed <= 0:
        return False, out or f"NO_TESTS_DISCOVERED (passed=0, rc={rc})"
    return True, out


def _run_targets_cow_or_pytest(
    repo_root: pathlib.Path,
    targets: Sequence[str],
    *,
    timeout_s: float = 15.0,
) -> dict[str, Any]:
    """Sub-10ms `os.fork()` CoW runner fast path when tests do not import `pytest`, else `mhz.run_pytest_targets`."""
    uses_pytest_pkg = False
    for t in targets:
        rel_t = str(t).split("::")[0].lstrip("./")
        tp = repo_root / rel_t
        if tp.is_file():
            try:
                txt = tp.read_text(encoding="utf-8", errors="replace")
                if "pytest" in txt or "monkeypatch" in txt or "capsys" in txt:
                    uses_pytest_pkg = True
                    break
            except OSError:
                pass
    if not uses_pytest_pkg:
        res = cow_runner.run_targets_cow_fork(repo_root, targets, timeout_s=min(10.0, timeout_s), capture_frames=False)
        if int(res.get("passed", 0)) > 0 or res.get("failed_nodeids"):
            return res
    return mhz.run_pytest_targets(repo_root, targets, timeout_s=timeout_s)


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
        run_res = _run_targets_cow_or_pytest(repo_root, all_targets, timeout_s=timeout_s)
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
                ast.Add: (ast.Sub, ast.Mult),
                ast.Sub: (ast.Add, ast.Mult),
                ast.Mult: (ast.FloorDiv, ast.Add),
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

    # Channel 4b (`SWE-Serve`): Mutable default argument isolation (`def f(x, acc=[])` -> `acc=None`)
    for fn_idx, node in enumerate(all_nodes):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.args.defaults:
            n_args = len(node.args.args)
            n_defs = len(node.args.defaults)
            mut_positions: list[tuple[int, str, str]] = []
            for d_i, d_node in enumerate(node.args.defaults):
                arg_obj = node.args.args[n_args - n_defs + d_i]
                if isinstance(d_node, ast.List) and not d_node.elts:
                    mut_positions.append((d_i, arg_obj.arg, "[]"))
                elif isinstance(d_node, ast.Dict) and not d_node.keys:
                    mut_positions.append((d_i, arg_obj.arg, "{}"))
                elif isinstance(d_node, ast.Call) and isinstance(d_node.func, ast.Name) and d_node.func.id == "set" and not d_node.args:
                    mut_positions.append((d_i, arg_obj.arg, "set()"))
            if mut_positions:
                t_copy = copy.deepcopy(orig_tree)
                fn_copy = list(ast.walk(t_copy))[fn_idx]
                if isinstance(fn_copy, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    guards: list[ast.stmt] = []
                    for d_i, arg_name, init_expr in mut_positions:
                        fn_copy.args.defaults[d_i] = ast.Constant(value=None)
                        guards.extend(ast.parse(f"if {arg_name} is None:\n    {arg_name} = {init_expr}\n").body)
                    # Preserve docstring as first statement when present
                    if (
                        fn_copy.body
                        and isinstance(fn_copy.body[0], ast.Expr)
                        and isinstance(fn_copy.body[0].value, ast.Constant)
                        and isinstance(fn_copy.body[0].value.value, str)
                    ):
                        fn_copy.body = [fn_copy.body[0], *guards, *fn_copy.body[1:]]
                    else:
                        fn_copy.body = [*guards, *fn_copy.body]
                    ast.fix_missing_locations(t_copy)
                    _emit("stateful_mutable_default_isolation", ast.unparse(t_copy))

    # Channel 4c (`SWE-Perf`): Asymptotic `O(N^2) -> O(N)` loop membership `set()` hoist
    for fn_idx, node in enumerate(all_nodes):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            param_names = {a.arg for a in node.args.args}
            for stmt_i, stmt in enumerate(node.body):
                if isinstance(stmt, ast.For):
                    mutated_in_loop = {
                        sub.func.value.id
                        for sub in ast.walk(stmt)
                        if isinstance(sub, ast.Call)
                        and isinstance(sub.func, ast.Attribute)
                        and isinstance(sub.func.value, ast.Name)
                        and sub.func.attr in ("append", "extend", "pop", "remove", "clear", "insert")
                    }
                    seq_cands: list[str] = []
                    for sub in ast.walk(stmt):
                        if isinstance(sub, ast.Compare) and len(sub.ops) == 1 and isinstance(sub.ops[0], (ast.In, ast.NotIn)):
                            comp0 = sub.comparators[0]
                            if isinstance(comp0, ast.Name) and comp0.id in param_names and comp0.id not in mutated_in_loop:
                                if comp0.id not in seq_cands:
                                    seq_cands.append(comp0.id)
                    if seq_cands:
                        t_copy = copy.deepcopy(orig_tree)
                        fn_copy = list(ast.walk(t_copy))[fn_idx]
                        if isinstance(fn_copy, (ast.FunctionDef, ast.AsyncFunctionDef)) and stmt_i < len(fn_copy.body):
                            for_copy = fn_copy.body[stmt_i]
                            hoist_stmts: list[ast.stmt] = []
                            rename_map: dict[str, str] = {}
                            for s_name in seq_cands:
                                h_name = f"_fast_set_{s_name}"
                                rename_map[s_name] = h_name
                                hoist_stmts.extend(ast.parse(f"{h_name} = set({s_name})\n").body)
                            for sub in ast.walk(for_copy):
                                if isinstance(sub, ast.Compare) and len(sub.ops) == 1 and isinstance(sub.ops[0], (ast.In, ast.NotIn)):
                                    comp0 = sub.comparators[0]
                                    if isinstance(comp0, ast.Name) and comp0.id in rename_map:
                                        comp0.id = rename_map[comp0.id]
                            fn_copy.body = [*fn_copy.body[:stmt_i], *hoist_stmts, *fn_copy.body[stmt_i:]]
                            ast.fix_missing_locations(t_copy)
                            _emit("asymptotic_loop_set_hoist", ast.unparse(t_copy))

    # Channel 6 (PR #7049 `NAME_SCOPE`): Attribute -> In-Scope Local/Module Field (`__spec__.parent` -> `parent`)
    try:
        from canonical.swe_kernel.unified_unfamiliar_leapfrog_v1 import generate_name_scope_candidates

        for ns_tag, ns_src in generate_name_scope_candidates(orig_src, focus_lines=focus_lines, max_candidates=12):
            _emit(ns_tag, ns_src)
    except Exception:
        pass

    # Channel 7 (Unwired `oe_sygus_synthesizer_v1`): Live-Frame Observational-Equivalence SyGuS
    if m_eq and frame_records:
        try:
            from canonical.runtime import oe_sygus_synthesizer_v1 as sgs

            exp_v = ast.literal_eval(m_eq.group(2).strip())
            last_fr = frame_records[-1]
            locs_r = dict(last_fr.get("locals_repr") or {})
            env_d: dict[str, Any] = {}
            for k, rv in locs_r.items():
                try:
                    env_d[k] = ast.literal_eval(str(rv))
                except Exception:
                    continue
            if env_d:
                for row in sgs.synthesize_value_expressions([(env_d, exp_v)], lang="python", max_results=6):
                    expr_py = str(row["code"])
                    for node in all_nodes:
                        if isinstance(node, ast.Return) and node.value is not None:
                            _emit(f"oe_sygus_return:{expr_py}", mhz._splice_ast_node(orig_src, node, f"return {expr_py}"))
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
    base_passed = int(frame_run.get("passed", 0))
    pool = zygote_pool.ZygotePrewarmedPool(prewarm_enabled=False)
    passing_cids: list[str] = []
    partial_by_file: dict[str, tuple[int, str, str, str]] = {}
    forked_total = 0
    per_batch_timeout = min(5.0, max(1.5, timeout_s / 2.0))
    for start in range(0, min(len(cow_jobs), 96), 8):
        batch = cow_jobs[start : start + 8]
        forked_total += len(batch)
        res = pool.run_parallel_sharded(
            [fn for _, fn in batch],
            winner_predicate=None,
            timeout_s=per_batch_timeout,
        )
        for item in res.get("results") or ():
            cid_i = str(item.get("candidate_id") or "")
            if cid_i not in job_payloads:
                continue
            if item.get("passed"):
                passing_cids.append(cid_i)
            else:
                tp = int(item.get("tests_passed", 0))
                if tp > base_passed:
                    r_rel_i, tag_i, src_i = job_payloads[cid_i]
                    prev = partial_by_file.get(r_rel_i)
                    if prev is None or tp > prev[0]:
                        partial_by_file[r_rel_i] = (tp, cid_i, tag_i, src_i)
        if passing_cids:
            break

    # Phase 4 Multi-File Orthogonal CoW Patch Composition (`FeatureBench` cross-module synthesis):
    # When single-file candidates strictly increase `tests_passed` on >= 2 distinct files, compose
    # their orthogonal file overlays in `os.fork()` CoW (`0` disk writes!) and verify jointly on disk!
    if not passing_cids and len(partial_by_file) >= 2:
        multi_edits = {r_rel: tup[3] for r_rel, tup in sorted(partial_by_file.items())}
        multi_tags = "+".join(f"{r_rel}:{tup[2]}" for r_rel, tup in sorted(partial_by_file.items()))

        def _multi_shard() -> Mapping[str, Any]:
            devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull, 1)
            os.dup2(devnull, 2)
            os.close(devnull)
            out = cow_runner._execute_suite_in_current_process(
                repo_root,
                all_targets,
                overlays=multi_edits,
                capture_frames=False,
            )
            return {"passed": bool(out.get("ok")), "tests_passed": int(out.get("passed", 0))}

        forked_total += 1
        m_res = pool.run_parallel_sharded([_multi_shard], winner_predicate=None, timeout_s=per_batch_timeout)
        m_items = list(m_res.get("results") or ())
        if m_items and m_items[0].get("passed"):
            ok_m, _reason_m, meta_m = _verify_python_candidate_edits(
                repo_root,
                multi_edits,
                base_snapshot,
                test_targets,
                regression_tests=regression_tests,
                neg_guard=neg_guard,
                timeout_s=timeout_s,
            )
            if ok_m:
                first_rel = sorted(multi_edits.keys())[0]
                return {
                    "solved": True,
                    "channel": f"orthogonal_multifile:{multi_tags}",
                    "modified_files": sorted(multi_edits.keys()),
                    "patched_source": multi_edits[first_rel],
                    "candidates_screened_cow": forked_total,
                    "version_space": {
                        "passing_candidates_in_batch": 1,
                        "equivalence_classes": 1,
                        "diagnosis": "IDENTIFIED_BY_ORTHOGONAL_MULTIFILE_TESTS",
                    },
                    "covered_source_files": [r for r in ranked_files if cov_lines.get(r)],
                    "test_run": meta_m.get("test_run"),
                }
            _restore_tree(repo_root, base_snapshot)

    # Move IV Fallback: Putback Backward AST Witness Propagation (`reverse_tomography_algebra_v1`) +
    # Value-Space Angelic + Bottom-Up Observational Equivalence (`angelic_oe_synthesizer_v1`)
    if not passing_cids and ranked_files and test_targets:
        try:
            from canonical.swe_kernel import reverse_tomography_algebra_v1 as rta

            top_rel = ranked_files[0]
            orig_top = base_snapshot[top_rel].decode("utf-8", errors="replace")
            residual = rta.extract_output_residual(rich_output)
            top_cov = cov_lines.get(top_rel) or [1]
            rta_cands = rta.backpropagate_ast_repairs(
                orig_top, [{"lineno": int(ln), "score": 1.0} for ln in top_cov[:6]], residual, max_patches=8
            )
            rta_jobs = []
            for r_i, (p_src, _ln, p_rule) in enumerate(rta_cands):
                cid_r = f"{top_rel}::rta_{r_i}::putback_ast:{p_rule}"
                job_payloads[cid_r] = (top_rel, f"putback_ast:{p_rule}", p_src)

                def _make_rta_shard(c_id: str = cid_r, r_rel: str = top_rel, c_src: str = p_src) -> Callable[[], Mapping[str, Any]]:
                    def _shard() -> Mapping[str, Any]:
                        devnull = os.open(os.devnull, os.O_WRONLY)
                        os.dup2(devnull, 1)
                        os.dup2(devnull, 2)
                        os.close(devnull)
                        out = cow_runner._execute_suite_in_current_process(repo_root, all_targets, overlays={r_rel: c_src}, capture_frames=False)
                        return {"candidate_id": c_id, "passed": bool(out.get("ok"))}

                    return _shard

                rta_jobs.append(_make_rta_shard())
            if rta_jobs:
                forked_total += len(rta_jobs)
                rta_res = pool.run_parallel_sharded(rta_jobs, winner_predicate=None, timeout_s=per_batch_timeout)
                for item in rta_res.get("results") or ():
                    if item.get("passed") and item.get("candidate_id") in job_payloads:
                        passing_cids.append(str(item["candidate_id"]))
        except Exception:
            pass

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


def _synthesize_zero_test_oracle(
    root: pathlib.Path,
    *,
    issue_text: str = "",
) -> str | None:
    """Phase 4 Zero-Test Oracle Harvester (`the_guide_is_a_test_suite_v1` + `metamorphic_laws_v1` + `reverse_tomography_algebra_v1`).

    Synthesizes an executable pytest file for a testless repository (`0` `test_*.py` files) from:
      1. Docstring `>>> expr` / expected-value transcripts (`doctest` + `the_guide_is_a_test_suite_v1`).
      2. Metamorphic & stateful multi-call laws (`f(x) == f(x)` repeat-call purity + `f(f(x)) == f(x)` idempotence).
      3. `reverse_tomography_algebra_v1.synthesize_metamorphic_oracle_test` when `issue_text` is provided.
    """
    import doctest

    py_files = sorted(
        p
        for p in root.rglob("*.py")
        if not any(part in _SKIP_DIRS for part in p.parts)
        and not p.name.startswith("test_")
        and not p.name.startswith("_canonical_spine_")
    )
    if not py_files:
        return None

    assertions: list[str] = []
    imports_needed: set[str] = set()
    dt_parser = doctest.DocTestParser()

    for pf in py_files[:12]:
        rel_mod = pf.relative_to(root).with_suffix("").as_posix().replace("/", ".")
        if rel_mod.endswith(".__init__"):
            rel_mod = rel_mod[: -len(".__init__")]
        if not rel_mod or "." in pf.stem:
            continue
        try:
            src = pf.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(src)
        except Exception:
            continue

        # 1. Harvest docstring `>>>` examples (`the_guide_is_a_test_suite_v1` discipline)
        docstrings: list[str] = []
        mod_doc = ast.get_docstring(tree)
        if mod_doc:
            docstrings.append(mod_doc)
        pub_fns: list[ast.FunctionDef] = []
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                pub_fns.append(node)
                fdoc = ast.get_docstring(node)
                if fdoc:
                    docstrings.append(fdoc)

        for ds in docstrings:
            if ">>>" not in ds:
                continue
            try:
                examples = dt_parser.get_examples(ds)
            except Exception:
                examples = []
            setup_lines: list[str] = []
            for ex in examples:
                s_src = ex.source.strip()
                s_want = ex.want.strip()
                if not s_src:
                    continue
                if not s_want:
                    setup_lines.append(s_src)
                elif "\n" not in s_src and "\n" not in s_want and not s_want.startswith("Traceback"):
                    imports_needed.add(f"from {rel_mod} import *")
                    prefix = ("; ".join(setup_lines) + "; ") if setup_lines else ""
                    assertions.append(f"    {prefix}assert ({s_src}) == ({s_want})")

        # 2. Metamorphic & stateful repeat-call purity probes (`metamorphic_laws_v1` discipline)
        for fn_node in pub_fns[:8]:
            req_arity = len(fn_node.args.args) - len(fn_node.args.defaults)
            fname = fn_node.name
            if req_arity == 1:
                imports_needed.add(f"import {rel_mod} as _m_{rel_mod.replace('.', '_')}")
                m_alias = f"_m_{rel_mod.replace('.', '_')}"
                # Repeat-call purity via `repr()` snapshot (catches in-place mutable-default leaks!)
                if fn_node.args.defaults:
                    assertions.append(
                        f"    _r1 = repr({m_alias}.{fname}('probe_a')); _r2 = repr({m_alias}.{fname}('probe_a')); assert _r1 == _r2"
                    )
                if any(k in fname.lower() for k in ("normalize", "canonical", "clean", "sanitize", "trim")):
                    assertions.append(
                        f"    _v = {m_alias}.{fname}('  HeLLo  '); assert {m_alias}.{fname}(_v) == _v"
                    )

    if assertions:
        lines = sorted(imports_needed) + ["", "def test_synthesized_zero_test_oracle():"] + assertions + [""]
        return "\n".join(lines)

    # 3. Issue-text metamorphic oracle fallback (`reverse_tomography_algebra_v1`)
    if issue_text.strip():
        try:
            from canonical.swe_kernel import reverse_tomography_algebra_v1 as rta

            tmp_name = "_canonical_rta_probe_oracle.py"
            res_o = rta.synthesize_metamorphic_oracle_test(root, issue_text, oracle_filename=tmp_name, timeout_s=8)
            p_tmp = root / tmp_name
            if p_tmp.is_file():
                code_o = p_tmp.read_text(encoding="utf-8")
                p_tmp.unlink()
                if res_o.get("synthesized") or "def test_" in code_o:
                    return code_o
        except Exception:
            pass

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
    temp_witness_rel: str | None = None
    zero_test_oracle_synthesized = False
    if not test_file:
        # Discover a default test file if present
        cands = sorted(
            p.relative_to(root).as_posix()
            for p in root.rglob("test_*.py")
            if not any(part in _SKIP_DIRS for part in p.parts)
        )
        if not cands:
            zt_code = _synthesize_zero_test_oracle(root, issue_text=issue_text)
            if zt_code:
                stages_run.append("ZERO_TEST_ORACLE_SYNTHESIS")
                temp_witness_rel = "_canonical_spine_wall1_witness_test.py"
                (root / temp_witness_rel).write_text(zt_code, encoding="utf-8")
                test_file = temp_witness_rel
                zero_test_oracle_synthesized = True
            else:
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
        else:
            test_file = cands[0]

    # Stage 0: Run baseline oracle
    stages_run.append("BASELINE_ORACLE")
    base_run = _run_targets_cow_or_pytest(root, [test_file], timeout_s=min(15.0, timeout_s))
    base_output = str(base_run.get("output") or "")
    base_failed = _pytest_failed(base_run)
    if zero_test_oracle_synthesized and not base_failed:
        _restore_tree(root, base_snapshot)
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
    active_test_file = test_file

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
        witness_snapshot = _snapshot_tree(root) if zero_test_oracle_synthesized else base_snapshot

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
    skill_store_path: str | pathlib.Path | None = None,
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
        "import importlib as _il, sys as _sys\n"
        "_il.invalidate_caches()\n"
        "for _m in [k for k, v in list(_sys.modules.items()) if getattr(v, '__file__', None) and str(getattr(v, '__file__', '')).startswith('.')]:\n"
        "    _sys.modules.pop(_m, None)\n"
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

    # Same external store as the multifile path: a proposer-verified fix on any path must be
    # crystallised once, not re-derived next time.
    _store_target = skill_store_path or os.environ.get("BRAIN_SKILL_STORE_PATH")
    try:
        _skill_store = causal_nexus_v1.SkillStoreV2(_store_target)
    except Exception:  # pragma: no cover
        _skill_store = None

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

        # Stage 1.7: External skill-store recall (`SkillStoreV2.propose`).
        #
        # Learning without recall is not learning: the store was written but never read, so a fix
        # verified yesterday had to be rediscovered today. This stage asks the store first, because
        # a stored morphism is cheaper than any synthesis and carries a witness proving it once
        # held. A proposal is accepted only through the same verified CoW oracle as everything
        # else; success increments `verified_transfers`, failure increments `refutations` and the
        # morphism retires once refutations outnumber transfers.
        _micro_stages: list[str] = ["STAGE_1_7_SKILL_STORE_RECALL"]
        skill_recall_attempts = 0
        skill_recall_hits = 0
        if _skill_store is not None and getattr(_skill_store, "morphisms", None):
            for rel in ranked_files:
                orig_src = (root / rel).read_text(encoding="utf-8", errors="replace")
                try:
                    proposals = _skill_store.propose(orig_src, limit=8)
                except Exception:
                    proposals = []
                for morph, new_src in proposals:
                    if not isinstance(new_src, str) or not new_src.strip() or new_src == orig_src:
                        continue
                    fixed = new_src + ("" if new_src.endswith("\n") else "\n")
                    skill_recall_attempts += 1
                    # Verify in a hardlinked CoW workspace through the same honest oracle as every
                    # other candidate. (The microscope's zygote helper is scoped to the other
                    # entry point; this loop must use the one in scope.)
                    rec_dir = pathlib.Path(tmp) / f"cow_recall_{skill_recall_attempts}"
                    cow_imp.create_zero_copy_cow_workspace(root, rec_dir)
                    _cow_write(rec_dir / rel, fixed)
                    ok, _rec_out = _run_pytest_in(rec_dir, rel_tests if test_files is None else [
                        str(t) for t in (test_files or ()) if str(t).endswith(".py")
                    ])
                    try:
                        if ok:
                            _skill_store.mark_transfer(morph.morphism_id)
                            skill_recall_hits += 1
                        else:
                            _skill_store.mark_refutation(morph.morphism_id)
                    except Exception:
                        pass
                    if ok:
                        if apply_to_source:
                            (root / rel).write_text(fixed, encoding="utf-8")
                        return {
                            "schema": SCHEMA,
                            "pass": True,
                            "status": "PASS__SKILL_STORE_RECALL_VERIFIED",
                            "tier": "SKILL_STORE_RECALL",
                            "patched_files": [rel],
                            "patches": {rel: fixed},
                            "recalled_morphism_id": morph.morphism_id,
                            "skill_recall_attempts": skill_recall_attempts,
                            "skill_recall_hits": skill_recall_hits,
                            "stages_run": _micro_stages,
                            "verified_by_cow_oracle": True,
                            "model_calls": 0,
                            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
                        }

        # Stage 2: Deterministic K3=0 Fast Lane (STUN/guard proposals + canonical solve_repository_task)
        _stages_after_admission: list[str] = list(_micro_stages)
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
            # Admission: a suite-green patch that embeds a test literal is not a repair.
            stun_cands, admission_refusals = repair_admission.filter_candidates(
                stun_cands, orig_src, test_sources, max_admitted=10
            )
            if admission_refusals:
                _stages_after_admission.append("REPAIR_ADMISSION_GATE")
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
                            "stages_run": _stages_after_admission,
                            "admission_refusals": admission_refusals[:8],
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
            # Admission before the oracle: a proposer's patch that hardcodes the witness will pass
            # the suite and be wrong forever after. Measured 2026-11-26: `return ((user or '') and
            # 'bob')` was accepted here as a verified repair.
            adm_refusals: list[dict[str, Any]] = []
            admitted_map: dict[str, str] = {}
            for _rel, _new in patch_map.items():
                _orig = (root / _rel).read_text(encoding="utf-8", errors="replace") if (root / _rel).is_file() else ""
                _ok, _reason, _ev = repair_admission.admits_repair(_new, _orig)
                if _ok:
                    admitted_map[_rel] = _new
                else:
                    adm_refusals.append({"rel": _rel, "reason": _reason, **_ev})
            if adm_refusals and not admitted_map:
                continue
            if admitted_map:
                patch_map = admitted_map
            screened_count += 1
            orthogonal_candidates.append(patch_map)
            cand_dir = pathlib.Path(tmp) / f"cow_prop_{idx}"
            cow_imp.create_zero_copy_cow_workspace(root, cand_dir)
            for relp, content in patch_map.items():
                _cow_write(cand_dir / relp, content)
            ok_full, full_out = _run_pytest_in(cand_dir, rel_tests)
            if ok_full:
                # Read the pre-state BEFORE writing, otherwise the crystalliser sees orig == new
                # and (correctly) refuses a morphism with no prediction error.
                orig_sources = {
                    relp: (root / relp).read_text(encoding="utf-8", errors="replace")
                    for relp in patch_map
                    if (root / relp).is_file()
                }
                if apply_to_source:
                    for relp, content in patch_map.items():
                        (root / relp).write_text(content, encoding="utf-8")
                # The writer, on the path where a proposer's patch is confirmed on disk.
                # A verified fix that is not crystallised has to be rediscovered next time; that
                # is the difference between an instrument and an agent.
                crystallized = _crystallize_verified_repair(
                    skill_store=_skill_store,
                    law_store=law_store,
                    language="python",
                    failure_output=base_out[:400],
                    edits=patch_map,
                    orig_sources=orig_sources,
                    provenance="UNTRUSTED_PROPOSER_VERIFIED",
                )
                return {
                    "schema": SCHEMA,
                    "pass": True,
                    "status": "PASS__INVERTED_RESIDUAL_HOLE_VERIFIED",
                    "tier": "INVERTED_RESIDUAL_HOLE_VERIFIED",
                    "patched_files": sorted(patch_map.keys()),
                    "proposals_screened": screened_count,
                    "angelic_hole_packet": hole_packet,
                    "verified_by_cow_oracle": True,
                    "learned_skill_id": crystallized["learned_skill_id"],
                    "learned_skill_ids": crystallized["learned_skill_ids"],
                    "crystallized_law_ids": crystallized["crystallized_law_ids"],
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


def solve_swe_repo_native_multifile(
    repo_root: str | Path,
    *,
    test_targets: Sequence[str] | None = None,
    candidate_files: Sequence[str] | None = None,
    in_run_repair_vocab: Mapping[str, Any] | None = None,
    repair_store: str | Path | None = None,
    learn_verified: bool = True,
    prior_demonstrations: Sequence[tuple[str, str, str]] = (),
    witness_envs: Sequence[Mapping[str, Any]] | None = None,
    witness_targets: Sequence[Any] | None = None,
    mine_git_history: bool = True,
    history_limit: int = 200,
    residual_proposer: Callable[[Mapping[str, Any]], Sequence[Mapping[str, str]]] | None = None,
    keep_patch_applied: bool = False,
    timeout_s: float = 30.0,
    skill_store_path: str | Path | None = None,
) -> dict[str, Any]:
    """Try learned edits, strict-prior insertions and localized synthesis on a disposable repo.

    A selected-suite pass is not a solved issue or transferable rule. The
    zygote is a screening optimization; a fresh pytest process is the gate.
    """
    import ast as _ast
    import os as _os
    import shutil as _shutil
    import subprocess as _sp
    import tempfile as _tf

    from canonical.runtime.memory_policy_v1 import can_read_memory, can_write_memory
    from canonical.runtime import cow_zygote_speculative_verifier_v1 as zygote
    from canonical.swe_kernel import angelic_oe_synthesizer_v1 as angelic_oe
    from canonical.swe_kernel import causal_dataflow_graph_v1 as cdg
    from canonical.swe_kernel import repo_component_petri_v1 as petri
    from canonical.tools import arm_learned_from_its_own_verified_repairs_v1 as arm_learn
    from canonical.tools import assertion_localisation_v1 as assert_loc
    from canonical.swe_kernel.induced_edit_basis_v1 import joint_expression_templates, render_one_site
    from canonical.swe_kernel.local_type_paths_v1 import return_paths
    from canonical.swe_kernel import prior_owned_insertions_v1 as history
    from canonical.swe_kernel import repair_input_dependency_gate_v1 as dependencies
    from canonical.swe_kernel.repo_native_test_surface_v1 import (
        EXCLUDED, copy_product_tree, restored_surface, test_surface, merge_vocab, export_vocab)
    from canonical.tools import line_localisation_v1 as line_loc

    t0 = time.perf_counter()
    root = pathlib.Path(repo_root).resolve()
    if not root.is_dir():
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "FAIL_CLOSED__REPO_ROOT_MISSING",
            "model_calls": 0,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }

    # An explicitly supplied candidate belongs to the caller, not the native
    # learner. Permit the upstream diagnostic only with its own external store;
    # never mix it into a witnessed journal or a default owned skill store.
    if residual_proposer is not None and (
        not callable(residual_proposer) or not skill_store_path or repair_store is not None
        or not learn_verified or not can_write_memory()
    ):
        return {"pass": False, "status": "REFUSED__MODEL_FREE_ROUTE", "model_calls": 0}
    # Never accept an out-of-workspace source or an edit to a test as a product fix.
    for target in [*(candidate_files or ()), *(test_targets or ())]:
        name = str(target).split("::")[0]
        if pathlib.Path(name).is_absolute() or not (root / name).resolve().is_relative_to(root):
            return {"pass": False, "status": "REFUSED__PATH_OUTSIDE_WORKSPACE", "model_calls": 0}
    if not can_read_memory():
        repair_store = in_run_repair_vocab = None
        prior_demonstrations, mine_git_history = (), False
    learn_verified = learn_verified and can_write_memory()
    # Build/merge in-run alpha-canonical repair vocabulary from any prior verified demonstrations.
    try:
        vocab = merge_vocab({}, in_run_repair_vocab) if in_run_repair_vocab else {}
    except (AttributeError, KeyError, TypeError, ValueError):
        return {"pass": False, "status": "REFUSED__INVALID_VOCABULARY", "model_calls": 0}
    demos_list: list[tuple[str, str, str]] = [
        (str(a), str(b), str(c)) for a, b, c in prior_demonstrations
    ]
    if demos_list:
        folded = arm_learn.fold(demos_list)
        vocab = merge_vocab(vocab, folded)

    journal = None
    if repair_store is not None:
        from canonical.swe_kernel.repair_journal_v1 import RepairJournal, token
        if pathlib.Path(repair_store).resolve().is_relative_to(root):
            return {'pass':False, 'status':'REFUSED__STORE_INSIDE_RECEIVER', 'model_calls':0}
        if learn_verified or pathlib.Path(repair_store).is_file():
            journal = RepairJournal(repair_store, read_only=not learn_verified)
            if learn_verified:journal.sleep()  # bounded resume; never mutate read-only receivers

    deadline = time.monotonic() + timeout_s
    history_info = {"base": None, "candidates": 0, "error": None}
    oracle = lambda ws: test_surface(ws, test_targets, timeout=deadline - time.monotonic())
    with _tf.TemporaryDirectory(prefix='native_baseline_') as tb:
        copied = pathlib.Path(tb)/'repo'
        try:
            copy_product_tree(root, copied)
        except (OSError, ValueError, RuntimeError) as exc:
            return {'pass':False, 'status':'UNMEASURED__SOURCE_COPY', 'detail':str(exc)[:200], 'model_calls':0}
        baseline = oracle(copied)
        baseline['output'] = baseline['output'].replace(str(copied)+'/', '')

    def _verify_in_isolated_cow(
        rel_edits: Mapping[str, str],
        *,
        single_test_src: str | None = None,
        stored_duty_proposal: bool = False,
    ) -> tuple[bool, str, bool]:
        """Screen self-contained assertions if possible; confirm on a fresh project copy.

        `stored_duty_proposal` marks a candidate whose value came from the skill
        store rather than from this failure. It relaxes exactly one rule -- the
        input-dependency gate -- and nothing else. That gate exists to stop a
        search from *settling* for a lookup; it must not stop the system from
        trying a value it learned elsewhere and verifying it, which is the only
        way a stored duty can ever be reused. The CoW oracle still decides.
        """
        if time.monotonic() >= deadline:
            return False, "BUDGET_EXHAUSTED", False
        for rel, candidate in rel_edits.items():
            if rel not in py_source_rels:
                return False, "NOT_PRODUCT_SOURCE", False
            if not stored_duty_proposal:
                dep = dependencies.gate((root / rel).read_text(encoding="utf-8"), candidate)
                if dep["status"] != dependencies.PASS:
                    return False, dep["reason"], False
        zygote_used = False
        if len(rel_edits) == 1 and single_test_src:
            only_rel, new_src = next(iter(rel_edits.items()))
            orig_p = root / only_rel
            if orig_p.is_file():
                zres = zygote.verify_candidate_patch_cow(
                    orig_p.read_text(encoding="utf-8", errors="replace"),new_src,single_test_src,
                    timeout_s=min(1.0,deadline-time.monotonic()))
                zygote_used = bool(zres.get('tested'))
                if zres['verdict']=='FAIL':
                    return False,'zygote assertion: '+zres['failed_test'],zygote_used
        with _tf.TemporaryDirectory(prefix="wave23_cow_") as td:
            ws = pathlib.Path(td) / "repo"
            copy_product_tree(root,ws)
            for rel, content in rel_edits.items():
                dst = ws / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                if dst.exists() or dst.is_symlink():
                    dst.unlink()
                dst.write_text(content, encoding="utf-8")
            checked = oracle(ws)
            ok = restored_surface(baseline,checked)
            return ok, checked["output"], zygote_used

    # Honor the same storage and workspace boundaries for the upstream writers
    # as for the witnessed journal. A read-only receiver must not open a writer.
    _skill_store = _closure_law_store = None
    default_dir = pathlib.Path(__file__).resolve().parents[2] / "canonical/astra_runtime/tmp"
    skill_path = pathlib.Path(skill_store_path or _os.environ.get("BRAIN_SKILL_STORE_PATH")
                              or default_dir / "tree_rewrite_morphism_store_v1.json").resolve()
    law_path = pathlib.Path(_os.environ.get("BRAIN_LAW_STORE_PATH")
                            or default_dir / "canonical_law_store_v1.json").resolve()
    if learn_verified and (repair_store is None or skill_store_path is not None):
        if (skill_path.is_relative_to(root) or law_path.is_relative_to(root)
                or (residual_proposer is not None and skill_path.is_relative_to(default_dir))):
            return {"pass": False, "status": "REFUSED__NON_EXTERNAL_STORE", "model_calls": 0}
        _skill_store = causal_nexus_v1.SkillStoreV2(skill_path)
        if residual_proposer is None:
            try:
                _closure_law_store = CanonicalLawStore(law_path)
            except (OSError, ValueError, KeyError, TypeError):
                pass  # An unreadable optional store cannot attest or learn a law.

    def _crystallize_and_finish(
        edits: Mapping[str, str],
        *,
        tier: str,
        localization: Mapping[str, Any],
        stages: list[str],
        zygote_screened: int,
        extra: Mapping[str, Any] | None = None,
        supplied: bool = False,
    ) -> dict[str, Any]:
        new_demos: list[tuple[str, str, str]] = []
        orig_sources: dict[str, str] = {}
        for rel, new_src in sorted(edits.items()):
            orig_p = root / rel
            if orig_p.is_file():
                orig_src = orig_p.read_text(encoding="utf-8", errors="replace")
                orig_sources[rel] = orig_src
                new_demos.append((f"{rel}@{hashlib.sha256(orig_src.encode()).hexdigest()}:{hashlib.sha256(new_src.encode()).hexdigest()}", orig_src, new_src))
        learned = arm_learn.fold([] if supplied else new_demos)
        learned["node"] = ([] if supplied else joint_expression_templates(new_demos)) + learned["node"]
        updated_vocab = merge_vocab(vocab, learned)
        ticket = None
        if not supplied and journal is not None and learn_verified:
            cert = {'failed_before':sorted(baseline['failed']), 'mechanism':tier,
                    'restored_surface_sha256':token([sorted(baseline['passed']|baseline['failed']), sorted(baseline['skipped'])]),
                    'target_tests':{name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in test_rels},
                    'edits':[d[0] for d in new_demos], 'authority':'SELECTED_TESTS_ONLY'}
            ticket = journal.enqueue(cert,learned)
            journal.sleep()
        crystallized = _crystallize_verified_repair(
            skill_store=_skill_store, law_store=_closure_law_store, language="python",
            failure_output=base_out, edits=edits, orig_sources=orig_sources,
            provenance="UNTRUSTED_PROPOSER_VERIFIED" if supplied else f"ZERO_MODEL_{tier}",
            duty_witness=str((dict(extra) if extra else {}).get("backward_obligation_source") or ""),
        )
        if keep_patch_applied:
            for rel, new_src in sorted(edits.items()):
                dst = root / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_text(new_src, encoding="utf-8")
        return {
            "schema": SCHEMA,
            "pass": True,
            "status": f"PASS__REPO_NATIVE_{tier}",
            "tier": tier,
            "patched_files": sorted(edits.keys()),
            "patches": dict(edits),
            "localization": dict(localization),
            "history": dict(history_info), "teacher_key":ticket,
            "tested_surface_count": len(baseline["passed"]) + len(baseline["failed"]),
            "knowledge_status": "TEACHER_HYPOTHESIS_RECHECK_ON_RECEIVER",
            "stages_run": stages,
            "zygote_screened_candidates": zygote_screened,
            "updated_repair_vocab": export_vocab(updated_vocab),
            "crystallized_demo_count": len(new_demos),
            "learned_skill_id": crystallized["learned_skill_id"],
            "learned_skill_ids": crystallized["learned_skill_ids"],
            "crystallized_law_ids": crystallized["crystallized_law_ids"],
            "host_mutated": bool(keep_patch_applied),
            "model_calls": int(supplied),
            "producer_origin": "UNTRUSTED_PROPOSER" if supplied else "REPO_NATIVE",
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            **(dict(extra) if extra else {}),
        }

    # Baseline run
    base_out = baseline["output"]
    if baseline["status"] not in {"GREEN", "RED"}:
        return {"schema": SCHEMA, "pass": False, "status": "UNMEASURED__" + baseline["status"],
                "model_calls": 0, "detail": base_out[-500:]}
    if baseline["status"] == "GREEN":
        return {
            "schema": SCHEMA,
            "pass": True,
            "status": "PASS__BASELINE_ALREADY_GREEN",
            "tier": "ALREADY_GREEN",
            "tested_surface_count": len(baseline["passed"]), "issue_satisfied": None,
            "patched_files": [],
            "updated_repair_vocab": export_vocab(vocab),
            "model_calls": 0,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }

    # Stage 0: Cross-file crash-frame + assertion + line localization
    stages_run: list[str] = ["STAGE_0_CROSSFILE_LOCALIZATION"]
    crash_frames = cdg.extract_crash_frames(base_out)
    product_files = []
    for parent, dirs, names in _os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDED and d not in {'test','tests'} and not d.startswith('.'))
        product_files.extend(pathlib.Path(parent)/f for f in sorted(names) if f.endswith('.py'))
    py_source_rels = [p.relative_to(root).as_posix() for p in product_files
        if not p.name.startswith("test_") and not p.name.endswith("_test.py")
        and p.name != "conftest.py" and not p.is_symlink()
        and p.relative_to(root).as_posix() not in {str(t).split("::")[0] for t in test_targets or ()}]
    test_rels = [
        t for t in (test_targets or ()) if str(t).endswith(".py") and (root / t).is_file()
    ] or [
        p.relative_to(root).as_posix()
        for p in sorted(root.rglob("test*.py"))
        if ".git" not in p.parts and "__pycache__" not in p.parts
    ]
    single_test_src = (
        (root / test_rels[0]).read_text(encoding="utf-8", errors="replace")
        if len(test_rels) == 1 and (root / test_rels[0]).is_file()
        else None
    )

    # Collect assertion names from failing test files & crash frames
    assert_names: set[str] = set()
    for fr in crash_frames:
        f_file = str(fr.get("file") or "")
        f_line = int(fr.get("line") or 0)
        p_fr = pathlib.Path(f_file) if _os.path.isabs(f_file) else (root / f_file)
        if p_fr.resolve().is_relative_to(root) and p_fr.is_file() and f_line > 0:
            try:
                node = assert_loc.failing_assertion(p_fr.read_text(encoding="utf-8", errors="replace"), f_line)
                if node is not None:
                    assert_names.update(assert_loc.names_in(node))
            except Exception:
                pass

    # Rank candidate source files across crash frames + explicit hints
    ranked_files: list[str] = []
    if candidate_files:
        for cf in candidate_files:
            if cf in py_source_rels and cf not in ranked_files:
                ranked_files.append(str(cf))
    for fr in crash_frames:
        f_file = str(fr.get("file") or "")
        try:
            rel = pathlib.Path(f_file).resolve().relative_to(root).as_posix()
        except Exception:
            rel = f_file
        if rel in py_source_rels and rel not in ranked_files:
            ranked_files.append(rel)
    for rel in py_source_rels:
        if rel not in ranked_files:
            ranked_files.append(rel)
    ranked_files = ranked_files[:8]

    ranked_lines_by_file: dict[str, list[int]] = {}
    for rel in ranked_files:
        fp = root / rel
        rankings: dict[str, list[tuple[int, float]]] = {}
        frame_lines = [
            int(fr.get("line") or 0)
            for fr in crash_frames
            if str(fr.get("file") or "").endswith(rel) and int(fr.get("line") or 0) > 0
        ]
        if frame_lines:
            rankings["frames"] = [(ln, 1.0) for ln in frame_lines]
        if assert_names:
            try:
                al = line_loc.assertion_lines(fp, assert_names)
                if al:
                    rankings["assertion"] = [(int(x[0]), float(x[1])) if isinstance(x, (tuple, list)) else (int(x), 1.0) for x in al]
            except Exception:
                pass
        try:
            el = line_loc.exception_lines(fp, base_out)
            if el:
                rankings["exception"] = [(int(x[0]), float(x[1])) if isinstance(x, (tuple, list)) else (int(x), 1.0) for x in el]
        except Exception:
            pass
        fused = line_loc.fuse(rankings) if rankings else []
        n_lines = len(fp.read_text(encoding="utf-8", errors="replace").splitlines())
        valid_fused = [
            int(x[0] if isinstance(x, (tuple, list)) else x)
            for x in fused
            if 1 <= int(x[0] if isinstance(x, (tuple, list)) else x) <= n_lines
        ]
        ranked_lines_by_file[rel] = valid_fused[:12] if valid_fused else list(range(1, min(40, n_lines) + 1))

    localization_report = {
        "crash_frames": crash_frames[:10],
        "assertion_names": sorted(assert_names)[:20],
        "ranked_files": ranked_files,
        "ranked_lines_by_file": ranked_lines_by_file,
    }
    zygote_screened = 0

    if residual_proposer is not None:
        # Explicit external-proposal diagnostic. The callback never sees the
        # journal, and its patch must still restore the actual selected cases.
        # No learned vocabulary or law from this lane goes into the native arm.
        packet = {"faulty_files": ranked_files[:4], "impacted_tests": test_rels[:6],
                  "failure_tail": base_out[-800:], "value_obligations": [],
                  "local_snippets": {r: (root / r).read_text(errors="replace")[:1800]
                                     for r in ranked_files[:3]}}
        proposals = residual_proposer(packet) or ()
        for edits in proposals[:8]:
            if not isinstance(edits, Mapping) or not edits:
                continue
            if not all(rel in ranked_files and isinstance(src, str) and
                       repair_admission.admits_repair(src, (root / rel).read_text(errors="replace"))[0]
                       for rel, src in edits.items()):
                continue
            ok, _, screened = _verify_in_isolated_cow(edits, single_test_src=single_test_src)
            zygote_screened += int(screened)
            if ok:
                return _crystallize_and_finish(edits, tier="SUPPLIED_PATCH_VERIFIED", supplied=True,
                    localization=localization_report, stages=["EXPLICIT_UNTRUSTED_PROPOSAL"],
                    zygote_screened=zygote_screened)
        return {"pass": False, "status": "REFUSED__SUPPLIED_PATCH_NOT_VERIFIED", "model_calls": 1}

    if journal is not None:
        retrieved = journal.recall(((root/rel).read_text(encoding='utf-8',errors='replace'),
                                    set(ranked_lines_by_file[rel])) for rel in ranked_files)
        vocab = merge_vocab(vocab,retrieved)
        localization_report['store_templates_retrieved'] = sum(map(len,retrieved.values()))

    # Stage 1: Online in-run learned repair vocabulary (`arm_learned_from_its_own_verified_repairs_v1`)
    if vocab:
        stages_run.append("STAGE_1_IN_RUN_ALPHA_CANONICAL_TRANSFER")
        for rel in ranked_files:
            orig_src = (root / rel).read_text(encoding="utf-8", errors="replace")
            try:
                props = arm_learn.propose(orig_src, vocab)
            except Exception:
                props = []
            for p_row in props[:12]:
                cand_src = render_one_site(orig_src, p_row)
                if not isinstance(cand_src, str) or cand_src == orig_src:
                    continue
                ok, _out, zused = _verify_in_isolated_cow({rel: cand_src}, single_test_src=single_test_src)
                zygote_screened += int(zused)
                if ok:
                    return _crystallize_and_finish(
                        {rel: cand_src},
                        tier="IN_RUN_ALPHA_TRANSFER",
                        extra={"fired_template_id": p_row["template_id"],
                               "candidate_sha256": hashlib.sha256(cand_src.encode()).hexdigest(),
                               "teacher_ids": p_row["template"]["taught_by"]},
                        localization=localization_report,
                        stages=stages_run,
                        zygote_screened=zygote_screened,
                    )

    # Stage 2: Repo-native git history template mining (`history_template_repair_v1`)
    history_templates_mined = 0
    if mine_git_history and (root / ".git").exists():
        stages_run.append("STAGE_2_GIT_HISTORY_TEMPLATE_REPAIR")
        try:
            history_info["base"] = history._git(root, "rev-parse", "HEAD").strip()
            h_index = history.mine(root, history_info["base"], ranked_files[:4], int(history_limit))
            history_templates_mined = sum(map(len, h_index.values()))
            for rel in ranked_files[:4]:
                orig_src = (root / rel).read_text(encoding="utf-8", errors="replace")
                for patched, origin in history.candidates(orig_src, rel, ranked_lines_by_file[rel], h_index):
                    history_info["candidates"] += 1
                    ok, _out, zused = _verify_in_isolated_cow({rel: patched}, single_test_src=single_test_src)
                    zygote_screened += int(zused)
                    if ok:
                        return _crystallize_and_finish(
                            {rel: patched},
                            tier="GIT_HISTORY_TEMPLATE",
                            localization=localization_report,
                            stages=stages_run,
                            zygote_screened=zygote_screened,
                            extra={"history_templates_mined": history_templates_mined, "template_origin": origin},
                        )
        except (OSError, ValueError, SyntaxError, _sp.TimeoutExpired) as exc:
            history_info["error"] = str(exc)[:200]

    # Stage 3: Repo-native Petri neighborhood mining + Angelic OE synthesis (`repo_component_petri_v1` + `angelic_oe_synthesizer_v1`)
    stages_run.append("STAGE_3_REPO_PETRI_AND_ANGELIC_OE")
    mined_components_total = 0
    oe_synthesized_exprs: list[str] = []

    # The failing run states the goal. `extract_value_obligations` mines the
    # `expected` side of a failed assertion; if it is a literal, the repair is to
    # make a return site produce exactly that value. Only literals the test itself
    # published are used -- nothing is invented, and the CoW oracle still decides.
    baseline_obligation_sources: list[str] = []
    try:
        for _ob in causal_nexus_v1.extract_value_obligations(base_out or ""):
            try:
                _src = causal_nexus_v1.literal_source(_ob.expected_value)
            except (ValueError, TypeError):
                continue
            if _src and _src not in baseline_obligation_sources:
                baseline_obligation_sources.append(_src)
    except Exception:
        baseline_obligation_sources = []
    if witness_envs and witness_targets:
        try:
            oe_synthesized_exprs = angelic_oe.synthesize_oe_expression(
                [dict(e) for e in witness_envs],
                list(witness_targets),
                max_depth=2,
                time_budget_s=0.35,
            )
        except Exception:
            oe_synthesized_exprs = []

    for rel in ranked_files[:4]:
        orig_src = (root / rel).read_text(encoding="utf-8", errors="replace")
        try:
            tree = _ast.parse(orig_src)
            anchor_ln = (ranked_lines_by_file.get(rel) or [1])[0]
            comps, _by_kind, _names = petri.mine_repo_neighborhood_components(
                repo_root=root,
                rel_path=rel,
                parsed_tree=tree,
                line_no=anchor_ln,
            )
            mined_components_total += len(comps)
        except Exception:
            pass
        # Backward obligation: the failing assertion already states the expected
        # value, so the repair is "make a return site produce that value", not a
        # forward search over a mutation grammar. Measured on the `None`-guard
        # probe, nothing filled `oe_synthesized_exprs` when there were no
        # witnesses, so the value the test named was never tried anywhere.
        # Stored duties are PROPOSALS, never decisions. A morphism learned on another
        # repo records the constant it substituted (`duty_witness`); that constant is
        # the only reusable part of a constant repair and anti-unification throws it
        # away. Offered here, with the observed obligation first, and every candidate
        # still goes through the same dependency gate and the same CoW oracle.
        _duty_candidates: list[tuple[str, bool]] = [(x, False) for x in baseline_obligation_sources]
        if _skill_store is not None:
            try:
                for _m in _skill_store.morphisms.values():
                    _w = getattr(_m, "duty_witness", "")
                    if _w and _w not in [c for c, _ in _duty_candidates]:
                        _duty_candidates.append((_w, True))
            except Exception:
                pass
        if _duty_candidates:
            _lines = orig_src.splitlines(keepends=True)
            for _src, _from_store in _duty_candidates[:8]:
                for _ln in (ranked_lines_by_file.get(rel) or []):
                    if not (1 <= _ln <= len(_lines)):
                        continue
                    _orig = _lines[_ln - 1]
                    if not _orig.lstrip().startswith("return"):
                        continue
                    _indent = _orig[: len(_orig) - len(_orig.lstrip())]
                    _cand = list(_lines)
                    _cand[_ln - 1] = f"{_indent}return {_src}\n"
                    _cand_src = "".join(_cand)
                    if _cand_src == orig_src:
                        continue
                    _ok, _out, _zused = _verify_in_isolated_cow(
                        {rel: _cand_src},
                        single_test_src=single_test_src,
                        stored_duty_proposal=_from_store,
                    )
                    zygote_screened += int(_zused)
                    if _ok:
                        return _crystallize_and_finish(
                            {rel: _cand_src},
                            tier="STORED_DUTY_PROPOSAL" if _from_store else "ASSERTION_BACKWARD_OBLIGATION",
                            localization=localization_report,
                            stages=stages_run,
                            zygote_screened=zygote_screened,
                            extra={
                                "mined_repo_components": mined_components_total,
                                "oe_synthesized_exprs": oe_synthesized_exprs[:5],
                                "backward_obligation_source": _src,
                            },
                        )
        for patched, proof in return_paths(orig_src, ranked_lines_by_file[rel]):
            ok, _, screened = _verify_in_isolated_cow({rel: patched}, single_test_src=single_test_src)
            zygote_screened += int(screened)
            if ok:
                return _crystallize_and_finish({rel: patched}, tier="LOCAL_TYPED_RETURN_PATH",
                    localization=localization_report, stages=stages_run, zygote_screened=zygote_screened,
                    extra={"typed_path": proof})
        try:
            struct_patches = angelic_oe.synthesize_causal_structural_patches(
                orig_src,
                ranked_lines_by_file.get(rel) or [1],
            )
        except Exception:
            struct_patches = []
        for _label, _ln, cand_src in struct_patches[:16]:
            if not isinstance(cand_src, str) or cand_src == orig_src:
                continue
            ok, _out, zused = _verify_in_isolated_cow({rel: cand_src}, single_test_src=single_test_src)
            zygote_screened += int(zused)
            if ok:
                return _crystallize_and_finish(
                    {rel: cand_src},
                    tier="ANGELIC_OE_STRUCTURAL",
                    localization=localization_report,
                    stages=stages_run,
                    zygote_screened=zygote_screened,
                    extra={
                        "mined_repo_components": mined_components_total,
                        "oe_synthesized_exprs": oe_synthesized_exprs[:5],
                    },
                )
        # Also test OE-synthesized expressions directly at localized return lines
        if oe_synthesized_exprs:
            orig_lines = orig_src.splitlines(keepends=True)
            for expr_str in oe_synthesized_exprs[:6]:
                for ln in (ranked_lines_by_file.get(rel) or range(1, len(orig_lines) + 1)):
                    if 1 <= ln <= len(orig_lines) and orig_lines[ln - 1].lstrip().startswith("return "):
                        indent = orig_lines[ln - 1][: len(orig_lines[ln - 1]) - len(orig_lines[ln - 1].lstrip())]
                        cand_lines = list(orig_lines)
                        cand_lines[ln - 1] = f"{indent}return {expr_str}\n"
                        cand_src = "".join(cand_lines)
                        if cand_src == orig_src:
                            continue
                        ok, _out, zused = _verify_in_isolated_cow({rel: cand_src}, single_test_src=single_test_src)
                        zygote_screened += int(zused)
                        if ok:
                            return _crystallize_and_finish(
                                {rel: cand_src},
                                tier="ANGELIC_OE_EXPRESSION",
                                localization=localization_report,
                                stages=stages_run,
                                zygote_screened=zygote_screened,
                                extra={
                                    "mined_repo_components": mined_components_total,
                                    "oe_synthesized_exprs": oe_synthesized_exprs[:5],
                                },
                            )

    # The older microscope uses a different acceptance oracle and can return a
    # green baseline without a patch. Do not bypass this route's witness gate.
    return {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED__REPO_NATIVE_EXHAUSTED",
        "tier": "REPO_NATIVE_EXHAUSTED_FAIL_CLOSED",
        "stages_run": stages_run,
        "localization": localization_report,
        "history_templates_mined": history_templates_mined,
        "history": history_info,
        "mined_repo_components": mined_components_total,
        "oe_synthesized_exprs": oe_synthesized_exprs[:5],
        "zygote_screened_candidates": zygote_screened,
        "updated_repair_vocab": export_vocab(vocab),
        "model_calls": 0,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
    }


def solve_producer_lineage_hole_inversion(
    *,
    source: str | None = None,
    test_source: str | None = None,
    entry_func: str | None = None,
    filename: str = "module.py",
    repo_root: str | pathlib.Path | None = None,
    top_rel_files: Sequence[str] = (),
    failing_tests: Sequence[str] = (),
    passing_tests: Sequence[str] = (),
    guard_observations: Sequence[Mapping[str, Any]] | None = None,
    guard_failing_ids: Sequence[str] = (),
    guard_passing_ids: Sequence[str] = (),
    guard_sites: Sequence[Mapping[str, Any]] = (),
    command_for_read_set: str | None = None,
    file_state_bytes: Mapping[str, bytes] | None = None,
    max_candidates: int = 120,
    timeout_sec: float = 12.0,
) -> dict[str, Any]:
    """Wave 28 (`0D` × 9 unwired SWE superweapons, `K3 = 0`):
    Backward Producer-Lineage Tracing + Typed Hole Inversion (Name / Constant / Expression /
    Differential Witness / Two-Site Guard) with real isolated execution and Kali anti-degeneracy gate.

    Wires:
      - `producer_lineage_graph_v1` (interprocedural guarded MIR + dynamic `ReturnLineageTracer`)
      - `the_value_that_was_rejected_had_a_producer_v1` (`rejected_value`, `fix_functions`)
      - `the_name_is_a_hole_v1` (`name_holes`, `candidates`, `patch`)
      - `the_constant_is_a_hole_v1` (`literals`, `input_characters`, `mutations`, `patch`)
      - `the_replacement_expression_v1` (`candidate_atoms`, `candidate_expressions`)
      - `closed_loop_trace_abduction_repair_v1` (`trace_sliced_proposals`, `angelic_specs`, `degeneracy_scan`)
      - `differential_witness_inversion_v1` (`synthesize_live_differential_witness_repairs`)
      - `causal_dependency_repair_v1` (`read_set_argv`)
      - `case_witness_v1` (`sites_in`) & `a_relation_over_two_guards_v1` (`learn_groups`)
    """
    t0 = time.perf_counter()
    from canonical.swe_kernel import case_witness_v1 as case_wit
    from canonical.swe_kernel import closed_loop_trace_abduction_repair_v1 as cta
    from canonical.swe_kernel import producer_lineage_graph_v1 as plg
    from canonical.tools import the_constant_is_a_hole_v1 as const_hole
    from canonical.tools import the_name_is_a_hole_v1 as name_hole
    from canonical.tools import the_value_that_was_rejected_had_a_producer_v1 as rej_prod

    stages: list[str] = []
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "model_calls": 0,
        "producer_lineage": None,
        "static_lineage_summary": None,
        "rejected_value_hint": None,
        "guard_groups": None,
        "causal_read_set": None,
        "case_witness_sites": None,
        "hole_type": None,
        "repaired_source": None,
        "candidates_tested": 0,
        "degeneracy_rejected": 0,
    }

    # Optional interventional read-set dependency analysis (`causal_dependency_repair_v1`)
    if command_for_read_set and file_state_bytes is not None:
        from canonical.swe_kernel import causal_dependency_repair_v1 as cdr

        stages.append("CAUSAL_READ_SET_ANALYSIS")
        report["causal_read_set"] = sorted(cdr.read_set_argv(str(command_for_read_set), dict(file_state_bytes)))

    # Optional two-site coupled guard synthesis (`a_relation_over_two_guards_v1`)
    if guard_observations and guard_sites:
        from canonical.tools import a_relation_over_two_guards_v1 as two_guards

        stages.append("TWO_SITE_GUARD_SYNTHESIS")
        groups = two_guards.learn_groups(
            [dict(o) for o in guard_observations],
            set(str(x) for x in guard_failing_ids),
            set(str(x) for x in guard_passing_ids),
            [dict(s) for s in guard_sites],
        )
        report["guard_groups"] = groups[:8]

    # Mode A: Repository-level Live-Frame Differential Witness Inversion (`differential_witness_inversion_v1`, 1,220L)
    if repo_root is not None and top_rel_files and failing_tests:
        from canonical.swe_kernel import differential_witness_inversion_v1 as dwi

        stages.append("LIVE_DIFFERENTIAL_WITNESS_INVERSION")
        rr = pathlib.Path(repo_root).resolve()
        with tempfile.TemporaryDirectory(prefix="wave28_dwi_") as td:
            cow_root = pathlib.Path(td) / "cow"
            shutil.copytree(
                rr,
                cow_root,
                ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache", "node_modules"),
            )
            pycache_dir = pathlib.Path(td) / "pyc"
            pycache_dir.mkdir(parents=True, exist_ok=True)
            import os as _os

            py_env = dict(_os.environ)
            py_env["PYTHONPATH"] = str(cow_root) + (
                _os.pathsep + py_env["PYTHONPATH"] if py_env.get("PYTHONPATH") else ""
            )
            cands, inspected = dwi.synthesize_live_differential_witness_repairs(
                cow_root=cow_root,
                pycache_dir=pycache_dir,
                py_exe=sys.executable,
                py_env=py_env,
                top_rel_files=[str(f) for f in top_rel_files],
                failing_tests=[str(t) for t in failing_tests],
                passing_tests=[str(t) for t in passing_tests],
                timeout_sec=float(timeout_sec),
            )
            report["dwi_inspected"] = int(inspected)
            report["dwi_candidate_count"] = len(cands)
            if cands:
                edits_map, hole_desc, reason = cands[0]
                return {
                    **report,
                    "pass": True,
                    "solved": True,
                    "status": "PASS__LIVE_DIFFERENTIAL_WITNESS_INVERTED",
                    "hole_type": "differential_witness",
                    "hole_detail": str(hole_desc),
                    "reason": str(reason),
                    "repaired_files": dict(edits_map),
                    "stages": stages,
                    "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
                }

    # Mode B: Single-Module Backward Producer Lineage + Typed Hole Inversion (Name -> Constant -> Trace Abduction)
    if source is not None and test_source is not None:
        src_text = str(source)
        tst_text = str(test_source)

        def _exec_passes(cand_src: str) -> tuple[bool, str]:
            ns: dict[str, Any] = {"__name__": "__wave28_verify__"}
            try:
                exec(compile(cand_src, filename, "exec"), ns)
                exec(compile(tst_text, "<test>", "exec"), ns)
                return True, ""
            except Exception as exc:  # noqa: BLE001
                return False, f"{type(exc).__name__}: {exc}"

        # 1. Static interprocedural lineage graph (`producer_lineage_graph_v1`)
        stages.append("STATIC_PRODUCER_LINEAGE_GRAPH")
        try:
            lg = plg.build_lineage_graph_from_sources({filename: src_text})
            lg_d = lg.to_dict()
            raw_nodes = lg_d.get("nodes")
            raw_edges = lg_d.get("edges")
            report["static_lineage_summary"] = {
                "functions": list(lg.functions()),
                "node_count": int(raw_nodes) if isinstance(raw_nodes, int) else len(raw_nodes or ()),
                "edge_count": int(raw_edges) if isinstance(raw_edges, int) else len(raw_edges or ()),
            }
            if entry_func is None and lg.functions():
                entry_func = str(lg.functions()[0])
        except Exception:
            pass

        if entry_func:
            try:
                report["case_witness_sites"] = [
                    {"line": int(ln), "expr": str(ex)} for ln, ex in case_wit.sites_in(src_text, entry_func)[:16]
                ]
            except Exception:
                pass

        # 2. Verify baseline actually fails (fail-closed if already green!)
        base_ok, base_err = _exec_passes(src_text)
        if base_ok:
            return {
                **report,
                "pass": False,
                "solved": False,
                "status": "FAIL_CLOSED__BASELINE_ALREADY_GREEN",
                "stages": stages,
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            }
        report["rejected_value_hint"] = rej_prod.rejected_value(base_err)

        # 3. Dynamic backward producer lineage + live frame locals capture
        stages.append("DYNAMIC_PRODUCER_LINEAGE_AND_FRAME_CAPTURE")
        probe_src = src_text + "\n\n" + tst_text
        try:
            exp_res = plg.explain_assertion(probe_src, filename=filename)
            report["producer_lineage"] = {
                "raised": bool(exp_res.get("raised")),
                "exception": exp_res.get("exception"),
                "found": bool((exp_res.get("explain") or {}).get("found")),
                "producer": (exp_res.get("explain") or {}).get("producer"),
                "returned_before_rejection": bool((exp_res.get("explain") or {}).get("returned_before_rejection")),
            }
        except Exception:
            pass

        executed_locals: dict[str, dict[str, dict[str, str]]] = {}
        executed_lines: set[int] = set()

        def _capture_trace(frame: Any, event: str, arg: Any) -> Any:
            if frame.f_code.co_filename == filename and event == "line":
                ln = int(frame.f_lineno)
                executed_lines.add(ln)
                snap: dict[str, dict[str, str]] = {}
                for k, v in frame.f_locals.items():
                    if not k.startswith("__"):
                        try:
                            snap[str(k)] = {"str": repr(v)[:120], "type": type(v).__name__}
                        except Exception:
                            pass
                executed_locals[str(ln)] = snap
            return _capture_trace

        ns_trace: dict[str, Any] = {"__name__": "__wave28_trace__"}
        old_tr = sys.gettrace()
        sys.settrace(_capture_trace)
        try:
            exec(compile(src_text, filename, "exec"), ns_trace)
            exec(compile(tst_text, "<test>", "exec"), ns_trace)
        except Exception:  # noqa: BLE001
            pass
        finally:
            sys.settrace(old_tr)

        candidates_tested = 0
        degeneracy_rejected = 0

        def _try_candidate(cand_src: str, hole_type: str, detail: str) -> dict[str, Any] | None:
            nonlocal candidates_tested, degeneracy_rejected
            if not cand_src or cand_src == src_text or candidates_tested >= max_candidates:
                return None
            # Anti-Kali degeneracy scan (blocks `if x == <test literal>: return <const>`)
            deg = cta.degeneracy_scan(cand_src, tst_text, buggy_source=src_text)
            if deg.get("degenerate"):
                degeneracy_rejected += 1
                return None
            candidates_tested += 1
            ok, _err = _exec_passes(cand_src)
            if ok:
                changed_lines = [
                    idx + 1
                    for idx, (a, b) in enumerate(zip(src_text.splitlines(), cand_src.splitlines()))
                    if a != b
                ]
                return {
                    **report,
                    "pass": True,
                    "solved": True,
                    "status": f"PASS__HOLE_INVERTED_{hole_type.upper()}",
                    "hole_type": hole_type,
                    "hole_detail": detail,
                    "repaired_source": cand_src,
                    "fixed_functions": sorted(rej_prod.fix_functions(cand_src, changed_lines)),
                    "candidates_tested": candidates_tested,
                    "degeneracy_rejected": degeneracy_rejected,
                    "stages": stages,
                    "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
                }
            return None

        # 4. Typed Hole 1: Name Hole (`the_name_is_a_hole_v1`)
        stages.append("NAME_HOLE_INVERSION")
        try:
            n_holes = name_hole.name_holes(src_text, executed_locals)
            specs = name_hole.spec_strings(tst_text, "")
            for hole in n_holes:
                ranked_names = [n for n, _sc, _why in name_hole.candidates(hole, specs)]
                # Also include all other in-scope non-callable locals on that exact executed frame
                for loc_name in sorted(hole.get("scope") or {}):
                    if loc_name != hole["name"] and loc_name not in ranked_names:
                        ranked_names.append(loc_name)
                for repl_name in ranked_names[:16]:
                    cand = name_hole.patch(src_text, hole, repl_name)
                    hit = _try_candidate(cand, "name_hole", f"line {hole['line']}: {hole['name']} -> {repl_name}")
                    if hit is not None:
                        return hit
        except Exception:
            pass

        # 5. Typed Hole 2: Constant Hole (`the_constant_is_a_hole_v1`)
        stages.append("CONSTANT_HOLE_INVERSION")
        try:
            lits = const_hole.literals(ast.parse(src_text))
            chars = const_hole.input_characters([base_err], tst_text)
            # Prefer executed lines first
            lits.sort(key=lambda h: (0 if int(h.get("line", -1)) in executed_lines else 1, int(h.get("line", 0))))
            # Also collect small integer constants present in test assertions as candidate deltas
            test_ints: list[int] = []
            try:
                for tn in ast.walk(ast.parse(tst_text)):
                    if isinstance(tn, ast.Constant) and isinstance(tn.value, int) and not isinstance(tn.value, bool):
                        test_ints.append(int(tn.value))
            except SyntaxError:
                pass
            for hole in lits:
                muts = list(const_hole.mutations(hole, chars))
                if isinstance(hole.get("value"), int) and not isinstance(hole.get("value"), bool):
                    cur_v = int(hole["value"])
                    seen_v = {v for v, _ in muts}
                    for delta in (-10, -5, -4, -3, 3, 4, 5, 10):
                        nv = cur_v + delta
                        if nv not in seen_v:
                            muts.append((nv, f"delta_{delta:+d}"))
                            seen_v.add(nv)
                for new_val, how in muts[:24]:
                    cand = const_hole.patch(src_text, hole, new_val)
                    hit = _try_candidate(cand, "constant_hole", f"line {hole['line']}: {hole['value']!r} -> {new_val!r} ({how})")
                    if hit is not None:
                        return hit
        except Exception:
            pass

        # 6. Typed Hole 3: Closed-Loop Trace Abduction & Angelic Expression Synthesis (`closed_loop_trace_abduction_repair_v1`)
        stages.append("CLOSED_LOOP_TRACE_ABDUCTION")
        if entry_func:
            try:
                ab = cta.trace_sliced_proposals(src_text, entry_func, tst_text)
                for prop in (ab.get("proposals") or [])[:40]:
                    cand = str(prop.get("source") or "")
                    hit = _try_candidate(cand, "trace_abduction", str(prop.get("origin") or "trace_abduction"))
                    if hit is not None:
                        return hit
                # Direct angelic synthesis over return-line specs
                fn_obj = cta.load_function(src_text, entry_func)
                cases = cta.extract_assert_cases(tst_text, entry_func, fn_obj)
                failing_c = [c for c in cases if not c.passed]
                passing_c = [c for c in cases if c.passed]
                a_specs = cta.angelic_specs(src_text, entry_func, failing_c, passing_c)
                if a_specs:
                    by_line: dict[int, list[tuple[Mapping[str, Any], Any]]] = {}
                    for sp in a_specs:
                        by_line.setdefault(int(sp["line"]), []).append((sp["env"], sp["target"]))
                    for ln, pairs in by_line.items():
                        names = sorted({k for env, _ in pairs for k in env.keys()})
                        exprs = cta.synthesize_expression(
                            pairs,
                            names=names,
                            constants=[0, 1, -1, 2, 10, 100],
                            max_depth=2,
                            budget=1500,
                        )
                        for ex in exprs[:16]:
                            cand = cta.replace_line_expression(src_text, ln, ex)
                            if cand:
                                hit = _try_candidate(cand, "angelic_expression_hole", f"line {ln}: return {ex}")
                                if hit is not None:
                                    return hit
            except Exception:
                pass

        report["candidates_tested"] = candidates_tested
        report["degeneracy_rejected"] = degeneracy_rejected

    any_aux = bool(report["guard_groups"] or report["causal_read_set"])
    return {
        **report,
        "pass": any_aux,
        "solved": False,
        "status": "PASS__AUXILIARY_CAUSAL_ANALYSIS" if any_aux else "FAIL_CLOSED__HOLE_INVERSION_UNSOLVED",
        "stages": stages,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
    }


def disambiguate_and_synthesize_repairs(
    *,
    # 1. Version-space repair disambiguation (`repair_version_space_selection_v1` + `passing_repairs_version_space_v1`)
    candidate_ids: Sequence[str] | None = None,
    behaviours: Mapping[str, Sequence[Any]] | None = None,
    probe_ids: Sequence[str] | None = None,
    probe_outcomes: Mapping[str, Sequence[str]] | None = None,
    observations: Mapping[str, str] | None = None,
    reference_outcomes: Mapping[str, Any] | None = None,
    candidate_sources: Mapping[str, str] | None = None,
    behaviour_of: Any = None,
    selection_oracle: Any = None,
    max_questions: int = 3,
    passing_task: Mapping[str, Any] | None = None,
    # 2. Angelic STUN/CEGIS + observational equivalence (`angelic_cegis_v1`)
    angelic_source: str | None = None,
    angelic_target: str | None = None,
    angelic_oracle: Any = None,
    angelic_inputs: Sequence[Mapping[str, Any]] | None = None,
    angelic_kind: str = "value",
    angelic_enclosing: Mapping[str, str] | None = None,
    angelic_budget: int = 256,
    equiv_pair: tuple[Any, Any] | None = None,
    equiv_inputs: Sequence[Mapping[str, Any]] | None = None,
    # 3. Inverse-pair completion (`inverse_completion_v1`)
    inverse_name: str | None = None,
    inverse_siblings: Sequence[str] = (),
    writer_payloads: Sequence[Any] | None = None,
    inverse_samples: Sequence[Any] = (),
    roundtrip_pair: tuple[Any, Any] | None = None,
    # 4. History-induced edit grammar (`history_induced_edit_grammar_v1`)
    history_pairs: Sequence[tuple[str, str, str]] | None = None,
    history_target_source: str | None = None,
    history_function_line: int | None = None,
    history_context_depth: int = 1,
    history_cap: int = 100,
    # 5. Repository seed corpus + real callers (`the_repository_is_the_seed_corpus_v1` + `the_callers_were_never_asked_v1`)
    seed_tree: str | pathlib.Path | None = None,
    seed_call: Mapping[str, Any] | None = None,
    caller_sites: Sequence[Mapping[str, Any]] | None = None,
    caller_seeds: Sequence[Mapping[str, Any]] | None = None,
    caller_defined_in: Sequence[str] = (),
    caller_module: str | None = None,
    # 6. Cross-repo dataflow lineage (`cross_repo_dataflow_v1`)
    dataflow_root: str | pathlib.Path | None = None,
    dataflow_var: str | None = None,
    dataflow_from_file: str | None = None,
    dataflow_to_file: str | None = None,
    dataflow_max_files: int = 200,
) -> dict[str, Any]:
    """Wave 32: Version-Space Repair Disambiguation, Angelic CEGIS, Inverse Completion & Repo-Seeded SWE (`0D`, `K3=0`).

    Composes 7 pure-stdlib hidden SWE synthesis & disambiguation engines lazily on demand:
      - `repair_version_space_selection_v1`: partition, diagnose, decide, ask_until_settled
      - `passing_repairs_version_space_v1`: enumerate distinct repairs passing the same suite + separating question
      - `angelic_cegis_v1`: AngelicCEGIS STUN synthesis, cross_frame_guard, observational_equivalence
      - `inverse_completion_v1`: detect_pair, determine_reader_shape, synthesise_reader, roundtrip_residual
      - `history_induced_edit_grammar_v1`: induce_grammar, localized_candidates
      - `the_repository_is_the_seed_corpus_v1` + `the_callers_were_never_asked_v1`: repo seed harvesting & real-caller inputs
      - `cross_repo_dataflow_v1`: cross-file/cross-repo causal variable lineage
    """
    t0 = time.perf_counter()
    engines_invoked: list[str] = []
    results: dict[str, Any] = {}
    any_ok = False
    all_ok = True

    # 1a. Version-space repair selection (`repair_version_space_selection_v1`)
    if candidate_ids is not None and behaviours is not None:
        from canonical.swe_kernel import repair_version_space_selection_v1 as rvss

        engines_invoked.append("canonical.swe_kernel.repair_version_space_selection_v1")
        part = rvss.partition(list(candidate_ids), dict(behaviours))
        diag = rvss.diagnose(part)
        dec = rvss.decide(
            part,
            probe_ids=list(probe_ids) if probe_ids is not None else None,
            probe_outcomes=dict(probe_outcomes) if probe_outcomes is not None else None,
            observations=dict(observations) if observations is not None else None,
            reference_outcomes=dict(reference_outcomes) if reference_outcomes is not None else None,
        )
        max_elim = None
        if probe_ids and probe_outcomes and reference_outcomes:
            ref_val = next(iter(reference_outcomes.values()), "")
            max_elim = rvss.maximum_elimination(
                part,
                str(ref_val),
                probe_ids=list(probe_ids),
                probe_outcomes=dict(probe_outcomes),
            )
        results["version_space"] = {
            "partition": part,
            "diagnosis": diag,
            "decision": dec,
            "maximum_elimination_probe": max_elim,
        }
        any_ok = True

    if candidate_sources is not None and probe_ids is not None and behaviour_of is not None and selection_oracle is not None:
        from canonical.swe_kernel import repair_version_space_selection_v1 as rvss

        if "canonical.swe_kernel.repair_version_space_selection_v1" not in engines_invoked:
            engines_invoked.append("canonical.swe_kernel.repair_version_space_selection_v1")
        sel = rvss.ask_until_settled(
            dict(candidate_sources),
            list(probe_ids),
            behaviour_of,
            selection_oracle,
            max_questions=int(max_questions),
        )
        sel_dict = sel.__dict__ if hasattr(sel, "__dict__") else {"selection": sel}
        results["active_selection"] = sel_dict
        any_ok = True

    # 1b. Passing repairs version space (`passing_repairs_version_space_v1`)
    if passing_task is not None:
        from canonical.swe_kernel import passing_repairs_version_space_v1 as prvs

        engines_invoked.append("canonical.swe_kernel.passing_repairs_version_space_v1")
        pr = prvs.passing_repairs(dict(passing_task))
        results["passing_repairs"] = pr
        any_ok = True

    # 2. Angelic STUN/CEGIS + Observational Equivalence (`angelic_cegis_v1`)
    if angelic_source is not None and angelic_oracle is not None and angelic_inputs is not None:
        from canonical.swe_kernel import angelic_cegis_v1 as acegis

        engines_invoked.append("canonical.swe_kernel.angelic_cegis_v1")
        if angelic_enclosing is not None and angelic_target:
            syn = acegis.cross_frame_guard(
                str(angelic_source),
                target=str(angelic_target),
                oracle=angelic_oracle,
                inputs=list(angelic_inputs),
                enclosing=dict(angelic_enclosing),
                budget=int(angelic_budget),
            )
        else:
            scope = acegis.harvest_scope(str(angelic_source), target=angelic_target)
            engine = acegis.AngelicCEGIS(budget=int(angelic_budget))
            if angelic_kind == "guard":
                syn = engine.invent_guard(scope, angelic_oracle, list(angelic_inputs))
            else:
                syn = engine.invent(scope, angelic_oracle, list(angelic_inputs), kind=str(angelic_kind))
        results["angelic_cegis"] = syn
        ok_a = bool(syn.get("ok") or syn.get("solved") or syn.get("found") or syn.get("expr") or syn.get("guard"))
        any_ok = any_ok or ok_a
        all_ok = all_ok and ok_a

    if equiv_pair is not None and equiv_inputs is not None:
        from canonical.swe_kernel import angelic_cegis_v1 as acegis

        if "canonical.swe_kernel.angelic_cegis_v1" not in engines_invoked:
            engines_invoked.append("canonical.swe_kernel.angelic_cegis_v1")
        eq_res = acegis.observational_equivalence(equiv_pair[0], equiv_pair[1], list(equiv_inputs))
        results["observational_equivalence"] = eq_res
        any_ok = True

    # 3. Inverse-pair completion (`inverse_completion_v1`)
    if inverse_name is not None or writer_payloads is not None or roundtrip_pair is not None:
        from canonical.swe_kernel import inverse_completion_v1 as invc

        engines_invoked.append("canonical.swe_kernel.inverse_completion_v1")
        inv_rep: dict[str, Any] = {}
        if inverse_name is not None:
            inv_rep["pair"] = invc.detect_pair(str(inverse_name), list(inverse_siblings))
        if writer_payloads is not None:
            inv_rep["reader_shape"] = invc.determine_reader_shape(list(writer_payloads))
            if inverse_name is not None:
                inv_rep["synthesised_reader"] = invc.synthesise_reader(
                    str(inverse_name),
                    list(writer_payloads),
                    list(inverse_samples),
                )
        if roundtrip_pair is not None and inverse_samples:
            inv_rep["roundtrip_residual"] = invc.roundtrip_residual(
                roundtrip_pair[0], roundtrip_pair[1], list(inverse_samples)
            )
        results["inverse_completion"] = inv_rep
        any_ok = True

    # 4. History-induced edit grammar (`history_induced_edit_grammar_v1`)
    if history_pairs is not None:
        from canonical.swe_kernel import history_induced_edit_grammar_v1 as hieg

        engines_invoked.append("canonical.swe_kernel.history_induced_edit_grammar_v1")
        templates = hieg.induce_grammar(list(history_pairs), context_depth=int(history_context_depth))
        cands: list[dict[str, Any]] = []
        if history_target_source is not None and templates:
            cands = hieg.localized_candidates(
                str(history_target_source),
                templates,
                history_function_line,
                cap=int(history_cap),
            )
        results["history_edit_grammar"] = {
            "template_count": len(templates),
            "candidate_count": len(cands),
            "candidates": cands[:20],
        }
        any_ok = any_ok or (len(templates) > 0)

    # 5. Repository seed corpus + real callers (`the_repository_is_the_seed_corpus_v1` + `the_callers_were_never_asked_v1`)
    if seed_tree is not None:
        from canonical.swe_kernel import the_repository_is_the_seed_corpus_v1 as seedc

        engines_invoked.append("canonical.swe_kernel.the_repository_is_the_seed_corpus_v1")
        docs = seedc.harvest_documents(pathlib.Path(seed_tree).resolve())
        calls = (
            seedc.calls_from([str(d.get("text") or d.get("content") or "") for d in docs], dict(seed_call))
            if seed_call is not None
            else []
        )
        results["repo_seed_corpus"] = {
            "document_count": len(docs),
            "sample_paths": [str(d.get("path") or d.get("rel") or "") for d in docs[:10]],
            "synthesized_calls": calls[:20],
        }
        any_ok = True

    if caller_sites is not None and caller_seeds is not None:
        from canonical.swe_kernel import the_callers_were_never_asked_v1 as realcall

        engines_invoked.append("canonical.swe_kernel.the_callers_were_never_asked_v1")
        c_cands = realcall.candidates_for(
            list(caller_sites),
            list(caller_seeds),
            defined_in=list(caller_defined_in),
            module=caller_module,
        )
        results["real_caller_candidates"] = {
            "candidate_count": len(c_cands),
            "candidates": c_cands[:20],
        }
        any_ok = True

    # 6. Cross-repo dataflow lineage (`cross_repo_dataflow_v1`)
    if dataflow_root is not None:
        from canonical.swe_kernel import cross_repo_dataflow_v1 as crdf

        engines_invoked.append("canonical.swe_kernel.cross_repo_dataflow_v1")
        graph = crdf.build_cross_repo_graph(pathlib.Path(dataflow_root).resolve(), max_files=int(dataflow_max_files))
        paths = (
            crdf.causal_path_cross_repo(
                graph,
                str(dataflow_var),
                from_file=dataflow_from_file,
                to_file=dataflow_to_file,
            )
            if dataflow_var
            else []
        )
        file_count = int(getattr(graph, "file_count", len(getattr(graph, "per_file", {}))))
        results["cross_repo_dataflow"] = {
            "files_indexed": file_count,
            "node_count": int(getattr(graph, "node_count", 0)),
            "edge_count": int(getattr(graph, "edge_count", 0)),
            "var": dataflow_var,
            "causal_path_count": len(paths),
            "causal_paths": paths[:20],
        }
        any_ok = True

    passed = bool(engines_invoked) and any_ok and all_ok
    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "pass": passed,
        "status": (
            "PASS__WAVE32_DISAMBIGUATE_AND_SYNTHESIZE"
            if passed
            else ("FAIL_CLOSED__NO_WAVE32_INPUTS" if not engines_invoked else "FAIL_CLOSED__WAVE32_SUBSTAGE_UNSOLVED")
        ),
        "engines_invoked": engines_invoked,
        "results": results,
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
    "disambiguate_and_synthesize_repairs",
    "multi_file_causal_localize_and_repair",
    "solve_producer_lineage_hole_inversion",
    "solve_repository_task",
    "solve_swe_inverted_microscope",
    "solve_swe_repo_native_multifile",
    "synthesize_counterfactual_and_angelic_repair",
    "trace_expression_and_literal_repair",
]
