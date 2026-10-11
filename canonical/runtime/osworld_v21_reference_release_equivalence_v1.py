"""OSWorld v2.1 public-reference -> official-release semantic-authentication adapter.

This is deliberately narrow.  It authenticates the *observed public instruction
semantics* used by the finite 108-task coverage matrix to the official
osworld-v2.1 task release by composing already-proved content-addressed facts:

1. the owner release manifest identifies one immutable 108-task release and its
   regenerated task-hash manifest;
2. the independent reference-run scorecard reports the same release and exact
   manifest digest, with all 108 tasks integrity-checked before every run;
3. the public corpus replay independently checks instruction.txt ==
   task_record.json instruction for all 108 task ids.

It does NOT claim byte access to gated task implementations, equivalence to
Anthropic's September-10 target population, harness equivalence, or score
authority.
"""
from __future__ import annotations

from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_OSWORLD_V21_REFERENCE_RELEASE_EQUIVALENCE_ADAPTER_V1"
OFFICIAL_RELEASE = "osworld-v2.1"
OFFICIAL_TASK_COMMIT = "0a1aadad95aa79b00b3783e717d865089ab06e26"
OFFICIAL_HASH_MANIFEST_SHA256 = (
    "c54d428329be5ca72742a6becd49ee83cf739df5dea429bba182e1f3f21badfb"
)
TASK_COUNT = 108


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "public_instruction_semantics_authenticated_to_official_v21": False,
        "anthropic_sep10_population_equivalence": False,
        "harness_equivalence": False,
        "score_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def evaluate(
    official_release: Mapping[str, Any],
    reference_scorecard: Mapping[str, Any],
    public_replay: Mapping[str, Any],
) -> dict[str, Any]:
    if not all(isinstance(x, Mapping) for x in (official_release, reference_scorecard, public_replay)):
        return _fail("INPUT_NOT_MAPPING")

    if official_release.get("release") != OFFICIAL_RELEASE:
        return _fail("OFFICIAL_RELEASE_MISMATCH")
    if official_release.get("task_commit") != OFFICIAL_TASK_COMMIT:
        return _fail("OFFICIAL_TASK_COMMIT_MISMATCH")
    if official_release.get("task_hash_manifest_sha256") != OFFICIAL_HASH_MANIFEST_SHA256:
        return _fail("OFFICIAL_HASH_MANIFEST_MISMATCH")
    if official_release.get("task_count") != TASK_COUNT:
        return _fail("OFFICIAL_TASK_COUNT_MISMATCH")
    if official_release.get("all_task_files_unmodified_verified") is not True:
        return _fail("OFFICIAL_TASK_FILE_VERIFICATION_REQUIRED")

    if reference_scorecard.get("task_release") != OFFICIAL_RELEASE:
        return _fail("REFERENCE_RELEASE_MISMATCH")
    if reference_scorecard.get("hash_manifest_sha256") != OFFICIAL_HASH_MANIFEST_SHA256:
        return _fail("REFERENCE_HASH_MANIFEST_MISMATCH")
    if reference_scorecard.get("matched") != TASK_COUNT:
        return _fail("REFERENCE_MATCHED_TASK_COUNT_MISMATCH")
    if reference_scorecard.get("integrity_checked_before_every_run") is not True:
        return _fail("PRE_RUN_INTEGRITY_CHECK_REQUIRED")
    if reference_scorecard.get("each_run_manifest_carries_same_values") is not True:
        return _fail("PER_RUN_INTEGRITY_BINDING_REQUIRED")

    if public_replay.get("unique_tasks_replayed") != TASK_COUNT:
        return _fail("PUBLIC_REPLAY_TASK_COUNT_MISMATCH")
    if public_replay.get("instruction_task_record_identity_checks_passed") != TASK_COUNT:
        return _fail("INSTRUCTION_TASK_RECORD_IDENTITY_INCOMPLETE")
    if public_replay.get("canonical_release_hash_match") is not True:
        return _fail("PUBLIC_REPLAY_RELEASE_HASH_NOT_MATCHED")

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__PUBLIC_INSTRUCTION_SEMANTICS_AUTHENTICATED_TO_OFFICIAL_OSWORLD_V21_RELEASE",
        "release": OFFICIAL_RELEASE,
        "task_count": TASK_COUNT,
        "task_commit": OFFICIAL_TASK_COMMIT,
        "task_hash_manifest_sha256": OFFICIAL_HASH_MANIFEST_SHA256,
        "public_instruction_semantics_authenticated_to_official_v21": True,
        "proof_basis": [
            "OWNER_RELEASE_MANIFEST_BINDS_IMMUTABLE_TASK_COMMIT_AND_108_FILE_HASH_MANIFEST",
            "REFERENCE_RUNS_BIND_SAME_RELEASE_AND_EXACT_HASH_MANIFEST_FOR_108_OF_108_TASKS",
            "REFERENCE_SCORECARD_STATES_INTEGRITY_CHECKED_BEFORE_EVERY_RUN_AND_PER_RUN_MANIFEST_REPEATS_VALUES",
            "INDEPENDENT_PUBLIC_REPLAY_CONFIRMS_108_OF_108_INSTRUCTION_TO_TASK_RECORD_IDENTITY",
        ],
        "remaining_exact_boundary": (
            "ANTHROPIC_2026_09_10_TARGET_POPULATION_TO_OFFICIAL_V21_OR_SOUND_EQUIVALENT_"
            "POPULATION_BINDING__THEN_PROTOCOL_EQUIVALENT_BRAIN_HARNESS_AND_AUTHENTIC_SCORE"
        ),
        "owner_gated_task_bytes_accessed": False,
        "hidden_task_implementation_byte_equivalence_claimed": False,
        "anthropic_sep10_population_equivalence": False,
        "harness_equivalence": False,
        "score_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
