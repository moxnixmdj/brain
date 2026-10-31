# PROJECT_BRAIN
"""python.refactor.rename_parameter.v1 — scope-aware parameter rename with
cross-file call-site propagation.

The crown can rename SYMBOLS (choreograph) but not PARAMETERS: a param
rename must rewrite the definition, the function body (with true lexical
scoping), and every *call site that spells the old keyword* — across
modules, through ``from m import f``, ``import m``, ``import m as a``,
and ``from pkg import mod`` forms — while leaving positional calls
untouched and never silently dropping a site it cannot resolve.

Scope law (the part that makes it right, not just fast):
* the param is a binding of the target function's scope; nested
  functions/lambdas/classes that BIND the same name (their own param,
  an assignment target, a comprehension variable) SHADOW it — the walk
  records those as ``shadowed_keep`` evidence and never edits them.
* ``global``/``nonlocal`` mentions of the param name anywhere inside the
  target body hard-refuse (REFUSE_NONLOCAL_OR_GLOBAL) — renaming would
  change semantic truth beyond AST scope resolution.
* call sites whose receiver resolves only dynamically (``obj.fib(...)``)
  are listed as ``unknown_receiver`` and lower ``complete`` — complete
  is true only when zero unresolved sites remain (choreograph's law).
* every splice verifies the bytes it replaces (SPAN_INTEGRITY); editing
  is offset-sorted single-pass per file, so formatting/comments are
  preserved byte-for-byte outside the spliced identifiers.

Verification law: after edits, the named tests run (run_tests) — on red,
ALL file bytes are restored and the adapter refuses
TESTS_RED_AFTER_EDIT with the failing pytest tail as evidence.  A rename
that cannot prove green is not a rename.

Replacement identifiers are NFKC-normalized like Python AST bindings before
validation/collision checks; the canonical name is emitted and reported.
Original-source spans retain exact-preimage guards. Compiler symbol tables
refuse replacement capture in the target scope and nested scopes where the old
parameter is free; unrelated nested bindings do not block the rename.

Inputs (kwargs, repo-confined):
  source_root      tree to edit IN PLACE (crown worktree convention)
  module           posix path of the defining module, e.g. "pkg/core.py"
  qualname         function name or dotted path, e.g. "fib" or "C.m"
  old_param        parameter name to replace
  new_param        replacement (must be a valid identifier)
  output_path      summary artifact (registry result_fields mirror)
  run_tests        optional list of pytest-relative test paths to verify
  python_executable interpreter for verification (default: this one)
  timeout_s        wall-clock cap for the suite call (default 300)

result_fields: adapter, module, qualname, old_param, new_param,
edit_count, files_edited, unknown_sites, shadowed_keeps, gate, complete,
output_path, output_sha256, output_verified, verified.
"""

from __future__ import annotations

import ast
import hashlib
import json
import keyword as pykeyword
import stat
import sys
import symtable
import unicodedata
from pathlib import Path

SCHEMA = "PROJECT_BRAIN_REFACTOR_RENAME_PARAMETER_V1"


