from __future__ import annotations
import unittest

from canonical.runtime.finance_metric_formula_v1 import (
    FinanceFormulaError,
    average_expression,
    beat_miss_expression,
    cagr_expression,
    debt_to_equity_expression,
    debt_to_total_capital_expression,
    difference_bps_expression,
    dio_expression,
    fixed_charge_coverage_expression,
    formula_record,
    margin_expression,
    midpoint_expression,
    percent_change_expression,
)

class Tests(unittest.TestCase):
    def test_public_style_formulas_compile_without_rounding(self):
        self.assertEqual(cagr_expression(100,176.41,2),"((176.41/100)**(1/2)-1)*100")
        self.assertEqual(difference_bps_expression("17.05","16.45"),"(17.05-16.45)*100")
        self.assertEqual(midpoint_expression(100,120),"(100+120)/2")
        self.assertEqual(percent_change_expression(100,102.2),"((102.2/100)-1)*100")
        self.assertEqual(margin_expression(6363,25846),"(6363/25846)*100")
        self.assertEqual(
            dio_expression(22000,22427,106100,371),
            "(((22000+22427)/2)/106100)*371",
        )
        self.assertEqual(debt_to_equity_expression(1365,100),"1365/100")
        self.assertEqual(
            debt_to_total_capital_expression(1365,100),
            "(1365/(1365+100))*100",
        )
        self.assertEqual(fixed_charge_coverage_expression(9056,920),"9056/920")
        self.assertEqual(beat_miss_expression(104,100),"((104/100)-1)*100")
        self.assertEqual(average_expression([1,2,3]),"(1+2+3)/3")

    def test_record_keeps_convention_explicit(self):
        out=formula_record(
            "DIO",
            dio_expression(22000,22427,106100,371),
            convention="actual fiscal-year days; average beginning/ending inventory",
        )
        self.assertFalse(out["accounting_convention_selection_authority"])
        self.assertFalse(out["intermediate_rounding_allowed"])
        self.assertTrue(out["calculator_execution_required"])

    def test_invalid_denominators_fail_closed(self):
        with self.assertRaises(FinanceFormulaError):
            margin_expression(1,0)
        with self.assertRaises(FinanceFormulaError):
            debt_to_total_capital_expression(1,-1)
        with self.assertRaises(FinanceFormulaError):
            cagr_expression(0,2,2)

if __name__=="__main__":
    unittest.main()
