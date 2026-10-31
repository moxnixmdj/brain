"""Chain actual engines; reports alone cannot establish delivered software."""
import ast
import contextlib
import io
import json
from pathlib import Path
import sys
import shutil
from tempfile import TemporaryDirectory
import unittest

from canonical.runtime.bound_capabilities import file_write_text as writer
from canonical.runtime.bound_capabilities import python_source_symbol_index as index
from canonical.runtime.bound_capabilities import python_crossfile_edit_choreograph as planner
from canonical.runtime.bound_capabilities import python_change_impact_testselect as selector
from canonical.runtime.bound_capabilities import python_refactor_rename_symbol as rename
from canonical.runtime.bound_capabilities import python_repair_apply_verified_v1 as delivery


class CrossfileWorkflowExecutionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(prefix='crossfile-workflow-execution-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        files = {
            'kernel/__init__.py': '',
            'kernel/core.py': 'def helper(x): return x+1\n',
            'application/__init__.py': '',
            'application/service.py': 'from kernel.core import helper\ndef invoice(x): return helper(x)*2\n',
            'gateway/__init__.py': '',
            'gateway/api.py': 'from application.service import invoice\ndef quote(x): return {"total": invoice(x)}\n',
            'tests/test_service.py': 'from application.service import invoice\ndef test_service(): assert invoice(2)==6\n',
            'tests/test_api.py': 'from gateway.api import quote\ndef test_api(): assert quote(2)=={"total": 6}\n',
            'tests/test_unrelated.py': 'def test_unrelated(): assert 2+2==4\n',
        }
        for name, text in files.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(text.encode())
        (self.root / 'kernel/core.py').chmod(0o640)
        self.originals = self.sources()

    def sources(self):
        return {p.relative_to(self.root).as_posix(): p.read_bytes()
                for p in self.root.rglob('*.py')}

    def run_python(self, *args):
        rc, output = delivery._run_test([sys.executable, '-B', *args], self.root, 20)
        self.assertEqual(rc, 0, output.decode(errors='replace'))

    def build_index(self, output='reports/index.json'):
        result = index.run({'source_root': '.', 'output_path': output}, self.root)
        self.assertTrue(result['output_verified'])
        self.assertEqual(result['unparseable_count'], 0)

    def plan(self):
        result = planner.run({'source_root': '.', 'index_path': 'reports/index.json',
                              'output_path': 'reports/plan.json',
                              'edits': [{'op': 'rename_symbol', 'module': 'kernel/core.py',
                                         'name': 'helper', 'new_name': 'compute'}]}, self.root)
        self.assertTrue(result['cache_used'])
        self.assertEqual(result['planned_op_count'], 1)
        self.assertEqual(result['refused_op_count'], 0)
        report = json.loads((self.root / 'reports/plan.json').read_bytes())
        self.assertTrue(report['complete'])
        self.assertEqual(set(report['affected_files']), {'kernel/core.py', 'application/service.py'})
        return report

    def select(self, changed, index_path='reports/index.json', output='reports/selection.json'):
        result = selector.run({'source_root': '.', 'index_path': index_path,
                               'changed_paths': changed, 'output_path': output}, self.root)
        self.assertTrue(result['output_verified'])
        return json.loads((self.root / output).read_bytes())['selected_tests']

    def execute(self, tests):
        with contextlib.redirect_stdout(io.StringIO()):
            return rename.run({'source_root': '.', 'module': 'kernel/core.py',
                               'qualname': 'helper', 'new_symbol': 'compute',
                               'run_tests': tests, 'output_path': 'reports/delivery.json'}, self.root)

    def test_real_index_plan_selection_delivery_and_fresh_acceptance(self):
        self.run_python('-m', 'pytest', '-q', '-p', 'no:cacheprovider', 'tests')
        self.build_index()
        planned = self.plan()
        selected = self.select(planned['affected_files'])
        self.assertEqual(set(selected), {'tests/test_service.py', 'tests/test_api.py'})
        selection = json.loads((self.root / 'reports/selection.json').read_bytes())
        self.assertEqual(selection['totals']['candidate_tests'], 3)
        self.assertEqual(selection['totals']['selected_tests'], 2)
        result = self.execute(selected)
        self.assertTrue(result['verified'])
        self.assertTrue(result['complete'])
        self.assertEqual(set(result['files_edited']), set(planned['affected_files']))
        expected = dict(self.originals)
        expected['kernel/core.py'] = b'def compute(x): return x+1\n'
        expected['application/service.py'] = b'from kernel.core import compute\ndef invoice(x): return compute(x)*2\n'
        self.assertEqual(self.sources(), expected)
        self.assertEqual((self.root / 'kernel/core.py').stat().st_mode & 0o777, 0o640)
        # An old pre-edit index cannot justify post-edit test selection.
        with self.assertRaisesRegex(RuntimeError, 'INDEX_CACHE_SOURCE_STALE'):
            self.select(result['files_edited'], output='reports/stale-selection.json')
        self.assertFalse((self.root / 'reports/stale-selection.json').exists())
        self.build_index('reports/post-index.json')
        self.assertEqual(self.select(result['files_edited'], 'reports/post-index.json',
                                     'reports/post-selection.json'), selected)
        self.run_python('-m', 'pytest', '-q', '-p', 'no:cacheprovider', 'tests')
        self.run_python('-c', 'from gateway.api import quote; from kernel import core; '
                        'assert quote(7)=={"total":16}; assert core.compute(7)==8; '
                        'assert not hasattr(core,"helper")')
        self.assertEqual(self.sources(), expected)

    def test_red_dynamic_contract_rolls_back_and_original_index_is_valid(self):
        test = self.root / 'tests/test_dynamic.py'
        test.write_bytes(b'import kernel.core as core\ndef test_dynamic():\n'
                         b'    assert getattr(core,"helper")(2)==3\n')
        before = self.sources()
        self.run_python('-m', 'pytest', '-q', '-p', 'no:cacheprovider', 'tests')
        self.build_index()
        selected = self.select(['kernel/core.py', 'application/service.py'])
        self.assertIn('tests/test_dynamic.py', selected)
        with self.assertRaisesRegex(SystemExit, 'TESTS_RED_AFTER_EDIT'):
            self.execute(selected)
        self.assertEqual(self.sources(), before)
        self.assertFalse((self.root / 'reports/delivery.json').exists())
        self.assertEqual((self.root / 'kernel/core.py').stat().st_mode & 0o777, 0o640)
        self.assertEqual(self.select(['kernel/core.py', 'application/service.py']), selected)
        self.run_python('-m', 'pytest', '-q', '-p', 'no:cacheprovider', 'tests')

    def test_existing_doctest_gate_refuses_incomplete_documented_api_rename(self):
        core = self.root / 'kernel/core.py'
        core.write_bytes(b'def helper(x):\n    """Example.\n\n'
                         b'    >>> helper(2)\n    3\n    """\n    return x+1\n')
        before = self.sources()
        self.run_python('-m', 'pytest', '-q', '-p', 'no:cacheprovider',
                        '--doctest-modules', 'kernel/core.py', 'tests')
        self.build_index()
        planned = self.plan()
        selected = self.select(planned['affected_files'])
        with self.assertRaisesRegex(SystemExit, 'TESTS_RED_AFTER_EDIT'):
            self.execute(['--doctest-modules', 'kernel/core.py', *selected])
        self.assertEqual(self.sources(), before)
        self.assertFalse((self.root / 'reports/delivery.json').exists())
        self.run_python('-m', 'pytest', '-q', '-p', 'no:cacheprovider',
                        '--doctest-modules', 'kernel/core.py', 'tests')

    def test_staged_code_and_example_edit_passes_frozen_acceptance(self):
        core = self.root / 'kernel/core.py'
        core.write_bytes(b'outside = "helper("\ndef helper(x):\n    """Example.\n\n'
                         b'    >>> helper(2)\n    3\n    """\n    return x+1\n')
        original_root = self.root
        original = self.sources()
        self.run_python('-m', 'pytest', '-q', '-p', 'no:cacheprovider',
                        '--doctest-modules', 'kernel/core.py', 'tests')
        with TemporaryDirectory(prefix='crossfile-staged-completion-') as tmp:
            candidate = Path(tmp) / 'project'
            shutil.copytree(original_root, candidate,
                            ignore=shutil.ignore_patterns('__pycache__', '.pytest_cache'))
            self.assertEqual(list(candidate.rglob('*.pyc')), [])
            self.root = candidate
            try:
                self.build_index()
                selected = self.select(self.plan()['affected_files'])
                self.assertTrue(self.execute(selected)['verified'])
                target = candidate / 'kernel/core.py'
                raw = target.read_bytes()
                function = next(n for n in ast.parse(raw).body
                                if isinstance(n, ast.FunctionDef) and n.name == 'compute')
                doc = function.body[0].value
                self.assertIsInstance(doc, ast.Constant)
                self.assertIsInstance(doc.value, str)
                offset = delivery._REPAIR._PATCH._byte_offset
                lines = raw.splitlines(keepends=True)
                start = offset(lines, doc.lineno, doc.col_offset)
                end = offset(lines, doc.end_lineno, doc.end_col_offset)
                segment = raw[start:end]
                self.assertEqual(segment.count(b'>>> helper('), 1)
                updated = raw[:start] + segment.replace(b'>>> helper(', b'>>> compute(') + raw[end:]
                result = writer.run({'output_path': 'kernel/core.py',
                                     'content': updated.decode('utf-8')}, candidate)
                self.assertTrue(result['output_verified'])
                self.run_python('-m', 'pytest', '-q', '-p', 'no:cacheprovider',
                                '--doctest-modules', 'kernel/core.py', 'tests')
                self.run_python('-c', 'from gateway.api import quote; from kernel import core; '
                                'assert quote(7)=={"total":16}; assert not hasattr(core,"helper")')
                expected = dict(original)
                expected['kernel/core.py'] = original['kernel/core.py'].replace(
                    b'def helper(', b'def compute(').replace(b'>>> helper(', b'>>> compute(')
                expected['application/service.py'] = original['application/service.py'].replace(
                    b'helper', b'compute')
                self.assertEqual(self.sources(), expected)
                self.assertEqual((candidate / 'kernel/core.py').stat().st_mode & 0o777, 0o640)
            finally:
                self.root = original_root
        self.assertEqual(self.sources(), original)

    def test_stale_plan_cannot_authorize_writes_or_discard_user_edit(self):
        self.build_index()
        core = self.root / 'kernel/core.py'
        core.write_bytes(core.read_bytes() + b'# external edit after indexing\n')
        before = self.sources()
        diagnostic = io.StringIO()
        with contextlib.redirect_stdout(diagnostic):
            with self.assertRaises(SystemExit) as failure:
                self.plan()
        self.assertEqual(failure.exception.code, 1)
        self.assertEqual(json.loads(diagnostic.getvalue())['message'],
                         'INDEX_CACHE_SOURCE_STALE:kernel/core.py')
        self.assertEqual(self.sources(), before)
        self.assertFalse((self.root / 'reports/plan.json').exists())
        self.assertFalse((self.root / 'reports/delivery.json').exists())


if __name__ == '__main__':
    unittest.main()
