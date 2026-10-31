"""Real specialist coordination; no fake executors or acceptance overrides."""
import sys

import pytest

from canonical.runtime.bound_capabilities import python_iterative_software_repair_loop_v1 as iterative
from canonical.runtime.bound_capabilities import python_repair_measured_acceptance_controller_v1 as measured
from canonical.runtime.confined_crossfile_qualification_v1 import qualify_repair
from canonical.tests.test_zero_ambient_namespace_launcher_v1 import UID, GID


def project(root, coupled=False):
    source = root / 'src'
    source.mkdir()
    names = [('a', 3), ('b', 5)] if coupled else [('a', 3), ('b', 5), ('c', 7)]
    for name, boundary in names:
        (source / (name + '.py')).write_text(f'def {name}(x): return x < {boundary}\n')
        (source / ('trace_' + name + '.py')).write_text(f'from {name} import {name}\nassert {name}({boundary})\n')
    if coupled:
        tests = ('from a import a\nfrom b import b\ndef test_joint():\n'
                 '    assert a(3) and b(5)\n    assert a(2) and b(4)\n'
                 '    assert not a(4)\n    assert not b(6)\n')
    else:
        tests = ''.join(f'from {n} import {n}\ndef test_{n}():\n    assert {n}({v})\n'
                        f'    assert {n}({v-1})\n    assert not {n}({v+1})\n' for n, v in names)
    (source / 'test_all.py').write_text(tests)
    args = {'source_root': 'src', 'test_paths': ['src/trace_' + n + '.py' for n, _ in names],
            'test_argv': [sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider', str(source)],
            'task_text': 'tests_pass must be true.', 'output_path': 'out/report.json',
            'repair_strategy': 'iterative_then_guided', 'timeout_s': 10,
            'max_guided_files': 3, 'mutations_per_file': 12, 'max_pair_candidates': 30,
            'iterative_candidates_per_file': 1, 'iterative_max_candidates': 12}
    return source, args


def contents(source):
    return {p.name: p.read_bytes() for p in source.glob('*.py')}


@pytest.mark.parametrize('source_root', ['src', '.'])
def test_three_edit_pytest_repair_uses_existing_iterative_engine_and_measured_gate(tmp_path, source_root):
    source, args = project(tmp_path)
    args['source_root'] = source_root
    before = contents(source)
    result = measured.run(args, tmp_path)
    assert result['pass'] is True, result
    assert result['winner_mode'] == 'ITERATIVE_STRICT_PROGRESS'
    assert len(result['patches']) == 3
    search = result['repair_search']
    assert [r['score_after'] for r in search['rounds']] == [2, 1, 0]
    assert search['tested_candidate_count'] == 6
    assert [r['engine'] for r in search['search_attempts']] == ['iterative']
    assert len(search['verification_replays']) == 2
    assert result['measured_fields']['test_count'] == 3
    assert result['acceptance_stop_authorized'] is True
    assert contents(source) == before
    assert not list((tmp_path / 'out').glob('.repair-search-*'))


def test_guided_pair_bound_does_not_solve_three_required_edits(tmp_path):
    source, args = project(tmp_path)
    before = contents(source)
    result = measured.run({**args, 'repair_strategy': 'guided'}, tmp_path)
    assert result['pass'] is False
    assert result['repair_pass'] is False
    assert result['repair_summary']['patches'] == []
    assert result['repair_summary']['pair_candidates_tested'] <= args['max_pair_candidates']
    assert contents(source) == before


def test_normal_exhaustion_falls_back_to_guided_nonmonotonic_pair(tmp_path):
    source, args = project(tmp_path, coupled=True)
    before = contents(source)
    result = measured.run(args, tmp_path)
    assert result['pass'] is True, result
    assert result['winner_mode'] == 'COUPLED_PAIR_GUIDED'
    assert [r['engine'] for r in result['repair_search']['search_attempts']] == ['iterative', 'guided']
    assert result['repair_search']['search_attempts'][0]['status'] == 'OPEN__NO_STRICTLY_IMPROVING_CANDIDATE'
    assert result['repair_search']['crossed_nonmonotonic_valley'] is True
    assert len(result['patches']) == 2
    assert contents(source) == before


def test_semantic_rejection_does_not_trigger_another_search_route(tmp_path):
    source, args = project(tmp_path)
    result = measured.run({**args, 'task_text': 'tests_pass must be false.'}, tmp_path)
    assert result['repair_pass'] is True
    assert result['pass'] is False
    assert result['acceptance_stop_authorized'] is False
    assert result['patches'] == []
    assert [a['engine'] for a in result['repair_search']['search_attempts']] == ['iterative']


def test_search_cannot_overwrite_or_delete_old_intermediate_file(tmp_path):
    source, args = project(tmp_path)
    output = tmp_path / 'out'
    output.mkdir()
    old = output / '.v8_repair_report.json'
    old.write_bytes(b'caller-owned artifact')
    result = measured.run(args, tmp_path)
    assert result['pass'] is True
    assert old.read_bytes() == b'caller-owned artifact'


def test_source_drift_stops_before_guided_fallback(tmp_path):
    source, args = project(tmp_path)
    test = source / 'test_all.py'
    test.write_text(test.read_text() + "\nfrom pathlib import Path\n(Path(__file__).parent / 'unexpected.txt').write_text('effect')\n")
    before = contents(source)
    with pytest.raises(measured.RepairAcceptanceError, match='PORTFOLIO_INPUT_DRIFT'):
        measured.run(args, tmp_path)
    assert contents(source) == before
    assert not (tmp_path / 'out/report.json').exists()
    assert not list((tmp_path / 'out').glob('.repair-search-*'))


def test_missing_executor_restores_trial_source_and_does_not_fallback(tmp_path):
    source, args = project(tmp_path)
    path = source / 'a.py'
    before = path.read_bytes()
    with pytest.raises(FileNotFoundError):
        iterative._best(tmp_path, path, [source / 'trace_a.py'],
                        ['/__brain_missing_executable__/python', 'missing_test.py'],
                        2, 3, 1, set(), None)
    assert path.read_bytes() == before


@pytest.mark.parametrize('override', [
    {'repair_strategy': 'invented'}, {'repair_strategy': None},
    {'iterative_max_rounds': True}, {'iterative_max_rounds': 0},
    {'iterative_candidates_per_file': 5001}, {'iterative_max_candidates': '12'},
])
def test_invalid_strategy_or_budget_refuses_before_source_work(tmp_path, override):
    source, args = project(tmp_path)
    before = contents(source)
    with pytest.raises(measured.RepairAcceptanceError, match='REPAIR_STRATEGY|ITERATIVE_LIMIT'):
        measured.run({**args, **override}, tmp_path)
    assert contents(source) == before
    assert not (tmp_path / 'out').exists()


@pytest.mark.parametrize('text,rc,timed_out,expected', [
    ('3 failed, 2 passed in 0.10s', 1, False, 3),
    ('1 failed, 2 errors in 0.10s', 1, False, 3),
    ('2 skipped in 0.10s', 1, False, None),
    ('1 error in 0.10s', 2, False, None),
    ('3 failed in 0.10s', 1, True, None),
    ('3 failed in 0.10s', 0, False, 0),
    ('FAIL: test_x\nFAILED (failures=2, errors=1)', 1, False, 3),
    ('FAILED tests/test_x.py::test_x\n', 1, False, None),
])
def test_failure_metric_understands_real_runner_shapes_without_inventing_scores(text, rc, timed_out, expected):
    assert iterative._score({'stdout': text, 'stderr': '', 'returncode': rc, 'timed_out': timed_out}) == expected


def test_confined_three_edit_portfolio_is_reconstructed_and_replayed(tmp_path):
    source, args = project(tmp_path)
    before = contents(source)
    payload = {'task_text': args['task_text'], 'repair_strategy': 'iterative_then_guided',
               'test_paths': [p.removeprefix('src/') for p in args['test_paths']],
               'search_limits': {k: args[k] for k in ('max_guided_files', 'iterative_candidates_per_file',
                                                     'iterative_max_candidates', 'timeout_s')}}
    result = qualify_repair(source, payload, host_uid=UID, host_gid=GID)
    assert result['pass'] is True, result
    observed = result['observed']
    assert observed['baseline']['failed'] == 3
    assert observed['repair']['winner_mode'] == 'ITERATIVE_STRICT_PROGRESS'
    assert len(observed['realized_patches']) == 3
    assert observed['replay']['completed'] == 3
    assert observed['replay']['failed'] == 0
    assert result['source_unchanged'] is True
    assert result['input_snapshot_unchanged'] is True
    assert result['source_promotion_performed'] is False
    assert result['independent_semantic_oracle_credit'] is False
    assert contents(source) == before


def test_failed_fresh_replay_restores_source_without_falling_back(tmp_path):
    source, args = project(tmp_path)
    counter = tmp_path / 'oracle-count.txt'
    test = source / 'test_all.py'
    test.write_text(test.read_text() + f'''
from pathlib import Path
def test_replay_stability():
    if a(3) and b(5) and c(7):
        p = Path({str(counter)!r})
        count = int(p.read_text()) + 1 if p.exists() else 1
        p.write_text(str(count))
        assert count < 3
''')
    before = contents(source)
    with pytest.raises(RuntimeError, match='FINAL_REPLAY_FAILED'):
        measured.run(args, tmp_path)
    assert counter.read_text() == '3'
    assert contents(source) == before
    assert not (tmp_path / 'out/report.json').exists()
    assert not list((tmp_path / 'out').glob('.repair-search-*'))


@pytest.mark.parametrize('code,error', [
    ('raise RuntimeError("execution error, not an interpretable test metric")\n',
     'BASELINE_FAILURE_METRIC_UNPARSEABLE'),
    ('import time\ntime.sleep(5)\n', 'BASELINE_TIMEOUT'),
])
def test_baseline_execution_failure_refuses_instead_of_trying_guided(tmp_path, code, error):
    source, args = project(tmp_path)
    oracle = source / 'oracle.py'
    oracle.write_text(code)
    before = contents(source)
    with pytest.raises(RuntimeError, match=error):
        measured.run({**args, 'test_argv': [sys.executable, str(oracle)], 'timeout_s': 1}, tmp_path)
    assert contents(source) == before
    assert not (tmp_path / 'out/report.json').exists()


def test_same_named_unowned_directory_is_not_excluded_from_drift_check(tmp_path):
    source, args = project(tmp_path)
    args['source_root'] = '.'
    test = source / 'test_all.py'
    test.write_text(test.read_text() + f'''
from pathlib import Path
scratch = next(Path({str(tmp_path / 'out')!r}).glob('.repair-search-*'))
unowned = Path({str(source)!r}) / 'nested' / scratch.name
unowned.mkdir(parents=True, exist_ok=True)
(unowned / 'effect.txt').write_text('must not be excluded')
''')
    before = contents(source)
    with pytest.raises(measured.RepairAcceptanceError, match='PORTFOLIO_INPUT_DRIFT'):
        measured.run(args, tmp_path)
    assert contents(source) == before
    assert not (tmp_path / 'out/report.json').exists()


@pytest.mark.parametrize('override', [
    {'repair_strategy': 'unknown'}, {'repair_strategy': False},
    {'search_limits': {'iterative_max_rounds': True}},
    {'search_limits': {'iterative_max_rounds': 21}},
    {'search_limits': {'iterative_candidates_per_file': 0}},
    {'search_limits': {'iterative_max_candidates': 50001}},
])
def test_confined_schema_validates_strategy_and_iterative_limits_before_execution(tmp_path, override):
    source, args = project(tmp_path)
    payload = {'task_text': args['task_text'], 'test_paths': ['trace_a.py'], **override}
    before = contents(source)
    with pytest.raises(ValueError, match='REPAIR_STRATEGY_UNSUPPORTED|REPAIR_SEARCH_LIMITS_INVALID'):
        qualify_repair(source, payload, host_uid=UID, host_gid=GID)
    assert contents(source) == before


def test_round_exhaustion_falls_back_without_publishing_partial_iterative_edits(tmp_path):
    source, args = project(tmp_path)
    before = contents(source)
    result = measured.run({**args, 'iterative_max_rounds': 1,
                           'mutations_per_file': 2, 'max_pair_candidates': 1}, tmp_path)
    assert result['pass'] is False
    assert result['repair_pass'] is False
    assert result['acceptance_stop_authorized'] is False
    assert result['repair_strategy'] == 'iterative_then_guided'
    summary = result['repair_summary']
    assert [a['engine'] for a in summary['search_attempts']] == ['iterative', 'guided']
    assert summary['search_attempts'][0]['status'] == 'OPEN__NO_COMPLETE_REPAIR_IN_BOUNDED_SEARCH'
    assert summary['search_attempts'][0]['tested_candidate_count'] == 1
    assert summary['patches'] == []
    assert contents(source) == before
