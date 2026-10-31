"""Reuse real execution boundary controls on cross-file parameter renaming."""
import contextlib
import io
import unittest

from canonical.tests import test_rename_execution_safety_reuse_v1 as safety
from canonical.runtime.bound_capabilities import python_refactor_rename_parameter as rename


class ParameterRefactorExecutionSafetyTests(safety.RenameExecutionSafetyTests):
    def setUp(self):
        super().setUp()
        self.caller.write_text('from pkg.core import top\ndef call(): return top(x=2)\n')
        self.originals[self.caller] = (self.caller.read_bytes(), self.caller.stat().st_mode & 0o777)

    def execute(self, **kwargs):
        args = dict(source_root='src', module='pkg/core.py', qualname='top',
                    old_param='x', new_param='value', output_path='report.json',
                    run_tests=['tests/test_behavior.py'])
        args.update(kwargs)
        with contextlib.redirect_stdout(io.StringIO()):
            return rename.run(args, self.root)

    def test_real_crossfile_rename_remains_verified(self):
        result = self.execute()
        self.assertTrue(result['verified'])
        self.assertTrue(result['complete'])
        self.assertEqual(result['files_edited'], 2)
        self.assertEqual(self.core.read_text(), 'def top(value): return value+1\n')
        self.assertEqual(self.caller.read_text(), 'from pkg.core import top\ndef call(): return top(value=2)\n')
        self.assertEqual(self.core.stat().st_mode & 0o777, 0o640)
        self.assertEqual(self.test.read_bytes(), self.originals[self.test][0])

    def test_late_span_refusal_does_not_publish_earlier_file(self):
        # Python normalizes fullwidth ｘ to x in the AST, unlike source bytes.
        # Unsupported spellings must refuse without an earlier edit left behind.
        self.caller.write_text('from pkg.core import top\ncaption="é"; result = top(ｘ=2)\n')
        self.originals[self.caller] = (self.caller.read_bytes(), self.caller.stat().st_mode & 0o777)
        with self.assertRaisesRegex(SystemExit, 'SPAN_INTEGRITY'):
            self.execute(run_tests=[])
        self.assert_restored()


if __name__ == '__main__':
    unittest.main()
