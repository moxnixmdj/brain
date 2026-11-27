"""Observe the same pytest case identities before and after an edit (including unittest cases)."""
from __future__ import annotations

import dataclasses
import os
import shutil
import signal
from pathlib import Path
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET


EXCLUDED = frozenset({'.git', '.venv', 'venv', 'node_modules', '__pycache__', '.pytest_cache'})


def copy_product_tree(source, destination):
    """Copy a trusted disposable checkout without following external links.

    This is not process confinement: untrusted project code also needs an OS
    sandbox. In particular, fork alone is not a filesystem snapshot.
    """
    source = Path(source).resolve(strict=True)
    def ignore(folder, names):
        skipped = {n for n in names if n in EXCLUDED or n.endswith('.pyc')}
        for n in set(names) - skipped:
            p = Path(folder)/n
            if p.is_symlink() and (Path(os.readlink(p)).is_absolute() or not p.resolve().is_relative_to(source)):
                raise ValueError('external or absolute product symlink: '+str(p.relative_to(source)))
        return skipped
    shutil.copytree(source,destination,ignore=ignore,symlinks=True)


def restored_surface(baseline, candidate):
    return (baseline['status']=='RED' and bool(baseline['failed']) and candidate['status']=='GREEN'
            and candidate['passed']==baseline['passed'] | baseline['failed']
            and candidate['skipped']==baseline['skipped'])


def _case_key(nodeid):
    """Map a `path::name` nodeid to the same `(classname, name)` identity the pytest report yields."""
    path, _, leaf = str(nodeid).partition('::')
    parts = [p for p in path.replace('\\', '/').split('/') if p]
    if parts[:1] == ['tests']:
        parts = parts[1:]
    if parts and parts[-1].endswith('.py'):
        parts[-1] = parts[-1][:-3]
    if parts[:1] == ['src']:
        parts = parts[1:]
    classname = '.'.join(parts)
    return (classname, leaf)


def _stdlib_surface(root, targets, *, timeout):
    """Run the same surface with no pytest, via the `os.fork()` CoW stdlib runner.

    `pytest` is not a dependency of this project, and the benchmark numbers must
    come from an oracle that runs wherever the spine runs. The spine already
    ships a runner that discovers plain `def test_*` functions, `Test*` classes
    and `unittest.TestCase` subclasses -- and that fails closed on an empty run,
    which is the exact lie this module was written to catch.

    Nothing is relaxed relative to the pytest path: an empty run is NO_CASES, a
    crashing or timing-out runner is RUNNER_ERROR, and only "all cases passed
    and at least one ran" is GREEN. `error` cases are an errored case; they are
    never silently dropped.
    """
    from canonical.swe_kernel import stdlib_cow_test_runner_v1 as cow_runner

    payload = cow_runner.run_targets_cow_fork(
        root, targets or ('.',), timeout_s=min(15.0, float(timeout)),
    )
    result = dict(
        status='NO_CASES', passed=set(), failed=set(), skipped=set(),
        output=str(payload.get('output') or ''),
    )
    if not payload.get('ok', True) and payload.get('timed_out'):
        return {**result, 'status': 'TIMEOUT'}
    errored = payload.get('errored_nodeids') or ()
    failed = payload.get('failed_nodeids') or ()
    # A payload carrying no counts at all means the child died before reporting.
    if payload.get('passed') is None and not failed:
        return {**result, 'status': 'RUNNER_ERROR'}
    for nodeid in failed:
        result['failed'].add(_case_key(nodeid))
    for nodeid in errored:
        result['failed'].add(_case_key(nodeid))
    passed_nodeids = payload.get('passed_nodeids') or ()
    if len(passed_nodeids) != int(payload.get('passed') or 0):
        # Identity is part of this surface's contract: `restored_surface`
        # compares the case sets, so a count without identities cannot be
        # represented honestly. Refuse rather than invent keys.
        return {**result, 'status': 'RUNNER_ERROR'}
    for nodeid in passed_nodeids:
        result['passed'].add(_case_key(nodeid))
    if result['failed']:
        return {**result, 'status': 'RED'}
    if result['passed']:
        return {**result, 'status': 'GREEN'}
    return result


