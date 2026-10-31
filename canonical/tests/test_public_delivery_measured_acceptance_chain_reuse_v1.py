"""Compose existing public delivery and snapshot-bound acceptance without a new engine.

Operator-authored frozen task, not an independent benchmark or general autonomy claim.
"""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from canonical.runtime import live_brain_route_admission_v1 as door
from canonical.runtime import python_request_acceptance_union_v1 as union
from canonical.runtime.bound_capabilities import python_repository_acceptance_measurement_v1 as measurement

ROOT = Path(__file__).resolve().parents[2]
FILES = {
    'rules/__init__.py': '',
    'rules/age.py': 'def eligible(age):\n    return age > 18\n',
    'rules/funds.py': 'def funded(cents):\n    return cents > 0\n',
    'service/__init__.py': '',
    'service/api.py': 'from rules.age import eligible\nfrom rules.funds import funded\ndef checkout(age, cents):\n    return eligible(age) and funded(cents)\n',
    'tests/test_checkout.py': '''import unittest
from service.api import checkout
class CheckoutTests(unittest.TestCase):
    def test_policy_matrix(self):
        for age in (0, 17, 18, 19, 100):
            for cents in (-100, -1, 0, 1, 100):
                with self.subTest(age=age, cents=cents):
                    self.assertEqual(checkout(age, cents), age >= 18 and cents >= 0)
''',
    'settings.json': '{"preserve": "user configuration"}\n',
}
# Fixed before requesting delivery; structural checks supplement, not replace, behavior.
CONTRACT = ('tests_pass must be true. '
            'File "rules/age.py" must contain "return age >= 18". '
            'File "rules/funds.py" must contain "return cents >= 0". '
            'Must not modify "tests/test_checkout.py". '
            'Must not modify "service/api.py". '
            'Must not modify "settings.json".')


class PublicDeliveryMeasuredAcceptanceChainTests(unittest.TestCase):
    def test_public_two_module_delivery_then_measured_union_and_negative_controls(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'canonical/astra_runtime/tmp',
                                         prefix='public_acceptance_chain_') as directory:
            base = Path(directory)
            candidate = base/'candidate'
            candidate.mkdir()
            for name, text in FILES.items():
                path = candidate/name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text)
            baseline = base/'baseline'
            shutil.copytree(candidate, baseline)
            _, baseline_sha = measurement._tree_manifest(baseline, max_files=100, max_bytes=1_000_000)
            native = [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'tests']
            before = subprocess.run(native, cwd=candidate, capture_output=True, timeout=10)
            self.assertNotEqual(before.returncode, 0)
            relative = candidate.relative_to(ROOT).as_posix()
            report = (base/'delivery.json').relative_to(ROOT).as_posix()
            goal = (f'Repair the python source root {relative} so the unit tests in '
                    f'{relative}/tests/test_checkout.py pass, apply the fix in place, '
                    f'and save the repair report to {report}.')
            delivered = door.solve({'task_id':base.name, 'goal':goal})
            self.assertTrue(delivered['pass'], delivered.get('status'))
            self.assertIs(delivered['executed'], True)
            self.assertEqual(delivered['compiled_capability_id'], 'python.software.repair.apply.verified.v1')
            # Public delivery alone must not silently grant semantic acceptance.
            self.assertFalse(delivered['semantic_acceptance_complete'])
            receipt = json.loads((base/'delivery.json').read_text())
            self.assertTrue(receipt['applied'])
            self.assertEqual(len(receipt['files_written']), 2)
            for name, original in FILES.items():
                if name not in {'rules/age.py','rules/funds.py'}:
                    self.assertEqual((candidate/name).read_text(), original)
            fresh = subprocess.run(native, cwd=candidate, capture_output=True, timeout=10)
            self.assertEqual(fresh.returncode, 0, fresh.stderr)
            manifest, delivered_sha = measurement._tree_manifest(candidate, max_files=100, max_bytes=1_000_000)
            measured = measurement.run({'source_root':'candidate',
                                       'test_paths':['tests/test_checkout.py'],
                                       'test_argv':native, 'timeout_s':10,
                                       'output_path':'measurement.json'}, base)
            self.assertTrue(measured['measurements']['tests_pass'], measured)
            self.assertEqual(measured['subject']['snapshot_sha256'], delivered_sha)

            def accept(task):
                return union.evaluate_union(task, measurement_receipt_path='measurement.json',
                                            receipt_root=base, baseline_root=baseline,
                                            candidate_root=candidate,
                                            expected_baseline_snapshot_sha256=baseline_sha)

            accepted = accept(CONTRACT)
            self.assertTrue(accepted['candidate_accepted'], accepted)
            self.assertTrue(accepted['acceptance_stop_authorized'])
            self.assertEqual(accepted['required_obligation_count'], accepted['passed_obligation_count'])
            self.assertFalse(accepted['unbound_obligation_ids'])
            with self.subTest(control='passing tests cannot erase false source requirement'):
                rejected = accept(CONTRACT+' File "rules/age.py" must contain "impossible_marker".')
                self.assertFalse(rejected['candidate_accepted'])
                self.assertTrue(rejected['failed_obligation_ids'])
            with self.subTest(control='passing tests cannot erase unsupported requirement'):
                rejected = accept(CONTRACT+' Preserve compatibility with historic clients.')
                self.assertFalse(rejected['candidate_accepted'])
                self.assertTrue(rejected['unbound_obligation_ids'])
            with self.subTest(control='post-measurement mutation invalidates receipt'):
                path = candidate/'rules/age.py'
                correct = path.read_bytes()
                path.write_text(FILES['rules/age.py'])
                rejected = accept(CONTRACT)
                self.assertFalse(rejected['candidate_accepted'])
                self.assertEqual(rejected['status'], 'FAIL_CLOSED')
                self.assertIn('CANDIDATE_SNAPSHOT_MISMATCH', str(rejected['errors']))
                path.write_bytes(correct)
            final_manifest, final_sha = measurement._tree_manifest(candidate, max_files=100, max_bytes=1_000_000)
            self.assertEqual((final_manifest, final_sha), (manifest, delivered_sha))
            self.assertTrue(accept(CONTRACT)['candidate_accepted'])
            _, restored_baseline_sha = measurement._tree_manifest(baseline, max_files=100, max_bytes=1_000_000)
            self.assertEqual(restored_baseline_sha, baseline_sha)
