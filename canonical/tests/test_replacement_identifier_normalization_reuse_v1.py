"""Python identifier normalization must precede existing collision checks."""
import contextlib
import io
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from canonical.runtime.bound_capabilities import python_refactor_rename_symbol as symbol
from canonical.runtime.bound_capabilities import python_refactor_rename_parameter as parameter


class ReplacementIdentifierNormalizationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(prefix='replacement-identifier-normalization-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.src = self.root / 'src'
        self.src.mkdir()
        self.definition = self.src / 'm.py'

    def execute(self, adapter, **kwargs):
        args = dict(source_root='src', module='m.py', qualname='top', output_path='report.json')
        args.update(kwargs)
        with contextlib.redirect_stdout(io.StringIO()):
            return adapter.run(args, self.root)

    def assert_refusal_preserved_source(self, original):
        self.assertEqual(self.definition.read_bytes(), original)
        self.assertFalse((self.root / 'report.json').exists())

    def test_symbol_collision_uses_compiler_normalized_name(self):
        original = b'def K(x): return 99\ndef top(x): return x+1\n'
        self.definition.write_bytes(original)
        with self.assertRaisesRegex(SystemExit, 'NEW_NAME_COLLIDES'):
            self.execute(symbol, new_symbol='K')
        self.assert_refusal_preserved_source(original)

    def test_parameter_collision_uses_compiler_normalized_name(self):
        original = b'def top(x, K=10): return x+K\n'
        self.definition.write_bytes(original)
        with self.assertRaisesRegex(SystemExit, 'NEW_PARAM_ALREADY_PRESENT'):
            self.execute(parameter, old_param='x', new_param='K')
        self.assert_refusal_preserved_source(original)

    def prepare_real_test(self):
        test = self.src / 'test_behavior.py'
        raw = b'from caller import call\ndef test_behavior():\n    assert call()==3\n'
        test.write_bytes(raw)
        return test, raw

    def test_symbol_emits_and_reports_canonical_name_with_real_pytest(self):
        self.definition.write_bytes(b'def top(x): return x+1\n')
        caller = self.src / 'caller.py'
        caller.write_bytes(b'from m import top\ndef call(): return top(2)\n')
        test, raw = self.prepare_real_test()
        result = self.execute(symbol, new_symbol='K', run_tests=['test_behavior.py'])
        self.assertTrue(result['verified'])
        self.assertEqual(result['new_symbol'], 'K')
        self.assertEqual(self.definition.read_bytes(), b'def K(x): return x+1\n')
        self.assertEqual(caller.read_bytes(), b'from m import K\ndef call(): return K(2)\n')
        self.assertEqual(test.read_bytes(), raw)

    def test_parameter_emits_and_reports_canonical_name_with_real_pytest(self):
        self.definition.write_bytes(b'def top(x): return x+1\n')
        caller = self.src / 'caller.py'
        caller.write_bytes(b'from m import top\ndef call(): return top(x=2)\n')
        test, raw = self.prepare_real_test()
        result = self.execute(parameter, old_param='x', new_param='K', run_tests=['test_behavior.py'])
        self.assertTrue(result['verified'])
        self.assertEqual(result['new_param'], 'K')
        self.assertEqual(self.definition.read_bytes(), b'def top(K): return K+1\n')
        self.assertEqual(caller.read_bytes(), b'from m import top\ndef call(): return top(K=2)\n')
        self.assertEqual(test.read_bytes(), raw)

    def test_normalized_keyword_refuses_before_publication(self):
        original = b'def top(x): return x+1\n'
        self.definition.write_bytes(original)
        for adapter, operands in [(symbol, dict(new_symbol='ｉｆ')),
                                  (parameter, dict(old_param='x', new_param='ｉｆ'))]:
            self.definition.write_bytes(original)
            (self.root / "report.json").unlink(missing_ok=True)
            with self.subTest(adapter=adapter.__name__):
                with self.assertRaisesRegex(SystemExit, 'INVALID_IDENTIFIER'):
                    self.execute(adapter, **operands)
                self.assert_refusal_preserved_source(original)


if __name__ == '__main__':
    unittest.main()
