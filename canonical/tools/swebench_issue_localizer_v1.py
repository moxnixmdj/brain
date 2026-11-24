"""Conservative, read-only SWE issue localization hints; no execution authority.

Uses only the public problem statement and Python files under the supplied tree.
The result is advisory: no caller may treat a candidate as an execution policy,
verification, a test command, or proof of a correct repair. Ambiguous or bounded
searches do not choose a value. It does not inspect gold/test patches or run code.
"""
from __future__ import annotations

import ast
import os
from pathlib import Path
import re
import stat
from typing import Any

SCHEMA = 'PROJECT_BRAIN_SWEBENCH_ISSUE_LOCALIZER_V1'
MAX_STATEMENT_CHARS = 40_000
MAX_ENTRIES = 12_000
MAX_DEPTH = 32
MAX_SOURCE_FILES = 500
MAX_FILE_BYTES = 256_000
MAX_SCAN_BYTES = 8_000_000
EXCLUDED_DIRS = {'.git', '.hg', '.svn', '.venv', 'venv', 'node_modules', '__pycache__', '.tox', '.mypy_cache', '.pytest_cache'}
PATH_RE = re.compile(r'(?<![A-Za-z0-9_./\\-])([A-Za-z0-9_./-]+\.py)(?![A-Za-z0-9_])')
NAMED_SYMBOL_RE = re.compile(r'\b(?:function|method|class)\s+[`\'"]?([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)')
CALL_SYMBOL_RE = re.compile(r'(?<![\w.])([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)\s*\(')
TRACE_SYMBOL_RE = re.compile(r'\bin\s+([A-Za-z_]\w*)\s*(?:\n|$)')


class LocalizationUnavailable(ValueError):
    pass


def _is_test(path: str) -> bool:
    parts = path.split('/')
    name = parts[-1]
    return name.startswith('test_') or name.endswith('_test.py') or any(x in {'test', 'tests'} for x in parts[:-1])


def _inventory(root_fd: int) -> list[str]:
    count = 0
    files: list[str] = []
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW

    def walk(fd: int, prefix: str, depth: int) -> None:
        nonlocal count
        if depth > MAX_DEPTH:
            raise LocalizationUnavailable('TREE_DEPTH_LIMIT')
        with os.scandir(fd) as it:
            names = []
            for entry in it:
                count += 1
                if count > MAX_ENTRIES:
                    raise LocalizationUnavailable('TREE_ENTRY_LIMIT')
                names.append(entry.name)
        for name in sorted(names):
            rel = prefix + '/' + name if prefix else name
            try:
                st = os.stat(name, dir_fd=fd, follow_symlinks=False)
                if stat.S_ISDIR(st.st_mode):
                    if name in EXCLUDED_DIRS or name.startswith('.'):
                        continue
                    sub = os.open(name, flags, dir_fd=fd)
                    try:
                        walk(sub, rel, depth + 1)
                    finally:
                        os.close(sub)
                elif stat.S_ISREG(st.st_mode) and name.endswith('.py'):
                    files.append(rel)
            except OSError as exc:
                raise LocalizationUnavailable('TREE_UNREADABLE') from exc
    walk(root_fd, '', 0)
    return sorted(files)


