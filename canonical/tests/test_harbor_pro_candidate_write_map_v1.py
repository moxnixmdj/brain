from __future__ import annotations

from pathlib import Path
import os
import tempfile
import unittest

from canonical.runtime.harbor_pro_candidate_write_map_v1 import (
    CandidateApplyError, apply_source_map, source_map_from_winner,
)


class CandidateWriteMapTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / 'app'
        self.root.mkdir(mode=0o700)

    def tearDown(self):
        self.tmp.cleanup()

    def test_source_map_and_apply_preserves_unrelated_files(self):
        (self.root / 'src').mkdir()
        (self.root / 'src/a.js').write_text('before\n')
        (self.root / 'notes.txt').write_text('keep\n')
        winner = {'file': 'src/a.js', 'patched_source': 'after\n', 'diff': 'diff --git',
                  'extra_patches': {'src/b.js': 'new b\n'}}
        mapping, diff_bytes, nonempty = source_map_from_winner(winner)
        self.assertEqual(mapping, {'src/a.js': 'after\n', 'src/b.js': 'new b\n'})
        self.assertEqual(diff_bytes, len('diff --git'))
        self.assertTrue(nonempty)
        applied = apply_source_map(self.root, mapping)
        self.assertEqual((self.root / 'src/a.js').read_text(), 'after\n')
        self.assertEqual((self.root / 'src/b.js').read_text(), 'new b\n')
        self.assertEqual((self.root / 'notes.txt').read_text(), 'keep\n')
        self.assertEqual(applied['files_written'], 2)

    def test_rejects_escape_vcs_and_conflicting_maps(self):
        for path in ('/etc/passwd', '../evil', 'src/../evil', '.git/config'):
            with self.assertRaises(CandidateApplyError):
                source_map_from_winner({'patched_files': {path: 'x'}})
        with self.assertRaisesRegex(CandidateApplyError, 'CONFLICTING_SOURCE_MAP'):
            source_map_from_winner({'file': 'a.js', 'patched_source': 'one',
                                    'extra_patches': {'a.js': 'two'}})

    def test_rollback_removes_new_file_and_restores_old_bytes(self):
        target = self.root / 'a.txt'
        target.write_bytes(b'before')
        # Inject failure while writing the second file by making its final
        # target a directory. The first file must be restored.
        blocker = self.root / 'blocked'
        blocker.mkdir()
        with self.assertRaisesRegex(CandidateApplyError, 'TARGET_NOT_REGULAR_FILE'):
            apply_source_map(self.root, {'a.txt': 'after', 'blocked': 'x'})
        self.assertEqual(target.read_bytes(), b'before')

    def test_partial_write_failure_restores_created_file(self):
        (self.root / 'real.txt').write_text('before')
        # Local test double injects a late failure after an earlier file was written.
        from canonical.runtime import harbor_pro_candidate_write_map_v1 as mod
        original_write = mod._write_one
        calls = []
        def flaky(root_fd, parts, data, old_mode):
            calls.append(parts)
            if parts[-1] == 'late.txt':
                raise mod.CandidateApplyError('INJECTED_LATE_FAILURE')
            return original_write(root_fd, parts, data, old_mode)
        try:
            mod._write_one = flaky
            with self.assertRaisesRegex(CandidateApplyError, 'INJECTED_LATE_FAILURE'):
                apply_source_map(self.root, {'early.txt': 'new', 'late.txt': 'late', 'real.txt': 'changed'})
        finally:
            mod._write_one = original_write
        self.assertFalse((self.root / 'early.txt').exists())
        self.assertEqual((self.root / 'real.txt').read_text(), 'before')

    def test_symlink_target_not_followed(self):
        outside = Path(self.tmp.name) / 'outside'
        outside.write_text('outside')
        link = self.root / 'link'
        link.symlink_to(outside)
        with self.assertRaisesRegex(CandidateApplyError, 'TARGET_NOT_REGULAR_FILE|TARGET_UNSAFE'):
            apply_source_map(self.root, {'link': 'pwned'})
        self.assertEqual(outside.read_text(), 'outside')



class ImportedWorkerCycleTests(unittest.TestCase):
    def test_js_engine_candidate_is_applied_to_repo_copy(self):
        import shutil
        if not shutil.which('node'):
            self.skipTest('node required')
        from canonical.runtime import harbor_container_solver_worker_v1 as worker
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'app'
            root.mkdir(mode=0o700)
            source = "function fmt(v, enc) {\n  const out = v ? enc(v) : '';\n  return out;\n}\nmodule.exports = {fmt};\n"
            (root / 'fmt.js').write_text(source)
            (root / 'package.json').write_text('{"scripts":{"test":"node --test"}}\n')
            (root / 'fmt.test.js').write_text("const test = require('node:test');\nconst assert = require('node:assert/strict');\nconst {fmt} = require('./fmt.js');\ntest('empty', () => assert.equal(fmt('', s => '[' + s + ']'), '[]'));\ntest('nonempty', () => assert.equal(fmt('x', s => '[' + s + ']'), '[x]'));\n")
            result = worker._pro_imported_cycle({'harbor_suite': 'pro-v2', 'harbor_repo': str(root),
                                                  'harbor_task': 'Fix fmt empty string behavior',
                                                  'observations': []}, str(root))
            self.assertTrue(result['pass'])
            self.assertEqual(result['actions'][0]['type'], 'finish')
            self.assertEqual(result['language'], 'javascript_typescript')
            self.assertTrue(result['candidate_applied'])
            self.assertNotEqual((root / 'fmt.js').read_text(), source)
            self.assertEqual(result['staging']['confinement_verified'], False)
            self.assertTrue(result['official_verifier_expected'])


if __name__ == '__main__':
    unittest.main()
