import json
import unittest
from canonical.runtime import h100_library_first_routing_v1 as r

class H100LibraryFirstRoutingTests(unittest.TestCase):
    def test_precommit_route_orders_are_exact(self):
        d=json.loads(r.PRE.read_text())
        self.assertEqual(d["route_orders"]["LIBRARY_FIRST"][0],"ZERO_LEARNED_PARAMETRIC_UNARY_FAMILY_ROUTE")
        self.assertEqual(d["route_orders"]["RAW_FIRST"][-1],"ZERO_LEARNED_PARAMETRIC_UNARY_FAMILY_ROUTE")

    def test_library_first_wins_immediately_on_every_frozen_transfer_task(self):
        d=json.loads(r.TRANSFER_PRE.read_text())
        fam={x["transfer_task"]["task_id"]:x["compiled_family"] for x in d["families"]}
        order=json.loads(r.PRE.read_text())["route_orders"]["LIBRARY_FIRST"]
        for task_id,expected in fam.items():
            out=r.run_order(task_id,expected,order,d)
            self.assertTrue(out["success"],out)
            self.assertEqual(out["winner_route"],"ZERO_LEARNED_PARAMETRIC_UNARY_FAMILY_ROUTE")
            self.assertEqual(out["attempted_route_count"],1)

    def test_raw_first_reaches_same_winner_after_three_failed_generic_routes(self):
        d=json.loads(r.TRANSFER_PRE.read_text())
        fam={x["transfer_task"]["task_id"]:x["compiled_family"] for x in d["families"]}
        order=json.loads(r.PRE.read_text())["route_orders"]["RAW_FIRST"]
        for task_id,expected in fam.items():
            out=r.run_order(task_id,expected,order,d)
            self.assertTrue(out["success"],out)
            self.assertEqual(out["winner_route"],"ZERO_LEARNED_PARAMETRIC_UNARY_FAMILY_ROUTE")
            self.assertEqual(out["attempted_route_count"],4)

    def test_full_measurement_is_zero_learned(self):
        out=r.run()
        self.assertEqual(len(out["tasks"]),3)
        self.assertEqual(out["persistent_learned_bytes"],0)
        self.assertEqual(out["h100_terminal_credit_delta"],0)
        for row in out["tasks"]:
            self.assertGreater(row["measured_wall_clock_speedup_raw_over_library"],1.0)

if __name__=="__main__":
    unittest.main(verbosity=2)
