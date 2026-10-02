from __future__ import annotations

import unittest

from canonical.runtime import multiplex_terminal_instrumentation_reducer_v1 as m


class MultiplexTerminalInstrumentationReducerTests(unittest.TestCase):
    def good_receipts(self,bid):
        rows=[]
        for p in m.PARENTS[bid]:
            rows.append(m.make_receipt(
                behavior_id=bid,
                portfolio=p,
                parent_case_id=f"{p}::case::0",
                load_bearing=True,
                instrumentation_pass=True,
                parent_terminal_pass=True,
            ))
        return rows

    def test_all_six_contracts_accept_complete_same_case_receipts(self):
        self.assertEqual(len(m.bound_behavior_ids()),6)
        for bid in m.bound_behavior_ids():
            with self.subTest(bid=bid):
                out=m.reduce_behavior(bid,self.good_receipts(bid))
                self.assertTrue(out["pass"],out)
                self.assertTrue(out["no_standalone_terminal_population_generated"])

    def test_missing_parent_coverage_fails_closed(self):
        rows=self.good_receipts(m.M0)
        rows=[x for x in rows if x["portfolio"]!="T3"]
        out=m.reduce_behavior(m.M0,rows)
        self.assertFalse(out["pass"])
        self.assertIn("MISSING_LOAD_BEARING_PARENT_COVERAGE:T3",out["errors"])

    def test_parent_terminal_failure_blocks_behavior(self):
        rows=self.good_receipts(m.P1)
        rows[0]["parent_terminal_pass"]=False
        out=m.reduce_behavior(m.P1,rows)
        self.assertFalse(out["pass"])
        self.assertIn("PARENT_TERMINAL_ACCEPTANCE_FAIL:0",out["errors"])

    def test_direct_instrumentation_failure_blocks_behavior(self):
        rows=self.good_receipts(m.P3)
        rows[0]["instrumentation_pass"]=False
        out=m.reduce_behavior(m.P3,rows)
        self.assertFalse(out["pass"])
        self.assertIn("DIRECT_INSTRUMENTATION_FAIL:0",out["errors"])

    def test_cross_behavior_inheritance_is_forbidden(self):
        rows=self.good_receipts(m.STRUCTURED)
        rows[0]["cross_behavior_score_inheritance"]=True
        out=m.reduce_behavior(m.STRUCTURED,rows)
        self.assertFalse(out["pass"])
        self.assertIn("CROSS_BEHAVIOR_SCORE_INHERITANCE_NOT_FALSE:0",out["errors"])

    def test_duplicate_parent_case_cannot_double_count(self):
        rows=self.good_receipts(m.P2)
        rows.append(dict(rows[0]))
        out=m.reduce_behavior(m.P2,rows)
        self.assertFalse(out["pass"])
        self.assertTrue(any(x.startswith("DUPLICATE_PARENT_CASE:") for x in out["errors"]))

    def test_non_load_bearing_case_cannot_claim_positive_instrumentation(self):
        with self.assertRaises(ValueError):
            m.make_receipt(
                behavior_id=m.NATIVE,
                portfolio="T1",
                parent_case_id="T1::case::x",
                load_bearing=False,
                instrumentation_pass=True,
                parent_terminal_pass=True,
            )

    def test_tuning_replay_fails_closed(self):
        rows=self.good_receipts(m.M0)
        rows[0]["case_replayed_for_tuning"]=True
        out=m.reduce_behavior(m.M0,rows)
        self.assertFalse(out["pass"])
        self.assertIn("TUNING_REPLAY_NOT_FALSE:0",out["errors"])


if __name__=="__main__":
    unittest.main(verbosity=2)
