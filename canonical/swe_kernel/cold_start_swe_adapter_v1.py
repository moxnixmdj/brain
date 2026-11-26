#!/usr/bin/env python3
"""Cold-Start SWE Adapter (`cold_start_swe_adapter_v1`).

The bottleneck this removes
---------------------------
`UnifiedModel.solve_swe_repo_native` needs `(repo_root, test_targets, candidate_files)`.
A person (and every real benchmark) supplies `(repository, natural-language issue)`. That
gap is why PR #7080's measured SWE-bench Pro V2 Hard-51 result is **0/51**: not a failure
of repair, a failure of *reaching* repair. Nothing is learned from a goal the system
cannot even phrase to itself.

What this does, in the §9.1 order (Goal -> Scan -> Recall -> Acquire -> Act -> Verify)
------------------------------------------------------------------------------
1. **Goal.** Keep the issue text whole. It is the fixed point everything is measured against.
2. **Scan.** Walk the repository: test files, source files, the test framework actually used,
   the newest/noisiest artifacts. This is the same information a person gets from `ls` and
   `git status`, obtained by reading, not by guessing.
3. **Bind.** Choose `test_targets` and `candidate_files` by *evidence*:
      * targets  <- files whose names match the issue's own nouns, then test files that import
                    a symbol the issue names, then every test file (bounded);
      * candidates <- files that define a symbol the tests import and the issue names,
                    then files the targets import, then every source file ranking by
                    issue-term overlap.
   No model. Term overlap and import graphs only.
4. **Act & verify.** Hand the bound inputs to `solve_swe_repo_native`, which is honest about
   failure (`FAIL_CLOSED` with a named missing fact) and never guesses green.
5. **Refuse honestly.** With no test file, there is no oracle, so there is no verification,
   so there is no repair. That returns `FAIL_CLOSED: NO_ORACLE_TARGET` rather than a patch
   nobody can check. This is the largest single honesty constraint in the module.

Every result reports `model_calls: 0` and the evidence used to bind, so a wrong binding is
inspectable rather than mysterious (§11: separate verified / unverified / failed).
"""
from __future__ import annotations

import ast
import pathlib
import re
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "COLD_START_SWE_ADAPTER_V1"
AUTHORITY = "NONE_SANDBOX"

_SKIP_PARTS = frozenset({
    ".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "node_modules", ".venv", "venv", "build", "dist", ".tox", ".nox",
})

_STOPWORDS = frozenset(
    """
    a an the is are was were be been being of in on at to for from by with without and or not
    no if then else when while this that these those it its as into about over under after
    before should would could can cannot does do did done has have had having we you they he
    she i me my our your their them us but so than too very just also only same such which who
    what where how why all any both each few more most other some there here use used using
    get gets got make makes made cause causes caused when where fix fixes fixed bug bugs issue
    error errors fail fails failed failure test tests testing expected expect actual instead
    instead return returns returned call calls called function functions method methods value
    values code file files line lines still instead currently always never must shall need
    needs needed want wants work works working broken breaks broke crash crashes crashed
    raises raise raised exception via per non none true false null undefined
    """.split()
)

_TEST_NAME_RE = re.compile(r"^(?:test_.*|.*_test)\.py$")


def _issue_terms(issue_text: str) -> list[str]:
    """Salient terms from the issue, longest first (longer terms are more specific)."""
    words = re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", issue_text or "")
    seen: dict[str, None] = {}
    for w in words:
        lw = w.lower()
        if lw in _STOPWORDS:
            continue
        seen.setdefault(lw, None)
    return sorted(seen, key=lambda s: (-len(s), s))


def _repo_files(root: pathlib.Path, suffix: str = ".py") -> list[str]:
    out: list[str] = []
    for p in sorted(root.rglob(f"*{suffix}")):
        rel = p.relative_to(root)
        if any(part in _SKIP_PARTS for part in rel.parts):
            continue
        out.append(rel.as_posix())
    return out


def _is_test_path(rel: str) -> bool:
    name = rel.rsplit("/", 1)[-1]
    return bool(_TEST_NAME_RE.match(name)) or "/tests/" in f"/{rel}" or "/test/" in f"/{rel}"


def _imported_names(src: str) -> set[str]:
    """Names a module imports (`from x import a, b`) plus plain `import x` module stems."""
    out: set[str] = set()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return out
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                out.add(alias.name.split(".")[0])
        elif isinstance(node, ast.Import):
            for alias in node.names:
                out.add(alias.name.split(".")[0])
    return out


