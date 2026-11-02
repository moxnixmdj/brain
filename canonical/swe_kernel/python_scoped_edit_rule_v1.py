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
            # A prefix of executable statements was inserted before unchanged body `bb[0]`.
            anchor = ab[len(ab) - len(bb)]
            b0, b1 = locate(bb[0])
            a0, _ = a_locate(ab[0])
            a_anc0, a1 = a_locate(anchor)
            if (before[:b0] == after[:a0]
                    and (len(bb) == 1 or before[b0:b1] == after[a_anc0:a1])
                    and before[b1:] == after[a1:]):
                scope = 'entry'
                start, end, a_start, a_end = b0, b1, a0, a1
            else:
                # Mid-function guard/statement insertion before statement `bb[k]` (`k > 0`),
                # where prefix `bb[:k]` and suffix `bb[k:]` are unchanged outside the insertion point.
                ins_count = len(ab) - len(bb)
                for k in range(1, len(bb)):
                    bk0, bk1 = locate(bb[k])
                    ak0, _ = a_locate(ab[k])
                    ak_anc0, ak1 = a_locate(ab[k + ins_count])
                    if (before[start:bk0] == after[a_start:ak0]
                            and before[bk0:bk1] == after[ak_anc0:ak1]
                            and before[bk1:end] == after[ak1:a_end]):
                        scope = 'mid_insertion'
                        start, end, a_start, a_end = bk0, bk1, ak0, ak1
                        break
        elif bb and len(ab) == len(bb) and (len(bb) > 3 or (end - start) > 320):
            narrowed = _narrow_statement_edit(
                before, after, bb, ab, locate, a_locate, start, end, a_start, a_end
            )
            if narrowed is not None:
                scope = 'statement'
                start, end, a_start, a_end = narrowed
        initial = None if scope == 'statement' else {name: f'?id{i}' for i, (_, _, name) in enumerate(parameters(fn))}
        rule = builder(dedented(before[start:end]).strip(),
                       dedented(after[a_start:a_end]).strip(),
                       language='python', error_class=error_class,
                       _prepared=True, _python_lex=True, _initial_ident_map=initial)
        if rule is None:
            return None
        param_bindings = (
            []
            if scope == 'statement'
            else [[initial[name], kind, i] for kind, i, name in parameters(fn)]
        )
        rule.update(pattern_format=FORMAT, python_scope=scope,
                    parameter_bindings=param_bindings,
                    generator=generator(fn), asynchronous=isinstance(fn, ast.AsyncFunctionDef))
        rule['skill_id'] = identity(rule)
        return rule
    except (SyntaxError, ValueError, tokenize.TokenError, IndentationError):
        return None


def _narrow_statement_edit(before, after, bb, ab, locate, a_locate, start, end, a_start, a_end):
    """Narrow a single-statement or single `if/elif` header edit inside a multi-statement function/method."""
    if len(bb) != len(ab) or not bb:
        return None
    diffs = []
    for k, (bs, as_) in enumerate(zip(bb, ab)):
        bk0, bk1 = locate(bs)
        ak0, ak1 = a_locate(as_)
        if before[bk0:bk1] != after[ak0:ak1]:
            diffs.append((k, bs, as_, bk0, bk1, ak0, ak1))
    if len(diffs) != 1:
        return None
    _, bs, as_, bk0, bk1, ak0, ak1 = diffs[0]
    if before[start:bk0] != after[a_start:ak0] or before[bk1:end] != after[ak1:a_end]:
        return None

    if isinstance(bs, ast.If) and isinstance(as_, ast.If) and bs.body and as_.body:
        b_b0 = locate(bs.body[0])[0]
        a_b0 = a_locate(as_.body[0])[0]
        # 1) Only the `if`/`elif` condition header changed while body + orelse stayed identical
        if before[b_b0:bk1] == after[a_b0:ak1]:
            bh_end = before.find('\n', bk0, b_b0)
            ah_end = after.find('\n', ak0, a_b0)
            if bh_end > bk0 and ah_end > ak0 and before[bh_end:b_b0] == after[ah_end:a_b0]:
                return bk0, bh_end, ak0, ah_end
        # 2) Recurse into `body` if header + orelse match
        if len(bs.body) == len(as_.body):
            sub = _narrow_statement_edit(
                before, after, bs.body, as_.body, locate, a_locate, bk0, bk1, ak0, ak1
            )
            if sub is not None:
                return sub
        # 3) Recurse into `orelse` (`elif` chains or `else` blocks) if header + body match
        if bs.orelse and len(bs.orelse) == len(as_.orelse):
            sub = _narrow_statement_edit(
                before, after, bs.orelse, as_.orelse, locate, a_locate, bk0, bk1, ak0, ak1
            )
            if sub is not None:
                return sub
    elif (
        isinstance(bs, (ast.For, ast.AsyncFor, ast.While, ast.With, ast.AsyncWith))
        and type(bs) is type(as_)
        and len(bs.body) == len(as_.body)
    ):
        sub = _narrow_statement_edit(
            before, after, bs.body, as_.body, locate, a_locate, bk0, bk1, ak0, ak1
        )
        if sub is not None:
            return sub

    return bk0, bk1, ak0, ak1


