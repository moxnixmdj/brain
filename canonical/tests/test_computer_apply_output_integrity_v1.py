"""Real subprocess and file controls for applying a learned compression recipe."""
from __future__ import annotations

import bz2
import gzip
import lzma
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest

from canonical.runtime import computer_env_v1 as cenv


class ApplyOutputIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'work'
        self.root.mkdir()
        self.source = self.root / 'source.txt'
        self.content = b'correct user data\n' * 20000
        self.source.write_bytes(self.content)

    def recipe(self, code, suffix='gz'):
        name = 'result.' + suffix
        return {'argv': [sys.executable, '-c', code, '{input}'],
                'target': name, 'stdout_to': name}

    def test_wrong_but_valid_gzip_is_refused_without_publishing(self):
        recipe = self.recipe('import gzip,sys; sys.stdout.buffer.write(gzip.compress(b"wrong data"))')
        result = cenv.apply(recipe, self.source, output_name='result.gz')
        self.assertFalse(result['pass'], result)
        self.assertEqual(result['status'], 'OPEN__OUTPUT_CONTENT_MISMATCH')
        self.assertFalse((self.root / 'result.gz').exists())
        self.assertEqual(list(self.root.glob('.brain-*')), [])
        self.assertEqual(self.source.read_bytes(), self.content)

    def test_correct_single_file_compression_formats_preserve_all_bytes(self):
        for suffix, module, decompress in (('gz', 'gzip', gzip.decompress),
                                           ('bz2', 'bz2', bz2.decompress),
                                           ('xz', 'lzma', lzma.decompress)):
            with self.subTest(suffix=suffix):
                recipe = self.recipe('import sys,' + module + '; sys.stdout.buffer.write('
                                     + module + '.compress(open(sys.argv[1], "rb").read()))', suffix)
                name = 'result.' + suffix
                result = cenv.apply(recipe, self.source, output_name=name)
                self.assertTrue(result['pass'], result)
                self.assertTrue(result['source_content_verified'])
                self.assertEqual(decompress((self.root / name).read_bytes()), self.content)
                self.assertEqual(self.source.read_bytes(), self.content)

    def test_existing_output_is_not_clobbered(self):
        target = self.root / 'result.gz'
        target.write_bytes(b'valuable preexisting destination')
        recipe = self.recipe('import gzip,sys; sys.stdout.buffer.write(gzip.compress(b"other"))')
        result = cenv.apply(recipe, self.source, output_name=target.name)
        self.assertFalse(result['pass'], result)
        self.assertEqual(target.read_bytes(), b'valuable preexisting destination')

    def test_existing_symlink_is_not_followed_or_removed(self):
        protected = self.root / 'protected.txt'
        protected.write_bytes(b'protected')
        target = self.root / 'result.gz'
        target.symlink_to(protected)
        result = cenv.apply(self.recipe('print("should not run")'), self.source, output_name=target.name)
        self.assertFalse(result['pass'], result)
        self.assertTrue(target.is_symlink())
        self.assertEqual(protected.read_bytes(), b'protected')

    def test_dangling_symlink_is_also_an_existing_destination(self):
        target = self.root / 'result.gz'
        target.symlink_to(self.root / 'missing.txt')
        result = cenv.apply(self.recipe('print("should not run")'), self.source, output_name=target.name)
        self.assertFalse(result['pass'], result)
        self.assertTrue(target.is_symlink())
        self.assertFalse((self.root / 'missing.txt').exists())

    def test_failed_command_cannot_publish_even_if_it_emits_valid_gzip(self):
        recipe = self.recipe('import gzip,sys; sys.stdout.buffer.write(gzip.compress('
                             'open(sys.argv[1], "rb").read())); sys.exit(7)')
        result = cenv.apply(recipe, self.source, output_name='result.gz')
        self.assertFalse(result['pass'], result)
        self.assertFalse((self.root / 'result.gz').exists())

    def test_modifying_the_staged_input_does_not_touch_original_or_publish(self):
        code = ('import gzip,sys; open(sys.argv[1], "wb").write(b"changed"); '
                'sys.stdout.buffer.write(gzip.compress(b"changed"))')
        result = cenv.apply(self.recipe(code), self.source, output_name='result.gz')
        self.assertFalse(result['pass'], result)
        self.assertEqual(self.source.read_bytes(), self.content)
        self.assertFalse((self.root / 'result.gz').exists())

    def test_output_traversal_and_source_alias_are_refused(self):
        recipe = self.recipe('print("should not run")')
        for name in ('../escape.gz', str(self.root / 'absolute.gz'), self.source.name):
            with self.subTest(name=name):
                result = cenv.apply(recipe, self.source, output_name=name)
                self.assertFalse(result['pass'], result)
                self.assertEqual(self.source.read_bytes(), self.content)
        self.assertFalse((self.root / 'absolute.gz').exists())
        self.assertFalse((self.root.parent / 'escape.gz').exists())

    def test_destination_created_during_execution_is_not_overwritten(self):
        target = self.root / 'result.gz'
        code = ('import gzip,sys; open(%r, "wb").write(b"concurrent writer"); '
                'sys.stdout.buffer.write(gzip.compress(open(sys.argv[1], "rb").read()))') % str(target)
        result = cenv.apply(self.recipe(code), self.source, output_name=target.name)
        self.assertFalse(result['pass'], result)
        self.assertEqual(target.read_bytes(), b'concurrent writer')

    def test_subprocess_output_symlink_is_not_followed(self):
        protected = self.root / 'protected.txt'
        protected.write_bytes(b'protected')
        code = ('import os,sys; os.symlink(%r, "result.gz"); sys.stdout.write("bad")') % str(protected)
        result = cenv.apply(self.recipe(code), self.source, output_name='result.gz')
        self.assertFalse(result['pass'], result)
        self.assertEqual(protected.read_bytes(), b'protected')
        self.assertFalse((self.root / 'result.gz').exists())

    def test_existing_output_is_refused_by_perform_before_discovery(self):
        target = self.root / 'source.txt.gz'
        target.write_bytes(b'existing')
        result = cenv.perform('compress source.txt into source.txt.gz', cwd=self.root)
        self.assertEqual(result['status'], 'OPEN__OUTPUT_ALREADY_EXISTS')
        self.assertEqual(target.read_bytes(), b'existing')
        self.assertEqual(self.source.read_bytes(), self.content)

    def test_existing_chain_output_is_not_removed(self):
        target = self.root / 'source.tar.gz'
        target.write_bytes(b'valuable existing archive')
        result = cenv.perform('pack source.txt into source.tar.gz', cwd=self.root)
        self.assertEqual(result['status'], 'OPEN__OUTPUT_ALREADY_EXISTS')
        self.assertEqual(target.read_bytes(), b'valuable existing archive')
        self.assertEqual(self.source.read_bytes(), self.content)

    def test_real_tar_gzip_chain_preserves_source_and_leaves_no_staging_files(self):
        binaries = {name: shutil.which(name) for name in ('tar', 'gzip', 'unshare')}
        if not all(binaries.values()):
            self.skipTest('tar, gzip and network namespaces are required')
        check = subprocess.run([binaries['unshare'], '--user', '--map-root-user', '--net',
                                sys.executable, '-c', 'pass'], capture_output=True, timeout=15)
        if check.returncode:
            self.skipTest('network namespace unavailable; no unrestricted fallback')
        bindir = Path(self.tmp.name) / 'bin'
        bindir.mkdir()
        for name in ('tar', 'gzip'):
            (bindir / name).symlink_to(binaries[name])
        state = Path(self.tmp.name) / 'state'
        state.mkdir()
        env = {k: v for k, v in os.environ.items() if not k.startswith('BRAIN_')}
        env.update(PATH=str(bindir), PYTHONPATH=str(Path(__file__).resolve().parents[2]),
                   PYTHONDONTWRITEBYTECODE='1', BRAIN_STATE_DIR=str(state),
                   BRAIN_TRANSFER_LEARNING_STATE=str(state / 'episodes.json'))
        code = ('from canonical.runtime.computer_env_v1 import perform; import json,sys; '
                'print(json.dumps(perform("pack source.txt into source.tar.gz", cwd=sys.argv[1])))')
        proc = subprocess.run([binaries['unshare'], '--user', '--map-root-user', '--net',
                               sys.executable, '-c', code, str(self.root)], env=env,
                              capture_output=True, text=True, timeout=60, check=True)
        import json
        result = json.loads(proc.stdout)
        self.assertTrue(result['pass'], result)
        with tarfile.open(self.root / 'source.tar.gz', 'r:gz') as archive:
            self.assertEqual(archive.getnames(), ['source.txt'])
            self.assertEqual(archive.extractfile('source.txt').read(), self.content)
        self.assertEqual(self.source.read_bytes(), self.content)
        self.assertEqual(list(self.root.glob('.brain-*')), [])

    def test_empty_source_is_verified_to_eof(self):
        self.source.write_bytes(b'')
        recipe = self.recipe('import gzip,sys; sys.stdout.buffer.write(gzip.compress('
                             'open(sys.argv[1], "rb").read()))')
        result = cenv.apply(recipe, self.source, output_name='result.gz')
        self.assertTrue(result['pass'], result)
        self.assertTrue(result['source_content_verified'])
        self.assertEqual(gzip.decompress((self.root / 'result.gz').read_bytes()), b'')

    def test_truncated_after_first_decompressed_byte_is_refused(self):
        for suffix, compress in (('gz', gzip.compress), ('bz2', bz2.compress), ('xz', lzma.compress)):
            with self.subTest(suffix=suffix):
                payload = compress(self.content)
                code = 'import sys; sys.stdout.buffer.write(bytes.fromhex(%r))' % payload[:-5].hex()
                name = 'result.' + suffix
                result = cenv.apply(self.recipe(code, suffix), self.source, output_name=name)
                self.assertFalse(result['pass'], result)
                self.assertFalse((self.root / name).exists())


if __name__ == '__main__':
    unittest.main()
