"""Deterministic Stage-A admission reducer for rank15 wdm-design.

Authority is the underlying frozen evidence, not a hand-written PASS label.
This reducer authorizes instruction exposure only. It never authorizes task
execution and never changes whole-family or terminal ownership credit.
"""
from __future__ import annotations
from typing import Any

EXPECTED_BENCHMARK_REF="452bf305c6daa62fc59061d22133a7cbc7c1572e"
EXPECTED_TASK="wdm-design"
EXPECTED_RANK=15
EXPECTED_TASK_SHA="57a897eff90387df26415d1bfb81c492d50b4d41159587617bfefda8c2f2bf8d"
EXPECTED_TARGET_MODEL="Claude Opus 5.5"
EXPECTED_BAR=0.664

def evaluate(e: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    required = ("target_lock","contamination","surface","acceptance","requirement_graph","statistics","donor_protocol")
    for key in required:
        if not isinstance(e.get(key), dict):
            failures.append("MISSING_EVIDENCE:"+key)
    if failures:
        return _result(failures)

    lock=e["target_lock"]
    if lock.get("status")!="FROZEN_STAGE_A_LOCAL_QUALIFICATION_SCOPE":
        failures.append("TARGET_LOCK_NOT_FROZEN")
    if lock.get("target_model")!=EXPECTED_TARGET_MODEL:
        failures.append("TARGET_MODEL_MISMATCH")
    if lock.get("benchmark_ref")!=EXPECTED_BENCHMARK_REF:
        failures.append("BENCHMARK_REF_MISMATCH")
    if float((lock.get("acceptance_bar") or {}).get("success_fraction",-1))!=EXPECTED_BAR:
        failures.append("ACCEPTANCE_BAR_MISMATCH")
    sample=lock.get("sample_manifest") or {}
    if sample.get("rank15_task")!=EXPECTED_TASK or sample.get("rank15_identity_sha256")!=EXPECTED_TASK_SHA:
        failures.append("RANK15_IDENTITY_MISMATCH")

    contamination=e["contamination"]
    if contamination.get("task")!=EXPECTED_TASK or contamination.get("rank")!=EXPECTED_RANK:
        failures.append("CONTAMINATION_LEDGER_TASK_MISMATCH")
    if contamination.get("task_identity_sha256")!=EXPECTED_TASK_SHA:
        failures.append("CONTAMINATION_LEDGER_IDENTITY_MISMATCH")
    if contamination.get("benchmark_ref")!=EXPECTED_BENCHMARK_REF:
        failures.append("CONTAMINATION_LEDGER_BENCHMARK_MISMATCH")
    if contamination.get("state")!="UNEXPOSED__STAGE_A_PRE_EXPOSURE":
        failures.append("TASK_NOT_UNEXPOSED")
    for field in ("instruction_read","hidden_verifier_read","task_specific_hints_read","task_specific_web_or_repo_search","task_command_executed"):
        if contamination.get(field) is not False:
            failures.append("EXPOSURE_FLAG_NOT_FALSE:"+field)
    if contamination.get("clean_for_stage_b_exposure") is not True:
        failures.append("CONTAMINATION_LEDGER_NOT_CLEAN")

    surface=e["surface"]
    if surface.get("status")!="STAGE_A_GENERIC_SURFACE_PASS__TASK_SPECIFIC_SURFACE_UNCLAIMED":
        failures.append("GENERIC_SURFACE_NOT_PASS")
    verified=surface.get("verified")
    if not isinstance(verified,list) or not verified or any(x.get("conclusion")!="success" for x in verified if isinstance(x,dict)):
        failures.append("GENERIC_SURFACE_VERIFICATION_NOT_ALL_SUCCESS")

    acceptance=e["acceptance"]
    runner=acceptance.get("runner") or {}
    if runner.get("source_exact_match") is not True or runner.get("tests_passed")!=runner.get("tests_run") or not runner.get("tests_run"):
        failures.append("INDEPENDENT_ACCEPTANCE_NOT_VERIFIED")
    if "MAY_BE_USED_AS_A_NECESSARY_FAIL_CLOSED_TERMINAL_GATE_ONLY__MUST_NOT_BE_TREATED_AS_SUFFICIENT_TERMINAL_AUTHORITY" != acceptance.get("integration_rule"):
        failures.append("ACCEPTANCE_SCOPE_NOT_FAIL_CLOSED")

    requirement=e["requirement_graph"]
    rr=requirement.get("runner") or {}
    if requirement.get("status")!="INDEPENDENT_VERIFICATION_PASS__BRAIN_OWNED_NARROW_COMPONENT__ZERO_FAMILY_CREDIT":
        failures.append("REQUIREMENT_GRAPH_NOT_VERIFIED")
    if rr.get("exact_source_match") is not True or rr.get("conclusion")!="success":
        failures.append("REQUIREMENT_GRAPH_RUNNER_NOT_VERIFIED")
    behaviors=set(requirement.get("independently_verified_behaviors") or [])
    if "SEEDED_REQUIREMENT_MUTATION_SUITE_HAS_ZERO_SURVIVORS_ON_VERIFICATION_CORPUS" not in behaviors:
        failures.append("REQUIREMENT_MUTATION_COVERAGE_MISSING")

    stats=e["statistics"]
    if stats.get("status")!="FROZEN_BEFORE_RANK15_INSTRUCTION_EXPOSURE":
        failures.append("STATISTICAL_PLAN_NOT_FROZEN")
    if stats.get("benchmark_ref")!=EXPECTED_BENCHMARK_REF or float(stats.get("target_success_fraction",-1))!=EXPECTED_BAR:
        failures.append("STATISTICAL_TARGET_MISMATCH")
    if stats.get("replay") is not False or stats.get("cherry_picking") is not False:
        failures.append("STATISTICAL_PLAN_REPLAY_OR_CHERRYPICK")
    if (stats.get("sequential_promotion") or {}).get("no_promotion_from_point_estimate_alone") is not True:
        failures.append("STATISTICAL_PROMOTION_TOO_WEAK")

    donor=e["donor_protocol"]
    if donor.get("status")!="STAGE_A_PROTOCOL_AVAILABLE__NOT_DONOR_DELETION_EVIDENCE__ZERO_CREDIT":
        failures.append("DONOR_PROTOCOL_NOT_AVAILABLE")
    if donor.get("actual_donor_deletion_passed") is not False:
        failures.append("DONOR_PROTOCOL_CONFUSES_PLAN_WITH_EVIDENCE")
    mandatory=set(donor.get("mandatory_for_donor_derived_promotion") or [])
    required_protocol_bits={
        "ENUMERATE_ALL_UNAVOIDABLE_RUNTIME_DEPENDENCIES_INCLUDING_BASE_MODELS_SERVICES_LIBRARIES_AND_LEARNED_SUBSTRATES",
        "PHYSICALLY_REMOVE_OR_DENY_THE_DONOR_AS_TARGET_CAPABILITY_PROVIDER_WHERE_APPLICABLE",
        "RUN_THE_EXACT_BRAIN_ROUTE_IN_A_CLEAN_ROOM_WITH_DONOR_TARGET_CAPABILITY_ACCESS_UNAVAILABLE",
        "FAIL_PROMOTION_IF_TARGET_BEHAVIOR_DISAPPEARS_OR_AN_UNDISCLOSED_DEPENDENCY_IS_REQUIRED",
    }
    if not required_protocol_bits.issubset(mandatory):
        failures.append("DONOR_PROTOCOL_INCOMPLETE")

    return _result(failures)

def _result(failures: list[str]) -> dict[str, Any]:
    f=sorted(set(failures))
    return {
        "schema":"BRAIN_RANK15_STAGE_A_ADMISSION_VERDICT_V1",
        "pass":not f,
        "authorize_instruction_exposure":not f,
        "authorize_task_execution":False,
        "failed_predicates":f,
        "terminal_goal_achieved":False,
        "capability_credit_delta":0,
        "family_credit_delta":0,
    }
