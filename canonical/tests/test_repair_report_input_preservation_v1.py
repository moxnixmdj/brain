"""Filesystem oracles for JSON report roles, distinct from source-edit authority."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from canonical.runtime import write_authority_v1 as authority
from canonical.runtime.bound_capabilities import python_test_guided_patch_search_v1 as search
from canonical.runtime.bound_capabilities import python_software_repair_loop_v1 as repair


class ReportInputPreservation(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(prefix='brain_report_inputs_')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'calc.py').write_text('def add(a,b):\n    return a-b\n')
        (self.root / 'test_calc.py').write_text(
            'import calc\ndef test_add():\n    assert calc.add(2,3)==5\n')
        self.before = {p.name: p.read_bytes() for p in self.root.iterdir()}

    def test_patch_search_refuses_aliases_before_tests(self):
        for target in ('calc.py', 'test_calc.py', 'alias.py', 'link.json'):
            with self.subTest(target=target):
                if target == 'alias.py':
                    (self.root / target).symlink_to(self.root / 'calc.py')
                if target == 'link.json':
                    (self.root / target).hardlink_to(self.root / 'calc.py')
                with patch.object(search, '_run_tests') as execute:
                    with self.assertRaisesRegex(authority.WriteAuthorityViolation,
                                                'REPORT_OVERWRITES_INPUT'):
                        search.run({'source_path': 'calc.py', 'test_paths': ['test_calc.py'],
                                    'output_path': target}, self.root)
                    execute.assert_not_called()
                for name, raw in self.before.items():
                    self.assertEqual((self.root / name).read_bytes(), raw)

    def test_multi_edit_loop_refuses_discovered_source_before_tests(self):
        for target in ('calc.py', 'test_calc.py'):
            with self.subTest(target=target):
                with patch.object(repair, '_test') as execute:
                    with self.assertRaisesRegex(authority.WriteAuthorityViolation,
                                                'REPORT_OVERWRITES_INPUT'):
                        repair.run({'test_paths': ['test_calc.py'],
                                    'output_path': target}, self.root)
                    execute.assert_not_called()
                for name, raw in self.before.items():
                    self.assertEqual((self.root / name).read_bytes(), raw)

    def test_distinct_existing_report_is_allowed(self):
        report = self.root / 'report.json'
        report.write_text('{}')
        authority.check_report(self.root, report, [self.root / 'calc.py'])
        self.assertEqual(report.read_text(), '{}')

    def test_legitimate_transformer_authority_is_unchanged(self):
        self.assertIsNone(authority.violation(self.root,
            {'source_path': 'calc.py', 'output_path': 'calc.py'},
            'python.refactor.rename_parameter.v1'))

    def test_real_repair_with_separate_report_restores_source(self):
        result = search.run({'source_path': 'calc.py', 'test_paths': ['test_calc.py'],
                             'output_path': 'report.json', 'max_candidates': 10}, self.root)
        self.assertTrue(result['pass'])
        self.assertIn('unified_diff', result)
        self.assertTrue((self.root / 'report.json').is_file())
        for name, raw in self.before.items():
            self.assertEqual((self.root / name).read_bytes(), raw)
