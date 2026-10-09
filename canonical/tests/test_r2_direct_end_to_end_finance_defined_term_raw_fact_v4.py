from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from canonical.runtime import r2_direct_end_to_end_adequacy_v3 as v3
from canonical.runtime import r2_direct_end_to_end_adequacy_v4 as v4
from canonical.runtime import general_adequate_decision_fixed_point_v2 as fixed
from canonical.tests.test_finance_defined_term_raw_fact_unless_v1 import case


def _goal(inp: str, out: str) -> str:
    return (
        "Using the source-defined raw-fact finance UNLESS case at "
        f"{inp}, select and independently verify the applicable branch "
        f"and save it to {out}."
    )


class R2DirectRouterV4FinanceRawFactTests(unittest.TestCase):
    def test_v4_routes_real_raw_fact_case(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            inp = root / "canonical/tmp/case.json"
            outp = root / "canonical/tmp/result.json"
            inp.parent.mkdir(parents=True, exist_ok=True)
            inp.write_text(json.dumps(case("130.00")), encoding="utf-8")
            goal = _goal("canonical/tmp/case.json", "canonical/tmp/result.json")
            request = {"task_id": "v4-raw-fact", "goal": goal}

            pf = v4.preflight(request, repo_root=root)
            self.assertTrue(pf["matched"], pf)
            self.assertEqual(
                pf["route_id"],
                v4.FINANCE_DEFINED_TERM_RAW_FACT_ROUTE_ID,
            )
            self.assertFalse(outp.exists())

            out = v4.run(request, repo_root=root)
            self.assertTrue(out["pass"], out)
            self.assertEqual(out["selected_branch"], "EXCEPTION_BRANCH")
            self.assertFalse(out["retry_by_other_route_authorized"])
            self.assertTrue(outp.is_file())

    def test_v4_fallback_equals_v3_for_nonmatching_goal(self):
        with TemporaryDirectory() as td:
            root = Path(td)
            request = {"task_id": "fallback", "goal": 'Reply with exactly "HELLO".'}
            self.assertEqual(
                v4.preflight(request, repo_root=root),
                v3.preflight(request, repo_root=root),
            )
            self.assertEqual(
                v4.run(request, repo_root=root),
                v3.run(request, repo_root=root),
            )

    def test_matched_failure_never_falls_through_to_v3(self):
        bad = {
            "matched": True,
            "status": "FAIL_CLOSED",
            "pass": False,
            "reason": "forced",
        }
        with patch.object(
            v4.finance_defined_raw,
            "preflight",
            return_value=bad,
        ), patch.object(
            v4.v3,
            "preflight",
            side_effect=AssertionError("fallback forbidden"),
        ):
            out = v4.preflight({"task_id": "x", "goal": "x"})
        self.assertEqual(out["status"], "FAIL_CLOSED")

    def test_fixed_point_front_door_closes_v4_at_step_zero(self):
        root = Path(fixed.__file__).resolve().parents[2]
        tmp = root / "canonical/astra_runtime/tmp"
        tmp.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(dir=tmp) as td:
            base = Path(td)
            inp = base / "case.json"
            outp = base / "result.json"
            inp.write_text(json.dumps(case("100.00")), encoding="utf-8")
            goal = _goal(
                inp.relative_to(root).as_posix(),
                outp.relative_to(root).as_posix(),
            )
            out = fixed.run(
                {"task_id": "v4-fixed-point", "goal": goal},
                repo_root=root,
            )
            self.assertTrue(out["pass"], out)
            self.assertEqual(
                out["route_id"],
                v4.FINANCE_DEFINED_TERM_RAW_FACT_ROUTE_ID,
            )
            self.assertEqual(
                out["r2_fixed_point_status"],
                "PASS__R2_DIRECT_END_TO_END_ADEQUACY_CLOSED",
            )
            self.assertEqual(out["r2_fixed_point_steps"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
