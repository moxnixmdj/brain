"""Real execution regressions for the post-6506 semantic audit; no mocked tools."""
import ast
import json
from pathlib import Path
import runpy
import sys

import pytest

from canonical.runtime.bound_capabilities import software_repair_crossfile_choreograph_v1 as repair
from canonical.runtime.bound_capabilities import python_tests_generate_scaffold as scaffold
from canonical.runtime.bound_capabilities import python_source_symbol_index as index

PAIR = '''def has_dupes(xs):
    for i in range(len(xs)):
        for j in range(i + 1, len(xs)):
            if xs[i] == xs[j]:
                return True
    return False
'''
ADJACENT = PAIR.replace('range(len(xs))', 'range(len(xs) - 1)').replace('range(i + 1, len(xs))', '[i + 1]')


def project(root, source=PAIR):
    app = root / 'project/app'
    tests = root / 'project/tests'
    app.mkdir(parents=True)
    tests.mkdir()
    (app / '__init__.py').write_text('')
    (tests / '__init__.py').write_text('')
    target = app / 'check.py'
    target.write_text(source)
    (tests / 'test_check.py').write_text(
        'import unittest\nfrom app.check import has_dupes\nclass T(unittest.TestCase):\n'
        '    def test_yes(self):\n        self.assertTrue(has_dupes([1,1]))\n'
        '    def test_no(self):\n        self.assertFalse(has_dupes([1,2,3]))\n')
    return target


def optimize(root):
    return repair.run({'source_root': 'project/app', 'output_path': 'report.json'}, root)


@pytest.mark.parametrize('values', [[[1], [1]], [{'x': 1}, {'x': 1}], [1, 2, 1], [1, '1', 1], []])
def test_duplicate_optimization_preserves_existing_input_domain(tmp_path, values):
    target = project(tmp_path)
    before = runpy.run_path(str(target))['has_dupes'](values)
    result = optimize(tmp_path)
    assert result['verified'] is True
    assert runpy.run_path(str(target))['has_dupes'](values) is before


def test_duplicate_optimization_preserves_nan_identity_semantics(tmp_path):
    target = project(tmp_path)
    nan = float('nan')
    before = runpy.run_path(str(target))['has_dupes']([nan, nan])
    optimize(tmp_path)
    assert before is False
    assert runpy.run_path(str(target))['has_dupes']([nan, nan]) is False


@pytest.mark.parametrize('source', [ADJACENT, PAIR.replace('xs[j]', 'xs[i]'),
                                    PAIR.replace('range(i + 1, len(xs))', 'range(i + 2, len(xs))')])
def test_noncanonical_scan_is_not_rewritten(tmp_path, source):
    target = project(tmp_path, source)
    # A matcher must establish the algorithm before the regression-suite gate.
    assert repair._match_nested_dup_scan(ast.parse(source).body[0]) is None
    before = target.read_bytes()
    if source == ADJACENT:
        optimize(tmp_path)
        assert target.read_bytes() == before
        assert runpy.run_path(str(target))['has_dupes']([1, 2, 1]) is False


def test_exported_api_survives_pruning(tmp_path):
    target = project(tmp_path, PAIR + '\n__all__ = ["has_dupes", "public_api"]\ndef public_api(x):\n    return x * 2\n')
    repair._try_dead_code_pruning(tmp_path / 'project', tmp_path / 'project/tests', [target])
    module = runpy.run_path(str(target))
    assert module['public_api'](4) == 8
    assert 'public_api' in module['__all__']


def test_dynamic_export_declaration_preserves_functions(tmp_path):
    target = project(tmp_path, 'EXPORTS = ["public_api"]\n__all__ = list(EXPORTS)\n' +
                     PAIR + '\ndef public_api(x):\n    return x * 2\n')
    # Exercise the pruning pass directly, independently of the optimizer.
    repair._try_dead_code_pruning(tmp_path / 'project', tmp_path / 'project/tests', [target])
    assert runpy.run_path(str(target))['public_api'](4) == 8


