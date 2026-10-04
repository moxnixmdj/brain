import unittest

from canonical.runtime.livebench_frozen_active_legacy15_v1 import (
    ACTIVE_IDS,
    EXCLUDED_IDS,
    EXPECTED_COMMITMENT,
    commitment,
    verify,
)


class FrozenActiveLegacy15Tests(unittest.TestCase):
    def test_exact_commitment_opening(self):
        self.assertEqual(commitment(), EXPECTED_COMMITMENT)

    def test_exact_cardinality(self):
        self.assertEqual(len(ACTIVE_IDS), 15)
        self.assertEqual(len(set(ACTIVE_IDS)), 15)

    def test_excluded_disjoint(self):
        self.assertFalse(set(ACTIVE_IDS) & set(EXCLUDED_IDS))

    def test_each_excluded_id_changes_commitment(self):
        for iid in EXCLUDED_IDS:
            with self.subTest(iid=iid):
                self.assertNotEqual(commitment(ACTIVE_IDS + (iid,)), EXPECTED_COMMITMENT)

    def test_verify(self):
        self.assertEqual(verify()["status"], "PASS__EXISTING_TERMINAL_SET_COMMITMENT_OPENED")


if __name__ == "__main__":
    unittest.main()
