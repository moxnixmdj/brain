"""R3 auto-context exclusion for the generic runtime; not system-wide amnesia."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from canonical.runtime import autonomous_verified_self_improvement_v1 as learning

from canonical.runtime import live_brain_runtime_v1 as runtime
from canonical.runtime import unified_cognitive_fabric_v1 as fabric


PROBLEM = {'task_id': 'test', 'initial_facts': [], 'target_effects': ['DONE'], 'capabilities': []}


class R3ContextExclusionTests(unittest.TestCase):
    def test_generic_exclusion_skips_r3_state_and_forwards_no_prior_episodes(self):
        with mock.patch.object(runtime, '_active_learning_context') as context, \
             mock.patch.object(runtime, '_skill_plan') as plan, \
             mock.patch.object(runtime, '_run_learning_episode') as learn, \
             mock.patch.object(runtime, '_v12_run', return_value={'pass': True, 'status': 'FIXTURE'}) as solver:
            result = runtime.run({'mode': 'generic', 'problem': PROBLEM, 'learn': False,
                                  'r3_context_mode': 'exclude'})
        self.assertTrue(result['pass'], result)
        context.assert_not_called(); plan.assert_not_called(); learn.assert_not_called()
        self.assertEqual(solver.call_args.kwargs['kwargs']['prior_verified_episode_records'], [])
        self.assertEqual(result['verified_prior_episode_count_reused'], 0)
        self.assertEqual(result['active_verified_skill_count'], 0)
        self.assertEqual(result['r3_context_policy'], 'EXCLUDED_AUTOMATIC_R3_HISTORY_ONLY')

    def test_real_solver_excludes_populated_r3_context_without_writing_state(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'state.json'
            state = learning._empty_state()
            state['episodes']['old'] = {'episode_id': 'old', 'scope_id': 'scope',
                                        'program_sha256': 'fixture-not-independent-proof'}
            path.write_text(json.dumps(state))
            before = path.read_bytes()
            common = {'mode': 'generic', 'problem': PROBLEM, 'learn': False,
                      'state_path': str(path), 'scope_id': 'scope', 'episode_id': 'new',
                      'auto_repair': False}
            use = runtime.run(dict(common, r3_context_mode='use'))
            exclude = runtime.run(dict(common, r3_context_mode='exclude'))
            self.assertFalse(use['pass'])
            self.assertFalse(exclude['pass'])
            self.assertEqual(use['verified_prior_episode_count_reused'], 1)
            self.assertEqual(exclude['verified_prior_episode_count_reused'], 0)
            self.assertEqual(exclude['r3_context_policy'], 'EXCLUDED_AUTOMATIC_R3_HISTORY_ONLY')
            self.assertEqual(path.read_bytes(), before)

    def test_exclusion_cannot_be_combined_with_learning_or_injected_history(self):
        requests = [
            {'mode': 'generic', 'problem': PROBLEM, 'r3_context_mode': 'exclude'},
            {'mode': 'generic', 'problem': PROBLEM, 'learn': False, 'r3_context_mode': 'exclude',
             'solver_kwargs': {'prior_verified_episode_records': [{'episode_id': 'injected'}]}},
            {'mode': 'generic', 'problem': PROBLEM, 'learn': False, 'r3_context_mode': 'typo'},
        ]
        for request in requests:
            with self.subTest(request=request), mock.patch.object(runtime, '_active_learning_context') as context, \
                 mock.patch.object(runtime, '_v12_run') as solver:
                result = runtime.run(request)
            self.assertFalse(result['pass'], result)
            context.assert_not_called(); solver.assert_not_called()

    def test_fabric_adaptive_forwards_exclusion_and_does_not_drain(self):
        with mock.patch.object(runtime, '_active_learning_context') as context, \
             mock.patch.object(runtime, '_v12_run', return_value={'pass': True, 'status': 'FIXTURE'}) as solver, \
             mock.patch.object(fabric.improvement_driver, 'drain') as drain:
            result = fabric.run({'mode': 'ADAPTIVE_SOLVER', 'payload': PROBLEM,
                                 'options': {'learn': False, 'r3_context_mode': 'exclude'}})
        self.assertTrue(result['result']['pass'], result)
        context.assert_not_called(); drain.assert_not_called()
        self.assertEqual(solver.call_args.kwargs['kwargs']['prior_verified_episode_records'], [])
        self.assertEqual(result['result']['_live_runtime']['r3_context_policy'],
                         'EXCLUDED_AUTOMATIC_R3_HISTORY_ONLY')

    def test_option_is_refused_for_other_fabric_modes_not_silently_ignored(self):
        for mode in ('RAW_GOAL', 'CATALOG', 'ONE_SHOT_REALITY_CLOSURE'):
            with self.subTest(mode=mode), mock.patch.object(fabric.live_runtime, 'run') as run, \
                 mock.patch.object(fabric.one_shot_reality_closure, 'run') as closure:
                result = fabric.run({'mode': mode, 'payload': {'task_id': 't', 'goal': 'example'},
                                     'options': {'learn': False, 'r3_context_mode': 'exclude'}})
            self.assertFalse(result['pass'])
            self.assertIn('R3_CONTEXT_MODE_UNSUPPORTED', result['reason'])
            run.assert_not_called(); closure.assert_not_called()


if __name__ == '__main__':
    unittest.main()
