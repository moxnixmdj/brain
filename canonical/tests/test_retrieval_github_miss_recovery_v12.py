from canonical.runtime import retrieval_github_miss_recovery_v12 as a

a.validate()
assert len(a.CASES)==6
assert {x["episode_id"] for x in a.CASES}=={
 "GITHUB_ZH_SEGMENTATION","GITHUB_ZH_PINYIN","GITHUB_RU_NLP",
 "GITHUB_AR_TEXT","GITHUB_PY_LINTER","GITHUB_PY_CLI"
}

orig=a.base.github
try:
 def fake(query,*,limit=50,timeout=20.0):
  for row in a.CASES:
   if query in row["queries"]:
    return [row["target"]] if row["episode_id"] in {"GITHUB_ZH_SEGMENTATION","GITHUB_RU_NLP","GITHUB_PY_LINTER"} else ["wrong/example"]
  return []
 a.base.github=fake
 out=a.run()
finally:
 a.base.github=orig

assert out["baseline_case_count"]==6
assert out["usable_case_count"]==6
assert out["recovered_case_count"]==3
assert out["recovery_rate"]==0.5
assert out["open_world_completeness_claim"] is False
assert out["execution_authority"] is False
print("test_retrieval_github_miss_recovery_v12: PASS")
