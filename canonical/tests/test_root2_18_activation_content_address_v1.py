from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ACTIVATION = ROOT / "canonical/governance/ROOT2_18_CURRENT_14_24_SCHEDULING_ACTIVATION_V1.json"


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def test_root2_18_activation_has_exact_content_addresses() -> None:
    activation = json.loads(ACTIVATION.read_text(encoding="utf-8"))

    subject = ROOT / activation["subject_path"]
    verification = ROOT / activation["verification_path"]

    assert activation["subject_git_blob_sha"] == git_blob_sha(subject)
    assert activation["verification_git_blob_sha"] == git_blob_sha(verification)
    assert "PENDING" not in activation["verification_git_blob_sha"]
    assert activation["scheduling_authority"] is True
    assert activation["execution_authority"] is False
    assert activation["promotion_authority"] is False
    assert activation["fresh_reality_authority"] is False
    assert activation["acceptance_credit_delta"] == 0
