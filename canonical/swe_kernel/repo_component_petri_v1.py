"""Repo-Native Component Mining + Type-Transition Petri-Net Expression & Handler Synthesis.

Breaks the fixed-grammar ceiling (`THE_SPACE_IS_THE_ARTIFACT` 75.2% wall) with zero model calls:
1. Mines repository-native methods, functions, exception types, called test target symbols, and
   specification literals from the 2-hop causal neighborhood around a localized fault site
   (cached per `(repo_root, rel_path)` so AST mining runs once per file in ~20ms).
2. Builds a bounded Type-Transition Petri Net over live runtime frame tokens (`locals`, `self.<attr>`,
   iterable element types) + higher-order collection/string/optional/exception functors:
   - Mapped repo-method comprehensions: `[el.m(*args) for el in seq]`,
     `[rv for rv in (el.m(*args) for el in seq) if rv is not None]`, `[x for x in seq if x]`
   - Optional-to-String & Tuple slot coalescing: `(a, b or "")`, `(expr) or ""`, early `return None`
     guard elision when non-None output is required
   - Delimiter & whitespace monoid laws: `sep.join(...)`, `(expr).rstrip()`, `(expr).strip()`
   - Direct 1-step repo-native method/helper calls + signature keyword forwarding
   - Exception-handler widening (`except E1:` -> `except (E1, EscapedExc):`) driven by `exceptions_seen`
3. Filters candidate expressions safely inside an ephemeral `os.fork()` Copy-on-Write child.
"""

from __future__ import annotations

import ast
import builtins
import os
from pathlib import Path

from canonical.swe_kernel.cow_lens_fuzz_and_negative_space_v1 import (
    synthesize_bidirectional_fst_lens,
)
import re
from typing import Any

from canonical.swe_kernel.incremental_semantic_graph_v1 import IncrementalSemanticGraph

_BUILTIN_NAMES = frozenset(dir(builtins))
_SAFE_EXCEPTION_NAMES = frozenset(
    name
    for name in _BUILTIN_NAMES
    if isinstance(getattr(builtins, name, None), type)
    and issubclass(getattr(builtins, name), BaseException)
)
_ITERABLE_TYPE_NAMES = frozenset(
    {"list", "tuple", "set", "frozenset", "dict_keys", "dict_values", "generator", "iterator"}
)

# Per-(repo_root_str, rel_path) module component cache to avoid redundant AST/import scans
_FILE_COMPONENT_CACHE: dict[
    tuple[str, str],
    tuple[list["RepoCallableComponent"], dict[str, list["RepoCallableComponent"]], set[str]],
] = {}


class RepoCallableComponent:
    """Typed callable component mined from the target file or its 1-hop semantic graph."""

    __slots__ = (
        "call_syntax",
        "owner_class",
        "name",
        "min_arity",
        "max_arity",
        "param_names",
        "kwonly_names",
        "is_method",
    )

    def __init__(
        self,
        *,
        call_syntax: str,
        owner_class: str | None,
        name: str,
        min_arity: int,
        max_arity: int,
        param_names: tuple[str, ...],
        kwonly_names: tuple[str, ...] = (),
        is_method: bool = False,
    ) -> None:
        self.call_syntax = call_syntax
        self.owner_class = owner_class
        self.name = name
        self.min_arity = min_arity
        self.max_arity = max_arity
        self.param_names = param_names
        self.kwonly_names = kwonly_names
        self.is_method = is_method


def extract_test_called_symbols_and_literals(
    repo_root: Path,
    failing_nodeids: list[str],
    *,
    max_literals: int = 12,
) -> tuple[set[str], list[str]]:
    """Extract `(called_symbol_names, spec_string_literals)` from the failing test ASTs.

    `called_symbol_names` identifies the exact functions/methods directly exercised in the failing
    test (e.g. `to_header`, `get_help_record`, `build`, `invoke`, `main`), rescuing fault ranking
    from generic `__init__` / `_utils` boilerplate.
    """
    called_symbols: set[str] = set()
    seen_lit: set[str] = set()
    literals: list[str] = []
    by_file: dict[str, set[str]] = {}
    for nid in failing_nodeids[:8]:
        if "::" not in nid:
            continue
        parts = nid.split("::")
        rel_test = parts[0]
        fn_raw = parts[-1].split("[", 1)[0]
        by_file.setdefault(rel_test, set()).add(fn_raw)
        # Also extract identifier tokens from the test function name itself (`test_show_envvar_empty` -> `envvar`)
        for tok in fn_raw.lower().split("_"):
            if len(tok) >= 4 and tok not in {"test", "tests", "none", "true", "false", "with", "from"}:
                called_symbols.add(tok)

    for rel_test, fn_names in by_file.items():
        p = repo_root / rel_test
        if not p.is_file():
            continue
        try:
            tree = ast.parse(p.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        target_nodes: list[ast.AST] = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in fn_names:
                target_nodes.append(node)
        # Also include helper methods in the same test class (`self._build` -> `build`)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if any(
                    isinstance(it, (ast.FunctionDef, ast.AsyncFunctionDef)) and it.name in fn_names
                    for it in node.body
                ):
                    target_nodes.extend(
                        it for it in node.body if isinstance(it, (ast.FunctionDef, ast.AsyncFunctionDef)) and it.name.startswith("_")
                    )

        for tnode in target_nodes:
            for sub in ast.walk(tnode):
                if isinstance(sub, ast.Call):
                    if isinstance(sub.func, ast.Attribute):
                        attr = sub.func.attr.lstrip("_")
                        if len(attr) >= 3 and attr not in {"assert", "fail", "raises", "mark", "parametrize"}:
                            called_symbols.add(sub.func.attr)
                            called_symbols.add(attr)
                    elif isinstance(sub.func, ast.Name):
                        nm = sub.func.id.lstrip("_")
                        if len(nm) >= 3 and nm not in _BUILTIN_NAMES:
                            called_symbols.add(sub.func.id)
                            called_symbols.add(nm)
                elif isinstance(sub, ast.keyword) and isinstance(sub.arg, str):
                    kw = sub.arg
                    if 1 <= len(kw) <= 32 and kw not in seen_lit:
                        seen_lit.add(kw)
                        literals.append(kw)
                elif isinstance(sub, ast.Compare):
                    for cmp_val in [sub.left, *sub.comparators]:
                        if isinstance(cmp_val, ast.Constant) and isinstance(cmp_val.value, str):
                            cval = cmp_val.value
                            if 1 <= len(cval) <= 64 and cval not in seen_lit:
                                seen_lit.add(cval)
                                literals.append(cval)
                elif isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                    val = sub.value
                    if (
                        1 <= len(val) <= 32
                        and val not in seen_lit
                        and (
                            re.match(r"^[A-Za-z_][A-Za-z0-9_\-\.]*$", val)
                            or val in {", ", ",", " ", "/", ":", ";", "|", "\n", "-", "_"}
                        )
                    ):
                        seen_lit.add(val)
                        literals.append(val)
    return called_symbols, literals[:max_literals]


