from pathlib import Path
from canonical.runtime import retrieval_route_strategy_calibration_v3 as c3
from canonical.runtime import retrieval_recovery_mechanism_calibration_v1 as rm

ROOT=Path(__file__).resolve().parents[2]

def test_v11_is_in_first_pass_calibration():
    out=c3.calibrate_repository(ROOT)
    assert out["v11_stratified_events_included"] is True
    assert out["v11_event_count"]==30
    assert out["case_count"]>=30
    keys=set(out["route_strategy_stats"])
    assert "GITHUB_REPOSITORY_SEARCH::NATIVE_LANGUAGE_BEHAVIOR_V11" in keys
    assert "MAVEN_CENTRAL_SEARCH::BEHAVIOR_ANCHOR_V11" in keys

def test_recovery_mechanisms_are_separate_and_truthful():
    out=rm.calibrate_repository(ROOT)
    m=out["mechanisms"]
    assert m["MULTI_QUERY_DECOMPOSITION_V12"]["residual_trial_count"]==18
    assert m["MULTI_QUERY_DECOMPOSITION_V12"]["recovered_count"]==10
    assert m["RESIDUAL_ROOT_FIX_V13"]["residual_trial_count"]==8
    assert m["RESIDUAL_ROOT_FIX_V13"]["recovered_count"]==5
    assert m["MAVEN_DEEP_MANIFEST_V14"]["residual_trial_count"]==3
    assert m["MAVEN_DEEP_MANIFEST_V14"]["recovered_count"]==1
    assert m["BEHAVIOR_CONTEXT_GRAPH_SNOWBALL_V16"]["recovered_count"]==1
    assert m["VERSION_HISTORY_IDENTITY_V18"]["recovered_count"]==1
    assert out["open_world_completeness_claim"] is False

if __name__=="__main__":
    test_v11_is_in_first_pass_calibration()
    test_recovery_mechanisms_are_separate_and_truthful()
    print("test_retrieval_calibration_v3: PASS")
