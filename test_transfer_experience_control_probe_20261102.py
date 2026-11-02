import unittest

import transfer_experience_control_probe_20261102 as probe


class TransferExperienceControlProbeTests(unittest.TestCase):
    def test_fresh_processes_with_equal_fixed_baseline_and_real_off_arm(self):
        report = probe.run()
        rows = {row['role']: row for row in report['rows']}
        self.assertEqual(len({row['pid'] for row in rows.values()}), 4)
        self.assertTrue(rows['teach']['host_plan_reaches_target'])
        self.assertFalse(rows['off']['result']['pass'])
        self.assertFalse(rows['off']['host_plan_reaches_target'])
        self.assertTrue(rows['off']['episode_store_unchanged'])
        self.assertFalse(rows['off']['result']['experience_policy']['may_read_retained_experience'])
        self.assertFalse(rows['off']['result']['experience_policy']['may_learn_model'])
        self.assertFalse(rows['off']['result']['experience_policy']['may_persist_experience'])
        self.assertTrue(rows['cold']['host_plan_reaches_target'])
        self.assertTrue(rows['warm']['host_plan_reaches_target'])
        self.assertFalse(rows['cold']['result']['transferred'])
        self.assertTrue(rows['warm']['result']['transferred'])
        self.assertGreater(rows['warm']['result']['prior_transitions'], 0)
        self.assertEqual(rows['cold']['result']['fixed_plan_trials'], 1)
        self.assertEqual(rows['warm']['result']['fixed_plan_trials'], 1)


if __name__ == '__main__':
    unittest.main()
