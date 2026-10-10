from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from execution_guard.logical_attempt_identity_v2 import logical_attempt_id

ROOT = Path(__file__).resolve().parents[2]
CLAIM = ROOT / "canonical/governance/TB_SCIENCE_RANK20_LOGICAL_ATTEMPT_CLAIM_BINDING_20261010_V1.json"
ADMISSION = ROOT / "canonical/governance/TB_SCIENCE_RANK20_CAPABILITY_FIRST_CHECKPOINT_ADMISSION_20261010_V1.json"
ADMISSION_VERIFY = ROOT / "canonical/verification/TB_SCIENCE_RANK20_CAPABILITY_FIRST_ADMISSION_INDEPENDENT_VERIFICATION_20261010_V1.json"
MANIFEST = ROOT / "canonical/governance/TB_SCIENCE_TERMINAL_EXECUTION_MANIFEST_V1.json"
LEDGER = ROOT / "canonical/governance/TB_SCIENCE_CURRENT_SLOT_LEDGER_RECONCILIATION_20261010_V41.json"
IDENTITY = ROOT / "execution_guard/logical_attempt_identity_v2.py"
AGENT = ROOT / "canonical/runtime/harbor_science_agent_v13.py"
AGENT_VERIFY = ROOT / "canonical/verification/AGENT_V13_IDENTITY_V2_REPAIR_VERIFY_20261010_V1.json"

SCHEMA = "PROJECT_BRAIN_TB_SCIENCE_RANK20_PRECLAIM_BINDING_VERIFY_V1"
EXPECTED_SLOT = "terminal-bench-science/hysteretic-aquifer-control::trial-0"
EXPECTED_DIGEST = "sha256:681df0c3b2ada03a933ac4d2e11f07983676f87a9f26b61e416987904b880289"


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()


def _git_blob(path: Path) -> str:
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON_OBJECT_REQUIRED:" + str(path))
    return value


def verify(root: Path = ROOT) -> dict[str, Any]:
    del root
    errors: list[str] = []
    claim = _read(CLAIM)
    admission = _read(ADMISSION)
    admission_verify = _read(ADMISSION_VERIFY)
    manifest = _read(MANIFEST)

    expected_blobs = {
        "rank19_ledger_v41_blob": _git_blob(LEDGER),
        "capability_first_checkpoint_admission_blob": _git_blob(ADMISSION),
        "capability_first_admission_verification_blob": _git_blob(ADMISSION_VERIFY),
        "frozen_manifest_blob": _git_blob(MANIFEST),
        "identity_v2_blob": _git_blob(IDENTITY),
        "agent_v13_identity_repair_verification_blob": _git_blob(AGENT_VERIFY),
        "agent_v13_blob": _git_blob(AGENT),
    }
    for field, actual in expected_blobs.items():
        if claim.get(field) != actual:
            errors.append(field.upper() + "_MISMATCH")

    if claim.get("slot_id") != EXPECTED_SLOT:
        errors.append("CLAIM_SLOT_MISMATCH")
    if claim.get("task_digest") != EXPECTED_DIGEST:
        errors.append("CLAIM_TASK_DIGEST_MISMATCH")

    slot = admission.get("slot")
    if not isinstance(slot, Mapping):
        errors.append("ADMISSION_SLOT_MISSING")
    else:
        if slot.get("slot_id") != EXPECTED_SLOT:
            errors.append("ADMISSION_SLOT_MISMATCH")
        if slot.get("task_digest") != EXPECTED_DIGEST:
            errors.append("ADMISSION_DIGEST_MISMATCH")
        if slot.get("task_content_read") is not False:
            errors.append("ADMISSION_TASK_CONTENT_ALREADY_READ")

    for field in (
        "execution_claim_authority",
        "execution_authority",
        "promotion_authority",
    ):
        if admission.get(field) is not False:
            errors.append("ADMISSION_" + field.upper() + "_MUST_BE_FALSE")
    if admission.get("task_read") is not False:
        errors.append("ADMISSION_TASK_READ_MUST_BE_FALSE")
    if admission.get("task_started") is not False:
        errors.append("ADMISSION_TASK_STARTED_MUST_BE_FALSE")
    if admission.get("benchmark_trials_consumed") != 0:
        errors.append("ADMISSION_TRIALS_MUST_BE_ZERO")
    if admission_verify.get("status") != (
        "PASS__RANK20_UNEXPOSED_PRECLAIM_CAPABILITY_FIRST_ADMISSION__ZERO_EXECUTION_CREDIT"
    ):
        errors.append("ADMISSION_VERIFICATION_NOT_CURRENT_PASS")

    rows = manifest.get("slots")
    if not isinstance(rows, list):
        rows = manifest.get("manifest")
    if not isinstance(rows, list):
        errors.append("MANIFEST_SLOT_LIST_MISSING")
        rows = []
    matches = [
        row for row in rows
        if isinstance(row, Mapping)
        and row.get("slot_id") == EXPECTED_SLOT
        and row.get("task_digest") == EXPECTED_DIGEST
    ]
    if len(matches) != 1:
        errors.append("MANIFEST_UNIQUE_RANK20_ROW_NOT_PROVED")

    forbidden_claim_fields = {
        "task_content",
        "task_prompt",
        "execution_authority",
        "activation_authority",
        "task_read_authority",
        "reward",
        "result",
    }
    present = sorted(forbidden_claim_fields.intersection(claim))
    if present:
        errors.append("PRECLAIM_FORBIDDEN_FIELDS:" + ",".join(present))

    claim_digest = "sha256:" + _canonical_sha256(claim)
    attempt = logical_attempt_id(
        slot_id=EXPECTED_SLOT,
        task_digest=EXPECTED_DIGEST,
        execution_claim_binding_digest=claim_digest,
    )
    return {
        "schema": SCHEMA,
        "status": "PASS__RANK20_PRECLAIM_BOUND__ZERO_EXPOSURE" if not errors else "FAIL_CLOSED__RANK20_PRECLAIM_INVALID",
        "pass": not errors,
        "errors": errors,
        "claim_git_blob_sha": _git_blob(CLAIM),
        "execution_claim_binding_digest": claim_digest,
        "logical_attempt_id_v2": attempt,
        "task_content_read": False,
        "task_started": False,
        "benchmark_trials_consumed": 0,
        "execution_authority": False,
        "activation_authority": False,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "terminal_credit_delta": 0,
    }


if __name__ == "__main__":
    print(json.dumps(verify(), sort_keys=True))
