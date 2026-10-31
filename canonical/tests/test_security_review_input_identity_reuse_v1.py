"""Direct real adapter boundary: review inputs cannot become diagnostic outputs."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from canonical.runtime.bound_capabilities import python_review_diff_security_gate as gate
from canonical.runtime.write_authority_v1 import WriteAuthorityViolation


class SecurityReviewInputIdentityTests(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.root = Path(td.name)
        (self.root/'wt').mkdir()
        self.source = self.root/'wt/m.py'
        self.source.write_text('value = 2\n')
        self.diff = self.root/'change.diff'
        self.diff.write_text('--- a/m.py\n+++ b/m.py\n@@ -1 +1 @@\n-value = 1\n+value = 2\n')
        self.source_bytes = self.source.read_bytes()
        self.diff_bytes = self.diff.read_bytes()
        self.source_mode = self.source.stat().st_mode

    def args(self, output, **extra):
        args = {'diff_path': 'change.diff', 'worktree_path': 'wt',
                'output_path': output, 'timeout_s': 3}
        args.update(extra)
        return args

    def assert_intact(self):
        self.assertEqual(self.source.read_bytes(), self.source_bytes)
        self.assertEqual(self.diff.read_bytes(), self.diff_bytes)
        self.assertEqual(self.source.stat().st_mode, self.source_mode)

    def refuse_alias(self, output):
        with self.assertRaisesRegex(WriteAuthorityViolation, '^REPORT_'):
            gate.run(self.args(output), self.root)
        self.assert_intact()

    def test_reviewed_source_cannot_be_report(self):
        self.refuse_alias('wt/m.py')

    def test_reviewed_diff_cannot_be_report(self):
        self.refuse_alias('change.diff')

    def test_differently_named_source_hardlink_cannot_be_report(self):
        os.link(self.source, self.root/'alias.json')
        self.refuse_alias('alias.json')
        self.assertEqual((self.root/'alias.json').read_bytes(), self.source_bytes)

    def test_differently_named_diff_hardlink_cannot_be_report(self):
        os.link(self.diff, self.root/'alias.json')
        self.refuse_alias('alias.json')
        self.assertEqual((self.root/'alias.json').read_bytes(), self.diff_bytes)

    def test_source_symlink_cannot_be_report(self):
        (self.root/'alias.json').symlink_to(self.source)
        self.refuse_alias('alias.json')
        self.assertTrue((self.root/'alias.json').is_symlink())

    def test_unreviewed_worktree_data_is_not_a_report_destination(self):
        data = self.root/'wt/config.json'
        data.write_text('{"setting": 1}\n')
        self.refuse_alias('wt/config.json')
        self.assertEqual(data.read_text(), '{"setting": 1}\n')

    def test_alias_refusal_happens_before_interpreter_probe(self):
        with self.assertRaisesRegex(WriteAuthorityViolation, '^REPORT_'):
            gate.run(self.args('wt/m.py', python_executable=str(self.root/'no-interpreter')), self.root)
        self.assert_intact()

    def test_diff_parent_escape_refuses_before_interpreter_probe(self):
        outside = self.root/'outside.py'
        outside.write_text('value = 2\n')
        self.diff.write_text(self.diff_bytes.decode().replace('a/m.py', 'a/../outside.py').replace('b/m.py', 'b/../outside.py'))
        with self.assertRaisesRegex(SystemExit, 'TOUCHED_FILE_OUTSIDE_WORKTREE'):
            gate.run(self.args('report.json', python_executable=str(self.root/'no-interpreter')), self.root)
        self.assertEqual(outside.read_text(), 'value = 2\n')
        self.assertFalse((self.root/'report.json').exists())

    def test_diff_symlink_escape_refuses_before_interpreter_probe(self):
        outside = self.root/'outside.py'
        outside.write_text('value = 2\n')
        self.source.unlink()
        self.source.symlink_to(outside)
        with self.assertRaisesRegex(SystemExit, 'TOUCHED_FILE_OUTSIDE_WORKTREE'):
            gate.run(self.args('report.json', python_executable=str(self.root/'no-interpreter')), self.root)
        self.assertEqual(outside.read_text(), 'value = 2\n')
        self.assertTrue(self.source.is_symlink())
        self.assertFalse((self.root/'report.json').exists())

    def test_fresh_report_and_replay_preserve_all_inputs(self):
        first = gate.run(self.args('reports/review.json'), self.root)
        payload = (self.root/'reports/review.json').read_bytes()
        second = gate.run(self.args('reports/review.json'), self.root)
        self.assertEqual(first, second)
        self.assertEqual((self.root/'reports/review.json').read_bytes(), payload)
        self.assertTrue(first['output_verified'])
        self.assertEqual(json.loads(payload)['files_touched'], 1)
        self.assert_intact()


if __name__ == '__main__':
    unittest.main()
