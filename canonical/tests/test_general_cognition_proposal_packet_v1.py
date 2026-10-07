from canonical.runtime.general_cognition_proposal_packet_v1 import (
    make_request,
    make_packet,
    unwrap,
)


def request():
    return make_request(
        task_contract_sha256="1" * 64,
        capability_id="solve",
        action_contract_sha256="2" * 64,
        verifier_id="TYPED_ACCEPTANCE_PROGRAM_V1",
        proposal_context={"fields": ["x"]},
    )


def test_round_trip_binds_untrusted_proposal_to_exact_request():
    r = request()
    p = make_packet(r, source_id="replaceable-substrate", proposal={"candidate_values": {"x": 2}})
    out = unwrap(p, request=r)
    assert out["proposal"] == {"candidate_values": {"x": 2}}
    assert out["proposal_authority"] is False


def test_cross_task_replay_is_rejected():
    r1 = request()
    p = make_packet(r1, source_id="replaceable-substrate", proposal={"candidate_values": {"x": 2}})
    r2 = make_request(
        task_contract_sha256="3" * 64,
        capability_id="solve",
        action_contract_sha256="2" * 64,
        verifier_id="TYPED_ACCEPTANCE_PROGRAM_V1",
    )
    try:
        unwrap(p, request=r2)
    except Exception:
        pass
    else:
        raise AssertionError("cross-task proposal replay should fail")


def test_packet_tamper_is_rejected():
    r = request()
    p = make_packet(r, source_id="replaceable-substrate", proposal={"candidate_values": {"x": 2}})
    p["proposal"]["candidate_values"]["x"] = 3
    try:
        unwrap(p, request=r)
    except Exception:
        pass
    else:
        raise AssertionError("tampered proposal packet should fail")


def test_source_cannot_claim_authority():
    r = request()
    p = make_packet(r, source_id="replaceable-substrate", proposal={"candidate_values": {"x": 2}})
    p["proposal_authority"] = True
    try:
        unwrap(p, request=r)
    except Exception:
        pass
    else:
        raise AssertionError("proposal source may not claim authority")
