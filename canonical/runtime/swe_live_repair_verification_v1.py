"""Compose live cross-file repair with the existing counted suite runner.

This is producer-side verification, not an independent verifier or a sandbox.
The adapter may edit the project and tests execute arbitrary project code. A
failed post-check does not undo those effects. The adapter's report is staged
away from the requested destination until the post-check has passed.
"""
from __future__ import annotations

import hashlib
import os
import pathlib
import secrets
import sys
import tempfile
from typing import Any, Callable, Mapping

from canonical.runtime import write_authority_v1
from canonical.runtime.bound_capabilities import python_test_guided_patch_search_v1 as suite


class RepairVerificationFailure(RuntimeError):
    """The report must not be published; project side effects may remain."""


def _test_files(test_dir: pathlib.Path, project: pathlib.Path) -> list[pathlib.Path]:
    targets = []
    for path in sorted(test_dir.rglob('*.py')):
        if any(part in ('.git', '__pycache__') for part in path.parts):
            continue
        if not (path.name.startswith('test_') or path.name.endswith('_test.py')):
            continue
        resolved = path.resolve()
        if project not in resolved.parents or not resolved.is_file():
            raise RepairVerificationFailure('TEST_TARGET_OUTSIDE_PROJECT:' + str(path))
        targets.append(resolved)
    return targets


def _digests(paths: list[pathlib.Path]) -> dict[pathlib.Path, str]:
    return {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def run(adapter: Any, fn: Callable[..., Any], args: Mapping[str, Any], root: pathlib.Path) -> dict[str, Any]:
    """Run the pinned adapter, then publish its report only after a counted suite.

    Discovery only establishes the presence of test files before dispatch; it
    does not prove they will pass. Checks are repeated after adapter execution.
    A suite can still be inadequate, dishonest, or have arbitrary side effects.
    """
    root = root.resolve()
    src_raw = str(args.get('source_root') or '').strip()
    out_raw = str(args.get('output_path') or '').strip()
    if not src_raw or not out_raw:
        raise RepairVerificationFailure('MISSING_REQUIRED_ARGUMENTS')
    src = adapter._safe_path(root, src_raw, allow_root=False)
    out = adapter._safe_path(root, out_raw)
    if not (src.is_file() or src.is_dir()):
        raise RepairVerificationFailure('SOURCE_ROOT_NOT_FOUND')
    project, test_dir, focus = adapter._resolve_workspace(src, root)
    if project in (root, root / 'canonical', root / 'canonical/runtime') or len(focus) > 64:
        raise RepairVerificationFailure('REFUSING_BROAD_REPO_MUTATION')
    if not focus:
        raise RepairVerificationFailure('NO_PYTHON_SOURCE_FILES')
    tests = _test_files(test_dir, project)
    if not tests:
        raise RepairVerificationFailure('NO_TESTS_DISCOVERED_BEFORE_REPAIR')
    # The adapter transforms source, but its output_path is a *report*, not
    # authority to overwrite any Python source/test in the project. Check
    # aliases too, including a hard link to one of those files.
    project_python = [p for p in project.rglob('*.py') if p.is_file()]
    write_authority_v1.check_report(root, out, project_python)
    initial_tests = _digests(tests)

    scratch_parent = root / 'canonical/astra_runtime/tmp'
    scratch_parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='swe_report_', dir=scratch_parent) as scratch:
        staged = pathlib.Path(scratch) / 'report.json'
        staged_args = dict(args, output_path=staged.relative_to(root).as_posix())
        result = fn(staged_args, root)
        if not isinstance(result, dict) or result.get('output_verified') is not True or not staged.is_file():
            raise RepairVerificationFailure('ADAPTER_DID_NOT_PRODUCE_VERIFIED_REPORT;PROJECT_EFFECTS_MAY_REMAIN')
        if _test_files(test_dir, project) != tests or _digests(tests) != initial_tests:
            raise RepairVerificationFailure('TEST_FILES_CHANGED_DURING_REPAIR;PROJECT_EFFECTS_MAY_REMAIN')
        env = {
            'PYTHONPATH': str(project) + (os.pathsep + os.environ['PYTHONPATH'] if os.environ.get('PYTHONPATH') else ''),
            'PYTHONDONTWRITEBYTECODE': '1',
        }
        # Adapt the existing runner to require collected test cases. Its normal
        # script-oracle mode would accept a no-op __main__ as a passing test.
        # A completion marker also rejects os._exit(0) before runner completion.
        # This is a correctness check, not an adversarially trusted channel.
        marker = 'SWE_COUNTED_SUITE_COMPLETE_' + secrets.token_hex(16)
        argv = suite.suite_argv(sys.executable, *tests)
        argv[2] = (suite.SUITE_RUNNER + '\n_brain_original_shape = _brain_suite_shape\n'
                   'def _brain_suite_shape(target):\n'
                   '    prefer, required, _script = _brain_original_shape(target)\n'
                   '    return prefer, required, False\n'
                   + suite.SUITE_ENTRY + '\nprint(' + repr(marker) + ')\n')
        check = suite._run_tests(root, argv, 120, extra_env=env, cwd=project)
        completed = str(check.get('stdout') or '').splitlines()[-1:] == [marker]
        if check['returncode'] != 0 or check['timed_out'] or not completed:
            diagnostic = str(check.get('stderr') or check.get('stdout') or '')[-600:]
            if not completed:
                diagnostic = 'MISSING_COMPLETION_MARKER:' + diagnostic
            raise RepairVerificationFailure('COUNTED_TEST_SUITE_FAILED;PROJECT_EFFECTS_MAY_REMAIN:' + diagnostic)
        if _test_files(test_dir, project) != tests or _digests(tests) != initial_tests:
            raise RepairVerificationFailure('TEST_FILES_CHANGED_DURING_VERIFICATION;PROJECT_EFFECTS_MAY_REMAIN')
        payload = staged.read_bytes()
        if hashlib.sha256(payload).hexdigest() != result.get('output_sha256'):
            raise RepairVerificationFailure('STAGED_REPORT_DIGEST_MISMATCH;PROJECT_EFFECTS_MAY_REMAIN')
        # Recheck aliases after tests, which themselves can mutate the project.
        write_authority_v1.check_report(root, out, [p for p in project.rglob('*.py') if p.is_file()])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(payload)
        result['output_path'] = out.relative_to(root).as_posix()
        result['output_sha256'] = hashlib.sha256(out.read_bytes()).hexdigest()
        result['producer_suite_check'] = {'runner': 'python_test_guided_patch_search_v1.suite_argv (script oracles disabled)',
                                          'target_count': len(tests), 'returncode': 0,
                                          'independent': False}
        return result
