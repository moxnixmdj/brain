"""Independent behavioral oracles for the current SWE counterexamples.

Real source, compilers, child processes and public routes; no tool mocks or
historical trees. Positive controls prevent safety from becoming blanket refusal.
"""
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile

import pytest

from canonical.swe_kernel import egraph_and_deductive_synthesizer_v1 as engine
from canonical.swe_kernel import polyglot_build_ci_engine_v1 as polyglot
from canonical.swe_kernel import transform_contracts_v1 as contracts
from canonical.runtime import live_brain_route_admission_v1 as door

ROOT = Path(__file__).resolve().parents[2]


def project(base, source, assertion):
    pkg, tests = base / 'pkg', base / 'tests'
    pkg.mkdir(parents=True)
    tests.mkdir()
    (tests / '__init__.py').write_text('')
    mod = pkg / 'subject.py'
    mod.write_text(source)
    (tests / 'test_subject.py').write_text('import unittest, subject\nclass T(unittest.TestCase):\n    def test_existing(self):\n        ' + assertion + '\n')
    return mod


def test_split_collision_is_non_destructive(tmp_path):
    mod = project(tmp_path, 'def foo(): return 1\ndef bar(): return 2\n', 'self.assertEqual(subject.foo(),1)')
    existing = mod.with_name('foo.py')
    existing.write_bytes(b'def existing_api(): return 42\n')
    before = {p: p.read_bytes() for p in (mod, existing)}
    result = engine.structural_refactor_python(mod, 'Split subject.py into one module per function.')
    assert result['reason'] == 'SPLIT_MODULE_DESTINATION_COLLISION'
    assert {p: p.read_bytes() for p in before} == before
    assert not mod.with_name('bar.py').exists()


def test_failed_split_removes_only_new_files_and_restores_bytes(tmp_path):
    mod = project(tmp_path, 'def foo(): return 1\ndef bar(): return 2\n', 'self.assertEqual(subject.foo.__module__, "subject")')
    before = mod.read_bytes()
    result = engine.structural_refactor_python(mod, 'Split subject.py into one module per function.')
    assert result['reason'] == 'SUITE_FAILED_AFTER_SPLIT_MODULE'
    assert mod.read_bytes() == before
    assert not mod.with_name('foo.py').exists()
    assert not mod.with_name('bar.py').exists()


def test_split_preserves_non_function_statements(tmp_path):
    mod = project(tmp_path, '"""API documentation."""\nFACTOR=3\n__all__=["foo"]\ndef foo(): return 1\ndef bar(): return 2\n', 'self.assertEqual(subject.FACTOR,3)')
    result = engine.structural_refactor_python(mod, 'Split subject.py into one module per function.')
    assert result['verified'] is True
    code = mod.read_text()
    assert 'FACTOR=3' in code
    assert '__all__=["foo"]' in code
    subprocess.run([sys.executable, '-B', '-c', 'import subject; assert subject.foo()==1 and subject.bar()==2 and subject.__all__==["foo"]'], cwd=mod.parent, check=True)


def test_split_refuses_unresolved_module_globals_without_mutation(tmp_path):
    mod = project(tmp_path, 'FACTOR=3\ndef scale(x): return x*FACTOR\ndef fixed(): return 7\n', 'self.assertEqual(subject.fixed(),7)')
    before = mod.read_bytes()
    result = engine.structural_refactor_python(mod, 'Split subject.py into one module per function.')
    assert result['reason'] == 'SPLIT_MODULE_GLOBAL_DEPENDENCIES_UNPROVED'
    assert mod.read_bytes() == before
    assert runpy.run_path(str(mod))['scale'](4) == 12


@pytest.mark.parametrize('prefix', ['__all__=["public_api"]\n', 'EXPORTS=["public_api"]\n__all__=list(EXPORTS)\n', ''])
def test_dead_code_preserves_public_and_exported_api(tmp_path, prefix):
    mod = project(tmp_path, prefix + 'def public_api(x): return x*2\ndef _unused(): return 99\ndef kept(x): return x+1\n', 'self.assertEqual(subject.kept(1),2)')
    before = mod.read_bytes()
    result = engine.structural_refactor_python(mod, 'Remove dead code and preserve the public API.')
    if prefix.startswith('EXPORTS'):
        assert result['reason'] == 'NO_DEAD_CODE_FOUND'
        assert mod.read_bytes() == before
        assert runpy.run_path(str(mod))['public_api'](4) == 8
        return
    assert result['verified'] is True
    namespace = runpy.run_path(str(mod))
    assert namespace['public_api'](4) == 8
    assert '_unused' not in namespace


