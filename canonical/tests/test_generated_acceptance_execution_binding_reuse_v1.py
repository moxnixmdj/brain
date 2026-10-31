"""Actual generated programs under normal/optimized interpreters; no import stubs."""
from pathlib import Path
import sys
import tempfile
import pytest
from canonical.runtime.bound_capabilities import python_software_request_semantic_acceptance_v1 as compiler
from canonical.runtime.bound_capabilities import python_test_guided_patch_search_v1 as engine

CASES = [
    ('Calling m.f with JSON arguments [] must be true.', 'def f(): return True\n', 'def f(): return False\n'),
    ('File "m.py" must contain exact text "TOKEN".', 'value = "TOKEN"\n', 'value = "other"\n'),
    ('Python function f must exist in file "m.py".', 'def f(): return 1\n', 'class C: pass\n'),
    ('Python class C must exist in file "m.py".', 'class C: pass\n', 'def f(): return 1\n'),
    ('Calling m.f with JSON arguments [] must raise ValueError.', 'def f(): raise ValueError("expected")\n', 'def f(): return None\n'),
]


@pytest.mark.parametrize('flags', [[], ['-O'], ['-OO']], ids=['normal','optimized','double-optimized'])
@pytest.mark.parametrize('accepted', [True, False], ids=['correct','incorrect'])
@pytest.mark.parametrize('task,good,bad', CASES, ids=['boolean','text','function','class','exception'])
def test_every_generated_contract_retains_verdict_under_optimization(flags, accepted, task, good, bad):
    compilation = compiler.compile_request(task)
    assert compilation['coverage_complete'] is True
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        source = root/'m.py'
        source.write_text(good if accepted else bad)
        program = root/'check.py'
        program.write_text(compiler.render_test(compilation))
        before = source.read_bytes(), program.read_bytes()
        result = engine._run_tests(root, [sys.executable, *flags, 'check.py'], 3)
        assert (result['returncode'] == 0) is accepted, result
        assert ('V9_SEMANTIC_ACCEPTANCE_PASS' in result['stdout']) is accepted
        assert (source.read_bytes(), program.read_bytes()) == before


@pytest.mark.parametrize('flags', [[], ['-O'], ['-OO']], ids=['normal','optimized','double-optimized'])
def test_preloaded_standard_library_module_cannot_impersonate_candidate(flags):
    compilation = compiler.compile_request('Calling os.fspath with JSON arguments ["x"] must equal "x".')
    assert compilation['coverage_complete'] is True
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        source = root/'os.py'
        source.write_text('def fspath(x): return "wrong candidate"\n')
        (root/'check.py').write_text(compiler.render_test(compilation))
        result = engine._run_tests(root, [sys.executable, *flags, 'check.py'], 3)
        assert result['returncode'] != 0, result
        assert 'SEMANTIC_MODULE_ORIGIN_MISMATCH:os' in result['stderr']
        assert 'V9_SEMANTIC_ACCEPTANCE_PASS' not in result['stdout']
        assert source.read_text() == 'def fspath(x): return "wrong candidate"\n'


@pytest.mark.parametrize('flags', [[], ['-O'], ['-OO']], ids=['normal','optimized','double-optimized'])
@pytest.mark.parametrize('layout', ['package', 'package-and-module', 'dotted-module'])
def test_real_candidate_imports_preserve_unique_local_module_policy(flags, layout):
    module = 'pkg.child' if layout == 'dotted-module' else 'pkg'
    compilation = compiler.compile_request(f'Calling {module}.f with JSON arguments [] must be true.')
    assert compilation['coverage_complete'] is True
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        package = root/'pkg'
        package.mkdir()
        (package/'__init__.py').write_text('' if layout == 'dotted-module' else 'def f(): return True\n')
        if layout == 'dotted-module':
            (package/'child.py').write_text('def f(): return True\n')
        if layout == 'package-and-module':
            # Existing compiler policy refuses ambiguous file/package candidates.
            (root/'pkg.py').write_text('def f(): return False\n')
        (root/'check.py').write_text(compiler.render_test(compilation))
        result = engine._run_tests(root, [sys.executable, *flags, 'check.py'], 3)
        if layout == 'package-and-module':
            assert result['returncode'] != 0, result
            assert 'SEMANTIC_MODULE_NOT_UNIQUE_REPOSITORY_LOCAL:pkg' in result['stderr']
            assert 'V9_SEMANTIC_ACCEPTANCE_PASS' not in result['stdout']
        else:
            assert result['returncode'] == 0, result
            assert 'V9_SEMANTIC_ACCEPTANCE_PASS' in result['stdout']
