"""The raw wrapper's own memory hooks honor the runtime learning switch.

This does not certify nested adapters or other memory channels as disabled.
"""
import unittest
from unittest import mock

from canonical.runtime import live_brain_runtime_v1 as runtime
from canonical.runtime import live_integrated_brain_v1 as integrated
from canonical.runtime import unified_cognitive_fabric_v1 as fabric


class RawGoalLearningSwitchTests(unittest.TestCase):
    def call(self, learn):
        raw = {'pass': False, 'status': 'FAIL__EXAMPLE', 'semantic_acceptance_complete': False}
        with mock.patch.object(integrated, '_run_raw_goal_impl', return_value=raw) as execute, \
             mock.patch.object(integrated, '_record_raw_goal_experience') as successes, \
             mock.patch.object(integrated, '_record_raw_goal_pathology') as pathology, \
             mock.patch.object(integrated, '_record_raw_goal_failure_diagnosis') as diagnosis, \
             mock.patch.object(integrated, '_advance_learning_queue') as queue:
            result = runtime.run({'mode': 'raw_bound', 'request': {'task_id': 't', 'goal': 'example'},
                                  'learn': learn, 'auto_repair': False})
        execute.assert_called_once()
        return result, (successes, pathology, diagnosis, queue)

    def test_learning_false_skips_raw_wrapper_recording_and_queue(self):
        result, hooks = self.call(False)
        self.assertFalse(result['pass'])
        self.assertIsNone(result['learning'])
        for hook in hooks:
            hook.assert_not_called()

    def test_fabric_learning_false_reaches_the_raw_wrapper(self):
        raw = {'pass': False, 'status': 'FAIL__EXAMPLE', 'semantic_acceptance_complete': False}
        with mock.patch.object(integrated, '_run_raw_goal_impl', return_value=raw), \
             mock.patch.object(integrated, '_record_raw_goal_experience') as successes, \
             mock.patch.object(integrated, '_record_raw_goal_pathology') as pathology, \
             mock.patch.object(integrated, '_record_raw_goal_failure_diagnosis') as diagnosis, \
             mock.patch.object(integrated, '_advance_learning_queue') as queue, \
             mock.patch.object(fabric.improvement_driver, 'drain') as drain:
            result = fabric.run({'mode': 'RAW_GOAL',
                                 'payload': {'task_id': 't', 'goal': 'example'},
                                 'options': {'learn': False, 'auto_repair': False}})
        self.assertFalse(result['result']['pass'])
        self.assertIsNone(result['compounding_tick'])
        drain.assert_not_called()
        for hook in (successes, pathology, diagnosis, queue):
            hook.assert_not_called()

    def test_explicit_learning_mode_with_learning_disabled_fails_closed(self):
        for mode in ('LEARNING_EPISODE', 'IMPROVEMENT_CYCLE'):
            with self.subTest(mode=mode):
                with mock.patch.object(fabric.self_improvement, 'run_learning_episode') as learn, \
                     mock.patch.object(fabric.improvement_driver, 'drain') as drain, \
                     mock.patch.object(fabric.one_shot_reality_closure, 'run') as one_shot:
                    result = fabric.run({'mode': mode, 'payload': {}, 'options': {'learn': False}})
                self.assertFalse(result['pass'])
                self.assertIn('LEARNING_DISABLED', result['reason'])
                learn.assert_not_called(); drain.assert_not_called(); one_shot.assert_not_called()

    def test_learning_true_preserves_existing_hooks(self):
        with mock.patch.object(runtime, '_observe_runtime_outcome', return_value=None):
            result, hooks = self.call(True)
        self.assertFalse(result['pass'])
        for hook in hooks:
            hook.assert_called_once()


if __name__ == '__main__':
    unittest.main()