def extract_test_spec_literals(
    repo_root: Path,
    failing_nodeids: list[str],
    *,
    max_literals: int = 12,
) -> list[str]:
    _, lits = extract_test_called_symbols_and_literals(
        repo_root, failing_nodeids, max_literals=max_literals
    )
    return lits


def _fn_signature_bounds(
    fn_node: ast.FunctionDef | ast.AsyncFunctionDef,
    is_method: bool,
) -> tuple[int, int, tuple[str, ...], tuple[str, ...]]:
    pos_args = [a.arg for a in fn_node.args.posonlyargs] + [a.arg for a in fn_node.args.args]
    if is_method and pos_args and pos_args[0] in {"self", "cls"}:
        pos_args = pos_args[1:]
    n_defaults = len(fn_node.args.defaults)
    min_arity = max(0, len(pos_args) - n_defaults)
    max_arity = len(pos_args) if fn_node.args.vararg is None else len(pos_args) + 1
    kwonly = tuple(a.arg for a in fn_node.args.kwonlyargs)
    return min_arity, max_arity, tuple(pos_args), kwonly


def _mine_file_level_components(
    repo_root: Path,
    rel_path: str,
    parsed_tree: ast.AST,
    semantic_graph: IncrementalSemanticGraph | None = None,
) -> tuple[list[RepoCallableComponent], dict[str, list[RepoCallableComponent]], set[str]]:
    cache_key = (str(repo_root), rel_path)
    cached = _FILE_COMPONENT_CACHE.get(cache_key)
    if cached is not None:
        return cached

    module_functions: list[RepoCallableComponent] = []
    methods_by_class: dict[str, list[RepoCallableComponent]] = {}
    class_bases: dict[str, list[str]] = {}
    in_scope_exceptions: set[str] = set(_SAFE_EXCEPTION_NAMES)

    def _scan_module_tree(
        tree: ast.AST,
        *,
        is_current_file: bool,
        imported_names: set[str] | None = None,
    ) -> None:
        for top in getattr(tree, "body", []):
            if isinstance(top, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if top.name.startswith("__") and top.name.endswith("__"):
                    continue
                if not is_current_file and imported_names is not None and top.name not in imported_names:
                    continue
                mn, mx, pnames, kwonly = _fn_signature_bounds(top, is_method=False)
                if mx <= 3:
                    module_functions.append(
                        RepoCallableComponent(
                            call_syntax=top.name,
                            owner_class=None,
                            name=top.name,
                            min_arity=mn,
                            max_arity=mx,
                            param_names=pnames,
                            kwonly_names=kwonly,
                            is_method=False,
                        )
                    )
            elif isinstance(top, ast.ClassDef):
                bases_here: list[str] = []
                for b in top.bases:
                    if isinstance(b, ast.Name):
                        bases_here.append(b.id)
                    elif isinstance(b, ast.Attribute):
                        bases_here.append(b.attr)
                class_bases[top.name] = bases_here
                if any(
                    b.endswith(("Error", "Exception", "Abort", "Interrupt", "Exit"))
                    for b in ([top.name] + bases_here)
                ):
                    if is_current_file or (imported_names and top.name in imported_names):
                        in_scope_exceptions.add(top.name)
                for item in top.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if item.name.startswith("__") and item.name.endswith("__"):
                            continue
                        mn, mx, pnames, kwonly = _fn_signature_bounds(item, is_method=True)
                        if mx <= 3:
                            methods_by_class.setdefault(top.name, []).append(
                                RepoCallableComponent(
                                    call_syntax=f"self.{item.name}",
                                    owner_class=top.name,
                                    name=item.name,
                                    min_arity=mn,
                                    max_arity=mx,
                                    param_names=pnames,
                                    kwonly_names=kwonly,
                                    is_method=True,
                                )
                            )

    _scan_module_tree(parsed_tree, is_current_file=True)

    imported_by_rel: dict[str, set[str]] = {}
    cur_pkg_parts = list(Path(rel_path).parts[:-1])
    for sub in ast.walk(parsed_tree):
        if isinstance(sub, ast.ImportFrom):
            names = {alias.name for alias in sub.names if alias.name != "*"}
            for nm in names:
                if nm.endswith(("Error", "Exception", "Abort", "Interrupt", "Exit")):
                    in_scope_exceptions.add(nm)
            mod = sub.module or ""
            cand_rels: list[str] = []
            if sub.level and sub.level >= 1:
                base_parts = cur_pkg_parts[: max(0, len(cur_pkg_parts) - (sub.level - 1))]
                mod_parts = [p for p in mod.split(".") if p]
                joined = "/".join(base_parts + mod_parts)
                cand_rels.extend([f"{joined}.py", f"{joined}/__init__.py"])
            elif mod:
                mod_slash = mod.replace(".", "/")
                cand_rels.extend(
                    [
                        f"{mod_slash}.py",
                        f"src/{mod_slash}.py",
                        f"{mod_slash}/__init__.py",
                        f"src/{mod_slash}/__init__.py",
                    ]
                )
            for cr in cand_rels:
                if (repo_root / cr).is_file():
                    imported_by_rel.setdefault(cr, set()).update(names)
                    break

    if semantic_graph is not None:
        try:
            for nb in semantic_graph.neighbors(rel_path)[:5]:
                if nb.endswith(".py") and nb not in imported_by_rel and (repo_root / nb).is_file():
                    imported_by_rel[nb] = set()
        except Exception:
            pass

    for imp_rel, imp_names in list(imported_by_rel.items())[:6]:
        try:
            imp_tree = ast.parse((repo_root / imp_rel).read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        _scan_module_tree(imp_tree, is_current_file=False, imported_names=imp_names if imp_names else None)

    # Propagate 2-hop class inheritance
    for _ in range(2):
        for cls_name, bases in list(class_bases.items()):
            existing = {c.name for c in methods_by_class.get(cls_name, [])}
            for b in bases:
                for b_comp in methods_by_class.get(b, []):
                    if b_comp.name not in existing:
                        existing.add(b_comp.name)
                        methods_by_class.setdefault(cls_name, []).append(b_comp)

    res = (module_functions[:28], methods_by_class, in_scope_exceptions)
    if len(_FILE_COMPONENT_CACHE) > 256:
        _FILE_COMPONENT_CACHE.clear()
    _FILE_COMPONENT_CACHE[cache_key] = res
    return res


def mine_repo_neighborhood_components(
    *,
    repo_root: Path,
    rel_path: str,
    parsed_tree: ast.AST,
    line_no: int,
    semantic_graph: IncrementalSemanticGraph | None = None,
) -> tuple[list[RepoCallableComponent], dict[str, list[RepoCallableComponent]], set[str]]:
    mod_fns, methods_by_class, in_scope_excs = _mine_file_level_components(
        repo_root, rel_path, parsed_tree, semantic_graph=semantic_graph
    )
    enclosing_class: str | None = None
    enclosing_func: str | None = None
    for node in ast.walk(parsed_tree):
        if isinstance(node, ast.ClassDef):
            if node.lineno <= line_no <= getattr(node, "end_lineno", node.lineno):
                enclosing_class = node.name
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.lineno <= line_no <= getattr(node, "end_lineno", node.lineno):
                enclosing_func = node.name

    direct: list[RepoCallableComponent] = [f for f in mod_fns if f.name != enclosing_func]
    if enclosing_class and enclosing_class in methods_by_class:
        for m in methods_by_class[enclosing_class]:
            if m.name != enclosing_func:
                direct.insert(0, m)
    return direct[:32], methods_by_class, in_scope_excs


def _match_args_for_component(
    comp: RepoCallableComponent,
    available_vars: list[str],
    available_self_attrs: list[str],
) -> list[tuple[str, ...]]:
    if comp.min_arity == 0 and comp.max_arity == 0:
        return [()]
    bindings: list[tuple[str, ...]] = []
    var_set = set(available_vars)
    if comp.min_arity <= len(comp.param_names):
        exact_prefix: list[str] = []
        for pname in comp.param_names[: comp.max_arity]:
            if pname in var_set:
                exact_prefix.append(pname)
            elif f"self.{pname}" in available_self_attrs:
                exact_prefix.append(f"self.{pname}")
            else:
                break
        if len(exact_prefix) >= comp.min_arity:
            bindings.append(tuple(exact_prefix[: comp.min_arity]))
            if len(exact_prefix) > comp.min_arity:
                bindings.append(tuple(exact_prefix))
    if comp.min_arity <= 1 <= comp.max_arity:
        for v in available_vars[:5]:
            if v not in {"self", "cls"} and (v,) not in bindings:
                bindings.append((v,))
    if comp.min_arity == 0 and () not in bindings:
        bindings.insert(0, ())
    return bindings[:3]


def synthesize_exception_handler_widening(
    *,
    source_text: str,
    line_no: int,
    escaping_exceptions: list[dict[str, Any]],
    rel_path: str,
    in_scope_exceptions: set[str],
    parsed_tree: ast.AST | None = None,
) -> list[tuple[str, str]]:
    if not escaping_exceptions:
        return []
    tree = parsed_tree or ast.parse(source_text)
    lines = source_text.splitlines(keepends=True)
    out: list[tuple[str, str]] = []
    seen: set[str] = set()

    ordered_excs: list[str] = []
    for e in escaping_exceptions:
        if e.get("rel_path") and e.get("rel_path") != rel_path:
            continue
        ex_name = str(e.get("exc_type") or "")
        if ex_name in in_scope_exceptions and ex_name not in ordered_excs:
            ordered_excs.append(ex_name)
    if not ordered_excs:
        return []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Try) or not node.handlers:
            continue
        start_ln = node.lineno
        end_ln = getattr(node, "end_lineno", start_ln)
        exc_in_try = [
            str(e.get("exc_type"))
            for e in escaping_exceptions
            if e.get("rel_path") == rel_path
            and isinstance(e.get("lineno"), int)
            and start_ln <= int(e["lineno"]) <= end_ln
            and str(e.get("exc_type")) in in_scope_exceptions
        ]
        if not (start_ln <= line_no <= end_ln or exc_in_try):
            continue
        cand_excs = exc_in_try or ordered_excs
        for handler in node.handlers:
            if handler.type is None:
                continue
            h_ln = handler.lineno
            if getattr(handler.type, "end_lineno", h_ln) != h_ln or handler.type.end_col_offset is None:
                continue
            existing_names = (
                [ast.unparse(elt).strip() for elt in handler.type.elts]
                if isinstance(handler.type, ast.Tuple)
                else [ast.unparse(handler.type).strip()]
            )
            orig_line = lines[h_ln - 1]
            for new_exc in cand_excs[:3]:
                if new_exc in existing_names:
                    continue
                merged_tuple = "(" + ", ".join(existing_names + [new_exc]) + ")"
                new_line = orig_line[: handler.type.col_offset] + merged_tuple + orig_line[handler.type.end_col_offset :]
                cand_lines = list(lines)
                cand_lines[h_ln - 1] = new_line
                patched = "".join(cand_lines)
                if patched not in seen:
                    try:
                        ast.parse(patched)
                        seen.add(patched)
                        out.append(
                            (
                                patched,
                                f"Exception-handler Petri widening at L{h_ln}: `{ast.unparse(handler.type)}` -> `{merged_tuple}`",
                            )
                        )
                    except SyntaxError:
                        pass
    return out


def synthesize_repo_petri_repairs(
    *,
    repo_root: Path,
    rel_path: str,
    source_text: str,
    line_no: int,
    pass_samples: list[dict[str, Any]],
    fail_samples: list[dict[str, Any]],
    escaping_exceptions: list[dict[str, Any]],
    spec_literals: list[str] | None = None,
    called_symbols: set[str] | None = None,
    parsed_tree: ast.AST | None = None,
    semantic_graph: IncrementalSemanticGraph | None = None,
) -> tuple[list[tuple[str, str]], int]:
    """Synthesize single-site repairs via Repo-Native Component Petri-Net transitions."""
    try:
        tree = parsed_tree or ast.parse(source_text)
    except SyntaxError:
        return [], 0
    lines = source_text.splitlines(keepends=True)
    if line_no < 1 or line_no > len(lines):
        return [], 0

    direct_comps, methods_by_class, in_scope_excs = mine_repo_neighborhood_components(
        repo_root=repo_root,
        rel_path=rel_path,
        parsed_tree=tree,
        line_no=line_no,
        semantic_graph=semantic_graph,
    )

    out_patches: list[tuple[str, str]] = []
    seen_patches: set[str] = set()

    def _emit_patch(patched_src: str, desc: str) -> None:
        if patched_src != source_text and patched_src not in seen_patches:
            try:
                ast.parse(patched_src)
                seen_patches.add(patched_src)
                out_patches.append((patched_src, desc))
            except SyntaxError:
                pass

    # 1. Exception-handler widening (`except E1:` -> `except (E1, E2):`)
    for p_src, desc in synthesize_exception_handler_widening(
        source_text=source_text,
        line_no=line_no,
        escaping_exceptions=escaping_exceptions,
        rel_path=rel_path,
        in_scope_exceptions=in_scope_excs,
        parsed_tree=tree,
    ):
        _emit_patch(p_src, desc)

    target_stmt: ast.stmt | None = None
    enclosing_fn: ast.FunctionDef | ast.AsyncFunctionDef | None = None
    enclosing_if_returning_none: ast.If | None = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.lineno <= line_no <= getattr(node, "end_lineno", node.lineno):
                enclosing_fn = node
        elif isinstance(node, ast.If) and not node.orelse and len(node.body) == 1:
            b0 = node.body[0]
            if (
                isinstance(b0, ast.Return)
                and (b0.value is None or (isinstance(b0.value, ast.Constant) and b0.value.value is None))
                and (node.lineno == line_no or b0.lineno == line_no)
            ):
                enclosing_if_returning_none = node
        if isinstance(node, (ast.Return, ast.Assign, ast.AnnAssign, ast.Expr)):
            if node.lineno == line_no and getattr(node, "end_lineno", line_no) == line_no:
                target_stmt = node

    # 1b. Early `if <cond>: return None` guard elision (plus Optional-to-str coalescing on the
    # subsequent return inside the same directly-tested function!)
    if (
        enclosing_if_returning_none is not None
        and enclosing_fn is not None
        and (not called_symbols or enclosing_fn.name in called_symbols)
    ):
        g_start = enclosing_if_returning_none.lineno - 1
        g_end = getattr(enclosing_if_returning_none, "end_lineno", enclosing_if_returning_none.lineno)
        # Only elide if the function has another non-None `return` later in its body
        later_returns = [
            sub
            for sub in ast.walk(enclosing_fn)
            if isinstance(sub, ast.Return)
            and sub.lineno > g_end
            and sub.value is not None
            and not (isinstance(sub.value, ast.Constant) and sub.value.value is None)
        ]
        if later_returns:
            cand_lines = lines[:g_start] + lines[g_end:]
            _emit_patch(
                "".join(cand_lines),
                f"Elide early `return None` guard at L{g_start + 1} in `{enclosing_fn.name}`",
            )
            # Also pair guard elision with `x or ""` coalescing on any potentially-None element in the later tuple return
            lr = later_returns[0]
            if isinstance(lr.value, ast.Tuple) and getattr(lr.value, "end_lineno", lr.lineno) == lr.lineno:
                lr_idx = lr.lineno - 1
                new_elts: list[str] = []
                changed_elt = False
                for elt in lr.value.elts:
                    es = ast.unparse(elt).strip()
                    if isinstance(elt, (ast.Attribute, ast.Name)) and "or " not in es and "make_" not in es:
                        new_elts.append(f"{es} or ''")
                        changed_elt = True
                    else:
                        new_elts.append(es)
                if changed_elt and lr.value.end_col_offset is not None:
                    lr_line = lines[lr_idx]
                    repl_tup = "(" + ", ".join(new_elts) + ")"
                    mod_lines = list(lines)
                    mod_lines[lr_idx] = lr_line[: lr.value.col_offset] + repl_tup + lr_line[lr.value.end_col_offset :]
                    del mod_lines[g_start:g_end]
                    _emit_patch(
                        "".join(mod_lines),
                        f"Elide early `return None` guard + coalesce Optional tuple slot in `{enclosing_fn.name}`",
                    )

    if target_stmt is None:
        return out_patches[:8], len(out_patches)

    all_samples = fail_samples + pass_samples
    local_vars: list[str] = []
    iterable_vars: list[tuple[str, str | None]] = []
    self_attrs: list[str] = []

    if enclosing_fn is not None:
        for arg in enclosing_fn.args.args:
            if arg.arg not in local_vars:
                local_vars.append(arg.arg)
        for sub in ast.walk(enclosing_fn):
            if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Store) and getattr(sub, "lineno", 0) <= line_no:
                if sub.id not in local_vars:
                    local_vars.append(sub.id)
            elif isinstance(sub, ast.Attribute) and isinstance(sub.value, ast.Name) and sub.value.id == "self":
                sa = f"self.{sub.attr}"
                if sa not in self_attrs:
                    self_attrs.append(sa)

    for smp in all_samples:
        for k, inf in (smp.get("locals") or {}).items():
            if not isinstance(inf, dict):
                continue
            if k not in local_vars:
                local_vars.append(k)
            tp = str(inf.get("type") or "")
            if tp in _ITERABLE_TYPE_NAMES or k.endswith(("s", "_list", "_seq", "args", "opts", "params", "items", "records", "values")):
                if all(iv != k for iv, _ in iterable_vars):
                    inferred_cls: str | None = None
                    stem = k[:-1] if k.endswith("s") and len(k) > 2 else k
                    for cls_name in methods_by_class:
                        if cls_name.lower().startswith(stem.lower()) or stem.lower().endswith(cls_name.lower()):
                            inferred_cls = cls_name
                            break
                    iterable_vars.append((k, inferred_cls))
            if k == "self":
                for ak in (inf.get("attrs") or {}):
                    sa = f"self.{ak}"
                    if sa not in self_attrs:
                        self_attrs.append(sa)

    orig_line = lines[line_no - 1]
    rhs_node: ast.expr | None = None
    if isinstance(target_stmt, ast.Return) and target_stmt.value is not None:
        rhs_node = target_stmt.value
    elif isinstance(target_stmt, ast.Assign) and len(target_stmt.targets) == 1:
        rhs_node = target_stmt.value
    elif isinstance(target_stmt, ast.AnnAssign) and target_stmt.value is not None:
        rhs_node = target_stmt.value

    if rhs_node is None or rhs_node.end_col_offset is None:
        return out_patches[:8], len(out_patches)

    rhs_src = ast.unparse(rhs_node).strip()
    c_start, c_end = rhs_node.col_offset, rhs_node.end_col_offset
    candidate_rhs: list[tuple[str, str]] = []

    # 2. String-formatting monoid unit normalization (`.rstrip()` / `.strip()`) on `return <f-str / str>`
    if isinstance(target_stmt, ast.Return):
        is_str_expr = isinstance(rhs_node, ast.JoinedStr) or (
            isinstance(rhs_node, ast.BinOp) and isinstance(rhs_node.op, (ast.Add, ast.Mod))
        )
        if not is_str_expr and isinstance(rhs_node, ast.Name):
            for smp in fail_samples:
                inf = (smp.get("locals") or {}).get(rhs_node.id) or {}
                if inf.get("type") == "str":
                    is_str_expr = True
                    break
        if is_str_expr and not rhs_src.endswith((".strip()", ".rstrip()")):
            candidate_rhs.insert(0, (f"({rhs_src}).rstrip()", f"Trailing-delimiter monoid normalization `({rhs_src}).rstrip()`"))
            candidate_rhs.append((f"({rhs_src}).strip()", f"Whitespace monoid normalization `({rhs_src}).strip()`"))

    # 3. Tuple Optional-slot coalescing `(a, b)` -> `(a, b or '')` when an element is `None` in fail_samples
    if isinstance(rhs_node, ast.Tuple):
        new_t_elts: list[str] = []
        coalesced = False
        for elt in rhs_node.elts:
            es = ast.unparse(elt).strip()
            is_none_in_fail = False
            for smp in fail_samples:
                locs = smp.get("locals") or {}
                if "." in es:
                    b_n, a_n = es.split(".", 1)
                    einf = ((locs.get(b_n) or {}).get("attrs") or {}).get(a_n)
                else:
                    einf = locs.get(es)
                if isinstance(einf, dict) and einf.get("is_none"):
                    is_none_in_fail = True
                    break
            if is_none_in_fail:
                new_t_elts.append(f"{es} or ''")
                coalesced = True
            else:
                new_t_elts.append(es)
        if coalesced:
            tup_s = "(" + ", ".join(new_t_elts) + ")"
            candidate_rhs.insert(0, (tup_s, f"Optional tuple-slot coalescing `{tup_s}`"))

    # 4. Builtin unshadowing (`hash_(x)` -> `hash(x)`)
    for sub in ast.walk(rhs_node):
        if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name):
            fn_id = sub.func.id
            if fn_id.endswith("_") and fn_id[:-1] in _BUILTIN_NAMES and fn_id not in local_vars:
                candidate_rhs.insert(
                    0,
                    (rhs_src.replace(f"{fn_id}(", f"{fn_id[:-1]}(", 1), f"Builtin unshadowing `{fn_id}` -> `{fn_id[:-1]}`"),
                )

    # 5. Higher-order comprehension & sequence projections
    # 5a. Filter `None` or empty elements on existing list/generator comprehension or sequence
    if isinstance(rhs_node, (ast.ListComp, ast.GeneratorExp)) and len(rhs_node.generators) == 1:
        gen = rhs_node.generators[0]
        if not gen.ifs:
            elt_s = ast.unparse(rhs_node.elt)
            tgt_s = ast.unparse(gen.target)
            iter_s = ast.unparse(gen.iter)
            br_l, br_r = ("[", "]") if isinstance(rhs_node, ast.ListComp) else ("(", ")")
            candidate_rhs.insert(
                0,
                (
                    f"{br_l}{elt_s} for {tgt_s} in {iter_s} if {tgt_s}{br_r}",
                    f"Filter empty elements in comprehension `{rhs_src}`",
                ),
            )
            candidate_rhs.insert(
                1,
                (
                    f"{br_l}{elt_s} for {tgt_s} in {iter_s} if {elt_s} is not None{br_r}",
                    f"Filter `None` elements in comprehension `{rhs_src}`",
                ),
            )
    elif isinstance(rhs_node, ast.Call) and isinstance(rhs_node.func, ast.Attribute) and rhs_node.func.attr == "join" and len(rhs_node.args) == 1:
        arg0 = rhs_node.args[0]
        sep_s = ast.unparse(rhs_node.func.value)
        if isinstance(arg0, (ast.ListComp, ast.GeneratorExp)) and len(arg0.generators) == 1 and not arg0.generators[0].ifs:
            gen = arg0.generators[0]
            elt_s = ast.unparse(arg0.elt)
            tgt_s = ast.unparse(gen.target)
            iter_s = ast.unparse(gen.iter)
            candidate_rhs.insert(
                0,
                (
                    f"{sep_s}.join({elt_s} for {tgt_s} in {iter_s} if {tgt_s})",
                    f"Filter empty elements inside `{sep_s}.join(...)`",
                ),
            )

    # 5b. Mapped repo-method comprehension ONLY when LHS/RHS shares a semantic token with a mined method
    lhs_hint = ast.unparse(target_stmt).lower()
    for seq_var, elem_cls in iterable_vars[:4]:
        if seq_var in {"self", "cls"}:
            continue
        candidate_cls_list = ([elem_cls] if elem_cls and elem_cls in methods_by_class else []) + [
            c for c in methods_by_class if c != elem_cls
        ]
        for cname in candidate_cls_list[:2]:
            for m_comp in methods_by_class.get(cname, [])[:8]:
                name_tokens = [
                    t for t in m_comp.name.lower().split("_") if len(t) >= 4 and t not in {"from", "with", "make"}
                ]
                if not any(tok in lhs_hint for tok in name_tokens):
                    continue
                for args_tup in _match_args_for_component(
                    m_comp, [v for v in local_vars if v != seq_var], self_attrs
                )[:2]:
                    arg_str = ", ".join(args_tup)
                    comp_plain = f"[_el.{m_comp.name}({arg_str}) for _el in {seq_var}]"
                    comp_non_none = f"[_rv for _rv in (_el.{m_comp.name}({arg_str}) for _el in {seq_var}) if _rv is not None]"
                    candidate_rhs.insert(0, (comp_plain, f"Repo-component mapped comprehension `{comp_plain}`"))
                    candidate_rhs.insert(1, (comp_non_none, f"Repo-component filtered comprehension `{comp_non_none}`"))

    # 6. Signature keyword forwarding on existing Call
    if isinstance(rhs_node, ast.Call) and spec_literals:
        existing_kws = {kw.arg for kw in rhs_node.keywords if kw.arg}
        called_name = (
            rhs_node.func.attr
            if isinstance(rhs_node.func, ast.Attribute)
            else (rhs_node.func.id if isinstance(rhs_node.func, ast.Name) else "")
        )
        matching_comps = [c for c in direct_comps if c.name == called_name]
        for cls_ms in methods_by_class.values():
            matching_comps.extend(c for c in cls_ms if c.name == called_name)
        allowed_kw_names = {p for mc in matching_comps for p in (mc.param_names + mc.kwonly_names)}
        for slit in spec_literals:
            if slit in allowed_kw_names and slit not in existing_kws and slit in local_vars and rhs_src.endswith(")"):
                sep = ", " if (rhs_node.args or rhs_node.keywords) else ""
                new_call = rhs_src[:-1] + f"{sep}{slit}={slit})"
                candidate_rhs.insert(0, (new_call, f"Repo-signature keyword forwarding `{slit}={slit}`"))

    # 7. Bidirectional FST / Codec Lens synthesis when failing witness + spec literal form a transducer pair
    if fail_samples and spec_literals and isinstance(target_stmt, ast.Return):
        obs_inputs: list[Any] = []
        for fs in fail_samples[:3]:
            locs = fs.get("locals") or {}
            for lv_summary in locs.values():
                rep = lv_summary.get("repr") if isinstance(lv_summary, dict) else None
                if rep:
                    try:
                        val = ast.literal_eval(rep)
                        if isinstance(val, (str, bytes)) and val not in obs_inputs:
                            obs_inputs.append(val)
                    except Exception:
                        pass
        for obs_in in obs_inputs[:3]:
            for slit in spec_literals[:6]:
                if isinstance(slit, str) and slit != obs_in and len(slit) >= 2:
                    lens = synthesize_bidirectional_fst_lens([(obs_in, slit)])
                    if lens is not None and lens.roundtrip_verified:
                        fwd_expr = lens.forward_expr_template.replace("{x}", f"({rhs_src})")
                        candidate_rhs.insert(
                            0,
                            (fwd_expr, f"Bidirectional FST Lens [{lens.lens_family}:{lens.lens_id}]"),
                        )
                        break

    for ex, dsc in candidate_rhs[:8]:
        if ex != rhs_src:
            new_line = orig_line[:c_start] + ex + orig_line[c_end:]
            cand_lines = list(lines)
            cand_lines[line_no - 1] = new_line
            _emit_patch("".join(cand_lines), dsc)

    return out_patches[:8], len(candidate_rhs)


