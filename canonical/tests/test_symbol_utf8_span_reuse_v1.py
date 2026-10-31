"""Execute UTF-8 binding-aware symbol refactors against real pytest."""
import contextlib
import io
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from canonical.runtime.bound_capabilities import python_refactor_rename_symbol as rename


class SymbolUtf8SpanTests(unittest.TestCase):
    def check_rename(self, core, caller, expected_core, expected_caller,
                     old='top', new='apex', files=2):
        with TemporaryDirectory(prefix='symbol-utf8-span-') as tmp:
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
            with contextlib.redirect_stdout(io.StringIO()):
                result = rename.run(dict(source_root='src', module='pkg/core.py', qualname=old,
                                         new_symbol=new, output_path='report.json',
                                         run_tests=['tests/test_behavior.py']), root)
            self.assertTrue(result['verified'])
            self.assertTrue(result['complete'])
            self.assertEqual(len(result['files_edited']), files)
            self.assertEqual(definition.read_bytes(), expected_core.encode('utf-8'))
            self.assertEqual(consumer.read_bytes(), expected_caller.encode('utf-8'))
            self.assertEqual(definition.stat().st_mode & 0o777, 0o640)
            self.assertEqual(test.read_bytes(), test_bytes)

    def test_multibyte_prefix_before_function_reference(self):
        self.check_rename('def top(x): return x+1\n',
                          'from pkg.core import top\ndef call(): label="🙂é top"; return top(2) # top stays\n',
                          'def apex(x): return x+1\n',
                          'from pkg.core import apex\ndef call(): label="🙂é top"; return apex(2) # top stays\n')

    def test_import_column_after_unicode_prefix(self):
        self.check_rename('def top(x): return x+1\n',
                          'label="雪"; from pkg.core import top\ndef call(): return top(2)\n',
                          'def apex(x): return x+1\n',
                          'label="雪"; from pkg.core import apex\ndef call(): return apex(2)\n')

    def test_unicode_identifier_boundaries_remain_guarded(self):
        for text, column, side in [('αtop', 2, 'left'), ('topα', 0, 'right')]:
            with self.subTest(side=side):
                with self.assertRaisesRegex(SystemExit, 'SPAN_INTEGRITY:' + side + '_boundary'):
                    rename._splice_file(Path('m.py'), text.encode('utf-8'),
                                        [(1, column, 'top')], 'apex')

    def test_unicode_symbol_and_replacement(self):
        self.check_rename('def café(x): return x+1\n',
                          'from pkg.core import café\ndef call(): return café(2)\n',
                          'def résultat(x): return x+1\n',
                          'from pkg.core import résultat\ndef call(): return résultat(2)\n',
                          old='café', new='résultat')

    def test_unicode_module_alias_width(self):
        self.check_rename('def top(x): return x+1\n',
                          'import pkg.core as café\ndef call(): label="🙂"; return café.top(2)\n',
                          'def apex(x): return x+1\n',
                          'import pkg.core as café\ndef call(): label="🙂"; return café.apex(2)\n')

    def test_crlf_and_no_final_newline(self):
        self.check_rename('# é\r\ndef top(x): return x+1',
                          'from pkg.core import top\r\ndef call(): label="雪"; return top(2)',
                          '# é\r\ndef apex(x): return x+1',
                          'from pkg.core import apex\r\ndef call(): label="雪"; return apex(2)')

    def test_unicode_separator_inside_literal(self):
        self.check_rename('label="a\u2028b"\ndef top(x): return x+1\n',
                          'from pkg.core import top\nlabel="a\u2028b"\ndef call(): return top(2)\n',
                          'label="a\u2028b"\ndef apex(x): return x+1\n',
                          'from pkg.core import apex\nlabel="a\u2028b"\ndef call(): return apex(2)\n')

    def test_unicode_class_receiver_width(self):
        core = ('class Échelle:\n    @staticmethod\n    def top(x): return x+1\n'
                '    def use(self): label="🙂"; return Échelle.top(2)\n')
        caller = 'from pkg.core import Échelle\ndef call(): return Échelle().use()\n'
        self.check_rename(core, caller, core.replace('def top(', 'def apex(').replace('.top(', '.apex('),
                          caller, old='Échelle.top', files=1)

    def test_normalized_spelling_refuses_without_publication(self):
        with TemporaryDirectory(prefix='symbol-normalized-refusal-') as tmp:
            root = Path(tmp)
            src = root / 'src'
            src.mkdir()
            definition = src / 'm.py'
            original = 'def ｔop(x): return x+1\n'.encode('utf-8')
            definition.write_bytes(original)
            with self.assertRaisesRegex(SystemExit, 'SPAN_INTEGRITY'):
                rename.run(dict(source_root='src', module='m.py', qualname='top',
                                new_symbol='apex', output_path='report.json'), root)
            self.assertEqual(definition.read_bytes(), original)
            self.assertFalse((root / 'report.json').exists())


if __name__ == '__main__':
    unittest.main()
