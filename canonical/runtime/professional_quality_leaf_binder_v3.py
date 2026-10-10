"""Professional-quality leaf binder V3.

V3 preserves V2 execution-leaf behavior and adds one mandatory semantic-leaf
admission layer: a V2-admissible semantic receipt is still OPEN unless its
embedded semantic_property_truth_candidate passes the current, mission-bound
semantic property-truth admission gate.

This prevents a generic leaf receipt from self-certifying universal semantic
truth with leaf_semantic_satisfied=true while omitting current claim identity,
defeater totality, positive-issuance totality, or claim-scoped closure.

No new leaf truth is created by this binder. It only constrains admission.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import professional_quality_leaf_binder_v2 as base
from canonical.runtime import professional_semantic_property_truth_admission_v1 as semantic_gate

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_LEAF_BINDER_V3"


def _semantic_candidate_verdict(
    *,
    repo_root: Path,
    receipt_result: Mapping[str, Any],
) -> dict[str, Any] | None:
    if receipt_result.get("kind") != "SEMANTIC" or receipt_result.get("admitted") is not True:
        return None
    path_text = receipt_result.get("path")
    path = base._resolve(repo_root, path_text)
    if path is None or not path.is_file() or path.is_symlink():
        return {
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": "SEMANTIC_RECEIPT_NOT_READABLE_FOR_V3_ADMISSION",
            "leaf_property_truth_admissible": False,
        }
    try:
        receipt = base._load(path)
    except Exception:
        return {
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": "SEMANTIC_RECEIPT_JSON_INVALID_FOR_V3_ADMISSION",
            "leaf_property_truth_admissible": False,
        }
    candidate = receipt.get("semantic_property_truth_candidate")
    if not isinstance(candidate, Mapping):
        return {
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": "SEMANTIC_PROPERTY_TRUTH_CANDIDATE_REQUIRED",
            "leaf_property_truth_admissible": False,
        }
    if candidate.get("leaf_id") != receipt_result.get("leaf_id"):
        return {
            "pass": False,
            "status": "FAIL_CLOSED",
            "reason": "SEMANTIC_PROPERTY_TRUTH_CANDIDATE_LEAF_MISMATCH",
            "leaf_property_truth_admissible": False,
        }
    return semantic_gate.verify_candidate(candidate, repo_root=repo_root)


def harden_base_output(
    base_output: Mapping[str, Any],
    *,
    repo_root: Path = ROOT,
) -> dict[str, Any]:
    out = deepcopy(dict(base_output))
    results = deepcopy(list(out.get("receipt_results") or []))

    semantic_gate_results: list[dict[str, Any]] = []
    for row in results:
        if not isinstance(row, dict):
            continue
        verdict = _semantic_candidate_verdict(repo_root=repo_root, receipt_result=row)
        if verdict is None:
            continue
        semantic_gate_results.append({
            "leaf_id": row.get("leaf_id"),
            "path": row.get("path"),
            "verdict": verdict,
        })
        if verdict.get("pass") is not True or verdict.get("leaf_property_truth_admissible") is not True:
            row["admitted"] = False
            errors = row.get("errors")
            if not isinstance(errors, list):
                errors = []
                row["errors"] = errors
            errors.append("SEMANTIC_PROPERTY_TRUTH_ADMISSION_FAILED")
            row["semantic_property_truth_admission"] = verdict
        else:
            row["semantic_property_truth_admission"] = verdict

    semantic_leaf_ids = set(out.get("verified_semantic_leaf_ids") or []) | set(
        out.get("open_semantic_leaf_ids") or []
    )
    execution_leaf_ids = set(out.get("verified_execution_leaf_ids") or []) | set(
        out.get("open_execution_leaf_ids") or []
    )

    admitted_by_leaf: dict[str, bool] = {
        leaf: False for leaf in semantic_leaf_ids | execution_leaf_ids
    }
    for row in results:
        if isinstance(row, Mapping) and row.get("admitted") is True:
            leaf = row.get("leaf_id")
            if isinstance(leaf, str) and leaf in admitted_by_leaf:
                admitted_by_leaf[leaf] = True

    verified_semantic = sorted(x for x in semantic_leaf_ids if admitted_by_leaf.get(x))
    verified_execution = sorted(x for x in execution_leaf_ids if admitted_by_leaf.get(x))
    open_semantic = sorted(semantic_leaf_ids - set(verified_semantic))
    open_execution = sorted(execution_leaf_ids - set(verified_execution))
    rejected = [x for x in results if isinstance(x, Mapping) and x.get("admitted") is not True]

    structural_errors = list(out.get("structural_errors") or [])
    existing_evidence_current = out.get("existing_evidence_current") is True
    all_leaves_verified = len(verified_semantic) == 12 and len(verified_execution) == 12
    promotion_ready = (
        not structural_errors
        and existing_evidence_current
        and not rejected
        and all_leaves_verified
        and out.get("manifest_status_has_promotion_authority") is False
        and out.get("terminal_authority") is False
    )

    out.update({
        "schema": SCHEMA,
        "status": (
            "PASS__ALL_24_LEAVES_DERIVED_WITH_SEMANTIC_TOTALITY_ADMISSION"
            if promotion_ready
            else "OPEN__LEAF_RECEIPTS_OR_SEMANTIC_TOTALITY_EVIDENCE_REMAIN"
        ),
        "pass": promotion_ready,
        "receipt_results": results,
        "verified_semantic_leaf_ids": verified_semantic,
        "verified_execution_leaf_ids": verified_execution,
        "open_semantic_leaf_ids": open_semantic,
        "open_execution_leaf_ids": open_execution,
        "verified_leaf_count": len(verified_semantic) + len(verified_execution),
        "open_leaf_count": len(open_semantic) + len(open_execution),
        "rejected_receipt_count": len(rejected),
        "promotion_ready": promotion_ready,
        "semantic_property_truth_gate": {
            "runtime": "canonical/runtime/professional_semantic_property_truth_admission_v1.py",
            "current_claim_pack": semantic_gate.PACK_PATH,
            "semantic_receipts_checked": len(semantic_gate_results),
            "semantic_receipts_admitted": sum(
                x["verdict"].get("pass") is True
                and x["verdict"].get("leaf_property_truth_admissible") is True
                for x in semantic_gate_results
            ),
            "semantic_receipts_rejected": sum(
                not (
                    x["verdict"].get("pass") is True
                    and x["verdict"].get("leaf_property_truth_admissible") is True
                )
                for x in semantic_gate_results
            ),
        },
        "semantic_gate_results": semantic_gate_results,
        "semantic_truth_authority": False,
        "execution_authority": False,
        "acceptance_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    })
    return out


def evaluate(
    *,
    manifest_path: Path = base.MANIFEST,
    graph_path: Path = base.GRAPH,
    registry_path: Path = base.REGISTRY,
    repo_root: Path = ROOT,
) -> dict[str, Any]:
    base_out = base.evaluate(
        manifest_path=manifest_path,
        graph_path=graph_path,
        registry_path=registry_path,
        repo_root=repo_root,
    )
    return harden_base_output(base_out, repo_root=repo_root)


if __name__ == "__main__":
    import json
    print(json.dumps(evaluate(), indent=2, sort_keys=True))
