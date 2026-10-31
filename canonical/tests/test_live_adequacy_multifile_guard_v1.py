"""A live adequacy result must not collapse different files' line identities."""
from __future__ import annotations

import pathlib
import tempfile
import time
import unittest
from unittest.mock import patch

from canonical.runtime import live_brain_route_admission_v1 as door
from canonical.runtime import live_integrated_brain_v1

ROOT = pathlib.Path(__file__).resolve().parents[2]
CID = 'python.source.test_adequacy.v1'


class MultiFileAdequacyGuardTests(unittest.TestCase):
    def setUp(self):
        work = ROOT / 'canonical/astra_runtime/tmp'
        work.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(prefix='adequacy_multifile_', dir=work)
        self.addCleanup(self.tmp.cleanup)
        self.base = pathlib.Path(self.tmp.name)
        self.app = self.base / 'app'
        self.tests = self.base / 'tests'
        self.app.mkdir()
        self.tests.mkdir()
        (self.app / '__init__.py').write_text('')
        (self.tests / '__init__.py').write_text('')
        (self.app / 'one.py').write_text('def value():\n    return 1\n')
        (self.app / 'two.py').write_text('def uncovered():\n    return 999\n')
        self.marker = self.base / 'test_imported.txt'
        (self.tests / 'test_one.py').write_text(
            'import unittest\nfrom pathlib import Path\n'
            f'Path({str(self.marker)!r}).write_text("ran")\n'
            'from app.one import value\n'
            'class T(unittest.TestCase):\n'
            '    def test_value(self): self.assertEqual(value(), 1)\n')
        self.out = self.base / 'report.json'
        self.entry = dict(live_integrated_brain_v1.load_verified_registry()[CID])
        self.args = {'capability_id': CID, 'source_root': self.app.relative_to(ROOT).as_posix(),
                     'output_path': self.out.relative_to(ROOT).as_posix()}
        self.action = {'type': 'invoke_capability', 'args': self.args,
                       'expect': {'type': 'field_equals', 'field': 'output_verified', 'value': True}}

    def test_multifile_refuses_before_tests_or_report(self):
        # Both functions use lines 1 and 2. The old adapter unions line numbers
        # and calls the unimported module covered, reporting answer=yes.
        with self.assertRaises(door.LocalExecutionFailure) as exc:
            door.run_adapter_locally(self.entry, self.action)
        self.assertIn('MULTIFILE_ADEQUACY_REQUIRES_FILE_AWARE_TRACING', str(exc.exception))
        self.assertFalse(self.marker.exists())
        self.assertFalse(self.out.exists())

    def test_direct_pinned_adapter_still_has_the_known_false_positive(self):
        from canonical.runtime.bound_capabilities import python_source_test_adequacy as pinned
        result = pinned.run(self.args, ROOT)
        self.assertEqual(result['answer'], 'yes')
        self.assertEqual(result['tests_run'], 1)
        self.assertTrue(self.marker.exists())

    def test_binding_the_tests_directory_still_checks_both_subject_files(self):
        args = dict(self.args, source_root=self.tests.relative_to(ROOT).as_posix())
        action = dict(self.action, args=args)
        with self.assertRaises(door.LocalExecutionFailure) as exc:
            door.run_adapter_locally(self.entry, action)
        self.assertIn('MULTIFILE_ADEQUACY_REQUIRES_FILE_AWARE_TRACING', str(exc.exception))
        self.assertFalse(self.marker.exists())
        self.assertFalse(self.out.exists())

    def test_explicit_test_root_does_not_bypass_guard(self):
        args = dict(self.args, test_root=self.tests.relative_to(ROOT).as_posix())
        with self.assertRaises(door.LocalExecutionFailure) as exc:
            door.run_adapter_locally(self.entry, dict(self.action, args=args))
        self.assertIn('MULTIFILE_ADEQUACY_REQUIRES_FILE_AWARE_TRACING', str(exc.exception))
        self.assertFalse(self.marker.exists())

    def test_unrelated_python_file_without_functions_does_not_block_single_target(self):
        (self.app / 'two.py').write_text('VALUE = 999\n')
        result = door.run_adapter_locally(self.entry, self.action)
        self.assertEqual(result['answer'], 'yes')
        self.assertEqual(result['tests_run'], 1)
        self.assertTrue(self.marker.exists())
        self.assertTrue(self.out.is_file())

    def test_live_execution_does_not_retry_after_the_guard(self):
        entry = dict(self.entry, action_template=self.action)
        compiled = {'selected_capability': CID, 'inputs': {},
                    'target_effects': ['software.task.completed']}
        called = []
        def controller(*args):
            called.append(True)
            return None, 'CONTROL_PLAN_INVALID'
        with patch.object(door.live_integrated_brain_v1, 'drive_controller', controller):
            result = door._execute('ADEQUACY_GUARD', 'Check the tests for the project.',
                                   compiled, {CID: entry}, time.perf_counter_ns())
        self.assertFalse(result['pass'])
        self.assertIn('MULTIFILE_ADEQUACY_REQUIRES_FILE_AWARE_TRACING', result['reason'])
        self.assertFalse(called)
        self.assertFalse(self.marker.exists())
        self.assertFalse(self.out.exists())


if __name__ == '__main__':
    unittest.main()
