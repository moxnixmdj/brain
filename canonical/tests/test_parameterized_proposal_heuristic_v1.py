import base64
import json

from canonical.runtime.universal_parameterized_skill_candidate_v1 import (
    induce_parameterized_candidate,
)
from canonical.runtime.parameterized_proposal_heuristic_v1 import activate, propose


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


def episode(eid, x):
    return {
        "episode_id": eid,
        "scope_id": "scope",
        "steps": [step({"candidate_values": {"x": x, "mode": "safe"}})],
        "verification_receipt": {
            "independent_verified": True,
            "exact_byte_bound": True,
            "conclusion": "success",
            "public_runner_provenance": {"repository": "moxnixmdj/verification-capsule-runner"},
        },
    }


def candidate():
    return induce_parameterized_candidate([episode("e1", 1), episode("e2", 2)])


def test_parameterized_candidate_can_activate_only_as_zero_authority_proposal_heuristic():
    h = activate(candidate())
    assert h["proposal_reuse_authorized"] is True
    assert h["execution_authority"] is False
    assert h["state_transition_authority"] is False
    assert h["behavior_preservation_proved"] is False


def test_instantiated_heuristic_proposal_requires_live_reverification():
    c = candidate()
    h = activate(c)
    sid = c["parameter_slots"][0]["slot_id"]
    out = propose(
        h,
        c,
        step_index=0,
        parameters={sid: 7},
        verifier_id="TYPED_ACCEPTANCE_PROGRAM_V1",
        action_contract_sha256="1" * 64,
    )
    assert out["proposal"]["candidate_values"]["x"] == 7
    assert out["proposal"]["candidate_values"]["mode"] == "safe"
    assert out["proposal_authority"] is False
    assert out["live_reverification_required"] is True


def test_action_contract_mismatch_blocks_heuristic_reuse():
    c = candidate()
    h = activate(c)
    sid = c["parameter_slots"][0]["slot_id"]
    try:
        propose(
            h,
            c,
            step_index=0,
            parameters={sid: 7},
            verifier_id="TYPED_ACCEPTANCE_PROGRAM_V1",
            action_contract_sha256="2" * 64,
        )
    except Exception:
        pass
    else:
        raise AssertionError("cross-action heuristic reuse must fail")


def test_verifier_mismatch_blocks_heuristic_reuse():
    c = candidate()
    h = activate(c)
    sid = c["parameter_slots"][0]["slot_id"]
    try:
        propose(
            h,
            c,
            step_index=0,
            parameters={sid: 7},
            verifier_id="EXACT_JSON_V1",
            action_contract_sha256="1" * 64,
        )
    except Exception:
        pass
    else:
        raise AssertionError("cross-verifier heuristic reuse must fail")
