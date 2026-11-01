"""Postconditions checked from pre-execution source and actual output bytes.

The front-door caller captures the preimage itself, rather than trusting a
producer's success flag. These are bounded structural preservation contracts;
project tests and behavioral regression oracles remain separately necessary.
"""
from __future__ import annotations

import ast
import hashlib
from pathlib import Path

from canonical.swe_kernel import transform_contracts_v1 as contracts

PYTHON_OPERATIONS = frozenset({'memoize_function', 'add_thread_pool', 'release_gil', 'optimize_function', 'remove_dead_code', 'split_module'})


def _dump(node):
    return ast.dump(node, include_attributes=False)


def verify_python(before: str, after: str, operation: str, symbol: str = '') -> str:
    old, new = ast.parse(before), ast.parse(after)
    old_functions = {n.name:n for n in old.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    new_functions = {n.name:n for n in new.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    bound_imports = {a.asname or a.name for n in new.body if isinstance(n, ast.ImportFrom) for a in n.names}
    for name, fn in old_functions.items():
        protected = not name.startswith('_') or bool(fn.decorator_list)
        if protected and name not in new_functions and not (operation == 'split_module' and name in bound_imports):
            return 'PUBLIC_OR_DECORATED_API_REMOVED:' + name
    def exports(tree):
        return [_dump(n) for n in tree.body if isinstance(n, (ast.Assign, ast.AnnAssign, ast.AugAssign))
                and any(isinstance(t, ast.Name) and t.id == '__all__' for t in (n.targets if isinstance(n, ast.Assign) else [n.target]))]
    if exports(old) != exports(new):
        return 'EXPORT_CONTRACT_CHANGED'
    if operation in {'remove_dead_code', 'split_module'}:
        return ''
    selected = symbol if symbol and symbol != 'auto' else next(iter(old_functions), '')
    original = old_functions.get(selected)
    rewritten = new_functions.get(selected)
    if original is None or rewritten is None:
        return 'TRANSFORM_TARGET_FUNCTION_MISSING'
    if operation == 'memoize_function':
        if not contracts.memoization_safe(old, original):
            return 'MEMOIZATION_EFFECTS_UNPROVED'
        if [_dump(n) for n in rewritten.body] != [_dump(n) for n in original.body]:
            return 'MEMOIZATION_CHANGED_FUNCTION_BODY'
        if not rewritten.decorator_list:
            return 'MEMOIZATION_DECORATOR_MISSING'
    else:
        fallback = contracts.body_without_docstring(original)
        if [_dump(n) for n in rewritten.body[-len(fallback):]] != [_dump(n) for n in fallback]:
            return 'ORIGINAL_DOMAIN_FALLBACK_MISSING'
        if operation == 'add_thread_pool' and contracts.sum_reduction(original) is None:
            return 'PARALLEL_REDUCTION_CONTRACT_UNPROVED'
        if operation == 'release_gil' and contracts.sum_reduction(original) != 'sum':
            return 'NATIVE_SUM_CONTRACT_UNPROVED'
    return ''


def verify_typescript(before: str, after: str) -> str:
    from canonical.runtime import tree_sitter_swe_kernel_v1 as syntax
    def data_tokens(source):
        raw = source.encode('utf-8')
        tree = syntax.parse_bytes('typescript', raw)
        if tree.root_node.has_error:
            raise ValueError('TS_PARSE_FAILED')
        result = []
        stack = [tree.root_node]
        while stack:
            node = stack.pop()
            if node.type in {'string', 'string_fragment', 'escape_sequence', 'comment', 'regex', 'number'}:
                result.append((node.type, raw[node.start_byte:node.end_byte]))
            else:
                stack.extend(reversed(node.children))
        return result
    return '' if data_tokens(before) == data_tokens(after) else 'TS_LITERAL_OR_COMMENT_CHANGED'


def applicable(capability: str, args: dict) -> bool:
    return ((capability == 'python.swe.transform_and_synthesize.v1' and args.get('operation') in PYTHON_OPERATIONS)
            or (capability == 'code.polyglot.transform_and_verify.v1' and args.get('operation') == 'ts_rename_symbol'))


def capture(root: Path, args: dict) -> dict[str, str | None]:
    target = (root / str(args.get('target_path') or '')).resolve()
    if root != target and root not in target.parents:
        raise ValueError('TRANSITION_TARGET_OUTSIDE_ROOT')
    paths = [target] if target.is_file() else sorted(target.rglob('*.py'))
    if len(paths) > 1000:
        raise ValueError('TRANSITION_SOURCE_COUNT_LIMIT')
    if args.get('operation') == 'split_module' and target.is_file():
        tree = ast.parse(target.read_text(encoding='utf-8'))
        paths.extend(target.parent / (fn.name + '.py') for fn in tree.body if isinstance(fn, ast.FunctionDef))
    result = {}
    total = 0
    for path in paths:
        if path.is_symlink():
            raise ValueError('TRANSITION_SYMLINK_REFUSED')
        if not path.exists():
            result[path.relative_to(root).as_posix()] = None
            continue
        data = path.read_bytes()
        total += len(data)
        if total > 16_000_000:
            raise ValueError('TRANSITION_SOURCE_BYTES_LIMIT')
        result[path.relative_to(root).as_posix()] = data.decode('utf-8')
    return result


def verify(root: Path, args: dict, preimages: dict[str, str | None]) -> dict:
    checked = 0
    for rel, before in preimages.items():
        if before is None:
            continue
        target = (root / rel).resolve()
        if root not in target.parents or not target.is_file():
            raise ValueError('TRANSITION_TARGET_MISSING_OR_OUTSIDE_ROOT')
        after = target.read_text(encoding='utf-8')
        if args.get('operation') == 'ts_rename_symbol':
            reason = verify_typescript(before, after)
        else:
            reason = verify_python(before, after, str(args['operation']), str(args.get('symbol') or ''))
        if reason:
            raise ValueError(reason)
        checked += 1
    if checked == 0:
        raise ValueError('TRANSITION_NOT_MEASURED')
    return {'schema':'PROJECT_BRAIN_SWE_TRANSITION_CHECK_V1', 'checked_files':checked,
            'assurance':'BOUNDED_STRUCTURAL_PRESERVATION',
            'before_sha256':{p:hashlib.sha256(s.encode('utf-8')).hexdigest() for p,s in preimages.items() if s is not None}}


def restore(root: Path, preimages: dict[str, str | None]) -> None:
    from canonical.swe_kernel.transform_contracts_v1 import FileEdits
    edits = {}
    for rel, before in preimages.items():
        path = (root / rel).resolve()
        if root not in path.parents:
            raise ValueError('RESTORE_OUTSIDE_ROOT')
        if before is None:
            path.unlink(missing_ok=True)
        else:
            data = before.encode('utf-8')
            if path.is_file() and path.read_bytes() == data:
                continue
            edits[path] = data
    with FileEdits(edits) as transaction:
        transaction.commit()
