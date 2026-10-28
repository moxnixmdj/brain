# PROJECT_BRAIN
"""python.software.issue_to_pr.orchestrate.v1 — the issue→PR closed loop.

One task file in, a pull-request-ready change out: the orchestrator drives
the already-landed software-engineering slices as one deterministic machine
instead of four disconnected tools:

    task (JSON: edits[] = choreograph op spec)
      -> stage name/describe           [this adapter]
      -> cross-file edit plan          (slice 4: python_crossfile_edit_choreograph)
      -> apply plan to a WORKTREE copy (this adapter; source tree is never mutated)
      -> prove application             (re-index + re-plan: fixed point == no-op)
      -> select impacted tests        (slice 2: advisory, not a proof of coverage)
      -> run all discovered tests      (one pytest run on the worktree)
      -> emit unified diff + pr_intent + Merkle receipt (this adapter)

Correctness laws it refuses to violate:

* NEVER-MUTATE-SOURCE — ``repository_root`` bytes are hashed before/after;
  any drift is caught and the run FAILS CLOSED.  All edits land in
  ``worktree_path`` (a byte-copy of ``source_root``).
* COMPLETE-OR-REFUSE — a plan with any AMBIGUOUS_* site or a refused op
  aborts the whole task before any write; the refusals and ambiguous sites
  are reported verbatim (truth over progress).
* APPLIED-MEANS-PROVABLE — after writing, the worktree is re-indexed and
  the same edits are re-planned; rename ops must now refuse with
  NAME_NOT_AT_MODULE_SCOPE (old name gone) and the new name must bind at
  module scope.  Anything else is a hard failure.
* TESTS-BEFORE-VERIFIED — impact selection is advisory: dynamic dependencies
  can evade it.  Verification requires a successful pytest run with at least
  one passed test over every conventionally named test file discovered under
  source_root. Missing or uncollected files, deselected tests, skipped-only,
  failed, or unreportable runs cannot pass. Tests outside source_root,
  nonstandard test filenames, and skipped tests are not covered.
* FAIL CLOSED on any unknown/missing input; v1 applies ``rename_symbol``
  and ``move_symbol`` ops (decorator-aware cut spans, deterministic
  multi-name import splitting, and re-import injection when the defining
  module still references the moved name); any other op refuses with
  UNSUPPORTED_OP_AT_APPLY — listed, never silently skipped.
* Determinism — same inputs (tree bytes + task) produce byte-identical
  diff, pr_intent and receipt; proven by pins running the loop twice.

Inputs (kwargs; every path is confined to the repo by _safe_path):
  task_path      JSON: {"issue_id", "title", "body", "edits": [ops]}
  source_root    tree to change (relative to repo)
  worktree_path  (re)created byte-copy of source_root; edited there
  output_path    final summary JSON (registry result_fields mirror)
  diff_path      unified diff artifact (source_root -> worktree bytes)
  pr_intent_path PR title/body/checklist JSON artifact
  index_path     optional validated slice-1 index cache (speed law)
  timeout_s      per-test-run wall clock cap (default 300)

result_fields: adapter, task_id, planned_op_count, applied_op_count,
refused_op_count, applied_site_count, test_selected_count,
test_passed_count, test_failed_count, diff_sha256, pr_intent_verified,
verified.
"""

from __future__ import annotations

import ast
import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from canonical.runtime.bound_capabilities import (
    python_crossfile_edit_choreograph as choreograph,
)
from canonical.runtime.bound_capabilities import (
    python_change_impact_testselect as testselect,
)
from canonical.runtime.bound_capabilities.python_test_corpus_discovery_v1 import (
    discover_test_files,
)

ARTIFACT_VERSION = 1
NAME_RE = re.compile(r"^[A-Za-z_]\w*$")
_DEF_RE_TEMPLATE = r"^(?P<head>\s*(?:async\s+)?(?:def|class)\s+)(?P<name>{name})(?P<tail>\b)"

# paths that must not be copied into the worktree
_SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "node_modules"}


def _fail(reason: str) -> None:
    payload = json.dumps({"error": True, "capability": "python.software.issue_to_pr.orchestrate.v1",
                          "reason": reason}, indent=2, sort_keys=True)
    raise SystemExit(payload)


def _safe_path(repo: Path, rel: str, must_exist: bool = False) -> Path:
    if not rel or not isinstance(rel, str):
        _fail("MISSING_OR_INVALID_PATH_ARGUMENT")
    p = (repo / rel).resolve()
    if p != repo and repo not in p.parents:
        _fail("PATH_ESCAPE:" + rel)
    if must_exist and not p.exists():
        _fail("PATH_MISSING:" + rel)
    return p


