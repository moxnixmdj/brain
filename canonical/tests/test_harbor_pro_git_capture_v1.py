"""Local Git fixture and mocked Harbor exec; neither is a Docker verification."""
import asyncio
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest

from canonical.runtime import harbor_pro_git_capture_v1 as worker
from canonical.runtime import harbor_pro_capture_transport_v1 as transport
from canonical.runtime.harbor_pro_patch_handoff_v1 import PatchHandoffError


def git(repo, *args):
    return subprocess.run(['git', '-C', str(repo), *args], check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout


class RecordedEnvironment:
    def __init__(self, stdout='', code=0, error=None):
        self.stdout, self.code, self.error = stdout, code, error
        self.calls = []

    async def exec(self, command, **kwargs):
        self.calls.append((command, kwargs))
        if self.error:
            raise self.error
        return SimpleNamespace(return_code=self.code, stdout=self.stdout, stderr='')


class GitCaptureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / 'repo with space'
        self.repo.mkdir()
        git(self.repo, 'init', '-q')
        (self.repo / 'a.txt').write_bytes(b'base\n')
        (self.repo / 'deleted.txt').write_bytes(b'deleted\n')
        git(self.repo, 'add', '.')
        git(self.repo, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
            'commit', '-qm', 'base')
        self.base = git(self.repo, 'rev-parse', 'HEAD').decode().strip()
        (self.repo / 'a.txt').write_bytes(b'staged\n')
        git(self.repo, 'add', 'a.txt')
        (self.repo / 'a.txt').write_bytes(b'final\n')
        (self.repo / 'deleted.txt').unlink()
        (self.repo / 'new.bin').write_bytes(b'\0binary\xff')
        self.logs = self.root / 'agent'
        self.logs.mkdir()

    def test_capture_and_transport_to_candidate_patch_on_real_git_fixture(self):
        before_index = git(self.repo, 'diff', '--cached', '--binary')
        proc = subprocess.run([sys.executable, str(Path(worker.__file__)), str(self.repo), self.base],
                              text=True, capture_output=True, check=True)
        self.assertEqual(git(self.repo, 'diff', '--cached', '--binary'), before_index)
        env = RecordedEnvironment(proc.stdout)
        result = asyncio.run(transport.capture_unqualified_candidate(env, repo='/app with space',
                                   expected_base=self.base, agent_log_dir=self.logs))
        patch = (self.logs / 'model.patch').read_bytes()
        self.assertEqual(result['patch_sha256'], hashlib.sha256(patch).hexdigest())
        self.assertFalse(result['worker_quiescence_verified'])
        self.assertFalse(result['base_commit_verified'])
        self.assertFalse(result['container_boundary_verified'])
        self.assertFalse(result['external_verifier_invoked'])
        self.assertIn("'/app with space'", env.calls[0][0])
        self.assertIn('/opt/brain-ro/canonical/runtime/harbor_pro_git_capture_v1.py', env.calls[0][0])
        self.assertEqual(env.calls[0][1], {'timeout_sec': 300})
        fresh = self.root / 'fresh'
        fresh.mkdir()
        git(fresh, 'init', '-q')
        (fresh / 'a.txt').write_bytes(b'base\n')
        (fresh / 'deleted.txt').write_bytes(b'deleted\n')
        git(fresh, 'apply', '--check', str(self.logs / 'model.patch'))
        git(fresh, 'apply', str(self.logs / 'model.patch'))
        self.assertEqual((fresh / 'a.txt').read_bytes(), b'final\n')
        self.assertFalse((fresh / 'deleted.txt').exists())
        self.assertEqual((fresh / 'new.bin').read_bytes(), b'\0binary\xff')

    def test_mismatched_base_and_nonroot_path_fail(self):
        wrong = 'b' * len(self.base) if self.base != 'b' * len(self.base) else 'c' * len(self.base)
        with self.assertRaisesRegex(worker.CaptureError, 'BASE_MISMATCH_BEFORE_CAPTURE'):
            worker.capture_candidate(self.repo, wrong)
        (self.repo / 'sub').mkdir()
        with self.assertRaisesRegex(worker.CaptureError, 'REPOSITORY_NOT_TOP_LEVEL'):
            worker.capture_candidate(self.repo / 'sub', self.base)
        with self.assertRaisesRegex(worker.CaptureError, 'BRAIN_ROOT_INSIDE_REPOSITORY'):
            worker.capture_candidate(Path('/'), self.base)

    def test_transport_rejects_tampering_and_nonzero_without_publication(self):
        data = worker.capture_candidate(self.repo, self.base)
        cases = [RecordedEnvironment(worker.MARKER + json.dumps(data) + '\n', code=1),
                 RecordedEnvironment(worker.MARKER + json.dumps(data | {'sha256': '0' * 64}) + '\n'),
                 RecordedEnvironment(worker.MARKER + json.dumps(data | {'patch_base64': '!'}) + '\n'),
                 RecordedEnvironment((worker.MARKER + json.dumps(data) + '\n') * 2),
                 RecordedEnvironment(worker.MARKER + json.dumps(data | {'worker_quiescence_verified': True}) + '\n')]
        for env in cases:
            with self.subTest(stdout=env.stdout[:100], code=env.code):
                with self.assertRaises((transport.CaptureTransportError, PatchHandoffError)):
                    asyncio.run(transport.capture_unqualified_candidate(env, repo='/app',
                                    expected_base=self.base, agent_log_dir=self.logs))
                self.assertEqual(list(self.logs.iterdir()), [])
                self.assertEqual(len(env.calls), 1)

    def test_uncertain_dispatch_does_not_retry_or_publish(self):
        env = RecordedEnvironment(error=TimeoutError('lost'))
        from canonical.runtime.harbor_environment_transport_v2 import HarborTransportUncertainError
        with self.assertRaises(HarborTransportUncertainError):
            asyncio.run(transport.capture_unqualified_candidate(env, repo='/app',
                            expected_base=self.base, agent_log_dir=self.logs))
        self.assertEqual(len(env.calls), 1)
        self.assertEqual(list(self.logs.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
