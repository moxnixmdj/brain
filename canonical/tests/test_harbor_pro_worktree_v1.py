"""Real local filesystem tests only; staging is not process confinement."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from canonical.runtime import harbor_pro_worktree_v1 as stage


class StageWorktreeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.src = self.root / 'app'
        self.dst = self.root / 'staged'
        self.src.mkdir(mode=0o700)
        self.dst.mkdir(mode=0o700)

    def tearDown(self):
        self.tmp.cleanup()

    def put(self, path, data):
        target = self.src / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return target

    def test_regular_files_copied_symlinks_and_bloat_dirs_skipped(self):
        original = self.put('src/mod.js', b'const a = 1;\n')
        self.put('node_modules/pkg/index.js', b'module.exports = 1;\n')
        self.put('dist/bundle.js', b'bundle')
        self.put('.git/config', b'secret')
        external = self.root / 'outside.txt'
        external.write_bytes(b'private')
        (self.src / 'external.js').symlink_to(external)
        (self.src / 'broken.js').symlink_to(self.root / 'missing')
        (self.src / 'node_modules' / 'pkg' / 'internal.js').symlink_to('index.js')
        original.chmod(0o755)
        result = stage.stage_worktree(self.src, self.dst)
        self.assertEqual((self.dst / 'src/mod.js').read_bytes(), b'const a = 1;\n')
        self.assertFalse((self.dst / 'node_modules').exists())
        self.assertFalse((self.dst / 'dist').exists())
        self.assertEqual((self.dst / 'src/mod.js').stat().st_mode & 0o777, 0o755)
        self.assertFalse((self.dst / '.git').exists())
        self.assertFalse((self.dst / 'external.js').exists())
        self.assertFalse((self.dst / 'broken.js').exists())
        self.assertEqual(result['symlinks_skipped'], 2)
        self.assertEqual(result['excluded_entries'], 3)
        self.assertFalse(result['dependency_completeness_verified'])
        self.assertFalse(result['confinement_verified'])
        self.assertFalse(result['test_execution_authorized'])
        self.assertFalse(result['patch_applied'])
        (self.dst / 'src/mod.js').write_text('changed')
        self.assertEqual(original.read_bytes(), b'const a = 1;\n')

    def test_authorize_test_execution_flag_is_reported_verbatim(self):
        self.put('a.txt', b'x')
        default = stage.stage_worktree(self.src, self.dst)
        self.assertFalse(default['test_execution_authorized'])
        # A fresh private destination: a reused one is refused by design.
        other = self.root / 'staged2'
        other.mkdir(mode=0o700)
        granted = stage.stage_worktree(self.src, other, authorize_test_execution=True)
        self.assertTrue(granted['test_execution_authorized'])

    @unittest.skipUnless(shutil.which('node'), 'node required')
    def test_imported_js_engine_generates_candidate_from_staged_fixture(self):
        from canonical.runtime import multilang_causal_swe_engine_v1 as engine
        original = self.put('fmt.js', b"function fmt(v, enc) {\n  const out = v ? enc(v) : '';\n  return out;\n}\nmodule.exports = {fmt};\n")
        self.put('package.json', b'{"scripts":{"test":"node --test"}}\n')
        self.put('fmt.test.js', b"const test = require('node:test');\nconst assert = require('node:assert/strict');\nconst {fmt} = require('./fmt.js');\ntest('empty', () => assert.equal(fmt('', s => '[' + s + ']'), '[]'));\ntest('nonempty', () => assert.equal(fmt('x', s => '[' + s + ']'), '[x]'));\n")
        source = original.read_bytes()
        staging = stage.stage_worktree(self.src, self.dst)
        self.assertEqual(staging['symlinks_skipped'], 0)
        result = engine.solve_js_repository(self.dst, timeout_s=10, max_candidates=30)
        self.assertEqual(result['status'], 'VERIFIED')
        self.assertTrue(result['winner']['diff'])
        self.assertEqual(original.read_bytes(), source)
        self.assertEqual((self.dst / 'fmt.js').read_bytes(), source)
        self.assertFalse(staging['confinement_verified'])

    def test_staged_process_can_still_modify_original_by_absolute_path(self):
        original = self.put('original.txt', b'before')
        stage.stage_worktree(self.src, self.dst)
        # Harmless disposable fixture demonstrates why copying is not a sandbox.
        subprocess.run([sys.executable, '-c', 'from pathlib import Path; import sys; Path(sys.argv[1]).write_text("after")',
                        str(original)], cwd=self.dst, check=True, timeout=10)
        self.assertEqual(original.read_text(), 'after')

    def test_hardlink_and_special_files_rejected(self):
        self.put('source.txt', b'x')
        os.link(self.src / 'source.txt', self.src / 'linked.txt')
        with self.assertRaisesRegex(stage.StageError, 'SOURCE_HARDLINK_REJECTED'):
            stage.stage_worktree(self.src, self.dst)
        (self.src / 'linked.txt').unlink()
        os.mkfifo(self.src / 'fifo')
        with self.assertRaisesRegex(stage.StageError, 'SPECIAL_FILE_REJECTED'):
            stage.stage_worktree(self.src, self.dst)

    def test_limits_and_private_empty_destination(self):
        self.put('nested/file.txt', b'abc')
        with patch.object(stage, 'MAX_TOTAL_BYTES', 2):
            with self.assertRaisesRegex(stage.StageError, 'BYTE_LIMIT'):
                stage.stage_worktree(self.src, self.dst)
        # A failed stage may be partial and must be discarded, not reused.
        self.assertTrue(any(self.dst.iterdir()))
        with self.assertRaisesRegex(stage.StageError, 'DESTINATION_NOT_EMPTY'):
            stage.stage_worktree(self.src, self.dst)
        with tempfile.TemporaryDirectory(dir=self.root) as td:
            loose = Path(td)
            loose.chmod(0o755)
            with self.assertRaisesRegex(stage.StageError, 'DESTINATION_NOT_PRIVATE'):
                stage.stage_worktree(self.src, loose)
        with tempfile.TemporaryDirectory(dir=self.root) as td:
            with patch.object(stage, 'MAX_ENTRIES', 0):
                with self.assertRaisesRegex(stage.StageError, 'ENTRY_LIMIT'):
                    stage.stage_worktree(self.src, td)
        with tempfile.TemporaryDirectory(dir=self.root) as td:
            with patch.object(stage, 'MAX_DEPTH', 0):
                with self.assertRaisesRegex(stage.StageError, 'DEPTH_LIMIT'):
                    stage.stage_worktree(self.src, td)

    def test_root_symlinks_and_overlapping_paths_rejected(self):
        alias = self.root / 'alias'
        alias.symlink_to(self.src, target_is_directory=True)
        with self.assertRaisesRegex(stage.StageError, 'ROOT_UNAVAILABLE_OR_SYMLINK'):
            stage.stage_worktree(alias, self.dst)
        inside = self.src / 'inner'
        inside.mkdir(mode=0o700)
        with self.assertRaisesRegex(stage.StageError, 'OVERLAPPING_OR_ROOT_PATH'):
            stage.stage_worktree(self.src, inside)
        with self.assertRaisesRegex(stage.StageError, 'ABSOLUTE_PATHS_REQUIRED'):
            stage.stage_worktree('relative', self.dst)


if __name__ == '__main__':
    unittest.main()
