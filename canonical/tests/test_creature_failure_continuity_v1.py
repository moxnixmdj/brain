"""A real fabric failure survives restart as telemetry, not as a skill."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]

TEACH = '''import json,sys
from canonical.runtime.unified_cognitive_fabric_v1 import run
out=run({'mode':'LEARNING_EPISODE','payload':{'task_id':'CONTINUITY-FAIL-001',
 'initial_facts':[],'target_effects':['unreachable.effect'],'capabilities':[]},
 'options':{'state_path':sys.argv[1],'episode_id':'continuity-episode-1',
 'scope_id':'continuity-scope','max_capability_expansions':0}})
print(json.dumps({'status':out['status'],'inner_pass':out['inner_pass'],
                  'result_status':out['result']['status']}))
'''
REOPEN = '''import json,sys
from canonical.runtime.autonomous_verified_self_improvement_v1 import load_state
s=load_state(sys.argv[1])
print(json.dumps({'stats':s['stats'],'failures':list(s['failures'])}))
'''


class FailureContinuityTests(unittest.TestCase):
    def test_fabric_records_failure_and_new_process_reopens_it_without_skill_claim(self):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=str(ROOT))
        with tempfile.TemporaryDirectory(prefix='brain_continuity_') as tmp:
            state = str(Path(tmp) / 'state.json')
            def run(code):
                p = subprocess.run([sys.executable, '-c', code, state], cwd=ROOT, env=env,
                                   capture_output=True, text=True, check=True, timeout=30)
                return json.loads(p.stdout)
            outcome = run(TEACH)
            self.assertEqual(outcome['status'], 'FABRIC_DISPATCH_COMPLETE')
            self.assertFalse(outcome['inner_pass'])
            self.assertIn('ORPHANED_TELEMETRY', outcome['result_status'])
            data = run(REOPEN)
            self.assertEqual(data['stats']['failure_class_count'], 1)
            self.assertEqual(len(data['failures']), 1)
            self.assertEqual(data['stats']['verified_episode_count'], 0)
            self.assertEqual(data['stats']['verified_skill_count'], 0)
            self.assertEqual(data['stats']['pending_improvement_count'], 0)
