"""Real runner output belongs outside the deterministic transformation artifact."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from canonical.tests.test_python_refactor_extract_function_v1 import _build, _run, TEST


class ExtractionExecutionDiagnosticsTests(unittest.TestCase):
    def test_two_worlds_preserve_different_logs_but_identical_artifacts(self):
        with TemporaryDirectory(prefix='extract-diagnostics-') as directory:
            root=Path(directory)
            reports=[];sources=[];results=[]
            oracle=TEST+'\ndef test_diagnostic():\n    from pathlib import Path\n    print(Path("diagnostic.txt").read_text())\n'
            for name,log in [('one','run-one took 0.00s'),('two','run-two took 9.99s')]:
                work=root/name
                _build(work,extra={'tests/test_core.py':oracle,'diagnostic.txt':log})
                result,artifact=_run(work,run_tests=['-s','tests/test_core.py'])
                self.assertTrue(result['verified'])
                self.assertEqual(artifact['verification']['pytest_rc'],0)
                self.assertIn(log,result['execution_diagnostics']['stdout'])
                self.assertEqual(result['execution_diagnostics']['returncode'],0)
                self.assertNotIn('pytest_tail',artifact['verification'])
                self.assertEqual((work/'tests/test_core.py').read_text(),oracle)
                reports.append((work/'_out/extract.json').read_bytes())
                sources.append((work/'pkg/core.py').read_bytes())
                results.append(result)
            self.assertEqual(reports[0],reports[1])
            self.assertEqual(sources[0],sources[1])
            self.assertEqual(results[0]['output_sha256'],results[1]['output_sha256'])
            self.assertNotEqual(results[0]['execution_diagnostics']['stdout'],results[1]['execution_diagnostics']['stdout'])

    def test_no_test_run_has_no_execution_diagnostics(self):
        with TemporaryDirectory(prefix='extract-no-run-') as directory:
            work=Path(directory);_build(work)
            result,artifact=_run(work)
            self.assertFalse(result['verified'])
            self.assertIsNone(result['execution_diagnostics'])
            self.assertEqual(artifact['verification']['run_tests'],[])
            registry=json.loads((Path(__file__).resolve().parents[2]/
                'canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json').read_text())['capabilities']
            self.assertEqual(set(result),set(registry['python.refactor.extract_function.v1']['result_fields']))


if __name__=='__main__': unittest.main()
