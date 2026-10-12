"""Verified Root1 acquisition provider for R3 structural success-adapter rules.

This provider is intentionally narrow. It never authors verifier code and never
changes R3 verification authority. For one exact parked proof-bearing success it:

1. reauthenticates the retained proof/replay context;
2. asks the existing repair reducer whether a verifier-preserving adapter remains
   structurally admissible;
3. proves that one existing structural normalization profile already produces a
   candidate accepted by the existing bound-success adapter; and
4. adds only an ACTIVE rule allowing that profile to be attempted for the exact
   (surface, source_schema) class.

The rule grants no success, verification, learning, promotion, or terminal
authority. Every future candidate still passes the existing bound adapter and
immutable independent verifier.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Callable, Mapping

from canonical.runtime import autonomous_verified_self_improvement_v1 as learning
from canonical.runtime import r3_bound_success_adapter_v1 as bound
from canonical.runtime import r3_structural_bound_success_adapter_v1 as structural
from canonical.runtime import r3_success_adapter_author_context_v1 as author_context
from canonical.runtime import r3_verification_frontier_repair_reducer_v1 as repair_reducer

SCHEMA = "PROJECT_BRAIN_R3_STRUCTURAL_ADAPTER_RULE_ACQUISITION_PROVIDER_V1"
RULES_PATH = "canonical/runtime/R3_STRUCTURAL_BOUND_ADAPTER_RULES_V1.json"
FRONTIER_KIND = "EXPAND_SUCCESS_VERIFICATION_FRONTIER"


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "progress_claimed": False,
        "reason": reason,
        "verification_authority_changed": False,
        "verification_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        **extra,
    }


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _rule_id(surface: str, source_schema: str, profile: str) -> str:
    digest = sha256(
        _canon({
            "surface": surface,
            "source_schema": source_schema,
            "normalization_profile": profile,
            "verification_kind": bound.VERIFICATION_KIND,
        })
    ).hexdigest()
    return "R3_STRUCTURAL_BOUND_RULE::" + digest[:24]


def _load_rules(root: Path) -> tuple[Path, dict[str, Any]]:
    target = (root / RULES_PATH).resolve(strict=True)
    target.relative_to(root)
    if target.is_symlink() or not target.is_file():
        raise ValueError("STRUCTURAL_RULE_FILE_INVALID")
    doc = json.loads(target.read_text(encoding="utf-8"))
    if (
        not isinstance(doc, dict)
        or doc.get("schema") != "PROJECT_BRAIN_R3_STRUCTURAL_BOUND_ADAPTER_RULES_V1"
        or doc.get("version") != 1
        or not isinstance(doc.get("rules"), list)
    ):
        raise ValueError("STRUCTURAL_RULE_FRONTIER_INVALID")
    return target, doc


def _write_rules(target: Path, doc: Mapping[str, Any]) -> None:
    encoded = json.dumps(doc, indent=2, sort_keys=True) + "\n"
    tmp = target.with_name(target.name + ".tmp")
    tmp.write_text(encoded, encoding="utf-8")
    tmp.replace(target)


def make_provider(
    *,
    repo_root: str | Path,
    state_path: str | Path,
) -> Callable[[Mapping[str, Any]], Mapping[str, Any] | None]:
    root = Path(repo_root).resolve(strict=True)
    raw_state_path = Path(state_path)

    def provider(request: Mapping[str, Any]) -> Mapping[str, Any] | None:
        if not isinstance(request, Mapping):
            return _fail("REQUEST_NOT_OBJECT")
        if request.get("kind") != FRONTIER_KIND:
            return _fail("REQUEST_KIND_UNSUPPORTED")
        if request.get("verification_authority_change_allowed") is not False:
            return _fail("VERIFICATION_AUTHORITY_CHANGE_MUST_BE_FORBIDDEN")
        if (
            request.get("allowed_frontier_change_class")
            != "SUCCESS_ADAPTER_ONLY__VERIFICATION_AUTHORITY_IMMUTABLE"
        ):
            return _fail("FRONTIER_CHANGE_CLASS_INVALID")

        wid = str(request.get("improvement_work_id") or "").strip()
        blocked_id = str(request.get("blocked_success_work_id") or "").strip()
        observation_id = str(request.get("observation_id") or "").strip()
        if not wid or not blocked_id or not observation_id:
            return _fail("REQUEST_IDENTITY_INCOMPLETE")

        try:
            state_target = raw_state_path.resolve(strict=True)
            state = learning.load_state(state_target)
            queue = state.get("improvement_queue")
            observations = state.get("observations")
            if not isinstance(queue, Mapping) or not isinstance(observations, Mapping):
                return _fail("R3_STATE_INVALID")
            handoff = queue.get(wid)
            blocked = queue.get(blocked_id)
            observation = observations.get(observation_id)
            if (
                not isinstance(handoff, Mapping)
                or handoff.get("kind") != FRONTIER_KIND
                or handoff.get("status") != "PENDING"
            ):
                return _fail("FRONTIER_HANDOFF_NOT_CURRENT_PENDING_WORK")
            payload = handoff.get("payload")
            if (
                not isinstance(payload, Mapping)
                or str(payload.get("blocked_success_work_id") or "") != blocked_id
                or str(payload.get("observation_id") or "") != observation_id
            ):
                return _fail("FRONTIER_HANDOFF_BINDING_MISMATCH")
            if (
                not isinstance(blocked, Mapping)
                or blocked.get("kind") != "ADAPT_SUCCESS_TO_VERIFIABLE_EPISODE"
                or blocked.get("status") != "PARKED"
                or blocked.get("frontier_expansion_work_id") != wid
                or blocked.get("parked_reason") != "NO_CURRENT_OWNED_VERIFICATION_PATH"
            ):
                return _fail("BLOCKED_SUCCESS_NOT_CURRENT_ADAPTER_GAP")
            if (
                not isinstance(observation, Mapping)
                or observation.get("observation_id") != observation_id
                or observation.get("frontier_expansion_work_id") != wid
                or observation.get("learning_disposition_reason")
                != "OWNED_SUCCESS_ADAPTER_RETURNED_NO_CANDIDATE"
            ):
                return _fail("SUCCESS_OBSERVATION_NOT_PROVEN_ADAPTER_MISS")

            try:
                proof = learning.get_success_proof_context(
                    observation_id,
                    state_path=state_target,
                )
            except Exception as exc:
                if "SUCCESS_OBSERVATION_PROOF_UNAVAILABLE:" in str(exc):
                    return _fail(
                        "RETAINED_SUCCESS_PROOF_UNAVAILABLE__"
                        "NEW_PROOF_BEARING_EXPERIENCE_REQUIRED",
                        observation_id=observation_id,
                    )
                raise
            replay = learning.get_success_replay_context(
                observation_id,
                state_path=state_target,
            )
            context = author_context.compile_context(proof, replay)
            if context.get("pass") is not True:
                return _fail(
                    "ADAPTER_AUTHOR_CONTEXT_COMPILATION_FAILED",
                    adapter_author_context=deepcopy(dict(context)),
                )
            reduction = repair_reducer.reduce_author_context(context)
            if reduction.get("pass") is not True:
                return _fail(
                    "VERIFICATION_FRONTIER_REPAIR_REDUCTION_FAILED",
                    repair_class_reduction=deepcopy(dict(reduction)),
                )
            if repair_reducer.ADAPTER not in (
                reduction.get("admissible_repair_classes") or []
            ):
                return _fail(
                    "VERIFIER_PRESERVING_ADAPTER_NOT_ADMISSIBLE",
                    repair_class_reduction=deepcopy(dict(reduction)),
                )

            replay_context = replay.get("context")
            if not isinstance(replay_context, Mapping):
                return _fail("REPLAY_CONTEXT_INVALID")
            adapter_request = {
                "kind": "SUCCESS_TO_CANONICAL_EPISODE_CANDIDATE",
                "observation": deepcopy(dict(observation)),
                "replay_context": deepcopy(dict(replay_context)),
                "improvement_work_id": blocked_id,
                "authority_requested": "CANDIDATE_ONLY",
            }

            if structural.adapt(adapter_request, repo_root=root) is not None:
                return _fail("STRUCTURAL_ADAPTER_ALREADY_AVAILABLE__NO_FRONTIER_CHANGE_REQUIRED")

            selected_profile = None
            candidate = None
            for profile in structural.NORMALIZATION_PROFILES:
                maybe = structural.preflight(
                    adapter_request,
                    repo_root=root,
                    normalization_profile=profile,
                )
                if isinstance(maybe, Mapping):
                    selected_profile = profile
                    candidate = maybe
                    break
            if selected_profile is None or not isinstance(candidate, Mapping):
                return _fail(
                    "NO_EXISTING_VERIFIER_PRESERVING_STRUCTURAL_PROFILE_PROVED",
                    repair_class_reduction=deepcopy(dict(reduction)),
                )
            if (
                candidate.get("candidate_only") is not True
                or candidate.get("promotion_authority") is True
                or candidate.get("terminal_authority") is True
            ):
                return _fail("STRUCTURAL_PREFLIGHT_CANDIDATE_AUTHORITY_INVALID")

            surface = str(observation.get("surface") or "").strip()
            source_schema = str(observation.get("schema") or "").strip()
            if not surface or not source_schema:
                return _fail("OBSERVATION_SURFACE_AND_SCHEMA_REQUIRED")

            target, rules_doc = _load_rules(root)
            rules = rules_doc["rules"]
            active = [
                row for row in rules
                if isinstance(row, Mapping)
                and row.get("status") == "ACTIVE"
                and row.get("surface") == surface
                and row.get("source_schema") == source_schema
                and row.get("verification_kind") == bound.VERIFICATION_KIND
            ]
            if active:
                if (
                    len(active) == 1
                    and active[0].get("normalization_profile") == selected_profile
                ):
                    return _fail("IDENTICAL_STRUCTURAL_RULE_ALREADY_ACTIVE")
                return _fail("CONFLICTING_STRUCTURAL_RULE_ALREADY_ACTIVE")

            rule = {
                "rule_id": _rule_id(surface, source_schema, selected_profile),
                "status": "ACTIVE",
                "surface": surface,
                "source_schema": source_schema,
                "verification_kind": bound.VERIFICATION_KIND,
                "normalization_profile": selected_profile,
                "admission_basis": (
                    "EXACT_RETAINED_SUCCESS_PROVED_EXISTING_NORMALIZATION_PROFILE_"
                    "REACHES_EXISTING_BOUND_SUCCESS_ADAPTER"
                ),
                "source_observation_id": observation_id,
                "source_author_context_sha256": context.get("context_sha256"),
                "source_repair_reduction_class": reduction.get("retained_proof_class"),
                "candidate_generation_only": True,
                "verification_authority": False,
                "promotion_authority": False,
                "terminal_authority": False,
            }
            rules_doc["rules"] = [
                *rules,
                rule,
            ]
            _write_rules(target, rules_doc)

            return {
                "schema": SCHEMA,
                "status": "ROOT1_VERIFIER_PRESERVING_STRUCTURAL_ADAPTER_RULE_INSTALLED",
                "pass": True,
                "progress_claimed": True,
                "rule": deepcopy(rule),
                "structural_candidate_status": candidate.get("status"),
                "verification_authority_changed": False,
                "verification_authority": False,
                "promotion_authority": False,
                "terminal_authority": False,
            }
        except Exception as exc:
            return _fail(
                "ROOT1_STRUCTURAL_ADAPTER_RULE_ACQUISITION_EXCEPTION:"
                + type(exc).__name__
                + ":"
                + str(exc)
            )

    return provider
