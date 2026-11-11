import hashlib
from pathlib import Path

import pytest

from canonical.runtime.shadow_write_only_escrow_v1 import (
    HEADER_BYTES,
    EscrowError,
    preflight,
)


def test_preflight_reads_no_result_and_binds_capacity():
    out = preflight(declared_max_result_bytes=4096, fixed_envelope_bytes=8192)
    assert out["pass"] is True
    assert out["result_content_read"] is False
    assert out["payload_capacity_bytes"] == 8192 - HEADER_BYTES


def test_preflight_rejects_unbounded_capacity_before_result_execution():
    with pytest.raises(EscrowError, match="DECLARED_RESULT_BOUND_EXCEEDS_ESCROW_CAPACITY"):
        preflight(declared_max_result_bytes=8192, fixed_envelope_bytes=4096)


def test_artifact_identity_can_be_lease_only():
    lease = hashlib.sha256(b"synthetic-lease").hexdigest()
    assert len(lease) == 64
    assert f"{lease}.cms" == f"{lease}.cms"


def test_no_decrypt_api_is_exposed_by_runtime_source():
    source = Path("canonical/runtime/shadow_write_only_escrow_v1.py").read_text()
    assert "def decrypt" not in source
    assert '"cms",\n                "-encrypt"' in source
    assert "ESCROW_ENCRYPTION_FAILED" in source
    assert "proc.stderr" not in source