def _read_python(root_fd: int, rel: str) -> bytes:
    parts = rel.split('/')
    if any(x in ('', '.', '..') for x in parts):
        raise LocalizationUnavailable('INVALID_RELATIVE_PATH')
    dirfd = os.dup(root_fd)
    try:
        for part in parts[:-1]:
            nextfd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=dirfd)
            os.close(dirfd); dirfd = nextfd
        fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=dirfd)
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_FILE_BYTES:
                raise LocalizationUnavailable('SOURCE_FILE_TOO_LARGE_OR_INVALID')
            buf = bytearray()
            while len(buf) <= MAX_FILE_BYTES:
                block = os.read(fd, min(65536, MAX_FILE_BYTES + 1 - len(buf)))
                if not block:
                    break
                buf.extend(block)
            after = os.fstat(fd)
            if len(buf) > MAX_FILE_BYTES or len(buf) != before.st_size or (
                before.st_ino, before.st_dev, before.st_size, before.st_mtime_ns, before.st_ctime_ns
            ) != (after.st_ino, after.st_dev, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
                raise LocalizationUnavailable('SOURCE_FILE_CHANGED')
            return bytes(buf)
        finally:
            os.close(fd)
    except OSError as exc:
        raise LocalizationUnavailable('SOURCE_FILE_UNREADABLE') from exc
    finally:
        os.close(dirfd)


def _definitions(data: bytes) -> dict[str, int]:
    try:
        tree = ast.parse(data)
    except (SyntaxError, UnicodeError, ValueError, RecursionError, MemoryError):
        return {}
    names: dict[str, int] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names[node.name] = names.get(node.name, 0) + 1
    return names


def _path_mentions(statement: str, files: list[str]) -> list[str]:
    # A backslash path must not disappear from the scan and leave a plausible
    # but unrelated symbol-only hit behind.
    if re.search(r'[^\s`\'"]*\\[^\s`\'"]*\.py\b', statement):
        raise LocalizationUnavailable('PATH_REFERENCE_UNRESOLVED_OR_UNSAFE')
    found: set[str] = set()
    known = set(files)
    for match in PATH_RE.finditer(statement):
        candidate = match.group(1)
        if candidate.startswith('/') or '\\' in candidate or any(p in ('', '.', '..') for p in candidate.split('/')):
            raise LocalizationUnavailable('PATH_REFERENCE_UNRESOLVED_OR_UNSAFE')
        matches = ([candidate] if candidate in known else []) + [
            p for p in files if p.endswith('/' + candidate)
        ]
        if not matches:
            raise LocalizationUnavailable('PATH_REFERENCE_UNRESOLVED_OR_UNSAFE')
        found.update(matches)
    return sorted(found)


def _symbol_mentions(statement: str) -> set[str]:
    symbols: set[str] = set()
    for regex in (NAMED_SYMBOL_RE, CALL_SYMBOL_RE, TRACE_SYMBOL_RE):
        for match in regex.finditer(statement):
            symbols.add(match.group(1).split('.')[-1])
    return symbols


def _field(candidates: list[str], basis: str) -> dict[str, Any]:
    choices = sorted(set(candidates))
    return {'status': 'SELECTED' if len(choices) == 1 else ('AMBIGUOUS' if choices else 'MISSING'),
            'value': choices[0] if len(choices) == 1 else None,
            'candidates': choices[:20], 'candidate_count': len(choices), 'basis': basis}


def explicit_input_candidates(localization: dict[str, Any]) -> dict[str, str] | None:
    """Return an all-or-nothing, explicit-reference subset for future wiring.

    This is not an authorization check. Even these candidates are unverified
    guesses, and must not be used to bypass confinement or receipt admission.
    Filename-derived tests and symbol-only file searches are not included.
    """
    if localization.get('status') != 'ADVISORY_CANDIDATES':
        return None
    expected = {'target_path': 'EXPLICIT_ISSUE_PATH',
                'symbol': 'EXPLICIT_ISSUE_SYMBOL_AND_AST',
                'test_target': 'EXPLICIT_ISSUE_PATH'}
    values = {}
    for name, basis in expected.items():
        field = localization.get(name)
        if (not isinstance(field, dict) or field.get('status') != 'SELECTED'
                or field.get('basis') != basis or not isinstance(field.get('value'), str)
                or not field['value']):
            return None
        values[name] = field['value']
    return values


def localize_issue(statement: str, worktree: str | Path) -> dict[str, Any]:
    result: dict[str, Any] = {'schema': SCHEMA, 'authority': 'NONE__ADVISORY_ONLY',
                              'status': 'NOT_LOCATED', 'reason': None,
                              'target_path': _field([], 'EXPLICIT_ISSUE_PATH_OR_UNIQUE_SYMBOL'),
                              'symbol': _field([], 'EXPLICIT_ISSUE_SYMBOL_AND_AST'),
                              'test_target': _field([], 'EXPLICIT_ISSUE_PATH_OR_UNIQUE_TEST_FILENAME')}
    if not isinstance(statement, str) or not statement.strip():
        result['reason'] = 'PROBLEM_STATEMENT_EMPTY'; return result
    if len(statement) > MAX_STATEMENT_CHARS:
        result['reason'] = 'PROBLEM_STATEMENT_LIMIT'; return result
    try:
        if not all(hasattr(os, x) for x in ('O_DIRECTORY', 'O_NOFOLLOW', 'O_NONBLOCK')):
            raise LocalizationUnavailable('SAFE_FILE_OPEN_UNAVAILABLE')
        root = Path(worktree)
        root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            files = _inventory(root_fd)
            paths = _path_mentions(statement, files)
            sources = [p for p in files if not _is_test(p)]
            source_mentions = [p for p in paths if not _is_test(p)]
            test_mentions = [p for p in paths if _is_test(p)]
            symbols = _symbol_mentions(statement)
            target = _field(source_mentions, 'EXPLICIT_ISSUE_PATH')
            # Never resolve an explicitly ambiguous file by guessing a symbol.
            if not source_mentions and symbols:
                if len(sources) > MAX_SOURCE_FILES:
                    raise LocalizationUnavailable('SYMBOL_SCAN_FILE_LIMIT')
                hits = []
                total = 0
                for path in sources:
                    data = _read_python(root_fd, path); total += len(data)
                    if total > MAX_SCAN_BYTES:
                        raise LocalizationUnavailable('SYMBOL_SCAN_BYTE_LIMIT')
                    defs = _definitions(data)
                    if any(name in defs for name in symbols):
                        hits.append(path)
                target = _field(hits, 'EXPLICIT_SYMBOL_AST_SEARCH')
            target_value = target['value']
            symbol_field = _field([], 'EXPLICIT_ISSUE_SYMBOL_AND_AST')
            if target_value and symbols:
                defs = _definitions(_read_python(root_fd, target_value))
                # Duplicate definitions are not uniquely localized, even in one file.
                names = [name for name in sorted(symbols) if defs.get(name) == 1]
                ambiguous_names = [name for name in sorted(symbols) if defs.get(name, 0) > 1]
                if ambiguous_names:
                    symbol_field = {'status': 'AMBIGUOUS', 'value': None,
                                    'candidates': (names + ambiguous_names)[:20],
                                    'candidate_count': len(names) + len(ambiguous_names),
                                    'basis': 'DUPLICATE_AST_DEFINITION'}
                else:
                    symbol_field = _field(names, 'EXPLICIT_ISSUE_SYMBOL_AND_AST')
            tests = _field(test_mentions, 'EXPLICIT_ISSUE_PATH')
            if not test_mentions and target_value:
                stem = Path(target_value).stem
                tests = _field([p for p in files if _is_test(p) and Path(p).name in {f'test_{stem}.py', f'{stem}_test.py'}],
                               'MATCHING_TEST_FILENAME_HEURISTIC')
            result.update(status='ADVISORY_CANDIDATES', target_path=target, symbol=symbol_field, test_target=tests)
        finally:
            os.close(root_fd)
    except (LocalizationUnavailable, OSError) as exc:
        result['reason'] = str(exc) if isinstance(exc, LocalizationUnavailable) else 'WORKTREE_UNAVAILABLE'
    return result
