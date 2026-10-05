import unittest
from canonical.runtime import h100_deterministic_code_accounting_loophole_v1 as a

class DeterministicCodeAccountingLoopholeTests(unittest.TestCase):
    def setUp(self):
        self.rows=[
            {"input":{"x":1},"output":"A"},
            {"input":{"x":2},"output":"B"},
            {"input":{"x":3},"output":"C"},
        ]

    def test_finite_lookup_perfect_training_accuracy_zero_learned(self):
        p=a.compile_finite_lookup(self.rows)
        self.assertEqual(p["persistent_learned_bytes"],0)
        self.assertEqual(a.finite_dataset_accuracy(p,self.rows),1.0)
        self.assertGreater(p["deterministic_capability_bytes"],0)

    def test_unseen_input_abstains(self):
        p=a.compile_finite_lookup(self.rows)
        self.assertEqual(a.lookup(p,{"x":4})["status"],"ABSTAIN_UNSEEN_INPUT")

    def test_representation_changes_learned_count_not_total_bits(self):
        out=a.syntax_only_accounting_same_payload(1000,100)
        self.assertEqual(out["learned_blob_representation"]["total_persistent_bytes"],1100)
        self.assertEqual(out["embedded_code_representation"]["total_persistent_bytes"],1100)
        self.assertEqual(out["learned_blob_representation"]["counted_learned_bytes"],1000)
        self.assertEqual(out["embedded_code_representation"]["counted_learned_bytes"],0)
        self.assertTrue(out["learned_byte_metric_changed_by_representation"])

    def test_conflicting_lookup_rows_fail_closed(self):
        with self.assertRaises(a.AccountingLoopholeError):
            a.compile_finite_lookup([
                {"input":{"x":1},"output":"A"},
                {"input":{"x":1},"output":"B"},
            ])

    def test_certificate(self):
        c=a.certificate(self.rows,{"x":9})
        self.assertEqual(c["finite_training_accuracy"],1.0)
        self.assertEqual(c["unseen_status"],"ABSTAIN_UNSEEN_INPUT")
        self.assertEqual(c["persistent_learned_bytes"],0)
        self.assertGreater(c["deterministic_capability_bytes"],0)

if __name__=="__main__":
    unittest.main(verbosity=2)
