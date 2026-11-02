"""Producer-run integration with trusted authored fixtures only.

This invokes the existing repair adapter directly and runs fixture tests in
host subprocesses. It is not a carrier, an independent verification, or the
fabric entrypoint. Run only from a disposable checkout with trusted fixtures.
"""
from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from canonical.runtime import repair_candidate_broker_v1 as broker
from canonical.tests.retained_repair_curriculum_v1 import audit, build_case, execute


class TrustedRepairBrokerIntegrationTests(unittest.TestCase):
    def test_existing_repair_operates_only_on_the_staged_fixture(self):
        root = Path(__file__).resolve().parents[2]
        scratch = root / 'canonical/astra_runtime/tmp'
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='broker_integration_', dir=scratch) as td:
            base = Path(td)
            case = build_case(base / 'fixture', 'floor_boundary', 'teaching')
            before = broker.snapshot_project(case['project'])
            staging_parent = base / 'staging'
            staging_parent.mkdir()
            stage = broker.stage_project(before, staging_parent=staging_parent)
            original_bytes = case['target'].read_bytes()
            audit_bytes = case['audit'].read_bytes()
            source = stage / 'engine/primitives.py'
            staged_case = {'project': stage, 'target': source, 'audit': case['audit'],
                           'args': {**case['args'], 'source_root': stage.name,
                                    'test_paths': [stage.name + '/test_behavior.py'],
                                    'output_path': 'reports/result.json',
                                    'retained_learning': {'enabled': False}}}
            with patch.dict(os.environ, {'PYTHONDONTWRITEBYTECODE': '1'}):
                self.assertNotEqual(audit(staged_case)['returncode'], 0)
                output = execute('apply', staging_parent, staged_case)
                self.assertEqual(audit(staged_case)['returncode'], 0)
            self.assertTrue(output['result']['pass'], output['result'])
            self.assertEqual(case['target'].read_bytes(), original_bytes)
            self.assertEqual(case['audit'].read_bytes(), audit_bytes)
            self.assertFalse((staging_parent / 'memory/skills.sqlite').exists())
            after = broker.snapshot_project(stage)
            candidate = broker.compare_candidate(before, after, target='engine/primitives.py',
                                                  protected_tests=('test_behavior.py',))
            self.assertFalse(candidate['publication_authority'])
            self.assertFalse(candidate['semantic_acceptance_complete'])
            self.assertFalse(candidate['execution_authority'])

    def test_direct_staged_teach_restart_reuse_and_disabled_control(self):
        import json
        import subprocess
        import sys
        root = Path(__file__).resolve().parents[2]
        scratch = root / 'canonical/astra_runtime/tmp'
        scratch.mkdir(parents=True, exist_ok=True)
        child = '''import json, os, sys
from canonical.runtime.bound_capabilities import python_repair_apply_verified_v1 as repair
calls=[]
def watch(event,args):
    if event == "sqlite3.connect": calls.append(str(args[0]))
sys.addaudithook(watch)
out=repair.run(json.loads(sys.stdin.read()),sys.argv[1])
print(json.dumps({"pid":os.getpid(),"result":out,"sqlite_connects":calls}))
'''
        with tempfile.TemporaryDirectory(prefix='broker_reuse_', dir=scratch) as td:
            base = Path(td)
            staging = base / 'staging'; staging.mkdir()
            roles = ('teaching', 'off', 'cold', 'warm')
            cases = {role: build_case(base / 'fixtures', 'floor_boundary', role) for role in roles}
            results, pids = {}, set()
            with patch.dict(os.environ, {'PYTHONDONTWRITEBYTECODE': '1'}):
                for role in roles:
                    case = cases[role]
                    before = broker.snapshot_project(case['project'])
                    stage = broker.stage_project(before, staging_parent=staging)
                    config = dict(case['args']['retained_learning'])
                    config['target_path'] = stage.name + '/engine/primitives.py'
                    config['db_path'] = 'memory/cold.sqlite' if role == 'cold' else 'memory/skills.sqlite'
                    config['enabled'] = role != 'off'
                    args = {**case['args'], 'source_root': stage.name,
                            'test_paths': [stage.name + '/test_behavior.py'],
                            'output_path': 'reports/' + role + '.json', 'retained_learning': config}
                    staged_case = {'project': stage, 'audit': case['audit']}
                    self.assertNotEqual(audit(staged_case)['returncode'], 0)
                    db = staging / 'memory/skills.sqlite'
                    frozen_db = db.read_bytes() if role == 'off' else None
                    original = case['target'].read_bytes()
                    proc = subprocess.run([sys.executable, '-B', '-c', child, str(staging)],
                                          input=json.dumps(args), text=True, capture_output=True,
                                          cwd=root, timeout=120, check=True)
                    value = json.loads(proc.stdout); pids.add(value['pid'])
                    self.assertTrue(value['result']['pass'], value['result'])
                    self.assertEqual(audit(staged_case)['returncode'], 0)
                    self.assertEqual(case['target'].read_bytes(), original)
                    assessment = broker.compare_candidate(before, broker.snapshot_project(stage),
                                                          target='engine/primitives.py',
                                                          protected_tests=('test_behavior.py',))
                    self.assertFalse(assessment['publication_authority'])
                    if role == 'off':
                        self.assertEqual(db.read_bytes(), frozen_db)
                        self.assertEqual(value['sqlite_connects'], [])
                    results[role] = value['result']
            self.assertEqual(len(pids), 4)
            self.assertTrue(results['teaching']['retained_learning']['teaching']['crystallized'])
            self.assertFalse(results['off']['retained_learning']['enabled'])
            self.assertFalse(results['cold']['retained_learning']['hit'])
            self.assertTrue(results['warm']['retained_learning']['hit'])
            self.assertEqual(results['warm']['repair_search_invocations'], 0)
            self.assertGreater(results['cold']['repair_search_invocations'], 0)
            self.assertGreater(results['off']['repair_search_invocations'], 0)


if __name__ == '__main__':
    unittest.main()
