"""Strong bytes accounting and persistent-information lower bound.

This module repairs a weaker metric: zero persistent *learned* bytes can coexist
with a growing deterministic capability library. The strong bytes target freezes
a capability-bearing kernel and then asks whether any durable capability-bearing
artifact changed or was added.

It also separates an information lower bound from a persistence lower bound.
A separator may be necessary for a decision while requiring zero persistent bits
when it can be reacquired JIT before the irreversible deadline.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Any

SCHEMA = "PROJECT_BRAIN_BYTES_STRONG_ACCOUNTING_AND_PERSISTENCE_CUT_V1"
HEX = set("0123456789abcdef")


class BytesResearchError(ValueError):
    pass


@dataclass(frozen=True)
class Artifact:
    path: str
    sha256: str
    byte_count: int
    persistent: bool
    capability_bearing: bool
    learned: bool
    category: str
    noncapability_role_verified: bool
    noncapability_role_receipt_sha256: str | None


def _is_sha256(value: str) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value.lower()) <= HEX


def artifact(row: Mapping[str, Any]) -> Artifact:
    if not isinstance(row, Mapping):
        raise BytesResearchError("ARTIFACT_NOT_MAPPING")
    path = row.get("path")
    digest = row.get("sha256")
    size = row.get("byte_count")
    persistent = row.get("persistent")
    capability_bearing = row.get("capability_bearing")
    learned = row.get("learned")
    category = row.get("category")
    noncapability_role_verified = row.get("noncapability_role_verified", False)
    noncapability_role_receipt_sha256 = row.get("noncapability_role_receipt_sha256")
    if not isinstance(path, str) or not path:
        raise BytesResearchError("ARTIFACT_PATH_INVALID")
    if not _is_sha256(digest):
        raise BytesResearchError("ARTIFACT_SHA256_INVALID")
    if not isinstance(size, int) or isinstance(size, bool) or size < 0:
        raise BytesResearchError("ARTIFACT_BYTE_COUNT_INVALID")
    if not isinstance(persistent, bool):
        raise BytesResearchError("ARTIFACT_PERSISTENCE_INVALID")
    if not isinstance(capability_bearing, bool):
        raise BytesResearchError("ARTIFACT_CAPABILITY_ROLE_INVALID")
    if not isinstance(learned, bool):
        raise BytesResearchError("ARTIFACT_LEARNED_ROLE_INVALID")
    if learned and not capability_bearing:
        raise BytesResearchError("LEARNED_ARTIFACT_MUST_BE_CAPABILITY_BEARING")
    if not isinstance(category, str) or not category:
        raise BytesResearchError("ARTIFACT_CATEGORY_INVALID")
    if persistent and not capability_bearing:
        if noncapability_role_verified is not True:
            raise BytesResearchError("PERSISTENT_NONCAPABILITY_ROLE_NOT_INDEPENDENTLY_VERIFIED")
        if not _is_sha256(noncapability_role_receipt_sha256):
            raise BytesResearchError("PERSISTENT_NONCAPABILITY_ROLE_RECEIPT_INVALID")
    elif not isinstance(noncapability_role_verified, bool):
        raise BytesResearchError("NONCAPABILITY_ROLE_VERIFICATION_FLAG_INVALID")
    return Artifact(
        path=path,
        sha256=digest.lower(),
        byte_count=size,
        persistent=persistent,
        capability_bearing=capability_bearing,
        learned=learned,
        category=category,
        noncapability_role_verified=bool(noncapability_role_verified),
        noncapability_role_receipt_sha256=(
            str(noncapability_role_receipt_sha256).lower()
            if isinstance(noncapability_role_receipt_sha256, str)
            else None
        ),
    )


def _manifest(rows: Iterable[Mapping[str, Any]]) -> dict[str, Artifact]:
    out: dict[str, Artifact] = {}
    for raw in rows:
        item = artifact(raw)
        if item.path in out:
            raise BytesResearchError("DUPLICATE_ARTIFACT_PATH:" + item.path)
        out[item.path] = item
    return out


def ceil_log2_classes(n: int) -> int:
    if not isinstance(n, int) or isinstance(n, bool) or n < 1:
        raise BytesResearchError("DISTINCTION_COUNT_INVALID")
    return 0 if n == 1 else (n - 1).bit_length()


def persistent_bits_lower_bound(
    required_future_decision_classes: int,
    *,
    separator_reacquirable_before_deadline: bool,
) -> int:
    """Information-theoretic persistent-state lower bound.

    If the separator can be reacquired before commitment, this theorem alone
    imposes no persistent-state lower bound. If not, m distinguishable future
    decision classes require at least ceil(log2(m)) retained bits.
    """
    if not isinstance(separator_reacquirable_before_deadline, bool):
        raise BytesResearchError("REACQUIRABILITY_FLAG_INVALID")
    if separator_reacquirable_before_deadline:
        ceil_log2_classes(required_future_decision_classes)
        return 0
    return ceil_log2_classes(required_future_decision_classes)


def strong_bytes_accounting(
    before_rows: Iterable[Mapping[str, Any]],
    after_rows: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Compare a frozen durable capability manifest before vs after acquisition.

    Any added or content-changed *persistent capability-bearing* artifact breaks
    zero-incremental-capability-bytes, even when it is deterministic/nonlearned.
    Removals are reported separately and do not create positive incremental bytes.
    """
    before = _manifest(before_rows)
    after = _manifest(after_rows)

    def durable_capability(m: dict[str, Artifact]) -> dict[str, Artifact]:
        return {
            p: a for p, a in m.items()
            if a.persistent and a.capability_bearing
        }

    bcap = durable_capability(before)
    acap = durable_capability(after)

    new_or_changed: list[str] = []
    incremental_bytes = 0
    for path, item in sorted(acap.items()):
        old = bcap.get(path)
        if old is None or old.sha256 != item.sha256:
            new_or_changed.append(path)
            incremental_bytes += item.byte_count

    removed = sorted(set(bcap) - set(acap))
    before_capability_bytes = sum(a.byte_count for a in bcap.values())
    after_capability_bytes = sum(a.byte_count for a in acap.values())
    learned_bytes_after = sum(
        a.byte_count for a in after.values()
        if a.persistent and a.learned
    )
    persistent_task_state_bytes_after = sum(
        a.byte_count for a in after.values()
        if a.persistent and (not a.capability_bearing)
    )
    ephemeral_capability_bytes_after = sum(
        a.byte_count for a in after.values()
        if (not a.persistent) and a.capability_bearing
    )

    return {
        "schema": SCHEMA,
        "before_persistent_capability_bytes": before_capability_bytes,
        "after_persistent_capability_bytes": after_capability_bytes,
        "net_persistent_capability_storage_delta_bytes":
            after_capability_bytes - before_capability_bytes,
        "incremental_new_or_changed_capability_bytes": incremental_bytes,
        "new_or_changed_persistent_capability_artifacts": new_or_changed,
        "removed_persistent_capability_artifacts": removed,
        "persistent_learned_bytes_after": learned_bytes_after,
        "persistent_noncapability_state_bytes_after": persistent_task_state_bytes_after,
        "ephemeral_capability_bytes_in_after_manifest": ephemeral_capability_bytes_after,
        "zero_persistent_learned_bytes": learned_bytes_after == 0,
        "zero_incremental_persistent_capability_bytes": len(new_or_changed) == 0,
        "literal_zero_persistent_capability_bytes": after_capability_bytes == 0,
        "metric_warning":
            "ZERO_LEARNED_BYTES_IS_WEAKER_THAN_ZERO_INCREMENTAL_CAPABILITY_BYTES",
    }


