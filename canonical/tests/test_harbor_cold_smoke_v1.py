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

    def test_missing_wave_is_allowed_only_for_the_cold_model(self):
        from canonical.runtime.brain_unified_model_v1 import UnifiedModel, artifact_digest

        self.assertTrue(callable(UnifiedModel.rung3_proposer_jitrl_solve))
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / 'producer'
            stage(dest)
            # No actual full registry or privileged data enters this process.
            artifact = json.loads((dest / DEFAULT_ARTIFACT).read_bytes())
            artifact['model_id'] = 'non-cold-installation'
            artifact['digest'] = {'value': artifact_digest(artifact)}
            path = Path(tmp) / 'custom.json'
            path.write_text(json.dumps(artifact))
            cmd = [sys.executable, '-I', '-S', '-B', '-c',
                   'import sys; sys.path.insert(0, sys.argv[1]); '
                   'from canonical.runtime.brain_unified_model_v1 import open_model; open_model(sys.argv[2])',
                   str(dest), str(path)]
            proc = subprocess.run(cmd, cwd=tmp, capture_output=True, text=True, timeout=15)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn('UnifiedModelError: FULL_MODEL_WAVE_PROVIDER_MISSING', proc.stderr)


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

    def test_pro_audits_handoff_identity_and_reports_measured_phase_times(self):
        # Audit input records only; this is not a task replay or an earned reward.
        from canonical.runtime.harbor_pro_patch_handoff_v1 import store_candidate_patch
        with tempfile.TemporaryDirectory() as tmp:
            jobs = Path(tmp)
            src, dst = (jobs / d / 'trial' for d in ('brain-pro-smoke', 'brain-pro-smoke-regrade'))
            patch = b'diff --git a/a b/a\n'
            for d in (src, dst):
                (d / 'agent').mkdir(parents=True)
                (d / 'result.json').write_text(json.dumps({'task_name': 'swebench-pro/a', 'task_checksum': 'one',
                    'started_at': '2026-11-25T10:00:00Z', 'finished_at': '2026-11-25T10:00:12.250Z',
                    'exception_info': None, 'verifier_result': {'rewards': {'reward': 0}}}))
            digest = hashlib.sha256(patch).hexdigest()
            handoff = store_candidate_patch(agent_log_dir=src/'agent', patch=patch,
                expected_base='a'*40, reported_base='a'*40, expected_sha256=digest)
            (src/'agent/brain_epistemic_trace.json').write_text(json.dumps({'status': 'FINISHED',
                'patch_emitted': True, 'pro_candidate_handoff': handoff,
                'external_harbor_vm_eval_status': 'EXPERIMENTAL_DISPATCH__UNVERIFIED'}))
            replay = {'task': 'a', 'patch': handoff['patch_path'], 'apply_rc': 0}
            def row(**override):
                (dst/'agent/replay.json').write_text(json.dumps({**replay, **override}))
                return audit(jobs, ['a'], pro=True)['rows'][0]
            ok = row()
            self.assertEqual((ok['reward'], ok['replay'], ok['patch_sha256']), (0, 'APPLIED', digest))
            self.assertEqual(ok['replay_trial_s'], 12.25)
            self.assertIsNone(ok['verifier_s'])  # missing phase timing is not zero
            self.assertIsNone(row(apply_rc=False)['reward'])
            self.assertIsNone(row(task='b')['reward'])
            (src/'agent/model.patch').write_bytes(patch.replace(b'a/a', b'x/x'))
            self.assertIsNone(row()['reward'])  # same length and path, different intervention

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