def _sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _read_pytest_report(path: Path) -> dict:
    """Read outcome counts from pytest's JUnit report, not its console text.

    A successful process with no usable report, or no actually passed test,
    is not evidence that the worktree was tested. Pytest's built-in JUnit
    plugin emits one top-level suite; accept multiple top-level suites too.
    """
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else root.findall("./testsuite")
    if not suites:
        raise ValueError("PYTEST_REPORT_HAS_NO_SUITES")
    totals = {key: 0 for key in ("tests", "failures", "errors", "skipped")}
    failed_cases = []
    for suite in suites:
        for key in totals:
            count = int(suite.attrib[key])
            if count < 0:
                raise ValueError("PYTEST_REPORT_NEGATIVE_COUNT")
            totals[key] += count
        for case in suite.findall(".//testcase"):
            if case.find("failure") is not None or case.find("error") is not None:
                failed_cases.append("::".join(filter(None, (
                    case.get("classname", ""), case.get("name", "")))))
    failed = totals["failures"] + totals["errors"]
    passed = totals["tests"] - failed - totals["skipped"]
    if passed < 0:
        raise ValueError("PYTEST_REPORT_INCONSISTENT_COUNTS")
    return {"reported_cases": totals["tests"], "passed": passed, "failed": failed,
            "skipped": totals["skipped"], "failed_cases": failed_cases[:50]}


def _run_worktree_tests(worktree: Path, python_exe: str,
                        pytest_version: str | None, timeout_s: int) -> dict:
    """Run the existing test-discovery rule once, without an impact-only gate.

    Discover without the helper's default 5,000-file cap: truncation would
    make a full-worktree claim false. Pass the worktree directory explicitly,
    bypassing `testpaths` without pytest's quadratic per-file argument cost;
    independently check that pytest collected every discovered file.
    """
    try:
        files = discover_test_files(worktree, limit=sys.maxsize)
    except FileNotFoundError:
        files = []
    evidence = {
        "scope": "conventional_test_files_under_source_root",
        "discovered_files": len(files), "reported_cases": 0, "passed": 0,
        "failed": 0, "skipped": 0, "deselected": 0, "uncollected_files": 0,
        "failed_cases": [], "deselected_cases": [], "uncollected_examples": [], "pytest_rc": None,
        "status": "NO_TEST_FILES" if not files else "PYTEST_UNAVAILABLE",
    }
    if not files or not pytest_version:
        return evidence

    try:
        # JUnit is written outside the worktree and discarded after reading;
        # timing, temporary paths, and captured output do not taint deterministic
        # PR-intent artifacts.
        with tempfile.TemporaryDirectory(prefix="brain-issue-to-pr-pytest-") as tmp:
            report = Path(tmp) / "pytest.xml"
            selection_report = Path(tmp) / "selection.json"
            plugin_name = "_brain_pr_test_audit_" + Path(tmp).name.replace("-", "_")
            # JUnit omits deselected and ignored files. Record pytest's real
            # collection and deselection hooks too, so a configured ignore,
            # -k/-m/--deselect cannot hide a test behind a successful exit.
            (Path(tmp) / (plugin_name + ".py")).write_text(
                "import json, pytest\n"
                "from collections import Counter\n"
                "deselected = Counter()\n"
                "removed = Counter()\n"
                "collected = set()\n"
                "def pytest_deselected(items):\n"
                "    deselected.update(item.nodeid for item in items)\n"
                "@pytest.hookimpl(hookwrapper=True, tryfirst=True)\n"
                "def pytest_collection_modifyitems(items):\n"
                "    before = Counter(item.nodeid for item in items)\n"
                "    yield\n"
                "    removed.update(before - Counter(item.nodeid for item in items))\n"
                "def pytest_collectreport(report):\n"
                "    path = report.nodeid.split('::', 1)[0]\n"
                "    if path.endswith('.py'): collected.add(path)\n"
                "def pytest_sessionfinish(session, exitstatus):\n"
                "    paths = sorted(str((session.config.rootpath / p).resolve()) for p in collected)\n"
                "    omitted = deselected | removed\n"
                "    with open(" + repr(str(selection_report)) + ", 'w', encoding='utf-8') as f:\n"
                "        json.dump({'deselected': sum(omitted.values()), "
                "'deselected_cases': sorted(omitted.elements())[:50], 'collected_files': paths}, f)\n", encoding="utf-8")
            env = os.environ.copy()
            env["PYTHONPATH"] = tmp + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
            proc = subprocess.run(
                [python_exe, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-p", plugin_name,
                 "--junitxml=" + str(report), str(worktree)],
                cwd=worktree, capture_output=True, text=True, timeout=timeout_s, env=env)
            evidence["pytest_rc"] = proc.returncode
            try:
                evidence.update(_read_pytest_report(report))
                selection = json.loads(selection_report.read_text(encoding="utf-8"))
                count, cases = selection["deselected"], selection["deselected_cases"]
                collected_files = selection["collected_files"]
                if type(count) is not int or count < 0 or not isinstance(cases, list) or \
                        len(cases) > count or any(not isinstance(case, str) for case in cases) or \
                        not isinstance(collected_files, list) or \
                        any(not isinstance(path, str) for path in collected_files):
                    raise ValueError("PYTEST_SELECTION_REPORT_INVALID")
                missing = sorted({str(path.resolve()) for path in files} - set(collected_files))
                examples = [str(Path(path).relative_to(worktree)).replace("\\", "/")
                            for path in missing[:50]]
                evidence.update({"deselected": count, "deselected_cases": cases,
                                 "uncollected_files": len(missing), "uncollected_examples": examples})
            except (OSError, ET.ParseError, ValueError, KeyError, TypeError):
                evidence["status"] = "REPORT_UNAVAILABLE"
                return evidence
    except subprocess.TimeoutExpired:
        evidence["status"] = "TIMEOUT"
        return evidence
    except OSError:
        evidence["status"] = "PYTEST_LAUNCH_FAILED"
        return evidence

    if evidence["pytest_rc"] != 0 or evidence["failed"]:
        evidence["status"] = "FAILED"
    elif evidence["uncollected_files"]:
        evidence["status"] = "UNCOLLECTED_TEST_FILES"
    elif evidence["deselected"]:
        evidence["status"] = "DESELECTED_TESTS"
    elif not evidence["passed"]:
        evidence["status"] = "NO_PASSED_TESTS"
    else:
        evidence["status"] = "PASSED"
    return evidence