@pytest.mark.parametrize('source', [
    'counter=0\ndef f(x):\n    global counter\n    counter+=1\n    return x+counter\n',
    'def f(x): return [x]\n',
    'VALUE=1\ndef f(x): return x+VALUE\n',
])
def test_effectful_or_mutable_memoization_is_refused(tmp_path, source):
    mod = project(tmp_path, source, 'self.assertTrue(callable(subject.f))')
    before = mod.read_bytes()
    result = engine.memoize_function(mod, 'f')
    assert result['reason'] == 'MEMOIZE_EFFECTS_OR_RESULT_DOMAIN_UNPROVED'
    assert mod.read_bytes() == before


def test_pure_recursive_memoization_and_noninteger_fallback(tmp_path):
    mod = project(tmp_path, '"""Keep the future import legal."""\nfrom __future__ import annotations\ndef fib(n):\n    return n if n<2 else fib(n-1)+fib(n-2)\n', 'self.assertEqual(subject.fib(7),13)')
    result = engine.memoize_function(mod, 'fib')
    assert result['verified'] is True
    fn = runpy.run_path(str(mod))['fib']
    assert fn(20) == 6765
    assert fn.cache_info().maxsize == 1024
    assert fn(-0.0) == -0.0
    assert fn.__name__ == 'fib'


def test_memo_analysis_does_not_execute_source_in_caller(tmp_path):
    marker = tmp_path / 'pids.txt'
    source = ('import os\nfrom pathlib import Path\n' + f'p=Path({str(marker)!r})\np.write_text((p.read_text() if p.exists() else "")+str(os.getpid())+"\\n")\n' + 'def square(x): return x*x\n')
    mod = project(tmp_path, source, 'self.assertEqual(subject.square(3),9)')
    assert engine.memoize_function(mod, 'square')['verified'] is True
    assert os.getpid() not in [int(x) for x in marker.read_text().splitlines()]


def test_thread_pool_preserves_absolute_value_reduction(tmp_path):
    mod = project(tmp_path, 'def magnitude(xs):\n    return sum(abs(x) for x in xs)\n', 'self.assertEqual(subject.magnitude([5]),5)')
    assert engine.add_thread_pool_parallel(mod, 'magnitude')['verified'] is True
    fn = runpy.run_path(str(mod))['magnitude']
    assert fn([-2,3]) == 5
    assert fn(iter([-2,3])) == 5
    assert fn([-2.5,3.5]) == 6.0


def test_arbitrary_reduction_is_not_replaced_with_sum(tmp_path):
    mod = project(tmp_path, 'def product(xs):\n    out=1\n    for x in xs: out*=x\n    return out\n', 'self.assertEqual(subject.product([5]),5)')
    before = mod.read_bytes()
    assert engine.add_thread_pool_parallel(mod, 'product')['reason'] == 'THREAD_POOL_ADDITIVE_CONTRACT_UNPROVED'
    assert mod.read_bytes() == before
    assert runpy.run_path(str(mod))['product']([2,3]) == 6


def test_thread_pool_does_not_claim_a_measured_slowdown_is_faster(tmp_path):
    mod = project(tmp_path, 'def total(xs): return sum(xs)\n', 'self.assertEqual(subject.total([1,2]),3)')
    before = mod.read_bytes()
    result = engine.add_thread_pool_parallel(mod, 'total', require_speedup=True)
    assert result['reason'] == 'THREAD_POOL_NOT_FASTER'
    assert result['measurement']['median_after_ns'] > result['measurement']['median_before_ns']
    assert mod.read_bytes() == before


def test_gil_kernel_preserves_bigints_and_intermediate_overflow(tmp_path):
    mod = project(tmp_path, 'def total(xs): return sum(xs)\n', 'self.assertEqual(subject.total([1,2]),3)')
    result = engine.release_gil_sum_kernel(mod, 'total')
    assert result['verified'] is True
    fn = runpy.run_path(str(mod))['total']
    for xs in [[2**63], [2**63-1,1], [-2**63,-1], [2**62,2**62,-2**62], [], [True,2], [1.5,2.5]]:
        assert fn(xs) == sum(xs)
    assert fn(iter([2**63])) == 2**63


