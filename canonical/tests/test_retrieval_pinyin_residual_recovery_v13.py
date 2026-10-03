from canonical.runtime import retrieval_pinyin_residual_recovery_v13 as a
assert len(a.QUERIES)==3
assert a.TARGET.casefold() not in " ".join(a.QUERIES).casefold()
orig=a.base.github
try:
 def fake(q,*,limit=100,timeout=20.0):
  return [a.TARGET] if q==a.QUERIES[1] else ["wrong/example"]
 a.base.github=fake
 out=a.run()
finally:
 a.base.github=orig
assert out["target_hit"] is True
assert out["target_rank"]==2
assert out["open_world_completeness_claim"] is False
assert out["execution_authority"] is False
print("test_retrieval_pinyin_residual_recovery_v13: PASS")
