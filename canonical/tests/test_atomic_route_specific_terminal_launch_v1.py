from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path
from unittest import mock

from canonical.runtime import atomic_route_specific_terminal_launch_v1 as a
from canonical.runtime import portfolio_multiplex_terminal_instrumentation_v1 as multiplex


class AtomicRouteSpecificTerminalLaunchTests(unittest.TestCase):
    C = "TEST_ONLY_COMMITMENT"
    B = "TEST_ONLY_BEACON"

    @property
    def root(self) -> Path:
        return Path(__file__).resolve().parents[2]

    def _good_parent_rows(self, commitment: str, beacon: str):
        out = {}
        required = a.REQUIRED_MULTIPLEX_PARENTS
        for bid in sorted(a.MULTIPLEX_IDS):
            rows = []
            for portfolio in sorted(required[bid]):
                rows.append({
                    "behavior_id": bid,
                    "portfolio": portfolio,
                    "case_id": f"{portfolio}::case::0",
                    "candidate_package_commitment": commitment,
                    "post_freeze_beacon": beacon,
                    "binding_blob": multiplex.BINDINGS[bid]["binding_blob"],
                    "load_bearing": True,
                    "direct_instrumentation_pass": True,
                    "parent_terminal_acceptance_pass": True,
                    "case_replaced": False,
                    "tuning_replay": False,
                    "result_to_runtime_feedback": False,
                    "candidate_visible_keys": ["public_task"],
                    "claims_behavior_credit": False,
                })
            out[bid] = rows
        return out

    def test_prelaunch_commitment_is_deterministic_and_case_free(self):
        with mock.patch(
            "canonical.runtime.cad_t0_geometry_population.generate_post_freeze",
            side_effect=AssertionError("terminal case generator called"),
        ), mock.patch.object(
            a.direct, "execute_direct_route", side_effect=AssertionError("direct terminal executor called")
        ), mock.patch.object(
            a.saccr, "execute_terminal", side_effect=AssertionError("SA-CCR terminal executor called")
        ):
            one = a.build_prelaunch_commitment(self.root)
            two = a.build_prelaunch_commitment(self.root)
        self.assertTrue(one["pass"], one)
        self.assertEqual(one["candidate_package_commitment"], two["candidate_package_commitment"])
        self.assertFalse(one["terminal_case_generation_performed"])
        self.assertEqual(one["executor_state"]["derived_bound_executor_count"], 12)

    def test_shadow_never_generates_terminal_cases(self):
        with mock.patch(
            "canonical.runtime.cad_t0_geometry_population.generate_post_freeze",
            side_effect=AssertionError("terminal case generator called"),
        ), mock.patch.object(
            a.direct, "execute_direct_route", side_effect=AssertionError("direct terminal executor called")
        ), mock.patch.object(
            a.saccr, "execute_terminal", side_effect=AssertionError("SA-CCR terminal executor called")
        ):
            out = a.shadow_preflight(self.root)
        self.assertFalse(out["terminal_case_generation_performed"])
        self.assertEqual(out["terminal_results_observed"], 0)
        self.assertEqual(out["derived_bound_executor_count"], 12)

    def test_parent_observation_validation_requires_all_frozen_parent_portfolios(self):
        rows = self._good_parent_rows(self.C, self.B)
        rows[multiplex.M0] = [x for x in rows[multiplex.M0] if x["portfolio"] != "T3"]
        out = a.validate_parent_observations(rows, commitment=self.C, beacon=self.B)
        self.assertFalse(out["pass"])
        self.assertTrue(any(x.startswith("MISSING_LOAD_BEARING_PARENT_COVERAGE:") for x in out["errors"]))

    def test_parent_observation_validation_binds_exact_commitment_and_beacon(self):
        rows = self._good_parent_rows(self.C, self.B)
        rows[multiplex.P3][0]["candidate_package_commitment"] = "WRONG"
        rows[multiplex.P3][1]["post_freeze_beacon"] = "WRONG"
        out = a.validate_parent_observations(rows, commitment=self.C, beacon=self.B)
        self.assertFalse(out["pass"])
        self.assertTrue(any(x.startswith("COMMITMENT_MISMATCH:") for x in out["errors"]))
        self.assertTrue(any(x.startswith("BEACON_MISMATCH:") for x in out["errors"]))

    def test_replay_and_cross_behavior_shortcuts_fail_closed(self):
        rows = self._good_parent_rows(self.C, self.B)
        rows[multiplex.M0][0]["tuning_replay"] = True
        rows[multiplex.STRUCTURED][0]["candidate_visible_keys"] = ["hidden_oracle"]
        out = a.validate_parent_observations(rows, commitment=self.C, beacon=self.B)
        self.assertFalse(out["pass"])
        self.assertIn("MULTIPLEX_REDUCTION_FAIL:" + multiplex.M0, out["errors"])
        self.assertIn("MULTIPLEX_REDUCTION_FAIL:" + multiplex.STRUCTURED, out["errors"])

    def test_real_execution_refuses_before_authority_without_touching_direct_cases(self):
        commitment = a.build_prelaunch_commitment(self.root)
        self.assertTrue(commitment["pass"], commitment)
        rows = self._good_parent_rows(commitment["candidate_package_commitment"], self.B)
        with mock.patch.object(
            a.cad, "execute_cad_route", side_effect=AssertionError("CAD terminal executor called")
        ), mock.patch.object(
            a.direct, "execute_direct_route", side_effect=AssertionError("direct terminal executor called")
        ), mock.patch.object(
            a.saccr, "execute_terminal", side_effect=AssertionError("SA-CCR terminal executor called")
        ):
            out = a.execute_real(
                commitment=commitment["candidate_package_commitment"],
                beacon=self.B,
                parent_observations=rows,
                root=self.root,
            )
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED_PRELAUNCH_NOT_AUTHORIZED")
        self.assertEqual(out["terminal_results_observed"], 0)

    def test_live_execution_plan_uses_current_cad_v4_binding(self):
        plan = json.loads((self.root / a.PLAN).read_text(encoding="utf-8"))
        cad = next(x for x in plan["direct_populations"] if x["behavior_id"] == a.CAD_ID)
        self.assertEqual(cad["binding"]["path"], "canonical/governance/CAD_T0_POST_REFREEZE_BINDING_V4.json")
        self.assertEqual(cad["binding"]["blob_sha"], "a636d1292e6f92d240fab420a9ee75ced7a05104")


if __name__ == "__main__":
    unittest.main(verbosity=2)