def test_optimizer_retains_unhashable_and_custom_equality_domain(tmp_path):
    mod = project(tmp_path, 'def dedupe(xs):\n    seen=[]\n    for x in xs:\n        if x not in seen:\n            seen.append(x)\n    return seen\n', 'self.assertEqual(subject.dedupe([1,1,2]),[1,2])')
    assert engine.egraph_optimize_function(mod, 'dedupe')['verified'] is True
    fn = runpy.run_path(str(mod))['dedupe']
    assert fn([[1],[1],[2]]) == [[1],[2]]
    assert fn(iter([[1],[1],[2]])) == [[1],[2]]
    assert fn([1,True,2]) == [1,2]


def test_gauss_optimizer_preserves_index_protocol_and_shadowed_range(tmp_path):
    mod = project(tmp_path, 'def total(n):\n    out=0\n    for x in range(n): out+=x\n    return out\n', 'self.assertEqual(subject.total(10),45)')
    assert engine.egraph_optimize_function(mod, 'total')['verified'] is True
    fn = runpy.run_path(str(mod))['total']
    class Index:
        def __index__(self): return 4
    assert fn(Index()) == 6
    fn.__globals__['range'] = lambda n: [10,20]
    assert fn(4) == 30


def test_ts_rename_preserves_literals_comments_properties_and_shorthand(tmp_path):
    path = tmp_path / 'app.ts'
    path.write_text('export function add(a,b) { return a+b; }\n// add is a label\nexport const label="add";\nexport const obj={add};\nexport const literal={add: 7};\n')
    result = polyglot.ts_transform_and_verify(path, 'Rename function add to plus.')
    assert result['verified'] is True
    source = path.read_text()
    assert '// add is a label' in source
    proc = subprocess.run(['node', '--input-type=module', '-e', source+'\nconsole.log(JSON.stringify([label,obj.add(2,3),literal.add]));'], text=True, capture_output=True, check=True)
    assert json.loads(proc.stdout) == ['add',5,7]


def test_ts_shadowed_binding_is_refused_without_edits(tmp_path):
    path = tmp_path / 'app.ts'
    path.write_text('export function add(a,b){return a+b;}\nfunction other(add){return add;}\n')
    before = path.read_bytes()
    assert polyglot.ts_transform_and_verify(path, 'Rename add to plus.')['verified'] is False
    assert path.read_bytes() == before


def test_file_edits_exception_restores_existing_and_removes_new(tmp_path):
    old, new = tmp_path/'old.py', tmp_path/'new.py'
    old.write_bytes(b'original\n')
    with pytest.raises(ValueError, match='validation failed'):
        with contracts.FileEdits({old:b'changed\n',new:b'new\n'}):
            raise ValueError('validation failed')
    assert old.read_bytes() == b'original\n'
    assert not new.exists()


@pytest.mark.parametrize('case', ['memo', 'gil', 'pool', 'exports', 'rename', 'split_collision'])
def test_public_route_semantic_counterexamples(case):
    parent = ROOT / 'canonical/astra_runtime/tmp'
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='swe-contract-', dir=parent) as raw:
        base = Path(raw)
        if case == 'rename':
            target = base/'app.ts'
            target.write_text('export function add(a,b){return a+b;}\nexport const label="add";\n')
            goal = f'Rename the exported function add to plus in {target.relative_to(ROOT)} and preserve other behavior.'
        else:
            sources = {'memo':'counter=0\ndef next_value(x):\n    global counter\n    counter+=1\n    return counter+x\n',
                       'gil':'def total(xs): return sum(xs)\n', 'pool':'def magnitude(xs): return sum(abs(x) for x in xs)\n',
                       'exports':'__all__=["public_api"]\ndef public_api(x): return x*2\ndef _unused(): return 99\n',
                       'split_collision':'def foo(): return 1\ndef bar(): return 2\n'}
            assertions = {'memo':'self.assertEqual(subject.next_value(0),1)', 'gil':'self.assertEqual(subject.total([1,2]),3)',
                          'pool':'self.assertEqual(subject.magnitude([5]),5)', 'exports':'self.assertEqual(subject.public_api(4),8)',
                          'split_collision':'self.assertEqual(subject.foo(),1)'}
            target = project(base, sources[case], assertions[case])
            rel = target.relative_to(ROOT)
            goal = {'memo':f'Add memoisation to function next_value in {rel} without changing behavior.',
                    'gil':f'Make function total in {rel} release the GIL while preserving Python integer sum semantics.',
                    'pool':f'Add a thread pool to function magnitude in {rel} without changing behavior.',
                    'exports':f'Remove dead code from {rel} and preserve the public API.',
                    'split_collision':f'Split {rel} into one module per function.'}[case]
        if case == 'split_collision':
            existing = target.with_name('foo.py'); existing.write_text('def existing_api(): return 42\n')
        result = door.solve({'task_id':'SWE_CONTRACT_'+case.upper(), 'goal':goal})
        if case in {'memo','split_collision'}:
            assert result['pass'] is False, result
            assert target.read_text() == sources[case]
            if case == 'split_collision': assert existing.read_text() == 'def existing_api(): return 42\n'
        else:
            assert result['pass'] is True, result
            if case == 'rename':
                assert 'label="add"' in target.read_text()
            else:
                namespace = runpy.run_path(str(target))
                if case == 'gil': assert namespace['total']([2**63]) == 2**63
                elif case == 'pool': assert namespace['magnitude']([-2,3]) == 5
                else: assert namespace['public_api'](4) == 8


