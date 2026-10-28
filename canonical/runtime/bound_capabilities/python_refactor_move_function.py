# PROJECT_BRAIN
"""python.refactor.move_function.v1 — move a module-level function to another module.

The act a refactor runner is expected to have, and the one thing the brain was
missing next to `rename_symbol`.  Nothing about it is new machinery: the
definition is located with the same scope law, its bytes are cut by the same
span rule, every import that provably binds it is rewritten by the same
FILE-identity test (`_module_aliases`), and a red named suite restores every
byte.  What is new is only the direction: the def leaves one module and arrives
in another, and the imports have to follow.

Law:

* exactly ONE module-scope definition of ``qualname`` in ``module``; zero
  refuses SYMBOL_NOT_FOUND, two refuse MULTI_DEFINITION;
* the moved span includes its decorators and nothing else (comments immediately
  above the def are NOT moved -- they are not provably the symbol's);
* the target may be a new file (created) or an existing one (appended at the
  end, separated by two blank lines);
* every ``from <src> import name`` site becomes ``from <tgt> import name``,
  where <tgt> is spelled in the same package prefix the file already used --
  the identity test is the FILE, so ``pkg.calc`` and ``calc`` both count;
* a source module that still USES the name after the move gets
  ``from <tgt> import name`` injected, because otherwise the move silently
  breaks its own file;
* ``import <src> as alias`` + ``alias.name`` sites are rewritten ONLY when that
  alias is used for nothing else; otherwise the whole edit refuses with
  UNSUPPORTED_SHARED_MODULE_IMPORT and lists the sites -- a half-rewritten
  import is worse than a refusal;
* after every write all edited files are re-parsed; a syntax error restores all
  original bytes and refuses SYNTAX_ERROR_AFTER_EDIT;
* a named pytest suite runs; red restores ALL original bytes and refuses
  TESTS_RED_AFTER_EDIT.  No suite named => gate PASS_BLIND, verified=false.

Inputs (kwargs, repo-confined):
  source_root    tree to edit (in place)
  module         posix path of the defining module, e.g. "pkg/calc.py"
  qualname       dotted address of the function, e.g. "add"
  target_module  posix path of the module to move it into, e.g. "pkg/ops.py"
  output_path    summary artifact
  run_tests      optional list of pytest-relative test paths to verify
  python_executable, timeout_s

result_fields: adapter, module, qualname, symbol_kind, moved_to, edit_count,
files_edited, injected_imports, unresolved_sites, gate, complete,
output_path, output_sha256, output_verified, verified.
"""

from __future__ import annotations

import ast
import hashlib
import json
import subprocess
import sys
from pathlib import Path

SCHEMA = "PROJECT_BRAIN_REFACTOR_MOVE_FUNCTION_V1"
CAPABILITY_ID = "python.refactor.move_function.v1"


def _fail(reason: str) -> None:
    raise SystemExit(json.dumps({"error": True, "capability": CAPABILITY_ID,
                                 "reason": reason}, indent=2, sort_keys=True))


def _safe_path(repo: Path, rel: str, must_exist: bool = False) -> Path:
    if not rel or not isinstance(rel, str):
        _fail("MISSING_OR_INVALID_PATH_ARGUMENT")
    p = (repo / rel).resolve()
    if p != repo and repo not in p.parents:
        _fail("PATH_ESCAPE:" + rel)
    if must_exist and not p.exists():
        _fail("PATH_MISSING:" + rel)
    return p


