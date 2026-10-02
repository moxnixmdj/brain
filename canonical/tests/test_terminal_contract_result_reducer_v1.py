import copy
import unittest

from canonical.runtime import portfolio_multiplex_terminal_instrumentation_v1 as multiplex
from canonical.runtime import terminal_contract_result_reducer_v1 as reducer
from canonical.runtime import terminal_parent_portfolio_launcher_v1 as launcher

COMMITMENT="terminal-candidate-commitment"
BEACON="post-freeze-beacon"

def good_parent_rows(portfolio):
    rows=[]
    for behavior_id,binding in multiplex.BINDINGS.items():
        if portfolio not in binding["portfolios"]:
            continue
        rows.append({
            "behavior_id":behavior_id,
            "portfolio":portfolio,
            "case_id":f"{portfolio}::{behavior_id}::0",
            "candidate_package_commitment":COMMITMENT,
            "post_freeze_beacon":BEACON,
            "binding_blob":binding["binding_blob"],
            "load_bearing":True,
            "direct_instrumentation_pass":True,
            "parent_terminal_acceptance_pass":True,
            "case_replaced":False,
            "tuning_replay":False,
            "result_to_runtime_feedback":False,
            "candidate_visible_keys":["task_visible_input"],
            "claims_behavior_credit":False,
        })
    return rows

def wave():
    parent={p:good_parent_rows(p) for p in launcher.PORTFOLIOS}
    pre=launcher.validate_parent_receipts(parent,commitment=COMMITMENT,beacon=BEACON)
    direct={
        bid:{"behavior_id":bid,"pass":True,"terminal_result":True}
        for bid in sorted(reducer.DIRECT_IDS)
    }
    return {
        "status":"PASS",
        "pass":True,
        "parent_portfolio_receipts":parent,
        "parent_reduction":pre,
        "direct_results":direct,
        "direct_failures":[],
        "direct_routes_executed_once":sorted(direct),
        "shared_direct_route_duplicate_execution_count":0,
        "no_case_replacement":True,
        "no_tuning_replay":True,
        "result_to_runtime_feedback_during_wave":False,
        "terminal_result":True,
    }

class TerminalContractResultReducerTests(unittest.TestCase):
    def test_exact_twelve_pass(self):
        out=reducer.reduce_wave(wave(),commitment=COMMITMENT,beacon=BEACON)
        self.assertTrue(out["valid"],out)
        self.assertTrue(out["all_contracts_pass"],out)
        self.assertEqual(out["contract_count"],12)
        self.assertEqual(set(out["contract_verdicts"]),set(reducer.ACTIVE_IDS))
        cad=out["contract_verdicts"][launcher.CAD_ID]
        self.assertEqual(cad["evidence_sources"],["DIRECT","PARENT_MULTIPLEX"])

    def test_direct_failure_is_valid_negative_evidence(self):
        w=wave()
        target=next(x for x in sorted(reducer.DIRECT_IDS) if x != launcher.CAD_ID)
        w["direct_results"][target]["pass"]=False
        w["direct_failures"]=[target]
        w["pass"]=False
        w["status"]="FAIL_CLOSED"
        out=reducer.reduce_wave(w,commitment=COMMITMENT,beacon=BEACON)
        self.assertTrue(out["valid"],out)
        self.assertFalse(out["all_contracts_pass"])
        self.assertEqual(out["contract_verdicts"][target]["status"],"FAIL")

    def test_multiplex_failure_is_valid_negative_evidence(self):
        w=wave()
        target=next(x for x in sorted(reducer.MULTIPLEX_IDS) if x != launcher.CAD_ID)
        for rows in w["parent_portfolio_receipts"].values():
            for row in rows:
                if row["behavior_id"]==target:
                    row["direct_instrumentation_pass"]=False
                    break
            else:
                continue
            break
        w["pass"]=False
        w["status"]="FAIL_CLOSED"
        out=reducer.reduce_wave(w,commitment=COMMITMENT,beacon=BEACON)
        self.assertTrue(out["valid"],out)
        self.assertFalse(out["all_contracts_pass"])
        self.assertEqual(out["contract_verdicts"][target]["status"],"FAIL")

    def test_missing_direct_result_fails_closed(self):
        w=wave()
        target=next(iter(reducer.DIRECT_IDS))
        del w["direct_results"][target]
        out=reducer.reduce_wave(w,commitment=COMMITMENT,beacon=BEACON)
        self.assertFalse(out["valid"])
        self.assertTrue(any("DIRECT_RESULT_SET_MISMATCH" in e for e in out["errors"]))

    def test_beacon_mismatch_fails_closed(self):
        w=wave()
        first=next(iter(w["parent_portfolio_receipts"].values()))
        first[0]["post_freeze_beacon"]="wrong"
        out=reducer.reduce_wave(w,commitment=COMMITMENT,beacon=BEACON)
        self.assertFalse(out["valid"])
        self.assertTrue(any("PARENT_REVALIDATION" in e for e in out["errors"]))

    def test_duplicate_execution_guard_fails_closed(self):
        w=wave()
        w["shared_direct_route_duplicate_execution_count"]=1
        out=reducer.reduce_wave(w,commitment=COMMITMENT,beacon=BEACON)
        self.assertFalse(out["valid"])
        self.assertIn("DUPLICATE_DIRECT_ROUTE_EXECUTION",out["errors"])

if __name__=="__main__":
    unittest.main(verbosity=2)
