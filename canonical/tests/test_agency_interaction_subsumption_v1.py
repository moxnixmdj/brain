from copy import deepcopy

from canonical.runtime.agency_interaction_subsumption_v1 import (
    _load_bound,
    verify_documents,
    verify_repository,
)


def test_exact_repository_premises_close_interaction_residual():
    out=verify_repository()
    assert out["pass"] is True,out
    assert out["cross_component_new_mechanism_required"] is False
    assert len(out["frozen_agency_dimensions"])==6


def test_missing_live_replanning_interaction_fails_closed():
    docs=_load_bound()
    docs=deepcopy(docs)
    docs["delegation_relation"]["required_interactions"].remove(
        "LIVE_RECEIPT_TO_REVISED_PARTITION_ASSIGNMENT_OR_SCHEDULE"
    )
    out=verify_documents(docs)
    assert out["pass"] is False
    assert "DELEGATION_INTERACTION_COVER_INCOMPLETE" in out["errors"]


def test_receipt_alphabet_drift_fails_closed():
    docs=deepcopy(_load_bound())
    docs["delegation_v2_relation"]["exact_contract_boundary"]["supported_receipt_kinds"].remove(
        "STEP_UNAVAILABLE"
    )
    out=verify_documents(docs)
    assert out["pass"] is False
    assert "DELEGATION_RECEIPT_ALPHABET_DRIFT" in out["errors"]


def test_recovery_ceiling_drift_fails_closed():
    docs=deepcopy(_load_bound())
    docs["recovery_verify"]["theorem"]["universal_achieved_bounds"]["terminal_recovery"]=0
    out=verify_documents(docs)
    assert out["pass"] is False
    assert "RECOVERY_CEILING_NOT_BOUND" in out["errors"]


def test_stateful_checkpoint_witness_drift_fails_closed():
    docs=deepcopy(_load_bound())
    docs["stateful_agency"]["local_continuity_truth_repair"]["exact_process_trace"]=[]
    out=verify_documents(docs)
    assert out["pass"] is False
    assert "STATEFUL_CHECKPOINT_RELAUNCH_TRACE_MISSING" in out["errors"]
