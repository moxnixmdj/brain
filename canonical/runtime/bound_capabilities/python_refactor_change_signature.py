# PROJECT_BRAIN
"""python.refactor.change_signature.v1 — change a function's SIGNATURE and every
call site that must follow, by byte splice, with a verification gate.

A signature change is the one refactor that is simultaneously local and global:
the ``def`` is one span, and every caller that passes the affected parameters
must move with it or the program stops meaning what it meant.  So this verb
never guesses:

* ``renames``      {"old": "new"}      parameter renamed at the def and in the
                                       body, and every ``old=`` keyword at a
                                       call site.
* ``add``          [{"name":..., "default": <expr>, "keyword_only": bool}]
                                       appended to the signature.  A parameter
                                       WITHOUT a default needs ``call_default``,
                                       because then every resolved call site is
                                       rewritten to pass it and a call site this
                                       verb cannot resolve refuses the edit.
* ``remove``       ["name"]            only a TRAILING parameter with a default,
                                       never referenced in the body and never
                                       passed by any resolved call site.
* ``set_defaults`` {"name": <expr>}    replace a default value only.

Call-site law: a call is edited only when it PROVABLY binds this function --
``sym(...)`` in the defining module, ``from mod import sym`` then ``sym(...)``,
or ``import mod [as m]`` then ``m.sym(...)``.  Anything else (a bare name in a
module that merely shares the word, ``getattr`` dispatch, the function used as a
VALUE) is listed in ``unknown_sites`` and lowers ``complete`` -- and refuses the
edit outright when the change is not backward compatible.

Refusals (each one names the reason and leaves every byte untouched):
SIGNATURE_NOT_STATED, SYMBOL_NOT_FOUND, NOT_A_FUNCTION, INVALID_PARAM_NAME,
DUPLICATE_PARAM, PARAM_NOT_FOUND, NEW_NAME_COLLIDES, PARAM_IN_USE,
REMOVAL_SHIFTS_ARGUMENT, REQUIRED_PARAM_NEEDS_CALL_VALUE, CALL_KEYWORD_COLLISION,
CALL_ARITY_INCOMPATIBLE, FUNCTION_OBJECT_ESCAPES, SPAN_INTEGRITY,
SYNTAX_ERROR_IN_FILE, SYNTAX_ERROR_AFTER_EDIT, TESTS_RED_AFTER_EDIT, PATH_*.

Verification law: the edited tree is re-parsed, then the named pytest suite runs;
red restores ALL original bytes.  No ``run_tests`` named => gate PASS_BLIND and
``verified: false`` loudly.
"""

from __future__ import annotations

import ast
import hashlib
import io
import json
import subprocess
import sys
import tokenize
from pathlib import Path

SCHEMA = "PROJECT_BRAIN_REFACTOR_CHANGE_SIGNATURE_V1"
CAPABILITY_ID = "python.refactor.change_signature.v1"


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


def _sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _modname_of(rel: str) -> str:
    noext = rel[:-3] if rel.endswith(".py") else rel
    return ".".join(p for p in noext.split("/") if p != "__init__")


def _params_of(fn):
    a = fn.args
    out = list(a.posonlyargs) + list(a.args) + list(a.kwonlyargs)
    for extra in (a.vararg, a.kwarg):
        if extra is not None:
            out.append(extra)
    return out


def _binds_name(node, name: str) -> bool:
    """True if nested scope `node` rebinds `name` for its own body."""
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


def _resolve_def(tree, parts):
    """Follow the qualname to (node, kind).  Same law as rename_symbol."""
    nodes = tree.body
    owner_class = None
    for idx, seg in enumerate(parts):
        hit_fn = [n for n in nodes
                  if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                  and n.name == seg]
        hit_cls = [n for n in nodes if isinstance(n, ast.ClassDef) and n.name == seg]
        hits = hit_fn + hit_cls
        if not hits:
            _fail("SYMBOL_NOT_FOUND:" + ".".join(parts[:idx + 1]))
        if len(hits) > 1:
            _fail("MULTI_DEFINITION:" + ".".join(parts[:idx + 1]))
        target = hits[0]
        if idx == len(parts) - 1:
            if target in hit_fn:
                return target, ("METHOD" if owner_class is not None else "FUNCTION")
            return target, "CLASS"
        if target in hit_cls:
            owner_class = target
        nodes = target.body
    _fail("SYMBOL_NOT_FOUND:" + ".".join(parts))


