from __future__ import annotations

import copy
import unittest

from canonical.runtime import p1_v5_direct_surface_scope_relation_v1 as rel


class P1V5DirectSurfaceScopeRelationTests(unittest.TestCase):
    def sources(self):
        return (
            rel._load(rel.BINDING),
            rel._load(rel.PORTFOLIOS),
            rel._load(rel.FOUR_CONTRACTS),
            rel._load(rel.ABSOLUTE_SUITES),
            rel._load(rel.NATIVE_ROUTES),
            rel._load(rel.V5),
        )

    def test_live_relation_is_role_superset_but_not_terminal_or_full_surface_proof(self):
        out = rel.evaluate()
        self.assertTrue(out["status"].startswith("PASS__"), out)
        self.assertTrue(out["all_declared_p1_surface_relations_exact_or_superset"])
        self.assertTrue(out["v5_is_superset_carrier_for_frozen_p1_residual_role"])
        self.assertEqual(len(out["surface_relations"]), 3)
        self.assertEqual(len({r["claim_id"] for r in out["surface_relations"]}), 3)
        self.assertTrue(all(r["relation_scope"] == "UNRESOLVED_SEMANTICS_WITHIN_EXACT_FROZEN_P1_CONTRACT_ROLE_ONLY" for r in out["surface_relations"]))
        self.assertFalse(out["full_surface_superset_claim"])
        self.assertFalse(out["terminal_surface_proof_complete"])
        self.assertFalse(out["can_clear_p1_scope_quarantine"])
        self.assertFalse(out["execution_authority"])
        self.assertEqual(out["new_reality_units_consumed"], 0)

    def test_surface_without_p1_route_fails_closed(self):
        b, p, fc, a, nr, v = self.sources()
        p = copy.deepcopy(p)
        for s in p["portfolios"]["T0"]["surfaces"]:
            if s["id"] == "CURSORBENCH_4_0":
                s["proof_routes"] = []
        out = rel.evaluate(binding=b, portfolios=p, four_contracts=fc, absolute_suites=a, native_routes=nr, v5=v)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertTrue(any(x.startswith("P1_ROUTE_NOT_BOUND_TO_SURFACE:") for x in out["errors"]))

    def test_missing_first_class_scope_in_v5_fails_closed(self):
        b, p, fc, a, nr, v = self.sources()
        v = copy.deepcopy(v)
        v["scope"]["mechanism_classes"].remove("SCOPE")
        out = rel.evaluate(binding=b, portfolios=p, four_contracts=fc, absolute_suites=a, native_routes=nr, v5=v)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("V5_MECHANISM_SET_DRIFT", out["errors"])

    def test_weakened_p1_rescue_oracle_fails_closed(self):
        b, p, fc, a, nr, v = self.sources()
        a = copy.deepcopy(a)
        for suite in a["suites"]:
            if suite["id"] == "P1_TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_DIRECT":
                suite["oracle"].remove("NOMINATED_REPAIR_RESCUES_TERMINAL_OUTCOME")
        out = rel.evaluate(binding=b, portfolios=p, four_contracts=fc, absolute_suites=a, native_routes=nr, v5=v)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("P1_ORACLE_SET_DRIFT", out["errors"])

    def test_synthetic_terminal_firewall_cannot_be_removed(self):
        b, p, fc, a, nr, v = self.sources()
        b = copy.deepcopy(b)
        b["terminal_acceptance"]["standalone_synthetic_whole_domain_score_forbidden"] = False
        out = rel.evaluate(binding=b, portfolios=p, four_contracts=fc, absolute_suites=a, native_routes=nr, v5=v)
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertIn("SYNTHETIC_TERMINAL_SCORE_FIREWALL_MISSING", out["errors"])

    def test_scope_bridge_never_inherits_adjacent_surface_contracts(self):
        out = rel.evaluate()
        self.assertFalse(out["anti_overclaim"]["adjacent_contract_inheritance"])
        self.assertFalse(out["anti_overclaim"]["private_benchmark_score_reproduction_claim"])
        self.assertEqual(
            {r["relation"] for r in out["surface_relations"]},
            {"SUPERSET"},
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