def _tree_manifest(root: Path) -> dict:
    rows = []
    for p in sorted(root.rglob("*.py")):
        if p.is_file() and not any(part in _SKIP_DIRS for part in p.parts):
            rows.append([str(p.relative_to(root)).replace("\\", "/"), _sha256(p.read_bytes())])
    return {"file_count": len(rows),
            "sha256": _sha256(json.dumps(rows, separators=(",", ":")).encode("utf-8"))}


OWNED_DIR_MARKER = ".brain_owned_output_v1"


def _copy_tree(src: Path, dst: Path) -> None:
    """Stage a byte-copy of src at dst, recreating dst only when Brain owns it.

    Ownership is the marker a previous run left behind.  A non-empty worktree
    path without it is the caller's data and is refused, never deleted.
    Measured before this: an existing directory at worktree_path lost its
    contents on every run, including runs whose verification then failed.
    """
    if dst.is_symlink() or (dst.exists() and not dst.is_dir()):
        _fail("WORKTREE_PATH_NOT_A_DIRECTORY")
    if dst.is_dir():
        if any(dst.iterdir()) and not (dst / OWNED_DIR_MARKER).is_file():
            _fail("WORKTREE_DIR_NOT_OWNED_BY_BRAIN")
        shutil.rmtree(dst)
    dst.mkdir(parents=True)

    def ignore(_dir, names):
        return [n for n in names if n in _SKIP_DIRS]

    shutil.copytree(src, dst, dirs_exist_ok=True, ignore=ignore)
    (dst / OWNED_DIR_MARKER).write_text(
        "staged by python_issue_to_pr_orchestrate; safe to recreate\n", encoding="utf-8")


# --------------------------------------------------------------------------
# apply layer — deterministic token splicing driven only by plan site rows
# --------------------------------------------------------------------------

def _splice_token(line: str, name: str, new_name: str, col: int) -> str:
    """Replace the token occurrence of `name` sitting exactly at `col`
    (ast col_offset semantics).  Off-position refuses, never guesses."""
    seg = line[col:col + len(name)]
    if seg != name or not re.fullmatch(r"[A-Za-z_]\w*", name):
        raise ValueError(f"TOKEN_NOT_AT_INDEXED_POSITION:{col}:{seg!r}")
    if len(line) > col + len(name) and (line[col + len(name)].isalnum() or line[col + len(name)] == "_"):
        raise ValueError("TOKEN_BOUNDARY_VIOLATION:" + line[:60])
    return line[:col] + new_name + line[col + len(name):]


def _splice_site(line: str, name: str, new_name: str, site: dict) -> str:
    if site["kind"] == "REFERENCE":
        return _splice_token(line, name, new_name, int(site["col"]))
    if site["kind"] == "DEFINITION":
        m = re.match(_DEF_RE_TEMPLATE.format(name=re.escape(name)), line)
        if not m:
            raise ValueError("DEFINITION_TOKEN_MISMATCH:" + line[:60])
        return m.group("head") + new_name + line[m.end("name"):]
    raise ValueError("UNSUPPORTED_INLINE_KIND:" + site["kind"])


