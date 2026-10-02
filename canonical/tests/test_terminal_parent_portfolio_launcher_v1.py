from __future__ import annotations

import inspect
import unittest
from collections import Counter
from unittest.mock import patch

from canonical.runtime import portfolio_multiplex_terminal_instrumentation_v1 as multiplex
from canonical.runtime import terminal_parent_portfolio_launcher_v1 as launcher

COMMITMENT = "candidate-package-commitment"
BEACON = "post-freeze-beacon"


def good_parent_rows(portfolio, *, commitment=COMMITMENT, beacon=BEACON):
    rows = []
    for behavior_id, binding in multiplex.BINDINGS.items():
        if portfolio not in binding["portfolios"]:
            continue
        rows.append({
            "behavior_id": behavior_id,
            "portfolio": portfolio,
            "case_id": f"{portfolio}::{behavior_id}::aggregate",
            "candidate_package_commitment": commitment,
            "post_freeze_beacon": beacon,
            "binding_blob": binding["binding_blob"],
            "load_bearing": True,
            "direct_instrumentation_pass": True,
            "parent_terminal_acceptance_pass": True,
            "case_replaced": False,
            "tuning_replay": False,
            "result_to_runtime_feedback": False,
            "candidate_visible_keys": ["PUBLIC_TASK_PAYLOAD_ONLY"],
            "claims_behavior_credit": False,
        })
    return rows


def direct_result(behavior_id):
    row = {
        "behavior_id": behavior_id,
        "pass": True,
        "terminal_result": True,
    }
    if behavior_id == launcher.CAD_ID:
        row["case_count"] = 128
        row["cases"] = [{"case_id": f"CAD::{i}"} for i in range(128)]
    return row


class TerminalParentPortfolioLauncherTests(unittest.TestCase):
    def test_static_route_algebra_is_exact_twelve(self):
        out = launcher.static_route_preflight()
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["active_contract_count"], 12)
        self.assertEqual(out["direct_multiplex_overlap"], [launcher.CAD_ID])

    def test_public_execute_wave_exposes_no_runner_injection_parameters(self):
        params = set(inspect.signature(launcher.execute_wave).parameters)
        self.assertEqual(params, {"commitment", "beacon", "root"})

    def test_authority_guard_blocks_before_any_runner_invocation(self):
        with patch.object(
            launcher.launch_authority, "evaluate",
            return_value={"launch_authority": False, "failed_predicates": ["X"]},
        ), patch.object(
            launcher.direct, "execute_direct_route",
            side_effect=AssertionError("direct terminal executor called"),
        ), patch.object(
            launcher.cad, "execute_cad_route",
            side_effect=AssertionError("CAD terminal executor called"),
        ), patch.object(
            launcher.parent_runner, "execute_parent_portfolio",
            side_effect=AssertionError("parent producer called"),
        ):
            out = launcher.execute_wave(commitment=COMMITMENT, beacon=BEACON)
        self.assertFalse(out["pass"])
        self.assertEqual(out["status"], "FAIL_CLOSED_LAUNCH_NOT_AUTHORIZED")
        self.assertFalse(out["direct_runner_invoked"])
        self.assertFalse(out["parent_runner_invoked"])

    def test_canonical_direct_routes_run_once_before_parent_and_only_cad_is_shared(self):
        direct_calls = Counter()
        parent_calls = Counter()
        events = []

        def direct_run(behavior_id, **kwargs):
            events.append("D:" + behavior_id)
            direct_calls[behavior_id] += 1
            return direct_result(behavior_id)

        def cad_run(**kwargs):
            events.append("D:" + launcher.CAD_ID)
            direct_calls[launcher.CAD_ID] += 1
            return direct_result(launcher.CAD_ID)

        def parent_run(portfolio, **kwargs):
            events.append("P:" + portfolio)
            parent_calls[portfolio] += 1
            self.assertEqual(set(kwargs["direct_results"]), {launcher.CAD_ID})
            self.assertEqual(kwargs["direct_results"][launcher.CAD_ID]["case_count"], 128)
            self.assertEqual(sum(direct_calls.values()), 6)
            return good_parent_rows(
                portfolio,
                commitment=kwargs["commitment"],
                beacon=kwargs["beacon"],
            )

        with patch.object(
            launcher.launch_authority, "evaluate",
            return_value={"launch_authority": True},
        ), patch.object(
            launcher.direct, "execute_direct_route", side_effect=direct_run
        ), patch.object(
            launcher.cad, "execute_cad_route", side_effect=cad_run
        ), patch.object(
            launcher.parent_runner, "execute_parent_portfolio", side_effect=parent_run
        ):
            out = launcher.execute_wave(commitment=COMMITMENT, beacon=BEACON)

        self.assertTrue(out["pass"], out)
        self.assertEqual(set(direct_calls), set(launcher.DIRECT_PORTFOLIOS))
        self.assertTrue(all(v == 1 for v in direct_calls.values()))
        self.assertEqual(parent_calls, Counter({"T0": 1, "T1": 1, "T2": 1, "T3": 1}))
        first_parent = min(i for i, x in enumerate(events) if x.startswith("P:"))
        self.assertTrue(all(x.startswith("D:") for x in events[:first_parent]))
        self.assertEqual(out["shared_direct_route_duplicate_execution_count"], 0)
        self.assertTrue(out["canonical_parent_runner_only"])
        self.assertTrue(out["canonical_direct_runners_only"])
        self.assertTrue(out["cad_parent_reuses_exact_direct_result"])

    def test_direct_failure_does_not_selectively_skip_parent_portfolios(self):
        parent_calls = Counter()

        def direct_run(behavior_id, **kwargs):
            row = direct_result(behavior_id)
            if behavior_id == launcher.direct.BROWSER_ID:
                row["pass"] = False
            return row

        def parent_run(portfolio, **kwargs):
            parent_calls[portfolio] += 1
            return good_parent_rows(
                portfolio,
                commitment=kwargs["commitment"],
                beacon=kwargs["beacon"],
            )

        with patch.object(
            launcher.launch_authority, "evaluate",
            return_value={"launch_authority": True},
        ), patch.object(
            launcher.direct, "execute_direct_route", side_effect=direct_run
        ), patch.object(
            launcher.cad, "execute_cad_route",
            return_value=direct_result(launcher.CAD_ID),
        ), patch.object(
            launcher.parent_runner, "execute_parent_portfolio", side_effect=parent_run
        ):
            out = launcher.execute_wave(commitment=COMMITMENT, beacon=BEACON)

        self.assertFalse(out["pass"])
        self.assertEqual(out["direct_failures"], [launcher.direct.BROWSER_ID])
        self.assertEqual(parent_calls, Counter({"T0": 1, "T1": 1, "T2": 1, "T3": 1}))

    def test_missing_required_parent_coverage_fails_closed(self):
        receipts = {p: good_parent_rows(p) for p in launcher.PORTFOLIOS}
        receipts["T3"] = [
            row for row in receipts["T3"] if row["behavior_id"] != multiplex.M0
        ]
        out = launcher.validate_parent_receipts(
            receipts, commitment=COMMITMENT, beacon=BEACON
        )
        self.assertFalse(out["pass"])
        self.assertIn(
            f"MISSING_LOAD_BEARING_PARENT_COVERAGE:{multiplex.M0}:T3",
            out["errors"],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
