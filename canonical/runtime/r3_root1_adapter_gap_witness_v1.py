from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime import autonomous_verified_self_improvement_v1 as learning
from canonical.runtime import r3_bound_success_adapter_v1 as bound_adapter
from canonical.runtime import r3_raw_success_adapter_v1 as raw_adapter
from canonical.runtime import root1_acquisition_closure_controller_v3 as root1

SCHEMA = "PROJECT_BRAIN_R3_ROOT1_ADAPTER_GAP_WITNESS_V1"
FRONTIER_KIND = "EXPAND_SUCCESS_VERIFICATION_FRONTIER"
BLOCKED_KIND = "ADAPT_SUCCESS_TO_VERIFIABLE_EPISODE"
REQUIRED_PRIMITIVE = "R3_SUCCESS_ADAPTER_PATCH_AUTHOR"

SUCCESS_ADAPTER_FRONTIER_PATHS = (
    "canonical/runtime/r3_bound_success_adapter_v1.py",
    "canonical/runtime/r3_raw_success_adapter_v1.py",
)
SUCCESS_VERIFICATION_AUTHORITY_PATHS = (
    "canonical/runtime/r3_independent_learning_verifier_v1.py",
    "canonical/runtime/r3_bound_success_checkpoint_verifier_v1.py",
    "canonical/runtime/r3_raw_success_checkpoint_verifier_v1.py",
)


class AdapterGapWitnessError(ValueError):
    pass


def _canon(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canon(value)).hexdigest()


