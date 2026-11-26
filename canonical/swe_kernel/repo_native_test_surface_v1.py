"""Observe the same pytest case identities before and after an edit (including unittest cases)."""
from __future__ import annotations

import dataclasses
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET


def test_surface(root, targets, *, timeout):
    result = dict(status='NO_CASES', passed=set(), failed=set(), skipped=set(), output='')
    if timeout <= 0:
        return {**result, 'status':'TIMEOUT'}
    with tempfile.TemporaryDirectory(prefix='test_surface_') as td:
        xml = Path(td)/'report.xml'
        cmd = [sys.executable, '-m', 'pytest', '-q', '--tb=short', '-p', 'no:cacheprovider',
               '-o', 'addopts=', '--junitxml='+str(xml), '--', *(targets or ['.'])]
        try:
            proc = subprocess.run(cmd, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  timeout=min(15,timeout), text=True, errors='replace',
                                  env={**os.environ, 'PYTHONPATH':str(root),'PYTHONDONTWRITEBYTECODE':'1',
                                       'PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1','PYTEST_ADDOPTS':''})
        except subprocess.TimeoutExpired:
            return {**result, 'status':'TIMEOUT'}
        result['output'] = proc.stdout
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