def test_memoization_rejects_mutable_default_results(tmp_path):
    mod = project(tmp_path, 'def f(x=[]): return x\n', 'self.assertEqual(subject.f(),[])')
    before = mod.read_bytes()
    assert engine.memoize_function(mod, 'f')['reason'] == 'MEMOIZE_EFFECTS_OR_RESULT_DOMAIN_UNPROVED'
    assert mod.read_bytes() == before


def test_compiler_diagnostics_reach_missing_semicolon_repair(tmp_path):
    path = tmp_path/'bad.cpp'
    path.write_text('int add(int a, int b) {\n    return a+b\n}\n')
    result = polyglot.cpp_transform_and_verify(path, 'Repair the missing semicolon so this file compiles.')
    assert result['verified'] is True
    subprocess.run(['g++', '-fsyntax-only', str(path)], check=True, capture_output=True)
    assert 'return a+b;' in path.read_text()


def test_candidate_timeout_does_not_hang_the_caller(tmp_path):
    source = 'def f(xs):\n    while True: pass\n'
    result = engine._compare_in_child(source, source, tmp_path/'subject.py', 'f', False, timeout=0.2)
    assert result['equivalent'] is False
    assert result['reason'] == 'CHILD_FAILED_OR_TIMED_OUT'


def test_command_transport_preserves_both_channels(tmp_path):
    from canonical.runtime import pipeline_exec_v1 as transport
    rc, out, err = transport.run_command([sys.executable, '-c', 'import sys; print("result"); print("diagnostic", file=sys.stderr); sys.exit(3)'], str(tmp_path))
    assert rc == 3
    assert out == b'result\n'
    assert err == b'diagnostic\n'


@pytest.mark.parametrize('operation,before,after', [
    ('remove_dead_code', '__all__=["api"]\ndef api(x): return x*2\n', '__all__=["api"]\n'),
    ('memoize_function', 'counter=0\ndef f(x):\n    global counter\n    counter+=1\n    return counter+x\n', 'def f(x): return x+1\n'),
    ('add_thread_pool', 'def f(xs): return sum(abs(x) for x in xs)\n', 'def f(xs): return sum(xs)\n'),
    ('release_gil', 'def f(xs): return sum(xs)\n', 'def f(xs): return -1\n'),
])
def test_acceptance_rejects_producer_pass_for_a_broken_transition(tmp_path, operation, before, after):
    import hashlib
    from canonical.runtime import raw_goal_trace_acceptance_v1 as acceptance
    path = tmp_path/'subject.py'; path.write_text(after)
    args = {'target_path':'subject.py', 'operation':operation, 'symbol':'f'}
    result = {'verified':True, 'gate':'PASS', 'target_sha256':hashlib.sha256(path.read_bytes()).hexdigest(), 'transition_preimages':{'subject.py':before}}
    accepted, reason, _ = acceptance._inspect_python_swe_transform(args, result, tmp_path)
    assert accepted is False
    assert reason.startswith('SWE_TRANSITION_CONTRACT_FAILED:')


