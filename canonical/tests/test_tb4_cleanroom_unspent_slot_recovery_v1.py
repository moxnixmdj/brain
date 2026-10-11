from canonical.runtime.tb4_cleanroom_unspent_slot_recovery_v1 import evaluate


def h(ch, n):
    return ch * n


def good():
    return {
        "frozen_release_commit": "452bf305c6daa62fc59061d22133a7cbc7c1572e",
        "task": "cad-model",
        "task_tree_sha": "e0d9d5571c902b9cd810f37e53d4a3cae1db05f3",
        "preverifier_roots": {
            "brain_commit_sha": "2b02287599d6878952a4a355fd05c4c6f219a34e",
            "runner_commit_sha": "53be3a64392ff8c184c8d7eb8bb1b4008560fcfe",
            "predates_first_verifier_exposure": True,
            "same_configured_route_as_original": True,
            "independently_verified": True,
            "verification_receipt_sha256": h("a",64),
        },
        "actor_cognition_isolation": {
            "mode": "DETERMINISTIC_BRAIN_ACTOR",
            "postverifier_user_or_chat_state_available": False,
            "task_specific_postresult_memory_available": False,
            "context_constructed_only_from_preverifier_root_and_current_trial_surface": True,
            "independently_verified": True,
            "verification_receipt_sha256": h("d",64),
            "actor_program_sha256": h("e",64),
            "all_trial_relevant_randomness_disabled_or_content_addressed": True,
        },
        "historical_consumption": {
            "consumed_trial_indices": [1],
            "independently_verified": True,
            "verification_receipt_sha256": h("b",64),
        },
        "requested_recovery_trial_indices": [2,3,4,5],
        "cleanroom_isolation": {
            "fresh_environment_from_preverifier_roots": True,
            "current_brain_tree_unavailable": True,
            "postresult_artifact_store_unavailable": True,
            "historical_verifier_outputs_unavailable": True,
            "hidden_verifier_unavailable_during_actor_phase": True,
            "actor_write_closed_before_verifier_phase": True,
            "cross_recovered_trial_result_propagation_disabled": True,
            "independently_verified": True,
            "verification_receipt_sha256": h("c",64),
        },
        "recovery_trials": [
            {
                "trial_index": i,
                "attempt_id": f"cad-model-cleanroom-{i}",
                "starts_from_exact_preverifier_roots": True,
                "postresult_information_available_to_actor": False,
                "hidden_verifier_available_to_actor": False,
                "configuration_mutable_from_other_trial_results": False,
            }
            for i in [2,3,4,5]
        ],
    }


def test_recovers_only_capacity():
    out=evaluate(good())
    assert out["pass"]
    assert out["recovered_creditable_slots"]==4
    assert out["success_credit_delta"]==0
    assert out["requires_separate_official_verifier_receipt_per_recovered_slot"] is True


def test_cannot_recover_consumed_slot():
    x=good()
    x["requested_recovery_trial_indices"]=[1,2,3,4,5]
    x["recovery_trials"]=[
        {
            "trial_index": i,
            "attempt_id": f"x-{i}",
            "starts_from_exact_preverifier_roots": True,
            "postresult_information_available_to_actor": False,
            "hidden_verifier_available_to_actor": False,
            "configuration_mutable_from_other_trial_results": False,
        } for i in [1,2,3,4,5]
    ]
    assert evaluate(x)["reason"]=="RECOVERY_OVERLAPS_CONSUMED_SLOT"


def test_postresult_access_fails_closed():
    x=good()
    x["cleanroom_isolation"]["postresult_artifact_store_unavailable"]=False
    assert evaluate(x)["pass"] is False


def test_verifier_exposure_fails_closed():
    x=good()
    x["recovery_trials"][0]["hidden_verifier_available_to_actor"]=True
    assert evaluate(x)["pass"] is False


def test_cross_trial_adaptation_fails_closed():
    x=good()
    x["recovery_trials"][1]["configuration_mutable_from_other_trial_results"]=True
    assert evaluate(x)["pass"] is False


def test_unverified_roots_fail_closed():
    x=good()
    x["preverifier_roots"]["independently_verified"]=False
    assert evaluate(x)["pass"] is False


def test_postverifier_cognitive_state_fails_closed():
    x=good()
    x["actor_cognition_isolation"]["postverifier_user_or_chat_state_available"]=True
    assert evaluate(x)["pass"] is False


def test_external_actor_requires_stateless_pinned_session():
    x=good()
    x["actor_cognition_isolation"]={
        "mode":"STATELESS_PINNED_EXTERNAL_COGNITION",
        "postverifier_user_or_chat_state_available":False,
        "task_specific_postresult_memory_available":False,
        "context_constructed_only_from_preverifier_root_and_current_trial_surface":True,
        "independently_verified":True,
        "verification_receipt_sha256":h("f",64),
        "model_id":"MODEL-X",
        "model_configuration_id":"CONFIG-X",
        "provider_conversation_memory_disabled":False,
        "fresh_session_per_trial":True,
    }
    assert evaluate(x)["pass"] is False
