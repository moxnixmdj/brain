"""These automatic routes must not execute exploratory programs outside a boundary.

Dependency substitutes only check route selection; no subprocess primitive, loader,
filesystem implementation or network API is patched. The executable fixture is a
real, harmless local script whose execution leaves a temporary marker.
"""
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from canonical.runtime import computer_env_v1 as cenv
from canonical.runtime import composer_route_v1 as composer
from canonical.runtime import curriculum_v1 as curriculum
from canonical.runtime import live_brain_route_admission_v1 as door
from canonical.runtime import cli_capability_acquisition_v1 as acquisition
from canonical.runtime import jit_knowledge_v1 as jit
from canonical.runtime import ignorance_ledger_v1 as ledger
from canonical.swe_kernel import closed_loop_autonomous_controller_v1 as controller
from canonical.swe_kernel.verified_skill_crystallizer_v1 import VerifiedSkillStore

BLOCKED = 'FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT'


class UnconfinedAutomaticRouteGuardTests(unittest.TestCase):
    def test_door_fallback_refuses_before_real_file_execution(self):
        with tempfile.TemporaryDirectory() as d:
            source = Path(d) / 'notes.txt'
            source.write_bytes(b'original')
            with mock.patch.object(cenv, 'perform', return_value={'pass': True}) as perform:
                result = door._serve_by_acting({'task_id': 'T', 'goal': 'compress notes.txt into notes.txt.gz', 'cwd': d})
            perform.assert_not_called()
            self.assertFalse(result['pass'])
            self.assertEqual(result['status'], BLOCKED)
            self.assertEqual(source.read_bytes(), b'original')
            self.assertFalse((Path(d) / 'notes.txt.gz').exists())

    def test_door_refuses_before_recalled_workflow_and_preserves_prior_effect_uncertainty(self):
        from canonical.swe_kernel import causal_trace_to_skill_compiler_v1 as compiler
        prior = {'pass': False, 'status': 'FAIL__RAW_GOAL_COMPILATION_GAP',
                 'executed': True, 'side_effects_may_exist': True}
        with mock.patch.object(door, '_solve_request', return_value=prior), \
             mock.patch.object(compiler, 'recall_and_execute_workflow', return_value={'pass': True}) as recall:
            result = door.solve({'task_id': 'T', 'goal': 'compress notes.txt into notes.txt.gz'})
        recall.assert_not_called()
        self.assertFalse(result['pass'])
        self.assertEqual(result['status'], BLOCKED)
        self.assertTrue(result['executed'])
        self.assertTrue(result['side_effects_may_exist'])
        self.assertFalse(result['fallback_executed'])

    def test_safety_check_error_does_not_try_recall(self):
        from canonical.swe_kernel import causal_trace_to_skill_compiler_v1 as compiler
        prior = {'pass': False, 'status': 'FAIL__RAW_GOAL_COMPILATION_GAP'}
        with mock.patch.object(door, '_solve_request', return_value=prior), \
             mock.patch.object(door, '_serve_by_acting', side_effect=RuntimeError('check unavailable')), \
             mock.patch.object(compiler, 'recall_and_execute_workflow', return_value={'pass': True}) as recall:
            result = door.solve({'task_id': 'T', 'goal': 'compress notes.txt into notes.txt.gz'})
        recall.assert_not_called()
        self.assertFalse(result['pass'])
        self.assertEqual(result['status'], 'FAIL__RAW_GOAL_COMPILATION_GAP')

    def test_explicit_contract_refusal_is_preserved(self):
        prior = {'pass': False, 'status': 'FAIL_CLOSED__REQUESTED_CONTRACT_CHECKS_NOT_VERIFIED'}
        with mock.patch.object(door, '_solve_request', return_value=prior), \
             mock.patch.object(door, '_serve_by_acting') as fallback:
            result = door.solve({'task_id': 'T', 'goal': 'compress notes.txt into notes.txt.gz',
                                 'contract_checks': [{'kind': 'example'}]})
        fallback.assert_not_called()
        self.assertEqual(result['status'], prior['status'])
        self.assertFalse(result['pass'])

    def test_composer_does_not_start_unconfined_candidate_code_or_exploration(self):
        from canonical.runtime import program_synthesis_v1 as synth, documentation_mining_v1 as docs
        with mock.patch.object(synth, 'synthesize_or_recall', return_value={'pass': False}) as s, \
             mock.patch.object(docs, 'learn_or_recall', return_value={'pass': False}) as d, \
             mock.patch.object(cenv, 'discover', return_value={'closed': False}) as discover:
            result = composer.route('compress notes.txt into notes.txt.gz', g={})
        s.assert_not_called(); d.assert_not_called(); discover.assert_not_called()
        self.assertFalse(result['pass'])
        self.assertEqual(result['status'], BLOCKED)

    def test_curriculum_explore_does_not_run_programs(self):
        with mock.patch.object(cenv, 'discover', return_value={'closed': True}) as discover:
            result = curriculum._try_explore('compress a.txt into a.txt.gz')
        discover.assert_not_called()
        self.assertFalse(result['closed'])
        self.assertEqual(result['status'], BLOCKED)

    def test_learning_fallback_does_not_run_named_program_or_perform(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            marker = root / 'executed'
            exe = root / 'fixture-command'
            exe.write_text('#!/bin/sh\nprintf ran > "' + str(marker) + '"\n')
            exe.chmod(0o700)
            source = root / 'notes.txt'
            source.write_bytes(b'original')
            request = {'task_id': 'T', 'goal': 'compress notes.txt into notes.txt.gz', 'cwd': d}
            with mock.patch.dict(os.environ, {'BRAIN_VERIFIED_SKILL_DB': str(root / 'skills.sqlite')}), \
                 mock.patch.object(door, 'solve', return_value={'pass': False, 'status': 'FAIL__RAW_GOAL_COMPILATION_GAP'}), \
                 mock.patch.object(ledger, 'note', return_value='test-gap'), \
                 mock.patch.object(ledger, 'rank', return_value=[]), \
                 mock.patch.object(jit, 'resolve', return_value={'complete': True, 'document_count': 0}), \
                 mock.patch.object(door, '_named_executable', return_value=str(exe)), \
                 mock.patch.object(door.goal_compiler, '_repo_paths', return_value=[('notes.txt', source)]), \
                 mock.patch.object(VerifiedSkillStore, 'count', return_value=0), \
                 mock.patch.object(acquisition, 'acquire', return_value={'verified': False}) as acquire, \
                 mock.patch.object(cenv, 'perform', return_value={'pass': False}) as perform:
                result = door.solve_or_learn(request)
            self.assertFalse(marker.exists(), 'named executable ran without confinement')
            acquire.assert_not_called(); perform.assert_not_called()
            self.assertFalse(result['pass'])
            self.assertEqual(result['learning']['computer_env_status'], BLOCKED)
            self.assertEqual(result['learning']['executable_status'], BLOCKED)
            self.assertEqual(source.read_bytes(), b'original')

    def test_learning_does_not_retry_a_boundary_refusal(self):
        prior = {'pass': False, 'status': BLOCKED, 'failure_class': BLOCKED.removeprefix('FAIL_CLOSED__')}
        with mock.patch.object(door, 'solve', return_value=prior), \
             mock.patch.object(jit, 'resolve') as resolve, \
             mock.patch.object(cenv, 'perform') as perform:
            result = door.solve_or_learn({'task_id': 'T', 'goal': 'compress a.txt into a.txt.gz'}, learn=True)
        resolve.assert_not_called(); perform.assert_not_called()
        self.assertEqual(result['status'], BLOCKED)
        self.assertFalse(result['pass'])

    def test_curriculum_never_falls_through_boundary_refusal(self):
        with mock.patch.object(curriculum, '_try_solve', return_value={'closed': False, 'status': BLOCKED}), \
             mock.patch.object(curriculum, '_try_acquire', return_value={'closed': True}) as acquire, \
             mock.patch.object(curriculum, 'ordered_channels', return_value=['solve', 'acquire']), \
             mock.patch.object(curriculum, 'credit_channel') as credit, \
             mock.patch.object(ledger, 'resolve') as resolve:
            result = curriculum.study({'id': 'fixture-gap', 'what': 'compress a.txt into a.txt.gz'})
        acquire.assert_not_called(); credit.assert_not_called(); resolve.assert_not_called()
        self.assertFalse(result['pass'])
        self.assertEqual(result['status'], BLOCKED)
        self.assertEqual(result['channels_tried'], ['solve'])

    def test_curriculum_execution_channels_refuse(self):
        for func, args in ((curriculum._try_with, ('a.txt.gz', 'gzip')),
                           (curriculum._try_acquire, ('a.txt.gz',)),
                           (curriculum._try_synthesize, ('a.txt.gz',)),
                           (curriculum._try_documentation, ('a.txt.gz',))):
            with self.subTest(channel=func.__name__):
                result = func(*args)
                self.assertFalse(result['closed'])
                self.assertEqual(result['status'], BLOCKED)

    def test_real_route_calls_do_not_run_a_path_executable(self):
        unshare = shutil.which('unshare')
        if not unshare:
            self.skipTest('network namespaces unavailable; no unconfined fallback')
        probe = subprocess.run([unshare, '--user', '--map-root-user', '--net',
                                sys.executable, '-c', 'pass'], capture_output=True, timeout=15)
        if probe.returncode:
            self.skipTest('network namespaces unavailable; no unconfined fallback')
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); bindir = root / 'bin'; bindir.mkdir()
            marker = root / 'executed'
            fake = bindir / 'gzip'
            fake.write_text('#!/bin/sh\nprintf invoked > "' + str(marker) + '"\n')
            fake.chmod(0o700)
            (root / 'notes.txt').write_bytes(b'original')
            repo = Path(__file__).resolve().parents[2]
            code = '''
import json, pathlib, sys
sys.path.insert(0, sys.argv[1])
from canonical.runtime import composer_route_v1 as composer, curriculum_v1 as cur
from canonical.runtime import live_brain_route_admission_v1 as door
root = pathlib.Path(sys.argv[2]); goal = 'compress notes.txt into notes.txt.gz'
results = [door._serve_by_acting({'task_id': 'T', 'goal': goal, 'cwd': str(root)}),
           composer.route(goal, g={}), cur._try_explore(goal), cur._try_acquire(goal),
           cur._try_with(goal, 'gzip'), cur._try_synthesize(goal), cur._try_documentation(goal)]
print(json.dumps([x.get('status') for x in results]))
'''
            env = {'PATH': str(bindir), 'HOME': d, 'PYTHONDONTWRITEBYTECODE': '1',
                   'BRAIN_STATE_DIR': str(root / 'state')}
            proc = subprocess.run([unshare, '--user', '--map-root-user', '--net',
                                   sys.executable, '-I', '-c', code, str(repo), d],
                                  env=env, capture_output=True, text=True, timeout=30, check=True)
            import json
            self.assertEqual(json.loads(proc.stdout), [BLOCKED] * 7)
            self.assertFalse(marker.exists(), 'PATH executable ran outside confinement')
            self.assertEqual((root / 'notes.txt').read_bytes(), b'original')
            self.assertFalse((root / 'notes.txt.gz').exists())

    def test_controller_refuses_demonstration_before_compilation(self):
        with mock.patch.object(controller, 'compile_and_qualify_skill') as compile_skill, \
             mock.patch.object(controller, 'recall_and_execute_workflow') as recall:
            result = controller.solve_or_learn({'task_id': 'T', 'goal': 'some task',
                                                'demonstration_trace': [{'kind': 'cli_exec', 'argv': ['anything']}],
                                                'postcondition': {'kind': 'stdout_integer'}})
        compile_skill.assert_not_called(); recall.assert_not_called()
        self.assertFalse(result['pass'])
        self.assertEqual(result['status'], BLOCKED)
        self.assertFalse(result['executed'])

    def test_controller_does_not_override_boundary_refusal(self):
        self.assertTrue(controller._is_honest_contract_refusal({'status': BLOCKED}))

    def test_controller_does_not_run_unconfined_query_or_archive(self):
        with tempfile.TemporaryDirectory() as d:
            source = Path(d) / 'notes.txt'; source.write_bytes(b'one\ntwo\n')
            for goal in ('count lines in notes.txt', 'pack notes.txt into notes.tar.gz'):
                with self.subTest(goal=goal):
                    with mock.patch.object(controller, 'recall_and_execute_workflow', return_value=None) as recall, \
                         mock.patch.object(door, 'solve', return_value={'pass': False, 'status': 'FAIL__RAW_GOAL_COMPILATION_GAP'}), \
                         mock.patch.object(cenv, 'answer_query', return_value={'pass': False}) as query, \
                         mock.patch.object(cenv, 'perform', return_value={'pass': False}) as perform:
                        result = controller.solve_or_learn({'task_id': 'T', 'goal': goal}, cwd=d,
                                                           allow_tier1_composition=False, record_open_gap=False)
                    recall.assert_not_called(); query.assert_not_called(); perform.assert_not_called()
                    self.assertFalse(result['pass'])
                    self.assertEqual(result['status'], BLOCKED)
                    self.assertEqual(source.read_bytes(), b'one\ntwo\n')


if __name__ == '__main__':
    unittest.main()
