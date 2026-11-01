"""Conservative source contracts shared by SWE producers and acceptance checks.

These checks establish bounded structural obligations, not universal Python
program equivalence. Unknown effects/domains are refused or use the original
implementation as a runtime fallback. No repository module is executed here.
"""
from __future__ import annotations

import ast
from pathlib import Path
from typing import Iterable


def body_without_docstring(fn: ast.FunctionDef) -> list[ast.stmt]:
    body = list(fn.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
        body.pop(0)
    return body


def fresh_name(tree: ast.AST, stem: str) -> str:
    occupied = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    occupied.update(n.arg for n in ast.walk(tree) if isinstance(n, ast.arg))
    occupied.update(n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.ClassDef)))
    while stem in occupied or any(n.startswith(stem + '_') for n in occupied):
        stem += '_'
    return stem


def memoization_safe(tree: ast.Module, fn: ast.FunctionDef, *, allow_helpers: bool = True) -> bool:
    """A deliberately small pure scalar/recursive arithmetic language.

    Mutable results, external reads, attributes, arbitrary calls, decorators,
    generators and writes to shared state are outside this contract. Runtime
    caching is separately restricted to exact integers so custom equality/hash
    and mutable inputs still execute the original function.
    """
    if fn.decorator_list or fn.args.vararg or fn.args.kwarg:
        return False
    for default in fn.args.defaults + [d for d in fn.args.kw_defaults if d is not None]:
        try:
            value = ast.literal_eval(default)
        except (ValueError, TypeError):
            return False
        if value is not None and type(value) not in (int, float, bool, str):
            return False
    helpers = memoization_dependencies(tree, fn) if allow_helpers else {}
    parameters = {a.arg for a in fn.args.posonlyargs + fn.args.args + fn.args.kwonlyargs}
    locals_ = {n.id for s in fn.body for n in ast.walk(s) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)}
    allowed = (ast.Return, ast.If, ast.Assign, ast.AugAssign, ast.Expr, ast.Pass,
               ast.Name, ast.Constant, ast.BinOp, ast.UnaryOp, ast.BoolOp,
               ast.Compare, ast.IfExp, ast.Call, ast.Load, ast.Store,
               ast.operator, ast.unaryop, ast.boolop, ast.cmpop, ast.keyword)
    for statement in fn.body:
        for node in ast.walk(statement):
            if not isinstance(node, allowed):
                return False
            if isinstance(node, ast.Constant) and not (node.value is None or type(node.value) in (int, float, bool, str)):
                return False
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and node.id not in parameters | locals_ | {fn.name} | set(helpers):
                return False
            if isinstance(node, ast.Call) and not (isinstance(node.func, ast.Name) and node.func.id in {fn.name} | set(helpers)):
                return False
    return True


def memoization_dependencies(tree: ast.Module, fn: ast.FunctionDef) -> dict[str, ast.FunctionDef]:
    """Closed leaf arithmetic helpers, guarded by code/default identity at reuse."""
    result = {}
    called = {n.func.id for n in ast.walk(fn) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)} - {fn.name}
    for node in tree.body:
        if (isinstance(node, ast.FunctionDef) and node.name in called
                and not any(isinstance(n, ast.Call) for n in ast.walk(node))
                and memoization_safe(tree, node, allow_helpers=False)):
            result[node.name] = node
    return result


def sum_reduction(fn: ast.FunctionDef) -> str | None:
    """Recognize an additive reduction, not an arbitrary one-argument function."""
    if fn.decorator_list or len(fn.args.posonlyargs + fn.args.args) != 1 or fn.args.kwonlyargs or fn.args.vararg or fn.args.kwarg:
        return None
    param = (fn.args.posonlyargs + fn.args.args)[0].arg
    body = body_without_docstring(fn)
    if len(body) == 3:
        first, loop, last = body
        if (isinstance(first, ast.Assign) and len(first.targets) == 1 and isinstance(first.targets[0], ast.Name)
                and isinstance(first.value, ast.Constant) and type(first.value.value) is int and first.value.value == 0
                and isinstance(loop, ast.For) and isinstance(loop.target, ast.Name) and isinstance(loop.iter, ast.Name)
                and loop.iter.id == param and not loop.orelse and len(loop.body) == 1
                and len({param, first.targets[0].id, loop.target.id}) == 3):
            expected = ast.parse(f"{first.targets[0].id} += {loop.target.id}").body[0]
            returned = ast.parse(f"return {first.targets[0].id}").body[0]
            if ast.dump(loop.body[0]) == ast.dump(expected) and ast.dump(last) == ast.dump(returned):
                return 'sum'
    if len(body) != 1 or not isinstance(body[0], ast.Return):
        return None
    call = body[0].value
    if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id == 'sum' and len(call.args) == 1 and not call.keywords):
        return None
    arg = call.args[0]
    if isinstance(arg, ast.Name) and arg.id == param:
        return 'sum'
    if isinstance(arg, ast.GeneratorExp) and len(arg.generators) == 1:
        gen = arg.generators[0]
        if isinstance(gen.target, ast.Name) and isinstance(gen.iter, ast.Name) and gen.iter.id == param and not gen.ifs and not gen.is_async:
            expr = arg.elt
            if (isinstance(expr, ast.Call) and isinstance(expr.func, ast.Name) and expr.func.id == 'abs'
                    and len(expr.args) == 1 and not expr.keywords and isinstance(expr.args[0], ast.Name) and expr.args[0].id == gen.target.id):
                return 'abs_sum'
    return None


