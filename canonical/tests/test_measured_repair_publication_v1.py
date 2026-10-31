"""Actual controller execution must not replace caller-owned report bytes."""
import hashlib
import json
import sys

import pytest

from canonical.runtime.bound_capabilities import python_repair_measured_acceptance_controller_v1 as measured


def project(root, race=False):
    src = root / 'src'
    src.mkdir()
    (src / 'm.py').write_text('def f(x): return x < 3\n')
    (src / 'trace_fail.py').write_text('from m import f\nassert f(3)\n')
    (src / 'trace_pass.py').write_text('from m import f\nassert f(2)\n')
    report = root / 'out' / 'report.json'
    marker = root / 'executions.txt'
    body = ('import unittest\nfrom pathlib import Path\nfrom m import f\n'
            f'p = Path({str(marker)!r})\n'
            "with p.open('a') as stream: stream.write('ran\\n')\n")
    if race:
        body += (f'target = Path({str(report)!r})\n'
                 'try:\n'
                 "    with target.open('x') as stream: stream.write('concurrent caller work')\n"
                 'except FileExistsError:\n    pass\n')
    body += ('class T(unittest.TestCase):\n'
             '    def test_boundary(self):\n'
             '        self.assertTrue(f(3))\n'
             '        self.assertTrue(f(2))\n'
             '        self.assertFalse(f(4))\n'
             'if __name__ == "__main__": unittest.main()\n')
    (src / 'test_all.py').write_text(body)
    args = {'source_root': 'src', 'test_paths': ['src/trace_fail.py', 'src/trace_pass.py'],
            'test_argv': [sys.executable, str(src / 'test_all.py')],
            'task_text': 'tests_pass must be true.', 'output_path': 'out/report.json',
            'max_guided_files': 1, 'mutations_per_file': 12, 'max_pair_candidates': 10,
            'timeout_s': 5}
    return src, args, report, marker


def contents(src):
    return {p.name: p.read_bytes() for p in src.glob('*.py')}


@pytest.mark.parametrize('strategy', ['guided', 'iterative_then_guided'])
def test_existing_report_refuses_before_any_oracle_execution(tmp_path, strategy):
    src, args, report, marker = project(tmp_path)
    before = contents(src)
    report.parent.mkdir()
    report.write_bytes(b'existing caller work')
    with pytest.raises(measured.RepairAcceptanceError, match='OUTPUT_ALREADY_EXISTS'):
        measured.run({**args, 'repair_strategy': strategy}, tmp_path)
    assert report.read_bytes() == b'existing caller work'
    assert not marker.exists()
    assert contents(src) == before
    assert not list(report.parent.glob('.repair-search-*'))


@pytest.mark.parametrize('strategy', ['guided', 'iterative_then_guided'])
def test_report_created_after_preflight_is_not_replaced(tmp_path, strategy):
    src, args, report, marker = project(tmp_path, race=True)
    before = contents(src)
    with pytest.raises(measured.RepairAcceptanceError, match='OUTPUT_ALREADY_EXISTS'):
        measured.run({**args, 'repair_strategy': strategy}, tmp_path)
    assert report.read_bytes() == b'concurrent caller work'
    assert len(marker.read_text().splitlines()) >= 4
    assert contents(src) == before
    assert not list(report.parent.glob('.swe-report-*'))
    assert not list(report.parent.glob('.repair-search-*'))


def test_successful_atomic_report_keeps_exact_hash_and_acceptance_semantics(tmp_path):
    src, args, report, marker = project(tmp_path)
    before = contents(src)
    result = measured.run(args, tmp_path)
    raw = report.read_bytes()
    payload = json.loads(raw)
    assert result['pass'] is True
    assert result['acceptance_stop_authorized'] is True
    assert result['artifact_integrity_verified'] is True
    assert result['output_verified'] is True
    assert result['output_sha256'] == hashlib.sha256(raw).hexdigest()
    assert payload['pass'] is True
    assert payload['patches'] == result['patches']
    assert len(result['repair_search']['verification_replays']) == 2
    assert contents(src) == before
    assert not list(report.parent.glob('.swe-report-*'))


def test_existing_dangling_report_symlink_is_not_followed_or_replaced(tmp_path):
    src, args, report, marker = project(tmp_path)
    report.parent.mkdir()
    report.symlink_to('missing.json')
    with pytest.raises(measured.RepairAcceptanceError, match='OUTPUT_ALREADY_EXISTS'):
        measured.run(args, tmp_path)
    assert report.is_symlink()
    assert report.readlink().as_posix() == 'missing.json'
    assert not (report.parent / 'missing.json').exists()
    assert not marker.exists()
