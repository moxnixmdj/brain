"""Checkpoint-derived candidate adapter for proof-bearing bound successes.

This adapter grants no verification or promotion authority. It is used only when
retained checkpoint bytes already prove a sequence of verified bound-capability
steps but the original replay wrapper does not expose a canonical compiled-bound
request.

The adapter reconstructs the *minimal conservative* compiled-bound contract:
- preconditions are every declared step requirement not produced by an earlier
  verified step;
- postconditions are the exact retained verified_target_effects;
- every retained target effect must be produced by at least one verified step.

The resulting candidate is then delegated to r3_bound_success_adapter_v1 and the
existing independent bound-success verifier remains the sole learning authority.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime import autonomous_verified_self_improvement_v1 as learning
from canonical.runtime import r3_bound_success_adapter_v1 as bound
from canonical.runtime import r3_structural_bound_success_adapter_v1 as structural

SCHEMA = "PROJECT_BRAIN_R3_CHECKPOINT_RECONSTRUCTION_SUCCESS_ADAPTER_V1"


def _items(value: Any, *, allow_empty: bool = False) -> list[str] | None:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return None
    out: list[str] = []
    for raw in value:
        item = str(raw or "").strip()
        if not item:
            return None
        if item not in out:
            out.append(item)
    if not allow_empty and not out:
        return None
    return out


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


def _checkpoint(root: Path, relative: str) -> Mapping[str, Any] | None:
    rel = Path(str(relative or "").strip())
    if not rel.as_posix() or rel.is_absolute() or ".." in rel.parts:
        return None
    try:
        target = (root / rel).resolve(strict=True)
        target.relative_to(root)
    except Exception:
        return None
    if not target.is_file() or target.is_symlink():
        return None
    try:
        doc = json.loads(target.read_text(encoding="utf-8"))
    except Exception:
        return None
    return doc if isinstance(doc, Mapping) else None


def adapt(
    request: Mapping[str, Any],
    *,
    repo_root: str | Path,
) -> Mapping[str, Any] | None:
    """Build a conservative bound-success candidate from retained checkpoint proof."""
    try:
        if not isinstance(request, Mapping):
            return None
        observation = request.get("observation")
        replay = request.get("replay_context")
        if not isinstance(observation, Mapping) or not isinstance(replay, Mapping):
            return None
        if str(replay.get("mode") or "").strip() in {"compiled_bound", "raw_bound"}:
            return None
        # Preserve the already-verified native structural acquisition path.
        # This adapter is a strict fallback for misses outside that admitted class.
        if structural.preflight(request, repo_root=repo_root) is not None:
            return None

        material = _proof_material(observation)
        if not isinstance(material, Mapping):
            return None
        selected = _items(material.get("selected_plan"))
        targets = _items(material.get("verified_target_effects"))
        checkpoint_binding = material.get("controller_checkpoint")
        if (
            selected is None
            or targets is None
            or not isinstance(checkpoint_binding, Mapping)
        ):
            return None

        checkpoint_path = str(checkpoint_binding.get("path") or "").strip()
        plan_sha256 = str(checkpoint_binding.get("plan_sha256") or "").strip()
        if len(plan_sha256) != 64:
            return None

        root = Path(repo_root).resolve(strict=True)
        doc = _checkpoint(root, checkpoint_path)
        if (
            not isinstance(doc, Mapping)
            or doc.get("schema") != "PROJECT_BRAIN_CONTROLLER_CHECKPOINT_V1"
            or doc.get("status") != "COMPLETE"
            or doc.get("plan_sha256") != plan_sha256
        ):
            return None

        completed = doc.get("completed_actions")
        if not isinstance(completed, list) or len(completed) != len(selected) + 1:
            return None
        finish = completed[-1]
        if (
            not isinstance(finish, Mapping)
            or not isinstance(finish.get("plan"), Mapping)
            or finish["plan"].get("type") != "finish"
        ):
            return None

        initial_facts: list[str] = []
        produced: set[str] = set()
        for index, capability_id in enumerate(selected):
            row = completed[index]
            if not isinstance(row, Mapping):
                return None
            plan = row.get("plan")
            result = row.get("result")
            if (
                not isinstance(plan, Mapping)
                or plan.get("type") != "invoke_verified_bound_capability_adapter"
                or not isinstance(result, Mapping)
                or result.get("pass") is not True
            ):
                return None
            args = plan.get("args")
            if (
                not isinstance(args, Mapping)
                or str(args.get("capability_id") or "").strip() != capability_id
            ):
                return None
            requires = _items(args.get("requires", []), allow_empty=True)
            provides = _items(args.get("provides"))
            if requires is None or provides is None:
                return None
            for fact in requires:
                if fact not in produced and fact not in initial_facts:
                    initial_facts.append(fact)
            produced.update(provides)

        if any(target not in produced for target in targets):
            return None

        raw = replay.get("request")
        if not isinstance(raw, Mapping):
            raw = replay.get("problem")
        task_id = ""
        if isinstance(raw, Mapping):
            task_id = str(raw.get("task_id") or "").strip()
        if not task_id:
            task_id = str(material.get("task_id") or "").strip()
        if not task_id:
            task_id = str(observation.get("observation_id") or "").strip()
        if not task_id:
            return None

        normalized = deepcopy(dict(replay))
        normalized["mode"] = "compiled_bound"
        normalized["request"] = {
            "task_id": task_id,
            "initial_facts": initial_facts,
            "target_effects": targets,
        }
        candidate = bound.adapt(
            {
                **dict(request),
                "observation": observation,
                "replay_context": normalized,
            },
            repo_root=repo_root,
        )
        if not isinstance(candidate, Mapping):
            return None

        out = deepcopy(dict(candidate))
        out["schema"] = SCHEMA
        out["status"] = "CHECKPOINT_RECONSTRUCTION_SUCCESS_EPISODE_CANDIDATE_READY"
        out["reconstructed_preconditions"] = initial_facts
        out["reconstructed_postconditions"] = targets
        out["reconstruction_basis"] = (
            "VERIFIED_CHECKPOINT_DECLARED_REQUIRES_PROVIDES_PLUS_RETAINED_VERIFIED_TARGET_EFFECTS"
        )
        out["candidate_only"] = True
        out["execution_authority"] = False
        out["verification_authority"] = False
        out["promotion_authority"] = False
        out["terminal_authority"] = False
        return out
    except Exception:
        return None
