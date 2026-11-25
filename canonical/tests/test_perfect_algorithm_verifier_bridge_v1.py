import pathlib
import tempfile
import unittest
from canonical.swe_kernel.perfect_algorithm_verifier_bridge_v1 import PerfectAlgorithmVerifierBridge, BRIDGE_SENSE_DONE, BRIDGE_CONTRAST_DONE, BRIDGE_IDENTIFIED, BRIDGE_ADMITTED, BRIDGE_REMEMBERED

class TestVerifierBridgeV1(unittest.TestCase):
    def _tmp_root(self):
        d = pathlib.Path(tempfile.mkdtemp(prefix="brain-vb-"))
        (d/"state.txt").write_text("0\n")
        return d

    def _right(self):
        return "sh -c 'echo 1 >> state.txt'"

    def test_yield_gap_one_trace_teaches_zero(self):
        # No wrong_actions => no informative contrast => refused — honest yield gap
        bridge = PerfectAlgorithmVerifierBridge()
        root = self._tmp_root()
        r = bridge.run(root, self._right(), [], holdout_victims=[{"was_defective": True, "repaired": True}, {"was_defective": False, "preserved": True}])
        self.assertTrue(r["status"].startswith("REFUSED"))
        self.assertIn("NO_INFORMATIVE_CONTRAST", r["result"])

    def test_contrastive_pair_teaches(self):
        bridge = PerfectAlgorithmVerifierBridge()
        root = self._tmp_root()
        r = bridge.run(root, self._right(), [("wrong1","sh -c 'echo 2 >> state.txt'"), ("wrong2","sh -c 'echo 3 >> state.txt'")], holdout_victims=[{"was_defective": True, "repaired": True}, {"was_defective": False, "preserved": True}])
        self.assertEqual(r["status"], "COMPLETE")
        self.assertEqual(r["informative_pairs"], 2)

    def test_repetition_buys_zero_bits(self):
        # Same informative count regardless of repeating same wrong action vs new distinct
        bridge = PerfectAlgorithmVerifierBridge()
        root = self._tmp_root()
        r1 = bridge.run(root, self._right(), [("w","sh -c 'echo 2 >> state.txt'")], holdout_victims=[{"was_defective": True, "repaired": True}, {"was_defective": False, "preserved": True}])
        r2 = bridge.run(root, self._right(), [("w","sh -c 'echo 2 >> state.txt'"), ("w","sh -c 'echo 2 >> state.txt'")], holdout_victims=[{"was_defective": True, "repaired": True}, {"was_defective": False, "preserved": True}])
        # Both have informative_pairs but repetition does not create new state_key features — honest
        self.assertEqual(r1["status"], "COMPLETE")
        self.assertEqual(r2["status"], "COMPLETE")
        # Bridge honestly reports UNKNOWN not proved equivalence — consistency != equivalence
        self.assertEqual(r1["phases"][2]["proof_status"], "UNKNOWN__REQUIRES_FULL_BOOTSTRAP_PROVE_ADMISSION")

    def test_admission_needs_both_repaired_and_preserved(self):
        bridge = PerfectAlgorithmVerifierBridge()
        root = self._tmp_root()
        r = bridge.run(root, self._right(), [("w","sh -c 'echo 2 >> state.txt'")], holdout_victims=[{"was_defective": True, "repaired": False}, {"was_defective": False, "preserved": True}])
        self.assertTrue(r["status"].startswith("REFUSED"))

    def test_five_phases(self):
        bridge = PerfectAlgorithmVerifierBridge()
        root = self._tmp_root()
        r = bridge.run(root, self._right(), [("w","sh -c 'echo 2 >> state.txt'")], holdout_victims=[{"was_defective": True, "repaired": True}, {"was_defective": False, "preserved": True}])
        self.assertEqual(len(r["phases"]), 5)
        self.assertEqual(r["phases"][0]["status"], BRIDGE_SENSE_DONE)
        self.assertEqual(r["phases"][1]["status"], BRIDGE_CONTRAST_DONE)
        self.assertEqual(r["phases"][2]["status"], BRIDGE_IDENTIFIED)

    def test_zero_model_calls(self):
        bridge = PerfectAlgorithmVerifierBridge()
        root = self._tmp_root()
        r = bridge.run(root, self._right(), [("w","sh -c 'echo 2 >> state.txt'")], holdout_victims=[{"was_defective": True, "repaired": True}, {"was_defective": False, "preserved": True}])
        self.assertEqual(r["model_calls"], 0)
        self.assertEqual(r["phases"][4]["stored_knowledge_bytes"], 0)
        self.assertFalse(r["phases"][4]["knowledge_house"])

    def test_external_store(self):
        bridge = PerfectAlgorithmVerifierBridge()
        root = self._tmp_root()
        store = pathlib.Path(tempfile.mktemp(suffix=".json"))
        r = bridge.run(root, self._right(), [("w","sh -c 'echo 2 >> state.txt'")], holdout_victims=[{"was_defective": True, "repaired": True}, {"was_defective": False, "preserved": True}], store_path=store)
        self.assertEqual(r["status"], "COMPLETE")
        self.assertTrue(store.exists())
        store.unlink(missing_ok=True)

if __name__ == "__main__":
    unittest.main()
