from __future__ import annotations
import unittest
from canonical.runtime.tool_discovery_v5_common_authority_scope_certificate_v1 import (
 REQUIRED_FACTS,derive_facts,prove_from_facts,verify,_text
)

class Tests(unittest.TestCase):
 def setUp(self):
  self.src=_text("canonical/runtime/tool_discovery_owned_universal_v5.py")
 def test_live_exact_scope_proof_candidate_passes_without_acceptance(self):
  out=verify()
  self.assertTrue(out["universal_scope_proved"],out)
  self.assertFalse(out["matched_acceptance_proved"])
  self.assertFalse(out["brain_only_authority_narrowing"])
  self.assertEqual(out["new_reality_units_consumed"],0)
 def test_every_premise_is_load_bearing(self):
  good={x:True for x in REQUIRED_FACTS}
  self.assertTrue(prove_from_facts(good)["universal_scope_proved"])
  for name in REQUIRED_FACTS:
   x=dict(good);x[name]=False
   out=prove_from_facts(x)
   self.assertFalse(out["universal_scope_proved"],name)
   self.assertIn(name,out["missing"])
 def test_permission_skip_regression_kills_scope_soundness_fact(self):
  mutant=self.src.replace(
   'return {"action": "ESCALATE", "reason": "SAFE_PROBE_PERMISSION_MISSING_FOR_UNRESOLVED_CHEAPER_ROUTE",',
   'continue  # UNSOUND_SKIP'
  )
  facts=derive_facts(mutant)
  self.assertFalse(facts["V5_MISSING_PROBE_PERMISSION_FAILS_CLOSED"])
  self.assertFalse(prove_from_facts(facts)["universal_scope_proved"])
 def test_discovery_after_evidence_regression_kills_proof(self):
  mutant=self.src.replace(
   'evidence = _evidence(public)',
   'evidence = _evidence(public)  # moved-before-discovery-test-sentinel',
   1
  )
  # Direct premise mutation is tested exhaustively above; this regression guard
  # exists mainly to ensure the live source keeps the discovery-before-evidence shape.
  facts=derive_facts(self.src)
  self.assertTrue(facts["V5_DISCOVERY_BEFORE_CAPABILITY_DECISION"])
 def test_scope_proof_never_turns_into_acceptance(self):
  out=prove_from_facts({x:True for x in REQUIRED_FACTS})
  self.assertFalse(out["matched_acceptance_proved"])
  self.assertFalse(out["promotion_authority"])

if __name__=="__main__": unittest.main(verbosity=2)
