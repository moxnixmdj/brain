import inspect
import pytest
from canonical.runtime.shadow_cryptographic_escrow_v1 import (
    DEFAULT_PADDED_PLAINTEXT_BYTES, EscrowError, _fixed_plaintext,
    output_name, recover_fixed_plaintext, write_encrypted_result
)

def test_output_name_is_lease_only():
    d="a"*64
    assert output_name(d)=="shadow-result-"+d+".cms"

def test_fixed_plaintext_hides_payload_length_at_container_layer():
    a=_fixed_plaintext(b"x",DEFAULT_PADDED_PLAINTEXT_BYTES)
    b=_fixed_plaintext(b"x"*10000,DEFAULT_PADDED_PLAINTEXT_BYTES)
    assert len(a)==len(b)==DEFAULT_PADDED_PLAINTEXT_BYTES
    assert recover_fixed_plaintext(a)==b"x"
    assert recover_fixed_plaintext(b)==b"x"*10000

def test_writer_api_has_no_private_key_parameter():
    params=set(inspect.signature(write_encrypted_result).parameters)
    assert all("private" not in p.lower() for p in params)

def test_noncanonical_padding_rejected():
    with pytest.raises(EscrowError,match="NONCANONICAL_PADDED_SIZE"):
        write_encrypted_result(
          payload=b"x",lease_digest_sha256="a"*64,
          recipient_cert_path="/missing",expected_recipient_cert_sha256="b"*64,
          escrow_dir="/tmp/escrow-test",padded_plaintext_bytes=1024
        )

def test_invalid_lease_rejected():
    with pytest.raises(EscrowError,match="INVALID_LEASE"):
        output_name("bad")
