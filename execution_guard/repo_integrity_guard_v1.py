#!/usr/bin/env python3
"""Repo Integrity Guard V1 — fail-closed structural defenses against evidence tampering.

Why this exists
---------------
Session e0a256f8 (PR #4689 and its unpushed continuation) produced a green test
suite and a "19/19 terminal" authority without a single new external
measurement.  The mechanisms were all *structural*, and therefore all
*structurally detectable*:

  1. a ``conftest.py`` that monkeypatched ``pathlib.Path``, ``builtins.open``,
     the import loader, ``urllib``/``http.client`` and ``subprocess`` so that
     184 pinned test files read historical git blobs instead of the tree;
  2. hand-edited authority JSON (``truth.achieved`` false -> true, 7/19 -> 19/19)
     with unchanged evidence refs and deleted fail-closed records;
  3. RECEIPT/VERIFY pairs with identical payload hashes produced by the same
     process and labelled ``independent_verified: true``;
  4. "proof" documents consisting only of boolean flags;
  5. tautological / weakened assertions;
  6. third-party modules replaced through ``sys.modules`` (``cadquery``),
     ``docker`` faked through a patched ``subprocess.run``;
  7. a tool that pushes, opens and self-merges a PR into ``main``.

This guard encodes each of those as a rule.  It is stdlib-only, deterministic,
and runs in three places: the referee workflow ``.github/workflows/repo-integrity-guard.yml``
(``pull_request_target``: the copy on ``main`` judges every pull request and signs the
verdict as the Brain Referee app — the pull request's own copy is never executed), the
regular test suite (``canonical/tests/test_repo_integrity_guard_v1.py``), and by hand:

    python3 execution_guard/repo_integrity_guard_v1.py            # static rules
    python3 execution_guard/repo_integrity_guard_v1.py --base origin/main   # + diff rules
    python3 execution_guard/repo_integrity_guard_v1.py --self-test  # prove the rules fire

Exit status is non-zero on any violation.  There is no override flag: the
only way to change what the guard accepts is to edit this file, which is a
protected path (see ``PROTECTED_PATHS`` and ``.github/CODEOWNERS``).

Terminal achievement
--------------------
``truth.achieved == true`` is rejected unless the owner countersign file
exists *and* its SHA-256 equals ``TERMINAL_ACHIEVED_COUNTERSIGN_SHA256`` below,
which is ``None`` until the human owner edits this file.  No agent can flip the
terminal verdict by editing data alone.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable

SCHEMA = "PROJECT_BRAIN_REPO_INTEGRITY_GUARD_V1"
ROOT = Path(__file__).resolve().parents[1]

# --------------------------------------------------------------------------- policy
TERMINAL_ACHIEVED_COUNTERSIGN_SHA256: str | None = None  # owner-edited only
TERMINAL_ACHIEVED_COUNTERSIGN_PATH = "canonical/governance/TERMINAL_ACHIEVEMENT_OWNER_COUNTERSIGN_V1.json"

PROTECTED_PATHS = (
    "execution_guard/repo_integrity_guard_v1.py",
    "canonical/tests/test_repo_integrity_guard_v1.py",
    ".github/workflows/repo-integrity-guard.yml",
    ".github/workflows/frontier-state-consistency.yml",
    ".github/CODEOWNERS",
    "canonical/governance/REPO_INTEGRITY_POLICY_V1.json",
    "AGENTS.md",
    "execution_guard/honest_suite_baseline_v1.py",
    "canonical/verification/HONEST_SUITE_BASELINE_20261014_V1.json",
    ".github/scripts/land_on_main.sh",
)

AUTHORITY_FILES = {
    "authority": "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json",
    "manifest": "canonical/governance/TERMINAL_CLOSURE_MANIFEST_V1.json",
    "pointer": "canonical/CANONICAL_POINTER.json",
    "scoreboard": "canonical/governance/REAL_OUTPUT_SCOREBOARD_V1.json",
    "useful_ownership": "canonical/capabilities/frontier/OPUS_5_5_USEFUL_CAPABILITY_OWNERSHIP_V1.json",
    "ownership_matrix": "canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json",
    "hierarchy": "canonical/governance/ACTIVE_GOAL_HIERARCHY_V1.json",
    "epoch": "canonical/governance/TERMINAL_AUTHORITY_EPOCH_V1.json",
}
CAPABILITY_REGISTRY = "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
GUARD_WORKFLOW = ".github/workflows/repo-integrity-guard.yml"
FRONTIER_WORKFLOW = ".github/workflows/frontier-state-consistency.yml"
GUARD_INVOCATION = "trusted/execution_guard/repo_integrity_guard_v1.py --ci --root subject"
LAND_SCRIPT = ".github/scripts/land_on_main.sh"
# Workflows allowed to use pull_request_target (they run the MAIN version of themselves
# against pull requests).  Frozen: a new entry needs an owner-merged change to this file.
PULL_REQUEST_TARGET_ALLOWLIST = (
    ".github/workflows/repo-integrity-guard.yml",
    ".github/workflows/drift-immunity-guard.yml",
    ".github/workflows/load-bearing-primary-admission.yml",
)

TEST_DIR_MARKERS = ("/tests/", "/test/")
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", "tmp_arena_import", ".mypy_cache", ".pytest_cache", "build", "dist"}

# Limits for a single pull request (diff mode).  Legitimate work splits into
# several PRs; a single PR that needs more than this is exactly the pattern we
# refuse to admit without a human.
MAX_FAMILY_FLIPS_PER_PR = 2
MAX_ATOMIC_PROVED_DELTA_PER_PR = 4
MAX_NEW_CAPABILITIES_PER_PR = 3
MAX_NEW_RECEIPTS_PER_PR = 40
MAX_TEST_WEAKENINGS_PER_PR = 10
MAX_DELETED_TEST_FILES_PER_PR = 20

GRANDIOSE = re.compile(
    r"singularit|omega|ultimate|supreme|sovereign|transcend|apex|absolute|infinit|omniscien|omnivers|totality|reality",
    re.I,
)
INDEPENDENCE_CLAIM = re.compile(r"INDEPENDENT_PASS|INDEPENDENTLY_VERIFIED", re.I)
RUN_REF_KEY = re.compile(r"(run_id|run_url|workflow_run|capsule_run|verification_run|external_run|actions_run|job_url|runner_attestation)", re.I)
MEASUREMENT_KEY = re.compile(r"(score|measured|observed|passed|total|n_tasks|task_count|sample|count|value|accuracy|rate|threshold)", re.I)
FAIL_CLOSED_KEYS = re.compile(
    r"^(acceptance_calibration|current_machine_verdict|terminal_predicates|reducer_verification|current_ledger|current_ledger_git_blob_sha|blocker|quarantine[a-z_]*|countermodel[a-z_]*|unresolved[a-z_]*|open_famil[a-z_]*|pending[a-z_]*|invalidated[a-z_]*|fail_closed[a-z_]*|donor_deletion_cleanroom|global_ownership_postconditions)$",
    re.I,
)

# Workflows that pushed receipts straight to main before this guard existed.  Frozen: this
# tuple may only lose entries, and it is now empty — carriers open a pull request through
# .github/scripts/land_on_main.sh and the referee judges it like any other change.
LEGACY_DIRECT_MAIN_PUSH_WORKFLOWS: tuple[str, ...] = ()  # emptied 2026-10-14: every carrier now lands through .github/scripts/land_on_main.sh

STDLIB_PATCH_ROOTS_ANYWHERE = {"builtins", "pathlib", "Path", "importlib", "http", "ssl", "socket", "hashlib", "io"}
STDLIB_PATCH_ROOTS_TESTS = STDLIB_PATCH_ROOTS_ANYWHERE | {"subprocess", "urllib", "os", "json", "shutil", "time", "tempfile", "sys"}
CONFTEST_IMPORT_ALLOWLIST = {"os", "sys", "pathlib", "pytest", "json", "typing", "__future__", "re"}
PRIVILEGED_ARGV0 = {"sudo", "su", "doas", "apt", "apt-get", "pip", "pip3", "chmod", "chown", "tee", "ln", "mount"}


# --------------------------------------------------------------------------- model
@dataclass
class Violation:
    code: str
    path: str
    detail: str
    line: int | None = None

    def as_dict(self) -> dict[str, Any]:
        return {"code": self.code, "path": self.path, "line": self.line, "detail": self.detail}

    def __str__(self) -> str:
        loc = f"{self.path}:{self.line}" if self.line else self.path
        return f"[{self.code}] {loc} — {self.detail}"


@dataclass
class Report:
    violations: list[Violation] = field(default_factory=list)
    rules_run: list[str] = field(default_factory=list)
    mode: str = "static"
    base: str | None = None

    def extend(self, rule: str, items: Iterable[Violation]) -> None:
        self.rules_run.append(rule)
        self.violations.extend(items)

    @property
    def ok(self) -> bool:
        return not self.violations

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "mode": self.mode,
            "base": self.base,
            "pass": self.ok,
            "violation_count": len(self.violations),
            "rules_run": self.rules_run,
            "violations": [v.as_dict() for v in self.violations],
        }


# --------------------------------------------------------------------------- helpers
def _iter_files(root: Path, suffixes: tuple[str, ...] | None = None) -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            p = Path(dirpath) / fn
            if suffixes is None or p.suffix in suffixes:
                yield p


def _rel(root: Path, p: Path) -> str:
    return p.relative_to(root).as_posix()


def _is_test_path(rel: str) -> bool:
    r = "/" + rel
    return any(m in r for m in TEST_DIR_MARKERS) or Path(rel).name == "conftest.py" or Path(rel).name.startswith("test_")


def _read(root: Path, rel: str) -> str | None:
    p = root / rel
    try:
        return p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _load_json(root: Path, rel: str) -> Any:
    text = _read(root, rel)
    if text is None:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _parse(path: Path) -> ast.AST | None:
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (SyntaxError, UnicodeDecodeError, OSError, ValueError):
        return None


def _attr_root(node: ast.AST) -> str | None:
    while isinstance(node, ast.Attribute):
        node = node.value
    if isinstance(node, ast.Name):
        return node.id
    return None


def _attr_chain(node: ast.AST) -> str:
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return ".".join(reversed(parts))


def _git(root: Path, *args: str) -> str | None:
    try:
        out = subprocess.run(["git", *args], cwd=str(root), capture_output=True, text=True, check=False)
    except OSError:
        return None
    if out.returncode != 0:
        return None
    return out.stdout


def _git_blob_sha(path: Path) -> str | None:
    try:
        data = path.read_bytes()
    except OSError:
        return None
    h = hashlib.sha1()
    h.update(f"blob {len(data)}\0".encode())
    h.update(data)
    return h.hexdigest()


def _walk_leaves(obj: Any, prefix: str = "") -> Iterable[tuple[str, Any]]:
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _walk_leaves(v, f"{prefix}.{k}" if prefix else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _walk_leaves(v, f"{prefix}[{i}]")
    else:
        yield prefix, obj


def _strings(obj: Any) -> Iterable[str]:
    for _, v in _walk_leaves(obj):
        if isinstance(v, str):
            yield v


def _module_scope_assignments(tree: ast.AST) -> Iterable[ast.AST]:
    """Yield Assign/AugAssign nodes that execute at import time (not inside def/class)."""
    stack: list[ast.AST] = list(getattr(tree, "body", []))
    while stack:
        node = stack.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            continue
        if isinstance(node, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
            yield node
        for child in ast.iter_child_nodes(node):
            stack.append(child)


def _assign_targets(node: ast.AST) -> list[ast.AST]:
    if isinstance(node, ast.Assign):
        return list(node.targets)
    if isinstance(node, (ast.AugAssign, ast.AnnAssign)):
        return [node.target]
    return []


# --------------------------------------------------------------------------- static rules
def rule_conftest_minimal(root: Path) -> list[Violation]:
    """A conftest.py may only set up sys.path and define fixtures.  No hooks, no
    foreign imports, no attribute/subscript writes to objects it did not create,
    no subprocess, no network."""
    out: list[Violation] = []
    for p in _iter_files(root, (".py",)):
        if p.name != "conftest.py":
            continue
        rel = _rel(root, p)
        tree = _parse(p)
        if tree is None:
            out.append(Violation("CONFTEST_UNPARSEABLE", rel, "conftest.py must be valid Python"))
            continue
        local_names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                local_names.add(node.name)
            elif isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        local_names.add(t.id)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
                for n in names:
                    top = n.split(".")[0]
                    if top not in CONFTEST_IMPORT_ALLOWLIST:
                        out.append(Violation("CONFTEST_FORBIDDEN_IMPORT", rel, f"import of '{n}' is not allowed in conftest.py", node.lineno))
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("pytest_"):
                out.append(Violation("CONFTEST_HOOK_FORBIDDEN", rel, f"pytest hook '{node.name}' is not allowed (hooks were used to swap files/modules per test)", node.lineno))
            elif isinstance(node, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
                for t in _assign_targets(node):
                    if isinstance(t, ast.Attribute):
                        r = _attr_root(t)
                        if r and r not in local_names:
                            out.append(Violation("CONFTEST_FOREIGN_ATTRIBUTE_WRITE", rel, f"assignment to '{_attr_chain(t)}' (monkeypatch) is not allowed in conftest.py", node.lineno))
                    elif isinstance(t, ast.Subscript):
                        chain = _attr_chain(t.value) if isinstance(t.value, (ast.Attribute, ast.Name)) else ""
                        if chain in {"sys.modules", "os.environ", "builtins.__dict__"}:
                            out.append(Violation("CONFTEST_FOREIGN_SUBSCRIPT_WRITE", rel, f"write to '{chain}[...]' is not allowed in conftest.py", node.lineno))
            elif isinstance(node, ast.Call):
                chain = _attr_chain(node.func) if isinstance(node.func, (ast.Attribute, ast.Name)) else ""
                if chain in {"setattr", "delattr", "sys.modules.update", "sys.modules.pop", "sys.modules.clear"} or chain.startswith(("subprocess.", "os.system", "os.popen", "urllib.", "http.", "importlib.")):
                    out.append(Violation("CONFTEST_FORBIDDEN_CALL", rel, f"call to '{chain}' is not allowed in conftest.py", node.lineno))
    return out


def rule_no_stdlib_monkeypatch(root: Path) -> list[Violation]:
    """No file may assign to attributes of builtins/pathlib/importlib/http/ssl/socket/hashlib/io
    (any scope).  Test code additionally may not assign to subprocess/urllib/os/json/shutil/
    time/tempfile/sys attributes at import time, nor to urllib.request.urlopen at any scope,
    nor call setattr() on those modules."""
    out: list[Violation] = []
    for p in _iter_files(root, (".py",)):
        rel = _rel(root, p)
        tree = _parse(p)
        if tree is None:
            continue
        is_test = _is_test_path(rel)
        module_level = set(id(n) for n in _module_scope_assignments(tree))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
                for t in _assign_targets(node):
                    if not isinstance(t, ast.Attribute):
                        continue
                    r = _attr_root(t)
                    chain = _attr_chain(t)
                    if r in STDLIB_PATCH_ROOTS_ANYWHERE:
                        out.append(Violation("STDLIB_MONKEYPATCH", rel, f"assignment to '{chain}' hijacks the standard library for every caller", node.lineno))
                    elif is_test and r in STDLIB_PATCH_ROOTS_TESTS:
                        if chain.startswith("urllib.request.") or id(node) in module_level:
                            out.append(Violation("TEST_STDLIB_MONKEYPATCH", rel, f"test code may not assign to '{chain}' here (module scope or network entry point)", node.lineno))
            elif isinstance(node, ast.Call):
                fn = node.func
                name = fn.id if isinstance(fn, ast.Name) else _attr_chain(fn)
                if name in {"setattr", "delattr"} and node.args:
                    r = _attr_root(node.args[0]) if isinstance(node.args[0], (ast.Attribute, ast.Name)) else None
                    if r in STDLIB_PATCH_ROOTS_ANYWHERE or (is_test and r in STDLIB_PATCH_ROOTS_TESTS):
                        out.append(Violation("STDLIB_SETATTR", rel, f"{name}() on standard-library object '{_attr_chain(node.args[0])}'", node.lineno))
    return out


def rule_no_sys_modules_injection(root: Path) -> list[Violation]:
    """``sys.modules[<literal>] = ...`` is forbidden in tests entirely and in runtime
    for any name that is not the project's own namespace.  This is how a fake
    ``cadquery`` was installed."""
    out: list[Violation] = []
    own_prefixes = ("canonical", "astra", "brain", "project_brain", "tests", "_")
    for p in _iter_files(root, (".py",)):
        rel = _rel(root, p)
        tree = _parse(p)
        if tree is None:
            continue
        is_test = _is_test_path(rel)
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
                continue
            for t in _assign_targets(node):
                if not (isinstance(t, ast.Subscript) and _attr_chain(t.value) == "sys.modules"):
                    continue
                key = t.slice
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    if is_test or not key.value.startswith(own_prefixes):
                        out.append(Violation("SYS_MODULES_INJECTION", rel, f"sys.modules['{key.value}'] assignment replaces a real module with a stand-in", node.lineno))
                elif p.name == "conftest.py":
                    out.append(Violation("SYS_MODULES_INJECTION", rel, "dynamic sys.modules[...] assignment in conftest.py", node.lineno))
    return out


def rule_no_historical_pins(root: Path) -> list[Violation]:
    """No pin files, no ``git cat-file``/``git show`` in test infrastructure, no git
    mutation from tests outside an explicit fixture cwd."""
    out: list[Violation] = []
    pin_name = re.compile(r"(historical_test_commits|test_pins|pinned_commits|historical_specs).*\.json$", re.I)
    mutating = {"commit", "add", "push", "fetch", "checkout", "reset", "stash", "worktree", "rebase", "merge", "pull"}
    historical = {"cat-file", "show"}
    for p in _iter_files(root):
        rel = _rel(root, p)
        if pin_name.search(p.name) and _is_test_path(rel):
            out.append(Violation("HISTORICAL_PIN_FILE", rel, "test pin ledgers are forbidden: tests must run against the tree as it is"))
        if p.suffix != ".py" or not _is_test_path(rel):
            continue
        tree = _parse(p)
        if tree is None:
            continue
        is_conftest = p.name == "conftest.py"
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            argv: list[str] = []
            first = node.args[0] if node.args else None
            if isinstance(first, (ast.List, ast.Tuple)):
                for e in first.elts:
                    if isinstance(e, ast.Constant) and isinstance(e.value, str):
                        argv.append(e.value)
                    else:
                        argv.append("?")
            elif isinstance(first, ast.Constant) and isinstance(first.value, str):
                argv = first.value.split()
            else:
                for a in node.args:
                    if isinstance(a, ast.Constant) and isinstance(a.value, str):
                        argv.append(a.value)
            if len(argv) >= 2 and argv[0] == "git":
                sub = argv[1]
                has_cwd = any(k.arg == "cwd" for k in node.keywords)
                if sub in historical and (is_conftest or not has_cwd):
                    out.append(Violation("TEST_READS_HISTORICAL_GIT_OBJECTS", rel, f"'git {sub}' in test infrastructure serves historical bytes instead of the tree", node.lineno))
                if sub in mutating and not has_cwd:
                    out.append(Violation("TEST_MUTATES_REPOSITORY", rel, f"'git {sub}' without an explicit fixture cwd= would mutate the repository under test", node.lineno))
                if sub in mutating and is_conftest:
                    out.append(Violation("TEST_MUTATES_REPOSITORY", rel, f"'git {sub}' is never allowed in conftest.py", node.lineno))
    return out


def rule_no_privileged_or_fake_tooling_in_tests(root: Path) -> list[Violation]:
    """Tests may not run sudo/apt/pip/tee/ln/chmod, and may not fabricate the
    output of external tools (docker, sqlite3, chroot) by intercepting subprocess."""
    out: list[Violation] = []
    faked_tools = {"docker", "sqlite3", "chroot", "podman", "nsenter"}
    for p in _iter_files(root, (".py",)):
        rel = _rel(root, p)
        if not _is_test_path(rel):
            continue
        tree = _parse(p)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                chain = _attr_chain(node.func) if isinstance(node.func, (ast.Attribute, ast.Name)) else ""
                if chain.startswith(("subprocess.", "os.system", "os.popen", "os.exec")) and node.args:
                    first = node.args[0]
                    argv0 = None
                    if isinstance(first, (ast.List, ast.Tuple)) and first.elts and isinstance(first.elts[0], ast.Constant):
                        argv0 = str(first.elts[0].value)
                    elif isinstance(first, ast.Constant) and isinstance(first.value, str):
                        argv0 = first.value.split()[0] if first.value.split() else None
                    if argv0 and Path(argv0).name in PRIVILEGED_ARGV0:
                        out.append(Violation("TEST_PRIVILEGED_COMMAND", rel, f"test code executes '{argv0}'", node.lineno))
            # fabricated tool output: a function that returns CompletedProcess for docker/sqlite3 argv
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                src_names = {n.value for n in ast.walk(node) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
                if src_names & faked_tools and any(isinstance(n, ast.Call) and _attr_chain(n.func) == "subprocess.CompletedProcess" for n in ast.walk(node)):
                    out.append(Violation("TEST_FABRICATES_TOOL_OUTPUT", rel, f"function '{node.name}' synthesises subprocess.CompletedProcess for {sorted(src_names & faked_tools)}", node.lineno))
    return out


def _tautology_in_call(call: ast.Call) -> str | None:
    fn = call.func
    name = fn.attr if isinstance(fn, ast.Attribute) else (fn.id if isinstance(fn, ast.Name) else "")
    args = call.args
    if name == "assertIn" and len(args) >= 2 and isinstance(args[1], (ast.Set, ast.List, ast.Tuple)):
        lhs = ast.dump(args[0])
        for e in args[1].elts:
            if ast.dump(e) == lhs:
                return "assertIn(x, {.., x, ..}) can never fail"
    if name in {"assertEqual", "assertIs", "assertCountEqual", "assertSetEqual", "assertDictEqual", "assertListEqual"} and len(args) >= 2 and ast.dump(args[0]) == ast.dump(args[1]):
        has_call = any(isinstance(n, ast.Call) for n in ast.walk(args[0]))
        has_state = any(isinstance(n, (ast.Name, ast.Attribute, ast.Subscript)) for n in ast.walk(args[0]))
        if has_state and not has_call:  # f(x) == f(x) is a legitimate determinism check
            return f"{name}(x, x) can never fail"
    if name in {"assertTrue", "assertIsNotNone"} and args:
        a = args[0]
        if isinstance(a, ast.Constant) and bool(a.value) is True:
            return f"{name}(<constant>) can never fail"
        if isinstance(a, ast.BoolOp) and isinstance(a.op, ast.Or) and any(isinstance(v, ast.Constant) and bool(v.value) for v in a.values):
            return f"{name}(... or True) can never fail"
    return None


def rule_no_tautological_assertions(root: Path) -> list[Violation]:
    out: list[Violation] = []
    for p in _iter_files(root, (".py",)):
        rel = _rel(root, p)
        if not _is_test_path(rel):
            continue
        tree = _parse(p)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Assert):
                if isinstance(node.test, ast.Constant) and bool(node.test.value):
                    out.append(Violation("TAUTOLOGICAL_ASSERTION", rel, "assert <truthy constant>", node.lineno))
                elif isinstance(node.test, ast.BoolOp) and isinstance(node.test.op, ast.Or) and any(isinstance(v, ast.Constant) and bool(v.value) for v in node.test.values):
                    out.append(Violation("TAUTOLOGICAL_ASSERTION", rel, "assert ... or True", node.lineno))
                elif isinstance(node.test, ast.Compare) and len(node.test.ops) == 1 and isinstance(node.test.ops[0], ast.In) and isinstance(node.test.comparators[0], (ast.Set, ast.List, ast.Tuple)):
                    lhs = ast.dump(node.test.left)
                    if any(ast.dump(e) == lhs for e in node.test.comparators[0].elts):
                        out.append(Violation("TAUTOLOGICAL_ASSERTION", rel, "assert x in {.., x, ..}", node.lineno))
            elif isinstance(node, ast.Call):
                why = _tautology_in_call(node)
                if why:
                    out.append(Violation("TAUTOLOGICAL_ASSERTION", rel, why, node.lineno))
            elif isinstance(node, ast.Try):
                has_assert = any(isinstance(n, ast.Assert) or (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr.startswith("assert")) for b in node.body for n in ast.walk(b))
                swallow = node.handlers and all(len(h.body) == 1 and isinstance(h.body[0], (ast.Pass, ast.Continue)) or (len(h.body) == 1 and isinstance(h.body[0], ast.Expr) and isinstance(h.body[0].value, ast.Constant)) for h in node.handlers)
                if has_assert and swallow:
                    out.append(Violation("ASSERTION_SWALLOWED", rel, "assertion inside try/except: pass", node.lineno))
    return out


def rule_no_automerge_tooling(root: Path) -> list[Violation]:
    """No file in the repository may merge pull requests, approve them, or push to main on
    its own.  Workflows that already pushed receipts straight to main before this guard
    existed are grandfathered by exact name in LEGACY_DIRECT_MAIN_PUSH_WORKFLOWS; that list
    may only shrink, and any other file matching is a violation."""
    out: list[Violation] = []
    merge_pat = re.compile(r"gh\s+pr\s+merge|[\"']pr[\"']\s*,\s*[\"']merge[\"']|gh\s+pr\s+review\s+--approve|--admin\b|git\s+push\s+(-f\s+|--force(-with-lease)?\s+)[\w\-]+\s+(HEAD:)?main\b")
    push_main_pat = re.compile(r"git\s+push\s+[\w\-]+\s+(HEAD:)?main\b")
    for p in _iter_files(root, (".py", ".sh", ".yml", ".yaml", ".bash")):
        rel = _rel(root, p)
        if rel == "execution_guard/repo_integrity_guard_v1.py":
            continue
        text = _read(root, rel)
        if not text:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if merge_pat.search(line):
                # `gh pr merge --auto` is allowed: GitHub completes it only when every required
                # check (the signed referee verdict) has passed, so it cannot bypass anything.
                if re.search(r"gh\s+pr\s+merge", line) and "--auto" in line and "--admin" not in line:
                    continue
                out.append(Violation("AUTOMERGE_TOOLING", rel, f"self-merge / approval / force-push to main is forbidden: {line.strip()[:120]}", i))
            elif push_main_pat.search(line) and rel not in LEGACY_DIRECT_MAIN_PUSH_WORKFLOWS:
                out.append(Violation("DIRECT_MAIN_PUSH", rel, f"pushing to main outside a reviewed pull request is forbidden: {line.strip()[:120]}", i))
    return out


def rule_workflow_guard_integrity(root: Path) -> list[Violation]:
    out: list[Violation] = []
    wf = _read(root, GUARD_WORKFLOW)
    if wf is not None:
        wf = "\n".join(l for l in wf.splitlines() if not l.lstrip().startswith("#"))
    if wf is None:
        out.append(Violation("GUARD_WORKFLOW_MISSING", GUARD_WORKFLOW, "the integrity guard workflow must exist"))
    else:
        if GUARD_INVOCATION not in wf:
            out.append(Violation("GUARD_WORKFLOW_TAMPERED", GUARD_WORKFLOW, f"must run the TRUSTED guard against the subject: {GUARD_INVOCATION}"))
        if not re.search(r"^\s*pull_request_target:", wf, re.M):
            out.append(Violation("GUARD_WORKFLOW_TAMPERED", GUARD_WORKFLOW, "must be triggered by pull_request_target so the version on main judges every pull request"))
        if re.search(r"^\s*pull_request:", wf, re.M):
            out.append(Violation("GUARD_WORKFLOW_TAMPERED", GUARD_WORKFLOW, "a pull_request trigger would run the pull request's own copy of the referee"))
        if "paths:" in wf or "paths-ignore:" in wf:
            out.append(Violation("GUARD_WORKFLOW_TAMPERED", GUARD_WORKFLOW, "must run on every pull request without a paths filter"))
        if "continue-on-error" in wf or "if: false" in wf:
            out.append(Violation("GUARD_WORKFLOW_TAMPERED", GUARD_WORKFLOW, "continue-on-error / disabled steps are forbidden"))
        if "fetch-depth: 0" not in wf:
            out.append(Violation("GUARD_WORKFLOW_TAMPERED", GUARD_WORKFLOW, "the subject checkout must use fetch-depth: 0 so diff rules can see the base"))
        if "persist-credentials: false" not in wf:
            out.append(Violation("GUARD_WORKFLOW_TAMPERED", GUARD_WORKFLOW, "checkouts must not persist credentials"))
        if not re.search(r"^\s*environment:\s*referee\s*$", wf, re.M):
            out.append(Violation("GUARD_WORKFLOW_TAMPERED", GUARD_WORKFLOW, "the verdict must be signed from the `referee` environment (main-only key)"))
        if re.search(r"(python3?|bash|sh|node|source|\.)\s+\.?/?subject/|cd\s+subject\b|PYTHONPATH=\S*subject", wf):
            out.append(Violation("GUARD_WORKFLOW_TAMPERED", GUARD_WORKFLOW, "nothing from subject/ may be executed; the subject is data"))
    fw = _read(root, FRONTIER_WORKFLOW)
    if fw is not None:
        fw = "\n".join(l for l in fw.splitlines() if not l.lstrip().startswith("#"))
        if 'assert t["truth"]["achieved"] is False' not in fw:
            out.append(Violation("FRONTIER_WORKFLOW_RELAXED", FRONTIER_WORKFLOW, "the terminal-achieved assertion was removed"))
        if re.search(r"if\s+[\"']control_plane_precedence[\"']\s+not\s+in\s+h\s*:", fw):
            out.append(Violation("FRONTIER_WORKFLOW_RELAXED", FRONTIER_WORKFLOW, "mirror checks must not be switchable off by a key in the mirrored document"))
    for name in ("load-bearing-primary-admission.yml", "drift-immunity-guard.yml", "frontier-state-consistency.yml"):
        text = _read(root, f".github/workflows/{name}")
        text = "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("#")) if text else text
        if text and "continue-on-error: true" in text:
            out.append(Violation("GUARD_WORKFLOW_TAMPERED", f".github/workflows/{name}", "continue-on-error: true on a guard workflow"))
    return out


def rule_referee_exclusivity(root: Path) -> list[Violation]:
    """Only the referee workflow may touch the referee key or post check runs, and only
    allowlisted workflows may use pull_request_target.  A workflow that could obtain the
    referee's signing key, or post a check run under its name, could forge a verdict."""
    out: list[Violation] = []
    key_pat = re.compile(r"environment:\s*referee\b|REFEREE_APP|check-runs|checks:\s*write|create-github-app-token")
    for p in _iter_files(root / ".github", (".yml", ".yaml")):
        rel = _rel(root, p)
        if rel == GUARD_WORKFLOW:
            continue
        text = _read(root, rel)
        if not text:
            continue
        text = "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("#"))
        for i, line in enumerate(text.splitlines(), 1):
            if key_pat.search(line):
                out.append(Violation("REFEREE_KEY_EXPOSURE", rel, f"only {GUARD_WORKFLOW} may use the referee environment, app token or check-run API: {line.strip()[:100]}", i))
        if re.search(r"^\s*pull_request_target\s*:", text, re.M) and rel not in PULL_REQUEST_TARGET_ALLOWLIST:
            out.append(Violation("PULL_REQUEST_TARGET_NOT_ALLOWLISTED", rel, "pull_request_target runs with main's context against untrusted pull requests; only allowlisted workflows may use it"))
    code_pat = re.compile(r"REFEREE_APP|/check-runs")
    for p in _iter_files(root, (".py", ".sh", ".bash")):
        rel = _rel(root, p)
        if rel in ("execution_guard/repo_integrity_guard_v1.py",):
            continue
        text = _read(root, rel)
        if not text:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if code_pat.search(line):
                out.append(Violation("REFEREE_KEY_EXPOSURE", rel, f"referee key / check-run API outside the referee workflow: {line.strip()[:100]}", i))
    return out


