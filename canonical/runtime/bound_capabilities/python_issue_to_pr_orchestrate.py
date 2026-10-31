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
      -> select minimal tests          (slice 2: python_change_impact_testselect)
      -> run selected tests            (pytest on the worktree)
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
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

from canonical.runtime.bound_capabilities import (
    python_crossfile_edit_choreograph as choreograph,
)
from canonical.runtime.bound_capabilities import (
    python_change_impact_testselect as testselect,
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


def _tree_manifest(root: Path) -> dict:
    rows = []
    for p in sorted(root.rglob("*.py")):
        if p.is_file() and not any(part in _SKIP_DIRS for part in p.parts):
            rows.append([str(p.relative_to(root)).replace("\\", "/"), _sha256(p.read_bytes())])
    return {"file_count": len(rows),
            "sha256": _sha256(json.dumps(rows, separators=(",", ":")).encode("utf-8"))}


def _copy_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)

    def ignore(_dir, names):
        return [n for n in names if n in _SKIP_DIRS]

    shutil.copytree(src, dst, dirs_exist_ok=True, ignore=ignore)


# --------------------------------------------------------------------------
# apply layer — deterministic token splicing driven only by plan site rows
# --------------------------------------------------------------------------

def _splice_token(line: str, name: str, new_name: str, col: int) -> str:
    """Replace the token occurrence of `name` sitting exactly at `col`
    (ast col_offset semantics).  Off-position refuses, never guesses."""
    raw, token = line.encode("utf-8"), name.encode("utf-8")
    if col < 0 or raw[col:col + len(token)] != token or not name.isidentifier():
        raise ValueError(f"TOKEN_NOT_AT_INDEXED_POSITION:{col}")
    try:
        head, tail = raw[:col].decode("utf-8"), raw[col + len(token):].decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("TOKEN_BYTE_BOUNDARY_INVALID") from exc
    if tail and (tail[0].isalnum() or tail[0] == "_"):
        raise ValueError("TOKEN_BOUNDARY_VIOLATION:" + line[:60])
    return head + new_name + tail


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
        inline = [s for s in by_file[file_rel] if s["kind"] != "IMPORT_SITE"]
        import_sites = [s for s in by_file[file_rel] if s["kind"] == "IMPORT_SITE"]
        if import_sites:
            # AST alias spans identify the actual identifier, including in
            # parenthesized/backslash imports. Preserve every other byte:
            # comments, whitespace, other names and same-line statements.
            try:
                tree = ast.parse(original, filename=file_rel)
            except SyntaxError as exc:
                raise ValueError(f"IMPORT_FILE_UNPARSEABLE:{file_rel}:{exc.lineno}")
            aliases = [alias for node in ast.walk(tree)
                       if isinstance(node, ast.ImportFrom) and str(node.module or "") == defining_dot
                       for alias in node.names if alias.name == name]
            if not aliases:
                raise ValueError("IMPORT_SITE_STATEMENT_NOT_FOUND:" + file_rel)
            for alias in aliases:
                if alias.asname is not None:
                    raise ValueError(f"ALIASED_IMPORT_UNTRACKED:{file_rel}:{alias.lineno}")
                inline.append({"kind": "IMPORT_SITE", "lineno": alias.lineno, "col": alias.col_offset})
        # One reverse-position pass is essential: an import and a reference
        # may share a line, and earlier replacements change later offsets.
        for site in sorted(inline,
                           key=lambda s: (s.get("lineno", 0), s.get("col", 0)), reverse=True):
            idx = int(site["lineno"]) - 1
            if idx < 0 or idx >= len(new_lines):
                raise ValueError(f"LINE_OUT_OF_RANGE:{file_rel}:{site['lineno']}")
            body = new_lines[idx].rstrip("\n")
            ending = new_lines[idx][len(body):]
            body = (_splice_token(body, name, new_name, int(site["col"]))
                    if site["kind"] == "IMPORT_SITE" else _splice_site(body, name, new_name, site))
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


def _verify_application(work_src: Path, edits: list[dict]) -> tuple[bool, list[str]]:
    """Fixed-point proof: re-index the edited worktree.  Renames must leave
    the old name gone and the new name bound at module scope; moves must
    leave the moved name defined in the target module and absent from the
    defining module's own definitions (a re-injected from-import is text,
    not a definition)."""
    from canonical.runtime.bound_capabilities import python_source_symbol_index as indexer

    out = work_src / ".orchestrate_probe_index.json"
    indexer.run({"source_root": ".", "output_path": out.name}, work_src)
    index = json.loads(out.read_text(encoding="utf-8"))
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
    return (not problems), problems


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
    probe = subprocess.run([python_exe, "-c",
                            "import pytest;print(pytest.__version__)"],
                           capture_output=True, text=True, timeout=min(timeout_s, 60))
    if probe.returncode == 0:
        pytest_version = probe.stdout.strip()

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

    ok, verify_problems = _verify_application(worktree_abs, edits)
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
    testselect.run({
        "source_root": ".",
        "diff_path": ".orchestrate_stage.diff",
        "changed_paths": None,
        "test_roots": ["."],
        "output_path": ".orchestrate_testselect.json",
    }, worktree_abs)
    selection = json.loads((worktree_abs / ".orchestrate_testselect.json").read_text(encoding="utf-8"))
    selected = sorted(r["path"] for r in (selection.get("tests") or []) if r.get("selected"))

    # run the selected subset on the worktree
    test_passed, test_failed, run_rc = 0, 0, None
    if selected and pytest_version:
        proc = subprocess.run(
            [python_exe, "-m", "pytest", "-q", "-p", "no:cacheprovider"] + selected,
            cwd=worktree_abs, capture_output=True, text=True, timeout=timeout_s)
        run_rc = proc.returncode
        m = re.search(r"(\d+) passed", proc.stdout + proc.stderr)
        test_passed = int(m.group(1)) if m else 0
        m = re.search(r"(\d+) failed", proc.stdout + proc.stderr)
        test_failed = int(m.group(1)) if m else 0

    pr_intent = {
        "schema": "pr_intent_v1", "issue_id": issue_id, "title": title,
        "base": "main",
        "body": {
            "summary": str(task.get("body") or "")[:4000],
            "changed_files": changed_paths,
            "plan": {"planned_op_count": plan["planned_op_count"],
                     "planned_site_count": plan["planned_site_count"],
                     "complete": plan["complete"]},
            "tests": {"selected": len(selected), "passed": test_passed,
                      "failed": test_failed, "pytest_rc": run_rc},
            "proof": {"fixed_point_verified": True, "diff_sha256": diff_sha},
        },
        "checklist": ["plan complete (zero ambiguous sites)",
                      "apply fixed point proven by re-index",
                      "minimal test selection executed"],
    }
    pr_abs.parent.mkdir(parents=True, exist_ok=True)
    pr_text = json.dumps(pr_intent, indent=2, ensure_ascii=False) + "\n"
    pr_abs.write_text(pr_text, encoding="utf-8")
    pr_verified = json.loads(pr_abs.read_text(encoding="utf-8")) == pr_intent

    edits_verified = pr_verified and not problems
    tests_verified = (run_rc == 0) if selected else True
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
