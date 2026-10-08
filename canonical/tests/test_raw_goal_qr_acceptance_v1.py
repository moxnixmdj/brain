import unittest
from unittest.mock import patch
from canonical.runtime import raw_goal_qr_acceptance_v1 as qr
from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract

GOAL = 'Generate a QR code image for the text "brain-qr-42" and save it to canonical/astra_runtime/tmp/R2_QR_TEST.png'

class T(unittest.TestCase):
    def test_preflight(self):
        out = qr.preflight(GOAL)
        self.assertTrue(out["matched"], out)
        self.assertEqual(out["capability_id"], qr.QR_CAPABILITY_ID)
        self.assertEqual(out["payload"], "brain-qr-42")

    def test_extra_clause_does_not_match(self):
        out = qr.preflight(GOAL + " Then explain it.")
        self.assertFalse(out["matched"])

    @patch.object(qr, "execute_bound")
    def test_fresh_decoder_exact_match_is_required(self, decode):
        pf = qr.preflight(GOAL)
        contract = compile_contract(
            GOAL, source_id="user", routing_target_effects=[qr.ROUTING_EFFECT]
        )
        decode.return_value = {
            "pass": True,
            "result_sha256": "a" * 64,
            "result": {"stdout": "brain-qr-42\\n"},
        }
        raw = {
            "pass": True,
            "compiler_mode": "DETERMINISTIC_VERIFIED_CAPABILITY_MATCH",
            "compiled_capability_id": qr.QR_CAPABILITY_ID,
            "raw_goal_sha256": pf["goal_sha256"],
            "raw_task_contract_sha256": contract["task_contract_sha256"],
            "raw_source_coverage_complete": True,
            "raw_acceptance_obligation_count": len(
                contract["acceptance_contract"]["obligations"]
            ),
            "model_dependency_count": 0,
            "cognition_dependency_class": "MODEL_INDEPENDENT",
        }
        out = qr.verify(goal=GOAL, raw_result=raw)
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["decoded_payload_exact"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
