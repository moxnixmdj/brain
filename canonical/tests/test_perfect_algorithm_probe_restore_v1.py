"""Reversible-probe failure controls; no claim of real-world isolation."""
import random
import unittest

from canonical.runtime import environment_learning_v1 as el
from canonical.swe_kernel import perfect_algorithm_v1 as pa


class ProbeEnv:
    def __init__(self, *, action_fails=False, snapshot_fails=False, restore_fails=False):
        self.value = 0
        self.actions = []
        self.restores = 0
        self.action_fails = action_fails
        self.snapshot_fails = snapshot_fails
        self.restore_fails = restore_fails

    def reset(self):
        self.value = 0

    def state(self):
        return self.value

    def snapshot(self):
        if self.snapshot_fails:
            raise RuntimeError('snapshot failed')
        return self.value

    def act(self, action):
        self.actions.append(action)
        self.value += 1
        if self.action_fails:
            raise RuntimeError('action failed after mutation')

    def restore(self, snapshot):
        self.restores += 1
        if self.restore_fails:
            raise RuntimeError('restore failed')
        self.value = snapshot


SCAN = {'learned': {'model': {}}, 'observations': {}}


class ProbeRestoreTests(unittest.TestCase):
    def test_heuristic_failure_restores_before_next_probe(self):
        env = ProbeEnv()
        def broken(_):
            raise ValueError('heuristic failed')
        result = pa.right_question(env, SCAN, ['a', 'b'], heuristic=broken)
        self.assertEqual(env.value, 0)
        self.assertEqual(env.restores, 2)
        self.assertEqual(result['probed_actions'], 0)
        self.assertEqual([x['probe_error'] for x in result['ranked']],
                         ['ACTION_OR_HEURISTIC_FAILED'] * 2)

    def test_action_that_mutates_then_raises_is_restored(self):
        env = ProbeEnv(action_fails=True)
        result = pa.right_question(env, SCAN, ['a'], heuristic=float)
        self.assertEqual(env.value, 0)
        self.assertEqual(env.restores, 1)
        self.assertEqual(result['ranked'][0]['probe_error'], 'ACTION_OR_HEURISTIC_FAILED')

    def test_snapshot_failure_never_acts(self):
        env = ProbeEnv(snapshot_fails=True)
        result = pa.right_question(env, SCAN, ['a'], heuristic=float)
        self.assertEqual(env.actions, [])
        self.assertEqual(result['ranked'][0]['probe_error'], 'SNAPSHOT_FAILED')

    def test_restore_failure_aborts_subsequent_probes(self):
        env = ProbeEnv(restore_fails=True)
        with self.assertRaises(pa.ProbeRestoreError):
            pa.right_question(env, SCAN, ['a', 'b'], heuristic=float)
        self.assertEqual(env.actions, ['a'])
        self.assertEqual(env.restores, 1)

    def test_run_refuses_to_plan_after_restore_failure(self):
        env = ProbeEnv(restore_fails=True)
        result = pa.run(env, 'goal', ['a', 'b'], goal_predicate=lambda s: s == 3,
                        memory={'rules': [], 'priors': {}}, budget=0, heuristic=float)
        self.assertEqual(result['status'], 'OPEN__PROBE_RESTORE_FAILED')
        self.assertFalse(result['pass'])
        self.assertNotIn('plan', result['steps'])
        self.assertEqual(env.actions, ['a'])

    def test_exploration_heuristic_failure_restores_between_probes(self):
        env = ProbeEnv()
        def broken(_):
            raise ValueError('heuristic failed')
        el._choose_action(env, ['a', 'b'], random.Random(0), broken, epsilon=0)
        self.assertEqual(env.actions, ['a', 'b'])
        self.assertEqual(env.value, 0)
        self.assertEqual(env.restores, 2)

    def test_scan_restore_failure_stops_before_walk_or_plan(self):
        env = ProbeEnv(restore_fails=True)
        result = pa.run(env, 'goal', ['a', 'b'], goal_predicate=lambda s: s == 3,
                        memory={'rules': [], 'priors': {}}, budget=1, max_depth=1,
                        heuristic=float, seed=0)
        self.assertEqual(result['status'], 'OPEN__PROBE_RESTORE_FAILED')
        self.assertEqual(result['steps']['scan']['status'], 'REFUSED__PROBE_RESTORE_FAILED')
        self.assertNotIn('plan', result['steps'])
        self.assertEqual(env.actions, ['a'])

    def test_successful_probes_restore_and_report(self):
        env = ProbeEnv()
        result = pa.right_question(env, SCAN, ['a', 'b'], heuristic=float)
        self.assertEqual(env.value, 0)
        self.assertEqual(env.restores, 2)
        self.assertEqual(result['probed_actions'], 2)
        self.assertEqual([x['closeness'] for x in result['ranked']], [1.0, 1.0])


if __name__ == '__main__':
    unittest.main()
