"""The creature's real inspector gap produces a scoped information subgoal."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from canonical.runtime import creature_runtime_v1 as runtime
from canonical.runtime import self_authored_obligations_v1 as author
from canonical.runtime import unified_cognitive_fabric_v1 as fabric


class InspectorInvestigationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='inspector_investigation_')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_real_self_authored_goal_and_child_survive_restart_and_real_fabric(self):
        c = runtime.boot(self.root, identity='investigator', life=10)
        investigation = c.author_inspector_investigation()
        parent, child = investigation['parent'], investigation['child']
        ids, inspected = runtime._registry_and_inspectors()
        self.assertIn(parent['capability_id'], ids)
        self.assertNotIn(parent['capability_id'], inspected)
        proposals, before, done = author.capability_gap_proposals(ids, inspected)
        proposal = next(p for p in proposals if p.id == parent['id'])
        self.assertEqual(parent['claim'], proposal.claim)
        self.assertEqual(parent['source'], proposal.source)
        self.assertEqual(author.admit(proposal, before=before, done=done).status, author.ADMITTED)
        self.assertFalse(c.inspector_slot_check(before))
        self.assertTrue(c.inspector_slot_check(done))
        for cheat in author.cheat_worlds(done):
            self.assertFalse(c.inspector_slot_check(cheat))
        self.assertEqual(child['parent_id'], parent['id'])
        self.assertEqual(child['capability_id'], parent['capability_id'])
        self.assertEqual(c.report()['open'], 2)
        c = runtime.boot(self.root, identity='investigator')
        self.assertEqual(c.inspector_investigation(), investigation)
        self.assertFalse(c.inspector_slot_check(before))
        self.assertTrue(c.inspector_slot_check(done))
        row = c.step()
        self.assertEqual(row['work'], child['id'])
        self.assertTrue(row['ok'], row)
        self.assertEqual(row['information']['parent_id'], parent['id'])
        self.assertFalse(row['information']['execution_authority'])
        self.assertEqual(c.inspector_information()['observation'], row['information'])
        self.assertEqual(c.inspector_information()['freshness'], 'HISTORICAL_NOT_REVALIDATED')
        self.assertEqual(c.report()['open'], 1)
        c = runtime.boot(self.root, identity='investigator')
        self.assertEqual(c.inspector_investigation(), investigation)
        remembered = c.inspector_information()
        self.assertEqual(remembered['observation'], row['information'])
        remembered['observation']['listed'] = 'tampered copy'
        self.assertEqual(c.inspector_information()['observation'], row['information'])
        self.assertEqual(c.report()['open'], 1)
        self.assertNotIn(parent['id'], c._closed)
        self.assertIn(child['id'], c._closed)
        blocked = c.step(lambda work, instance: {'ok': True, 'verified': True, 'correct': True})
        self.assertEqual(blocked['status'], 'WAITING_FOR_INSPECTOR_VERIFIER')
        self.assertEqual(blocked['work'], parent['id'])
        self.assertNotIn(parent['id'], c._closed)
        self.assertEqual(c.report()['open'], 1)

    def test_goal_and_answer_recovered_across_fresh_processes(self):
        import os
        import subprocess
        import sys
        root = Path(__file__).resolve().parents[2]
        c = runtime.boot(self.root, identity='investigator', life=10)
        expected = c.author_inspector_investigation()
        code = '''import json, os, sys
from canonical.runtime import creature_runtime_v1 as R
c=R.boot(sys.argv[1], identity="investigator")
inv=c.inspector_investigation()
result=c.step() if sys.argv[2] == "run" else None
print(json.dumps({"pid":os.getpid(),"inv":inv,"row":result,"report":c.report(),
                  "memory":c.inspector_information(), "completed":c._self.state.completed}))
'''
        env = dict(os.environ, PYTHONPATH=str(root), PYTHONDONTWRITEBYTECODE='1')
        def spawn(mode):
            proc = subprocess.run([sys.executable, '-B', '-c', code, str(self.root), mode],
                                  env=env, cwd=root, text=True, capture_output=True,
                                  timeout=60, check=True)
            return json.loads(proc.stdout)
        run, read = spawn('run'), spawn('read')
        self.assertNotEqual(run['pid'], read['pid'])
        self.assertEqual(run['inv'], expected)
        self.assertTrue(run['row']['ok'])
        self.assertEqual(read['inv'], expected)
        self.assertEqual(read['report']['open'], 1)
        self.assertEqual(read['memory']['observation'], run['row']['information'])
        self.assertEqual(read['memory']['freshness'], 'HISTORICAL_NOT_REVALIDATED')
        self.assertEqual(read['completed'][-1]['information']['parent_id'], expected['parent']['id'])

    def test_wrong_answer_cannot_close_child_or_parent_even_after_restart(self):
        c = runtime.boot(self.root, identity='investigator', life=10)
        inv = c.author_inspector_investigation()
        # Flip the target's membership, regardless of which real gap is selected.
        from canonical.runtime import live_integrated_brain_v1 as live
        target = inv['parent']['capability_id']
        ids = set(live.load_verified_registry())
        forged_ids = ids - {target} if target in ids else ids | {target}
        forged = {'schema': fabric.SCHEMA, 'status': 'LIVE_FEDERATED_COGNITIVE_FABRIC',
                  'verified_bound_capability_ids': sorted(forged_ids)}
        with patch.object(fabric, 'run', return_value=forged):
            row = c.step()
        self.assertFalse(row['ok'])
        self.assertEqual(row['blocked'], 'CATALOG_MEMBERSHIP_MISMATCH')
        c = runtime.boot(self.root, identity='investigator')
        self.assertNotIn(inv['parent']['id'], c._closed)
        self.assertNotIn(inv['child']['id'], c._closed)
        self.assertIsNone(c.inspector_information())
        self.assertEqual(c.report()['open'], 2)

    def test_kill_during_child_preserves_parent_child_and_charge(self):
        import os
        import select
        import subprocess
        import sys
        root = Path(__file__).resolve().parents[2]
        c = runtime.boot(self.root, identity='investigator', life=10)
        expected = c.author_inspector_investigation()
        code = '''import sys, time
from unittest.mock import patch
from canonical.runtime import creature_runtime_v1 as R, unified_cognitive_fabric_v1 as F
c=R.boot(sys.argv[1], identity="investigator")
def wait(*args, **kwargs):
    print("ENTERED", flush=True)
    time.sleep(60)
with patch.object(F, "run", side_effect=wait):
    c.step()
'''
        env = dict(os.environ, PYTHONPATH=str(root), PYTHONDONTWRITEBYTECODE='1')
        proc = subprocess.Popen([sys.executable, '-B', '-c', code, str(self.root)],
                                env=env, cwd=root, text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        try:
            ready, _, _ = select.select([proc.stdout], [], [], 30)
            self.assertTrue(ready, 'child did not enter the operation')
            self.assertEqual(proc.stdout.readline().strip(), 'ENTERED')
        finally:
            proc.kill()
            proc.communicate(timeout=10)
        c = runtime.boot(self.root, identity='investigator')
        self.assertEqual(c.inspector_investigation(), expected)
        self.assertEqual(c.report()['life_remaining'], 9.75)
        self.assertEqual(c.report()['open'], 2)
        self.assertNotIn(expected['parent']['id'], c._closed)
        self.assertNotIn(expected['child']['id'], c._closed)
        self.assertEqual(len(c._self.state.interrupted), 1)

    def test_real_parent_check_is_not_an_independent_decoy_verifier(self):
        c = runtime.boot(self.root, identity='investigator', life=10)
        inv = c.author_inspector_investigation()
        parent = inv['parent']
        self.assertEqual(parent['check_id'], 'INSPECTED_VERIFIED_SLOT_V1')
        self.assertFalse(parent['independent_verification'])
        self.assertFalse(parent['execution_authority'])

    def test_tampered_investigation_is_refused(self):
        c = runtime.boot(self.root, identity='investigator')
        inv = c.author_inspector_investigation()
        path = self.root / 'inspector_investigation.json'
        data = json.loads(path.read_text())
        data['parent']['check_id'] = 'ARBITRARY_CODE'
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, 'INSPECTOR_INVESTIGATION_INVALID'):
            runtime.boot(self.root, identity='investigator')

    def test_child_does_not_reuse_an_unrelated_catalog_question_result(self):
        c = runtime.boot(self.root, identity='investigator', life=10)
        inv = c.author_inspector_investigation()
        child = inv['child']
        unrelated = runtime.Creature._catalog_spec('investigator', child['capability_id'])
        self.assertNotEqual(child['id'], unrelated['id'])
        self.assertEqual(c.report()['open'], 2)

    def test_generic_success_with_colliding_ids_does_not_close_typed_work(self):
        c = runtime.boot(self.root, identity='investigator', life=10)
        inv = c.author_inspector_investigation()
        c.abandon_inspector_investigation(inv['parent']['id'])
        for wid in (inv['parent']['id'], inv['child']['id']):
            p = author.Proposal(id=wid, claim='unrelated', source='test',
                                check=lambda w: (w.get('inspected') or {}).get('x') == 'verified')
            c.author_board([p], before={'inspected': {'x': 'missing'}},
                           done={'inspected': {'x': 'verified'}})
            self.assertTrue(c.step(lambda work, instance: {'ok': True})['ok'])
        again = c.author_inspector_investigation()
        self.assertEqual(again, inv)
        self.assertEqual(c.report()['open'], 2)
        self.assertNotIn(inv['parent']['id'], c._closed)
        self.assertNotIn(inv['child']['id'], c._closed)
        c = runtime.boot(self.root, identity='investigator')
        self.assertEqual(c.report()['open'], 2)

    def test_no_gap_does_not_create_an_investigation(self):
        c = runtime.boot(self.root, identity='investigator', life=10)
        with patch.object(runtime, '_registry_and_inspectors', return_value=(['cap.x'], ['cap.x'])):
            with self.assertRaisesRegex(ValueError, 'NO_AFFORDABLE_INSPECTOR_GAP'):
                c.author_inspector_investigation()
        self.assertIsNone(c.inspector_investigation())
        self.assertEqual(c.report()['open'], 0)
        self.assertFalse((self.root / 'inspector_investigation.json').exists())

    def test_no_silent_replacement_and_explicit_abandon(self):
        c = runtime.boot(self.root, identity='investigator', life=10)
        inv = c.author_inspector_investigation()
        with self.assertRaisesRegex(ValueError, 'WOULD_REPLACE'):
            c.author_catalog_question('some.other.capability')
        with self.assertRaisesRegex(ValueError, 'WOULD_REPLACE'):
            c.author_board([], before={}, done={})
        with self.assertRaisesRegex(ValueError, 'INSPECTOR_INVESTIGATION_OWNS_CHILD'):
            c.abandon_catalog_question(inv['child']['id'])
        self.assertEqual(c.abandon_inspector_investigation(inv['parent']['id'])['status'],
                         'ABANDONED_NOT_COMPLETED')
        c = runtime.boot(self.root, identity='investigator')
        self.assertEqual(c.report()['open'], 0)


if __name__ == '__main__':
    unittest.main()
