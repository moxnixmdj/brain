"""Producer audit of post-PR6506 semantic boundaries; not a certification.

Run from repository root:
    PYTHONPATH=. .venv/bin/python canonical/verification/swe_postmerge_semantic_audit_20261031.py

Calls real public adapters on disposable, deliberately under-tested projects.
Never runs against application source in this checkout and never patches loaders.
The reported wrong outputs/mutations are observations, not expected-good behavior.
"""
import json
from pathlib import Path
import runpy
import sys
from tempfile import TemporaryDirectory

from canonical.runtime.bound_capabilities import software_repair_crossfile_choreograph_v1 as repair
from canonical.runtime.bound_capabilities import python_tests_generate_scaffold as scaffold

PAIR = '''def has_dupes(xs):
    for i in range(len(xs)):
        for j in range(i + 1, len(xs)):
            if xs[i] == xs[j]:
                return True
    return False
'''
ADJACENT = '''def has_dupes(xs):
    for i in range(len(xs) - 1):
        for j in [i + 1]:
            if xs[i] == xs[j]:
                return True
    return False
'''

def call(path, value):
    try:
        return {'value':runpy.run_path(str(path))['has_dupes'](value)}
    except Exception as e:
        return {'error':type(e).__name__,'message':str(e)}

results = {}
Path('.arena').mkdir(exist_ok=True)
with TemporaryDirectory(prefix='postmerge-semantic-', dir=Path('.arena').resolve()) as td:
    work=Path(td)
    for name, source, witness in [('unhashable_elements', PAIR, [[1],[1]]),
                                  ('adjacent_only_comparison', ADJACENT, [1,2,1])]:
        root=work/name
        app=root/'project/app';tests=root/'project/tests'
        app.mkdir(parents=True);tests.mkdir()
        (app/'__init__.py').write_text('');(tests/'__init__.py').write_text('')
        target=app/'check.py';target.write_text(source)
        (tests/'test_check.py').write_text('import unittest\nfrom app.check import has_dupes\n'
             'class T(unittest.TestCase):\n'
             '    def test_duplicate(self):\n        self.assertTrue(has_dupes([1,1]))\n'
             '    def test_distinct(self):\n        self.assertFalse(has_dupes([1,2,3]))\n')
        before=call(target,witness)
        try:
            res=repair.run({'source_root':'project/app','output_path':'repair.json'},root)
            results[name]={'before':before,'after':call(target,witness),
                'verified':res.get('verified'),'mode':res.get('mode'),'edit_count':res.get('edit_count')}
        except BaseException as e:
            results[name]={'before':before,'adapter_error':type(e).__name__+':'+str(e)}
    root=work/'public_api_pruning';app=root/'project/app';tests=root/'project/tests'
    app.mkdir(parents=True);tests.mkdir()
    (app/'__init__.py').write_text('');(tests/'__init__.py').write_text('')
    target=app/'api.py'
    target.write_text('__all__ = ["kept", "public_api"]\n'
        'def kept(x):\n    return x + 1\n'
        'def public_api(x):\n    return x * 2\n')
    (tests/'test_api.py').write_text('import unittest\nfrom app.api import kept\n'
        'class T(unittest.TestCase):\n    def test_kept(self):\n        self.assertEqual(kept(1),2)\n')
    before=runpy.run_path(str(target))['public_api'](4)
    try:
        res=repair.run({'source_root':'project/app','output_path':'repair.json'},root)
        after=runpy.run_path(str(target))
        results['public_api_pruning']={'before':before,'declared_in_all':'public_api' in after['__all__'],
            'public_api_exists_after':'public_api' in after,'verified':res.get('verified'),'mode':res.get('mode')}
    except BaseException as e:
        results['public_api_pruning']={'adapter_error':type(e).__name__+':'+str(e)}
    for suffix in ('txt','py'):
        root=work/('scaffold_mutation_'+suffix);app=root/'source';app.mkdir(parents=True)
        state=app/('state.'+suffix);state.write_text('VALUE = 1\n' if suffix=='py' else 'original')
        original=state.read_bytes()
        (app/'m.py').write_text('from pathlib import Path\ndef f(x: int):\n'
            f'    Path(__file__).with_name("state.{suffix}").write_text("VALUE = 999\\n")\n'
            '    return x\n')
        try:
            res=scaffold.run({'source_root':'source','generated_tests_root':'tests',
                             'output_path':'report.json','python_executable':sys.executable},root)
            results['scaffold_mutation_'+suffix]={'verified':res.get('verified'),
                'test_passed':res.get('test_passed'),'source_data_preserved':state.read_bytes()==original}
        except BaseException as e:
            results['scaffold_mutation_'+suffix]={'adapter_error':type(e).__name__+':'+str(e),
                'source_data_preserved':state.exists() and state.read_bytes()==original}
    root=work/'async_smoke';app=root/'source';app.mkdir(parents=True)
    (app/'m.py').write_text('async def f(x: int):\n    raise RuntimeError("body must fail if executed")\n')
    try:
        res=scaffold.run({'source_root':'source','generated_tests_root':'tests',
                         'output_path':'report.json','python_executable':sys.executable},root)
        results['async_smoke']={'verified':res.get('verified'),'test_passed':res.get('test_passed'),
                               'async_body':'unconditional RuntimeError if actually awaited'}
    except BaseException as e:
        results['async_smoke']={'adapter_error':type(e).__name__+':'+str(e)}
print(json.dumps(results,indent=2))
