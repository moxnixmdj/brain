from pathlib import Path
from canonical.runtime import retrieval_real_hidden_witness_arena_v1 as arena
from canonical.runtime import retrieval_empirical_calibration_v1 as cal

ROOT=Path(__file__).resolve().parents[2]

catalog=arena.load_catalog(ROOT)
trees=arena.load_tree_fingerprints(ROOT)
content=arena.load_content_fingerprints(ROOT)
assert len(catalog["targets"])==13
assert len(trees)==13
assert len(content)==1
assert "RW_CADRIP" in content
assert trees["RW_CADRIP"]["path_count"]<=8
assert all(len(x.get("commit") or "")==40 for x in catalog["targets"])
for target in catalog["targets"]:
    fp=trees[target["id"]]
    assert fp["repository"]==target["repository"]
    assert fp["commit"]==target["commit"]
    assert fp["truncated"] is False
    assert fp["path_count"]>=3

tess=next(x for x in catalog["targets"] if x["id"]=="RW_TESSERACT")
hidden=arena.surface_text(tess,profile="NO_IDENTITY",route="HYBRID",tree_tokens=trees["RW_TESSERACT"]["tree_tokens"]).casefold()
assert "tesseract" not in hidden

result=arena.evaluate(ROOT)
assert result["catalog_target_count"]==13
assert result["query_independent_tree_fingerprint_count"]==13
assert result["bounded_full_content_fingerprint_count"]==1
assert result["case_count"]==104
assert result["open_world_completeness_claim"] is False
assert result["external_provider_recall_measured"] is False
assert result["candidate_identity_leakage_allowed"] is False
assert set(result["routes"])=={"METADATA","STRUCTURE","HYBRID"}
# Generic morphology/compound features, not target-specific aliases.
assert set(arena.features("parsing")) & set(arena.features("parser"))
assert "~ocr" in arena.features("OCR")
assert "~ocr" in arena.features("ocrclass")

for route in result["routes"]:
    m=result["metrics"][route]
    assert 0.0 <= m["top1_recall"] <= 1.0
    assert 0.0 <= m["top3_recall"] <= 1.0
    assert m["top3_recall"] >= m["top1_recall"]
    assert len(result["route_top1_hit_case_ids"][route]) <= result["case_count"]

pool=result["monotonic_pooled_candidate_metrics"]
assert pool["1"]["recall"] <= pool["3"]["recall"] <= pool["5"]["recall"]
assert pool["1"]["mean_candidate_pool_size"] <= pool["3"]["mean_candidate_pool_size"] <= pool["5"]["mean_candidate_pool_size"]
assert pool["5"]["max_candidate_pool_size"] <= 13

calibrated=cal.calibrate_arena(ROOT)
assert calibrated["arena"]["target_count"]==13
assert calibrated["arena"]["case_count"]==104
c=calibrated["calibration"]
assert c["case_count"]==104
assert len(c["empirical_route_order"])==3
assert 0.0 <= c["coverage"] <= 1.0
assert c["prior"]=="JEFFREYS_BETA_0_5_0_5"
assert calibrated["live_provider_calibration_complete"] is False

# A deliberately correlated toy universe must report perfect success overlap.
toy=cal.calibrate_hit_sets(
    case_ids=["a","b","c"],
    route_hit_case_ids={"r1":["a","b"],"r2":["a","b"]},
    route_mean_latency_ms={"r1":1.0,"r2":2.0},
)
pair=toy["pairwise_success_overlap"][0]
assert pair["jaccard_success_overlap"]==1.0
assert pair["a_unique_successes"]==0 and pair["b_unique_successes"]==0
assert toy["empirical_route_order"][0]["route"]=="r1"

print("test_retrieval_real_hidden_witness_arena_v1: PASS")
