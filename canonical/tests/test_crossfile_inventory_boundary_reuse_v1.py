"""Kernel availability is not cross-file work; the real planner remains usable."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from canonical.runtime.bound_capabilities import software_repair_crossfile_choreograph_v1 as inventory
from canonical.runtime.bound_capabilities import python_crossfile_edit_choreograph as planner

ROOT = Path(__file__).resolve().parents[2]


class CrossfileInventoryBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(prefix='brain_crossfile_inventory_')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.registry = self.root / 'canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json'
        self.registry.parent.mkdir(parents=True)
        self.registry.write_bytes((ROOT / self.registry.relative_to(self.root)).read_bytes())
        self.package = self.root / 'pkg'
        self.package.mkdir()
        self.definition = self.package / 'a.py'
        self.caller = self.package / 'b.py'
        self.definition.write_text('def helper(x):\n    return x+1\n')
        self.caller.write_text('from pkg.a import helper\ndef f():\n    return helper(2)\n')
        self.originals = {p: p.read_bytes() for p in (self.definition, self.caller)}

    def test_importable_kernels_do_not_certify_choreography(self):
        result = inventory.run({'source_root': 'pkg', 'output_path': 'inventory.json',
                                'verified': True, 'choreography_verified': True,
                                'execution_performed': True}, self.root)
        self.assertFalse(result['choreography_verified'])
        self.assertFalse(result['verified'])
        self.assertFalse(result['execution_performed'])
        report = json.loads((self.root / 'inventory.json').read_bytes())
        self.assertFalse(report['choreography_verified'])
        for path, raw in self.originals.items():
            self.assertEqual(path.read_bytes(), raw)

    def test_report_alias_cannot_overwrite_declared_source(self):
        alias = self.root / 'inventory.json'
        alias.hardlink_to(self.definition)
        with self.assertRaisesRegex(RuntimeError, '^REPORT_OVERWRITES_INPUT:'):
            inventory.run({'source_root': 'pkg', 'output_path': 'inventory.json'}, self.root)
        self.assertEqual(self.definition.read_bytes(), self.originals[self.definition])

    def test_unrelated_report_hardlinks_are_not_misclassified_as_source(self):
        report = self.root / 'other_report.json'
        report.write_text('{}')
        alias = self.root / 'inventory.json'
        alias.hardlink_to(report)
        result = inventory.run({'source_root': 'pkg', 'output_path': 'inventory.json'}, self.root)
        self.assertTrue(result['output_verified'])
        self.assertFalse(result['verified'])
        self.assertTrue(alias.samefile(report))
        for path, raw in self.originals.items():
            self.assertEqual(path.read_bytes(), raw)

    def test_existing_real_planner_produces_crossfile_sites_without_claiming_edits(self):
        result = planner.run({'source_root': '.', 'output_path': 'plan.json',
                              'edits': [{'op': 'rename_symbol', 'module': 'pkg/a.py',
                                         'name': 'helper', 'new_name': 'compute'}]}, self.root)
        self.assertEqual(result['planned_op_count'], 1)
        self.assertEqual(result['refused_op_count'], 0)
        report = json.loads((self.root / 'plan.json').read_bytes())
        self.assertEqual(set(report['affected_files']), {'pkg/a.py', 'pkg/b.py'})
        sites = report['plans'][0]['sites']
        self.assertTrue(any(s['kind'] == 'DEFINITION' and s['file'] == 'pkg/a.py' for s in sites))
        self.assertTrue(any(s['kind'] == 'IMPORT_SITE' and s['file'] == 'pkg/b.py' for s in sites))
        for path, raw in self.originals.items():
            self.assertEqual(path.read_bytes(), raw)


if __name__ == '__main__':
    unittest.main()
