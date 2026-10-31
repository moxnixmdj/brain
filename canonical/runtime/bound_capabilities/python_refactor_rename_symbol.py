# PROJECT_BRAIN
"""python.refactor.rename_symbol.v1 — rename ANY def-sited symbol with
provable-binding scope law (function, class, module-level binding, method,
nested function).

``rename_parameter`` renames a binding INSIDE one function; this verb
renames the symbol ITSELF — the def site plus every use that provably
resolves to that binding, across modules — and refuses or reports
everything else.  Nothing textual.  Every edit is an identifier-span byte
splice verified against the original bytes (SPAN_INTEGRITY), applied
offset-sorted per line so formatting and comments survive byte-for-byte.

Symbol classes and their rename law:
* FUNCTION / CLASS / MODULE_BINDING (top level): the def site, in-file
  uses in scopes that do not shadow, and cross-file uses that provably
  import this symbol: ``from m import s [as alias]`` (only the imported
  NAME token is rewritten; an alias stays the alias and its uses are
  untouched) and ``import m`` + ``m.s`` sites.  Dynamic receivers and
  getattr dispatch are listed in ``unknown_sites`` and lower ``complete``.
* METHOD (``Class.method``): the def inside that class body plus
  ``self.m`` / ``cls.m`` / ``C.m`` sites inside the same module.
  ``super().m`` refers to the PARENT method — recorded, never touched.
* NESTED_FUNCTION: file-local rename with the same shadow law.

Refusals: SYMBOL_NOT_FOUND, MULTI_DEFINITION, INVALID_IDENTIFIER,
NEW_NAME_COLLIDES (the replacement binds anywhere in an affected scope,
or is imported-as anywhere), REFUSE_NONLOCAL_OR_GLOBAL (an affected
module declares the old name global/nonlocal),
SYMBOL_KIND_UNSUPPORTED (locals, params, class assignments),
ALIAS_BINDING_SAME_NAME, SPAN_INTEGRITY, TESTS_RED_AFTER_EDIT (named
pytest suite red/timeout/launch failure -> every original byte/mode restored),
SOURCE_CHANGED_AFTER_VERIFICATION (test execution changed candidate/input bytes),
SYNTAX_ERROR_IN_FILE, PATH_*.

Verification law: after edits the named pytest suite runs; red restores
ALL original bytes.  No run_tests named => gate PASS_BLIND,
verified=false loudly.  Determinism: identical worlds -> byte-identical
trees and artifacts.

Replacement identifiers are NFKC-normalized like Python AST bindings before
validation/collision checks; the canonical name is emitted and reported.
Original-source spans retain exact-preimage guards.

Inputs (kwargs, repo-confined):
  source_root        tree to edit IN PLACE (crown worktree convention)
  module             posix path of the defining module, e.g. "pkg/core.py"
  qualname           dotted address: "fib", "Calc", "Calc.add", "THRESHOLD",
                     "outer.inner"
  new_symbol         replacement identifier (isidentifier, not a keyword)
  output_path        summary artifact (registry result_fields mirror)
  run_tests          optional list of pytest-relative test paths to verify
  python_executable  interpreter for verification (default: this one)
  timeout_s          wall-clock cap for the suite call (default 300)

result_fields: adapter, module, qualname, old_symbol, new_symbol,
symbol_kind, edit_count, files_edited, unknown_sites, shadowed_keeps,
gate, complete, output_path, output_sha256, output_verified, verified.
"""

from __future__ import annotations

import ast
import hashlib
import json
import keyword as pykeyword
import stat
import sys
import unicodedata
from pathlib import Path

SCHEMA = "PROJECT_BRAIN_REFACTOR_RENAME_SYMBOL_V1"


