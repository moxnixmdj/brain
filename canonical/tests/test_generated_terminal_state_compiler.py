from __future__ import annotations
import json,tempfile,unittest
from pathlib import Path
from canonical.runtime.generated_terminal_state_compiler import compile_state

class Tests(unittest.TestCase):
    def make(self,admitted=True):
        td=tempfile.TemporaryDirectory(); root=Path(td.name); g=root/"canonical/governance"; g.mkdir(parents=True)
        bid="B1"
        (g/"BEHAVIORAL_CONTRACT_REGISTRY_V1.json").write_text(json.dumps({"active_contracted_residuals":[{"behavior_id":bid}]}))
        (g/"ACTIVE_TERMINAL_PROOF_BASIS_V1.json").write_text(json.dumps({
            "contracts":[{"behavior_id":bid,"proof_state":"TERMINAL_ROUTE_FROZEN_ADMISSIBLE" if admitted else "OPEN","blockers":[] if admitted else ["X"]}],
            "admissible_frozen_terminal_route_count":1 if admitted else 0,"execution_authority":admitted}))
        (g/"GLOBAL_TERMINAL_REPLACEMENT_POPULATION_PROTOCOL_V2.json").write_text(json.dumps({
            "active_contracts":[bid],
            "admissible_frozen_routes":[bid] if admitted else [],
            "admissible_frozen_route_count":1 if admitted else 0,
            "execution_authority":admitted
        }))
        basis_status="READY" if admitted else "BLOCKED"
        basis_obj=json.loads((g/"ACTIVE_TERMINAL_PROOF_BASIS_V1.json").read_text())
        basis_obj["status"]=basis_status
        (g/"ACTIVE_TERMINAL_PROOF_BASIS_V1.json").write_text(json.dumps(basis_obj))
        (g/"EXACT_FOUR_PORTFOLIO_PREQUALIFICATION_V1.json").write_text(json.dumps({
            "admissible_frozen_terminal_route_count":1 if admitted else 0,
            "active_terminal_proof_basis_status":basis_status,
            "prequalification_progress":{
                "admissible_frozen_terminal_route_count":1 if admitted else 0,
                "admissible_frozen_terminal_routes":[bid] if admitted else []
            },
            "portfolio_status":{"T0":{"blockers":[] if admitted else ["X"]}}
        }))
        (g/"TERMINAL_ROUTE_CLOSURE_QUEUE_RECEIPT_V1.json").write_text(json.dumps({
            "source_basis_status":basis_status,
            "closed_route_count":1 if admitted else 0,
            "open_route_count":0 if admitted else 1,
            "closed_behavior_ids":[bid] if admitted else [],
            "queue":[] if admitted else [{"behavior_id":bid}]
        }))
        (g/"progress.json").write_text(json.dumps({"status":"INDEPENDENT_PASS"}))
        (g/"TERMINAL_PROGRESS_EVIDENCE_INDEX_V1.json").write_text(json.dumps({"entries":[{"behavior_id":bid,"path":"canonical/governance/progress.json"}]}))
        return td,root

    def test_ready_state(self):
        td,root=self.make(True)
        try:
            out=compile_state(root); self.assertTrue(out["pass"]); self.assertTrue(out["execution_authority"])
            self.assertEqual(out["reconciliation_candidate_count"],0)
        finally: td.cleanup()

    def test_progress_does_not_self_promote(self):
        td,root=self.make(False)
        try:
            out=compile_state(root); self.assertFalse(out["execution_authority"])
            self.assertEqual(out["authoritative_admissible_route_count"],0)
            self.assertEqual(out["reconciliation_candidate_count"],1)
        finally: td.cleanup()

    def test_derived_admission_lag_fails_closed(self):
        td,root=self.make(True)
        try:
            g=root/"canonical/governance"
            protocol=json.loads((g/"GLOBAL_TERMINAL_REPLACEMENT_POPULATION_PROTOCOL_V2.json").read_text())
            protocol["admissible_frozen_routes"]=[]
            protocol["admissible_frozen_route_count"]=0
            (g/"GLOBAL_TERMINAL_REPLACEMENT_POPULATION_PROTOCOL_V2.json").write_text(json.dumps(protocol))
            preq=json.loads((g/"EXACT_FOUR_PORTFOLIO_PREQUALIFICATION_V1.json").read_text())
            preq["admissible_frozen_terminal_route_count"]=0
            (g/"EXACT_FOUR_PORTFOLIO_PREQUALIFICATION_V1.json").write_text(json.dumps(preq))
            out=compile_state(root)
            self.assertFalse(out["pass"])
            self.assertTrue(out["derived_state_reconciliation_required"])
            self.assertTrue(any(x.startswith("PROTOCOL_ADMISSION_MISMATCH:") for x in out["errors"]))
            self.assertIn("PREQUAL_ADMISSIBLE_COUNT_MISMATCH:0!=1",out["errors"])
        finally: td.cleanup()

    def test_closure_queue_drift_fails_closed(self):
        td,root=self.make(True)
        try:
            g=root/"canonical/governance"
            q=json.loads((g/"TERMINAL_ROUTE_CLOSURE_QUEUE_RECEIPT_V1.json").read_text())
            q["closed_behavior_ids"]=[]
            q["closed_route_count"]=0
            q["open_route_count"]=1
            q["queue"]=[{"behavior_id":"B1"}]
            (g/"TERMINAL_ROUTE_CLOSURE_QUEUE_RECEIPT_V1.json").write_text(json.dumps(q))
            out=compile_state(root)
            self.assertFalse(out["pass"])
            self.assertTrue(out["derived_state_reconciliation_required"])
            self.assertTrue(any(x.startswith("QUEUE_CLOSED_ADMISSION_MISMATCH:") for x in out["errors"]))
            self.assertIn("QUEUE_CLOSED_COUNT_MISMATCH",out["errors"])
        finally: td.cleanup()

    def test_nested_prequalification_drift_fails_closed(self):
        td,root=self.make(True)
        try:
            g=root/"canonical/governance"
            p=json.loads((g/"EXACT_FOUR_PORTFOLIO_PREQUALIFICATION_V1.json").read_text())
            p["prequalification_progress"]["admissible_frozen_terminal_route_count"]=0
            p["prequalification_progress"]["admissible_frozen_terminal_routes"]=[]
            (g/"EXACT_FOUR_PORTFOLIO_PREQUALIFICATION_V1.json").write_text(json.dumps(p))
            out=compile_state(root)
            self.assertFalse(out["pass"])
            self.assertTrue(out["derived_state_reconciliation_required"])
            self.assertIn("PREQUAL_NESTED_ADMISSIBLE_COUNT_MISMATCH:0!=1",out["errors"])
            self.assertTrue(any(x.startswith("PREQUAL_NESTED_ADMISSION_MISMATCH:") for x in out["errors"]))
        finally: td.cleanup()

    def test_contract_set_mismatch_fails_closed(self):
        td,root=self.make(True)
        try:
            g=root/"canonical/governance"
            (g/"GLOBAL_TERMINAL_REPLACEMENT_POPULATION_PROTOCOL_V2.json").write_text(json.dumps({
                "active_contracts":["OTHER"],"admissible_frozen_routes":["OTHER"],
                "admissible_frozen_route_count":1,"execution_authority":True
            }))
            out=compile_state(root); self.assertFalse(out["pass"]); self.assertIn("CONTRACT_SET_MISMATCH",out["errors"])
        finally: td.cleanup()

if __name__=="__main__":
    unittest.main()
