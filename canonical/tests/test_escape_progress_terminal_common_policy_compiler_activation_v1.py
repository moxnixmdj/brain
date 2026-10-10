from __future__ import annotations
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]
ACT=ROOT/"canonical/governance/ESCAPE_PROGRESS_TERMINAL_COMMON_POLICY_COMPILER_ACTIVATION_20261010_V1.json"
CLASSIFIER=ROOT/"canonical/governance/CURRENT_RESIDUAL_REUSE_CLASSIFICATION_20261010_V1.json"

class EscapeTerminalPolicyCompilerActivationTests(unittest.TestCase):
    def test_activation_binds_verified_compiler(self):
        self.assertTrue(ACT.is_file())
        a=json.loads(ACT.read_text())
        self.assertEqual(a["status"],"ACTIVE_VERIFIED_PROOF_COMPOSITION_MECHANISM__ZERO_ROW_CREDIT")
        self.assertEqual(a["runtime"]["git_blob_sha"],"e2dce48ca532798fc29749001b3d4cbf300332d7")
        self.assertEqual(a["verification"]["status"],"PASS__DEVELOPMENT_15_OF_15__INDEPENDENT_15_OF_15__PYCOMPILE__MUTATION_KILLED")
        self.assertFalse(a["execution_authority"])
        self.assertEqual(a["terminal_credit_delta"],0)

    def test_current_gap_a_cut_uses_compiler_before_private_acquisition(self):
        d=json.loads(CLASSIFIER.read_text())
        row=next(x for x in d["classifications"] if x["residual_id"]=="ESCAPE_GAP_A_ACQUISITION_TOTALITY")
        self.assertEqual(
            row["terminal_common_policy_compiler"]["path"],
            "canonical/runtime/escape_progress_terminal_common_policy_compiler_v1.py",
        )
        self.assertEqual(row["terminal_common_policy_compiler"]["git_blob_sha"],"e2dce48ca532798fc29749001b3d4cbf300332d7")
        self.assertIn("REAL_ROW_PROOFS_0_OF_10",row["current_gate_status"])
        self.assertTrue(
            d["next_shared_execution_cut"][0].startswith(
                "INSTANTIATE_VERIFIED_TERMINAL_COMMON_POLICY_COMPILER"
            )
        )

if __name__=="__main__":
    unittest.main(verbosity=2)
