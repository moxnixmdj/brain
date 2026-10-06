from canonical.runtime.matched_delegation_synthesis_artifact_direct_v1 import execute_case,run_batch

def test_delegation_synthesis_artifact_batch_passes():
    out=run_batch(20261007,10)
    assert out["all_pass"] is True,out
    assert out["passed"]==10

def test_multiworker_evidence_is_causally_required_by_synthesis():
    row=execute_case(123456,0)
    assert row["pass"] is True,row
    assert row["delegation_case_class"]=="DUAL_ROOT_FANIN"
    assert row["delegation_worker_count"]>=2
    assert row["delegation_plan_pass"] is True
    assert row["synthesis_pass"] is True
    assert row["artifact_pass"] is True
    assert row["missing_evidence_ablation_fails"] is True

def test_objective_trace_is_delegation_to_evidence_to_synthesis_to_artifact():
    row=execute_case(987654,1)
    events=row["objective_trace"]["events"]
    delegates=[x for x in events if x["type"]=="DELEGATE"]
    evidence=[x for x in events if x["type"]=="EVIDENCE_RECEIVED"]
    synthesis=next(x for x in events if x["type"]=="SYNTHESIS")
    artifact=next(x for x in events if x["type"]=="ARTIFACT_CREATED")
    terminal=events[-1]
    assert len({x["worker_id"] for x in delegates})>=2
    assert len(evidence)>=2
    assert set(synthesis["evidence_ids"])=={x["evidence_id"] for x in evidence}
    assert artifact["synthesis_id"]==synthesis["synthesis_id"]
    assert set(artifact["artifact_binds_evidence_ids"])==set(synthesis["evidence_ids"])
    assert terminal["type"]=="TERMINAL" and terminal["success"] is True
