"""Fail-closed accounting guard for the sub-100 MB learned-core experiment.

This module does not create capability credit. It only enforces the resource and
provider boundary for the H100 experiment and checks whether the frozen Brain
acceptance contract has fully closed.

The critical accounting rule is deliberately hostile to convenient bookkeeping:
all persistent learned state counts, independent of where it is hosted. External
learned capability providers are forbidden during scored execution because their
weights cannot be omitted from the budget by moving them behind a network call.

Every learned artifact byte count must also be independently verified and bound
to a content-addressed receipt. A self-reported byte count is not load-bearing.
"""
from __future__ import annotations

from typing import Any, Mapping

INPUT_SCHEMA = "PROJECT_BRAIN_SUB100MB_EXPERIMENT_INPUT_V1"
VERDICT_SCHEMA = "PROJECT_BRAIN_SUB100MB_EXPERIMENT_VERDICT_V1"
HYPOTHESIS_ID = "H100_FRONTIER_CAPABILITY_WITH_LE_100000000_PERSISTENT_LEARNED_BYTES"
MAX_LEARNED_BYTES = 100_000_000
FROZEN_FAMILY_COUNT = 19
FROZEN_ATOMIC_COUNT = 38
HEX = set("0123456789abcdef")

_ALLOWED_DEPENDENCY_KINDS = {
    "raw_knowledge_source",
    "deterministic_tool",
    "executor",
    "storage",
    "network_transport",
    "learned_component",
}
_FORBIDDEN_DEPENDENCY_KINDS = {
    "external_learned_capability_provider",
    "external_frontier_model",
}


def _is_nonnegative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value.lower()) <= HEX


