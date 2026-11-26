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


def test_surface(root, targets, *, timeout):
    result = dict(status='NO_CASES', passed=set(), failed=set(), skipped=set(), output='')
    if timeout <= 0:
        return {**result, 'status':'TIMEOUT'}
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