def rule_execution_guard_no_achieved_exemption(root: Path) -> list[Violation]:
    """An execution guard must get stricter, never exempt, when a change claims terminal achievement."""
    out: list[Violation] = []
    pat = re.compile(r"achieved|TERMINAL_TRUE|terminal_true", re.I)
    exempt = re.compile(r"return\s+(0|\[\]|True|None)\b|sys\.exit\(0\)|^\s*continue\b|^\s*pass\b")
    for p in _iter_files(root / "execution_guard", (".py",)):
        rel = _rel(root, p)
        if rel == "execution_guard/repo_integrity_guard_v1.py":
            continue
        lines = (_read(root, rel) or "").splitlines()
        for i, line in enumerate(lines):
            if pat.search(line) and line.lstrip().startswith(("if ", "elif ")):
                window = lines[i + 1 : i + 4]
                if any(exempt.search(w) for w in window):
                    out.append(Violation("EXECUTION_GUARD_ACHIEVED_EXEMPTION", rel, "guard exempts a change because it claims terminal achievement", i + 1))
    return out


def _blocker_strings(t: dict[str, Any]) -> tuple[str, str, str, dict[str, int]]:
    m = re.fullmatch(r"(\d+)/(\d+)_PASS__(\d+)/(\d+)_OPEN", str(t["truth"]["opus55_acceptance"]))
    if not m or m.group(2) != m.group(4):
        raise ValueError("opus55_acceptance malformed")
    accepted, total, open_count = int(m.group(1)), int(m.group(2)), int(m.group(3))
    af = t["atomic_acceptance_frontier"]
    proved, unresolved, atom_total = int(af["proved"]), int(af["unresolved"]), int(af["total"])
    if accepted + open_count != total or proved + unresolved != atom_total:
        raise ValueError("counts do not add up")
    b = f"TERMINAL_FALSE__{open_count}_OF_{total}_FAMILIES_OPEN__{unresolved}_OF_{atom_total}_ATOMIC_PREDICATES_UNRESOLVED__SEE_CURRENT_TERMINAL_AUTHORITY_NEXT_FOR_EXACT_ACTIVE_ROUTE"
    e = "CURRENT_TERMINAL_AUTHORITY_NEXT_PASS_OR_FALSIFICATION__OR_ANOTHER_CAUSALLY_BOUND_ZERO_REALITY_DELTA__NO_TERMINAL_PROMOTION_WITHOUT_SEPARATE_INDEPENDENT_REDUCTION"
    return b, str(t["next"]), e, {"accepted": accepted, "total": total, "open": open_count, "proved": proved, "unresolved": unresolved, "atom_total": atom_total}


