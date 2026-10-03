from canonical.runtime import global_retrieval_controller_v1 as g

s=g.new_state()
s=g.add_candidates(s,[{"url":"https://example.test/a","name":"A"}],source_id="engine-a",upstream_group="web-index-1",action_id="q1")
s=g.add_candidates(s,[{"url":"https://example.test/a","description":"extra"},{"url":"https://example.test/b"}],source_id="engine-b",upstream_group="web-index-2",action_id="q2")
assert len(s["candidates"])==2
ids=[x["candidate_id"] for x in s["candidates"]]
s2=g.apply_rerank(s,{ids[0]:0.01,ids[1]:100.0},reason="test")
assert {x["candidate_id"] for x in s2["candidates"]}==set(ids)
assert all(x["active"] is True for x in s2["candidates"])

sources=[
 {"source_id":"search-a","upstream_group":"shared-index","bounded_scope":False},
 {"source_id":"registry","upstream_group":"registry-direct","bounded_scope":True,"authoritative_enumeration":True,"scope_id":"registry-snapshot-1","enumeration_transport":"DIRECT_API"},
]
enums=g.compile_queryless_enumeration(sources)
assert len(enums)==1 and enums[0]["source_id"]=="registry"

cand={"url":"x","dependencies":["dep-a"],"forks":["fork-a"],"mirrors":["mirror-a"]}
edges=g.graph_snowball_actions(cand)
assert {x["edge_type"] for x in edges}=={"dependencies","forks","mirrors"}

fresh=g.marginal_novelty({"attempts":10,"novel_candidate_actions":5,"sufficient_witness_actions":1,"failures":0,"mean_latency_seconds":1},already_consumed_upstream_group=False)
corr=g.marginal_novelty({"attempts":10,"novel_candidate_actions":5,"sufficient_witness_actions":1,"failures":0,"mean_latency_seconds":1},already_consumed_upstream_group=True)
assert fresh["utility"]>corr["utility"]

plan=g.compile_global_plan(query_actions=[{"action_id":"q","source_id":"search-a"}],sources=sources,source_stats={})
assert plan["queryless_enumeration_action_count"]==1
assert plan["candidate_memory_monotonic"] is True
assert plan["open_world_nonexistence_claim_authorized"] is False
assert g.terminal_state(g.new_state(),open_world=True)["status"].startswith("UNKNOWN")

try:
 g.add_candidates(g.new_state(),[{"url":"x","verified_sufficient":True}],source_id="x",upstream_group="x",action_id="x")
 raise AssertionError("authority smuggling accepted")
except ValueError as e:
 assert "AUTHORITY_SMUGGLING" in str(e)

print("test_global_retrieval_controller_v1: PASS")
