"""Atomic promotion of one independently verified R2 direct route into live state V1."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping

from canonical.runtime import r2_direct_live_dispatcher_v1 as live

SCHEMA = "PROJECT_BRAIN_PROMOTE_R2_DIRECT_LIVE_ROUTE_V1"
CANDIDATE_SCHEMA = "PROJECT_BRAIN_R2_DIRECT_ROUTE_DEPLOYMENT_CANDIDATE_V1"
RECEIPT_SCHEMA = "PROJECT_BRAIN_R2_DIRECT_LIVE_DEPLOYMENT_INDEPENDENT_RECEIPT_V1"
SELECTION_CLASS = "UNIQUE_MATCH_REQUIRED"
ROOT = Path(__file__).resolve().parents[2]
CURRENT_POINTER = ROOT / "canonical/governance/CURRENT_R2_DIRECT_LIVE_STATE.json"

_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_CALLABLE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$")


class R2DirectLivePromotionError(RuntimeError):
    pass


def _git_blob_sha_bytes(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def _git_blob_sha(path: Path) -> str:
    return _git_blob_sha_bytes(path.read_bytes())


def _json_bytes(value: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(
            dict(value),
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _inside(
    root: Path,
    raw: Any,
    *,
    prefixes: tuple[str, ...],
    label: str,
) -> tuple[str, Path]:
    value = str(raw or "").strip()
    rel = Path(value)
    if not value or rel.is_absolute() or ".." in rel.parts:
        raise R2DirectLivePromotionError(label + "_PATH_INVALID")
    if not any(value.startswith(prefix) for prefix in prefixes):
        raise R2DirectLivePromotionError(label + "_PATH_SCOPE_INVALID:" + value)
    resolved_root = root.resolve()
    full = (resolved_root / rel).resolve()
    if full == resolved_root or resolved_root not in full.parents:
        raise R2DirectLivePromotionError(label + "_PATH_OUTSIDE_REPOSITORY")
    if not full.is_file() or full.is_symlink():
        raise R2DirectLivePromotionError(label + "_FILE_REQUIRED:" + value)
    return value, full


def _load_json(path: Path, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise R2DirectLivePromotionError(label + "_JSON_INVALID") from exc
    if not isinstance(value, Mapping):
        raise R2DirectLivePromotionError(label + "_JSON_OBJECT_REQUIRED")
    return dict(value)


def _sha40(value: Any, *, label: str) -> str:
    text = str(value or "").strip().lower()
    if not _SHA40.fullmatch(text):
        raise R2DirectLivePromotionError(label + "_SHA_INVALID")
    return text


def _callable(value: Any, *, label: str) -> str:
    text = str(value or "").strip()
    if not _CALLABLE.fullmatch(text):
        raise R2DirectLivePromotionError(label + "_CALLABLE_INVALID")
    return text


def _verify_file(
    root: Path,
    rel: Any,
    expected: Any,
    *,
    prefixes: tuple[str, ...],
    label: str,
) -> tuple[str, Path, str]:
    rel_text, path = _inside(root, rel, prefixes=prefixes, label=label)
    expected_sha = _sha40(expected, label=label)
    actual = _git_blob_sha(path)
    if actual != expected_sha:
        raise R2DirectLivePromotionError(
            label + "_BLOB_MISMATCH:" + expected_sha + "!=" + actual
        )
    return rel_text, path, actual


def _validate_candidate(
    root: Path,
    candidate_path: str,
) -> tuple[dict[str, Any], str]:
    candidate_rel, candidate_file = _inside(
        root,
        candidate_path,
        prefixes=("canonical/governance/",),
        label="CANDIDATE",
    )
    candidate_sha = _git_blob_sha(candidate_file)
    candidate = _load_json(candidate_file, label="CANDIDATE")
    if candidate.get("schema") != CANDIDATE_SCHEMA:
        raise R2DirectLivePromotionError("CANDIDATE_SCHEMA_INVALID")
    if candidate.get("deployment_requested") is not True:
        raise R2DirectLivePromotionError("CANDIDATE_DEPLOYMENT_NOT_REQUESTED")
    if candidate.get("selection_class") != SELECTION_CLASS:
        raise R2DirectLivePromotionError("CANDIDATE_SELECTION_CLASS_INVALID")
    if candidate.get("incremental_spend_usd") != 0:
        raise R2DirectLivePromotionError("CANDIDATE_INCREMENTAL_SPEND_NOT_ZERO")
    if candidate.get("terminal_authority") is not False:
        raise R2DirectLivePromotionError("CANDIDATE_TERMINAL_AUTHORITY_FORBIDDEN")
    if candidate.get("semantic_open_barrier") not in (True, False):
        raise R2DirectLivePromotionError("CANDIDATE_SEMANTIC_OPEN_BARRIER_INVALID")

    route_id = str(candidate.get("route_id") or "").strip()
    if not route_id:
        raise R2DirectLivePromotionError("CANDIDATE_ROUTE_ID_REQUIRED")
    capability_id = candidate.get("capability_id")
    if capability_id is not None and not isinstance(capability_id, str):
        raise R2DirectLivePromotionError("CANDIDATE_CAPABILITY_ID_INVALID")
    scope = str(candidate.get("scope") or "").strip()
    if not scope:
        raise R2DirectLivePromotionError("CANDIDATE_SCOPE_REQUIRED")

    runtime_rel, _, runtime_sha = _verify_file(
        root,
        candidate.get("runtime_path"),
        candidate.get("runtime_git_blob_sha"),
        prefixes=("canonical/runtime/",),
        label="CANDIDATE_RUNTIME",
    )
    verification_rel, verification_file, verification_sha = _verify_file(
        root,
        candidate.get("route_verification_path"),
        candidate.get("route_verification_git_blob_sha"),
        prefixes=("canonical/verification/",),
        label="CANDIDATE_ROUTE_VERIFICATION",
    )
    verification = _load_json(
        verification_file,
        label="CANDIDATE_ROUTE_VERIFICATION",
    )
    status = str(verification.get("status") or "")
    if verification.get("pass") is not True and not (
        status.startswith("PASS") or "VERIFIED" in status
    ):
        raise R2DirectLivePromotionError(
            "CANDIDATE_ROUTE_VERIFICATION_NOT_POSITIVE"
        )
    if verification.get("terminal_authority") is True:
        raise R2DirectLivePromotionError(
            "CANDIDATE_ROUTE_VERIFICATION_TERMINAL_AUTHORITY_FORBIDDEN"
        )

    return {
        "candidate_path": candidate_rel,
        "candidate_git_blob_sha": candidate_sha,
        "route_id": route_id,
        "capability_id": capability_id,
        "runtime_path": runtime_rel,
        "runtime_git_blob_sha": runtime_sha,
        "preflight_callable": _callable(
            candidate.get("preflight_callable"),
            label="PREFLIGHT",
        ),
        "run_callable": _callable(
            candidate.get("run_callable"),
            label="RUN",
        ),
        "verification_path": verification_rel,
        "verification_git_blob_sha": verification_sha,
        "scope": scope,
        "selection_class": SELECTION_CLASS,
        "semantic_open_barrier": bool(candidate["semantic_open_barrier"]),
    }, candidate_sha


def _validate_receipt(
    root: Path,
    receipt_path: str,
    *,
    candidate: Mapping[str, Any],
    candidate_sha: str,
) -> tuple[str, str]:
    receipt_rel, receipt_file = _inside(
        root,
        receipt_path,
        prefixes=("canonical/verification/",),
        label="RECEIPT",
    )
    receipt_sha = _git_blob_sha(receipt_file)
    receipt = _load_json(receipt_file, label="RECEIPT")
    expected = {
        "schema": RECEIPT_SCHEMA,
        "status": "INDEPENDENT_PASS__R2_DIRECT_LIVE_DEPLOYMENT",
        "candidate_path": candidate["candidate_path"],
        "candidate_git_blob_sha": candidate_sha,
        "route_id": candidate["route_id"],
        "runtime_path": candidate["runtime_path"],
        "runtime_git_blob_sha": candidate["runtime_git_blob_sha"],
        "route_verification_path": candidate["verification_path"],
        "route_verification_git_blob_sha": candidate["verification_git_blob_sha"],
        "selection_class": SELECTION_CLASS,
        "semantic_open_barrier": candidate["semantic_open_barrier"],
        "semantic_open_barrier_authorized": candidate["semantic_open_barrier"],
        "independent_verified": True,
        "preflight_pure_no_effect": True,
        "matched_route_failure_no_fallthrough": True,
        "producer_independent_acceptance": True,
        "exact_raw_obligation_acceptance": True,
        "deployment_eligible": True,
        "verification_authority_mutated": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "incremental_spend_usd": 0,
    }
    for key, value in expected.items():
        if receipt.get(key) != value:
            raise R2DirectLivePromotionError(
                "RECEIPT_BINDING_MISMATCH:" + key
            )
    return receipt_rel, receipt_sha


def _binding_matches(
    existing: Mapping[str, Any],
    candidate: Mapping[str, Any],
    receipt_rel: str,
    receipt_sha: str,
) -> bool:
    expected = {
        "route_id": candidate["route_id"],
        "capability_id": candidate["capability_id"],
        "runtime_path": candidate["runtime_path"],
        "runtime_git_blob_sha": candidate["runtime_git_blob_sha"],
        "preflight_callable": candidate["preflight_callable"],
        "run_callable": candidate["run_callable"],
        "verification_path": candidate["verification_path"],
        "verification_git_blob_sha": candidate["verification_git_blob_sha"],
        "candidate_path": candidate["candidate_path"],
        "candidate_git_blob_sha": candidate["candidate_git_blob_sha"],
        "independent_receipt_path": receipt_rel,
        "independent_receipt_git_blob_sha": receipt_sha,
        "scope": candidate["scope"],
        "selection_class": SELECTION_CLASS,
        "semantic_open_barrier": candidate["semantic_open_barrier"],
    }
    return all(existing.get(key) == value for key, value in expected.items())


def _replay_selected(
    *,
    root: Path,
    pointer: Path,
    replay_request: Mapping[str, Any],
    route_id: str,
) -> dict[str, Any]:
    replay = live.preflight(
        replay_request,
        repo_root=root,
        pointer_path=pointer,
    )
    if (
        replay.get("matched") is not True
        or replay.get("route_id") != route_id
        or replay.get("_live_route_source") != "DYNAMIC"
    ):
        raise R2DirectLivePromotionError(
            "POSTCOMMIT_DEFAULT_REPLAY_DID_NOT_SELECT_PROMOTED_ROUTE:"
            + str(replay.get("status") or replay.get("reason") or "UNKNOWN")
        )
    return replay


def _atomic_write(path: Path, raw: bytes) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(raw)
    tmp.replace(path)


def promote(
    *,
    candidate_path: str,
    receipt_path: str,
    replay_request: Mapping[str, Any],
    repo_root: str | Path = ROOT,
    pointer_path: str | Path | None = None,
) -> dict[str, Any]:
    if not isinstance(replay_request, Mapping):
        raise R2DirectLivePromotionError("REPLAY_REQUEST_OBJECT_REQUIRED")
    if not str(replay_request.get("task_id") or "").strip() or not str(
        replay_request.get("goal") or ""
    ).strip():
        raise R2DirectLivePromotionError("REPLAY_TASK_ID_AND_GOAL_REQUIRED")

    root = Path(repo_root).resolve()
    pointer = (
        Path(pointer_path).resolve()
        if pointer_path is not None
        else root / "canonical/governance/CURRENT_R2_DIRECT_LIVE_STATE.json"
    )
    pointer_before = pointer.read_bytes()
    current = live.load_state(repo_root=root, pointer_path=pointer)
    candidate, candidate_sha = _validate_candidate(root, candidate_path)
    receipt_rel, receipt_sha = _validate_receipt(
        root,
        receipt_path,
        candidate=candidate,
        candidate_sha=candidate_sha,
    )
    candidate["candidate_git_blob_sha"] = candidate_sha
    route_id = str(candidate["route_id"])

    baseline_ids = set(current["baseline"]["declared_route_ids"])
    if route_id in baseline_ids:
        raise R2DirectLivePromotionError(
            "ROUTE_ID_ALREADY_OWNED_BY_BASELINE:" + route_id
        )

    existing = [
        row
        for row in current["dynamic_routes"]
        if str(row.get("route_id") or "") == route_id
    ]
    if existing:
        if len(existing) != 1 or not _binding_matches(
            existing[0],
            candidate,
            receipt_rel,
            receipt_sha,
        ):
            raise R2DirectLivePromotionError(
                "ROUTE_ID_ALREADY_LIVE_WITH_DIFFERENT_BINDING:" + route_id
            )
        replay = _replay_selected(
            root=root,
            pointer=pointer,
            replay_request=replay_request,
            route_id=route_id,
        )
        return {
            "schema": SCHEMA,
            "status": "ALREADY_LIVE_EXACT_BINDING",
            "pass": True,
            "frontier_changed": False,
            "route_id": route_id,
            "new_generation": current["generation"],
            "postcommit_default_routable": True,
            "replay_route_id": replay.get("route_id"),
            "verification_authority_mutated": False,
            "incremental_spend_usd": 0,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }

    row = {
        "route_id": route_id,
        "capability_id": candidate["capability_id"],
        "runtime_path": candidate["runtime_path"],
        "runtime_git_blob_sha": candidate["runtime_git_blob_sha"],
        "preflight_callable": candidate["preflight_callable"],
        "run_callable": candidate["run_callable"],
        "verification_path": candidate["verification_path"],
        "verification_git_blob_sha": candidate["verification_git_blob_sha"],
        "candidate_path": candidate["candidate_path"],
        "candidate_git_blob_sha": candidate_sha,
        "independent_receipt_path": receipt_rel,
        "independent_receipt_git_blob_sha": receipt_sha,
        "scope": candidate["scope"],
        "selection_class": SELECTION_CLASS,
        "semantic_open_barrier": candidate["semantic_open_barrier"],
        "active": True,
        "automatic_live_admission": True,
        "collision_policy": (
            "FAIL_CLOSED_ON_BASELINE_OR_OTHER_DYNAMIC_ENGAGEMENT"
        ),
    }

    new_state = {
        key: deepcopy(value)
        for key, value in current.items()
        if not key.startswith("_")
    }
    new_state["generation"] = int(current["generation"]) + 1
    new_state["dynamic_routes"] = [
        deepcopy(dict(existing_row))
        for existing_row in current["dynamic_routes"]
    ] + [row]
    new_state["dynamic_routes"].sort(key=lambda x: str(x["route_id"]))

    raw = _json_bytes(new_state)
    state_sha = _git_blob_sha_bytes(raw)
    state_rel = (
        "canonical/governance/R2_DIRECT_LIVE_STATE_"
        + state_sha[:16]
        + ".json"
    )
    state_target = (root / state_rel).resolve()
    if root != state_target and root not in state_target.parents:
        raise R2DirectLivePromotionError("NEW_STATE_TARGET_OUTSIDE_REPOSITORY")
    state_target.parent.mkdir(parents=True, exist_ok=True)
    if state_target.exists():
        if state_target.read_bytes() != raw:
            raise R2DirectLivePromotionError(
                "CONTENT_ADDRESSED_STATE_TARGET_CONFLICT"
            )
    else:
        _atomic_write(state_target, raw)

    pointer_doc = {
        "schema": live.POINTER_SCHEMA,
        "date": "2026-10-09",
        "status": "ACTIVE_CURRENT_R2_DIRECT_LIVE_STATE_POINTER",
        "binding_semantics": (
            "MUTABLE_CURRENT_POINTER_PATH_IDENTITY__"
            "IMMUTABLE_TARGET_GIT_BLOB_BOUND"
        ),
        "target": {
            "path": state_rel,
            "git_blob_sha": state_sha,
            "schema": live.STATE_SCHEMA,
        },
        "incremental_spend_usd": 0,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    pointer_raw = _json_bytes(pointer_doc)

    try:
        _atomic_write(pointer, pointer_raw)
        observed = live.load_state(repo_root=root, pointer_path=pointer)
        if (
            observed.get("generation") != new_state["generation"]
            or observed.get("_target_git_blob_sha") != state_sha
        ):
            raise R2DirectLivePromotionError(
                "POSTCOMMIT_CURRENT_POINTER_RELOAD_FAILED"
            )
        replay = _replay_selected(
            root=root,
            pointer=pointer,
            replay_request=replay_request,
            route_id=route_id,
        )
    except Exception:
        _atomic_write(pointer, pointer_before)
        raise

    basis = {
        "route_id": route_id,
        "previous_state_git_blob_sha": current["_target_git_blob_sha"],
        "new_state_git_blob_sha": state_sha,
        "new_state_path": state_rel,
        "new_generation": new_state["generation"],
        "current_pointer_path": str(pointer.relative_to(root)),
        "candidate_path": candidate["candidate_path"],
        "candidate_git_blob_sha": candidate_sha,
        "independent_receipt_path": receipt_rel,
        "independent_receipt_git_blob_sha": receipt_sha,
        "replay_task_id": replay_request.get("task_id"),
        "frontier_changed": True,
        "verification_authority_mutated": False,
    }
    receipt_digest = hashlib.sha256(
        json.dumps(
            basis,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()
    return {
        "schema": SCHEMA,
        "status": (
            "PASS__R2_DIRECT_ROUTE_PROMOTED__CURRENT_POINTER_SWAPPED__"
            "DEFAULT_REPLAY_SELECTED_PROMOTED_ROUTE"
        ),
        "pass": True,
        **basis,
        "postcommit_default_routable": True,
        "replay_route_id": replay.get("route_id"),
        "promotion_receipt_sha256": receipt_digest,
        "promotion_executed": True,
        "incremental_spend_usd": 0,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