def test_surface(root, targets, *, timeout):
    result = dict(status='NO_CASES', passed=set(), failed=set(), skipped=set(), output='')
    if timeout <= 0:
        return {**result, 'status':'TIMEOUT'}
    try:
        import pytest  # noqa: F401
        has_pytest = True
    except ImportError:
        has_pytest = False
    if not has_pytest:
        return _stdlib_surface(root, targets, timeout=timeout)
    with tempfile.TemporaryDirectory(prefix='test_surface_') as td:
        xml = Path(td)/'report.xml'
        cmd = [sys.executable, '-m', 'pytest', '-q', '--tb=short', '-p', 'no:cacheprovider',
               '-o', 'addopts=', '--junitxml='+str(xml), '--', *(targets or ['.'])]
        env={'PATH':f'{Path(sys.executable).parent}:/usr/bin:/bin', 'HOME':td, 'LC_ALL':'C.UTF-8',
             'PYTHONPATH':os.pathsep.join([str(Path(root)/'src'), str(root)]), 'PYTHONDONTWRITEBYTECODE':'1',
             'PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1'}
        with tempfile.TemporaryFile() as log:
            proc = subprocess.Popen(cmd,cwd=root,env=env,stdin=subprocess.DEVNULL,stdout=log,
                                    stderr=subprocess.STDOUT,start_new_session=True)
            try:
                proc.wait(timeout=min(15,timeout))
            except subprocess.TimeoutExpired:
                try: os.killpg(proc.pid,signal.SIGKILL)
                except ProcessLookupError: pass
                proc.wait()
                return {**result, 'status':'TIMEOUT'}
            size=log.tell();log.seek(max(0,size-65536))
            result['output']=log.read().decode(errors='replace')
        if not xml.is_file():
            return {**result, 'status':'NO_REPORT'}
        try:
            cases = ET.parse(xml).findall('.//testcase')
        except ET.ParseError:
            return {**result, 'status':'MALFORMED_REPORT'}
        seen = set()
        for case in cases:
            key = (case.get('classname'), case.get('name'))
            if key in seen or not all(key) or case.find('error') is not None:
                return {**result, 'status':'INCOMPLETE_CASES'}
            seen.add(key)
            bucket = ('failed' if case.find('failure') is not None else
                      'skipped' if case.find('skipped') is not None else 'passed')
            result[bucket].add(key)
        if proc.returncode == 1 and result['failed']:
            result['status'] = 'RED'
        elif proc.returncode == 0 and result['passed'] and not result['failed']:
            result['status'] = 'GREEN'
        elif proc.returncode not in (0,5):
            result['status'] = 'RUNNER_ERROR'
        return result


def merge_vocab(current, learned):
    """Merge by actual template identity; repeated witnesses do not inflate support."""
    from canonical.swe_kernel.induced_edit_basis_v1 import EditTemplate, NodeTemplate
    result = {}
    for kind, cls in [('leaf', EditTemplate), ('node', NodeTemplate)]:
        by_id = {}
        for row in [*current.get(kind, ()), *learned.get(kind, ())]:
            if isinstance(row, dict):
                values = {k.name:row[k.name] for k in dataclasses.fields(cls)}
                for field in ('context', 'taught_by'):
                    values[field] = tuple(values[field])
                row = cls(**values)
            key = row.template_id()
            if key in by_id:
                witnesses = tuple(sorted(set(row.taught_by) | set(by_id[key].taught_by)))
                row = dataclasses.replace(row, taught_by=witnesses, support=len(witnesses))
            by_id[key] = row
        result[kind] = list(by_id.values())
    return result


def export_vocab(vocab):
    return {kind:[row.as_dict() for row in rows] for kind,rows in vocab.items()}
