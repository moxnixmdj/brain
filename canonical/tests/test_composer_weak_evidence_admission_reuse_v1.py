"""Composer planning must not turn weak vocabulary into a requested SWE pipeline."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from canonical.runtime import composer_route_v1 as composer


class ComposerWeakEvidenceAdmissionReuseTests(unittest.TestCase):
    def test_nonsense_does_not_select_a_hardcore_software_review_chain(self):
        result = composer.route('xyzzy plugh frobnicate nothing at all here')
        self.assertFalse(result['pass'], result)
        self.assertEqual(result['status'], 'OPEN__COMPOSER_NO_REACHABLE_TOKEN')
        self.assertEqual(result['chain'], [])
        rejected = [row for row in result['tried'] if row.get('intent_admission')]
        self.assertTrue(rejected)
        self.assertTrue(any(row['intent_admission'].get('rule') == 'R3_WEAK_EVIDENCE'
                            for row in rejected))

    def test_stated_python_command_still_uses_existing_command_runner(self):
        result = composer.route('Run the command "python3 -c \'print(42)\'"')
        self.assertTrue(result['pass'], result)
        self.assertEqual(result['chain'], ['shell.command.run'])
        self.assertEqual(result['tried'][0]['stated_command_line'],
                         ['python3', '-c', 'print(42)'])
        self.assertEqual(result['authority'], 'TYPE_LEVEL_COMPOSITION_REACHABLE')

    def test_opposite_quotes_inside_single_quoted_command_are_preserved(self):
        goal = "Run the command 'python3 -c \"print(42)\"'"
        self.assertEqual(composer.extract_argv(goal), ['python3', '-c', 'print(42)'])

    def test_nested_quoted_command_does_not_consume_following_report_clause(self):
        goal = 'Run the command "python3 -c \'print(42)\'" and save the report to report.json.'
        self.assertEqual(composer.extract_argv(goal), ['python3', '-c', 'print(42)'])

    def test_unterminated_quoted_command_is_not_a_partial_command(self):
        self.assertIsNone(composer.extract_argv('Run the command "python3 --version'))

    def test_nested_quoted_python_command_really_executes(self):
        root = Path(__file__).resolve().parents[2]
        with TemporaryDirectory(prefix='quoted_python_', dir=root / 'canonical/astra_runtime/tmp') as tmp:
            output = Path(tmp) / 'result.txt'
            rel = output.relative_to(root).as_posix()
            code = 'import pathlib,sys;pathlib.Path(sys.argv[1]).write_text(str(42))'
            goal = (f'Run the command "python3 -c \'{code}\' {rel}" '
                    f'and save output to {rel}')
            route = composer.route(goal)
            result = composer.execute_chain(route['chain'], goal)
            self.assertTrue(result['pass'], result)
            self.assertEqual(output.read_text(), '42')
            observed = result['steps'][0]['result']
            self.assertEqual(observed['returncode'], 0)
            self.assertEqual(observed['argv'], ['python3', '-c', code, rel])

    def test_specific_text_request_still_finds_writer_without_executing(self):
        result = composer.route('Write the text hello to out.txt')
        self.assertTrue(result['pass'], result)
        self.assertEqual(result['chain'], ['text.file.write'])
        self.assertNotIn('execution', result)
        self.assertNotIn('semantic_acceptance_complete', result)

    def test_operand_free_typed_plan_is_not_mistaken_for_task_execution(self):
        # The existing route API can plan a type-level chain before operands
        # exist. Reusing lexical admission must not silently replace that API
        # with the full live execution gate (which additionally checks inputs).
        result = composer.route('extract text from a pdf file')
        self.assertTrue(result['pass'], result)
        self.assertEqual(result['authority'], 'TYPE_LEVEL_COMPOSITION_REACHABLE')
        self.assertNotIn('execution', result)
        self.assertNotIn('semantic_acceptance_complete', result)


if __name__ == '__main__':
    unittest.main()
