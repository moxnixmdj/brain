from __future__ import annotations
import hashlib, pathlib, subprocess
import pytest

from canonical.runtime.shadow_crypto_escrow_v1 import (
    DEFAULT_PADDED_PLAINTEXT_BYTES,
    EscrowWriteFailure,
    output_filename,
    write_encrypted_result,
)

def keypair(tmp_path):
    key=tmp_path/"private.pem"
    cert=tmp_path/"recipient.crt"
    subprocess.run(["openssl","genpkey","-algorithm","RSA","-pkeyopt","rsa_keygen_bits:2048","-out",str(key)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    subprocess.run(["openssl","req","-new","-x509","-sha256","-key",str(key),"-subj","/CN=Brain Escrow Test","-days","1","-out",str(cert)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return key,cert

def decrypt(cipher,key,cert):
    p=subprocess.run(["openssl","cms","-decrypt","-binary","-inform","DER","-in",str(cipher),"-inkey",str(key),"-recip",str(cert)],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    n=int.from_bytes(p.stdout[:8],"big")
    return p.stdout[8:8+n],len(p.stdout)

def test_roundtrip_and_fixed_padding(tmp_path):
    key,cert=keypair(tmp_path)
    c=cert.read_bytes(); sha=hashlib.sha256(c).hexdigest()
    lease="a"*64
    r=write_encrypted_result(result_bytes=b'{"score":0.7}',recipient_certificate_pem=c,expected_certificate_sha256=sha,lease_digest_sha256=lease,output_dir=tmp_path/"out",padded_plaintext_bytes=4096)
    out=tmp_path/"out"/output_filename(lease)
    plain,total=decrypt(out,key,cert)
    assert plain==b'{"score":0.7}'
    assert total==4096
    assert r["plaintext_length_disclosed"] is False
    assert r["plaintext_sha256_disclosed"] is False
    assert r["score_or_result_signal_disclosed"] is False
    assert r["decryption_path_present_in_writer"] is False
    assert r["acceptance_credit_authorized"] is False

def test_ciphertext_size_hides_result_length(tmp_path):
    key,cert=keypair(tmp_path)
    c=cert.read_bytes(); sha=hashlib.sha256(c).hexdigest()
    r1=write_encrypted_result(result_bytes=b"x",recipient_certificate_pem=c,expected_certificate_sha256=sha,lease_digest_sha256="1"*64,output_dir=tmp_path/"a",padded_plaintext_bytes=4096)
    r2=write_encrypted_result(result_bytes=b"x"*1000,recipient_certificate_pem=c,expected_certificate_sha256=sha,lease_digest_sha256="2"*64,output_dir=tmp_path/"b",padded_plaintext_bytes=4096)
    assert r1["ciphertext_bytes"]==r2["ciphertext_bytes"]

def test_output_is_lease_derived_and_exclusive(tmp_path):
    key,cert=keypair(tmp_path)
    c=cert.read_bytes(); sha=hashlib.sha256(c).hexdigest(); lease="b"*64
    kwargs=dict(result_bytes=b"x",recipient_certificate_pem=c,expected_certificate_sha256=sha,lease_digest_sha256=lease,output_dir=tmp_path/"out",padded_plaintext_bytes=4096)
    write_encrypted_result(**kwargs)
    assert (tmp_path/"out"/(lease+".cms.der")).is_file()
    with pytest.raises(EscrowWriteFailure,match="ESCROW_RESULT_ALREADY_EXISTS"):
        write_encrypted_result(**kwargs)

def test_wrong_certificate_fails_closed(tmp_path):
    key,cert=keypair(tmp_path)
    with pytest.raises(EscrowWriteFailure,match="RECIPIENT_CERTIFICATE_SHA256_MISMATCH"):
        write_encrypted_result(result_bytes=b"x",recipient_certificate_pem=cert.read_bytes(),expected_certificate_sha256="0"*64,lease_digest_sha256="c"*64,output_dir=tmp_path/"out",padded_plaintext_bytes=4096)

def test_invalid_lease_and_oversize_fail_closed(tmp_path):
    key,cert=keypair(tmp_path)
    c=cert.read_bytes(); sha=hashlib.sha256(c).hexdigest()
    with pytest.raises(EscrowWriteFailure,match="INVALID_LEASE_DIGEST_SHA256"):
        write_encrypted_result(result_bytes=b"x",recipient_certificate_pem=c,expected_certificate_sha256=sha,lease_digest_sha256="bad",output_dir=tmp_path/"out",padded_plaintext_bytes=4096)
    with pytest.raises(EscrowWriteFailure,match="RESULT_EXCEEDS_FIXED_ESCROW_PAYLOAD"):
        write_encrypted_result(result_bytes=b"x"*4090,recipient_certificate_pem=c,expected_certificate_sha256=sha,lease_digest_sha256="d"*64,output_dir=tmp_path/"out2",padded_plaintext_bytes=4096)