def _in_tree(repo: Path, src_abs: Path, raw: str, must_exist: bool = False) -> Path:
    """A stated module path, resolved inside `source_root` however the caller spelled it.

    Two spellings are legitimate and a caller does not say which one they used: the
    path relative to the tree being edited (this adapter's own contract), and the path
    relative to the repository (what the front binder produces, because the sentence
    named an absolute path).  Both are the same file, so both are tried -- SOURCE-ROOT
    FIRST, and the repository-relative reading only when the first one names nothing.
    Ordering is the whole law: measured, reading repo-relative first made a path that
    resolved *inside* the tree fail PATH_MISSING, because the tree-relative spelling of
    it was a deeper path that does not exist.  A path that resolves outside the tree is
    an escape and fails closed, whichever spelling it arrived in.
    """
    if not raw or not isinstance(raw, str):
        _fail("MISSING_OR_INVALID_PATH_ARGUMENT")
    candidate = Path(raw)
    readings = [candidate] if candidate.is_absolute() else [src_abs / raw, repo / raw]
    resolved = []
    for reading in readings:
        try:
            resolved.append(reading.resolve())
        except OSError:
            continue
    inside = [p for p in resolved if p == src_abs or src_abs in p.parents]
    if must_exist:
        existing = [p for p in inside if p.exists()]
        if existing:
            return existing[0]
        if any(p.exists() for p in resolved):
            _fail("PATH_OUTSIDE_SOURCE_ROOT:" + raw)
        _fail("PATH_MISSING:" + raw)
    if not inside:
        _fail("PATH_OUTSIDE_SOURCE_ROOT:" + raw)
    # A NEW FILE'S PARENT IS THE EVIDENCE.  Both readings can point inside the tree when
    # the caller spells a path relative to the repository, and the tree-relative reading
    # then names a deeper path that cannot be created because its directory does not
    # exist.  Measured: `pkg/canonical/astra_runtime/.../ops.py` won over the correct
    # `pkg/ops.py` and the adapter refused an honest request.  Prefer the reading whose
    # parent directory exists; fall back to the caller's own order.
    creatable = [p for p in inside if p.parent.is_dir()]
    return creatable[0] if creatable else inside[0]


    _fail("PATH_OUTSIDE_SOURCE_ROOT:" + raw)


def _sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _modname_of(rel: str) -> str:
    noext = rel[:-3] if rel.endswith(".py") else rel
    parts = [p for p in noext.split("/") if p != "__init__"]
    return ".".join(parts)


def _module_aliases(module_abs, src_abs, repo, all_py, extra=()):
    """Every dotted name that provably denotes `module_abs`, and no other file.

    `extra` names files that are about to exist.  Without it a NEW target module
    has no owner among the files scanned so far, its package-qualified spelling
    fails the uniqueness test, and the importers are rewritten to the bare stem:
    measured, moving `add` into a new `pkg/ops.py` produced `from ops import add`
    in a file that had written `from pkg.calc import add`.  The file becomes
    correct only after the move, which is exactly when nobody is checking.
    """
    universe = sorted(set(all_py) | {p for p in extra if p is not None})
    names = set()
    for base in (src_abs, src_abs.parent, repo):
        try:
            rel = module_abs.relative_to(base)
        except ValueError:
            continue
        if rel.suffix == ".py":
            names.add(_modname_of(rel.as_posix()))
    unique = set()
    for name in names:
        owners = set()
        for path in universe:
            for base in (src_abs, src_abs.parent, repo):
                try:
                    rel = path.relative_to(base)
                except ValueError:
                    continue
                if rel.suffix == ".py" and _modname_of(rel.as_posix()) == name:
                    owners.add(path)
        if owners == {module_abs}:
            unique.add(name)
    return unique


def _resolve_def(tree, parts):
    nodes = tree.body
    enclosing = None
    for i, part in enumerate(parts):
        found = None
        for nd in nodes:
            if isinstance(nd, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) \
                    and nd.name == part:
                found = nd
                break
            if isinstance(nd, (ast.Assign, ast.AnnAssign)):
                tgts = nd.targets if isinstance(nd, ast.Assign) else [nd.target]
                if any(isinstance(t, ast.Name) and t.id == part for t in tgts):
                    found = nd
                    break
        if found is None:
            return None, None, None
        if i == len(parts) - 1:
            if isinstance(found, (ast.FunctionDef, ast.AsyncFunctionDef)):
                return found, "FUNCTION", enclosing
            if isinstance(found, ast.ClassDef):
                return found, "CLASS", enclosing
            return found, "MODULE_BINDING", enclosing
        enclosing = found
        nodes = getattr(found, "body", [])
    return None, None, None


