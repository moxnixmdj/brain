import json
import tempfile
from pathlib import Path

from canonical.runtime.objective_fixed_bar_pass_lock_reconciliation_v1 import (
    BOUND,
    ROOT,
    verify_documents,
    verify_repository,
)


def _load_bound_from_repo():
    out={}
    for key,(rel,_sha) in BOUND.items():
        out[key]=json.loads((ROOT/rel).read_text())
    return out


def test_repository_binding_passes():
    out=verify_repository()
    assert out["pass"] is True
    assert out["terminal_credit_delta"] == 0
    assert out["execution_authority"] is False


def test_tb4_current_frozen_route_is_fail_locked():
    out=verify_repository()
    row=out["surfaces"]["TB4"]
    assert row["required_successes"] == 220
    assert row["current_maximum_attainable_successes"] == 180
    assert row["decision"] == "FAIL_LOCKED"
    assert row["scheduler_action"].startswith("DELETE_CURRENT_FROZEN_DIRECT_EXECUTION_ROUTE")


def test_automation_exact_pass_lock_is_240():
    out=verify_repository()
    row=out["surfaces"]["AUTOMATIONBENCH"]
    assert row["population_slots"] == 600
    assert row["required_successes"] == 240
    assert row["pass_lock_rule"] == "OBSERVED_VALID_SUCCESSES_GE_240"


def test_hle_candidate_lock_is_677_but_not_promoted():
    out=verify_repository()
    row=out["surfaces"]["HLE_DIAMOND_TOOLS"]
    assert row["population_questions"] == 1000
    assert row["candidate_required_correct_judgments"] == 677
    assert row["promotion_state"].startswith("ARITHMETIC_CANDIDATE")
    assert "DO_NOT_RUN" in row["scheduler_action"]


def test_chartography_candidate_lock_is_890_but_not_promoted():
    out=verify_repository()
    row=out["surfaces"]["CHARTOGRAPHY"]
    assert row["scheduled_trials"] == 1000
    assert row["candidate_required_successes"] == 890
    assert row["promotion_state"].startswith("ARITHMETIC_CANDIDATE")
    assert "DO_NOT_RUN" in row["scheduler_action"]


def test_no_fresh_reality_or_promotion_authority():
    out=verify_repository()
    assert out["fresh_reality_authority"] is False
    assert out["execution_authority"] is False
    assert out["promotion_authority"] is False
    assert out["terminal_authority"] is False


def test_semantic_mutation_fails_document_verification():
    docs=_load_bound_from_repo()
    docs["automation"]=json.loads(json.dumps(docs["automation"]))
    docs["automation"]["represented_scope"]["target_threshold"]=0.41
    out=verify_documents(docs)
    assert out["pass"] is False
    assert "AUTOMATION_REQUIRED_SUCCESS_DRIFT" in out["errors"]


def test_tb4_attainability_mutation_fails():
    docs=_load_bound_from_repo()
    docs["tb4_attainability"]=json.loads(json.dumps(docs["tb4_attainability"]))
    docs["tb4_attainability"]["derived"]["maximum_attainable_successes"]=220
    out=verify_documents(docs)
    assert out["pass"] is False
    assert "TB4_MAX_ATTAINABLE_SUCCESS_DRIFT" in out["errors"]
    assert "TB4_CURRENT_FROZEN_ROUTE_NOT_FAIL_LOCKED" in out["errors"]
