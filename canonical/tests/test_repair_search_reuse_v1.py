"""Differential rendering, actual process counts, and fresh acceptance checks."""
import ast
import sys

import pytest

from canonical.runtime.bound_capabilities import python_coupled_software_repair_loop_v1 as coupled
from canonical.runtime.bound_capabilities import python_provenance_guided_coupled_repair_v1 as guided
from canonical.runtime.bound_capabilities import python_repair_measured_acceptance_controller_v1 as measured


def reference_pool(row, tests, limit):
    """Original parse-per-edit algorithm, independently expressed as an oracle."""
    text = row['path'].read_bytes().decode('utf-8')
    parsed = ast.parse(text)
    nums, strings = coupled._PATCH._test_literals(tests)
    raw = text.encode('utf-8')
    lines = raw.splitlines(keepends=True)
    rows = []
    for key, descriptor, replace in coupled._PATCH._candidate_specs(parsed, nums, strings):
        again = ast.parse(text)
        target = next(n for n in ast.walk(again) if coupled._PATCH._node_key(n) == key)
        replacement = replace(target)
        ast.fix_missing_locations(replacement)
        data = ast.unparse(replacement).encode('utf-8')
        start = coupled._PATCH._byte_offset(lines, target.lineno, target.col_offset)
        end = coupled._PATCH._byte_offset(lines, target.end_lineno, target.end_col_offset)
        if raw[start:end] == data:
            continue
        priority = max([s['score'] for s in row['symbols'] if s['score'] > 0
                        and s['lineno'] <= descriptor['lineno'] <= s['end_lineno']] or [0])
        rows.append((priority, {'start': start, 'end': end, 'replacement': data, 'mutation': descriptor}))
    rows.sort(key=lambda r: (-r[0], r[1]['start'], r[1]['end'], str(r[1]['mutation'])))
    return [r for _, r in rows[:limit]]


@pytest.mark.parametrize('source', [
    'def f(x):\n    return x < 3\n',
    "def f(x):\n    label = 'é'; return x + 2 if x > 0 else -1\n",
    'def f(x):\r\n    return not (x < 3 and x != 2)\r\n',
    "@staticmethod\ndef f(x):\n    assert x > 0\n    return 'old' if x else 'new'\n",
    'class C:\n    async def f(self, x):\n        while x < 3:\n            x = x + 1\n        return x\n',
])
def test_same_candidate_bytes_order_and_priority_as_parse_per_edit(tmp_path, source):
    path = tmp_path / 'm.py'
    path.write_bytes(source.encode())
    tests = tmp_path / 'test_values.py'
    tests.write_text("values = [0, 2, 9, 'old', 'new', 'é']\n")
    row = {'path': path, 'symbols': coupled._defs(path)}
    for index, symbol in enumerate(row['symbols']):
        symbol['score'] = index + 1
    before = path.read_bytes()
    assert coupled._pool(row, [tests], 128) == reference_pool(row, [tests], 128)
    assert path.read_bytes() == before


def test_pool_parses_source_once_not_once_per_mutation(tmp_path):
    path = tmp_path / 'm.py'
    path.write_text(''.join(f'def f{i}(x): return x < {i}\n' for i in range(100)))
    row = {'path': path, 'symbols': []}
    calls = []
    previous = sys.getprofile()
    def observe(frame, event, arg):
        if event == 'call' and frame.f_code is ast.parse.__code__:
            calls.append(frame.f_locals.get('filename'))
    try:
        sys.setprofile(observe)
        edits = coupled._pool(row, [], 12)
    finally:
        sys.setprofile(previous)
    assert len(edits) == 12
    assert calls == [str(path)]


def test_replacer_cannot_mutate_shared_parsed_tree():
    text = 'def f(x): return x < 3\n'
    tree = ast.parse(text)
    before = ast.dump(tree, include_attributes=True)
    target = next(n for n in ast.walk(tree) if isinstance(n, ast.Compare))
    def change(node):
        node.ops = [ast.LtE()]
        return node
    edit = coupled._edit_node(text.encode(), text.encode().splitlines(True), target, {}, change)
    assert edit['replacement'] == b'x <= 3'
    assert ast.dump(tree, include_attributes=True) == before


