from __future__ import annotations

import hashlib
import unittest

from canonical.runtime import direct_route_terminal_executors_v1 as ex


class DirectRouteTerminalExecutorsTests(unittest.TestCase):
    C="TEST_ONLY_COMMITMENT"
    B="TEST_ONLY_NONTERMINAL_BEACON"

    def test_exact_frozen_counts(self):
        self.assertEqual(ex.COUNTS[ex.SA_CCR_ID], 2000)
        self.assertEqual(ex.COUNTS[ex.BROWSER_ID], 150)
        self.assertEqual(ex.COUNTS[ex.DELEGATION_ID], 132)
        self.assertEqual(ex.COUNTS[ex.TOOL_ID], 180)
        self.assertEqual(ex.COUNTS[ex.RESEARCH_ID], 180)

    def test_saccr_case_id_and_global_v2_seed_rule(self):
        cid=f"{ex.SA_CCR_ID}::SA_CCR_TERMINAL_POPULATION_V1::slot::17"
        self.assertEqual(ex.case_id(ex.SA_CCR_ID,17),cid)
        raw=b"PROJECT_BRAIN_TERMINAL_V2\0"+self.C.encode()+b"\0"+self.B.encode()+b"\0"+cid.encode()
        expected=int.from_bytes(hashlib.sha256(raw).digest()[:8],"big")
        self.assertEqual(ex.derive_seed(ex.SA_CCR_ID,self.C,self.B,17),expected)

    def test_route_specific_prefixes_change_seed_namespace(self):
        seeds={
            bid:ex.derive_seed(bid,self.C,self.B,0)
            for bid in (ex.SA_CCR_ID,ex.BROWSER_ID,ex.DELEGATION_ID,ex.TOOL_ID,ex.RESEARCH_ID)
        }
        self.assertEqual(len(set(seeds.values())),5)

    def test_each_direct_route_executes_one_case_information_safely(self):
        runners=(
            ex.run_saccr_case,
            ex.run_browser_case,
            ex.run_delegation_case,
            ex.run_tool_case,
            ex.run_research_case,
        )
        for run in runners:
            with self.subTest(run=run.__name__):
                row=run(self.C,self.B,0)
                self.assertTrue(row["pass"],row)
                self.assertIn("case_id",row)
                self.assertIn("seed",row)

    def test_delegation_exact_11_class_cycle(self):
        rows=[ex.run_delegation_case(self.C,self.B,i) for i in range(11)]
        self.assertTrue(all(x["pass"] for x in rows),rows)
        expected=[
            "BASE_PARALLEL",
            "RESOURCE_CONFLICT",
            "WORKER_UNAVAILABLE",
            "STEP_UNAVAILABLE",
            "WORKER_CAPABILITY_REMOVED",
            "RESOURCE_CAPACITY_CHANGED",
            "CHAIN",
            "FORK_JOIN",
            "FANOUT_JOIN",
            "DUAL_ROOT_FANIN",
            "ALTERNATIVE_PLAN",
        ]
        self.assertEqual([x["case_class"] for x in rows],expected)

    def test_browser_tool_research_cycles_are_complete(self):
        browser=[ex.run_browser_case(self.C,self.B,i)["case_class"] for i in range(5)]
        tool=[ex.run_tool_case(self.C,self.B,i)["case_class"] for i in range(6)]
        research=[ex.run_research_case(self.C,self.B,i)["case_class"] for i in range(6)]
        self.assertEqual(browser,["DIRECT","NAVIGATE","CONFIRM","STALE_REBIND","AMBIGUOUS"])
        self.assertEqual(tool,[
            "NO_CHANGE","SELECTED_TOOL_LOSES_CAPABILITY","CHEAPER_TOOL_GAINS_CAPABILITY",
            "CHEAPER_TOOL_UNAVAILABLE","CHEAPER_TOOL_UNAUTHORIZED","NO_SUFFICIENT_ROUTE",
        ])
        self.assertEqual(research,["biology","finance","systems","law","energy","materials"])

    def test_production_executor_has_no_reduced_count_argument(self):
        with self.assertRaises(TypeError):
            ex.execute_direct_route(
                ex.SA_CCR_ID,
                commitment=self.C,
                beacon=self.B,
                count=1,
            )


if __name__=="__main__":
    unittest.main(verbosity=2)