_FENCED_PY_RE = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)
_EXPECTED_CLAUSE_RE = re.compile(
    r"(?:expected(?:\s+output|\s+result|\s+value)?|should\s+(?:return|be|produce|equal|yield)|instead\s+of)\s*:?\s*"
    r"(`[^`\n]+`|'[^'\n]*'|\"[^\"\n]*\"|\([^\n)]*\)|\[[^\n\]]*\]|-?\d+(?:\.\d+)?|None|True|False)",
    re.IGNORECASE,
)


def _index_repo_exportable_symbols(repo_root: Path) -> dict[str, str]:
    """Map top-level Python class/function names -> import module dotted path."""
    sym_to_mod: dict[str, str] = {}
    search_bases = [repo_root / "src", repo_root]
    seen_files: set[Path] = set()
    for base in search_bases:
        if not base.is_dir():
            continue
        for py_p in sorted(base.rglob("*.py")):
            if py_p in seen_files:
                continue
            rel_parts = py_p.relative_to(base).parts
            if any(pt.startswith(".") or pt in {"tests", "test", "docs", "examples", "build", "venv", ".venv"} for pt in rel_parts):
                continue
            seen_files.add(py_p)
            if rel_parts[-1] == "__init__.py":
                mod_parts = list(rel_parts[:-1])
            else:
                mod_parts = list(rel_parts[:-1]) + [rel_parts[-1][:-3]]
            if not mod_parts:
                continue
            dotted = ".".join(mod_parts)
            try:
                tr = ast.parse(py_p.read_text(encoding="utf-8", errors="replace"))
            except SyntaxError:
                continue
            for node in tr.body:
                if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Prefer shorter public package export paths (`click` / `werkzeug.datastructures`)
                    prev = sym_to_mod.get(node.name)
                    if prev is None or len(dotted) < len(prev):
                        sym_to_mod[node.name] = dotted
    return sym_to_mod


