"""Reuse the existing delivery lane; report authority never authorizes source writes."""
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import subprocess
import sys
import unittest

from canonical.runtime import live_brain_route_admission_v1 as door
from canonical.runtime import write_authority_v1 as authority
from canonical.runtime.bound_capabilities import python_repair_apply_verified_v1 as apply

ROOT = Path(__file__).resolve().parents[2]
BROKEN = 'def f(x):\n    return x < 3\n'
FIXED = 'def f(x):\n    return x <= 3\n'
TEST = 'from m import f\nassert f(3)\nassert f(2)\nassert not f(4)\n'
CID = 'python.software.repair.apply.verified.v1'


class VerifiedRepairDeliveryReuseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(dir=ROOT / 'canonical/astra_runtime/tmp',
                                      prefix='verified_delivery_')
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.source = self.base / 'm.py'
        self.tests = self.base / 'test_all.py'
        self.source.write_text(BROKEN)
        self.tests.write_text(TEST)
        self.rel = self.base.relative_to(ROOT).as_posix()

    def args(self, output):
        return {'source_root': self.rel,
                'test_paths': [str(self.tests.relative_to(ROOT))],
                'test_argv': [sys.executable, str(self.tests)],
                'output_path': str(output.relative_to(ROOT)), 'timeout_s': 30}

    def fresh_test(self):
        return subprocess.run([sys.executable, '-B', 'test_all.py'],
                              cwd=self.base, capture_output=True, timeout=30)

    def live(self, report):
        goal = (f'Repair the python source {self.rel}/m.py so the unit tests in '
                f'{self.rel}/test_all.py pass, apply the fix in place, '
                f'and save the repair report to {report.relative_to(ROOT)}.')
        return door.solve({'task_id': self.base.name, 'goal': goal})

    def test_public_delivery_persists_repair_and_passes_fresh_unchanged_tests(self):
        self.assertNotEqual(self.fresh_test().returncode, 0)
        result = self.live(self.base / 'report.json')
        self.assertTrue(result['pass'], result.get('status'))
        self.assertIs(result['executed'], True)
        self.assertEqual(result['compiled_capability_id'], CID)
        report = json.loads((self.base / 'report.json').read_text())
        self.assertTrue(report['applied'])
        self.assertEqual(report['pre_apply_test_returncode'], 1)
        self.assertEqual(report['post_apply_test_returncode'], 0)
        self.assertEqual(self.source.read_text(), FIXED)
        self.assertEqual(self.tests.read_text(), TEST)
        self.assertEqual(self.fresh_test().returncode, 0)
        # Local execution is not an independent raw-request acceptance receipt.
        self.assertFalse(result['semantic_acceptance_complete'])

    def test_public_second_application_does_not_claim_another_source_change(self):
        self.live(self.base / 'first.json')
        before = self.source.read_bytes()
        result = self.live(self.base / 'second.json')
        # This request explicitly promises a source change. The adapter can
        # truthfully say already-correct, but the door must not claim an edit.
        self.assertFalse(result['pass'], result.get('status'))
        self.assertEqual(result['status'], 'FAIL_CLOSED__PROMISED_SOURCE_CHANGE_NOT_APPLIED')
        report = json.loads((self.base / 'second.json').read_text())
        self.assertEqual(report['status'], 'PASS__STATED_TEST_ALREADY_PASSES_NOTHING_TO_REPAIR')
        self.assertFalse(report['applied'])
        self.assertEqual(report['files_written'], [])
        self.assertEqual(self.source.read_bytes(), before)
        self.assertEqual(self.fresh_test().returncode, 0)

    def test_report_cannot_replace_source_or_test_even_when_suite_already_passes(self):
        self.source.write_text(FIXED)
        for target in (self.source, self.tests):
            for hardlink in (False, True):
                with self.subTest(target=target.name, hardlink=hardlink):
                    report = self.base / 'alias.json' if hardlink else target
                    if hardlink:
                        report.unlink(missing_ok=True)
                        report.hardlink_to(target)
                    with self.assertRaisesRegex(authority.WriteAuthorityViolation,
                                                'REPORT_OVERWRITES_INPUT'):
                        apply.run(self.args(report), ROOT)
                    self.assertEqual(self.source.read_text(), FIXED)
                    self.assertEqual(self.tests.read_text(), TEST)

    def test_public_report_alias_refuses_without_corrupting_source(self):
        report = self.base / 'report.json'
        report.hardlink_to(self.source)
        result = self.live(report)
        self.assertFalse(result['pass'], result.get('status'))
        self.assertEqual(self.source.read_text(), BROKEN)
        self.assertEqual(self.tests.read_text(), TEST)
        self.assertNotEqual(self.fresh_test().returncode, 0)

    def test_search_intermediate_report_cannot_replace_source(self):
        # The inner search writes a second, derived report before applying a patch.
        intermediate = self.base / '.apply_repair_report.json'
        intermediate.hardlink_to(self.source)
        with self.assertRaisesRegex(authority.WriteAuthorityViolation,
                                    'REPORT_OVERWRITES_INPUT'):
            apply.run(self.args(self.base / 'report.json'), ROOT)
        self.assertEqual(self.source.read_text(), BROKEN)
        self.assertEqual(self.tests.read_text(), TEST)

    def test_separate_existing_report_hardlink_remains_allowed(self):
        original = self.base / 'old.json'
        original.write_text('{}')
        report = self.base / 'report.json'
        report.hardlink_to(original)
        result = apply.run(self.args(report), ROOT)
        self.assertTrue(result['applied'], result.get('status'))
        self.assertEqual(self.source.read_text(), FIXED)
        self.assertEqual(self.fresh_test().returncode, 0)

    def test_unrepairable_public_request_does_not_deliver_a_fake_fix(self):
        broken = 'def f(x):\n    raise RuntimeError("not a bounded operator repair")\n'
        self.source.write_text(broken)
        result = self.live(self.base / 'report.json')
        self.assertFalse(result['pass'], result.get('status'))
        report = json.loads((self.base / 'report.json').read_text())
        self.assertFalse(report['applied'])
        self.assertEqual(report['files_written'], [])
        self.assertEqual(self.source.read_text(), broken)
        self.assertEqual(self.tests.read_text(), TEST)
        self.assertNotEqual(self.fresh_test().returncode, 0)


if __name__ == '__main__':
    unittest.main()
