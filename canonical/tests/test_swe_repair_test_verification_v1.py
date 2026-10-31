"""Fresh filesystem checks for the live cross-file repair verification seam."""
from __future__ import annotations

import json
import os
import pathlib
import tempfile
import unittest

from canonical.runtime import live_brain_route_admission_v1 as door
from canonical.runtime import live_integrated_brain_v1

ROOT = pathlib.Path(__file__).resolve().parents[2]
CID = 'software.repair.choreograph.crossfile.v1'


class LiveRepairVerificationTests(unittest.TestCase):
    def setUp(self):
        work = ROOT / 'canonical/astra_runtime/tmp'
        work.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='repair_verify_', dir=work)
        self.addCleanup(self.temp.cleanup)
        self.base = pathlib.Path(self.temp.name)
        self.project = self.base / 'project'
        (self.project / 'app').mkdir(parents=True)
        (self.project / 'app/__init__.py').write_text('')
        self.source = self.project / 'app/mod.py'
        self.source.write_text('VALUE = 1\n')
        self.out = self.base / 'report.json'
        self.entry = dict(live_integrated_brain_v1.load_verified_registry()[CID])

    def _invoke(self, output=None):
        action = {
            'args': {'capability_id': CID,
                     'source_root': self.project.relative_to(ROOT).as_posix(),
                     'output_path': (output or self.out).relative_to(ROOT).as_posix()},
            'expect': {'type': 'field_equals', 'field': 'output_verified', 'value': True},
        }
        return door.run_adapter_locally(self.entry, action)

    def _tests(self, text):
        tests = self.project / 'tests'
        tests.mkdir(exist_ok=True)
        (tests / '__init__.py').write_text('')
        (tests / 'test_mod.py').write_text(text)

    def test_no_tests_never_dispatches_repair_or_publishes_verified_report(self):
        before = self.source.read_bytes()
        with self.assertRaises(door.LocalExecutionFailure):
            self._invoke()
        self.assertEqual(self.source.read_bytes(), before)
        self.assertFalse(self.out.exists())

    def test_all_skipped_tests_cannot_verify_repair(self):
        self._tests('import unittest\nclass T(unittest.TestCase):\n'
                    '    @unittest.skip("not implemented")\n'
                    '    def test_value(self): self.assertTrue(True)\n')
        with self.assertRaises(door.LocalExecutionFailure):
            self._invoke()
        self.assertFalse(self.out.exists())

    def test_real_failure_cannot_publish_a_verified_report(self):
        # The pinned adapter's unittest discovery sees no unittest cases here;
        # the existing suite runner actually executes this simple test function.
        self._tests('def test_value():\n    assert 1 == 2\n')
        with self.assertRaises(door.LocalExecutionFailure):
            self._invoke()
        self.assertFalse(self.out.exists())

    def test_noop_main_guard_is_not_a_passing_test(self):
        self._tests('if __name__ == "__main__":\n    pass\n')
        with self.assertRaises(door.LocalExecutionFailure):
            self._invoke()
        self.assertFalse(self.out.exists())

    def test_exit_zero_before_runner_finishes_is_not_success(self):
        self._tests('import os\ndef test_value():\n    os._exit(0)\n')
        with self.assertRaises(door.LocalExecutionFailure):
            self._invoke()
        self.assertFalse(self.out.exists())

    def test_failed_postcheck_reports_real_repair_side_effects_without_report(self):
        self.source.write_text('def query(conn, value):\n'
                               '    return conn.execute(f"SELECT * FROM t WHERE id={value}")\n')
        before = self.source.read_bytes()
        self._tests('def test_value():\n    assert False\n')
        with self.assertRaises(door.LocalAdapterExecutionFailure) as failure:
            self._invoke()
        self.assertIn('PROJECT_EFFECTS_MAY_REMAIN', str(failure.exception))
        self.assertNotEqual(self.source.read_bytes(), before)
        self.assertFalse(self.out.exists())

    def test_changed_test_file_rejects_report(self):
        replacement = ('import unittest\nclass T(unittest.TestCase):\n'
                       '    def test_value(self): self.assertTrue(True)\n')
        self.source.write_text('from pathlib import Path\n'
                               'p = Path(__file__).parents[1] / "tests/test_mod.py"\n'
                               f'p.write_text({replacement!r})\n')
        self._tests('import unittest\nclass T(unittest.TestCase):\n'
                    '    def test_value(self): self.assertTrue(True)\n# original\n')
        with self.assertRaises(door.LocalAdapterExecutionFailure) as failure:
            self._invoke()
        self.assertIn('TEST_FILES_CHANGED_DURING_REPAIR', str(failure.exception))
        self.assertFalse(self.out.exists())

    def test_report_hardlink_cannot_overwrite_source(self):
        self._tests('import unittest\nclass T(unittest.TestCase):\n'
                    '    def test_value(self): self.assertTrue(True)\n')
        os.link(self.source, self.out)
        before = self.source.read_bytes()
        with self.assertRaises(door.LocalExecutionFailure):
            self._invoke()
        self.assertEqual(self.source.read_bytes(), before)

    def test_real_passing_suite_publishes_requested_report(self):
        self._tests('import unittest\nfrom app.mod import VALUE\n'
                    'class T(unittest.TestCase):\n'
                    '    def test_value(self): self.assertEqual(VALUE, 1)\n')
        result = self._invoke()
        self.assertTrue(result['verified'])
        self.assertTrue(self.out.is_file())
        self.assertTrue(json.loads(self.out.read_text())['choreography_verified'])
        self.assertEqual(result['output_path'], self.out.relative_to(ROOT).as_posix())

    def test_report_cannot_overwrite_a_source_file(self):
        self._tests('import unittest\nclass T(unittest.TestCase):\n'
                    '    def test_value(self): self.assertEqual(1, 1)\n')
        before = self.source.read_bytes()
        with self.assertRaises(door.LocalExecutionFailure):
            self._invoke(self.source)
        self.assertEqual(self.source.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
