from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest

from canonical.runtime import professional_quality_whole_leaf_claim_scope_gate_v2 as gate

ROOT = Path(__file__).resolve().parents[2]
CHAIN = "canonical/governance/PROFESSIONAL_QUALITY_R10_EXECUTION_WHOLE_LEAF_V2_CHAIN_20261010_V1.json"


def load_chain():
    return json.loads((ROOT / CHAIN).read_text(encoding="utf-8"))


class R10ExecutionWholeLeafV2CurrentChainTests(unittest.TestCase):
    def test_exact_current_chain_passes_gate_without_property_credit(self):
        out = gate.verify_entry(load_chain(), repo_root=ROOT)
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["status"],
            "PASS__CLAIM_SCOPED_WHOLE_LEAF_DOMAIN_AND_SCOPE_COVER_ADMISSIBLE__PROPERTY_TRUTH_SEPARATE",
        )
        self.assertTrue(out["whole_leaf_domain_equivalence_proved"])
        self.assertTrue(out["whole_leaf_scope_complete"])
        self.assertFalse(out["leaf_property_truth_authority"])
        self.assertFalse(out["semantic_truth_authority"])
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["quality_authority"])
        self.assertFalse(out["acceptance_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)

    def test_certificate_blob_substitution_fails_closed(self):
        chain = deepcopy(load_chain())
        chain["certificate"]["git_blob_sha"] = "0" * 40
        out = gate.verify_entry(chain, repo_root=ROOT)
        self.assertFalse(out["pass"], out)
        self.assertIn("CERTIFICATE", out["reason"])

    def test_claim_scope_blob_substitution_fails_closed(self):
        chain = deepcopy(load_chain())
        chain["claim_scope"]["git_blob_sha"] = "0" * 40
        out = gate.verify_entry(chain, repo_root=ROOT)
        self.assertFalse(out["pass"], out)
        self.assertIn("CLAIM_SCOPE", out["reason"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
