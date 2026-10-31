"""Real public composed effects must be measured against a PRE-execution world."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import uuid

from canonical.runtime import live_brain_route_admission_v1 as admission
from canonical.runtime import live_integrated_brain_v1 as live
from canonical.runtime import goal_compiler

ROOT = Path(__file__).resolve().parents[2]


class CompositionObservationOrderReuseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(prefix='e7w9_', dir=ROOT / 'canonical/astra_runtime/tmp')
        self.addCleanup(self.tmp.cleanup)
        self.work = Path(self.tmp.name)
        self.base = self.work.relative_to(ROOT).as_posix()
        self.task = 'OBS_ORDER_' + uuid.uuid4().hex
        self.addCleanup(self.cleanup_state)

    def cleanup_state(self):
        for path in (ROOT / 'canonical/astra_runtime/state').glob(self.task + '__*'):
            if path.is_file():
                path.unlink()

    def run_goal(self, goal):
        result = admission.solve({'task_id': self.task, 'goal': goal})
        self.assertTrue(result.get('pass'), result.get('status'))
        self.assertTrue((result.get('raw_goal_acceptance') or {}).get('pass'), result)
        self.assertNotIn('observed_effect_errors', result)
        return result

    def test_compile_gap_deletion_reuses_pre_execution_observation(self):
        source = self.work / 'a.txt'
        source.write_text('remove only this')
        goal = 'Delete the file ' + self.base + '/a.txt'
        with self.assertRaises(goal_compiler.GoalCompilationFailure):
            live.compile_against_live_registry(goal, ROOT)
        self.run_goal(goal)
        self.assertFalse(source.exists())

    def test_creating_an_empty_file_is_a_real_observed_effect(self):
        self.run_goal('Create an empty file ' + self.base + '/e9')
        self.assertEqual((self.work / 'e9').read_bytes(), b'')

    def test_creating_a_directory_is_a_real_observed_effect(self):
        self.run_goal('Create the directory ' + self.base + '/d9')
        self.assertTrue((self.work / 'd9').is_dir())

    def test_in_place_transformation_is_measured_against_original_bytes(self):
        source = self.work / 'a.txt'
        source.write_text('alpha\nbeta\n')
        self.run_goal('Convert the file ' + self.base + '/a.txt to upper case')
        self.assertEqual(source.read_text(), 'ALPHA\nBETA\n')

    def test_read_only_answer_does_not_require_mutation(self):
        source = self.work / 'a.txt'
        original = b'alpha\nbeta\n'
        source.write_bytes(original)
        self.run_goal('Read the file ' + self.base + '/a.txt')
        self.assertEqual(source.read_bytes(), original)

    def test_unchanged_world_still_rejects_forged_producer_success(self):
        source = self.work / 'a.txt'
        source.write_text('unchanged')
        goal = 'Delete the file ' + self.base + '/a.txt'
        before = admission.observe_world(goal)
        after = admission.observe_world(goal)
        # Deliberately forged producer flag: no command executed and no effect.
        errors = admission.observed_effect_errors(goal, before, after, {'pass': True}, [])
        self.assertIn('NO_OBSERVED_EFFECT', errors)
        self.assertEqual(source.read_text(), 'unchanged')


if __name__ == '__main__':
    unittest.main()
