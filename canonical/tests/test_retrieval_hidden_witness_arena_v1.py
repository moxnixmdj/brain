from canonical.runtime import global_retrieval_controller_v1 as g
from canonical.runtime import retrieval_hidden_witness_arena_v1 as a

full=a.run_arena(set(g.MECHANISMS),limit=768)
assert full["status"]=="PASS", full["failures"][:3]
assert full["case_count"]>=700
assert full["hidden_witness_recall"]==1.0
assert full["verified_witness_count"]==full["case_count"]
assert full["open_world_completeness_claim"] is False

no_queryless=set(g.MECHANISMS)-{"QUERYLESS_BOUNDED_ENUMERATION"}
bad=a.run_arena(no_queryless,limit=768)
assert bad["status"]=="FAIL"
assert bad["hidden_witness_recall"]<1.0
assert any(
 x["case"]["vocabulary"]=="NO_SHARED_TEXT" or x["case"]["indexing"]=="WEB_UNINDEXED_ENUMERABLE"
 for x in bad["failures"]
)

no_multilingual=set(g.MECHANISMS)-{"UNICODE_MULTILINGUAL_QUERYING"}
bad=a.run_arena(no_multilingual,limit=768)
assert bad["status"]=="FAIL"
assert bad["hidden_witness_recall"]<1.0
assert any(x["case"]["script"] in {"CJK","ARABIC","CYRILLIC"} for x in bad["failures"])

no_history=set(g.MECHANISMS)-{"REVISION_AND_HISTORY_ENUMERATION"}
bad=a.run_arena(no_history,limit=768)
assert bad["status"]=="FAIL"
assert any(x["case"]["revision"] in {"NONDEFAULT_BRANCH","TAG_ONLY","OLD_COMMIT"} for x in bad["failures"])

print("test_retrieval_hidden_witness_arena_v1: PASS",full["case_count"])
