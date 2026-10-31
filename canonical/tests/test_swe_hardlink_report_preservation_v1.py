"""Different names/extensions must not hide report-to-source inode aliases."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from canonical.runtime import write_authority_v1 as authority
from canonical.runtime import live_brain_route_admission_v1 as door
from canonical.runtime import live_integrated_brain_v1 as live
from canonical.runtime.bound_capabilities import python_source_symbol_index as index

ROOT = Path(__file__).resolve().parents[2]
CID = 'python.source.symbols.index.ast'


class HardlinkReportPreservation(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(dir=ROOT/'canonical/astra_runtime/tmp', prefix='hardlink_report_')
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.source = self.base/'mod.py'
        self.body = 'def add(a,b): return a+b\n'
        self.source.write_text(self.body)
        self.report = self.base/'report.json'
        self.report.hardlink_to(self.source)

    def test_unlisted_explicit_source_argument_cannot_hide_alias(self):
        for slot, value in [('module', str(self.source)), ('changed_paths', [str(self.source)])]:
            with self.subTest(slot=slot):
                reason = authority.violation(ROOT, {slot:value, 'output_path':str(self.report)}, CID)
                self.assertIsNotNone(reason)
                self.assertIn('OUTPUT_OVERWRITES_A_STATED_SOURCE', reason)
        self.assertEqual(self.source.read_text(), self.body)

    def test_source_directory_protects_different_extension_hardlink(self):
        reason = authority.violation(ROOT, {'source_root':str(self.base), 'output_path':str(self.report)}, CID)
        self.assertIsNotNone(reason)
        self.assertIn('read_as=source_root', reason)

    def test_local_adapter_refuses_before_corrupting_source(self):
        entry = live.load_verified_registry()[CID]
        action = {'type':'invoke_capability','args':{'capability_id':CID,
                  'source_root':str(self.base.relative_to(ROOT)),
                  'output_path':str(self.report.relative_to(ROOT))}}
        with self.assertRaisesRegex(door.LocalExecutionFailure, 'OUTPUT_OVERWRITES_A_STATED_SOURCE'):
            door.run_adapter_locally(entry, action)
        self.assertEqual(self.source.read_text(), self.body)

    def test_direct_index_protects_file_and_directory_inputs(self):
        for source in (self.source, self.base):
            with self.subTest(source=source):
                with self.assertRaisesRegex(authority.WriteAuthorityViolation, 'REPORT_OVERWRITES_INPUT'):
                    index.run({'source_root':str(source), 'output_path':str(self.report)}, ROOT)
                self.assertEqual(self.source.read_text(), self.body)

    def test_ordinary_existing_report_does_not_trigger_directory_alias_scan(self):
        self.report.unlink();self.report.write_text('{}')
        # The guard's own helper, not pathlib or a test harness replacement.
        with patch.object(authority, '_directory_source_files', side_effect=AssertionError('unnecessary scan')):
            self.assertIsNone(authority.violation(ROOT, {'source_root':str(self.base),
                                                       'output_path':str(self.report)}, CID))

    def test_distinct_hardlinked_reports_and_transformer_remain_allowed(self):
        self.report.unlink();original=self.base/'original.json';original.write_text('{}')
        self.report.hardlink_to(original)
        self.assertIsNone(authority.violation(ROOT, {'source_root':str(self.base),
                                                    'output_path':str(self.report)}, CID))
        self.assertIsNone(authority.violation(ROOT, {'source_path':str(self.source),
                                                    'output_path':str(self.source)},
                                             'python.refactor.rename_parameter.v1'))

    def test_index_with_separate_existing_report_remains_repeatable(self):
        self.report.unlink();self.report.write_text('{}')
        args={'source_root':str(self.base), 'output_path':str(self.report)}
        first=index.run(args,ROOT);second=index.run(args,ROOT)
        self.assertEqual(first['output_sha256'],second['output_sha256'])
        self.assertEqual(json.loads(self.report.read_text())['totals']['files'],1)
        self.assertEqual(self.source.read_text(),self.body)


if __name__ == '__main__':
    unittest.main()
