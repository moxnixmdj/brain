"""Tests exercise advisory hints, not repair admission or effect verification."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from canonical.tools import swebench_issue_localizer_v1 as loc


class LocalizerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.put('pkg/thing.py', 'def repair():\n    return 1\n')
        self.put('tests/test_thing.py', 'def test_repair():\n    pass\n')

    def tearDown(self):
        self.temp.cleanup()

    def put(self, name, text):
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def test_explicit_references(self):
        r = loc.localize_issue('In pkg/thing.py, function repair fails. See tests/test_thing.py.', self.root)
        self.assertEqual(r['authority'], 'NONE__ADVISORY_ONLY')
        self.assertEqual(r['target_path']['value'], 'pkg/thing.py')
        self.assertEqual(r['symbol']['value'], 'repair')
        self.assertEqual(r['test_target']['value'], 'tests/test_thing.py')

    def test_explicit_subset_requires_all_three_explicit_references(self):
        full = loc.localize_issue('pkg/thing.py function repair; tests/test_thing.py', self.root)
        self.assertEqual(loc.explicit_input_candidates(full), {
            'target_path': 'pkg/thing.py', 'symbol': 'repair', 'test_target': 'tests/test_thing.py'})
        guessed_test = loc.localize_issue('pkg/thing.py function repair', self.root)
        self.assertIsNone(loc.explicit_input_candidates(guessed_test))
        guessed_path = loc.localize_issue('repair() tests/test_thing.py', self.root)
        self.assertIsNone(loc.explicit_input_candidates(guessed_path))
        self.assertIsNone(loc.explicit_input_candidates(loc.localize_issue('missing.py', self.root)))

    def test_symbol_only_and_test_filename(self):
        r = loc.localize_issue('Calling repair() fails.', self.root)
        self.assertEqual(r['target_path']['value'], 'pkg/thing.py')
        self.assertEqual(r['symbol']['value'], 'repair')
        self.assertEqual(r['test_target']['value'], 'tests/test_thing.py')
        self.assertEqual(r['test_target']['basis'], 'MATCHING_TEST_FILENAME_HEURISTIC')

    def test_missing_and_ambiguous(self):
        r = loc.localize_issue('A vague issue with no evidence.', self.root)
        self.assertEqual([r[k]['status'] for k in ('target_path', 'symbol', 'test_target')], ['MISSING'] * 3)
        self.put('other/thing.py', 'def repair():\n    pass\n')
        r = loc.localize_issue('thing.py: repair() fails', self.root)
        self.assertEqual(r['target_path']['status'], 'AMBIGUOUS')
        self.assertIsNone(r['target_path']['value'])
        r = loc.localize_issue('repair() fails', self.root)
        self.assertEqual(r['target_path']['status'], 'AMBIGUOUS')
        self.assertIsNone(r['symbol']['value'])
        r = loc.localize_issue('missing.py has function repair', self.root)
        self.assertEqual(r['reason'], 'PATH_REFERENCE_UNRESOLVED_OR_UNSAFE')
        self.assertIsNone(r['target_path']['value'])

    def test_duplicate_definition_and_test_ambiguity(self):
        self.put('pkg/thing.py', 'def repair(): pass\ndef repair(): pass\n')
        self.put('other/test_thing.py', 'pass\n')
        r = loc.localize_issue('pkg/thing.py function repair', self.root)
        self.assertEqual(r['symbol']['status'], 'AMBIGUOUS')
        self.assertEqual(r['test_target']['status'], 'AMBIGUOUS')
        self.assertIsNone(r['symbol']['value'])
        self.assertIsNone(r['test_target']['value'])

    def test_ranked_results_use_import_and_evidence_without_claiming_authority(self):
        self.put('other/thing.py', 'def repair():\n    pass\n')
        self.put('docs/noise.py', 'def repair():\n    pass\n')
        self.put('vendor/noise.py', 'def repair():\n    pass\n')
        issue = 'repair fails\nfrom pkg.thing import repair\nrepair()'
        r = loc.localize_issue(issue, self.root)
        self.assertEqual(r['target_path']['status'], 'AMBIGUOUS')
        ranked = r['ranked_candidates']
        self.assertTrue(ranked['scan_complete'])
        self.assertEqual(ranked['target_paths'][0]['path'], 'pkg/thing.py')
        self.assertIn('import_module:pkg/thing', ranked['target_paths'][0]['evidence'])
        self.assertNotIn('docs/noise.py', str(ranked))
        self.assertNotIn('vendor/noise.py', str(ranked))
        self.assertEqual(ranked['authority'], 'NONE__ADVISORY_ONLY')
        self.assertIsNone(loc.explicit_input_candidates(r))

    def test_quoted_source_line_ranks_enclosing_function(self):
        self.put('pkg/example.py', 'def convert(data):\n    result = data + 123456789012345\n    return result\n')
        r = loc.localize_issue('Broken conversion\n    result = data + 123456789012345', self.root)
        top = r['ranked_candidates']['target_paths'][0]
        self.assertEqual(top['path'], 'pkg/example.py')
        self.assertEqual(top['symbols'], ['convert'])
        self.assertIn('quoted_source_lines:1', top['evidence'])

    def test_tie_order_is_lexical_and_top_k_is_bounded(self):
        for i in range(15):
            self.put(f'p{i:02d}/same.py', 'def repair(): pass\n')
        r = loc.localize_issue('repair() fails', self.root)
        ranked = r['ranked_candidates']['target_paths']
        self.assertEqual(len(ranked), loc.TOP_K)
        self.assertEqual([x['path'] for x in ranked], sorted(x['path'] for x in ranked))
        self.assertEqual(r['target_path']['status'], 'AMBIGUOUS')

    def test_partial_scan_retains_ranked_suggestions_not_unique_authority(self):
        self.put('other/thing.py', 'def repair(): pass\n')
        with patch.object(loc, 'MAX_SOURCE_FILES', 1):
            r = loc.localize_issue('from pkg.thing import repair\nrepair()', self.root)
        self.assertFalse(r['ranked_candidates']['scan_complete'])
        self.assertGreater(r['ranked_candidates']['omitted_files'], 0)
        self.assertEqual(r['ranked_candidates']['target_paths'][0]['path'], 'pkg/thing.py')
        self.assertEqual(r['target_path']['status'], 'INCOMPLETE')
        self.assertIsNone(r['target_path']['value'])

    def test_unsafe_paths_and_symlinks_are_never_read(self):
        (self.root / 'link.py').symlink_to(self.root.parent / 'external.py')
        (self.root / 'linked_dir').symlink_to(self.root.parent, target_is_directory=True)
        for text in ('../external.py function repair', '/etc/external.py', 'link.py', 'linked_dir/external.py', r'..\external.py function repair'):
            r = loc.localize_issue(text, self.root)
            self.assertEqual(r['status'], 'NOT_LOCATED', text)
            self.assertEqual(r['reason'], 'PATH_REFERENCE_UNRESOLVED_OR_UNSAFE')
        with self.assertRaises(loc.LocalizationUnavailable):
            fd = __import__('os').open(self.root, __import__('os').O_RDONLY | __import__('os').O_DIRECTORY)
            try:
                loc._read_python(fd, 'link.py')
            finally:
                __import__('os').close(fd)

    def test_deterministic_and_bounded(self):
        query = 'pkg/thing.py function repair'
        self.assertEqual(loc.localize_issue(query, self.root), loc.localize_issue(query, self.root))
        self.assertEqual(loc.localize_issue('x' * (loc.MAX_STATEMENT_CHARS + 1), self.root)['reason'], 'PROBLEM_STATEMENT_LIMIT')
        with patch.object(loc, 'MAX_ENTRIES', 1):
            self.assertEqual(loc.localize_issue(query, self.root)['reason'], 'TREE_ENTRY_LIMIT')
        with patch.object(loc, 'MAX_SOURCE_FILES', 0):
            limited = loc.localize_issue('repair()', self.root)
            self.assertFalse(limited['ranked_candidates']['scan_complete'])
            self.assertEqual(limited['ranked_candidates']['scanned_files'], 0)
            self.assertIsNone(limited['target_path']['value'])
        with patch.object(loc, 'MAX_FILE_BYTES', 2):
            self.assertEqual(loc.localize_issue(query, self.root)['reason'], 'SOURCE_FILE_TOO_LARGE_OR_INVALID')


if __name__ == '__main__':
    unittest.main()
