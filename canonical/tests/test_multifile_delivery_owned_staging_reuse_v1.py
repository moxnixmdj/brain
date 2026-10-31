"""Real multi-file delivery must preserve user metadata and own its staging files."""
import ast
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from canonical.runtime.bound_capabilities import python_repair_apply_verified_v1 as apply


class DeliveryOwnedStagingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(prefix='brain_multifile_delivery_')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / 'module.py'
        self.source.write_bytes(b'original source\n')
        self.legacy_stage = self.root / 'module.py.brain_apply_tmp'

    def assert_no_owned_stage(self):
        self.assertEqual(list(self.root.glob('*.brain_apply_tmp.*')), [])

    def test_existing_fixed_name_staging_file_is_not_consumed(self):
        self.legacy_stage.write_bytes(b'preexisting user work')
        apply._atomic_write(self.source, b'new source\n')
        self.assertEqual(self.source.read_bytes(), b'new source\n')
        self.assertTrue(self.legacy_stage.exists())
        self.assertEqual(self.legacy_stage.read_bytes(), b'preexisting user work')
        self.assert_no_owned_stage()

    @unittest.skipUnless(os.name == 'posix', 'POSIX source permissions')
    def test_atomic_source_replacement_preserves_permission_bits(self):
        self.source.chmod(0o751)
        apply._atomic_write(self.source, b'new source\n')
        self.assertEqual(stat.S_IMODE(self.source.stat().st_mode), 0o751)
        self.assert_no_owned_stage()

    @unittest.skipUnless(os.name == 'posix', 'POSIX symlink semantics')
    def test_existing_staging_symlink_cannot_redirect_writes(self):
        unrelated = self.root / 'unrelated.txt'
        unrelated.write_bytes(b'user data')
        self.legacy_stage.symlink_to(unrelated)
        apply._atomic_write(self.source, b'new source\n')
        self.assertEqual(unrelated.read_bytes(), b'user data')
        self.assertFalse(self.source.is_symlink())
        self.assertTrue(self.legacy_stage.is_symlink())
        self.assertEqual(self.source.read_bytes(), b'new source\n')
        self.assert_no_owned_stage()

    def test_existing_staging_hardlink_cannot_overwrite_other_data(self):
        unrelated = self.root / 'unrelated.txt'
        unrelated.write_bytes(b'user data')
        os.link(unrelated, self.legacy_stage)
        apply._atomic_write(self.source, b'new source\n')
        self.assertEqual(unrelated.read_bytes(), b'user data')
        self.assertTrue(self.legacy_stage.samefile(unrelated))
        self.assertFalse(self.source.samefile(unrelated))
        self.assert_no_owned_stage()

    def test_replace_failure_cleans_only_owned_staging_and_keeps_source(self):
        self.legacy_stage.write_bytes(b'preexisting user work')
        mode = stat.S_IMODE(self.source.stat().st_mode)
        # Explicit negative fault injection, not a fabricated successful run.
        with patch.object(apply.os, 'replace', side_effect=OSError('publication refused')):
            with self.assertRaisesRegex(OSError, 'publication refused'):
                apply._atomic_write(self.source, b'new source\n')
        self.assertEqual(self.source.read_bytes(), b'original source\n')
        self.assertEqual(stat.S_IMODE(self.source.stat().st_mode), mode)
        self.assertTrue(self.legacy_stage.exists())
        self.assertEqual(self.legacy_stage.read_bytes(), b'preexisting user work')
        self.assert_no_owned_stage()

    @unittest.skipUnless(hasattr(os, 'fchmod'), 'descriptor permission changes')
    def test_permission_failure_happens_before_publication_and_cleans_staging(self):
        self.source.chmod(0o751)
        with patch.object(apply.os, 'fchmod', side_effect=PermissionError('mode refused')):
            with self.assertRaisesRegex(PermissionError, 'mode refused'):
                apply._atomic_write(self.source, b'new source\n')
        self.assertEqual(self.source.read_bytes(), b'original source\n')
        self.assertEqual(stat.S_IMODE(self.source.stat().st_mode), 0o751)
        self.assert_no_owned_stage()

    def test_invalid_write_payload_does_not_leave_owned_staging(self):
        with self.assertRaises(TypeError):
            apply._atomic_write(self.source, object())
        self.assertEqual(self.source.read_bytes(), b'original source\n')
        self.assertFalse(self.legacy_stage.exists())
        self.assert_no_owned_stage()

    @unittest.skipUnless(os.name == 'posix', 'POSIX metadata with real coupled repair')
    def test_real_two_package_repair_persists_and_preserves_metadata_and_user_work(self):
        self.source.unlink()  # helper-unit placeholder is not part of this repository task
        self.exercise_pair()

    @unittest.skipUnless(os.name == 'posix', 'POSIX public delivery')
    def test_public_request_delivers_two_package_repair_with_unchanged_native_tests(self):
        repo = Path(__file__).resolve().parents[2]
        with TemporaryDirectory(dir=repo / 'canonical/astra_runtime/tmp',
                                prefix='multifile_delivery_') as directory:
            self.root = Path(directory)
            self.exercise_pair(public=True)

    @unittest.skipUnless(os.name == 'posix', 'POSIX multi-file rollback')
    def test_real_second_publication_failure_restores_both_files_and_modes(self):
        self.source.unlink()
        self.exercise_pair(fail_second=True)

    def exercise_pair(self, public=False, fail_second=False):
        for package, function, body in (('lower', 'allows', 'x < 3'),
                                        ('upper', 'accepts', 'x > 5')):
            folder = self.root / package
            folder.mkdir()
            (folder / '__init__.py').touch()
            (folder / 'bounds.py').write_text(f'def {function}(x):\n    return {body}\n')
        lower = self.root / 'lower/bounds.py'
        upper = self.root / 'upper/bounds.py'
        lower.chmod(0o751)
        upper.chmod(0o640)
        tests = self.root / 'tests'
        tests.mkdir()
        suite = tests / 'test_bounds.py'
        suite.write_text('import unittest\nfrom lower.bounds import allows\n'
                         'from upper.bounds import accepts\n'
                         'class T(unittest.TestCase):\n'
                         ' def test_boundaries(self):\n'
                         '  self.assertEqual((allows(3),accepts(5)),(True,True))\n'
                         '  self.assertTrue(allows(2.9)); self.assertTrue(accepts(5.1))\n'
                         '  self.assertFalse(allows(3.1)); self.assertFalse(accepts(4.9))\n')
        original_tests = suite.read_bytes()
        config = self.root / 'settings.json'
        config.write_bytes(b'{"user_configuration":"preserve"}')
        user_stage = lower.with_name('bounds.py.brain_apply_tmp')
        user_stage.write_bytes(b'uncommitted user work')
        native = [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'tests']
        before = subprocess.run(native, cwd=self.root, capture_output=True, timeout=15)
        self.assertNotEqual(before.returncode, 0)
        if fail_second:
            originals = {p: (p.read_bytes(), stat.S_IMODE(p.stat().st_mode)) for p in (lower, upper)}
            real_replace = os.replace
            first_writes = []

            def refuse_second(source, destination):
                if Path(destination) == upper:
                    raise OSError('second source publication refused')
                value = real_replace(source, destination)
                if Path(destination) == lower:
                    first_writes.append(lower.read_bytes())
                return value

            # Only inject a filesystem publication error; search and its tests
            # execute normally, and the first replacement really reaches disk.
            with patch.object(apply.os, 'replace', side_effect=refuse_second):
                with self.assertRaisesRegex(OSError, 'second source publication refused'):
                    apply.run({'source_root': '.', 'output_path': 'report.json',
                               'timeout_s': 3, 'mutations_per_file': 12,
                               'max_pair_candidates': 300}, self.root)
            # Both candidate publication and restoration now use the owned
            # atomic writer: observe the actual candidate, then exact original.
            self.assertEqual(len(first_writes), 2)
            self.assertNotEqual(first_writes[0], originals[lower][0])
            self.assertEqual(first_writes[1], originals[lower][0])
            for path, (raw, mode) in originals.items():
                self.assertEqual(path.read_bytes(), raw)
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), mode)
            self.assertEqual(suite.read_bytes(), original_tests)
            self.assertEqual(user_stage.read_bytes(), b'uncommitted user work')
            self.assertEqual(config.read_bytes(), b'{"user_configuration":"preserve"}')
            self.assertFalse((self.root / 'report.json').exists())
            self.assertEqual(list(self.root.rglob('*.brain_apply_tmp.*')), [])
            self.assertNotEqual(subprocess.run(native, cwd=self.root, capture_output=True,
                                              timeout=15).returncode, 0)
            return
        if public:
            from canonical.runtime import live_brain_route_admission_v1 as door
            repo = Path(__file__).resolve().parents[2]
            rel = self.root.relative_to(repo).as_posix()
            goal = (f'Repair the python source root {rel} so the unit tests in '
                    f'{rel}/tests/test_bounds.py pass, apply the fix in place, '
                    f'and save the repair report to {rel}/report.json.')
            outer = door.solve({'task_id': self.root.name, 'goal': goal})
            self.assertTrue(outer['pass'], outer.get('status'))
            self.assertIs(outer['executed'], True)
            self.assertEqual(outer['compiled_capability_id'], apply.CAPABILITY_ID)
            self.assertFalse(outer['semantic_acceptance_complete'])
            result = json.loads((self.root / 'report.json').read_bytes())
        else:
            result = apply.run({'source_root': '.', 'output_path': 'report.json',
                                'timeout_s': 3, 'mutations_per_file': 12,
                                'max_pair_candidates': 300}, self.root)
        self.assertTrue(result['pass'], result)
        self.assertTrue(result['applied'])
        written = {str(Path(name).relative_to(rel)) if public else name
                   for name in result['files_written']}
        self.assertEqual(written, {'lower/bounds.py', 'upper/bounds.py'})
        after = subprocess.run(native, cwd=self.root, capture_output=True, timeout=15)
        self.assertEqual(after.returncode, 0, after.stderr)
        self.assertEqual(suite.read_bytes(), original_tests)
        self.assertEqual(config.read_bytes(), b'{"user_configuration":"preserve"}')
        self.assertIsInstance(ast.parse(lower.read_bytes()).body[0].body[0].value.ops[0], ast.LtE)
        self.assertIsInstance(ast.parse(upper.read_bytes()).body[0].body[0].value.ops[0], ast.GtE)
        self.assertEqual(stat.S_IMODE(lower.stat().st_mode), 0o751)
        self.assertEqual(stat.S_IMODE(upper.stat().st_mode), 0o640)
        self.assertTrue(user_stage.exists())
        self.assertEqual(user_stage.read_bytes(), b'uncommitted user work')
        report = json.loads((self.root / 'report.json').read_bytes())
        self.assertEqual(report['pre_apply_test_returncode'], 1)
        self.assertEqual(report['post_apply_test_returncode'], 0)
        self.assertEqual(list(self.root.rglob('*.brain_apply_tmp.*')), [])


if __name__ == '__main__':
    unittest.main()
