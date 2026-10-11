from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_OSWORLD_REFERENCE_INSTRUCTION_AUTHENTICITY_V1"
ROOT = Path(__file__).resolve().parents[2]

IDENTITY_PATH = ROOT / "canonical/governance/OSWORLD_V21_PINNED_TASK_UNIVERSE_IDENTITY_20261010_V1.json"
REFERENCE_PATH = ROOT / "canonical/governance/OSWORLD_V21_PUBLIC_REFERENCE_SEMANTIC_COVERAGE_20261011_V1.json"
VERIFY_PATH = ROOT / "canonical/verification/OSWORLD_V21_PUBLIC_REFERENCE_SEMANTIC_COVERAGE_INDEPENDENT_VERIFY_20261011_V1.json"


def _load(path: Path) -> Mapping[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, Mapping):
        raise ValueError(f"JSON_OBJECT_REQUIRED:{path}")
    return doc


def evaluate(
    identity: Mapping[str, Any],
    reference: Mapping[str, Any],
    verification: Mapping[str, Any],
) -> dict[str, Any]:
    base = {
        "schema": SCHEMA,
        "pass": False,
        "instruction_authenticity_closed": False,
        "full_task_implementation_semantics_closed": False,
        "evaluator_implementation_closed": False,
        "score_ready": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "acceptance_credit_delta": 0,
        "terminal_credit_delta": 0,
    }
    try:
        owner = identity["public_release_bindings"]["task_hash_manifest"]
        canon = reference["canonical_release_identity"]
        pub = reference["public_reference_source"]
        acq = reference["acquisition_result"]
        replay = verification["source_replay"]

        values = {
            str(owner["sha256"]),
            str(canon["canonical_hash_manifest_sha256"]),
            str(pub["scorecard_task_integrity_hash_manifest_sha256"]),
            str(replay["canonical_official_release_hash_manifest_sha256"]),
        }
        if len(values) != 1:
            return {**base, "status": "FAIL_CLOSED", "reason": "TASK_HASH_MANIFEST_IDENTITY_MISMATCH"}

        h = next(iter(values))
        if len(h) != 64:
            return {**base, "status": "FAIL_CLOSED", "reason": "TASK_HASH_MANIFEST_SHA256_INVALID"}

        checks = {
            "official_task_count": owner.get("task_count") == 108,
            "official_identity_replay_count": identity.get("independent_replay", {}).get("parsed_task_count") == 108,
            "reference_scorecard_matched_count": pub.get("scorecard_matched_task_count") == 108,
            "reference_task_ids_acquired": acq.get("task_ids_acquired") == 108,
            "reference_unique_task_ids": acq.get("unique_task_ids") == 108,
            "reference_instruction_files": acq.get("instruction_files") == 108,
            "reference_task_record_files": acq.get("task_record_files") == 108,
            "independent_unique_tasks": replay.get("unique_tasks_replayed") == 108,
            "independent_instruction_task_record_checks": replay.get("instruction_task_record_identity_checks_passed") == 108,
            "independent_subject_pass": str(verification.get("status", "")).startswith("PASS__"),
            "reference_subject_claims_integrity_check": (
                pub.get("source_claim")
                == "TASK_INTEGRITY_HASH_CHECKED_BEFORE_EVERY_RUN__EACH_RUN_MANIFEST_CARRIES_SAME_VALUES"
            ),
        }
        failed = sorted(k for k, ok in checks.items() if not ok)
        if failed:
            return {
                **base,
                "status": "FAIL_CLOSED",
                "reason": "AUTHENTICITY_PREMISE_FAILED:" + ",".join(failed),
                "checks": checks,
            }

        return {
            **base,
            "pass": True,
            "status": "PASS__REFERENCE_INSTRUCTIONS_AUTHENTICATED_TO_EXACT_HASH_CHECKED_V21_TASK_UNIVERSE",
            "instruction_authenticity_closed": True,
            "official_task_hash_manifest_sha256": h,
            "task_count": 108,
            "checks": checks,
            "proof": (
                "THE_OFFICIAL_RELEASE_BINDS_ONE_108_FILE_TASK_HASH_MANIFEST__THE_PUBLIC_REFERENCE_RUN_RECORD "
                "ATTESTS_THAT_SAME_MANIFEST_WAS_CHECKED_BEFORE_EVERY_RUN_AND_MATCHED_108_TASKS__THE_PUBLIC "
                "CORPUS_CONTAINS_INSTRUCTION_AND_TASK_RECORD_FILES_FOR_ALL_108__A_SECOND_CARRIER REPLAYED "
                "108_UNIQUE_TASKS_AND_108_INSTRUCTION_TASK_RECORD_IDENTITY_CHECKS__THEREFORE_THE_PUBLISHED "
                "INSTRUCTION_CORPUS_IS_AUTHENTICATED_AS_RUNTIME_OBSERVATION_FROM_THE_EXACT_HASH_CHECKED "
                "TASK_UNIVERSE__THIS_DOES_NOT_REVEAL_OR_PROVE_ALL_HIDDEN_TASK_OR_EVALUATOR_IMPLEMENTATION_BYTES"
            ),
            "remaining_externality": [
                "MATERIAL_OFFICIAL_TASK_AND_ASSET_BYTES_OR_AN_OWNER_EQUIVALENT_EXECUTION_SERVICE_FOR_MATCHED_BRAIN_SCORING",
                "HIDDEN_TASK_EVALUATOR_IMPLEMENTATION_SEMANTICS_NOT_EXPOSED_BY_INSTRUCTION_CORPUS",
                "PROTOCOL_EQUIVALENT_BRAIN_HARNESS_AND_AUTHENTIC_PARTIAL_SCORE_GE_81_8_OR_STRONGER_CERTIFICATE",
            ],
        }
    except Exception as exc:
        return {**base, "status": "FAIL_CLOSED", "reason": type(exc).__name__ + ":" + str(exc)}


def evaluate_repo(root: str | Path | None = None) -> dict[str, Any]:
    base = Path(root).resolve() if root is not None else ROOT
    return evaluate(
        _load(base / IDENTITY_PATH.relative_to(ROOT)),
        _load(base / REFERENCE_PATH.relative_to(ROOT)),
        _load(base / VERIFY_PATH.relative_to(ROOT)),
    )


if __name__ == "__main__":
    print(json.dumps(evaluate_repo(), indent=2, sort_keys=True))
