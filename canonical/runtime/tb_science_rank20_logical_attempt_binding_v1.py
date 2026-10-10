from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from execution_guard.logical_attempt_identity_v2 import logical_attempt_id as derive_logical_attempt_id

ROOT = Path(__file__).resolve().parents[2]
BINDING_REL = "canonical/governance/TB_SCIENCE_RANK20_LOGICAL_ATTEMPT_CLAIM_BINDING_20261010_V1.json"
BINDING_PATH = ROOT / BINDING_REL
SLOT_ID = "terminal-bench-science/hysteretic-aquifer-control::trial-0"
TASK_DIGEST = "sha256:681df0c3b2ada03a933ac4d2e11f07983676f87a9f26b61e416987904b880289"
CLAIM_EPOCH_ID = "RANK20_IDENTITY_V2_VALIDATION_20261010_V1"
EXPECTED_GIT_BLOB_SHA = "564026d24111cecf763c48b118191f1ea72c2bc5"
EXPECTED_CANONICAL_SHA256 = "0d61d00d8b5dfd829397c801428f2c287d05deeb0fab318e6a0377b10d851b63"
EXECUTION_CLAIM_BINDING_DIGEST = "sha256:" + EXPECTED_CANONICAL_SHA256
EXPECTED_LOGICAL_ATTEMPT_ID = "205b4f35a594b98d3d307ff077e510dbe94ba9e8ceb5c41b869af50042a99e8c"

INTERNAL_BINDINGS = {
    "capability_first_admission": (
        "canonical/governance/TB_SCIENCE_RANK20_CAPABILITY_FIRST_CHECKPOINT_ADMISSION_20261010_V1.json",
        "b03861813f9b9a730659e6e0b6e7301a45061b04",
    ),
    "capability_first_admission_verification": (
        "canonical/verification/TB_SCIENCE_RANK20_CAPABILITY_FIRST_ADMISSION_INDEPENDENT_VERIFICATION_20261010_V1.json",
        "d12c7c1f9e1259eaf3950689556fd0e6a37ba705",
    ),
    "frozen_manifest": (
        "canonical/governance/TB_SCIENCE_TERMINAL_EXECUTION_MANIFEST_V1.json",
        "6dfa880b1f68881531afbba6ca211681801fd19b",
    ),
    "rank19_result": (
        "canonical/verification/TB_SCIENCE_RANK19_RESULT_TRUTH_20261010_V1.json",
        "66b02049cc3d142cefe8c6bcc966fdcc4c5cb08b",
    ),
    "rank19_diagnosis": (
        "canonical/governance/TB_SCIENCE_RANK19_IDENTITY_SKEW_DIAGNOSIS_20261010_V1.json",
        "e4ce666de016716328ac577b4858a126f41126da",
    ),
    "agent_v13_identity_v2_repair_verification": (
        "canonical/verification/AGENT_V13_IDENTITY_V2_REPAIR_VERIFY_20261010_V1.json",
        "ec982a8cde737669d42abfb62a9f3cbdf0752434",
    ),
    "repaired_agent_v13": (
        "canonical/runtime/harbor_science_agent_v13.py",
        "470bfe079aeffaa07a3b92975b4edea17c9a20e1",
    ),
    "identity_v2": (
        "execution_guard/logical_attempt_identity_v2.py",
        "67ff638459af1bb50a094e9479fb4aa5e2a3de1c",
    ),
}