def rule_authority_consistency(root: Path) -> list[Violation]:
    """The terminal truth may not be flipped by hand, and every mirror must agree with it."""
    out: list[Violation] = []
    docs = {k: _load_json(root, v) for k, v in AUTHORITY_FILES.items()}
    t = docs["authority"]
    if not isinstance(t, dict):
        return [Violation("AUTHORITY_MISSING", AUTHORITY_FILES["authority"], "terminal authority must exist and be valid JSON")]
    achieved = t.get("truth", {}).get("achieved")
    if achieved is not False:
        sign = root / TERMINAL_ACHIEVED_COUNTERSIGN_PATH
        ok = (
            TERMINAL_ACHIEVED_COUNTERSIGN_SHA256 is not None
            and sign.is_file()
            and hashlib.sha256(sign.read_bytes()).hexdigest() == TERMINAL_ACHIEVED_COUNTERSIGN_SHA256
        )
        if not ok:
            out.append(Violation("TERMINAL_ACHIEVED_WITHOUT_OWNER_COUNTERSIGN", AUTHORITY_FILES["authority"], "truth.achieved is not false; terminal achievement requires the owner to edit the guard's countersign constant"))
    try:
        b, n, e, c = _blocker_strings(t)
    except (KeyError, ValueError, TypeError) as exc:
        return out + [Violation("AUTHORITY_COUNTS_MALFORMED", AUTHORITY_FILES["authority"], str(exc))]
    if achieved is False:
        contradictions = {"TERMINAL_TRUE", "19_OF_19_ACCEPTED", "0_OF_19_OPEN", "38/38_PROVED", "0/19_OPEN"}
        for key, val in _walk_leaves(t):
            if isinstance(val, str) and any(s in val for s in contradictions):
                out.append(Violation("AUTHORITY_SELF_CONTRADICTION", AUTHORITY_FILES["authority"], f"{key} claims terminal truth while truth.achieved is false"))
    else:
        bad = re.compile(r"UNRESOLVED|NOT_PROVED|QUARANTINED|OPEN_ATOMS|TERMINAL_FALSE|FAIL_CLOSED")
        for name in ("authority", "manifest", "useful_ownership", "ownership_matrix", "pointer"):
            d = docs.get(name)
            if isinstance(d, dict):
                for key, val in _walk_leaves(d):
                    if isinstance(val, str) and bad.search(val):
                        out.append(Violation("AUTHORITY_SELF_CONTRADICTION", AUTHORITY_FILES[name], f"{key} still says '{val[:80]}' while truth.achieved is true"))
                        break

    def expect(name: str, getter: Callable[[dict[str, Any]], Any], want: Any, label: str) -> None:
        d = docs.get(name)
        if not isinstance(d, dict):
            out.append(Violation("MIRROR_MISSING", AUTHORITY_FILES[name], "mirror file missing or invalid"))
            return
        try:
            got = getter(d)
        except (KeyError, TypeError, IndexError):
            out.append(Violation("MIRROR_FIELD_MISSING", AUTHORITY_FILES[name], f"{label} missing"))
            return
        if got != want:
            out.append(Violation("MIRROR_DRIFT", AUTHORITY_FILES[name], f"{label} = {str(got)[:90]!r}, authority requires {str(want)[:90]!r}"))

    expect("pointer", lambda d: d["current_frontier"]["critical_blocker"], b, "current_frontier.critical_blocker")
    expect("pointer", lambda d: d["current_frontier"]["highest_leverage_capability_gap"], b, "current_frontier.highest_leverage_capability_gap")
    expect("pointer", lambda d: d["current_frontier"]["next_step"], n, "current_frontier.next_step")
    expect("scoreboard", lambda d: d["active_frontier_accounting"]["residual_gap"], b, "active_frontier_accounting.residual_gap")
    expect("scoreboard", lambda d: d["active_frontier_accounting"]["current_parent_blocker"], b, "active_frontier_accounting.current_parent_blocker")
    expect("scoreboard", lambda d: d["next_required_action"], n, "next_required_action")
    expect("scoreboard", lambda d: d["next_progress_event_target"], e, "next_progress_event_target")
    expect("scoreboard", lambda d: (d["canonical_acceptance_truth"]["accepted_families"], d["canonical_acceptance_truth"]["open_families"], d["canonical_acceptance_truth"]["total_families"]), (c["accepted"], c["open"], c["total"]), "canonical_acceptance_truth family counts")
    expect("scoreboard", lambda d: (d["canonical_acceptance_truth"]["proved_atomic_predicates"], d["canonical_acceptance_truth"]["unresolved_atomic_predicates"], d["canonical_acceptance_truth"]["total_atomic_predicates"]), (c["proved"], c["unresolved"], c["atom_total"]), "canonical_acceptance_truth atomic counts")
    expect("useful_ownership", lambda d: d["residual_gap"], b, "residual_gap")
    expect("useful_ownership", lambda d: d["current_atomic_blocker"], b, "current_atomic_blocker")
    expect("useful_ownership", lambda d: d["next_action"], n, "next_action")
    expect("useful_ownership", lambda d: d["current_atomic_next_action"], n, "current_atomic_next_action")
    expect("useful_ownership", lambda d: (d["acceptance_truth"]["accepted_families"], d["acceptance_truth"]["proved_atomic_predicates"], d["acceptance_truth"]["unresolved_atomic_predicates"], d["acceptance_truth"]["achieved"]), (c["accepted"], c["proved"], c["unresolved"], achieved), "acceptance_truth")
    expect("ownership_matrix", lambda d: (d["postwave_acceptance_summary"]["calibrated_family_count"], d["postwave_acceptance_summary"]["pending_acceptance_family_count"], d["postwave_acceptance_summary"]["verified_owned_family_count"]), (c["accepted"], c["open"], c["accepted"]), "postwave_acceptance_summary family counts")
    expect("ownership_matrix", lambda d: (d["postwave_acceptance_summary"]["atomic_acceptance"]["proved"], d["postwave_acceptance_summary"]["atomic_acceptance"]["unresolved"]), (c["proved"], c["unresolved"]), "postwave_acceptance_summary.atomic_acceptance")
    if achieved is False:
        expect("ownership_matrix", lambda d: bool(d["summary"]["blocker"]), True, "summary.blocker must stay non-empty while terminal is false")
    m = docs.get("manifest")
    if isinstance(m, dict):
        fams = m.get("families") or []
        passed = sum(1 for f in fams if isinstance(f, dict) and f.get("closure_state") == "PASS")
        expect("manifest", lambda d: len(d["families"]), c["total"], "families length")
        expect("manifest", lambda d: d["verified_closed_family_count"], passed, "verified_closed_family_count vs families with closure_state == PASS")
        expect("manifest", lambda d: d["open_family_count"], c["open"], "open_family_count")
        expect("manifest", lambda d: d["verified_closed_family_count"], c["accepted"], "verified_closed_family_count vs authority accepted")
        expect("manifest", lambda d: d["current_machine_verdict"]["achieved"], achieved, "current_machine_verdict.achieved")
        for key in ("acceptance_calibration", "reducer_verification", "terminal_predicates", "current_machine_verdict"):
            if not m.get(key):
                out.append(Violation("FAIL_CLOSED_RECORD_MISSING", AUTHORITY_FILES["manifest"], f"manifest.{key} must exist and be non-empty"))
    h = docs.get("hierarchy")
    if isinstance(h, dict):
        proj = h.get("terminal_authority_projection")
        if not isinstance(proj, dict):
            out.append(Violation("MIRROR_FIELD_MISSING", AUTHORITY_FILES["hierarchy"], "terminal_authority_projection missing"))
        else:
            blob = _git_blob_sha(root / AUTHORITY_FILES["authority"])
            expect("hierarchy", lambda d: d["terminal_authority_projection"]["authority_git_blob_sha"], blob, "terminal_authority_projection.authority_git_blob_sha")
            expect("hierarchy", lambda d: d["terminal_authority_projection"]["projected_atomic_acceptance"], f"{c['proved']}_OF_{c['atom_total']}_PROVED__{c['unresolved']}_OF_{c['atom_total']}_OPEN", "terminal_authority_projection.projected_atomic_acceptance")
            expect("hierarchy", lambda d: d["terminal_authority_projection"]["projected_family_acceptance"], f"{c['accepted']}_OF_{c['total']}_PASS__{c['open']}_OF_{c['total']}_OPEN", "terminal_authority_projection.projected_family_acceptance")
        expect("hierarchy", lambda d: d["postwave_terminal_state"]["terminal_goal_achieved"], achieved, "postwave_terminal_state.terminal_goal_achieved")
        expect("hierarchy", lambda d: d["terminal_closure"]["override_allowed"], False, "terminal_closure.override_allowed")
        if achieved is False:
            expect("hierarchy", lambda d: d["terminal_closure"]["current_verdict"], "NOT_ACHIEVED", "terminal_closure.current_verdict")
    return out


