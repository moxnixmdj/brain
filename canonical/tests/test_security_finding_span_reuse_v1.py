"""Actual Bandit spans, not mocked scanner reports, determine changed-code scope."""
import difflib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from canonical.runtime.bound_capabilities import python_review_diff_security_gate as gate

BASE = ('import subprocess\ndef run(command):\n    return subprocess.run(\n'
        '        "echo hello",\n        shell=True,\n    )\n')


@unittest.skipUnless(importlib.util.find_spec('bandit'), 'real Bandit required')
class SecurityFindingSpanTests(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.root = Path(td.name)
        (self.root/'wt').mkdir()

    def review(self, before, after):
        source = self.root/'wt/m.py'
        source.write_text(after)
        diff = ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                           fromfile='a/m.py', tofile='b/m.py', n=0))
        (self.root/'change.diff').write_text(diff)
        result = gate.run({'diff_path': 'change.diff', 'worktree_path': 'wt',
                           'output_path': 'report.json'}, self.root)
        self.assertEqual(source.read_text(), after)
        self.assertEqual((self.root/'change.diff').read_text(), diff)
        return result, json.loads((self.root/'report.json').read_text())

    def test_variable_command_edit_with_unchanged_shell_anchor_blocks(self):
        result, report = self.review(BASE, BASE.replace('"echo hello"', 'command'))
        self.assertEqual(result['gate'], 'FAIL', report)
        self.assertIs(result['verified'], False)
        rows = [row for row in report['blocking_findings'] if row['test_id'] == 'B602']
        self.assertEqual(len(rows), 1, report)
        self.assertEqual(rows[0]['line'], 5)
        self.assertEqual(rows[0]['severity'], 'HIGH')

    def test_direct_shell_flag_change_still_blocks(self):
        after = BASE.replace('"echo hello"', 'command')
        result, report = self.review(after.replace('shell=True', 'shell=False'), after)
        self.assertEqual(result['gate'], 'FAIL', report)
        self.assertTrue(any(row['test_id'] == 'B602' for row in report['blocking_findings']))

    def test_unrelated_function_rename_does_not_block_preexisting_call(self):
        before = BASE.replace('"echo hello"', 'command')
        result, report = self.review(before, before.replace('def run(', 'def execute('))
        self.assertEqual(result['gate'], 'PASS', report)
        self.assertIs(result['verified'], True)
        rows = [row for row in report['advisory_findings'] if row['test_id'] == 'B602']
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['out_of_scope'], 'preexisting')

    def test_literal_command_remains_advisory_under_existing_policy(self):
        result, report = self.review(BASE, BASE.replace('"echo hello"', '"echo goodbye"'))
        self.assertEqual(result['gate'], 'PASS', report)
        self.assertEqual(report['blocking_count'], 0)

    def test_report_is_reproducible_for_same_actual_analyzer_inputs(self):
        after = BASE.replace('"echo hello"', 'command')
        first, _ = self.review(BASE, after)
        payload = (self.root/'report.json').read_bytes()
        second, _ = self.review(BASE, after)
        self.assertEqual(first, second)
        self.assertEqual((self.root/'report.json').read_bytes(), payload)


if __name__ == '__main__':
    unittest.main()
