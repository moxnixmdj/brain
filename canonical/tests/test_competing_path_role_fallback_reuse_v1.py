"""Explicit file roles must survive fallback and action-template key order."""
from itertools import permutations
from pathlib import Path
import tempfile
import pytest
from canonical.runtime import goal_compiler as compiler
from canonical.runtime.live_integrated_brain_v1 import load_verified_registry


@pytest.mark.parametrize('order', list(permutations(['source_paths','test_paths','output_path'])))
@pytest.mark.parametrize('explicit_source', [False, True], ids=['source-directory','source-file'])
def test_named_tests_are_not_consumed_by_source_list_fallback(order, explicit_source):
    entry = dict(load_verified_registry()['python.software.repair.loop.test_guided.ast.v1'])
    entry['action_template'] = dict(entry['action_template'])
    entry['action_template']['args'] = {key:'${input.'+key+'}' for key in order}
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root/'project/src').mkdir(parents=True)
        (root/'project/src/module.py').write_text('def f(): return 1\n')
        # No test_ prefix: ownership must follow stated role, not name heuristics.
        (root/'project/src/driver.py').write_text('from module import f\nassert f() == 1\n')
        (root/'reports').mkdir()
        (root/'reports/result.json').write_text('{}')
        source = 'project/src/module.py' if explicit_source else 'root project/src'
        goal = f'Repair the python source {source} using the tests project/src/driver.py and save the report to reports/result.json.'
        bound = compiler._bind_inputs(goal, root, entry)
        assert bound['test_paths'] == ['project/src/driver.py']
        assert bound.get('source_paths', []) == (['project/src/module.py'] if explicit_source else [])
        assert bound['output_path'] == 'reports/result.json'
