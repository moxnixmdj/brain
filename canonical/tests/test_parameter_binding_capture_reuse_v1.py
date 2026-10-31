"""Replacement identifiers must not capture compiler-resolved bindings."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from canonical.runtime.bound_capabilities import python_refactor_rename_parameter as rename


class ParameterBindingCaptureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(prefix='parameter-binding-capture-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / 'm.py'

    def run_rename(self, **kwargs):
        args = dict(source_root='.', module='m.py', qualname='f', old_param='x',
                    new_param='value', output_path='reports/result.json')
        args.update(kwargs)
        return rename.run(args, self.root)

    def refuses(self, source, **kwargs):
        raw = source.encode('utf-8')
        self.source.write_bytes(raw)
        self.source.chmod(0o640)
        with self.assertRaisesRegex(SystemExit, 'NEW_PARAM_NAME_CAPTURED'):
            self.run_rename(**kwargs)
        self.assertEqual(self.source.read_bytes(), raw)
        self.assertEqual(self.source.stat().st_mode & 0o777, 0o640)
        self.assertFalse((self.root / 'reports/result.json').exists())

    def test_local_assignment_collision(self):
        self.refuses('def f(x):\n    value=10\n    return x+value\n')

    def test_normalized_replacement_cannot_bypass_local_capture_guard(self):
        self.refuses('def f(x):\n    K=10\n    return x+K\n', new_param='K')

    def test_branch_binding_collision(self):
        self.refuses('def f(x):\n    if x:\n        value=10\n    return x\n')

    def test_import_binding_collision(self):
        self.refuses('def f(x):\n    import math as value\n    return x+value.floor(2)\n')

    def test_with_binding_collision(self):
        self.refuses('def f(x):\n    with open("data") as value:\n        return x+len(value.read())\n')

    def test_exception_binding_collision(self):
        self.refuses('def f(x):\n    try:\n        return x+1\n    except ValueError as value:\n        return x\n')

    def test_function_definition_collision(self):
        self.refuses('def f(x):\n    def value(): return 1\n    return x+value()\n')

    def test_existing_builtin_reference_would_be_shadowed(self):
        self.refuses('def f(x): return x+len([1,2])\n', new_param='len')

    def test_nested_local_captures_outer_parameter_reference(self):
        self.refuses('def f(x):\n    def inner():\n        value=10\n        return x+value\n    return inner()\n')

    def test_nested_global_declaration_captures_rewritten_reference(self):
        self.refuses('value=10\ndef f(x):\n    def inner():\n        global value\n        return x+value\n    return inner()\n')

    def test_comprehension_binding_captures_outer_parameter_reference(self):
        self.refuses('def f(x): return [x+value for value in (1,2)]\n')

    def test_unrelated_nested_binding_remains_allowed_with_real_pytest(self):
        core = ('def f(x):\n    def inner(value): return value+1\n'
                '    return x+inner(2)\n')
        self.source.write_text(core)
        test = self.root / 'test_behavior.py'
        oracle = b'from m import f\ndef test_behavior(): assert f(2)==5\n'
        test.write_bytes(oracle)
        result = self.run_rename(run_tests=['test_behavior.py'])
        self.assertTrue(result['verified'])
        self.assertEqual(self.source.read_text(), core.replace('f(x)', 'f(value)').replace('return x+', 'return value+'))
        self.assertEqual(test.read_bytes(), oracle)

    def test_nested_old_parameter_shadows_target_and_stays_unchanged(self):
        core = ('def f(x):\n    def inner(x):\n        value=10\n        return x+value\n'
                '    return x+inner(2)\n')
        self.source.write_text(core)
        test = self.root / 'test_behavior.py'
        oracle = b'from m import f\ndef test_behavior(): assert f(2)==14\n'
        test.write_bytes(oracle)
        result = self.run_rename(run_tests=['test_behavior.py'])
        self.assertTrue(result['verified'])
        self.assertIn('def inner(x):\n        value=10\n        return x+value\n', self.source.read_text())
        self.assertEqual(test.read_bytes(), oracle)


if __name__ == '__main__':
    unittest.main()