def _frontier_sha256(
    paths: Sequence[str],
    *,
    repo_root: str | Path,
) -> str:
    root = Path(repo_root).resolve(strict=True)
    rows: list[dict[str, str]] = []
    for relative in paths:
        target = (root / relative).resolve(strict=True)
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise AdapterGapWitnessError(
                "FRONTIER_PATH_ESCAPES_REPOSITORY:" + relative
            ) from exc
        if not target.is_file() or target.is_symlink():
            raise AdapterGapWitnessError(
                "FRONTIER_FILE_INVALID:" + relative
            )
        rows.append({
            "path": relative,
            "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        })
    return hashlib.sha256(_canon(rows)).hexdigest()


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "pass": False,
        "reason": reason,
        "root1_positive_gap_established": False,
        "execution_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        **extra,
    }


def compile_gap(
    work: Mapping[str, Any],
    *,
    state_path: str | Path,
    repo_root: str | Path,
    acquisition_provider_bound: bool,
) -> dict[str, Any]:
    """Compile one parked R3 adapter miss into constructive Root1 gap evidence.

    This function grants no acquisition or promotion authority. It proves only the
    currently bound fact: the exact retained success cannot be adapted by either
    owned success adapter under the unchanged adapter/verifier frontier, and no
    acquisition provider is currently bound to this handoff.
    """
    if not isinstance(work, Mapping):
        return _fail("WORK_NOT_OBJECT")
    if acquisition_provider_bound:
        return _fail("ACQUISITION_PROVIDER_ALREADY_BOUND__GAP_COMPILER_NOT_AUTHORITY")

    wid = str(work.get("work_id") or "").strip()
    if not wid:
        return _fail("WORK_ID_REQUIRED")

    try:
        state = learning.load_state(state_path)
        queue = state.get("improvement_queue")
        observations = state.get("observations")
        if not isinstance(queue, Mapping) or not isinstance(observations, Mapping):
            return _fail("R3_STATE_INVALID")

        canonical = queue.get(wid)
        if (
            not isinstance(canonical, Mapping)
            or canonical.get("kind") != FRONTIER_KIND
            or canonical.get("status") != "PENDING"
        ):
            return _fail("FRONTIER_HANDOFF_NOT_CURRENT_PENDING_WORK")

        payload = canonical.get("payload")
        if not isinstance(payload, Mapping):
            return _fail("FRONTIER_HANDOFF_PAYLOAD_INVALID")
        blocked_id = str(payload.get("blocked_success_work_id") or "").strip()
        observation_id = str(payload.get("observation_id") or "").strip()
        if not blocked_id or not observation_id:
            return _fail("FRONTIER_HANDOFF_IDENTITY_INCOMPLETE")

        blocked = queue.get(blocked_id)
        if (
            not isinstance(blocked, Mapping)
            or blocked.get("kind") != BLOCKED_KIND
            or blocked.get("status") != "PARKED"
            or blocked.get("frontier_expansion_work_id") != wid
            or blocked.get("parked_reason") != "NO_CURRENT_OWNED_VERIFICATION_PATH"
        ):
            return _fail("BLOCKED_SUCCESS_WORK_NOT_CURRENT_PARKED_ADAPTER_GAP")

        observation = observations.get(observation_id)
        if not isinstance(observation, Mapping):
            return _fail("SUCCESS_OBSERVATION_MISSING")
        if observation.get("observation_id") != observation_id:
            return _fail("SUCCESS_OBSERVATION_ID_MISMATCH")
        if (
            observation.get("learning_disposition_reason")
            != "OWNED_SUCCESS_ADAPTER_RETURNED_NO_CANDIDATE"
            or observation.get("frontier_expansion_work_id") != wid
        ):
            return _fail("SUCCESS_OBSERVATION_NOT_PROVEN_ADAPTER_FRONTIER_MISS")

        proof = learning.get_success_proof_context(
            observation_id,
            state_path=state_path,
        )
        replay = learning.get_success_replay_context(
            observation_id,
            state_path=state_path,
        )

        adapter_sha = _frontier_sha256(
            SUCCESS_ADAPTER_FRONTIER_PATHS,
            repo_root=repo_root,
        )
        authority_sha = _frontier_sha256(
            SUCCESS_VERIFICATION_AUTHORITY_PATHS,
            repo_root=repo_root,
        )
        stored_adapter = str(payload.get("adapter_frontier_sha256") or "")
        stored_authority = str(payload.get("verification_authority_sha256") or "")
        if (
            stored_adapter != adapter_sha
            or str(blocked.get("adapter_frontier_sha256") or "") != adapter_sha
            or str(observation.get("adapter_frontier_sha256") or "") != adapter_sha
        ):
            return _fail(
                "SUCCESS_ADAPTER_FRONTIER_CHANGED__REACTIVATE_BEFORE_ROOT1_GAP"
            )
        if (
            stored_authority != authority_sha
            or str(blocked.get("verification_authority_sha256") or "") != authority_sha
            or str(observation.get("verification_authority_sha256") or "") != authority_sha
        ):
            return _fail("VERIFICATION_AUTHORITY_FRONTIER_CHANGED")

        adapter_request = {
            "kind": "SUCCESS_TO_CANONICAL_EPISODE_CANDIDATE",
            "observation": deepcopy(dict(observation)),
            "replay_context": deepcopy(dict(replay["context"])),
            "improvement_work_id": blocked_id,
            "authority_requested": "CANDIDATE_ONLY",
        }
        bound_candidate = bound_adapter.adapt(
            adapter_request,
            repo_root=repo_root,
        )
        raw_candidate = raw_adapter.adapt(
            adapter_request,
            repo_root=repo_root,
        )
        if isinstance(bound_candidate, Mapping) or isinstance(raw_candidate, Mapping):
            return _fail(
                "OWNED_ADAPTER_CANDIDATE_NOW_AVAILABLE__ROOT1_GAP_NOT_ESTABLISHED"
            )

        registry_path = (
            Path(repo_root).resolve(strict=True)
            / "canonical"
            / "runtime"
            / "BOUND_CAPABILITY_REGISTRY_V1.json"
        )
        registry_raw = registry_path.read_bytes()
        registry_doc = json.loads(registry_raw.decode("utf-8"))
        registry_caps = (
            registry_doc.get("capabilities")
            if isinstance(registry_doc, Mapping)
            else None
        )
        if not isinstance(registry_caps, Mapping):
            return _fail("BOUND_CAPABILITY_REGISTRY_INVALID")
        exact_owned = sorted(
            str(capability_id)
            for capability_id, row in registry_caps.items()
            if isinstance(row, Mapping)
            and row.get("status") == "VERIFIED_BOUND_CAPABILITY"
            and REQUIRED_PRIMITIVE in {
                str(effect)
                for effect in (row.get("provides") or [])
                if isinstance(effect, str)
            }
        )
        if exact_owned:
            return _fail(
                "EXACT_ADAPTER_AUTHORING_PRIMITIVE_ALREADY_VERIFIED_OWNED",
                verified_capability_ids=exact_owned,
            )

        witness_core = {
            "blocked_success_work_id": blocked_id,
            "frontier_handoff_work_id": wid,
            "observation_id": observation_id,
            "output_sha256": observation.get("output_sha256"),
            "proof_capsule_sha256": proof.get("proof_capsule_sha256"),
            "replay_capsule_sha256": replay.get("replay_capsule_sha256"),
            "adapter_frontier_sha256": adapter_sha,
            "verification_authority_sha256": authority_sha,
            "bound_capability_registry_sha256": hashlib.sha256(
                registry_raw
            ).hexdigest(),
            "required_primitive": REQUIRED_PRIMITIVE,
        }
        witness_id = "r3-root1-adapter-gap:" + _sha(witness_core)

        gap_evidence = {
            "positive_operational_gap": True,
            "constructive_witness_verified": True,
            "constructive_witness_content_addressed": True,
            "operative_failure_demonstrated": True,
            "acquisition_routes_accounted": True,
            "unresolved_after_available_acquisition": True,
            "required_behavior": (
                "Author or bind a candidate R3 success adapter for the exact retained "
                "success while modifying only the owned success-adapter frontier and "
                "leaving independent verification authority unchanged."
            ),
            "witness_id": witness_id,
            "witness": witness_core,
            "currently_bound_frontier_acquisition_provider_present": False,
            "current_owned_adapter_frontier_exhausted_for_witness": True,
            "exact_required_primitive_verified_owned": False,
            "claim_scope": (
                "CURRENT_BOUND_R3_SUCCESS_ADAPTER_FRONTIER_AND_CURRENTLY_BOUND_"
                "ACQUISITION_PROVIDER_SET_ONLY"
            ),
        }

        transaction = root1.root1_atomic_transaction(
            gap_evidence=gap_evidence,
            required_primitives=[REQUIRED_PRIMITIVE],
            verified_primitives=[],
            transfer_mappings=(),
            search_actions=(),
            acquisition_routes=(),
        )
        gate = transaction.get("gate")
        if not isinstance(gate, Mapping) or gate.get("root1_active") is not True:
            return _fail(
                "ROOT1_CONSTRUCTIVE_GAP_GATE_DID_NOT_REOPEN",
                gap_evidence=gap_evidence,
                root1_transaction=transaction,
            )
        delta = transaction.get("minimum_delta")
        if (
            not isinstance(delta, Mapping)
            or delta.get("missing_primitives") != [REQUIRED_PRIMITIVE]
        ):
            return _fail(
                "ROOT1_MINIMUM_DELTA_NOT_EXACT_ADAPTER_AUTHOR_PRIMITIVE",
                gap_evidence=gap_evidence,
                root1_transaction=transaction,
            )

        return {
            "schema": SCHEMA,
            "status": (
                "PASS__ROOT1_CONSTRUCTIVE_R3_ADAPTER_AUTHORING_GAP_ESTABLISHED__"
                "NO_CURRENT_BOUND_ACQUISITION_ROUTE"
            ),
            "pass": True,
            "root1_positive_gap_established": True,
            "required_primitive": REQUIRED_PRIMITIVE,
            "witness_id": witness_id,
            "witness": witness_core,
            "gap_evidence": gap_evidence,
            "root1_transaction": transaction,
            "adapter_frontier_sha256": adapter_sha,
            "verification_authority_sha256": authority_sha,
            "current_bound_acquisition_route_count": 0,
            "execution_authority": False,
            "promotion_authority": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }
    except Exception as exc:
        return _fail(
            "ROOT1_ADAPTER_GAP_WITNESS_EXCEPTION:"
            + type(exc).__name__
            + ":"
            + str(exc)
        )
