"""Actual UTF-8 cross-file parameter edits, preserving all other bytes."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from canonical.runtime.bound_capabilities import python_refactor_rename_parameter as rename


class ParameterUtf8SpanTests(unittest.TestCase):
    def check_rename(self, core, caller, expected_core, expected_caller, old='x', new='value'):
        with TemporaryDirectory(prefix='parameter-utf8-span-') as tmp:
            root = Path(tmp)
            src = root / 'src'
            for package in ('pkg', 'use', 'tests'):
                (src / package).mkdir(parents=True)
                (src / package / '__init__.py').write_bytes(b'')
            definition = src / 'pkg/core.py'
            consumer = src / 'use/caller.py'
            definition.write_bytes(core.encode('utf-8'))
            consumer.write_bytes(caller.encode('utf-8'))
            definition.chmod(0o640)
            test = src / 'tests/test_behavior.py'
            test_bytes = b'from use.caller import call\ndef test_behavior():\n    assert call()==3\n'
            test.write_bytes(test_bytes)
            result = rename.run(dict(source_root='src', module='pkg/core.py', qualname='top',
                                     old_param=old, new_param=new, output_path='report.json',
                                     run_tests=['tests/test_behavior.py']), root)
            self.assertTrue(result['verified'])
            self.assertTrue(result['complete'])
            self.assertEqual(result['files_edited'], 2)
            self.assertEqual(definition.read_bytes(), expected_core.encode('utf-8'))
            self.assertEqual(consumer.read_bytes(), expected_caller.encode('utf-8'))
            self.assertEqual(definition.stat().st_mode & 0o777, 0o640)
            self.assertEqual(test.read_bytes(), test_bytes)

    def test_multibyte_prefix_before_keyword(self):
        self.check_rename('def top(x): return x+1\n',
                          'from pkg.core import top\ndef call(): label="🙂é"; return top(x=2)\n',
                          'def top(value): return value+1\n',
                          'from pkg.core import top\ndef call(): label="🙂é"; return top(value=2)\n')

    def test_multibyte_identifier_and_replacement(self):
        self.check_rename('def top(café):\n    label="雪"; return café+1\n',
                          'from pkg.core import top\ndef call(): return top(café=2)\n',
                          'def top(résultat):\n    label="雪"; return résultat+1\n',
                          'from pkg.core import top\ndef call(): return top(résultat=2)\n',
                          old='café', new='résultat')

    def test_multiple_spans_on_same_line_preserve_literal_and_comment(self):
        self.check_rename('def top(x): label="🙂 x"; return x+x-1 # x stays here\n',
                          'from pkg.core import top\ndef call(): return top(x=2)\n',
                          'def top(value): label="🙂 x"; return value+value-1 # x stays here\n',
                          'from pkg.core import top\ndef call(): return top(value=2)\n')

    def test_crlf_and_missing_final_newline_remain_byte_exact(self):
        self.check_rename('# é\r\ndef top(x):\r\n    label="🙂"; return x+1',
                          'from pkg.core import top\r\ndef call(): label="雪"; return top(x=2)',
                          '# é\r\ndef top(value):\r\n    label="🙂"; return value+1',
                          'from pkg.core import top\r\ndef call(): label="雪"; return top(value=2)')

    def test_unicode_separator_in_literal_is_not_a_source_newline(self):
        self.check_rename('label="a\u2028b"\ndef top(x): return x+1\n',
                          'from pkg.core import top\nlabel="a\u2028b"\ndef call(): return top(x=2)\n',
                          'label="a\u2028b"\ndef top(value): return value+1\n',
                          'from pkg.core import top\nlabel="a\u2028b"\ndef call(): return top(value=2)\n')


if __name__ == '__main__':
    unittest.main()
