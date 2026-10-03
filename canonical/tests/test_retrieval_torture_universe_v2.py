from canonical.runtime import global_retrieval_controller_v1 as g
from canonical.runtime import retrieval_torture_universe_v2 as t

rows=t.generate_pairwise_universe()
assert len(rows) > 1000, len(rows)
assert any(x["dimensions"]["vocabulary"]=="NO_SHARED_TEXT" and x["observable"] for x in rows)
assert any(x["dimensions"]["script"]=="CJK" and x["dimensions"]["metadata"]=="EMPTY" and x["dimensions"]["revision"]=="NONDEFAULT_BRANCH" for x in rows)

out=t.evaluate(set(g.MECHANISMS))
assert out["status"]=="PASS", out
assert out["architectural_failure_class_coverage"]==1.0
assert out["inaccessible_case_count"]>0
assert out["inaccessible_correct_state"]=="UNKNOWN"
assert out["open_world_completeness_claim"] is False

# Remove the queryless escape hatch: zero-lexical-bridge/index-lag cases must fail.
weakened=set(g.MECHANISMS)-{"QUERYLESS_BOUNDED_ENUMERATION"}
bad=t.evaluate(weakened)
assert bad["status"]=="FAIL"
assert any("QUERYLESS_BOUNDED_ENUMERATION" in x["missing"] for x in bad["misses"])

# Remove multilingual handling: native-script cases must fail.
weakened=set(g.MECHANISMS)-{"UNICODE_MULTILINGUAL_QUERYING"}
bad=t.evaluate(weakened)
assert bad["status"]=="FAIL"
assert any("UNICODE_MULTILINGUAL_QUERYING" in x["missing"] for x in bad["misses"])

print("test_retrieval_torture_universe_v2: PASS", len(rows))
