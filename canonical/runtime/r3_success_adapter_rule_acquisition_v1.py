"""Native Root1 provider for constrained R3 success-adapter frontier expansion.

This provider cannot author Python and cannot modify verifier authority. It can
only append a predeclared adapter rule for direct R2 route classes whose
independent verifier implementation already exists in canonical bytes.
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import autonomous_verified_self_improvement_v1 as learning
from canonical.runtime import r2_direct_end_to_end_adequacy_v1 as direct
from canonical.runtime.r3_direct_r2_success_adapter_v1 import (
    RULES_PATH, VERIFICATION_KIND,
)

SCHEMA = "PROJECT_BRAIN_R3_SUCCESS_ADAPTER_RULE_ACQUISITION_V1"
PROVIDER_ID = "BRAIN_NATIVE_R3_ADAPTER_RULE_ACQUISITION_V1"
SUPPORTED_ROUTES = frozenset({
    direct.EXACT_LITERAL_ROUTE_ID,
    direct.LITERAL_JSON_ROUTE_ID,
})


def _canon(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return sha256(_canon(value)).hexdigest()


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "NO_ADMISSIBLE_NATIVE_ADAPTER_RULE_ACQUISITION",
        "pass": False,
        "reason": reason,
        "candidate_generation_authority": False,
        "verification_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        **extra,
    }


def can_acquire(
    work: Mapping[str, Any],
    *,
    state_path: str | Path,
) -> bool:
    """Return True only for the exact preverified native rule-acquisition scope."""
    try:
        if not isinstance(work, Mapping) or work.get("kind") != "EXPAND_SUCCESS_VERIFICATION_FRONTIER":
            return False
        payload = work.get("payload")
        if not isinstance(payload, Mapping):
            return False
        observation_id = str(payload.get("observation_id") or "").strip()
        if not observation_id:
            return False
        state = learning.load_state(state_path)
        observation = state.get("observations", {}).get(observation_id)
        if not isinstance(observation, Mapping):
            return False
        replay_capsule = observation.get("replay_capsule")
        proof_capsule = observation.get("proof_capsule")
        replay = replay_capsule.get("context") if isinstance(replay_capsule, Mapping) else None
        material = proof_capsule.get("material") if isinstance(proof_capsule, Mapping) else None
        return bool(
            isinstance(replay, Mapping)
            and replay.get("mode") == "decision"
            and isinstance(material, Mapping)
            and material.get("proof_kind") == "R2_DIRECT_ADEQUACY_READONLY_REVERIFY_V1"
            and str(material.get("route_id") or "") in SUPPORTED_ROUTES
        )
    except Exception:
        return False


def acquire(
    request: Mapping[str, Any],
    *,
    state_path: str | Path,
    repo_root: str | Path,
) -> dict[str, Any]:
    try:
        if not isinstance(request, Mapping):
            return _fail("REQUEST_NOT_OBJECT")
        if request.get("kind") != "EXPAND_SUCCESS_VERIFICATION_FRONTIER":
            return _fail("REQUEST_KIND_NOT_ADMITTED")
        if (
            request.get("allowed_frontier_change_class")
            != "SUCCESS_ADAPTER_ONLY__VERIFICATION_AUTHORITY_IMMUTABLE"
            or request.get("verification_authority_change_allowed") is not False
        ):
            return _fail("AUTHORITY_FIREWALL_NOT_PROVED")
        observation_id = str(request.get("observation_id") or "").strip()
        if not observation_id:
            return _fail("OBSERVATION_ID_REQUIRED")

        state = learning.load_state(state_path)
        observation = state.get("observations", {}).get(observation_id)
        if not isinstance(observation, Mapping):
            return _fail("OBSERVATION_NOT_FOUND")
        replay_capsule = observation.get("replay_capsule")
        proof_capsule = observation.get("proof_capsule")
        replay = replay_capsule.get("context") if isinstance(replay_capsule, Mapping) else None
        material = proof_capsule.get("material") if isinstance(proof_capsule, Mapping) else None
        if not isinstance(replay, Mapping) or not isinstance(material, Mapping):
            return _fail("PROOF_AND_REPLAY_MATERIAL_REQUIRED")
        if replay.get("mode") != "decision":
            return _fail("REPLAY_MODE_NOT_DIRECT_DECISION")
        if material.get("proof_kind") != "R2_DIRECT_ADEQUACY_READONLY_REVERIFY_V1":
            return _fail("DIRECT_R2_PROOF_KIND_NOT_AVAILABLE")
        route_id = str(material.get("route_id") or "")
        if route_id not in SUPPORTED_ROUTES:
            return _fail(
                "NO_PREVERIFIED_RULE_TEMPLATE_FOR_ROUTE",
                route_id=route_id or None,
            )

        root = Path(repo_root).resolve(strict=True)
        target = (root / RULES_PATH).resolve(strict=True)
        target.relative_to(root)
        raw = target.read_bytes()
        doc = json.loads(raw.decode("utf-8"))
        if (
            not isinstance(doc, Mapping)
            or doc.get("schema") != "PROJECT_BRAIN_R3_SUCCESS_ADAPTER_RULES_V1"
            or doc.get("version") != 1
            or not isinstance(doc.get("rules"), list)
        ):
            return _fail("RULE_FRONTIER_INVALID")

        rules = [dict(x) for x in doc["rules"] if isinstance(x, Mapping)]
        if any(
            row.get("status") == "ACTIVE"
            and row.get("route_id") == route_id
            and row.get("verification_kind") == VERIFICATION_KIND
            for row in rules
        ):
            return _fail("ADMISSIBLE_RULE_ALREADY_ACTIVE", route_id=route_id)

        rule_core = {
            "adapter_class": "DIRECT_R2_READONLY_ACCEPTANCE_V1",
            "route_id": route_id,
            "verification_kind": VERIFICATION_KIND,
            "source_observation_id": observation_id,
            "source_proof_capsule_sha256": proof_capsule.get("sha256"),
            "source_replay_capsule_sha256": replay_capsule.get("sha256"),
        }
        rule = {
            "rule_id": "r3-adapter-rule:" + _sha(rule_core),
            "status": "ACTIVE",
            **rule_core,
            "candidate_only": True,
            "verification_authority": False,
            "promotion_authority": False,
            "terminal_authority": False,
        }
        rules.append(rule)
        rules.sort(key=lambda row: str(row.get("rule_id") or ""))
        new_doc = {
            "schema": "PROJECT_BRAIN_R3_SUCCESS_ADAPTER_RULES_V1",
            "version": 1,
            "rules": rules,
        }
        payload = json.dumps(new_doc, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        tmp = target.with_name(target.name + ".tmp")
        tmp.write_text(payload, encoding="utf-8")
        os.replace(tmp, target)
        after = sha256(target.read_bytes()).hexdigest()
        before = sha256(raw).hexdigest()
        if after == before:
            return _fail("RULE_FRONTIER_DID_NOT_CHANGE", route_id=route_id)

        return {
            "schema": SCHEMA,
            "status": "PASS__NATIVE_ADAPTER_RULE_ACQUIRED",
            "pass": True,
            "provider_id": PROVIDER_ID,
            "route_id": route_id,
            "rule_id": rule["rule_id"],
            "rule_frontier_sha256_before": before,
            "rule_frontier_sha256_after": after,
            "candidate_generation_authority": True,
            "source_patch_execution_authority": False,
            "verification_authority": False,
            "promotion_authority": False,
            "terminal_authority": False,
        }
    except Exception as exc:
        return _fail(type(exc).__name__ + ":" + str(exc))
