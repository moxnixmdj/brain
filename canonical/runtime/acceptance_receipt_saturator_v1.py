"""Compile existing immutable receipts into atomic Opus 5.5 acceptance evidence bindings.

This compiler grants no capability credit by itself. It is deliberately fail-closed:
- every frozen predicate must have an explicit saturation disposition,
- a receipt can bind only one explicitly named predicate claim,
- every bound claim needs a content-addressed source path/SHA,
- scope_complete and independent_or_objective must both be true,
- proof kind must be admissible for the predicate kind,
- incomplete/insufficient receipts are retained as exclusions so they are never reconsidered.

The output is suitable as OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2 input.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

PREDICATE_TO_PROOF_KINDS = {
    "PUBLIC_FIXED_BAR": {"PUBLIC_BAR_RESULT", "ABSOLUTE_CEILING", "BOUND_DOMINANCE"},
    "ABSOLUTE_CEILING": {"ABSOLUTE_CEILING", "BOUND_DOMINANCE"},
    "DIRECT_SCOPE_AUDIT": {"RECEIPT", "DIRECT_ORACLE", "ABSOLUTE_CEILING", "BOUND_DOMINANCE"},
    "INVARIANT": {"RECEIPT", "DIRECT_ORACLE", "ABSOLUTE_CEILING", "BOUND_DOMINANCE"},
    "DEPENDENCY_PROOF": {"RECEIPT", "DIRECT_ORACLE", "ABSOLUTE_CEILING", "BOUND_DOMINANCE"},
    "MATCHED_NONINFERIORITY": {"MATCHED_COMPARATOR", "ABSOLUTE_CEILING", "BOUND_DOMINANCE"},
    "MATCHED_SCOPE_AUDIT": {"MATCHED_COMPARATOR", "DIRECT_ORACLE", "ABSOLUTE_CEILING", "BOUND_DOMINANCE"},
}

FINAL_SEARCH_STATES = {
    "SEARCHED_EXHAUSTIVELY_NO_MATCH",
    "SEARCHED_EXHAUSTIVELY_MATCH_BOUND",
    "SEARCHED_EXHAUSTIVELY_ONLY_INSUFFICIENT_MATCHES",
}


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _valid_bound_claim(pid: str, pred: Mapping[str, Any], claim: Mapping[str, Any], errors: list[str]) -> bool:
    proof_kind = claim.get("proof_kind")
    allowed = PREDICATE_TO_PROOF_KINDS.get(str(pred.get("kind")), set())
    if proof_kind not in allowed:
        errors.append(f"INADMISSIBLE_PROOF_KIND:{pid}:{proof_kind}")
        return False
    required = {
        "predicate_id": pid,
        "state": "PROVED",
        "source_path": claim.get("source_path"),
        "source_sha": claim.get("source_sha"),
        "independent_or_objective": True,
        "scope_complete": True,
    }
    for key, expected in required.items():
        if claim.get(key) != expected:
            errors.append(f"INVALID_BOUND_CLAIM_FIELD:{pid}:{key}")
            return False
    if not isinstance(claim.get("source_path"), str) or not claim["source_path"]:
        errors.append(f"MISSING_SOURCE_PATH:{pid}")
        return False
    if not isinstance(claim.get("source_sha"), str) or len(claim["source_sha"]) < 7:
        errors.append(f"MISSING_SOURCE_SHA:{pid}")
        return False
    return True


def compile_saturation(registry: Mapping[str, Any], inventory: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    predicates = registry.get("predicates")
    if not isinstance(predicates, list) or not predicates:
        return {
            "schema": "PROJECT_BRAIN_ACCEPTANCE_RECEIPT_SATURATION_VERDICT_V1",
            "status": "FAIL_CLOSED",
            "pass": False,
            "errors": ["PREDICATE_REGISTRY_MISSING"],
        }

    by_id: dict[str, Mapping[str, Any]] = {}
    for pred in predicates:
        if not isinstance(pred, Mapping) or not isinstance(pred.get("id"), str):
            errors.append("INVALID_PREDICATE")
            continue
        by_id[pred["id"]] = pred

    snapshot = inventory.get("source_snapshot_sha")
    if not isinstance(snapshot, str) or not snapshot:
        errors.append("SOURCE_SNAPSHOT_SHA_MISSING")

    dispositions = inventory.get("predicate_dispositions")
    if not isinstance(dispositions, list):
        dispositions = []
        errors.append("PREDICATE_DISPOSITIONS_MISSING")

    disp_by_id: dict[str, Mapping[str, Any]] = {}
    for row in dispositions:
        if not isinstance(row, Mapping):
            errors.append("INVALID_DISPOSITION_ROW")
            continue
        pid = row.get("predicate_id")
        if pid not in by_id:
            errors.append(f"DISPOSITION_UNKNOWN_PREDICATE:{pid}")
            continue
        if pid in disp_by_id:
            errors.append(f"DUPLICATE_DISPOSITION:{pid}")
            continue
        disp_by_id[str(pid)] = row

    claims: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []
    searched = 0

    for pid, pred in sorted(by_id.items()):
        row = disp_by_id.get(pid)
        if row is None:
            continue
        state = row.get("search_state")
        if state in FINAL_SEARCH_STATES:
            searched += 1
        else:
            continue

        bound = row.get("bound_claim")
        if state == "SEARCHED_EXHAUSTIVELY_MATCH_BOUND":
            if not isinstance(bound, Mapping):
                errors.append(f"BOUND_MATCH_WITHOUT_CLAIM:{pid}")
                continue
            candidate = dict(bound)
            candidate["predicate_id"] = pid
            candidate["state"] = "PROVED"
            if _valid_bound_claim(pid, pred, candidate, errors):
                claims.append(candidate)

        insufficient = row.get("insufficient_receipts", [])
        if not isinstance(insufficient, list):
            errors.append(f"INSUFFICIENT_RECEIPTS_INVALID:{pid}")
            continue
        for item in insufficient:
            if not isinstance(item, Mapping):
                errors.append(f"INSUFFICIENT_RECEIPT_ROW_INVALID:{pid}")
                continue
            if not item.get("source_path") or not item.get("source_sha") or not item.get("reason"):
                errors.append(f"INSUFFICIENT_RECEIPT_UNBOUND:{pid}")
                continue
            exclusions.append({
                "predicate_id": pid,
                "source_path": item["source_path"],
                "source_sha": item["source_sha"],
                "reason": item["reason"],
            })

    complete = (
        not errors
        and len(by_id) > 0
        and searched == len(by_id)
        and len(disp_by_id) == len(by_id)
    )

    return {
        "schema": "PROJECT_BRAIN_ACCEPTANCE_RECEIPT_SATURATION_VERDICT_V1",
        "status": "COMPLETE" if complete else "INCOMPLETE_FAIL_CLOSED",
        "pass": complete,
        "errors": sorted(set(errors)),
        "source_snapshot_sha": snapshot if isinstance(snapshot, str) else None,
        "predicate_count": len(by_id),
        "searched_predicate_count": searched,
        "proved_claim_count": len(claims),
        "insufficient_receipt_count": len(exclusions),
        "claims": claims,
        "insufficient_receipts": exclusions,
        "bindings_payload": {
            "schema": "PROJECT_BRAIN_OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2",
            "status": "RECEIPT_SATURATION_COMPLETE" if complete else "RECEIPT_SATURATION_REQUIRED__NO_NEW_REALITY_AUTHORIZED",
            "saturation": {
                "status": "COMPLETE" if complete else "REQUIRED",
                "source_snapshot_sha": snapshot if complete else None,
            },
            "claims": claims,
            "rules": [
                "NO_CLAIM_WITHOUT_CONTENT_ADDRESSED_SOURCE_PATH_AND_SHA",
                "NO_PROVED_CLAIM_WITHOUT_INDEPENDENT_OR_OBJECTIVE_EVIDENCE",
                "NO_PROVED_CLAIM_WITHOUT_SCOPE_COMPLETE_TRUE",
                "BEHAVIORAL_19_OF_19_PASS_DOES_NOT_AUTOPOPULATE_ATOMIC_ACCEPTANCE_CLAIMS",
                "INSUFFICIENT_RECEIPTS_ARE_COMPILED_AS_EXCLUSIONS_NOT_RECONSIDERED",
                "NO_NEW_REALITY_BEFORE_RECEIPT_SATURATION_COMPLETE",
            ],
            "capability_credit_delta": 0,
            "family_credit_delta": 0,
        },
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "incremental_spend_usd": 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("registry", type=Path)
    ap.add_argument("inventory", type=Path)
    args = ap.parse_args()
    result = compile_saturation(_load(args.registry), _load(args.inventory))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not result["errors"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