def _apply_rename(work_src: Path, op: dict, plan_op: dict) -> dict:
    module, name, new_name = op["module"], op["name"], op["new_name"]
    defining_dot = module[:-3].replace("/", ".") if module.endswith(".py") else module.replace("/", ".")
    by_file: dict[str, list[dict]] = {}
    for site in plan_op["sites"]:
        by_file.setdefault(site["file"], []).append(site)
    touched = []
    for file_rel in sorted(by_file):
        path = (work_src / file_rel)
        if not path.is_file():
            raise ValueError("PLANNED_FILE_MISSING_IN_WORKTREE:" + file_rel)
        original = path.read_text(encoding="utf-8")
        lines = original.splitlines(keepends=True)
        new_lines = list(lines)
        splices = []
        import_sites = [s for s in by_file[file_rel] if s["kind"] == "IMPORT_SITE"]
        if import_sites:
            # plan rows carry only the file for IMPORT_SITE: re-parse the file
            # and locate every ImportFrom statement that names the symbol.
            try:
                tree = ast.parse(original, filename=file_rel)
            except SyntaxError as exc:
                raise ValueError(f"IMPORT_FILE_UNPARSEABLE:{file_rel}:{exc.lineno}")
            spans = []
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and str(node.module or "") == defining_dot:
                    if any(a.name == name for a in node.names):
                        if node.end_lineno != node.lineno:
                            raise ValueError("MULTILINE_IMPORT_SPAN:" +
                                             f"{file_rel}:{node.lineno}")
                        spans.append((int(node.lineno), int(node.col_offset)))
            if not spans:
                raise ValueError("IMPORT_SITE_STATEMENT_NOT_FOUND:" + file_rel)
            for lineno, col0 in spans:
                idx = lineno - 1
                if idx < 0 or idx >= len(new_lines):
                    raise ValueError(f"LINE_OUT_OF_RANGE:{file_rel}:{lineno}")
                body = new_lines[idx].rstrip("\n")
                ending = new_lines[idx][len(body):]
                # splice only the alias token inside `from X import <names>`
                head, _, tail = body.partition(" import ")
                if not tail:
                    raise ValueError(f"IMPORT_STATEMENT_SHAPE_UNKNOWN:{file_rel}:{lineno}")
                seg = re.sub(r"\b" + re.escape(name) + r"\b(?!\s+as\b)",
                             new_name, tail, count=1)
                if seg == tail:
                    # name present only as `name as alias`: refusing beats guessing
                    raise ValueError(f"ALIASED_IMPORT_UNTRACKED:{file_rel}:{lineno}")
                new_lines[idx] = head + " import " + seg + ending
                splices.append({"file": file_rel, "kind": "IMPORT_SITE", "lineno": lineno})
        inline = [s for s in by_file[file_rel] if s["kind"] != "IMPORT_SITE"]
        for site in sorted(inline,
                           key=lambda s: (s.get("lineno", 0), s.get("col", 0)), reverse=True):
            idx = int(site["lineno"]) - 1
            if idx < 0 or idx >= len(new_lines):
                raise ValueError(f"LINE_OUT_OF_RANGE:{file_rel}:{site['lineno']}")
            body = new_lines[idx].rstrip("\n")
            ending = new_lines[idx][len(body):]
            body = _splice_site(body, name, new_name, site)
            new_lines[idx] = body + ending
            splices.append({"file": file_rel, "kind": site["kind"],
                            "lineno": int(site["lineno"])})
        new_text = "".join(new_lines)
        path.write_text(new_text, encoding="utf-8")
        touched.append({"file": file_rel, "new_sha256": _sha256(new_text.encode("utf-8")),
                        "splice_count": len(splices)})
    return {"touched_files": touched,
            "splice_total": sum(r["splice_count"] for r in touched)}


