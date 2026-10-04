from pathlib import Path
from canonical.runtime import global_retrieval_controller_v1 as state_base
from canonical.runtime import global_retrieval_controller_v4 as c4
from canonical.runtime import global_retrieval_entrypoint_v4 as e4
from canonical.runtime import retrieval_route_strategy_calibration_v3 as fc
from canonical.runtime import retrieval_recovery_mechanism_calibration_v1 as rc

ROOT=Path(__file__).resolve().parents[2]

def calibrations():
    return fc.calibrate_repository(ROOT),rc.calibrate_repository(ROOT)

def test_scope_locks():
    first,recovery=calibrations()
    nonmaven=c4.compile_global_plan(
        query_actions=[],sources=[],route_strategy_calibration=first,
        recovery_mechanism_calibration=recovery,state=state_base.new_state(),
        recovery_context={
            "ecosystem":"PYTHON",
            "repository_candidates_available":True,
            "behavior_context_links_available":True,
            "current_manifest_identity_observed":True,
            "versioned_identity_drift_suspected":True,
        },
    )
    mids={x["mechanism_id"] for x in nonmaven["conditional_recovery_actions"]}
    assert "BEHAVIOR_CONTEXT_GRAPH_SNOWBALL_V16" not in mids
    assert "VERSION_HISTORY_IDENTITY_V18" not in mids

    maven=c4.compile_global_plan(
        query_actions=[],sources=[],route_strategy_calibration=first,
        recovery_mechanism_calibration=recovery,state=state_base.new_state(),
        recovery_context={
            "ecosystem":"MAVEN",
            "prior_first_pass_miss":True,
            "repository_candidates_available":True,
            "behavior_context_links_available":True,
            "current_manifest_identity_observed":True,
            "versioned_identity_drift_suspected":True,
        },
    )
    mids={x["mechanism_id"] for x in maven["conditional_recovery_actions"]}
    assert "MULTI_QUERY_DECOMPOSITION_V12" in mids
    assert "MAVEN_DEEP_MANIFEST_V14" in mids
    assert "BEHAVIOR_CONTEXT_GRAPH_SNOWBALL_V16" in mids
    assert "VERSION_HISTORY_IDENTITY_V18" in mids

def test_authorized_entrypoint_uses_new_calibrations():
    out=e4.compile_authorized_plan(
        root=ROOT,query_actions=[],sources=[],
        recovery_context={"ecosystem":"MAVEN","current_manifest_identity_observed":True,"versioned_identity_drift_suspected":True},
    )
    assert out["status"].startswith("PASS__AUTHORIZED_SCOPE_AWARE")
    assert out["first_pass_calibration"]["v11_stratified_events_included"] is True
    assert out["recovery_mechanism_calibration"]["mechanism_count"]==5
    mids={x["mechanism_id"] for x in out["plan"]["conditional_recovery_actions"]}
    assert "VERSION_HISTORY_IDENTITY_V18" in mids
    assert out["execution_authority"] is False
    assert out["promotion_authority"] is False

if __name__=="__main__":
    test_scope_locks()
    test_authorized_entrypoint_uses_new_calibrations()
    print("test_global_retrieval_controller_v4: PASS")
