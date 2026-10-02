from __future__ import annotations

import unittest

from canonical.runtime.acceptance_proof_transmuter_v1 import evaluate


def protocols():
    return {
        "protocols": [
            {"family": "OWNED", "proof_mode": "THEORETICAL_CEILING", "status": "PASS"},
            {"family": "MATCHED", "proof_mode": "MATCHED_DIRECT_NONINFERIORITY", "status": "DEFINED_RESULT_OPEN"},
            {"family": "PUBLIC", "proof_mode": "PUBLIC_FIXED_BAR", "status": "DEFINED_RESULT_OPEN"},
            {"family": "MIXED", "proof_mode": "PUBLIC_FIXED_BAR_PLUS_SCOPE_AUDIT", "status": "DEFINED_RESULT_OPEN"},
        ]
    }


def evidence(**kwargs):
    base = {
        "id": "E1",
        "family": "MATCHED",
        "mode": "UNIVERSAL",
        "verified": True,
        "independent": True,
        "contamination_clean": True,
        "binds_frozen_protocol": True,
        "scope_relation": "EXACT",
        "closes_entire_protocol": True,
        "result": {
            "all_admissible_inputs_proved": True,
            "formal_completeness": True,
        },
    }
    base.update(kwargs)
    return base


class AcceptanceProofTransmuterTests(unittest.TestCase):
    def family(self, out, name):
        return next(r for r in out["families"] if r["family"] == name)

    def test_already_pass_preserved(self):
        out = evaluate(protocols(), {"evidence": []})
        self.assertEqual(self.family(out, "OWNED")["result_status"], "PASS")

    def test_universal_full_scope_closes_matched_protocol(self):
        out = evaluate(protocols(), {"evidence": [evidence()]})
        row = self.family(out, "MATCHED")
        self.assertEqual(row["result_status"], "PASS")
        self.assertEqual(row["closure_mode"], "UNIVERSAL")

    def test_behavioral_only_never_closes(self):
        ev = evidence(
            mode="BEHAVIORAL_ONLY",
            result={"all_admissible_inputs_proved": True, "formal_completeness": True},
        )
        out = evaluate(protocols(), {"evidence": [ev]})
        self.assertEqual(self.family(out, "MATCHED")["result_status"], "DEFINED_RESULT_OPEN")

    def test_partial_scope_never_closes(self):
        ev = evidence(scope_relation="PARTIAL")
        out = evaluate(protocols(), {"evidence": [ev]})
        self.assertEqual(self.family(out, "MATCHED")["result_status"], "DEFINED_RESULT_OPEN")

    def test_unverified_never_closes(self):
        ev = evidence(verified=False)
        out = evaluate(protocols(), {"evidence": [ev]})
        self.assertEqual(self.family(out, "MATCHED")["result_status"], "DEFINED_RESULT_OPEN")

    def test_absolute_theoretical_ceiling_closes(self):
        ev = evidence(
            mode="ABSOLUTE_DOMINANCE",
            result={
                "direction": "higher",
                "brain_lower_bound": 1.0,
                "theoretical_upper_bound": 1.0,
            },
        )
        out = evaluate(protocols(), {"evidence": [ev]})
        row = self.family(out, "MATCHED")
        self.assertEqual(row["result_status"], "PASS")
        self.assertEqual(row["witness_reason"], "THEORETICAL_CEILING_DOMINANCE")

    def test_absolute_target_bound_squeeze_closes(self):
        ev = evidence(
            mode="ABSOLUTE_DOMINANCE",
            result={
                "direction": "higher",
                "brain_lower_bound": 0.94,
                "target_upper_bound": 0.91,
            },
        )
        out = evaluate(protocols(), {"evidence": [ev]})
        self.assertEqual(self.family(out, "MATCHED")["result_status"], "PASS")

    def test_lower_is_better_floor_closes(self):
        ev = evidence(
            mode="ABSOLUTE_DOMINANCE",
            result={
                "direction": "lower",
                "brain_upper_bound": 0.0,
                "theoretical_lower_bound": 0.0,
            },
        )
        out = evaluate(protocols(), {"evidence": [ev]})
        self.assertEqual(self.family(out, "MATCHED")["result_status"], "PASS")

    def test_public_fixed_bar_closes_only_when_entire_protocol_bound(self):
        ev = evidence(
            id="PUB",
            family="PUBLIC",
            mode="PUBLIC_FIXED_BAR",
            result={"threshold_pass": True},
        )
        out = evaluate(protocols(), {"evidence": [ev]})
        self.assertEqual(self.family(out, "PUBLIC")["result_status"], "PASS")

        partial = evidence(
            id="MIX",
            family="MIXED",
            mode="PUBLIC_FIXED_BAR",
            closes_entire_protocol=False,
            result={"threshold_pass": True},
        )
        out2 = evaluate(protocols(), {"evidence": [partial]})
        self.assertEqual(self.family(out2, "MIXED")["result_status"], "DEFINED_RESULT_OPEN")

    def test_evidence_structure_fails_closed(self):
        out = evaluate(protocols(), {"evidence": "nope"})
        self.assertEqual(out["status"], "FAIL_CLOSED")

    def test_current_repo_protocols_remain_2_closed_17_open_without_new_witnesses(self):
        from pathlib import Path
        import json

        root = Path(__file__).resolve().parents[2]
        protocol_path = root / "canonical/governance/OPUS55_TERMINAL_PROOF_PROTOCOLS_V1.json"
        input_path = root / "canonical/governance/OPUS55_ACCEPTANCE_PROOF_TRANSMUTATION_INPUT_V1.json"
        if not protocol_path.exists() or not input_path.exists():
            self.skipTest("repository integration fixtures not present in isolated unit-test sandbox")
        pdoc = json.loads(protocol_path.read_text(encoding="utf-8"))
        edoc = json.loads(input_path.read_text(encoding="utf-8"))
        out = evaluate(pdoc, edoc)
        self.assertEqual(out["status"], "PASS")
        self.assertEqual(out["family_count"], 19)
        self.assertEqual(out["closed_family_count"], 2)
        self.assertEqual(out["open_family_count"], 17)


if __name__ == "__main__":
    unittest.main(verbosity=2)
