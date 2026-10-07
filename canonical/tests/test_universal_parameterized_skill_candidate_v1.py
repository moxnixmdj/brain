import base64
import json

from canonical.runtime.universal_parameterized_skill_candidate_v1 import (
    induce_parameterized_candidate,
    instantiate_candidate,
)


def step(proposal):
    encoded = base64.b64encode(
        json.dumps(proposal, sort_keys=True, separators=(",", ":")).encode()
    ).decode()
    return {
        "index": 0,
        "op": "solve",
        "inputs": [
            "VERIFIER::TYPED_ACCEPTANCE_PROGRAM_V1",
            "ACTION_CONTRACT_SHA256::" + "1" * 64,
            "ACCEPTED_PROPOSAL_BASE64::" + encoded,
        ],
        "outputs": ["ANSWER_VERIFIED"],
    }


def episode(eid, proposal):
    return {
        "episode_id": eid,
        "scope_id": "scope",
        "steps": [step(proposal)],
        "verification_receipt": {
            "independent_verified": True,
            "exact_byte_bound": True,
            "conclusion": "success",
            "public_runner_provenance": {
                "repository": "moxnixmdj/verification-capsule-runner",
            },
        },
    }


def test_varying_scalar_leaf_becomes_typed_slot_only():
    cand = induce_parameterized_candidate([
        episode("e1", {"candidate_values": {"x": 1, "mode": "safe"}}),
        episode("e2", {"candidate_values": {"x": 2, "mode": "safe"}}),
    ])
    assert cand["status"] == "PARAMETERIZED_SKILL_CANDIDATE_ONLY"
    assert cand["reuse_authorized"] is False
    assert len(cand["parameter_slots"]) == 1
    slot = cand["parameter_slots"][0]
    assert slot["json_type"] == "integer"
    assert slot["domain_proved"] is False
    template = cand["steps"][0]["proposal_template"]
    assert template["candidate_values"]["mode"] == "safe"
    assert set(template["candidate_values"]["x"]) == {"$slot"}


def test_structure_drift_is_rejected():
    try:
        induce_parameterized_candidate([
            episode("e1", {"candidate_values": {"x": 1}}),
            episode("e2", {"candidate_values": {"x": 2, "extra": 3}}),
        ])
    except Exception:
        pass
    else:
        raise AssertionError("proposal structure drift must not generalize")


def test_action_contract_drift_is_rejected():
    a = episode("e1", {"candidate_values": {"x": 1}})
    b = episode("e2", {"candidate_values": {"x": 2}})
    b["steps"][0]["inputs"][1] = "ACTION_CONTRACT_SHA256::" + "2" * 64
    try:
        induce_parameterized_candidate([a, b])
    except Exception:
        pass
    else:
        raise AssertionError("different action contracts must not generalize")


def test_parameter_type_drift_is_rejected():
    try:
        induce_parameterized_candidate([
            episode("e1", {"candidate_values": {"x": 1}}),
            episode("e2", {"candidate_values": {"x": "1"}}),
        ])
    except Exception:
        pass
    else:
        raise AssertionError("parameter type drift must not generalize")


def test_instantiation_is_candidate_only_and_type_checked():
    cand = induce_parameterized_candidate([
        episode("e1", {"candidate_values": {"x": 1}}),
        episode("e2", {"candidate_values": {"x": 2}}),
    ])
    sid = cand["parameter_slots"][0]["slot_id"]
    inst = instantiate_candidate(cand, {sid: 7})
    assert inst["steps"][0]["proposal"]["candidate_values"]["x"] == 7
    assert inst["execution_authority"] is False
    assert inst["reuse_authorized"] is False


def test_no_variation_uses_exact_skill_path_instead():
    try:
        induce_parameterized_candidate([
            episode("e1", {"candidate_values": {"x": 1}}),
            episode("e2", {"candidate_values": {"x": 1}}),
        ])
    except Exception as exc:
        assert "NO_PARAMETER_VARIATION" in str(exc)
    else:
        raise AssertionError("identical episodes should use exact skill induction")
