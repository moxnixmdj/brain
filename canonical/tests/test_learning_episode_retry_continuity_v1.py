"""Manual-only retry capsules survive restart; automatic replay stays blocked."""
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
out=run({'mode':'LEARNING_EPISODE','payload':{'task_id':'continuity-retry',
 'initial_facts':[],'target_effects':['unreachable.effect'],'capabilities':[]},
 'options':{'state_path':sys.argv[1],'retain_retry_context':True,
 'episode_id':'retry-example','scope_id':'retry-scope','max_capability_expansions':0}})
print(json.dumps(out))
'''
REOPEN = '''import json,sys
from canonical.runtime import autonomous_verified_self_improvement_v1 as a
from canonical.runtime import live_brain_runtime_v1 as runtime
s=a.load_state(sys.argv[1]); fid=next(iter(s['failures']))
r=a.get_failure_retry_context(fid,state_path=sys.argv[1])
blocked=runtime.execute_failure_repair_cycle({'failure_fingerprint':fid,'autonomous':True},state_path=sys.argv[1])
# Manual retry disables learning, but may still execute problem capabilities.
before=open(sys.argv[1], 'rb').read()
replayed=runtime._replay_retry_context(r['context'],repo_root=runtime.ROOT,
 information_provider=None,proposal_provider=None,capability_expander=None,state_path=sys.argv[1])
unchanged=before == open(sys.argv[1], 'rb').read()
print(json.dumps({'retry':r,'blocked':blocked,'replayed':replayed,'state_unchanged':unchanged,'stats':a.load_state(sys.argv[1])['stats']}))
'''


class LearningEpisodeRetryContinuityTests(unittest.TestCase):
    def test_restart_reopens_manual_context_and_blocks_automatic_execution(self):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=str(ROOT))
        with tempfile.TemporaryDirectory(prefix='brain_retry_continuity_') as tmp:
            state = str(Path(tmp) / 'state.json')
            def run(code):
                p = subprocess.run([sys.executable, '-c', code, state], cwd=ROOT, env=env,
                                   capture_output=True, text=True, check=True, timeout=30)
                return json.loads(p.stdout)
            taught = run(TEACH)
            self.assertEqual(taught['result']['status'], 'FAILURE_DIAGNOSED__REPAIR_QUEUED')
            data = run(REOPEN)
            self.assertFalse(data['retry']['autonomous_replay_authorized'])
            self.assertEqual(data['retry']['autonomous_replay_reason'], 'RETRY_CONTEXT_MANUAL_ONLY')
            self.assertEqual(data['retry']['context']['problem']['task_id'], 'continuity-retry')
            self.assertFalse(data['retry']['context']['learn'])
            self.assertEqual(data['blocked']['status'], 'AUTONOMOUS_REPAIR_BLOCKED__REPLAY_NOT_PROVED_SAFE')
            self.assertFalse(data['replayed']['pass'])
            self.assertEqual(data['replayed']['solver_output']['reason'],
                             taught['result']['solver_output']['reason'])
            self.assertTrue(data['state_unchanged'])
            self.assertEqual(data['stats']['failure_class_count'], 1)
            self.assertEqual(data['stats']['verified_skill_count'], 0)

    def test_context_marker_remains_fail_closed_if_authorization_flag_is_changed(self):
        from canonical.runtime import autonomous_verified_self_improvement_v1 as learning
        from canonical.runtime.unified_cognitive_fabric_v1 import run
        with tempfile.TemporaryDirectory(prefix='brain_retry_marker_') as tmp:
            state = Path(tmp) / 'state.json'
            request = {'mode': 'LEARNING_EPISODE', 'payload': {'task_id': 'marker',
                       'initial_facts': [], 'target_effects': ['absent'], 'capabilities': []},
                       'options': {'state_path': str(state), 'retain_retry_context': True,
                                   'max_capability_expansions': 0}}
            self.assertEqual(run(request)['result']['status'], 'FAILURE_DIAGNOSED__REPAIR_QUEUED')
            data = json.loads(state.read_text())
            fid, failure = next(iter(data['failures'].items()))
            capsule = next(iter(failure['retry_capsules'].values()))
            capsule['autonomous_replay_authorized'] = True
            state.write_text(json.dumps(data))
            retry = learning.get_failure_retry_context(fid, state_path=state)
            self.assertFalse(retry['autonomous_replay_authorized'])
            self.assertEqual(retry['autonomous_replay_reason'], 'RETRY_CONTEXT_MANUAL_ONLY')
            cycle = run({'mode': 'IMPROVEMENT_CYCLE', 'payload': {}, 'options': {
                'state_path': str(state), 'max_improvement_actions': 1}})
            self.assertEqual(cycle['result']['next_improvement_action']['last_attempt_status'],
                             'AUTONOMOUS_REPAIR_BLOCKED__REPLAY_NOT_PROVED_SAFE')

    def test_unsupported_contexts_fail_before_execution(self):
        from canonical.runtime.unified_cognitive_fabric_v1 import run
        with tempfile.TemporaryDirectory(prefix='brain_retry_reject_') as tmp:
            state = Path(tmp) / 'state.json'
            request = {'mode': 'LEARNING_EPISODE', 'payload': {'task_id': 't',
                       'capabilities': []}, 'options': {'state_path': str(state),
                       'retain_retry_context': True, 'effect_root': tmp}}
            self.assertIn('LEARNING_RETRY_OPTIONS_NOT_REPLAYABLE', run(request)['reason'])
            self.assertFalse(state.exists())
            del request['options']['effect_root']
            self.assertIn('OPAQUE_COGNITION_PROVIDER_FORBIDDEN',
                          run(request, proposal_provider=lambda *args: None)['reason'])
            self.assertFalse(state.exists())
            request['payload']['password'] = 'do-not-store'
            self.assertIn('RETRY_CONTEXT_SENSITIVE_KEY_REJECTED', run(request)['reason'])
            self.assertFalse(state.exists())
            from canonical.runtime import autonomous_verified_self_improvement_v1 as learning
            data = learning._empty_state()
            data['skills']['existing'] = {'active': True}
            state.write_text(json.dumps(data))
            before = state.read_bytes()
            del request['payload']['password']
            self.assertIn('LEARNING_RETRY_ACTIVE_SKILL_NOT_REPLAYABLE', run(request)['reason'])
            self.assertEqual(state.read_bytes(), before)
