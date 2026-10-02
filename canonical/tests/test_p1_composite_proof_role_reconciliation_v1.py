from __future__ import annotations
import copy, json, unittest
from pathlib import Path
from canonical.runtime.p1_composite_proof_role_reconciliation_v1 import evaluate
from canonical.runtime.p1_terminal_execution_scope_audit_v1 import evaluate as audit

ROOT=Path(__file__).resolve().parents[2]
def load(rel): return json.loads((ROOT/rel).read_text())
def docs():
 return [
  load("canonical/governance/P1_TRAJECTORY_T0_T2_MULTIPLEX_TERMINAL_BINDING_V1.json"),
  load("canonical/verification/TRAJECTORY_TYPED_IR_V4_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"),
  load("canonical/verification/TERMINAL_V3_ONE_SHOT_WAVE_RESULT_20261002_V1.json"),
  audit(),
  load("canonical/governance/P1_COMPOSITE_PROOF_ROLE_RECONCILIATION_V1.json")]

class T(unittest.TestCase):
 def test_live_composite_partition_passes_without_credit(self):
  out=evaluate(*docs())
  self.assertTrue(out["pass"],out)
  self.assertEqual((out["required_check_count"],out["v4_check_count"],out["terminal_check_count"]),(8,4,4))
  self.assertEqual(out["required_mutation_count"],9)
  self.assertEqual(out["terminal_case_count"],60)
  self.assertTrue(out["narrow_terminal_scope_audit_preserved"])
  self.assertFalse(out["quarantine_resolved"])
  self.assertFalse(out["recovery_acceptance_transport_authorized"])
 def test_missing_v4_check_fails_closed(self):
  d=docs(); c=copy.deepcopy(d[4]); c["proof_roles"]["V4_TYPED_CROSS_DOMAIN_PREFLIGHT"].pop(); d[4]=c
  out=evaluate(*d); self.assertFalse(out["pass"]); self.assertIn("CHECK_PARTITION_INVALID",out["errors"])
 def test_predeclared_composite_role_is_load_bearing(self):
  d=docs(); b=copy.deepcopy(d[0]); b["evaluator"]["typed_cross_domain_scope_role"]="REMOVED"; d[0]=b
  out=evaluate(*d); self.assertFalse(out["pass"]); self.assertIn("COMPOSITE_ROLE_NOT_PREDECLARED",out["errors"])

if __name__=="__main__": unittest.main(verbosity=2)