def _fail(reason: str) -> None:
    raise SystemExit(json.dumps({"error": True,
                                 "capability": "python.refactor.rename_parameter.v1",
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


def _modname_of(rel: str) -> str:
    noext = rel[:-3] if rel.endswith(".py") else rel
    parts = [p for p in noext.split("/") if p != "__init__"]
    return ".".join(parts)


def _params_of(fn) -> list:
    a = fn.args
    out = list(a.posonlyargs) + list(a.args) + list(a.kwonlyargs)
    for extra in (a.vararg, a.kwarg):
        if extra is not None:
            out.append(extra)
    return out


def _binds_name(node, name: str) -> bool:
    """True if `node` (a nested scope) binds `name` as one of ITS OWN locals."""
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
        if any(p.arg == name for p in _params_of(node)):
            return True
    # assignments/bindings at the FIRST level of the scope (not nested scopes)
    targets = []
    for sub in ast.iter_child_nodes(node):
        if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda,
                            ast.ClassDef)):
            continue
        if isinstance(sub, ast.Assign):
            targets += sub.targets
        elif isinstance(sub, (ast.AnnAssign, ast.AugAssign)):
            targets.append(sub.target)
        elif isinstance(sub, (ast.For, ast.AsyncFor, ast.With, ast.AsyncWith)):
            if isinstance(sub, (ast.For, ast.AsyncFor)):
                targets.append(sub.target)
        elif isinstance(sub, ast.comprehension):
            targets.append(sub.target)
    for t in targets:
        for n in ast.walk(t):
            if isinstance(n, ast.Name) and n.id == name:
                return True
    return False


def _refuse_replacement_capture(raw: bytes, path: Path, fn, old: str, new: str) -> None:
    """Reuse Python's compiler scopes, not a second binding classifier.

    Any existing use/binding of the new name in the target could be shadowed.
    Descend only where the old parameter is free: an unrelated nested scope,
    or one with its own old parameter, must not block a safe outer rename.
    """
    try:
        module = symtable.symtable(raw.decode("utf-8"), str(path), "exec")
    except SyntaxError as exc:
        _fail("SYNTAX_ERROR_IN_FILE:" + str(path) + ":" + str(exc))
    pending = [module]
    matches = []
    while pending:
        scope = pending.pop()
        if scope.get_name() == fn.name and scope.get_lineno() == fn.lineno:
            matches.append(scope)
        pending.extend(scope.get_children())
    if len(matches) != 1:
        _fail("PARAMETER_SCOPE_NOT_UNIQUE:" + fn.name)
    target = matches[0]
    if new in target.get_identifiers():
        _fail("NEW_PARAM_NAME_CAPTURED:" + new + ":" + target.get_name())
    pending = list(target.get_children())
    while pending:
        scope = pending.pop()
        if old not in scope.get_identifiers() or not scope.lookup(old).is_free():
            continue
        if new in scope.get_identifiers():
            _fail("NEW_PARAM_NAME_CAPTURED:" + new + ":" + scope.get_name())
        pending.extend(scope.get_children())


def _collect_body_renames(fn, name: str, new: str, shadowed: list) -> list:
    """rename-edits for Name(`name`, Load) inside fn's body respecting scoping."""
    edits = []

    def process(node):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node is fn:
                for child in fn.body:
                    process(child)
                return
            if _binds_name(node, name):
                shadowed.append({"line": node.lineno,
                                 "scope": getattr(node, "name", "<lambda>"),
                                 "rule": "same-name binding shadowed the rename"})
                return
            for child in ast.iter_child_nodes(node):
                process(child)
            return
        if isinstance(node, ast.Lambda):
            if _binds_name(node, name):
                shadowed.append({"line": node.lineno, "scope": "<lambda>",
                                 "rule": "lambda binds the name"})
                return
            for child in ast.iter_child_nodes(node):
                process(child)
            return
        if isinstance(node, ast.ClassDef):
            shadowed.append({"line": node.lineno, "scope": node.name,
                             "rule": "class body is its own scope"})
            return
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) \
                and node.id == name:
            edits.append((node.lineno, node.col_offset, name))
        for child in ast.iter_child_nodes(node):
            process(child)

    for stmt in fn.body:
        process(stmt)
    return edits