def referenced_names(trees: Iterable[ast.Module]) -> set[str]:
    """Reuse the cross-file repair's conservative export/reference rules."""
    refs: set[str] = set()
    for tree in trees:
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                refs.add(node.id)
            elif isinstance(node, ast.Attribute):
                refs.add(node.attr)
            elif isinstance(node, ast.ImportFrom):
                refs.update(a.name for a in node.names)
            elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                if any(isinstance(t, ast.Name) and t.id == '__all__' for t in targets):
                    try:
                        exports = ast.literal_eval(node.value)
                    except (ValueError, TypeError):
                        exports = None
                    if isinstance(exports, (list, tuple, set)) and all(isinstance(v, str) for v in exports):
                        refs.update(exports)
                    else:
                        refs.update(n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)))
    return refs


def implicitly_removable(fn: ast.AST, refs: set[str]) -> bool:
    return (isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef))
            and fn.name.startswith('_') and not fn.name.startswith('__')
            and fn.name not in refs and not fn.decorator_list)


def split_is_self_contained(tree: ast.Module, funcs: list[ast.FunctionDef]) -> bool:
    import builtins
    module_bindings = {n.id for s in tree.body for n in ast.walk(s) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)}
    module_bindings.update(n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)))
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            module_bindings.update(a.asname or a.name.split('.')[0] for a in node.names)
    for fn in funcs:
        if fn.decorator_list or any(isinstance(n, (ast.Global, ast.Nonlocal)) for n in ast.walk(fn)):
            return False
        local = {a.arg for a in ast.walk(fn) if isinstance(a, ast.arg)}
        local.update(n.id for n in ast.walk(fn) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store))
        loads = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
        # Including defaults and annotations is conservative: their original
        # evaluation scope must also remain valid in the extracted module.
        free = loads - local - {fn.name}
        if free & module_bindings or free - set(dir(builtins)):
            return False
    return True


class FileEdits:
    """Stage all bytes before replacing files; restore on exception/refusal.

    This is exception-safe multi-file editing, not a power-loss atomic filesystem
    transaction. Symlinks and non-regular destinations are never followed.
    """
    def __init__(self, edits: dict[Path, bytes]):
        self.edits = edits
        self.before: dict[Path, tuple[bytes, object] | None] = {}
        self.committed = False
        self.applied: list[Path] = []

    def __enter__(self):
        import os
        import tempfile
        staged: dict[Path, Path] = {}
        try:
            for path, data in self.edits.items():
                if path.is_symlink() or (path.exists() and not path.is_file()):
                    raise ValueError('NON_REGULAR_EDIT_TARGET:' + str(path))
                self.before[path] = (path.read_bytes(), path.stat()) if path.exists() else None
                fd, raw = tempfile.mkstemp(prefix='.brain-edit-', dir=path.parent)
                stage = Path(raw)
                staged[path] = stage
                with os.fdopen(fd, 'wb') as stream:
                    stream.write(data)
                    stream.flush()
                if self.before[path] is not None:
                    os.chmod(stage, self.before[path][1].st_mode & 0o7777)
            for path, stage in staged.items():
                os.replace(stage, path)
                self.applied.append(path)
        except BaseException:
            self._restore()
            raise
        finally:
            for stage in staged.values():
                stage.unlink(missing_ok=True)
        return self

    def commit(self):
        self.committed = True

    def _restore(self):
        import os
        for path in reversed(self.applied):
            prior = self.before[path]
            if prior is None:
                path.unlink(missing_ok=True)
            else:
                data, stat = prior
                import tempfile
                fd, raw = tempfile.mkstemp(prefix='.brain-restore-', dir=path.parent)
                stage = Path(raw)
                try:
                    with os.fdopen(fd, 'wb') as stream:
                        stream.write(data)
                    os.chmod(stage, stat.st_mode & 0o7777)
                    os.replace(stage, path)
                finally:
                    stage.unlink(missing_ok=True)
                os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))

    def __exit__(self, typ, value, tb):
        if not self.committed or typ is not None:
            self._restore()
        return False
