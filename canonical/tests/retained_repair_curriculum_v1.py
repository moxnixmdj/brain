"""Small repository-derived curriculum; seeded faults, not upstream bug scores.

Source snapshots are immutable and licensed in fixtures/retained_repair_projects_v1.
Visible repair tests and external post-repair audit tests are authored fixtures.
The exact same bounded search/fallback remains available in both evaluation arms.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

FIXTURES = Path(__file__).with_name('fixtures') / 'retained_repair_projects_v1'
ROOT = Path(__file__).resolve().parents[2]
FAMILIES = ('floor_boundary', 'iterator_extent', 'integer_encoding')


def build_case(repo: Path, family: str, role: str):
    project = repo / role
    package = project / 'engine'
    package.mkdir(parents=True)
    (package / '__init__.py').write_text('')
    held = role != 'teaching'
    if family == 'floor_boundary':
        name = 'boltons_mathutils.py'
        original = (FIXTURES / name).read_text()
        before = original.replace('return options[i - 1]', 'return options[i - %d]' % (3 if held else 2))
        service = ('from .primitives import floor\n'
                   'def select_tier(amount, tiers):\n    return floor(amount, tiers)\n')
        visible = ('from engine.service import select_tier\n',
                   ['self.assertEqual(select_tier(7,[1,5,10]),5)',
                    'self.assertEqual(select_tier(10,[1,5,10]),10)',
                    'self.assertEqual(select_tier(1,[1,5,10]),1)'])
        hidden = ['self.assertEqual(select_tier(0.5,[-10,0,1,100]),0)',
                  'self.assertEqual(select_tier(1000,[-10,0,1,100]),100)',
                  'self.assertEqual(select_tier(-2,[-10,0,1,100]),-10)']
    elif family == 'iterator_extent':
        name = 'more_itertools_recipes.py'
        original = (FIXTURES / name).read_text()
        before = original.replace('return list(islice(iterable, n))',
                                  'return list(islice(iterable, n - %d))' % (2 if held else 1), 1)
        service = ('from .primitives import take\n'
                   'def first_batch(values, size):\n    return take(size, iter(values))\n')
        visible = ('from engine.service import first_batch\n',
                   ['self.assertEqual(first_batch([1,2,3,4],3),[1,2,3])',
                    'self.assertEqual(first_batch([1,2],1),[1])',
                    'self.assertEqual(first_batch([],4),[])'])
        hidden = ['self.assertEqual(first_batch(range(30),19),list(range(19)))',
                  'self.assertEqual(first_batch([8,9],0),[])',
                  'self.assertEqual(first_batch([8,9],20),[8,9])']
    elif family == 'integer_encoding':
        name = 'itsdangerous_encoding.py'
        original = (FIXTURES / name).read_text()
        before = original.replace('.lstrip(b"\\x00")', '.%s(b"\\x00")' % ('strip' if held else 'rstrip'))
        (package / 'exc.py').write_bytes((FIXTURES / 'itsdangerous_exc.py').read_bytes())
        service = ('from .primitives import int_to_bytes, bytes_to_int\n'
                   'def serialize_counter(value):\n    return int_to_bytes(value)\n'
                   'def read_counter(raw):\n    return bytes_to_int(raw)\n')
        visible = ('from engine.service import serialize_counter, read_counter\n',
                   ['self.assertEqual(serialize_counter(256),b"\\x01\\x00")',
                    'self.assertEqual(serialize_counter(1),b"\\x01")',
                    'self.assertEqual(serialize_counter(0),b"")'])
        hidden = ['self.assertEqual(read_counter(serialize_counter(65536)),65536)',
                  'self.assertEqual(serialize_counter(65536),b"\\x01\\x00\\x00")',
                  'self.assertEqual(read_counter(serialize_counter(2**32)),2**32)']
    else:
        raise ValueError(family)
    if before == original:
        raise AssertionError('SEEDED_FAULT_DID_NOT_CHANGE_UPSTREAM_SOURCE')
    target = package / 'primitives.py'
    target.write_text(before)
    (package / 'service.py').write_text(service)
    def suite(statements):
        return ('import unittest\n' + visible[0] + 'class Tests(unittest.TestCase):\n'
                + ''.join(' def test_%d(self): %s\n' % (i, line) for i, line in enumerate(statements)))
    tests = project / 'test_behavior.py'
    tests.write_text(suite(visible[1]))
    audit = repo / 'audit' / (role + '_test.py')
    audit.parent.mkdir(exist_ok=True)
    audit.write_text(suite(hidden))
    contract = {'schema_version': 1, 'scope_id': 'upstream-derived/' + family + '/v1',
                'verification_kind': 'TEST_SUITE',
                'dependencies': {'source_snapshot': hashlib.sha256((FIXTURES / name).read_bytes()).hexdigest()},
                'preconditions': {'target_role': family}}
    context = {key: contract[key] for key in ('dependencies', 'preconditions')}
    args = {'source_root': role, 'test_paths': [role + '/test_behavior.py'],
            'output_path': 'reports/' + role + '.json', 'timeout_s': 30,
            'max_guided_files': 2, 'max_guided_symbols_per_file': 2,
            'mutations_per_file': 12, 'max_pair_candidates': 24,
            'retained_learning': {'enabled': True, 'db_path': 'memory/skills.sqlite',
                                  'target_path': role + '/engine/primitives.py',
                                  'contract': contract, 'context': context}}
    return {'args': args, 'original': original, 'before': before,
            'target': target, 'test': tests, 'audit': audit, 'project': project}


CHILD = r'''
import hashlib, json, os, resource, sys, time
from pathlib import Path
from canonical.runtime.bound_capabilities import python_repair_apply_verified_v1 as apply
from canonical.swe_kernel.verified_skill_crystallizer_v1 import VerifiedSkillStore
from canonical.swe_kernel.skill_verification_contract_v1 import ProjectTestOracle
mode, root, config = sys.argv[1:]
root = Path(root)
config = json.loads(config)
calls = []
def observe(event, args):
    if event == 'subprocess.Popen': calls.append(str(args[0]))
sys.addaudithook(observe)
start = time.monotonic()
if mode == 'teach':
    target = root / config['args']['retained_learning']['target_path']
    setting = config['args']['retained_learning']
    oracle = ProjectTestOracle(target.parents[1], 'engine/primitives.py', ['test_behavior.py'], setting['contract']['scope_id'])
    db = root / setting['db_path']; db.parent.mkdir(exist_ok=True)
    result = VerifiedSkillStore(db, seed=False).crystallize_code_fix(
        before_snippet=target.read_text(), after_snippet=config['original'], language='python',
        contract=setting['contract'], training_verifier=oracle)
else:
    result = apply.run(config['args'], root)
usage = resource.getrusage(resource.RUSAGE_CHILDREN)
own = resource.getrusage(resource.RUSAGE_SELF)
print(json.dumps({'pid': os.getpid(), 'result': result, 'elapsed_s': time.monotonic()-start,
                  'subprocess_calls': len(calls), 'child_user_s': usage.ru_utime,
                  'child_system_s': usage.ru_stime, 'max_child_rss_kib': usage.ru_maxrss,
                  'worker_user_s': own.ru_utime, 'worker_system_s': own.ru_stime,
                  'worker_max_rss_kib': own.ru_maxrss}))
'''


def execute(mode, repo, case):
    import time
    started=time.monotonic()
    payload = {'args': case['args']}
    if mode == 'teach':
        payload['original'] = case['original']
    proc = subprocess.run([sys.executable, '-c', CHILD, mode, str(repo), json.dumps(payload)],
                          cwd=ROOT, capture_output=True, text=True, timeout=120)
    if proc.returncode:
        raise AssertionError(proc.stderr[-6000:])
    result=json.loads(proc.stdout)
    result['process_wall_s']=time.monotonic()-started
    return result


def audit(case):
    import resource
    import time
    start=time.monotonic()
    before=resource.getrusage(resource.RUSAGE_CHILDREN)
    from canonical.runtime.bound_capabilities.python_repair_apply_verified_v1 import _REPAIR, _run_test
    rc, tail = _run_test(_REPAIR._PATCH.suite_argv(sys.executable, str(case['audit'])),
                         case['project'], 20, (case['project'],))
    after=resource.getrusage(resource.RUSAGE_CHILDREN)
    return {'returncode': rc, 'output_tail': tail.decode('utf-8', 'replace')[-1000:],
            'elapsed_s': time.monotonic()-start, 'subprocess_calls': 1,
            'child_user_s':after.ru_utime-before.ru_utime,
            'child_system_s':after.ru_stime-before.ru_stime}
