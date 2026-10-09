from copy import deepcopy

from canonical.runtime.benchmark_witness_elimination_compiler_v4 import (
    compile_manifest,
    evaluate_claim,
)

SHA = "1" * 40
BIND = {"path": "canonical/governance/x.json", "git_blob_sha": SHA}
RECEIPT = {"path": "canonical/verification/x.json", "git_blob_sha": SHA}

def proof(claim_id, scope, *, claim_value=None, target_value=None):
    out = {
        "claim_id": claim_id,
        "status": "PROVED_EXACT",
        "proof_type": "DETERMINISTIC_DERIVATION",
        "target_scope": scope,
        "evidence_class": "DETERMINISTIC_FORMAL_PROOF",
        "target_tuple_binding": dict(BIND),
        "receipts": [dict(RECEIPT)],
    }
    if claim_value is not None:
        out["claim_value"] = claim_value
    if target_value is not None:
        out["target_value"] = target_value
    return out

def v3_certificate(lower=0.70, target=0.578):
    return {
        "predicate_id": "CODING_CURSORBENCH_GE_57_8",
        "exact_target_tuple_bound": True,
        "target_tuple_binding": dict(BIND),
        "certificate": {
            "type": "THRESHOLD_LOWER_BOUND",
            "receipts": [dict(RECEIPT)],
            "evaluator_relation": {
                "status": "PROVED_EXACT",
                "relation_type": "EXACT_IDENTITY",
                "target_scope": "FROZEN_TARGET_EVALUATOR_HARNESS_FALLBACK",
                "evidence_class": "EXACT_FROZEN_TARGET_HARNESS",
                "target_tuple_binding": dict(BIND),
                "receipts": [dict(RECEIPT)],
            },
            "proved_lower_bound": lower,
            "target_threshold": target,
            "premise_proofs": {
                "SCORE_DECOMPOSITION_EXACT": proof(
                    "SCORE_DECOMPOSITION_EXACT", "FROZEN_TARGET_SCORING_RULE"
                ),
                "LOWER_BOUND_GE_TARGET": proof(
                    "LOWER_BOUND_GE_TARGET",
                    "FROZEN_TARGET_SCORE_THRESHOLD",
                    claim_value=lower,
                    target_value=target,
                ),
            },
        },
    }

def base():
    identity = {
        "benchmark_id": "CURSORBENCH_4_0",
        "benchmark_version": "4.0",
        "target_id": "OPUS_5_5_MAX",
        "harness_hash": "h1",
        "scoring_rule_hash": "s1",
        "resource_contract_hash": "r1",
    }
    policy = {
        "predicate_id": "CODING_CURSORBENCH_GE_57_8",
        "claim_scope": "CURSORBENCH_4_0_FIXED_BAR",
        "policy_binding": dict(BIND),
        "candidate_binding": dict(BIND),
        "candidate_frozen": True,
        "frozen_at": "2026-10-09T08:00:00+00:00",
        "frozen_identity": dict(identity),
        "identity_keys": list(identity),
        "freshness_keys": [
            "benchmark_id",
            "benchmark_version",
            "target_id",
            "harness_hash",
            "scoring_rule_hash",
        ],
        "scope": {"mode": "EXACT_TASK_SET", "task_ids": ["a", "b"]},
        "require_clean_provenance": True,
        "evaluator": {
            "mode": "ROBUST_FAMILY",
            "required_evaluator_ids": ["native", "independent"],
        },
    }
    evidence = {
        "observed_at": "2026-10-09T08:01:00+00:00",
        "observed_identity": dict(identity),
        "scope_records": [
            {"task_id": "a", "state": "VALID_RESULT"},
            {"task_id": "b", "state": "COUNTED_FAILURE"},
        ],
        "provenance": {
            "binding": dict(RECEIPT),
            "precommitment_frozen": True,
            "target_outcome_not_used": True,
            "status": "CLEAN",
        },
        "evaluator_records": [
            {
                "evaluator_id": "native",
                "binding": dict(RECEIPT),
                "calibration_pass": True,
                "stable_under_declared_perturbations": True,
                "relation": "BRAIN_GE_TARGET",
            },
            {
                "evaluator_id": "independent",
                "binding": dict(RECEIPT),
                "calibration_pass": True,
                "stable_under_declared_perturbations": True,
                "relation": "BRAIN_GT_TARGET",
            },
        ],
        "failure_accounting_complete": True,
        "undisclosed_exclusion_count": 0,
        "reproducible": True,
        "evidence_capsule_binding": dict(RECEIPT),
        "v3_certificate": v3_certificate(),
    }
    return {"policy": policy, "evidence": evidence, "current_identity": dict(identity)}

