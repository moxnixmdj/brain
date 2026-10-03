from __future__ import annotations
import json
from pathlib import Path
import unittest

from canonical.runtime import tool_discovery_retrieval_authority_gate_v2 as gate

ROOT=Path(__file__).resolve().parents[2]

class T(unittest.TestCase):
 def test_repository_passes_exact_v6_gate(self):
  out=gate.evaluate_repository(ROOT)
  self.assertTrue(out["pass"],out)
  self.assertTrue(out["global_v6_authority_mandatory"])
  self.assertTrue(out["monotonic_candidate_retention_mandatory"])
  self.assertTrue(out["queryless_bounded_enumeration_mandatory"])
  self.assertTrue(out["conditional_novelty_scheduling_mandatory"])
  self.assertTrue(out["zero_yield_never_completeness"])
  self.assertTrue(out["open_world_unknown_preserved"])

 def test_current_authority_mismatch_fails_closed(self):
  def load(rel): return json.loads((ROOT/rel).read_text(encoding="utf-8"))
  base=__import__("canonical.runtime.tool_discovery_retrieval_authority_gate_v1",fromlist=["x"]).evaluate_repository(ROOT)
  current=load(gate.EXPECTED["current_authority_path"])
  activation=load(gate.EXPECTED["v6_activation_path"])
  verification=load(gate.EXPECTED["v6_verification_path"])
  actual={
   "current_authority_blob":gate.EXPECTED["current_authority_blob"],
   "v6_activation_blob":gate.EXPECTED["v6_activation_blob"],
   "v6_verification_blob":gate.EXPECTED["v6_verification_blob"],
   **{k:v for k,v in gate.EXPECTED.items() if k in gate.PATHS},
  }
  current["authority"]["git_blob_sha"]="0"*40
  out=gate.validate(base,current,activation,verification,actual)
  self.assertFalse(out["pass"])
  self.assertIn("CURRENT_AUTHORITY_V6_ACTIVATION_BINDING_MISMATCH",out["errors"])

 def test_zero_yield_completeness_invariant_is_load_bearing(self):
  def load(rel): return json.loads((ROOT/rel).read_text(encoding="utf-8"))
  base=__import__("canonical.runtime.tool_discovery_retrieval_authority_gate_v1",fromlist=["x"]).evaluate_repository(ROOT)
  current=load(gate.EXPECTED["current_authority_path"])
  activation=load(gate.EXPECTED["v6_activation_path"])
  verification=load(gate.EXPECTED["v6_verification_path"])
  actual={
   "current_authority_blob":gate.EXPECTED["current_authority_blob"],
   "v6_activation_blob":gate.EXPECTED["v6_activation_blob"],
   "v6_verification_blob":gate.EXPECTED["v6_verification_blob"],
   **{k:v for k,v in gate.EXPECTED.items() if k in gate.PATHS},
  }
  activation["mandatory_v6_invariants"].remove("ZERO_YIELD_ROUNDS_NEVER_PROVE_COMPLETENESS")
  out=gate.validate(base,current,activation,verification,actual)
  self.assertFalse(out["pass"])
  self.assertIn("V6_INVARIANT_MISSING:ZERO_YIELD_ROUNDS_NEVER_PROVE_COMPLETENESS",out["errors"])

if __name__=="__main__":unittest.main(verbosity=2)
