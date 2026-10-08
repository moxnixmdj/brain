"""One-shot verified closure runner for the live Project Brain.

This controller does not manufacture terminal credit. It executes every currently
owned fail-closed closure mechanism that is safe to run synchronously, then emits
an exact fixed-point cut:
- INTERNAL_ACTIONABLE: Brain-owned repair/acquisition/proof work still exists.
- EXTERNAL_INFORMATION: the selected policy-changing fact is not currently owned.
- ACCEPTANCE_EVIDENCE: checkpoint evidence remains open but is not, by itself, a
  proved capability deficit.

A PASS means only that no currently identified *internal* residual remains after
the owned closure machinery reaches a fixed point. It never means omniscience or
permanent optimality.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha1, sha256
import json
from pathlib import Path
import re
from typing import Any, Callable, Mapping

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_ONE_SHOT_VERIFIED_CLOSURE_V1"

R2_POINTER = "canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json"
TERMINAL_POINTER = "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
PROOF_QUOTIENT = "canonical/governance/FROZEN_19_ACCEPTANCE_PROOF_SHAPE_QUOTIENT_20261007_V1.json"

_EXTERNAL_MARKERS = (
    "FRESH_EXTERNAL_REALITY",
    "DECISIVE_REALITY_NOT_CURRENTLY_OBSERVABLE",
    "EXTERNAL_REQUIRED",
)
_INTERNAL_MARKERS = (
    "NEW_POLICY_OR_STRONGER_ADEQUACY_EVIDENCE",
    "NEW_SOURCE_ALIGNED_PROOF_PRIMITIVE",
    "GENUINELY_NEW_R3_PRIMITIVE",
    "CAPABILITY",
    "ADEQUACY",
    "PROOF_PRIMITIVE",
)


class OneShotClosureError(ValueError):
    pass


def _canon(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha256_obj(value: Any) -> str:
    return sha256(_canon(value).encode("utf-8")).hexdigest()


def _inside(root: Path, relative: str) -> Path:
    rel = Path(str(relative or "").strip())
    if not rel.as_posix() or rel.is_absolute() or ".." in rel.parts:
        raise OneShotClosureError("PATH_INVALID:" + str(relative))
    target = (root / rel).resolve(strict=False)
    target.relative_to(root.resolve(strict=True))
    return target


def _read_json(root: Path, relative: str) -> dict[str, Any]:
    path = _inside(root, relative)
    if not path.is_file() or path.is_symlink():
        raise OneShotClosureError("JSON_FILE_MISSING_OR_UNSAFE:" + relative)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise OneShotClosureError("JSON_NOT_OBJECT:" + relative)
    return value


def _git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def _binding_status(root: Path, binding: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(binding, Mapping):
        return {"pass": False, "reason": "BINDING_NOT_OBJECT"}
    relative = str(binding.get("path") or "").strip()
    expected = str(binding.get("git_blob_sha") or "").strip().lower()
    if not relative or not re.fullmatch(r"[0-9a-f]{40}", expected):
        return {"pass": False, "reason": "BINDING_IDENTITY_INVALID"}
    try:
        path = _inside(root, relative)
        if not path.is_file() or path.is_symlink():
            return {"pass": False, "reason": "BOUND_FILE_MISSING_OR_UNSAFE", "path": relative}
        actual = _git_blob_sha(path)
    except Exception as exc:
        return {
            "pass": False,
            "reason": type(exc).__name__ + ":" + str(exc),
            "path": relative,
        }
    return {
        "pass": actual == expected,
        "path": relative,
        "expected_git_blob_sha": expected,
        "actual_git_blob_sha": actual,
        "reason": None if actual == expected else "CONTENT_ADDRESS_DRIFT",
    }


def _classify_r2_edge(edge: Any) -> dict[str, Any]:
    text = str(edge or "").strip()
    upper = text.upper()
    if any(marker in upper for marker in _EXTERNAL_MARKERS):
        cls = "EXTERNAL_INFORMATION"
    elif any(marker in upper for marker in _INTERNAL_MARKERS):
        cls = "INTERNAL_ACTIONABLE"
    else:
        cls = "INTERNAL_ACTIONABLE"
    return {"edge": text, "class": cls}


def _latest_r3_receipt(root: Path) -> tuple[str | None, dict[str, Any] | None]:
    base = root / "canonical" / "verification"
    if not base.is_dir():
        return None, None
    best: tuple[int, Path] | None = None
    pat = re.compile(
        r"^R3_AUTONOMOUS_VERIFIED_COMPOUNDING_LOOP_IMPLEMENTATION_20261008_V(\d+)\.json$"
    )
    for path in base.iterdir():
        match = pat.match(path.name)
        if match and path.is_file() and not path.is_symlink():
            row = (int(match.group(1)), path)
            if best is None or row[0] > best[0]:
                best = row
    if best is None:
        return None, None
    relative = best[1].resolve().relative_to(root.resolve()).as_posix()
    value = json.loads(best[1].read_text(encoding="utf-8"))
    return relative, value if isinstance(value, dict) else None


def _r3_receipt_freshness(root: Path) -> dict[str, Any]:
    relative, receipt = _latest_r3_receipt(root)
    if relative is None or not isinstance(receipt, Mapping):
        return {
            "pass": False,
            "receipt_path": relative,
            "reason": "R3_CLOSURE_RECEIPT_MISSING",
            "drift": [],
        }
    exact = receipt.get("exact_live_blobs")
    if not isinstance(exact, Mapping) or not exact:
        return {
            "pass": False,
            "receipt_path": relative,
            "reason": "R3_EXACT_LIVE_BLOBS_MISSING",
            "drift": [],
        }
    drift = []
    for path_text, expected_raw in sorted(exact.items()):
        expected = str(expected_raw or "").lower()
        try:
            path = _inside(root, str(path_text))
            actual = _git_blob_sha(path)
        except Exception as exc:
            drift.append({
                "path": path_text,
                "expected_git_blob_sha": expected,
                "actual_git_blob_sha": None,
                "reason": type(exc).__name__ + ":" + str(exc),
            })
            continue
        if actual != expected:
            drift.append({
                "path": path_text,
                "expected_git_blob_sha": expected,
                "actual_git_blob_sha": actual,
                "reason": "CONTENT_ADDRESS_DRIFT",
            })
    return {
        "pass": not drift,
        "receipt_path": relative,
        "receipt_status": receipt.get("status"),
        "drift": drift,
        "reason": None if not drift else "R3_RECEIPT_NOT_EXACT_CURRENT_BYTES",
    }


def _authority_snapshot(root: Path) -> dict[str, Any]:
    from canonical.runtime import r2_direct_end_to_end_adequacy_v1 as direct

    r2 = _read_json(root, R2_POINTER)
    terminal = _read_json(root, TERMINAL_POINTER)

    scheduler = _binding_status(root, r2.get("scheduler_cut"))
    direct_info = r2.get("direct_adequacy")
    direct_info = direct_info if isinstance(direct_info, Mapping) else {}
    activation_binding = {
        "path": direct_info.get("activation_path"),
        "git_blob_sha": direct_info.get("activation_git_blob_sha"),
    }
    activation = _binding_status(root, activation_binding)
    declared_routes = int(direct_info.get("current_route_count") or 0)
    runtime_routes = len(getattr(direct, "ROUTES", {}))
    route_coherent = declared_routes == runtime_routes and declared_routes > 0

    terminal_live = terminal.get("live_truth")
    terminal_live = terminal_live if isinstance(terminal_live, Mapping) else {}
    terminal_scheduler = str(terminal_live.get("current_r2_scheduler_cut") or "")
    current_scheduler_name = Path(str((r2.get("scheduler_cut") or {}).get("path") or "")).stem
    terminal_coherent = not terminal_scheduler or terminal_scheduler == current_scheduler_name

    return {
        "pass": bool(
            scheduler.get("pass")
            and activation.get("pass")
            and route_coherent
            and terminal_coherent
        ),
        "scheduler_binding": scheduler,
        "direct_activation_binding": activation,
        "declared_direct_route_count": declared_routes,
        "runtime_direct_route_count": runtime_routes,
        "direct_route_count_coherent": route_coherent,
        "terminal_r2_scheduler_cut": terminal_scheduler or None,
        "current_r2_scheduler_name": current_scheduler_name or None,
        "terminal_pointer_coherent": terminal_coherent,
        "r2": r2,
        "terminal": terminal,
    }


def _checkpoint_snapshot(root: Path, terminal: Mapping[str, Any]) -> dict[str, Any]:
    live = terminal.get("live_truth")
    live = live if isinstance(live, Mapping) else {}
    quotient = {}
    path = root / PROOF_QUOTIENT
    if path.is_file() and not path.is_symlink():
        quotient = _read_json(root, PROOF_QUOTIENT)
    obligations = quotient.get("independent_open_obligations")
    if not isinstance(obligations, list):
        obligations = []
    return {
        "accepted_family_count": int(live.get("frozen_terminal_family_pass_count") or 0),
        "open_family_count": int(live.get("frozen_terminal_family_open_count") or 0),
        "proved_atomic_predicate_count": int(live.get("frozen_atomic_predicates_proved") or 0),
        "unresolved_atomic_predicate_count": int(live.get("frozen_atomic_predicates_unresolved") or 0),
        "independent_open_evidence_obligations": deepcopy(obligations),
        "independent_open_evidence_obligation_count": len(obligations),
        "classification": "ACCEPTANCE_EVIDENCE_NOT_AUTOMATIC_CAPABILITY_DEFICIT",
    }


def _r3_drain_to_fixed_point(
    *,
    root: Path,
    state_path: str | Path | None,
    max_rounds: int,
    max_actions_per_round: int,
    episode_verification_provider=None,
    skill_verification_provider=None,
    success_episode_adapter_provider=None,
    failure_repair_provider=None,
    verification_frontier_acquisition_provider=None,
    verification_frontier_acquisition_provider_id: str,
) -> dict[str, Any]:
    from canonical.runtime import autonomous_verified_self_improvement_v1 as learning
    from canonical.runtime import r3_improvement_queue_driver_v1 as driver

    path = learning.DEFAULT_STATE_PATH if state_path is None else Path(state_path)
    rounds: list[dict[str, Any]] = []
    made_progress = False
    for index in range(max_rounds):
        out = driver.drain(
            state_path=path,
            repo_root=root,
            episode_verification_provider=episode_verification_provider,
            skill_verification_provider=skill_verification_provider,
            success_episode_adapter_provider=success_episode_adapter_provider,
            failure_repair_provider=failure_repair_provider,
            verification_frontier_acquisition_provider=verification_frontier_acquisition_provider,
            verification_frontier_acquisition_provider_id=(
                verification_frontier_acquisition_provider_id
            ),
            max_actions=max_actions_per_round,
        )
        if not isinstance(out, Mapping):
            raise OneShotClosureError("R3_DRAIN_RESULT_NOT_OBJECT")
        row = deepcopy(dict(out))
        row["closure_round"] = index + 1
        rounds.append(row)
        progress = out.get("progress") is True
        made_progress = made_progress or progress
        if not progress:
            break
    else:
        return {
            "pass": False,
            "fixed_point_reached": False,
            "made_progress": made_progress,
            "rounds": rounds,
            "last": rounds[-1] if rounds else None,
            "reason": "R3_CLOSURE_ROUND_BOUND_EXHAUSTED",
        }

    last = rounds[-1] if rounds else {}
    return {
        "pass": True,
        "fixed_point_reached": True,
        "made_progress": made_progress,
        "rounds": rounds,
        "last": last,
        "reason": None,
    }


def run(
    request: Mapping[str, Any] | None = None,
    *,
    repo_root: str | Path = ROOT,
    state_path: str | Path | None = None,
    episode_verification_provider=None,
    skill_verification_provider=None,
    success_episode_adapter_provider=None,
    failure_repair_provider=None,
    verification_frontier_acquisition_provider: Callable[
        [Mapping[str, Any]], Mapping[str, Any] | None
    ] | None = None,
    verification_frontier_acquisition_provider_id: str = (
        "HOST_VERIFICATION_FRONTIER_ACQUISITION_PROVIDER"
    ),
) -> dict[str, Any]:
    """Execute owned closure machinery to a verified current fixed point."""
    request = {} if request is None else request
    if not isinstance(request, Mapping):
        raise OneShotClosureError("REQUEST_NOT_OBJECT")
    root = Path(repo_root).resolve(strict=True)
    max_rounds = int(request.get("max_rounds", 32))
    max_actions = int(request.get("max_actions_per_round", 8))
    if not 1 <= max_rounds <= 256:
        raise OneShotClosureError("MAX_ROUNDS_INVALID")
    if not 1 <= max_actions <= 64:
        raise OneShotClosureError("MAX_ACTIONS_PER_ROUND_INVALID")

    from canonical.runtime import unified_cognitive_fabric_v1 as fabric

    before_catalog = fabric.catalog()
    authority_before = _authority_snapshot(root)
    r3_before = _r3_receipt_freshness(root)

    drain = _r3_drain_to_fixed_point(
        root=root,
        state_path=state_path,
        max_rounds=max_rounds,
        max_actions_per_round=max_actions,
        episode_verification_provider=episode_verification_provider,
        skill_verification_provider=skill_verification_provider,
        success_episode_adapter_provider=success_episode_adapter_provider,
        failure_repair_provider=failure_repair_provider,
        verification_frontier_acquisition_provider=(
            verification_frontier_acquisition_provider
        ),
        verification_frontier_acquisition_provider_id=(
            verification_frontier_acquisition_provider_id
        ),
    )

    after_catalog = fabric.catalog()
    authority_after = _authority_snapshot(root)
    r3_after = _r3_receipt_freshness(root)
    r2 = authority_after["r2"]
    terminal = authority_after["terminal"]

    internal: list[dict[str, Any]] = []
    external: list[dict[str, Any]] = []

    if after_catalog.get("r1_structural_closure") is not True:
        internal.append({
            "root": "R1",
            "class": "LIVE_ARCHITECTURE_OR_INVOCATION_CLOSURE",
            "details": deepcopy(after_catalog.get("known_r1_residuals") or []),
        })
    if authority_after.get("pass") is not True:
        internal.append({
            "root": "AUTHORITY",
            "class": "CURRENT_RUNTIME_AUTHORITY_COHERENCE",
            "details": {
                "scheduler_binding": authority_after["scheduler_binding"],
                "direct_activation_binding": authority_after["direct_activation_binding"],
                "direct_route_count_coherent": authority_after["direct_route_count_coherent"],
                "terminal_pointer_coherent": authority_after["terminal_pointer_coherent"],
            },
        })
    if r3_after.get("pass") is not True:
        internal.append({
            "root": "R3",
            "class": "EXACT_CURRENT_CLOSURE_RECEIPT_FRESHNESS",
            "details": r3_after,
        })

    remaining = r2.get("remaining_hard_frontier")
    if not isinstance(remaining, list):
        remaining = []
    for edge in remaining:
        classified = _classify_r2_edge(edge)
        target = external if classified["class"] == "EXTERNAL_INFORMATION" else internal
        target.append({
            "root": "R2",
            **classified,
        })

    last = drain.get("last")
    if isinstance(last, Mapping):
        blockers = last.get("blockers_skipped")
        if isinstance(blockers, list):
            for blocker in blockers:
                text = _canon(blocker).upper() if isinstance(blocker, Mapping) else str(blocker).upper()
                target = external if any(x in text for x in _EXTERNAL_MARKERS) else internal
                target.append({
                    "root": "R3_QUEUE",
                    "class": (
                        "EXTERNAL_INFORMATION"
                        if target is external
                        else "INTERNAL_ACTIONABLE"
                    ),
                    "details": deepcopy(blocker),
                })

    checkpoint = _checkpoint_snapshot(root, terminal)
    fixed_point = drain.get("fixed_point_reached") is True
    internally_closed = fixed_point and not internal
    status = (
        "PASS__MAXIMAL_VERIFIED_FIXED_POINT__EXTERNAL_OR_ACCEPTANCE_EVIDENCE_RESIDUALS_ONLY"
        if internally_closed
        else "OPEN__INTERNAL_ACTIONABLE_RESIDUALS_REMAIN"
    )
    result = {
        "schema": SCHEMA,
        "status": status,
        "pass": internally_closed,
        "fixed_point_reached": fixed_point,
        "internal_actionable_residual_count": len(internal),
        "internal_actionable_residuals": internal,
        "external_information_residual_count": len(external),
        "external_information_residuals": external,
        "checkpoint": checkpoint,
        "r1_before": {
            "closed": before_catalog.get("r1_structural_closure") is True,
            "live_owned_capability_count": before_catalog.get("live_owned_capability_count"),
            "verified_learned_skill_count": before_catalog.get("verified_learned_skill_count"),
        },
        "r1_after": {
            "closed": after_catalog.get("r1_structural_closure") is True,
            "live_owned_capability_count": after_catalog.get("live_owned_capability_count"),
            "verified_learned_skill_count": after_catalog.get("verified_learned_skill_count"),
        },
        "authority_before": {
            k: deepcopy(v) for k, v in authority_before.items() if k not in {"r2", "terminal"}
        },
        "authority_after": {
            k: deepcopy(v) for k, v in authority_after.items() if k not in {"r2", "terminal"}
        },
        "r3_receipt_before": r3_before,
        "r3_receipt_after": r3_after,
        "r3_drain": drain,
        "result_sha256": None,
        "incremental_spend_usd": 0,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "hard_nonclaims": [
            "NO_CLAIM_ALL_EXTERNAL_REALITY_IS_OBSERVABLE",
            "NO_CLAIM_OPEN_CHECKPOINT_EVIDENCE_EQUALS_CAPABILITY_DEFICIT",
            "NO_CLAIM_PERMANENT_GLOBAL_OPTIMALITY",
            "NO_SELF_CERTIFICATION",
        ],
    }
    digest_view = deepcopy(result)
    digest_view.pop("result_sha256", None)
    result["result_sha256"] = _sha256_obj(digest_view)
    return result


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
