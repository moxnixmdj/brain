import json,tempfile
from pathlib import Path
from canonical.runtime import retrieval_live_instrumented_executor_v1 as x
from canonical.runtime import retrieval_live_event_ledger_v1 as ledger

ROOT=Path(__file__).resolve().parents[2]

with tempfile.TemporaryDirectory() as td:
 path=Path(td)/"events.jsonl"
 calls={"n":0}
 def provider(action):
  calls["n"]+=1
  return {"status":"SUCCESS","candidates":[{"url":"https://example.test/a"},{"repository":"org/repo"}],"request_count":2}
 out=x.execute_observed(
  root=ROOT,episode_id="EP1",sequence=1,
  action={"action_id":"A1","source_id":"S1","upstream_group":"G1"},
  provider=provider,event_path=path,
 )
 assert out["status"]=="PASS__LIVE_RETRIEVAL_EVENT_APPENDED",out
 assert out["event"]["latency_seconds"]>0
 assert out["event"]["request_count"]==2
 assert out["event"]["candidate_ids"]==["https://example.test/a","org/repo"]
 assert calls["n"]==1
 rows=ledger.load_jsonl(path)
 assert len(rows)==1
 agg=ledger.aggregate(rows)
 assert agg["event_count"]==1 and agg["source_stats"]["S1"]["attempts"]==1

 try:
  x.execute_observed(
   root=ROOT,episode_id="EP1",sequence=2,
   action={"action_id":"A1","source_id":"S1","upstream_group":"G1"},
   provider=provider,event_path=path,
  )
  raise AssertionError("duplicate execution accepted")
 except x.LiveRetrievalExecutionError as e:
  assert "DUPLICATE_EPISODE_ACTION_EVENT" in str(e)
 assert calls["n"]==1

 def failing(action):
  raise RuntimeError("transient boom")
 out=x.execute_observed(
  root=ROOT,episode_id="EP1",sequence=2,
  action={"action_id":"A2","source_id":"S2","upstream_group":"G2"},
  provider=failing,event_path=path,
 )
 assert out["status"]=="RECORDED__FAILED_RETRYABLE"
 assert out["event"]["status"]=="FAILED_RETRYABLE"
 assert out["event"]["latency_seconds"]>0

 def cheating(action):
  return {"status":"SUCCESS","verified_sufficient":True,"candidates":[{"url":"https://example.test/cheat","verified_sufficient":True}]}
 out=x.execute_observed(
  root=ROOT,episode_id="EP1",sequence=3,
  action={"action_id":"A3","source_id":"S3","upstream_group":"G3"},
  provider=cheating,event_path=path,
 )
 assert out["status"]=="RECORDED__FAILED_PERMANENT"
 assert out["event"]["status"]=="FAILED_PERMANENT"
 assert out["event"]["candidate_ids"]==[]
 assert "AUTHORITY_VIOLATION" in (out["provider_error"] or "")

 rows=ledger.load_jsonl(path)
 assert len(rows)==3
 assert ledger.aggregate(rows)["event_count"]==3

with tempfile.TemporaryDirectory() as td:
 path=Path(td)/"events.jsonl"
 def good(action):
  return {"status":"SUCCESS","candidates":[{"candidate_id":"w1"}]}
 try:
  x.execute_observed(
   root=ROOT,episode_id="EP2",sequence=1,
   action={"action_id":"A1","source_id":"S1"},
   provider=good,event_path=path,
   verified_sufficient_candidate_ids=["w1"],
  )
  raise AssertionError("sufficiency without receipt accepted")
 except x.LiveRetrievalExecutionError as e:
  assert "SUFFICIENT_EVENT_REQUIRES_INDEPENDENT_RECEIPT" in str(e)

 out=x.execute_observed(
  root=ROOT,episode_id="EP2",sequence=1,
  action={"action_id":"A1","source_id":"S1"},
  provider=good,event_path=path,
  verified_sufficient_candidate_ids=["w1"],
  independent_receipt="receipt:independent:test",
 )
 assert out["event"]["verified_sufficient_candidate_ids"]==["w1"]
 assert out["event"]["independent_receipt"]=="receipt:independent:test"

print("test_retrieval_live_instrumented_executor_v1: PASS")