def _module_callsites(tree, target_mod: str, target_sym: str,
                      old: str, is_same_module: bool):
    """Return (edits, unknown_rows, positional_count) of keyword call-site
    renames (kw.arg == old) to calls resolving to (target_mod, target_sym)."""
    # import tables
    binding = {}       # localalias -> (module, attr)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                binding[a.asname or a.name.split(".")[0]] = (a.name, None)
        elif isinstance(node, ast.ImportFrom):
            for a in node.names:
                binding[a.asname or a.name] = (node.module or "", a.name)

    def resolves(func) -> bool:
        if isinstance(func, ast.Name):
            if is_same_module and func.id == target_sym and func.id not in binding:
                return True
            hit = binding.get(func.id)
            return bool(hit and hit == (target_mod, target_sym))
        if isinstance(func, ast.Attribute):
            v = func.value
            if isinstance(v, ast.Name):
                hit = binding.get(v.id)
                # import pkg.core [as c]; from pkg import core
                return bool(hit and hit[0] == target_mod and
                            (hit[1] is None or hit[1] == target_mod.split(".")[-1]) and
                            func.attr == target_sym)
        return False

    def unknown_receiver(func) -> bool:
        return isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) \
            and func.attr == target_sym and not resolves(func)

    def dynamic_getattr(func) -> bool:
        """getattr(x, "<target_sym>")(...) — the receiver resolves at runtime."""
        return isinstance(func, ast.Call) and isinstance(func.func, ast.Name) \
            and func.func.id == "getattr" and len(func.args) >= 2 \
            and isinstance(func.args[1], ast.Constant) \
            and func.args[1].value == target_sym

    edits, unknown, positional = [], [], 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if resolves(node.func):
                if not node.keywords:
                    positional += 1
                for kw in node.keywords:
                    if kw.arg == old:
                        edits.append((kw.lineno, kw.col_offset, old))
                    elif kw.arg is None:  # **kwargs passthrough
                        unknown.append({"line": node.lineno,
                                        "rule": "star-star kwargs passthrough"})
            elif unknown_receiver(node.func):
                unknown.append({"line": node.lineno,
                                "rule": "dynamic receiver, unresolvable module"})
            elif dynamic_getattr(node.func):
                unknown.append({"line": node.lineno,
                                "rule": "getattr dynamic dispatch"})
    return edits, unknown, positional


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
    qualname = str(args.get("qualname") or "")
    old = str(args.get("old_param") or "")
    # Match Python AST binding names before keyword and collision checks.
    new = unicodedata.normalize("NFKC", str(args.get("new_param") or ""))
    for nm, label in ((new, "new_param"),):
        if not nm.isidentifier() or pykeyword.iskeyword(nm):
            _fail("INVALID_IDENTIFIER:" + label)
    out_rel = str(args.get("output_path") or "")
    out_abs = _safe_path(repo, out_rel)
    python_exe = str(args.get("python_executable") or sys.executable)
    timeout_s = int(args.get("timeout_s") or 300)
    run_tests = list(args.get("run_tests") or [])

    target_mod = _modname_of(module_rel)
    parts = qualname.split(".")

    all_py = sorted(p for p in src_abs.rglob("*.py") if "__pycache__" not in p.parts)
    originals = {p: p.read_bytes() for p in all_py}
    modes = {p: stat.S_IMODE(p.stat().st_mode) for p in all_py}
    from canonical.runtime.write_authority_v1 import check_report
    check_report(repo, out_abs, originals)

    per_file_edits = {}
    unknown_sites = []
    shadowed_keeps = []
    positional_untouched = 0
    found_defs = 0

    for path in all_py:
        rel = path.relative_to(src_abs).as_posix()
        try:
            tree = ast.parse(originals[path].decode("utf-8"), filename=rel)
        except (SyntaxError, UnicodeDecodeError) as exc:
            _fail("SYNTAX_ERROR_IN_FILE:" + rel + ":" + str(exc))
        this_mod = _modname_of(rel)
        edits = []
        # def site + body (target module only)
        if this_mod == target_mod:
            scope = tree.body
            fn = None
            cursor = parts
            nodes = tree.body
            while cursor:
                head, cursor = cursor[0], cursor[1:]
                hit = [n for n in nodes
                       if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                       and getattr(n, "name", None) == head]
                if not hit:
                    fn = None
                    break
                fn = hit[0]
                found_defs += len(hit)
                if len(hit) > 1:
                    _fail("MULTI_DEFINITION:" + qualname)
                nodes = fn.body
            if fn and isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                params = _params_of(fn)
                names = [p.arg for p in params]
                if old not in names:
                    _fail("PARAM_NOT_FOUND:" + old + " on " + qualname)
                if new in names:
                    _fail("NEW_PARAM_ALREADY_PRESENT:" + new)
                for d in ast.walk(fn):
                    if isinstance(d, (ast.Global, ast.Nonlocal)) and old in d.names:
                        _fail("REFUSE_NONLOCAL_OR_GLOBAL:" + old)
                _refuse_replacement_capture(originals[path], path, fn, old, new)
                target_arg = next(p for p in params if p.arg == old)
                edits.append((target_arg.lineno, target_arg.col_offset, old, new))
                edits += [(ln, col, o, n) for (ln, col, o) in
                          _collect_body_renames(fn, old, new, shadowed_keeps)
                          for n in (new,)]
        # call sites everywhere
        e2, unk, posc = _module_callsites(tree, target_mod, parts[-1],
                                          old, this_mod == target_mod)
        edits += [(ln, col, o, new) for (ln, col, o) in e2]
        for u in unk:
            unknown_sites.append({"file": rel, **u})
        positional_untouched += posc
        if edits:
            per_file_edits[path] = edits

    if found_defs == 0:
        _fail("SYMBOL_NOT_FOUND:" + qualname + " in " + module_rel)
    if found_defs > 1:
        _fail("MULTI_DEFINITION:" + qualname)

    complete = len(unknown_sites) == 0

    # Validate every splice before publishing any file.
    applied = {}
    files_edited = sorted(p.relative_to(src_abs).as_posix() for p in per_file_edits)
    edit_rows = []
    for path, edits in per_file_edits.items():
        rel = path.relative_to(src_abs).as_posix()
        # AST columns are UTF-8 byte offsets, as in patch-search _byte_offset.
        # Keep the existing prefix table to avoid rescanning lines per edit.
        data = originals[path]
        pos_map = [0]
        for ln in data.splitlines(keepends=True):
            pos_map.append(pos_map[-1] + len(ln))
        for lineno, col, old_t, new_t in sorted(edits, key=lambda e: (e[0], e[1]), reverse=True):
            off = pos_map[lineno - 1] + col
            old_bytes, new_bytes = old_t.encode("utf-8"), new_t.encode("utf-8")
            if data[off:off + len(old_bytes)] != old_bytes:
                _fail("SPAN_INTEGRITY:" + rel + ":" + str(lineno) + ":" + str(col))
            data = data[:off] + new_bytes + data[off + len(old_bytes):]
            edit_rows.append({"file": rel, "line": lineno, "from": old_t, "to": new_t})
        applied[path] = data

    # Reuse native delivery rather than creating another publication/runner law.
    from canonical.runtime.bound_capabilities import python_repair_apply_verified_v1 as delivery
    try:
        for path, data in applied.items():
            delivery._atomic_write(path, data, mode=modes[path])
            delivery._REPAIR._PATCH._purge_source_bytecode(path)

        evidence = {"run_tests": run_tests}
        gate = "PASS"
        verified = False
        if run_tests:
            proc = delivery._REPAIR._PATCH._run_tests(
                src_abs, [python_exe, "-m", "pytest", "-q", "-p", "no:cacheprovider"]
                + run_tests, timeout_s, extra_env={"PYTHONDONTWRITEBYTECODE": "1"})
            if proc["timed_out"]:
                _fail("TIMEOUT:edits fully rolled back")
            evidence["pytest_rc"] = proc["returncode"]
            evidence["pytest_tail"] = proc["stdout"].strip().splitlines()[-3:]
            if proc["returncode"] != 0:
                _fail("TESTS_RED_AFTER_EDIT:edits fully rolled back:" +
                      ";".join((proc["stdout"].strip().splitlines() or ["<no output>"])[-2:])[:300])
            verified = True

        changed = [p.relative_to(src_abs).as_posix() for p, original in originals.items()
                   if not delivery._source_matches(p, applied.get(p, original), modes[p])]
        if changed:
            _fail("SOURCE_CHANGED_AFTER_VERIFICATION:" + ",".join(changed))

        artifact = {
            "schema": SCHEMA,
            "source_root": src_rel,
            "module": module_rel,
            "target_module": target_mod,
            "qualname": qualname,
            "old_param": old,
            "new_param": new,
            "edit_count": len(edit_rows),
            "files_edited": files_edited,
            "edits": sorted(edit_rows, key=lambda r: (r["file"], r["line"])),
            "unknown_sites": sorted(unknown_sites, key=lambda r: (r["file"], r["line"])),
            "shadowed_keeps": sorted(shadowed_keeps, key=lambda r: (r["line"], r["scope"])),
            "positional_callsites_untouched": positional_untouched,
            "verification": evidence,
            "gate": gate,
            "law": ("definition + body + resolvable keyword call sites renamed in one "
                    "in-place pass; scoping/shadowing respected byte-exactly; dynamic "
                    "receivers list and lower complete, never silently dropped; named "
                    "tests run post-edit and a red suite rolls the whole edit back"),
            "complete": complete,
        }
        out_abs.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(artifact, indent=2, ensure_ascii=False) + "\n"
        report_mode = stat.S_IMODE(out_abs.stat().st_mode) if out_abs.is_file() else 0o644
        delivery._atomic_write(out_abs, text.encode("utf-8"), mode=report_mode)
        out_verified = json.loads(out_abs.read_text(encoding="utf-8")) == artifact
        if not out_verified:
            _fail("REPORT_READBACK_FAILED")

        return {
            "adapter": "python_refactor_rename_parameter",
            "module": module_rel,
            "qualname": qualname,
            "old_param": old,
            "new_param": new,
            "edit_count": len(edit_rows),
            "files_edited": len(files_edited),
            "unknown_sites": len(unknown_sites),
            "shadowed_keeps": len(shadowed_keeps),
            "gate": gate,
            "complete": complete,
            "output_path": out_rel,
            "output_sha256": _sha256(text.encode("utf-8")),
            "output_verified": out_verified,
            "verified": bool(verified),
        }
    except BaseException:
        delivery._restore_sources(originals, modes)
        raise


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--source_root", required=True)
    p.add_argument("--module", required=True)
    p.add_argument("--qualname", required=True)
    p.add_argument("--old_param", required=True)
    p.add_argument("--new_param", required=True)
    p.add_argument("--output_path", required=True)
    p.add_argument("--run_tests", nargs="*", default=None)
    ns = p.parse_args()
    print(json.dumps(run(vars(ns), Path.cwd()), indent=2, sort_keys=True))
