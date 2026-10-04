from pathlib import Path
import shutil
import subprocess

import pytest

from canonical.runtime.shadow_write_only_result_escrow_v1 import (
    CASE_COUNT,
    PLAINTEXT_BYTES,
    ResultEscrowError,
    encode_score_vector,
    escrow_object_name,
    public_receipt_fingerprint,
    seal_score_vector,
)
from canonical.runtime.shadow_write_only_result_release_v1 import release_score_vector


LEASE = "ab" * 32


def rows_all(passed: bool):
    return [
        {"checker_count": 5, "passed_mask": 31 if passed else 0}
        for _ in range(CASE_COUNT)
    ]


def test_score_vector_geometry_is_result_independent():
    a = encode_score_vector(rows_all(True), LEASE, padding=b"x" * 64)
    b = encode_score_vector(rows_all(False), LEASE, padding=b"y" * 64)
    assert len(a) == len(b) == PLAINTEXT_BYTES
    assert a != b


def test_object_name_depends_only_on_lease():
    assert escrow_object_name(LEASE) == f"livebench-result-{LEASE}.cms"


def test_invalid_result_rows_fail_closed_before_publication():
    with pytest.raises(ResultEscrowError):
        encode_score_vector([{"checker_count": 1, "passed_mask": 1}], LEASE)


@pytest.mark.skipif(shutil.which("openssl") is None, reason="openssl required")
def test_public_surface_is_identical_for_opposite_results(tmp_path: Path):
    key = tmp_path / "key.pem"
    cert = tmp_path / "cert.pem"
    subprocess.run([
        "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
        "-keyout", str(key), "-out", str(cert), "-subj", "/CN=pb-test", "-days", "1",
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    a_dir = tmp_path / "a"; b_dir = tmp_path / "b"
    ra = seal_score_vector(rows=rows_all(True), lease_digest_sha256=LEASE, recipient_cert_path=cert, sink_dir=a_dir)
    rb = seal_score_vector(rows=rows_all(False), lease_digest_sha256=LEASE, recipient_cert_path=cert, sink_dir=b_dir)

    assert ra == rb
    assert public_receipt_fingerprint(ra) == public_receipt_fingerprint(rb)
    assert ra["result_derived_public_field_count"] == 0
    assert ra["result_score_visible"] is False

    ca = (a_dir / ra["escrow_object_name"]).read_bytes()
    cb = (b_dir / rb["escrow_object_name"]).read_bytes()
    assert len(ca) == len(cb)
    assert ca != cb


@pytest.mark.skipif(shutil.which("openssl") is None, reason="openssl required")
def test_release_requires_private_key_and_recomputes_exact_score(tmp_path: Path):
    key = tmp_path / "key.pem"
    cert = tmp_path / "cert.pem"
    subprocess.run([
        "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
        "-keyout", str(key), "-out", str(cert), "-subj", "/CN=pb-test", "-days", "1",
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    sink = tmp_path / "sink"
    receipt = seal_score_vector(rows=rows_all(True), lease_digest_sha256=LEASE, recipient_cert_path=cert, sink_dir=sink)
    cipher = sink / receipt["escrow_object_name"]

    with pytest.raises(ResultEscrowError, match="RELEASE_PRIVATE_KEY_REQUIRED"):
        release_score_vector(
            ciphertext_path=cipher,
            recipient_cert_path=cert,
            private_key_path=tmp_path / "missing.pem",
            expected_lease_digest_sha256=LEASE,
        )

    released = release_score_vector(
        ciphertext_path=cipher,
        recipient_cert_path=cert,
        private_key_path=key,
        expected_lease_digest_sha256=LEASE,
    )
    assert released["score_percent"] == 100.0
    assert released["target_met"] is True
    assert released["full_score_cases"] == 200


@pytest.mark.skipif(shutil.which("openssl") is None, reason="openssl required")
def test_atomic_escrow_object_cannot_be_replaced(tmp_path: Path):
    key = tmp_path / "key.pem"
    cert = tmp_path / "cert.pem"
    subprocess.run([
        "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
        "-keyout", str(key), "-out", str(cert), "-subj", "/CN=pb-test", "-days", "1",
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    sink = tmp_path / "sink"
    seal_score_vector(rows=rows_all(True), lease_digest_sha256=LEASE, recipient_cert_path=cert, sink_dir=sink)
    with pytest.raises(ResultEscrowError, match="ESCROW_OBJECT_ALREADY_EXISTS"):
        seal_score_vector(rows=rows_all(False), lease_digest_sha256=LEASE, recipient_cert_path=cert, sink_dir=sink)
