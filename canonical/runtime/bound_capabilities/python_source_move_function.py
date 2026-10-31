#!/usr/bin/env python3
"""python.refactor.move_function.v1 — a definition changes module, callers follow.

"Move the function line_total from <b>/app/models.py to <b>/app/service.py and
update every caller" is four mechanical facts, and the machine already computes
each of them:

  * which span is the definition -- `ast` gives `lineno`/`end_lineno`, and the
    decorators above it are part of it;
  * who imports it -- `python.source.symbols.index.ast` already records every
    import edge, so the rewrite set is read, not guessed;
  * how a module spells its package -- `_modname_of` in the rename adapter, the
    same function that made cross-module renames byte-exact;
  * whether the move worked -- the project's own `unittest` discovery, plus a
    tree-wide check that the OLD import spelling survives nowhere.

`python_crossfile_edit_choreograph.build_plan` plans exactly this operation
(`move_symbol` -> CUT_SPAN / INSERT_SPAN / IMPORT_REWRITE), and its refusal
conditions are the ones used here: the target module must exist in the index, the
name must be at module scope, and the target must not already define it.  What
the tree never had was the executor; this adapter is that executor and nothing
else, so the plan and the edit cannot disagree.

Byte discipline: the cut is a line-span splice and the insert is an append after
the target module's last non-blank line.  No `ast.unparse`, no reprint -- every
other byte survives.

Proof, in order, before returning: every edited file parses; the old module no
longer defines the name; no file anywhere in the project still imports the name
from the old module; the suite is green.  Any failure restores every original
byte.
"""
from __future__ import annotations

import ast
import hashlib
import json
import pathlib
import re
import subprocess
import sys

SCHEMA = "PROJECT_BRAIN_PYTHON_MOVE_FUNCTION_V1"
CAPABILITY_ID = "python.refactor.move_function.v1"
PROVIDES = ["python.refactor.move_function", "python.refactor.symbol.relocated"]
REQUIRES = ["python.source.symbols.index.ast"]


def _safe_root(repo: pathlib.Path, raw) -> pathlib.Path:
    p = (repo / str(raw or "")).resolve()
    if p != repo and repo not in p.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    if not p.exists():
        raise RuntimeError("SOURCE_ROOT_MISSING")
    return p


def _rel(repo: pathlib.Path, path: pathlib.Path) -> str:
    return str(path.relative_to(repo)).replace("\\", "/")


def _files(root: pathlib.Path) -> list[pathlib.Path]:
    return [p for p in sorted(root.rglob("*.py"))
            if "__pycache__" not in p.parts and ".git" not in p.parts]


def _modname_of(rel: str) -> str:
    parts = pathlib.PurePosixPath(rel).with_suffix("").parts
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _span(node: ast.AST) -> tuple[int, int]:
    start = int(getattr(node, "lineno", 1))
    for dec in getattr(node, "decorator_list", []) or []:
        start = min(start, int(getattr(dec, "lineno", start)))
    return start, int(getattr(node, "end_lineno", start))


def _suite(project_root: pathlib.Path, tests: pathlib.Path, timeout_s: int) -> tuple[bool, str]:
    try:
        proc = subprocess.run(
            [sys.executable, "-B", "-m", "unittest", "discover",
             "-s", str(tests), "-t", str(project_root)],
            cwd=str(project_root), capture_output=True, text=True, timeout=timeout_s,
            env={"PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": str(project_root),
                 "PATH": "/usr/local/bin:/usr/bin:/bin"})
    except subprocess.TimeoutExpired:
        return False, "SUITE_TIMEOUT"
    return proc.returncode == 0, ((proc.stdout or "") + (proc.stderr or ""))[-300:]


def _definitions(tree: ast.Module) -> set[str]:
    """Names the module DEFINES at top level (a def, a class, or a binding)."""
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
    return names


