from __future__ import annotations

import unittest
from pathlib import Path

from canonical.runtime import tool_discovery_frozen_scope_completeness_discharge_v1 as d

ROOT = Path(__file__).resolve().parents[2]


class Tests(unittest.TestCase):
    def _sources(self):
        v1 = (ROOT / "canonical/runtime/tool_discovery_information_safe_proof.py").read_text(encoding="utf-8")
        v2 = (ROOT / "canonical/runtime/tool_discovery_information_safe_proof_v2.py").read_text(encoding="utf-8")
        return v1, v2

    def test_exact_frozen_scope_discharges(self):
        out = d.evaluate()
        self.assertTrue(out["scope_semantics_discharged"], out)
        self.assertEqual(out["basis_kind"], "EXACT_COMPLETE_TARGET_CASE_UNIVERSE")
        self.assertEqual(out["missing_source_facts"], [])
        self.assertEqual(out["terminal_cases_replayed"], 0)
        self.assertEqual(out["new_reality_units_consumed"], 0)
        self.assertEqual(out["capability_credit_delta"], 0)
        self.assertEqual(out["family_credit_delta"], 0)
        self.assertFalse(out["promotion_authority"])

    def test_omitting_public_tool_universe_fails(self):
        v1, v2 = self._sources()
        needle = '"tools": [dict(t) for t in case["tools"]],'
        self.assertIn(needle, v1)
        facts = d.derive_frozen_scope_facts(v1.replace(needle, '"tools": [],', 1), v2)
        self.assertFalse(facts["V1_PUBLIC_EXPOSES_COMPLETE_CASE_TOOL_IDENTITY_LIST"])

    def test_replacing_v2_identity_universe_fails(self):
        v1, v2 = self._sources()
        needle = "case=v1.generate_case(seed,0)"
        self.assertIn(needle, v2)
        mutated = v2.replace(needle, needle + '\n    case["tools"] = []', 1)
        facts = d.derive_frozen_scope_facts(v1, mutated)
        self.assertFalse(facts["V2_DOES_NOT_REPLACE_GENERATED_TOOL_IDENTITY_UNIVERSE"])

    def test_hidden_capabilities_must_remain_separate(self):
        v1, v2 = self._sources()
        needle = 'table = case["_oracle"]["epoch1" if epoch == 1 else "epoch0"]'
        self.assertIn(needle, v1)
        mutated = v1.replace(needle, "table = {}", 1)
        facts = d.derive_frozen_scope_facts(mutated, v2)
        self.assertFalse(facts["V1_HIDDEN_CAPABILITY_TRUTH_IS_SEPARATE_ORACLE_STATE"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
