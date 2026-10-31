"""Real request targets, not payload words or parent directories, govern work."""
from pathlib import Path
import json
import subprocess
import tempfile
import uuid

import pytest
from canonical.runtime import goal_compiler as compiler
from canonical.runtime import live_brain_route_admission_v1 as door
from canonical.runtime import swe_typed_plan_v1 as typed

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize('wording', [
    'Count the functions in {file}.',
    'Count the functions in the source file {file}.',
    'Count the functions in {file} and save the report to {report}.',
])
def test_public_count_keeps_named_file_not_parent(wording):
    parent = ROOT / 'canonical/astra_runtime/tmp'
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='intent-scope-', dir=parent) as raw:
        root = Path(raw)
        source = root / 'calc.py'
        source.write_text('def add(a,b):\n    return a+b\ndef mul(a,b):\n    return a*b\n')
        sibling = root / 'other.py'
        sibling.write_text('def unrelated():\n    return 0\n')
        before = {p.name: p.read_bytes() for p in root.glob('*.py')}
        goal = wording.format(file=source.relative_to(ROOT).as_posix(),
                              report=(root / 'report.json').relative_to(ROOT).as_posix())
        result = door.solve({'task_id': 'COUNT_SCOPE_' + uuid.uuid4().hex, 'goal': goal})
        assert result['pass'] is True, result
        rows = result.get('execution') or []
        assert len(rows) == 1, result
        row = rows[0]
        assert row['capability_id'] == 'python.source.definition_count.v1'
        data = row['result']
        assert data['files_scanned'] == 1, data
        assert data['function_count'] == 2, data
        assert {p.name: p.read_bytes() for p in root.glob('*.py')} == before
        report = ROOT / data['output_path']
        assert json.loads(report.read_text())['function_count'] == 2


@pytest.mark.parametrize('message', ['fix calc', 'repair the broken function', 'rename total to sum'])
def test_commit_payload_never_authorizes_source_repair(message):
    parent = ROOT / 'canonical/astra_runtime/tmp'
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='commit-intent-', dir=parent) as raw:
        repo = Path(raw)
        def git(*args):
            return subprocess.check_output(['git', '-C', str(repo), *args], text=True).strip()
        git('init', '-q', '--initial-branch=arena/1e5b1d49-brain')
        git('config', 'user.name', 'Fixture')
        git('config', 'user.email', 'fixture@example.invalid')
        source = repo / 'calc.py'
        source.write_text('def add(a,b):\n    return a-b\n')
        (repo / 'test_calc.py').write_text(
            'import unittest, calc\nclass T(unittest.TestCase):\n'
            '    def test_add(self): self.assertEqual(calc.add(2,3),5)\n')
        git('add', '.')
        git('commit', '-qm', 'fixture baseline')
        source.write_text(source.read_text() + '# requested existing change\n')
        git('add', 'calc.py')
        before = source.read_bytes()
        previous = git('rev-parse', 'HEAD')
        goal = f"Commit the current changes in {repo.relative_to(ROOT).as_posix()} with the message '{message}'."
        plan = typed.build_plan(goal, ROOT)
        assert plan is not None
        assert plan[2]['selected_capability'] == 'git.repository.operate.v1'
        assert plan[2]['inputs']['op'] == 'commit'
        # Never allow this test to commit the checkout under test.
        assert any(str(value) == repo.relative_to(ROOT).as_posix()
                   for value in plan[2]['inputs'].values()), plan[2]['inputs']
        result = door.solve({'task_id': 'COMMIT_INTENT_' + uuid.uuid4().hex, 'goal': goal})
        assert source.read_bytes() == before, result
        assert result['pass'] is True, result
        assert result['compiled_capability_id'] == 'git.repository.operate.v1', result
        assert git('rev-parse', 'HEAD') != previous
        assert git('log', '-1', '--format=%s') == message


def test_directory_scoped_commit_cannot_mutate_or_commit_enclosing_checkout():
    parent = ROOT / 'canonical/astra_runtime/tmp'
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='not-a-repository-', dir=parent) as raw:
        scope = Path(raw)
        source = scope / 'calc.py'
        source.write_text('def add(a,b):\n    return a-b\n')
        (scope / 'test_calc.py').write_text(
            'import unittest, calc\nclass T(unittest.TestCase):\n'
            '    def test_add(self): self.assertEqual(calc.add(2,3),5)\n')
        before = source.read_bytes()
        head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT)
        result = door.solve({'task_id': 'NON_REPO_COMMIT_' + uuid.uuid4().hex,
                             'goal': f"Commit the current changes in {scope.relative_to(ROOT).as_posix()} with the message 'fix calc'."})
        assert result['pass'] is False, result
        assert source.read_bytes() == before
        assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT) == head


def test_two_repository_scopes_do_not_default_to_enclosing_checkout():
    parent = ROOT / 'canonical/astra_runtime/tmp'
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='ambiguous-repos-', dir=parent) as raw:
        a, b = Path(raw) / 'one', Path(raw) / 'two'
        a.mkdir()
        b.mkdir()
        goal = f"Commit the changes in {a.relative_to(ROOT).as_posix()} and {b.relative_to(ROOT).as_posix()} with the message 'fix calc'."
        assert typed.build_plan(goal, ROOT) is None


@pytest.mark.parametrize('tests', [
    'import pytest\n@pytest.mark.skip(reason="not executed")\ndef test_never():\n    assert True\n',
    'import pytest\n@pytest.mark.parametrize("value", [1,2])\ndef test_value(value):\n    assert value < 2\n',
])
def test_native_verification_uses_real_pytest_semantics(tmp_path, tests):
    from canonical.runtime.bound_capabilities import software_repair_crossfile_choreograph_v1 as native
    (tmp_path / 'test_calc.py').write_text(tests)
    passed, ran, reason = native._verify_project(tmp_path, tmp_path)
    assert passed is False, (passed, ran, reason)


def test_native_verification_counts_actual_parameterized_passes(tmp_path):
    from canonical.runtime.bound_capabilities import software_repair_crossfile_choreograph_v1 as native
    (tmp_path / 'test_calc.py').write_text(
        'import pytest\n@pytest.mark.parametrize("value", [1,2])\ndef test_value(value):\n    assert value < 3\n')
    passed, ran, reason = native._verify_project(tmp_path, tmp_path)
    assert passed is True, reason
    assert ran == 2
