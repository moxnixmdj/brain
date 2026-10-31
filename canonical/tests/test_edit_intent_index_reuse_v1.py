"""The real symbol-index output must be reusable without stale or destructive glue."""
import json
import importlib.util
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from canonical.runtime.bound_capabilities import python_issue_nl_parse_edit_intent as intent
from canonical.runtime.bound_capabilities import python_source_symbol_index as index


class EditIntentIndexReuseTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory(prefix='brain-intent-index-')
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.src=self.root/'src'
        (self.src/'pkg').mkdir(parents=True)
        (self.src/'pkg/core.py').write_text('def helper(x): return x+1\n')
        (self.root/'issue.json').write_text(json.dumps({
            'issue_id':'REUSE','title':'Rename helper to compute in pkg/core.py',
        }))
        self.args={'source_root':'src','issue_path':'issue.json','output_path':'intent.json'}
        index.run({'source_root':'src','output_path':'index.json'},self.root)

    def test_standard_producer_cache_matches_fresh_source_relative_edits(self):
        fresh=intent.run(self.args,self.root)
        before=(self.root/'intent.json').read_bytes()
        cached=intent.run(dict(self.args,index_path='index.json'),self.root)
        self.assertTrue(fresh['complete'])
        self.assertTrue(cached['complete'])
        self.assertTrue(cached['cache_used'])
        self.assertEqual((self.root/'intent.json').read_bytes(),before)
        self.assertEqual(json.loads(before)['edits'],[{
            'op':'rename_symbol','module':'pkg/core.py',
            'name':'helper','new_name':'compute',
        }])

    def test_stale_cache_cannot_bind_a_deleted_symbol(self):
        (self.src/'pkg/core.py').write_text('def other(x): return x+1\n')
        with self.assertRaisesRegex(SystemExit,'INDEX_CACHE_SOURCE_STALE'):
            intent.run(dict(self.args,index_path='index.json'),self.root)
        self.assertFalse((self.root/'intent.json').exists())

    def test_fresh_index_preserves_existing_probe_file(self):
        probe=self.src/'.nl_intent_probe_index.json'
        original=b'{"caller_owned":"keep these bytes"}\n'
        probe.write_bytes(original)
        result=intent.run(self.args,self.root)
        self.assertTrue(result['complete'])
        self.assertTrue(probe.exists())
        self.assertEqual(probe.read_bytes(),original)

    def test_failed_index_build_cleans_only_owned_scratch(self):
        before={p.relative_to(self.root) for p in self.root.rglob('*')}
        def failing_build(args,root):
            (Path(root)/args['output_path']).write_text('partial')
            raise RuntimeError('BUILD_INTERRUPTED')
        with patch.object(index,'run',side_effect=failing_build):
            with self.assertRaisesRegex(RuntimeError,'BUILD_INTERRUPTED'):
                intent.run(self.args,self.root)
        self.assertEqual({p.relative_to(self.root) for p in self.root.rglob('*')},before)

    def test_report_preserves_issue_and_its_filesystem_aliases(self):
        issue=self.root/'issue.json'
        original=issue.read_bytes()
        alias=self.root/'issue_alias.json'
        alias.hardlink_to(issue)
        symlink=self.root/'issue_symlink.json'
        symlink.symlink_to(issue)
        for output in ('issue.json','issue_alias.json','issue_symlink.json'):
            with self.subTest(output=output):
                issue.write_bytes(original)
                with self.assertRaisesRegex(SystemExit,'REPORT_OVERWRITES_INPUT'):
                    intent.run(dict(self.args,output_path=output),self.root)
                self.assertEqual(issue.read_bytes(),original)

    def test_report_preserves_its_cached_index(self):
        cache=self.root/'index.json'
        original=cache.read_bytes()
        with self.assertRaisesRegex(SystemExit,'REPORT_OVERWRITES_INPUT'):
            intent.run(dict(self.args,index_path='index.json',output_path='index.json'),self.root)
        self.assertEqual(cache.read_bytes(),original)

    def test_report_preserves_python_source_and_disguised_alias(self):
        source=self.src/'pkg/core.py'
        original=source.read_bytes()
        alias=self.root/'source_alias.json'
        alias.hardlink_to(source)
        with self.assertRaisesRegex(SystemExit,'REPORT_OVERWRITES_INPUT'):
            intent.run(dict(self.args,output_path='source_alias.json'),self.root)
        self.assertEqual(source.read_bytes(),original)
        for output in ('src/pkg/core.py','new_module.py'):
            with self.subTest(output=output):
                with self.assertRaisesRegex(SystemExit,'REPORT_DESTINATION_IS_SOURCE'):
                    intent.run(dict(self.args,output_path=output),self.root)
                self.assertEqual(source.read_bytes(),original)
                self.assertFalse((self.root/'new_module.py').exists())

    def test_unsafe_report_is_refused_before_index_loading(self):
        with patch.object(intent,'_load_index',side_effect=AssertionError('index loaded')):
            with self.assertRaisesRegex(SystemExit,'REPORT_OVERWRITES_INPUT'):
                intent.run(dict(self.args,output_path='issue.json'),self.root)

    def test_ordinary_report_does_not_repeat_source_inventory(self):
        # A validated cache must avoid both rebuilding and an alias-only walk.
        with patch.object(index,'run',side_effect=AssertionError('cache rebuilt')):
            with patch.object(index,'_py_files',wraps=index._py_files) as inventory:
                result=intent.run(dict(self.args,index_path='index.json'),self.root)
        self.assertTrue(result['complete'])
        self.assertEqual(inventory.call_count,1)  # the existing freshness check only

    def test_standard_cached_intent_drives_real_worktree_diff_and_tests(self):
        if importlib.util.find_spec('pytest') is None:
            self.skipTest('real worktree test gate requires pytest')
        from canonical.tests import test_python_issue_nl_parse_edit_intent_v1 as fixtures
        # Reuse the existing multi-file fixture and actual orchestrator. No
        # remote PR is opened: the product here is a tested worktree and diff.
        with TemporaryDirectory(prefix='brain-cached-intent-worktree-') as tmp:
            root=fixtures._make_repo(Path(tmp))
            fixtures._write_issue(root,{
                'issue_id':'CACHED-WORKTREE',
                'title':'Rename helper to compute in pkg/core.py',
            })
            index.run({'source_root':'src','output_path':'index.json'},root)
            cache=(root/'index.json').read_bytes()
            original={p.relative_to(root):p.read_bytes() for p in (root/'src').rglob('*.py')}
            parsed=intent.run({'source_root':'src','issue_path':'issue.json',
                              'index_path':'index.json','output_path':'intent.json'},root)
            self.assertTrue(parsed['complete'])
            self.assertTrue(parsed['cache_used'])
            edits=json.loads((root/'intent.json').read_text())['edits']
            (root/'task.json').write_text(json.dumps({
                'issue_id':'CACHED-WORKTREE','title':'Rename helper to compute',
                'body':'','edits':edits,
            }))
            fixtures.orch.run({
                'task_path':'task.json','source_root':'src','worktree_path':'worktree',
                'output_path':'summary.json','diff_path':'change.diff',
                'pr_intent_path':'pr_intent.json','python_executable':sys.executable,
            },root)
            summary=json.loads((root/'summary.json').read_text())
            self.assertTrue(summary['verified'],summary)
            self.assertGreater(summary['test_selected_count'],0)
            self.assertGreater(summary['test_passed_count'],0)
            self.assertEqual(summary['test_failed_count'],0)
            self.assertIn('+def compute(', (root/'change.diff').read_text())
            self.assertEqual((root/'index.json').read_bytes(),cache)
            self.assertEqual({p.relative_to(root):p.read_bytes() for p in (root/'src').rglob('*.py')},original)


if __name__=='__main__': unittest.main()