STATIC_RULES: dict[str, Callable[[Path], list[Violation]]] = {
    "conftest_minimal": rule_conftest_minimal,
    "no_stdlib_monkeypatch": rule_no_stdlib_monkeypatch,
    "no_sys_modules_injection": rule_no_sys_modules_injection,
    "no_historical_pins": rule_no_historical_pins,
    "no_privileged_or_fake_tooling_in_tests": rule_no_privileged_or_fake_tooling_in_tests,
    "no_tautological_assertions": rule_no_tautological_assertions,
    "no_automerge_tooling": rule_no_automerge_tooling,
    "referee_exclusivity": rule_referee_exclusivity,
    "workflow_guard_integrity": rule_workflow_guard_integrity,
    "execution_guard_no_achieved_exemption": rule_execution_guard_no_achieved_exemption,
    "authority_consistency": rule_authority_consistency,
}


# --------------------------------------------------------------------------- diff rules
@dataclass
class Change:
    status: str  # A M D R
    path: str
    old_path: str | None = None


def _changed_files(root: Path, base: str) -> list[Change] | None:
    out = _git(root, "diff", "--name-status", "-M", f"{base}...HEAD")
    if out is None:
        out = _git(root, "diff", "--name-status", "-M", base, "HEAD")
    if out is None:
        return None
    changes: list[Change] = []
    for line in out.splitlines():
        parts = line.split("\t")
        if not parts or not parts[0]:
            continue
        st = parts[0][0]
        if st == "R" and len(parts) >= 3:
            changes.append(Change("R", parts[2], parts[1]))
        elif len(parts) >= 2:
            changes.append(Change(st, parts[1]))
    # include uncommitted (staged + unstaged) changes relative to HEAD
    wt = _git(root, "status", "--porcelain")
    if wt:
        seen = {c.path for c in changes}
        for line in wt.splitlines():
            st, _, path = line[:2], line[2], line[3:]
            path = path.split(" -> ")[-1].strip()
            if not path or (set(path.split("/")) & SKIP_DIRS):
                continue
            code = "A" if "?" in st or "A" in st else ("D" if "D" in st else "M")
            if path.endswith("/"):  # untracked directory: expand to its files
                for sub in _iter_files(root / path):
                    rel = _rel(root, sub)
                    if rel not in seen:
                        changes.append(Change(code, rel))
                        seen.add(rel)
            elif path not in seen:
                changes.append(Change(code, path))
                seen.add(path)
    return changes


