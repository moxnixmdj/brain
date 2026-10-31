"""Prove the existing extractor's discovered oracles actually run and fail closed."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from canonical.tests.test_python_refactor_extract_function_v1 import _build, _run


class ExtractionDiscoveryReuseTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory(prefix='extract-discovery-reuse-')
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)

    def test_existing_discovery_executes_three_behavioral_oracles(self):
        oracle='from pathlib import Path\nfrom pkg.core import demo\n'
        for name,arg,expected in [('odd',3,12),('even',4,2),('other',5,18)]:
            oracle+=f'\ndef test_{name}():\n    assert demo({arg})=={expected}\n'
            oracle+=f'    with Path("executed.txt").open("a") as f: f.write("{name}\\n")\n'
        _build(self.root,extra={'tests/test_behavior.py':oracle})
        result,artifact=_run(self.root,run_tests=[])
        self.assertTrue(result['verified'])
        self.assertEqual(sorted((self.root/'executed.txt').read_text().splitlines()),['even','odd','other'])
        self.assertEqual(artifact['verification']['run_tests'],[str(self.root/'tests/test_behavior.py')])
        self.assertEqual(artifact['verification']['pytest_rc'],0)
        self.assertEqual((self.root/'tests/test_behavior.py').read_text(),oracle)
        self.assertIn('score = odd_score(base)',(self.root/'pkg/core.py').read_text())

    def refusal_restores_source(self,oracle):
        _build(self.root,extra={'tests/test_oracle.py':oracle})
        source=self.root/'pkg/core.py'
        before=source.read_bytes()
        with self.assertRaisesRegex(SystemExit,'TESTS_RED_AFTER_EDIT'):
            _run(self.root,run_tests=[])
        self.assertEqual(source.read_bytes(),before)
        self.assertEqual((self.root/'tests/test_oracle.py').read_text(),oracle)
        self.assertFalse((self.root/'_out/extract.json').exists())

    def test_discovered_red_oracle_runs_and_rolls_back(self):
        self.refusal_restores_source('from pathlib import Path\nfrom pkg.core import demo\n'
            'def test_wrong():\n    Path("red-executed.txt").write_text("ran")\n    assert demo(3)==999\n')
        self.assertEqual((self.root/'red-executed.txt').read_text(),'ran')

    def test_all_skipped_discovered_suite_cannot_verify_an_edit(self):
        self.refusal_restores_source('import unittest\nclass TestSkipped(unittest.TestCase):\n'
            '    @unittest.skip("no behavioral oracle")\n    def test_skipped(self): pass\n')

    def test_discovered_empty_test_file_cannot_verify_an_edit(self):
        self.refusal_restores_source('def helper(): return 42\n')

    def test_collection_exit_zero_cannot_verify_an_edit(self):
        self.refusal_restores_source('raise SystemExit(0)\n')

    def test_no_corpus_keeps_verification_false(self):
        _build(self.root)
        result,artifact=_run(self.root,run_tests=[])
        self.assertFalse(result['verified'])
        self.assertEqual(artifact['verification']['run_tests'],[])
        self.assertNotIn('pytest_rc',artifact['verification'])
        self.assertTrue(result['output_verified'])


if __name__=='__main__': unittest.main()
