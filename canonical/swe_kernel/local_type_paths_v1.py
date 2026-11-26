"""Backward search from a return annotation to an in-scope argument.

Edges are the repository's own undecorated unary functions, not a library of
handwritten adapters. Type agreement only licenses *trying* a term. The caller
must still verify the actual edit. Currently module-local, nominal annotations,
one or two calls, single-line returns; never import the inspected module.
"""
from __future__ import annotations

import ast
import hashlib
from collections import Counter, defaultdict


def _nominal(node):
    return node.id if isinstance(node, ast.Name) and node.id not in ('Any', 'Never') else None


def return_paths(source, lines, *, budget=12, tree=None):
    try:
        tree = tree or ast.parse(source)
    except SyntaxError:
        return
    if budget <= 0:
        return
    selected = set(lines)
    defs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    # Ambiguous module bindings (including imports and assignments) aren't edges.
    bindings = Counter()
    for stmt in tree.body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bindings[stmt.name] += 1
        elif isinstance(stmt, (ast.ImportFrom, ast.Import)):
            bindings.update(a.asname or a.name.split('.')[0] for a in stmt.names)
        else:
            bindings.update(n.id for n in ast.walk(stmt) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store))
    suppliers = defaultdict(list)
    for fn in defs:
        sig = fn.args
        args = [*sig.posonlyargs, *sig.args]
        if (bindings[fn.name] == 1 and len(args) == 1 and not sig.vararg and not sig.kwarg
                and not sig.kwonlyargs and not fn.decorator_list and not sig.defaults
                and _nominal(fn.returns) and _nominal(args[0].annotation)):
            suppliers[_nominal(fn.returns)].append((fn.name, _nominal(args[0].annotation), fn.lineno))

    body = source.encode('utf-8').splitlines(keepends=True)
    emitted = set()
    for fn in defs:
        goal_type = _nominal(fn.returns)
        args = {a.arg: _nominal(a.annotation) for a in (*fn.args.posonlyargs, *fn.args.args, *fn.args.kwonlyargs)}
        shadowed = set(args) | {n.id for n in ast.walk(fn) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)}
        if not goal_type or not suppliers[goal_type] or not any(fn.lineno <= n <= fn.end_lineno for n in selected):
            continue
        # Do not touch returns belonging to nested functions/classes, or a
        # return in a different branch just because its function was reached.
        todo = list(fn.body)
        while todo:
            n = todo.pop(0)
            if isinstance(n, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                continue
            todo.extend(ast.iter_child_nodes(n))
            if not (isinstance(n, ast.Return) and n.lineno in selected and n.value and n.lineno == n.end_lineno):
                continue
            for outer, mid, outer_line in suppliers[goal_type]:
                if outer == fn.name or outer in shadowed:
                    continue
                paths = [([(outer, outer_line)], mid)]
                paths.extend(([(outer, outer_line), (inner, inner_line)], inp)
                             for inner, inp, inner_line in suppliers[mid] if inner not in {outer, fn.name} | shadowed)
                for chain, needed in paths:
                    for arg, given in args.items():
                        if given != needed:
                            continue
                        expr = arg
                        for call, _ in reversed(chain):
                            expr = f'{call}({expr})'
                        line = body[n.lineno-1]
                        replacement = line[:n.value.col_offset] + expr.encode() + line[n.value.end_col_offset:]
                        if replacement == line or (n.lineno, expr) in emitted:
                            continue
                        emitted.add((n.lineno, expr))
                        patch = b''.join([*body[:n.lineno-1], replacement, *body[n.lineno:]]).decode()
                        yield patch, {'owner': fn.name, 'line': n.lineno, 'parameter': arg, 'input_type': given,
                                      'output_type': goal_type, 'suppliers_inner_first': list(reversed(chain)),
                                      'source_sha256': hashlib.sha256(source.encode()).hexdigest()}
                        if len(emitted) >= budget:
                            return
