"""Content identity, untrusted cache and implicit API controls on real adapters."""
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys

from canonical.runtime.bound_capabilities import python_source_definition_count as counter
from canonical.runtime.bound_capabilities import software_repair_crossfile_choreograph_v1 as repair
from canonical.runtime import goal_compiler as compiler

ROOT = Path(__file__).resolve().parents[2]


def test_same_size_timestamp_preserving_edit_is_recounted(tmp_path):
    source = tmp_path / 'source'
    source.mkdir()
    file = source / 'm.py'
    file.write_bytes(b'def f(): pass\n')
    first = counter.run({'source_root': 'source', 'output_path': 'one.json'}, tmp_path)
    stat = file.stat()
    file.write_bytes(b'value = 1    \n'[:stat.st_size])
    # Keep exactly the same size and mtime, as packaging/restore tools can do.
    assert file.stat().st_size == stat.st_size
    os.utime(file, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    second = counter.run({'source_root': 'source', 'output_path': 'two.json'}, tmp_path)
    assert first['function_count'] == 1
    assert second['function_count'] == 0


def test_executable_legacy_cache_is_not_deserialized(tmp_path):
    source = tmp_path / 'source'
    source.mkdir()
    (source / 'm.py').write_text('def f(): pass\n')
    cache_dir = tmp_path / 'cache'
    cache_dir.mkdir()
    code = '''import json,pickle,sys,tempfile,hashlib
from pathlib import Path
from canonical.runtime.bound_capabilities import python_source_definition_count as counter
root=Path(sys.argv[1]); marker=root/'executed.txt'; source=root/'source'
class CachePayload:
 def __reduce__(self): return (marker.write_text, ('untrusted cache executed',))
cache=Path(tempfile.gettempdir())/('brain_def_count_v1_'+hashlib.sha256(str(source).encode()).hexdigest()[:16]+'.pkl')
cache.write_bytes(pickle.dumps(CachePayload()))
result=counter.run({'source_root':'source','output_path':'count.json'},root)
print(json.dumps({'executed':marker.exists(),'count':result['function_count']}))
'''
    proc = subprocess.run([sys.executable, '-c', code, str(tmp_path)], cwd=ROOT,
                          env=dict(os.environ, TMPDIR=str(cache_dir)),
                          capture_output=True, text=True, check=True)
    result = json.loads(proc.stdout)
    assert result == {'executed': False, 'count': 1}


def test_implicit_public_api_is_not_deleted_by_unrequested_pruning(tmp_path):
    app = tmp_path / 'project/app'
    tests = tmp_path / 'project/tests'
    app.mkdir(parents=True)
    tests.mkdir()
    (app / '__init__.py').write_text('')
    (tests / '__init__.py').write_text('')
    source = app / 'api.py'
    source.write_text('def kept(x):\n    return x+1\ndef public_api(x):\n    return x*2\n')
    (tests / 'test_api.py').write_text('import unittest\nfrom app.api import kept\n'
        'class T(unittest.TestCase):\n    def test_kept(self):\n        self.assertEqual(kept(1),2)\n')
    before = source.read_bytes()
    result = repair.run({'source_root':'project/app','output_path':'report.json'}, tmp_path)
    assert result['verified'] is True
    assert source.read_bytes() == before
    assert runpy.run_path(str(source))['public_api'](4) == 8


def test_explicit_file_scope_wins_over_context_directory(tmp_path):
    file = tmp_path / 'm.py'
    file.write_text('def f(): pass\n')
    entry = {'adapter_module': 'python_source_definition_count',
             'proposal_bindings': {'source_root': {'type':'path_file_or_dir'}}}
    paths = [('m.py',file),('.',tmp_path)]
    goal = f'Count the functions in the python file {file} in the source root {tmp_path}.'
    assert compiler._declared_exact_file_scope(entry,'source_root',paths,goal) == 'm.py'
    # The directory-only contract cannot acquire file authority.
    entry['proposal_bindings']['source_root']['type'] = 'path_dir'
    assert compiler._declared_exact_file_scope(entry,'source_root',paths,goal) is None


def test_two_named_source_files_do_not_acquire_unique_file_scope(tmp_path):
    paths = []
    for name in ['a.py','b.py']:
        file = tmp_path / name
        file.write_text('def f(): pass\n')
        paths.append((name,file))
    entry = {'adapter_module':'python_source_definition_count',
             'proposal_bindings': {'source_root':{'type':'path_file_or_dir'}}}
    assert compiler._declared_exact_file_scope(entry,'source_root',paths,
               'Count the functions in the file a.py and the file b.py.') is None


def test_explicit_public_removal_preserves_other_implicit_api(tmp_path):
    app = tmp_path / 'project/app'
    app.mkdir(parents=True)
    (app / '__init__.py').write_text('')
    source = app / 'api.py'
    source.write_text('def legacy(x):\n    return x\ndef public_api(x):\n    return x*2\n')
    tests = tmp_path / 'project/tests'
    tests.mkdir()
    (tests / '__init__.py').write_text('')
    (tests / 'test_api.py').write_text('import unittest\nfrom app.api import public_api\n'
        'class T(unittest.TestCase):\n    def test_public(self):\n        self.assertEqual(public_api(4),8)\n')
    repair.run({'source_root':'project/app', 'output_path':'report.json',
                'remove_functions':['legacy']}, tmp_path)
    namespace = runpy.run_path(str(source))
    assert 'legacy' not in namespace
    assert namespace['public_api'](4) == 8


def test_ambiguous_explicit_removal_fails_before_any_edit(tmp_path):
    app = tmp_path / 'project/app'
    app.mkdir(parents=True)
    for name in ['a.py','b.py']:
        (app / name).write_text('def legacy(): return 1\n')
    before = {p:p.read_bytes() for p in app.glob('*.py')}
    import pytest
    with pytest.raises(RuntimeError, match='REMOVAL_TARGET_NOT_UNIQUE'):
        repair.run({'source_root':'project/app', 'output_path':'report.json',
                    'remove_functions':['legacy']}, tmp_path)
    assert {p:p.read_bytes() for p in app.glob('*.py')} == before


def test_named_public_removal_survives_real_goal_binding():
    import tempfile
    from canonical.runtime import live_brain_route_admission_v1 as door
    parent = ROOT / 'canonical/astra_runtime/tmp'
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='explicit-removal-', dir=parent) as raw:
        project = Path(raw)
        app = project / 'app'
        tests = project / 'tests'
        app.mkdir()
        tests.mkdir()
        (app / '__init__.py').write_text('')
        (tests / '__init__.py').write_text('')
        source = app / 'api.py'
        source.write_text('def legacy(x):\n    return x\ndef public_api(x):\n    return x*2\n')
        (tests / 'test_api.py').write_text('import unittest\nfrom app.api import public_api\n'
            'class T(unittest.TestCase):\n    def test_public(self):\n        self.assertEqual(public_api(4),8)\n')
        result = door.solve({'task_id':'explicit-removal-control',
            'goal':f'Remove the unused function legacy from {app.relative_to(ROOT)} and keep the suite green.'})
        assert result['pass'] is True, result.get('status')
        namespace = runpy.run_path(str(source))
        assert 'legacy' not in namespace
        assert namespace['public_api'](4) == 8