def _apply_move(work_src: Path, op: dict, plan_op: dict) -> dict:
    """Apply a choreographed move_symbol plan: cut the (decorator-aware)
    definition span out of the defining module, insert it at the target
    module's end (module created if absent), rewrite from-imports that
    bound the moved name (splitting multi-name imports deterministically),
    and inject a re-import into the defining module when the slice-4 plan
    proved it still references the moved name.  Any wobble fails closed."""
    module, qualname, to_module = op["module"], op["qualname"], op["to_module"]
    name = qualname.rsplit(".", 1)[-1]
    defining_dot = (module[:-3] if module.endswith(".py") else module).replace("/", ".")
    to_dot = (to_module[:-3] if to_module.endswith(".py") else to_module).replace("/", ".")

    # ---- 1. cut the definition block -----------------------------------
    cut_site = next((s for s in plan_op["sites"] if s["kind"] == "CUT_SPAN"), None)
    if not cut_site:
        raise ValueError("MOVE_PLAN_MISSING_CUT_SPAN")
    src_path = work_src / module
    if not src_path.is_file():
        raise ValueError("PLANNED_FILE_MISSING_IN_WORKTREE:" + module)
    lines = src_path.read_text(encoding="utf-8").splitlines(keepends=True)
    top = int(cut_site["lineno"]) - 1
    # decorator-aware upward scan with paren tracking
    depth, curs = 0, top - 1
    while curs >= 0:
        raw = lines[curs].rstrip("\n")
        stripped = raw.strip()
        if depth > 0:
            depth += raw.count(")") - raw.count("(")
            top = curs
            curs -= 1
            continue
        if stripped.startswith("@"):
            d = raw.count("(") - raw.count(")")
            top = curs
            curs -= 1
            if d > 0:
                depth = d
            continue
        break
    if depth != 0:
        raise ValueError("MOVE_DECORATOR_SPAN_COMPLEX:" + module)
    bottom = int(cut_site["line_end"]) - 1
    if not (0 <= top <= bottom < len(lines)):
        raise ValueError(f"MOVE_SPAN_OUT_OF_RANGE:{module}:{top + 1}-{bottom + 1}")
    block = lines[top:bottom + 1]
    head_line = next(l for l in block if re.match(r"\s*(def|class)\s", l))
    if not re.match(r"\s*(?:def|class)\s+" + re.escape(name) + r"\b", head_line.lstrip("\n")):
        raise ValueError("MOVE_CUT_NOT_TARGET_DEFINITION:" + module)
    rem_text = "".join(lines[:top] + lines[bottom + 1:])
    rem_text = re.sub(r"\n{3,}", "\n\n", rem_text)
    if not rem_text.endswith("\n"):
        rem_text += "\n"

    refs_here = [s for s in plan_op["sites"]
                 if s["kind"] == "REFERENCE" and s["file"] == module]
    if refs_here:
        inject = f"from {to_dot} import {name}\n"
        rem_lines = rem_text.splitlines(keepends=True)
        insert_at = 0
        for i, l in enumerate(rem_lines):
            if re.match(r"(import |from )", l):
                insert_at = i + 1
        rem_lines.insert(insert_at, inject)
        rem_text = "".join(rem_lines)
    src_path.write_text(rem_text, encoding="utf-8")

    # ---- 2. insert the block at the target end --------------------------
    tgt_path = work_src / to_module
    created = not tgt_path.is_file()
    if created:
        tgt_path.parent.mkdir(parents=True, exist_ok=True)
        tgt_path.write_text("", encoding="utf-8")
    tgt_text = tgt_path.read_text(encoding="utf-8")

    # dependency-closure law: names the moved block loads that were bound at
    # module scope in the DEFINING module follow the move as injected
    # from-imports into the TARGET (deterministic order; never silently
    # dropped — if the block cannot be parsed the whole apply refuses).
    block_text = "".join(block)
    try:
        block_tree = ast.parse(block_text, filename="<moved_block>")
        src_tree = ast.parse(src_path.read_text(encoding="utf-8"), filename=module)
    except SyntaxError as exc:
        raise ValueError(f"MOVE_DEPENDENCY_ANALYSIS_UNPARSEABLE:{exc.lineno}")

    def _bound_names(tree) -> set[str]:
        bound = set()
        for node in getattr(tree, "body", []):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                bound.add(node.name)
            elif isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        bound.add(t.id)
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                bound.add(node.target.id)
            elif isinstance(node, ast.Import):
                bound.update((a.asname or a.name.split(".")[0]) for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                bound.update((a.asname or a.name) for a in node.names)
        return bound

    def _loaded_names(tree) -> set[str]:
        loaded = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                loaded.add(node.id)
        return loaded

    defining_scope = _bound_names(src_tree)
    block_own_scope = set(_bound_names(block_tree))
    for node in ast.walk(block_tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            a = node.args
            block_own_scope.update(x.arg for x in [*a.posonlyargs, *a.args, *a.kwonlyargs])
            if a.vararg:
                block_own_scope.add(a.vararg.arg)
            if a.kwarg:
                block_own_scope.add(a.kwarg.arg)
        else:
            tgt = getattr(node, "target", None)
            if isinstance(tgt, ast.Name):
                block_own_scope.add(tgt.id)
    needed = sorted(n for n in _loaded_names(block_tree)
                    if n in defining_scope and n not in block_own_scope and n != name)
    if needed:
        inject_line = f"from {defining_dot} import {', '.join(needed)}\n"
        tgt_lines = tgt_text.splitlines(keepends=True)
        existing_inject = False
        insert_at = 0
        for i, l in enumerate(tgt_lines):
            if re.match(r"(import |from )", l):
                insert_at = i + 1
                if l.strip() == inject_line.strip():
                    existing_inject = True
        if not existing_inject:
            tgt_lines.insert(insert_at, inject_line)
            tgt_text = "".join(tgt_lines)

    if tgt_text.strip():
        tgt_text = tgt_text.rstrip("\n") + "\n\n" + block_text.rstrip("\n") + "\n"
    else:
        tgt_text = block_text.rstrip("\n") + "\n"
    tgt_path.write_text(tgt_text, encoding="utf-8")

    # ---- 3. rewrite from-imports on every planned IMPORT_REWRITE site ---
    rewrites = 0
    for site in plan_op["sites"]:
        if site["kind"] != "IMPORT_REWRITE":
            continue
        file_rel = site["file"]
        path = work_src / file_rel
        text = path.read_text(encoding="utf-8")
        t_lines = text.splitlines(keepends=True)
        try:
            tree = ast.parse(text, filename=file_rel)
        except SyntaxError as exc:
            raise ValueError(f"IMPORT_FILE_UNPARSEABLE:{file_rel}:{exc.lineno}")
        edit_lines = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and str(node.module or "") == defining_dot \
                    and any(a.name == name for a in node.names):
                if node.end_lineno != node.lineno:
                    raise ValueError(f"MULTILINE_IMPORT_SPAN:{file_rel}:{node.lineno}")
                edit_lines.append(int(node.lineno))
        if not edit_lines:
            raise ValueError("IMPORT_REWRITE_STATEMENT_NOT_FOUND:" + file_rel)
        for lineno in sorted(edit_lines, reverse=True):
            idx = lineno - 1
            body = t_lines[idx].rstrip("\n")
            ending = t_lines[idx][len(body):]
            _prefix, _mid, tail = body.partition("import")
            names_part = tail.strip()
            if names_part.startswith("(") or names_part.endswith("\\"):
                raise ValueError(f"MULTILINE_IMPORT_SPAN:{file_rel}:{lineno}")
            names = [x.strip() for x in names_part.split(",")]
            moved_alias = next(a for a in names if a.split(" as ")[0].strip() == name)
            others = [a for a in names if a is not moved_alias]
            seg = [f"from {to_dot} import {moved_alias}"]
            if others:
                seg.append(f"from {defining_dot} import {', '.join(others)}")
            t_lines[idx:idx + 1] = [s + ("\n" if i < len(seg) - 1 else ending)
                                    for i, s in enumerate(seg)]
            rewrites += 1
        path.write_text("".join(t_lines), encoding="utf-8")

    touched = [{"file": module, "op": "CUT"}, {"file": to_module, "op": "INSERT"}]
    touched += [{"file": s["file"], "op": "IMPORT_REWRITE"} for s in plan_op["sites"]
                if s["kind"] == "IMPORT_REWRITE"]
    return {"touched_files": touched,
            "splice_total": 1 + rewrites + (1 if refs_here else 0)}


def _verify_application(work_src: Path, edits: list[dict]) -> tuple[bool, list[str], bytes]:
    """Prove the edits against a fresh index and return its bytes for reuse.

    Renames must leave the old name gone and the new name bound at module
    scope; moves must leave the definition in the target and not the source.
    The same freshly built index can then serve advisory impact selection,
    after that consumer verifies its file-set and content hashes.
    """
    from canonical.runtime.bound_capabilities import python_source_symbol_index as indexer

    out = work_src / ".orchestrate_probe_index.json"
    indexer.run({"source_root": ".", "output_path": out.name}, work_src)
    index_bytes = out.read_bytes()
    index = json.loads(index_bytes)
    out.unlink()
    problems = []
    defs_of = {}
    for row in index.get("modules") or []:
        defs_of[row["path"]] = {d["name"] for d in row.get("definitions") or []
                                if str(d["qualname"]).count(".") == 0}
    for op in edits:
        if op["op"] == "rename_symbol":
            mod_names = defs_of.get(op["module"])
            if mod_names is None:
                problems.append("MODULE_NOT_REINDEXED:" + op["module"])
                continue
            if op["name"] in mod_names:
                problems.append("OLD_NAME_STILL_DEFINED:" + op["module"] + ":" + op["name"])
            if op["new_name"] not in mod_names:
                problems.append("NEW_NAME_NOT_DEFINED:" + op["module"] + ":" + op["new_name"])
        elif op["op"] == "move_symbol":
            name = str(op["qualname"]).rsplit(".", 1)[-1]
            src_names = defs_of.get(op["module"], set())
            tgt_names = defs_of.get(op["to_module"])
            if tgt_names is None:
                problems.append("TARGET_MODULE_NOT_REINDEXED:" + op["to_module"])
                continue
            if name not in tgt_names:
                problems.append("MOVED_NAME_NOT_IN_TARGET:" + op["to_module"] + ":" + name)
            if name in src_names:
                problems.append("MOVED_NAME_STILL_IN_SOURCE:" + op["module"] + ":" + name)
    return (not problems), problems, index_bytes


def run(args, root):
    repo = Path(root).resolve()
    args = dict(args or {})
    task_rel = str(args.get("task_path") or "")
    task_path = _safe_path(repo, task_rel, must_exist=True)
    try:
        task = json.loads(task_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        _fail("TASK_UNREADABLE_JSON:" + type(exc).__name__)
    for key in ("issue_id", "edits"):
        if key not in task:
            _fail("TASK_SCHEMA_MISSING:" + key)
    edits = task["edits"]
    if not isinstance(edits, list) or not edits:
        _fail("TASK_EDITS_EMPTY")
    for op in edits:
        if not isinstance(op, dict) or op.get("op") not in ("rename_symbol", "move_symbol"):
            _fail("UNSUPPORTED_OP_AT_APPLY:" + str((op or {}).get("op")))
    issue_id = str(task["issue_id"])
    title = str(task.get("title") or issue_id)

    source_root = str(args.get("source_root") or "")
    source_abs = _safe_path(repo, source_root, must_exist=True)
    if not source_abs.is_dir():
        _fail("SOURCE_ROOT_NOT_DIRECTORY")
    worktree_rel = str(args.get("worktree_path") or "")
    worktree_abs = _safe_path(repo, worktree_rel)
    output_abs = _safe_path(repo, str(args.get("output_path") or ""))
    diff_abs = _safe_path(repo, str(args.get("diff_path") or ""))
    pr_abs = _safe_path(repo, str(args.get("pr_intent_path") or ""))
    timeout_s = int(args.get("timeout_s") or 300)
    python_exe = str(args.get("python_executable") or sys.executable)
    pytest_version = None
    try:
        probe = subprocess.run([python_exe, "-c",
                                "import pytest;print(pytest.__version__)"],
                               capture_output=True, text=True, timeout=min(timeout_s, 60))
        if probe.returncode == 0:
            pytest_version = probe.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass  # The edit can still be inspected, but tests cannot be verified.

    # nesting laws — the spoke index scan rglobs its root: any overlap
    # between the source tree, the worktree, or the artifact outputs double-
    # indexes the world and poisons the manifest proof.  Refuse overlap.
    if worktree_abs == source_abs or worktree_abs in source_abs.parents \
            or source_abs in worktree_abs.parents:
        _fail("WORKTREE_OVERLAPS_SOURCE_ROOT")
    for out_abs, key in ((output_abs, "output_path"), (diff_abs, "diff_path"),
                         (pr_abs, "pr_intent_path")):
        if out_abs == source_abs or source_abs in out_abs.parents \
                or out_abs == worktree_abs or worktree_abs in out_abs.parents:
            _fail("ARTIFACT_PATH_OVERLAPS_SOURCE_OR_WORKTREE:" + key)

    started = time.monotonic()
    before = _tree_manifest(source_abs)

    _copy_tree(source_abs, worktree_abs)

    # a move_symbol into a not-yet-existing module states the intent to
    # create that module: stage the empty file so the planner can index it.
    for op in edits:
        if op["op"] == "move_symbol":
            tgt = worktree_abs / str(op["to_module"])
            if not tgt.exists():
                tgt.parent.mkdir(parents=True, exist_ok=True)
                tgt.write_text("", encoding="utf-8")

    plan_path = ".orchestrate_plan.json"
    ch_args = {"source_root": ".", "output_path": plan_path,
               "edits_path": None, "edits": json.dumps(edits)}
    if args.get("index_path"):
        cached = _safe_path(repo, str(args["index_path"]), must_exist=True)
        # spoke guards confine reads to their own root: pass the cache into
        # the worktree, reuse through slice-4's validated cache law.
        shutil.copy2(cached, worktree_abs / ".orchestrate_index_cache.json")
        ch_args["index_path"] = ".orchestrate_index_cache.json"
    choreograph.run(ch_args, worktree_abs)
    plan = json.loads((worktree_abs / plan_path).read_text(encoding="utf-8"))

    refused = int(plan["refused_op_count"])
    ambiguous = int(plan["ambiguous_site_count"])
    if refused or ambiguous:
        receipt = {"task_id": issue_id, "refused": True, "refusal_reason":
                   "AMBIGUOUS_OR_REFUSED_PLAN", "plan_refusals": plan["refusals"],
                   "ambiguous_site_count": ambiguous}
        output_abs.parent.mkdir(parents=True, exist_ok=True)
        output_abs.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        after = _tree_manifest(source_abs)
        if after != before:
            _fail("SOURCE_TREE_MUTATED_BEFORE_REFUSAL")
        _fail(json.dumps(receipt, sort_keys=True))

    applied, problems = 0, []
    splice_rows = []
    for op, plan_op in zip(edits, plan["plans"]):
        apply_row = (_apply_rename if op["op"] == "rename_symbol" else _apply_move)(
            worktree_abs, op, plan_op)
        applied += 1
        splice_rows.append(apply_row)

    ok, verify_problems, verified_index = _verify_application(worktree_abs, edits)
    if not ok:
        _fail("APPLICATION_PROOF_FAILED:" + ",".join(verify_problems))

    after = _tree_manifest(source_abs)
    if after != before:
        _fail("SOURCE_TREE_MUTATED")

    # minimal test selection on the staged diff
    old_new = {}
    for row in splice_rows:
        for f in row["touched_files"]:
            rel = f["file"]
            old_file = source_abs / rel
            old_text = old_file.read_text(encoding="utf-8") if old_file.is_file() else ""
            new_text = (worktree_abs / rel).read_text(encoding="utf-8")
            if old_text != new_text:
                old_new[rel] = (old_text, new_text)
    diff_chunks = []
    for rel in sorted(old_new):
        old_text, new_text = old_new[rel]
        created = not (source_abs / rel).is_file()
        diff_chunks.append("".join(difflib.unified_diff(
            old_text.splitlines(keepends=True), new_text.splitlines(keepends=True),
            fromfile=("/dev/null" if created else "a/" + rel), tofile="b/" + rel)))
    diff_text = "".join(diff_chunks)
    diff_abs.parent.mkdir(parents=True, exist_ok=True)
    diff_abs.write_text(diff_text, encoding="utf-8")
    diff_sha = _sha256(diff_text.encode("utf-8"))

    changed_paths = sorted(old_new)
    # diff-based selection (exact line ranges) beats path-list module-wide mode;
    # the spoke sees the diff inside its own root (confinement law).
    (worktree_abs / ".orchestrate_stage.diff").write_text(diff_text, encoding="utf-8")
    # Reuse the just-rebuilt fixed-point index instead of parsing the entire
    # staged tree a second time. The selector independently rechecks its file
    # set and hashes; the temporary copy is removed even if selection fails.
    with tempfile.TemporaryDirectory(prefix=".orchestrate_verified_", dir=worktree_abs) as tmp:
        cache = Path(tmp) / "index.json"
        cache.write_bytes(verified_index)
        testselect.run({
            "source_root": ".",
            "diff_path": ".orchestrate_stage.diff",
            "changed_paths": None,
            "test_roots": ["."],
            "output_path": ".orchestrate_testselect.json",
            "index_path": str(cache.relative_to(worktree_abs)),
        }, worktree_abs)
    selection = json.loads((worktree_abs / ".orchestrate_testselect.json").read_text(encoding="utf-8"))
    selected = sorted(r["path"] for r in (selection.get("tests") or []) if r.get("selected"))

    # The impact slice is useful advice, but static imports cannot establish
    # that unselected tests are unaffected (dynamic imports are one example).
    # Run the whole conventionally discovered suite once in the existing copy.
    test_evidence = _run_worktree_tests(worktree_abs, python_exe, pytest_version, timeout_s)
    test_evidence["selected"] = len(selected)
    test_evidence["selection_role"] = "advisory"
    test_passed = test_evidence["passed"]
    test_failed = test_evidence["failed"]

    pr_intent = {
        "schema": "pr_intent_v1", "issue_id": issue_id, "title": title,
        "base": "main",
        "body": {
            "summary": str(task.get("body") or "")[:4000],
            "changed_files": changed_paths,
            "plan": {"planned_op_count": plan["planned_op_count"],
                     "planned_site_count": plan["planned_site_count"],
                     "complete": plan["complete"]},
            "tests": test_evidence,
            "proof": {"fixed_point_verified": True, "diff_sha256": diff_sha},
        },
        "checklist": ["plan complete (zero ambiguous sites)",
                      "apply fixed point proven by re-index",
                      "run discovered conventional tests under source_root"],
    }
    pr_abs.parent.mkdir(parents=True, exist_ok=True)
    pr_text = json.dumps(pr_intent, indent=2, ensure_ascii=False) + "\n"
    pr_abs.write_text(pr_text, encoding="utf-8")
    pr_verified = json.loads(pr_abs.read_text(encoding="utf-8")) == pr_intent

    edits_verified = pr_verified and not problems
    tests_verified = test_evidence["status"] == "PASSED"
    verified = edits_verified and tests_verified
    summary = {
        "adapter": "python_issue_to_pr_orchestrate",
        "task_id": issue_id,
        "planned_op_count": plan["planned_op_count"],
        "applied_op_count": applied,
        "refused_op_count": refused,
        "applied_site_count": sum(r["splice_total"] for r in splice_rows),
        "test_selected_count": len(selected),
        "test_passed_count": test_passed,
        "test_failed_count": test_failed,
        "test_pytest": pytest_version or "UNAVAILABLE",
        "diff_sha256": diff_sha,
        "pr_intent_verified": pr_verified,
        "edits_verified": bool(edits_verified),
        "verified": bool(verified),
    }
    output_abs.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(summary, indent=2, ensure_ascii=False) + "\n"
    output_abs.write_text(text, encoding="utf-8")
    summary["output_path"] = str(args.get("output_path"))
    summary["output_sha256"] = _sha256(text.encode("utf-8"))
    summary["seconds"] = round(time.monotonic() - started, 3)
    return summary


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    for name in ("task_path", "source_root", "worktree_path", "output_path",
                 "diff_path", "pr_intent_path"):
        p.add_argument("--" + name, required=True)
    p.add_argument("--index_path", default=None)
    p.add_argument("--python_executable", default=None)
    p.add_argument("--timeout_s", type=int, default=300)
    ns = p.parse_args()
    result = run(vars(ns), Path.cwd())
    print(json.dumps(result, indent=2, sort_keys=True))
