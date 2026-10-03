#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from canonical.runtime import tool_discovery_retrieval_false_negative_benchmark_v1 as bench

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "canonical/governance/TOOL_DISCOVERY_MULTILINGUAL_RETRIEVAL_INPUT_V1.json"


def load_input():
    return json.loads(INPUT.read_text(encoding="utf-8"))


class ToolDiscoveryRetrievalFalseNegativeBenchmarkV1Tests(unittest.TestCase):
    def test_frozen_supported_fixture_universe_has_perfect_recall(self):
        out = bench.evaluate(load_input())
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["finite_supported_fixture_recall"], 1.0, out)
        self.assertEqual(out["supported_fixture_missed_count"], 0, out)
        self.assertEqual(
            out["supported_fixture_found_count"],
            out["supported_fixture_count"],
            out,
        )

    def test_non_latin_languages_are_present_in_real_query_lattice(self):
        out = bench.evaluate(load_input())
        hints = set(out["language_hints"])
        for hint in ("CJK", "ARABIC", "CYRILLIC", "LATIN"):
            self.assertIn(hint, hints, (hint, hints))

    def test_open_world_unsupported_boundaries_never_become_nonexistence(self):
        out = bench.evaluate(load_input())
        self.assertGreater(out["unsupported_boundary_count"], 0)
        for row in out["unsupported_boundaries"]:
            self.assertEqual(
                row["state"],
                "UNKNOWN_OUTSIDE_PROVED_FINITE_FIXTURE_SCOPE",
                row,
            )
            self.assertFalse(row["nonexistence_claim_authorized"], row)

    def test_removing_chinese_variants_creates_detectable_false_negative(self):
        x = load_input()
        x = copy.deepcopy(x)
        x["language_variants"].pop("zh")
        out = bench.evaluate(x)
        self.assertFalse(out["pass"], out)
        self.assertLess(out["finite_supported_fixture_recall"], 1.0, out)
        missed = {row["fixture_id"] for row in out["missed_fixtures"]}
        self.assertIn("ZH_METADATA_ONLY", missed)

    def test_removing_exact_route_identifier_creates_detectable_false_negative(self):
        x = copy.deepcopy(load_input())
        x["aliases"] = [v for v in x["aliases"] if "valid_route_top1" not in v]
        x["observables"]["api_symbols"] = [
            v for v in x["observables"]["api_symbols"]
            if v != "valid_route_top1"
        ]
        out = bench.evaluate(x)
        self.assertFalse(out["pass"], out)
        missed = {row["fixture_id"] for row in out["missed_fixtures"]}
        self.assertIn("DESCRIPTIONLESS_CODE_IDENTIFIER", missed)

    def test_misleading_metadata_fixture_is_recovered_from_code_observable(self):
        out = bench.evaluate(load_input())
        row = next(
            x for x in out["found_fixtures"]
            if x["fixture_id"] == "MISLEADING_REPO_NAME"
        )
        self.assertGreater(row["match_count"], 0, row)
        self.assertEqual(row["surface"], "CODE_CONTENT")

    def test_benchmark_grants_zero_authority_or_credit(self):
        out = bench.evaluate(load_input())
        self.assertEqual(out["capability_credit_delta"], 0)
        self.assertEqual(out["family_credit_delta"], 0)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])
        self.assertIn(
            "FINITE_FIXTURE_RECALL_1_0_IS_NOT_OPEN_WORLD_RECALL_1_0",
            out["hard_nonclaims"],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