@pytest.mark.parametrize('action', ['text', 'python', 'delete', 'create', 'absolute', 'process'])
def test_smoke_subject_effects_are_refused_before_source_mutation(tmp_path, action):
    source = tmp_path / 'source'
    source.mkdir()
    state = source / ('state.py' if action == 'python' else 'state.txt')
    state.write_text('VALUE = 1\n')
    actions = {
        'text': 'p.write_text("changed")',
        'python': 'p.write_text("VALUE = 999\\n")',
        'delete': 'p.unlink()',
        'create': 'p.with_name("created.txt").write_text("new")',
        'absolute': f'Path({str(state)!r}).write_text("changed")',
        'process': 'subprocess.run([sys.executable, "-c", "pass"], check=True)',
    }
    (source / 'm.py').write_text('from pathlib import Path\nimport subprocess, sys\n'
        'def f(x: int):\n    p = Path(__file__).with_name(' + repr(state.name) + ')\n'
        '    ' + actions[action] + '\n    return x\n')
    before = {p.name: p.read_bytes() for p in source.iterdir()}
    result = scaffold.run({'source_root': 'source', 'generated_tests_root': 'generated',
                           'output_path': 'report.json', 'python_executable': sys.executable}, tmp_path)
    assert result['verified'] is False
    assert result['test_passed'] == 0
    report = json.loads((tmp_path / 'report.json').read_text())
    assert report['runner_evidence']['ran'] == 1
    assert report['runner_evidence']['read_only_effect_refused'] is True
    assert {p.name: p.read_bytes() for p in source.iterdir() if p.is_file()} == before


def test_scaffold_does_not_overwrite_reserved_probe_filename(tmp_path):
    source = tmp_path / 'source'
    source.mkdir()
    (source / 'm.py').write_text('def f(x: int):\n    return x\n')
    marker = source / '.testgen_probe_index.json'
    marker.write_bytes(b'owned by project, not the indexer')
    result = scaffold.run({'source_root': 'source', 'generated_tests_root': 'tests',
                           'output_path': 'report.json'}, tmp_path)
    assert result['verified'] is True
    assert marker.read_bytes() == b'owned by project, not the indexer'


def test_parallel_index_matches_real_serial_derivation(tmp_path):
    source = tmp_path / 'source'
    source.mkdir()
    for i in range(65):
        (source / f'm{i:03}.py').write_text(f'def f{i}(x):\n    return x + {i}\n')
    result = index.run({'source_root': 'source', 'output_path': 'index.json'}, tmp_path)
    artifact = json.loads((tmp_path / 'index.json').read_text())
    assert result['parsed_module_count'] == 65
    expected = []
    import hashlib
    for p in sorted(source.glob('*.py')):
        kind, row = index._parse_single_module_worker((p.relative_to(tmp_path).as_posix(),
                                 hashlib.sha256(p.read_bytes()).hexdigest(), str(p)))
        assert kind == 'ok'
        expected.append(row)
    assert artifact['modules'] == expected


def test_worker_refuses_hash_from_a_different_source_snapshot(tmp_path):
    source = tmp_path / 'm.py'
    source.write_text('def current():\n    return 1\n')
    kind, row = index._parse_single_module_worker(('m.py', '0' * 64, str(source)))
    assert kind == 'err'
    assert row['error'] == 'SOURCE_CHANGED_DURING_PARSE'


def test_optimized_scan_matches_exhaustive_mixed_value_witnesses(tmp_path):
    from itertools import product
    target = project(tmp_path)
    original = runpy.run_path(str(target))['has_dupes']
    optimize(tmp_path)
    optimized = runpy.run_path(str(target))['has_dupes']
    values = [None, True, False, 0, 1, '1', b'1', [], {}, float('nan')]
    for length in range(4):
        for items in product(values, repeat=length):
            assert optimized(list(items)) == original(list(items))


def test_optimization_preserves_shadowed_length_semantics(tmp_path):
    target = project(tmp_path, 'len = lambda xs: 2\n' + PAIR)
    original = runpy.run_path(str(target))['has_dupes']
    optimize(tmp_path)
    assert runpy.run_path(str(target))['has_dupes']([1, 2, 1]) == original([1, 2, 1])


def test_smoke_skip_is_not_execution_success(tmp_path):
    source = tmp_path / 'source'
    source.mkdir()
    (source / 'm.py').write_text('import unittest\ndef f(x: int):\n    raise unittest.SkipTest("not evaluated")\n')
    result = scaffold.run({'source_root': 'source', 'generated_tests_root': 'tests',
                           'output_path': 'report.json'}, tmp_path)
    assert result['verified'] is False
    assert result['test_passed'] == 0