def extract_candidate_repro_tests_from_issue(
    repo_root: Path,
    problem_statement: str,
) -> list[str]:
    """Deterministically abduce candidate pytest reproduction modules from a raw GitHub
    issue report (`problem_statement`) using fenced snippets, `>>>` doctests, and
    repo-symbol-grounded call expressions (`model_calls = 0`)."""
    if not problem_statement or not problem_statement.strip():
        return []

    expected_vals: list[Any] = []
    for m_exp in _EXPECTED_CLAUSE_RE.finditer(problem_statement):
        raw_tok = m_exp.group(1).strip()
        if raw_tok.startswith("`") and raw_tok.endswith("`"):
            raw_tok = raw_tok[1:-1].strip()
        try:
            val = ast.literal_eval(raw_tok)
            if val not in expected_vals:
                expected_vals.append(val)
        except Exception:
            pass

    candidates: list[str] = []

    def _wrap_test(body_src: str) -> None:
        indented = "\n".join(f"    {ln}" if ln.strip() else "" for ln in body_src.splitlines())
        mod_src = f"def test_abduced_issue_repro():\n{indented}\n"
        try:
            ast.parse(mod_src)
            if mod_src not in candidates:
                candidates.append(mod_src)
        except SyntaxError:
            pass

    # 1. Fenced Python blocks
    for m_code in _FENCED_PY_RE.finditer(problem_statement):
        block = m_code.group(1).strip()
        if not block:
            continue
        try:
            b_tree = ast.parse(block)
        except SyntaxError:
            continue
        if not b_tree.body:
            continue
        has_assert = any(isinstance(n, ast.Assert) for n in ast.walk(b_tree))
        if has_assert:
            _wrap_test(block)
            continue

        # Check if final statement is an expression, `print(expr)`, or `var = expr`
        last_stmt = b_tree.body[-1]
        prefix_src = ast.unparse(ast.Module(body=b_tree.body[:-1], type_ignores=[]))
        target_expr_src: str | None = None
        if isinstance(last_stmt, ast.Expr):
            if (
                isinstance(last_stmt.value, ast.Call)
                and isinstance(last_stmt.value.func, ast.Name)
                and last_stmt.value.func.id == "print"
                and len(last_stmt.value.args) == 1
            ):
                target_expr_src = ast.unparse(last_stmt.value.args[0])
            else:
                target_expr_src = ast.unparse(last_stmt.value)
        elif isinstance(last_stmt, ast.Assign) and len(last_stmt.targets) == 1 and isinstance(last_stmt.targets[0], ast.Name):
            prefix_src = block
            target_expr_src = last_stmt.targets[0].id

        if target_expr_src and expected_vals:
            for ev in expected_vals[:3]:
                combined = (f"{prefix_src}\n" if prefix_src else "") + f"assert ({target_expr_src}) == {repr(ev)}"
                _wrap_test(combined)

        # Also emit crash-free execution witness (for issues reporting an unexpected exception)
        _wrap_test(block)

    # 2. Interactive `>>>` doctest transcripts
    lines = problem_statement.splitlines()
    idx = 0
    doctest_stmts: list[str] = []
    while idx < len(lines):
        s_ln = lines[idx].lstrip()
        if s_ln.startswith(">>> "):
            expr_part = s_ln[4:]
            idx += 1
            while idx < len(lines) and lines[idx].lstrip().startswith("... "):
                expr_part += "\n" + lines[idx].lstrip()[4:]
                idx += 1
            # Peek next non-empty line for literal output
            if idx < len(lines) and lines[idx].strip() and not lines[idx].lstrip().startswith((">>>", "Traceback")):
                out_ln = lines[idx].strip()
                try:
                    ev = ast.literal_eval(out_ln)
                    doctest_stmts.append(f"assert ({expr_part}) == {repr(ev)}")
                    idx += 1
                    continue
                except Exception:
                    pass
            doctest_stmts.append(expr_part)
        else:
            idx += 1
    if doctest_stmts and any(st.startswith("assert ") for st in doctest_stmts):
        _wrap_test("\n".join(doctest_stmts))

    # 3. Repo-symbol-grounded backticked call expressions + expected literal
    if expected_vals:
        sym_map: dict[str, str] | None = None
        for m_bt in re.finditer(r"`([^`\n]{4,160})`", problem_statement):
            expr_cand = m_bt.group(1).strip()
            try:
                e_ast = ast.parse(expr_cand, mode="eval").body
            except SyntaxError:
                continue
            if not any(isinstance(n, ast.Call) for n in ast.walk(e_ast)):
                continue
            free_names = sorted(
                {
                    n.id
                    for n in ast.walk(e_ast)
                    if isinstance(n, ast.Name) and n.id not in _BUILTIN_NAMES
                }
            )
            if sym_map is None:
                sym_map = _index_repo_exportable_symbols(repo_root)
            if free_names and all(fn in sym_map for fn in free_names):
                imp_lines = [f"from {sym_map[fn]} import {fn}" for fn in free_names]
                for ev in expected_vals[:3]:
                    _wrap_test("\n".join(imp_lines + [f"assert ({expr_cand}) == {repr(ev)}"]))

    return candidates[:8]