def _is_git_sha(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 40 and set(value.lower()) <= HEX


def _receipt(value: Any) -> bool:
    return (
        isinstance(value, Mapping)
        and isinstance(value.get("path"), str)
        and bool(value.get("path"))
        and _is_git_sha(value.get("git_blob_sha"))
    )


def _fail(*errors: str) -> dict[str, Any]:
    return {
        "schema": VERDICT_SCHEMA,
        "hypothesis_id": HYPOTHESIS_ID,
        "status": "FAIL_CLOSED",
        "pass": False,
        "errors": sorted(set(errors)),
        "budget_pass": False,
        "provider_boundary_pass": False,
        "capability_pass": False,
        "learned_bytes_total": None,
        "learned_bytes_headroom": None,
        "execution_authority": False,
        "promotion_authority": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }


def audit(doc: Mapping[str, Any]) -> dict[str, Any]:
    """Audit one exact H100 candidate.

    Required properties:
    - the budget is frozen at exactly 100,000,000 persistent learned bytes;
    - every persistent learned artifact is content-addressed and byte-counted;
    - each byte count is independently verified by a content-addressed receipt;
    - learned runtime components must point to a counted artifact;
    - external learned/frontier capability providers are forbidden while scored;
    - terminal capability requires all 19 families, all 19 ownership rows, and
      all 38 atomic predicates to be closed.

    Raw knowledge sources are allowed only as declared knowledge sources. This
    guard cannot prove semantic non-leakage of their content; that remains a
    separate verification obligation.
    """
    if not isinstance(doc, Mapping) or doc.get("schema") != INPUT_SCHEMA:
        return _fail("SCHEMA_INVALID")
    if doc.get("hypothesis_id") != HYPOTHESIS_ID:
        return _fail("HYPOTHESIS_ID_INVALID")
    if doc.get("max_persistent_learned_bytes") != MAX_LEARNED_BYTES:
        return _fail("BUDGET_NOT_FROZEN_EXACTLY_100000000")

    errors: list[str] = []

    artifacts_raw = doc.get("learned_artifacts")
    if not isinstance(artifacts_raw, list):
        return _fail("LEARNED_ARTIFACTS_INVALID")

    artifacts: dict[str, Mapping[str, Any]] = {}
    paths: set[str] = set()
    learned_total = 0
    receipts: list[str] = []
    for i, row in enumerate(artifacts_raw):
        if not isinstance(row, Mapping):
            errors.append(f"LEARNED_ARTIFACT_NOT_OBJECT:{i}")
            continue
        aid = row.get("id")
        path = row.get("path")
        size = row.get("bytes")
        digest = row.get("sha256")
        if not isinstance(aid, str) or not aid:
            errors.append(f"LEARNED_ARTIFACT_ID_INVALID:{i}")
            continue
        if aid in artifacts:
            errors.append(f"LEARNED_ARTIFACT_ID_DUPLICATE:{aid}")
            continue
        if not isinstance(path, str) or not path:
            errors.append(f"LEARNED_ARTIFACT_PATH_INVALID:{aid}")
            continue
        if path in paths:
            errors.append(f"LEARNED_ARTIFACT_PATH_DUPLICATE:{path}")
            continue
        if not _is_nonnegative_int(size):
            errors.append(f"LEARNED_ARTIFACT_BYTES_INVALID:{aid}")
            continue
        if not _is_sha256(digest):
            errors.append(f"LEARNED_ARTIFACT_SHA256_INVALID:{aid}")
            continue
        if row.get("byte_count_verified") is not True or row.get("independent") is not True:
            errors.append(f"LEARNED_ARTIFACT_BYTE_COUNT_NOT_INDEPENDENTLY_VERIFIED:{aid}")
            continue
        if not _receipt(row.get("verification_receipt")):
            errors.append(f"LEARNED_ARTIFACT_VERIFICATION_RECEIPT_INVALID:{aid}")
            continue
        artifacts[aid] = row
        paths.add(path)
        learned_total += int(size)
        receipt = row["verification_receipt"]
        receipts.append(str(receipt["path"]) + "@" + str(receipt["git_blob_sha"]))

    dependencies_raw = doc.get("runtime_dependencies")
    if not isinstance(dependencies_raw, list):
        return _fail("RUNTIME_DEPENDENCIES_INVALID")

    dependency_ids: set[str] = set()
    forbidden_dependencies: list[str] = []
    for i, row in enumerate(dependencies_raw):
        if not isinstance(row, Mapping):
            errors.append(f"RUNTIME_DEPENDENCY_NOT_OBJECT:{i}")
            continue
        did = row.get("id")
        kind = row.get("kind")
        if not isinstance(did, str) or not did:
            errors.append(f"RUNTIME_DEPENDENCY_ID_INVALID:{i}")
            continue
        if did in dependency_ids:
            errors.append(f"RUNTIME_DEPENDENCY_ID_DUPLICATE:{did}")
            continue
        dependency_ids.add(did)
        if kind in _FORBIDDEN_DEPENDENCY_KINDS:
            forbidden_dependencies.append(did)
            continue
        if kind not in _ALLOWED_DEPENDENCY_KINDS:
            errors.append(f"RUNTIME_DEPENDENCY_KIND_INVALID:{did}")
            continue
        if kind == "learned_component":
            artifact_id = row.get("artifact_id")
            if artifact_id not in artifacts:
                errors.append(f"LEARNED_COMPONENT_NOT_COUNTED:{did}")

    scored = doc.get("scored_execution")
    if not isinstance(scored, Mapping):
        return _fail("SCORED_EXECUTION_INVALID")

    frontier_calls = scored.get("external_frontier_model_calls")
    learned_provider_calls = scored.get("external_learned_capability_calls")
    if not _is_nonnegative_int(frontier_calls):
        errors.append("EXTERNAL_FRONTIER_MODEL_CALL_COUNT_INVALID")
    if not _is_nonnegative_int(learned_provider_calls):
        errors.append("EXTERNAL_LEARNED_CAPABILITY_CALL_COUNT_INVALID")

    capability = doc.get("capability_contract")
    if not isinstance(capability, Mapping):
        return _fail("CAPABILITY_CONTRACT_INVALID")

    total_families = capability.get("total_families")
    accepted_families = capability.get("accepted_families")
    verified_owned_families = capability.get("verified_owned_families")
    total_atomic = capability.get("total_atomic")
    proved_atomic = capability.get("proved_atomic")

    if total_families != FROZEN_FAMILY_COUNT:
        errors.append("FAMILY_DENOMINATOR_CHANGED")
    if total_atomic != FROZEN_ATOMIC_COUNT:
        errors.append("ATOMIC_DENOMINATOR_CHANGED")
    for label, value, upper in (
        ("ACCEPTED_FAMILIES", accepted_families, FROZEN_FAMILY_COUNT),
        ("VERIFIED_OWNED_FAMILIES", verified_owned_families, FROZEN_FAMILY_COUNT),
        ("PROVED_ATOMIC", proved_atomic, FROZEN_ATOMIC_COUNT),
    ):
        if not _is_nonnegative_int(value) or int(value) > upper:
            errors.append(f"{label}_INVALID")

    if errors:
        return _fail(*errors)

    budget_pass = learned_total <= MAX_LEARNED_BYTES
    provider_boundary_pass = (
        not forbidden_dependencies
        and int(frontier_calls) == 0
        and int(learned_provider_calls) == 0
    )
    capability_pass = (
        accepted_families == FROZEN_FAMILY_COUNT
        and verified_owned_families == FROZEN_FAMILY_COUNT
        and proved_atomic == FROZEN_ATOMIC_COUNT
    )

    if not budget_pass or not provider_boundary_pass:
        status = "CANDIDATE_REJECTED"
    elif capability_pass:
        status = "H100_CLOSED"
    else:
        status = "EXPERIMENT_OPEN"

    return {
        "schema": VERDICT_SCHEMA,
        "hypothesis_id": HYPOTHESIS_ID,
        "status": status,
        "pass": budget_pass and provider_boundary_pass and capability_pass,
        "errors": [],
        "budget_pass": budget_pass,
        "provider_boundary_pass": provider_boundary_pass,
        "capability_pass": capability_pass,
        "learned_bytes_total": learned_total,
        "learned_bytes_headroom": MAX_LEARNED_BYTES - learned_total,
        "learned_artifact_verification_receipts": sorted(set(receipts)),
        "forbidden_runtime_dependencies": sorted(forbidden_dependencies),
        "capability_contract": {
            "accepted_families": accepted_families,
            "verified_owned_families": verified_owned_families,
            "total_families": total_families,
            "proved_atomic": proved_atomic,
            "total_atomic": total_atomic,
        },
        "hard_nonclaim": (
            "BUDGET_OR_PROVIDER_PASS_ALONE_CREATES_NO_CAPABILITY_CREDIT; "
            "H100_CLOSES_ONLY_WHEN_THE_FROZEN_19_FAMILY_38_ATOM_CONTRACT_CLOSES."
        ),
        "execution_authority": False,
        "promotion_authority": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }
