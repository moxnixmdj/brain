"""Pinned historical bugs; generation never substitutes repaired held-out source.

Source snapshots and selected upstream test bodies are unchanged. Consumers and
extra audit properties are authored here, not upstream or independent certification.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).parent / 'fixtures/historical_repair_projects_v1'
FAMILIES = {'boundary': ('bits_capacity', 'unit_boundary'),
            'zero_consumption': ('ichunked_zero', 'chunked_even_zero')}


def build_case(repo: Path, case_id: str, role: str):
    manifest = json.loads((FIXTURES / 'PROVENANCE.json').read_text())
    spec = next(row for row in manifest['cases'] if row['id'] == case_id)
    fixture = FIXTURES / case_id
    project = repo / role
    target = project / spec['source_path']
    target.parent.mkdir(parents=True)
    target.write_bytes((fixture / 'before.py').read_bytes())
    if case_id.endswith('_zero'):
        (target.parent / 'recipes.py').write_bytes((fixture / 'recipes.py').read_bytes())
        (target.parent / '__init__.py').write_bytes((fixture / 'init.py').read_bytes())
        imports = 'from unittest import TestCase\nfrom itertools import count\nimport more_itertools as mi\n'
        function = 'ichunked' if case_id == 'ichunked_zero' else 'chunked_even'
        consumer = (f'from more_itertools import {function}\n'
                    f'def batches(values, width):\n    return [list(c) for c in {function}(values, width)]\n')
        consumer_tests = '''import unittest
from consumer import batches
class ConsumerTests(unittest.TestCase):
 def test_zero_does_not_consume(self):
  source=iter([11,13,17]); self.assertEqual(batches(source,0),[]); self.assertEqual(list(source),[11,13,17])
 def test_regular_values(self):
  self.assertEqual([v for c in batches(range(7),3) for v in c],list(range(7)))
'''
        audit = '''import unittest
from consumer import batches
class Audit(unittest.TestCase):
 def test_no_iteration_on_zero(self):
  class Untouchable:
   def __iter__(self): raise AssertionError('zero must not even request an iterator')
  self.assertEqual(batches(Untouchable(),0),[])
 def test_negative_does_not_consume(self):
  source=iter([23,29])
  with self.assertRaisesRegex(ValueError,'n must be at least 0'): batches(source,-3)
  self.assertEqual(list(source),[23,29])
 def test_positive_roundtrip(self):
  for n in (1,2,4,9): self.assertEqual([v for c in batches(range(19),n) for v in c],list(range(19)))
'''
    else:
        (target.parent / '__init__.py').write_text('')
        if case_id == 'bits_capacity':
            imports = 'from pytest import raises\nfrom boltons.mathutils import Bits\n'
            consumer = 'from boltons.mathutils import Bits\ndef encode(value,width):\n    return Bits(value,width).as_bin()\n'
            consumer_tests = '''import unittest
from consumer import encode
class ConsumerTests(unittest.TestCase):
 def test_valid(self): self.assertEqual(encode(7,3),'111')
 def test_overflow(self):
  with self.assertRaises(ValueError): encode(8,3)
'''
            audit = '''import unittest
from consumer import encode
class Audit(unittest.TestCase):
 def test_boundaries(self):
  for width in (1,4,9):
   self.assertEqual(len(encode((1<<width)-1,width)),width)
   with self.assertRaises(ValueError): encode(1<<width,width)
'''
        else:
            imports = 'from boltons import strutils\n'
            consumer = 'from boltons.strutils import bytes2human\ndef display(value):\n    return bytes2human(value,2)\n'
            consumer_tests = '''import unittest
from consumer import display
class ConsumerTests(unittest.TestCase):
 def test_boundary(self): self.assertEqual(display(1024),'1.00K')
 def test_sign(self): self.assertEqual(display(-1024),'-1.00K')
 def test_ordinary(self): self.assertEqual(display(512),'512.00B')
'''
            audit = '''import unittest
from consumer import display
class Audit(unittest.TestCase):
 def test_other_boundaries(self):
  for power,suffix in ((2,'M'),(3,'G'),(4,'T')):
   self.assertEqual(display(1024**power),'1.00'+suffix)
   self.assertEqual(display(-1024**power),'-1.00'+suffix)
'''
    upstream = (fixture / 'upstream_tests.txt').read_text()
    node = next(n for n in ast.parse(upstream).body if getattr(n, 'name', None) == spec['selected_test'])
    # Exact unchanged upstream test body, with only dependency imports repackaged.
    selected = ast.get_source_segment(upstream, node)
    test = project / 'test_upstream.py'
    test.write_text(imports + selected + '\n')
    (project / 'consumer.py').write_text(consumer)
    (project / 'test_consumer.py').write_text(consumer_tests)
    audit_path = repo / 'audits' / (role + '.py')
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(audit)
    family = next(k for k, v in FAMILIES.items() if case_id in v)
    contract = {'schema_version': 1, 'scope_id': 'historical/' + family + '/v1',
                'verification_kind': 'TEST_SUITE', 'dependencies': {'python_major': 3},
                'preconditions': {'semantic_family': family}}
    args = {'source_root': role, 'test_paths': [role + '/test_upstream.py', role + '/test_consumer.py'],
            'output_path': 'reports/' + role + '.json', 'timeout_s': 15,
            'max_guided_files': 2, 'max_guided_symbols_per_file': 2,
            'max_control_files': 2, 'max_control_symbols_per_file': 2,
            'mutations_per_file': 24, 'max_pair_candidates': 12,
            'retained_learning': {'enabled': True, 'db_path': 'memory/skills.sqlite',
                 'target_path': role + '/' + spec['source_path'], 'contract': contract,
                 'context': {k: dict(contract[k]) for k in ('dependencies', 'preconditions')}}}
    return {'args': args, 'project': project, 'target': target, 'test': test,
            'audit': audit_path, 'case_id': case_id, 'upstream_test_body_sha256': hashlib.sha256(selected.encode()).hexdigest()}


WORKER = r'''
import json,os,resource,sys,time
from pathlib import Path
from canonical.runtime.bound_capabilities import python_repair_apply_verified_v1 as apply
from canonical.swe_kernel.skill_verification_contract_v1 import ProjectTestOracle
from canonical.swe_kernel.verified_skill_crystallizer_v1 import VerifiedSkillStore
mode,root,payload=sys.argv[1:];root=Path(root);config=json.loads(Path(payload).read_text());args=config['args']
calls=[]
sys.addaudithook(lambda event,args: calls.append(args[0]) if event=='subprocess.Popen' else None)
start=time.monotonic()
if mode=='teach':
 setting=args['retained_learning'];project=root/args['source_root'];target=root/setting['target_path']
 oracle=ProjectTestOracle(project,str(target.relative_to(project)),[str((root/p).relative_to(project)) for p in args['test_paths']],setting['contract']['scope_id'],timeout_s=15)
 db=root/setting['db_path'];db.parent.mkdir(parents=True,exist_ok=True)
 result=VerifiedSkillStore(db,seed=False).crystallize_code_fix(before_snippet=target.read_text(),after_snippet=config['expert_after'],language='python',contract=setting['contract'],training_verifier=oracle)
elif mode in ('audit','corpus'):
 targets=[config['audit']] if mode=='audit' else [str(root/p) for p in args['test_paths']]
 rc,tail=apply._run_test(apply._REPAIR._PATCH.suite_argv(sys.executable,*targets),root/args['source_root'],15,(root/args['source_root'],))
 result={'returncode':rc,'tail':tail.decode('utf-8','replace')[-2000:]}
else:result=apply.run(args,root)
child=resource.getrusage(resource.RUSAGE_CHILDREN);own=resource.getrusage(resource.RUSAGE_SELF)
print(json.dumps({'pid':os.getpid(),'result':result,'runtime_wall_s':time.monotonic()-start,'subprocess_calls':len(calls),'worker_user_s':own.ru_utime,'worker_system_s':own.ru_stime,'child_user_s':child.ru_utime,'child_system_s':child.ru_stime,'worker_max_rss_kib':own.ru_maxrss,'max_single_child_rss_kib':child.ru_maxrss}))
'''


def execute(mode: str, repo: Path, case: dict):
    started = time.monotonic()
    payload = {'args': case['args']}
    if mode == 'teach':
        payload['expert_after'] = (FIXTURES / case['case_id'] / 'after.py').read_text()
    if mode == 'audit':
        payload['audit'] = str(case['audit'])
    repo.mkdir(parents=True, exist_ok=True)
    # Large real modules exceed per-argument OS limits. Teaching data never enter
    # an apply payload; use a temporary file outside the measured project.
    with tempfile.TemporaryDirectory(prefix='historical_payload_', dir=repo) as td:
        path = Path(td) / 'payload.json'
        path.write_text(json.dumps(payload))
        proc = subprocess.run([sys.executable, '-c', WORKER, mode, str(repo), str(path)],
                              cwd=ROOT, capture_output=True, text=True, timeout=180)
    if proc.returncode:
        raise RuntimeError(proc.stderr[-6000:])
    result = json.loads(proc.stdout)
    result['process_wall_s'] = time.monotonic() - started
    return result
