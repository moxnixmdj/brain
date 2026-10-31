"""Compiled source, not a lossy AST name map, defines real runtime callees."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from canonical.runtime import raw_goal_trace_acceptance_v1 as acceptance
from canonical.runtime.bound_capabilities import python_interprocedural_value_provenance_v1 as provenance


DUPLICATE = ('class A:\n def work(self): return 1\n'
             'class B:\n def work(self): return 2\n')


class ProvenanceCompilerIdentityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(prefix='brain_code_identity_')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / 'm.py'
        self.report = self.root / 'report.json'
        self.args = {'source_root': '.', 'test_paths': ['test_m.py'],
                     'output_path': 'report.json'}

    def produce(self, source):
        self.source.write_text(source)
        (self.root / 'test_m.py').write_text('from m import f\nassert f()==999\n')
        self.result = provenance.run(self.args, self.root)
        self.assertEqual(self.result['failing_test_count'], 1)
        return json.loads(self.report.read_bytes())

    def inspect(self):
        return acceptance._inspect_value_provenance(self.args, self.result, self.root)

    def rewrite(self, data):
        self.report.write_text(json.dumps(data))

    def assert_accepted(self):
        ok, code, info = self.inspect()
        self.assertTrue(ok, (code, info))
        self.assertGreater(info['edges_recomputed'], 0)

    def test_real_lambda_is_accepted_but_nonexistent_lambda_line_is_not(self):
        data = self.produce('helper=lambda x:x+1\ndef f(): return helper(1)\n')
        self.assert_accepted()
        edge = next(row for row in data['ranked_call_edges'] if row['callee']['function'] == '<lambda>')
        edge['callee']['firstlineno'] += 1000
        self.rewrite(data)
        ok, code, _ = self.inspect()
        self.assertFalse(ok)
        self.assertEqual(code, 'PROVENANCE_CALLEE_IS_NOT_DEFINED_WHERE_THE_REPORT_SAYS')

    def test_real_comprehensions_and_generators_are_accepted(self):
        for expression in ('sum(x+1 for x in range(3))',
                           'sum([x+1 for x in range(3)])',
                           'len({x:x+1 for x in range(3)})',
                           'len({x+1 for x in range(3)})'):
            with self.subTest(expression=expression):
                self.produce('def f(): return ' + expression + '\n')
                self.assert_accepted()

    def test_decorator_start_lines_and_class_methods_match_runtime(self):
        self.produce('def identity(fn): return fn\n'
                     '@identity\ndef helper(x): return x+1\n'
                     'class C:\n @classmethod\n def work(cls,x): return helper(x)\n'
                     'def f(): return C.work(1)\n')
        self.assert_accepted()

    def test_same_name_definitions_at_one_callsite_keep_separate_coverage(self):
        data = self.produce(DUPLICATE +
                            'def dispatch(obj): return obj.work()\n'
                            'def f(): return dispatch(A())+dispatch(B())\n')
        edges = [row for row in data['ranked_call_edges'] if row['callee']['function'] == 'work']
        self.assertEqual(len(edges), 2)
        self.assertEqual(len({row['callee']['firstlineno'] for row in edges}), 2)
        self.assertEqual({row['fail_coverage'] for row in edges}, {1})
        self.assert_accepted()

    def test_defined_same_name_substitute_cannot_borrow_another_callees_coverage(self):
        data = self.produce(DUPLICATE + 'def f(): return A().work()\n')
        edge = next(row for row in data['ranked_call_edges'] if row['callee']['function'] == 'work')
        self.assertEqual(edge['callee']['firstlineno'], 2)
        edge['callee']['firstlineno'] = 4  # real B.work exists, but this call never reached it
        self.rewrite(data)
        ok, code, _ = self.inspect()
        self.assertFalse(ok, 'a real but unobserved same-name callee must not pass')
        self.assertEqual(code, 'PROVENANCE_FAIL_COVERAGE_NOT_REPRODUCED_FROM_TRACES')

    def test_coherently_forged_anonymous_trace_still_needs_a_real_code_identity(self):
        data = self.produce('helper=lambda x:x+1\ndef f(): return helper(1)\n')
        self.assert_accepted()
        for edge in data['ranked_call_edges']:
            if edge['callee']['function'] == '<lambda>':
                edge['callee']['firstlineno'] = 1000
        for trace in data['test_traces']:
            for event in trace['events']:
                if event['callee']['function'] == '<lambda>':
                    event['callee']['firstlineno'] = 1000
        self.rewrite(data)
        ok, code, _ = self.inspect()
        self.assertFalse(ok)
        self.assertEqual(code, 'PROVENANCE_CALLEE_IS_NOT_DEFINED_WHERE_THE_REPORT_SAYS')

    def test_ast_def_line_cannot_substitute_for_decorated_runtime_start(self):
        data = self.produce('def identity(fn): return fn\n'
                            '@identity\ndef helper(x): return x+1\n'
                            'def f(): return helper(1)\n')
        self.assert_accepted()
        edge = next(row for row in data['ranked_call_edges'] if row['callee']['function'] == 'helper')
        self.assertEqual(edge['callee']['firstlineno'], 2)
        edge['callee']['firstlineno'] = 3
        self.rewrite(data)
        ok, code, _ = self.inspect()
        self.assertFalse(ok)
        self.assertEqual(code, 'PROVENANCE_CALLEE_IS_NOT_DEFINED_WHERE_THE_REPORT_SAYS')

    def test_reinspection_does_not_execute_source(self):
        marker = self.root / 'source_executed'
        self.produce(f'from pathlib import Path\nPath({str(marker)!r}).touch()\n'
                     'def f(): return 1\n')
        self.assertTrue(marker.exists(), 'actual suite must have executed the source')
        marker.unlink()
        self.assert_accepted()
        self.assertFalse(marker.exists(), 'source validation must not execute it again')


if __name__ == '__main__':
    unittest.main()
