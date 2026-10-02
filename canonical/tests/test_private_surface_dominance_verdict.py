import json
import pathlib
import unittest

from canonical.runtime.proof_route_dominance import evaluate

ROOT=pathlib.Path(__file__).resolve().parents[2]
INPUT=ROOT/"canonical/governance/PRIVATE_SURFACE_DOMINANCE_INPUT_V1.json"
RECEIPT=ROOT/"canonical/verification/PRIVATE_SURFACE_DOMINANCE_VERDICT_V1.json"

class Tests(unittest.TestCase):
    def test_frozen_verdict_matches_compiler(self):
        payload=json.loads(INPUT.read_text(encoding="utf-8"))
        receipt=json.loads(RECEIPT.read_text(encoding="utf-8"))
        out=evaluate(payload)

        self.assertEqual(out["status"],receipt["compiler_status"])
        self.assertEqual(out["global_uncovered_obligations"],receipt["global_uncovered_obligations"])
        self.assertEqual(out["admissible_routes"],receipt["admissible_routes"])

        actual={
            row["route_id"]:{
                "redundant":row["redundant"],
                "uncovered_obligations":row["uncovered_obligations"],
            }
            for row in out["blocked_route_verdicts"]
        }
        expected={
            row["route_id"]:{
                "redundant":row["redundant"],
                "uncovered_obligations":row["uncovered_obligations"],
            }
            for row in receipt["blocked_route_verdicts"]
        }
        self.assertEqual(actual,expected)

    def test_only_mysterymechanism_is_currently_deletable(self):
        payload=json.loads(INPUT.read_text(encoding="utf-8"))
        out=evaluate(payload)
        redundant=sorted(
            row["route_id"] for row in out["blocked_route_verdicts"]
            if row["redundant"]
        )
        self.assertEqual(redundant,["BLOCKED_MYSTERYMECHANISM"])

    def test_no_false_terminal_credit(self):
        receipt=json.loads(RECEIPT.read_text(encoding="utf-8"))
        self.assertEqual(receipt["capability_credit_delta"],0)
        self.assertEqual(receipt["family_credit_delta"],0)
        self.assertEqual(receipt["fresh_terminal_evidence_consumed"],0)

if __name__=="__main__":
    unittest.main(verbosity=2)