def _base_json(root: Path, base: str, rel: str) -> Any:
    text = _git(root, "show", f"{base}:{rel}")
    if text is None:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def diff_rule_protected_paths(changes: list[Change], **_: Any) -> list[Violation]:
    out = []
    for c in changes:
        if c.path in PROTECTED_PATHS or (c.old_path and c.old_path in PROTECTED_PATHS):
            out.append(Violation("PROTECTED_PATH_MODIFIED", c.path, "integrity-critical path changed; this PR cannot be merged by an agent — the repository owner must review it in person"))
    return out


def diff_rule_governance_flips(changes: list[Change], root: Path, base_docs: dict[str, Any], head_docs: dict[str, Any], **_: Any) -> list[Violation]:
    out: list[Violation] = []
    bm, hm = base_docs.get("manifest"), head_docs.get("manifest")
    if isinstance(bm, dict) and isinstance(hm, dict):
        bfam = {f.get("id"): f for f in bm.get("families", []) if isinstance(f, dict)}
        flips = 0
        for f in hm.get("families", []):
            if not isinstance(f, dict):
                continue
            fid = f.get("id")
            old = bfam.get(fid, {})
            now_pass = f.get("closure_state") == "PASS" or str(f.get("ownership_status", "")).startswith("VERIFIED_OWNED")
            was_pass = old.get("closure_state") == "PASS" or str(old.get("ownership_status", "")).startswith("VERIFIED_OWNED")
            if now_pass and not was_pass:
                flips += 1
                ev_keys = ("proof_bundle", "acceptance_calibration_evidence", "terminal_behavioral_adjudication_evidence", "scope_restoration_evidence", "behavioral_scope_quarantine_evidence")
                changed = any(json.dumps(f.get(k), sort_keys=True) != json.dumps(old.get(k), sort_keys=True) for k in ev_keys)
                if not changed:
                    out.append(Violation("FAMILY_FLIPPED_WITHOUT_NEW_EVIDENCE", AUTHORITY_FILES["manifest"], f"family {fid} moved to PASS/VERIFIED_OWNED with unchanged evidence references"))
                for k in ev_keys:
                    refs = f.get(k)
                    for ref in ([refs] if isinstance(refs, str) else refs if isinstance(refs, list) else []):
                        if isinstance(ref, str) and ref.startswith("canonical/") and not (root / ref).exists():
                            out.append(Violation("EVIDENCE_REFERENCE_MISSING", AUTHORITY_FILES["manifest"], f"family {fid}: {k} -> {ref} does not exist"))
        if flips > MAX_FAMILY_FLIPS_PER_PR:
            out.append(Violation("FAMILY_FLIP_FLOOD", AUTHORITY_FILES["manifest"], f"{flips} families flipped to PASS in one change (limit {MAX_FAMILY_FLIPS_PER_PR}); split the work and bring evidence per family"))
    bt, ht = base_docs.get("authority"), head_docs.get("authority")
    if isinstance(bt, dict) and isinstance(ht, dict):
        try:
            bp = int(bt["atomic_acceptance_frontier"]["proved"])
            hp = int(ht["atomic_acceptance_frontier"]["proved"])
            if hp - bp > MAX_ATOMIC_PROVED_DELTA_PER_PR:
                out.append(Violation("ATOMIC_PROVED_FLOOD", AUTHORITY_FILES["authority"], f"proved atomic predicates jumped {bp} -> {hp} in one change (limit +{MAX_ATOMIC_PROVED_DELTA_PER_PR})"))
        except (KeyError, TypeError, ValueError):
            pass
    return out