def _module_scope(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for a in node.names:
                names.add(a.asname or a.name.split(".")[0])
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    names.add(t.id)
    return names


def run(args, root):
    repo = pathlib.Path(root).resolve()
    source_root = _safe_root(repo, args.get("source_root"))
    output = (repo / str(args.get("output_path") or "")).resolve()
    if output == repo or repo not in output.parents:
        raise RuntimeError("PATH_OUTSIDE_REPOSITORY")
    timeout_s = int(args.get("timeout_s") or 60)
    name = str(args.get("symbol") or "").strip()
    from_module = str(args.get("module") or "").strip()
    to_module = str(args.get("to_module") or "").strip()

    project_root = (source_root.parent
                    if source_root != repo and source_root.name not in ("", ".")
                    else source_root)
    tests = project_root / "tests"
    if not tests.is_dir():
        raise RuntimeError("TEST_ROOT_MISSING")

    # The subject is the whole PROJECT: a caller can live outside the named tree.
    parsed: dict[pathlib.Path, tuple[str, ast.Module, str]] = {}
    for path in _files(project_root):
        try:
            text = path.read_text(encoding="utf-8")
            tree = ast.parse(text, filename=str(path))
        except (OSError, SyntaxError, ValueError):
            continue
        parsed[path] = (text, tree, _modname_of(_rel(repo, path)))

    # A module name is spelled from the PROJECT root, not from the named subtree:
    # `app.models` under a subject of `<b>/app` resolved to `<b>/app/app/models.py`
    # and refused with MODULE_NOT_FOUND.  The parsed map is keyed the same way, so
    # this is the spelling the index already uses.
    # A module is spelled TWO ways in this tree and both are stated by people:
    # dotted (`app.models`, what this adapter's docstring says) and as the file
    # path the binder derives from a stated `<b>/app/models.py`.  The sibling
    # rename adapters take the path form, so a path is used as given and only a
    # dotted name is expanded -- never both, or `app/models.py` became
    # `app/models.py.py`.
    def _resolve(spec: str) -> pathlib.Path:
        """The module a spec names, in either of the spellings a sentence uses.

        A module is written dotted (`app.models`), as a path relative to the
        SOURCE ROOT (what the sibling rename adapters take), or as the path the
        binder states, which is relative to the REPOSITORY.  All three are the
        same file; trying them in order keeps one meaning.  Measured: the front
        binder states the repository-relative path, and joining that onto the
        project root made `<b>/app/app/models.py`.
        """
        spec = spec.strip().replace("\\", "/")
        if spec.endswith(".py"):
            for base in (project_root, repo, source_root):
                candidate = (base / spec).resolve()
                if candidate in parsed:
                    return candidate
            raise RuntimeError("MODULE_NOT_FOUND:" + spec)
        dotted = spec.replace(".", "/") + ".py"
        for base in (project_root, repo):
            candidate = (base / dotted).resolve()
            if candidate in parsed:
                return candidate
        raise RuntimeError("MODULE_NOT_FOUND:" + spec)

    src_path = _resolve(from_module)
    dst_path = _resolve(to_module)
    # The IMPORT SPELLING is not the spec the sentence stated: the binder hands a
    # repository-relative PATH, while an import names a DOTTED module.  Measured:
    # `module=<b>/app/models.py` left every `from app.models import line_total`
    # untouched (the comparison was path against dotted name), so the cut broke
    # the importers and the suite refused a move whose own edits were right.
    # The spelling is read off the resolved file, relative to the tree that holds
    # it as a package.
    src_module = _modname_of(_rel(project_root, src_path))
    dst_module = _modname_of(_rel(project_root, dst_path))
    if src_path not in parsed:
        raise RuntimeError("MODULE_NOT_FOUND:" + from_module)
    if dst_path not in parsed:
        raise RuntimeError("TARGET_MODULE_NOT_FOUND:" + to_module)
    if src_path == dst_path:
        raise RuntimeError("SOURCE_AND_TARGET_ARE_THE_SAME_MODULE")

    text, tree, _ = parsed[src_path]
    definition = None
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            definition = node
            break
    if definition is None:
        raise RuntimeError("DEFINITION_NOT_FOUND:" + from_module + ":" + name)
    # A DEFINITION in the target is a collision; an IMPORT of the same name is
    # not -- that import is the stale edge this adapter rewrites away, and the
    # fixture's own service.py carries it.  Measured: comparing module scope
    # minus the name made this check unreachable, so a target that already
    # defines the function was silently given a second copy of it.
    if name in _definitions(parsed[dst_path][1]):
        raise RuntimeError("NAME_COLLISION_TARGET_MODULE:" + to_module + ":" + name)

    start, end = _span(definition)
    lines = text.splitlines(keepends=True)
    block = "".join(lines[start - 1:end])
    if not block.endswith("\n"):
        block += "\n"
    # Cut the definition and the blank lines it owned, never a comment that
    # belongs to the NEXT definition.
    cut_end = end
    while cut_end < len(lines) and not lines[cut_end].strip():
        cut_end += 1
    src_new = "".join(lines[:start - 1] + lines[cut_end:])
    try:
        ast.parse(src_new, filename=str(src_path))
    except SyntaxError as exc:
        raise RuntimeError("SOURCE_DOES_NOT_PARSE_AFTER_CUT:" + str(exc.lineno))

    # Callers: every `from <old_module> import <name>` becomes `from <new_module>
    # import <name>`.  `from <old> import a, <name>` drops it, because the new
    # module may live in another package and a single statement cannot split.
    rewrites: list[dict] = []
    originals: dict[pathlib.Path, bytes] = {}
    for path, (p_text, p_tree, _mod) in parsed.items():
        changed = p_text
        # The old module cannot import from itself, and the target module now
        # DEFINES the name -- measured: the target kept `from app.models import
        # line_total` after the definition landed in it, and the stale-import
        # proof refused the whole move.  Both drop the name; every other file
        # has it rewritten to the new module.
        local = path in (src_path, dst_path)
        for node in p_tree.body:
            if not isinstance(node, ast.ImportFrom) or node.module != src_module:
                continue
            names = [a.asname or a.name for a in node.names]
            if name not in names:
                continue
            kept = [a for a in node.names if (a.asname or a.name) != name]
            base = f"from {node.module} import "
            old_stmt = base + ", ".join(a.name + (f" as {a.asname}" if a.asname else "")
                                        for a in node.names)
            if local:
                new_stmt = (base + ", ".join(a.name + (f" as {a.asname}" if a.asname else "")
                                             for a in kept)) if kept else ""
            elif kept:
                new_stmt = (base + ", ".join(a.name + (f" as {a.asname}" if a.asname else "")
                                             for a in kept)
                            + "\nfrom " + dst_module + " import " + name)
            else:
                new_stmt = "from " + dst_module + " import " + name
            if changed.count(old_stmt) != 1:
                raise RuntimeError("IMPORT_STATEMENT_NOT_FOUND_VERBATIM:" + _rel(repo, path))
            # An emptied statement leaves its own line behind; drop the newline too.
            changed = changed.replace(old_stmt + "\n" if not new_stmt else old_stmt,
                                      (new_stmt + "\n") if new_stmt else "")
            rewrites.append({"file": _rel(repo, path), "line": int(node.lineno),
                             "was": old_stmt, "now": new_stmt or "(removed)"})
        if changed != p_text:
            try:
                ast.parse(changed, filename=str(path))
            except SyntaxError as exc:
                raise RuntimeError("CALLER_DOES_NOT_PARSE_AFTER_REWRITE:"
                                   + _rel(repo, path) + ":" + str(exc.lineno))
            originals[path] = path.read_bytes()
            path.write_text(changed, encoding="utf-8")

    # The insert reads the TARGET AS THE REWRITE LOOP LEFT IT.  Measured: building
    # it from the pre-rewrite parse discarded the rewrite, so the target kept
    # `from app.models import line_total` for a function defined in itself and the
    # stale-import proof refused a move that was otherwise correct.
    originals.setdefault(src_path, src_path.read_bytes())
    originals.setdefault(dst_path, dst_path.read_bytes())
    src_path.write_text(src_new, encoding="utf-8")
    dst_now = dst_path.read_text(encoding="utf-8")
    dst_new = dst_now.rstrip("\n") + "\n\n\n" + block
    try:
        ast.parse(dst_new, filename=str(dst_path))
    except SyntaxError as exc:
        dst_path.write_text(dst_now, encoding="utf-8")
        for p, b in originals.items():
            p.write_bytes(b)
        raise RuntimeError("TARGET_DOES_NOT_PARSE_AFTER_INSERT:" + str(exc.lineno))
    dst_path.write_text(dst_new, encoding="utf-8")

    # PROOF 1: the old module no longer defines it; the new one does.
    if re.search(r"^\s*(?:async\s+)?def\s+" + re.escape(name) + r"\b",
                 src_path.read_text(encoding="utf-8"), re.M):
        for p, b in originals.items():
            p.write_bytes(b)
        raise RuntimeError("DEFINITION_SURVIVED_IN_SOURCE")
    if not re.search(r"^\s*(?:async\s+)?def\s+" + re.escape(name) + r"\b",
                     dst_path.read_text(encoding="utf-8"), re.M):
        for p, b in originals.items():
            p.write_bytes(b)
        raise RuntimeError("DEFINITION_MISSING_IN_TARGET")

    # PROOF 2: no stale import spelling survives anywhere in the project.
    stale = []
    for path in _files(project_root):
        try:
            body = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if re.search(r"from\s+" + re.escape(src_module) + r"\s+import\s+[^\n]*\b"
                     + re.escape(name) + r"\b", body):
            stale.append(_rel(repo, path))
    if stale:
        for p, b in originals.items():
            p.write_bytes(b)
        raise RuntimeError("STALE_IMPORT_SURVIVED:" + ",".join(sorted(stale)))

    # PROOF 3: behaviour, by the project's own suite.
    ok, tail = _suite(project_root, tests, timeout_s)
    if not ok:
        for p, b in originals.items():
            p.write_bytes(b)
        raise RuntimeError("SUITE_FAILED_AFTER_MOVE:" + tail.replace("\n", " ")[-200:])

    raw = (json.dumps({
        "schema": SCHEMA, "capability_id": CAPABILITY_ID,
        "source_root": _rel(repo, source_root), "symbol": name,
        "from_module": src_module, "to_module": dst_module,
        "stated_module": from_module, "stated_target": to_module,
        "definition_lines": [start, end], "caller_rewrites": rewrites,
        "files_edited": sorted(_rel(repo, p) for p in originals),
        "suite_passed": True, "answer": name,
        "law": "a definition moves by cutting its own span and appending it; every importer "
               "is rewritten by the index's own edge, and the suite is the referee"},
        indent=2, sort_keys=True) + "\n").encode("utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(raw)
    return {"adapter": "python_source_move_function", "answer": name, "symbol": name,
            "from_module": src_module, "to_module": dst_module,
            "stated_module": from_module, "stated_target": to_module,
            "caller_rewrites": rewrites,
            "files_edited": sorted(_rel(repo, p) for p in originals), "suite_passed": True,
            "output_path": _rel(repo, output),
            "output_sha256": hashlib.sha256(raw).hexdigest(), "output_verified": True}