def test_full_locked_claim_is_proven_but_has_zero_credit():
    out = evaluate_claim(base())
    assert out["status"] == "PROVEN", out
    assert out["promotion_authority"] is False
    assert out["terminal_credit"] == 0
    assert out["acceptance_credit"] == 0
    assert all(v == "PASS" for v in out["locks"].values())

def test_current_target_drift_makes_proof_stale():
    x = base()
    x["current_identity"]["benchmark_version"] = "4.1"
    out = evaluate_claim(x)
    assert out["status"] == "STALE"
    assert out["reason"] == "CURRENT_IDENTITY_DRIFT:benchmark_version"

def test_observed_identity_substitution_is_unknown_not_proven():
    x = base()
    x["evidence"]["observed_identity"]["target_id"] = "OTHER"
    out = evaluate_claim(x)
    assert out["status"] == "UNKNOWN"
    assert out["reason"] == "IDENTITY_MISMATCH:target_id"

def test_missing_task_blocks_scope_inflation():
    x = base()
    x["evidence"]["scope_records"].pop()
    out = evaluate_claim(x)
    assert out["status"] == "UNKNOWN"
    assert out["reason"] == "CLAIM_SCOPE_EXCEEDS_OR_DIFFERS_FROM_EVIDENCE_SCOPE"

def test_extra_task_also_fails_exact_scope_identity():
    x = base()
    x["evidence"]["scope_records"].append({"task_id": "c", "state": "VALID_RESULT"})
    assert evaluate_claim(x)["status"] == "UNKNOWN"

def test_duplicate_task_rejected():
    x = base()
    x["evidence"]["scope_records"].append({"task_id": "a", "state": "VALID_RESULT"})
    out = evaluate_claim(x)
    assert out["status"] == "UNKNOWN"
    assert out["reason"] == "SCOPE_RECORD_DUPLICATE:a"

def test_nonterminal_scope_record_rejected():
    x = base()
    x["evidence"]["scope_records"][0]["state"] = "MISSING"
    out = evaluate_claim(x)
    assert out["status"] == "UNKNOWN"
    assert out["reason"] == "SCOPE_RECORD_NONTERMINAL:a"

def test_contamination_never_promotes():
    x = base()
    x["evidence"]["provenance"]["status"] = "CONTAMINATED"
    out = evaluate_claim(x)
    assert out["status"] == "UNKNOWN"
    assert out["reason"] == "RUN_CONTAMINATED_OR_UNCLEARED"

def test_target_outcome_leakage_never_promotes():
    x = base()
    x["evidence"]["provenance"]["target_outcome_not_used"] = False
    assert evaluate_claim(x)["status"] == "UNKNOWN"

def test_policy_must_precede_evidence():
    x = base()
    x["evidence"]["observed_at"] = "2026-10-09T07:59:59+00:00"
    out = evaluate_claim(x)
    assert out["status"] == "UNKNOWN"
    assert out["reason"] == "EVIDENCE_PREDATES_FROZEN_POLICY"

def test_evaluator_family_cannot_be_cherry_picked():
    x = base()
    x["evidence"]["evaluator_records"].pop()
    out = evaluate_claim(x)
    assert out["status"] == "UNKNOWN"
    assert out["reason"] == "EVALUATOR_FAMILY_COVERAGE_MISMATCH"

def test_calibration_failure_blocks_evaluator():
    x = base()
    x["evidence"]["evaluator_records"][0]["calibration_pass"] = False
    assert evaluate_claim(x)["status"] == "UNKNOWN"

def test_evaluator_instability_blocks_evaluator():
    x = base()
    x["evidence"]["evaluator_records"][0]["stable_under_declared_perturbations"] = False
    assert evaluate_claim(x)["status"] == "UNKNOWN"

def test_admissible_evaluator_counterevidence_disproves_robust_claim():
    x = base()
    x["evidence"]["evaluator_records"][1]["relation"] = "TARGET_GT_BRAIN"
    out = evaluate_claim(x)
    assert out["status"] == "DISPROVEN"
    assert out["reason"].startswith("ADMISSIBLE_EVALUATOR_FAVORS_TARGET:")

