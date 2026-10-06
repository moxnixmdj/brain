from canonical.runtime.matched_research_tool_artifact_direct_v1 import execute_case,causal_ablation,run_batch

def test_direct_research_tool_artifact_batch_passes_all_domains():
    out=run_batch(20261007,12)
    assert out["all_pass"] is True,out
    assert out["passed"]==12
    assert len(out["domains"])==6

def test_artifact_is_content_bound_to_research_history():
    row=execute_case(123456,0)
    assert row["pass"] is True,row
    doc=row["artifact_payload"]
    assert doc["research_history_sha256"]==row["research_history_sha256"]
    assert len(doc["resolved_requirement_ids"])==row["required_requirement_count"]
    ab=causal_ablation(123456,0)
    assert ab["full_pass"] is True
    assert ab["hash_changed"] is True
    assert ab["research_binding_removed"] is True

def test_objective_trace_has_causal_research_tool_artifact_chain():
    row=execute_case(987654,1)
    events=row["objective_trace"]["events"]
    research=next(x for x in events if x["type"]=="RESEARCH_RESULT")
    tool=next(x for x in events if x["type"]=="TOOL_RESULT")
    artifact=next(x for x in events if x["type"]=="ARTIFACT_CREATED")
    terminal=events[-1]
    assert research["research_scorer_pass"] is True
    assert tool["ok"] is True
    assert research["seq"]<tool["seq"]<artifact["seq"]<terminal["seq"]
    assert research["event_id"] in artifact["source_event_ids"]
    assert tool["event_id"] in artifact["source_event_ids"]
    assert artifact["content_binds_research_history_sha256"]==research["research_history_sha256"]
    assert terminal["type"]=="TERMINAL" and terminal["success"] is True
