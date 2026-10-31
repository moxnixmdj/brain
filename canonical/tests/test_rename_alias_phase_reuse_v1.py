"""Execute the real rename adapter; distinguish preconditions from residuals."""
import contextlib
import io
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from canonical.tests.test_python_refactor_rename_symbol_v1 import _build, _run, _bytes


class RenameAliasPhaseReuseTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory(prefix='rename-alias-phase-')
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)

    def run_rename(self,**kwargs):
        with contextlib.redirect_stdout(io.StringIO()):
            return _run(self.root,qualname='top',new_symbol='apex',**kwargs)

    def test_preserved_alias_to_new_name_passes_real_pytest(self):
        src=_build(self.root,core='def top(x): return x+1\n',packages={
            'use/caller.py':'from pkg.core import top as apex\n\ndef call(): return apex(2)\n',
        })
        tests=src/'tests';tests.mkdir()
        (tests/'test_behavior.py').write_text(
            'from use.caller import call\n\ndef test_behavior():\n    assert call()==3\n')
        before_tests=(tests/'test_behavior.py').read_bytes()
        result=self.run_rename(run_tests=['tests/test_behavior.py'])
        self.assertTrue(result['verified'])
        self.assertTrue(result['complete'])
        self.assertEqual(result['gate'],'PASS')
        self.assertEqual((src/'use/caller.py').read_text(),
            'from pkg.core import apex as apex\n\ndef call(): return apex(2)\n')
        self.assertEqual((tests/'test_behavior.py').read_bytes(),before_tests)

    def test_genuine_preexisting_import_alias_collision_refuses_before_writes(self):
        src=_build(self.root,core='def top(x): return x+1\ndef other(x): return x-1\n',packages={
            'use/caller.py':'from pkg.core import top, other as apex\n\ndef call(): return top(2)+apex(2)\n',
        })
        before=_bytes(src)
        with self.assertRaisesRegex(SystemExit,'NEW_NAME_COLLIDES:apex \\(import alias\\)'):
            self.run_rename()
        self.assertEqual(_bytes(src),before)
        self.assertFalse((self.root/'_out/refactor.json').exists())

    def test_red_pytest_restores_alias_and_definition_bytes(self):
        src=_build(self.root,core='def top(x): return x+1\n',packages={
            'use/caller.py':'from pkg.core import top as apex\n\ndef call(): return apex(2)\n',
            'tests/test_red.py':'def test_red():\n    assert 1==2\n',
        })
        before=_bytes(src)
        with self.assertRaisesRegex(SystemExit,'TESTS_RED_AFTER_EDIT'):
            self.run_rename(run_tests=['tests/test_red.py'])
        self.assertEqual(_bytes(src),before)
        self.assertFalse((self.root/'_out/refactor.json').exists())

    def test_nonmatching_alias_is_preserved_without_claiming_test_verification(self):
        src=_build(self.root,core='def top(x): return x+1\n',packages={
            'use/caller.py':'from pkg.core import top as stable\n\ndef call(): return stable(2)\n',
        })
        result=self.run_rename()
        self.assertEqual((src/'use/caller.py').read_text(),
            'from pkg.core import apex as stable\n\ndef call(): return stable(2)\n')
        self.assertTrue(result['complete'])
        self.assertFalse(result['verified'])
        self.assertEqual(result['gate'],'PASS_BLIND')


if __name__=='__main__': unittest.main()