def _import_table(tree):
    binding = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                binding[a.asname or a.name.split(".")[0]] = (a.name, None)
        elif isinstance(node, ast.ImportFrom):
            for a in node.names:
                binding[a.asname or a.name] = (node.module or "", a.name)
    return binding


def _line_starts(text: str) -> list[int]:
    starts = [0]
    for line in text.splitlines(keepends=True):
        starts.append(starts[-1] + len(line))
    return starts


def _offset(starts, lineno: int, col: int) -> int:
    return starts[lineno - 1] + col


def _paren_span(text: str, starts, after_offset: int):
    """(open_offset, close_offset) of the first '(' at/after after_offset."""
    tokens = list(tokenize.generate_tokens(io.StringIO(text).readline))
    opened = None
    depth = 0
    for tok in tokens:
        if tok.type != tokenize.OP or tok.string not in "()":
            continue
        here = _offset(starts, tok.start[0], tok.start[1])
        if opened is None:
            if tok.string == "(" and here >= after_offset:
                opened = here
                depth = 1
            continue
        depth += 1 if tok.string == "(" else -1
        if depth == 0:
            return opened, here
    _fail("SPAN_INTEGRITY:unbalanced_parentheses")


def _render_param(name, annotation_src, default_src, prefix=""):
    out = prefix + name
    if annotation_src:
        out += ": " + annotation_src
    if default_src is not None:
        out += "=" + default_src
    return out


def _signature_text(fn, source: str):
    """Render this def's parameter list, keeping every annotation and default."""
    a = fn.args
    positional = list(a.posonlyargs) + list(a.args)
    ndefaults = len(a.defaults)
    rendered = []
    for index, arg in enumerate(positional):
        d_index = index - (len(positional) - ndefaults)
        default = a.defaults[d_index] if d_index >= 0 else None
        ann = ast.get_source_segment(source, arg.annotation) if arg.annotation else None
        dflt = ast.get_source_segment(source, default) if default is not None else None
        rendered.append({
            "kind": "posonly" if index < len(a.posonlyargs) else "positional",
            "name": arg.arg, "annotation": ann, "default": dflt,
            "has_default": default is not None,
        })
    if a.vararg is not None:
        rendered.append({"kind": "vararg", "name": a.vararg.arg,
                         "annotation": (ast.get_source_segment(source, a.vararg.annotation)
                                        if a.vararg.annotation else None),
                         "default": None, "has_default": False})
    for arg, default in zip(a.kwonlyargs, a.kw_defaults):
        rendered.append({
            "kind": "kwonly", "name": arg.arg,
            "annotation": ast.get_source_segment(source, arg.annotation) if arg.annotation else None,
            "default": ast.get_source_segment(source, default) if default is not None else None,
            "has_default": default is not None,
        })
    if a.kwarg is not None:
        rendered.append({"kind": "kwarg", "name": a.kwarg.arg,
                         "annotation": (ast.get_source_segment(source, a.kwarg.annotation)
                                        if a.kwarg.annotation else None),
                         "default": None, "has_default": False})
    return rendered


def _render_signature(params) -> str:
    parts = []
    seen_kwonly = False
    for p in params:
        kind = p["kind"]
        if kind == "kwonly" and not seen_kwonly:
            seen_kwonly = True
            if not any(x["kind"] == "vararg" for x in params):
                parts.append("*")
        if kind == "posonly":
            parts.append(_render_param(p["name"], p["annotation"], p["default"]))
        elif kind == "positional":
            parts.append(_render_param(p["name"], p["annotation"], p["default"]))
        elif kind == "vararg":
            parts.append(_render_param(p["name"], p["annotation"], None, prefix="*"))
        elif kind == "kwonly":
            parts.append(_render_param(p["name"], p["annotation"], p["default"]))
        elif kind == "kwarg":
            parts.append(_render_param(p["name"], p["annotation"], None, prefix="**"))
    return "(" + ", ".join(parts) + ")"


