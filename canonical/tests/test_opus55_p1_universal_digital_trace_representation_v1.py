from canonical.runtime.verify_opus55_p1_universal_digital_trace_representation_v1 import (
    decode_record,
    decode_trace,
    encode_record,
    encode_trace,
    verify,
)


def test_record_codec_is_unambiguous_on_adversarial_examples():
    cases = [
        [],
        [b""],
        [b"a"],
        [b"", b"a"],
        [b"a", b""],
        [b"\x00", b"\xff", b"ab"],
    ]
    enc = [encode_record(x) for x in cases]
    assert len(enc) == len(set(enc))
    assert [decode_record(x) for x in enc] == cases


def test_trace_codec_is_unambiguous_on_adversarial_examples():
    cases = [
        [],
        [[b""]],
        [[b"a"]],
        [[b"a"], [b"b", b""]],
        [[b"\x00", b"\xff"]],
    ]
    enc = [encode_trace(x) for x in cases]
    assert len(enc) == len(set(enc))
    assert [decode_trace(x) for x in enc] == cases


def test_live_tree_p1_candidate_is_fail_closed_and_zero_credit():
    out = verify()
    assert out["status"] == "PASS", out
    assert out["p1_candidate_mechanically_coherent"] is True
    assert out["p2_proved"] is False
    assert out["p3_proved"] is False
    assert out["terminal"] is False
    assert out["acceptance_credit_delta"] == 0
    assert out["execution_authority"] is False
    assert out["promotion_authority"] is False
    assert out["fresh_reality_authority"] is False
