from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_TB4_SUCCESS_SLOT_RECEIPT_V1"
AGGREGATE_SCHEMA = "PROJECT_BRAIN_TB4_SUCCESS_SLOT_AGGREGATE_V1"
FROZEN_RELEASE_COMMIT = "452bf305c6daa62fc59061d22133a7cbc7c1572e"
CURRENT_REQUIRED_SUCCESSES = 219
TRIALS_PER_TASK = 5

SCOPE_PATH = (
    Path(__file__).resolve().parents[1]
    / "evidence"
    / "TB4_EXACT_66_TASK_TARGET_SCOPE_20261008_V1.json"
)
EXPECTED_SCOPE_BLOB = "cc18e607aa403906944deaf5097751fc3e1f1015"
EXPECTED_PROTOCOL_RECEIPT_BLOB = "b963c13eee7b58d97279fe249919d3c489b19cf8"
EXPECTED_ZERO_SPEND_RECEIPT_BLOB = "75afb4de1594a858b873ec28bbca453ae3c9f40d"


class TB4SuccessSlotError(ValueError):
    pass


@dataclass(frozen=True)
class SlotVerdict:
    accepted: bool
    reason: str
    success_slot_delta: int
    task: str | None = None
    trial_index: int | None = None
    attempt_id: str | None = None
    owner_sandbox_identity_required: bool = False
    acceptance_credit_delta: int = 0
    execution_authority: bool = False
    replay_authority: bool = False


def _hex(value: Any, length: int, name: str) -> str:
    if not isinstance(value, str) or len(value) != length or any(
        c not in "0123456789abcdef" for c in value
    ):
        raise TB4SuccessSlotError(name + "_INVALID")
    return value


