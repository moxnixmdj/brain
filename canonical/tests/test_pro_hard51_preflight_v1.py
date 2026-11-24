"""Synthetic public-metadata preflight checks, not container or execution tests."""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from canonical.tools import pro_hard51_preflight_v1 as preflight


class ProHard51PreflightTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.ids = [preflight.DISCLOSED_ID] + [
            f'instance_org__repo-{i:040x}' + ('-vnan' if i % 2 else '') for i in range(1, 51)
        ]
        self.files = {'hard51_ids.txt': ('\n'.join(self.ids) + '\n').encode()}
        for iid in self.ids:
            self.files[f'tasks/{iid}/instruction.md'] = f'Public task {iid}\n'.encode()
            self.files[f'tasks/{iid}/task.toml'] = (
                f'[task]\nname = "swebench-pro/{iid}"\n'
                f'[agent]\nnetwork_mode = "no-network"\n'
                f'[environment]\ndocker_image = "ghcr.io/scaleapi/swe-bench_pro-v2:{iid}"\n'
            ).encode()
        for path, data in self.files.items():
            target = self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        manifest = ''.join(f'{hashlib.sha256(data).hexdigest()}  {path}\n'
                           for path, data in sorted(self.files.items())).encode()
        (self.root / 'SHA256SUMS').write_bytes(manifest)
        self.manifest_pin = hashlib.sha256(manifest).hexdigest()
        self.ids_pin = hashlib.sha256(self.files['hard51_ids.txt']).hexdigest()
        self.patches = contextlib.ExitStack()
        self.addCleanup(self.patches.close)
        self.patches.enter_context(mock.patch.object(preflight, 'MANIFEST_SHA256', self.manifest_pin))
        self.patches.enter_context(mock.patch.object(preflight, 'IDS_SHA256', self.ids_pin))

    def test_smoke_and_full_are_read_only_and_record_disclosure(self):
        smoke = preflight.build_plan(self.root, selection='smoke5', requested_isolated_vm_eval=True)
        full = preflight.build_plan(self.root, selection='hard51')
        self.assertEqual([t['instance_id'] for t in smoke['tasks']], self.ids[:5])
        self.assertEqual([t['instance_id'] for t in full['tasks']], self.ids)
        self.assertEqual(smoke['tasks'][0]['disclosure'], preflight.DISCLOSURE)
        self.assertIsNone(smoke['tasks'][1]['disclosure'])
        self.assertTrue(smoke['requested_isolated_vm_eval'])
        self.assertFalse(smoke['execution_authorized'])
        self.assertFalse(smoke['isolation_verified'])
        self.assertEqual(smoke['instances_executed'], 0)
        self.assertEqual(smoke['patches_verified'], 0)
        self.assertTrue(all(t['status'] == 'NOT_RUN_ONESHOT_CARRIER_UNQUALIFIED' for t in full['tasks']))
        self.assertFalse((self.root / 'predictions.jsonl').exists())

    def test_tampered_manifest_id_and_selected_task_are_refused(self):
        manifest = self.root / 'SHA256SUMS'
        original = manifest.read_bytes()
        manifest.write_bytes(original + b'changed')
        with self.assertRaisesRegex(preflight.PreflightRefused, 'MANIFEST_PIN_MISMATCH'):
            preflight.build_plan(self.root, selection='smoke5')
        manifest.write_bytes(original)
        ids = self.root / 'hard51_ids.txt'
        ids.write_bytes(ids.read_bytes() + b'x')
        with self.assertRaisesRegex(preflight.PreflightRefused, 'HARD51_PIN_MISMATCH'):
            preflight.build_plan(self.root, selection='smoke5')
        ids.write_bytes(self.files['hard51_ids.txt'])
        instruction = self.root / f'tasks/{self.ids[0]}/instruction.md'
        instruction.write_bytes(b'tampered\n')
        with self.assertRaisesRegex(preflight.PreflightRefused, 'TASK_METADATA_HASH_MISMATCH'):
            preflight.build_plan(self.root, selection='smoke5')

    def test_cli_opt_in_is_not_execution_admission(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = preflight.main(['--v2-root', str(self.root), '--selection', 'smoke5',
                                   '--allow-isolated-vm-eval'])
        result = json.loads(output.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual(result['status'], 'PREFLIGHT_ONLY_EXECUTION_BLOCKED')
        self.assertFalse(result['execution_authorized'])
        self.assertEqual(result['instances_executed'], 0)

    def test_missing_selected_metadata_fails_closed(self):
        (self.root / f'tasks/{self.ids[0]}/task.toml').unlink()
        with self.assertRaisesRegex(preflight.PreflightRefused, 'PUBLIC_METADATA_UNREADABLE'):
            preflight.build_plan(self.root, selection='smoke5')


if __name__ == '__main__':
    unittest.main()
