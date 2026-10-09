"""Rule-gated normalization of proof-bearing successes into the existing bound verifier.

This adapter grants no verification or promotion authority. It is deliberately
narrow: a replay wrapper may differ, but the retained checkpoint/proof must already
be accepted by r3_bound_success_adapter_v1 after normalization.

V2 adds one verifier-preserving normalization: when replay context omits
`target_effects`, the adapter may recover that exact field from the authenticated
success proof capsule's `verified_target_effects`. It never invents target effects
and it never changes independent verification authority.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime import autonomous_verified_self_improvement_v1 as learning
from canonical.runtime import r3_bound_success_adapter_v1 as bound

SCHEMA = "PROJECT_BRAIN_R3_STRUCTURAL_BOUND_SUCCESS_ADAPTER_V1"
RULES_PATH = "canonical/runtime/R3_STRUCTURAL_BOUND_ADAPTER_RULES_V1.json"
PROFILE_REPLAY_TARGETS = "REPLAY_TARGET_EFFECTS_V1"
PROFILE_PROOF_TARGETS = "PROOF_VERIFIED_TARGET_EFFECTS_V1"
NORMALIZATION_PROFILES = (
    PROFILE_REPLAY_TARGETS,
    PROFILE_PROOF_TARGETS,
)


def _canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False, default=str)


def _sha(value: Any) -> str:
    return sha256(_canon(value).encode("utf-8")).hexdigest()


def _proof_material(observation: Mapping[str, Any]) -> Mapping[str, Any] | None:
    capsule = observation.get("proof_capsule")
    if not isinstance(capsule, Mapping):
        return None
    material = capsule.get("material")
    expected = str(capsule.get("sha256") or "").strip()
    if not isinstance(material, Mapping) or len(expected) != 64:
        return None
    if learning._sha(material) != expected:
        return None
    return material


def _items(value: Any) -> list[str] | None:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return None
    out = [str(x).strip() for x in value]
    if not out or any(not x for x in out):
        return None
    return out


def _normalized_request(
    request: Mapping[str, Any],
    *,
    normalization_profile: str,
) -> Mapping[str, Any] | None:
    observation = request.get("observation")
    replay = request.get("replay_context")
    if not isinstance(observation, Mapping) or not isinstance(replay, Mapping):
        return None
    mode = str(replay.get("mode") or "").strip()
    if mode == "compiled_bound":
        return None
    raw = replay.get("request")
    if not isinstance(raw, Mapping):
        raw = replay.get("problem")
    if not isinstance(raw, Mapping):
        return None

    normalized_raw = deepcopy(dict(raw))
    if normalization_profile == PROFILE_REPLAY_TARGETS:
        if _items(normalized_raw.get("target_effects")) is None:
            return None
    elif normalization_profile == PROFILE_PROOF_TARGETS:
        material = _proof_material(observation)
        if not isinstance(material, Mapping):
            return None
        proved_targets = _items(material.get("verified_target_effects"))
        if proved_targets is None:
            return None
        replay_targets = _items(normalized_raw.get("target_effects"))
        if replay_targets is not None and replay_targets != proved_targets:
            return None
        normalized_raw["target_effects"] = proved_targets
    else:
        return None

    normalized = deepcopy(dict(replay))
    normalized["mode"] = "compiled_bound"
    normalized["request"] = normalized_raw
    return {
        **dict(request),
        "observation": observation,
        "replay_context": normalized,
    }


def preflight(
    request: Mapping[str, Any],
    *,
    repo_root: str | Path,
    normalization_profile: str | None = None,
) -> Mapping[str, Any] | None:
    profiles = (
        (normalization_profile,)
        if normalization_profile is not None
        else NORMALIZATION_PROFILES
    )
    for profile in profiles:
        if profile not in NORMALIZATION_PROFILES:
            return None
        normalized = _normalized_request(
            request,
            normalization_profile=profile,
        )
        if normalized is None:
            continue
        candidate = bound.adapt(normalized, repo_root=repo_root)
        if candidate is None:
            continue
        out = dict(candidate)
        out["structural_normalization_profile"] = profile
        return out
    return None


def _load_rules(repo_root: str | Path) -> Mapping[str, Any]:
    root = Path(repo_root).resolve(strict=True)
    target = (root / RULES_PATH).resolve(strict=True)
    target.relative_to(root)
    doc = json.loads(target.read_text(encoding="utf-8"))
    if (
        not isinstance(doc, Mapping)
        or doc.get("schema") != "PROJECT_BRAIN_R3_STRUCTURAL_BOUND_ADAPTER_RULES_V1"
        or doc.get("version") != 1
        or not isinstance(doc.get("rules"), list)
    ):
        raise ValueError("STRUCTURAL_BOUND_RULE_FRONTIER_INVALID")
    return doc


def _identity(request: Mapping[str, Any]) -> tuple[str, str] | None:
    observation = request.get("observation")
    if not isinstance(observation, Mapping):
        return None
    surface = str(observation.get("surface") or "").strip()
    schema = str(observation.get("schema") or "").strip()
    if not surface or not schema:
        return None
    return surface, schema


def adapt(request: Mapping[str, Any], *, repo_root: str | Path) -> Mapping[str, Any] | None:
    try:
        ident = _identity(request)
        if ident is None:
            return None
        surface, schema = ident
        doc = _load_rules(repo_root)
        matches = [
            row for row in doc["rules"]
            if isinstance(row, Mapping)
            and row.get("status") == "ACTIVE"
            and row.get("surface") == surface
            and row.get("source_schema") == schema
            and row.get("verification_kind") == bound.VERIFICATION_KIND
        ]
        if len(matches) != 1:
            return None
        profile = str(
            matches[0].get("normalization_profile")
            or PROFILE_REPLAY_TARGETS
        )
        candidate = preflight(
            request,
            repo_root=repo_root,
            normalization_profile=profile,
        )
        if candidate is None:
            return None
        out = dict(candidate)
        out["schema"] = SCHEMA
        out["status"] = "STRUCTURAL_BOUND_SUCCESS_EPISODE_CANDIDATE_READY"
        out["structural_rule_id"] = matches[0].get("rule_id")
        out["structural_normalization_profile"] = profile
        out["candidate_only"] = True
        out["execution_authority"] = False
        out["verification_authority"] = False
        out["promotion_authority"] = False
        out["terminal_authority"] = False
        return out
    except Exception:
        return None