def _definitions(tree, name: str) -> list:
    """Every module-scope definition of `name` in this module, in source order."""
    out = []
    for nd in tree.body:
        if isinstance(nd, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) \
                and nd.name == name:
            out.append(nd)
        elif isinstance(nd, (ast.Assign, ast.AnnAssign)):
            tgts = nd.targets if isinstance(nd, ast.Assign) else [nd.target]
            if any(isinstance(t, ast.Name) and t.id == name for t in tgts):
                out.append(nd)
    return out


def _uses_name(tree, name: str) -> bool:
    return any(isinstance(nd, ast.Name) and nd.id == name
               and isinstance(nd.ctx, ast.Load) for nd in ast.walk(tree))


def _import_spec(a) -> str:
    return a.name + (" as " + a.asname if getattr(a, "asname", None) else "")


def _import_line_after(lines: list[str]) -> int:
    """Line index (0-based) after the module docstring and the import block."""
    idx = 0
    if lines and lines[0].lstrip().startswith(("\"\"\"", "'''")):
        quote = lines[0].lstrip()[:3]
        if lines[0].count(quote) >= 2 and len(lines[0].strip()) > 3:
            idx = 1
        else:
            idx = 1
            while idx < len(lines) and quote not in lines[idx]:
                idx += 1
            idx += 1
    last_import = idx
    while last_import < len(lines):
        raw = lines[last_import]
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            last_import += 1
            continue
        if stripped.startswith(("import ", "from ")) or raw.startswith((" ", "\t")):
            last_import += 1
            continue
        break
    return last_import


def _cut_span(node, lines: list[str]) -> tuple:
    """(start, end) 0-based line indexes covering decorators through the body."""
    start = min([node.lineno] + [d.lineno for d in getattr(node, "decorator_list", [])]) - 1
    end = node.end_lineno
    return start, end