def test_failure_accounting_incomplete_blocks_claim():
    x = base()
    x["evidence"]["failure_accounting_complete"] = False
    assert evaluate_claim(x)["status"] == "UNKNOWN"

def test_undisclosed_exclusion_blocks_claim():
    x = base()
    x["evidence"]["undisclosed_exclusion_count"] = 1
    assert evaluate_claim(x)["status"] == "UNKNOWN"

def test_reproducibility_required():
    x = base()
    x["evidence"]["reproducible"] = False
    assert evaluate_claim(x)["status"] == "UNKNOWN"

def test_v3_structural_proof_remains_required():
    x = base()
    del x["evidence"]["v3_certificate"]["certificate"]["premise_proofs"]["SCORE_DECOMPOSITION_EXACT"]
    out = evaluate_claim(x)
    assert out["status"] == "UNKNOWN"
    assert out["reason"].startswith("V3_NOT_ADMISSIBLE:")

def test_proved_lower_bound_below_target_is_disproven():
    x = base()
    x["evidence"]["v3_certificate"] = v3_certificate(lower=0.50, target=0.578)
    out = evaluate_claim(x)
    assert out["status"] == "DISPROVEN"
    assert out["reason"] == "PROVED_LOWER_BOUND_BELOW_TARGET"

def test_bound_scope_receipt_mode():
    x = base()
    x["policy"]["scope"] = {"mode": "BOUND_SCOPE_RECEIPT", "scope_id": "gold-220"}
    x["evidence"].pop("scope_records")
    x["evidence"]["scope_receipt"] = {
        "binding": dict(RECEIPT),
        "independent_verified": True,
        "scope_complete": True,
        "scope_id": "gold-220",
    }
    assert evaluate_claim(x)["status"] == "PROVEN"

def test_proof_carrying_superset_mode():
    x = base()
    x["policy"]["scope"] = {"mode": "PROOF_CARRYING_SUPERSET"}
    x["evidence"].pop("scope_records")
    x["evidence"]["scope_cover"] = {
        "benchmark_id": "CURSORBENCH_4_0",
        "predicate_id": "CODING_CURSORBENCH_GE_57_8",
        "scope_completeness": {
            "verified": True,
            "independent": True,
            "source_path": "canonical/verification/scope.json",
            "source_sha": SHA,
            "basis": "UNIVERSAL_FORMAL_SCOPE_PROOF",
            "all_admissible_target_inputs_proved": True,
            "formal_completeness": True,
        },
        "cover_completeness": {
            "verified": True,
            "independent": True,
            "source_path": "canonical/verification/cover.json",
            "source_sha": SHA,
            "covers_entire_scope": True,
        },
        "cells": [{
            "cell_id": "ALL",
            "scope_relation": "PROVEN_STRONGER",
            "policy_id": "P",
            "brain_owned_policy": True,
            "deployable": True,
            "resource_admissible": True,
            "external_target_capability_provider": False,
            "adequacy_certificate": {
                "verified": True,
                "independent": True,
                "source_path": "canonical/verification/adequacy.json",
                "source_sha": SHA,
                "adequate_for_entire_cell": True,
            },
        }],
    }
    assert evaluate_claim(x)["status"] == "PROVEN"

def test_public_description_cannot_masquerade_as_scope_superset():
    x = base()
    x["policy"]["scope"] = {"mode": "PROOF_CARRYING_SUPERSET"}
    x["evidence"].pop("scope_records")
    x["evidence"]["scope_cover"] = {
        "benchmark_id": "CURSORBENCH_4_0",
        "predicate_id": "CODING_CURSORBENCH_GE_57_8",
        "scope_completeness": {
            "verified": True,
            "independent": True,
            "source_path": "canonical/evidence/blog.json",
            "source_sha": SHA,
            "basis": "PUBLIC_DESCRIPTION_ONLY",
        },
        "cover_completeness": {
            "verified": True,
            "independent": True,
            "source_path": "canonical/evidence/cover.json",
            "source_sha": SHA,
            "covers_entire_scope": True,
        },
        "cells": [],
    }
    assert evaluate_claim(x)["status"] == "UNKNOWN"

