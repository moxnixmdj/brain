import copy,json
from pathlib import Path
from canonical.runtime import global_retrieval_authority_guard_v1 as g
from canonical.runtime import global_retrieval_entrypoint_v1 as e

ROOT=Path(__file__).resolve().parents[2]

out=g.evaluate_repository(ROOT)
assert out["pass"] is True,out
assert out["candidate_memory_monotonic"] is True
assert out["open_world_unknown_preserved"] is True

def load(rel):
 return json.loads((ROOT/rel).read_text(encoding="utf-8"))
def blob(rel):
 return g.git_blob_sha((ROOT/rel).read_bytes())
actual={
 "activation_blob":blob(g.EXPECTED["activation_path"]),
 "activation_verification_blob":blob(g.EXPECTED["activation_verification_path"]),
 "core_verification_blob":blob(g.EXPECTED["core_verification_path"]),
 "controller_blob":blob(g.EXPECTED["controller_path"]),
 "torture_blob":blob(g.EXPECTED["torture_path"]),
}
p=load(g.EXPECTED["pointer_path"]);a=load(g.EXPECTED["activation_path"])
av=load(g.EXPECTED["activation_verification_path"]);cv=load(g.EXPECTED["core_verification_path"])

bad=copy.deepcopy(p);bad["policy"]["candidate_memory"]="DESTRUCTIVE"
assert g.validate(bad,a,av,cv,actual)["pass"] is False
bad=copy.deepcopy(p);bad["status"]="STALE"
assert g.validate(bad,a,av,cv,actual)["pass"] is False
bad_actual=dict(actual);bad_actual["controller_blob"]="0"*40
assert g.validate(p,a,av,cv,bad_actual)["pass"] is False

plan=e.compile_authorized_plan(
 root=ROOT,
 query_actions=[{"action_id":"q1","source_id":"web-a"}],
 sources=[
  {"source_id":"web-a","upstream_group":"web-index","bounded_scope":False},
  {"source_id":"registry","upstream_group":"registry","bounded_scope":True,
   "authoritative_enumeration":True,"scope_id":"snapshot-1",
   "enumeration_transport":"DIRECT_API"},
 ],
 source_stats={},
)
assert plan["status"]=="PASS__AUTHORIZED_GLOBAL_RETRIEVAL_PLAN_COMPILED",plan
assert plan["authority_gate"]["pass"] is True
assert plan["plan"]["queryless_enumeration_action_count"]==1
assert plan["plan"]["open_world_nonexistence_claim_authorized"] is False
assert plan["execution_authority"] is False
print("test_global_retrieval_authority_guard_v1: PASS")
