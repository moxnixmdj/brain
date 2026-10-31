"""Exercise real cross-file rename failure boundaries, without runner mocks."""
import contextlib
import io
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from canonical.runtime.bound_capabilities import python_refactor_rename_symbol as rename


class RenameExecutionSafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(prefix='rename-execution-safety-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.src = self.root / 'src'
        for name in ('pkg', 'use', 'tests'):
            (self.src / name).mkdir(parents=True)
            (self.src / name / '__init__.py').write_text('')
        self.core = self.src / 'pkg/core.py'
        self.core.write_text('def top(x): return x+1\n')
        self.caller = self.src / 'use/caller.py'
        self.caller.write_text('from pkg.core import top\ndef call(): return top(2)\n')
        self.core.chmod(0o640)
        self.test = self.src / 'tests/test_behavior.py'
        self.test.write_text('from use.caller import call\ndef test_behavior():\n    assert call()==3\n')
        self.originals = {p: (p.read_bytes(), p.stat().st_mode & 0o777)
                          for p in self.src.rglob('*.py')}

    def execute(self, **kwargs):
        args = dict(source_root='src', module='pkg/core.py', qualname='top',
                    new_symbol='apex', output_path='report.json',
                    run_tests=['tests/test_behavior.py'])
        args.update(kwargs)
        with contextlib.redirect_stdout(io.StringIO()):
            return rename.run(args, self.root)

    def assert_restored(self):
        for p, (raw, mode) in self.originals.items():
            self.assertEqual(p.read_bytes(), raw, str(p))
            self.assertEqual(p.stat().st_mode & 0o777, mode, str(p))
        self.assertFalse((self.root / 'report.json').is_file())

    def test_real_timeout_restores_every_edited_file(self):
        self.test.write_text('import time\ndef test_behavior():\n    time.sleep(30)\n')
        self.originals[self.test] = (self.test.read_bytes(), self.test.stat().st_mode & 0o777)
        with self.assertRaises((subprocess.TimeoutExpired, SystemExit)):
            self.execute(timeout_s=1)
        self.assert_restored()

    def test_missing_interpreter_restores_every_edited_file(self):
        with self.assertRaises((FileNotFoundError, SystemExit)):
            self.execute(python_executable=str(self.root / 'missing/python'))
        self.assert_restored()

    def test_green_test_cannot_replace_verified_candidate(self):
        self.test.write_text('from pathlib import Path\nfrom use.caller import call\n'
                             'def test_behavior():\n    assert call()==3\n'
                             '    Path("pkg/core.py").write_text("def apex(x): return 999\\n")\n')
        self.originals[self.test] = (self.test.read_bytes(), self.test.stat().st_mode & 0o777)
        with self.assertRaisesRegex(SystemExit, 'SOURCE_CHANGED_AFTER_VERIFICATION'):
            self.execute()
        self.assert_restored()

    def test_green_test_cannot_change_source_permissions(self):
        self.test.write_text('from pathlib import Path\ndef test_behavior():\n'
                             '    Path("pkg/core.py").chmod(0o600)\n')
        self.originals[self.test] = (self.test.read_bytes(), self.test.stat().st_mode & 0o777)
        with self.assertRaisesRegex(SystemExit, 'SOURCE_CHANGED_AFTER_VERIFICATION'):
            self.execute()
        self.assert_restored()

    def test_actual_output_overflow_restores_edits(self):
        self.test.write_text('import sys\ndef test_behavior():\n'
                             '    sys.stdout.write("x" * 9_000_000)\n'
                             '    sys.stdout.flush()\n')
        self.originals[self.test] = (self.test.read_bytes(), self.test.stat().st_mode & 0o777)
        with self.assertRaisesRegex(RuntimeError, 'TEST_OUTPUT_LIMIT_EXCEEDED'):
            self.execute(run_tests=['-s', 'tests/test_behavior.py'])
        self.assert_restored()

    def test_report_publication_failure_restores_edits(self):
        (self.root / 'report.json').mkdir()
        with self.assertRaises(OSError):
            self.execute()
        self.assert_restored()

    def test_report_hardlink_cannot_overwrite_source(self):
        (self.root / 'report.json').hardlink_to(self.core)
        before = self.core.read_bytes()
        with self.assertRaisesRegex(RuntimeError, 'REPORT_OVERWRITES_INPUT'):
            self.execute()
        self.assertEqual(self.core.read_bytes(), before)
        self.assertEqual(self.caller.read_bytes(), self.originals[self.caller][0])

    def test_real_crossfile_rename_remains_verified(self):
        result = self.execute()
        self.assertTrue(result['verified'])
        self.assertTrue(result['complete'])
        self.assertEqual(result['files_edited'], ['pkg/core.py', 'use/caller.py'])
        self.assertEqual(self.core.read_text(), 'def apex(x): return x+1\n')
        self.assertEqual(self.caller.read_text(), 'from pkg.core import apex\ndef call(): return apex(2)\n')
        self.assertEqual(self.core.stat().st_mode & 0o777, 0o640)
        self.assertEqual(self.test.read_bytes(), self.originals[self.test][0])


if __name__ == '__main__':
    unittest.main()