def test_manifest_counts_all_four_truth_states():
    a = base()
    b = deepcopy(a)
    b["current_identity"]["benchmark_version"] = "4.1"
    c = deepcopy(a)
    c["evidence"]["scope_records"].pop()
    d = deepcopy(a)
    d["evidence"]["evaluator_records"][0]["relation"] = "TARGET_GT_BRAIN"
    out = compile_manifest({"claims": [a, b, c, d]})
    assert out["proved_count"] == 1
    assert out["stale_count"] == 1
    assert out["unknown_count"] == 1
    assert out["disproved_count"] == 1
    assert out["promotion_authority"] is False

def test_stronger_scope_cover_for_different_benchmark_is_rejected():
    x = base()
    x["policy"]["scope"] = {"mode": "PROOF_CARRYING_SUPERSET"}
    x["evidence"].pop("scope_records")
    x["evidence"]["scope_cover"] = {
        "benchmark_id": "SOME_OTHER_BENCHMARK",
        "predicate_id": "CODING_CURSORBENCH_GE_57_8",
        "scope_completeness": {
            "verified": True,
            "independent": True,
            "source_path": "canonical/verification/scope.json",
            "source_sha": SHA,
            "basis": "UNIVERSAL_FORMAL_SCOPE_PROOF",
            "all_admissible_target_inputs_proved": True,
            "formal_completeness": True,
        },
        "cover_completeness": {
            "verified": True,
            "independent": True,
            "source_path": "canonical/verification/cover.json",
            "source_sha": SHA,
            "covers_entire_scope": True,
        },
        "cells": [{
            "cell_id": "ALL",
            "scope_relation": "PROVEN_STRONGER",
            "policy_id": "P",
            "brain_owned_policy": True,
            "deployable": True,
            "resource_admissible": True,
            "external_target_capability_provider": False,
            "adequacy_certificate": {
                "verified": True,
                "independent": True,
                "source_path": "canonical/verification/adequacy.json",
                "source_sha": SHA,
                "adequate_for_entire_cell": True,
            },
        }],
    }
    out = evaluate_claim(x)
    assert out["status"] == "UNKNOWN"
    assert out["reason"] == "SCOPE_COVER_BENCHMARK_ID_MISMATCH"


def test_adverse_evidence_is_monotone_non_improving():
    baseline = evaluate_claim(base())
    assert baseline["status"] == "PROVEN"

    mutations = []

    contaminated = base()
    contaminated["evidence"]["provenance"]["status"] = "CONTAMINATED"
    mutations.append(contaminated)

    missing_scope = base()
    missing_scope["evidence"]["scope_records"].pop()
    mutations.append(missing_scope)

    unstable_judge = base()
    unstable_judge["evidence"]["evaluator_records"][0]["stable_under_declared_perturbations"] = False
    mutations.append(unstable_judge)

    counterevidence = base()
    counterevidence["evidence"]["evaluator_records"][0]["relation"] = "TARGET_GT_BRAIN"
    mutations.append(counterevidence)

    for case in mutations:
        assert evaluate_claim(case)["status"] != "PROVEN"

def test_timezone_naive_freeze_is_rejected():
    x = base()
    x["policy"]["frozen_at"] = "2026-10-09T08:00:00"
    out = evaluate_claim(x)
    assert out["status"] == "UNKNOWN"
    assert out["reason"] == "POLICY_OR_EVIDENCE_TIMEZONE_MISSING"


def test_objective_mode_requires_independent_evaluator_evidence():
    x = base()
    x["policy"]["evaluator"] = {
        "mode": "OBJECTIVE",
        "objective_validator": True,
    }
    x["evidence"].pop("evaluator_records")
    out = evaluate_claim(x)
    assert out["status"] == "UNKNOWN"
    assert out["reason"] == "OBJECTIVE_EVALUATOR_EVIDENCE_MISSING"

    x["evidence"]["objective_evaluator"] = {
        "binding": dict(RECEIPT),
        "independent_verified": True,
        "relation": "BRAIN_GE_TARGET",
    }
    assert evaluate_claim(x)["status"] == "PROVEN"


def test_objective_counterevidence_disproves_claim():
    x = base()
    x["policy"]["evaluator"] = {
        "mode": "OBJECTIVE",
        "objective_validator": True,
    }
    x["evidence"].pop("evaluator_records")
    x["evidence"]["objective_evaluator"] = {
        "binding": dict(RECEIPT),
        "independent_verified": True,
        "relation": "TARGET_GT_BRAIN",
    }
    assert evaluate_claim(x)["status"] == "DISPROVEN"
