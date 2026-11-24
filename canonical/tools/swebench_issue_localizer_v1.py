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
MAX_ENTRIES = 50_000
MAX_DEPTH = 32
MAX_SOURCE_FILES = 6_000
MAX_FILE_BYTES = 256_000
MAX_SCAN_BYTES = 64_000_000
TOP_K = 10
EXCLUDED_DIRS = {'.git', '.hg', '.svn', '.venv', 'venv', 'node_modules', '__pycache__',
                 '.tox', '.mypy_cache', '.pytest_cache', 'doc', 'docs', 'vendor',
                 'vendors', 'vendored', 'third_party', 'third-party', 'build', 'dist'}
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


def _ranked_candidates(statement: str, files: list[str], paths: list[str], root_fd: int) -> dict[str, Any]:
    """Bounded reproducible ranking, not a confidence or correctness guarantee."""
    # Exclude issue-template boilerplate from lexical evidence; never execute it.
    text = re.sub(r'<!--.*?-->', ' ', statement, flags=re.DOTALL)
    title = text.splitlines()[0] if text.splitlines() else ''
    modules = set(re.findall(r'\bfrom\s+([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+)\s+import\b', text))
    modules.update(re.findall(r'\b[A-Za-z_]\w*(?:\.[A-Za-z_]\w*){2,}\b', text))
    module_paths = sorted(m.replace('.', '/') for m in modules)
    symbols = _symbol_mentions(text)
    symbols.update(re.findall(r'`([A-Za-z_]\w{2,})`', text))
    symbols.update(re.findall(r'\bfrom\s+[A-Za-z_.][\w.]*\s+import\s+([A-Za-z_]\w*)', text))
    symbols -= {'print', 'len', 'str', 'int', 'list', 'dict', 'range', 'isinstance', 'type', 'super', 'Exception', 'ValueError'}
    frequencies = {s: len(re.findall(r'\b' + re.escape(s) + r'\b', text)) for s in symbols}
    ranked_symbols = sorted(symbols, key=lambda s: (-int(bool(re.search(r'\b'+re.escape(s)+r'\b', title))), -frequencies[s], s))[:128]
    names = set(ranked_symbols)
    title_tokens = {t.lower() for t in re.findall(r'[A-Za-z_]{3,}', title)} - {'the', 'and', 'for', 'when', 'not', 'with', 'from', 'does', 'into', 'that', 'this', 'support', 'output'}
    snippets = sorted({line.strip() for line in text.splitlines()
                       if 25 <= len(line.strip()) <= 200 and
                       (line.startswith('    ') or line.lstrip().startswith(('# ', 'if ', 'return ')))})[:40]

    def priority(path: str) -> tuple[int, str]:
        stem = Path(path).stem.lower()
        module = path[:-3]
        relevance = 0
        for mp in module_paths:
            if module == mp or module == mp + '/__init__': relevance = max(relevance, 4)
            elif module.startswith(mp + '/'): relevance = max(relevance, 3)
            elif mp.startswith(module + '/'): relevance = max(relevance, 2)
        if stem in title_tokens: relevance = max(relevance, 1)
        if path in paths: relevance = 5
        return (-relevance, path)

    scan = sorted(files, key=priority)
    complete = len(scan) <= MAX_SOURCE_FILES and len(symbols) <= 128
    symbols_truncated = len(symbols) > 128
    scan = scan[:MAX_SOURCE_FILES]
    used = 0
    omitted = 0
    sources: list[dict[str, Any]] = []
    tests: list[dict[str, Any]] = []
    ascii_names = [s for s in ranked_symbols if s.isascii()]
    unicode_names = [s.encode('utf-8') for s in ranked_symbols if not s.isascii()]
    symbol_re = re.compile(rb'\b(?:' + b'|'.join(re.escape(s.encode('ascii')) for s in ascii_names) + rb')\b') if ascii_names else None
    for i, path in enumerate(scan):
        try:
            data = _read_python(root_fd, path)
        except LocalizationUnavailable as exc:
            if str(exc) == 'SOURCE_FILE_TOO_LARGE_OR_INVALID':
                complete = False; omitted += 1; continue
            raise
        if used + len(data) > MAX_SCAN_BYTES:
            complete = False; omitted += len(scan) - i; break
        used += len(data)
        has_symbol = bool(symbol_re and symbol_re.search(data)) or any(name in data for name in unicode_names)
        found = _definitions(data) if has_symbol else {}
        matched = sorted(names.intersection(found))
        evidence: list[str] = []
        score = 0
        if path in paths:
            score += 200; evidence.append('issue_path')
        module = path[:-3]
        exact = [mp for mp in module_paths if module == mp or module == mp + '/__init__']
        package = [mp for mp in module_paths if module.startswith(mp + '/')]
        # Prefer a specific module, not a package initializer imported alongside it.
        if exact:
            mp = max(exact, key=len)
            score += 15 if path.endswith('/__init__.py') else 80
            evidence.append('import_module:' + mp)
        elif package:
            mp = max(package, key=len)
            score += 16; evidence.append('import_package:' + mp)
        for s in matched:
            weight = min(frequencies[s], 5) * 3 + (25 if re.search(r'\b'+re.escape(s)+r'\b', title) else 0)
            score += weight; evidence.append('definition:' + s)
        hits = [line for line in snippets if line.encode('utf-8') in data]
        context_symbols: list[str] = []
        if hits:
            score += min(len(hits), 5) * 20; evidence.append('quoted_source_lines:' + str(len(hits)))
            try:
                code_lines = data.decode('utf-8').splitlines()
                nodes = [n for n in ast.walk(ast.parse(data)) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
                for lineno, line in enumerate(code_lines, 1):
                    if line.strip() not in hits: continue
                    enclosing = [n for n in nodes if n.lineno <= lineno <= (n.end_lineno or n.lineno)]
                    if enclosing:
                        context_symbols.append(min(enclosing, key=lambda n: (n.end_lineno or n.lineno) - n.lineno).name)
            except (SyntaxError, UnicodeError, ValueError, RecursionError, MemoryError):
                pass
        stem = Path(path).stem.lower().removeprefix('test_').removesuffix('_test')
        if stem in title_tokens:
            score += 35; evidence.append('title_filename:' + stem)
        if score:
            ordered = sorted(matched, key=lambda s: (-int(bool(re.search(r'\b'+re.escape(s)+r'\b', title))), -frequencies[s], s))
            ordered += [s for s in sorted(set(context_symbols)) if s not in ordered]
            item = {'path': path, 'score': score, 'evidence': evidence, 'symbols': ordered}
            if not _is_test(path): sources.append(item)
            elif Path(path).name.startswith('test_') or Path(path).name.endswith('_test.py'): tests.append(item)
    sources.sort(key=lambda item: (-item['score'], item['path']))
    # Related test filenames and package locality are weak suggestions, not tests known to fail.
    if sources:
        top = sources[0]['path']
        stem = Path(top).stem
        top_parent = str(Path(top).parent)
        known_tests = {item['path']: item for item in tests}
        for path in files:
            if not _is_test(path): continue
            if Path(path).name in {f'test_{stem}.py', f'{stem}_test.py'}:
                item = known_tests.setdefault(path, {'path': path, 'score': 0, 'evidence': [], 'symbols': []})
                item['score'] += 30; item['evidence'].append('target_filename')
                if str(Path(path).parent).startswith(top_parent + '/'):
                    item['score'] += 10; item['evidence'].append('target_package')
        tests = list(known_tests.values())
    tests.sort(key=lambda item: (-item['score'], item['path']))
    legacy_symbols = _symbol_mentions(statement)
    return {'authority': 'NONE__ADVISORY_ONLY', 'scan_complete': complete,
            'symbols_truncated': symbols_truncated,
            'scanned_files': len(scan) - omitted, 'scanned_bytes': used, 'omitted_files': omitted + max(0, len(files) - len(scan)),
            'target_paths': sources[:TOP_K], 'test_targets': tests[:TOP_K],
            '_symbol_source_paths': sorted(item['path'] for item in sources if legacy_symbols.intersection(item['symbols']))}


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
            source_mentions = [p for p in paths if not _is_test(p)]
            test_mentions = [p for p in paths if _is_test(p)]
            symbols = _symbol_mentions(statement)
            ranked = _ranked_candidates(statement, files, paths, root_fd)
            hits = ranked.pop('_symbol_source_paths')
            target = _field(source_mentions, 'EXPLICIT_ISSUE_PATH')
            # A partial scan can produce suggestions, but not a unique conclusion.
            if not source_mentions and symbols:
                target = _field(hits, 'EXPLICIT_SYMBOL_AST_SEARCH')
                if not ranked['scan_complete'] and target['status'] == 'SELECTED':
                    target.update(status='INCOMPLETE', value=None)
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
            result.update(status='ADVISORY_CANDIDATES', target_path=target, symbol=symbol_field, test_target=tests,
                          ranked_candidates=ranked)
        finally:
            os.close(root_fd)
    except (LocalizationUnavailable, OSError) as exc:
        result['reason'] = str(exc) if isinstance(exc, LocalizationUnavailable) else 'WORKTREE_UNAVAILABLE'
    return result
