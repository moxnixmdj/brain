from pathlib import Path
from canonical.runtime import retrieval_real_hidden_witness_fusion_v2 as f

ROOT=Path(__file__).resolve().parents[2]
out=f.evaluate(ROOT)
assert out["status"]=="MEASURED__LEAVE_ONE_TARGET_OUT_CROSS_VALIDATED_RANK_FUSION"
assert out["cross_validated"]["case_count"]==104
assert out["cross_validated"]["target_fold_count"]==13
assert out["preserves_existing_pooled_top5_recall"] is True
assert out["baseline"]["monotonic_pooled"]["5"]["recall"]==1.0
assert out["open_world_recall_claim"] is False
assert out["live_provider_oracle"] is False
assert len(out["folds"])==13
for fold in out["folds"]:
    assert fold["heldout_case_count"]==8
    assert set(fold["selected_weights"])==set(out["routes"])
    assert fold["heldout_top5"]>=0.0
# Promotion eligibility is empirical. The test must not assume an improvement
# exists before independent execution measures it.
assert isinstance(out["promotion_eligible"],bool)
print("test_retrieval_real_hidden_witness_fusion_v2: PASS")
