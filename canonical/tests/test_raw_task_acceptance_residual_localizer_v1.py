from copy import deepcopy

from canonical.runtime.lossless_raw_task_contract_v1 import compile_contract
from canonical.runtime.raw_task_acceptance_residual_localizer_v1 import localize


def contract(text):
    out = compile_contract(
        text,
        source_id="user",
        routing_target_effects=["candidate.ready"],
    )
    assert out["pass"] is True, out
    return out


def test_explicit_exact_response_gets_objective_route_but_not_acceptance():
    c = contract('Respond with exactly "YES".')
    out = localize(c)
    assert out["pass"] is True, out
    assert out["required_obligation_count"] == 1
    assert out["objective_route_obligation_count"] == 1
    assert out["semantic_residual_obligation_count"] == 0
    row = out["obligations"][0]
    assert row["status"] == "OBJECTIVE_ACCEPTANCE_ROUTE_AVAILABLE"
    assert [x["route_id"] for x in row["available_objective_routes"]] == [
        "INSTRUCTION_CONSTRAINTS_V1"
    ]
    assert row["accepted"] is False
    assert row["acceptance_receipt_still_required"] is True
    assert out["objective_route_availability_is_acceptance"] is False
    assert out["acceptance_credit_authorized"] is False


def test_imperative_recognition_alone_stays_semantic_residual():
    c = contract("Create a polished financial report.")
    row0 = c["acceptance_contract"]["obligations"][0]
    assert row0["structured_requirement_ids"], c
    out = localize(c)
    assert out["pass"] is True, out
    assert out["objective_route_obligation_count"] == 0
    assert out["semantic_residual_obligation_count"] == 1
    row = out["obligations"][0]
    assert row["status"] == "SEMANTIC_ADJUDICATION_REQUIRED"
    assert row["semantic_residual_reason"] == (
        "SOURCE_BOUND_REQUIREMENT_IDENTIFIED_BUT_NO_SOUND_CANDIDATE_ACCEPTANCE_SEMANTICS_COMPILED"
    )
    assert row["accepted"] is False


def test_source_aligned_controlled_field_requirement_gets_route():
    c = contract("score must be at least 5.")
    out = localize(
        c,
        candidate_field_schema={
            "score": {"type": "number", "dimension": "points"},
        },
    )
    assert out["pass"] is True, out
    row = out["obligations"][0]
    assert row["status"] == "OBJECTIVE_ACCEPTANCE_ROUTE_AVAILABLE"
    ids = {x["route_id"] for x in row["available_objective_routes"]}
    assert "SOURCE_ALIGNED_ACCEPTANCE_PROGRAM_V1" in ids
    route = next(
        x for x in row["available_objective_routes"]
        if x["route_id"] == "SOURCE_ALIGNED_ACCEPTANCE_PROGRAM_V1"
    )
    assert route["acceptance_program"]["accept_when"]["op"] == "ge"
    assert row["accepted"] is False


def test_mixed_task_partitions_without_dropping_semantic_remainder():
    c = contract(
        'Respond with exactly "YES".\n'
        "Create a polished financial report."
    )
    out = localize(c)
    assert out["pass"] is True, out
    assert out["required_obligation_count"] == 2
    assert out["accounted_obligation_count"] == 2
    assert out["objective_route_obligation_count"] == 1
    assert out["semantic_residual_obligation_count"] == 1
    assert set(out["objective_route_obligation_ids"]).isdisjoint(
        out["semantic_residual_obligation_ids"]
    )
    assert (
        set(out["objective_route_obligation_ids"])
        | set(out["semantic_residual_obligation_ids"])
    ) == set(c["acceptance_contract"]["required_obligation_ids"])


def test_unrecognized_raw_segment_remains_residual_not_ignored():
    c = contract("Blue horizons beyond measure.")
    out = localize(c)
    assert out["pass"] is True, out
    assert out["semantic_residual_obligation_count"] == 1
    assert out["obligations"][0]["semantic_residual_reason"] == (
        "NO_SOUND_OBJECTIVE_CANDIDATE_ACCEPTANCE_ROUTE_FOR_RAW_SEGMENT"
    )
    assert out["missing_route_may_be_silently_ignored"] is False


def test_segment_hash_drift_fails_closed():
    c = contract("Create a PDF.")
    bad = deepcopy(c)
    bad["acceptance_contract"]["obligations"][0]["text"] = "Create a DOCX."
    out = localize(bad)
    assert out["pass"] is False
    assert "SEGMENT_SHA256_MISMATCH" in out["reason"]


def test_required_obligation_set_drift_fails_closed():
    c = contract("Create a PDF.")
    bad = deepcopy(c)
    bad["acceptance_contract"]["required_obligation_ids"] = ["invented"]
    out = localize(bad)
    assert out["pass"] is False
    assert "REQUIRED_OBLIGATION_SET_MISMATCH" in out["reason"]


def test_invalid_field_schema_fails_closed():
    c = contract("score must be at least 5.")
    out = localize(c, candidate_field_schema="not-a-schema")
    assert out["pass"] is False
    assert "CANDIDATE_FIELD_SCHEMA_INVALID" in out["reason"]


def test_out_of_grammar_normative_requirement_does_not_get_source_route():
    c = contract("score must be professionally excellent.")
    out = localize(
        c,
        candidate_field_schema={
            "score": {"type": "number", "dimension": "points"},
        },
    )
    assert out["pass"] is True, out
    row = out["obligations"][0]
    assert row["status"] == "SEMANTIC_ADJUDICATION_REQUIRED"
    assert not row["available_objective_routes"]
    diag = next(
        x for x in row["route_diagnostics"]
        if x["route_id"] == "SOURCE_ALIGNED_ACCEPTANCE_PROGRAM_V1"
    )
    assert diag["status"] == "UNRESOLVED"
