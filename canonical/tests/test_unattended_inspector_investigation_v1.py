"""An unattended runner uses the creature's own persisted inspector investigation."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from canonical.runtime import creature_runtime_v1 as runtime
from canonical.runtime import unified_cognitive_fabric_v1 as fabric


class UnattendedInspectorInvestigationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='unattended_inspector_')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_no_caller_named_goal_runs_then_resumes_without_claiming_parent(self):
        first = runtime.run_unattended_inspector_investigation(self.root, cycles=4)
        inv = first['investigation']
        parent, child = inv['parent'], inv['child']
        self.assertTrue(first['authored_now'])
        self.assertEqual([row['status'] for row in first['run']['steps']],
                         ['WORKED', 'WAITING_FOR_INSPECTOR_VERIFIER'])
        self.assertEqual(first['run']['steps'][0]['work'], child['id'])
        self.assertTrue(first['run']['steps'][0]['ok'])
        self.assertEqual(first['run']['steps'][1]['work'], parent['id'])
        self.assertEqual(first['information']['parent_id'], parent['id'])
        self.assertEqual(first['information']['freshness'], 'HISTORICAL_NOT_REVALIDATED')
        self.assertEqual(first['run']['open'], 1)
        self.assertEqual(first['run']['life_spent'], 0.25)
        with patch.object(fabric, 'run', side_effect=AssertionError('must not rerun completed child')):
            again = runtime.run_unattended_inspector_investigation(self.root, cycles=4)
        self.assertFalse(again['authored_now'])
        self.assertEqual(again['investigation'], inv)
        self.assertEqual(again['information'], first['information'])
        self.assertEqual([row['status'] for row in again['run']['steps']],
                         ['WAITING_FOR_INSPECTOR_VERIFIER'])
        self.assertEqual(again['run']['life_spent'], 0.25)
        self.assertEqual(again['run']['open'], 1)

    def test_new_process_resumes_the_same_unfinished_parent(self):
        first = runtime.run_unattended_inspector_investigation(self.root, cycles=1)
        root = Path(__file__).resolve().parents[2]
        script = '''import json, os, sys
from canonical.runtime import creature_runtime_v1 as R
r=R.run_unattended_inspector_investigation(sys.argv[1], cycles=3)
print(json.dumps({"pid":os.getpid(),"result":r}))
'''
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=str(root))
        proc = subprocess.run([sys.executable, '-B', '-c', script, str(self.root)],
                              cwd=root, env=env, capture_output=True, text=True,
                              timeout=60, check=True)
        parsed = json.loads(proc.stdout)
        self.assertNotEqual(parsed['pid'], os.getpid())
        result = parsed['result']
        self.assertFalse(result['authored_now'])
        self.assertEqual(result['investigation'], first['investigation'])
        self.assertEqual(result['information'], first['information'])
        self.assertEqual(result['run']['steps'][0]['status'], 'WAITING_FOR_INSPECTOR_VERIFIER')
        self.assertEqual(result['run']['open'], 1)

    def test_wrong_answer_is_not_remembered_or_parent_closed(self):
        from canonical.runtime import live_integrated_brain_v1 as live
        c = runtime.boot(self.root, identity='creature')
        target = c.author_inspector_investigation()['parent']['capability_id']
        ids = set(live.load_verified_registry())
        forged = ids - {target} if target in ids else ids | {target}
        bad = {'schema': fabric.SCHEMA, 'status': 'LIVE_FEDERATED_COGNITIVE_FABRIC',
               'verified_bound_capability_ids': sorted(forged)}
        with patch.object(fabric, 'run', return_value=bad):
            result = runtime.run_unattended_inspector_investigation(self.root, cycles=2)
        self.assertFalse(result['run']['steps'][0]['ok'])
        self.assertIsNone(result['information'])
        self.assertEqual(result['run']['closed'], 0)
        self.assertGreaterEqual(result['run']['open'] + result['run']['parked'], 1)

    def test_an_existing_unfinished_catalog_goal_is_not_replaced(self):
        creature = runtime.boot(self.root, identity='creature')
        goal = creature.author_catalog_question('python.source.audit.ast')
        with self.assertRaisesRegex(ValueError, 'WOULD_REPLACE'):
            runtime.run_unattended_inspector_investigation(self.root, cycles=1)
        again = runtime.boot(self.root, identity='creature')
        self.assertEqual(again.catalog_question(goal['id']), goal)
        self.assertEqual(again.report()['open'], 1)


if __name__ == '__main__':
    unittest.main()
