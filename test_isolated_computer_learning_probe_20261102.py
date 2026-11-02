"""Live namespace/real-program research regression; requires Linux user namespaces."""
import unittest

import isolated_computer_learning_probe_20261102 as probe


class IsolatedComputerLearningProbeTests(unittest.TestCase):
    def test_real_learner_restart_controls_and_escape_canaries(self):
        report = probe.run()
        rows = {row['role']: row for row in report['rows']}
        self.assertEqual(set(rows), {'teach', 'cold', 'warm'})
        for role, row in rows.items():
            with self.subTest(role=role):
                self.assertEqual(row['launcher_status'], 'CHILD_EXITED')
                self.assertEqual(row['returncode'], 0)
                self.assertTrue(row['result']['pass'])
                self.assertTrue(row['result']['source_content_verified'])
                self.assertTrue(row['full_external_decompression_matches'])
                self.assertTrue(row['worker_reported_source_unchanged'])
                self.assertTrue(row['input_file_unchanged'])
                self.assertTrue(row['sentinel_unchanged'])
                self.assertFalse(row['host_listener_connection_observed'])
                self.assertTrue(all(row['worker_reported_checks'].values()), row)
                neg = row['worker_reported_negative_controls']
                self.assertEqual(neg['wrong_status'], 'OPEN__OUTPUT_CONTENT_MISMATCH')
                self.assertFalse(neg['wrong_published'])
                self.assertEqual(neg['missing_status'], 'OPEN__NO_EXISTING_INPUT_FILE_IN_GOAL')
                self.assertFalse(neg['missing_published'])
                self.assertEqual(neg['existing_status'], 'OPEN__OUTPUT_ALREADY_EXISTS')
                self.assertTrue(neg['existing_unchanged'])
        self.assertFalse(rows['teach']['result']['from_memory'])
        self.assertFalse(rows['cold']['result']['from_memory'])
        self.assertTrue(rows['warm']['result']['from_memory'])
        self.assertEqual(rows['warm']['result']['learned_by'], 'PASS__RECALLED_AND_REVERIFIED')
        self.assertEqual(report['timeout_control']['status'], 'WALLCLOCK_LIMIT_EXCEEDED')
        self.assertEqual(report['timeout_control']['broker_payload'], 'READY')
        self.assertFalse(report['timeout_control']['late_descendant_message_seen'])


if __name__ == '__main__':
    unittest.main()
