import unittest
from collections import Counter

from canonical.runtime import portfolio_multiplex_terminal_instrumentation_v1 as multiplex
from canonical.runtime import terminal_parent_portfolio_launcher_v1 as launcher


COMMITMENT = "candidate-package-commitment"
BEACON = "post-freeze-beacon"


def good_parent_rows(portfolio, *, commitment=COMMITMENT, beacon=BEACON):
    rows = []
    for behavior_id, binding in multiplex.BINDINGS.items():
        if portfolio not in binding["portfolios"]:
            continue
        rows.append(
            {
                "behavior_id": behavior_id,
                "portfolio": portfolio,
                "case_id": f"{portfolio}::{behavior_id}::case::0",
                "candidate_package_commitment": commitment,
                "post_freeze_beacon": beacon,
                "binding_blob": binding["binding_blob"],
                "load_bearing": True,
                "direct_instrumentation_pass": True,
                "parent_terminal_acceptance_pass": True,
                "case_replaced": False,
                "tuning_replay": False,
                "result_to_runtime_feedback": False,
                "candidate_visible_keys": ["task_visible_input"],
                "claims_behavior_credit": False,
            }
        )
    return rows


class TerminalParentPortfolioLauncherTests(unittest.TestCase):
    def test_static_route_algebra_is_exact_twelve(self):
        out = launcher.static_route_preflight()
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["active_contract_count"], 12)
        self.assertEqual(out["direct_multiplex_overlap"], [launcher.CAD_ID])

    def test_plan_deduplicates_shared_tool_route(self):
        out = launcher.build_launch_plan()
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["direct_route_execution_count"], 6)
        self.assertIn(launcher.direct.TOOL_ID, out["shared_direct_routes_deduplicated"])
        self.assertIn(launcher.direct.TOOL_ID, out["portfolios"]["T2"]["direct"])
        self.assertIn(launcher.direct.TOOL_ID, out["portfolios"]["T3"]["direct"])

    def test_zero_terminal_rehearsal_full_wave_passes_with_stubbed_runners(self):
        direct_calls = Counter()
        parent_calls = Counter()

        def parent_runner(portfolio, **kwargs):
            parent_calls[portfolio] += 1
            self.assertEqual(kwargs["commitment"], COMMITMENT)
            self.assertEqual(kwargs["beacon"], BEACON)
            return good_parent_rows(portfolio, **kwargs)

        def direct_runner(behavior_id, **kwargs):
            direct_calls[behavior_id] += 1
            return {
                "behavior_id": behavior_id,
                "pass": True,
                "terminal_result": True,
            }

        def cad_runner(**kwargs):
            direct_calls[launcher.CAD_ID] += 1
            return {
                "behavior_id": launcher.CAD_ID,
                "pass": True,
                "terminal_result": True,
            }

        out = launcher.execute_wave(
            commitment=COMMITMENT,
            beacon=BEACON,
            parent_runner=parent_runner,
            direct_runner=direct_runner,
            cad_runner=cad_runner,
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(parent_calls, Counter({"T0": 1, "T1": 1, "T2": 1, "T3": 1}))
        self.assertEqual(set(direct_calls), set(launcher.DIRECT_PORTFOLIOS))
        self.assertTrue(all(count == 1 for count in direct_calls.values()))
        self.assertEqual(out["shared_direct_route_duplicate_execution_count"], 0)

    def test_missing_required_parent_coverage_fails_closed(self):
        receipts = {
            p: good_parent_rows(p)
            for p in launcher.PORTFOLIOS
        }
        target = multiplex.M0
        receipts["T3"] = [
            row for row in receipts["T3"] if row["behavior_id"] != target
        ]
        out = launcher.validate_parent_receipts(
            receipts, commitment=COMMITMENT, beacon=BEACON
        )
        self.assertFalse(out["pass"])
        self.assertIn(
            f"MISSING_LOAD_BEARING_PARENT_COVERAGE:{target}:T3",
            out["errors"],
        )

    def test_beacon_mismatch_fails_closed(self):
        receipts = {p: good_parent_rows(p) for p in launcher.PORTFOLIOS}
        receipts["T0"][0]["post_freeze_beacon"] = "wrong"
        out = launcher.validate_parent_receipts(
            receipts, commitment=COMMITMENT, beacon=BEACON
        )
        self.assertFalse(out["pass"])
        self.assertTrue(any("PARENT_BEACON_MISMATCH" in err for err in out["errors"]))

    def test_direct_failure_blocks_wave(self):
        def parent_runner(portfolio, **kwargs):
            return good_parent_rows(portfolio, **kwargs)

        def direct_runner(behavior_id, **kwargs):
            return {
                "behavior_id": behavior_id,
                "pass": behavior_id != launcher.direct.BROWSER_ID,
                "terminal_result": True,
            }

        def cad_runner(**kwargs):
            return {
                "behavior_id": launcher.CAD_ID,
                "pass": True,
                "terminal_result": True,
            }

        out = launcher.execute_wave(
            commitment=COMMITMENT,
            beacon=BEACON,
            parent_runner=parent_runner,
            direct_runner=direct_runner,
            cad_runner=cad_runner,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["direct_failures"], [launcher.direct.BROWSER_ID])


if __name__ == "__main__":
    unittest.main(verbosity=2)
