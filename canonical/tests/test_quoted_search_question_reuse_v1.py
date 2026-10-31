"""Question words in quoted operands must not choose the search operation."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from canonical.runtime import composer_route_v1 as route

ROOT=Path(__file__).resolve().parents[2]


class QuotedSearchQuestionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory(dir=ROOT/'canonical/astra_runtime/tmp',prefix='command_operand_')
        self.addCleanup(self.tmp.cleanup)
        self.source=Path(self.tmp.name)/'sample.txt'
        self.source.write_text('total\nwhat changed\nother\n')
        self.rel=self.source.relative_to(ROOT).as_posix()

    def test_commit_message_does_not_state_a_count_or_location_query(self):
        for message in ('fix total','what changed','does it work'):
            with self.subTest(message=message):
                goal=f"Create a git commit in the repository that contains {self.rel} with the message '{message}'."
                self.assertIsNone(route.extract_argv(goal))
        self.assertEqual(self.source.read_text(),'total\nwhat changed\nother\n')

    def test_public_unsupported_commit_request_refuses_without_dispatch(self):
        from canonical.runtime import live_brain_route_admission_v1 as door
        source=self.source.with_suffix('.py')
        source.write_text('def total(values): return sum(values)\n')
        goal=(f'Create a git commit in the repository that contains {source.relative_to(ROOT)} '
              "with the message 'fix total'.")
        self.assertIsNone(route.extract_argv(goal))
        result=door.solve({'task_id':Path(self.tmp.name).name,'goal':goal})
        self.assertFalse(result['pass'],result.get('status'))
        self.assertIs(result.get('executed'),False,result.get('status'))
        self.assertEqual(source.read_text(),'def total(values): return sum(values)\n')
        self.assertNotIn('composer_execution',result)

    def test_broken_source_does_not_authorize_a_quoted_repair(self):
        from canonical.runtime import live_brain_route_admission_v1 as door
        source=Path(self.tmp.name)/'util.py'
        before='def total(values):\n    out = 0\n    for v in values:\n        out = out - v\n    return out\n'
        source.write_text(before)
        goal=(f'Create a git commit in the repository that contains {source.relative_to(ROOT)} '
              "with the message 'fix total'.")
        result=door.solve({'task_id':Path(self.tmp.name).name+'_broken','goal':goal})
        self.assertFalse(result['pass'],result.get('status'))
        self.assertIs(result.get('executed'),False,result.get('status'))
        self.assertEqual(source.read_text(),before)
        self.assertNotIn('composer_execution',result)

    def test_explicit_test_guided_patch_search_still_executes(self):
        from canonical.runtime import live_brain_route_admission_v1 as door
        source=Path(self.tmp.name)/'util.py'
        source.write_text('def total(values):\n    out = 0\n    for v in values:\n        out = out - v\n    return out\n')
        tests=Path(self.tmp.name)/'test_util.py'
        tests.write_text('import unittest, sys, os\nsys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))\nimport util\nclass T(unittest.TestCase):\n    def test_total(self):\n        self.assertEqual(util.total([1,2,3]),6)\nif __name__ == "__main__": unittest.main()\n')
        base=Path(self.tmp.name).relative_to(ROOT).as_posix()
        goal=(f'Find a test guided repair patch for the python source {base}/util.py with the test guided repair loop '
              f'so that the unit tests in {base}/test_util.py pass, and save '
              f'the repair report to {base}/repair.json.')
        result=door.solve({'task_id':Path(self.tmp.name).name+'_repair','goal':goal})
        self.assertTrue(result['pass'],result.get('status'))
        self.assertIs(result.get('executed'),True)
        self.assertNotIn('observed_effect_errors',result)
        patch=result['execution'][0]['result']
        self.assertTrue(patch['source_restored'])
        self.assertIn('out = out - v',source.read_text())
        self.assertIn('+        out = out + v',patch['patches'][0]['unified_diff'])
        self.assertEqual(patch['verification_replays'],[{'pass':True},{'pass':True}])
        self.assertFalse(result['semantic_acceptance_complete'])
        self.assertTrue((Path(self.tmp.name)/'repair.json').is_file())

    def test_swe_instruction_and_effects_ignore_quoted_data(self):
        from canonical.runtime import declared_input_derivation_v1 as derivation
        from canonical.runtime import swe_typed_plan_v1 as typed
        from canonical.runtime import capability_selection_retrieval_v1 as selection
        for message in ('fix total', 'repair bug', 'find every caller'):
            goal=f"Create a git commit containing {self.rel} with message '{message}'."
            with self.subTest(message=message):
                self.assertFalse(derivation.is_swe_request(goal))
                self.assertFalse(typed.is_swe_request(goal))
                self.assertIsNone(selection._effect_winner(goal,[
                    {'capability_id':'python.source.repair.v1'},
                    {'capability_id':'python.source.review.v1'}]))
        self.assertTrue(derivation.is_swe_request(f"Repair {self.rel} with message 'review'."))
        self.assertTrue(typed.is_swe_request(f"Find every caller in {self.rel}."))
        self.assertFalse(typed._effect_consistent(
            f"Review {self.rel} with message 'fix total'.",'python.source.repair.v1'))
        self.assertEqual(selection._effect_winner(
            f"Review {self.rel} with message 'fix total'.",[
                {'capability_id':'python.source.repair.v1'},
                {'capability_id':'python.source.review.v1'}]),'python.source.review.v1')

    def test_actual_count_request_keeps_literal_pattern(self):
        goal=f"How many lines in the file {self.rel} contain 'total'?"
        self.assertEqual(route.extract_argv(goal),['grep','-c','total',self.rel])

    def test_actual_location_request_is_not_turned_into_a_count(self):
        goal=f"Which lines in the file {self.rel} contain 'total'?"
        self.assertEqual(route.extract_argv(goal),['grep','-n','total',self.rel])

    def test_actual_boolean_request_is_not_turned_into_a_count(self):
        goal=f"Does the file {self.rel} contain 'total'?"
        self.assertEqual(route.extract_argv(goal),['grep','-q','total',self.rel])


if __name__=='__main__': unittest.main()