def _fail(reason: str) -> None:
    raise SystemExit(json.dumps({"error": True,
                                 "capability": "python.refactor.rename_symbol.v1",
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


def _sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _splice_file(path: Path, b: bytes, edits, new: str) -> bytes:
    """Rewrite exact identifier spans in one file, offset-sorted per line.

    Module level so the splice can be replaced in a test: ``complete`` is a
    measurement over the POST-edit trees, and the only way to prove that
    measurement can fail is to make a splice not land.
    """
    # Match AST byte columns; Unicode separators inside literals are not lines.
    lines = b.splitlines(keepends=True)
    replacement = new.encode("utf-8")
    out_lines = []
    by_line = {}
    for (ln, col, name) in edits:
        by_line.setdefault(ln, []).append((col, name))
    for i, raw in enumerate(lines, start=1):
        if i not in by_line:
            out_lines.append(raw)
            continue
        row = raw
        for col, name in sorted(by_line[i], key=lambda e: e[0],
                                reverse=True):
            token = name.encode("utf-8")
            seg = row[col:col + len(token)]
            if seg != token:
                _fail("SPAN_INTEGRITY:" + f"{path.name}:{i}:{col}")
            # Boundary laws operate on Unicode characters, not single bytes.
            before = row[:col].decode("utf-8")[-1:]
            after = row[col + len(token):].decode("utf-8")[:1]
            if before.isalnum() or before == "_":
                _fail("SPAN_INTEGRITY:left_boundary")
            if after.isalnum() or after == "_":
                _fail("SPAN_INTEGRITY:right_boundary")
            row = row[:col] + replacement + row[col + len(token):]
        out_lines.append(row)
    return b"".join(out_lines)


def _modname_of(rel: str) -> str:
    noext = rel[:-3] if rel.endswith(".py") else rel
    parts = [p for p in noext.split("/") if p != "__init__"]
    return ".".join(parts)


def _module_files(all_py, src_abs) -> dict:
    """dotted module name relative to source_root -> the files spelling it."""
    index: dict = {}
    for path in all_py:
        index.setdefault(_modname_of(path.relative_to(src_abs).as_posix()),
                         set()).add(path)
    return index


def _package_of(path, src_abs) -> str:
    """The dotted package a module's relative imports resolve against."""
    rel = path.relative_to(src_abs).as_posix()
    name = _modname_of(rel)
    if rel.endswith("__init__.py"):
        return name
    return name.rpartition(".")[0]


def _resolve_module(index, module: str, level: int, package: str):
    """Files an import spelling provably denotes, or the empty set.

    ``source_root`` may sit BELOW the import root (``.../app`` while callers
    write ``from app.models import x``), so identity is resolved on dotted
    SEGMENT suffixes, most specific first: ``app.models`` finds ``models.py``
    and ``mymodels`` never does.  ``level`` resolves ``from . import x``.
    """
    if level:
        parts = [p for p in package.split(".") if p]
        name = ".".join([p for p in parts[: len(parts) - (level - 1)]
                         + [module or ""] if p])
    else:
        name = module or ""
    segs = [s for s in name.split(".") if s]
    for i in range(len(segs)):
        hit = index.get(".".join(segs[i:]))
        if hit:
            return hit
    return frozenset()


def _params_of(fn):
    a = fn.args
    out = list(a.posonlyargs) + list(a.args) + list(a.kwonlyargs)
    for extra in (a.vararg, a.kwarg):
        if extra is not None:
            out.append(extra)
    return out


def _binds_name(node, name: str) -> bool:
    """True if nested scope `node` binds `name` as one of ITS OWN locals."""
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
        if any(p.arg == name for p in _params_of(node)):
            return True
    targets = []
    for sub in ast.iter_child_nodes(node):
        if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda,
                            ast.ClassDef)):
            continue
        if isinstance(sub, ast.Assign):
            targets += sub.targets
        elif isinstance(sub, (ast.AnnAssign, ast.AugAssign)):
            targets.append(sub.target)
        elif isinstance(sub, (ast.For, ast.AsyncFor)):
            targets.append(sub.target)
        elif isinstance(sub, ast.comprehension):
            targets.append(sub.target)
    for t in targets:
        for n in ast.walk(t):
            if isinstance(n, ast.Name) and n.id == name:
                return True
    return False


def _def_targets(node, name: str) -> bool:
    tgts = []
    if isinstance(node, ast.Assign):
        tgts = node.targets
    elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
        tgts = [node.target]
    for t in tgts:
        for n in ast.walk(t):
            if isinstance(n, ast.Name) and n.id == name:
                return True
    return False


def _resolve_def(tree, parts: list[str]):
    """Follow the qualname. Return (node, kind, enclosing_class_or_None)."""
    nodes = tree.body
    owner_class = None
    target = None
    for idx, seg in enumerate(parts):
        hit_fn = [n for n in nodes if isinstance(
            n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == seg]
        hit_cls = [n for n in nodes if isinstance(n, ast.ClassDef)
                   and n.name == seg]
        hit_assign = [n for n in nodes if isinstance(n, (ast.Assign, ast.AnnAssign))
                      and _def_targets(n, seg)]
        hits = hit_fn + hit_cls + hit_assign
        if not hits:
            _fail("SYMBOL_NOT_FOUND:" + ".".join(parts[:idx + 1]))
        if len(hits) > 1:
            _fail("MULTI_DEFINITION:" + ".".join(parts[:idx + 1]))
        target = hits[0]
        if idx == len(parts) - 1:
            if target in hit_fn:
                if owner_class is not None:
                    kind = "METHOD"
                elif len(parts) >= 2:
                    kind = "NESTED_FUNCTION"
                else:
                    kind = "FUNCTION"
            elif target in hit_cls:
                kind = "CLASS"
            else:
                if len(parts) > 1:
                    _fail("SYMBOL_KIND_UNSUPPORTED:local_or_nested_binding")
                kind = "MODULE_BINDING"
            return target, kind, owner_class
        # descend
        if target in hit_cls:
            owner_class = target
        if not hasattr(target, "body"):
            _fail("QUALNAME_NOT_A_SCOPE:" + ".".join(parts[:idx + 1]))
        nodes = target.body
    _fail("SYMBOL_NOT_FOUND:" + ".".join(parts))


def _import_table(tree):
    """localalias -> (module, imported_name|None, relative_level)."""
    binding = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                binding[a.asname or a.name.split(".")[0]] = (a.name, None, 0)
        elif isinstance(node, ast.ImportFrom):
            for a in node.names:
                binding[a.asname or a.name] = (node.module or "", a.name,
                                               int(node.level or 0))
    return binding


def _collect_edits_in_scope(node, old: str, new: str, edits: list,
                            shadowed: list, collisions: list):
    """Every Name(old) reference (Load/Store/Del) whose scope resolves it to
    the outer binding, respecting lexical shadowing; simultaneous Load of
    `new` inside those same scopes is a collision."""
    def process(nd, top=False):
        if isinstance(nd, (ast.FunctionDef, ast.AsyncFunctionDef,
                           ast.Lambda)) and not top:
            if _binds_name(nd, old) or _binds_name(nd, new):
                shadowed.append({"line": nd.lineno,
                                 "scope": getattr(nd, "name", "<lambda>"),
                                 "rule": "nested scope binds old or new name"})
                if _binds_name(nd, new):
                    collisions.append(nd.lineno)
                return
        elif isinstance(nd, ast.ClassDef) and not top:
            if _binds_name(nd, new):
                collisions.append(nd.lineno)
        elif isinstance(nd, ast.Name) and nd.id == old:
            # any reference context (Load/Store/Del) = the same binding here
            edits.append((nd.lineno, nd.col_offset, old))
            return
        elif isinstance(nd, ast.Name) and nd.id == new:
            collisions.append(nd.lineno)
        for child in ast.iter_child_nodes(nd):
            process(child)
    process(node, top=True)


def _name_col(line_text: str, keyword: str, name: str) -> int:
    """UTF-8 byte column of `name`: search text, then match AST coordinates."""
    idx = line_text.find(keyword)
    if idx < 0:
        _fail("SPAN_INTEGRITY:keyword:" + keyword)
    col = line_text.find(name, idx + len(keyword) + 1)
    if col < 0:
        _fail("SPAN_INTEGRITY:name_span")
    return len(line_text[:col].encode("utf-8"))


def run(args, root):
    repo = Path(root).resolve()
    args = dict(args or {})

    src_rel = str(args.get("source_root") or "")
    src_abs = _safe_path(repo, src_rel, must_exist=True)
    if not src_abs.is_dir():
        _fail("SOURCE_ROOT_NOT_DIRECTORY")
    module_rel = str(args.get("module") or "")
    module_abs = _safe_path(src_abs, module_rel, must_exist=True)
    if not module_rel.endswith(".py"):
        _fail("MODULE_MUST_BE_PY")
    qualname = str(args.get("qualname") or "").strip()
    if not qualname:
        _fail("SYMBOL_NOT_FOUND:<empty>")
    # Match Python AST binding names before keyword and collision checks.
    new = unicodedata.normalize("NFKC", str(args.get("new_symbol") or ""))
    if not new.isidentifier() or pykeyword.iskeyword(new):
        _fail("INVALID_IDENTIFIER:new_symbol")
    out_rel = str(args.get("output_path") or "")
    out_abs = _safe_path(repo, out_rel)
    python_exe = str(args.get("python_executable") or sys.executable)
    timeout_s = int(args.get("timeout_s") or 300)
    run_tests = list(args.get("run_tests") or [])

    parts = [p for p in qualname.split(".") if p]
    old = parts[-1]
    all_py = sorted(p for p in src_abs.rglob("*.py")
                    if "__pycache__" not in p.parts)
    mod_files = _module_files(all_py, src_abs)
    originals = {p: p.read_bytes() for p in all_py}
    modes = {p: stat.S_IMODE(p.stat().st_mode) for p in all_py}
    from canonical.runtime.write_authority_v1 import check_report
    check_report(repo, out_abs, originals)
    parsed = {}
    for path in all_py:
        rel = path.relative_to(src_abs).as_posix()
        try:
            parsed[path] = ast.parse(originals[path].decode("utf-8"),
                                     filename=rel)
        except (SyntaxError, UnicodeDecodeError) as exc:
            _fail("SYNTAX_ERROR_IN_FILE:" + rel + ":" + str(exc))

    target_tree = parsed[module_abs]
    def_node, kind, enclosing_cls = _resolve_def(target_tree, parts)
    cross = kind in ("FUNCTION", "CLASS", "MODULE_BINDING")

    if kind == "METHOD":
        # Inheritance law: a base-class method rename silently breaks any
        # subclass that (a) overrides the same method (super().old now
        # dangles) or (b) inherits-and-calls self.old through the base.
        # Refuse loudly instead of breaking behavior.
        base_names = []
        for nd in ast.walk(target_tree):
            if isinstance(nd, ast.ClassDef):
                for b in nd.bases:
                    if isinstance(b, ast.Name) and b.id == parts[-2]:
                        base_names.append(nd.name)
        for nd in ast.walk(target_tree):
            if isinstance(nd, ast.ClassDef) and nd.name in base_names:
                for sub in nd.body:
                    if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                            and sub.name == old:
                        _fail("REFUSE_INHERITED_OVERRIDE:" + nd.name
                              + "." + old)
                for attr in ast.walk(nd):
                    if isinstance(attr, ast.Attribute) and attr.attr == old \
                            and isinstance(attr.value, ast.Name) \
                            and attr.value.id == "self":
                        _fail("REFUSE_INHERITED_USE:" + nd.name
                              + " self." + old)
    cls_name = parts[-2] if kind == "METHOD" else None
    # module-level collisions in the defining module
    if kind in ("FUNCTION", "CLASS", "MODULE_BINDING"):
        for nd in target_tree.body:
            if isinstance(nd, (ast.FunctionDef, ast.AsyncFunctionDef,
                               ast.ClassDef)) and nd.name == new:
                _fail("NEW_NAME_COLLIDES:" + new + " (def)")
            if isinstance(nd, (ast.Assign, ast.AnnAssign)) and \
                    _def_targets(nd, new):
                _fail("NEW_NAME_COLLIDES:" + new + " (module binding)")
        if new in _import_table(target_tree):
            _fail("NEW_NAME_COLLIDES:" + new + " (import alias)")
    if kind == "METHOD" and enclosing_cls is not None:
        for nd in enclosing_cls.body:
            if isinstance(nd, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                    and nd.name == new:
                _fail("NEW_NAME_COLLIDES:" + new + " (method)")

    per_file_edits: dict = {}
    unknown_sites = []
    shadowed_keeps = []
    collisions = []

    # ---------------------------------------------------------- refusal scan
    # global/nonlocal on the old name anywhere it could rebind our edits
    for path, tree in parsed.items():
        if not cross and path != module_abs:
            continue
        for nd in ast.walk(tree):
            if isinstance(nd, (ast.Global, ast.Nonlocal)) and old in nd.names:
                rel = path.relative_to(src_abs).as_posix()
                _fail("REFUSE_NONLOCAL_OR_GLOBAL:" + old + " in " + rel)

    # ---------------------------------------------------------- edit harvest
    def _targets(module, level, package):
        """True when an import spelling provably denotes OUR module file."""
        return module_abs in _resolve_module(mod_files, module, level, package)

    def _cross_sites(tree, package, bindings, lines, rel, *,
                     check_new_alias_collisions=True):
        """Provable cross-module references to the old symbol in one file.

        File identity (never a dotted-string guess) decides what is ours, so
        the same function is both the harvest and the post-edit residual
        measurement: after the splice it must find NOTHING.
        """
        edits, unknown = [], []
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id == old:
                hit = bindings.get(old)
                if hit and hit[1] == old and _targets(hit[0], hit[2], package):
                    edits.append((node.lineno, node.col_offset, old))
            elif isinstance(node, ast.Attribute) and node.attr == old:
                v = node.value
                if isinstance(v, ast.Name):
                    hit = bindings.get(v.id)
                    if hit and hit[1] is None and _targets(hit[0], hit[2],
                                                           package):
                        # import M [as alias]; alias.old(...)
                        edits.append((node.lineno,
                                      node.col_offset + len(v.id.encode("utf-8")) + 1, old))
                    elif hit and hit[1] is not None and _targets(
                            (hit[0] + "." if hit[0] else "") + hit[1],
                            hit[2], package):
                        # from PKG import M; M.old(...) — M is our module
                        edits.append((node.lineno,
                                      node.col_offset + len(v.id.encode("utf-8")) + 1, old))
                    elif not hit:
                        unknown.append({"file": rel, "line": node.lineno,
                                        "rule": "unresolvable module receiver"})
        # the import lines themselves (rewrite the imported NAME token)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and _targets(
                    node.module or "", int(node.level or 0), package):
                for a in node.names:
                    if a.name == old and a.asname is None:
                        ln = node.lineno
                        col = _name_col(lines[ln - 1], "import", old)
                        edits.append((ln, col, old))
                    elif a.name == old and a.asname == old:
                        _fail("ALIAS_BINDING_SAME_NAME:" + str(node.lineno))
                    elif (check_new_alias_collisions and a.asname == new
                          and a.name != old):
                        # another symbol imported AS the new name: after the
                        # rename this module binds `new` to something else
                        # while edited uses spell `new` for ours.
                        _fail("NEW_NAME_COLLIDES:" + new + " (import alias)")
                    elif a.name == old and a.asname == new:
                        # `from m import old as new`: after renaming the name
                        # token the alias spells `new as new` and still
                        # resolves to this symbol — legal, allow.
                        ln = node.lineno
                        col = _name_col(lines[ln - 1], "import", old)
                        edits.append((ln, col, old))
                    elif a.name == old and a.asname:
                        # `from m import old as x`: alias x stays x.
                        ln = node.lineno
                        col = _name_col(lines[ln - 1], "import", old)
                        edits.append((ln, col, old))
        return edits, unknown

    def_node_line = None
    for path, tree in parsed.items():
        rel = path.relative_to(src_abs).as_posix()
        edits = []
        bindings = _import_table(tree)
        package = _package_of(path, src_abs)
        lines = [line.decode("utf-8") for line in originals[path].splitlines()]

        if path == module_abs:
            # def site (name span resolved from the source line)
            ln = def_node.lineno
            if kind == "MODULE_BINDING":
                # Assign/AnnAssign: the target Name node carries the span
                tgts = [nd for nd in ast.walk(def_node)
                        if isinstance(nd, ast.Name) and nd.id == old
                        and isinstance(nd.ctx, (ast.Store, ast.AugStore))]
                if tgts:
                    edits.append((tgts[0].lineno, tgts[0].col_offset, old))
                else:
                    edits.append((ln, _name_col(lines[ln - 1], old, old), old))
            else:
                kw = "class" if kind == "CLASS" else "def"
                edits.append((ln, _name_col(lines[ln - 1], kw, old), old))
            if kind == "METHOD" and enclosing_cls is not None:
                for nd in ast.walk(enclosing_cls):
                    if isinstance(nd, ast.Attribute) and nd.attr == old:
                        v = nd.value
                        if isinstance(v, ast.Name) and v.id in (
                                "self", "cls", cls_name):
                            # self.m / cls.m / Meter.m inside Meter's body all
                            # resolve to THIS method
                            edits.append((nd.lineno, nd.col_offset
                                          + len(v.id.encode("utf-8")) + 1, old))
                        elif isinstance(v, ast.Call) and isinstance(
                                v.func, ast.Name) and v.func.id == "super":
                            unknown_sites.append(
                                {"file": rel, "line": nd.lineno,
                                 "rule": "super() resolves to the parent method"})
                        elif isinstance(v, ast.Name) and v.id == cls_name:
                            pass  # handled above
                        else:
                            unknown_sites.append(
                                {"file": rel, "line": nd.lineno,
                                 "rule": "unattributable attribute receiver"})
                if cls_name:
                    for nd in ast.walk(tree):
                        if isinstance(nd, ast.Attribute) and nd.attr == old \
                                and isinstance(nd.value, ast.Name) \
                                and nd.value.id == cls_name:
                            edits.append((nd.lineno, nd.col_offset
                                          + len(cls_name.encode("utf-8")) + 1, old))
            else:
                scope = ast.Module(body=tree.body, type_ignores=[])
                _collect_edits_in_scope(scope, old, new, edits,
                                        shadowed_keeps, collisions)
                # the def-name edit itself was already recorded; dedupe later
        elif cross:
            ce, cu = _cross_sites(tree, package, bindings, lines, rel)
            edits.extend(ce)
            unknown_sites.extend(cu)
        # getattr dynamic dispatch (any file)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                    and node.func.id == "getattr" and len(node.args) >= 2 \
                    and isinstance(node.args[1], ast.Constant) \
                    and node.args[1].value == old:
                unknown_sites.append({"file": rel, "line": node.lineno,
                                      "rule": "getattr dynamic dispatch"})
        if edits:
            per_file_edits[path] = sorted(set(edits),
                                          key=lambda e: (e[0], e[1],
                                                         -len(e[2])))

    if collisions:
        _fail("NEW_NAME_COLLIDES:" + new)
    if not per_file_edits:
        _fail("SYMBOL_NOT_FOUND:no_editable_sites")

    applied = {}
    for path, edits in per_file_edits.items():
        after = _splice_file(path, originals[path], edits, new)
        try:
            ast.parse(after.decode("utf-8"), filename=path.name)
        except SyntaxError as exc:
            _fail("SYNTAX_ERROR_AFTER_EDIT:" + str(exc))
        applied[path] = after

    # ------------------------------------------------ residual law (pre-write)
    # `complete` is a claim about the WHOLE tree, so measure it: re-run the
    # harvest over the post-edit trees and refuse if it still finds a provable
    # reference.  Without this an import spelling the harvest mis-resolved
    # would be reported "complete" and silently left stale.
    post = dict(parsed)
    for path, b in applied.items():
        post[path] = ast.parse(b.decode("utf-8"), filename=str(path))
    residual = []
    # Collision preconditions were checked on the original trees. A generated
    # `from m import new as new` is not a pre-existing competing binding.
    # Reuse the same reference harvest here, without reapplying that precondition.
    for path, tree in post.items():
        if path == module_abs:
            continue        # same-file law incl. shadowed keeps: see harvest
        lines = [line.decode("utf-8") for line in
                 (applied.get(path) or originals[path]).splitlines()]
        re_edits, _ = _cross_sites(tree, _package_of(path, src_abs),
                                   _import_table(tree), lines,
                                   path.relative_to(src_abs).as_posix(),
                                   check_new_alias_collisions=False)
        residual.extend((path.relative_to(src_abs).as_posix(), ln)
                        for ln, _col, _name in re_edits)
    if residual:
        residual.sort()
        _fail("RESIDUAL_REFERENCE:" + ",".join(
            f"{f}:{ln}" for f, ln in residual[:8]))

    # Reuse native delivery's owned publication, bounded process lifecycle,
    # exact restoration and bytecode invalidation instead of a second executor.
    from canonical.runtime.bound_capabilities import python_repair_apply_verified_v1 as delivery

    try:
        for path, b in applied.items():
            delivery._atomic_write(path, b, mode=modes[path])
            delivery._REPAIR._PATCH._purge_source_bytecode(path)

        gate = "PASS"
        verified = bool(run_tests)
        if run_tests:
            rc, output = delivery._run_test(
                [python_exe, "-m", "pytest", "-q", "-p", "no:cacheprovider"]
                + run_tests, src_abs, timeout_s)
            if rc != 0:
                tail = "\n".join(output.decode("utf-8", errors="replace")
                                 .strip().splitlines()[-6:])
                _fail("TESTS_RED_AFTER_EDIT:" + tail)
        else:
            gate = "PASS_BLIND"

        changed = [p.relative_to(src_abs).as_posix() for p, original in originals.items()
                   if not delivery._source_matches(p, applied.get(p, original), modes[p])]
        if changed:
            _fail("SOURCE_CHANGED_AFTER_VERIFICATION:" + ",".join(changed))

        unknown_sites.sort(key=lambda r: (r["file"], r["line"]))
        complete = not unknown_sites
        seen_shadows = {}
        for s in shadowed_keeps:
            seen_shadows.setdefault((s["line"], s["scope"], s["rule"]), s)
        shadowed_rows = [seen_shadows[k] for k in sorted(seen_shadows)]
        out = {
            "schema": SCHEMA,
            "adapter": "python_refactor_rename_symbol",
            "capability": "python.refactor.rename_symbol.v1",
            "module": module_rel,
            "qualname": qualname,
            "old_symbol": old,
            "new_symbol": new,
            "symbol_kind": kind,
            "edit_count": sum(len(v) for v in per_file_edits.values()),
            "files_edited": sorted(p.relative_to(src_abs).as_posix()
                                   for p in applied),
            "unknown_sites": unknown_sites,
            "shadowed_keeps": shadowed_rows,
            "gate": gate,
            "complete": complete,
            "output_verified": True,
            "verified": verified,
        }
        out_abs.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(out, indent=1, sort_keys=True, default=list) + "\n"
        report_mode = stat.S_IMODE(out_abs.stat().st_mode) if out_abs.is_file() else 0o644
        final = dict(out)
        final["output_path"] = out_rel
        final["output_sha256"] = _sha256(payload.encode("utf-8"))
        delivery._atomic_write(out_abs, payload.encode("utf-8"), mode=report_mode)
    except BaseException:
        delivery._restore_sources(originals, modes)
        raise
    print(json.dumps(final, indent=1, sort_keys=True, default=list))
    return final