def fixture(root, flaky=False):
    (root / 'm.py').write_text('def f(x): return x < 3\n')
    (root / 'trace_fail.py').write_text('from m import f\nassert f(3)\n')
    (root / 'trace_pass.py').write_text('from m import f\nassert f(2)\n')
    oracle = ("from pathlib import Path\n"
              "p = Path('calls.log')\n"
              "with p.open('a') as log: log.write('ran\\n')\n"
              "from m import f\nassert f(3)\nassert f(2)\nassert not f(4)\n")
    if flaky:
        oracle += "assert len(p.read_text().splitlines()) != 3\n"
    (root / 'test_all.py').write_text(oracle)
    return {'source_root': '.', 'test_paths': ['trace_fail.py', 'trace_pass.py'],
            'test_argv': [sys.executable, 'test_all.py'], 'output_path': 'report.json',
            'timeout_s': 4, 'max_guided_files': 1, 'mutations_per_file': 12, 'max_pair_candidates': 50}


def test_first_single_success_still_gets_two_real_fresh_replays(tmp_path):
    args = fixture(tmp_path)
    before = (tmp_path / 'm.py').read_bytes()
    first = guided.run(args, tmp_path)
    assert first['pass'] is True
    assert first['single_candidates_tested'] == 1
    assert first['winner_mode'] == 'SINGLE_GUIDED'
    assert len(first['verification_replays']) == 2
    assert all(r['returncode'] == 0 and not r['timed_out'] for r in first['verification_replays'])
    assert len((tmp_path / 'calls.log').read_text().splitlines()) == 4
    second = guided.run({**args, 'output_path': 'second.json'}, tmp_path)
    assert second['pass'] is True
    assert second['patches'] == first['patches']
    assert len((tmp_path / 'calls.log').read_text().splitlines()) == 8
    assert (tmp_path / 'm.py').read_bytes() == before


def test_exploration_pass_and_fresh_replay_failure_emit_no_patch(tmp_path):
    args = fixture(tmp_path, flaky=True)
    before = (tmp_path / 'm.py').read_bytes()
    result = guided.run(args, tmp_path)
    assert result['pass'] is False
    assert result['patches'] == []
    assert len(result['verification_replays']) == 2
    assert result['verification_replays'][0]['returncode'] != 0
    assert result['source_restored'] is True
    assert (tmp_path / 'm.py').read_bytes() == before


def test_directory_test_target_is_rebased_to_actual_repaired_candidate(tmp_path):
    src = tmp_path / 'src'
    src.mkdir()
    fixture(src)
    tests = src / 'tests'
    tests.mkdir()
    (tests / 'test_m.py').write_text('from m import f\ndef test_boundary():\n    assert f(3)\n    assert not f(4)\n')
    original = (src / 'm.py').read_bytes()
    result = measured.run({'source_root': 'src', 'test_paths': ['src/trace_fail.py', 'src/trace_pass.py'],
        'test_argv': [sys.executable, '-m', 'pytest', '-q', str(tests)],
        'task_text': 'tests_pass must be true.', 'output_path': 'out/report.json',
        'timeout_s': 10, 'max_guided_files': 1, 'mutations_per_file': 12, 'max_pair_candidates': 30}, tmp_path)
    assert result['pass'] is True, result
    assert result['measured_fields']['tests_pass'] is True
    assert result['acceptance_stop_authorized'] is True
    assert result['source_restored'] is True
    assert (src / 'm.py').read_bytes() == original


@pytest.mark.parametrize('source', ['def invalid(:', '\udcff'])
def test_unparseable_source_does_not_invent_candidates(tmp_path, source):
    path = tmp_path / 'm.py'
    path.write_bytes(source.encode('utf-8', 'surrogatepass'))
    assert coupled._pool({'path': path, 'symbols': []}, [], 12) == []


@pytest.mark.parametrize('summary,expected', [
    ('621 passed, 22 subtests passed in 3.30s\n', 621),
    ('=== 2 failed, 5 passed, 1 skipped, 2 warnings in 0.10s ===\n', 7),
    ('1 passed, 1 error in 0.10s\n', 2),
    ('2 skipped in 0.01s\n', 0),
    ('Ran 2 tests in 0.01s\nOK\nRan 3 tests in 0.01s\nOK\n', 5),
    ('collected 99 items\n', 0),
])
def test_measurement_counts_real_summary_without_double_counting_subtests(summary, expected):
    from canonical.runtime.bound_capabilities.python_repository_acceptance_measurement_v1 import _test_count
    assert _test_count(summary) == expected
