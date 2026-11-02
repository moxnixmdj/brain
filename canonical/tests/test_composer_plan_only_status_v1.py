"""A reachable type plan is not a completed job."""
import unittest

from canonical.runtime import composer_route_v1 as composer


class ComposerPlanOnlyStatusTests(unittest.TestCase):
    def test_regular_plan_states_no_execution_or_goal_acceptance(self):
        result = composer.route('write the text hello to out.txt')
        self.assertTrue(result['pass'])  # route reachability only
        self.assertEqual(result['authority'], 'TYPE_LEVEL_COMPOSITION_REACHABLE')
        self.assertFalse(result['executed'])
        self.assertFalse(result['semantic_acceptance_complete'])

    def test_stated_command_plan_states_no_execution_or_goal_acceptance(self):
        result = composer.route('copy the file one.txt to two.txt')
        self.assertTrue(result['pass'])
        self.assertEqual(result['authority'], 'TYPE_LEVEL_COMPOSITION_REACHABLE')
        self.assertFalse(result['executed'])
        self.assertFalse(result['semantic_acceptance_complete'])

    def test_discovery_refusal_also_has_not_executed(self):
        result = composer.route('compress the input into out.gz', g={})
        self.assertFalse(result['pass'])
        self.assertFalse(result['executed'])
        self.assertFalse(result['semantic_acceptance_complete'])


if __name__ == '__main__':
    unittest.main()
