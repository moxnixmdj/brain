"""Real local Git fixtures, not Harbor, Docker, or official verification."""
import hashlib
from pathlib import Path
import subprocess
import tempfile
import unittest

from canonical.runtime import harbor_pro_patch_handoff_v1 as handoff


def git(repo, *args):
    return subprocess.run(['git', '-C', str(repo), *args], check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout


class PatchHandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        git(self.repo, 'init', '-q')
        (self.repo / 'original.txt').write_bytes(b'original\n')
        (self.repo / 'delete.txt').write_bytes(b'delete\n')
        git(self.repo, 'add', '.')
        git(self.repo, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
            'commit', '-qm', 'base')
        self.base = git(self.repo, 'rev-parse', 'HEAD').decode().strip()
        (self.repo / 'original.txt').write_bytes(b'changed\n')
        (self.repo / 'delete.txt').unlink()
        (self.repo / 'binary.bin').write_bytes(b'\0binary\xff\0')
        git(self.repo, 'add', '-A')
        self.patch = git(self.repo, 'diff', '--cached', '--binary', '--full-index', '--no-ext-diff')
        self.logs = self.root / 'job' / 'instance_fixture' / 'agent'
        self.logs.mkdir(parents=True)
        self.args = dict(agent_log_dir=self.logs, patch=self.patch, expected_base=self.base,
                         reported_base=self.base, expected_sha256=hashlib.sha256(self.patch).hexdigest())

    def test_replay_candidate_bytes_apply_to_separate_git_fixture(self):
        result = handoff.store_candidate_patch(**self.args)
        target = self.logs / 'model.patch'
        self.assertEqual(target.read_bytes(), self.patch)
        self.assertEqual(result['patch_sha256'], hashlib.sha256(target.read_bytes()).hexdigest())
        self.assertFalse(result['base_commit_verified'])
        self.assertFalse(result['worker_quiescence_verified'])
        self.assertFalse(result['patch_completeness_verified'])
        self.assertFalse(result['external_verifier_invoked'])
        self.assertFalse(result['execution_authorized'])
        fresh = self.root / 'fresh'
        fresh.mkdir()
        git(fresh, 'init', '-q')
        (fresh / 'original.txt').write_bytes(b'original\n')
        (fresh / 'delete.txt').write_bytes(b'delete\n')
        git(fresh, 'apply', '--check', str(target))
        git(fresh, 'apply', str(target))
        self.assertEqual((fresh / 'original.txt').read_bytes(), b'changed\n')
        self.assertFalse((fresh / 'delete.txt').exists())
        self.assertEqual((fresh / 'binary.bin').read_bytes(), b'\0binary\xff\0')
        self.assertEqual(sorted(p.name for p in self.logs.iterdir()), ['model.patch'])

    def test_bad_digest_base_or_patch_is_not_published(self):
        cases = [({'expected_sha256': '0' * 64}, 'PATCH_SHA256_MISMATCH'),
                 ({'expected_sha256': 'x'}, 'SHA256_FORMAT_INVALID'),
                 ({'reported_base': 'a' * 40 if self.base != 'a' * 40 else 'b' * 40}, 'REPORTED_BASE_MISMATCH'),
                 ({'reported_base': 'short'}, 'BASE_FORMAT_INVALID'),
                 ({'patch': b'not a diff'}, 'PATCH_FORMAT_INVALID'),
                 ({'patch': b'x' * (handoff.MAX_PATCH_BYTES + 1)}, 'PATCH_BYTES_INVALID')]
        for changes, reason in cases:
            with self.subTest(reason=reason):
                with self.assertRaisesRegex(handoff.PatchHandoffError, reason):
                    handoff.store_candidate_patch(**(self.args | changes))
                self.assertEqual(list(self.logs.iterdir()), [])

    def test_existing_output_or_symlink_is_never_replaced(self):
        path = self.logs / 'model.patch'
        victim = self.root / 'victim'
        victim.write_bytes(b'preserve')
        path.symlink_to(victim)
        with self.assertRaisesRegex(handoff.PatchHandoffError, 'MODEL_PATCH_ALREADY_EXISTS'):
            handoff.store_candidate_patch(**self.args)
        self.assertTrue(path.is_symlink())
        self.assertEqual(victim.read_bytes(), b'preserve')
        self.assertEqual(sorted(p.name for p in self.logs.iterdir()), ['model.patch'])

    def test_empty_patch_is_stored_but_not_a_success_claim(self):
        empty = b''
        result = handoff.store_candidate_patch(**(self.args | {
            'patch': empty, 'expected_sha256': hashlib.sha256(empty).hexdigest()}))
        self.assertEqual((self.logs / 'model.patch').read_bytes(), empty)
        self.assertEqual(result['status'], 'CANDIDATE_BYTES_STORED__NOT_VERIFIED')

    def test_symlink_log_directory_is_refused(self):
        link = self.root / 'link'
        link.symlink_to(self.logs, target_is_directory=True)
        with self.assertRaisesRegex(handoff.PatchHandoffError, 'TRUSTED_AGENT_LOG_DIR_REQUIRED'):
            handoff.store_candidate_patch(**(self.args | {'agent_log_dir': link}))
        self.assertEqual(list(self.logs.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
