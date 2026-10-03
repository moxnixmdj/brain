from __future__ import annotations
import unittest
from canonical.runtime.evidence_omniretrieval_planner_v2 import ProofObligation,compile_channels,novelty_signal
from canonical.runtime.retrieval_monotonic_candidate_ledger_v1 import empty_ledger,ingest,mark_disposition
from canonical.runtime.retrieval_bounded_enumerator_v1 import start,consume_page,status
from canonical.runtime.retrieval_conditional_novelty_scheduler_v1 import rank_actions
from canonical.runtime.retrieval_adversarial_universe_v2 import run as run_torture
from canonical.runtime.retrieval_open_world_controller_v6 import compile_plan,ingest_candidates

class T(unittest.TestCase):
 def o(self):
  return ProofObligation(obligation_id="TOOL-X",concepts=("binary serializer",),aliases=("binary marshaler","二进制序列化器"),language_variants=("مسلسل ثنائي","двоичный сериализатор"),identifiers=("ubjson-codec",),code_symbols=("dumpb","loadb"),io_signatures=("object->bytes","bytes->object"),protocols=("UBJSON",),seed_repositories=("org/repo",),enumerable_scopes=("pypi:snapshot-20261003",),archive_seeds=("org/repo",))
 def test_channels(self):
  x=compile_channels(self.o());self.assertEqual(x["status"],"COMPILED")
  for c in ("MULTILINGUAL","STRUCTURAL_CODE","BEHAVIORAL","HISTORY","GRAPH","ECOSYSTEM","QUERYLESS_ENUMERATION","ARCHIVE"):self.assertTrue(x["channels"][c],c)
 def test_zero_yield_is_not_completeness(self):
  p=compile_channels(self.o());rounds=[]
  for c in p["active_channels"]:rounds += [{"channel":c,"new_unique_candidates":0},{"channel":c,"new_unique_candidates":0}]
  v=novelty_signal(p,rounds);self.assertEqual(v["status"],"LOW_NOVELTY_SIGNAL");self.assertFalse(v["completeness_proof"]);self.assertFalse(v["nonexistence_claim_authorized"])
 def test_monotonic_ledger(self):
  l=ingest(empty_ledger(),[{"url":"https://example.org/x","source":"web"}],epoch_id="E1");cid=next(iter(l["records"]));l2=mark_disposition(l,candidate_id_value=cid,disposition="DEPRIORITIZED",reason="rank");self.assertEqual(set(l["records"]),set(l2["records"]));l3=ingest(l2,[{"url":"https://example.org/y","source":"web"}],epoch_id="E2");self.assertTrue(set(l2["records"]).issubset(set(l3["records"])))
 def test_verified_requires_receipt(self):
  l=ingest(empty_ledger(),[{"url":"https://example.org/x","source":"web"}],epoch_id="E");cid=next(iter(l["records"]))
  with self.assertRaises(ValueError):mark_disposition(l,candidate_id_value=cid,disposition="VERIFIED_SUFFICIENT",reason="looks good")
 def test_bounded_enumeration(self):
  s=start({"source_id":"registry","scope_id":"snapshot","declared_finite":True,"independently_verified_finite":True,"start_cursor":"0"});s=consume_page(s,{"cursor":"0","success":True,"items":[{"item_id":"a"}],"next_cursor":"1","final":False});s=consume_page(s,{"cursor":"1","success":True,"items":[{"item_id":"b"}],"next_cursor":None,"final":True});v=status(s);self.assertTrue(v["complete"]);self.assertTrue(v["nonexistence_claim_authorized"]);self.assertFalse(v["open_world_completeness_claim_authorized"])
 def test_unproved_scope_does_not_close(self):
  s=start({"source_id":"registry","scope_id":"unknown","declared_finite":False,"independently_verified_finite":False});s=consume_page(s,{"cursor":None,"success":True,"items":[],"next_cursor":None,"final":True});self.assertFalse(status(s)["complete"])
 def test_novelty(self):
  a=[{"action_id":"popular-repeat","source_group":"web","latency_cost":1,"request_cost":1,"orthogonal_channel":False},{"action_id":"direct-registry","source_group":"registry","latency_cost":1,"request_cost":1,"orthogonal_channel":True}];o={"popular-repeat":{"attempts":10,"candidate_ids":["A","B"],"marginal_successes":0}};x=rank_actions(a,o);self.assertEqual(x["selected_action_id"],"direct-registry");self.assertFalse(x["actions"][0]["score_is_calibrated_probability"])
 def test_torture(self):
  x=run_torture();self.assertEqual(x["status"],"PASS",x);self.assertGreater(x["generated_case_count"],100);self.assertTrue(x["pairwise_complete"]);self.assertEqual(x["v6_finite_fixture_recall"],1.0);self.assertLess(x["lexical_only_recall"],1.0);self.assertEqual(x["outside_scope_correct_state"],"UNKNOWN")
 def test_controller(self):
  p=compile_plan(self.o(),[{"action_id":"A","source_group":"web","latency_cost":1,"request_cost":1,"orthogonal_channel":False}]);p2=ingest_candidates(p,[{"url":"https://example.org/repo","source":"web"}],epoch_id="E1");self.assertEqual(p2["candidate_ledger"]["candidate_count"],1);self.assertFalse(p2["nonexistence_claim_authorized"]);self.assertEqual(p2["acceptance_credit_delta"],0)
if __name__=="__main__":unittest.main(verbosity=2)
