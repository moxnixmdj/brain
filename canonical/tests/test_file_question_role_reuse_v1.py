"""File questions reuse existing diff/read/filter tools, not keyword substitutes."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import uuid

from canonical.runtime import composer_route_v1 as composer
from canonical.runtime import live_brain_route_admission_v1 as admission
from canonical.runtime import capability_selection_retrieval_v1 as selection

ROOT = Path(__file__).resolve().parents[2]


class FileQuestionRoleReuseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(prefix='m9k7_', dir=ROOT / 'canonical/astra_runtime/tmp')
        self.addCleanup(self.tmp.cleanup)
        self.work = Path(self.tmp.name)
        self.a = self.work / 'a.txt'
        self.b = self.work / 'b.txt'
        self.a.write_text('apple\n')
        self.b.write_text('banana\n')
        self.rel_a = self.a.relative_to(ROOT).as_posix()
        self.rel_b = self.b.relative_to(ROOT).as_posix()
        self.task = 'FILE_QUESTION_' + uuid.uuid4().hex
        self.addCleanup(self.cleanup_state)

    def cleanup_state(self):
        for p in (ROOT / 'canonical/astra_runtime/state').glob(self.task + '__*'):
            if p.is_file():
                p.unlink()

    def solve(self, goal):
        result = admission.solve({'task_id': self.task, 'goal': goal})
        self.assertTrue(result.get('pass'), result.get('status'))
        self.assertTrue((result.get('raw_goal_acceptance') or {}).get('pass'), result)
        return result

    def test_comparison_question_reuses_diff_for_both_exit_status_answers(self):
        for content, code in [('banana\n', 1), ('apple\n', 0)]:
            with self.subTest(code=code):
                self.b.write_text(content)
                goal = f'What is different between the files {self.rel_a} and {self.rel_b}?'
                result = self.solve(goal)
                step = result['composer_execution']['steps'][0]
                self.assertEqual(step['args']['argv'], ['diff', self.rel_a, self.rel_b])
                self.assertEqual(step['result']['returncode'], code)
                check = result['raw_goal_acceptance']['reinspection_ledger'][0]['reinspection']
                self.assertTrue(check['command_re_run'])
                self.assertEqual(check['returncode_reproduced'], code)
                self.assertEqual(self.a.read_text(), 'apple\n')
                self.assertEqual(self.b.read_text(), content)

    def test_question_subject_is_not_a_file_search(self):
        goal = f'What is different between the files {self.rel_a} and {self.rel_b}?'
        self.assertEqual(composer.extract_argv(goal), ['diff', self.rel_a, self.rel_b])

    def test_contents_with_descriptive_containing_clause_uses_existing_reader(self):
        goal = f'Show the contents of the file {self.rel_a} containing the report'
        result = self.solve(goal)
        step = result['composer_execution']['steps'][0]
        self.assertEqual(step['args']['argv'], ['cat', self.rel_a])
        self.assertEqual(step['result']['stdout'], 'apple\n')
        self.assertEqual(self.a.read_text(), 'apple\n')

    def test_real_file_search_keeps_filename_output(self):
        directory = self.work.relative_to(ROOT).as_posix()
        goal = f"Which files in the directory {directory} contain 'apple'?"
        result = self.solve(goal)
        step = result['composer_execution']['steps'][0]
        self.assertIn('-l', step['args']['argv'])
        self.assertEqual(step['result']['stdout'].strip(), self.rel_a)
        self.assertEqual(self.a.read_text(), 'apple\n')
        self.assertEqual(self.b.read_text(), 'banana\n')

    def test_missing_line_search_value_never_falls_through_to_whole_file(self):
        goal = f'Show the lines containing text in the file {self.rel_a}'
        self.assertIsNone(composer.extract_argv(goal))
        result = admission.solve({'task_id': self.task, 'goal': goal})
        self.assertFalse(result.get('pass'), result)
        self.assertEqual(self.a.read_text(), 'apple\n')

    def test_existing_scalar_precondition_scope_does_not_depend_on_registry_size(self):
        caps = json.loads((ROOT / 'canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json')
                          .read_text())['capabilities']
        providers = {str(token) for entry in caps.values() for token in entry.get('provides', [])}
        unsatisfied = {cid: [str(token) for token in entry.get('requires', [])
                             if str(token) not in providers]
                       for cid, entry in caps.items()}
        scoped = sorted(cid for cid, tokens in unsatisfied.items()
                        if selection._TYPED_SCALAR_PRECONDITION in tokens)
        self.assertEqual(scoped, ['math.numeric_expression.sympy'])
        self.assertNotIn(selection._TYPED_SCALAR_PRECONDITION, providers)


if __name__ == '__main__':
    unittest.main()
