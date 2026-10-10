"""Fail-closed reducer for Project Brain post-wave global ownership conditions."""
from __future__ import annotations
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_GLOBAL_OWNERSHIP_POSTCONDITIONS_V1"
TERMINAL_SHA="f4bec690aa0580cb532dbfd5985705bae8d153c9df31ffdf460b02f8b152e0f2"

def _fail(errors:list[str])->dict[str,Any]:
    return {
        "schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,
        "errors":sorted(set(errors)),
        "counters":{
            "donor_dependent_required_behaviors":None,
            "unresolved_verifier_mutations":None,
            "unresolved_composition_failures":None,
        },
        "final_donor_deletion_cleanroom_pass":False,
        "capability_credit_delta":0,"family_credit_delta":0,
    }

def evaluate_documents(
    terminal:Mapping[str,Any],
    reduction:Mapping[str,Any],
    dependency:Mapping[str,Any],
    cleanliness:Mapping[str,Any],
    composition:Mapping[str,Any],
    mutation:Mapping[str,Any],
    donor:Mapping[str,Any],
    closure:Mapping[str,Any],
)->dict[str,Any]:
    e:list[str]=[]

    if "ONE_SHOT_TERMINAL_WAVE_PASS" not in str(terminal.get("status","")):
        e.append("TERMINAL_WAVE_NOT_PASS")
    if terminal.get("terminal_results_observed") != 1:
        e.append("TERMINAL_RESULT_COUNT_NOT_ONE")
    if terminal.get("fresh_terminal_evidence_consumed") != 3352:
        e.append("TERMINAL_FRESH_EVIDENCE_COUNT_MISMATCH")
    art=terminal.get("artifact")
    if not isinstance(art,Mapping) or art.get("full_result_sha256") != TERMINAL_SHA:
        e.append("TERMINAL_FULL_RESULT_SHA_MISMATCH")
    direct=terminal.get("direct_terminal_population")
    if not isinstance(direct,Mapping) or direct.get("total_failures") != 0 or direct.get("total_passes") != direct.get("total_cases"):
        e.append("DIRECT_TERMINAL_POPULATION_NOT_ALL_PASS")
    parent=terminal.get("parent_terminal_population")
    if not isinstance(parent,Mapping) or parent.get("parent_reduction_status") != "PASS" or parent.get("multiplex_behavior_failures") != 0:
        e.append("PARENT_TERMINAL_POPULATION_NOT_PASS")
    guards=terminal.get("result_guards")
    if not isinstance(guards,Mapping) or guards.get("no_case_replacement") is not True or guards.get("no_tuning_replay") is not True or guards.get("result_to_runtime_feedback_during_wave") is not False:
        e.append("TERMINAL_RESULT_GUARDS_INVALID")

    if "12_OF_12_TERMINAL_CONTRACTS_PASS__19_OF_19_PROVISIONAL_FAMILY_ROWS_PASS" not in str(reduction.get("status","")):
        e.append("POSTWAVE_REDUCTION_NOT_PASS")
    cv=reduction.get("contract_verdict")
    fv=reduction.get("family_verdict")
    if not isinstance(cv,Mapping) or cv.get("valid") is not True or cv.get("contract_count") != 12 or cv.get("contract_pass_count") != 12 or cv.get("failed_contracts") != []:
        e.append("CONTRACT_VERDICT_NOT_12_OF_12")
    if not isinstance(fv,Mapping) or fv.get("valid") is not True or fv.get("family_count") != 19 or fv.get("family_pass_count") != 19 or fv.get("failed_families") != []:
        e.append("FAMILY_VERDICT_NOT_19_OF_19")
    if reduction.get("source_full_result_sha256") != TERMINAL_SHA:
        e.append("POSTWAVE_SOURCE_SHA_MISMATCH")

    pc=dependency.get("prewave_conclusion")
    if not isinstance(pc,Mapping) or pc.get("exact_runtime_dependencies_frozen") is not True or pc.get("no_known_opaque_target_capability_provider") is not True or pc.get("known_dependency_identity_complete_for_declared_operative_route") is not True:
        e.append("PREWAVE_DEPENDENCY_IDENTITY_INCOMPLETE")
    dp=dependency.get("dependency_policy")
    if not isinstance(dp,Mapping) or dp.get("paid_or_hosted_target_capability_provider") != "FORBIDDEN" or dp.get("opaque_external_target_capability_provider") != "NONE_DECLARED_IN_OPERATIVE_ROUTE":
        e.append("TARGET_PROVIDER_POLICY_NOT_CLEAN")

    pp=cleanliness.get("prewave_predicates")
    if not isinstance(pp,Mapping) or pp.get("brain_route_and_dependency_manifest_frozen") is not True or pp.get("no_known_opaque_target_capability_provider_in_operative_brain_route") is not True or pp.get("no_known_unresolved_controller_composition_defect_before_wave") is not True:
        e.append("PREWAVE_CLEANLINESS_NOT_PASS")

    if "INDEPENDENT_PASS" not in str(composition.get("status","")):
        e.append("COMPOSITION_RECEIPT_NOT_INDEPENDENT_PASS")
    conclusions=composition.get("conclusions")
    if not isinstance(conclusions,list) or "CURRENT_CONTROLLER_COMPOSITION_REGRESSION_SUITE_PASSES_ON_INDEPENDENT_PUBLIC_RUNNER" not in conclusions:
        e.append("CONTROLLER_COMPOSITION_NOT_CURRENT_PASS")

    if "INDEPENDENT_PASS" not in str(mutation.get("status","")):
        e.append("MUTATION_PREFLIGHT_NOT_INDEPENDENT_PASS")
    prop=str(mutation.get("verified_property",""))
    if "EVERY_PREDECLARED_SYNTHETIC_MUTATION_REJECTED" not in prop:
        e.append("VERIFIER_MUTATION_PREFLIGHT_INCOMPLETE")

    if "INDEPENDENT_PUBLIC_RUNNER_PASS__DONOR_DENIED_IDENTICAL_FROZEN_QUALIFICATION__BEHAVIOR_PRESERVED" not in str(donor.get("status","")):
        e.append("DONOR_CLEANROOM_NOT_PASS")
    if donor.get("behavior_preserved") is not True or donor.get("byte_identical_terminal_result") is not True or donor.get("undeclared_dependency_count") != 0:
        e.append("DONOR_CLEANROOM_SEMANTICS_INVALID")
    pre=donor.get("predeletion_result"); post=donor.get("postdeletion_result")
    if not isinstance(pre,Mapping) or not isinstance(post,Mapping) or pre.get("full_result_sha256") != TERMINAL_SHA or post.get("full_result_sha256") != TERMINAL_SHA:
        e.append("DONOR_CLEANROOM_RESULT_SHA_MISMATCH")

    counters=closure.get("counters")
    preds=closure.get("terminal_predicates")
    if closure.get("verified_closed_family_count") != 19 or closure.get("open_family_count") != 0:
        e.append("CLOSURE_FAMILY_ACCOUNTING_NOT_19_OF_19")
    if not isinstance(counters,Mapping) or counters.get("uncontracted_required_behaviors") != 0 or counters.get("unproved_required_behaviors") != 0 or counters.get("contaminated_promotion_evidence") != 0 or counters.get("resource_or_authority_violations") != 0:
        e.append("ALREADY_CLOSED_GLOBAL_COUNTER_REGRESSION")
    if not isinstance(preds,Mapping) or preds.get("all_frozen_opus_acceptance_predicates_pass") is not True:
        e.append("OPUS_ACCEPTANCE_PREDICATES_NOT_PASS")

    if e:
        return _fail(e)

    return {
        "schema":SCHEMA,
        "status":"PASS__GLOBAL_OWNERSHIP_POSTCONDITIONS_REDUCED_TO_ZERO",
        "pass":True,
        "errors":[],
        "counters":{
            "donor_dependent_required_behaviors":0,
            "unresolved_verifier_mutations":0,
            "unresolved_composition_failures":0,
        },
        "terminal_predicates":{
            "donor_dependent_required_behaviors_zero":True,
            "unresolved_verifier_mutations_zero":True,
            "unresolved_composition_failures_zero":True,
            "final_donor_deletion_cleanroom_pass":True,
        },
        "basis":{
            "donor":"DONOR_DENIED_BYTE_IDENTICAL_FROZEN_QUALIFICATION_AND_ZERO_UNDECLARED_DEPENDENCIES",
            "verifier":"FROZEN_PACKAGE_AND_MUTATION_PREFLIGHT_PLUS_IMMUTABLE_POSTWAVE_REDUCTION",
            "composition":"PREWAVE_CURRENT_CONTROLLER_COMPOSITION_PASS_PLUS_TERMINAL_PARENT_AND_12_CONTRACT_PASS",
        },
        "capability_credit_delta":0,
        "family_credit_delta":0,
        "rule":"POSTWAVE_OWNERSHIP_ONLY__NO_NEW_CAPABILITY_CREDIT",
    }
