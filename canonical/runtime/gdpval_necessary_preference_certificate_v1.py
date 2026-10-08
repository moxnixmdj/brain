from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_GDPVAL_NECESSARY_PREFERENCE_CERTIFICATE_V1"
PASS_OUTCOMES = {"BRAIN_WEAKLY_DOMINATES", "BRAIN_TOP"}
EXPECTED_TASKS = 220
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _valid_sha256(value: Any) -> bool:
    return isinstance(value, str) and _SHA256.fullmatch(value) is not None


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "pass": False,
        "status": "UNRESOLVED__FAIL_CLOSED",
        "reason": reason,
        "terminal_credit_delta": 0,
        "gdpval_credit_delta": 0,
    }
    out.update(extra)
    return out


def verify(manifest: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(manifest, Mapping):
        return _fail("MANIFEST_INVALID")

    if manifest.get("task_count") != EXPECTED_TASKS:
        return _fail("TASK_COUNT_NOT_220", observed=manifest.get("task_count"))

    envelope = manifest.get("preference_envelope")
    if not isinstance(envelope, Mapping):
        return _fail("PREFERENCE_ENVELOPE_MISSING")

    required_envelope_flags = {
        "published_owner_contract_bound": True,
        "same_task_pairwise_semantics_bound": True,
        "anonymized_ab_semantics_bound": True,
        "all_reference_and_submission_context_bound": True,
        "presentation_transform_bound_or_sound_overapproximation": True,
        "true_owner_relation_contained_in_envelope": True,
    }
    missing_flags = [
        key
        for key, expected in required_envelope_flags.items()
        if envelope.get(key) is not expected
    ]
    if missing_flags:
        return _fail(
            "OWNER_COMPATIBLE_PREFERENCE_ENVELOPE_NOT_SOUNDLY_BOUND",
            missing_envelope_flags=missing_flags,
        )

    for field in ("owner_contract_evidence_sha256", "envelope_containment_evidence_sha256"):
        if not _valid_sha256(envelope.get(field)):
            return _fail(
                "OWNER_COMPATIBLE_PREFERENCE_ENVELOPE_EVIDENCE_MISSING",
                missing_or_invalid_evidence_field=field,
            )

    tasks = manifest.get("tasks")
    if not isinstance(tasks, Sequence) or isinstance(tasks, (str, bytes)):
        return _fail("TASKS_INVALID")
    if len(tasks) != EXPECTED_TASKS:
        return _fail("TASK_LIST_NOT_220", observed=len(tasks))

    seen: set[str] = set()
    unresolved: list[dict[str, Any]] = []
    passed_tasks = 0
    total_dimensions = 0

    for idx, raw in enumerate(tasks):
        if not isinstance(raw, Mapping):
            return _fail("TASK_ENTRY_INVALID", task_index=idx)

        task_id = raw.get("task_id")
        if not isinstance(task_id, str) or not task_id.strip() or task_id in seen:
            return _fail(
                "TASK_ID_INVALID_OR_DUPLICATE",
                task_index=idx,
                task_id=task_id,
            )
        seen.add(task_id)

        cover_sound = raw.get("task_relevant_dimension_cover_sound") is True
        entailment_bound = raw.get("dominance_entails_noninferiority_over_envelope") is True
        cover_evidence = _valid_sha256(raw.get("dimension_cover_evidence_sha256"))
        entailment_evidence = _valid_sha256(raw.get("entailment_evidence_sha256"))

        if not cover_sound or not cover_evidence:
            unresolved.append(
                {
                    "task_id": task_id,
                    "kind": "DIMENSION_COVER_NOT_PROVED",
                    "missing_cover_evidence": not cover_evidence,
                }
            )
            continue

        if not entailment_bound or not entailment_evidence:
            unresolved.append(
                {
                    "task_id": task_id,
                    "kind": "DOMINANCE_TO_OWNER_ENVELOPE_ENTAILMENT_NOT_PROVED",
                    "missing_entailment_evidence": not entailment_evidence,
                }
            )
            continue

        dimensions = raw.get("dimensions")
        if (
            not isinstance(dimensions, Sequence)
            or isinstance(dimensions, (str, bytes))
            or not dimensions
        ):
            unresolved.append(
                {
                    "task_id": task_id,
                    "kind": "NO_CERTIFIED_DIMENSIONS",
                }
            )
            continue

        task_ok = True
        dim_seen: set[str] = set()
        for d_idx, dim in enumerate(dimensions):
            total_dimensions += 1
            if not isinstance(dim, Mapping):
                return _fail(
                    "DIMENSION_INVALID",
                    task_id=task_id,
                    dimension_index=d_idx,
                )

            dimension_id = dim.get("dimension_id")
            if (
                not isinstance(dimension_id, str)
                or not dimension_id.strip()
                or dimension_id in dim_seen
            ):
                return _fail(
                    "DIMENSION_ID_INVALID_OR_DUPLICATE",
                    task_id=task_id,
                    dimension_index=d_idx,
                    dimension_id=dimension_id,
                )
            dim_seen.add(dimension_id)

            outcome = dim.get("outcome")
            if outcome not in PASS_OUTCOMES:
                task_ok = False
                unresolved.append(
                    {
                        "task_id": task_id,
                        "kind": "PREFERENCE_DISCRIMINATOR_SURVIVES",
                        "dimension_id": dimension_id,
                        "outcome": outcome,
                    }
                )
                continue

            if not _valid_sha256(dim.get("evidence_sha256")):
                task_ok = False
                unresolved.append(
                    {
                        "task_id": task_id,
                        "kind": "DOMINANCE_EVIDENCE_MISSING_OR_UNADDRESSED",
                        "dimension_id": dimension_id,
                    }
                )

        if task_ok:
            passed_tasks += 1

    if unresolved:
        return _fail(
            "NECESSARY_PREFERENCE_NOT_PROVED_FOR_FULL_SCOPE",
            passed_tasks=passed_tasks,
            unresolved_task_count=len({x["task_id"] for x in unresolved}),
            unresolved=unresolved,
            total_dimensions=total_dimensions,
            next_action=(
                "LOCALIZE_ONLY_THE_LISTED_SURVIVING_ENVELOPE_OR_DIMENSION_"
                "COUNTEREXAMPLES__DO_NOT_REOPEN_CROWD_BT_OR_GENERAL_METADATA"
            ),
        )

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__SCOPE_COMPLETE_NECESSARY_PREFERENCE_LOGIC_CERTIFICATE",
        "task_count": EXPECTED_TASKS,
        "passed_tasks": passed_tasks,
        "total_dimensions": total_dimensions,
        "theorem": (
            "FOR_EACH_TASK_x__IF_THE_TRUE_OWNER_PAIRWISE_RELATION_JSTAR_x_IS_IN_"
            "THE_SOUNDLY_BOUND_ENVELOPE_E_x__AND_BRAIN_IS_PROVED_NONINFERIOR_TO_"
            "OPUS55_FOR_EVERY_RELATION_IN_E_x__THEN_BRAIN_IS_NONINFERIOR_TO_"
            "OPUS55_UNDER_JSTAR_x__THE_EXACT_OWNER_PROMPT_IS_NOT_LOGICALLY_REQUIRED"
        ),
        "exact_owner_prompt_required": False,
        "complete_owner_pairwise_graph_required": False,
        "exact_crowd_bt_elo_reproduction_required": False,
        "owner_grader_call_required_for_logic": False,
        "terminal_credit_delta": 0,
        "gdpval_credit_delta": 0,
        "promotion_boundary": (
            "LOGIC_CERTIFICATE_ONLY__GDPVAL_CREDIT_REQUIRES_REAL_220_TASK_EVIDENCE_"
            "PLUS_INDEPENDENT_REPLAY_OF_ENVELOPE_CONTAINMENT_AND_DOMINANCE"
        ),
    }
