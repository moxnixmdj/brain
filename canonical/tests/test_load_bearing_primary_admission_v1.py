import unittest

from execution_guard.load_bearing_primary_admission import admission_errors

OPEN = ["A", "B", "C"]


def base():
    return {
        "highest_leverage_now": True,
        "load_bearing_primary": {
            "open_obligation_ids": ["A"],
            "constructive_gap_for_open_obligation_ids": [],
            "scope_complete_discharge": False,
            "expected_obligation_discharge_lcb": "1/2",
            "expected_obligation_unlock_lcb": "0",
            "success_probability_lcb": "4/5",
            "wall_clock_cost_ub": "2",
        },
    }


class Tests(unittest.TestCase):
    def test_direct_open_obligation_passes(self):
        self.assertEqual(admission_errors(base(), OPEN), [])

    def test_missing_binding_fails(self):
        x = base()
        x.pop("load_bearing_primary")
        self.assertEqual(admission_errors(x, OPEN), ["LOAD_BEARING_PRIMARY_BINDING_MISSING"])

    def test_stale_target_fails(self):
        x = base()
        x["load_bearing_primary"]["open_obligation_ids"] = ["OLD"]
        self.assertIn("LOAD_BEARING_TARGET_NOT_CURRENT_OPEN:OLD", admission_errors(x, OPEN))

    def test_constructive_gap_passes(self):
        x = base()
        x["load_bearing_primary"]["open_obligation_ids"] = []
        x["load_bearing_primary"]["constructive_gap_for_open_obligation_ids"] = ["B"]
        x["load_bearing_primary"]["expected_obligation_discharge_lcb"] = 0
        x["load_bearing_primary"]["expected_obligation_unlock_lcb"] = "1/3"
        self.assertEqual(admission_errors(x, OPEN), [])

    def test_scope_complete_passes(self):
        x = base()
        x["load_bearing_primary"]["open_obligation_ids"] = []
        x["load_bearing_primary"]["scope_complete_discharge"] = True
        self.assertEqual(admission_errors(x, OPEN), [])

    def test_zero_yield_fails(self):
        x = base()
        x["load_bearing_primary"]["expected_obligation_discharge_lcb"] = 0
        x["load_bearing_primary"]["expected_obligation_unlock_lcb"] = 0
        self.assertIn("LOAD_BEARING_EXPECTED_YIELD_NOT_POSITIVE", admission_errors(x, OPEN))

    def test_probability_above_one_fails(self):
        x = base()
        x["load_bearing_primary"]["success_probability_lcb"] = "3/2"
        self.assertIn("LOAD_BEARING_SUCCESS_PROBABILITY_LCB_GT_ONE", admission_errors(x, OPEN))

    def test_no_open_obligations_disables_gate(self):
        self.assertEqual(admission_errors({}, []), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
