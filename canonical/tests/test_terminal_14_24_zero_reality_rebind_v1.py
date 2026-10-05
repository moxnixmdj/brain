from __future__ import annotations
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GOV = ROOT / "canonical" / "governance"

def load(name: str):
    return json.loads((GOV / name).read_text(encoding="utf-8"))

class Terminal1424RebindTests(unittest.TestCase):
    def test_candidate_matches_current_root_partition(self):
        c = load("TERMINAL_14_24_ZERO_REALITY_REBIND_CANDIDATE_V1.json")
        r = load("TERMINAL_ROOT_CAUSE_STATE_V1.json")
        s = r["current_residual_root_partition"]
        x = c["exact_state"]
        self.assertEqual(r["current_acceptance"]["proved_atomic"], 14)
        self.assertEqual(r["current_acceptance"]["unresolved_atomic"], 24)
        self.assertEqual(s["root1_positive_gap_count"], 0)
        self.assertEqual(s["root2_only_count"], 15)
        self.assertEqual(s["root3_only_count"], 6)
        self.assertEqual(s["root2_and_root3_count"], 3)
        self.assertEqual(x["root2_touching"], 18)
        self.assertEqual(x["root3_touching"], 9)

    def test_root2_set_is_exact_and_excludes_closed_livebench(self):
        c = load("TERMINAL_14_24_ZERO_REALITY_REBIND_CANDIDATE_V1.json")
        d = load("ROOT2_OUTPUT_ONLY_THRESHOLD_COMPILATION_V3.json")
        bound = set(c["exact_root2_touching"])
        dag = {p["id"] for p in d["predicates"]}
        self.assertEqual(bound, dag)
        self.assertEqual(len(bound), 18)
        self.assertNotIn("LIVEBENCH_IF_GE_65_7", bound)

    def test_root3_set_is_current_and_excludes_closed_unknown_domain(self):
        c = load("TERMINAL_14_24_ZERO_REALITY_REBIND_CANDIDATE_V1.json")
        r = load("TERMINAL_ROOT_CAUSE_STATE_V1.json")["current_residual_root_partition"]
        expected = set(r["root3_only"]) | set(r["root2_and_root3"])
        bound = set(c["exact_root3_touching"])
        self.assertEqual(bound, expected)
        self.assertEqual(len(bound), 9)
        self.assertNotIn("UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT", bound)

    def test_no_credit_or_reality_authority(self):
        c = load("TERMINAL_14_24_ZERO_REALITY_REBIND_CANDIDATE_V1.json")
        self.assertEqual(c["accounting"]["incremental_spend_usd"], 0)
        self.assertEqual(c["accounting"]["terminal_cases_consumed"], 0)
        self.assertEqual(c["accounting"]["acceptance_credit_delta"], 0)
        self.assertFalse(c["execution_authority"])
        self.assertFalse(c["promotion_authority"])
        self.assertFalse(c["fresh_reality_authority"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