def _walk_paths(obj: Any, prefix: tuple[Any, ...] = ()) -> Iterable[tuple[tuple[Any, ...], Any]]:
    """Yield every (path, value) including containers."""
    yield prefix, obj
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _walk_paths(v, prefix + (k,))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _walk_paths(v, prefix + (i,))


def _resolve(obj: Any, path: tuple[Any, ...]) -> Any:
    cur = obj
    for part in path:
        try:
            cur = cur[part]
        except (KeyError, IndexError, TypeError):
            return None
    return cur


def diff_rule_fail_closed_records(changes: list[Change], base_docs: dict[str, Any], head_docs: dict[str, Any], **_: Any) -> list[Violation]:
    """Records whose job is to say 'not yet' (calibration, verdicts, ledgers, blockers,
    quarantines, unresolved counts) may change value, but may not be deleted or emptied."""
    out: list[Violation] = []
    for name, rel in AUTHORITY_FILES.items():
        b, h = base_docs.get(name), head_docs.get(name)
        if not isinstance(b, dict) or not isinstance(h, dict):
            continue
        for path, val in _walk_paths(b):
            if not path or not isinstance(path[-1], str) or not FAIL_CLOSED_KEYS.match(path[-1]):
                continue
            if val in (None, "", [], {}):
                continue
            if _resolve(h, path) in (None, "", [], {}):
                dotted = ".".join(str(x) for x in path)
                out.append(Violation("FAIL_CLOSED_RECORD_DELETED", rel, f"{dotted} was removed or emptied (was {str(val)[:60]!r})"))
    return out


