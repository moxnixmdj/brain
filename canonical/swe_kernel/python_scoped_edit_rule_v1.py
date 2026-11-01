"""Bounded Python windows for the existing token-rule/store/oracle machinery.

Entry insertions bind function parameters by signature position, not by training
names. Other supported changes use one complete function window. No AST unparse
or whole-file normalization: bytes outside the selected edit are preserved.
"""
from __future__ import annotations

import ast
import builtins
import io
import keyword
import textwrap
import tokenize

FORMAT = 'python_scoped_edit_v1'
BUILTINS = frozenset(dir(builtins))


def tokens(source, keep):
    """Python's lexer with exact whitespace/comment/literal spans."""
    lines = source.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    result = []
    position = 0
    for t in tokenize.generate_tokens(io.StringIO(source).readline):
        if t.type in (tokenize.ENDMARKER, tokenize.DEDENT) or not t.string:
            continue
        start = offsets[t.start[0] - 1] + t.start[1]
        end = offsets[t.end[0] - 1] + t.end[1]
        if start > position:
            result.append(('ws', source[position:start], position, start))
        if t.type == tokenize.NAME:
            kind = 'kw' if (t.string in keep or t.string in BUILTINS or
                            keyword.iskeyword(t.string) or keyword.issoftkeyword(t.string)) else 'ident'
        elif t.type == tokenize.NUMBER:
            kind = 'num'
        elif t.type == tokenize.STRING:
            kind = 'str'
        elif t.type == tokenize.OP:
            kind = 'op'
        elif t.type in (tokenize.NL, tokenize.NEWLINE, tokenize.INDENT):
            kind = 'ws'
        else:
            kind = 'other'
        result.append((kind, t.string, start, end))
        position = end
    return result


def parameters(fn):
    groups = [('posonly', fn.args.posonlyargs), ('positional', fn.args.args),
              ('kwonly', fn.args.kwonlyargs)]
    out = [(kind, i, arg.arg) for kind, args in groups for i, arg in enumerate(args)]
    if fn.args.vararg:
        out.append(('vararg', 0, fn.args.vararg.arg))
    if fn.args.kwarg:
        out.append(('kwarg', 0, fn.args.kwarg.arg))
    return out


def generator(fn):
    pending = list(fn.body)
    while pending:
        n = pending.pop()
        if isinstance(n, (ast.Yield, ast.YieldFrom)):
            return True
        if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            pending.extend(ast.iter_child_nodes(n))
    return False


def body(fn):
    nodes = fn.body
    if (nodes and isinstance(nodes[0], ast.Expr) and isinstance(nodes[0].value, ast.Constant)
            and isinstance(nodes[0].value.value, str)):
        nodes = nodes[1:]
    return nodes


def functions(source):
    lines = source.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))

    def span(node):
        # AST columns are UTF-8 byte offsets, lexer columns are characters.
        end = offsets[node.end_lineno - 1] + len(
            lines[node.end_lineno - 1].encode('utf-8')[:node.end_col_offset].decode('utf-8'))
        return offsets[node.lineno - 1], end

    rows = []
    def visit(node, path):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                key = (*path, child.name)
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    rows.append((key, child, span(child), span))
                visit(child, key)
            else:
                visit(child, path)
    visit(ast.parse(source), ())
    return rows


def dedented(source):
    if '\r\n' in source:
        normalized = source.replace('\r\n', '\n')
        if '\n' in source.replace('\r\n', ''):
            raise ValueError('Mixed newline window is not supported')
        return textwrap.dedent(normalized).replace('\n', '\r\n')
    return textwrap.dedent(source)


def compile_rule(before, after, error_class, builder, identity):
    """Recognize only one changed function with byte-identical outside context."""
    try:
        bs = functions(before)
        aa = {key: (fn, span, locate) for key, fn, span, locate in functions(after)}
        choices = []
        for key, fn, (start, end), locate in bs:
            if key not in aa:
                continue
            afn, (a_start, a_end), a_locate = aa[key]
            if (before[:start] != after[:a_start] or before[end:] != after[a_end:]
                    or before[start:end] == after[a_start:a_end]):
                continue
            choices.append((end - start, fn, start, end, locate, afn, a_start, a_end, a_locate))
        if not choices:
            return None
        _, fn, start, end, locate, afn, a_start, a_end, a_locate = min(choices, key=lambda x: x[0])
        if [(k, i) for k, i, _ in parameters(fn)] != [(k, i) for k, i, _ in parameters(afn)]:
            return None
        scope = 'function'
        bb, ab = body(fn), body(afn)
        if bb and len(ab) > len(bb):
            # A prefix of executable statements was inserted before unchanged body.
            anchor = ab[len(ab) - len(bb)]
            b0, b1 = locate(bb[0])
            a0, _ = a_locate(ab[0])
            _, a1 = a_locate(anchor)
            if before[:b0] == after[:a0] and before[b1:] == after[a1:]:
                scope = 'entry'
                start, end, a_start, a_end = b0, b1, a0, a1
        initial = {name: f'?id{i}' for i, (_, _, name) in enumerate(parameters(fn))}
        rule = builder(dedented(before[start:end]).strip(),
                       dedented(after[a_start:a_end]).strip(),
                       language='python', error_class=error_class,
                       _prepared=True, _python_lex=True, _initial_ident_map=initial)
        if rule is None:
            return None
        rule.update(pattern_format=FORMAT, python_scope=scope,
                    parameter_bindings=[[initial[name], kind, i] for kind, i, name in parameters(fn)],
                    generator=generator(fn), asynchronous=isinstance(fn, ast.AsyncFunctionDef))
        rule['skill_id'] = identity(rule)
        return rule
    except (SyntaxError, ValueError, tokenize.TokenError, IndentationError):
        return None


def candidates(source, rule, matcher):
    """Enumerate scoped locations; the caller must behaviorally verify each."""
    try:
        rows = functions(source)
        for _, fn, (start, end), locate in rows:
            params = {(kind, i): name for kind, i, name in parameters(fn)}
            required = {(kind, i) for _, kind, i in rule['parameter_bindings']}
            if (set(params) != required or generator(fn) != rule['generator']
                    or isinstance(fn, ast.AsyncFunctionDef) != rule['asynchronous']):
                continue
            bindings = {hole: params[(kind, i)] for hole, kind, i in rule['parameter_bindings']}
            if rule['python_scope'] == 'entry':
                executable = body(fn)
                if not executable:
                    continue
                start, end = locate(executable[0])
            elif rule['python_scope'] != 'function':
                return
            window = source[start:end]
            changed = matcher(window, rule, _python_lex=True, _initial_bindings=bindings, _anchored=True)
            if changed is not None:
                candidate = source[:start] + changed + source[end:]
                # Invalid indentation or lexical substitutions never reach execution.
                ast.parse(candidate)
                yield candidate
    except (SyntaxError, ValueError, KeyError, TypeError, tokenize.TokenError, IndentationError):
        return


def renamed(source, rename_map, keep):
    pieces = []
    position = 0
    for kind, value, start, end in tokens(source, keep):
        if kind == 'ident' and value in rename_map:
            pieces.extend((source[position:start], rename_map[value]))
            position = end
    pieces.append(source[position:])
    return ''.join(pieces)
