"""Rule-gated normalization of proof-bearing successes into the existing bound verifier.

This adapter grants no verification or promotion authority. It is deliberately
narrow: a replay wrapper may differ, but the retained checkpoint/proof must already
be accepted by r3_bound_success_adapter_v1 after normalization.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import r3_bound_success_adapter_v1 as bound

SCHEMA = "PROJECT_BRAIN_R3_STRUCTURAL_BOUND_SUCCESS_ADAPTER_V1"
RULES_PATH = "canonical/runtime/R3_STRUCTURAL_BOUND_ADAPTER_RULES_V1.json"


def _canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False, default=str)


def _sha(value: Any) -> str:
    return sha256(_canon(value).encode("utf-8")).hexdigest()


def _normalized_request(request: Mapping[str, Any]) -> Mapping[str, Any] | None:
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
    target = raw.get("target_effects")
    if not isinstance(target, list) or not target:
        return None
    normalized = dict(replay)
    normalized["mode"] = "compiled_bound"
    normalized["request"] = dict(raw)
    return {
        **dict(request),
        "observation": observation,
        "replay_context": normalized,
    }


def preflight(request: Mapping[str, Any], *, repo_root: str | Path) -> Mapping[str, Any] | None:
    normalized = _normalized_request(request)
    if normalized is None:
        return None
    return bound.adapt(normalized, repo_root=repo_root)


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
        candidate = preflight(request, repo_root=repo_root)
        if candidate is None:
            return None
        out = dict(candidate)
        out["schema"] = SCHEMA
        out["status"] = "STRUCTURAL_BOUND_SUCCESS_EPISODE_CANDIDATE_READY"
        out["structural_rule_id"] = matches[0].get("rule_id")
        out["candidate_only"] = True
        out["execution_authority"] = False
        out["promotion_authority"] = False
        out["terminal_authority"] = False
        return out
    except Exception:
        return None
