from __future__ import annotations

import unittest
from unittest.mock import patch

from canonical.runtime import r2_direct_end_to_end_adequacy_v21 as v21
from canonical.runtime import r2_regcap_context_selection_direct_adequacy_v1 as direct
from canonical.runtime import general_adequate_decision_fixed_point_v2 as fp


class Tests(unittest.TestCase):
    def test_nonmatching_goal_delegates_to_v20(self):
        request = {"task_id": "x", "goal": "Unrelated task."}
        expected = {"matched": False, "status": "V20"}
        with patch.object(v21.v20, "preflight", return_value=expected) as prior:
            out = v21.preflight(request)
        self.assertEqual(out, expected)
        prior.assert_called_once()

    def test_matched_regcap_route_precedes_v20(self):
        request = {"task_id": "x", "goal": "matched"}
        with patch.object(
            v21.local,
            "preflight",
            return_value={"matched": True, "route_id": direct.ROUTE_ID},
        ), patch.object(
            v21.local,
            "run",
            return_value={"pass": True, "route_id": direct.ROUTE_ID},
        ) as local_run, patch.object(v21.v20, "run") as prior:
            out = v21.run(request)
        self.assertTrue(out["pass"])
        self.assertEqual(out["route_id"], direct.ROUTE_ID)
        local_run.assert_called_once()
        prior.assert_not_called()

    def test_semantic_open_precedes_v20(self):
        request = {"task_id": "x", "goal": "open"}
        opened = {
            "matched": False,
            "direct_route_semantic_open": True,
            "status": "OPEN__REGCAP_CONTEXT_SELECTION_NOT_YET_PROVED",
            "route_id": direct.ROUTE_ID,
        }
        with patch.object(v21.local, "preflight", return_value=opened), patch.object(
            v21.v20, "preflight"
        ) as prior:
            out = v21.preflight(request)
        self.assertEqual(out, opened)
        prior.assert_not_called()

    def test_fixed_point_is_bound_to_v21(self):
        self.assertIs(fp.direct_adequacy, v21)

    def test_fixed_point_closes_when_v21_direct_route_passes(self):
        request = {"task_id": "x", "goal": "bounded regcap direct"}
        direct_result = {
            "pass": True,
            "matched": True,
            "status": "PASS__DIRECT_END_TO_END_ADEQUACY_VERIFIED",
            "route_id": direct.ROUTE_ID,
            "execution_attempted": True,
        }
        with patch.object(
            fp.direct_adequacy,
            "preflight",
            return_value={"matched": True, "route_id": direct.ROUTE_ID},
        ), patch.object(
            fp.direct_adequacy,
            "run",
            return_value=direct_result,
        ):
            out = fp.run(request)
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["r2_fixed_point_status"],
            "PASS__R2_DIRECT_END_TO_END_ADEQUACY_CLOSED",
        )
        self.assertEqual(
            out["r2_fixed_point_trace"][0]["route_id"],
            direct.ROUTE_ID,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
