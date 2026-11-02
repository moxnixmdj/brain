"""Narrow experience-off control for transfer drive, not a whole-system guarantee."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from canonical.runtime import environment_learning_v1 as learner
from canonical.runtime import transfer_learning_v1 as transfer


class Counter:
    def __init__(self):
        self.value = 0
        self.actions = []

    def reset(self):
        self.value = 0

    def state(self):
        return self.value

    def act(self, action):
        self.actions.append(action)
        if action == 'inc':
            self.value += 1
        elif action == 'dec':
            self.value -= 1
        else:
            raise ValueError(action)

    def snapshot(self):
        return self.value

    def restore(self, value):
        self.value = value


class TransferLearningOffControlTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_state = transfer.STATE_PATH
        self.old_fingerprints = os.environ.get('BRAIN_TRANSFER_LEARNING_FINGERPRINTS')
        transfer.STATE_PATH = str(Path(self.tmp.name) / 'episodes.json')
        os.environ['BRAIN_TRANSFER_LEARNING_FINGERPRINTS'] = str(Path(self.tmp.name) / 'fingerprints.json')
        self.episodes = Path(transfer.STATE_PATH)
        self.fingerprints = Path(os.environ['BRAIN_TRANSFER_LEARNING_FINGERPRINTS'])
        # Non-empty stores: an empty store is not a control for memory use.
        self.episodes.write_text(json.dumps([{'plan': ['inc'], 'goal_key': 'target'}]))
        self.fingerprints.write_text(json.dumps({'fingerprints': {'prior': {'actions': ['inc']}}}))
        self.before = (self.episodes.read_bytes(), self.fingerprints.read_bytes())

    def tearDown(self):
        transfer.STATE_PATH = self.old_state
        if self.old_fingerprints is None:
            os.environ.pop('BRAIN_TRANSFER_LEARNING_FINGERPRINTS', None)
        else:
            os.environ['BRAIN_TRANSFER_LEARNING_FINGERPRINTS'] = self.old_fingerprints
        self.tmp.cleanup()

    def assert_stores_unchanged(self):
        self.assertEqual((self.episodes.read_bytes(), self.fingerprints.read_bytes()), self.before)

    def test_off_fixed_plan_executes_without_any_experience_or_model_access(self):
        env = Counter()
        with mock.patch.object(transfer, '_load', side_effect=AssertionError('episode read')), \
             mock.patch.object(transfer, '_save', side_effect=AssertionError('episode write')), \
             mock.patch.object(transfer, '_fp_load', side_effect=AssertionError('fingerprint read')), \
             mock.patch.object(transfer, '_fp_save', side_effect=AssertionError('fingerprint write')), \
             mock.patch.object(transfer, 'fingerprint', side_effect=AssertionError('fingerprinting')), \
             mock.patch.object(learner, 'learn_model', side_effect=AssertionError('model learning')):
            result = transfer.drive(env, ['inc', 'dec'], is_goal=lambda s: s == 2,
                                    goal_key='target', experience_mode='off',
                                    fixed_plan=['inc', 'inc'])
        self.assertTrue(result['pass'])
        self.assertEqual(result['status'], 'PASS__FIXED_PLAN_GOAL_OBSERVED')
        self.assertEqual(env.actions, ['inc', 'inc'])
        self.assertFalse(result['transferred'])
        self.assertFalse(result['episode_persisted'])
        self.assertEqual(result['experience_policy']['scope'], 'TRANSFER_DRIVE_ONLY')
        self.assert_stores_unchanged()

    def test_off_without_a_fixed_plan_does_not_probe_or_learn(self):
        env = Counter()
        result = transfer.drive(env, ['inc'], is_goal=lambda s: s == 1,
                                experience_mode='off')
        self.assertFalse(result['pass'])
        self.assertEqual(result['status'], 'OPEN__EXPERIENCE_DISABLED_NO_FIXED_PLAN')
        self.assertEqual(env.actions, [])
        self.assertEqual(result['interactions']['act_calls'], 0)
        self.assert_stores_unchanged()

    def test_failed_fixed_plan_cannot_fall_through_to_learning_in_off_mode(self):
        env = Counter()
        result = transfer.drive(env, ['inc'], is_goal=lambda s: s == 2,
                                experience_mode='off', fixed_plan=['inc'])
        self.assertFalse(result['pass'])
        self.assertEqual(result['status'], 'OPEN__FIXED_PLAN_GOAL_NOT_REACHED')
        self.assertEqual(env.actions, ['inc'])
        self.assert_stores_unchanged()

    def test_unavailable_fixed_action_is_rejected_before_any_effect(self):
        env = Counter()
        result = transfer.drive(env, ['inc'], is_goal=lambda s: s == 1,
                                experience_mode='off', fixed_plan=['inc', 'dec'])
        self.assertFalse(result['pass'])
        self.assertEqual(result['status'], 'FAIL_CLOSED__FIXED_PLAN_NOT_REPLAYABLE')
        self.assertEqual(env.actions, [])
        self.assert_stores_unchanged()

    def test_exception_after_fixed_effect_stops_both_modes(self):
        for mode in ('off', 'learn_and_recall'):
            with self.subTest(mode=mode):
                env = Counter()
                def broken_goal(_state):
                    raise RuntimeError('unavailable oracle')
                result = transfer.drive(env, ['inc'], is_goal=broken_goal,
                                        experience_mode=mode, fixed_plan=['inc'])
                self.assertFalse(result['pass'])
                self.assertEqual(result['status'], 'FAIL__FIXED_PLAN_EXECUTION_OR_CHECK')
                self.assertTrue(result['side_effects_may_exist'])
                self.assertEqual(env.actions, ['inc'])
                self.assert_stores_unchanged()

    def test_unchanged_fixed_plan_is_available_in_enabled_mode_too(self):
        env = Counter()
        result = transfer.drive(env, ['inc'], is_goal=lambda s: s == 2,
                                experience_mode='learn_and_recall', fixed_plan=['inc', 'inc'])
        self.assertTrue(result['pass'])
        self.assertEqual(result['status'], 'PASS__FIXED_PLAN_GOAL_OBSERVED')
        self.assertEqual(env.actions, ['inc', 'inc'])
        self.assert_stores_unchanged()

    def test_old_recall_only_switch_is_not_misrepresented_as_off(self):
        result = transfer.drive(Counter(), ['inc'], is_goal=lambda s: s == 1,
                                goal_key='fresh', use_transfer=False,
                                budget=8, seed=0, max_depth=3)
        self.assertTrue(result['pass'])
        self.assertTrue(result['episode_persisted'])
        self.assertTrue(result['experience_policy']['may_learn_model'])
        self.assertTrue(result['experience_policy']['may_persist_experience'])
        self.assertFalse(result['experience_policy']['may_read_retained_experience'])
        self.assertNotEqual(self.episodes.read_bytes(), self.before[0])

    def test_new_process_control_and_recall_use_same_fixed_baseline(self):
        fp = transfer.fingerprint(Counter(), ['inc', 'dec'], seed=0)
        transfer.remember(fp, 'target', ['inc'], reached=True)
        before = (self.episodes.read_bytes(), self.fingerprints.read_bytes())
        script = '''
import json, sys
from canonical.runtime import transfer_learning_v1 as t
from canonical.tests.test_transfer_learning_off_control_v1 import Counter
env = Counter()
r = t.drive(env, ['inc', 'dec'], is_goal=lambda s: s == 1, goal_key='target',
            experience_mode=sys.argv[1], fixed_plan=['dec'], budget=8, seed=0)
print(json.dumps({'result': r, 'final_state': env.state()}))
'''
        env = dict(os.environ, BRAIN_TRANSFER_LEARNING_STATE=str(self.episodes))
        def run(mode):
            proc = subprocess.run([sys.executable, '-c', script, mode],
                                  env=env, capture_output=True, text=True, check=True, timeout=10)
            return json.loads(proc.stdout)
        off = run('off')
        self.assertEqual((self.episodes.read_bytes(), self.fingerprints.read_bytes()), before)
        warm = run('learn_and_recall')
        self.assertFalse(off['result']['pass'])
        self.assertEqual(off['result']['status'], 'OPEN__FIXED_PLAN_GOAL_NOT_REACHED')
        self.assertEqual(off['final_state'], -1)
        self.assertTrue(warm['result']['pass'])
        self.assertEqual(warm['result']['status'], transfer.PASS_TRANSFERRED)
        self.assertEqual(warm['final_state'], 1)
        self.assertEqual(warm['result']['fixed_plan_trials'], 1)
        self.assertEqual(warm['result']['trials_spent'], 2)

    def test_invalid_mode_cannot_silently_enable_learning(self):
        env = Counter()
        with self.assertRaises(ValueError):
            transfer.drive(env, ['inc'], is_goal=lambda s: s == 1, experience_mode='of')
        self.assertEqual(env.actions, [])
        self.assert_stores_unchanged()


if __name__ == '__main__':
    unittest.main()
