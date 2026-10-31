"""Reuse existing command semantics without mistaking an answer for a mutation."""
from pathlib import Path
from tempfile import TemporaryDirectory
import os
import unittest
import uuid

from canonical.runtime import live_brain_route_admission_v1 as admission

ROOT = Path(__file__).resolve().parents[2]


class CommandEffectClassificationReuseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(prefix='k2v8_', dir=ROOT / 'canonical/astra_runtime/tmp')
        self.addCleanup(self.tmp.cleanup)
        self.work = Path(self.tmp.name)
        self.source = self.work / 'a.txt'
        self.rel = self.source.relative_to(ROOT).as_posix()
        self.task = 'CMD_EFFECT_' + uuid.uuid4().hex
        self.addCleanup(self.cleanup_state)

    def cleanup_state(self):
        for path in (ROOT / 'canonical/astra_runtime/state').glob(self.task + '__*'):
            if path.is_file():
                path.unlink()

    def solve(self, goal):
        result = admission.solve({'task_id': self.task, 'goal': goal})
        self.assertTrue(result.get('pass'), result.get('status'))
        acceptance = result.get('raw_goal_acceptance') or {}
        self.assertTrue(acceptance.get('pass'), result)
        return result

    def test_existing_inspector_flag_policy_is_shared_without_widening(self):
        from canonical.runtime import raw_goal_trace_acceptance_v1 as accept
        for argv in (['sort', '-u', 'a.txt'], ['grep', '-i', 'apple', 'a.txt'],
                     ['sed', '-e', 's/a/b/', 'a.txt']):
            with self.subTest(argv=argv):
                self.assertTrue(accept.command_is_read_only(argv))
        for argv in (['sort', '-o', 'b.txt', 'a.txt'],
                     ['sort', '--output=b.txt', 'a.txt'],
                     ['sed', '-i', 's/a/b/', 'a.txt'],
                     ['sed', '--in-place', 's/a/b/', 'a.txt'],
                     ['python3', '-c', 'print(42)'], ['chmod', '+x', 'a.txt']):
            with self.subTest(argv=argv):
                self.assertFalse(accept.command_is_read_only(argv))

    def test_duplicate_filter_answers_without_modifying_input(self):
        original = b'apple\nbanana\napple\n'
        self.source.write_bytes(original)
        result = self.solve('Remove the duplicate lines from the file ' + self.rel)
        step = result['composer_execution']['steps'][0]
        self.assertEqual(step['result']['stdout'], 'apple\nbanana\n')
        self.assertEqual(self.source.read_bytes(), original)
        self.assertTrue(result['raw_goal_acceptance']['reinspection_ledger'][0]
                        ['reinspection']['command_re_run'])

    def test_blank_line_filter_answers_without_modifying_input(self):
        original = b'apple\n\nbanana\n'
        self.source.write_bytes(original)
        result = self.solve('Remove the empty lines from the file ' + self.rel)
        self.assertEqual(result['composer_execution']['steps'][0]['result']['stdout'],
                         'apple\nbanana\n')
        self.assertEqual(self.source.read_bytes(), original)

    @unittest.skipUnless(os.name == 'posix', 'POSIX owner executable bit')
    def test_chmod_is_observed_even_when_size_and_mtime_are_unchanged(self):
        original = b'unchanged bytes\n'
        self.source.write_bytes(original)
        self.source.chmod(0o644)
        before = self.source.stat()
        self.solve('Make the file ' + self.rel + ' executable')
        after = self.source.stat()
        self.assertTrue(after.st_mode & 0o100)
        self.assertEqual((before.st_size, before.st_mtime_ns),
                         (after.st_size, after.st_mtime_ns))
        self.assertEqual(self.source.read_bytes(), original)

    def test_in_place_transform_still_has_to_change_the_world(self):
        self.source.write_text('alpha\n')
        goal = 'Convert the file ' + self.rel + ' to upper case'
        before = admission.observe_world(goal)
        errors = admission.observed_effect_errors(
            goal, before, admission.observe_world(goal), {'pass': True}, [])
        self.assertIn('NO_OBSERVED_EFFECT', errors)
        self.assertEqual(self.source.read_text(), 'alpha\n')

    def test_explicit_filter_output_cannot_be_forged_as_present(self):
        self.source.write_text('apple\napple\n')
        target = (self.work / 'b.txt').relative_to(ROOT).as_posix()
        goal = 'Write the unique lines of the file ' + self.rel + ' to the file ' + target
        before = admission.observe_world(goal)
        errors = admission.observed_effect_errors(
            goal, before, admission.observe_world(goal), {'pass': True}, [target])
        self.assertIn('NO_OBSERVED_EFFECT', errors)
        self.assertFalse((ROOT / target).exists())

    def test_explicit_reader_cannot_discharge_a_conflicting_mutation_request(self):
        self.source.write_text('alpha\n')
        for instruction in ('Delete the file ', 'Convert the file '):
            goal = instruction + self.rel + ' by running the command "cat ' + self.rel + '"'
            before = admission.observe_world(goal)
            errors = admission.observed_effect_errors(
                goal, before, admission.observe_world(goal), {'pass': True}, [])
            self.assertIn('NO_OBSERVED_EFFECT', errors, goal)
        self.assertEqual(self.source.read_text(), 'alpha\n')

    def test_permission_change_cannot_be_forged_as_a_success(self):
        self.source.write_text('unchanged')
        self.source.chmod(0o644)
        goal = 'Make the file ' + self.rel + ' executable'
        before = admission.observe_world(goal)
        errors = admission.observed_effect_errors(
            goal, before, admission.observe_world(goal), {'pass': True}, [])
        self.assertIn('NO_OBSERVED_EFFECT', errors)
        self.assertFalse(self.source.stat().st_mode & 0o100)


if __name__ == '__main__':
    unittest.main()
