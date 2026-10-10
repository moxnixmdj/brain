#!/usr/bin/env python3
"""Executable fail-closed audit for the shared Escape-Progress Gap A/B frontier.

This module does not grant CC_R3 merely because a row has a route description.
It verifies the exact proof obligations already declared by
the current shared-gap binding named by
CURRENT_RESIDUAL_REUSE_CLASSIFICATION_20261010_V1.json:

Gap A admits exactly one of two sound modes:
  - TERMINAL_COMMON_POLICY: a currently available authenticated scope-complete
    Brain-owned safe adequate resource-admissible common policy terminalizes the
    whole current decision region; or
  - STRICT_DISCRIMINATOR: an authenticated currently acquirable safe truthful
    discriminator has a finite complete outcome set and every nonterminal outcome
    strictly shrinks the finite decision region.

Gap B:
  - one executable verified action is bound;
  - one finite well-founded progress measure is bound;
  - every allowed outcome terminalizes or strictly decreases that measure.

The audit is intentionally generic: future row-specific receipts are supplied as
content-addressed proof records. Missing records remain explicit open predicates.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "canonical/governance/ESCAPE_PROGRESS_13_REACHED_STATE_ROUTE_MANIFEST_20261010_V2.json"
CLASSIFIER_RELATIVE_PATH = "canonical/governance/CURRENT_RESIDUAL_REUSE_CLASSIFICATION_20261010_V1.json"

SCHEMA = "PROJECT_BRAIN_ESCAPE_PROGRESS_SHARED_GAP_EXECUTABLE_AUDIT_V3"
GAP_A = "GAP_A_ACQUISITION_TOTALITY"
GAP_B = "GAP_B_INTERNAL_ROUTE_STRICT_PROGRESS"


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


def _current_binding_path(root: Path = ROOT) -> Path:
    """Resolve one current Gap A/B binding from the live residual classifier.

    The current classifier is a mutable pointer by path identity. Both shared
    Escape gaps must name the same versioned binding. Any absence, disagreement,
    path escape, symlink, or non-file fails closed instead of silently auditing
    a historical contract.
    """
    root = Path(root).resolve(strict=True)
    classifier_path = (root / CLASSIFIER_RELATIVE_PATH).resolve(strict=True)
    classifier_path.relative_to(root)
    doc = json.loads(classifier_path.read_text(encoding="utf-8"))
    rows = doc.get("classifications")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        raise ValueError("CURRENT_RESIDUAL_CLASSIFICATIONS_INVALID")

    bindings: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        rid = str(row.get("residual_id") or "")
        if rid not in {GAP_A.replace("GAP_A_", "ESCAPE_GAP_A_"), GAP_B.replace("GAP_B_", "ESCAPE_GAP_B_")}:
            continue
        value = row.get("existing_binding")
        if not isinstance(value, str) or not value.strip():
            raise ValueError("CURRENT_GAP_BINDING_MISSING:" + rid)
        bindings[rid] = value.strip()

    expected_ids = {
        "ESCAPE_GAP_A_ACQUISITION_TOTALITY",
        "ESCAPE_GAP_B_INTERNAL_ROUTE_STRICT_PROGRESS",
    }
    if set(bindings) != expected_ids:
        missing = ",".join(sorted(expected_ids - set(bindings)))
        raise ValueError("CURRENT_GAP_BINDING_CLASSIFICATION_MISSING:" + missing)
    if len(set(bindings.values())) != 1:
        raise ValueError("CURRENT_GAP_BINDING_DIVERGENCE")

    rel = Path(next(iter(bindings.values())))
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError("CURRENT_GAP_BINDING_PATH_INVALID")
    unresolved = root / rel
    if unresolved.is_symlink():
        raise ValueError("CURRENT_GAP_BINDING_SYMLINK_FORBIDDEN")
    target = unresolved.resolve(strict=True)
    target.relative_to(root)
    if not target.is_file():
        raise ValueError("CURRENT_GAP_BINDING_NOT_FILE")
    return target


def _nonempty_strings(value: Any) -> list[str] | None:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return None
    out: list[str] = []
    for raw in value:
        if not isinstance(raw, str) or not raw:
            return None
        if raw in out:
            return None
        out.append(raw)
    return out


def _proof_digest_valid(proof: Mapping[str, Any]) -> bool:
    claimed = proof.get("proof_sha256")
    if not isinstance(claimed, str) or len(claimed) != 64:
        return False
    material = {k: v for k, v in proof.items() if k != "proof_sha256"}
    return claimed == _sha(material)


def _audit_gap_a(row: Mapping[str, Any], proof: Mapping[str, Any] | None) -> list[str]:
    oid = str(row.get("obligation_id") or "")
    if not isinstance(proof, Mapping):
        return [f"{oid}:AUTHENTICATED_ACQUISITION_OR_TERMINAL_PROOF_REQUIRED"]

    missing: list[str] = []
    if proof.get("route_group") != GAP_A:
        missing.append(f"{oid}:PROOF_ROUTE_GROUP_MISMATCH")

    mode = proof.get("resolution_mode", "STRICT_DISCRIMINATOR")
    if mode == "TERMINAL_COMMON_POLICY":
        if proof.get("currently_available") is not True:
            missing.append(f"{oid}:TERMINAL_CERTIFICATE_CURRENT_AVAILABILITY_NOT_PROVED")
        policy_id = proof.get("common_policy_id")
        if not isinstance(policy_id, str) or not policy_id:
            missing.append(f"{oid}:COMMON_POLICY_ID_NOT_BOUND")
        if proof.get("authenticated_scope_complete_certificate") is not True:
            missing.append(f"{oid}:SCOPE_COMPLETE_TERMINAL_CERTIFICATE_NOT_AUTHENTICATED")
        if proof.get("brain_owned") is not True:
            missing.append(f"{oid}:COMMON_POLICY_BRAIN_OWNERSHIP_NOT_PROVED")
        if proof.get("adequate_over_entire_current_decision_region") is not True:
            missing.append(f"{oid}:COMMON_POLICY_REGION_ADEQUACY_NOT_PROVED")
        if proof.get("safe_over_entire_current_decision_region") is not True:
            missing.append(f"{oid}:COMMON_POLICY_REGION_SAFETY_NOT_PROVED")
        if proof.get("resource_admissible") is not True:
            missing.append(f"{oid}:COMMON_POLICY_RESOURCE_ADMISSIBILITY_NOT_PROVED")
        forbidden = (
            "finite_outcome_ids",
            "outcome_map_complete",
            "max_nonterminal_decision_region_size_after",
        )
        if any(key in proof for key in forbidden):
            missing.append(f"{oid}:TERMINAL_MODE_MUST_NOT_ENCODE_FAKE_DISCRIMINATOR_SHRINK")

    elif mode == "STRICT_DISCRIMINATOR":
        if proof.get("currently_acquirable") is not True:
            missing.append(f"{oid}:CURRENT_ACQUIRABILITY_NOT_PROVED")
        outcomes = _nonempty_strings(proof.get("finite_outcome_ids"))
        if not outcomes:
            missing.append(f"{oid}:FINITE_OUTCOME_SET_NOT_PROVED")
        if proof.get("outcome_map_complete") is not True:
            missing.append(f"{oid}:OUTCOME_MAP_COMPLETENESS_NOT_PROVED")
        before = proof.get("decision_region_size_before")
        after = proof.get("max_nonterminal_decision_region_size_after")
        if (
            isinstance(before, bool)
            or not isinstance(before, int)
            or before <= 1
        ):
            missing.append(f"{oid}:FINITE_DECISION_REGION_BEFORE_INVALID")
        if (
            isinstance(after, bool)
            or not isinstance(after, int)
            or not isinstance(before, int)
            or after < 1
            or after >= before
        ):
            missing.append(f"{oid}:STRICT_DECISION_REGION_SHRINK_NOT_PROVED")
        if proof.get("authenticated_truth_preserving") is not True:
            missing.append(f"{oid}:TRUTH_PRESERVATION_NOT_PROVED")
        if proof.get("safe") is not True:
            missing.append(f"{oid}:SAFETY_NOT_PROVED")
        terminal_only = (
            "currently_available",
            "common_policy_id",
            "authenticated_scope_complete_certificate",
            "adequate_over_entire_current_decision_region",
            "safe_over_entire_current_decision_region",
            "resource_admissible",
        )
        if any(key in proof for key in terminal_only):
            missing.append(f"{oid}:STRICT_MODE_MUST_NOT_MIX_TERMINAL_CERTIFICATE_FIELDS")
    else:
        missing.append(f"{oid}:GAP_A_RESOLUTION_MODE_INVALID")

    if not _proof_digest_valid(proof):
        missing.append(f"{oid}:CONTENT_ADDRESS_PROOF_INVALID")
    return missing


def _audit_gap_b(row: Mapping[str, Any], proof: Mapping[str, Any] | None) -> list[str]:
    oid = str(row.get("obligation_id") or "")
    missing: list[str] = []
    if not isinstance(proof, Mapping):
        return [f"{oid}:EXECUTABLE_PROGRESS_PROOF_REQUIRED"]
    if proof.get("route_group") != GAP_B:
        missing.append(f"{oid}:PROOF_ROUTE_GROUP_MISMATCH")
    action_id = proof.get("verified_action_id")
    if not isinstance(action_id, str) or not action_id:
        missing.append(f"{oid}:VERIFIED_EXECUTABLE_ACTION_NOT_BOUND")
    if proof.get("action_executable_now") is not True:
        missing.append(f"{oid}:ACTION_CURRENT_EXECUTABILITY_NOT_PROVED")
    measure = proof.get("progress_measure")
    if not isinstance(measure, Mapping):
        missing.append(f"{oid}:FINITE_PROGRESS_MEASURE_NOT_BOUND")
    else:
        if measure.get("well_founded") is not True:
            missing.append(f"{oid}:PROGRESS_MEASURE_WELL_FOUNDEDNESS_NOT_PROVED")
        current = measure.get("current_rank")
        floor = measure.get("minimum_rank")
        if (
            isinstance(current, bool)
            or not isinstance(current, int)
            or isinstance(floor, bool)
            or not isinstance(floor, int)
            or current < floor
        ):
            missing.append(f"{oid}:PROGRESS_RANK_INVALID")
    outcomes = proof.get("allowed_outcomes")
    if not isinstance(outcomes, Sequence) or isinstance(outcomes, (str, bytes)) or not outcomes:
        missing.append(f"{oid}:ALLOWED_OUTCOME_SET_NOT_BOUND")
    else:
        for index, outcome in enumerate(outcomes):
            if not isinstance(outcome, Mapping):
                missing.append(f"{oid}:OUTCOME_INVALID:{index}")
                continue
            terminal = outcome.get("terminal") is True
            decreases = outcome.get("strictly_decreases_measure") is True
            if terminal == decreases:
                missing.append(f"{oid}:OUTCOME_NOT_EXACTLY_TERMINAL_OR_DECREASING:{index}")
    if proof.get("safe") is not True:
        missing.append(f"{oid}:SAFETY_NOT_PROVED")
    if not _proof_digest_valid(proof):
        missing.append(f"{oid}:CONTENT_ADDRESS_PROOF_INVALID")
    return missing


def audit(
    manifest: Mapping[str, Any],
    binding: Mapping[str, Any],
    row_proofs: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    open_predicates: list[str] = []
    proofs = row_proofs if isinstance(row_proofs, Mapping) else {}
    rows = manifest.get("rows")
    shared = binding.get("shared_gaps")

    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        errors.append("MANIFEST_ROWS_INVALID")
        rows = []
    if not isinstance(shared, Mapping):
        errors.append("SHARED_GAP_BINDING_INVALID")
        shared = {}

    if len(rows) != 13:
        errors.append("ROW_COUNT_NOT_13")

    ids: list[str] = []
    group_counts = {GAP_A: 0, GAP_B: 0}
    per_row: list[dict[str, Any]] = []

    for raw in rows:
        if not isinstance(raw, Mapping):
            errors.append("ROW_NOT_OBJECT")
            continue
        oid = str(raw.get("obligation_id") or "")
        group = str(raw.get("route_group") or "")
        if not oid or oid in ids:
            errors.append("ROW_ID_INVALID_OR_DUPLICATE:" + oid)
            continue
        ids.append(oid)
        if group not in group_counts:
            errors.append(f"{oid}:UNKNOWN_ROUTE_GROUP:{group}")
            continue
        group_counts[group] += 1
        proof = proofs.get(oid)
        missing = _audit_gap_a(raw, proof) if group == GAP_A else _audit_gap_b(raw, proof)
        open_predicates.extend(missing)
        per_row.append({
            "obligation_id": oid,
            "route_group": group,
            "closed": not missing,
            "missing_predicates": missing,
            "proof_sha256": proof.get("proof_sha256") if isinstance(proof, Mapping) else None,
        })

    declared_a = (shared.get(GAP_A) or {}).get("obligation_count") if isinstance(shared, Mapping) else None
    declared_b = (shared.get(GAP_B) or {}).get("obligation_count") if isinstance(shared, Mapping) else None
    if (
        isinstance(declared_a, bool)
        or not isinstance(declared_a, int)
        or declared_a < 0
    ):
        errors.append("GAP_A_DECLARED_COUNT_INVALID")
    elif group_counts[GAP_A] != declared_a:
        errors.append(
            f"GAP_A_COUNT_MISMATCH:manifest={group_counts[GAP_A]}:binding={declared_a}"
        )
    if (
        isinstance(declared_b, bool)
        or not isinstance(declared_b, int)
        or declared_b < 0
    ):
        errors.append("GAP_B_DECLARED_COUNT_INVALID")
    elif group_counts[GAP_B] != declared_b:
        errors.append(
            f"GAP_B_COUNT_MISMATCH:manifest={group_counts[GAP_B]}:binding={declared_b}"
        )
    if (
        isinstance(declared_a, int)
        and not isinstance(declared_a, bool)
        and isinstance(declared_b, int)
        and not isinstance(declared_b, bool)
        and declared_a + declared_b != 13
    ):
        errors.append("DECLARED_SHARED_GAP_TOTAL_NOT_13")

    cc_r3_proved = not errors and not open_predicates and len(per_row) == 13
    status = (
        "PASS__CC_R3_SHARED_ESCAPE_PROGRESS_PROVED__13_OF_13"
        if cc_r3_proved
        else (
            "PASS__EXECUTABLE_AUDIT_CURRENT__CC_R3_OPEN"
            if not errors
            else "FAIL_CLOSED__AUDIT_INPUT_DRIFT"
        )
    )
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": not errors,
        "cc_r3_proved": cc_r3_proved,
        "row_count": len(per_row),
        "closed_row_count": sum(1 for row in per_row if row["closed"]),
        "open_row_count": sum(1 for row in per_row if not row["closed"]),
        "gap_a_count": group_counts[GAP_A],
        "gap_b_count": group_counts[GAP_B],
        "open_predicates": sorted(open_predicates),
        "rows": per_row,
        "errors": errors,
        "terminal_authority": False,
        "acceptance_credit_delta": 0,
        "terminal_credit_delta": 0,
    }


def audit_repo(
    root: Path = ROOT,
    row_proofs: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    root = Path(root).resolve(strict=True)
    manifest_path = (root / MANIFEST_PATH.relative_to(ROOT)).resolve(strict=True)
    manifest_path.relative_to(root)
    binding_path = _current_binding_path(root)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    binding = json.loads(binding_path.read_text(encoding="utf-8"))
    out = audit(manifest, binding, row_proofs=row_proofs)
    out["current_binding_path"] = binding_path.relative_to(root).as_posix()
    return out


if __name__ == "__main__":
    print(json.dumps(audit_repo(), sort_keys=True))
