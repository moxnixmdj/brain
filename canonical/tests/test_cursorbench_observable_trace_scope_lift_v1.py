from canonical.runtime.cursorbench_observable_trace_scope_lift_v1 import reduce_scope, verify

def good():
    return dict(
        benchmark_id="CURSORBENCH_4_0",
        predicate_id="CODING_CURSORBENCH_GE_57_8",
        official_score_is_externally_measurable=True,
        task_contexts_trace_representable=True,
        hidden_score_relevant_requirements_are_trace_or_outcome_predicates=True,
        opaque_payload_superdomain_total=True,
        public_taxonomy_used_as_exhaustive=False,
        brain_dominance_claimed=False,
    )

def test_current_bound_sources_pass():
    out = verify()
    assert out["pass"], out
    assert out["scope_complete"] is True
    assert out["dominance_closed"] is False
    assert out["adequacy_cover_closed"] is False
    assert out["acceptance_credit_delta"] == 0

def test_wrong_benchmark_rejected():
    x = good()
    x["benchmark_id"] = "CURSORBENCH_3_2"
    out = reduce_scope(**x)
    assert not out["pass"]
    assert "BENCHMARK_ID_MISMATCH" in out["errors"]

def test_wrong_predicate_rejected():
    x = good()
    x["predicate_id"] = "CODING_TB4_GE_66_4"
    out = reduce_scope(**x)
    assert not out["pass"]
    assert "PREDICATE_ID_MISMATCH" in out["errors"]

def test_public_taxonomy_cannot_be_used_as_exhaustive_scope():
    x = good()
    x["public_taxonomy_used_as_exhaustive"] = True
    out = reduce_scope(**x)
    assert not out["pass"]
    assert "PUBLIC_TAXONOMY_COMPLETENESS_SHORTCUT_FORBIDDEN" in out["errors"]

def test_hidden_requirement_escape_reopens_scope():
    x = good()
    x["hidden_score_relevant_requirements_are_trace_or_outcome_predicates"] = False
    out = reduce_scope(**x)
    assert not out["pass"]
    assert "HIDDEN_REQUIREMENT_SCOPE_ESCAPE_NOT_EXCLUDED" in out["errors"]

def test_opaque_payload_totality_is_load_bearing():
    x = good()
    x["opaque_payload_superdomain_total"] = False
    out = reduce_scope(**x)
    assert not out["pass"]
    assert "OPAQUE_PAYLOAD_SUPERDOMAIN_NOT_TOTAL" in out["errors"]

def test_scope_proof_cannot_smuggle_dominance():
    x = good()
    x["brain_dominance_claimed"] = True
    out = reduce_scope(**x)
    assert not out["pass"]
    assert "SCOPE_PROOF_SMUGGLES_DOMINANCE" in out["errors"]

def test_missing_external_score_binding_reopens():
    x = good()
    x["official_score_is_externally_measurable"] = False
    out = reduce_scope(**x)
    assert not out["pass"]
    assert "BENCHMARK_OUTCOME_NOT_BOUND_TO_EXTERNAL_MEASURE" in out["errors"]
