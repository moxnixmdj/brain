"""Engineering checks, not benchmark scores. No task, Docker or grader is emulated."""
from __future__ import annotations

import base64
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from canonical.tools.harbor_smoke_audit_v1 import audit
from canonical.tools.stage_harbor_runtime_v1 import DEFAULT_ARTIFACT, SOURCES, stage


class ColdMountTests(unittest.TestCase):
    def test_actual_worker_can_propose_with_only_cold_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / 'producer'
            manifest = stage(dest)
            files = {p.relative_to(dest).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in dest.rglob('*') if p.is_file()}
            self.assertEqual(files, manifest)
            self.assertEqual(set(files), {*SOURCES, DEFAULT_ARTIFACT})
            artifact = json.loads((dest / DEFAULT_ARTIFACT).read_bytes())
            self.assertEqual((artifact['knowledge'], artifact['skills']), ([], []))
            with self.assertRaises(FileExistsError):
                stage(dest)
            worker = dest / 'canonical/runtime/harbor_container_solver_worker_v1.py'
            inputs = {'harbor_task': 'Report the number of rows.', 'observations': [], 'cycle': 1}
            for cycle, expected in ((1, True), (2, False), (True, False)):
                inputs['cycle'] = cycle
                request = {'goal': inputs['harbor_task'], 'inputs': inputs, 'mode': 'EPISTEMIC'}
                arg = base64.b64encode(json.dumps(request).encode()).decode()
                proc = subprocess.run([sys.executable, '-I', '-B', str(worker), arg],
                                      cwd=tmp, check=True, capture_output=True, text=True, timeout=15)
                result = json.loads(proc.stdout.split('BRAIN_CONTAINER_SOLVE_V1:')[1])
                self.assertIs(result['pass'], expected)
                if expected:
                    self.assertEqual(result['model_digest'], artifact['digest']['value'])
                    self.assertIn('--phase discover', result['actions'][0]['args']['command'])
                    self.assertIs(result['task_completion_claimed'], False)
                else:
                    self.assertEqual(result['reason'], 'INVALID_HARBOR_CYCLE_ENVELOPE')
                    self.assertNotIn('actions', result)


class SmokeAccountingTests(unittest.TestCase):
    def test_verifier_zero_is_not_a_missing_duplicate_or_invalid_trial(self):
        with tempfile.TemporaryDirectory() as tmp:
            jobs = Path(tmp)
            selected = ['first', 'absent', 'duplicate', 'invalid']
            for i, (name, reward) in enumerate([('first', 0), ('duplicate', 0),
                                                ('duplicate', 1), ('invalid', True)]):
                trial = jobs / 'brain-tb4-smoke' / str(i)
                (trial / 'agent').mkdir(parents=True)
                (trial / 'result.json').write_text(json.dumps({'task_name': 'terminal-bench/' + name,
                    'exception_info': None, 'verifier_result': {'rewards': {'reward': reward}}}))
                (trial / 'agent/brain_epistemic_trace.json').write_text(json.dumps({
                    'status': 'BLOCKED_NO_MODEL_PROPOSAL',
                    'external_harbor_vm_eval_status': 'EXPERIMENTAL_DISPATCH__UNVERIFIED'}))
            report = audit(jobs, selected, pro=False)
            self.assertEqual([r['task'] for r in report['rows']], selected)
            self.assertEqual([r['reward'] for r in report['rows']], [0, None, None, None])
            self.assertTrue(report['issues'])
            self.assertNotIn('ungraded_reason', report['rows'][0])

    def test_pro_never_scores_a_producer_without_a_pristine_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            jobs = Path(tmp)
            trial = jobs / 'brain-pro-smoke/instance_test'
            trial.mkdir(parents=True)
            (trial / 'result.json').write_text(json.dumps({'task_name': 'swebench-pro/a',
                'exception_info': None, 'verifier_result': {'rewards': {'reward': 1}}}))
            row, = audit(jobs, ['a'], pro=True)['rows']
            self.assertIsNone(row['reward'])
            self.assertIn('missing', row['ungraded_reason'])