def test_acceptance_rejects_rename_that_changes_literal_data(tmp_path):
    import hashlib
    from canonical.runtime import raw_goal_trace_acceptance_v1 as acceptance
    before = 'export function add(a,b){return a+b;}\nexport const label="add";\n'
    path = tmp_path/'app.ts'; path.write_text(before.replace('add', 'plus'))
    args = {'target_path':'app.ts', 'operation':'ts_rename_symbol'}
    result = {'verified':True, 'gate':'PASS', 'language':'typescript', 'target_sha256':hashlib.sha256(path.read_bytes()).hexdigest(), 'transition_preimages':{'app.ts':before}}
    accepted, reason, _ = acceptance._inspect_polyglot_transform(args, result, tmp_path)
    assert accepted is False
    assert 'TS_LITERAL_OR_COMMENT_CHANGED' in reason


@pytest.mark.parametrize('parameter', ['out', 'array', '_bi', 'size'])
def test_native_generated_locals_do_not_capture_parameters(tmp_path, parameter):
    mod = project(tmp_path, f'def total({parameter}): return sum({parameter})\n', 'self.assertEqual(subject.total([1,2]),3)')
    assert engine.release_gil_sum_kernel(mod, 'total')['verified'] is True
    assert runpy.run_path(str(mod))['total']([2**63-1,1]) == 2**63


@pytest.mark.parametrize('parameter', ['size', 'chunks', 'pool'])
def test_thread_pool_generated_locals_do_not_capture_parameters(tmp_path, parameter):
    mod = project(tmp_path, f'def total({parameter}): return sum({parameter})\n', 'self.assertEqual(subject.total([1,2]),3)')
    assert engine.add_thread_pool_parallel(mod, 'total')['verified'] is True
    assert runpy.run_path(str(mod))['total']([-2,3]) == 1


def test_optimizer_does_not_skip_effects_surrounding_a_matching_fragment(tmp_path):
    mod = project(tmp_path, 'calls=[]\ndef dedupe(xs):\n    calls.append(1)\n    seen=[]\n    for x in xs:\n        if x not in seen: seen.append(x)\n    return seen\n', 'self.assertEqual(subject.dedupe([1,1]),[1])')
    before = mod.read_bytes()
    assert engine.egraph_optimize_function(mod, 'dedupe')['verified'] is False
    assert mod.read_bytes() == before


def test_ts_template_substitution_can_change_binding_not_literal_data(tmp_path):
    from canonical.swe_kernel import transition_verifier_v1 as verifier
    path = tmp_path/'app.ts'
    before = 'export function add(a,b){return a+b;}\nexport const label=`add=${add(2,3)}`;\n'
    path.write_text(before)
    assert polyglot.ts_transform_and_verify(path, 'Rename add to plus.')['verified'] is True
    assert verifier.verify_typescript(before, path.read_text()) == ''
    assert '`add=${plus(2,3)}`' in path.read_text()


def test_memoization_tracks_pure_helper_code_and_falls_back_after_change(tmp_path):
    mod = project(tmp_path, 'def add(a,b): return a+b\ndef twice(x): return add(x,x)\n', 'self.assertEqual(subject.twice(3),6)')
    assert engine.memoize_function(mod, 'twice')['verified'] is True
    fn = runpy.run_path(str(mod))['twice']
    assert fn(3) == 6
    fn.__globals__['add'] = lambda a,b: a-b
    assert fn(3) == 0


def test_canonical_loop_can_release_gil_without_becoming_fixed_width(tmp_path):
    mod = project(tmp_path, 'def total(xs):\n    out=0\n    for x in xs: out+=x\n    return out\n', 'self.assertEqual(subject.total([1,2]),3)')
    assert engine.release_gil_sum_kernel(mod, 'total')['verified'] is True
    assert runpy.run_path(str(mod))['total']([2**63]) == 2**63


def test_command_timeout_cleans_descendant_pipe_holders(tmp_path):
    import time
    from canonical.runtime import pipeline_exec_v1 as transport
    if os.name != 'posix':
        pytest.skip('POSIX process-group containment')
    started = time.monotonic()
    rc, _, _ = transport.run_command([sys.executable, '-c',
        'import os,time; pid=os.fork(); time.sleep(30) if pid==0 else None'], str(tmp_path), timeout=0.2)
    assert rc == -9
    assert time.monotonic() - started < 4


def test_command_both_output_channels_are_bounded(tmp_path):
    from canonical.runtime import pipeline_exec_v1 as transport
    _, out, err = transport.run_command([sys.executable, '-c',
        'import sys; sys.stdout.write("x"*5000); sys.stderr.write("e"*5000)'], str(tmp_path), max_bytes=128)
    assert out == b'x'*128
    assert err == b'e'*128