def _defined_names(src: str) -> set[str]:
    out: set[str] = set()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return out
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.add(node.name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for t in targets:
                if isinstance(t, ast.Name):
                    out.add(t.id)
    return out


def _module_stem(rel: str) -> str:
    return rel.rsplit("/", 1)[-1][:-3] if rel.endswith(".py") else rel


def scan_repository(root: pathlib.Path) -> dict[str, Any]:
    """Structural read of the repository. Pure I/O; no interpretation, no model."""
    files = _repo_files(root)
    tests = [f for f in files if _is_test_path(f)]
    sources = [f for f in files if not _is_test_path(f)]
    frameworks: list[str] = []
    test_sources = []
    for rel in tests[:40]:
        try:
            text = (root / rel).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        test_sources.append(text)
        if "import pytest" in text or "from pytest" in text:
            frameworks.append("pytest")
        if "import unittest" in text:
            frameworks.append("unittest")
        if re.search(r"^\s*def test_", text, re.M):
            frameworks.append("plain_functions")
    return {
        "python_files": len(files),
        "test_files": tests,
        "source_files": sources,
        "frameworks_detected": sorted(set(frameworks)),
    }


def bind_inputs(
    issue_text: str,
    root: pathlib.Path,
    scan: Mapping[str, Any],
    *,
    max_targets: int = 6,
    max_candidates: int = 8,
) -> dict[str, Any]:
    """Bind `(test_targets, candidate_files)` from evidence, and say which evidence was used."""
    terms = _issue_terms(issue_text)
    term_set = set(terms)
    tests: list[str] = list(scan.get("test_files") or ())
    sources: list[str] = list(scan.get("source_files") or ())
    evidence: dict[str, Any] = {"issue_terms": terms[:16], "steps": []}

    # ---- target selection ---------------------------------------------------------------
    scored: list[tuple[int, str]] = []
    for rel in tests:
        name = rel.lower().replace("_", "").replace("-", "")
        score = sum(3 for t in terms if t.replace("_", "") in name)
        try:
            text = (root / rel).read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = ""
        score += sum(2 for t in terms if t in text.lower())
        if score:
            scored.append((score, rel))
    scored.sort(key=lambda x: (-x[0], x[1]))
    targets = [rel for _, rel in scored[:max_targets]]
    if targets:
        evidence["steps"].append("TARGETS_BY_ISSUE_TERM_MATCH")
    else:
        # No lexical match: fall back to the whole test set, bounded. A wrong target still
        # produces an honest failure; a missing target produces no measurement at all.
        targets = tests[:max_targets]
        if targets:
            evidence["steps"].append("TARGETS_BY_FULL_TEST_SET_FALLBACK")

    # ---- candidate selection ------------------------------------------------------------
    wanted_symbols = _imported_names("\n".join(
        (root / t).read_text(encoding="utf-8", errors="replace") for t in targets
        if (root / t).is_file()
    ))
    evidence["symbols_tests_import"] = sorted(wanted_symbols)[:24]
    cands: list[tuple[int, str]] = []
    for rel in sources:
        try:
            text = (root / rel).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        defines = _defined_names(text)
        score = 0
        if defines & wanted_symbols:
            score += 5  # the tests import something this file defines
        if _module_stem(rel) in wanted_symbols:
            score += 5
        low = text.lower()
        score += sum(1 for t in terms if t in low)
        if score:
            cands.append((score, rel))
    cands.sort(key=lambda x: (-x[0], x[1]))
    candidates = [rel for _, rel in cands[:max_candidates]]
    if candidates:
        evidence["steps"].append("CANDIDATES_BY_IMPORT_GRAPH_AND_TERMS")
    else:
        candidates = sources[:max_candidates]
        if candidates:
            evidence["steps"].append("CANDIDATES_BY_FILE_ORDER_FALLBACK")

    return {
        "test_targets": targets,
        "candidate_files": candidates,
        "evidence": evidence,
    }


def solve_from_issue(
    issue_text: str,
    repo_root: str | pathlib.Path,
    *,
    timeout_s: float = 30.0,
    keep_patch_applied: bool = False,
    skill_store_path: str | pathlib.Path | None = None,
) -> dict[str, Any]:
    """Cold start: natural-language issue + repository in, verified repair or honest refusal out."""
    import time

    t0 = time.perf_counter()
    root = pathlib.Path(repo_root).resolve()
    base: dict[str, Any] = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "operation": "COLD_START_SWE",
        "issue": (issue_text or "").strip()[:400],
        "repo_root": str(root),
        "model_calls": 0,
    }
    if not root.is_dir():
        return {**base, "pass": False, "status": "FAIL_CLOSED", "reason": "REPO_ROOT_MISSING"}

    scan = scan_repository(root)
    base["scan"] = {
        "python_files": scan["python_files"],
        "test_file_count": len(scan["test_files"]),
        "frameworks_detected": scan["frameworks_detected"],
    }
    if not scan["test_files"]:
        # No oracle, no verification, no repair. Saying so is the honest outcome.
        return {
            **base,
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": "NO_ORACLE_TARGET__NO_TEST_FILE_IN_REPO",
            "elapsed_s": round(time.perf_counter() - t0, 3),
        }

    bound = bind_inputs(issue_text, root, scan)
    base["binding"] = bound

    from canonical.swe_kernel.canonical_swe_spine_v1 import solve_swe_repo_native_multifile

    res = solve_swe_repo_native_multifile(
        root,
        test_targets=bound["test_targets"],
        candidate_files=bound["candidate_files"],
        keep_patch_applied=keep_patch_applied,
        timeout_s=timeout_s,
        skill_store_path=skill_store_path,
    )
    return {
        **base,
        "pass": bool(res.get("pass")),
        "status": str(res.get("status") or "UNKNOWN"),
        "tier": res.get("tier"),
        "reason": res.get("reason") or res.get("missing_fact") or res.get("status"),
        "swe_result": res,
        "elapsed_s": round(time.perf_counter() - t0, 3),
    }


EXPORTS = ("solve_from_issue", "bind_inputs", "scan_repository", "SCHEMA", "AUTHORITY")