def _body_renames(fn, old: str, new: str, shadowed: list, rel: str) -> list:
    """Every Name(old) in this function's body that resolves to the parameter."""
    edits = []

    def walk(node, report):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                if _binds_name(child, old):
                    shadowed.append({"file": rel, "line": child.lineno,
                                     "scope": getattr(child, "name", "lambda"),
                                     "rule": "nested scope rebinds the parameter"})
                    continue
            if isinstance(child, ast.ClassDef):
                shadowed.append({"file": rel, "line": child.lineno,
                                 "scope": child.name,
                                 "rule": "class body is opaque to parameter scope"})
                continue
            if isinstance(child, ast.Name) and child.id == old:
                edits.append((child.lineno, child.col_offset, old, new))
                continue
            walk(child, report)

    # The def's OWN parameter list is not walked here: it is re-rendered from the
    # model in one span replacement, and an edit inside that span would overlap it.
    walk(ast.Module(body=list(fn.body), type_ignores=[]), None)
    return sorted(set(edits))


def _scope_shadowed_calls(tree, target_sym: str, target_node) -> set:
    """Calls that bind a DIFFERENT `target_sym` because an enclosing scope rebinds it.

    "return add(1, 2)" inside a function that defines its own `add` is not a call of the
    module-level function, and rewriting its keywords would corrupt an unrelated function.
    A nested def/class with the target's name is a rebinding in exactly the same way a
    parameter is.
    """
    skip = set()

    def rebinds(node) -> bool:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            if any(p.arg == target_sym for p in _params_of(node)):
                return True
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) \
                    and child.name == target_sym:
                return True
        return False

    def visit(node):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                if child is not target_node and rebinds(child):
                    for inner in ast.walk(child):
                        if isinstance(inner, ast.Call):
                            skip.add(id(inner))
                    continue
            if isinstance(child, ast.ClassDef) and child is not target_node:
                if any(isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef))
                       and x.name == target_sym for x in child.body):
                    for inner in ast.walk(child):
                        if isinstance(inner, ast.Call):
                            skip.add(id(inner))
                    continue
            visit(child)

    visit(tree)
    return skip