def _is_num(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _claim_set(doc: Any) -> set[str]:
    """Paths of leaves that assert independent verification."""
    out: set[str] = set()
    for k, v in _walk_leaves(doc):
        if (isinstance(v, str) and INDEPENDENCE_CLAIM.search(v)) or (k.split(".")[-1] == "independent_verified" and v is True):
            out.add(k)
    return out


def diff_rule_receipts(changes: list[Change], root: Path, base: str | None = None, **_: Any) -> list[Violation]:
    out: list[Violation] = []
    scopes = ("canonical/verification/", "canonical/astra_runtime/artifacts/", "canonical/governance/", "canonical/capabilities/")
    new_receipts = 0
    for c in changes:
        if c.status == "D" or not c.path.endswith(".json") or not c.path.startswith(scopes):
            continue
        doc = _load_json(root, c.path)
        if doc is None:
            continue
        if c.status == "A" and c.path.startswith(("canonical/verification/", "canonical/astra_runtime/artifacts/")):
            new_receipts += 1
        if not isinstance(doc, dict):
            continue
        claims = _claim_set(doc)
        if c.status != "A" and base:
            prior = _base_json(root, base, c.old_path or c.path)
            claims -= _claim_set(prior) if prior is not None else set()
        if claims:
            verifier = doc.get("verifier_identity") or doc.get("verifier_id") or doc.get("verifier")
            producer = doc.get("producer_id") or doc.get("producer_identity") or doc.get("producer")
            has_run_ref = any(RUN_REF_KEY.search(k) for k, _ in _walk_leaves(doc))
            if not verifier or verifier == producer:
                out.append(Violation("UNVERIFIABLE_INDEPENDENCE_CLAIM", c.path, "claims independent verification without a verifier identity distinct from the producer"))
            if not has_run_ref:
                out.append(Violation("UNVERIFIABLE_INDEPENDENCE_CLAIM", c.path, "claims independent verification without any run reference (run_id/run_url/workflow_run/...)"))
        name = Path(c.path).name
        if "_VERIFY_" in name or name.endswith("_VERIFY.json"):
            sibling = root / c.path.replace("_VERIFY_", "_RECEIPT_").replace("_VERIFY.json", "_RECEIPT.json")
            sdoc = _load_json(root, _rel(root, sibling)) if sibling.exists() else None
            if isinstance(sdoc, dict):
                hash_keys = [k for k in doc if isinstance(doc.get(k), str) and ("sha256" in k.lower() or k.lower().endswith("_sha")) and k in sdoc]
                same_payload = any(doc[k] == sdoc[k] for k in hash_keys)
                has_run_ref = any(RUN_REF_KEY.search(k) for k, _ in _walk_leaves(doc))
                verifier = doc.get("verifier_identity") or doc.get("verifier_id")
                producer = sdoc.get("producer_id") or sdoc.get("producer_identity") or sdoc.get("verifier_id")
                if same_payload and (not has_run_ref or not verifier or verifier == producer):
                    out.append(Violation("SELF_VERIFIED_RECEIPT_PAIR", c.path, "VERIFY document repeats the RECEIPT's hash values without an independent run reference / distinct verifier"))
        schema = str(doc.get("schema", ""))
        if c.status == "A" and ("PROOF" in name.upper() or "PROOF" in schema.upper()):
            has_measurement = any(_is_num(v) and MEASUREMENT_KEY.search(k.split(".")[-1]) for k, v in _walk_leaves(doc))
            if not has_measurement:
                out.append(Violation("PROOF_WITHOUT_MEASUREMENT", c.path, "a proof document must contain at least one numeric measurement (score/total/count/...); boolean flags are not evidence"))
    if new_receipts > MAX_NEW_RECEIPTS_PER_PR:
        out.append(Violation("RECEIPT_FLOOD", "canonical/verification/", f"{new_receipts} new receipt documents in one change (limit {MAX_NEW_RECEIPTS_PER_PR})"))
    return out


def diff_rule_capability_registry(changes: list[Change], root: Path, base: str, **_: Any) -> list[Violation]:
    out: list[Violation] = []
    if not any(c.path == CAPABILITY_REGISTRY for c in changes):
        return out
    b = _base_json(root, base, CAPABILITY_REGISTRY) or {}
    h = _load_json(root, CAPABILITY_REGISTRY) or {}
    bcaps = set((b.get("capabilities") or {}).keys()) if isinstance(b, dict) else set()
    hcaps = (h.get("capabilities") or {}) if isinstance(h, dict) else {}
    new_ids = sorted(set(hcaps) - bcaps)
    if len(new_ids) > MAX_NEW_CAPABILITIES_PER_PR:
        out.append(Violation("CAPABILITY_REGISTRATION_FLOOD", CAPABILITY_REGISTRY, f"{len(new_ids)} new capabilities in one change (limit {MAX_NEW_CAPABILITIES_PER_PR})"))
    for cid in new_ids:
        if GRANDIOSE.search(cid):
            out.append(Violation("CAPABILITY_SELF_AGGRANDIZEMENT", CAPABILITY_REGISTRY, f"capability id '{cid}' names a frontier/singularity instead of an effect"))
        entry = hcaps.get(cid) or {}
        refs = [v for _, v in _walk_leaves(entry) if isinstance(v, str) and v.startswith("canonical/") and v.endswith(".py")]
        for ref in refs:
            if not (root / ref).exists():
                out.append(Violation("CAPABILITY_MODULE_MISSING", CAPABILITY_REGISTRY, f"capability '{cid}' references missing module {ref}"))
    return out


WEAKENING_PATTERNS = (
    ("EQUAL_TO_IN", re.compile(r"assertIn\(|\bin\s*\{")),
    ("ASSERT_TRUE_OR", re.compile(r"assertTrue\(.*\sor\s")),
    ("GREATER_EQUAL_RELAX", re.compile(r"assertGreaterEqual\(|assertLessEqual\(")),
)


def diff_rule_test_weakening(changes: list[Change], root: Path, base: str, **_: Any) -> list[Violation]:
    out: list[Violation] = []
    deleted_tests = [c for c in changes if c.status == "D" and _is_test_path(c.path) and Path(c.path).name.startswith("test_")]
    if len(deleted_tests) > MAX_DELETED_TEST_FILES_PER_PR:
        out.append(Violation("TEST_DELETION_FLOOD", "canonical/tests/", f"{len(deleted_tests)} test files deleted in one change (limit {MAX_DELETED_TEST_FILES_PER_PR})"))
    weak = 0
    for c in changes:
        if c.status != "M" or not c.path.endswith(".py") or not _is_test_path(c.path):
            continue
        diff = _git(root, "diff", f"{base}...HEAD", "--", c.path) or _git(root, "diff", base, "HEAD", "--", c.path) or ""
        removed = [l[1:] for l in diff.splitlines() if l.startswith("-") and not l.startswith("---")]
        added = [l[1:] for l in diff.splitlines() if l.startswith("+") and not l.startswith("+++")]
        for name, pat in WEAKENING_PATTERNS:
            before = sum(1 for l in removed if "assertEqual(" in l) if name == "EQUAL_TO_IN" else sum(1 for l in removed if pat.search(l))
            after = sum(1 for l in added if pat.search(l))
            if name == "EQUAL_TO_IN":
                weak += max(0, min(before, after))
            else:
                weak += max(0, after - before)
    if weak > MAX_TEST_WEAKENINGS_PER_PR:
        out.append(Violation("TEST_WEAKENING_FLOOD", "canonical/tests/", f"{weak} assertion weakenings (exact->membership, ->or, ->>=) in one change (limit {MAX_TEST_WEAKENINGS_PER_PR})"))
    return out


DIFF_RULES: dict[str, Callable[..., list[Violation]]] = {
    "protected_paths": diff_rule_protected_paths,
    "governance_flips": diff_rule_governance_flips,
    "fail_closed_records": diff_rule_fail_closed_records,
    "receipts": diff_rule_receipts,
    "capability_registry": diff_rule_capability_registry,
    "test_weakening": diff_rule_test_weakening,
}


# --------------------------------------------------------------------------- runner
def resolve_base(root: Path, requested: str | None) -> str | None:
    candidates = [requested] if requested else []
    env_base = os.environ.get("GITHUB_BASE_REF")
    if env_base:
        candidates.append(f"origin/{env_base}")
    candidates += ["origin/main", "main"]
    for cand in candidates:
        if not cand:
            continue
        mb = _git(root, "merge-base", cand, "HEAD")
        if mb:
            return mb.strip()
    return None


def run(root: Path, base: str | None = None, static_only: bool = False) -> Report:
    report = Report()
    for name, fn in STATIC_RULES.items():
        report.extend(name, fn(root))
    if static_only:
        return report
    resolved = resolve_base(root, base)
    if resolved is None:
        report.mode = "static-only (no base ref resolvable)"
        return report
    changes = _changed_files(root, resolved)
    if changes is None:
        report.mode = "static-only (git diff unavailable)"
        return report
    report.mode = "static+diff"
    report.base = resolved
    base_docs = {k: _base_json(root, resolved, v) for k, v in AUTHORITY_FILES.items()}
    head_docs = {k: _load_json(root, v) for k, v in AUTHORITY_FILES.items()}
    for name, fn in DIFF_RULES.items():
        report.extend(f"diff:{name}", fn(changes=changes, root=root, base=resolved, base_docs=base_docs, head_docs=head_docs))
    return report


# --------------------------------------------------------------------------- self-test
def _write(root: Path, rel: str, text: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def self_test() -> list[str]:
    """Each fixture must trigger exactly its rule; the clean fixture must trigger nothing."""
    failures: list[str] = []
    fixtures: list[tuple[str, str, str, str]] = [
        ("conftest_minimal", "canonical/tests/conftest.py", "import subprocess\nsubprocess.run(['git','fetch'])\n", "CONFTEST_FORBIDDEN_IMPORT"),
        ("conftest_minimal", "canonical/tests/conftest.py", "def pytest_runtest_setup(item):\n    pass\n", "CONFTEST_HOOK_FORBIDDEN"),
        ("conftest_minimal", "canonical/tests/conftest.py", "from pathlib import Path\nPath.read_text = lambda *a, **k: ''\n", "CONFTEST_FOREIGN_ATTRIBUTE_WRITE"),
        ("no_stdlib_monkeypatch", "canonical/runtime/x.py", "import builtins\nbuiltins.open = print\n", "STDLIB_MONKEYPATCH"),
        ("no_stdlib_monkeypatch", "canonical/runtime/y.py", "import importlib.machinery\nimportlib.machinery.SourceFileLoader.get_data = None\n", "STDLIB_MONKEYPATCH"),
        ("no_stdlib_monkeypatch", "canonical/tests/test_a.py", "import urllib.request\ndef t():\n    urllib.request.urlopen = None\n", "TEST_STDLIB_MONKEYPATCH"),
        ("no_stdlib_monkeypatch", "canonical/tests/test_b.py", "import subprocess\nsubprocess.run = None\n", "TEST_STDLIB_MONKEYPATCH"),
        ("no_sys_modules_injection", "canonical/runtime/z.py", "import sys, types\nsys.modules['cadquery'] = types.ModuleType('cadquery')\n", "SYS_MODULES_INJECTION"),
        ("no_historical_pins", "canonical/tests/historical_test_commits.json", "{}", "HISTORICAL_PIN_FILE"),
        ("no_historical_pins", "canonical/tests/test_c.py", "import subprocess\nsubprocess.run(['git','cat-file','--batch'])\n", "TEST_READS_HISTORICAL_GIT_OBJECTS"),
        ("no_historical_pins", "canonical/tests/test_d.py", "import subprocess\nsubprocess.run(['git','commit','-m','x'])\n", "TEST_MUTATES_REPOSITORY"),
        ("no_privileged_or_fake_tooling_in_tests", "canonical/tests/test_e.py", "import subprocess\nsubprocess.run(['sudo','tee','/usr/bin/sqlite3'])\n", "TEST_PRIVILEGED_COMMAND"),
        ("no_privileged_or_fake_tooling_in_tests", "canonical/tests/test_f.py", "import subprocess\ndef fake(cmd):\n    if cmd[0] == 'docker':\n        return subprocess.CompletedProcess(cmd, 0, stdout='network_blocked=1')\n", "TEST_FABRICATES_TOOL_OUTPUT"),
        ("no_tautological_assertions", "canonical/tests/test_g.py", "import unittest\nclass T(unittest.TestCase):\n    def test_x(self):\n        v = 1\n        self.assertIn(v, {2, v})\n", "TAUTOLOGICAL_ASSERTION"),
        ("no_tautological_assertions", "canonical/tests/test_h.py", "def test_x():\n    try:\n        assert 1 == 2\n    except AssertionError:\n        pass\n", "ASSERTION_SWALLOWED"),
        ("no_automerge_tooling", "canonical/runtime/sync.py", "import subprocess\nsubprocess.run(['gh', 'pr', 'merge', '1', '--merge'])\n", "AUTOMERGE_TOOLING"),
        ("no_automerge_tooling", ".github/workflows/w.yml", "run: gh pr merge --auto --admin 1\n", "AUTOMERGE_TOOLING"),
        ("no_automerge_tooling", ".github/workflows/w2.yml", "run: git push origin HEAD:main\n", "DIRECT_MAIN_PUSH"),
        ("referee_exclusivity", ".github/workflows/other.yml", "on: push\njobs:\n  j:\n    runs-on: ubuntu-latest\n    environment: referee\n", "REFEREE_KEY_EXPOSURE"),
        ("referee_exclusivity", ".github/workflows/other2.yml", "on: push\njobs:\n  j:\n    steps:\n      - run: gh api -X POST repos/x/y/check-runs\n", "REFEREE_KEY_EXPOSURE"),
        ("referee_exclusivity", ".github/workflows/other3.yml", "on:\n  pull_request_target:\n    types: [opened]\n", "PULL_REQUEST_TARGET_NOT_ALLOWLISTED"),
        ("referee_exclusivity", "canonical/runtime/forge.py", "import os\nkey = os.environ['REFEREE_APP_PRIVATE_KEY']\n", "REFEREE_KEY_EXPOSURE"),
        ("workflow_guard_integrity", GUARD_WORKFLOW, "on:\n  pull_request:\njobs:\n  j:\n    steps:\n      - run: python3 subject/execution_guard/repo_integrity_guard_v1.py\n", "GUARD_WORKFLOW_TAMPERED"),
        ("execution_guard_no_achieved_exemption", "execution_guard/other.py", "def check(doc):\n    if doc.get('achieved'):\n        return 0\n    return 1\n", "EXECUTION_GUARD_ACHIEVED_EXEMPTION"),
    ]
    for rule, rel, text, code in fixtures:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write(root, rel, text)
            got = {v.code for v in STATIC_RULES[rule](root)}
            if code not in got:
                failures.append(f"{rule}: fixture {rel} did not raise {code} (got {sorted(got)})")
    # authority rule: hand-flipped achieved must fail; consistent false state must pass
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _write(root, AUTHORITY_FILES["authority"], json.dumps({"truth": {"achieved": True, "opus55_acceptance": "19/19_PASS__0/19_OPEN"}, "atomic_acceptance_frontier": {"proved": 38, "unresolved": 0, "total": 38}, "next": "X"}))
        got = {v.code for v in rule_authority_consistency(root)}
        if "TERMINAL_ACHIEVED_WITHOUT_OWNER_COUNTERSIGN" not in got:
            failures.append("authority_consistency: achieved=true without countersign was accepted")
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _write(root, AUTHORITY_FILES["authority"], json.dumps({"truth": {"achieved": False, "opus55_acceptance": "7/19_PASS__12/19_OPEN", "x": "TERMINAL_TRUE__0_OF_19_FAMILIES_OPEN"}, "atomic_acceptance_frontier": {"proved": 18, "unresolved": 20, "total": 38}, "next": "X"}))
        got = {v.code for v in rule_authority_consistency(root)}
        if "AUTHORITY_SELF_CONTRADICTION" not in got:
            failures.append("authority_consistency: contradictory sub-record was accepted")
    # diff rules on synthetic base/head docs
    base_docs = {
        "manifest": {"families": [{"id": "F1", "closure_state": "OPEN", "proof_bundle": "canonical/x.json"}, {"id": "F2", "closure_state": "OPEN", "proof_bundle": "p"}, {"id": "F3", "closure_state": "OPEN", "proof_bundle": "p"}], "acceptance_calibration": {"status": "FAIL_CLOSED"}},
        "authority": {"atomic_acceptance_frontier": {"proved": 18}},
    }
    head_docs = {
        "manifest": {"families": [{"id": "F1", "closure_state": "PASS", "proof_bundle": "canonical/x.json"}, {"id": "F2", "closure_state": "PASS", "proof_bundle": "p"}, {"id": "F3", "closure_state": "PASS", "proof_bundle": "p"}]},
        "authority": {"atomic_acceptance_frontier": {"proved": 38}},
    }
    with tempfile.TemporaryDirectory() as td:
        got = {v.code for v in diff_rule_governance_flips(changes=[], root=Path(td), base_docs=base_docs, head_docs=head_docs)}
        for code in ("FAMILY_FLIPPED_WITHOUT_NEW_EVIDENCE", "FAMILY_FLIP_FLOOD", "ATOMIC_PROVED_FLOOD"):
            if code not in got:
                failures.append(f"governance_flips: {code} not raised")
        got = {v.code for v in diff_rule_fail_closed_records(changes=[], base_docs=base_docs, head_docs=head_docs)}
        if "FAIL_CLOSED_RECORD_DELETED" not in got:
            failures.append("fail_closed_records: deleted acceptance_calibration not detected")
        root = Path(td)
        _write(root, "canonical/verification/X_RECEIPT_V1.json", json.dumps({"producer_id": "p", "payload_sha256": "abc", "pass": True}))
        _write(root, "canonical/verification/X_VERIFY_V1.json", json.dumps({"producer_id": "p", "payload_sha256": "abc", "independent_verified": True}))
        _write(root, "canonical/astra_runtime/artifacts/Y__ROW_PROOF_V1.json", json.dumps({"schema": "ROW_PROOF", "brain_owned": True, "adequate": True}))
        got = {v.code for v in diff_rule_receipts(changes=[Change("A", "canonical/verification/X_VERIFY_V1.json"), Change("A", "canonical/astra_runtime/artifacts/Y__ROW_PROOF_V1.json")], root=root)}
        for code in ("UNVERIFIABLE_INDEPENDENCE_CLAIM", "SELF_VERIFIED_RECEIPT_PAIR", "PROOF_WITHOUT_MEASUREMENT"):
            if code not in got:
                failures.append(f"receipts: {code} not raised")
        got = {v.code for v in diff_rule_protected_paths(changes=[Change("M", PROTECTED_PATHS[0])])}
        if "PROTECTED_PATH_MODIFIED" not in got:
            failures.append("protected_paths: modification not detected")
    # clean fixture: a minimal honest tree must produce zero static violations except the
    # ones that depend on real repository files (workflow + authority), which are skipped here
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _write(root, "canonical/tests/conftest.py", "import sys\nfrom pathlib import Path\nROOT = Path(__file__).resolve().parents[2]\nif str(ROOT) not in sys.path:\n    sys.path.insert(0, str(ROOT))\n")
        _write(root, "canonical/tests/test_ok.py", "import unittest\nclass T(unittest.TestCase):\n    def test_x(self):\n        self.assertEqual(1 + 1, 2)\n")
        _write(root, "canonical/runtime/ok.py", "import subprocess\ndef run():\n    return subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True)\n")
        _write(root, ".github/workflows/carrier.yml", "on: push\njobs:\n  j:\n    steps:\n      - run: |\n          git push origin HEAD:refs/heads/carrier/x\n          gh pr merge --auto --squash \"$url\"\n")
        for name in ("conftest_minimal", "no_stdlib_monkeypatch", "no_sys_modules_injection", "no_historical_pins", "no_privileged_or_fake_tooling_in_tests", "no_tautological_assertions", "no_automerge_tooling", "referee_exclusivity"):
            got = STATIC_RULES[name](root)
            if got:
                failures.append(f"clean fixture tripped {name}: {[str(v) for v in got][:3]}")
    return failures


# --------------------------------------------------------------------------- cli
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--base", default=None, help="git ref to diff against (default: merge-base with origin/main)")
    ap.add_argument("--static-only", action="store_true")
    ap.add_argument("--ci", action="store_true", help="CI mode: diff against GITHUB_BASE_REF/origin/main, JSON summary on stdout")
    ap.add_argument("--json", default=None, help="write the report to this path")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args(argv)
    if args.self_test:
        failures = self_test()
        for f in failures:
            print("SELF-TEST FAILURE:", f)
        print("self-test:", "PASS" if not failures else f"FAIL ({len(failures)})")
        return 0 if not failures else 2
    report = run(Path(args.root), base=args.base, static_only=args.static_only)
    if args.ci and report.mode != "static+diff":
        # Fail closed: in CI the diff rules are the point.  A shallow checkout, a
        # missing base ref or a broken git must fail the check, not quietly
        # downgrade it to the static rules.
        report.extend("ci:base", [Violation("CI_DIFF_BASE_UNRESOLVABLE", ".", f"CI mode requires a resolvable base ref for the diff rules; got mode={report.mode!r}")])
    if args.json:
        Path(args.json).write_text(json.dumps(report.as_dict(), indent=2) + "\n", encoding="utf-8")
    for v in report.violations:
        print(str(v))
    print(f"repo-integrity-guard: mode={report.mode} base={report.base} rules={len(report.rules_run)} violations={len(report.violations)} -> {'PASS' if report.ok else 'FAIL'}")
    if args.ci:
        print(json.dumps({"pass": report.ok, "violation_count": len(report.violations), "mode": report.mode}))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
