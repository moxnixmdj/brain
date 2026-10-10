"""Professional P1 Router V10: V9 plus exact R12 totality-verifier pinning.

V9 correctly requires executable semantic verification before any positive
certificate, but the semantic-verifier reference itself is caller-bound. V10
closes that control-plane substitution surface by requiring the exact canonical
R12 V2 totality verifier before V9 is allowed to execute a supplied verifier.

This is a strict fail-closed refinement:
* abstention/non-positive behavior is preserved;
* an exact canonical verifier may proceed to V9 unchanged;
* any foreign or stale semantic verifier is rejected before import/execution.

The module grants no semantic, quality, acceptance, promotion, or terminal
authority by itself.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import professional_quality_p1_router_v9 as base

SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_P1_ROUTER_V10"
APPROVED_TOTALITY_VERIFIER_PATH = (
    "canonical/runtime/professional_r12_v9_policy_cover_totality_semantic_verify_v2.py"
)
APPROVED_TOTALITY_VERIFIER_BLOB = "08ee0e1a82162032daadf002f6364b2b10a86ed3"
REQUIRED_V10_COMPONENTS = frozenset({
    "canonical/runtime/professional_quality_p1_router_v10.py",
    APPROVED_TOTALITY_VERIFIER_PATH,
})


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "semantic_truth_authority": False,
        "execution_authority": False,
        "quality_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
        **extra,
    }


def approved_totality_verifier_ref() -> dict[str, str]:
    return {
        "path": APPROVED_TOTALITY_VERIFIER_PATH,
        "git_blob_sha": APPROVED_TOTALITY_VERIFIER_BLOB,
    }


def _v10_subject_ok(ref: Any, *, root: Path) -> dict[str, Any]:
    prior = base._v9_subject_ok(ref, root=root)
    if prior.get("pass") is not True:
        return {
            "pass": False,
            "reason": "V9_SUBJECT_REJECTED",
            "v9_subject_state": prior,
        }
    doc, state = base.base._load_subject(ref, root=root)
    if doc is None:
        return {
            "pass": False,
            "reason": "V10_DECLARED_SYSTEM_SUBJECT_LOAD_FAILED",
            "subject_state": state,
        }
    components = (doc.get("system_material") or {}).get("components") or []
    paths = {
        row.get("path")
        for row in components
        if isinstance(row, Mapping)
    }
    missing = sorted(REQUIRED_V10_COMPONENTS - paths)
    if missing:
        return {
            "pass": False,
            "reason": "V10_LOAD_BEARING_COMPONENTS_NOT_IN_SUBJECT",
            "missing": missing,
        }
    pinned = [
        row
        for row in components
        if isinstance(row, Mapping)
        and row.get("path") == APPROVED_TOTALITY_VERIFIER_PATH
    ]
    if len(pinned) != 1:
        return {
            "pass": False,
            "reason": "V10_APPROVED_TOTALITY_VERIFIER_COMPONENT_NONUNIQUE",
        }
    if pinned[0].get("git_blob_sha") != APPROVED_TOTALITY_VERIFIER_BLOB:
        return {
            "pass": False,
            "reason": "V10_APPROVED_TOTALITY_VERIFIER_COMPONENT_STALE",
        }
    return {
        "pass": True,
        "subject_id": state.get("subject_id"),
        "subject_sha256": state.get("subject_sha256"),
        "subject_git_blob_sha": state.get("subject_git_blob_sha"),
    }


def _preflight_totality_verifier(state: Mapping[str, Any]) -> dict[str, Any]:
    bindings = state.get(base.base.STEP_BINDINGS_KEY)
    if not isinstance(bindings, Mapping):
        return {"pass": True, "verifier_present": False, "verifier_pinned": False}
    final = bindings.get(base.base.FINAL_STEP)
    if not isinstance(final, Mapping):
        return {"pass": True, "verifier_present": False, "verifier_pinned": False}
    supplied = final.get("material_totality_semantic_verifier")
    if supplied is None:
        return {"pass": True, "verifier_present": False, "verifier_pinned": False}
    if not isinstance(supplied, Mapping):
        return {"pass": False, "reason": "V10_TOTALITY_VERIFIER_REF_NOT_OBJECT"}
    expected = approved_totality_verifier_ref()
    if dict(supplied) != expected:
        return {
            "pass": False,
            "reason": "V10_UNAPPROVED_R12_TOTALITY_VERIFIER_REJECTED_PREEXECUTION",
            "expected": expected,
            "observed": dict(supplied),
        }
    return {"pass": True, "verifier_present": True, "verifier_pinned": True}


def route(state: Mapping[str, Any], *, repo_root: str | Path | None = None) -> dict[str, Any]:
    if not isinstance(state, Mapping):
        return _fail("STATE_NOT_OBJECT")
    root = (
        Path(repo_root).resolve()
        if repo_root is not None
        else Path(__file__).resolve().parents[2]
    )
    subject = _v10_subject_ok(state.get(base.base.SUBJECT_REF_KEY), root=root)
    if subject.get("pass") is not True:
        return _fail(
            "V10_DECLARED_SYSTEM_SUBJECT_INVALID",
            subject_verification=subject,
        )

    preflight = _preflight_totality_verifier(state)
    if preflight.get("pass") is not True:
        return _fail(
            str(preflight.get("reason") or "V10_TOTALITY_VERIFIER_PREFLIGHT_FAILED"),
            totality_verifier_preflight=preflight,
        )

    out = base.route(state, repo_root=root)
    if not isinstance(out, Mapping):
        return _fail("V9_RESULT_NOT_OBJECT")
    result = deepcopy(dict(out))
    result["schema"] = SCHEMA

    positive = (
        result.get("final_step_outcome") == "POSITIVE_CERTIFICATE"
        or result.get("positive_certification_authorized") is True
    )
    if positive and preflight.get("verifier_pinned") is not True:
        return _fail(
            "V10_POSITIVE_PATH_WITHOUT_PREEXECUTION_EXACT_VERIFIER_PIN",
            v9_result=result,
        )
    if positive and result.get("v9_executable_r12_totality_semantics_verified") is not True:
        return _fail(
            "V10_POSITIVE_PATH_WITHOUT_V9_EXECUTABLE_TOTALITY_SEMANTICS",
            v9_result=result,
        )

    result["v10_exact_r12_totality_verifier_pinned"] = (
        preflight.get("verifier_pinned") is True
    )
    result["v10_totality_verifier_preflight"] = preflight
    result["semantic_truth_authority"] = False
    result["quality_authority"] = False
    result["acceptance_authority"] = False
    result["promotion_authority"] = False
    result["terminal_authority"] = False
    result["terminal_credit_delta"] = 0
    result["incremental_spend_usd"] = 0
    return result


def run(args: Mapping[str, Any] | None = None, root: Any = None) -> dict[str, Any]:
    return route(args or {}, repo_root=root)
