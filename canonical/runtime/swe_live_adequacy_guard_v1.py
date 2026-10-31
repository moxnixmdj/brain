"""Conservative local preflight for the pinned test-adequacy adapter.

That adapter combines line numbers from all subject files, losing file identity.
Until a separately admitted file-aware implementation is available, refuse a
multi-file subject before running its tests or publishing its report. This does
not establish that its single-file adequacy conclusions are sound.
"""
from __future__ import annotations

import ast
import pathlib
from typing import Any, Mapping


def require_single_target_file(adapter: Any, args: Mapping[str, Any], root: pathlib.Path) -> None:
    """Mirror the pinned adapter's subject selection; stop on a second target.

    This is an admission guard, not a replacement adapter. Invalid arguments
    remain the adapter's responsibility unless needed to locate its subject.
    """
    repo = pathlib.Path(root).resolve()
    source_root = adapter._safe_root(repo, args.get('source_root'))
    declared_test_root = str(args.get('test_root') or '')
    candidates = ([declared_test_root] if declared_test_root else
                  [str(source_root / 'tests'), str(source_root.parent / 'tests'),
                   str(source_root / '..' / 'tests')])
    tests = None
    for candidate in candidates:
        path = pathlib.Path(candidate)
        probe = (repo / candidate).resolve() if not path.is_absolute() else path.resolve()
        if probe.is_dir():
            tests = probe
            break
    if tests is None:
        return  # The original adapter raises TEST_ROOT_MISSING.
    if tests != repo and repo not in tests.parents:
        raise RuntimeError('PATH_OUTSIDE_REPOSITORY')
    subject = tests.parent if source_root == tests or source_root.is_relative_to(tests) else source_root
    targets: set[pathlib.Path] = set()
    for path in subject.rglob('*.py'):
        # Match the pinned adapter's exclusions and syntax-error handling.
        if '__pycache__' in path.parts or 'tests' in path.parts:
            continue
        try:
            tree = ast.parse(path.read_text(encoding='utf-8', errors='replace'), filename=str(path))
        except (SyntaxError, ValueError):
            continue
        if any(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) for node in ast.walk(tree)):
            targets.add(path.resolve())
            if len(targets) > 1:
                raise RuntimeError('MULTIFILE_ADEQUACY_REQUIRES_FILE_AWARE_TRACING')
