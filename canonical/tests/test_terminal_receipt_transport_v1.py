import copy
import unittest

from canonical.runtime.terminal_receipt_transport_v1 import SCHEMA, evaluate


def sample_wave():
    return {
        "status": "ONE_SHOT_TERMINAL_WAVE_PASS__IMMUTABLE_PUBLIC_RUNNER_RECEIPT__NO_REPLAY_AUTHORIZED",
        "public_runner": {"conclusion": "success"},
        "result_guards": {
            "no_case_replacement": True,
            "no_tuning_replay": True,
            "result_to_runtime_feedback_during_wave": False,
        },
        "direct_terminal_population": {
            "routes": {"D": {"cases": 10, "passes": 10}}
        },
        "reduction_input": {
            "wave": {
                "parent_portfolio_receipts": {
                    "T0": [
                        {
                            "behavior_id": "R",
                            "binding_blob": "a" * 40,
                            "case_id": "T0::R",
                            "direct_instrumentation_pass": True,
                            "parent_terminal_acceptance_pass": True,
                            "case_replaced": False,
                            "tuning_replay": False,
                            "result_to_runtime_feedback": False,
                        }
                    ]
                }
            }
        },
    }


class ReceiptTransportTests(unittest.TestCase):
    def test_parent_binding_receipt_is_transport_eligible(self):
        manifest = {
            "schema": SCHEMA,
            "bindings": [
                {
                    "id": "R0",
                    "behavior_id": "R",
                    "current_binding_path": "r.json",
                    "receipt_anchor": "PARENT_RECEIPT_BINDING_BLOB",
                    "required_portfolios": ["T0"],
                }
            ],
        }
        out = evaluate(manifest, sample_wave(), {"r.json": "a" * 40})
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["rows"][0]["state"], "TRANSPORT_ELIGIBLE")

    def test_direct_summary_without_binding_blob_is_identity_only(self):
        manifest = {
            "schema": SCHEMA,
            "bindings": [
                {
                    "id": "D0",
                    "behavior_id": "D",
                    "current_binding_path": "d.json",
                    "receipt_anchor": "DIRECT_SUMMARY_ONLY",
                    "minimum_cases": 10,
                    "expected_historical_blob_sha": "b" * 40,
                }
            ],
        }
        out = evaluate(manifest, sample_wave(), {"d.json": "b" * 40})
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["rows"][0]["state"], "IDENTITY_ONLY")
        self.assertFalse(out["rows"][0]["receipt_binding_anchored"])

    def test_changed_parent_binding_blocks_transport(self):
        manifest = {
            "schema": SCHEMA,
            "bindings": [
                {
                    "id": "R0",
                    "behavior_id": "R",
                    "current_binding_path": "r.json",
                    "receipt_anchor": "PARENT_RECEIPT_BINDING_BLOB",
                    "required_portfolios": ["T0"],
                }
            ],
        }
        out = evaluate(manifest, sample_wave(), {"r.json": "b" * 40})
        self.assertEqual(out["rows"][0]["state"], "BLOCKED")
        self.assertIn(
            "CURRENT_BINDING_DIFFERS_FROM_RECEIPT_BINDING",
            out["rows"][0]["errors"],
        )

    def test_result_feedback_fails_closed(self):
        wave = copy.deepcopy(sample_wave())
        wave["result_guards"]["result_to_runtime_feedback_during_wave"] = True
        manifest = {
            "schema": SCHEMA,
            "bindings": [
                {
                    "id": "D0",
                    "behavior_id": "D",
                    "current_binding_path": "d.json",
                    "receipt_anchor": "DIRECT_SUMMARY_ONLY",
                    "minimum_cases": 10,
                    "expected_historical_blob_sha": "b" * 40,
                }
            ],
        }
        out = evaluate(manifest, wave, {"d.json": "b" * 40})
        self.assertFalse(out["pass"])
        self.assertIn("RESULT_TO_RUNTIME_FEEDBACK_NOT_PROVEN_ABSENT", out["errors"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
