from pathlib import Path
from canonical.runtime import retrieval_real_hidden_witness_arena_v1 as arena
from canonical.runtime import retrieval_empirical_calibration_v1 as cal

ROOT=Path(__file__).resolve().parents[2]

catalog=arena.load_catalog(ROOT)
assert len(catalog["targets"])==13
assert all(len(x.get("commit") or "")==40 for x in catalog["targets"])

tess=next(x for x in catalog["targets"] if x["id"]=="RW_TESSERACT")
hidden=arena.surface_text(tess,profile="NO_IDENTITY",route="HYBRID").casefold()
assert "tesseract" not in hidden

result=arena.evaluate(ROOT)
assert result["catalog_target_count"]==13
assert result["case_count"]==104
assert result["open_world_completeness_claim"] is False
assert result["external_provider_recall_measured"] is False
assert result["candidate_identity_leakage_allowed"] is False
assert set(result["routes"])=={"METADATA","STRUCTURE","HYBRID"}
for route in result["routes"]:
    m=result["metrics"][route]
    assert 0.0 <= m["top1_recall"] <= 1.0
    assert 0.0 <= m["top3_recall"] <= 1.0
    assert m["top3_recall"] >= m["top1_recall"]
    assert len(result["route_top1_hit_case_ids"][route]) <= result["case_count"]

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
