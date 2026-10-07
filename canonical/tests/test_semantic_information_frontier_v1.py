import unittest
from canonical.runtime.semantic_information_frontier_v1 import solve

def problem():
 return {
  "hypothesis_set_complete":True,
  "worlds":[
   {"world_id":"w1","terminal_signature_complete":True,"terminal_signature":{"decision":"ALLOW"}},
   {"world_id":"w2","terminal_signature_complete":True,"terminal_signature":{"decision":"ALLOW"}},
   {"world_id":"w3","terminal_signature_complete":True,"terminal_signature":{"decision":"DENY"}},
  ],
  "observations":[
   {"observation_id":"cheap_terminal_split","cost_units":1,"outcome_map_complete":True,
    "outcomes":{"w1":"same","w2":"same","w3":"different"}},
   {"observation_id":"expensive_full_identity","cost_units":10,"outcome_map_complete":True,
    "outcomes":{"w1":"one","w2":"two","w3":"three"}},
  ]
 }

class Tests(unittest.TestCase):
 def test_chooses_cheapest_terminally_sufficient_observation(self):
  out=solve(problem())
  self.assertTrue(out["pass"])
  self.assertEqual(out["first_observation_id"],"cheap_terminal_split")
  self.assertEqual(out["minimum_worst_case_cost_units"],1.0)

 def test_does_not_distinguish_terminally_equivalent_worlds(self):
  p=problem()
  p["worlds"]=p["worlds"][:2]
  for o in p["observations"]:
   o["outcomes"]={k:v for k,v in o["outcomes"].items() if k in {"w1","w2"}}
  out=solve(p)
  self.assertTrue(out["pass"])
  self.assertIsNone(out["first_observation_id"])
  self.assertEqual(out["minimum_worst_case_cost_units"],0.0)

 def test_incomplete_hypothesis_set_fails_closed(self):
  p=problem(); p["hypothesis_set_complete"]=False
  out=solve(p)
  self.assertFalse(out["pass"])
  self.assertIn("COMPLETENESS_UNPROVED",out["reason"])

 def test_incomplete_observation_map_fails_closed(self):
  p=problem(); del p["observations"][0]["outcomes"]["w3"]
  out=solve(p)
  self.assertFalse(out["pass"])
  self.assertIn("OUTCOME_MAP_INCOMPLETE",out["reason"])

 def test_unseparable_terminal_worlds_fail_closed(self):
  p=problem()
  for o in p["observations"]:
   o["outcomes"]={"w1":"x","w2":"x","w3":"x"}
  out=solve(p)
  self.assertFalse(out["pass"])
  self.assertIn("NOT_SEPARABLE",out["status"])

 def test_two_step_policy_is_exact_minimax(self):
  p={
   "hypothesis_set_complete":True,
   "worlds":[
    {"world_id":"a","terminal_signature_complete":True,"terminal_signature":{"d":"A"}},
    {"world_id":"b","terminal_signature_complete":True,"terminal_signature":{"d":"B"}},
    {"world_id":"c","terminal_signature_complete":True,"terminal_signature":{"d":"C"}},
    {"world_id":"d","terminal_signature_complete":True,"terminal_signature":{"d":"D"}},
   ],
   "observations":[
    {"observation_id":"split_ab_cd","cost_units":1,"outcome_map_complete":True,
     "outcomes":{"a":0,"b":0,"c":1,"d":1}},
    {"observation_id":"split_a_b","cost_units":1,"outcome_map_complete":True,
     "outcomes":{"a":0,"b":1,"c":0,"d":0}},
    {"observation_id":"split_c_d","cost_units":1,"outcome_map_complete":True,
     "outcomes":{"a":0,"b":0,"c":0,"d":1}},
    {"observation_id":"full","cost_units":4,"outcome_map_complete":True,
     "outcomes":{"a":"a","b":"b","c":"c","d":"d"}},
   ]
  }
  out=solve(p)
  self.assertTrue(out["pass"])
  self.assertEqual(out["first_observation_id"],"split_ab_cd")
  self.assertEqual(out["minimum_worst_case_cost_units"],2.0)

if __name__=="__main__":
 unittest.main(verbosity=2)
