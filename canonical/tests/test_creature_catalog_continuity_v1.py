"""A narrow information goal through the real fabric; no execution authority."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from canonical.runtime import creature_runtime_v1 as creature_runtime
from canonical.runtime import self_authored_obligations_v1 as author
from canonical.runtime import unified_cognitive_fabric_v1 as fabric


class CreatureCatalogContinuityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='creature_catalog_')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_information_goal_survives_restart_and_completes_through_real_fabric(self):
        first = creature_runtime.boot(self.root, identity='test', life=10)
        question = first.author_catalog_question('python.source.audit.ast')
        self.assertEqual(first.report()['open'], 1)
        # Reboot before executing: typed goal and its fixed check must survive.
        resumed = creature_runtime.boot(self.root, identity='test')
        self.assertEqual(resumed.catalog_question(question['id'])['claim'], question['claim'])
        row = resumed.step()
        self.assertTrue(row['ok'], row)
        self.assertEqual(row['information']['capability_id'], 'python.source.audit.ast')
        self.assertIs(row['information']['listed'], True)
        self.assertFalse(row['information']['execution_authority'])
        self.assertEqual(resumed.report()['closed'], 1)
        after = creature_runtime.boot(self.root, identity='test')
        self.assertEqual(after.report()['open'], 0)
        self.assertEqual(after.report()['closed'], 1)
        self.assertEqual(after._self.state.completed[-1]['information'], row['information'])

    def test_initial_life_grant_survives_a_restart_before_any_step(self):
        creature_runtime.boot(self.root, identity='test', life=10)
        again = creature_runtime.boot(self.root, identity='test', life=40)
        self.assertEqual(again.report()['life_remaining'], 10.0)

    def test_catalog_goal_survives_fresh_interpreters(self):
        import os
        import subprocess
        import sys
        root = Path(__file__).resolve().parents[2]
        first = creature_runtime.boot(self.root, identity='test', life=10)
        question = first.author_catalog_question('python.source.audit.ast')
        child = '''import json, os, sys
from canonical.runtime import creature_runtime_v1 as R
c=R.boot(sys.argv[1], identity="test")
question=c.catalog_question(sys.argv[2])
row=c.step() if sys.argv[3]=="run" else None
print(json.dumps({"pid":os.getpid(),"question":question,"row":row,"report":c.report(),
                  "completed":c._self.state.completed}))
'''
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=str(root))
        def spawn(mode):
            proc = subprocess.run([sys.executable, '-B', '-c', child, str(self.root), question['id'], mode],
                                  capture_output=True, text=True, env=env, cwd=root, timeout=60, check=True)
            return json.loads(proc.stdout)
        executed, recovered = spawn('run'), spawn('read')
        self.assertNotEqual(executed['pid'], recovered['pid'])
        self.assertTrue(executed['row']['ok'])
        self.assertIs(executed['row']['information']['listed'], True)
        self.assertEqual(recovered['question'], question)
        self.assertEqual(recovered['report']['closed'], 1)
        self.assertEqual(recovered['report']['open'], 0)
        self.assertEqual(recovered['completed'][-1]['information'], executed['row']['information'])

    def test_wrong_catalog_output_fails_and_remains_open_after_restart(self):
        c = creature_runtime.boot(self.root, identity='test', life=10)
        question = c.author_catalog_question('python.source.audit.ast')
        forged = {'schema': fabric.SCHEMA, 'status': 'LIVE_FEDERATED_COGNITIVE_FABRIC',
                  'verified_bound_capability_ids': []}
        with patch.object(fabric, 'run', return_value=forged):
            row = c.step()
        self.assertFalse(row['ok'])
        self.assertEqual(row['blocked'], 'CATALOG_MEMBERSHIP_MISMATCH')
        self.assertEqual(c.report()['closed'], 0)
        again = creature_runtime.boot(self.root, identity='test')
        self.assertEqual(again.report()['open'], 1)
        self.assertEqual(again.report()['closed'], 0)
        self.assertEqual(again.catalog_question(question['id'])['check_id'], 'CATALOG_MEMBERSHIP_V1')

    def test_false_listing_and_false_positive_are_distinguished(self):
        from canonical.runtime import live_integrated_brain_v1 as live
        target = 'brain.test.catalog.definitely_absent.v1'
        self.assertNotIn(target, live.load_verified_registry())
        c = creature_runtime.boot(self.root, identity='test', life=10)
        c.author_catalog_question(target)
        base = {'schema': fabric.SCHEMA, 'status': 'LIVE_FEDERATED_COGNITIVE_FABRIC'}
        with patch.object(fabric, 'run', return_value={**base, 'verified_bound_capability_ids': [target]}):
            self.assertEqual(c.step()['blocked'], 'CATALOG_MEMBERSHIP_MISMATCH')
        with patch.object(fabric, 'run', return_value={**base, 'verified_bound_capability_ids': []}):
            row = c.step()
        self.assertTrue(row['ok'])
        self.assertIs(row['information']['listed'], False)
        self.assertEqual(c.report()['closed'], 1)

    def test_failed_legacy_work_does_not_become_closed_at_restart(self):
        c = creature_runtime.boot(self.root, identity='test', life=10)
        p = author.Proposal(id='a', claim='a done', source='test',
                            check=lambda w: (w.get('inspected') or {}).get('a') == 'yes')
        c.author_board([p], before={'inspected': {'a': 'no'}}, done={'inspected': {'a': 'yes'}})
        self.assertFalse(c.step()['ok'])
        again = creature_runtime.boot(self.root, identity='test')
        self.assertEqual(again.report()['closed'], 0)
        # The legacy board itself is not durable and must be re-authored.
        again.author_board([p], before={'inspected': {'a': 'no'}}, done={'inspected': {'a': 'yes'}})
        self.assertEqual(again.report()['open'], 1)

    def test_failed_attempts_remain_parked_across_restart(self):
        c = creature_runtime.boot(self.root, identity='test', life=10)
        c.author_catalog_question('python.source.audit.ast')
        with patch.object(fabric, 'run', return_value={'status': 'bad'}):
            self.assertFalse(c.step()['ok'])
            c = creature_runtime.boot(self.root, identity='test')
            self.assertEqual(c.report()['open'], 1)
            self.assertFalse(c.step()['ok'])
        c = creature_runtime.boot(self.root, identity='test')
        self.assertEqual(c.report()['parked'], 1)
        self.assertEqual(c.report()['open'], 0)
        self.assertEqual(c.step()['status'], 'IDLE')

    def test_injected_performer_cannot_approve_a_typed_question(self):
        c = creature_runtime.boot(self.root, identity='test', life=10)
        c.author_catalog_question('python.source.audit.ast')
        called = []
        def forged(work, instance):
            called.append(True)
            return {'ok': True, 'verified': True, 'correct': True}
        row = c.step(forged)
        self.assertFalse(row['ok'])
        self.assertEqual(row['blocked'], 'CATALOG_CUSTOM_EXECUTOR_UNSUPPORTED')
        self.assertEqual(called, [])
        self.assertEqual(creature_runtime.boot(self.root, identity='test').report()['open'], 1)

    def test_interruption_keeps_the_spent_life_and_reports_unfinished(self):
        c = creature_runtime.boot(self.root, identity='test', life=10)
        c.author_catalog_question('python.source.audit.ast')
        with patch.object(fabric, 'run', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                c.step()
        again = creature_runtime.boot(self.root, identity='test')
        self.assertEqual(again.report()['life_remaining'], 9.0)
        self.assertEqual(again.report()['open'], 1)
        self.assertEqual(again.report()['closed'], 0)
        self.assertEqual(len(again._self.state.interrupted), 1)

    def test_killed_process_preserves_charge_and_unfinished_question(self):
        import os
        import select
        import subprocess
        import sys
        root = Path(__file__).resolve().parents[2]
        c = creature_runtime.boot(self.root, identity='test', life=10)
        c.author_catalog_question('python.source.audit.ast')
        child = '''import sys, time
from unittest.mock import patch
from canonical.runtime import creature_runtime_v1 as R, unified_cognitive_fabric_v1 as F
c=R.boot(sys.argv[1], identity="test")
def waiting(*args, **kwargs):
    print("ENTERED", flush=True)
    time.sleep(60)
with patch.object(F, "run", side_effect=waiting):
    c.step()
'''
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=str(root))
        proc = subprocess.Popen([sys.executable, '-B', '-c', child, str(self.root)],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, env=env, cwd=root)
        try:
            ready, _, _ = select.select([proc.stdout], [], [], 30)
            self.assertTrue(ready, 'child did not reach the operation')
            self.assertEqual(proc.stdout.readline().strip(), 'ENTERED')
        finally:
            proc.kill()
            proc.communicate(timeout=10)
        again = creature_runtime.boot(self.root, identity='test')
        self.assertEqual(again.report()['life_remaining'], 9.0)
        self.assertEqual(again.report()['open'], 1)
        self.assertEqual(again.report()['closed'], 0)
        self.assertEqual(len(again._self.state.interrupted), 1)

    def test_tampered_or_unknown_board_is_not_executed(self):
        c = creature_runtime.boot(self.root, identity='test')
        c.author_catalog_question('python.source.audit.ast')
        path = self.root / 'catalog_question.json'
        row = json.loads(path.read_text())
        row['check_id'] = 'RUN_ARBITRARY_CODE'
        path.write_text(json.dumps(row))
        with self.assertRaisesRegex(ValueError, 'CATALOG_QUESTION_INVALID'):
            creature_runtime.boot(self.root, identity='test')

    def test_prior_generic_success_cannot_close_the_typed_question(self):
        c = creature_runtime.boot(self.root, identity='test', life=10)
        qid = c._catalog_spec('test', 'python.source.audit.ast')['id']
        p = author.Proposal(id=qid, claim='different work', source='test',
                            check=lambda w: (w.get('inspected') or {}).get('a') == 'yes')
        c.author_board([p], before={'inspected': {'a': 'no'}}, done={'inspected': {'a': 'yes'}})
        c.step(lambda work, instance: {'ok': True, 'verified': True, 'correct': True})
        self.assertEqual(c.report()['closed'], 1)
        c.author_catalog_question('python.source.audit.ast')
        self.assertEqual(c.report()['closed'], 0)
        self.assertEqual(c.report()['open'], 1)
        c = creature_runtime.boot(self.root, identity='test')
        self.assertEqual(c.report()['closed'], 0)
        self.assertEqual(c.report()['open'], 1)

    def test_unfinished_question_is_not_silently_replaced(self):
        c = creature_runtime.boot(self.root, identity='test')
        question = c.author_catalog_question('python.source.audit.ast')
        with self.assertRaisesRegex(ValueError, 'WOULD_REPLACE'):
            c.author_catalog_question('other')
        with self.assertRaisesRegex(ValueError, 'WOULD_REPLACE'):
            c.author_board([], before={}, done={})
        self.assertEqual(c.abandon_catalog_question(question['id'])['status'], 'ABANDONED_NOT_COMPLETED')
        self.assertEqual(creature_runtime.boot(self.root, identity='test').report()['open'], 0)

    def test_invalid_catalog_target_rejected_before_board_write(self):
        c = creature_runtime.boot(self.root, identity='test')
        for target in ('', '../a', 'bad id', 'a/b', 'x' * 257):
            with self.subTest(target=target), self.assertRaises(ValueError):
                c.author_catalog_question(target)
        self.assertFalse((self.root / 'catalog_question.json').exists())


if __name__ == '__main__':
    unittest.main()
