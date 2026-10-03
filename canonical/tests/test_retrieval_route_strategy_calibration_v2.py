from pathlib import Path
from canonical.runtime import retrieval_route_strategy_calibration_v2 as c

ROOT=Path(__file__).resolve().parents[2]
out=c.calibrate_repository(ROOT)

assert out["provider_only_calibration_forbidden"] is True
assert out["open_world_completeness_claim"] is False
assert out["case_count"]==13, out["case_count"]
union=out["best_known_strategy_union"]
assert union["hit_case_count"]==13, union
assert union["hit_rate"]==1.0, union
assert union["miss_case_ids"]==[], union

stats=out["route_strategy_stats"]
assert stats["GITHUB_REPOSITORY_SEARCH::RAW_BEHAVIOR_V1"]["target_hit_count"]==0
assert stats["GITHUB_REPOSITORY_SEARCH::ANCHOR_COMPRESSED_V2"]["target_hit_count"]==3
assert stats["HUGGINGFACE_MODEL_SEARCH::RAW_BEHAVIOR_V1"]["target_hit_count"]==0
assert stats["HUGGINGFACE_MODEL_PIPELINE_ENUM::PROVIDER_NATIVE_ENUM_V2"]["target_hit_count"]==2
assert stats["CROSSREF_TITLE_SEARCH::PROVIDER_NATIVE_TITLE_V2"]["target_hit_count"]==2
assert stats["NPM_REGISTRY_SEARCH::MULTI_QUERY_LATTICE_V3"]["target_hit_count"]==2
assert stats["CRATES_IO_SEARCH::MULTI_QUERY_LATTICE_V3"]["target_hit_count"]==1

# The optimized route must empirically recover raw GitHub misses.
rows=[
 x for x in out["directional_conditional_recovery"]
 if x["route_a"]=="GITHUB_REPOSITORY_SEARCH::RAW_BEHAVIOR_V1"
 and x["route_b"]=="GITHUB_REPOSITORY_SEARCH::ANCHOR_COMPRESSED_V2"
]
assert len(rows)==1
assert rows[0]["a_miss_count"]==3
assert rows[0]["b_recovery_after_a_miss_count"]==3
assert rows[0]["b_conditional_recovery_rate_after_a_miss"]==1.0

print("test_retrieval_route_strategy_calibration_v2: PASS",union)