def _statement_windows(source, stmts, locate):
    """Yield `(start, end)` spans for statements and `if/elif` condition headers recursively."""
    out = []
    seen = set()

    def _visit(items):
        for st in items:
            s0, s1 = locate(st)
            if isinstance(st, ast.If) and st.body:
                b0 = locate(st.body[0])[0]
                h_end = source.find('\n', s0, b0)
                if h_end > s0 and (s0, h_end) not in seen:
                    seen.add((s0, h_end))
                    out.append((s0, h_end))
                _visit(st.body)
                if st.orelse:
                    _visit(st.orelse)
            elif isinstance(st, (ast.For, ast.AsyncFor, ast.While, ast.With, ast.AsyncWith)):
                _visit(st.body)
                if getattr(st, 'orelse', None):
                    _visit(st.orelse)
            elif isinstance(st, ast.Try):
                _visit(st.body)
                for h in st.handlers:
                    _visit(h.body)
                if st.orelse:
                    _visit(st.orelse)
                if st.finalbody:
                    _visit(st.finalbody)
            if (s0, s1) not in seen and '\n' not in source[s0:s1].strip():
                seen.add((s0, s1))
                out.append((s0, s1))

    _visit(stmts)
    return out


def candidates(source, rule, matcher):
    """Enumerate scoped locations; the caller must behaviorally verify each."""
    try:
        rows = functions(source)
        for _, fn, (start, end), locate in rows:
            params = {(kind, i): name for kind, i, name in parameters(fn)}
            required = {(kind, i) for _, kind, i in rule['parameter_bindings']}
            is_stmt_scope = rule['python_scope'] == 'statement'
            param_ok = required.issubset(set(params)) if is_stmt_scope else (set(params) == required)
            if (not param_ok or generator(fn) != rule['generator']
                    or isinstance(fn, ast.AsyncFunctionDef) != rule['asynchronous']):
                continue
            bindings = {hole: params[(kind, i)] for hole, kind, i in rule['parameter_bindings']}
            if rule['python_scope'] == 'entry':
                executable = body(fn)
                if not executable:
                    continue
                windows = [locate(executable[0])]
            elif rule['python_scope'] == 'mid_insertion':
                executable = body(fn)
                windows = [locate(st) for st in executable]
            elif is_stmt_scope:
                windows = _statement_windows(source, body(fn), locate)
            elif rule['python_scope'] == 'function':
                windows = [(start, end)]
            else:
                return
            for w_start, w_end in windows:
                window = source[w_start:w_end]
                changed = matcher(window, rule, _python_lex=True, _initial_bindings=bindings, _anchored=True)
                if changed is not None:
                    # Match indentation of `w_start` when inserting multi-line blocks inside a body
                    line_start = source.rfind('\n', 0, w_start) + 1
                    indent = source[line_start:w_start]
                    if '\n' in changed and indent and all(c in ' \t' for c in indent):
                        c_lines = changed.splitlines(keepends=True)
                        reindented = [c_lines[0]] + [
                            (indent + ln if ln.strip() else ln) for ln in c_lines[1:]
                        ]
                        changed = ''.join(reindented)
                    candidate = source[:w_start] + changed + source[w_end:]
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
