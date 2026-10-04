from unittest.mock import Mock

from canonical.runtime import unknown_domain_direct_hidden_generator_v1 as g1
from canonical.runtime import unknown_domain_direct_hidden_generator_v5 as g5


class HostileStr(str):
    def strip(self, *args, **kwargs):
        raise RuntimeError("INSTANCE_STRIP_MUST_NOT_RUN")

    def encode(self, *args, **kwargs):
        raise RuntimeError("INSTANCE_ENCODE_MUST_NOT_RUN")


class HostileBytes(bytes):
    def __bytes__(self):
        raise RuntimeError("INSTANCE_BYTES_MUST_NOT_RUN")

    def __len__(self):
        raise RuntimeError("INSTANCE_LEN_MUST_NOT_RUN")

    def __getitem__(self, *args, **kwargs):
        raise RuntimeError("INSTANCE_GETITEM_MUST_NOT_RUN")


def test_actual_type_hierarchy_accepts_real_subclasses_and_bypasses_overrides():
    beacon = HostileStr("A" * 16 + "\ud800")
    secret_text = HostileStr("S" * 31 + "\udfff")

    canonical = g5._canonical_beacon(beacon)
    assert type(canonical) is str
    assert canonical.isascii()

    secret = g5._secret_bytes_total(secret_text)
    assert type(secret) is bytes
    assert len(secret) >= 32

    secret_bytes = HostileBytes(b"B" * 32)
    materialized = g5._secret_bytes_total(secret_bytes)
    assert type(materialized) is bytes
    assert materialized == b"B" * 32


def test_actual_type_hierarchy_rejects_instance_class_reporting_proxies():
    fake_str = Mock(spec=str)
    fake_bytes = Mock(spec=bytes)

    assert isinstance(fake_str, str) is True
    assert isinstance(fake_bytes, bytes) is True
    assert g5._genuine_str(fake_str) is False
    assert g5._genuine_bytes(fake_bytes) is False

    try:
        g5._canonical_beacon(fake_str)
    except g1.UnknownDomainGeneratorError as exc:
        assert str(exc) == "POST_FREEZE_BEACON_INVALID"
    else:
        raise AssertionError("NON_HIERARCHY_STR_PROXY_MUST_BE_REJECTED")

    try:
        g5._secret_bytes_total(fake_bytes)
    except g1.UnknownDomainGeneratorError as exc:
        assert str(exc) == "EVALUATOR_SECRET_INVALID"
    else:
        raise AssertionError("NON_HIERARCHY_BYTES_PROXY_MUST_BE_REJECTED")