def run(args, root) -> dict:
    repo = Path(root).resolve()
    args = dict(args or {})
    src_rel = str(args.get("source_root") or "")
    src_abs = _safe_path(repo, src_rel, must_exist=True)
    if not src_abs.is_dir():
        _fail("SOURCE_ROOT_NOT_DIRECTORY")
    module_rel = str(args.get("module") or "")
    target_rel = str(args.get("target_module") or "")
    if not module_rel.endswith(".py"):
        _fail("MODULE_MUST_BE_PY:" + module_rel)
    if not target_rel.endswith(".py"):
        _fail("TARGET_MODULE_MUST_BE_PY:" + target_rel)
    module_abs = _in_tree(repo, src_abs, module_rel, must_exist=True)
    target_abs = _in_tree(repo, src_abs, target_rel)
    module_rel = module_abs.relative_to(src_abs).as_posix()
    target_rel = target_abs.relative_to(src_abs).as_posix()
    if module_abs == target_abs:
        _fail("SAME_MODULE:" + module_rel)
    qualname = str(args.get("qualname") or "").strip()
    if not qualname:
        _fail("SYMBOL_NOT_FOUND:<empty>")
    out_abs = _safe_path(repo, str(args.get("output_path") or ""))
    python_exe = str(args.get("python_executable") or sys.executable)
    timeout_s = int(args.get("timeout_s") or 300)
    # A STATED TEST PATH IS RESOLVED LIKE EVERY OTHER STATED PATH.  The front binder
    # produces repository-relative paths; pytest here runs with cwd=source_root, so an
    # un-normalised path silently selects no tests and the verification gate reports
    # "no tests ran" -- which this adapter correctly treats as red, refusing an edit that
    # was fine.  Measured on the first end-to-end run through solve().
    run_tests = []
    for raw in (args.get("run_tests") or []):
        stated = Path(str(raw))
        candidate = stated if stated.is_absolute() else (src_abs / str(raw))
        candidate = candidate.resolve()
        if not candidate.exists():
            alt = (repo / str(raw)).resolve()
            if alt.exists():
                candidate = alt
        if not candidate.exists():
            _fail("TEST_PATH_MISSING:" + str(raw))
        run_tests.append(candidate.relative_to(src_abs).as_posix()
                         if src_abs in candidate.parents else str(candidate))

    parts = [p for p in qualname.split(".") if p]
    name = parts[-1]

    all_py = sorted(p for p in src_abs.rglob("*.py") if "__pycache__" not in p.parts)
    originals = {p: p.read_bytes() for p in all_py}
    parsed = {}
    for path in all_py:
        rel = path.relative_to(src_abs).as_posix()
        try:
            parsed[path] = ast.parse(originals[path].decode("utf-8"), filename=rel)
        except (SyntaxError, UnicodeDecodeError) as exc:
            _fail("SYNTAX_ERROR_IN_FILE:" + rel + ":" + str(exc))

    tree = parsed[module_abs]
    defs = _definitions(tree, name) if len(parts) == 1 else []
    if not defs:
        node, kind, enclosing = _resolve_def(tree, parts)
        if node is None:
            _fail("SYMBOL_NOT_FOUND:" + qualname)
        if enclosing is not None:
            _fail("SYMBOL_NOT_AT_MODULE_SCOPE:" + qualname)
    else:
        if len(defs) > 1:
            _fail("MULTI_DEFINITION:" + name)
        node, kind, enclosing = defs[0], None, None
        kind = ("FUNCTION" if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                else "CLASS" if isinstance(node, ast.ClassDef) else "MODULE_BINDING")
    if kind != "FUNCTION":
        _fail("SYMBOL_KIND_UNSUPPORTED:" + str(kind))

    src_aliases = _module_aliases(module_abs, src_abs, repo, all_py)
    target_aliases = _module_aliases(target_abs, src_abs, repo, all_py, extra=(target_abs,))
    target_mod = sorted(target_aliases, key=len)[0] if target_aliases else _modname_of(target_rel)
    if target_mod in src_aliases:
        _fail("TARGET_IDENTITY_AMBIGUOUS:" + target_mod)
    if target_abs in parsed:
        existing_defs = _definitions(parsed[target_abs], name)
        if existing_defs:
            _fail("TARGET_ALREADY_DEFINES_SYMBOL:" + target_rel + ":" + name)

    src_lines = originals[module_abs].decode("utf-8").splitlines()
    cut_start, cut_end = _cut_span(node, src_lines)
    moved = src_lines[cut_start:cut_end]
    if not moved or moved[0].startswith((" ", "\t")):
        _fail("SPAN_INTEGRITY:def is not at module scope")

    edits: dict[Path, str] = {}
    injected: list[dict] = []
    unresolved: list[dict] = []

    # ---------------------------------------------------------------- source module
    before, after = src_lines[:cut_start], src_lines[cut_end:]
    # Normalise only the SEAM: the blank lines that separated the moved def from its
    # neighbours.  Nothing else in the file is touched, so the edit stays byte-faithful
    # everywhere the def was not.
    while before and not before[-1].strip():
        before.pop()
    while after and not after[0].strip():
        after.pop(0)
    rest = before + (["", ""] if before and after else []) + after
    text = "\n".join(rest).rstrip("\n") + "\n"
    edits[module_abs] = text
    try:
        rest_tree = ast.parse(text)
    except SyntaxError as exc:
        _fail("SYNTAX_ERROR_AFTER_EDIT:" + module_rel + ":" + str(exc))
    if _uses_name(rest_tree, name):
        lines = text.rstrip("\n").splitlines()
        at = _import_line_after(lines)
        lines.insert(at, "from %s import %s" % (_spell_for(target_abs, module_abs, src_abs, repo, all_py, target_mod), name))
        edits[module_abs] = "\n".join(lines) + "\n"
        injected.append({"file": module_rel, "import": name})

    # ---------------------------------------------------------------- target module
    existing = originals.get(target_abs, b"").decode("utf-8") if target_abs in originals else ""
    block = "\n".join(moved).rstrip("\n") + "\n"
    if existing.strip():
        edits[target_abs] = existing.rstrip("\n") + "\n\n\n" + block
    else:
        edits[target_abs] = block

    # ---------------------------------------------------------------- every importer
    for path, tree_i in parsed.items():
        if path in (module_abs, target_abs):
            continue
        rel = path.relative_to(src_abs).as_posix()
        lines = originals[path].decode("utf-8").splitlines()
        replacements = []  # (first_index, last_index, [new lines]) 0-based, inclusive
        for nd in ast.walk(tree_i):
            if isinstance(nd, ast.ImportFrom) and (nd.module or "") in src_aliases:
                moving = [a for a in nd.names if a.name == name]
                staying = [a for a in nd.names if a.name != name]
                if not moving:
                    continue
                new_mod = _spell_for(target_abs, path, src_abs, repo, all_py, target_mod,
                                     like=nd.module or "")
                moved_line = "from %s import %s" % (
                    new_mod, ", ".join(_import_spec(a) for a in moving))
                if staying:
                    # SPLIT, DO NOT SWAP.  `from pkg.calc import add, sub` binds two names
                    # and only one of them moved; rewriting the module for the whole line
                    # sends `sub` to a module that does not define it.  Measured on the
                    # first build: that is exactly what it did, and only a named test
                    # suite noticed.
                    stay_line = "from %s import %s" % (
                        nd.module or "", ", ".join(_import_spec(a) for a in staying))
                    replacements.append((nd.lineno - 1, nd.end_lineno - 1,
                                         [moved_line, stay_line]))
                else:
                    replacements.append((nd.lineno - 1, nd.end_lineno - 1, [moved_line]))
            elif isinstance(nd, ast.Import):
                for a in nd.names:
                    if a.name not in src_aliases or a.asname is None:
                        continue
                    alias = a.asname
                    attrs = {sub.attr for sub in ast.walk(tree_i)
                             if isinstance(sub, ast.Attribute)
                             and isinstance(sub.value, ast.Name)
                             and sub.value.id == alias}
                    if not attrs:
                        continue
                    if attrs - {name}:
                        unresolved.append({"file": rel, "line": nd.lineno,
                                           "rule": "module alias used for other symbols too",
                                           "alias": alias, "other": sorted(attrs - {name})})
                        continue
                    new_mod = _spell_for(target_abs, path, src_abs, repo, all_py, target_mod,
                                         like=a.name)
                    if len(nd.names) > 1:
                        # a compound `import a, b` keeps its other names in place
                        others = ", ".join(_import_spec(x) for x in nd.names
                                           if x is not a)
                        replacements.append((nd.lineno - 1, nd.end_lineno - 1,
                                             ["import %s" % others,
                                              "import %s as %s" % (new_mod, alias)]))
                    else:
                        replacements.append((nd.lineno - 1, nd.end_lineno - 1,
                                             ["import %s as %s" % (new_mod, alias)]))
        for first, last, new_lines in sorted(replacements, reverse=True):
            lines[first:last + 1] = new_lines
        if replacements:
            edits[path] = "\n".join(lines) + "\n"

    if unresolved:
        _fail("UNSUPPORTED_SHARED_MODULE_IMPORT:" + json.dumps(unresolved, sort_keys=True))

    # A MOVE WHOSE IMPORTERS CANNOT BE PROVEN IS A DELETION.  Every file that loads the
    # name must hold a provable import of it (from the old module or the new one); a file
    # that merely uses the name is a reference this adapter cannot follow, and the edit
    # refuses rather than leaving a NameError behind.
    for path, tree_i in parsed.items():
        if path in (module_abs, target_abs):
            continue
        loads = [nd for nd in ast.walk(tree_i)
                 if isinstance(nd, ast.Name) and nd.id == name]
        if not loads:
            continue
        provable = (
            any(isinstance(sub, ast.ImportFrom)
                and any(a.name == name for a in sub.names)
                and (sub.module or "") in (src_aliases | target_aliases)
                for sub in ast.walk(tree_i))
            or any(isinstance(sub, ast.Import)
                   and any(a.name in src_aliases and a.asname for a in sub.names)
                   for sub in ast.walk(tree_i))
            or _definitions(tree_i, name))
        if not provable:
            unresolved.append({"file": path.relative_to(src_abs).as_posix(),
                               "line": loads[0].lineno,
                               "rule": "name used with no provable import of it"})
    if unresolved:
        _fail("UNPROVABLE_REFERENCE:" + json.dumps(unresolved[:5], sort_keys=True))

    written_before = dict(originals)
    created = [path for path in edits if path not in originals]

    def _restore() -> None:
        """Every original byte back, and every file this run CREATED removed.

        Measured on the first pin run: the rollback restored all pre-existing files and
        left the new `pkg/ops.py` behind, so "restored" was false for the tree as a whole
        -- the next reader would find a module that the refused edit had created.
        """
        for path, raw in written_before.items():
            path.write_bytes(raw)
        for path in created:
            try:
                path.unlink()
            except FileNotFoundError:
                pass

    try:
        for path, text in edits.items():
            path.write_text(text, encoding="utf-8")
        for path in edits:
            tree_after = ast.parse(path.read_text(encoding="utf-8"))
            if path == module_abs and _definitions(tree_after, name):
                # the def must be GONE from where it was moved away from
                _fail("MOVE_LEFT_DEFINITION_BEHIND")
        verified = True
        gate = "PASS_BLIND"
        if run_tests:
            # -p no:cacheprovider: a VERIFICATION run must not write into the tree it is
            # judging.  Measured on the first pin run: the rollback restored every source
            # byte and still left `pkg/.pytest_cache/` behind, so "every byte restored" was
            # false to anyone comparing the tree.
            proc = subprocess.run([python_exe, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                                   *run_tests],
                                  cwd=str(src_abs), capture_output=True, text=True,
                                  timeout=timeout_s)
            if proc.returncode != 0:
                _restore()
                _fail("TESTS_RED_AFTER_EDIT:" + (proc.stdout or "")[-600:])
            gate = "PASS"
    except SystemExit:
        raise
    except Exception:
        _restore()
        raise

    artifact = {
        "adapter": "python_refactor_move_function",
        "capability": CAPABILITY_ID,
        "schema": SCHEMA,
        "module": module_rel,
        "qualname": qualname,
        "symbol_kind": kind,
        "moved_to": target_rel,
        "edit_count": len(edits),
        "moved_line_count": len(moved),
        "files_edited": sorted(p.relative_to(src_abs).as_posix() for p in edits),
        "injected_imports": injected,
        "unresolved_sites": [],
        "gate": gate,
        "complete": True,
        "verified": bool(run_tests) and verified,
        "output_path": str(out_abs.relative_to(repo)),
    }
    raw = json.dumps(artifact, indent=2, sort_keys=True).encode("utf-8")
    out_abs.parent.mkdir(parents=True, exist_ok=True)
    out_abs.write_bytes(raw)
    artifact["output_sha256"] = _sha256(raw)
    artifact["output_verified"] = _sha256(out_abs.read_bytes()) == artifact["output_sha256"]
    return artifact


def _spell_for(target_abs, from_path, src_abs, repo, all_py, target_mod, like: str = "") -> str:
    """How to spell the target module inside `from_path`, reusing the prefix it uses.

    A file that already writes `from pkg.calc import add` must get `from pkg.ops
    import add`, not `from ops import add`: the spelling is a property of the
    importer, and reusing its own prefix keeps the edit a one-token change.  When
    no spelling is shared, the shortest provable alias is used.
    """
    aliases = _module_aliases(target_abs, src_abs, repo, all_py, extra=(target_abs,))
    if not aliases:
        return target_mod
    stem = _modname_of(target_abs.relative_to(src_abs).as_posix()).split(".")[-1]
    if like:
        prefix = like[: -len(like.split(".")[-1])] if "." in like else ""
        candidate = prefix + stem
        if candidate in aliases:
            return candidate
        if "." in like and like.split(".")[-2] == stem:
            return like
    for alias in sorted(aliases, key=len):
        if alias.split(".")[-1] == stem:
            return alias
    return sorted(aliases, key=len)[0]
