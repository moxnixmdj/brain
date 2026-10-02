from __future__ import annotations

import unittest

from canonical.runtime.proof_coverage_compiler import evaluate


def route(rid, covers, **kw):
    base = {
        "id": rid,
        "covers": covers,
        "proof_mode": "FORMAL_PROOF",
        "zero_incremental_spend": True,
        "terminal_scope_authority": True,
        "prewave_admissible": True,
        "external_blocked": False,
        "new_reality_units": 0,
        "clean_case_spend": 0,
        "evidence_cost": 0.0,
    }
    base.update(kw)
    return base


class ProofCoverageCompilerTests(unittest.TestCase):
    def test_exact_minimum_prefers_one_multi_obligation_route(self):
        out = evaluate({
            "required_obligations": ["A", "B"],
            "routes": [
                route("A_ONLY", ["A"]),
                route("B_ONLY", ["B"]),
                route("BOTH", ["A", "B"]),
            ],
        })
        self.assertEqual(out["status"], "EXACT_MINIMUM_COVER_FOUND")
        self.assertEqual(out["selected_route_ids"], ["BOTH"])
        self.assertEqual(out["objective"]["route_count"], 1)

    def test_reality_units_dominate_route_count(self):
        out = evaluate({
            "required_obligations": ["A", "B"],
            "routes": [
                route("ONE_REALITY_ROUTE", ["A", "B"], new_reality_units=1),
                route("A_ZERO", ["A"]),
                route("B_ZERO", ["B"]),
            ],
        })
        self.assertEqual(out["selected_route_ids"], ["A_ZERO", "B_ZERO"])
        self.assertEqual(out["objective"]["new_reality_units"], 0)

    def test_partial_public_bar_without_scope_equivalence_is_rejected(self):
        out = evaluate({
            "required_obligations": ["A"],
            "routes": [
                route(
                    "PUBLIC",
                    ["A"],
                    proof_mode="PUBLIC_FIXED_BAR",
                    public_bar_source="https://example.invalid/bar",
                    zero_cost_executable=True,
                    harness_scope_equivalent=False,
                ),
            ],
        })
        self.assertEqual(out["status"], "INCOMPLETE_COVER")
        self.assertEqual(out["uncovered_obligations"], ["A"])
        self.assertIn("PUBLIC:PUBLIC_BAR_SCOPE_NOT_EQUIVALENT", out["rejected_routes"][0]["errors"])

    def test_matched_route_requires_exact_opus_binding(self):
        out = evaluate({
            "required_obligations": ["A"],
            "routes": [
                route(
                    "MATCHED",
                    ["A"],
                    proof_mode="MATCHED_EXACT_OPUS",
                    exact_opus_5_5_comparator_bound=False,
                    symmetric_harness_frozen=True,
                ),
            ],
        })
        self.assertEqual(out["status"], "INCOMPLETE_COVER")
        self.assertIn("MATCHED:EXACT_OPUS_COMPARATOR_NOT_BOUND", out["rejected_routes"][0]["errors"])

    def test_external_blocked_route_never_covers(self):
        out = evaluate({
            "required_obligations": ["A"],
            "routes": [route("BLOCKED", ["A"], external_blocked=True)],
        })
        self.assertEqual(out["status"], "INCOMPLETE_COVER")
        self.assertEqual(out["uncovered_obligations"], ["A"])

    def test_unknown_coverage_fails_route_closed(self):
        out = evaluate({
            "required_obligations": ["A"],
            "routes": [route("BAD", ["B"])],
        })
        self.assertEqual(out["status"], "INCOMPLETE_COVER")
        self.assertIn("BAD:UNKNOWN_OBLIGATION:B", out["rejected_routes"][0]["errors"])

    def test_tie_break_is_deterministic_by_route_id(self):
        out = evaluate({
            "required_obligations": ["A"],
            "routes": [route("Z", ["A"]), route("A_ROUTE", ["A"])],
        })
        self.assertEqual(out["selected_route_ids"], ["A_ROUTE"])

    def test_public_fixed_bar_requires_zero_cost_execution_and_source(self):
        out = evaluate({
            "required_obligations": ["A"],
            "routes": [
                route(
                    "BAR",
                    ["A"],
                    proof_mode="PUBLIC_FIXED_BAR",
                    harness_scope_equivalent=True,
                    zero_cost_executable=False,
                    public_bar_source="",
                ),
            ],
        })
        self.assertEqual(out["status"], "INCOMPLETE_COVER")
        errs = out["rejected_routes"][0]["errors"]
        self.assertIn("BAR:PUBLIC_BAR_NOT_ZERO_COST_EXECUTABLE", errs)
        self.assertIn("BAR:PUBLIC_BAR_SOURCE_MISSING", errs)


    def test_portfolio_multiplexed_open_domain_requires_frozen_binding_and_independent_preflight(self):
        rejected = evaluate({
            "required_obligations": ["A"],
            "routes": [
                route(
                    "MUX_BAD",
                    ["A"],
                    proof_mode="PORTFOLIO_MULTIPLEXED_OPEN_DOMAIN",
                    portfolio_multiplex_binding_frozen=False,
                    independent_preflight_bound=False,
                ),
            ],
        })
        self.assertEqual(rejected["status"], "INCOMPLETE_COVER")
        errs = rejected["rejected_routes"][0]["errors"]
        self.assertIn("MUX_BAD:PORTFOLIO_MULTIPLEX_BINDING_NOT_FROZEN", errs)
        self.assertIn("MUX_BAD:PORTFOLIO_MULTIPLEX_INDEPENDENT_PREFLIGHT_NOT_BOUND", errs)

        accepted = evaluate({
            "required_obligations": ["A"],
            "routes": [
                route(
                    "MUX_OK",
                    ["A"],
                    proof_mode="PORTFOLIO_MULTIPLEXED_OPEN_DOMAIN",
                    portfolio_multiplex_binding_frozen=True,
                    independent_preflight_bound=True,
                ),
            ],
        })
        self.assertEqual(accepted["status"], "EXACT_MINIMUM_COVER_FOUND")
        self.assertEqual(accepted["selected_route_ids"], ["MUX_OK"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
