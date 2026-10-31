"""Current filesystem bytes, not cache schema labels, are the freshness oracle."""
import contextlib
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from canonical.runtime.bound_capabilities import python_source_symbol_index as index
from canonical.runtime.bound_capabilities import python_change_impact_testselect as impact
from canonical.runtime.bound_capabilities import python_crossfile_edit_choreograph as choreography
from canonical.runtime.bound_capabilities import python_symbol_resolve as resolver


class PythonCacheFreshnessTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(prefix='brain-python-cache-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.src = self.root / 'src'
        (self.src / 'tests').mkdir(parents=True)
        (self.src / 'calc.py').write_text('def add(a,b):\n    return a+b\n')
        (self.src / 'tests/test_direct.py').write_text(
            'from calc import add\ndef test_direct(): assert add(1,2)==3\n')
        (self.src / 'tests/test_later.py').write_text("def test_later(): assert 'x'.upper() == 'X'\n")
        self.cache = self.root / 'index.json'
        self.build()

    def build(self):
        index.run({'source_root': 'src', 'output_path': 'index.json'}, self.root)

    def loaders(self):
        return (
            lambda: impact._load_index(self.root, self.src, self.root, self.cache),
            lambda: choreography._load_index(self.root, self.src, self.cache, 'src'),
            lambda: resolver._load_index(self.root, self.src, self.root, self.cache),
        )

    def assert_stale(self):
        for number, load in enumerate(self.loaders()):
            with self.subTest(consumer=number), contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises((RuntimeError, SystemExit)):
                    load()

    def test_changed_test_dependency_is_refused_by_all_consumers(self):
        (self.src / 'tests/test_later.py').write_text(
            'from calc import add\ndef test_later(): assert add(2,2)==4\n')
        self.assert_stale()
        args = {'source_root': 'src', 'index_path': 'index.json',
                'changed_paths': ['src/calc.py'], 'test_roots': ['src/tests'],
                'output_path': 'selection.json'}
        with self.assertRaisesRegex(RuntimeError, 'INDEX_CACHE'):
            impact.run(args, self.root)
        self.assertFalse((self.root / 'selection.json').exists())
        self.build()
        impact.run(args, self.root)
        selected = json.loads((self.root / 'selection.json').read_text())
        self.assertIn('src/tests/test_later.py', selected['selected_tests'])

    def test_added_test_is_refused(self):
        (self.src / 'tests/test_new.py').write_text('import calc\n')
        self.assert_stale()

    def test_deleted_file_is_refused(self):
        (self.src / 'tests/test_later.py').unlink()
        self.assert_stale()

    def test_renamed_file_is_refused(self):
        p = self.src / 'tests/test_later.py'
        p.rename(p.with_name('test_renamed.py'))
        self.assert_stale()

    def test_duplicate_row_is_refused(self):
        artifact = json.loads(self.cache.read_text())
        artifact['modules'].append(dict(artifact['modules'][0]))
        self.cache.write_text(json.dumps(artifact))
        self.assert_stale()

    def test_unparseable_file_is_part_of_freshness_manifest(self):
        broken = self.src / 'broken.py'
        broken.write_text('def broken(\n')
        self.build()
        for load in self.loaders():
            load()
        broken.write_text('def fixed(): return 1\n')
        self.assert_stale()

    def test_unchanged_cache_reuses_semantics_without_reparse(self):
        (self.src / 'report.json').write_text('{}')
        before = self.cache.read_bytes()
        with patch.object(index, 'run', side_effect=AssertionError('cache rebuilt')), \
             patch.object(index.ast, 'parse', side_effect=AssertionError('source reparsed')):
            for load in self.loaders():
                load()
        self.assertEqual(self.cache.read_bytes(), before)

    def test_missing_digest_is_refused(self):
        artifact = json.loads(self.cache.read_text())
        del artifact['modules'][0]['sha256']
        self.cache.write_text(json.dumps(artifact))
        self.assert_stale()

    def test_single_file_scope_ignores_unrelated_sibling(self):
        source = self.src / 'calc.py'
        index.run({'source_root': 'src/calc.py', 'output_path': 'single.json'}, self.root)
        artifact = json.loads((self.root / 'single.json').read_text())
        (self.src / 'unrelated.py').write_text('value = 1\n')
        index.validate_cached_index(self.root, source, artifact)
        source.write_text('def add(a,b): return a-b\n')
        with self.assertRaisesRegex(RuntimeError, 'INDEX_CACHE_SOURCE_STALE'):
            index.validate_cached_index(self.root, source, artifact)

    def test_same_size_mtime_restoration_does_not_hide_source_change(self):
        import os
        p = self.src / 'calc.py'
        stat = p.stat()
        p.write_text(p.read_text().replace('a+b', 'a-b'))
        os.utime(p, ns=(stat.st_atime_ns, stat.st_mtime_ns))
        self.assert_stale()


if __name__ == '__main__':
    unittest.main()
