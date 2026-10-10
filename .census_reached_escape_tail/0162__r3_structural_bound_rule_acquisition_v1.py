"""Native constrained acquisition for proof-bearing wrapper mismatches.

The provider may only append a rule when the existing bound adapter can already
construct a candidate after wrapper normalization. It cannot author Python,
modify verification authority, or self-certify the resulting episode.
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import autonomous_verified_self_improvement_v1 as learning
from canonical.runtime import r3_structural_bound_success_adapter_v1 as structural
from canonical.runtime import r3_bound_success_adapter_v1 as bound

SCHEMA = "PROJECT_BRAIN_R3_STRUCTURAL_BOUND_RULE_ACQUISITION_V1"
PROVIDER_ID = "BRAIN_NATIVE_STRUCTURAL_BOUND_RULE_ACQUISITION_V1"


def _canon(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False, default=str).encode("utf-8")


def _sha(value: Any) -> str:
    return sha256(_canon(value)).hexdigest()


def _adapter_request(work: Mapping[str, Any], *, state_path: str | Path) -> Mapping[str, Any] | None:
    payload = work.get("payload")
    if not isinstance(payload, Mapping):
        return None
    oid = str(payload.get("observation_id") or "").strip()
    if not oid:
        return None
    state = learning.load_state(state_path)
    obs = state.get("observations", {}).get(oid)
    if not isinstance(obs, Mapping):
        return None
    try:
        replay = learning.get_success_replay_context(oid, state_path=state_path)["context"]
        learning.get_success_proof_context(oid, state_path=state_path)
    except Exception:
        return None
    return {
        "kind": "SUCCESS_TO_CANONICAL_EPISODE_CANDIDATE",
        "observation": dict(obs),
        "replay_context": dict(replay),
        "authority_requested": "CANDIDATE_ONLY",
    }


def can_acquire(
    work: Mapping[str, Any],
    *,
    state_path: str | Path,
    repo_root: str | Path,
) -> bool:
    try:
        if work.get("kind") != "EXPAND_SUCCESS_VERIFICATION_FRONTIER":
            return False
        req = _adapter_request(work, state_path=state_path)
        return bool(req and structural.preflight(req, repo_root=repo_root) is not None)
    except Exception:
        return False


def acquire(
    request: Mapping[str, Any],
    *,
    state_path: str | Path,
    repo_root: str | Path,
) -> dict[str, Any]:
    def fail(reason: str) -> dict[str, Any]:
        return {
            "schema": SCHEMA, "status": "NO_ADMISSIBLE_STRUCTURAL_RULE_ACQUISITION",
            "pass": False, "reason": reason, "verification_authority": False,
            "promotion_authority": False, "terminal_authority": False,
        }
    try:
        if request.get("kind") != "EXPAND_SUCCESS_VERIFICATION_FRONTIER":
            return fail("REQUEST_KIND_NOT_ADMITTED")
        if request.get("verification_authority_change_allowed") is not False:
            return fail("VERIFICATION_AUTHORITY_FIREWALL_REQUIRED")
        work = {"kind": request.get("kind"), "payload": dict(request)}
        # Driver handoff request contains observation_id directly, while can_acquire
        # receives the queue work whose payload contains it.
        oid = str(request.get("observation_id") or "").strip()
        if not oid:
            return fail("OBSERVATION_ID_REQUIRED")
        state = learning.load_state(state_path)
        obs = state.get("observations", {}).get(oid)
        if not isinstance(obs, Mapping):
            return fail("OBSERVATION_NOT_FOUND")
        replay = learning.get_success_replay_context(oid, state_path=state_path)["context"]
        learning.get_success_proof_context(oid, state_path=state_path)
        adapter_request = {
            "kind": "SUCCESS_TO_CANONICAL_EPISODE_CANDIDATE",
            "observation": dict(obs),
            "replay_context": dict(replay),
            "authority_requested": "CANDIDATE_ONLY",
        }
        candidate = structural.preflight(adapter_request, repo_root=repo_root)
        if not isinstance(candidate, Mapping):
            return fail("EXISTING_BOUND_VERIFIER_CONTRACT_NOT_SATISFIED")
        normalization_profile = str(
            candidate.get("structural_normalization_profile") or ""
        ).strip()
        if normalization_profile not in structural.NORMALIZATION_PROFILES:
            return fail("STRUCTURAL_NORMALIZATION_PROFILE_INVALID")

        surface = str(obs.get("surface") or "").strip()
        source_schema = str(obs.get("schema") or "").strip()
        if not surface or not source_schema:
            return fail("OBSERVATION_IDENTITY_INCOMPLETE")

        root = Path(repo_root).resolve(strict=True)
        target = (root / structural.RULES_PATH).resolve(strict=True)
        target.relative_to(root)
        before_raw = target.read_bytes()
        doc = json.loads(before_raw.decode("utf-8"))
        rules = [dict(x) for x in doc.get("rules", []) if isinstance(x, Mapping)]
        if any(
            row.get("status") == "ACTIVE"
            and row.get("surface") == surface
            and row.get("source_schema") == source_schema
            for row in rules
        ):
            return fail("STRUCTURAL_RULE_ALREADY_ACTIVE")
        core = {
            "surface": surface,
            "source_schema": source_schema,
            "verification_kind": bound.VERIFICATION_KIND,
            "normalization_profile": normalization_profile,
            "source_observation_id": oid,
        }
        rule = {
            "rule_id": "r3-structural-bound:" + _sha(core),
            "status": "ACTIVE",
            **core,
            "candidate_only": True,
            "verification_authority": False,
            "promotion_authority": False,
            "terminal_authority": False,
        }
        rules.append(rule)
        rules.sort(key=lambda x: str(x.get("rule_id") or ""))
        out_doc = {
            "schema": "PROJECT_BRAIN_R3_STRUCTURAL_BOUND_ADAPTER_RULES_V1",
            "version": 1,
            "rules": rules,
        }
        tmp = target.with_name(target.name + ".tmp")
        tmp.write_text(json.dumps(out_doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(tmp, target)
        after_raw = target.read_bytes()
        if after_raw == before_raw:
            return fail("ADAPTER_FRONTIER_DID_NOT_CHANGE")
        return {
            "schema": SCHEMA,
            "status": "PASS__STRUCTURAL_BOUND_ADAPTER_RULE_ACQUIRED",
            "pass": True,
            "provider_id": PROVIDER_ID,
            "rule_id": rule["rule_id"],
            "verification_kind": bound.VERIFICATION_KIND,
            "normalization_profile": normalization_profile,
            "adapter_frontier_sha256_before": sha256(before_raw).hexdigest(),
            "adapter_frontier_sha256_after": sha256(after_raw).hexdigest(),
            "candidate_generation_authority": True,
            "verification_authority": False,
            "promotion_authority": False,
            "terminal_authority": False,
        }
    except Exception as exc:
        return fail(type(exc).__name__ + ":" + str(exc))
