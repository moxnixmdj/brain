"""Test the current arm without requiring or importing historical source."""
import shutil
import tempfile
from pathlib import Path
import unittest

from canonical.tools import computer_branch_comparison_v1 as bench


@unittest.skipUnless(shutil.which('wc'), 'requires real wc')
class CurrentComputerComparisonTests(unittest.TestCase):
    def test_discovery_snapshot_and_fresh_process_reuse(self):
        with tempfile.TemporaryDirectory(prefix='bc_') as tmp:
            root = Path(tmp)
            source = root / 'source'
            taught = bench.invoke(root, source, 'current', 'teach', 'warm')
            self.assertTrue(taught['admitted'], taught)
            target = root / 'target'
            target.mkdir()
            shutil.copytree(source / 'state', target / 'state')
            result = bench.invoke(root, target, 'current', 'target', 'warm', 'long_name')
            self.assertTrue(result['query_cache_present_before'])
            self.assertTrue(result['pass'], result)
            self.assertEqual(result['value'], str(bench.TARGETS['long_name'].count('\n')))
            missing = bench.invoke(root, root / 'missing', 'current', 'target', 'cold', 'missing')
            self.assertFalse(missing['pass'])
            self.assertEqual(missing['status'], 'OPEN__NO_EXISTING_INPUT_FILE_IN_GOAL')