def verify_reference_cases() -> dict[str, Any]:
    h0 = "0" * 64
    h1 = "1" * 64
    h2 = "2" * 64

    frozen = [
        {
            "path": "kernel.py",
            "sha256": h0,
            "byte_count": 4096,
            "persistent": True,
            "capability_bearing": True,
            "learned": False,
            "category": "FROZEN_KERNEL_CODE",
        }
    ]

    deterministic_registry_growth = frozen + [
        {
            "path": "registry.py",
            "sha256": h1,
            "byte_count": 2048,
            "persistent": True,
            "capability_bearing": True,
            "learned": False,
            "category": "COMPILED_CAPABILITY_LIBRARY",
        }
    ]
    a = strong_bytes_accounting(frozen, deterministic_registry_growth)

    raw_knowledge_growth = frozen + [
        {
            "path": "task_facts.json",
            "sha256": h2,
            "byte_count": 1000000,
            "persistent": True,
            "capability_bearing": False,
            "learned": False,
            "category": "RAW_TASK_KNOWLEDGE",
            "noncapability_role_verified": True,
            "noncapability_role_receipt_sha256": "f" * 64,
        }
    ]
    b = strong_bytes_accounting(frozen, raw_knowledge_growth)

    passed = (
        a["zero_persistent_learned_bytes"] is True
        and a["zero_incremental_persistent_capability_bytes"] is False
        and a["incremental_new_or_changed_capability_bytes"] == 2048
        and b["zero_incremental_persistent_capability_bytes"] is True
        and persistent_bits_lower_bound(
            2, separator_reacquirable_before_deadline=False
        ) == 1
        and persistent_bits_lower_bound(
            8, separator_reacquirable_before_deadline=False
        ) == 3
        and persistent_bits_lower_bound(
            8, separator_reacquirable_before_deadline=True
        ) == 0
    )
    return {
        "schema": SCHEMA,
        "status": "PASS" if passed else "FAIL",
        "deterministic_registry_counterexample": a,
        "raw_knowledge_noncapability_example": b,
        "nonreacquirable_two_class_bits": 1,
        "nonreacquirable_eight_class_bits": 3,
        "reacquirable_eight_class_persistent_lower_bound_bits": 0,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(verify_reference_cases(), indent=2, sort_keys=True))
