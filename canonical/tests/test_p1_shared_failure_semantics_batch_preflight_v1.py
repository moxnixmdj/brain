from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from canonical.runtime.p1_shared_failure_semantics_batch_preflight_v1 import FREEZE, evaluate
from canonical.runtime.p1_shared_failure_semantics_normalizer_v1 import normalize_case

ROOT = Path(__file__).resolve().parents[2]
BASE = json.loads((ROOT / FREEZE).read_text(encoding="utf-8"))


class Tests(unittest.TestCase):
    def test_live_exact_freeze_passes(self):
        out = evaluate()
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["minimum_new_reality_units"], 1)
        self.assertEqual(out["surface_count"], 3)
        self.assertFalse(out["execution_authority"])

    def test_surface_removal_fails(self):
        d = copy.deepcopy(BASE)
        d["frozen_direct_surfaces"] = d["frozen_direct_surfaces"][:-1]
        self.assertFalse(evaluate(freeze_override=d)["pass"])

    def test_case_selection_before_freeze_fails(self):
        d = copy.deepcopy(BASE)
        d["shared_batch_contract"]["post_freeze_case_selection_required"] = False
        self.assertFalse(evaluate(freeze_override=d)["pass"])

    def test_spend_fails(self):
        d = copy.deepcopy(BASE)
        d["shared_batch_contract"]["incremental_spend_usd"] = 1
        self.assertFalse(evaluate(freeze_override=d)["pass"])

    def test_premature_execution_authority_fails(self):
        d = copy.deepcopy(BASE)
        d["execution_authority"] = True
        self.assertFalse(evaluate(freeze_override=d)["pass"])

    def test_wrong_observation_fails(self):
        d = copy.deepcopy(BASE)
        d["selected_observation"] = "P1_FRONTIERCODE_ONLY_FAILURE_SEMANTICS_BATCH"
        self.assertFalse(evaluate(freeze_override=d)["pass"])

    def test_normalizer_never_defaults_missing_semantics(self):
        raw = {
            "surface_id": "T0/FRONTIERCODE_V1_1::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
            "case_id": "x",
            "source_observation_receipt": "r",
            "trajectory": [{
                "step": 1,
                "action_id": "A1",
                "domain": "CODE",
                "reads": [],
                "writes": ["terminal"],
                "depends_on": [],
                "dependency_composition": "SEQUENTIAL",
                "checks": [{
                    "kind": "SCOPE",
                    "id": "A1:SCOPE",
                    "pass": False,
                    "evidence": ["r1"],
                }],
            }],
            "terminal_failed_resources": ["terminal"],
        }
        out = normalize_case(raw)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertTrue(str(out["reason"]).startswith("FAILURE_SEMANTICS_UNBOUND"))

    def test_failed_check_without_receipt_fails(self):
        raw = {
            "surface_id": "T2/RECOVERY_SCOPE_COMPOSITION::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
            "case_id": "x",
            "source_observation_receipt": "r",
            "trajectory": [
                {
                    "step": 1,
                    "action_id": "A1",
                    "domain": "CODE",
                    "reads": [],
                    "writes": ["x"],
                    "depends_on": [],
                    "dependency_composition": "SEQUENTIAL",
                    "checks": [{
                        "kind": "SCOPE",
                        "id": "A1:SCOPE",
                        "pass": False,
                        "evidence": [],
                        "failure_semantics": "DIRECT_CONTRACT",
                    }],
                },
                {
                    "step": 2,
                    "action_id": "A2",
                    "domain": "CODE",
                    "reads": ["x"],
                    "writes": ["terminal"],
                    "depends_on": ["A1"],
                    "dependency_composition": "SEQUENTIAL",
                    "checks": [{
                        "kind": "INVARIANT",
                        "id": "A2:I",
                        "pass": False,
                        "evidence": ["r2"],
                        "failure_semantics": "DERIVED_UPSTREAM",
                    }],
                },
            ],
            "terminal_failed_resources": ["terminal"],
        }
        out = normalize_case(raw)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertTrue(str(out["reason"]).startswith("FAILED_CHECK_RECEIPTS_EMPTY"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
