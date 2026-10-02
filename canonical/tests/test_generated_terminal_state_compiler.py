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
        (g/"GLOBAL_TERMINAL_REPLACEMENT_POPULATION_PROTOCOL_V2.json").write_text(json.dumps({"active_contracts":[bid],"execution_authority":admitted}))
        (g/"EXACT_FOUR_PORTFOLIO_PREQUALIFICATION_V1.json").write_text(json.dumps({"portfolio_status":{"T0":{"blockers":[] if admitted else ["X"]}}}))
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

    def test_contract_set_mismatch_fails_closed(self):
        td,root=self.make(True)
        try:
            g=root/"canonical/governance"
            (g/"GLOBAL_TERMINAL_REPLACEMENT_POPULATION_PROTOCOL_V2.json").write_text(json.dumps({"active_contracts":["OTHER"],"execution_authority":True}))
            out=compile_state(root); self.assertFalse(out["pass"]); self.assertIn("CONTRACT_SET_MISMATCH",out["errors"])
        finally: td.cleanup()

if __name__=="__main__":
    unittest.main()
