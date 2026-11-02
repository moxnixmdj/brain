"""A real front-door control and direct retained-tool reuse, not a general benchmark."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parent


class ComputerGoalReuseProbeTests(unittest.TestCase):
    def test_real_goals_and_negative_controls(self):
        unshare = shutil.which('unshare')
        if not unshare or not shutil.which('gzip'):
            self.skipTest('gzip and unshare required')
        network_probe = subprocess.run(
            [unshare, '--user', '--map-root-user', '--net', sys.executable, '-c', 'pass'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
        if network_probe.returncode:
            self.skipTest('network namespace unavailable; no unrestricted fallback')
        proc = subprocess.run([sys.executable, str(ROOT / 'computer_goal_reuse_probe_20261102.py')],
                              cwd=ROOT, capture_output=True, text=True, timeout=120, check=True)
        result = json.loads(proc.stdout)
        rows = {(row['mode'], row['role']): row for row in result['rows']}
        self.assertEqual(len(rows), 7)
        self.assertEqual(len({row['pid'] for row in rows.values()}), 7)
        self.assertEqual(result['unexpected_generated_archive_names'], [])
        for role in ('teach', 'cold', 'warm'):
            fabric = rows['fabric', role]
            if fabric['result']['pass'] is True:
                self.assertTrue(fabric['target_exists'])
                self.assertTrue(fabric['full_decompression_matches_input'])
            else:
                self.assertFalse(fabric['target_exists'])
            self.assertTrue(fabric['source_unchanged'])
            self.assertTrue(fabric['neighboring_file_unchanged'])
            direct = rows['direct', role]
            self.assertIs(direct['result']['pass'], True)
            self.assertIs(direct['result']['source_content_verified'], True)
            self.assertTrue(direct['full_decompression_matches_input'])
            self.assertTrue(direct['source_unchanged'])
            self.assertTrue(direct['neighboring_file_unchanged'])
        self.assertIs(rows['direct', 'teach']['result']['from_memory'], False)
        self.assertIs(rows['direct', 'cold']['result']['from_memory'], False)
        self.assertIs(rows['direct', 'warm']['result']['from_memory'], True)
        self.assertEqual(rows['direct', 'missing']['result']['status'],
                         'OPEN__NO_EXISTING_INPUT_FILE_IN_GOAL')
        self.assertFalse(rows['direct', 'missing']['target_exists'])


if __name__ == '__main__':
    unittest.main()