def _call_edits(tree, target_mod: str, target_sym: str, rel: str, this_mod: str,
                renames: dict, added_required: list, added_optional: list,
                removed: list, new_signature: list, unknown: list,
                target_node=None):
    """Edits at every call site that PROVABLY binds target_sym."""
    edits = []
    bindings = _import_table(tree)
    shadowed = _scope_shadowed_calls(tree, target_sym, target_node)
    direct_ok = this_mod == target_mod
    alias_for_mod = {k: v[0] for k, v in bindings.items() if v[1] is None}
    imported = {k: v for k, v in bindings.items()
                if v[1] == target_sym and v[0] == target_mod}

    def matches(call):
        if id(call) in shadowed:
            return False
        f = call.func
        if isinstance(f, ast.Name):
            if direct_ok and f.id == target_sym and f.id not in bindings:
                return True
            return f.id in imported
        if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name):
            return (f.attr == target_sym
                    and alias_for_mod.get(f.value.id) == target_mod)
        return False

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not matches(node):
            continue
        row = {"file": rel, "line": node.lineno}
        positional = len(node.args)
        keywords = {kw.arg: kw for kw in node.keywords if kw.arg}
        # renames: the keyword name at the call follows the parameter
        for old, new in renames.items():
            kw = keywords.get(old)
            if kw is None:
                continue
            if new in keywords:
                _fail("CALL_KEYWORD_COLLISION:" + rel + ":" + str(node.lineno) + ":" + new)
            edits.append((kw.lineno, kw.col_offset, old, new))
        # a removed parameter may not be passed anywhere
        for name in removed:
            if name in keywords:
                _fail("PARAM_IN_USE:" + name + " passed at " + rel + ":" + str(node.lineno))
        # arity: positional count may not exceed what the new signature accepts
        new_positional = [p for p in new_signature
                          if p["kind"] in ("posonly", "positional")]
        if positional > len(new_positional) and not any(
                p["kind"] == "vararg" for p in new_signature):
            _fail("CALL_ARITY_INCOMPATIBLE:" + rel + ":" + str(node.lineno))
        if added_required:
            row["needs"] = [p["name"] for p in added_required]
        if added_optional:
            row["optional"] = [p["name"] for p in added_optional]
        # every resolved call is recorded, so the count is a fact even when the
        # signature change needs nothing inserted at it
        edits.append(("call", node, row))
    return edits


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
    out_rel = str(args.get("output_path") or "")
    out_abs = _safe_path(repo, out_rel)
    python_exe = str(args.get("python_executable") or sys.executable)
    timeout_s = int(args.get("timeout_s") or 300)
    run_tests = list(args.get("run_tests") or [])

    # A STRUCTURED EDIT SPEC IS A FILE, because that is how this repository already states
    # one: python.source.crossfile_edit.choreograph.v1 takes `edits_path`, a JSON document of
    # edit ops, and refuses a shape it cannot read.  A signature is the same kind of value --
    # a map of renames, adds, removals and defaults -- so it is stated the same way, and the
    # inline keys are kept for callers that already hold it in hand.
    spec = {}
    edits_rel = str(args.get("edits_path") or "")
    if edits_rel:
        edits_abs = _safe_path(repo, edits_rel, must_exist=True)
        try:
            spec = json.loads(edits_abs.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            _fail("EDITS_SPEC_UNREADABLE:" + str(exc))
        if not isinstance(spec, dict):
            _fail("EDITS_SPEC_INVALID:not_an_object")
        if isinstance(spec.get("edits"), dict):
            spec = spec["edits"]
    for key in ("renames", "add", "remove", "set_defaults", "call_default"):
        if args.get(key) in (None, "", [], {}) and spec.get(key) not in (None, "", [], {}):
            args[key] = spec[key]

    renames = {str(k): str(v) for k, v in dict(args.get("renames") or {}).items()}
    add = list(args.get("add") or [])
    remove = [str(x) for x in (args.get("remove") or [])]
    set_defaults = {str(k): str(v) for k, v in dict(args.get("set_defaults") or {}).items()}
    call_default = args.get("call_default")
    call_default = str(call_default) if call_default not in (None, "") else None

    if not any((renames, add, remove, set_defaults)):
        _fail("SIGNATURE_NOT_STATED")

    for name, value in set_defaults.items():
        try:
            ast.parse(str(value), mode="eval")
        except SyntaxError:
            _fail("INVALID_DEFAULT_EXPRESSION:" + name)
    if call_default is not None:
        try:
            ast.parse(call_default, mode="eval")
        except SyntaxError:
            _fail("INVALID_DEFAULT_EXPRESSION:call_default")
    for spec in add:
        if not isinstance(spec, dict) or not str(spec.get("name") or "").isidentifier():
            _fail("INVALID_PARAM_NAME:" + str(spec))
        if spec.get("default") is not None:
            try:
                ast.parse(str(spec["default"]), mode="eval")
            except SyntaxError:
                _fail("INVALID_DEFAULT_EXPRESSION:" + str(spec["name"]))

    parts = [p for p in qualname.split(".") if p]
    target_sym = parts[-1]
    target_mod = _modname_of(module_rel)

    all_py = sorted(p for p in src_abs.rglob("*.py") if "__pycache__" not in p.parts)
    originals = {p: p.read_bytes() for p in all_py}
    texts, parsed = {}, {}
    for path in all_py:
        rel = path.relative_to(src_abs).as_posix()
        try:
            text = originals[path].decode("utf-8")
            texts[path] = text
            parsed[path] = ast.parse(text, filename=rel)
        except (SyntaxError, UnicodeDecodeError) as exc:
            _fail("SYNTAX_ERROR_IN_FILE:" + rel + ":" + str(exc))

    def_node, kind = _resolve_def(parsed[module_abs], parts)
    if kind == "CLASS":
        _fail("NOT_A_FUNCTION:" + qualname)
    source = texts[module_abs]
    starts = _line_starts(source)

    current = _signature_text(def_node, source)
    old_signature = _render_signature(current)
    names = [p["name"] for p in current]

    # ------------------------------------------------------------ the new list
    new_params = [dict(p) for p in current]
    shadowed: list = []
    body_edits: list = []

    for old, new in renames.items():
        if old not in names:
            _fail("PARAM_NOT_FOUND:" + old)
        if not new.isidentifier():
            _fail("INVALID_PARAM_NAME:" + new)
        if new in names and new != old:
            _fail("DUPLICATE_PARAM:" + new)
        for param in new_params:
            if param["name"] == old:
                param["name"] = new
        body_edits += _body_renames(def_node, old, new, shadowed, module_rel)

    for name in remove:
        if name not in [p["name"] for p in new_params]:
            _fail("PARAM_NOT_FOUND:" + name)
        position = [p["name"] for p in new_params].index(name)
        param = new_params[position]
        if param["kind"] in ("vararg", "kwarg"):
            _fail("PARAM_KIND_UNSUPPORTED:" + name)
        if not param["has_default"]:
            _fail("REMOVAL_SHIFTS_ARGUMENT:" + name + " has no default")
        if position != len(new_params) - 1:
            _fail("REMOVAL_SHIFTS_ARGUMENT:" + name + " is not the last parameter")
        own_args = {id(a) for a in _params_of(def_node)}
        for node in ast.walk(def_node):
            if isinstance(node, ast.Name) and node.id == name:
                _fail("PARAM_IN_USE:" + name)
            # its OWN declaration is not a use of it
            if isinstance(node, ast.arg) and node.arg == name and id(node) not in own_args:
                _fail("PARAM_IN_USE:" + name)
        new_params.pop(position)

    for name, value in set_defaults.items():
        for param in new_params:
            if param["name"] == name:
                param["default"] = value
                param["has_default"] = True
                break
        else:
            _fail("PARAM_NOT_FOUND:" + name)

    added_required, added_optional = [], []
    for spec in add:
        name = str(spec["name"])
        if name in [p["name"] for p in new_params]:
            _fail("DUPLICATE_PARAM:" + name)
        default = spec.get("default")
        kw_only = bool(spec.get("keyword_only"))
        param = {"kind": "kwonly" if kw_only else "positional", "name": name,
                 "annotation": None,
                 "default": None if default is None else str(default),
                 "has_default": default is not None}
        new_params.append(param)
        if default is None:
            added_required.append(param)
        else:
            added_optional.append(param)
    if added_required and call_default is None:
        _fail("REQUIRED_PARAM_NEEDS_CALL_VALUE:" + added_required[0]["name"])

    has_kwarg = any(p["kind"] == "kwarg" for p in new_params)
    if added_required and has_kwarg:
        _fail("ADDED_PARAM_UNVERIFIABLE_WITH_KWARGS:" + added_required[0]["name"])

    # defaults may not follow non-defaults among the positional params
    positional = [p for p in new_params if p["kind"] in ("posonly", "positional")]
    seen_default = False
    for param in positional:
        if param["has_default"]:
            seen_default = True
        elif seen_default:
            _fail("DEFAULT_ORDER_VIOLATION:" + param["name"])

    new_signature = new_params
    new_text = _render_signature(new_params)

    per_file_edits: dict = {}
    if body_edits:
        per_file_edits.setdefault(module_abs, []).extend(body_edits)

    # ------------------------------------------------------- call-site harvest
    unknown: list = []
    call_sites = []
    for path, tree in parsed.items():
        rel = path.relative_to(src_abs).as_posix()
        this_mod = _modname_of(rel)
        found = _call_edits(tree, target_mod, target_sym, rel, this_mod, renames,
                            added_required, added_optional, remove, new_signature,
                            unknown, def_node if path == module_abs else None)
        for item in found:
            if item[0] == "call":
                call_sites.append((path, item[1], item[2], texts[path]))
            else:
                per_file_edits.setdefault(path, []).append(item)

    # a function used as a VALUE cannot be followed to its call sites
    for path, tree in parsed.items():
        rel = path.relative_to(src_abs).as_posix()
        this_mod = _modname_of(rel)
        bindings = _import_table(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id == target_sym \
                    and isinstance(node.ctx, ast.Load):
                if this_mod != target_mod and target_sym not in bindings:
                    continue
                if any(isinstance(parent, ast.Call) and parent.func is node
                       for parent in ast.walk(tree)):
                    continue
                unknown.append({"file": rel, "line": node.lineno,
                                "rule": "function object escapes (used as a value)"})
    if unknown and (added_required or remove):
        _fail("FUNCTION_OBJECT_ESCAPES:" + unknown[0]["file"] + ":"
              + str(unknown[0]["line"]))

    # ------------------------------------------------------------- splice plan
    open_at, close_at = _paren_span(source, starts, _offset(starts, def_node.lineno,
                                                           def_node.col_offset))
    spans = [(open_at, close_at + 1, new_text)]
    for (ln, col, old, new) in per_file_edits.get(module_abs, []):
        spans.append((_offset(starts, ln, col), _offset(starts, ln, col) + len(old), new))

    def _splice(text: str, file_spans) -> str:
        ordered = sorted(file_spans, key=lambda s: s[0], reverse=True)
        last_start = None
        for start, end, replacement in ordered:
            expected = text[start:end]
            if last_start is not None and end > last_start:
                _fail("SPAN_INTEGRITY:overlap")
            last_start = start
            if replacement not in ("", "__DELETE__") and expected.strip() == "":
                _fail("SPAN_INTEGRITY:empty_span")
            text = text[:start] + replacement + text[end:]
        return text

    applied = {}
    if spans:
        after = _splice(source, spans)
        applied[module_abs] = after
    for path, edits in per_file_edits.items():
        if path == module_abs:
            continue
        after = _splice(texts[path], [( _offset(_line_starts(texts[path]), ln, col),
                                        _offset(_line_starts(texts[path]), ln, col) + len(old),
                                        new) for (ln, col, old, new) in edits])
        applied[path] = after

    # call sites: keyword renames were harvested above; a required added
    # parameter is appended at every resolved call, last-to-first.
    per_call = {}
    for path, node, row, text in call_sites:
        per_call.setdefault(path, []).append((node, row))
    for path, rows in per_call.items():
        text = applied.get(path, texts[path])
        starts_here = _line_starts(text)
        inserts = []
        for node, row in rows:
            if row.get("needs"):
                end = _offset(starts_here, node.func.end_lineno,
                              node.func.end_col_offset)
                _, close_here = _paren_span(text, starts_here, end)
                payload = "".join(", " + name + "=" + str(call_default)
                                  for name in row["needs"])
                inserts.append((close_here, payload))
        if inserts:
            for offset, payload in sorted(inserts, reverse=True):
                text = text[:offset] + payload + text[offset:]
            applied[path] = text

    for path, after in applied.items():
        try:
            ast.parse(after, filename=path.name)
        except SyntaxError as exc:
            _fail("SYNTAX_ERROR_AFTER_EDIT:" + str(exc))

    for path, after in applied.items():
        path.write_text(after, encoding="utf-8")

    gate = "PASS"
    verified = bool(run_tests)
    if run_tests:
        proc = subprocess.run(
            [python_exe, "-m", "pytest", "-q", "-p", "no:cacheprovider"] + run_tests,
            cwd=src_abs, capture_output=True, text=True, timeout=timeout_s)
        if proc.returncode != 0:
            for path, original in originals.items():
                path.write_bytes(original)
            tail = "\n".join((proc.stdout + proc.stderr).strip().splitlines()[-6:])
            _fail("TESTS_RED_AFTER_EDIT:" + tail)
    else:
        gate = "PASS_BLIND"

    out = {
        "schema": SCHEMA,
        "adapter": "python_refactor_change_signature",
        "capability": CAPABILITY_ID,
        "module": module_rel,
        "qualname": qualname,
        "edits_path": edits_rel or None,
        "old_signature": old_signature,
        "new_signature": new_text,
        "renames": dict(sorted(renames.items())),
        "added": [p["name"] for p in added_required + added_optional],
        "removed": sorted(remove),
        "defaults_set": sorted(set_defaults),
        "call_sites_edited": len(call_sites),
        "edit_count": (sum(len(v) for v in per_file_edits.values()) + 1
                       + sum(len(row.get("needs") or []) for _p, _n, row, _t in call_sites)),
        "files_edited": sorted(p.relative_to(src_abs).as_posix() for p in applied),
        "unknown_sites": sorted(unknown, key=lambda r: (r["file"], r["line"])),
        "shadowed_keeps": sorted(shadowed, key=lambda r: (r["file"], r["line"])),
        "gate": gate,
        "complete": not unknown,
        "output_verified": True,
        "verified": verified,
    }
    out_abs.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(out, indent=1, sort_keys=True, default=list) + "\n"
    out_abs.write_text(payload, encoding="utf-8")
    final = dict(out)
    final["output_path"] = out_rel
    final["output_sha256"] = _sha256(payload.encode("utf-8"))
    print(json.dumps(final, indent=1, sort_keys=True, default=list))
    return final
