"""Reused search/measurement in a real namespace, with actual pytest replay."""
import pytest

from canonical.runtime.confined_crossfile_qualification_v1 import qualify_repair
from canonical.tests.test_zero_ambient_namespace_launcher_v1 import UID, GID


def fixture(tmp_path, pair=False):
    (tmp_path / 'a.py').write_text('def helper(x): return x < 3\ndef a(x): return helper(x)\n')
    if pair:
        (tmp_path / 'b.py').write_text('def b(x): return x > 5\n')
        fail = 'from a import a\nfrom b import b\nassert a(3) and b(5)\n'
        passing = 'from a import a\nfrom b import b\nassert a(2) and b(6)\n'
        test = 'from a import a\nfrom b import b\ndef test_boundaries():\n    assert a(3) and b(5)\n    assert a(2) and b(6)\n    assert not a(4)\n    assert not b(4)\n'
    else:
        fail = 'from a import a\nassert a(3)\n'
        passing = 'from a import a\nassert a(2)\n'
        test = 'from a import a\ndef test_boundary():\n    assert a(3)\n    assert not a(4)\n'
    (tmp_path / 'trace_fail.py').write_text(fail)
    (tmp_path / 'trace_pass.py').write_text(passing)
    (tmp_path / 'test_all.py').write_text(test)
    return {'task_text': 'tests_pass must be true.', 'test_paths': ['trace_fail.py', 'trace_pass.py'],
            'search_limits': {'max_guided_files': 2, 'mutations_per_file': 12,
                              'max_pair_candidates': 100, 'timeout_s': 10}}


def run(path, task):
    return qualify_repair(path, task, host_uid=UID, host_gid=GID)


@pytest.mark.parametrize('pair', [False, True])
def test_synthesized_single_or_coupled_patch_is_measured_and_replayed(tmp_path, pair):
    task = fixture(tmp_path, pair)
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    result = run(tmp_path, task)
    assert result['pass'] is True, result
    assert result['source_unchanged'] is True
    assert result['input_snapshot_unchanged'] is True
    observed = result['observed']
    assert observed['baseline']['failed'] == 1
    assert observed['replay']['completed'] == 1
    assert observed['replay']['failed'] == 0
    repair = observed['repair']
    assert repair['measured_fields']['test_count'] == 1
    assert repair['measured_fields']['tests_pass'] is True
    assert repair['winner_mode'] == ('COUPLED_PAIR_GUIDED' if pair else 'SINGLE_GUIDED')
    assert len(repair['patches']) == (2 if pair else 1)
    assert len(repair['repair_search']['verification_replays']) == 2
    assert repair['repair_search']['provenance_hypothesis_count'] > 0
    assert observed['candidate_unchanged_during_replay'] is True
    assert result['source_promotion_performed'] is False
    assert result['independent_semantic_oracle_credit'] is False
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == before


def test_unbound_requirement_does_not_disappear_after_search(tmp_path):
    task = fixture(tmp_path)
    task['task_text'] = 'tests_pass must be true and preserve every unknown business requirement.'
    result = run(tmp_path, task)
    assert result['pass'] is False
    report = result['observed']['repair']
    assert report['repair_pass'] is True
    assert report['acceptance_stop_authorized'] is False
    assert report['semantic_residual_obligation_ids']
    assert 'replay' not in result['observed']


def test_already_passing_baseline_is_not_a_repair(tmp_path):
    task = fixture(tmp_path)
    (tmp_path / 'a.py').write_text('def a(x): return x <= 3\n')
    result = run(tmp_path, task)
    assert result['pass'] is False
    assert result['observed']['reason'] == 'FAILING_EXECUTED_BASELINE_REQUIRED'
    assert 'repair' not in result['observed']


@pytest.mark.parametrize('change', [
    {'test_argv': ['python', '-c', 'pass']},
    {'task_text': ''},
    {'test_paths': []},
    {'test_paths': ['../outside.py']},
    {'test_paths': ['/tmp/outside.py']},
    {'test_paths': ['trace_fail.py', 'trace_fail.py']},
    {'test_paths': ['missing.py']},
    {'search_limits': {'timeout_s': True}},
    {'search_limits': {'mutations_per_file': 0}},
    {'search_limits': {'max_pair_candidates': 20001}},
    {'search_limits': {'unknown_limit': 1}},
])
def test_invalid_task_refuses_before_executing_source(tmp_path, change):
    task = fixture(tmp_path)
    task.update(change)
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    with pytest.raises(ValueError, match='REPAIR_'):
        run(tmp_path, task)
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == before
