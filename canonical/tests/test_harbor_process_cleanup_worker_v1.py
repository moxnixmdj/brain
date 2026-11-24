"""Safe local observation and validation only; no cleanup of live processes."""
import os
import unittest
from canonical.runtime import harbor_process_cleanup_worker_v1 as worker


class CleanupWorkerTests(unittest.TestCase):
    def test_snapshot_includes_this_process_and_starttime(self):
        result = worker.snapshot()
        self.assertIn(str(os.getpid()), result)
        self.assertGreater(result[str(os.getpid())], 0)
        self.assertEqual(worker._stat(os.getpid())[1], result[str(os.getpid())])

    def test_invalid_baselines_refused_before_any_signals(self):
        for baseline in ({}, {'abc': 4}, {'1': -1}, {'1': True}, {'1': '1'}):
            with self.subTest(baseline=baseline):
                with self.assertRaisesRegex(ValueError, 'BASELINE_INVALID'):
                    worker.cleanup(baseline)


if __name__ == '__main__':
    unittest.main()
