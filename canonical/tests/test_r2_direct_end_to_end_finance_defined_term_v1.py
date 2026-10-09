from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from canonical.runtime import r2_direct_end_to_end_adequacy_v1 as router
from canonical.tests.test_finance_defined_term_raw_fact_unless_v1 import case


ROOT = Path(__file__).resolve().parents[2]
TMP = ROOT / "canonical" / "astra_runtime" / "tmp"


class R2DirectEndToEndFinanceDefinedTermIntegrationTests(unittest.TestCase):
    def test_real_front_door_routes_and_executes_defined_term_raw_fact_case(self):
        TMP.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(dir=TMP) as td:
            base = Path(td)
            inp = base / "case.json"
            outp = base / "result.json"
            inp.write_text(json.dumps(case("130.00")), encoding="utf-8")
            input_rel = inp.relative_to(ROOT).as_posix()
            output_rel = outp.relative_to(ROOT).as_posix()
            goal = (
                "Using the source-defined raw-fact finance UNLESS case at "
                f"{input_rel}, select and independently verify the applicable branch "
                f"and save it to {output_rel}."
            )
            request = {"task_id": "front-door-defined-term", "goal": goal}

            pf = router.preflight(request)
            self.assertTrue(pf["matched"], pf)
            self.assertEqual(
                pf["route_id"],
                router.FINANCE_DEFINED_TERM_RAW_FACT_UNLESS_ROUTE_ID,
            )
            self.assertFalse(outp.exists())

            result = router.run(request)
            self.assertTrue(result["pass"], result)
            self.assertEqual(
                result["route_id"],
                router.FINANCE_DEFINED_TERM_RAW_FACT_UNLESS_ROUTE_ID,
            )
            self.assertTrue(result["semantic_acceptance_complete"])
            self.assertTrue(result["actual_goal_satisfaction_verified"])
            self.assertFalse(result["retry_by_other_route_authorized"])
            self.assertTrue(outp.is_file())

    def test_matched_preflight_failure_cannot_fall_through(self):
        bad = {
            "matched": True,
            "status": "FAIL_CLOSED",
            "reason": "forced",
        }
        with patch.object(
            router.finance_defined_term_adequacy,
            "preflight",
            return_value=bad,
        ), patch.object(
            router.finance_typed_unless_adequacy,
            "preflight",
            side_effect=AssertionError("fallback forbidden"),
        ):
            out = router.preflight({"task_id": "x", "goal": "not otherwise matched"})
        self.assertEqual(out["status"], "FAIL_CLOSED")
        self.assertEqual(
            out["route_id"],
            router.FINANCE_DEFINED_TERM_RAW_FACT_UNLESS_ROUTE_ID,
        )

    def test_matched_execution_failure_cannot_fall_through(self):
        pf = {
            "matched": True,
            "route_id": router.FINANCE_DEFINED_TERM_RAW_FACT_UNLESS_ROUTE_ID,
            "capability_id": "finance.defined_term_raw_fact.unless.stdlib",
            "goal_sha256": "a" * 64,
            "semantic_scope": router.ROUTES[
                router.FINANCE_DEFINED_TERM_RAW_FACT_UNLESS_ROUTE_ID
            ]["scope"],
        }
        failed = {
            "pass": False,
            "status": "OPEN__DIRECT_ADEQUACY_ROUTE_DID_NOT_VERIFY",
            "reason": "forced",
        }
        with patch.object(router, "preflight", return_value=pf), patch.object(
            router.finance_defined_term_adequacy,
            "run",
            return_value=failed,
        ), patch.object(
            router.finance_typed_unless_adequacy,
            "run",
            side_effect=AssertionError("fallback forbidden"),
        ):
            out = router.run({"task_id": "x", "goal": "x"})
        self.assertFalse(out["pass"])
        self.assertFalse(out["retry_by_other_route_authorized"])
        self.assertEqual(
            out["route_id"],
            router.FINANCE_DEFINED_TERM_RAW_FACT_UNLESS_ROUTE_ID,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