def _nonempty(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TB4SuccessSlotError(name + "_MISSING")
    return value.strip()


def _scope_map(scope_doc: Mapping[str, Any]) -> dict[str, str]:
    if not isinstance(scope_doc, Mapping):
        raise TB4SuccessSlotError("SCOPE_DOC_INVALID")
    if scope_doc.get("schema") != "PROJECT_BRAIN_TB4_EXACT_66_TASK_TARGET_SCOPE_20261008_V1":
        raise TB4SuccessSlotError("SCOPE_SCHEMA_INVALID")
    if scope_doc.get("source", {}).get("release_commit") != FROZEN_RELEASE_COMMIT:
        raise TB4SuccessSlotError("SCOPE_RELEASE_MISMATCH")
    rows = scope_doc.get("enumeration", {}).get("tasks")
    if not isinstance(rows, list) or not rows:
        raise TB4SuccessSlotError("SCOPE_TASKS_INVALID")
    out: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise TB4SuccessSlotError("SCOPE_TASK_ROW_INVALID")
        task = _nonempty(row.get("task"), "SCOPE_TASK")
        tree = _hex(row.get("tree_sha"), 40, "SCOPE_TASK_TREE_SHA")
        if task in out:
            raise TB4SuccessSlotError("SCOPE_TASK_DUPLICATE:" + task)
        out[task] = tree
    if len(out) != 66:
        raise TB4SuccessSlotError("SCOPE_TASK_COUNT_NOT_66")
    return out


def load_current_scope() -> Mapping[str, Any]:
    return json.loads(SCOPE_PATH.read_text(encoding="utf-8"))


def _validate_bindings(receipt: Mapping[str, Any]) -> None:
    bindings = receipt.get("authority_bindings")
    if not isinstance(bindings, Mapping):
        raise TB4SuccessSlotError("AUTHORITY_BINDINGS_MISSING")
    if bindings.get("scope_manifest_git_blob_sha") != EXPECTED_SCOPE_BLOB:
        raise TB4SuccessSlotError("SCOPE_MANIFEST_BINDING_MISMATCH")
    if bindings.get("protocol_receipt_git_blob_sha") != EXPECTED_PROTOCOL_RECEIPT_BLOB:
        raise TB4SuccessSlotError("PROTOCOL_RECEIPT_BINDING_MISMATCH")
    if bindings.get("zero_spend_receipt_git_blob_sha") != EXPECTED_ZERO_SPEND_RECEIPT_BLOB:
        raise TB4SuccessSlotError("ZERO_SPEND_RECEIPT_BINDING_MISMATCH")


def certify_slot(
    receipt: Mapping[str, Any],
    *,
    scope_doc: Mapping[str, Any] | None = None,
) -> SlotVerdict:
    try:
        if not isinstance(receipt, Mapping) or receipt.get("schema") != SCHEMA:
            raise TB4SuccessSlotError("RECEIPT_SCHEMA_INVALID")
        if receipt.get("frozen_release_commit") != FROZEN_RELEASE_COMMIT:
            raise TB4SuccessSlotError("FROZEN_RELEASE_COMMIT_MISMATCH")
        _validate_bindings(receipt)

        scope = _scope_map(scope_doc if scope_doc is not None else load_current_scope())
        task = _nonempty(receipt.get("task"), "TASK")
        if task not in scope:
            raise TB4SuccessSlotError("TASK_OUTSIDE_FROZEN_66_SCOPE")
        task_tree = _hex(receipt.get("task_tree_sha"), 40, "TASK_TREE_SHA")
        if task_tree != scope[task]:
            raise TB4SuccessSlotError("TASK_TREE_SHA_MISMATCH")

        trial_index = receipt.get("trial_index")
        if (
            isinstance(trial_index, bool)
            or not isinstance(trial_index, int)
            or not 1 <= trial_index <= TRIALS_PER_TASK
        ):
            raise TB4SuccessSlotError("TRIAL_INDEX_INVALID")
        attempt_id = _nonempty(receipt.get("attempt_id"), "ATTEMPT_ID")

        _hex(receipt.get("actor_config_sha256"), 64, "ACTOR_CONFIG_SHA256")
        _hex(receipt.get("output_sha256"), 64, "OUTPUT_SHA256")
        _hex(receipt.get("harbor_result_json_sha256"), 64, "HARBOR_RESULT_JSON_SHA256")

        if receipt.get("actor_output_frozen_before_verifier") is not True:
            raise TB4SuccessSlotError("ACTOR_OUTPUT_NOT_FROZEN_BEFORE_VERIFIER")
        if receipt.get("actor_write_closed_before_verifier") is not True:
            raise TB4SuccessSlotError("ACTOR_WRITE_NOT_CLOSED_BEFORE_VERIFIER")
        if receipt.get("hidden_verifier_exposed_to_actor") is not False:
            raise TB4SuccessSlotError("HIDDEN_VERIFIER_EXPOSURE_NOT_FALSE")
        if receipt.get("same_task_replay_after_verifier") is not False:
            raise TB4SuccessSlotError("SAME_TASK_REPLAY_NOT_FALSE")
        if receipt.get("official_frozen_task_bytes_used") is not True:
            raise TB4SuccessSlotError("OFFICIAL_FROZEN_TASK_BYTES_NOT_PROVED")
        if receipt.get("official_harbor_verifier_completed") is not True:
            raise TB4SuccessSlotError("OFFICIAL_HARBOR_VERIFIER_NOT_COMPLETED")
        if receipt.get("result_binding_complete") is not True:
            raise TB4SuccessSlotError("RESULT_BINDING_INCOMPLETE")

        declared = receipt.get("declared_success_slot_count")
        if declared != 1:
            raise TB4SuccessSlotError("SUCCESS_SLOT_MULTIPLICITY_MUST_EQUAL_ONE")

        reward = receipt.get("verifier_reward")
        if isinstance(reward, bool) or not isinstance(reward, (int, float)):
            raise TB4SuccessSlotError("VERIFIER_REWARD_INVALID")
        if reward <= 0:
            return SlotVerdict(
                accepted=False,
                reason="OFFICIAL_VERIFIER_REWARD_NOT_POSITIVE",
                success_slot_delta=0,
                task=task,
                trial_index=trial_index,
                attempt_id=attempt_id,
            )

        return SlotVerdict(
            accepted=True,
            reason="ONE_FROZEN_OFFICIAL_VERIFIER_PASS_CERTIFIES_EXACTLY_ONE_SUCCESS_SLOT",
            success_slot_delta=1,
            task=task,
            trial_index=trial_index,
            attempt_id=attempt_id,
        )
    except TB4SuccessSlotError as exc:
        return SlotVerdict(
            accepted=False,
            reason=str(exc),
            success_slot_delta=0,
        )


def aggregate_success_slots(
    receipts: Sequence[Mapping[str, Any]],
    *,
    scope_doc: Mapping[str, Any] | None = None,
    required_successes: int = CURRENT_REQUIRED_SUCCESSES,
) -> dict[str, Any]:
    if (
        isinstance(required_successes, bool)
        or not isinstance(required_successes, int)
        or required_successes <= 0
    ):
        raise TB4SuccessSlotError("REQUIRED_SUCCESSES_INVALID")
    if not isinstance(receipts, Sequence) or isinstance(receipts, (str, bytes)):
        raise TB4SuccessSlotError("RECEIPTS_INVALID")

    accepted: list[SlotVerdict] = []
    rejected: list[SlotVerdict] = []
    seen_attempts: set[str] = set()
    seen_slots: set[tuple[str, int]] = set()

    for receipt in receipts:
        verdict = certify_slot(receipt, scope_doc=scope_doc)
        if verdict.attempt_id is not None:
            if verdict.attempt_id in seen_attempts:
                raise TB4SuccessSlotError("DUPLICATE_ATTEMPT_ID:" + verdict.attempt_id)
            seen_attempts.add(verdict.attempt_id)
        if verdict.task is not None and verdict.trial_index is not None:
            slot = (verdict.task, verdict.trial_index)
            if slot in seen_slots:
                raise TB4SuccessSlotError(
                    "DUPLICATE_TASK_TRIAL_SLOT:" + verdict.task + ":" + str(verdict.trial_index)
                )
            seen_slots.add(slot)
        (accepted if verdict.accepted else rejected).append(verdict)

    success_count = sum(x.success_slot_delta for x in accepted)
    return {
        "schema": AGGREGATE_SCHEMA,
        "status": "THRESHOLD_MET" if success_count >= required_successes else "THRESHOLD_OPEN",
        "required_successes": required_successes,
        "certified_success_slots": success_count,
        "remaining_success_slots": max(0, required_successes - success_count),
        "threshold_met": success_count >= required_successes,
        "accepted_receipt_count": len(accepted),
        "rejected_receipt_count": len(rejected),
        "accepted": [asdict(x) for x in accepted],
        "rejected": [asdict(x) for x in rejected],
        "owner_sandbox_identity_required_as_separate_premise": False,
        "cardinality_rule": "ONE_ACCEPTED_RECEIPT_EQUALS_EXACTLY_ONE_SUCCESS_SLOT",
        "execution_authority": False,
        "replay_authority": False,
        "acceptance_credit_delta": 0,
    }


def scope_digest(scope_doc: Mapping[str, Any]) -> str:
    scope = _scope_map(scope_doc)
    raw = json.dumps(scope, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(raw).hexdigest()
