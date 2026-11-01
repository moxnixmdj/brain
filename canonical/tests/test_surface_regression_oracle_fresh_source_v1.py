"""The revert oracle must execute reverted source, not copied green bytecode."""
import pathlib
import py_compile
import subprocess
import tempfile
import unittest

from hardcore_swe_surface_probe_20261030 import oracle_refactor_then_test


class FreshSourceRevertOracleTests(unittest.TestCase):
    def test_green_bytecode_cannot_hide_the_reverted_bug(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            (root / 'app').mkdir()
            (root / 'tests').mkdir()
            (root / 'app/__init__.py').write_text('')
            (root / 'tests/__init__.py').write_text('')
            source = root / 'app/calc.py'
            source.write_text('def add(a, b):\n    return a - b\n')
            (root / 'tests/test_calc.py').write_text(
                'import unittest\nfrom app.calc import add\n'
                'class T(unittest.TestCase):\n'
                '    def test_add(self):\n        self.assertEqual(add(1, 2), 3)\n')

            def git(*args):
                subprocess.run(['git', '-c', 'user.name=fixture', '-c',
                                'user.email=fixture@example.invalid', *args],
                               cwd=root, check=True, capture_output=True)

            git('init', '-q')
            git('add', 'app', 'tests')
            git('commit', '-qm', 'buggy fixture')
            source.write_text('def add(a, b):\n    return a + b\n')
            (root / 'tests/test_regression.py').write_text(
                'import unittest\nfrom app.calc import add\n'
                'class R(unittest.TestCase):\n'
                '    def test_regression(self):\n        self.assertEqual(add(2, 3), 5)\n')
            git('add', 'app/calc.py', 'tests/test_regression.py')
            git('commit', '-qm', 'fix with regression test')
            # A real unchecked cache makes the copied-bytecode failure deterministic,
            # without changing the clock or substituting filesystem/import behavior.
            py_compile.compile(str(source), doraise=True,
                               invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH)
            ok, details = oracle_refactor_then_test(root, {})
            self.assertTrue(ok, details)
            self.assertTrue(details['new_tests_fail_on_buggy_code'], details)
            self.assertIn('return a + b', source.read_text())
