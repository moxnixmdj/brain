"""Read-only, bounded Pro issue/workspace hints; never execution authority.

The issue and repository are untrusted. These observations do not prove a test
fails, select a test command, authorize an edit, or establish a repair. No task
code is executed. A missing path is not by itself a request to create a file.
"""
from __future__ import annotations

import os
import re
import shutil
import stat
from typing import Any

from canonical.tools import swebench_issue_localizer_v1 as localizer

SCHEMA = 'PROJECT_BRAIN_HARBOR_PRO_GROUNDING_V1'
MAX_ISSUE_CHARS = 40_000
MAX_ENTRIES = 10_000
MAX_DEPTH = 16
MAX_MENTIONS = 30
MAX_TESTS = 30
EXCLUDED_DIRS = {'.git', '.hg', '.svn', '.venv', 'venv', 'node_modules',
                 '__pycache__', '.tox', '.mypy_cache', '.pytest_cache',
                 'vendor', 'vendors', 'third_party', 'third-party', 'build', 'dist'}
PATH_RE = re.compile(r'(?<![A-Za-z0-9_./\\-])([A-Za-z0-9_./-]+\.(?:py|js|jsx|ts|tsx))(?![A-Za-z0-9_])')
SYMBOL_RE = re.compile(r'\b(?:function|method|class)\s+[`\'"]?([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)|(?<![\w.])([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)\s*\(')
RUNNERS = ('python3', 'pytest', 'npm', 'node', 'mocha')


def _path_parts(path: str) -> list[str] | None:
    parts = path.split('/')
    if path.startswith('/') or len(path) > 1024 or len(parts) > MAX_DEPTH or any(
        part in ('', '.', '..') or part.startswith('.') for part in parts
    ):
        return None
    return parts


def _path_status(root: int, path: str) -> str:
    parts = _path_parts(path)
    if not parts:
        return 'UNSAFE_PATH'
    fd = os.dup(root)
    try:
        for part in parts[:-1]:
            try:
                child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            except FileNotFoundError:
                return 'MISSING_OR_PARENT_MISSING'
            except OSError:
                return 'UNSAFE_OR_UNREADABLE'
            os.close(fd)
            fd = child
        try:
            st = os.stat(parts[-1], dir_fd=fd, follow_symlinks=False)
        except FileNotFoundError:
            return 'MISSING_OR_PARENT_MISSING'
        except OSError:
            return 'UNSAFE_OR_UNREADABLE'
        return 'EXISTING_REGULAR_FILE' if stat.S_ISREG(st.st_mode) else 'NOT_REGULAR_FILE'
    finally:
        os.close(fd)


def _is_test(path: str) -> bool:
    parts = path.lower().split('/')
    name = parts[-1]
    return (any(p in ('test', 'tests', '__tests__') for p in parts[:-1])
            or name.startswith('test_') or name.endswith(('_test.py', '.test.js', '.spec.js',
                                                         '.test.ts', '.spec.ts', '.test.tsx', '.spec.tsx')))


def _tests(root: int) -> tuple[list[str], bool, int]:
    """Enumerate test-shaped regular files without following symlinks."""
    found: list[str] = []
    visited = 0
    complete = True

    def walk(fd: int, prefix: str, depth: int) -> None:
        nonlocal visited, complete
        if not complete:
            return
        if depth > MAX_DEPTH:
            complete = False
            return
        try:
            names = []
            with os.scandir(fd) as entries:
                for entry in entries:
                    visited += 1
                    if visited > MAX_ENTRIES:
                        complete = False
                        return
                    names.append(entry.name)
            for name in sorted(names):
                rel = prefix + '/' + name if prefix else name
                st = os.stat(name, dir_fd=fd, follow_symlinks=False)
                if stat.S_ISDIR(st.st_mode):
                    if name.startswith('.') or name in EXCLUDED_DIRS:
                        continue
                    child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                    try:
                        walk(child, rel, depth + 1)
                    finally:
                        os.close(child)
                    if not complete:
                        return
                elif stat.S_ISREG(st.st_mode) and rel.endswith(('.py', '.js', '.jsx', '.ts', '.tsx')) and _is_test(rel):
                    found.append(rel)
        except OSError:
            complete = False

    walk(root, '', 0)
    found.sort()
    return found[:MAX_TESTS], complete and len(found) <= MAX_TESTS, min(visited, MAX_ENTRIES)


def ground(instruction: Any, workspace: Any) -> dict[str, Any]:
    """Return bounded, untrusted hints; never run a command or authorize a repair."""
    result: dict[str, Any] = {'schema': SCHEMA, 'authority': 'NONE__ADVISORY_ONLY',
                              'status': 'UNAVAILABLE', 'reason': None,
                              'explicit_paths': [], 'mentioned_symbols': [],
                              'test_candidates': [], 'test_inventory_complete': False,
                              'runners_on_path': {}, 'python_localization': None,
                              'tests_run': False, 'repair_verified': False}
    if not isinstance(instruction, str) or not instruction.strip() or len(instruction) > MAX_ISSUE_CHARS:
        result['reason'] = 'INSTRUCTION_EMPTY_OR_TOO_LARGE'
        return result
    if not isinstance(workspace, str) or not os.path.isabs(workspace) or workspace == '/':
        result['reason'] = 'WORKSPACE_INVALID'
        return result
    try:
        fd = os.open(workspace, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    except OSError:
        result['reason'] = 'WORKSPACE_UNAVAILABLE'
        return result
    try:
        paths = sorted({m.group(1) for m in PATH_RE.finditer(instruction)})
        symbols = sorted({m.group(1) or m.group(2) for m in SYMBOL_RE.finditer(instruction)})
        result['explicit_paths'] = [{'path': p, 'status': _path_status(fd, p)} for p in paths[:MAX_MENTIONS]]
        result['path_mentions_truncated'] = len(paths) > MAX_MENTIONS
        result['mentioned_symbols'] = symbols[:MAX_MENTIONS]
        result['symbol_mentions_truncated'] = len(symbols) > MAX_MENTIONS
        tests, complete, visited = _tests(fd)
        result['test_candidates'] = tests
        result['test_inventory_complete'] = complete
        result['entries_seen'] = visited
        result['runners_on_path'] = {name: bool(shutil.which(name)) for name in RUNNERS}
        if any(p.endswith('.py') for p in paths) or re.search(r'\bpython\b', instruction, re.I):
            hints = localizer.localize_issue(instruction, workspace)
            ranked = hints.get('ranked_candidates') or {}
            result['python_localization'] = {
                'status': hints.get('status'), 'reason': hints.get('reason'),
                'authority': 'NONE__ADVISORY_ONLY', 'scan_complete': ranked.get('scan_complete', False),
                'target_paths': (ranked.get('target_paths') or [])[:5],
                'test_targets': (ranked.get('test_targets') or [])[:5],
            }
        result['status'] = 'OBSERVED__UNVERIFIED'
        return result
    finally:
        os.close(fd)