class Rank20ClaimBindingError(RuntimeError):
    pass


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _git_blob_sha(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _file_blob(path: Path) -> str:
    return _git_blob_sha(path.read_bytes())


def load_claim_binding() -> dict[str, Any]:
    raw = BINDING_PATH.read_bytes()
    if _git_blob_sha(raw) != EXPECTED_GIT_BLOB_SHA:
        raise Rank20ClaimBindingError("CLAIM_BINDING_GIT_BLOB_MISMATCH")
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise Rank20ClaimBindingError("CLAIM_BINDING_OBJECT_REQUIRED")

    slot = value.get("slot") or {}
    target = value.get("execution_target") or {}
    state = value.get("preclaim_state") or {}
    checks = {
        "schema": value.get("schema") == "PROJECT_BRAIN_TB_SCIENCE_RANK20_LOGICAL_ATTEMPT_CLAIM_BINDING_V1",
        "claim_epoch_id": value.get("claim_epoch_id") == CLAIM_EPOCH_ID,
        "purpose": value.get("purpose") == "FRESH_UNEXPOSED_LIVE_VALIDATION_OF_GENERIC_EXECUTION_TRANSPORT_IDENTITY_V2_REPAIR",
        "slot_id": slot.get("slot_id") == SLOT_ID,
        "task_digest": slot.get("task_digest") == TASK_DIGEST,
        "ledger_schedule_rank": slot.get("ledger_schedule_rank") == 20,
        "frozen_manifest_schedule_order": slot.get("frozen_manifest_schedule_order") == 19,
        "task_rank": slot.get("task_rank") == 19,
        "execution_repository": target.get("repository") == "moxnixmdj/verification-capsule-runner",
        "execution_base": target.get("execution_base") == "terminal-execution-v1",
        "execution_branch": target.get("execution_branch") == "execute/tb-science-rank20-20261010-v1",
        "activation_filename": target.get("activation_filename") == "ACTIVATE_RANK20_V1_PR.json",
        "task_read": state.get("task_read") is False,
        "task_started": state.get("task_started") is False,
        "durable_start": state.get("durable_start_cas_acquired") is False,
        "trials": state.get("benchmark_trials_consumed") == 0,
        "rank19_replay": state.get("rank19_retry_replay_replacement_authority") is False,
    }
    failed = [k for k, ok in checks.items() if not ok]
    if failed:
        raise Rank20ClaimBindingError("CLAIM_BINDING_FIELD_MISMATCH:" + ",".join(failed))

    bound = value.get("brain_bindings")
    if not isinstance(bound, dict):
        raise Rank20ClaimBindingError("BRAIN_BINDINGS_REQUIRED")
    for key, (path, expected_sha) in INTERNAL_BINDINGS.items():
        row = bound.get(key)
        if not isinstance(row, dict):
            raise Rank20ClaimBindingError("BRAIN_BINDING_MISSING:" + key)
        if row.get("path") != path or row.get("git_blob_sha") != expected_sha:
            raise Rank20ClaimBindingError("BRAIN_BINDING_DECLARATION_DRIFT:" + key)
        actual = _file_blob(ROOT / path)
        if actual != expected_sha:
            raise Rank20ClaimBindingError("BRAIN_BINDING_BYTE_DRIFT:" + key + ":" + actual)

    admission = json.loads((ROOT / INTERNAL_BINDINGS["capability_first_admission"][0]).read_text(encoding="utf-8"))
    if admission.get("authorized") is not True or admission.get("execution_authority") is not False:
        raise Rank20ClaimBindingError("ADMISSION_AUTHORITY_BOUNDARY_DRIFT")
    ident = admission.get("logical_attempt_identity") or {}
    if ident.get("minted") is not False or ident.get("execution_claim_binding_digest") is not None or ident.get("logical_attempt_id") is not None:
        raise Rank20ClaimBindingError("ADMISSION_PRECLAIM_IDENTITY_BOUNDARY_DRIFT")

    verification = json.loads((ROOT / INTERNAL_BINDINGS["capability_first_admission_verification"][0]).read_text(encoding="utf-8"))
    if not str(verification.get("status") or "").startswith("PASS__RANK20_UNEXPOSED_PRECLAIM_CAPABILITY_FIRST_ADMISSION"):
        raise Rank20ClaimBindingError("ADMISSION_VERIFICATION_STATUS_DRIFT")

    digest = hashlib.sha256(_canonical_bytes(value)).hexdigest()
    if digest != EXPECTED_CANONICAL_SHA256:
        raise Rank20ClaimBindingError("CLAIM_BINDING_CANONICAL_SHA256_MISMATCH:" + digest)
    return value


def execution_claim_binding_digest() -> str:
    load_claim_binding()
    return EXECUTION_CLAIM_BINDING_DIGEST


def logical_attempt_id() -> str:
    digest = execution_claim_binding_digest()
    actual = derive_logical_attempt_id(
        slot_id=SLOT_ID,
        task_digest=TASK_DIGEST,
        execution_claim_binding_digest=digest,
    )
    if actual != EXPECTED_LOGICAL_ATTEMPT_ID:
        raise Rank20ClaimBindingError("LOGICAL_ATTEMPT_ID_DERIVATION_MISMATCH:" + actual)
    return actual


def verify() -> dict[str, Any]:
    try:
        binding = load_claim_binding()
        actual_id = logical_attempt_id()
        return {
            "schema": "PROJECT_BRAIN_TB_SCIENCE_RANK20_CLAIM_BINDING_VERIFIER_V1",
            "status": "PASS__RANK20_CLAIM_BINDING_CONTENT_ADDRESSED__V2_LOGICAL_ATTEMPT_DERIVED__ZERO_EXPOSURE",
            "pass": True,
            "errors": [],
            "claim_epoch_id": binding["claim_epoch_id"],
            "execution_claim_binding_digest": EXECUTION_CLAIM_BINDING_DIGEST,
            "logical_attempt_id": actual_id,
            "task_read": False,
            "task_started": False,
            "benchmark_trials_consumed": 0,
            "execution_authority": False,
            "terminal_credit_delta": 0,
        }
    except Exception as exc:
        return {
            "schema": "PROJECT_BRAIN_TB_SCIENCE_RANK20_CLAIM_BINDING_VERIFIER_V1",
            "status": "FAIL_CLOSED",
            "pass": False,
            "errors": [type(exc).__name__ + ":" + str(exc)],
            "task_read": False,
            "task_started": False,
            "benchmark_trials_consumed": 0,
            "execution_authority": False,
            "terminal_credit_delta": 0,
        }


if __name__ == "__main__":
    out = verify()
    print(json.dumps(out, indent=2, sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)
